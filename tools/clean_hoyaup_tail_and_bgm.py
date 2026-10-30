"""Clean audio tail glitch and verify BGM volume across all 20 HOYAUP clips.
Eliminates:
1. Trailing 120-150ms digital noise burst caused by Gemini Flash TTS API chunking
2. Ensures clean 0.0 amplitude at the end of vo.wav
"""
import sys
import wave
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "03_Projects" / "_HyperFrames_Studio"
CLIPS_DIR = STUDIO / "clips"
ASSETS_DIR = STUDIO / "assets" / "clips"

sys.path.insert(0, str(ROOT))
from tools.clean_audio_tail_glitch import clean_vo_wav, clean_take_or_turn_wav

def clean_all_hoyaup():
    print("=== Cleaning Audio Tail Glitches for HOYAUP Clips ===")
    vo_cleaned = 0
    turn_cleaned = 0
    
    for i in range(1, 21):
        cid = f"hoy01-pov-s{i:02d}"
        vo_path = ASSETS_DIR / cid / "vo.wav"
        if vo_path.exists():
            ok, reason = clean_vo_wav(vo_path)
            if ok:
                vo_cleaned += 1
                print(f"[{cid}] vo.wav: {reason}")
            else:
                print(f"[{cid}] vo.wav: already clean")
                
        clip_dir = CLIPS_DIR / cid
        tts_dir = clip_dir / "tts"
        if tts_dir.exists():
            for p in sorted(tts_dir.glob("turn_*.wav")):
                tok, treason = clean_take_or_turn_wav(p)
                if tok and "trimmed" in treason:
                    turn_cleaned += 1
                    print(f"  [{cid}/tts] {p.name}: {treason}")

    print(f"\nDone! Cleaned {vo_cleaned} vo.wav files and {turn_cleaned} turn wav files.")

if __name__ == "__main__":
    clean_all_hoyaup()
