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
            "pause_after_s": 0.24, # 240ms
            "sfx": "pop"
        },
        "cta": {
            "rate_offset": 4,    # Urgency & excitement
            "pitch": "+2Hz",      # High conversion appeal
            "pause_after_s": 0.00,
            "sfx": "cash"
        }
    }

    # Fallback speaking-rate estimate (chars/sec) for lines that produce no
    # audio at all, so an inserted silence segment is roughly as long as the
    # real take would have been -- mirrors the same baseline sfx_manager.py
    # uses for its own text-length-based duration estimate.
    BASELINE_CHARS_PER_SEC = 10.0
    MIN_FALLBACK_SILENCE_S = 0.60
    MAX_FALLBACK_SILENCE_S = 6.0

    @classmethod
    def _estimate_silence_duration_s(cls, text: str, rate_pct: int) -> float:
        """
        Estimates how long a line's spoken audio *would* have been, purely
        from character count and the line's configured rate offset, for use
        as a stand-in silence duration when every TTS path failed for that
        line. Not meant to be precise -- only to keep the rest of the
        timeline's cues aligned with their real audio instead of drifting
        earlier by a missing line's worth of time.
        """
        char_count = len(text.strip()) if text else 0
        if char_count <= 0:
            char_count = 12  # empty-after-sanitize lines still get a floor pause
        speed_mult = max(0.5, 1.0 + (rate_pct / 100.0))
        est = (char_count / cls.BASELINE_CHARS_PER_SEC) / speed_mult
        return min(cls.MAX_FALLBACK_SILENCE_S, max(cls.MIN_FALLBACK_SILENCE_S, est))

    @staticmethod
    def _trim_silence(data: np.ndarray, sample_rate: int = 44100, threshold_db: float = -42.0) -> Tuple[np.ndarray, float]:
        """
        Strips leading and trailing digital dead silence from TTS takes so speech starts
        immediately within 15ms and ends cleanly with zero trailing gap.
        Eliminates audio drift and prevents voice leading subtitles.

        Returns `(trimmed_data, head_trim_seconds)` -- the trim amount lets a
        caller holding word-level timestamps (measured against the
        untrimmed take) shift them onto the trimmed waveform's own clock.
        """
        if len(data) == 0:
            return data, 0.0
        threshold = 10.0 ** (threshold_db / 20.0)
        abs_data = np.abs(data)
        non_silent = np.where(abs_data > threshold)[0]
        if len(non_silent) == 0:
            return data, 0.0
        pad_head = int(0.015 * sample_rate)
        pad_tail = int(0.025 * sample_rate)
        start_idx = max(0, non_silent[0] - pad_head)
        end_idx = min(len(data), non_silent[-1] + pad_tail)
        return data[start_idx:end_idx], start_idx / sample_rate

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
        try:
            from scripts.subtitle_engine import SubtitleEngine
        except ImportError:
            from subtitle_engine import SubtitleEngine

        for line_idx, line in enumerate(raw_lines):
            clean_line = re.sub(r"\s+", " ", line).strip()
            if not clean_line:
                continue

            clauses = SubtitleEngine.split_into_smart_clauses(clean_line, max_line_len=max_chars)
            for idx, cl in enumerate(clauses):
                final_clauses.append({
                    "text": cl.strip(),
                    "sfx": "whoosh" if len(final_clauses) == 0 else ("cash" if "บาท" in cl or "พิกัด" in cl else None),
                    # Which original script-line this clause came from -- lets
                    # a caller (scripts/stages/voice_stage.py's beat_cues
                    # folding) group clause-level cues back into one cue per
                    # script line, since this method's own splitting produces
                    # more clauses than lines whenever a line exceeds
                    # max_chars.
                    "line_idx": line_idx,
                })

        return final_clauses

    @staticmethod
    def _synthesize_line_with_word_timing(
        text: str, voice_name: str, rate_str: str, pitch_str: str, out_mp3: Path
    ) -> Optional[List[Dict]]:
        """
        Synthesizes one line via edge-tts's streaming API (instead of the
        CLI) so per-word timestamps can be captured alongside the audio --
        writes the same MP3 the CLI would have produced either way. Returns
        the word list (`{"text", "start", "end"}`, seconds relative to this
        line's own *untrimmed* audio) on success, or `None` on any failure
        (network hiccup, a library-version mismatch, an unsupported voice).
        Caller must fall back to the plain CLI call when this returns `None`
        -- word-level timing is a bonus, never a render-blocking dependency.
        """
        try:
            import asyncio
            import edge_tts

            async def _run() -> List[Dict]:
                # edge-tts defaults to boundary="SentenceBoundary" -- without
                # this explicit override it never emits WordBoundary chunks
                # at all, silently giving one timestamp for the whole line.
                communicate = edge_tts.Communicate(
                    text, voice_name, rate=rate_str, pitch=pitch_str, boundary="WordBoundary"
                )
                words: List[Dict] = []
                with open(out_mp3, "wb") as f:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            f.write(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            words.append({
                                "text": chunk["text"],
                                "start": chunk["offset"] / 1e7,
                                "end": (chunk["offset"] + chunk["duration"]) / 1e7,
                            })
                return words

            return asyncio.run(_run())
        except Exception:
            return None

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

        # Sanitize each line for TTS — strip emoji, expand abbreviations for voice synthesis
        # while PRESERVING original display_text for on-screen subtitle cues!
        try:
            from scripts.tts_sanitizer import TTSSanitizer
            for item in line_items:
                orig_t = item.get("text", "")
                item["display_text"] = orig_t
                item["tts_text"] = TTSSanitizer.clean(orig_t) if orig_t else ""
        except ImportError:
            for item in line_items:
                item["display_text"] = item.get("text", "")
                item["tts_text"] = item.get("text", "")

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
        substituted_lines = []  # idx of lines that got a silence stand-in instead of real audio

        with tempfile.TemporaryDirectory() as tmp_dir:
            for idx, item in enumerate(line_items):
                line_text = item["tts_text"]
                display_text = item["display_text"]
                if not line_text:
                    # Sanitizing left nothing to speak (emoji/symbol-only line).
                    # Still emit a cue + silence so every later line's timeline
                    # stays aligned with its real audio position instead of
                    # permanently drifting earlier by this line's duration.
                    beat_type = cls.detect_beat_type(idx, total_lines, display_text or "")
                    fallback_dur = cls._estimate_silence_duration_s(display_text or "", base_rate_pct)
                    print(f"⚠️ [VoiceEngine] Line {idx + 1}/{total_lines} sanitized to empty text "
                          f"(display: {display_text!r}) -- inserting {fallback_dur:.2f}s of silence "
                          f"to keep subsequent cues aligned.")
                    cues.append({
                        "id": idx + 1,
                        "beat": beat_type,
                        "start": round(current_time, 3),
                        "end": round(current_time + fallback_dur, 3),
                        "text": display_text,
                        "sfx": None,
                        "word_timings": [],
                        "substituted": True,
                        "line_idx": item.get("line_idx"),
                    })
                    audio_segments.append(np.zeros(int(fallback_dur * sample_rate), dtype=np.float32))
                    current_time += fallback_dur
                    substituted_lines.append(idx)
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
                tts_errors = []  # collected diagnostics from each fallback attempt, for the warning if all fail

                # 2. Synthesize via Edge-TTS's streaming API first -- same
                # audio the CLI would produce, but captures per-word
                # timestamps along the way. Any failure (network, library
                # version, unsupported voice) falls straight back to the
                # plain CLI call below, so a missing feature never blocks
                # voice synthesis -- it just means this line has no
                # word-level timing, same as before this existed.
                line_word_timings = cls._synthesize_line_with_word_timing(
                    line_text, voice_name, rate_str, pitch_str, raw_mp3
                )
                if not raw_mp3.exists() or raw_mp3.stat().st_size == 0:
                    tts_errors.append("edge-tts streaming API: no output produced (see edge-tts CLI result below)")
                    cmd_edge = [
                        "edge-tts",
                        "--voice", voice_name,
                        "--rate", rate_str,
                        "--pitch", pitch_str,
                        "--text", line_text,
                        "--write-media", str(raw_mp3)
                    ]
                    edge_proc = subprocess.run(cmd_edge, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                    line_word_timings = None  # CLI path never carries word data
                    if edge_proc.returncode != 0 or not raw_mp3.exists() or raw_mp3.stat().st_size == 0:
                        stderr_txt = (edge_proc.stderr or b"").decode("utf-8", errors="ignore").strip()
                        tts_errors.append(
                            f"edge-tts CLI: returncode={edge_proc.returncode}"
                            + (f", stderr={stderr_txt[-500:]}" if stderr_txt else "")
                        )

                # Fallback to gTTS if needed
                if not raw_mp3.exists() or raw_mp3.stat().st_size == 0:
                    try:
                        from gtts import gTTS
                        tts = gTTS(text=line_text, lang='th')
                        tts.save(str(raw_mp3))
                    except Exception as gtts_err:
                        tts_errors.append(f"gTTS: {type(gtts_err).__name__}: {gtts_err}")

                # 3. Post-process Audio with High-Presence Equalizer & Loudness Normalization (-16 LUFS)
                if raw_mp3.exists() and raw_mp3.stat().st_size > 0:
                    cmd_ffmpeg = [
                        "ffmpeg", "-y", "-i", str(raw_mp3),
                        "-filter:a", "equalizer=f=3400:width_type=h:width=1400:g=3.0,equalizer=f=250:width_type=h:width=100:g=-2.0,loudnorm=I=-16:TP=-1.5:LRA=9",
                        "-ar", str(sample_rate), "-ac", "2",
                        str(proc_wav)
                    ]
                    ffmpeg_proc = subprocess.run(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                    if ffmpeg_proc.returncode != 0 or not proc_wav.exists():
                        stderr_txt = (ffmpeg_proc.stderr or b"").decode("utf-8", errors="ignore").strip()
                        tts_errors.append(
                            f"ffmpeg post-process: returncode={ffmpeg_proc.returncode}"
                            + (f", stderr={stderr_txt[-500:]}" if stderr_txt else "")
                        )
                elif not tts_errors:
                    tts_errors.append("no TTS engine produced audio (edge-tts and gTTS both yielded no output)")

                # 4. Read waveform & register cues with exact sample accuracy
                if proc_wav.exists():
                    data, sr = sf.read(str(proc_wav), dtype='float32')
                    if data.ndim > 1:
                        data = data[:, 0] # mono for concatenation
                    
                    # Trim silence padding from TTS to ensure speech starts immediately within 15ms
                    data, head_trim_s = cls._trim_silence(data, sample_rate=sample_rate)
                    seg_duration = len(data) / sample_rate

                    # Shift word timestamps (measured against the untrimmed
                    # take) onto this trimmed waveform's clock, then onto the
                    # full-track timeline via current_time. A word that fell
                    # inside the trimmed trailing silence is dropped rather
                    # than clamped -- it never actually sounds.
                    word_timings = []
                    if line_word_timings:
                        for w in line_word_timings:
                            w_start = w["start"] - head_trim_s
                            w_end = w["end"] - head_trim_s
                            if w_end <= 0 or w_start >= seg_duration:
                                continue
                            w_start = max(0.0, w_start)
                            w_end = min(seg_duration, w_end)
                            word_timings.append({
                                "text": w["text"],
                                "start": round(current_time + w_start, 3),
                                "end": round(current_time + w_end, 3),
                            })

                    cues.append({
                        "id": idx + 1,
                        "beat": beat_type,
                        "start": round(current_time, 3),
                        "end": round(current_time + seg_duration, 3),
                        "text": display_text,
                        "sfx": sfx_tag,
                        "word_timings": word_timings,
                        "substituted": False,
                        "line_idx": item.get("line_idx"),
                    })

                    # Guarantee 1-D float32 before appending (guards against edge-cases
                    # where sf.read or _trim_silence returns a multi-channel view)
                    data = np.asarray(data, dtype=np.float32).flatten()
                    audio_segments.append(data)

                    # Insert Natural Breathing Pause (tight 50-70ms gap to eliminate audio drift)
                    if idx < total_lines - 1:
                        clean_pause = min(0.08, max(0.04, pause_s * 0.4))
                        silence_samples = int(clean_pause * sample_rate)
                        silence_gap = np.zeros(silence_samples, dtype=np.float32)
                        audio_segments.append(silence_gap)
                        current_time += seg_duration + clean_pause
                    else:
                        current_time += seg_duration
                else:
                    # Every TTS path (edge-tts streaming API, edge-tts CLI, gTTS)
                    # failed to produce usable audio for this line. Insert a
                    # silence stand-in sized off the line's text length so
                    # `current_time` still advances roughly as far as real
                    # speech would have carried it -- every later line's cue
                    # keeps pointing at its actual audio position instead of
                    # drifting permanently earlier by this line's duration.
                    fallback_dur = cls._estimate_silence_duration_s(line_text, line_rate_pct)
                    reason = "; ".join(tts_errors) if tts_errors else "unknown failure (no diagnostics captured)"
                    print(f"⚠️ [VoiceEngine] Line {idx + 1}/{total_lines} failed to synthesize "
                          f"(text: {display_text!r}) -- {reason}. Inserting {fallback_dur:.2f}s of "
                          f"silence to keep subsequent cues aligned.")

                    cues.append({
                        "id": idx + 1,
                        "beat": beat_type,
                        "start": round(current_time, 3),
                        "end": round(current_time + fallback_dur, 3),
                        "text": display_text,
                        "sfx": None,
                        "word_timings": [],
                        "substituted": True,
                        "line_idx": item.get("line_idx"),
                    })
                    audio_segments.append(np.zeros(int(fallback_dur * sample_rate), dtype=np.float32))

                    if idx < total_lines - 1:
                        clean_pause = min(0.08, max(0.04, pause_s * 0.4))
                        silence_gap = np.zeros(int(clean_pause * sample_rate), dtype=np.float32)
                        audio_segments.append(silence_gap)
                        current_time += fallback_dur + clean_pause
                    else:
                        current_time += fallback_dur

                    substituted_lines.append(idx)

            # Concatenate all audio segments
            if audio_segments:
                final_audio = np.concatenate(audio_segments)
            else:
                final_audio = np.zeros(sample_rate, dtype=np.float32)

            total_duration = len(final_audio) / sample_rate

            # Save stereo output
            stereo_audio = np.column_stack((final_audio, final_audio))
            sf.write(str(out_audio), stereo_audio, sample_rate)

        if substituted_lines:
            print(f"⚠️ [VoiceEngine] {len(substituted_lines)}/{total_lines} line(s) substituted with "
                  f"silence (indices: {substituted_lines}) -- see warnings above for per-line reasons.")

        return {
            "audio_path": str(out_audio),
            "duration": total_duration,
            "cues": cues,
            # Additive fields -- existing callers that only read "audio_path"/
            # "duration"/"cues" (scripts/api_voice.py, scripts/stages/voice_stage.py)
            # are unaffected by dict-key access. Callers that care can check
            # "substituted_line_count" to detect that some lines had no real
            # audio and got a timed silence stand-in instead.
            "substituted_line_count": len(substituted_lines),
            "substituted_line_indices": substituted_lines,
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
สนใจกดตะกร้าซ้ายล่าง ดูรายละเอียดได้เลยครับ!"""

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
