"""
Video Assembly Stage for OmniCut Pro Studio.
Handles boundary transitions, overlap compensation, LUT resolution,
FFmpeg video assembly, and project manifest persistence.
"""

import datetime
import inspect
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.config import EXPORTS_DIR
from scripts.asset_registry import AssetRegistry
from scripts.project_manifest import ProjectManifest
from scripts.pipeline_context import PipelineContext
from scripts.export_registry import ExportRegistry


def _every_boundary_is_a_cut(items) -> bool:
    """True if the boundary list is empty or entirely composed of plain cuts."""
    if not items:
        return True
    for item in items:
        kind = item.get("type") if isinstance(item, dict) else str(item)
        if kind and kind != "cut":
            return False
    return True


def _centre_transition_overlaps(clips: List[dict], transitions) -> None:
    """Give each planned transition its overlap, centred on the planned cut.

    VideoEditor (and the preview) start a transition ``duration`` before the
    end of the outgoing clip and run it to that end. Extending only the
    outgoing clip by the whole overlap therefore put the transition entirely
    AFTER the planned cut: its visual midpoint landed duration/2 late (175 ms
    for a 0.35 s wipe, on top of the J-lead -- audit A7d). Splitting the
    overlap puts the midpoint on the cut, where the J-lead wants the picture
    to change, without touching how the renderer applies xfade offsets:

    * outgoing clip: +overlap/2 at its tail (footage continues past the cut);
    * incoming clip: +overlap/2 at its head (``trim_start`` moves back, so the
      frame planned for the cut instant is still the one shown there); when
      the source has less than that before ``trim_start``, the rest is added
      to the incoming clip's tail instead.

    Every clip still gains exactly the overlaps of its boundaries, so every
    later cut and the total length are unchanged. Applied once per boundary
    (``_overlap_compensated`` on the outgoing clip marks it).
    """
    for i, boundary in enumerate(transitions[: len(clips) - 1]):
        kind = boundary.get("type") if isinstance(boundary, dict) else str(boundary)
        if not kind or kind == "cut":
            continue
        overlap = float(boundary.get("duration") or 0.0) if isinstance(boundary, dict) else 0.0
        if overlap <= 0:
            continue
        outgoing, incoming = clips[i], clips[i + 1]
        if outgoing.get("_overlap_compensated"):
            continue
        tail = round(overlap / 2.0, 4)
        head_total = round(overlap - tail, 4)

        # In both frontend SequencePlayer and FFmpeg, played duration =
        # (trim_end - trim_start) / speed, so a played extension of x needs
        # x * speed more source footage.
        out_speed = float(outgoing.get("speed") or 1.0)
        outgoing["duration"] = round(float(outgoing.get("duration") or 0.0) + tail, 3)
        if outgoing.get("trim_end") is not None:
            outgoing["trim_end"] = round(float(outgoing["trim_end"]) + tail * out_speed, 3)
        outgoing["_overlap_compensated"] = True

        in_speed = float(incoming.get("speed") or 1.0)
        head = 0.0
        if incoming.get("trim_start") is not None:
            head = min(head_total, max(0.0, float(incoming["trim_start"])) / in_speed)
            incoming["trim_start"] = round(float(incoming["trim_start"]) - head * in_speed, 3)
        incoming["duration"] = round(float(incoming.get("duration") or 0.0) + head_total, 3)
        if incoming.get("trim_end") is not None and head_total - head > 1e-9:
            incoming["trim_end"] = round(float(incoming["trim_end"]) + (head_total - head) * in_speed, 3)


def _fill_undecided_transitions(clips: List[dict], style_preset: Optional[str]) -> List[dict]:
    """Pick a boundary effect for every boundary of an all-cut clip list.

    All-cut means "nothing decided yet" (the editor always sends its own
    all-cut default), so the boundaries are filled -- but through the same
    style budget the shot planner uses (audit A7c): a style that keeps a
    boundary as a hard cut keeps it here too, instead of every boundary
    becoming a wipe. Slides follow the outgoing clip's camera pan.
    """
    from scripts.pipeline import choose_transition
    from scripts.style_motion_policy import apply_transition_budget, orient_slide_to_pan

    transitions: List[dict] = []
    previous_type = None
    for i in range(max(0, len(clips) - 1)):
        pick = choose_transition(clips[i].get("zoom"), clips[i + 1].get("zoom"), i, previous_type)
        pick = apply_transition_budget(pick, style_preset=style_preset, boundary_index=i + 1)
        pick = orient_slide_to_pan(pick, clips[i].get("keyframes"))
        previous_type = pick["type"]
        transitions.append(pick)
    return transitions


