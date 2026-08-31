"""
Voice Engine supporting Human-Like Reviewer Cadence (Dynamic Speed Curves, Expressive Pitch & Micro-Pauses)
Designed for authentic TikTok / Reels product reviews.
"""

import os
import sys
import subprocess
import json
import tempfile
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import soundfile as sf
import numpy as np

# Ensure UTF-8 I/O on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import VOICES, DEFAULT_VOICE, DEFAULT_VOICE_RATE, DEFAULT_VOICE_PITCH

class VoiceEngine:
    """Generates authentic, expressive Thai voiceover with human reviewer cadence and pauses."""

    # Pacing and Prosody Profiles for different beats
    BEAT_PROFILES = {
        "hook": {
            "rate_offset": 5,    # +5% faster
            "pitch": "+4Hz",      # Higher energy exclamation
            "pause_after_s": 0.34, # 340ms dramatic breathing room
            "sfx": "boom"
        },
        "problem": {
            "rate_offset": 0,    # Normal conversational
            "pitch": "+0Hz",      # Empathetic, questioning tone
            "pause_after_s": 0.22, # 220ms
            "sfx": "pop"
        },
        "feature": {
            "rate_offset": 2,    # Crisp & clear
            "pitch": "+3Hz",      # Enthusiastic reveal
            "pause_after_s": 0.26, # 260ms
            "sfx": "ding"
        },
        "benefit": {
            "rate_offset": 2,
            "pitch": "+2Hz",
            "pause_after_s": 0.24,
            "sfx": "pop"
        },
        "cta": {
            "rate_offset": 4,    # Urgency & closing
            "pitch": "+3Hz",      # Friendly high energy
            "pause_after_s": 0.38, # 380ms
            "sfx": "cash"
        }
    }

    @classmethod
    def detect_beat_type(cls, line_idx: int, total_lines: int, text: str) -> str:
        """Detect the emotional beat type of a script line."""
        clean = text.strip().lower()
        if line_idx == 0:
            return "hook"
        if line_idx == total_lines - 1:
            return "cta"
        if any(k in clean for k in ["ราคา", "โปร", "ตะกร้า", "คุ้ม", "สั่ง", "ซ้ายล่าง", "รีบกด"]):
            return "cta"
        if any(k in clean for k in ["ปัญหา", "พัง", "เบื่อ", "หัก", "ยาก", "ช้า", "ขาด", "หาย"]):
            return "problem"
        if any(k in clean for k in ["ดูด", "หมุน", "ชาร์จ", "วัตต์", "ทน", "แม่เหล็ก", "66w", "เร็ว", "แท้"]):
            return "feature"
        return "benefit"

    @classmethod
    def segment_into_clauses(cls, text_or_lines: any, max_chars: int = 38) -> List[Dict]:
        """
        Intelligently decomposes script into cohesive 1-line semantic clauses (15-38 chars).
        Ensures complete thoughts, attaches qualifiers (540 องศา, สบายๆ เลยครับ), 
        and prepares natural breathing intervals.
        """
        raw_lines = []
        if isinstance(text_or_lines, str):
            raw_lines = [l.strip() for l in text_or_lines.strip().split("\n") if l.strip()]
        elif isinstance(text_or_lines, list):
            for item in text_or_lines:
                if isinstance(item, str):
                    raw_lines.append(item.strip())
                elif isinstance(item, dict):
                    raw_lines.append(item.get("text", "").strip())

        final_clauses = []
        SPLIT_REGEX = re.compile(
            r"(?<=[!?])\s+|"
            r"(?=ถ้ายัง|บอกเลยว่า|คือดูด|ดูดแน่น|ชาร์จไว|แถม|จะนอน|หรือดู|หมดปัญหา|เสียบใน|พิกัด|กดใน|จิ้มใน|รีบกด)"
        )

        for line in raw_lines:
            clean_line = re.sub(r"\s+", " ", line).strip()
            if not clean_line:
                continue

            if len(clean_line) <= max_chars:
                final_clauses.append({"text": clean_line, "sfx": None})
                continue

            parts = [p.strip() for p in SPLIT_REGEX.split(clean_line) if p.strip()]
            curr = []
            for p in parts:
                cand = " ".join(curr + [p]) if curr else p
                if len(cand) <= max_chars:
                    curr.append(p)
                else:
                    if curr:
                        final_clauses.append({"text": " ".join(curr).strip(), "sfx": None})
                    curr = [p]
            if curr:
                rem = " ".join(curr).strip()
                if len(rem) <= 6 and final_clauses:
                    final_clauses[-1]["text"] = (final_clauses[-1]["text"] + " " + rem).strip()
                else:
                    final_clauses.append({"text": rem, "sfx": None})

        return final_clauses

    @classmethod
    def generate_crystal_voice(
        cls,
        text_or_lines: any,
        output_audio_path: str,
        speed: float = 1.20,
        voice_gender: str = "male",
        reviewer_style: str = "tiktok_hype"
    ) -> Dict[str, any]:
        """
        Synthesizes line-by-line Thai speech with dynamic human reviewer pitch/rate curves,
        natural micro-pauses, vocal presence equalization, and precise timestamp cues.
        """
        out_audio = Path(output_audio_path).resolve()
        out_audio.parent.mkdir(parents=True, exist_ok=True)

        line_items = cls.segment_into_clauses(text_or_lines)

        if not line_items:
            raise ValueError("No text lines provided for voice synthesis.")

        # Select Neural Voice
        # Male: th-TH-NiwatNeural (High energy, punchy)
        # Female: th-TH-PremwadeeNeural (Bright, clear, friendly)
        voice_name = "th-TH-NiwatNeural" if voice_gender == "male" else "th-TH-PremwadeeNeural"
        base_rate_pct = int((speed - 1.0) * 100) if speed >= 1.0 else int((speed - 1.0) * 100)

        cues = []
        audio_segments = []
        sample_rate = 44100
        current_time = 0.0
        total_lines = len(line_items)

        with tempfile.TemporaryDirectory() as tmp_dir:
            for idx, item in enumerate(line_items):
                line_text = item["text"]
                if not line_text:
                    continue

                # 1. Determine Beat & Dynamic Prosody
                beat_type = cls.detect_beat_type(idx, total_lines, line_text)
                profile = cls.BEAT_PROFILES.get(beat_type, cls.BEAT_PROFILES["benefit"])
                
                line_rate_pct = base_rate_pct + profile["rate_offset"]
                rate_str = f"+{line_rate_pct}%" if line_rate_pct >= 0 else f"{line_rate_pct}%"
                pitch_str = profile["pitch"]
                pause_s = profile["pause_after_s"]
                sfx_tag = item.get("sfx") or profile["sfx"]

                raw_mp3 = Path(tmp_dir) / f"raw_{idx}.mp3"
                proc_wav = Path(tmp_dir) / f"proc_{idx}.wav"

                # 2. Synthesize via Edge-TTS CLI
                cmd_edge = [
                    "edge-tts",
                    "--voice", voice_name,
                    "--rate", rate_str,
                    "--pitch", pitch_str,
                    "--text", line_text,
                    "--write-media", str(raw_mp3)
                ]
                subprocess.run(cmd_edge, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                # Fallback to gTTS if needed
                if not raw_mp3.exists() or raw_mp3.stat().st_size == 0:
                    try:
                        from gtts import gTTS
                        tts = gTTS(text=line_text, lang='th')
                        tts.save(str(raw_mp3))
                    except Exception:
                        pass

                # 3. Post-process Audio with High-Presence Equalizer & Loudness Normalization (-16 LUFS)
                if raw_mp3.exists() and raw_mp3.stat().st_size > 0:
                    cmd_ffmpeg = [
                        "ffmpeg", "-y", "-i", str(raw_mp3),
                        "-filter:a", "equalizer=f=3400:width_type=h:width=1400:g=3.0,equalizer=f=250:width_type=h:width=100:g=-2.0,loudnorm=I=-16:TP=-1.5:LRA=9",
                        "-ar", str(sample_rate), "-ac", "2",
                        str(proc_wav)
                    ]
                    subprocess.run(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                # 4. Read waveform & register cues
                if proc_wav.exists():
                    data, sr = sf.read(str(proc_wav), dtype='float32')
                    if data.ndim > 1:
                        data = data[:, 0] # mono for concatenation
                    
                    seg_duration = len(data) / sample_rate

                    cues.append({
                        "id": idx + 1,
                        "beat": beat_type,
                        "start": round(current_time, 3),
                        "end": round(current_time + seg_duration, 3),
                        "text": line_text,
                        "sfx": sfx_tag
                    })

                    audio_segments.append(data)

                    # Insert Natural Breathing Pause (except after the final line)
                    if idx < total_lines - 1:
                        silence_samples = int(pause_s * sample_rate)
                        silence_gap = np.zeros(silence_samples, dtype=np.float32)
                        audio_segments.append(silence_gap)
                        current_time += seg_duration + pause_s
                    else:
                        current_time += seg_duration

            # Concatenate all audio segments
            if audio_segments:
                final_audio = np.concatenate(audio_segments)
            else:
                final_audio = np.zeros(sample_rate, dtype=np.float32)

            total_duration = len(final_audio) / sample_rate

            # Save stereo output
            stereo_audio = np.column_stack((final_audio, final_audio))
            sf.write(str(out_audio), stereo_audio, sample_rate)

        return {
            "audio_path": str(out_audio),
            "duration": total_duration,
            "cues": cues
        }

    @classmethod
    def generate_voiceover(
        cls,
        text_or_lines: any,
        output_audio_path: str,
        voice: str = "th-TH-NiwatNeural",
        rate: str = "+20%",
        pitch: str = "+0Hz"
    ) -> Dict[str, any]:
        """Wrapper alias for pipeline compatibility."""
        gender = "female" if "Premwadee" in voice or "female" in voice else "male"
        speed = 1.20
        if rate:
            try:
                num = int(rate.replace("%", "").replace("+", ""))
                speed = 1.0 + (num / 100.0)
            except Exception:
                pass

        return cls.generate_crystal_voice(
            text_or_lines=text_or_lines,
            output_audio_path=output_audio_path,
            speed=speed,
            voice_gender=gender
        )

if __name__ == "__main__":
    sample_text = """ทุกคน! อย่าเพิ่งซื้อสายชาร์จธรรมดา ถ้ายังไม่เห็นตัวนี้
บอกเลยว่า Esseger สายชาร์จแม่เหล็ก 3-in-1 คือดูดแน่นมากกก ชาร์จไว 66W
แถมข้อต่อยังหมุนได้ 540 องศา จะนอนเล่นเกมหรือดูซีรีส์ก็ไม่เกะกะมือ
หมดปัญหาสายหักตรงคอ เสียบในที่มืดได้สบายๆ เลยครับ
พิกัดราคาพิเศษวันนี้แค่ 149 บาท กดในตะกร้าซ้ายล่างได้เลยครับ!"""

    res = VoiceEngine.generate_crystal_voice(
        text_or_lines=sample_text,
        output_audio_path="02_Assets/Voiceover/sample_human_reviewer_voice.wav",
        speed=1.20,
        voice_gender="male"
    )
    print("\n🎉 Human Reviewer Voice Generated Successfully!")
    print(f"Total Duration: {res['duration']:.2f}s")
    for c in res["cues"]:
        print(f"  [{c['start']}s -> {c['end']}s] ({c['beat']}) [SFX: {c['sfx']}] : {c['text']}")
