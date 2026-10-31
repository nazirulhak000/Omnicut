"""
Pipeline Context for OmniCut Pro Studio Pipeline.
Encapsulates parameters, mutable stage state, and helper methods across all pipeline stages.
"""

import copy
import hashlib
import json
import math
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from scripts.config import (
    BASE_DIR, DEFAULT_VOICE, DEFAULT_VOICE_RATE, SFX_VOLUME, VOICE_VOLUME
)
from scripts.project_manifest import ProjectManifest, REROLL_STAGE
from scripts.color_theme import extract_explicit_theme, is_color_theme, normalize_hex, resolve_color_theme
from scripts.spotlight_effect import normalize_spotlight
from scripts.voice_cut_map import resolve_voice_cuts


INCREMENTAL_RENDER_SCHEMA_VERSION = 1


# Retention controls (AI editor viral M3). Both are optional: with no
# target length and the "classic" format the script prompt, the manifest and
# every stage fingerprint stay exactly what they were before these existed.
TARGET_DURATION_CHOICES = (15, 25, 35, 45)
STORY_FORMATS = ("classic", "countdown", "problem_reveal", "myth_buster", "loop")
DEFAULT_STORY_FORMAT = "classic"


def normalize_target_duration(value: Any) -> Optional[int]:
    """A supported target clip length in seconds, or None (= no target).

    Accepts 15/25/35/45 as int, whole float or numeric string; anything else
    (bool, junk, other lengths) falls back silently to None.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(seconds) or seconds != int(seconds):
        return None
    seconds = int(seconds)
    return seconds if seconds in TARGET_DURATION_CHOICES else None


def normalize_story_format(value: Any) -> str:
    """A supported story format id; anything else falls back to "classic"."""
    if isinstance(value, str):
        key = value.strip().lower()
        if key in STORY_FORMATS:
            return key
    return DEFAULT_STORY_FORMAT


def channel_project_name(project_name, channel_id):
    """Main stays flat; a secondary channel may use only its own namespace."""
    if not project_name or channel_id is None:
        return project_name
    from scripts.channel_store import ChannelError
    parts = str(project_name).replace("\\", "/").split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ChannelError(422, "project_name_invalid", "ชื่อโปรเจกต์ไม่ถูกต้อง")
    if channel_id == "main":
        if len(parts) != 1:
            raise ChannelError(404, "resource_not_found", "ไม่พบโปรเจกต์ในช่องนี้")
        return project_name
    if len(parts) == 1:
        return f"{channel_id}/{project_name}"
    if len(parts) != 2 or parts[0] != channel_id:
        raise ChannelError(404, "resource_not_found", "ไม่พบโปรเจกต์ในช่องนี้")
    return "/".join(parts)

# `resume_from` is the stage-order policy. Keep the change-class mapping in
# ProjectManifest so the UI/API and this reuse seam cannot silently drift apart.
CHANGE_CLASS_TO_STAGE = dict(REROLL_STAGE)

STAGE_ARTIFACT_KEYS = {
    "script": None,
    "voice": "voice_audio",
    "mix": "mixed_audio",
    "subtitles": "subtitles_ass",
    "video": "mp4_video",
}

STAGE_DEPENDENCY_ARTIFACT_KEYS = {
    "script": (),
    "voice": (),
    "mix": ("voice_audio",),
    "subtitles": (),
    "video": ("mixed_audio", "subtitles_ass"),
}


def _canonical_json(value: Any) -> str:
    """Serialize a fingerprint payload deterministically across runs."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _payload_fingerprint(payload: Any) -> str:
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _resolve_path(value: Any) -> Optional[Path]:
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        path = BASE_DIR / path
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def _file_identity(value: Any) -> Optional[Dict[str, Any]]:
    """Return a cheap, deterministic identity for an external input file.

    Source/media inputs use path + size + nanosecond mtime rather than a full
    content hash. This avoids hashing a potentially multi-gigabyte source on
    every reroll while still invalidating reuse when the source is replaced in
    the normal filesystem contract. Generated artifacts use `_file_fingerprint`
    below and are content-hashed.
    """
    path = _resolve_path(value)
    if not path:
        return None
    try:
        stat = path.stat()
    except OSError:
        return {"path": str(path), "missing": True}
    if not path.is_file():
        return {"path": str(path), "not_a_file": True}
    return {
        "path": str(path),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _file_fingerprint(value: Any) -> Optional[Dict[str, Any]]:
    """Content fingerprint for a generated artifact, including its identity."""
    path = _resolve_path(value)
    if not path:
        return None
    try:
        stat = path.stat()
        if not path.is_file() or stat.st_size <= 0:
            return {"path": str(path), "valid": False}
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return {"path": str(path), "valid": False}
    return {
        "path": str(path),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": digest.hexdigest(),
        "valid": True,
    }


def _manifest_value(manifest: Dict[str, Any], key: str, default: Any = None) -> Any:
    params = manifest.get("render_params") or {}
    if key in params:
        return params[key]
    return manifest.get(key, default)


# Per-project voice/SFX bus levels set in the editor's Track Mix (L4-05). The
# config value is the default, and [0, 1] is the same ceiling that
# sfx_manager.build_audio_finishing_policy clamps to (loudnorm TP=-1 finishes
# the sum). A level equal to the default counts as "not set", so a project that
# never moved a slider keeps the exact mix fingerprint it was stamped with.
BUS_VOLUME_DEFAULTS = {"voice_volume": VOICE_VOLUME, "sfx_volume": SFX_VOLUME}


def bus_volume_override(manifest: Optional[Dict[str, Any]], key: str) -> Optional[float]:
    """The clamped voice/SFX level a project asks for, or None for the default."""
    default = BUS_VOLUME_DEFAULTS[key]
    raw = _manifest_value(manifest or {}, key)
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    value = round(min(1.0, max(0.0, value)), 3)
    return None if value == default else value


def _bus_volume_inputs(manifest: Dict[str, Any]) -> Dict[str, float]:
    """Mix-fingerprint entries for levels that differ from the default only."""
    inputs: Dict[str, float] = {}
    for key in BUS_VOLUME_DEFAULTS:
        value = bus_volume_override(manifest, key)
        if value is not None:
            inputs[key] = value
    return inputs


def _manifest_artifact_path(manifest: Dict[str, Any], key: str) -> Optional[Path]:
    entry = (manifest.get("artifacts") or {}).get(key) or {}
    return _resolve_path(entry.get("path"))


def _asset_identity(path_or_name: Any) -> Optional[Dict[str, Any]]:
    return _file_identity(path_or_name) if path_or_name else None


def _resolved_bgm_identity(name: Any) -> Optional[Dict[str, Any]]:
    if not name:
        return None
    try:
        from scripts.sfx_manager import SFXManager

        return _file_identity(SFXManager.resolve_bgm_path(str(name)))
    except Exception:
        # Asset lookup is supplemental. The selected name remains in the
        # payload, so a resolver failure cannot make an artifact look newer.
        return None


def _resolved_lut_identity(name: Any) -> Optional[Dict[str, Any]]:
    if not name:
        return None
    try:
        from scripts.asset_registry import AssetRegistry

        return _file_identity(AssetRegistry.resolve_lut_path(str(name)))
    except Exception:
        return None


def _sfx_identities(cues: Any) -> List[Dict[str, Any]]:
    identities: List[Dict[str, Any]] = []
    try:
        from scripts.sfx_manager import SFXManager
    except Exception:
        return identities

    for cue in cues or []:
        if not isinstance(cue, dict) or not cue.get("sfx"):
            continue
        identity = _file_identity(SFXManager.resolve(str(cue["sfx"])))
        identities.append({
            "name": str(cue["sfx"]),
            "file": identity or {"missing": True},
        })
    return identities


# --- Cut-bound SFX (roadmap Q4 follow-up) ----------------------------------
# A transition whoosh within SFX_CUT_SNAP_S of a visual cut is exempt from the
# SFX gap rule (sfx_manager.plan_sfx_events). The cut instants come from the
# clip list laid on the render's frame grid -- the same plan_sequence_frames()
# the renderer and the preview's buildSegments() use.
_MIN_PLAYED_CLIP_S = 0.2  # == timelineMath.js MIN_CLIP_DURATION


def _played_clip_duration(clip: Dict[str, Any]) -> Optional[float]:
    """Seconds a clip occupies on the output timeline, or None when unknown."""
    try:
        speed = float(clip.get("speed") or 1.0)
        speed = min(4.0, max(0.25, speed)) if math.isfinite(speed) else 1.0
        freeze_tail = min(10.0, max(0.0, float(clip.get("freeze_tail") or 0.0)))
        if clip.get("trim_end") is not None:
            span = float(clip["trim_end"]) - float(clip.get("trim_start") or 0.0)
            seconds = span / speed + freeze_tail
        elif clip.get("duration") is not None:
            seconds = float(clip["duration"])
        else:
            return None
    except (TypeError, ValueError):
        return None
    if not math.isfinite(seconds):
        return None
    return max(_MIN_PLAYED_CLIP_S, seconds)


def clip_cut_times(clip_list: Any) -> List[float]:
    """Output-timeline instant of every internal cut of ``clip_list``.

    A hard cut is the frame where the next clip starts; a transition counts
    at its visual midpoint (VideoAssemblyStage centres the overlap on the
    planned cut, so both land on the same instant). Empty when the list has
    fewer than two clips or any clip's played length is unknown.
    """
    clips = [clip for clip in (clip_list or []) if isinstance(clip, dict)]
    if len(clips) < 2:
        return []
    played: List[float] = []
    for clip in clips:
        seconds = _played_clip_duration(clip)
        if seconds is None:
            return []
        played.append(seconds)
    try:
        from scripts.video_editor import (
            DEFAULT_TRANSITION_DURATION, FPS, MAX_TRANSITION_DURATION, plan_sequence_frames,
        )
    except Exception:
        return []
    boundaries: List[Dict[str, Any]] = []
    for clip in clips[1:]:
        kind = str(clip.get("transition_in") or "cut")
        if kind == "cut":
            boundaries.append({"type": "cut"})
            continue
        raw = clip.get("transition_duration")
        try:
            overlap = DEFAULT_TRANSITION_DURATION if raw is None else float(raw)
        except (TypeError, ValueError):
            overlap = DEFAULT_TRANSITION_DURATION
        boundaries.append({"type": kind, "duration": min(MAX_TRANSITION_DURATION, max(0.1, overlap))})
    plan = plan_sequence_frames(played, boundaries, FPS)
    return [
        round((plan["start"][i] + plan["end"][i - 1]) / 2.0 / FPS, 6)
        for i in range(1, len(clips))
    ]


def cut_bound_sfx_plan(
    cues: Any,
    overlays: Any,
    total_duration: Any,
    cut_times: Optional[List[float]],
    base_cut_times: Optional[List[float]] = None,
) -> Optional[List[List[Any]]]:
    """The kept SFX events (``[source, index]``) when binding whooshes to
    ``cut_times`` changes the mix plan versus ``base_cut_times``; else None.

    Mirrors the plan inputs SFXManager.mix_audio_track uses (resolved file
    names, boom availability), so a None here means the mix would come out
    identical with or without these cuts.
    """
    if not cut_times:
        return None
    try:
        from scripts.sfx_manager import SFXManager, plan_sfx_events

        def _name(tag):
            path = SFXManager.resolve(tag) if tag else None
            return path.name if path and path.exists() else None

        boom = SFXManager.resolve("boom")
        boom_available = bool(boom and boom.exists())
        try:
            duration = float(total_duration) if total_duration is not None else None
        except (TypeError, ValueError):
            duration = None

        def _keys(cuts):
            return [
                [event["source"], event["index"]]
                for event in plan_sfx_events(
                    cues or [], overlays or [], total_duration=duration,
                    boom_available=boom_available, cut_times=cuts, sfx_filename=_name,
                )
            ]

        with_cuts = _keys(list(cut_times))
        return with_cuts if with_cuts != _keys(list(base_cut_times or [])) else None
    except Exception:
        return None


def _artifact_fingerprints_from_manifest(manifest: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    fingerprints: Dict[str, Dict[str, Any]] = {}
    for key in {key for key in STAGE_ARTIFACT_KEYS.values() if key}:
        path = _manifest_artifact_path(manifest, key)
        fingerprint = _file_fingerprint(path)
        if fingerprint:
            fingerprints[key] = fingerprint
    return fingerprints


def _stage_payload_from_manifest(
    manifest: Dict[str, Any],
    stage: str,
    artifact_fingerprints: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build the persisted input contract for one reusable stage."""
    artifact_fingerprints = artifact_fingerprints or {}
    raw_video_path = _manifest_value(manifest, "raw_video_path")
    human_voice_path = _manifest_value(manifest, "human_voice_audio_path")
    cues = manifest.get("cues") or []
    micro_cues = manifest.get("micro_cues") or cues
    overlays = manifest.get("overlays")
    if overlays is None:
        overlays = _manifest_value(manifest, "overlays")
    text_overlays = manifest.get("text_overlays")
    if text_overlays is None:
        text_overlays = _manifest_value(manifest, "text_overlays")

    common = {
        "product_name": _manifest_value(manifest, "product_name"),
        "key_features": _manifest_value(manifest, "key_features"),
        "pain_point": _manifest_value(manifest, "pain_point"),
        "price_deal": _manifest_value(manifest, "price_deal"),
        "custom_script": _manifest_value(manifest, "custom_script"),
        "script_overlays": _manifest_value(manifest, "script_overlays"),
        "ad_tone": _manifest_value(manifest, "ad_tone"),
        "angle": manifest.get("angle") or {},
    }

    if stage == "script":
        script_inputs = dict(common)
        # Retention controls shape the AI script. The keys are absent at their
        # defaults so a project that never set them keeps the fingerprint it
        # was stamped with.
        target_duration = normalize_target_duration(_manifest_value(manifest, "target_duration"))
        if target_duration is not None:
            script_inputs["target_duration"] = target_duration
        story_format = normalize_story_format(_manifest_value(manifest, "story_format"))
        if story_format != DEFAULT_STORY_FORMAT:
            script_inputs["story_format"] = story_format
        return {"schema_version": INCREMENTAL_RENDER_SCHEMA_VERSION, "stage": stage, "inputs": script_inputs}

    if stage == "voice":
        return {
            "schema_version": INCREMENTAL_RENDER_SCHEMA_VERSION,
            "stage": stage,
            "inputs": {
                "script_data": manifest.get("script_data") or {},
                "voice": _manifest_value(manifest, "voice"),
                "voice_rate": _manifest_value(manifest, "voice_rate"),
                "voice_engine_type": _manifest_value(manifest, "voice_engine_type"),
                "voice_engine_used": _manifest_value(manifest, "voice_engine_used") or _manifest_value(manifest, "voice_engine_type"),
                "voice_preset": _manifest_value(manifest, "voice_preset"),
                "ad_tone": _manifest_value(manifest, "ad_tone"),
                "human_voice_audio": _asset_identity(human_voice_path),
            },
        }

    if stage == "subtitles":
        from scripts.channel_identity import resolve_channel_identity, identity_fingerprint
        identity = resolve_channel_identity(_manifest_value(manifest, "channel_identity_snapshot"), channel_id=manifest.get("channel_id"))
        return {
            "schema_version": INCREMENTAL_RENDER_SCHEMA_VERSION,
            "stage": stage,
            "inputs": {
                "channel_identity": identity_fingerprint(identity),
                "cues": cues,
                "total_duration": manifest.get("total_duration"),
                "font_name": _manifest_value(manifest, "font_name"),
                "bilingual_subtitles": _manifest_value(manifest, "bilingual_subtitles"),
                "ghost_reveal": _manifest_value(manifest, "ghost_reveal", True),
                "show_watermark": _manifest_value(manifest, "show_watermark", True),
                "style_preset": _manifest_value(manifest, "style_preset"),
                "hook_brand": _manifest_value(manifest, "hook_brand"),
                "hook_model": _manifest_value(manifest, "hook_model"),
                "hook_label": _manifest_value(manifest, "hook_label"),
                "hook_duration": _manifest_value(manifest, "hook_duration", 5.0),
                "hook_motion": _manifest_value(manifest, "hook_motion"),
                "hook_colors": _manifest_value(manifest, "hook_colors"),
                "hook_style": _manifest_value(manifest, "hook_style"),
                "overlays": overlays,
                "product": manifest.get("product") or {},
                "color_theme": _manifest_value(manifest, "color_theme"),
                "color_theme_input": _manifest_value(manifest, "color_theme_input"),
                "text_overlays": text_overlays,
                "caption_position": _manifest_value(manifest, "caption_position"),
                "caption_color": _manifest_value(manifest, "caption_color"),
                "caption_scale": _manifest_value(manifest, "caption_scale"),
                "editorial_pacing": _manifest_value(manifest, "editorial_pacing"),
            },
        }

    if stage == "mix":
        bgm_name = _manifest_value(manifest, "bgm_name")
        mix_inputs = {
            "voice_audio": artifact_fingerprints.get("voice_audio"),
            "micro_cues": micro_cues,
            "total_duration": manifest.get("total_duration"),
            "overlays": overlays,
            "bgm_name": bgm_name,
            "bgm_file": _resolved_bgm_identity(bgm_name),
            "bgm_volume": _manifest_value(manifest, "bgm_volume"),
            "bgm_ducking": _manifest_value(manifest, "bgm_ducking"),
            "audio_mutes": _manifest_value(manifest, "audio_mutes") or {},
            "sfx_files": _sfx_identities(micro_cues),
            **_bus_volume_inputs(manifest),
        }
        # Ripple cuts of the voice (source seconds). Only the cuts the mix will
        # really apply count -- stale/invalid ones are ignored exactly like the
        # voice stage ignores them -- and the key is absent without cuts, so a
        # project that never cut keeps the fingerprint it was stamped with.
        voice_cuts, _, _ = resolve_voice_cuts(
            manifest.get("voice_edit"), artifact_fingerprints.get("voice_audio")
        )
        if voice_cuts:
            mix_inputs["voice_cuts"] = [[cut["start"], cut["end"]] for cut in voice_cuts]
        # Whooshes bound to visual cuts. Present only when the binding really
        # changes which SFX the mix keeps, so a project where it does not keeps
        # its stamped fingerprint, and a clip edit that moves such a cut re-mixes.
        cut_plan = cut_bound_sfx_plan(
            micro_cues, overlays, manifest.get("total_duration"),
            clip_cut_times(manifest.get("clip_list") or _manifest_value(manifest, "clip_list")),
        )
        if cut_plan:
            mix_inputs["cut_bound_sfx"] = cut_plan
        return {
            "schema_version": INCREMENTAL_RENDER_SCHEMA_VERSION,
            "stage": stage,
            "inputs": mix_inputs,
        }

    if stage == "video":
        from scripts.channel_identity import resolve_channel_identity, identity_fingerprint
        identity = resolve_channel_identity(_manifest_value(manifest, "channel_identity_snapshot"), channel_id=manifest.get("channel_id"))
        lut_name = _manifest_value(manifest, "lut_name")
        return {
            "schema_version": INCREMENTAL_RENDER_SCHEMA_VERSION,
            "stage": stage,
            "inputs": {
                "channel_identity": identity_fingerprint(identity),
                "raw_video": _asset_identity(raw_video_path),
                "total_duration": manifest.get("total_duration"),
                "clip_list": manifest.get("clip_list") or _manifest_value(manifest, "clip_list"),
                "transitions": manifest.get("transitions") or _manifest_value(manifest, "transitions"),
                "mixed_audio": artifact_fingerprints.get("mixed_audio"),
                "subtitles_ass": artifact_fingerprints.get("subtitles_ass"),
                "sticker_path": _asset_identity(_manifest_value(manifest, "sticker_path")),
                "stickers": _manifest_value(manifest, "stickers"),
                "effects": _manifest_value(manifest, "effects"),
                "spotlight": normalize_spotlight(_manifest_value(manifest, "spotlight")),
                "overlays": overlays,
                "product": manifest.get("product") or {},
                "color_theme": _manifest_value(manifest, "color_theme"),
                "color_theme_input": _manifest_value(manifest, "color_theme_input"),
                "lut_name": lut_name,
                "lut_file": _resolved_lut_identity(lut_name),
                "lut_intensity": _manifest_value(manifest, "lut_intensity"),
                "style_preset": _manifest_value(manifest, "style_preset"),
                "sticker_position": _manifest_value(manifest, "sticker_position"),
                "sticker_scale": _manifest_value(manifest, "sticker_scale"),
                "sticker_start_time": _manifest_value(manifest, "sticker_start_time"),
                "sticker_end_time": _manifest_value(manifest, "sticker_end_time"),
                "sticker_norm_x": _manifest_value(manifest, "sticker_norm_x"),
                "sticker_norm_y": _manifest_value(manifest, "sticker_norm_y"),
            },
        }

    raise ValueError(f"Unknown incremental-render stage: {stage}")


def build_incremental_render_metadata(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Create the strict reuse metadata after a successful manifest save."""
    artifact_fingerprints = _artifact_fingerprints_from_manifest(manifest)
    stage_fingerprints = {
        stage: _payload_fingerprint(_stage_payload_from_manifest(manifest, stage, artifact_fingerprints))
        for stage in STAGE_ARTIFACT_KEYS
    }
    return {
        "schema_version": INCREMENTAL_RENDER_SCHEMA_VERSION,
        "stage_fingerprints": stage_fingerprints,
        "artifact_fingerprints": artifact_fingerprints,
    }


def stage_for_change(change_class: str) -> str:
    """Resolve a UI change class through the canonical reroll policy."""
    try:
        return CHANGE_CLASS_TO_STAGE[change_class]
    except KeyError as exc:
        valid = ", ".join(sorted(CHANGE_CLASS_TO_STAGE))
        raise ValueError(f"Unknown change class '{change_class}'. Expected one of: {valid}") from exc


@dataclass
class PipelineContext:
    """Carries inputs, options, intermediate results, and progress hooks through stages."""

    # 1. Pipeline Inputs
    product_name: str
    raw_video_path: str
    project_name: Optional[str] = None
    key_features: str = "แม่เหล็กแรงดูดสูง เสียบง่าย ชาร์จเร็ว ไม่ทำร้ายแบต"
    pain_point: str = "สายชาร์จพังง่าย เสียบยากในที่มืด"
    price_deal: str = ""  # never a price/promo: clips must not mention price (project rule)
    custom_script: Optional[str] = None
    script_overlays: Optional[List[str]] = None
    voice: str = DEFAULT_VOICE
    voice_rate: str = DEFAULT_VOICE_RATE
    voice_engine_type: str = "gemini_tts"
    voice_preset: Optional[str] = "gemini_fenrir_male_strong"
    ad_tone: str = "commercial_hype"
    style_preset: str = "clean_tech_review"
    human_voice_audio_path: Optional[str] = None
    hook_brand: Optional[str] = None
    hook_model: Optional[str] = None
    hook_label: Optional[str] = None
    hook_duration: float = 5.0
    hook_motion: Optional[Dict[str, Any]] = None
    hook_colors: Optional[Dict[str, str]] = None
    hook_style: Optional[Dict[str, object]] = None
    # Retention controls (M3): target clip length (15/25/35/45 s, None = no
    # target) and story format. Normalised in __post_init__; bad input falls
    # back to the defaults silently.
    target_duration: Optional[int] = None
    story_format: str = DEFAULT_STORY_FORMAT
    font_name: str = "IBMPlex"
    bilingual_subtitles: bool = True
    # Progressive Ghost Reveal captions (SOP Phase 3) -- on by default, and
    # switchable per project from the caption inspector.
    ghost_reveal: bool = True
    show_watermark: Optional[bool] = None
    use_ai_vision: bool = True
    sticker_path: Optional[str] = None
    bgm_name: Optional[str] = None
    bgm_volume: Optional[float] = None
    bgm_ducking: bool = True
    audio_mutes: Optional[Dict[str, bool]] = None
    lut_name: Optional[str] = None
    lut_intensity: float = 1.0
    clip_list: Optional[List[Dict[str, Any]]] = None
    transitions: Optional[List[str]] = None
    export_mp4: bool = True
    export_preset: str = "post"
    product_id: Optional[str] = None
    angle_id: Optional[str] = None
    caption_position: str = "bottom"
    caption_color: Optional[str] = None
    caption_scale: float = 1.0
    text_overlays: Optional[List[Dict[str, Any]]] = None
    sticker_position: str = "top_right"
    sticker_scale: float = 1.0
    sticker_start_time: Optional[float] = None
    sticker_end_time: Optional[float] = None
    sticker_norm_x: Optional[float] = None
    sticker_norm_y: Optional[float] = None
    stickers: Optional[List[Dict[str, Any]]] = None
    effects: Optional[List[Dict[str, Any]]] = None
    resume_from: Optional[str] = None
    product_meta: Optional[Dict[str, Any]] = None
    # Optional explicit ColorThemeV1 input. The resolved contract is kept
    # separately so a manifest can persist the effective theme without
    # confusing it with the caller's override.
    color_theme: Optional[Dict[str, Any]] = None
    # Optional Product SpotlightV1 input.  The canonical value is resolved
    # lazily so old manifests and omitted requests stay a true no-op.
    spotlight: Optional[Dict[str, Any]] = None
    background_isolation: Optional[Dict[str, Any]] = None
    angle_meta: Optional[Dict[str, Any]] = None
    progress_callback: Optional[Callable[[str, float], None]] = None
    overlays: Optional[List[Dict[str, Any]]] = None
    cancel_event: Optional[threading.Event] = None
    channel_id: Optional[str] = None
    channel_identity_snapshot: Optional[Dict[str, Any]] = None
    job_scope: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        self.target_duration = normalize_target_duration(self.target_duration)
        self.story_format = normalize_story_format(self.story_format)
        from scripts.render_jobs import pin_job_scope
        self.job_scope = pin_job_scope(self.channel_id, self.job_scope)
        self.channel_id = self.job_scope.get("channel_id", self.channel_id)
        captured_identity = self.job_scope.get("channel_identity_snapshot")
        if self.channel_identity_snapshot is not None and captured_identity is not None and self.channel_identity_snapshot != captured_identity:
            from scripts.channel_store import ChannelError
            raise ChannelError(422, "channel_scope_conflict", "identity ของ pipeline ไม่ตรงกับงานที่ตรึงไว้")
        identity = self.channel_identity_snapshot or self.job_scope.get("channel_identity_snapshot")
        if identity is not None or self.channel_id is not None:
            from scripts.channel_identity import resolve_channel_identity
            identity = resolve_channel_identity(identity, channel_id=self.channel_id)
        self.channel_identity_snapshot = copy.deepcopy(identity)
        if identity is not None:
            self.job_scope = pin_job_scope(self.channel_id, {**self.job_scope, "channel_identity_snapshot": self.channel_identity_snapshot})

    def store_kwargs(self):
        """Direct legacy callers remain unscoped; request jobs always pin an ID."""
        return {"channel_id": self.channel_id} if self.channel_id is not None else {}

    def guard_media(self, value):
        """Request jobs check private artifact owners; standalone CLI stays compatible."""
        if self.channel_id is None:
            return Path(value)
        from scripts.channel_scope import ChannelScope
        from scripts.channel_workflows import require_media_owner
        provenance = self.job_scope or {}
        scope = ChannelScope(self.channel_id, provenance.get("channel_scope_source", "header"), bool(provenance.get("channel_scope_strict", False)))
        return require_media_owner(scope, value, base_dir=BASE_DIR)

    # 2. Stage Execution State
    project_dir: Optional[Path] = None
    is_reroll: bool = False
    manifest: Optional[Dict[str, Any]] = None
    raw_video: Optional[Path] = None
    is_image_source: bool = False
    image_files: List[str] = field(default_factory=list)

    voice_engine_used: str = "gemini_tts"
    script_data: Optional[Dict[str, Any]] = None
    cues: List[Dict[str, Any]] = field(default_factory=list)
    micro_cues: List[Dict[str, Any]] = field(default_factory=list)
    # One cue per script LINE (hook/feature/cta), set by VoiceStage before
    # SubtitleStage overwrites `cues` with subtitle-burst-level `micro_cues`.
    # This is the granularity scripts/shot_list_builder.py's shot list and
    # the guided-take mapping in ShotMatchingStage need -- see
    # C:\Users\Winon\.claude\plans\cheeky-cooking-quokka.md.
    beat_cues: List[Dict[str, Any]] = field(default_factory=list)
    total_duration: float = 0.0
    voice_audio_path: Optional[Path] = None
    # Ripple-cut state of the voice (scripts/voice_cut_map.py), set by VoiceStage:
    # `voice_edit` is the manifest object ONLY when its fingerprint matches the
    # current voice file, `voice_cuts` its normalised cuts in SOURCE seconds
    # (what the mix drops), `voice_source_duration` the real file length. When
    # the saved cuts cannot be used `voice_edit_stale` is set and
    # `voice_edit_notice` carries the Thai reason for the editor to show.
    voice_edit: Optional[Dict[str, Any]] = None
    voice_cuts: List[Dict[str, Any]] = field(default_factory=list)
    voice_source_duration: float = 0.0
    voice_edit_stale: bool = False
    voice_edit_notice: Optional[str] = None

    ass_sub_path: Optional[Path] = None
    effective_overlays: List[Dict[str, Any]] = field(default_factory=list)
    effective_text_overlays: Optional[List[Dict[str, Any]]] = None
    scrim_spans: List[tuple] = field(default_factory=list)
    editorial_pacing: Optional[Dict[str, Any]] = None
    resolved_color_theme: Optional[Dict[str, Any]] = None
    resolved_spotlight: Optional[Dict[str, Any]] = None

    effective_bgm_name: Optional[str] = None
    mixed_audio_path: Optional[Path] = None
    # The SFXManager.mix_audio_track kwargs of the mix made in THIS render
    # (None when the mix was reused/skipped). AudioMixStage.sync_cut_bound_sfx
    # re-runs it once with the final cut times when they change the SFX plan.
    mix_request: Optional[Dict[str, Any]] = None

    actual_clip_list: Optional[List[Dict[str, Any]]] = None
    ai_matched_shots: Optional[List[Dict[str, Any]]] = None
    shot_scales: Optional[List[float]] = None

    # Guided-take filming feature (scripts/recording_sessions.py,
    # scripts/shot_list_builder.py) -- see
    # C:\Users\Winon\.claude\plans\cheeky-cooking-quokka.md (Phase D).
    # `guided_take_meta` is populated by SourceResolutionStage from a raw
    # video's `.guided_take.json` sidecar when present, and lets
    # ShotMatchingStage map footage onto script beats exactly, skipping AI
    # vision entirely. `shot_list_id` is the manual-upload fallback trigger
    # ("map to this shot list"): with no sidecar present, ShotMatchingStage
    # instead divides the raw video proportionally by each beat's planned
    # duration ratio.
    guided_take_meta: Optional[Dict[str, Any]] = None
    shot_list_id: Optional[str] = None
    # User-curated beat→scene assignments from the Manual Storyboard Mapper.
    # List of {beat_index, video_path, trim_start, trim_end}.
    # ShotMatchingStage reads this; beats with a pinned entry skip AI Vision
    # and use the specified clip span directly.
    manual_shot_map: List[Dict[str, Any]] = field(default_factory=list)

    out_mp4: Optional[Path] = None
    result_paths: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    # Monotonic measurements are runtime diagnostics only. They are persisted
    # by VideoAssemblyStage as an inspectable render-performance snapshot, but
    # never participate in reuse fingerprints or render inputs.
    pipeline_started_at: Optional[float] = None
    stage_timings: Dict[str, float] = field(default_factory=dict)
    _fingerprint_cache: Dict[str, Dict[str, Any]] = field(default_factory=dict, init=False, repr=False)

    def resolve_color_theme_contract(self) -> Dict[str, Any]:
        """Resolve and cache the one colour contract shared by pipeline stages."""
        if self.resolved_color_theme is not None:
            return copy.deepcopy(self.resolved_color_theme)

        manifest = self.manifest if isinstance(self.manifest, dict) else {}
        params = manifest.get("render_params") or {}
        product: Dict[str, Any] = {}
        saved_product = manifest.get("product")
        if isinstance(saved_product, dict):
            product.update(copy.deepcopy(saved_product))
        if isinstance(self.product_meta, dict):
            product.update(copy.deepcopy(self.product_meta))

        explicit = self.color_theme if isinstance(self.color_theme, dict) else None
        if explicit is None:
            explicit = extract_explicit_theme(product)

        persisted = manifest.get("color_theme") or params.get("color_theme")
        preview = resolve_color_theme(product, style_preset=self.style_preset)
        product_colour = ((preview.get("source_metadata") or {}).get("product_color"))

        # A successful prior render is authoritative when there is no new
        # product colour/theme input. This keeps rerenders byte-for-byte stable
        # even if a future style fallback palette is edited.
        if explicit is None and not normalize_hex(product_colour) and is_color_theme(persisted):
            resolved = copy.deepcopy(dict(persisted))
        else:
            resolved = resolve_color_theme(
                product,
                explicit_theme=explicit,
                style_preset=self.style_preset,
            )
        self.resolved_color_theme = copy.deepcopy(resolved)
        return copy.deepcopy(resolved)

    def resolve_spotlight_contract(self) -> Dict[str, Any]:
        """Resolve the optional SpotlightV1 contract from input or manifest.

        Normalisation is the only boundary that can produce a value consumed
        by a renderer.  This prevents invalid/raw filter strings from
        crossing the pipeline and makes manifest reuse deterministic.
        """
        if self.resolved_spotlight is not None:
            return copy.deepcopy(self.resolved_spotlight)

        manifest = self.manifest if isinstance(self.manifest, dict) else {}
        candidate = self.spotlight
        if candidate is None:
            candidate = _manifest_value(manifest, "spotlight")
        if candidate is None and isinstance(self.effects, list):
            # Keep the legacy effects array usable as a transport for the
            # optional editor effect. This mirrors SequencePlayer's fallback
            # while preserving ordinary decorative effects unchanged.
            for item in self.effects:
                if not isinstance(item, dict):
                    continue
                kind = str(
                    item.get("kind")
                    or item.get("type")
                    or item.get("effect_type")
                    or ""
                ).strip().lower()
                if kind not in {"spotlight", "spotlightv1"}:
                    continue
                if "config" in item:
                    candidate = item["config"]
                elif "spotlight" in item:
                    candidate = item["spotlight"]
                else:
                    candidate = item
                break
        resolved = normalize_spotlight(candidate)
        self.resolved_spotlight = copy.deepcopy(resolved)
        return copy.deepcopy(resolved)

    def resolve_background_isolation_contract(self) -> Optional[Dict[str, Any]]:
        """Return subject-isolation metadata without activating unsafe paths.

        Artifact readiness and filesystem containment are checked by the
        renderer against the published cache manifest. This resolver only
        carries the optional contract across project save/load boundaries.
        """
        candidate = self.background_isolation
        if candidate is None and isinstance(self.manifest, dict):
            candidate = _manifest_value(self.manifest, "background_isolation")
            if candidate is None:
                candidate = _manifest_value(self.manifest, "backgroundIsolation")
        if not isinstance(candidate, dict):
            return None
        return copy.deepcopy(candidate)

    def notify(self, msg: str, progress: float) -> None:
        """Invokes the progress callback safely if one was registered."""
        if self.progress_callback:
            try:
                self.progress_callback(msg, progress)
            except Exception:
                pass

    def should_run(self, stage: str) -> bool:
        """Return whether a stage must run, including strict reuse validation.

        `resume_from` remains the explicit reroll policy. For manifests written
        with incremental-render metadata, an earlier stage is also rerun when
        its persisted input fingerprint or artifact fingerprint no longer
        matches. This turns silent stale-artifact reuse into a safe rebuild.
        Legacy manifests keep their old stage-order behavior until a successful
        render stamps the new metadata, preserving compatibility with existing
        projects that predate this contract.
        """
        if ProjectManifest.should_run(stage, self.resume_from):
            return True
        if not self.manifest:
            return False
        reusable, _ = self._reuse_status(stage=stage)
        return not reusable

    def out_path(self, stem: str, suffix: str) -> Path:
        """Returns a versioned path when rerolling or standard project dir path."""
        if self.is_reroll and self.project_name:
            return ProjectManifest.versioned_path(self.project_name, stem, suffix)
        if self.project_dir:
            return self.project_dir / f"{stem}{suffix}"
        raise ValueError("Cannot resolve out_path before project_dir is set")

    def reuse(self, key: str, label: str) -> Path:
        """Retrieves existing artifact path from manifest for partial rerolls."""
        if not self.manifest:
            raise FileNotFoundError(f"สุ่มใหม่ไม่ได้ — ไม่พบ manifest สำหรับ {label}")
        existing = ProjectManifest.artifact_path(self.manifest, key)
        if not existing:
            raise FileNotFoundError(
                f"สุ่มใหม่ไม่ได้ — ไม่พบไฟล์ {label} ของรอบก่อน ต้อง render เต็มรอบใหม่"
            )
        self.guard_media(existing)
        stage = next((s for s, artifact_key in STAGE_ARTIFACT_KEYS.items() if artifact_key == key), None)
        reusable, reason = self._reuse_status(stage=stage, key=key, path=existing)
        if not reusable:
            raise FileNotFoundError(
                f"Cannot safely reuse {label}: {reason}. Re-render the affected stage."
            )
        return existing

    @staticmethod
    def stage_for_change(change_class: str) -> str:
        """Resolve a UI change class through the canonical reroll policy."""
        return stage_for_change(change_class)

    def expected_stage_fingerprint(self, stage: str) -> str:
        """Return the fingerprint expected by the current context inputs."""
        snapshot = self._manifest_snapshot_from_context()
        artifact_fingerprints = self._current_artifact_fingerprints(snapshot, stage)
        return _payload_fingerprint(
            _stage_payload_from_manifest(snapshot, stage, artifact_fingerprints)
        )

    def _has_strict_reuse_metadata(self) -> bool:
        metadata = (self.manifest or {}).get("incremental_render") or {}
        return metadata.get("schema_version") == INCREMENTAL_RENDER_SCHEMA_VERSION

    def _manifest_snapshot_from_context(self) -> Dict[str, Any]:
        """Overlay the runtime context onto the last persisted manifest."""
        snapshot: Dict[str, Any] = dict(self.manifest or {})
        params = dict(snapshot.get("render_params") or {})

        # These are all inputs persisted by VideoAssemblyStage. Keeping the
        # overlay list explicit is important: a reroll may change overlays
        # while still reusing voice and mix artifacts.
        input_names = (
            "product_name", "key_features", "pain_point", "price_deal",
            "custom_script", "script_overlays", "voice", "voice_rate",
            "voice_engine_type", "voice_preset", "ad_tone", "style_preset",
            "human_voice_audio_path", "hook_brand", "hook_model", "hook_label",
            "hook_duration", "hook_motion", "hook_colors", "hook_style",
            "font_name", "bilingual_subtitles", "ghost_reveal", "show_watermark", "sticker_path", "bgm_name",
            "bgm_volume", "bgm_ducking", "audio_mutes", "lut_name",
            "lut_intensity", "product_id", "angle_id", "caption_position",
            "caption_color", "caption_scale", "sticker_position", "sticker_scale",
            "sticker_start_time", "sticker_end_time", "sticker_norm_x",
            "sticker_norm_y", "stickers", "effects", "text_overlays", "overlays",
            "clip_list", "transitions", "spotlight", "background_isolation",
            "channel_identity_snapshot",
        )
        input_names = input_names + ('editorial_pacing',)
        for name in input_names:
            value = getattr(self, name, None)
            if value is not None:
                snapshot[name] = value
                params[name] = value
        # The context is authoritative for the retention controls even at
        # their defaults: clearing a target must not leave the persisted one
        # in the snapshot (the script fingerprint drops default values).
        for name in ("target_duration", "story_format"):
            value = getattr(self, name, None)
            snapshot[name] = value
            params[name] = value

        if self.raw_video is not None:
            snapshot["raw_video_path"] = str(self.raw_video)
            params["raw_video_path"] = str(self.raw_video)
        if self.angle_meta is not None:
            snapshot["angle"] = self.angle_meta
        if self.product_meta is not None:
            snapshot["product"] = self.product_meta
        if self.color_theme is not None:
            params["color_theme_input"] = self.color_theme
        if self.resolved_color_theme is not None:
            snapshot["color_theme"] = self.resolved_color_theme
            params["color_theme"] = self.resolved_color_theme
        if self.resolved_spotlight is not None:
            snapshot["spotlight"] = self.resolved_spotlight
            params["spotlight"] = self.resolved_spotlight
        if self.script_data is not None:
            snapshot["script_data"] = self.script_data
        if self.cues:
            snapshot["cues"] = self.cues
        if self.micro_cues:
            snapshot["micro_cues"] = self.micro_cues
        if self.total_duration:
            snapshot["total_duration"] = self.total_duration
        if self.voice_edit is not None:
            snapshot["voice_edit"] = self.voice_edit
        if self.effective_overlays:
            snapshot["overlays"] = self.effective_overlays
            params["overlays"] = self.effective_overlays
        if self.effective_text_overlays is not None:
            snapshot["text_overlays"] = self.effective_text_overlays
            params["text_overlays"] = self.effective_text_overlays
        if self.editorial_pacing is not None:
            snapshot['editorial_pacing'] = self.editorial_pacing
        if self.actual_clip_list is not None:
            snapshot["clip_list"] = self.actual_clip_list
            params["clip_list"] = self.actual_clip_list
        if self.effective_bgm_name:
            snapshot["bgm_name"] = self.effective_bgm_name
            params["bgm_name"] = self.effective_bgm_name

        snapshot["render_params"] = params
        return snapshot

    def _current_artifact_fingerprints(
        self, snapshot: Dict[str, Any], stage: str
    ) -> Dict[str, Dict[str, Any]]:
        fingerprints: Dict[str, Dict[str, Any]] = {}
        context_paths = {
            "voice_audio": self.voice_audio_path,
            "mixed_audio": self.mixed_audio_path,
            "subtitles_ass": self.ass_sub_path,
            "mp4_video": self.out_mp4 or self.result_paths.get("mp4_video"),
        }
        dependency_keys = STAGE_DEPENDENCY_ARTIFACT_KEYS.get(stage, ())
        for key in dependency_keys:
            path = context_paths.get(key) or _manifest_artifact_path(snapshot, key)
            if not path:
                continue
            identity = _file_identity(path)
            cache_key = _canonical_json(identity)
            cache_name = f"{key}:{cache_key}"
            cached = self._fingerprint_cache.get(cache_name)
            if cached is None:
                cached = _file_fingerprint(path)
                if cached:
                    self._fingerprint_cache[cache_name] = cached
            if cached:
                fingerprints[key] = cached
        return fingerprints

    def _reuse_status(
        self,
        stage: Optional[str],
        key: Optional[str] = None,
        path: Optional[Path] = None,
    ) -> tuple:
        """Return `(reusable, reason)` for a stage/artifact pair."""
        if not self.manifest:
            return False, "manifest is missing"

        if not stage and key:
            return False, f"artifact key '{key}' is not covered by the reuse contract"

        if stage == "script" and not self.manifest.get("script_data"):
            return False, "persisted script data is missing"

        key = key or STAGE_ARTIFACT_KEYS.get(stage or "")
        if key:
            path = path or _manifest_artifact_path(self.manifest, key)
            if not path:
                return False, f"artifact '{key}' is missing"
            current = _file_fingerprint(path)
            if not current or not current.get("valid"):
                return False, f"artifact '{key}' is missing, empty, or not a file"
        else:
            current = None

        if not self._has_strict_reuse_metadata():
            # Old manifests have no declared input/output identity. Keep them
            # usable, but the file-level checks above still reject empty or
            # non-file paths. A successful job stamps strict metadata.
            return True, "legacy manifest"

        if not stage or stage not in STAGE_ARTIFACT_KEYS:
            return False, "stage is not covered by the reuse contract"

        metadata = self.manifest.get("incremental_render") or {}
        expected = self.expected_stage_fingerprint(stage)
        actual = (metadata.get("stage_fingerprints") or {}).get(stage)
        if actual != expected:
            return False, f"stage fingerprint mismatch for '{stage}'"

        if key:
            stored = (metadata.get("artifact_fingerprints") or {}).get(key)
            if stored != current:
                return False, f"artifact fingerprint mismatch for '{key}'"
        return True, "fingerprint verified"
