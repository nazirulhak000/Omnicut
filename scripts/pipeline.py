import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

from scripts.config import (
    BASE_DIR, RAW_DIR, PROJECTS_DIR, EXPORTS_DIR, LUTS_DIR,
    DEFAULT_VOICE, DEFAULT_VOICE_RATE, DEFAULT_VOICE_PITCH
)
from scripts.script_generator import ScriptGenerator
from scripts.voice_engine import VoiceEngine
from scripts.subtitle_engine import SubtitleEngine
from scripts.sfx_manager import SFXManager
from scripts.video_editor import VideoEditor
from scripts.image_motion_engine import ImageMotionEngine
from scripts.gemini_vision_matcher import GeminiVisionMatcher
from scripts.project_manifest import ProjectManifest
from scripts.it_angles import LOOK_PRESETS

class TikTokAutoCutterPipeline:
    """Main pipeline to run full automated TikTok video creation."""

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
        hook_title: Optional[str] = None,
        font_name: str = "IBMPlex",
        bilingual_subtitles: bool = True,
        use_ai_vision: bool = True,
        sticker_path: Optional[str] = None,
        bgm_name: Optional[str] = None,
        lut_name: Optional[str] = None,
        clip_list: Optional[List[Dict[str, any]]] = None,
        transitions: Optional[List[str]] = None,
        export_mp4: bool = True,
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

        raw_video = Path(raw_video_path).resolve() if raw_video_path else None
        
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
                raise FileNotFoundError(f"Raw video or product image not found: {raw_video_path}")

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
        print(f"🎬 Starting TikTok Auto-Cutter for: {product_name}")
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
            print(f"   Gemini Flash TTS voice generated! Duration: {total_duration:.2f}s, Cues: {len(cues)}")
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
        if ProjectManifest.should_run("subtitles", resume_from):
            _notify("💬 [3/5] กำลังสร้างซับไตเติล TikTok เคลื่อนไหว (Kanit-Black 86pt)...", 0.50)
            print(f"\n💬 [3/5] Generating TikTok Animated Subtitles (.ass with {font_name} font & 3-word bursts)...")
            ass_path = _out_path("subtitles", ".ass")
            banner_title = hook_title or f"{product_name}"
            _, micro_cues = SubtitleEngine.generate_ass(
                cues=cues,
                output_ass_path=str(ass_path),
                font_name=font_name,
                hook_title=banner_title,
                hook_duration=min(3.5, total_duration),
                bilingual=bilingual_subtitles
            )
            print(f"   Subtitles created: {ass_path} ({len(micro_cues)} micro-bursts)")
        else:
            ass_path = _reuse("subtitles_ass", "ไฟล์ซับไตเติล")
            micro_cues = manifest["micro_cues"]
            print(f"♻️  [3/5] Reusing subtitles: {ass_path.name} ({len(micro_cues)} micro-bursts)")

        # 4. SFX & BGM Audio Mixing
        #
        # micro_cues are derived from `cues` alone — font, bilingual and
        # hook_title never move a timing — so the mix only has to be rebuilt
        # when the voice itself was regenerated. That is what makes a hook or
        # subtitle re-roll cheap.
        if ProjectManifest.should_run("voice", resume_from):
            _notify("🎵 [4/5] กำลังมิกซ์เสียง Voice + เอฟเฟกต์ SFX (Boom/Pop/Cash) + BGM...", 0.65)
            print("\n🎵 [4/5] Mixing Audio (Voice + Boom/Whoosh/Pop/Ding/Cash SFX + Upbeat BGM)...")
            mixed_audio_path = _out_path("mixed_audio", ".wav")
            mix_kwargs = {"bgm_name": bgm_name} if bgm_name else {}
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

        ai_matched_shots = None
        if export_mp4 and use_ai_vision and os.environ.get("GEMINI_API_KEY"):
            _notify("👁️ [AI Vision] ให้ Gemini 2.5 Flash ดูคลิปและเลือกฉากที่ตรงกับสคริปต์...", 0.75)
            print("\n👁️ [AI Vision] Gemini 2.5 Flash is analyzing raw footage scenes...")
            try:
                raw_info = VideoEditor.get_media_info(str(raw_video))
                ai_matched_shots = GeminiVisionMatcher.match_script_to_video(
                    raw_video_path=str(raw_video),
                    cues=micro_cues,
                    raw_duration=raw_info.get("duration", 60.0)
                )
            except Exception as e:
                print(f"   ⚠️ AI Vision Matching skipped ({e}) — using rhythmic cuts.")

        # Opt-in only -- measured on this CPU-only machine (no CUDA) against
        # the real Esseger clip: lut3d added ~90% to the ffmpeg render step
        # (11.6s -> 22.0s on an 8s clip), nowhere near "cheap relative to
        # libx264's own cost". ANGLE_LUT_HINTS stays as a suggestion the
        # frontend can surface, but the pipeline never applies one silently --
        # a user has to pick a LUT explicitly and accept the slower render.
        lut_path = str(LUTS_DIR / lut_name) if lut_name else None

        # Punch-zoom pattern per angle (LOOK_PRESETS) -- safe to auto-apply
        # unlike the LUT above: same ffmpeg scale/crop work either way, just
        # different numbers, not an extra filter pass.
        shot_scales = LOOK_PRESETS.get(angle_meta.get("angle_key", "")) if angle_meta else None

        if export_mp4:
            _notify("✂️ [5/5] กำลังตัดต่อวิดีโอ 9:16 + Punch-Zoom & เรนเดอร์ไฟล์ MP4...", 0.85)
            print("\n✂️ [5/5] Cutting Video, Dynamic Punch-Zooming & Rendering Final MP4...")
            out_mp4 = EXPORTS_DIR / f"{project_name}_{timestamp_str}.mp4"
            VideoEditor.assemble_tiktok_video(
                raw_video_paths=[str(raw_video)],
                total_duration=total_duration,
                mixed_audio_path=str(mixed_audio_path),
                ass_subtitle_path=str(ass_path),
                output_mp4_path=str(out_mp4),
                cues=micro_cues,
                ai_matched_shots=ai_matched_shots,
                sticker_path=sticker_path,
                lut_path=lut_path,
                shot_scales=shot_scales,
                clip_list=clip_list,
                transitions=transitions
            )
            result_paths["mp4_video"] = str(out_mp4)
            result_paths["ai_matched_shots"] = ai_matched_shots
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
            "render_params": {
                "product_name": product_name,
                "raw_video_path": str(raw_video),
                "key_features": key_features,
                "pain_point": pain_point,
                "price_deal": price_deal,
                "hook_title": hook_title,
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
                "lut_name": lut_name,
                "clip_list": clip_list,
                "transitions": transitions,
            },
            "artifacts": artifacts,
        }
        if product_meta:
            manifest_fields["product"] = product_meta
        if angle_meta:
            manifest_fields["angle"] = angle_meta

        ProjectManifest.save(project_name, **manifest_fields)
        result_paths["manifest"] = str(ProjectManifest.path_for(project_name))

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
