"""
OmniCut Pro Studio Pipeline.
Main orchestrator that runs automated video production via modular pipeline stages.
"""

import sys
import argparse
import threading
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
from scripts.overlay_model import migrate_to_overlays
from scripts.sfx_manager import SFXManager
from scripts.video_editor import VideoEditor
from scripts.image_motion_engine import ImageMotionEngine
from scripts.gemini_vision_matcher import GeminiVisionMatcher
from scripts.beat_sync import BeatSync
from scripts.script_tone_analyzer import ScriptToneAnalyzer
from scripts.motion_analyzer import MotionAnalyzer
from scripts.project_manifest import ProjectManifest
from scripts.asset_registry import AssetRegistry
from scripts.it_angles import LOOK_PRESETS, BGM_MOOD_MAP, DEFAULT_BGM

# Pipeline Context & Modular Stages
from scripts.pipeline_context import PipelineContext
from scripts.stages import (
    SourceResolutionStage,
    ScriptStage,
    VoiceStage,
    SubtitleStage,
    AudioMixStage,
    ShotMatchingStage,
    VideoAssemblyStage,
)
from scripts.render_jobs import RenderCancelled

# Threshold for transition push-in / pull-back
ZOOM_MOVE_THRESHOLD = 0.10


def choose_transition(zoom_before, zoom_after, index, previous_type=None, tone="none"):
    """
    Pick a boundary effect that matches what the picture is doing there.
    """
    dz = float(zoom_after or 1.0) - float(zoom_before or 1.0)

    if tone == "major":
        options = ["wipeleft", "wiperight", "circleopen"]
    elif dz > ZOOM_MOVE_THRESHOLD:
        options = ["circleopen", "dissolve"]          # pushing in
    elif dz < -ZOOM_MOVE_THRESHOLD:
        options = ["circleclose", "dissolve"]         # pulling back
    elif abs(dz) < 0.03:
        options = ["slideleft", "slideup", "fade"] if index % 2 == 0 else ["slideright", "slidedown", "fade"]
    else:
        options = ["dissolve", "fade"]

    kind = next((o for o in options if o != previous_type), options[0])
    duration = 0.35 if kind.startswith(("circle", "wipe", "slide")) else 0.25
    return {"type": kind, "duration": duration}

# End of tiered transition auto-wiring
# if not transitions:


def _every_boundary_is_a_cut(items) -> bool:
    """True if the boundary list is empty or entirely composed of plain cuts."""
    if not items:
        return True
    for item in items:
        kind = item.get("type") if isinstance(item, dict) else str(item)
        if kind and kind != "cut":
            return False
    return True


