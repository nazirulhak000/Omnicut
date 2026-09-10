"""
Subtitle Stage for OmniCut Pro Studio.
Generates animated Thai & bilingual subtitles (.ass), parses/migrates overlays, and extracts scrim spans.
"""

from typing import List, Tuple

from scripts.subtitle_engine import SubtitleEngine, subtitle_artifact_is_current
from scripts.editorial_pacing import build_pacing_plan_from_cues
from scripts.overlay_model import migrate_to_overlays
from scripts.pipeline_context import PipelineContext
from scripts.project_manifest import ProjectManifest


class SubtitleStage:
    """Creates animated ASS subtitles with kinetic micro-bursts and overlays."""

    @classmethod
    def run(cls, ctx: PipelineContext) -> None:
        scrim_spans: List[Tuple[float, float]] = []

        should_generate = ctx.should_run("subtitles")
        if not should_generate and ctx.manifest:
            existing_ass_path = ProjectManifest.artifact_path(ctx.manifest, "subtitles_ass")
            if existing_ass_path and not subtitle_artifact_is_current(existing_ass_path):
                should_generate = True

        if should_generate:
            ctx.notify("💬 [3/5] กำลังสร้างซับไตเติล TikTok เคลื่อนไหว (Kanit-Black 86pt)...", 0.50)
            print(f"\n💬 [3/5] Generating TikTok Animated Subtitles (.ass with {ctx.font_name} font & 3-word bursts)...")
            ass_path = ctx.out_path("subtitles", ".ass")

            effective_hook_brand = ctx.hook_brand
            banner_combined_len = len(" ".join(filter(None, [effective_hook_brand, ctx.hook_model, ctx.hook_label])))
            if ctx.hook_duration is not None and abs(float(ctx.hook_duration) - 3.0) > 0.01:
                effective_hook_duration = float(ctx.hook_duration)
            else:
                effective_hook_duration = max(2.0, min(banner_combined_len / 11.0 + 0.6, 5.0))
            effective_hook_duration = min(effective_hook_duration, ctx.total_duration)

            effective_text_overlays = ctx.text_overlays if ctx.text_overlays is not None else (
                (ctx.manifest.get("text_overlays") if ctx.manifest else None) or
                ((ctx.manifest.get("render_params") or {}).get("text_overlays") if ctx.manifest else None)
            )

            if ctx.overlays is not None:
                effective_overlays = ctx.overlays
            else:
                effective_overlays = migrate_to_overlays({
                    **(ctx.manifest or {}),
                    "hook_brand": effective_hook_brand,
                    "hook_model": ctx.hook_model,
                    "hook_label": ctx.hook_label,
                    "hook_duration": effective_hook_duration,
                    "hook_motion": ctx.hook_motion,
                    "hook_colors": ctx.hook_colors,
                    "hook_style": ctx.hook_style,
                    "text_overlays": effective_text_overlays,
                })

            scrim_spans = [
                (float(o.get("start") or 0.0), float(o.get("end") or 0.0))
                for o in effective_overlays
                if o.get("scrim") and not o.get("hidden")
            ]

            # Capture the optional word-level timing contract before
            # generate_ass replaces ctx.cues with micro-cues. Legacy cues
            # without word_timings intentionally produce no plan.
            ctx.editorial_pacing = build_pacing_plan_from_cues(
                ctx.cues,
                duration=ctx.total_duration,
            )

            _, micro_cues = SubtitleEngine.generate_ass(
                cues=ctx.cues,
                output_ass_path=str(ass_path),
                font_name=ctx.font_name,
                overlays=effective_overlays,
                hook_brand=effective_hook_brand,
                hook_model=ctx.hook_model,
                hook_label=ctx.hook_label,
                hook_duration=effective_hook_duration,
                hook_motion=ctx.hook_motion,
                hook_colors=ctx.hook_colors,
                hook_style=ctx.hook_style,
                bilingual=ctx.bilingual_subtitles,
                caption_position=ctx.caption_position,
                caption_color=ctx.caption_color,
                caption_scale=ctx.caption_scale,
                text_overlays=effective_text_overlays,
                style_preset=ctx.style_preset,
            )
            # Sync micro_cues back
            ctx.cues = micro_cues
            ctx.micro_cues = micro_cues
            print(f"   Subtitles created: {ass_path} ({len(micro_cues)} micro-bursts)")
        else:
            if not ctx.manifest:
                raise ValueError("Cannot reuse subtitles without manifest")
            ass_path = ctx.reuse("subtitles_ass", "ไฟล์ซับไตเติล")
            micro_cues = ctx.manifest["micro_cues"]
            saved_params = (ctx.manifest.get("render_params") or {}) if ctx.manifest else {}
            effective_overlays = ctx.overlays if ctx.overlays is not None else migrate_to_overlays(ctx.manifest or {})
            scrim_spans = [
                (float(o.get("start") or 0.0), float(o.get("end") or 0.0))
                for o in effective_overlays
                if o.get("scrim") and not o.get("hidden")
            ]
            effective_text_overlays = ctx.text_overlays if ctx.text_overlays is not None else (
                ctx.manifest.get("text_overlays") or saved_params.get("text_overlays")
            )
            ctx.micro_cues = micro_cues
            ctx.editorial_pacing = (ctx.manifest or {}).get("editorial_pacing")
            print(f"♻️  [3/5] Reusing subtitles: {ass_path.name} ({len(micro_cues)} micro-bursts)")

        ctx.ass_sub_path = ass_path
        ctx.effective_overlays = effective_overlays
        ctx.effective_text_overlays = effective_text_overlays
        ctx.scrim_spans = scrim_spans
