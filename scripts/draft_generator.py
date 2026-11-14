"""
OmniCut Pro Studio - CapCut Draft Generator & AI Flow Auto-Slotter
scripts/draft_generator.py

Auto-slots AI Flow B-roll clips into CapCut draft timelines at exact beat timestamps
with strict compliance to:
  - Rule 3.3: CapCut draft backup (draft_content.json.bak mandatory before writes)
  - Rule 4.7: J-Cut Transitions (150ms-250ms audio lead-in, grid 1/30s)
  - Rule 4.17: Strict Topic Hold (B-roll stays locked to narration for full beat)
  - Rule 4.1: 9:16 Canvas standard (1080x1920, 30 FPS)
  - Rule 4.5: Audio mix standard (Voice 1.0, BGM 0.12)
"""

from __future__ import annotations

import json
import logging
import math
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.config import (
    BASE_DIR,
    CAPCUT_DRAFT_DIR,
    PROJECTS_DIR,
    RAW_DIR,
    ASSETS_DIR,
)
from scripts.capcut_builder import (
    upgrade_draft_content_to_7_1,
    CAPCUT_7_1_MATERIAL_KEYS,
)
from scripts.shot_matching import (
    match_flow_clips_to_beats,
    scan_flow_broll_clips,
    resolve_shot_source,
)

logger = logging.getLogger("omnicut.draft_generator")

FPS = 30.0
FRAME_DURATION = 1.0 / FPS
DEFAULT_J_LEAD = 0.18  # 180 ms canonical J-cut audio lead (Rule 4.7)


def frame_quantize(seconds: float) -> float:
    """Quantizes seconds to the 30 FPS grid (1/30s) to prevent cut boundary drift."""
    return round(float(seconds) * FPS) / FPS


def seconds_to_us(seconds: float) -> int:
    """Converts seconds to microseconds (CapCut timerange unit)."""
    return int(round(float(seconds) * 1_000_000))


def us_to_seconds(microseconds: int) -> float:
    """Converts microseconds to seconds."""
    return round(float(microseconds) / 1_000_000.0, 4)


def backup_draft_content(draft_file: Path) -> Optional[Path]:
    """
    Strict Rule 3.3 Compliance:
    Always creates a backup `draft_content.json.bak` before any modification or write.
    """
    draft_file = Path(draft_file)
    if not draft_file.exists():
        return None

    bak_file = draft_file.with_name("draft_content.json.bak")
    try:
        shutil.copy2(draft_file, bak_file)
        logger.info(f"🛡️ [Rule 3.3] Backed up draft to {bak_file}")
        return bak_file
    except Exception as e:
        logger.error(f"Failed to backup draft_content.json: {e}")
        raise IOError(f"Could not backup draft file before writing: {e}")


def calculate_jcut_boundaries(
    beat_cues: List[Dict[str, Any]],
    total_duration: Optional[float] = None,
    nominal_j_lead: float = DEFAULT_J_LEAD,
) -> List[Dict[str, Any]]:
    """
    Computes visual start, end, and duration for each beat according to Rule 4.7 & 4.17.
    
    Principles:
      - Beat 0 (Hook): Visual starts strictly at 0.0s (no negative J-cut).
      - Beat i > 0: Visual cuts in at `cue_start + j_lead` (audio leads visual).
      - Safe margins: For short cues (<0.8s), j_lead is capped at 25% of cue duration (<=100ms).
      - Strict Topic Hold: The visual for beat i stays active continuously until beat i+1 cuts in.
      - Grid: All cut boundaries are quantized to 1/30s frame boundary.
    """
    if not beat_cues:
        return []

    total_beats = len(beat_cues)
    shots_timing: List[Dict[str, Any]] = []

    # Calculate individual raw cue durations
    raw_starts = [float(c.get("start", 0.0)) for c in beat_cues]
    raw_ends = [float(c.get("end", 0.0)) for c in beat_cues]
    cue_durations = [max(0.1, e - s) for s, e in zip(raw_starts, raw_ends)]

    if total_duration is None:
        total_duration = max(raw_ends) if raw_ends else sum(cue_durations)
    total_duration = frame_quantize(total_duration)

    # Compute visual start for each shot
    visual_starts: List[float] = [0.0]  # Beat 0 always starts at 0.0s

    for i in range(1, total_beats):
        prev_dur = cue_durations[i - 1]
        curr_dur = cue_durations[i]
        # Safe margin for short shots (.agents/rules/j_cut_rules.md §3)
        effective_lead = min(nominal_j_lead, prev_dur * 0.25, curr_dur * 0.25, 0.25)
        # Next shot visual begins effective_lead AFTER voice onset
        v_start = frame_quantize(raw_starts[i] + effective_lead)
        # Ensure visual start is strictly after previous visual start
        v_start = max(v_start, visual_starts[-1] + FRAME_DURATION)
        visual_starts.append(v_start)

    # Compute visual end and duration for each shot (Strict Topic Hold)
    for i in range(total_beats):
        v_start = visual_starts[i]
        if i < total_beats - 1:
            v_end = visual_starts[i + 1]
        else:
            v_end = total_duration

        v_end = max(v_end, v_start + FRAME_DURATION)
        v_dur = frame_quantize(v_end - v_start)

        shots_timing.append({
            "beat_index": i,
            "cue_start": raw_starts[i],
            "cue_end": raw_ends[i],
            "visual_start": v_start,
            "visual_end": v_end,
            "visual_duration": v_dur,
            "j_lead": round(v_start - raw_starts[i], 3) if i > 0 else 0.0,
        })

    return shots_timing


