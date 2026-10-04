"""
Beat-time detection for BGM tracks.

Used by scripts/pipeline.py to snap auto-generated video cut boundaries onto
the music instead of leaving them purely caption-timed, and by
scripts/api_audio_beats.py to hand the same grid to the editor timeline so a
hand-placed cut can snap to the same beats the pipeline uses. Optional
dependency:
falls back to an empty beat list (== no snapping, cuts stay exactly where
caption timing put them) whenever librosa isn't installed or detection fails
for any reason, so a missing package or a bad audio file never breaks a
render -- same graceful-degrade pattern as GeminiVisionMatcher.
"""
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from scripts.config import MUSIC_DIR

BEAT_CACHE_FILE = MUSIC_DIR / ".beat_cache.json"

# Beats per bar used to split detected beats into "major" (bar downbeats --
# strong scene-change points) and "minor" (everything in between). 4 assumes
# common time, which every track in 02_Assets/Music is; a track in 3/4 would
# mark the wrong beats as downbeats, which is a mis-labeled snap target, not
# a crash.
BEATS_PER_BAR = 4

# Cached grids live under a version prefix so an older cache written before
# the bpm/major/minor split cannot be read back as the new shape.
BEAT_GRID_CACHE_VERSION = "v2"


def _valid_beat_times(value) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, (int, float)) and not isinstance(item, bool)
        and math.isfinite(item) and item >= 0
        for item in value
    )


