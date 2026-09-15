"""
Voice Stage for OmniCut Pro Studio.
Handles real human voice audio conversion, Gemini Flash TTS synthesis (with Edge-TTS fallback),
Edge-TTS synthesis, acoustic waveform alignment, and cue timing generation.
"""

import time
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple

from scripts.voice_engine import VoiceEngine
from scripts.subtitle_engine import SubtitleEngine
from scripts.pipeline_context import PipelineContext
from scripts.error_handler import AppError, ErrorCategory
from scripts.quota import is_quota_error


def _probe_audio_duration(audio_path: Path) -> float:
    """
    Runs ffprobe to get an audio file's duration in seconds.

    Raises AppError (category=FFMPEG) instead of silently defaulting to a
    plausible-looking-but-wrong value when ffprobe fails, returns empty
    stdout, or reports a non-positive/unparseable duration. A wrong
    duration here silently truncates or pads the final render (it flows
    into cue generation and the ffmpeg `-t {total_duration}` trim), so it
    must fail loudly rather than default to a stand-in like 15.0.
    """
    probe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
    ]
    try:
        probe_res = subprocess.run(
            probe_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
    except Exception as exc:
        raise AppError(
            category=ErrorCategory.FFMPEG,
            code="FFPROBE_LAUNCH_FAILED",
            message_th="ไม่สามารถเรียกใช้ ffprobe เพื่อตรวจสอบความยาวไฟล์เสียงได้",
            suggestion_th="กรุณาตรวจสอบว่าติดตั้ง ffmpeg/ffprobe ครบถ้วนและอยู่ใน PATH",
            details=f"file={audio_path}, error={exc}",
        ) from exc

    stdout = (probe_res.stdout or "").strip()
    stderr = (probe_res.stderr or "").strip()

    if probe_res.returncode != 0 or not stdout:
        raise AppError(
            category=ErrorCategory.FFMPEG,
            code="FFPROBE_DURATION_FAILED",
            message_th="ตรวจสอบความยาวไฟล์เสียงพากย์ไม่สำเร็จ (ffprobe ล้มเหลวหรือไฟล์เสีย)",
            suggestion_th="กรุณาตรวจสอบว่าไฟล์เสียงต้นทางไม่เสียหายและเป็นฟอร์แมตมาตรฐาน",
            details=f"file={audio_path}, returncode={probe_res.returncode}, stderr={stderr[:1000]}",
        )

    try:
        duration = float(stdout)
    except ValueError as exc:
        raise AppError(
            category=ErrorCategory.FFMPEG,
            code="FFPROBE_DURATION_UNPARSEABLE",
            message_th="ffprobe คืนค่าความยาวไฟล์เสียงที่ไม่สามารถแปลงเป็นตัวเลขได้",
            suggestion_th="กรุณาตรวจสอบว่าไฟล์เสียงต้นทางไม่เสียหายและเป็นฟอร์แมตมาตรฐาน",
            details=f"file={audio_path}, stdout={stdout!r}, stderr={stderr[:1000]}",
        ) from exc

    if duration <= 0:
        raise AppError(
            category=ErrorCategory.FFMPEG,
            code="FFPROBE_DURATION_NONPOSITIVE",
            message_th="ffprobe รายงานว่าไฟล์เสียงพากย์มีความยาวเป็นศูนย์หรือติดลบ",
            suggestion_th="กรุณาตรวจสอบว่าไฟล์เสียงต้นทางไม่เสียหายและมีเนื้อหาเสียงจริง",
            details=f"file={audio_path}, duration={duration}",
        )

    return duration


def _rms_speech_blocks(wav_data, sr: int) -> Tuple[List[Tuple[float, float]], float]:
    """
    Detects contiguous speech blocks (start, end) in seconds from raw audio
    samples using a simple RMS-energy threshold with a minimum-pause gate.
    Shared by both the Gemini TTS and human-voice alignment paths.
    """
    import numpy as np

    total_dur = len(wav_data) / sr
    hop = int(0.01 * sr)  # 10ms hops
    if hop <= 0 or len(wav_data) <= hop:
        return [], total_dur

    rms = np.array([np.sqrt(np.mean(wav_data[i:i + hop] ** 2)) for i in range(0, len(wav_data) - hop, hop)])
    peak = np.max(rms) if len(rms) > 0 else 1.0
    thresh = peak * 0.055

    min_pause_frames = int(0.14 / 0.01)  # >140ms silence is a speech pause
    is_speech = rms >= thresh

    blocks: List[Tuple[float, float]] = []
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

    return blocks, total_dur


def _proportional_fallback_cues(split_items: List[Dict[str, Any]], total_duration: float) -> List[Dict[str, Any]]:
    """Even/proportional (character-count weighted) cue split -- the safe
    fallback used when acoustic alignment fails or looks implausible."""
    cues: List[Dict[str, Any]] = []
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
    return cues


def _rms_aligned_cues(
    voice_audio_path: Path,
    split_items: List[Dict[str, Any]],
    total_duration: float,
    log_prefix: str = "[Voice Alignment]",
) -> List[Dict[str, Any]]:
    """
    Builds cues aligned to detected speech blocks in the actual audio
    (energy/RMS-based), falling back to a proportional character-count
    split -- logged when it happens -- if alignment fails outright or
    produces an implausible result (fewer detected speech blocks than
    script lines, which means silence/pause detection couldn't tell the
    lines apart and any alignment built on it would be worse than an even
    split, not better).
    """
    try:
        import soundfile as sf

        wav_data, sr = sf.read(str(voice_audio_path))
        if wav_data.ndim > 1:
            wav_data = wav_data[:, 0]

        blocks, total_dur = _rms_speech_blocks(wav_data, sr)

        if len(blocks) < len(split_items):
            print(
                f"⚠️ {log_prefix} พบช่วงเสียงพูด {len(blocks)} ช่วง แต่มี {len(split_items)} บรรทัด "
                f"({log_prefix} detected fewer speech blocks than script lines) — falling back to proportional split"
            )
            return _proportional_fallback_cues(split_items, total_duration)

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

        cues: List[Dict[str, Any]] = []
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
        return cues
    except Exception as align_err:
        print(f"⚠️ {log_prefix} Acoustic alignment fallback ({align_err}) — using proportional fallback")
        return _proportional_fallback_cues(split_items, total_duration)


def _fold_cues_by_line_idx(
    cues: List[Dict[str, Any]],
    original_lines: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Folds a clause-level cue list back into one cue per script line, using
    the `line_idx` tag `VoiceEngine.segment_into_clauses` stamps on every
    clause (`scripts/voice_engine.py`) -- the plain edge_tts path
    (`VoiceEngine.generate_voiceover`) splits each script line into several
    smart-clause cues internally, so its raw `cues` list is NOT 1:1 with
    script lines despite being built from `script_data["lines"]`. Dict
    insertion order (Python 3.7+) keeps groups in the order their line_idx
    first appears, so a line's clauses stay contiguous even though nothing
    here assumes line_idx values are a dense 0..n-1 range.
    """
    groups: Dict[int, List[Dict[str, Any]]] = {}
    for cue in cues:
        key = cue.get("line_idx")
        if key is None:
            continue
        groups.setdefault(key, []).append(cue)

    folded: List[Dict[str, Any]] = []
    for line_idx, group in groups.items():
        line = original_lines[line_idx] if 0 <= line_idx < len(original_lines) else {}
        folded.append({
            "id": line_idx + 1,
            "start": group[0]["start"],
            "end": group[-1]["end"],
            "text": line.get("text", "") or group[0].get("text", ""),
            "sfx": line.get("sfx"),
            "on_screen": line.get("on_screen", ""),
        })
    return folded


def _fold_cues_to_lines(
    cues: List[Dict[str, Any]],
    items_per_line: List[int],
    original_lines: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Folds a clause-level cue list (possibly several cues per script line --
    e.g. gemini_tts's smart-clause splitting, `items_per_line[i] > 1`) back
    into exactly one cue per original script line. Each folded cue spans its
    first clause's start to its last clause's end, so the resulting
    line-level boundary is pixel-identical to the clause-level cues it's
    derived from rather than a re-estimate. This is what
    `scripts/shot_list_builder.py`'s per-beat shot list needs: one entry per
    script line, not per subtitle-burst clause.
    """
    folded: List[Dict[str, Any]] = []
    pos = 0
    for line_idx, count in enumerate(items_per_line):
        group = cues[pos:pos + count]
        pos += count
        if not group:
            continue
        line = original_lines[line_idx] if line_idx < len(original_lines) else {}
        folded.append({
            "id": line_idx + 1,
            "start": group[0]["start"],
            "end": group[-1]["end"],
            "text": line.get("text", "") or " ".join(c.get("text", "") for c in group),
            "sfx": line.get("sfx"),
            "on_screen": line.get("on_screen", ""),
        })
    return folded


class VoiceStage:
    """Synthesizes or processes voiceover audio and derives timing cues."""

    @classmethod
    def run(cls, ctx: PipelineContext) -> None:
        # Gemini TTS is the safe/default engine.  Older manifests and callers
        # can still explicitly request Edge-TTS, but an omitted/blank value
        # must never silently enter the legacy branch.
        if ctx.voice_engine_type is None or (
            isinstance(ctx.voice_engine_type, str) and not ctx.voice_engine_type.strip()
        ):
            ctx.voice_engine_type = "gemini_tts"
            print("[VoiceStage] voice_engine_type ว่าง — ใช้ Gemini TTS เป็นค่าเริ่มต้น")
        elif ctx.voice_engine_type == "edge_tts":
            print("⚠️ [VoiceStage] ใช้ Edge-TTS ตามที่ระบุโดยผู้ใช้; จะไม่ใช้เป็น fallback ของ Gemini TTS")

        cues: List[Dict[str, Any]] = []
        beat_cues: List[Dict[str, Any]] = []
        voice_engine_used = ctx.voice_engine_type
        script_data = ctx.script_data or {"lines": []}

        # Check for Shot List audio reuse (SSOT) -- only for real video projects,
        # not when shot_list_builder itself is running.
        is_shot_list_job = (ctx.project_name or "").startswith("_ShotLists_")
        shot_list_record = None
        if not is_shot_list_job and not ctx.human_voice_audio_path:
            p_id = ctx.product_id
            a_id = ctx.angle_id
            if not (p_id and a_id) and ctx.shot_list_id and ":" in ctx.shot_list_id:
                parts = ctx.shot_list_id.split(":", 1)
                p_id, a_id = parts[0], parts[1]
            if p_id and a_id:
                try:
                    from scripts.shot_lists_store import ShotListsStore
                    rec = ShotListsStore.get(p_id, a_id)
                    if rec and rec.get("voice_audio_path"):
                        audio_p = Path(rec["voice_audio_path"])
                        if audio_p.exists() and audio_p.stat().st_size > 0:
                            recorded_preset = (rec.get("voice_params") or {}).get("voice_preset")
                            recorded_engine = (rec.get("voice_params") or {}).get("voice_engine_type")
                            # If the caller explicitly requested a different voice preset in Studio,
                            # synthesize the newly requested voice instead of forcing the old one.
                            # When voice_preset matches (or both are default/omitted), reuse the shot list audio.
                            preset_matches = not ctx.voice_preset or not recorded_preset or (ctx.voice_preset == recorded_preset)
                            engine_matches = (
                                not ctx.voice_engine_type
                                or not recorded_engine
                                or (ctx.voice_engine_type == recorded_engine)
                                or (preset_matches and bool(recorded_preset))
                            )
                            if preset_matches and engine_matches:
                                shot_list_record = rec
                            else:
                                print(f"[VoiceStage] Voice preset requested ({ctx.voice_preset}) differs from shot list ({recorded_preset}) -- will synthesize newly chosen voice.")
                except Exception as e:
                    print(f"[VoiceStage] Note: Could not check shot list store: {e}")

        if not ctx.should_run("voice"):
            if not ctx.manifest:
                raise ValueError("Cannot reuse voice without manifest")
            voice_audio_path = ctx.reuse("voice_audio", "เสียงพากย์")
            cues = ctx.manifest["cues"]
            beat_cues = ctx.manifest.get("beat_cues", cues)
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

            total_duration = _probe_audio_duration(voice_audio_path)

            lines_list = script_data["lines"]
            split_items = [
                {
                    "text": item["text"],
                    "sfx": item.get("sfx"),
                    "on_screen": item.get("on_screen", ""),
                }
                for item in lines_list
            ]
            cues = _rms_aligned_cues(
                voice_audio_path=voice_audio_path,
                split_items=split_items,
                total_duration=total_duration,
                log_prefix="[Human Voice]",
            )
            beat_cues = cues  # split_items above is already 1:1 with script lines
            print(f"   Human voice loaded! Duration: {total_duration:.2f}s, Cues synced: {len(cues)}")

        elif shot_list_record:
            voice_audio_path = ctx.out_path("voiceover", ".wav")
            ctx.notify("♻️ [2/5] ใช้เสียงพากย์จริงจากแผนถ่าย (ประหยัดเวลาและโควต้า)...", 0.25)
            src_audio = Path(shot_list_record["voice_audio_path"])
            shutil.copy2(str(src_audio), str(voice_audio_path))
            total_duration = shot_list_record.get("total_duration") or _probe_audio_duration(voice_audio_path)
            cues = shot_list_record.get("cues") or shot_list_record.get("beat_cues") or []
            beat_cues = shot_list_record.get("beat_cues") or cues
            voice_engine_used = (shot_list_record.get("voice_params") or {}).get("voice_engine_type") or "gemini_tts"
            print(f"\n♻️  [2/5] Reusing voiceover from Shot List: {src_audio.name} ({total_duration:.2f}s) - zero re-synthesis needed!")

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
                            ad_tone=ctx.ad_tone or "commercial_hype",
                            speed=speed_val
                        )
                        last_tts_error = None
                        break
                    except Exception as tts_err:
                        last_tts_error = tts_err
                        # A quota hit is the user's own daily cap -- it will
                        # not clear a second later, so retrying just wastes
                        # time before falling back the same way anyway.
                        if attempt == 0 and not is_quota_error(tts_err):
                            print(f"⚠️ [Gemini Flash TTS] ล้มเหลว ({tts_err}) — ลองใหม่อีกครั้ง...")
                            time.sleep(1.0)
                        elif is_quota_error(tts_err):
                            break
                if last_tts_error is not None:
                    raise last_tts_error

                total_duration = _probe_audio_duration(voice_audio_path)

                lines_list = script_data["lines"]
                split_items = []
                items_per_line: List[int] = []
                for item in lines_list:
                    cl_texts = SubtitleEngine.split_into_smart_clauses(item.get("text", "")) or [item.get("text", "")]
                    items_per_line.append(len(cl_texts))
                    for ci, cl in enumerate(cl_texts):
                        split_items.append({
                            "text": cl,
                            "sfx": item.get("sfx") if ci == 0 else None,
                            "on_screen": item.get("on_screen", "") if ci == 0 else ""
                        })

                cues = _rms_aligned_cues(
                    voice_audio_path=voice_audio_path,
                    split_items=split_items,
                    total_duration=total_duration,
                    log_prefix="[Gemini Flash TTS]",
                )
                # cues here is clause-level (gemini_tts split each line into
                # smart clauses above) -- fold back to one cue per script
                # line for beat_cues, since that's the granularity a shot
                # list is built at, not the subtitle-burst clause level.
                beat_cues = _fold_cues_to_lines(cues, items_per_line, lines_list)
                print(f"   Gemini Flash TTS voice generated! Duration: {total_duration:.2f}s, Cues: {len(cues)}")
            except Exception as gemini_err:
                print(f"❌ [Gemini Flash TTS] Failed ({gemini_err}) — HALTING (Strictly no fallback to Edge-TTS as configured)")
                if is_quota_error(gemini_err):
                    ctx.notify("❌ เกินโควต้าการใช้งาน AI ต่อวันแล้ว (หยุดการทำงาน — ไม่สลับไป Edge-TTS)", 0.30)
                    raise gemini_err

                if isinstance(gemini_err, AppError):
                    sugg = f" — {gemini_err.suggestion_th}" if gemini_err.suggestion_th else ""
                    ctx.notify(f"❌ {gemini_err.message_th}{sugg}", 0.30)
                    raise gemini_err

                from scripts.error_handler import classify_exception
                app_err = classify_exception(gemini_err, project_name=ctx.project_name)
                sugg = f" — {app_err.suggestion_th}" if app_err.suggestion_th else ""
                ctx.notify(f"❌ {app_err.message_th}{sugg}", 0.30)
                raise app_err
        elif ctx.voice_engine_type == "edge_tts":
            voice_engine_used = "edge_tts"
            voice_audio_path = ctx.out_path("voiceover", ".wav")
            ctx.notify("🗣️ [2/5] กำลังสังเคราะห์เสียง Edge-TTS (โหมดเดิม)...", 0.25)
            print("\n⚠️ [2/5] Synthesizing Voice via Legacy Edge-TTS (explicitly requested)...")
            voice_res = VoiceEngine.generate_voiceover(
                text_or_lines=script_data["lines"],
                output_audio_path=str(voice_audio_path),
                voice=ctx.voice,
                rate=ctx.voice_rate
            )
            cues = voice_res["cues"]
            beat_cues = _fold_cues_by_line_idx(cues, script_data["lines"])
            total_duration = voice_res["duration"]
            print(f"   Edge-TTS voice generated! Duration: {total_duration:.2f}s, Cues: {len(cues)}")
        else:
            raise ValueError(f"Unknown or unsupported voice engine: {ctx.voice_engine_type}")

        ctx.voice_audio_path = voice_audio_path
        ctx.cues = cues
        ctx.beat_cues = beat_cues
        ctx.total_duration = total_duration
        ctx.voice_engine_used = voice_engine_used
