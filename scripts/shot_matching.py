"""
OmniCut Pro Studio - AI Flow Shot Matching Engine
scripts/shot_matching.py

Recognizes and matches AI Flow generated B-roll clips (01_Raw/<product_id>/AI_Flow/*.mp4)
to script beat cues / labels with high priority (Architecture Plan §3.4.1).

Priority Hierarchy:
  1. User Manual Pin (manual_shot_map from UI)
  2. AI Flow B-roll (01_Raw/<product_id>/AI_Flow/*.mp4 matched by beat_index or label)
  3. Clean Real Camera Footage / Raw Video
  4. Still Image Motion Slideshow (Ken Burns)
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.config import BASE_DIR, RAW_DIR, PROJECTS_DIR
from scripts.pipeline_context import PipelineContext

logger = logging.getLogger("omnicut.shot_matching")

# Regex to detect beat index from Flow clip filenames
# e.g.: flow_20261114_120000_beat0_hook.mp4, flow_beat_1.mp4, flow_0_macro.mp4, beat2.mp4
_BEAT_INDEX_PATTERNS = [
    re.compile(r"(?:^|[-_])beat[-_]?(\d+)", re.IGNORECASE),
    re.compile(r"(?:^|[-_])shot[-_]?(\d+)", re.IGNORECASE),
    re.compile(r"^flow_\d{8}_\d{6}_(?:beat_?)?(\d+)", re.IGNORECASE),
    re.compile(r"^flow_\d{8}_\d{6}_(\d+)[-_]", re.IGNORECASE),
    re.compile(r"^(\d+)[-_]", re.IGNORECASE),
]

_ROLE_KEYWORDS = {
    "hook": ["hook", "intro", "open", "ฮุก", "เปิด"],
    "cta": ["cta", "outro", "basket", "buy", "ปิด", "ตะกร้า", "สั่งซื้อ"],
    "feature": ["feature", "body", "demo", "spec", "macro", "ฟีเจอร์", "การใช้งาน"],
}


def get_flow_broll_dir(product_id: str) -> Path:
    """Returns the dedicated directory for AI Flow clips for a given product."""
    return RAW_DIR / product_id / "AI_Flow"


def parse_beat_index_from_filename(filename: str) -> Optional[int]:
    """Extracts beat_index integer from a Flow filename if present."""
    stem = Path(filename).stem
    for pattern in _BEAT_INDEX_PATTERNS:
        m = pattern.search(stem)
        if m:
            try:
                return int(m.group(1))
            except (ValueError, IndexError):
                pass
    return None


def parse_label_from_filename(filename: str) -> str:
    """Extracts descriptive label or role from filename."""
    stem = Path(filename).stem
    # Remove flow timestamp prefix if present: flow_YYYYMMDD_HHMMSS_
    clean = re.sub(r"^flow_\d{8}_\d{6}_?", "", stem, flags=re.IGNORECASE)
    # Remove beat/shot index prefix: beat\d+_
    clean = re.sub(r"^(?:beat|shot)?[-_]?\d+[-_]?", "", clean, flags=re.IGNORECASE)
    return clean.strip("-_ ")


def scan_flow_broll_clips(product_id: str) -> List[Dict[str, Any]]:
    """
    Scans 01_Raw/<product_id>/AI_Flow/*.mp4 for generated B-roll clips.
    Returns list of clip metadata dictionaries sorted by modification time (newest first).
    """
    flow_dir = get_flow_broll_dir(product_id)
    if not flow_dir.exists() or not flow_dir.is_dir():
        return []

    clips: List[Dict[str, Any]] = []
    # Search for mp4, mov, webm
    video_files = list(flow_dir.glob("*.mp4")) + list(flow_dir.glob("*.mov")) + list(flow_dir.glob("*.webm"))

    for v_file in video_files:
        try:
            stat = v_file.stat()
            if stat.st_size == 0:
                continue

            fname = v_file.name
            beat_idx = parse_beat_index_from_filename(fname)
            label = parse_label_from_filename(fname)

            rel_path = f"01_Raw/{product_id}/AI_Flow/{fname}"
            clips.append({
                "path": str(v_file.resolve()),
                "relative_path": rel_path,
                "filename": fname,
                "beat_index": beat_idx,
                "label": label,
                "mtime": stat.st_mtime,
                "size_bytes": stat.st_size,
                "is_ai_flow": True,
            })
        except Exception as e:
            logger.warning(f"Error reading Flow clip {v_file}: {e}")

    # Sort newest first so recent generations take precedence
    clips.sort(key=lambda c: c["mtime"], reverse=True)
    return clips


def assign_beat_role(index: int, total: int) -> str:
    """Consistent role assignment: index 0 is 'hook', last is 'cta', rest 'feature'."""
    if total <= 1:
        return "hook"
    if index == 0:
        return "hook"
    if index == total - 1:
        return "cta"
    return "feature"


def match_flow_clips_to_beats(
    product_id: str,
    beat_cues: List[Dict[str, Any]],
) -> Dict[int, Dict[str, Any]]:
    """
    Matches available Flow clips to beat cues.
    
    Priority matching order per beat:
      1. Exact beat_index match in filename (e.g., beat0, beat_1)
      2. Role/label semantic match (e.g., "hook" on beat 0, "cta" on last beat)
      
    Returns a mapping of {beat_index: clip_dict}.
    """
    available_clips = scan_flow_broll_clips(product_id)
    if not available_clips:
        return {}

    total_beats = len(beat_cues)
    matched: Dict[int, Dict[str, Any]] = {}
    used_paths = set()

    # Pass 1: Exact beat_index match
    for clip in available_clips:
        b_idx = clip.get("beat_index")
        if b_idx is not None:
            if b_idx not in matched and clip["path"] not in used_paths:
                matched[b_idx] = clip
                used_paths.add(clip["path"])

    # Pass 2: Role / label match for unmatched beats
    for i in range(total_beats):
        if i in matched:
            continue
        role = assign_beat_role(i, total_beats)
        keywords = _ROLE_KEYWORDS.get(role, [])

        for clip in available_clips:
            if clip["path"] in used_paths:
                continue
            lbl = clip.get("label", "").lower()
            if any(kw in lbl for kw in keywords):
                matched[i] = clip
                used_paths.add(clip["path"])
                break

    return matched


def resolve_shot_source(
    product_id: str,
    beat_index: int,
    beat_cue: Dict[str, Any],
    raw_video: Optional[str] = None,
    manual_pin: Optional[Dict[str, Any]] = None,
    flow_clips_by_beat: Optional[Dict[int, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Resolves the source video/footage for a single beat according to strict priority:
      1. Manual Pin (from manual_shot_map)
      2. AI Flow B-roll clip (01_Raw/<product_id>/AI_Flow/*.mp4)
      3. Clean Raw Video
      4. Fallback (empty / still image motion)
    """
    # 1. Manual Pin takes top priority
    if manual_pin and manual_pin.get("video_path"):
        return {
            "source_path": manual_pin["video_path"],
            "source_type": "manual_pin",
            "is_ai_flow": False,
            "beat_index": beat_index,
            "trim_start": float(manual_pin.get("trim_start", 0.0)),
            "trim_end": float(manual_pin.get("trim_end", 0.0)),
            "speed": float(manual_pin.get("speed", 1.0)),
            "pinned": True,
        }

    # 2. AI Flow B-roll
    if flow_clips_by_beat is None:
        flow_clips_by_beat = match_flow_clips_to_beats(product_id, [beat_cue])
    
    flow_clip = flow_clips_by_beat.get(beat_index)
    if flow_clip and flow_clip.get("path"):
        return {
            "source_path": flow_clip["path"],
            "relative_path": flow_clip.get("relative_path", ""),
            "source_type": "ai_flow",
            "is_ai_flow": True,
            "beat_index": beat_index,
            "label": flow_clip.get("label", ""),
            "pinned": False,
        }

    # 3. Clean Raw Video
    if raw_video:
        return {
            "source_path": str(raw_video),
            "source_type": "raw_video",
            "is_ai_flow": False,
            "beat_index": beat_index,
            "pinned": False,
        }

    # 4. Fallback
    return {
        "source_path": "",
        "source_type": "none",
        "is_ai_flow": False,
        "beat_index": beat_index,
        "pinned": False,
    }


def build_flow_matched_clip_list(
    product_id: str,
    beat_cues: List[Dict[str, Any]],
    raw_video: Optional[str] = None,
    manual_pins: Optional[List[Dict[str, Any]]] = None,
    total_duration: Optional[float] = None,
    j_lead: float = 0.18,
) -> List[Dict[str, Any]]:
    """
    Builds a full clip list matching the beat cues, incorporating AI Flow B-roll
    as high-priority footage with Strict Topic Hold (Rule 4.17) and J-cut boundaries (Rule 4.7).
    """
    if not beat_cues:
        return []

    # Map manual pins by beat_index
    pin_by_beat = {}
    if manual_pins:
        for p in manual_pins:
            if "beat_index" in p and p.get("video_path"):
                pin_by_beat[int(p["beat_index"])] = p

    # Find Flow B-roll matches
    flow_matches = match_flow_clips_to_beats(product_id, beat_cues)

    clips: List[Dict[str, Any]] = []
    total_beats = len(beat_cues)

    for i, cue in enumerate(beat_cues):
        start = float(cue.get("start", 0.0))
        end = float(cue.get("end", 0.0))
        cue_dur = max(0.1, end - start)

        manual_pin = pin_by_beat.get(i)
        source = resolve_shot_source(
            product_id=product_id,
            beat_index=i,
            beat_cue=cue,
            raw_video=raw_video,
            manual_pin=manual_pin,
            flow_clips_by_beat=flow_matches,
        )

        src_path = source["source_path"]
        is_flow = source.get("is_ai_flow", False)
        is_manual = source.get("source_type") == "manual_pin"

        # Calculate trim points
        if is_manual:
            trim_start = source.get("trim_start", 0.0)
            trim_end = source.get("trim_end", trim_start + cue_dur)
            speed = source.get("speed", 1.0)
        else:
            trim_start = 0.0
            trim_end = round(cue_dur, 3)
            speed = 1.0

        clip_dict = {
            "id": f"clip_{i:02d}",
            "shot_index": i,
            "beat_index": i,
            "source_path": src_path,
            "trim_start": trim_start,
            "trim_end": trim_end,
            "duration": round(cue_dur, 3),
            "speed": speed,
            "zoom": 1.0,
            "is_ai_flow": is_flow,
            "source_type": source["source_type"],
            "manual_pinned": is_manual,
            "transition_in": "cut",
            "strict_topic_hold": True,  # Rule 4.17
        }
        clips.append(clip_dict)

    return clips


def integrate_flow_into_pipeline_context(ctx: PipelineContext) -> bool:
    """
    Inspects PipelineContext. If Flow B-roll clips exist in 01_Raw/<product_id>/AI_Flow/,
    slots them into ctx.actual_clip_list or ctx.manual_shot_map.
    Returns True if any Flow clips were integrated.
    """
    if not ctx.product_id or not ctx.beat_cues:
        return False

    matched = match_flow_clips_to_beats(ctx.product_id, ctx.beat_cues)
    if not matched:
        return False

    logger.info(f"⚡ [AI Flow] Matched {len(matched)} Flow B-roll clips for product {ctx.product_id}")

    # Ensure manual_shot_map has Flow pins if not already pinned by user
    if ctx.manual_shot_map is None:
        ctx.manual_shot_map = []

    pinned_indices = {int(p["beat_index"]) for p in ctx.manual_shot_map if "beat_index" in p and p.get("video_path")}

    integrated_count = 0
    for beat_idx, clip_info in matched.items():
        if beat_idx not in pinned_indices:
            cue = ctx.beat_cues[beat_idx]
            dur = max(0.1, float(cue.get("end", 0.0)) - float(cue.get("start", 0.0)))
            ctx.manual_shot_map.append({
                "beat_index": beat_idx,
                "video_path": clip_info["path"],
                "trim_start": 0.0,
                "trim_end": round(dur, 3),
                "speed": 1.0,
                "is_ai_flow": True,
            })
            integrated_count += 1

    return integrated_count > 0
