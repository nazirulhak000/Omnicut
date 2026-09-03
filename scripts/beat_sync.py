"""
Beat-time detection for BGM tracks.

Used by scripts/pipeline.py to snap auto-generated video cut boundaries onto
the music instead of leaving them purely caption-timed. Optional dependency:
falls back to an empty beat list (== no snapping, cuts stay exactly where
caption timing put them) whenever librosa isn't installed or detection fails
for any reason, so a missing package or a bad audio file never breaks a
render -- same graceful-degrade pattern as GeminiVisionMatcher.
"""
import json
from pathlib import Path
from typing import List, Optional, Tuple

from scripts.config import MUSIC_DIR

BEAT_CACHE_FILE = MUSIC_DIR / ".beat_cache.json"


class BeatSync:
    """Detects and caches beat onset timestamps for a BGM file."""

    @classmethod
    def _load_cache(cls) -> dict:
        if BEAT_CACHE_FILE.exists():
            try:
                return json.loads(BEAT_CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    @classmethod
    def _save_cache(cls, cache: dict) -> None:
        try:
            BEAT_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            BEAT_CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
        except Exception:
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
        if cached is not None:
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
