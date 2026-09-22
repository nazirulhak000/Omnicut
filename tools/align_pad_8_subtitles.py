"""Align speech audio using Faster-Whisper to extract word-level timestamps.
"""

import json
from pathlib import Path
from faster_whisper import WhisperModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCT_DIR = PROJECT_ROOT / ".tmp" / "Products" / "Xiaomi_Pad_8"
WORKSPACE_DIR = PRODUCT_DIR / "02_Workspace"
AUDIO_PATH = WORKSPACE_DIR / "audio" / "voice_pad_8_60s_sync.wav"
SUB_DIR = WORKSPACE_DIR / "subtitles"
SUB_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = SUB_DIR / "whisper_pad_8.json"

print(f"[*] Transcribing and aligning {AUDIO_PATH.name} with Faster-Whisper...")

model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe(
    str(AUDIO_PATH),
    language="th",
    word_timestamps=True,
    initial_prompt="Xiaomi Pad 8 แท็บเล็ต Snapdragon 8s Gen 4 HyperOS 3 Dolby Atmos Focus Pen Pro Turbo Charge"
)

result = {
    "language": info.language,
    "duration": info.duration,
    "segments": []
}

for s in segments:
    seg_data = {
        "start": round(s.start, 2),
        "end": round(s.end, 2),
        "text": s.text.strip(),
        "words": []
    }
    if s.words:
        for w in s.words:
            seg_data["words"].append({
                "word": w.word,
                "start": round(w.start, 2),
                "end": round(w.end, 2),
                "probability": round(w.probability, 3)
            })
    result["segments"].append(seg_data)
    print(f"  [{s.start:05.2f} - {s.end:05.2f}]: {s.text}")

OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[OK] Saved alignment to {OUT_JSON}")
