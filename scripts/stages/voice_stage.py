"""
Voice Stage for OmniCut Pro Studio.
Handles real human voice audio conversion, Gemini Flash TTS synthesis (with Edge-TTS fallback),
Edge-TTS synthesis, acoustic waveform alignment, and cue timing generation.
"""

import time
import subprocess
from pathlib import Path
from typing import List, Dict, Any

from scripts.voice_engine import VoiceEngine
from scripts.subtitle_engine import SubtitleEngine
from scripts.pipeline_context import PipelineContext


class VoiceStage:
    """Synthesizes or processes voiceover audio and derives timing cues."""

    @classmethod
    def run(cls, ctx: PipelineContext) -> None:
        cues: List[Dict[str, Any]] = []
        voice_engine_used = ctx.voice_engine_type
        script_data = ctx.script_data or {"lines": []}

        if not ctx.should_run("voice"):
            if not ctx.manifest:
                raise ValueError("Cannot reuse voice without manifest")
            voice_audio_path = ctx.reuse("voice_audio", "เสียงพากย์")
            cues = ctx.manifest["cues"]
            total_duration = ctx.manifest["total_duration"]
            voice_engine_used = (ctx.manifest.get("render_params") or {}).get("voice_engine_used", voice_engine_used)
            print(f"♻️  [2/5] Reusing voiceover: {voice_audio_path.name} ({total_duration:.2f}s)")

        elif ctx.human_voice_audio_path and Path(ctx.human_voice_audio_path).exists():
            voice_audio_path = ctx.out_path("voiceover", ".wav")
            ctx.notify("🎙️ [2/5] โหลดและประมวลผลไฟล์เสียงคนพูดจริง...", 0.25)
            print(f"\n🎙️ [2/5] Using REAL HUMAN VOICE: {ctx.human_voice_audio_path}")
            human_src = Path(ctx.human_voice_audio_path).resolve()
            conv_cmd = [
                "ffmpeg", "-y", "-i", str(human_src),
                "-ac", "2", "-ar", "44100", "-b:a", "192k",
                str(voice_audio_path)
            ]
            subprocess.run(conv_cmd, capture_output=True, encoding="utf-8", errors="ignore")

            probe_cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(voice_audio_path)
            ]
            probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            total_duration = float(probe_res.stdout.strip()) if probe_res.stdout.strip() else 15.0

            lines_list = script_data["lines"]
            num_lines = max(1, len(lines_list))
            dur_per_line = total_duration / num_lines
            for idx, item in enumerate(lines_list):
                cues.append({
                    "id": idx + 1,
                    "start": idx * dur_per_line,
                    "end": (idx + 1) * dur_per_line,
                    "text": item["text"],
                    "sfx": item.get("sfx"),
                    "on_screen": item.get("on_screen", "")
                })
            print(f"   Human voice loaded! Duration: {total_duration:.2f}s, Cues synced: {len(cues)}")

        elif ctx.voice_engine_type == "gemini_tts":
            ctx.notify("⚡ [2/5] กำลังสังเคราะห์เสียงพากย์ด้วย Google Gemini Flash TTS...", 0.25)
            print("\n⚡ [2/5] Synthesizing Voice via Google Gemini Flash TTS...")
            from scripts.gemini_tts_engine import GeminiFlashTTSEngine

            voice_audio_path = ctx.out_path("voiceover", ".wav")
            gemini_voice = GeminiFlashTTSEngine.resolve_voice(preset=ctx.voice_preset, gender=ctx.voice)

            speed_val = 1.15
            if ctx.voice_rate:
                try:
                    num = int(ctx.voice_rate.replace("%", "").replace("+", ""))
                    speed_val = 1.0 + (num / 100.0)
                except Exception:
                    pass

            full_script_text = script_data.get("full_text") or "\n".join([l["text"] for l in script_data["lines"]])
            voice_engine_used = "gemini_tts"
            try:
                last_tts_error = None
                for attempt in range(2):
                    try:
                        GeminiFlashTTSEngine.generate_speech(
                            text=full_script_text,
                            output_path=str(voice_audio_path),
                            voice_name=gemini_voice,
                            ad_tone=ctx.ad_tone or "commercial_premium",
                            speed=speed_val
                        )
                        last_tts_error = None
                        break
                    except Exception as tts_err:
                        last_tts_error = tts_err
                        if attempt == 0:
                            print(f"⚠️ [Gemini Flash TTS] ล้มเหลว ({tts_err}) — ลองใหม่อีกครั้ง...")
                            time.sleep(1.0)
                if last_tts_error is not None:
                    raise last_tts_error

                probe_cmd = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(voice_audio_path)
                ]
                probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
                total_duration = float(probe_res.stdout.strip()) if probe_res.stdout.strip() else 15.0

                lines_list = script_data["lines"]
                split_items = []
                for item in lines_list:
                    cl_texts = SubtitleEngine.split_into_smart_clauses(item.get("text", ""))
                    for ci, cl in enumerate(cl_texts):
                        split_items.append({
                            "text": cl,
                            "sfx": item.get("sfx") if ci == 0 else None,
                            "on_screen": item.get("on_screen", "") if ci == 0 else ""
                        })

                try:
                    import soundfile as sf
                    import numpy as np

                    wav_data, sr = sf.read(str(voice_audio_path))
                    if wav_data.ndim > 1:
                        wav_data = wav_data[:, 0]
                    total_dur = len(wav_data) / sr

                    hop = int(0.01 * sr)  # 10ms hops
                    rms = np.array([np.sqrt(np.mean(wav_data[i:i+hop]**2)) for i in range(0, len(wav_data)-hop, hop)])
                    peak = np.max(rms) if len(rms) > 0 else 1.0
                    thresh = peak * 0.055

                    min_pause_frames = int(0.14 / 0.01)  # >140ms silence is speech pause
                    is_speech = rms >= thresh

                    blocks = []
                    in_speech = False
                    start_f = 0
                    silence_count = 0

                    for f, sp in enumerate(is_speech):
                        if sp:
                            if not in_speech:
                                in_speech = True
                                start_f = max(0, f - 2)
                            silence_count = 0
                        else:
                            if in_speech:
                                silence_count += 1
                                if silence_count >= min_pause_frames:
                                    in_speech = False
                                    end_f = f - silence_count + 3
                                    if end_f > start_f + 5:
                                        blocks.append((start_f * 0.01, min(total_dur, end_f * 0.01)))
                    if in_speech:
                        blocks.append((start_f * 0.01, total_dur))

                    total_speech_dur = sum(b[1] - b[0] for b in blocks) if blocks else total_duration
                    total_chars = max(1, sum(len(x["text"]) for x in split_items))

                    def _time_at_speech_offset(offset: float) -> float:
                        accum = 0.0
                        for b_start, b_end in blocks:
                            b_dur = b_end - b_start
                            if accum + b_dur >= offset:
                                frac = (offset - accum) / b_dur if b_dur > 0 else 0
                                return b_start + (frac * b_dur)
                            accum += b_dur
                        return blocks[-1][1] if blocks else total_dur

                    curr_speech_offset = 0.0
                    for idx, item in enumerate(split_items):
                        item_chars = len(item["text"])
                        dur_in_speech = (item_chars / total_chars) * total_speech_dur
                        s_time = _time_at_speech_offset(curr_speech_offset)
                        e_time = _time_at_speech_offset(curr_speech_offset + dur_in_speech)

                        for b_start, b_end in blocks:
                            if abs(s_time - b_start) < 0.15:
                                s_time = b_start
                                break

                        if idx == 0:
                            s_time = blocks[0][0] if blocks else 0.0
                        if idx == len(split_items) - 1:
                            e_time = total_duration

                        cues.append({
                            "id": idx + 1,
                            "start": round(s_time, 3),
                            "end": round(e_time, 3),
                            "text": item["text"],
                            "sfx": item.get("sfx"),
                            "on_screen": item.get("on_screen", "")
                        })
                        curr_speech_offset += dur_in_speech
                except Exception as align_err:
                    print(f"⚠️ [Gemini Flash TTS] Acoustic alignment fallback ({align_err}) — using proportional fallback")
                    total_chars = max(1, sum(len(x["text"]) for x in split_items))
                    curr_t = 0.0
                    for idx, item in enumerate(split_items):
                        line_dur = (len(item["text"]) / total_chars) * total_duration
                        line_end = min(total_duration, curr_t + line_dur)
                        if idx == len(split_items) - 1:
                            line_end = total_duration
                        cues.append({
                            "id": idx + 1,
                            "start": round(curr_t, 3),
                            "end": round(line_end, 3),
                            "text": item["text"],
                            "sfx": item.get("sfx"),
                            "on_screen": item.get("on_screen", "")
                        })
                        curr_t = line_end
                print(f"   Gemini Flash TTS voice generated! Duration: {total_duration:.2f}s, Cues: {len(cues)}")
            except Exception as gemini_err:
                voice_engine_used = "edge_tts"
                print(f"⚠️ [Gemini Flash TTS] Failed ({gemini_err}) — falling back to Edge-TTS...")
                ctx.notify("⚠️ Gemini TTS ขัดข้อง สลับไปใช้ Edge-TTS สำรอง — เสียงจะไม่ใช่ Gemini", 0.30)
                voice_res = VoiceEngine.generate_voiceover(
                    text_or_lines=script_data["lines"],
                    output_audio_path=str(voice_audio_path),
                    voice=ctx.voice,
                    rate=ctx.voice_rate
                )
                cues = voice_res["cues"]
                total_duration = voice_res["duration"]
        else:
            voice_audio_path = ctx.out_path("voiceover", ".wav")
            ctx.notify("🗣️ [2/5] กำลังสังเคราะห์เสียง AI พากย์เร็ว TikTok และจับเวลา...", 0.25)
            print("\n🗣️ [2/5] Synthesizing AI Thai Voiceover & Timestamps...")
            voice_res = VoiceEngine.generate_voiceover(
                text_or_lines=script_data["lines"],
                output_audio_path=str(voice_audio_path),
                voice=ctx.voice,
                rate=ctx.voice_rate
            )
            cues = voice_res["cues"]
            total_duration = voice_res["duration"]
            print(f"   Voice generated! Duration: {total_duration:.2f}s, Cues: {len(cues)}")

        ctx.voice_audio_path = voice_audio_path
        ctx.cues = cues
        ctx.total_duration = total_duration
        ctx.voice_engine_used = voice_engine_used
