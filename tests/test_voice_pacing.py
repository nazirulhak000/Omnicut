"""
Test Script for Natural Rhythmic Voice Pacing (Edge-TTS Thai Neural)
Generates high-energy Thai voiceover with distinct pauses between script beats.
"""

import sys
import asyncio
import edge_tts
import soundfile as sf
import numpy as np
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

SAMPLE_RATE = 44100
OUT_DIR = Path("02_Assets/Voiceover/Test_Pacing")
# NOTE: this file has no `def test_*` functions -- it is a manual diagnostic
# script (see .agents/rules/testing_standard.md rule 4: side effects at
# import time are not allowed in tests/test_*.py). OUT_DIR is only created
# when main() actually runs under `if __name__ == "__main__":`, never on
# plain pytest collection/import.

# Sample Tech Script with 5 distinct beats
SCRIPT_BEATS = [
    {"text": "อย่าเพิ่งซื้อสายชาร์จธรรมดา ถ้ายังไม่เห็นตัวนี้!", "pause_s": 0.40, "sfx": "boom"},
    {"text": "Esseger สายชาร์จแม่เหล็ก 3-in-1 ดูดแน่น ชาร์จเร็ว 66W", "pause_s": 0.25, "sfx": "pop"},
    {"text": "ข้อต่อหมุนได้ 540 องศา เล่นเกมไม่สะดุด ไม่ติดมือ", "pause_s": 0.25, "sfx": "pop"},
    {"text": "หมดปัญหาสายหักตรงคอ เสียบในที่มืดได้สบายๆ", "pause_s": 0.30, "sfx": "ding"},
    {"text": "ราคาพิเศษวันนี้แค่ 149 บาท กดในตะกร้าซ้ายล่างได้เลยครับ", "pause_s": 0.40, "sfx": "cash"}
]

async def synthesize_beat(text: str, voice: str, rate: str = "+20%", pitch: str = "+4Hz", out_path: Path = None):
    # Construct SSML for natural expressive tone
    ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='th-TH'>
        <voice name='{voice}'>
            <prosody rate='{rate}' pitch='{pitch}'>
                {text}
            </prosody>
        </voice>
    </speak>"""
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(str(out_path))

async def build_rhythmic_voice(voice_name: str, label: str, rate: str = "+18%", pitch: str = "+3Hz"):
    import tempfile, subprocess
    
    audio_segments = []
    cues = []
    current_time = 0.0
    
    with tempfile.TemporaryDirectory() as tmp:
        for idx, beat in enumerate(SCRIPT_BEATS):
            tmp_mp3 = Path(tmp) / f"beat_{idx}.mp3"
            tmp_wav = Path(tmp) / f"beat_{idx}.wav"
            
            # 1. Synthesize line
            await synthesize_beat(beat["text"], voice_name, rate=rate, pitch=pitch, out_path=tmp_mp3)
            
            # 2. Convert to 44.1kHz stereo WAV
            cmd = [
                "ffmpeg", "-y", "-i", str(tmp_mp3),
                "-filter:a", "equalizer=f=3200:width_type=h:width=1200:g=2.5,loudnorm=I=-16:TP=-1.5:LRA=10",
                "-ar", str(SAMPLE_RATE), "-ac", "2",
                str(tmp_wav)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            
            # 3. Read data
            data, sr = sf.read(str(tmp_wav), dtype='float32')
            if data.ndim > 1:
                data = data[:, 0]
            
            dur = len(data) / SAMPLE_RATE
            
            cues.append({
                "line": idx + 1,
                "text": beat["text"],
                "start": round(current_time, 3),
                "end": round(current_time + dur, 3),
                "sfx": beat["sfx"]
            })
            
            audio_segments.append(data)
            
            # Insert rhythmic dramatic pause between lines
            pause_samples = int(beat["pause_s"] * SAMPLE_RATE)
            audio_segments.append(np.zeros(pause_samples, dtype=np.float32))
            
            current_time += dur + beat["pause_s"]
            
        final_mono = np.concatenate(audio_segments)
        final_stereo = np.column_stack((final_mono, final_mono))
        
        out_file = OUT_DIR / f"voice_{label}_rhythmic.wav"
        sf.write(str(out_file), final_stereo, SAMPLE_RATE)
        print(f"✓ Generated {label} Voice: {out_file} (Duration: {len(final_mono)/SAMPLE_RATE:.2f}s)")
        return str(out_file), cues

async def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("\n🎙️ Synthesizing Rhythmic Voice Samples with Dramatic Pauses...\n")
    # 1. Male Niwat (Fast, Energetic, Tech)
    f_male, cues_m = await build_rhythmic_voice("th-TH-NiwatNeural", "male_niwat", rate="+20%", pitch="+2Hz")
    # 2. Female Premwadee (Bright, Fast, Friendly)
    f_female, cues_f = await build_rhythmic_voice("th-TH-PremwadeeNeural", "female_premwadee", rate="+18%", pitch="+3Hz")
    
    print("\n--- CUES & TIMESTAMPS ---")
    for c in cues_m:
        print(f"  [{c['start']}s -> {c['end']}s] (SFX: {c['sfx']}) : {c['text']}")

if __name__ == "__main__":
    asyncio.run(main())
