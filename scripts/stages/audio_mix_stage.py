"""
Audio Mix Stage for OmniCut Pro Studio.
Handles background music resolution, volume balancing, ducking, and SFX mixing.
"""

from pathlib import Path
from typing import Optional

from scripts.it_angles import BGM_MOOD_MAP, DEFAULT_BGM
from scripts.project_manifest import ProjectManifest
from scripts.pipeline_context import PipelineContext


class AudioMixStage:
    """Mixes voiceover, sound effects, and background music track."""

    @classmethod
    def run(cls, ctx: PipelineContext) -> None:
        effective_bgm_name = ctx.bgm_name
        if not effective_bgm_name:
            angle_key = ctx.angle_meta.get("angle_key", "") if ctx.angle_meta else ""
            effective_bgm_name = BGM_MOOD_MAP.get(angle_key, DEFAULT_BGM)

        existing_mix = ProjectManifest.artifact_path(ctx.manifest, "mixed_audio") if ctx.manifest else None
        mix_is_due = ctx.should_run("mix")

        if not ctx.export_mp4:
            mixed_audio_path = existing_mix
            print("[4/5] skip audio mix -- no video render yet (preview plays separate stems)")
        elif mix_is_due or not existing_mix:
            ctx.notify("🎵 [4/5] กำลังมิกซ์เสียง Voice + เอฟเฟกต์ SFX (Boom/Pop/Cash) + BGM...", 0.65)
            print("\n🎵 [4/5] Mixing Audio (Voice + Boom/Whoosh/Pop/Ding/Cash SFX + Upbeat BGM)...")
            mixed_audio_path = ctx.out_path("mixed_audio", ".wav")
            mix_kwargs = {"bgm_name": effective_bgm_name} if effective_bgm_name else {}
            if ctx.bgm_volume is not None:
                mix_kwargs["bgm_vol"] = min(1.0, max(0.0, float(ctx.bgm_volume)))
            mutes = ctx.audio_mutes or {}
            if mutes.get("voice"):
                mix_kwargs["voice_vol"] = 0.0
            if mutes.get("sfx"):
                mix_kwargs["sfx_vol"] = 0.0
            if mutes.get("bgm"):
                mix_kwargs["bgm_vol"] = 0.0
            if ctx.bgm_ducking:
                mix_kwargs["bgm_ducking"] = True

            # Use pipeline module reference so unittest.mock.patch('scripts.pipeline.SFXManager.mix_audio_track') works
            import scripts.pipeline as pipeline_mod
            pipeline_mod.SFXManager.mix_audio_track(
                voice_audio_path=str(ctx.voice_audio_path),
                cues=ctx.micro_cues,
                total_duration=ctx.total_duration,
                output_audio_path=str(mixed_audio_path),
                overlays=ctx.effective_overlays,
                **mix_kwargs
            )
            print(f"   Audio mixed: {mixed_audio_path}")
        else:
            mixed_audio_path = existing_mix
            if mixed_audio_path:
                print(f"[4/5] Reusing mixed audio: {mixed_audio_path.name}")

        ctx.mixed_audio_path = mixed_audio_path
        ctx.effective_bgm_name = effective_bgm_name

        ctx.result_paths = {
            "project_name": ctx.project_name,
            "project_dir": str(ctx.project_dir),
            "script": ctx.script_data,
            "voice_audio": str(ctx.voice_audio_path),
            "mixed_audio": str(mixed_audio_path) if mixed_audio_path else None,
            "subtitles_ass": str(ctx.ass_sub_path),
            "duration": ctx.total_duration,
            "mp4_video": None,
        }