class VideoAssemblyStage:
    """Applies transitions, resolves LUTs, renders MP4 via VideoEditor, and saves manifest."""

    @classmethod
    def run(cls, ctx: PipelineContext) -> None:
        color_theme = ctx.resolve_color_theme_contract()
        spotlight = ctx.resolve_spotlight_contract()
        background_isolation = ctx.resolve_background_isolation_contract()
        actual_clip_list = ctx.actual_clip_list
        transitions = ctx.transitions

        boundary_count = max(0, len(actual_clip_list or []) - 1)
        if boundary_count and _every_boundary_is_a_cut(transitions):
            transitions = _fill_undecided_transitions(actual_clip_list, ctx.style_preset)
            if actual_clip_list:
                for i, clip in enumerate(actual_clip_list):
                    if i == 0:
                        continue
                    clip["transition_in"] = transitions[i - 1]["type"]
                    clip["transition_duration"] = transitions[i - 1]["duration"]
            filled = sum(1 for t in transitions if t.get("type") != "cut")
            print(f"   ✨ ใส่รอยต่อให้อัตโนมัติ {filled}/{boundary_count} จุดตามสไตล์ (ไม่มีรอยต่อเดิมให้ยึด)")

        # A transition overlaps its two clips, so the finished video is
        # shorter than the clips add up to -- by the sum of every transition.
        # Overlap extension is ONLY applied ONCE when clips are freshly generated
        # from cues (to compensate for transition shortening).
        # Existing or editor-provided clips must NEVER be inflated repeatedly.
        is_newly_generated = getattr(ctx, "is_newly_generated_clips", False)
        if is_newly_generated and transitions and actual_clip_list and len(actual_clip_list) > 1:
            _centre_transition_overlaps(actual_clip_list, transitions)

            # Reconcile final timeline duration with ctx.total_duration to eliminate any micro gap
            if ctx.total_duration and ctx.total_duration > 0:
                acc = 0.0
                for i, c in enumerate(actual_clip_list):
                    boundary_overlap = 0.0
                    if i > 0:
                        # Generated clips normally carry transition metadata,
                        # but callers may provide a clip list plus the
                        # transition list separately.  In that shape the
                        # missing per-clip metadata must not make the
                        # timeline look longer than it is and trigger a
                        # compensating shrink of the final clip.
                        t_in = c.get("transition_in")
                        if t_in is not None:
                            if t_in != "cut":
                                boundary_overlap = float(c.get("transition_duration", 0.35))
                        elif i - 1 < len(transitions):
                            boundary = transitions[i - 1]
                            boundary_type = boundary.get("type", "cut") if isinstance(boundary, dict) else str(boundary)
                            if boundary_type != "cut" and isinstance(boundary, dict):
                                boundary_overlap = float(boundary.get("duration") or 0.0)
                    seg_start = acc - boundary_overlap if i > 0 else 0.0
                    span = max(0.05, float(c.get("trim_end", 0.0)) - float(c.get("trim_start", 0.0)))
                    spd = float(c.get("speed", 1.0))
                    dur = span / spd
                    seg_end = seg_start + dur
                    acc = seg_end

                tail_gap = round(float(ctx.total_duration) - acc, 3)
                if abs(tail_gap) >= 0.01:
                    last_clip = actual_clip_list[-1]
                    last_dur = max(0.2, float(last_clip.get("duration", 0.0)) + tail_gap)
                    last_clip["duration"] = round(last_dur, 3)
                    last_spd = float(last_clip.get("speed", 1.0))
                    if last_clip.get("trim_end") is not None:
                        last_clip["trim_end"] = round(float(last_clip["trim_start"]) + (last_dur * last_spd), 3)

        # Opt-in LUT styling
        resolved_lut = AssetRegistry.resolve_lut_path(ctx.lut_name) if ctx.lut_name else None
        if ctx.lut_name and not resolved_lut:
            print(f"   ⚠️  ไม่พบไฟล์ฟิลเตอร์ (LUT) ชื่อ {ctx.lut_name} -- ข้ามการเกรดสี")
        lut_path = str(resolved_lut) if resolved_lut else None

        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        if ctx.export_mp4:
            ctx.notify("✂️ [5/5] เริ่มต้นตัดต่อวิดีโอ 9:16 + Punch-Zoom...", 0.85)
            print("\n✂️ [5/5] Cutting Video, Dynamic Punch-Zooming & Rendering Final MP4...")
            suffix = "_draft" if ctx.export_preset == "draft" else ""
            out_mp4 = EXPORTS_DIR / f"{ctx.project_name}_{timestamp_str}{suffix}.mp4"

            def on_ffmpeg_progress(curr_sec: float, tot_sec: float):
                ratio = min(1.0, max(0.0, curr_sec / max(0.1, tot_sec)))
                overall = round(0.85 + (ratio * 0.13), 3)
                pct_num = int(ratio * 100)
                ctx.notify(
                    f"✂️ [5/5] กำลังเรนเดอร์วิดีโอ 1080x1920... {curr_sec:.1f}s / {tot_sec:.1f}s ({pct_num}%)",
                    overall
                )

            # Use pipeline module reference so unittest.mock.patch('scripts.pipeline.VideoEditor.assemble_tiktok_video') works
            import scripts.pipeline as pipeline_mod
            # The clip bus is mixed inside VideoEditor, after the voice/BGM/SFX
            # stage. Preserve the saved slider values and mute only the copy
            # passed to this render.
            # Opt-in auto color matching
            enable_color_match = getattr(ctx, "enable_color_match", False) or (
                (ctx.manifest.get("render_params") or {}).get("enable_color_match", False) if ctx.manifest else False
            )
            color_matched_clips = actual_clip_list
            if enable_color_match and actual_clip_list and len(actual_clip_list) > 1:
                try:
                    from scripts.color_match import plan_color_match, apply_corrections
                    plan = plan_color_match(actual_clip_list)
                    if plan.get("corrections"):
                        color_matched_clips = apply_corrections(actual_clip_list, plan["corrections"])
                        print(f"   🎨 Auto Color Match: ปรับสีและแสงเทียบ Anchor สำเร็จ {len(plan['corrections'])} คลิป")
                except Exception as e:
                    print(f"   ⚠️ Auto Color Match ข้ามการทำงาน: {e}")

            render_clip_list = color_matched_clips
            if color_matched_clips and (ctx.audio_mutes or {}).get("clip"):
                render_clip_list = [{**clip, "volume": 0.0} for clip in color_matched_clips]
            assemble_kwargs = dict(
                raw_video_paths=[str(ctx.raw_video)] if ctx.raw_video else [],
                total_duration=ctx.total_duration,
                mixed_audio_path=str(ctx.mixed_audio_path),
                ass_subtitle_path=str(ctx.ass_sub_path),
                output_mp4_path=str(out_mp4),
                cues=ctx.micro_cues,
                ai_matched_shots=ctx.ai_matched_shots,
                sticker_path=ctx.sticker_path,
                lut_path=lut_path,
                lut_intensity=ctx.lut_intensity,
                shot_scales=ctx.shot_scales,
                clip_list=render_clip_list,
                transitions=transitions,
                export_preset=ctx.export_preset,
                sticker_position=ctx.sticker_position,
                sticker_scale=ctx.sticker_scale,
                sticker_start_time=ctx.sticker_start_time,
                sticker_end_time=ctx.sticker_end_time,
                sticker_norm_x=ctx.sticker_norm_x,
                sticker_norm_y=ctx.sticker_norm_y,
                stickers=ctx.stickers,
                effects=ctx.effects,
                style_preset=ctx.style_preset,
                scrim_spans=ctx.scrim_spans,
                progress_callback=on_ffmpeg_progress,
                cancel_event=ctx.cancel_event,
            )
            # The renderer seam is intentionally capability-detected.  This
            # round may run beside an older VideoEditor that cannot consume
            # SpotlightV1 yet; disabled/default requests therefore preserve
            # the exact legacy call, while a future renderer receives only the
            # normalized contract (never a raw filter string).
            try:
                signature = inspect.signature(pipeline_mod.VideoEditor.assemble_tiktok_video)
                accepts_spotlight = (
                    "spotlight" in signature.parameters
                    or any(
                        parameter.kind is inspect.Parameter.VAR_KEYWORD
                        for parameter in signature.parameters.values()
                    )
                )
            except (TypeError, ValueError):
                accepts_spotlight = False
            if accepts_spotlight and spotlight.get("enabled"):
                assemble_kwargs["spotlight"] = spotlight
            elif spotlight.get("enabled"):
                print("   ⚠️ VideoEditor รุ่นปัจจุบันยังไม่รองรับ SpotlightV1 — ข้ามเอฟเฟกต์อย่างปลอดภัย")
            if background_isolation is not None:
                assemble_kwargs["background_isolation"] = background_isolation
            assembly_started_at = time.perf_counter()
            try:
                pipeline_mod.VideoEditor.assemble_tiktok_video(**assemble_kwargs)
            finally:
                elapsed = round(max(0.0, time.perf_counter() - assembly_started_at), 3)
                ctx.stage_timings["ffmpeg_assembly"] = elapsed
                print(f"   [PERF] ffmpeg_assembly: {elapsed:.3f}s")
            ctx.result_paths["mp4_video"] = str(out_mp4)
            ctx.result_paths["ai_matched_shots"] = ctx.ai_matched_shots
            ctx.notify("🎉 การตัดต่อและเรนเดอร์เสร็จสมบูรณ์ 100%!", 1.0)
            print(f"   🎉 FINAL MP4 READY: {out_mp4}")

        export_id = None
        if ctx.result_paths.get("mp4_video"):
            export_record = ExportRegistry.ensure(
                ctx.result_paths["mp4_video"],
                product_id=ctx.product_id,
                angle_id=ctx.angle_id,
                project_name=ctx.project_name,
                status="rendered",
            )
            export_id = export_record["id"]
            ctx.result_paths["export_id"] = export_id

        # Persist manifest
        artifacts = {
            "voice_audio": {"path": str(ctx.voice_audio_path)},
            "subtitles_ass": {"path": str(ctx.ass_sub_path)},
        }
        if ctx.mixed_audio_path and Path(ctx.mixed_audio_path).exists():
            artifacts["mixed_audio"] = {"path": str(ctx.mixed_audio_path)}
        if ctx.result_paths.get("mp4_video"):
            artifacts["mp4_video"] = {
                "path": ctx.result_paths["mp4_video"],
                "export_id": export_id,
            }

        manifest_fields = {
            "export_id": export_id,
            "script_data": ctx.script_data,
            "cues": ctx.cues,
            "micro_cues": ctx.micro_cues,
            "beat_cues": ctx.beat_cues,
            "editorial_pacing": ctx.editorial_pacing,
            "style_preset": ctx.style_preset,
            "color_theme": color_theme,
            "spotlight": spotlight,
            "total_duration": ctx.total_duration,
            "clip_list": actual_clip_list,
            "transitions": transitions,
            "overlays": ctx.effective_overlays,
            "render_params": {
                "product_name": ctx.product_name,
                "style_preset": ctx.style_preset,
                "color_theme": color_theme,
                "color_theme_input": ctx.color_theme,
                "spotlight": spotlight,
                "raw_video_path": str(ctx.raw_video),
                "key_features": ctx.key_features,
                "pain_point": ctx.pain_point,
                "price_deal": ctx.price_deal,
                "overlays": ctx.effective_overlays,
                "custom_script": ctx.custom_script,
                "script_overlays": ctx.script_overlays,
                "voice": ctx.voice,
                "voice_rate": ctx.voice_rate,
                "voice_engine_type": ctx.voice_engine_type,
                "voice_engine_used": ctx.voice_engine_used,
                "voice_preset": ctx.voice_preset,
                "ad_tone": ctx.ad_tone,
                "human_voice_audio_path": ctx.human_voice_audio_path,
                "font_name": ctx.font_name,
                "bilingual_subtitles": ctx.bilingual_subtitles,
                "sticker_path": ctx.sticker_path,
                "bgm_name": ctx.effective_bgm_name or ctx.bgm_name,
                "bgm_volume": ctx.bgm_volume,
                "bgm_ducking": ctx.bgm_ducking,
                "audio_mutes": ctx.audio_mutes or {},
                "product_id": ctx.product_id,
                "angle_id": ctx.angle_id,
                "caption_position": ctx.caption_position,
                "caption_color": ctx.caption_color,
                "caption_scale": ctx.caption_scale,
                "sticker_position": ctx.sticker_position,
                "sticker_scale": ctx.sticker_scale,
                "sticker_start_time": ctx.sticker_start_time,
                "sticker_end_time": ctx.sticker_end_time,
                "sticker_norm_x": ctx.sticker_norm_x,
                "sticker_norm_y": ctx.sticker_norm_y,
                "stickers": ctx.stickers,
                "lut_name": ctx.lut_name,
                "lut_intensity": ctx.lut_intensity,
                "clip_list": actual_clip_list,
                "transitions": transitions,
                "text_overlays": ctx.effective_text_overlays,
                "callouts_materialized": getattr(ctx, "callouts_materialized", False),
            },
            "artifacts": artifacts,
            "text_overlays": ctx.effective_text_overlays,
            "callouts_materialized": getattr(ctx, "callouts_materialized", False),
        }
        performance = {
            "schema_version": 1,
            "stage_seconds": dict(ctx.stage_timings),
        }
        if ctx.pipeline_started_at is not None:
            performance["pipeline_elapsed_s"] = round(
                max(0.0, time.perf_counter() - ctx.pipeline_started_at), 3
            )
        manifest_fields["render_performance"] = performance
        if ctx.product_meta:
            manifest_fields["product"] = ctx.product_meta
        if ctx.angle_meta:
            manifest_fields["angle"] = ctx.angle_meta
        if background_isolation is not None:
            manifest_fields["background_isolation"] = background_isolation
            manifest_fields["render_params"]["background_isolation"] = background_isolation

        if ctx.project_name:
            ProjectManifest.save(ctx.project_name, **manifest_fields)
            ctx.result_paths["manifest"] = str(ProjectManifest.path_for(ctx.project_name))
            ctx.result_paths["clip_list"] = actual_clip_list
            ctx.result_paths["project_name"] = ctx.project_name

        ctx.notify("🎉 ตัดต่อเสร็จสมบูรณ์ 100%!", 1.0)