def create_base_draft_content(
    width: int = 1080,
    height: int = 1920,
    fps: float = FPS,
    draft_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generates an initial, fully schema-compliant CapCut 7.1 draft_content dict."""
    d_id = draft_id or str(uuid.uuid4()).upper()
    draft = {
        "id": d_id,
        "version": 360000,
        "new_version": "144.0.0",
        "fps": fps,
        "color_space": 0,
        "canvas_config": {
            "background": None,
            "height": height,
            "ratio": f"{width}:{height}" if width != 1080 or height != 1920 else "9:16",
            "width": width,
        },
        "platform": {
            "app_id": 359289,
            "app_source": "cc",
            "app_version": "7.1.0",
            "os": "windows",
        },
        "free_render_index_mode_on": True,
        "render_index_track_mode_on": True,
        "keyframe_graph_list": [],
        "materials": {k: [] for k in CAPCUT_7_1_MATERIAL_KEYS},
        "tracks": [],
        "relationships": [],
    }
    return draft


def get_or_create_track(draft_data: Dict[str, Any], track_type: str, track_name: str = "") -> Dict[str, Any]:
    """Finds or appends a track of given type in draft_data."""
    tracks = draft_data.setdefault("tracks", [])
    for t in tracks:
        if t.get("type") == track_type:
            if not track_name or t.get("name") == track_name or t.get("id") == track_name:
                return t

    new_track = {
        "id": track_name or str(uuid.uuid4()),
        "name": track_name or f"{track_type}_track_{len(tracks) + 1}",
        "type": track_type,
        "segments": [],
        "attribute": 0,
        "flag": 0,
    }
    tracks.append(new_track)
    return new_track


def slot_broll_clips_into_timeline(
    draft_data: Dict[str, Any],
    matched_shots: List[Dict[str, Any]],
    total_duration: Optional[float] = None,
    nominal_j_lead: float = DEFAULT_J_LEAD,
    track_name: str = "video_main",
) -> Dict[str, Any]:
    """
    Auto-slots B-roll / Flow clips into the video track of a CapCut draft.
    Calculates J-cut timing, enforces Strict Topic Hold, and adds material records.
    """
    if not matched_shots:
        return draft_data

    timing_list = calculate_jcut_boundaries(
        matched_shots,
        total_duration=total_duration,
        nominal_j_lead=nominal_j_lead,
    )

    video_track = get_or_create_track(draft_data, "video", track_name=track_name)
    existing_segments = video_track.setdefault("segments", [])

    materials = draft_data.setdefault("materials", {})
    videos_mat = materials.setdefault("videos", [])
    speeds_mat = materials.setdefault("speeds", [])

    for i, shot in enumerate(matched_shots):
        timing = timing_list[i]
        src_path = shot.get("source_path", "")
        if not src_path:
            continue

        v_start_s = timing["visual_start"]
        v_dur_s = timing["visual_duration"]
        v_start_us = seconds_to_us(v_start_s)
        v_dur_us = seconds_to_us(v_dur_s)

        # Create or find video material
        mat_id = str(uuid.uuid4())
        video_mat = {
            "id": mat_id,
            "path": str(Path(src_path).resolve()).replace("\\", "/"),
            "duration": seconds_to_us(max(v_dur_s, float(shot.get("duration", v_dur_s)))),
            "width": 1080,
            "height": 1920,
            "material_name": Path(src_path).name,
            "type": "video",
        }
        videos_mat.append(video_mat)

        # Speed material
        speed_val = float(shot.get("speed", 1.0))
        speed_id = str(uuid.uuid4())
        speeds_mat.append({
            "id": speed_id,
            "mode": 0,
            "speed": speed_val,
            "type": "speed",
        })

        # Video segment
        seg_id = str(uuid.uuid4())
        src_trim_start_us = seconds_to_us(float(shot.get("trim_start", 0.0)))
        src_trim_dur_us = int(round(v_dur_us * speed_val))

        segment = {
            "id": seg_id,
            "material_id": mat_id,
            "source_timerange": {
                "start": src_trim_start_us,
                "duration": src_trim_dur_us,
            },
            "target_timerange": {
                "start": v_start_us,
                "duration": v_dur_us,
            },
            "speed": speed_val,
            "volume": 0.0,  # Muted B-roll (Rule 4.5 / clean audio)
            "clip": {
                "alpha": 1.0,
                "flip": {"horizontal": False, "vertical": False},
                "rotation": 0.0,
                "scale": {
                    "x": float(shot.get("zoom", 1.0)),
                    "y": float(shot.get("zoom", 1.0)),
                },
                "transform": {"x": 0.0, "y": 0.0},
            },
            "extra_material_refs": [speed_id],
        }
        existing_segments.append(segment)

    # Ensure schema 7.1 integrity and relationships
    upgrade_draft_content_to_7_1(draft_data)
    return draft_data


def add_audio_track_to_draft(
    draft_data: Dict[str, Any],
    audio_path: str,
    track_type: str = "voice",
    volume: float = 1.0,
    target_start: float = 0.0,
    duration: Optional[float] = None,
) -> Dict[str, Any]:
    """Adds a clean voice or BGM track to draft_content."""
    p = Path(audio_path)
    if not p.exists():
        logger.warning(f"Audio file does not exist: {audio_path}")
        return draft_data

    materials = draft_data.setdefault("materials", {})
    audios_mat = materials.setdefault("audios", [])
    speeds_mat = materials.setdefault("speeds", [])

    mat_id = str(uuid.uuid4())
    audio_dur_us = seconds_to_us(duration or 30.0)

    audios_mat.append({
        "id": mat_id,
        "path": str(p.resolve()).replace("\\", "/"),
        "duration": audio_dur_us,
        "name": p.name,
        "type": "audio",
    })

    speed_id = str(uuid.uuid4())
    speeds_mat.append({
        "id": speed_id,
        "mode": 0,
        "speed": 1.0,
        "type": "speed",
    })

    track_name = f"audio_{track_type}"
    audio_track = get_or_create_track(draft_data, "audio", track_name=track_name)
    segments = audio_track.setdefault("segments", [])

    seg_id = str(uuid.uuid4())
    segments.append({
        "id": seg_id,
        "material_id": mat_id,
        "source_timerange": {"start": 0, "duration": audio_dur_us},
        "target_timerange": {"start": seconds_to_us(target_start), "duration": audio_dur_us},
        "speed": 1.0,
        "volume": float(volume),
        "extra_material_refs": [speed_id],
    })

    upgrade_draft_content_to_7_1(draft_data)
    return draft_data


def generate_capcut_draft_with_flow(
    product_id: str,
    beat_cues: List[Dict[str, Any]],
    draft_dir: Optional[Path] = None,
    draft_name: Optional[str] = None,
    raw_video: Optional[str] = None,
    voice_audio_path: Optional[str] = None,
    bgm_path: Optional[str] = None,
    total_duration: Optional[float] = None,
    nominal_j_lead: float = DEFAULT_J_LEAD,
) -> Path:
    """
    End-to-end generator:
      1. Resolves Flow B-roll clips for the product (01_Raw/<product_id>/AI_Flow/*.mp4).
      2. Creates or loads draft directory.
      3. Backs up existing draft_content.json to draft_content.json.bak (Rule 3.3).
      4. Auto-slots Flow clips with J-cut timing (Rule 4.7) and Strict Topic Hold (Rule 4.17).
      5. Injects voiceover (vol 1.0) and BGM (vol 0.12, Rule 4.5).
      6. Writes validated CapCut 7.1 draft_content.json.
    """
    if not draft_name:
        draft_name = f"OmniCut_Flow_{product_id}"

    if draft_dir is None:
        draft_dir = PROJECTS_DIR / product_id / "draft"
    draft_dir = Path(draft_dir)
    draft_dir.mkdir(parents=True, exist_ok=True)

    draft_file = draft_dir / "draft_content.json"

    # Rule 3.3: Backup if existing
    if draft_file.exists():
        backup_draft_content(draft_file)
        try:
            draft_data = json.loads(draft_file.read_text(encoding="utf-8"))
        except Exception:
            draft_data = create_base_draft_content()
    else:
        draft_data = create_base_draft_content()

    # 1. Match Flow clips and build shot list
    flow_matches = match_flow_clips_to_beats(product_id, beat_cues)
    shots: List[Dict[str, Any]] = []

    for i, cue in enumerate(beat_cues):
        src_info = resolve_shot_source(
            product_id=product_id,
            beat_index=i,
            beat_cue=cue,
            raw_video=raw_video,
            flow_clips_by_beat=flow_matches,
        )
        shots.append({
            **cue,
            "shot_index": i,
            "beat_index": i,
            "source_path": src_info["source_path"],
            "is_ai_flow": src_info.get("is_ai_flow", False),
            "zoom": 1.0,
            "speed": 1.0,
            "trim_start": 0.0,
        })

    # 2. Slot B-roll into video timeline
    slot_broll_clips_into_timeline(
        draft_data,
        matched_shots=shots,
        total_duration=total_duration,
        nominal_j_lead=nominal_j_lead,
        track_name="video_main",
    )

    # 3. Add Voice Audio (vol=1.0)
    if voice_audio_path and Path(voice_audio_path).exists():
        add_audio_track_to_draft(
            draft_data,
            audio_path=voice_audio_path,
            track_type="voice",
            volume=1.0,
            target_start=0.0,
            duration=total_duration,
        )

    # 4. Add BGM (vol=0.12, Rule 4.5 standard)
    if bgm_path and Path(bgm_path).exists():
        add_audio_track_to_draft(
            draft_data,
            audio_path=bgm_path,
            track_type="bgm",
            volume=0.12,
            target_start=0.0,
            duration=total_duration,
        )

    # Save finalized draft
    draft_file.write_text(
        json.dumps(draft_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info(f"✅ Generated CapCut draft with Flow B-roll at {draft_file}")
    return draft_file


def inject_flow_broll_into_existing_draft(
    draft_file_or_dir: Path,
    product_id: str,
    beat_cues: List[Dict[str, Any]],
    nominal_j_lead: float = DEFAULT_J_LEAD,
) -> Path:
    """
    Safely injects Flow B-roll clips into an existing CapCut draft:
      - Strictly backs up to draft_content.json.bak (Rule 3.3).
      - Replaces video track segments with Flow clips for matching beats.
    """
    path = Path(draft_file_or_dir)
    if path.is_dir():
        draft_file = path / "draft_content.json"
    else:
        draft_file = path

    if not draft_file.exists():
        raise FileNotFoundError(f"Draft file not found: {draft_file}")

    # Mandatory backup (Rule 3.3)
    backup_draft_content(draft_file)

    draft_data = json.loads(draft_file.read_text(encoding="utf-8"))

    # Resolve matches
    flow_matches = match_flow_clips_to_beats(product_id, beat_cues)
    shots: List[Dict[str, Any]] = []
    for i, cue in enumerate(beat_cues):
        src_info = resolve_shot_source(
            product_id=product_id,
            beat_index=i,
            beat_cue=cue,
            flow_clips_by_beat=flow_matches,
        )
        shots.append({
            **cue,
            "shot_index": i,
            "beat_index": i,
            "source_path": src_info["source_path"],
            "is_ai_flow": src_info.get("is_ai_flow", False),
            "zoom": 1.0,
            "speed": 1.0,
            "trim_start": 0.0,
        })

    # Clear old main video segments or update
    for track in draft_data.get("tracks", []):
        if track.get("type") == "video":
            track["segments"] = []

    slot_broll_clips_into_timeline(
        draft_data,
        matched_shots=shots,
        nominal_j_lead=nominal_j_lead,
        track_name="video_main",
    )

    draft_file.write_text(
        json.dumps(draft_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return draft_file
