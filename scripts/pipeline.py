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
    BASE_DIR, RAW_DIR, PROJECTS_DIR, EXPORTS_DIR,
    DEFAULT_VOICE, DEFAULT_VOICE_RATE, DEFAULT_VOICE_PITCH, MUSIC_DIR
)
from scripts.script_generator import ScriptGenerator
from scripts.voice_engine import VoiceEngine
from scripts.subtitle_engine import SubtitleEngine
from scripts.sfx_manager import SFXManager
from scripts.video_editor import VideoEditor
from scripts.capcut_generator import CapCutDraftGenerator

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
        voice: str = DEFAULT_VOICE,
        voice_rate: str = DEFAULT_VOICE_RATE,
        voice_engine_type: str = "edge_tts",
        f5_ref_preset: Optional[str] = "gemini_puck_male_hype",
        ad_tone: str = "commercial_premium",
        f5_custom_ref_path: Optional[str] = None,
        f5_custom_ref_text: Optional[str] = None,
        human_voice_audio_path: Optional[str] = None,
        hook_title: Optional[str] = None,
        font_name: str = "IBMPlex",
        bilingual_subtitles: bool = True,
        sticker_path: Optional[str] = None,
        export_mp4: bool = True,
        export_capcut: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, any]:
        """
        Executes all pipeline steps and returns paths to artifacts.
        """
        def _notify(msg: str, progress: float):
            if progress_callback:
                try:
                    progress_callback(msg, progress)
                except Exception:
                    pass

        raw_video = Path(raw_video_path).resolve()
        if not raw_video.exists():
            raise FileNotFoundError(f"Raw video not found: {raw_video}")

        # Determine Project Name
        if not project_name:
            clean_name = "".join(c for c in product_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
            project_name = f"TikTok_{clean_name}"

        project_dir = PROJECTS_DIR / project_name
        project_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n=======================================================")
        print(f"🎬 Starting TikTok Auto-Cutter for: {product_name}")
        print(f"📁 Project Folder: {project_dir}")
        print(f"=======================================================\n")

        # 1. Script & Lines Setup
        _notify("🧠 [1/5] วิเคราะห์สินค้าและจัดเตรียมสคริปต์ TikTok...", 0.10)
        print("🧠 [1/5] Setting up TikTok Script & Cues...")
        if custom_script:
            lines = [
                {"text": l.strip(), "sfx": "pop" if i > 0 else "whoosh"}
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

        # 2. Voice Handling (Human Voice vs F5-TTS Thai vs Edge-TTS)
        voice_audio_path = project_dir / "voiceover.wav"
        cues = []

        if human_voice_audio_path and Path(human_voice_audio_path).exists():
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
                    "sfx": item.get("sfx")
                })
            print(f"   Human voice loaded! Duration: {total_duration:.2f}s, Cues synced: {len(cues)}")
        elif voice_engine_type == "f5_tts":
            _notify("🎙️ [2/5] กำลังสังเคราะห์เสียงโคลน F5-TTS Thai (Local AI ~45 วิ)...", 0.25)
            print("\n🎙️ [2/5] Synthesizing Voice via Local F5-TTS Thai (VIZINTZOR/F5-TTS-TH-V2)...")
            from scripts.f5_tts_engine import PRESETS_DIR, ensure_default_presets
            ensure_default_presets()
            
            ref_audio = f5_custom_ref_path
            ref_text = f5_custom_ref_text
            if not ref_audio or not Path(ref_audio).exists():
                preset_file = PRESETS_DIR / f"{f5_ref_preset or 'tiktok_male_pro'}.wav"
                if preset_file.exists():
                    ref_audio = str(preset_file)
                    txt_file = preset_file.with_suffix(".txt")
                    ref_text = txt_file.read_text(encoding="utf-8").strip() if txt_file.exists() else ""

            voice_res = VoiceEngine.generate_f5_voice(
                text_or_lines=script_data["lines"],
                output_audio_path=str(voice_audio_path),
                ref_audio_path=ref_audio,
                ref_text=ref_text,
                step=8,
                speed=1.05
            )
            cues = voice_res["cues"]
            total_duration = voice_res["duration"]
            print(f"   F5-TTS Thai voice generated! Duration: {total_duration:.2f}s, Cues: {len(cues)}")
        elif voice_engine_type == "gemini_tts":
            _notify("⚡ [2/5] กำลังสังเคราะห์เสียงพากย์ด้วย Google Gemini 2.5 Flash TTS...", 0.25)
            print("\n⚡ [2/5] Synthesizing Voice via Google Gemini 2.5 Flash TTS...")
            from scripts.gemini_tts_engine import GeminiFlashTTSEngine
            import subprocess

            gemini_voice = "Kore" if voice == "female" else "Puck"
            if f5_ref_preset and "gemini" in f5_ref_preset:
                parts = f5_ref_preset.replace("gemini_", "").split("_")
                gemini_voice = parts[0].capitalize()

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
                    "sfx": item.get("sfx")
                })
            print(f"   Gemini Flash TTS voice generated! Duration: {total_duration:.2f}s, Cues: {len(cues)}")
        else:
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
        _notify("💬 [3/5] กำลังสร้างซับไตเติล TikTok เคลื่อนไหว (Kanit-Black 86pt)...", 0.50)
        print(f"\n💬 [3/5] Generating TikTok Animated Subtitles (.ass with {font_name} font & 3-word bursts)...")
        ass_path = project_dir / "subtitles.ass"
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

        # 4. SFX & BGM Audio Mixing
        _notify("🎵 [4/5] กำลังมิกซ์เสียง Voice + เอฟเฟกต์ SFX (Boom/Pop/Cash) + BGM...", 0.65)
        print("\n🎵 [4/5] Mixing Audio (Voice + Boom/Whoosh/Pop/Ding/Cash SFX + Upbeat BGM)...")
        mixed_audio_path = project_dir / "mixed_audio.wav"
        SFXManager.mix_audio_track(
            voice_audio_path=str(voice_audio_path),
            cues=micro_cues,
            total_duration=total_duration,
            output_audio_path=str(mixed_audio_path)
        )
        print(f"   Audio mixed: {mixed_audio_path}")

        result_paths = {
            "project_name": project_name,
            "project_dir": str(project_dir),
            "script": script_data,
            "voice_audio": str(voice_audio_path),
            "mixed_audio": str(mixed_audio_path),
            "subtitles_ass": str(ass_path),
            "duration": total_duration,
            "mp4_video": None,
            "capcut_draft": None
        }

        # 5. Direct Video Render (MP4)
        import datetime
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        if export_mp4:
            _notify("✂️ [5/5] กำลังตัดต่อวิดีโอ 9:16 + Punch-Zoom & เรนเดอร์ไฟล์ MP4...", 0.80)
            print("\n✂️ [5/5] Cutting Video, Dynamic Punch-Zooming & Rendering Final MP4...")
            out_mp4 = EXPORTS_DIR / f"{project_name}_{timestamp_str}.mp4"
            VideoEditor.assemble_tiktok_video(
                raw_video_paths=[str(raw_video)],
                total_duration=total_duration,
                mixed_audio_path=str(mixed_audio_path),
                ass_subtitle_path=str(ass_path),
                output_mp4_path=str(out_mp4),
                cues=micro_cues,
                sticker_path=sticker_path
            )
            result_paths["mp4_video"] = str(out_mp4)
            print(f"   🎉 FINAL MP4 READY: {out_mp4}")

        # 6. CapCut Draft Project
        if export_capcut:
            _notify("💻 กำลังสร้างโปรเจกต์ CapCut PC Draft...", 0.95)
            print("\n💻 Generating CapCut PC Draft Project...")
            bgm_path = MUSIC_DIR / "tiktok_upbeat_bgm.wav"
            capcut_draft_name = f"{project_name}_{timestamp_str}"
            capcut_dir = CapCutDraftGenerator.create_project(
                project_name=capcut_draft_name,
                raw_video_path=str(raw_video),
                voice_audio_path=str(voice_audio_path),
                cues=micro_cues,
                total_duration=total_duration,
                bgm_path=str(bgm_path) if bgm_path.exists() else None
            )
            result_paths["capcut_draft"] = str(capcut_dir)
            print(f"   🎉 CapCut Draft Ready: {capcut_dir}")

        _notify("🎉 ตัดต่อเสร็จสมบูรณ์ 100%!", 1.0)
        print(f"\n=======================================================")
        print("✅ PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"=======================================================\n")
        return result_paths
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