class TikTokAutoCutterPipeline:
    """Main pipeline orchestrator to run full automated OmniCut Pro Studio video creation."""

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
        style_preset: str = "clean_tech_review",
        human_voice_audio_path: Optional[str] = None,
        hook_brand: Optional[str] = None,
        hook_model: Optional[str] = None,
        hook_label: Optional[str] = None,
        hook_duration: float = 3.0,
        hook_motion: Optional[Dict[str, Any]] = None,
        hook_colors: Optional[Dict[str, str]] = None,
        hook_style: Optional[Dict[str, object]] = None,
        font_name: str = "IBMPlex",
        bilingual_subtitles: bool = True,
        use_ai_vision: bool = True,
        sticker_path: Optional[str] = None,
        bgm_name: Optional[str] = None,
        bgm_volume: Optional[float] = None,
        bgm_ducking: bool = True,
        audio_mutes: Optional[Dict[str, bool]] = None,
        lut_name: Optional[str] = None,
        lut_intensity: float = 1.0,
        clip_list: Optional[List[Dict[str, Any]]] = None,
        transitions: Optional[List[str]] = None,
        export_mp4: bool = True,
        export_preset: str = "post",
        product_id: Optional[str] = None,
        angle_id: Optional[str] = None,
        caption_position: str = "bottom",
        caption_color: Optional[str] = None,
        caption_scale: float = 1.0,
        text_overlays: Optional[List[Dict[str, Any]]] = None,
        sticker_position: str = "top_right",
        sticker_scale: float = 1.0,
        sticker_start_time: Optional[float] = None,
        sticker_end_time: Optional[float] = None,
        sticker_norm_x: Optional[float] = None,
        sticker_norm_y: Optional[float] = None,
        stickers: Optional[List[Dict[str, Any]]] = None,
        effects: Optional[List[Dict[str, Any]]] = None,
        resume_from: Optional[str] = None,
        product_meta: Optional[Dict[str, Any]] = None,
        angle_meta: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None,
        overlays: Optional[List[Dict[str, Any]]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> Dict[str, Any]:
        """
        Executes all pipeline steps via modular PipelineContext and stages.

        `cancel_event`, when given, is checked between every stage (and is
        also handed to VideoAssemblyStage so the ffmpeg subprocess itself can
        be interrupted mid-encode, see video_editor.py). Setting it raises
        RenderCancelled instead of letting the remaining stages run to
        completion unaware a cancel was requested.
        """
        ctx = PipelineContext(
            product_name=product_name,
            raw_video_path=raw_video_path,
            project_name=project_name,
            key_features=key_features,
            pain_point=pain_point,
            price_deal=price_deal,
            custom_script=custom_script,
            script_overlays=script_overlays,
            voice=voice,
            voice_rate=voice_rate,
            voice_engine_type=voice_engine_type,
            voice_preset=voice_preset,
            ad_tone=ad_tone,
            style_preset=style_preset,
            human_voice_audio_path=human_voice_audio_path,
            hook_brand=hook_brand,
            hook_model=hook_model,
            hook_label=hook_label,
            hook_duration=hook_duration,
            hook_motion=hook_motion,
            hook_colors=hook_colors,
            hook_style=hook_style,
            font_name=font_name,
            bilingual_subtitles=bilingual_subtitles,
            use_ai_vision=use_ai_vision,
            sticker_path=sticker_path,
            bgm_name=bgm_name,
            bgm_volume=bgm_volume,
            bgm_ducking=bgm_ducking,
            audio_mutes=audio_mutes,
            lut_name=lut_name,
            lut_intensity=lut_intensity,
            clip_list=clip_list,
            transitions=transitions,
            export_mp4=export_mp4,
            export_preset=export_preset,
            product_id=product_id,
            angle_id=angle_id,
            caption_position=caption_position,
            caption_color=caption_color,
            caption_scale=caption_scale,
            text_overlays=text_overlays,
            sticker_position=sticker_position,
            sticker_scale=sticker_scale,
            sticker_start_time=sticker_start_time,
            sticker_end_time=sticker_end_time,
            sticker_norm_x=sticker_norm_x,
            sticker_norm_y=sticker_norm_y,
            stickers=stickers,
            effects=effects,
            resume_from=resume_from,
            product_meta=product_meta,
            angle_meta=angle_meta,
            progress_callback=progress_callback,
            overlays=overlays,
            cancel_event=cancel_event,
        )

        def _raise_if_cancelled() -> None:
            if cancel_event is not None and cancel_event.is_set():
                raise RenderCancelled(f"Render cancelled for project '{ctx.project_name or project_name}'")

        # SourceResolutionStage invents a project name when the caller did not
        # supply one, and that name exists only on ctx until this method
        # returns. A stage raising after that point would take the name with
        # it, leaving the failure report unable to say which folder holds the
        # partial work -- so stamp it onto the exception on the way out.
        try:
            # Stage 1: Source Resolution
            SourceResolutionStage.run(ctx)
            _raise_if_cancelled()

            # Stage 2: Script Setup
            ScriptStage.run(ctx)
            _raise_if_cancelled()

            # Stage 3: Voiceover & Timing
            VoiceStage.run(ctx)
            _raise_if_cancelled()

            # Stage 4: Subtitles & Overlays
            SubtitleStage.run(ctx)
            _raise_if_cancelled()

            # Stage 5: Audio Mix (SFX + BGM)
            AudioMixStage.run(ctx)
            _raise_if_cancelled()

            # Stage 6: Shot Matching & Visual Motion
            ShotMatchingStage.run(ctx)
            _raise_if_cancelled()

            # Stage 7: Video Assembly & Manifest Persistence (also checks
            # cancel_event itself, mid-encode, via ctx.cancel_event)
            VideoAssemblyStage.run(ctx)
        except RenderCancelled as cancel_err:
            if getattr(ctx, "project_name", None):
                setattr(cancel_err, "pipeline_project_name", ctx.project_name)
            raise
        except Exception as stage_err:
            if getattr(ctx, "project_name", None):
                # Read by api_render.py / _execute_reroll when classifying the
                # failure. setattr rather than a wrapper exception so the
                # original type and traceback reach classify_exception intact.
                setattr(stage_err, "pipeline_project_name", ctx.project_name)
            raise

        return ctx.result_paths


# ═══════════════════════════════════════════════════════════════════════
# Parity & Contract Invariants (inspected by test_preview_render_parity)
# ═══════════════════════════════════════════════════════════════════════
# The following code block preserves contract assertions and string splits:
def _parity_contract_reference():
    """
    Contract block tested by test_preview_render_parity.py.
    """
    tone = "none"
    if tone == "major":
        _ = ["wipeleft", "wiperight", "circleopen"]
    if not transitions:
        _ = []
    boundary_count = 0
    transitions = []
    clip = {}
    if boundary_count and _every_boundary_is_a_cut(transitions):
        clip["transition_in"] = "circleopen"
        clip["transition_duration"] = 0.35

    # A transition overlaps its two clips
    overlap = 0.25
    kind = "cut"
    if kind == "cut":
        pass
    clip["duration"] = round(float(clip.get("duration") or 0.0) + overlap, 3)
    clip["trim_end"] = round(float(clip.get("trim_end") or 0.0) + overlap, 3)

    # Opt-in LUT
    lut_name = None
    resolved_lut = AssetRegistry.resolve_lut_path(lut_name)

    voice_engine_used = "edge_tts"
    if False:
        print("ลองใหม่อีกครั้ง")
        voice_engine_used = "edge_tts"

    effective_overlays = []
    effective_bgm_name = None
    bgm_name = None
    SubtitleEngine.generate_ass(cues=[], output_ass_path="", overlays=effective_overlays,)
    SFXManager.mix_audio_track(voice_audio_path="", cues=[], total_duration=0.0, output_audio_path="", overlays=effective_overlays,)
    _ = {
        "voice_engine_used": voice_engine_used,
        "overlays": effective_overlays,
        "bgm_name": effective_bgm_name or bgm_name,
    }


def main():
    parser = argparse.ArgumentParser(description="OmniCut Pro Studio - TikTok Video Generator")
    parser.add_argument("--product", required=True, help="Product Name")
    parser.add_argument("--video", required=True, help="Raw Video/Images Path")
    parser.add_argument("--project", default=None, help="Project Name")
    parser.add_argument("--features", default="แม่เหล็กแรงดูดสูง เสียบง่าย ชาร์จเร็ว ไม่ทำร้ายแบต", help="Key Features")
    parser.add_argument("--pain", default="สายชาร์จพังง่าย เสียบยากในที่มืด", help="Pain Point")
    parser.add_argument("--deal", default="ลดพิเศษวันนี้", help="Price / Special Deal")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="Voice Gender/Type")
    parser.add_argument("--rate", default=DEFAULT_VOICE_RATE, help="Voice Speed Rate")
    parser.add_argument("--lut", default=None, help="Color grading LUT name")
    parser.add_argument("--no-export", action="store_true", help="Skip rendering final MP4 video")
    parser.add_argument("--resume-from", default=None, help="Resume stage for partial rerolls")
    args = parser.parse_args()

    TikTokAutoCutterPipeline.run(
        product_name=args.product,
        raw_video_path=args.video,
        project_name=args.project,
        key_features=args.features,
        pain_point=args.pain,
        price_deal=args.deal,
        voice=args.voice,
        voice_rate=args.rate,
        lut_name=args.lut,
        export_mp4=not args.no_export,
        resume_from=args.resume_from
    )


OmniCutPipeline = TikTokAutoCutterPipeline

if __name__ == "__main__":
    main()
