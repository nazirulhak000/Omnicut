"""
Pipeline Context for OmniCut Pro Studio Pipeline.
Encapsulates parameters, mutable stage state, and helper methods across all pipeline stages.
"""

import copy
import hashlib
import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from scripts.config import (
    BASE_DIR, DEFAULT_VOICE, DEFAULT_VOICE_RATE
)
from scripts.project_manifest import ProjectManifest, REROLL_STAGE
from scripts.color_theme import extract_explicit_theme, is_color_theme, normalize_hex, resolve_color_theme
from scripts.spotlight_effect import normalize_spotlight


INCREMENTAL_RENDER_SCHEMA_VERSION = 1

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
        return {"schema_version": INCREMENTAL_RENDER_SCHEMA_VERSION, "stage": stage, "inputs": common}

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
        return {
            "schema_version": INCREMENTAL_RENDER_SCHEMA_VERSION,
            "stage": stage,
            "inputs": {
                "cues": cues,
                "total_duration": manifest.get("total_duration"),
                "font_name": _manifest_value(manifest, "font_name"),
                "bilingual_subtitles": _manifest_value(manifest, "bilingual_subtitles"),
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
        return {
            "schema_version": INCREMENTAL_RENDER_SCHEMA_VERSION,
            "stage": stage,
            "inputs": {
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
            },
        }

    if stage == "video":
        lut_name = _manifest_value(manifest, "lut_name")
        return {
            "schema_version": INCREMENTAL_RENDER_SCHEMA_VERSION,
            "stage": stage,
            "inputs": {
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
    price_deal: str = "ลดพิเศษวันนี้"
    custom_script: Optional[str] = None
    script_overlays: Optional[List[str]] = None
    voice: str = DEFAULT_VOICE
    voice_rate: str = DEFAULT_VOICE_RATE
    voice_engine_type: str = "gemini_tts"
    voice_preset: Optional[str] = "gemini_puck_male_hype"
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
    font_name: str = "IBMPlex"
    bilingual_subtitles: bool = True
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

    ass_sub_path: Optional[Path] = None
    effective_overlays: List[Dict[str, Any]] = field(default_factory=list)
    effective_text_overlays: Optional[List[Dict[str, Any]]] = None
    scrim_spans: List[tuple] = field(default_factory=list)
    editorial_pacing: Optional[Dict[str, Any]] = None
    resolved_color_theme: Optional[Dict[str, Any]] = None
    resolved_spotlight: Optional[Dict[str, Any]] = None

    effective_bgm_name: Optional[str] = None
    mixed_audio_path: Optional[Path] = None

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
            "font_name", "bilingual_subtitles", "show_watermark", "sticker_path", "bgm_name",
            "bgm_volume", "bgm_ducking", "audio_mutes", "lut_name",
            "lut_intensity", "product_id", "angle_id", "caption_position",
            "caption_color", "caption_scale", "sticker_position", "sticker_scale",
            "sticker_start_time", "sticker_end_time", "sticker_norm_x",
            "sticker_norm_y", "stickers", "effects", "text_overlays", "overlays",
            "clip_list", "transitions", "spotlight", "background_isolation",
        )
        input_names = input_names + ('editorial_pacing',)
        for name in input_names:
            value = getattr(self, name, None)
            if value is not None:
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
