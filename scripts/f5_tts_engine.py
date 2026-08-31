"""
F5-TTS Thai Voice Cloning Engine (VIZINTZOR/F5-TTS-TH-V2)
Optimized for AMD Ryzen 7 7735HS CPU inference with single-pass synthesis, 8-step Euler ODE & live step-by-step progress logging.
"""

import os
import sys

# Ensure UTF-8 I/O on Windows to prevent UnicodeEncodeError with Thai IPA phonemes
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

os.environ["PYTHONIOENCODING"] = "utf-8"

import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import torch
import torchaudio
import soundfile as sf
import numpy as np
import torchdiffeq
import f5_tts.model.cfm as cfm_module

# 1. Robust audio loader using soundfile to prevent torchcodec Windows DLL issues
def _safe_torchaudio_load(uri, *args, **kwargs):
    data, sr = sf.read(str(uri), dtype='float32')
    tensor = torch.from_numpy(data)
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)
    else:
        tensor = tensor.t()
    return tensor, sr

torchaudio.load = _safe_torchaudio_load

# 2. Live step-by-step ODE progress tracker
_orig_odeint = torchdiffeq.odeint

def _tracked_odeint(func, y0, t, *args, **kwargs):
    total_steps = max(1, len(t) - 1)
    current_step = [0]
    start_t = time.time()
    
    def wrapped_func(t_val, x_val):
        current_step[0] += 1
        pct = min(100, int((current_step[0] / total_steps) * 100))
        elapsed = time.time() - start_t
        print(f"   ⚡ [F5-TTS Thai] กำลังประมวลผล Diffusion Step {current_step[0]}/{total_steps} ({pct}%) | ใช้เวลา {elapsed:.1f}s", flush=True)
        return func(t_val, x_val)
        
    return _orig_odeint(wrapped_func, y0, t, *args, **kwargs)

cfm_module.odeint = _tracked_odeint
torchdiffeq.odeint = _tracked_odeint

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set optimal CPU thread count for AMD Ryzen 7 7735HS (8 physical cores)
torch.set_num_threads(8)

PRESETS_DIR = PROJECT_ROOT / "02_Assets" / "Voiceover" / "Presets"
PRESETS_DIR.mkdir(parents=True, exist_ok=True)

# Global model singleton to prevent reloading weights on each request
_TTS_MODEL_INSTANCE = None

def get_tts_engine(model_type: str = "v2"):
    """Loads and caches the F5-TTS Thai model."""
    global _TTS_MODEL_INSTANCE
    if _TTS_MODEL_INSTANCE is None:
        print(f"[F5-TTS-TH] Initializing F5-TTS Thai model ('{model_type}')...")
        from f5_tts_th.tts import TTS
        _TTS_MODEL_INSTANCE = TTS(model=model_type)
        print("[F5-TTS-TH] Model loaded successfully!")
    return _TTS_MODEL_INSTANCE

def ensure_default_presets():
    """Ensures default voice reference samples exist in 02_Assets/Voiceover/Presets."""
    presets = {
        "tiktok_male_pro": {
            "text": "สวัสดีครับทุกคน วันนี้ผมมีไอเทมเด็ดที่บอกเลยว่าต้องมีมาแนะนำครับ",
            "voice": "th-TH-NiwatNeural",
            "rate": "+15%",
            "pitch": "+0Hz"
        },
        "tiktok_female_pro": {
            "text": "สวัสดีค่ะทุกคน วันนี้มีของดีราคาโดนใจคุณภาพพรีเมียมมารีวิวให้ดูกันค่ะ",
            "voice": "th-TH-PremwadeeNeural",
            "rate": "+15%",
            "pitch": "+2Hz"
        },
        "tiktok_hype_seller": {
            "text": "รีบดูก่อนของหมด ตัวนี้เด็ดจริง คุ้มค่าที่สุด รีบกดสั่งซื้อในตะกร้าได้เลยครับ",
            "voice": "th-TH-NiwatNeural",
            "rate": "+25%",
            "pitch": "+2Hz"
        }
    }

    import subprocess
    for preset_name, data in presets.items():
        wav_path = PRESETS_DIR / f"{preset_name}.wav"
        txt_path = PRESETS_DIR / f"{preset_name}.txt"
        
        if not txt_path.exists():
            txt_path.write_text(data["text"], encoding="utf-8")
            
        if not wav_path.exists():
            cmd = [
                "edge-tts",
                "--text", data["text"],
                "--voice", data["voice"],
                "--rate", data["rate"],
                "--pitch", data["pitch"],
                "--write-media", str(wav_path)
            ]
            subprocess.run(cmd, capture_output=True)
            print(f"[F5-TTS-TH] Created reference preset: {preset_name}")

