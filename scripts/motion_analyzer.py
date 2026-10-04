"""
Motion-energy detection for raw footage.

Used by scripts/pipeline.py to bias cut boundaries, punch-zoom intensity, and
the no-AI-Vision shot offset toward moments with real on-screen motion,
instead of guessing purely from audio/caption timing. Optional dependency:
falls back to an empty score list (== no motion bias, everything else in
pipeline.py keeps working exactly as before) whenever opencv isn't installed
or analysis fails for any reason -- same graceful-degrade pattern as
GeminiVisionMatcher and BeatSync.
"""
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from scripts.config import ASSETS_DIR

MOTION_CACHE_FILE = ASSETS_DIR / ".motion_cache.json"
SAMPLE_INTERVAL_SECONDS = 0.25
ANALYSIS_WIDTH = 160
ANALYSIS_HEIGHT = 284
SMOOTH_WINDOW = 3
MAX_FRAMES_SAFETY = 30 * 60 * 60  # ~1h at 30fps -- a raw TikTok source never gets close


def _valid_motion_entry(value) -> bool:
    if not isinstance(value, dict):
        return False
    times, scores = value.get("times"), value.get("scores")
    if not isinstance(times, list) or not isinstance(scores, list) or len(times) != len(scores):
        return False
    return all(
        isinstance(item, (int, float)) and not isinstance(item, bool)
        and math.isfinite(item) and item >= 0
        for item in times
    ) and all(
        isinstance(item, (int, float)) and not isinstance(item, bool)
        and math.isfinite(item) and 0 <= item <= 1
        for item in scores
    )


class MotionAnalyzer:
    """Frame-difference motion score over time for one raw video file."""

    @staticmethod
    def _compute_file_hash(filepath: Path) -> str:
        """Same quick-hash shape as GeminiVisionMatcher._compute_file_hash --
        md5 of size + first 8MB, cheap enough to run before deciding whether
        a cached score list already covers this file."""
        hasher = hashlib.md5()
        hasher.update(str(filepath.stat().st_size).encode("utf-8"))
        with open(filepath, "rb") as f:
            hasher.update(f.read(8 * 1024 * 1024))
        return hasher.hexdigest()

    @classmethod
    def _load_cache(cls) -> Dict[str, dict]:
        if MOTION_CACHE_FILE.exists():
            try:
                cache = json.loads(MOTION_CACHE_FILE.read_text(encoding="utf-8"))
                return cache if isinstance(cache, dict) else {}
            except Exception:
                return {}
        return {}

    @classmethod
    def _save_cache(cls, cache: Dict[str, dict]) -> None:
        tmp_path = None
        try:
            MOTION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(cache, ensure_ascii=False, indent=2)
            fd, tmp_path = tempfile.mkstemp(
                prefix=MOTION_CACHE_FILE.name + ".", suffix=".tmp", dir=str(MOTION_CACHE_FILE.parent)
            )
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(tmp_path, MOTION_CACHE_FILE)
            tmp_path = None
        except Exception:
            pass
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    @classmethod
    def get_motion_scores(cls, raw_video_path: Optional[Path]) -> Tuple[List[float], List[float]]:
        """
        (times, scores) for `raw_video_path` -- scores normalized 0..1
        against this clip's own peak, one sample every SAMPLE_INTERVAL_SECONDS,
        cached by file hash so the same raw footage is only ever analyzed
        once. Returns ([], []) (never raises) when the file is missing,
        opencv isn't installed, or analysis fails for any reason -- callers
        must treat that as "no motion data", not as an error.
        """
        if not raw_video_path:
            return [], []
        path = Path(raw_video_path)
        if not path.exists():
            return [], []

        try:
            key = cls._compute_file_hash(path)
        except Exception:
            return [], []

        cache = cls._load_cache()
        cached = cache.get(key)
        if _valid_motion_entry(cached):
            return cached.get("times", []), cached.get("scores", [])

        try:
            import cv2

            cap = cv2.VideoCapture(str(path))
            if not cap.isOpened():
                return [], []
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            frame_interval = max(1, round(fps * SAMPLE_INTERVAL_SECONDS))

            times: List[float] = []
            raw_scores: List[float] = []
            prev_gray = None
            frame_idx = 0
            # Sequential read + skip, not cv2.CAP_PROP_POS_MSEC seeking: most
            # containers only decode cleanly from a keyframe forward, so
            # random-access seeking is far slower here than decoding every
            # frame and just not processing the ones we don't sample.
            while frame_idx < MAX_FRAMES_SAFETY:
                ok, frame = cap.read()
                if not ok:
                    break
                if frame_idx % frame_interval == 0:
                    small = cv2.resize(frame, (ANALYSIS_WIDTH, ANALYSIS_HEIGHT))
                    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                    if prev_gray is not None:
                        diff = cv2.absdiff(prev_gray, gray)
                        raw_scores.append(float(diff.mean()))
                        times.append(round(frame_idx / fps, 3))
                    prev_gray = gray
                frame_idx += 1
            cap.release()

            if not raw_scores:
                return [], []

            peak = max(raw_scores) or 1.0
            norm = [s / peak for s in raw_scores]

            # Short moving average damps single-frame noise (camera shake,
            # compression artifacts) without erasing real motion peaks.
            smoothed = []
            for i in range(len(norm)):
                lo = max(0, i - SMOOTH_WINDOW // 2)
                hi = min(len(norm), i + SMOOTH_WINDOW // 2 + 1)
                smoothed.append(sum(norm[lo:hi]) / (hi - lo))

        except Exception as e:
            print(f"   ⚠️ Motion analysis skipped for {path.name} ({e}) — cut/zoom stay audio-timed.")
            return [], []

        cache[key] = {"times": times, "scores": smoothed}
        cls._save_cache(cache)
        return times, smoothed

    @staticmethod
    def segment_mean_score(times: List[float], scores: List[float], t0: float, t1: float) -> Optional[float]:
        """Average motion score between t0 and t1, or the single nearest
        sample if the window is narrower than one analysis step. None if
        there's no data."""
        if not times:
            return None
        values = [s for t, s in zip(times, scores) if t0 <= t < t1]
        if values:
            return sum(values) / len(values)
        mid = (t0 + t1) / 2
        nearest_idx = min(range(len(times)), key=lambda i: abs(times[i] - mid))
        return scores[nearest_idx]

    @staticmethod
    def nearest_trough(times: List[float], scores: List[float], target: float, tolerance: float) -> Optional[float]:
        """
        Time of the lowest-motion sample within `tolerance` seconds of
        `target`, or None if there's no data in range. Used to nudge a cut
        boundary off a moving frame onto a comparatively still one -- a real
        editor doesn't cut mid-action.
        """
        if not times:
            return None
        candidates = [(t, s) for t, s in zip(times, scores) if abs(t - target) <= tolerance]
        if not candidates:
            return None
        return min(candidates, key=lambda ts: ts[1])[0]


if __name__ == "__main__":
    print("MotionAnalyzer ready.")
