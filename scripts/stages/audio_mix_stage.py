"""
Audio Mix Stage for OmniCut Pro Studio.
Handles background music resolution, volume balancing, ducking, and SFX mixing.
"""

from pathlib import Path
from typing import Optional

from scripts.it_angles import BGM_MOOD_MAP, DEFAULT_BGM
from scripts.project_manifest import ProjectManifest
from scripts.pipeline_context import PipelineContext, bus_volume_override


# Shown to the user after a render whose full mix failed. The clip still has
# its voice (that is the fallback), so this says exactly what is missing.
MIX_DEGRADED_REASON = "มิกซ์เสียงเต็มล้มเหลว จึงใช้เสียงพากย์อย่างเดียว: คลิปนี้ไม่มีเพลงพื้นหลังและเอฟเฟกต์ SFX"


def _stderr_tail(text, limit: int = 200) -> str:
    """Last non-empty ffmpeg stderr line, trimmed -- the line that names the failure."""
    lines = [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]
    return (lines[-1] if lines else "")[:limit]


class AudioMixStage:
    """Mixes voiceover, sound effects, and background music track."""

    @classmethod
    def run(cls, ctx: PipelineContext) -> None:
        effective_bgm_name = ctx.bgm_name
        if not effective_bgm_name:
            angle_key = ctx.angle_meta.get("angle_key", "") if ctx.angle_meta else ""
            effective_bgm_name = BGM_MOOD_MAP.get(angle_key, DEFAULT_BGM)

        existing_mix = ProjectManifest.artifact_path(ctx.manifest, "mixed_audio") if ctx.manifest else None
        # A mix that fell back to voice-only is not "done": mix again on the next
        # render until it succeeds, instead of reusing the file with no music.
        mix_is_due = ctx.should_run("mix") or bool((ctx.manifest or {}).get("mix_degraded"))
        mix_degraded = False
        mix_degraded_reason = None
        mix_degraded_detail = None

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
            # Voice/SFX levels from the editor's Track Mix (L4-05). Read through
            # the same helper the mix fingerprint uses, so a level change both
            # re-mixes and reaches the filter; a default level adds nothing and
            # the call stays exactly what it was. Mutes below still win.
            for key, kwarg in (("voice_volume", "voice_vol"), ("sfx_volume", "sfx_vol")):
                level = bus_volume_override(ctx.manifest, key)
                if level is not None:
                    mix_kwargs[kwarg] = level
            mutes = ctx.audio_mutes or {}
            if mutes.get("voice"):
                mix_kwargs["voice_vol"] = 0.0
            if mutes.get("sfx"):
                mix_kwargs["sfx_vol"] = 0.0
            if mutes.get("bgm"):
                mix_kwargs["bgm_vol"] = 0.0
            if ctx.bgm_ducking:
                mix_kwargs["bgm_ducking"] = True
            # Ripple cuts of the voice (VoiceStage already verified they fit the
            # file). Only passed when there are cuts so an uncut call is unchanged;
            # BGM is deliberately not cut (it keeps playing across the join).
            voice_cuts = getattr(ctx, "voice_cuts", None)
            if voice_cuts:
                mix_kwargs["voice_cuts"] = voice_cuts
                source_duration = getattr(ctx, "voice_source_duration", 0.0)
                if source_duration:
                    mix_kwargs["voice_source_duration"] = source_duration

            # Use pipeline module reference so unittest.mock.patch('scripts.pipeline.SFXManager.mix_audio_track') works
            import scripts.pipeline as pipeline_mod
            # Cleared here as well as inside mix_audio_track: a mock that never
            # touches it must not inherit an earlier real call's failure.
            pipeline_mod.SFXManager.last_mix_status = {"success": True, "fallback": False, "error": None}
            pipeline_mod.SFXManager.mix_audio_track(
                voice_audio_path=str(ctx.voice_audio_path),
                cues=ctx.micro_cues,
                total_duration=ctx.total_duration,
                output_audio_path=str(mixed_audio_path),
                overlays=ctx.effective_overlays,
                **mix_kwargs
            )
            print(f"   Audio mixed: {mixed_audio_path}")

            mix_status = dict(getattr(pipeline_mod.SFXManager, "last_mix_status", None) or {})
            if mix_status.get("fallback_error"):
                # The voice-only copy failed too: there is no usable mix. Stop
                # with the reason instead of handing a missing/partial file on.
                raise RuntimeError(
                    "มิกซ์เสียงล้มเหลวทั้งแบบเต็มและแบบเสียงพากย์อย่างเดียว: "
                    f"{_stderr_tail(mix_status.get('fallback_error')) or 'ไม่ทราบสาเหตุ'}"
                )
            if mix_status.get("fallback"):
                mix_degraded = True
                mix_degraded_reason = MIX_DEGRADED_REASON
                mix_degraded_detail = _stderr_tail(mix_status.get("error")) or None
                print(f"   ⚠️ {mix_degraded_reason}")
                ctx.notify(f"⚠️ {mix_degraded_reason}", 0.66)
            # Keep the manifest in step with the mix that is on disk now: set it
            # when this mix is degraded, clear it when a good remix replaced a
            # degraded one. Nothing is written for the ordinary good-to-good case.
            if ctx.project_name and (mix_degraded or (ctx.manifest or {}).get("mix_degraded")):
                try:
                    ProjectManifest.save(
                        ctx.project_name,
                        mix_degraded=mix_degraded,
                        mix_degraded_reason=mix_degraded_reason,
                        mix_degraded_detail=mix_degraded_detail,
                    )
                except Exception as save_err:
                    print(f"   ⚠️ บันทึกสถานะมิกซ์เสียงลงโปรเจกต์ไม่สำเร็จ: {save_err}")
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
            "mix_degraded": mix_degraded,
        }
        if mix_degraded:
            ctx.result_paths["mix_degraded_reason"] = mix_degraded_reason
            if mix_degraded_detail:
                ctx.result_paths["mix_degraded_detail"] = mix_degraded_detail