def list_voice_presets() -> List[Dict[str, str]]:
    """Returns available voice presets."""
    ensure_default_presets()
    presets = []
    for wav_file in PRESETS_DIR.glob("*.wav"):
        name = wav_file.stem
        txt_file = wav_file.with_suffix(".txt")
        ref_text = txt_file.read_text(encoding="utf-8").strip() if txt_file.exists() else ""
        presets.append({
            "name": name,
            "label": name.replace("_", " ").title(),
            "wav_path": str(wav_file),
            "ref_text": ref_text
        })
    return presets

def generate_f5_speech(
    text_or_lines: any,
    output_audio_path: str,
    ref_audio_path: Optional[str] = None,
    ref_text: Optional[str] = None,
    step: int = 8,
    speed: float = 1.05,
    cfg: float = 2.0,
    segment_mode: bool = False
) -> Dict[str, any]:
    """
    Generates voiceover using F5-TTS Thai (VIZINTZOR/F5-TTS-TH-V2).
    """
    # Ensure torchaudio patch is active
    torchaudio.load = _safe_torchaudio_load
    cfm_module.odeint = _tracked_odeint
    torchdiffeq.odeint = _tracked_odeint
    
    out_audio = Path(output_audio_path).resolve()
    out_audio.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Setup reference audio & text
    ensure_default_presets()
    if not ref_audio_path or not Path(ref_audio_path).exists():
        default_preset = PRESETS_DIR / "tiktok_male_pro.wav"
        ref_audio_path = str(default_preset)
        ref_text_path = default_preset.with_suffix(".txt")
        ref_text = ref_text_path.read_text(encoding="utf-8").strip() if ref_text_path.exists() else ""

    if not ref_text:
        ref_text_file = Path(ref_audio_path).with_suffix(".txt")
        if ref_text_file.exists():
            ref_text = ref_text_file.read_text(encoding="utf-8").strip()
        else:
            ref_text = "สวัสดีครับทุกคน วันนี้มีของดีมาแนะนำครับ"

    # 2. Parse text/lines
    line_items = []
    if isinstance(text_or_lines, str):
        for raw_line in text_or_lines.strip().split('\n'):
            t = raw_line.strip()
            if t:
                line_items.append({"text": t, "sfx": None})
    elif isinstance(text_or_lines, list):
        for item in text_or_lines:
            if isinstance(item, str):
                line_items.append({"text": item.strip(), "sfx": None})
            elif isinstance(item, dict):
                line_items.append({"text": item.get("text", "").strip(), "sfx": item.get("sfx")})

    tts = get_tts_engine(model_type="v2")
    sample_rate = 24000
    start_time = time.time()
    cues = []

    # Single-pass full script synthesis: Fastest on CPU (1 batch only)
    full_text = " ".join([item["text"] for item in line_items if item["text"]])
    print(f"\n[F5-TTS-TH] Fast CPU Synthesis (step={step}, chars={len(full_text)})...", flush=True)
    
    wav = tts.infer(
        ref_audio=ref_audio_path,
        ref_text=ref_text,
        gen_text=full_text,
        step=step,
        speed=speed,
        cfg=cfg,
        max_chars=1000
    )

    if isinstance(wav, tuple):
        wav = wav[0]
    if not isinstance(wav, np.ndarray):
        wav = np.array(wav, dtype=np.float32)
    final_wav = wav.flatten()
    total_duration = len(final_wav) / sample_rate

    # Distribute cues accurately across lines based on character lengths
    total_chars = max(1, sum(len(item["text"]) for item in line_items))
    current_time = 0.0
    for idx, item in enumerate(line_items):
        line_dur = total_duration * (len(item["text"]) / total_chars)
        cues.append({
            "id": idx + 1,
            "start": round(current_time, 3),
            "end": round(current_time + line_dur, 3),
            "text": item["text"],
            "sfx": item.get("sfx")
        })
        current_time += line_dur

    # Save to audio file
    sf.write(str(out_audio), final_wav, sample_rate)
    elapsed = time.time() - start_time
    print(f"\n[F5-TTS-TH] Completed in {elapsed:.1f}s! Total audio: {total_duration:.2f}s (RTF: {elapsed/max(0.1, total_duration):.2f})", flush=True)

    return {
        "audio_path": str(out_audio),
        "duration": total_duration,
        "cues": cues,
        "rtf": round(elapsed / max(0.1, total_duration), 2)
    }

if __name__ == "__main__":
    ensure_default_presets()
    print("Presets available:", [p["name"] for p in list_voice_presets()])
