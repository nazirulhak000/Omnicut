"""API Router for the editor's audio analysis: beat grids and dead air.

Two read-only endpoints, both feeding timeline decisions:

- `/api/audio/beats` hands the frontend the *same* beat grid scripts/pipeline.py
  already snaps auto-generated cuts to, so a hand-placed cut and a generated
  one agree about where the music is.
- `/api/audio/silences` reports dead-air spans for the Cut Silences action.
  It only reports; the timeline previews the proposed cuts and the user
  confirms, because a ripple delete moves every clip after it.

Both degrade rather than fail where the analysis is merely unavailable: a
track with no detectable beats means "no snap targets", not an error.
"""
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from scripts.api_videos import _allowed_media_path
from scripts.beat_sync import BeatSync
from scripts.config import BASE_DIR, CAPCUT_DRAFT_DIR, MUSIC_DIR
from scripts.silence_detect import (
    DEFAULT_MIN_SILENCE_S,
    DEFAULT_NOISE_DB,
    DEFAULT_PADDING_S,
    SilenceDetectError,
    build_keep_ranges,
    detect_silences,
)

router = APIRouter(prefix="/api/audio", tags=["audio-beats"])

# Only these are analyzed. A name pointing at anything else is a bad request,
# not a 500 from librosa trying to decode a .json.
AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"}


def _resolve_bgm(bgm_name: str) -> Path:
    """
    Resolve `bgm_name` to a real audio file inside MUSIC_DIR.

    The name arrives from a query string, so it is treated as hostile:
    anything with a path separator, a parent reference, or a resolved location
    outside MUSIC_DIR is rejected before it reaches the filesystem. Matching
    the posture of `_allowed_media_path` in api_videos.py, containment is
    checked *after* resolve() as well, so a symlink inside MUSIC_DIR pointing
    out of the tree cannot be used to read an arbitrary file.

    A bare stem ("tiktok_upbeat_bgm") is accepted and matched against the
    known audio suffixes, since that is how the plan's endpoint is specified.
    """
    name = urllib.parse.unquote(bgm_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="ต้องระบุชื่อไฟล์เพลง (bgm_name)")

    # Reject traversal and any attempt to address a nested or absolute path.
    if "/" in name or "\\" in name or name.startswith(".") or Path(name).is_absolute():
        raise HTTPException(status_code=400, detail="ชื่อไฟล์เพลงไม่ถูกต้อง")
    if Path(name).name != name:
        raise HTTPException(status_code=400, detail="ชื่อไฟล์เพลงไม่ถูกต้อง")

    base = MUSIC_DIR.resolve()
    suffix = Path(name).suffix.lower()
    if suffix:
        if suffix not in AUDIO_SUFFIXES:
            raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์เสียงเท่านั้น")
        candidates = [base / name]
    else:
        candidates = [base / f"{name}{ext}" for ext in sorted(AUDIO_SUFFIXES)]

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except (OSError, RuntimeError, ValueError):
            continue
        # Containment re-checked after resolve: a symlink out of MUSIC_DIR
        # must not become a readable path.
        if resolved != base and base not in resolved.parents:
            continue
        if resolved.is_file():
            return resolved

    raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์เพลง: {name}")


@router.get("/beats")
def get_bgm_beats(bgm_name: str) -> Dict[str, Any]:
    """
    Beat grid for one BGM track in 02_Assets/Music.

    Returns `{bpm, major_beats, minor_beats, available}`. `available` is False
    when detection produced nothing (librosa missing, silent track, decode
    failure) so the timeline can tell "this track has no beats" apart from
    "the request failed" without inspecting empty arrays.
    """
    path = _resolve_bgm(bgm_name)

    grid = BeatSync.get_beat_grid(path)
    major: List[float] = list(grid.get("major_beats") or [])
    minor: List[float] = list(grid.get("minor_beats") or [])

    return {
        "status": "ok",
        "bgm_name": path.name,
        "bpm": grid.get("bpm"),
        "major_beats": major,
        "minor_beats": minor,
        "available": bool(major or minor),
    }


def _resolve_media(media_path: str) -> Path:
    """
    Resolve a caller-supplied media path for analysis.

    Reuses `_allowed_media_path` from api_videos.py rather than inventing a
    second containment rule: silence detection must be able to read exactly
    what the media endpoint is already willing to serve, and no more. As
    there, containment is checked both before and after resolve() so a
    symlink cannot widen the set.
    """
    decoded = urllib.parse.unquote(media_path or "").strip()
    if not decoded:
        raise HTTPException(status_code=400, detail="ต้องระบุไฟล์สื่อ (media_path)")

    base = BASE_DIR.resolve()
    drafts = CAPCUT_DRAFT_DIR.resolve()
    target = Path(decoded)
    if not target.is_absolute():
        target = base / decoded

    if not _allowed_media_path(target, base, drafts):
        raise HTTPException(status_code=403, detail="ไม่อนุญาตให้เข้าถึงไฟล์นี้")
    try:
        target = target.resolve()
    except (OSError, RuntimeError, ValueError):
        raise HTTPException(status_code=403, detail="ไม่อนุญาตให้เข้าถึงไฟล์นี้") from None
    if not _allowed_media_path(target, base, drafts):
        raise HTTPException(status_code=403, detail="ไม่อนุญาตให้เข้าถึงไฟล์นี้")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์สื่อ")
    return target


@router.get("/silences")
def get_media_silences(
    media_path: str,
    noise_db: float = DEFAULT_NOISE_DB,
    min_silence_s: float = DEFAULT_MIN_SILENCE_S,
    padding_s: float = DEFAULT_PADDING_S,
) -> Dict[str, Any]:
    """
    Dead-air spans in one media file, plus the ranges a ripple delete would
    keep.

    Read-only by design: nothing is cut here. `keep_ranges` lets the timeline
    show the resulting cut before the user commits, and `fully_silent` flags
    the case the caller must refuse outright -- cutting every span would leave
    an empty timeline.
    """
    if min_silence_s <= 0:
        raise HTTPException(status_code=400, detail="min_silence_s ต้องมากกว่า 0")
    if padding_s < 0:
        raise HTTPException(status_code=400, detail="padding_s ต้องไม่ติดลบ")

    target = _resolve_media(media_path)

    try:
        analysis = detect_silences(
            target,
            noise_db=noise_db,
            min_silence_s=min_silence_s,
            padding_s=padding_s,
        )
    except SilenceDetectError as exc:
        # The user asked for an edit; a failed analysis must say so rather
        # than come back as "no dead air found".
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    keep_ranges = build_keep_ranges(analysis["duration"], analysis["silences"])
    return {
        "status": "ok",
        "media_name": target.name,
        **analysis,
        "keep_ranges": keep_ranges,
        "fully_silent": bool(analysis["silences"]) and not keep_ranges,
    }