class BeatSync:
    """Detects and caches beat onset timestamps for a BGM file."""

    @classmethod
    def _load_cache(cls) -> dict:
        if BEAT_CACHE_FILE.exists():
            try:
                cache = json.loads(BEAT_CACHE_FILE.read_text(encoding="utf-8"))
                return cache if isinstance(cache, dict) else {}
            except Exception:
                return {}
        return {}

    @classmethod
    def _save_cache(cls, cache: dict) -> None:
        tmp_path = None
        try:
            BEAT_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(cache, ensure_ascii=False, indent=2)
            fd, tmp_path = tempfile.mkstemp(
                prefix=BEAT_CACHE_FILE.name + ".", suffix=".tmp", dir=str(BEAT_CACHE_FILE.parent)
            )
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(tmp_path, BEAT_CACHE_FILE)
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
    def get_beat_times(cls, bgm_path: Optional[Path]) -> List[float]:
        """
        Beat onset timestamps (seconds) for `bgm_path`, cached by filename +
        size so the same BGM track is only ever analyzed once. Returns []
        (never raises) when the file is missing, librosa isn't installed, or
        detection fails -- callers must treat that as "no beat data", not
        as an error.
        """
        if not bgm_path:
            return []
        path = Path(bgm_path)
        if not path.exists():
            return []

        key = f"{path.name}:{path.stat().st_size}"
        cache = cls._load_cache()
        cached = cache.get(key)
        if _valid_beat_times(cached):
            return cached

        try:
            import librosa
            y, sr = librosa.load(str(path), sr=None, mono=True)
            _, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = [round(float(t), 3) for t in librosa.frames_to_time(beat_frames, sr=sr)]
        except Exception as e:
            print(f"   ⚠️ Beat-sync skipped for {path.name} ({e}) — cuts stay caption-timed.")
            return []

        cache[key] = beat_times
        cls._save_cache(cache)
        return beat_times

    @classmethod
    def get_beat_grid(cls, bgm_path: Optional[Path]) -> Dict[str, object]:
        """
        Beat grid for `bgm_path`: ``{"bpm", "major_beats", "minor_beats"}``.

        Built on top of `get_beat_times`, which stays the single place that
        talks to librosa and owns the graceful-degrade contract -- so a
        missing file, a missing librosa or a failed detection returns
        ``{"bpm": None, "major_beats": [], "minor_beats": []}`` here, exactly
        as callers of `get_beat_times` see ``[]``.

        The split is positional: every `BEATS_PER_BAR`-th detected beat is a
        bar downbeat (major), the rest are subdivisions (minor). librosa's
        beat tracker does not label downbeats, so this is an assumption about
        the music, not a measurement of it -- it places the strong markers on
        a regular grid rather than claiming to have found the kick drum.

        Cached separately from the raw beat list (see
        `BEAT_GRID_CACHE_VERSION`) so repeated UI requests for the same track
        do not re-derive the grid, and so an older v1 cache entry can never
        be misread as this shape.
        """
        empty: Dict[str, object] = {"bpm": None, "major_beats": [], "minor_beats": []}
        if not bgm_path:
            return empty
        path = Path(bgm_path)
        if not path.exists():
            return empty

        try:
            cache_key = f"{BEAT_GRID_CACHE_VERSION}:{path.name}:{path.stat().st_size}"
        except OSError:
            return empty

        cache = cls._load_cache()
        cached = cache.get(cache_key)
        if (
            isinstance(cached, dict)
            and _valid_beat_times(cached.get("major_beats"))
            and _valid_beat_times(cached.get("minor_beats"))
            and (
                cached.get("bpm") is None
                or (
                    isinstance(cached.get("bpm"), (int, float))
                    and not isinstance(cached.get("bpm"), bool)
                    and math.isfinite(cached["bpm"]) and cached["bpm"] > 0
                )
            )
        ):
            return {
                "bpm": cached.get("bpm"),
                "major_beats": list(cached.get("major_beats") or []),
                "minor_beats": list(cached.get("minor_beats") or []),
            }

        beats = cls.get_beat_times(path)
        if not beats:
            # No beat data at all -- do not cache, so that a track which
            # failed only because librosa was absent is re-analyzed once it
            # is installed.
            return empty

        grid = {
            "bpm": cls._estimate_bpm(beats),
            "major_beats": [b for i, b in enumerate(beats) if i % BEATS_PER_BAR == 0],
            "minor_beats": [b for i, b in enumerate(beats) if i % BEATS_PER_BAR != 0],
        }

        cache = cls._load_cache()
        cache[cache_key] = grid
        cls._save_cache(cache)
        return grid

    @staticmethod
    def _estimate_bpm(beats: List[float]) -> Optional[float]:
        """
        Tempo from the median gap between consecutive beats, or None when
        there are fewer than two beats to measure a gap from.

        Median rather than mean: a single dropped or doubled beat shifts a
        mean tempo noticeably, while the median ignores it. A non-positive
        or non-finite gap yields None instead of an infinite BPM.
        """
        if len(beats) < 2:
            return None
        gaps = sorted(b2 - b1 for b1, b2 in zip(beats, beats[1:]))
        mid = len(gaps) // 2
        median = gaps[mid] if len(gaps) % 2 else (gaps[mid - 1] + gaps[mid]) / 2
        if not median or median <= 0:
            return None
        bpm = 60.0 / median
        if bpm != bpm or bpm in (float("inf"), float("-inf")):
            return None
        return round(bpm, 1)

    @classmethod
    def get_rms_energy(cls, audio_path: Optional[Path]) -> Tuple[List[float], List[float]]:
        """
        (times, rms) arrays for `audio_path` -- the loudness envelope of the
        already-mixed voice+SFX+BGM track, used by pipeline.py to pick which
        shot is the "hit" of its group by how loud that moment actually is,
        instead of guessing from caption text alone. Not cached: the mixed
        track is regenerated on most rerolls anyway, and RMS analysis is
        cheap next to beat tracking. Returns ([], []) (never raises) when the
        file is missing or librosa isn't installed.
        """
        if not audio_path:
            return [], []
        path = Path(audio_path)
        if not path.exists():
            return [], []

        try:
            import librosa
            y, sr = librosa.load(str(path), sr=None, mono=True)
            hop_length = 512
            rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
            times = librosa.frames_to_time(range(len(rms)), sr=sr, hop_length=hop_length)
            return [round(float(t), 3) for t in times], [float(r) for r in rms]
        except Exception as e:
            print(f"   ⚠️ Energy analysis skipped for {path.name} ({e}) — zoom emphasis stays text-based.")
            return [], []

    @staticmethod
    def segment_mean_energy(times: List[float], rms: List[float], t0: float, t1: float) -> Optional[float]:
        """Average RMS between t0 and t1, or the single nearest sample if the
        window is narrower than one analysis frame. None if there's no data."""
        if not times:
            return None
        values = [r for t, r in zip(times, rms) if t0 <= t < t1]
        if values:
            return sum(values) / len(values)
        mid = (t0 + t1) / 2
        nearest_idx = min(range(len(times)), key=lambda i: abs(times[i] - mid))
        return rms[nearest_idx]


if __name__ == "__main__":
    print("BeatSync ready.")
