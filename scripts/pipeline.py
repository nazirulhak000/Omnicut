import os
import sys
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

from scripts.config import (
    BASE_DIR, INBOX_DIR, RAW_DIR, PROJECTS_DIR, EXPORTS_DIR, LUTS_DIR,
    DEFAULT_VOICE, DEFAULT_VOICE_RATE, DEFAULT_VOICE_PITCH
)
from scripts.script_generator import ScriptGenerator
from scripts.voice_engine import VoiceEngine
from scripts.subtitle_engine import SubtitleEngine
from scripts.sfx_manager import SFXManager
from scripts.video_editor import VideoEditor
from scripts.image_motion_engine import ImageMotionEngine
from scripts.gemini_vision_matcher import GeminiVisionMatcher
from scripts.beat_sync import BeatSync
from scripts.script_tone_analyzer import ScriptToneAnalyzer
from scripts.motion_analyzer import MotionAnalyzer
from scripts.project_manifest import ProjectManifest
from scripts.it_angles import LOOK_PRESETS, BGM_MOOD_MAP, DEFAULT_BGM

class TikTokAutoCutterPipeline:
    """Main pipeline to run full automated OmniCut Pro Studio video creation."""

    @classmethod
    def run(
        cls,
        product_name: str,
        raw_video_path: str,
        project_name: Optional[str] = None,
        key_features: str = "แม่เหล็กแรงดูดสูง เสียบง่าย ชาร์จเร็ว ไม่ทำร้ายแบต",
        pain_point: str = "สายชาร์จพังง่าย เสียบยากในที่มืด",
        price_deal: str = "ลดพิเศษวันนี้",
        custom_script: Optional[str] = None,
        script_overlays: Optional[List[str]] = None,
        voice: str = DEFAULT_VOICE,
        voice_rate: str = DEFAULT_VOICE_RATE,
        voice_engine_type: str = "edge_tts",
        voice_preset: Optional[str] = "gemini_puck_male_hype",
        ad_tone: str = "commercial_premium",
        human_voice_audio_path: Optional[str] = None,
        hook_brand: Optional[str] = None,
        hook_model: Optional[str] = None,
        hook_label: Optional[str] = None,
        hook_duration: float = 3.0,
        hook_motion: Optional[Dict[str, Any]] = None,
        hook_colors: Optional[Dict[str, str]] = None,
        font_name: str = "IBMPlex",
        bilingual_subtitles: bool = True,
        use_ai_vision: bool = True,
        sticker_path: Optional[str] = None,
        bgm_name: Optional[str] = None,
        bgm_volume: Optional[float] = None,
        bgm_ducking: bool = True,
        lut_name: Optional[str] = None,
        lut_intensity: float = 1.0,
        clip_list: Optional[List[Dict[str, any]]] = None,
        transitions: Optional[List[str]] = None,
        export_mp4: bool = True,
        export_preset: str = "post",
        product_id: Optional[str] = None,
        angle_id: Optional[str] = None,
        caption_position: str = "bottom",
        caption_color: Optional[str] = None,
        caption_scale: float = 1.0,
        text_overlays: Optional[List[Dict[str, any]]] = None,
        sticker_position: str = "top_right",
        sticker_scale: float = 1.0,
        resume_from: Optional[str] = None,
        product_meta: Optional[Dict[str, any]] = None,
        angle_meta: Optional[Dict[str, any]] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, any]:
        """
        Executes all pipeline steps and returns paths to artifacts.

        Pass `resume_from` ("voice" / "subtitles" / "video") to rebuild only that
        stage and everything after it, reusing earlier artifacts recorded in the
        project manifest. A full run leaves `resume_from` as None.
        """
        def _notify(msg: str, progress: float):
            if progress_callback:
                try:
                    progress_callback(msg, progress)
                except Exception:
                    pass

        raw_video = None
        if raw_video_path:
            p = Path(raw_video_path)
            if p.exists():
                raw_video = p.resolve()
            elif (BASE_DIR / raw_video_path).exists():
                raw_video = (BASE_DIR / raw_video_path).resolve()
            elif (RAW_DIR / p.name).exists():
                raw_video = (RAW_DIR / p.name).resolve()
            elif (INBOX_DIR / p.name).exists():
                raw_video = (INBOX_DIR / p.name).resolve()
            else:
                # Search recursively in product folders under RAW_DIR and INBOX_DIR
                matched_raw = list(RAW_DIR.glob(f"**/{p.name}"))
                matched_inbox = list(INBOX_DIR.glob(f"**/{p.name}"))
                if matched_raw:
                    raw_video = matched_raw[0].resolve()
                elif matched_inbox:
                    raw_video = matched_inbox[0].resolve()
                else:
                    raw_video = p.resolve()
        
        # Check if raw_video_path is an image or directory of images
        image_extensions = ('.jpg', '.jpeg', '.png', '.webp')
        is_image_source = False
        image_files = []

        if raw_video and raw_video.is_dir():
            image_files = [str(f) for f in raw_video.iterdir() if f.suffix.lower() in image_extensions]
            if image_files:
                is_image_source = True
        elif raw_video and raw_video.is_file() and raw_video.suffix.lower() in image_extensions:
            is_image_source = True
            image_files = [str(raw_video)]
        elif not raw_video or not raw_video.exists():
            # Check if there are product images in INBOX_DIR/product_images or INBOX_DIR
            candidate_imgs = list((INBOX_DIR / "product_images").glob("**/*.*")) + list(INBOX_DIR.glob("*.*"))
            valid_imgs = [str(f) for f in candidate_imgs if f.suffix.lower() in image_extensions]
            if valid_imgs:
                is_image_source = True
                image_files = valid_imgs[:6]
            else:
                raise FileNotFoundError(f"ไม่พบไฟล์วิดีโอดิบหรือรูปสินค้า: '{raw_video_path}' กรุณาตรวจสอบตำแหน่งไฟล์")

        # Pre-flight validation: check video file integrity (reject 0-byte or truncated files)
        if raw_video and raw_video.is_file() and not is_image_source:
            if raw_video.stat().st_size < 1024:
                raise ValueError(f"ไฟล์วิดีโอ '{raw_video.name}' มีขนาด 0 bytes หรือเสียหาย กรุณาตรวจสอบไฟล์ต้นฉบับ")

        if clip_list:
            for c_idx, c_item in enumerate(clip_list):
                c_src = c_item.get("source_path")
                if c_src:
                    c_path = Path(c_src)
                    if not c_path.is_absolute():
                        c_path = BASE_DIR / c_src
                    if c_path.exists() and c_path.is_file() and c_path.stat().st_size < 1024:
                        raise ValueError(f"คลิปที่ {c_idx + 1} ('{c_path.name}') มีขนาด 0 bytes หรือเสียหาย")

        # Determine Project Name
        if not project_name:
            clean_name = "".join(c for c in product_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
            project_name = f"TikTok_{clean_name}"

        project_dir = PROJECTS_DIR / project_name
        project_dir.mkdir(parents=True, exist_ok=True)

        is_reroll = bool(resume_from)
        manifest = ProjectManifest.require(project_name) if is_reroll else None

        def _out_path(stem: str, suffix: str) -> Path:
            """Fresh numbered file when re-rolling, so an earlier take survives."""
            if is_reroll:
                return ProjectManifest.versioned_path(project_name, stem, suffix)
            return project_dir / f"{stem}{suffix}"

        def _reuse(key: str, label: str) -> Path:
            existing = ProjectManifest.artifact_path(manifest, key)
            if not existing:
                raise FileNotFoundError(
                    f"สุ่มใหม่ไม่ได้ — ไม่พบไฟล์ {label} ของรอบก่อน ต้อง render เต็มรอบใหม่"
                )
            return existing

        print(f"\n=======================================================")
        print(f"🎬 Starting OmniCut Pro Studio for: {product_name}")
        print(f"📁 Project Folder: {project_dir}")
        if is_reroll:
            print(f"♻️  Re-roll from stage: {resume_from}")
        print(f"=======================================================\n")

        # 1. Script & Lines Setup
        if ProjectManifest.should_run("script", resume_from):
            _notify("🧠 [1/5] วิเคราะห์สินค้าและจัดเตรียมสคริปต์ TikTok...", 0.10)
            print("🧠 [1/5] Setting up TikTok Script & Cues...")
            if custom_script:
                overlays = script_overlays or []
                lines = [
                    {
                        "text": l.strip(),
                        "sfx": "pop" if i > 0 else "whoosh",
                        # Spec-bar text for this line, e.g. "20W PD" -- see
                        # subtitle_engine.py's SpecBar style. Index-aligned with
                        # the AI script's `lines`, which is the same array the
                        # frontend split into custom_script.
                        "on_screen": (overlays[i].strip() if i < len(overlays) else "")
                    }
                    for i, l in enumerate(custom_script.strip().split("\n"))
                    if l.strip()
                ]
                if lines:
                    lines[-1]["sfx"] = "cash"
                script_data = {
                    "hook": lines[0]["text"] if lines else product_name,
                    "lines": lines,
                    "full_text": "\n".join([l["text"] for l in lines])
                }
            else:
                # 1.1 Try AIBridge (Antigravity Pro / Gemini) for dynamic human-like script
                ai_script = None
                from scripts.ai_bridge import AIBridge
                if AIBridge.is_available():
                    try:
                        _notify("🧠 [1/5] ให้ AI Pro วิเคราะห์จุดขายและเขียนบทพากย์พร้อมแปล...", 0.12)
                        print("✨ [1/5] Generating dynamic script via AIBridge...")
                        ai_ctx = {
                            "product_name": product_name,
                            "angle_title": angle_meta.get("title", "รีวิวสินค้า") if angle_meta else "รีวิวสินค้าสุดปัง",
                            "hook": angle_meta.get("hook", "") if angle_meta else f"ใครหา {product_name} อยู่ดูคลิปนี้เลย",
                            "specs": [{"label": "จุดเด่น", "value": key_features[:60]}],
                            "price_deal": price_deal
                        }
                        ai_resp = AIBridge.generate("script", ai_ctx)
                        ai_lines = ai_resp.get("lines", [])
                        if ai_lines:
                            ai_script = {
                                "hook": ai_resp.get("hook_title") or ai_lines[0].get("text", product_name),
                                "lines": ai_lines,
                                "full_text": "\n".join([l.get("text", "") for l in ai_lines])
                            }
                            print(f"✨ [Pipeline] Dynamic script ready! ({len(ai_lines)} lines)")
                    except Exception as ai_err:
                        print(f"⚠️ [Pipeline] AI script gen failed ({ai_err}) — falling back to ScriptGenerator...")

                if ai_script:
                    script_data = ai_script
                else:
                    script_data = ScriptGenerator.generate(
                        product_name=product_name,
                        key_features=key_features,
                        pain_point=pain_point,
                        price_deal=price_deal
                    )
        else:
            script_data = manifest["script_data"]
            print(f"♻️  [1/5] Reusing script ({len(script_data.get('lines', []))} lines)")

        # 2. Voice Handling (Human Voice vs Gemini Flash TTS vs Edge-TTS)
        cues = []

        if not ProjectManifest.should_run("voice", resume_from):
            voice_audio_path = _reuse("voice_audio", "เสียงพากย์")
            cues = manifest["cues"]
            total_duration = manifest["total_duration"]
            print(f"♻️  [2/5] Reusing voiceover: {voice_audio_path.name} ({total_duration:.2f}s)")

        elif human_voice_audio_path and Path(human_voice_audio_path).exists():
            voice_audio_path = _out_path("voiceover", ".wav")
            _notify("🎙️ [2/5] โหลดและประมวลผลไฟล์เสียงคนพูดจริง...", 0.25)
            print(f"\n🎙️ [2/5] Using REAL HUMAN VOICE: {human_voice_audio_path}")
            human_src = Path(human_voice_audio_path).resolve()
            import subprocess
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
        elif voice_engine_type == "gemini_tts":
            _notify("⚡ [2/5] กำลังสังเคราะห์เสียงพากย์ด้วย Google Gemini Flash TTS...", 0.25)
            print("\n⚡ [2/5] Synthesizing Voice via Google Gemini Flash TTS...")
            from scripts.gemini_tts_engine import GeminiFlashTTSEngine
            import subprocess

            voice_audio_path = _out_path("voiceover", ".wav")
            gemini_voice = GeminiFlashTTSEngine.resolve_voice(preset=voice_preset, gender=voice)

            speed_val = 1.15
            if voice_rate:
                try:
                    num = int(voice_rate.replace("%", "").replace("+", ""))
                    speed_val = 1.0 + (num / 100.0)
                except Exception:
                    pass

            full_script_text = script_data.get("full_text") or "\n".join([l["text"] for l in script_data["lines"]])
            try:
                GeminiFlashTTSEngine.generate_speech(
                    text=full_script_text,
                    output_path=str(voice_audio_path),
                    voice_name=gemini_voice,
                    ad_tone=ad_tone or "commercial_premium",
                    speed=speed_val
                )

                probe_cmd = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(voice_audio_path)
                ]
                probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
                total_duration = float(probe_res.stdout.strip()) if probe_res.stdout.strip() else 15.0

                lines_list = script_data["lines"]
                # Split raw lines into smart clauses for frame-accurate timing
                split_items = []
                for item in lines_list:
                    cl_texts = SubtitleEngine.split_into_smart_clauses(item.get("text", ""))
                    for ci, cl in enumerate(cl_texts):
                        split_items.append({
                            "text": cl,
                            "sfx": item.get("sfx") if ci == 0 else None,
                            "on_screen": item.get("on_screen", "") if ci == 0 else ""
                        })
                
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
                print(f"⚠️ [Gemini Flash TTS] Failed ({gemini_err}) — falling back to Edge-TTS...")
                _notify("⚠️ Gemini TTS ขัดข้อง สลับไปใช้ Edge-TTS สำรอง...", 0.30)
                voice_res = VoiceEngine.generate_voiceover(
                    text_or_lines=script_data["lines"],
                    output_audio_path=str(voice_audio_path),
                    voice=voice,
                    rate=voice_rate
                )
                cues = voice_res["cues"]
                total_duration = voice_res["duration"]
        else:
            voice_audio_path = _out_path("voiceover", ".wav")
            _notify("🗣️ [2/5] กำลังสังเคราะห์เสียง AI พากย์เร็ว TikTok และจับเวลา...", 0.25)
            print("\n🗣️ [2/5] Synthesizing AI Thai Voiceover & Timestamps...")
            voice_res = VoiceEngine.generate_voiceover(
                text_or_lines=script_data["lines"],
                output_audio_path=str(voice_audio_path),
                voice=voice,
                rate=voice_rate
            )
            cues = voice_res["cues"]
            total_duration = voice_res["duration"]
            print(f"   Voice generated! Duration: {total_duration:.2f}s, Cues: {len(cues)}")

        # 3. Subtitles Generation (Rapid-fire 2-4 word bursts)
        #
        # `gradient_hook_duration` (None when there's no hook banner at all)
        # is threaded down to assemble_tiktok_video below so its gradient
        # backdrop only shows while the banner text is actually on screen --
        # it must survive both branches here, not just the regenerate path,
        # or a video-only reroll loses the gradient even though the reused
        # .ass still burns the banner.
        gradient_hook_duration = None
        if ProjectManifest.should_run("subtitles", resume_from):
            _notify("💬 [3/5] กำลังสร้างซับไตเติล TikTok เคลื่อนไหว (Kanit-Black 86pt)...", 0.50)
            print(f"\n💬 [3/5] Generating TikTok Animated Subtitles (.ass with {font_name} font & 3-word bursts)...")
            ass_path = _out_path("subtitles", ".ass")
            # No caller supplies any of the three -- fall back to product_name
            # as the brand line alone, same as the old single-field default,
            # so the banner never silently disappears on a fresh 1-click run.
            effective_hook_brand = hook_brand or (product_name if not (hook_model or hook_label) else "")
            # Hold time scales with how long the banner actually takes to
            # read (~11 chars/sec, the same fast cadence as the TikTok voice
            # rate) instead of one flat 3s for every title -- a 6-char hook
            # doesn't need the same hold as a 40-char one. A caller that
            # explicitly moved hook_duration away from the 3.0 default is
            # respected as-is.
            banner_combined_len = len(" ".join(filter(None, [effective_hook_brand, hook_model, hook_label])))
            if hook_duration is not None and abs(float(hook_duration) - 3.0) > 0.01:
                effective_hook_duration = float(hook_duration)
            else:
                # Floor raised from 1.6 -> 2.0: the staggered elastic-bounce
                # entrance (brand/model/label settle by ~750ms) plus at least
                # one pulse cycle plus the 150ms exit fade needs more room
                # than the old flat 120ms pop-in ever did.
                effective_hook_duration = max(2.0, min(banner_combined_len / 11.0 + 0.6, 5.0))
            effective_hook_duration = min(effective_hook_duration, total_duration)
            if effective_hook_brand or hook_model or hook_label:
                gradient_hook_duration = effective_hook_duration
            effective_text_overlays = text_overlays if text_overlays is not None else (
                (manifest.get("text_overlays") if manifest else None) or
                ((manifest.get("render_params") or {}).get("text_overlays") if manifest else None)
            )
            _, micro_cues = SubtitleEngine.generate_ass(
                cues=cues,
                output_ass_path=str(ass_path),
                font_name=font_name,
                hook_brand=effective_hook_brand,
                hook_model=hook_model,
                hook_label=hook_label,
                hook_duration=effective_hook_duration,
                hook_motion=hook_motion,
                hook_colors=hook_colors,
                bilingual=bilingual_subtitles,
                caption_position=caption_position,
                caption_color=caption_color,
                caption_scale=caption_scale,
                text_overlays=effective_text_overlays
            )
            # Sync translations back to main cues
            cues = micro_cues
            print(f"   Subtitles created: {ass_path} ({len(micro_cues)} micro-bursts)")
        else:
            ass_path = _reuse("subtitles_ass", "ไฟล์ซับไตเติล")
            micro_cues = manifest["micro_cues"]
            saved_params = (manifest.get("render_params") or {}) if manifest else {}
            if saved_params.get("hook_brand") or saved_params.get("hook_model") or saved_params.get("hook_label"):
                gradient_hook_duration = float(saved_params.get("hook_duration") or 3.0)
            print(f"♻️  [3/5] Reusing subtitles: {ass_path.name} ({len(micro_cues)} micro-bursts)")

        # Auto-pick BGM by angle mood when the caller didn't name one --
        # falls back to DEFAULT_BGM for an unmapped/missing angle_key, never
        # to SFXManager's own hardcoded default silently. Computed once, up
        # here, so the mix step below and the beat-detection step further
        # down (which needs to know which exact file will play) always agree
        # on the same track -- resolving it twice risked them disagreeing on
        # a reroll where only one of the two runs.
        effective_bgm_name = bgm_name
        if not effective_bgm_name:
            angle_key = angle_meta.get("angle_key", "") if angle_meta else ""
            effective_bgm_name = BGM_MOOD_MAP.get(angle_key, DEFAULT_BGM)

        # 4. SFX & BGM Audio Mixing
        #
        # micro_cues are derived from `cues` alone — font, bilingual and
        # hook_title never move a timing — so the mix only has to be rebuilt
        # when the voice itself was regenerated. That is what makes a hook or
        # subtitle re-roll cheap.
        if ProjectManifest.should_run("mix", resume_from):
            _notify("🎵 [4/5] กำลังมิกซ์เสียง Voice + เอฟเฟกต์ SFX (Boom/Pop/Cash) + BGM...", 0.65)
            print("\n🎵 [4/5] Mixing Audio (Voice + Boom/Whoosh/Pop/Ding/Cash SFX + Upbeat BGM)...")
            mixed_audio_path = _out_path("mixed_audio", ".wav")
            mix_kwargs = {"bgm_name": effective_bgm_name} if effective_bgm_name else {}
            if bgm_volume is not None:
                mix_kwargs["bgm_vol"] = min(1.0, max(0.0, float(bgm_volume)))
            if bgm_ducking:
                mix_kwargs["bgm_ducking"] = True
            SFXManager.mix_audio_track(
                voice_audio_path=str(voice_audio_path),
                cues=micro_cues,
                total_duration=total_duration,
                output_audio_path=str(mixed_audio_path),
                **mix_kwargs
            )
            print(f"   Audio mixed: {mixed_audio_path}")
        else:
            mixed_audio_path = _reuse("mixed_audio", "เสียงที่มิกซ์แล้ว")
            print(f"♻️  [4/5] Reusing mixed audio: {mixed_audio_path.name}")

        result_paths = {
            "project_name": project_name,
            "project_dir": str(project_dir),
            "script": script_data,
            "voice_audio": str(voice_audio_path),
            "mixed_audio": str(mixed_audio_path),
            "subtitles_ass": str(ass_path),
            "duration": total_duration,
            "mp4_video": None,
        }

        # If source is still images, generate 9:16 Ken-Burns motion video footage first
        if is_image_source and image_files:
            _notify("🖼️ [Image Motion] สร้างวิดีโอ 9:16 Motion Slideshow จากรูปภาพสินค้า...", 0.70)
            print(f"\n🖼️ [Image Motion] Generating 9:16 Motion Slideshow from {len(image_files)} product images...")
            motion_raw_path = project_dir / "image_motion_footage.mp4"
            ImageMotionEngine.generate_motion_video_from_images(
                image_paths=image_files,
                cues=cues,
                total_duration=total_duration,
                output_video_path=str(motion_raw_path),
                project_dir=project_dir
            )
            raw_video = motion_raw_path
            use_ai_vision = False # Image motion is already timed to cues

        # 5. Direct Video Render (MP4) with Optional Gemini Vision Scene Matching
        import datetime
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        raw_duration = 60.0
        if raw_video:
            try:
                raw_info = VideoEditor.get_media_info(str(raw_video))
                raw_duration = float(raw_info.get("duration", 60.0))
            except Exception:
                raw_duration = 60.0

        # Check if caller already provided multi-shot clips (e.g. from Web Editor timeline)
        has_manual_multi_clips = bool(clip_list and len(clip_list) > 1)
        actual_clip_list = clip_list if has_manual_multi_clips else None

        ai_matched_shots = None
        # ONLY invoke AI Vision if we need to auto-generate the clip list from scratch!
        # If the user already has clips on the timeline (e.g. editing in Editor), skip AI Vision completely.
        if not actual_clip_list and raw_video and use_ai_vision and os.environ.get("GEMINI_API_KEY"):
            # Check local cache first: if already analyzed, reuse instantly without showing "AI กำลังดู"
            cached_shots = GeminiVisionMatcher.get_cached_matches(str(raw_video), micro_cues)
            if cached_shots:
                print(f"   ⚡ [AI Vision] Reusing {len(cached_shots)} cached scene matches (Instant 0s)")
                ai_matched_shots = cached_shots
            else:
                _notify("👁️ [AI Vision] ให้ Gemini 2.5 Flash ดูคลิปและเลือกฉากที่ตรงกับสคริปต์ (ครั้งแรก)...", 0.76)
                print("\n👁️ [AI Vision] Gemini 2.5 Flash is analyzing raw footage scenes (first time)...")
                try:
                    ai_matched_shots = GeminiVisionMatcher.match_script_to_video(
                        raw_video_path=str(raw_video),
                        cues=micro_cues,
                        raw_duration=raw_duration
                    )
                    _notify("👁️ [AI Vision] จับคู่ฉากสมบูรณ์ กำลังส่งต่อให้ขั้นตอนตัดต่อ...", 0.82)
                except Exception as e:
                    print(f"   ⚠️ AI Vision Matching skipped ({e}) — using rhythmic cuts.")
        
        # Punch-zoom pattern per angle (LOOK_PRESETS)
        shot_scales = LOOK_PRESETS.get(angle_meta.get("angle_key", "")) if angle_meta else None

        # Beat times for the chosen BGM track, used below to snap auto-cut
        # boundaries onto the music instead of leaving them purely
        # caption-timed. Best-effort: an unresolved BGM file or a missing
        # librosa install just means no snapping, never a failed render.
        beat_times: List[float] = []
        try:
            resolved_bgm_path = SFXManager.resolve_bgm_path(effective_bgm_name)
            if resolved_bgm_path:
                beat_times = BeatSync.get_beat_times(resolved_bgm_path)
        except Exception:
            beat_times = []

        # Loudness envelope of the already-mixed track (voice+SFX+BGM) --
        # used below to punch the zoom in on whichever shot is actually loud
        # in the final mix, instead of guessing from caption text alone.
        # `energy_mean`/`energy_std` gate what counts as "loud": None means
        # no usable data (librosa missing, or a silent/too-short clip), and
        # every caller below must fall back to the text heuristic then.
        energy_times: List[float] = []
        energy_rms: List[float] = []
        energy_mean: Optional[float] = None
        energy_std: Optional[float] = None
        try:
            energy_times, energy_rms = BeatSync.get_rms_energy(mixed_audio_path)
            if energy_rms:
                energy_mean = sum(energy_rms) / len(energy_rms)
                variance = sum((r - energy_mean) ** 2 for r in energy_rms) / len(energy_rms)
                energy_std = variance ** 0.5
        except Exception:
            energy_times, energy_rms, energy_mean, energy_std = [], [], None, None
        energy_peak = max(energy_rms) if energy_rms else None

        # Frame-difference motion score of the raw footage -- used below to
        # bias cut boundaries away from mid-action frames and blended into
        # the zoom-emphasis signal alongside audio loudness. Best-effort:
        # missing opencv or a failed analysis just means no motion bias,
        # everything falls back to the audio/text-only signals already here.
        motion_times: List[float] = []
        motion_scores: List[float] = []
        try:
            if raw_video:
                motion_times, motion_scores = MotionAnalyzer.get_motion_scores(raw_video)
        except Exception:
            motion_times, motion_scores = [], []

        if not actual_clip_list and raw_video:
            try:
                # Use smart clause cues so video shots match the 1-Click rhythm & thought scenes
                active_cues = micro_cues if (micro_cues and len(micro_cues) > 0) else cues
                effective_shot_scales = shot_scales or [1.25, 1.0, 1.35, 1.05, 1.3, 1.0]
                shots = []
                if active_cues:
                    # J-Cut (Audio Lead-in): เสียงประโยคถัดไปดังขึ้นก่อนภาพตัดเปลี่ยน 150-180ms เพื่อความลื่นไหล
                    from scripts.config import J_CUT_OFFSET_SECONDS, MIN_SHOT_DURATION, MAX_SHOT_DURATION
                    n_cues = len(active_cues)
                    cut_points = [0.0]
                    for i in range(1, n_cues):
                        c_curr_start = float(active_cues[i].get("start", 0.0))
                        prev_dur = float(active_cues[i - 1].get("end", 0.0)) - float(active_cues[i - 1].get("start", 0.0))
                        curr_dur = float(active_cues[i].get("end", 0.0)) - float(active_cues[i].get("start", 0.0))
                        lead = min(J_CUT_OFFSET_SECONDS, prev_dur * 0.25, curr_dur * 0.25, 0.25)
                        cut_points.append(round(c_curr_start + lead, 3))
                    cut_points.append(round(total_duration, 3))

                    # Merge consecutive micro-cues into shots >= MIN_SHOT_DURATION:
                    # a 2-3 word caption burst is not a natural video cut on its
                    # own -- a human editor holds a shot for a beat even while
                    # the captions keep changing under it. This only slows the
                    # VIDEO crop cadence; subtitles still burn per-cue from
                    # `cues` untouched below, so caption rhythm is unaffected.
                    groups: List[List[int]] = []
                    current: List[int] = []
                    group_start = cut_points[0]
                    for i in range(n_cues):
                        tentative_dur = cut_points[i + 1] - group_start
                        if current and tentative_dur > MAX_SHOT_DURATION:
                            groups.append(current)
                            current = []
                            group_start = cut_points[i]
                        current.append(i)
                        held_dur = cut_points[i + 1] - group_start
                        if held_dur >= MIN_SHOT_DURATION and i < n_cues - 1:
                            groups.append(current)
                            current = []
                            group_start = cut_points[i + 1]
                    if current:
                        groups.append(current)

                    # The greedy pass above closes a group the instant it
                    # would exceed MAX_SHOT_DURATION, without regard for
                    # whether MIN_SHOT_DURATION was ever reached -- a long
                    # cue followed by a short one can leave that short one
                    # stranded below MIN if the *next* cue is also long
                    # enough to force another early close. Sweep once more
                    # and fold every under-MIN group into whichever neighbor
                    # absorbs it without blowing too far past MAX (prefer
                    # the previous group, matching the forward-leaning bias
                    # of the greedy pass itself). Every successful merge
                    # shrinks `groups` by one, so this always terminates; a
                    # group that fits neither neighbor (e.g. one cue already
                    # longer than the tolerance on its own) is left short --
                    # there's no other choice at that point.
                    MERGE_TOLERANCE = 1.15
                    changed = True
                    while changed:
                        changed = False
                        for gi, g in enumerate(groups):
                            dur = cut_points[g[-1] + 1] - cut_points[g[0]]
                            if dur >= MIN_SHOT_DURATION:
                                continue
                            if gi > 0:
                                prev = groups[gi - 1]
                                merged_dur = cut_points[g[-1] + 1] - cut_points[prev[0]]
                                if merged_dur <= MAX_SHOT_DURATION * MERGE_TOLERANCE:
                                    groups[gi - 1] = prev + g
                                    del groups[gi]
                                    changed = True
                                    break
                            if gi < len(groups) - 1:
                                nxt = groups[gi + 1]
                                merged_dur = cut_points[nxt[-1] + 1] - cut_points[g[0]]
                                if merged_dur <= MAX_SHOT_DURATION * MERGE_TOLERANCE:
                                    groups[gi] = g + nxt
                                    del groups[gi + 1]
                                    changed = True
                                    break

                    # Snap the internal shot boundaries first onto the
                    # nearest low-motion frame (a real editor doesn't cut
                    # mid-action), then onto the nearest BGM beat, so cuts
                    # land on a still moment AND the music instead of purely
                    # on caption timing. Voice and captions never move --
                    # only which exact frame a video cut happens on.
                    boundary_times = [cut_points[0]] + [cut_points[g[-1] + 1] for g in groups]
                    if motion_times:
                        MOTION_SNAP_TOLERANCE = 0.15
                        for b_idx in range(1, len(boundary_times) - 1):
                            trough = MotionAnalyzer.nearest_trough(
                                motion_times, motion_scores, boundary_times[b_idx], MOTION_SNAP_TOLERANCE
                            )
                            if trough is not None:
                                prev_b = boundary_times[b_idx - 1]
                                next_b = boundary_times[b_idx + 1]
                                if (trough - prev_b) >= MIN_SHOT_DURATION * 0.8 and (next_b - trough) >= MIN_SHOT_DURATION * 0.8:
                                    boundary_times[b_idx] = round(trough, 3)
                    if beat_times:
                        BEAT_SNAP_TOLERANCE = 0.15
                        for b_idx in range(1, len(boundary_times) - 1):
                            t = boundary_times[b_idx]
                            nearest = min(beat_times, key=lambda bt: abs(bt - t))
                            if abs(nearest - t) <= BEAT_SNAP_TOLERANCE:
                                prev_b = boundary_times[b_idx - 1]
                                next_b = boundary_times[b_idx + 1]
                                if (nearest - prev_b) >= MIN_SHOT_DURATION * 0.8 and (next_b - nearest) >= MIN_SHOT_DURATION * 0.8:
                                    boundary_times[b_idx] = round(nearest, 3)

                    emphasis_scale_idx = effective_shot_scales.index(max(effective_shot_scales))

                    # Semantic tone-shift signal from Gemini (one call for
                    # the whole render, not per boundary): "major" beats the
                    # gap/sentence heuristic below and gets a stronger
                    # transition -- a real topic change (pain -> solution,
                    # body -> CTA) reads as more than a pause. No API key or
                    # a failed call just returns [], and every boundary
                    # falls through to the heuristic exactly as before this
                    # existed.
                    group_texts = [
                        " ".join(str(active_cues[i].get("text", "")) for i in g).strip()
                        for g in groups
                    ]
                    tone_shifts = ScriptToneAnalyzer.classify_tone_shifts(group_texts)

                    auto_transitions = []
                    for g_idx, group in enumerate(groups):
                        v_start = boundary_times[g_idx]
                        v_end = boundary_times[g_idx + 1]
                        c_dur = max(0.2, v_end - v_start)
                        anchor_idx = group[0]
                        ai_shot = ai_matched_shots[anchor_idx] if ai_matched_shots and anchor_idx < len(ai_matched_shots) else None

                        # Content-aware zoom: blend how much is actually
                        # happening on screen (motion) with how loud this
                        # moment is in the final mix (audio energy) into one
                        # 0..1 "emphasis" score, then scale continuously
                        # between this shot's normal pattern zoom and the
                        # pattern's hardest push-in -- a real editor punches
                        # in *proportionally* to the beat/impact, not as an
                        # on/off switch. Falls back to the old text-keyword
                        # heuristic (a binary switch) only when neither
                        # motion nor audio-energy data is available at all.
                        motion_score = (
                            MotionAnalyzer.segment_mean_score(motion_times, motion_scores, v_start, v_end)
                            if motion_times else None
                        )
                        energy_score = None
                        if energy_peak and energy_rms:
                            seg_energy = BeatSync.segment_mean_energy(energy_times, energy_rms, v_start, v_end)
                            if seg_energy is not None:
                                energy_score = min(1.0, seg_energy / energy_peak)

                        if motion_score is not None and energy_score is not None:
                            emphasis_score = 0.6 * motion_score + 0.4 * energy_score
                        elif motion_score is not None:
                            emphasis_score = motion_score
                        elif energy_score is not None:
                            emphasis_score = energy_score
                        else:
                            emphasis_score = None

                        base_scale = effective_shot_scales[g_idx % len(effective_shot_scales)]
                        max_scale = effective_shot_scales[emphasis_scale_idx]

                        if ai_shot:
                            ai_start = float(ai_shot.get("start_time", 0.0))
                            ai_zoom = float(ai_shot.get("punch_zoom", base_scale))
                            scale = min(1.4, max(1.0, ai_zoom))
                            raw_offset = max(0.0, min(ai_start, max(0.0, raw_duration - c_dur - 0.2)))
                        else:
                            if emphasis_score is not None:
                                scale = base_scale + (max_scale - base_scale) * emphasis_score
                            else:
                                has_emphasis = any(
                                    active_cues[i].get("sfx") or "!" in str(active_cues[i].get("text", ""))
                                    or any(e in str(active_cues[i].get("text", "")) for e in ("⚠️", "❌", "⚡"))
                                    for i in group
                                )
                                scale = max_scale if has_emphasis else base_scale

                            # No AI Vision: bias the rhythmic fallback offset
                            # toward the highest-motion moment near its own
                            # target instead of a pure modulo walk, so at
                            # least the no-Vision path favors a real action
                            # beat over an arbitrary point in the footage.
                            target_offset = (g_idx * 3.5) % max(1.0, raw_duration - c_dur - 1.0)
                            raw_offset = target_offset
                            if motion_times:
                                window = 2.0
                                candidates = [
                                    (t, s) for t, s in zip(motion_times, motion_scores)
                                    if abs(t - target_offset) <= window and t + c_dur <= raw_duration
                                ]
                                if candidates:
                                    raw_offset = max(candidates, key=lambda ts: ts[1])[0]

                        shots.append({
                            "start": v_start,
                            "end": v_end,
                            "scale": scale,
                            "raw_offset": raw_offset
                        })

                        if g_idx > 0:
                            # Boundary between this shot and the previous one.
                            # Three tiers, cheapest signal first: a long pause
                            # (real breath / topic change) gets a slower
                            # dissolve; a short pause or a sentence ending
                            # gets a quick fade; anything else -- including a
                            # boundary that landed exactly on a music beat --
                            # stays a hard cut, which is still the default
                            # for most boundaries, not every one gets a
                            # transition.
                            prev_last_cue = active_cues[groups[g_idx - 1][-1]]
                            next_first_cue = active_cues[group[0]]
                            gap = float(next_first_cue.get("start", 0.0)) - float(prev_last_cue.get("end", 0.0))
                            prev_text = str(prev_last_cue.get("text", "")).strip()
                            sentence_end = prev_text.endswith((".", "!", "?", "ครับ", "ค่ะ", "นะคะ", "นะครับ"))
                            tone = tone_shifts[g_idx - 1] if (g_idx - 1) < len(tone_shifts) else "none"
                            if tone == "major":
                                wipe_type = "wipeleft" if g_idx % 2 == 0 else "circleopen"
                                auto_transitions.append({"type": wipe_type, "duration": 0.35})
                            elif gap > 0.6:
                                auto_transitions.append({"type": "dissolve", "duration": 0.3})
                            elif gap > 0.35 or sentence_end:
                                auto_transitions.append({"type": "fade", "duration": 0.2})
                            else:
                                auto_transitions.append("cut")

                    if not transitions and auto_transitions:
                        transitions = auto_transitions
                else:
                    curr_t = 0.0
                    shot_idx = 0
                    while curr_t < total_duration:
                        dur = 2.0
                        end_t = min(curr_t + dur, total_duration)
                        scale = effective_shot_scales[shot_idx % len(effective_shot_scales)]
                        raw_offset = (shot_idx * 3.5) % max(1.0, raw_duration - dur - 1.0)
                        shots.append({
                            "start": curr_t,
                            "end": end_t,
                            "scale": scale,
                            "raw_offset": raw_offset
                        })
                        curr_t = end_t
                        shot_idx += 1

                generated_clips = []
                for idx, shot in enumerate(shots):
                    s_dur = max(0.2, shot["end"] - shot["start"])
                    raw_start_offset = float(shot.get("raw_offset", 0.0))
                    trim_end = round(raw_start_offset + s_dur, 3)
                    generated_clips.append({
                        "id": f"clip_{idx}",
                        "source_path": str(raw_video),
                        "trim_start": round(raw_start_offset, 3),
                        "trim_end": trim_end,
                        "duration": round(s_dur, 3),
                        "speed": 1.0,
                        "zoom": round(float(shot.get("scale", 1.0)), 2),
                        "shot_index": idx,
                        "transition_in": "cut"
                    })
                actual_clip_list = generated_clips
            except Exception as shot_err:
                print(f"Warning: Failed to generate shot clip_list: {shot_err}")
                actual_clip_list = [{
                    "id": "clip_0",
                    "source_path": str(raw_video),
                    "trim_start": 0.0,
                    "trim_end": round(total_duration, 3),
                    "duration": round(total_duration, 3),
                    "speed": 1.0,
                    "transition_in": "cut"
                }]

        # Opt-in LUT styling
        lut_path = str(LUTS_DIR / lut_name) if lut_name else None

        if export_mp4:
            _notify("✂️ [5/5] เริ่มต้นตัดต่อวิดีโอ 9:16 + Punch-Zoom...", 0.85)
            print("\n✂️ [5/5] Cutting Video, Dynamic Punch-Zooming & Rendering Final MP4...")
            suffix = "_draft" if export_preset == "draft" else ""
            out_mp4 = EXPORTS_DIR / f"{project_name}_{timestamp_str}{suffix}.mp4"

            def on_ffmpeg_progress(curr_sec: float, tot_sec: float):
                ratio = min(1.0, max(0.0, curr_sec / max(0.1, tot_sec)))
                overall = round(0.85 + (ratio * 0.13), 3)
                pct_num = int(ratio * 100)
                _notify(
                    f"✂️ [5/5] กำลังเรนเดอร์วิดีโอ 1080x1920... {curr_sec:.1f}s / {tot_sec:.1f}s ({pct_num}%)",
                    overall
                )

            VideoEditor.assemble_tiktok_video(
                raw_video_paths=[str(raw_video)] if raw_video else [],
                total_duration=total_duration,
                mixed_audio_path=str(mixed_audio_path),
                ass_subtitle_path=str(ass_path),
                output_mp4_path=str(out_mp4),
                cues=micro_cues,
                ai_matched_shots=ai_matched_shots,
                sticker_path=sticker_path,
                lut_path=lut_path,
                lut_intensity=lut_intensity,
                shot_scales=shot_scales,
                clip_list=actual_clip_list,
                transitions=transitions,
                export_preset=export_preset,
                sticker_position=sticker_position,
                sticker_scale=sticker_scale,
                hook_duration=gradient_hook_duration,
                progress_callback=on_ffmpeg_progress
            )
            result_paths["mp4_video"] = str(out_mp4)
            result_paths["ai_matched_shots"] = ai_matched_shots
            _notify("🎉 การตัดต่อและเรนเดอร์เสร็จสมบูรณ์ 100%!", 1.0)
            print(f"   🎉 FINAL MP4 READY: {out_mp4}")

        # 6. Persist everything a re-roll will need to reuse
        artifacts = {
            "voice_audio": {"path": str(voice_audio_path)},
            "mixed_audio": {"path": str(mixed_audio_path)},
            "subtitles_ass": {"path": str(ass_path)},
        }
        if result_paths["mp4_video"]:
            artifacts["mp4_video"] = {"path": result_paths["mp4_video"]}

        manifest_fields = {
            "script_data": script_data,
            "cues": cues,
            "micro_cues": micro_cues,
            "total_duration": total_duration,
            "clip_list": actual_clip_list,
            "render_params": {
                "product_name": product_name,
                "raw_video_path": str(raw_video),
                "key_features": key_features,
                "pain_point": pain_point,
                "price_deal": price_deal,
                "hook_brand": hook_brand,
                "hook_model": hook_model,
                "hook_label": hook_label,
                "hook_motion": hook_motion,
                "hook_colors": hook_colors,
                "custom_script": custom_script,
                "script_overlays": script_overlays,
                "voice": voice,
                "voice_rate": voice_rate,
                "voice_engine_type": voice_engine_type,
                "voice_preset": voice_preset,
                "ad_tone": ad_tone,
                "human_voice_audio_path": human_voice_audio_path,
                "font_name": font_name,
                "bilingual_subtitles": bilingual_subtitles,
                "sticker_path": sticker_path,
                "bgm_name": bgm_name,
                "bgm_volume": bgm_volume,
                "bgm_ducking": bgm_ducking,
                "product_id": product_id,
                "angle_id": angle_id,
                "caption_position": caption_position,
                "caption_color": caption_color,
                "caption_scale": caption_scale,
                "sticker_position": sticker_position,
                "sticker_scale": sticker_scale,
                "lut_name": lut_name,
                "lut_intensity": lut_intensity,
                "clip_list": actual_clip_list,
                "transitions": transitions,
                "text_overlays": effective_text_overlays,
            },
            "artifacts": artifacts,
            "text_overlays": effective_text_overlays,
        }
        if product_meta:
            manifest_fields["product"] = product_meta
        if angle_meta:
            manifest_fields["angle"] = angle_meta

        ProjectManifest.save(project_name, **manifest_fields)
        result_paths["manifest"] = str(ProjectManifest.path_for(project_name))
        result_paths["clip_list"] = actual_clip_list
        result_paths["project_name"] = project_name

        _notify("🎉 ตัดต่อเสร็จสมบูรณ์ 100%!", 1.0)
        print(f"\n=======================================================")
        print("✅ PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"=======================================================\n")
        return result_paths

def main():
    parser = argparse.ArgumentParser(description="TikTok Product Auto-Cutter")
    parser.add_argument("--product", type=str, default="Esseger สายชาร์จแม่เหล็ก", help="Product Name")
    parser.add_argument("--video", type=str, default=r"01_Raw/20260812_Esseger-สายชาร์จแม่เหล็ก/Video/esseger_สายชาร์จ_raw.mov", help="Raw video file path")
    parser.add_argument("--features", type=str, default="แม่เหล็กแรงดูดสูง เสียบปึ้ง ชาร์จเร็ว ไม่ทำร้ายแบต ทนทานมาก", help="Key features")
    parser.add_argument("--pain", type=str, default="สายชาร์จพันกัน เสียบยากในที่มืด", help="Pain point")
    parser.add_argument("--deal", type=str, default="ราคาโปรพิเศษวันนี้", help="Price / Promotion deal")
    parser.add_argument("--voice", type=str, default="female", help="Voice (female/male)")
    parser.add_argument("--rate", type=str, default="+15%", help="Voice speed rate")

    args = parser.parse_args()

    TikTokAutoCutterPipeline.run(
        product_name=args.product,
        raw_video_path=args.video,
        key_features=args.features,
        pain_point=args.pain,
        price_deal=args.deal,
        voice=args.voice,
        voice_rate=args.rate
    )

if __name__ == "__main__":
    main()

# Alias for OmniCut Pro Studio
OmniCutPipeline = TikTokAutoCutterPipeline
