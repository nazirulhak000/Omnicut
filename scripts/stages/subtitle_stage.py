"""
Subtitle Stage for OmniCut Pro Studio.
Generates animated Thai & bilingual subtitles (.ass), parses/migrates overlays, and extracts scrim spans.
"""

import copy
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from scripts.subtitle_engine import MICRO_BURST_MAX_CHARS, SubtitleEngine, subtitle_artifact_is_current
from scripts.editorial_pacing import build_pacing_plan_from_cues
from scripts.overlay_model import guess_brand_model, migrate_to_overlays
from scripts.pipeline_context import PipelineContext
from scripts.product_callout_builder import build_product_callouts
from scripts.project_manifest import ProjectManifest


def _materialize_product_callouts(
    ctx: PipelineContext,
    effective_overlays: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Return overlays without auto-injecting unwanted callouts.
    
    Automatic product callouts (brand/model overlays in the center of the video)
    have been disabled per user request. Overlays remain strictly user-authored.
    """
    return [copy.deepcopy(dict(item)) for item in (effective_overlays or []) if isinstance(item, Mapping)]


def _first_sequence(value: Any) -> List[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _contains_on_screen(cues: Sequence[Mapping[str, Any]]) -> bool:
    return any(str(cue.get("on_screen") or "").strip() for cue in cues)


def _is_product_callout(item: Mapping[str, Any]) -> bool:
    return item.get("role") == "product_callout" and item.get("kind") == "text"


def _callout_semantic(item: Mapping[str, Any]) -> Tuple[str, str] | None:
    if not _is_product_callout(item):
        return None
    tiers = item.get("tiers")
    text = ""
    if isinstance(tiers, Sequence) and not isinstance(tiers, (str, bytes, bytearray)):
        first = tiers[0] if tiers else None
        if isinstance(first, Mapping):
            text = str(first.get("text") or "")
    if not text:
        text = str(item.get("text") or item.get("value") or "")
    callout_type = str(item.get("callout_type") or "feature").strip().casefold()
    normalized_text = " ".join(text.split()).strip().casefold()
    return (callout_type, normalized_text) if normalized_text else None


class SubtitleStage:
    """Creates animated ASS subtitles with kinetic micro-bursts and overlays."""

    @classmethod
    def run(cls, ctx: PipelineContext) -> None:
        scrim_spans: List[Tuple[float, float]] = []

        saved_params = (ctx.manifest.get("render_params") or {}) if ctx.manifest else {}
        effective_show_watermark = (
            ctx.show_watermark
            if ctx.show_watermark is not None
            else saved_params.get("show_watermark", True)
        )

        should_generate = ctx.should_run("subtitles")
        if not should_generate and ctx.manifest:
            existing_ass_path = ProjectManifest.artifact_path(ctx.manifest, "subtitles_ass")
            if existing_ass_path:
                ctx.guard_media(existing_ass_path)
                if not subtitle_artifact_is_current(existing_ass_path):
                    should_generate = True
                elif saved_params.get("show_watermark") is not None and saved_params.get("show_watermark") != effective_show_watermark:
                    should_generate = True

        if should_generate:
            ctx.notify(f"💬 [3/5] กำลังสร้างซับไตเติล TikTok เคลื่อนไหว (ฟอนต์ {ctx.font_name})...", 0.50)
            print(
                f"\n💬 [3/5] Generating TikTok Animated Subtitles (.ass, {ctx.font_name} font, "
                f"micro-burst clauses up to {MICRO_BURST_MAX_CHARS} chars, 1 highlight per burst)..."
            )
            ass_path = ctx.out_path("subtitles", ".ass")

            effective_hook_brand = ctx.hook_brand
            effective_hook_model = ctx.hook_model
            effective_hook_label = ctx.hook_label
            if (
                not (effective_hook_brand or "").strip()
                and not (effective_hook_model or "").strip()
                and not (effective_hook_label or "").strip()
            ):
                guessed_b, guessed_m = guess_brand_model(ctx.product_name)
                if guessed_b or guessed_m:
                    effective_hook_brand = guessed_b or None
                    effective_hook_model = guessed_m or None

            banner_combined_len = len(" ".join(filter(None, [effective_hook_brand, effective_hook_model, effective_hook_label])))
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
                    "hook_model": effective_hook_model,
                    "hook_label": effective_hook_label,
                    "hook_duration": effective_hook_duration,
                    "hook_motion": ctx.hook_motion,
                    "hook_colors": ctx.hook_colors,
                    "hook_style": ctx.hook_style,
                    "style_preset": ctx.style_preset,
                    "ad_tone": ctx.ad_tone,
                    "text_overlays": effective_text_overlays,
                })

            effective_overlays = _materialize_product_callouts(ctx, effective_overlays)

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
                hook_model=effective_hook_model,
                hook_label=effective_hook_label,
                hook_duration=effective_hook_duration,
                hook_motion=ctx.hook_motion,
                hook_colors=ctx.hook_colors,
                hook_style=ctx.hook_style,
                bilingual=ctx.bilingual_subtitles,
                ghost_reveal=getattr(ctx, "ghost_reveal", True),
                caption_position=ctx.caption_position,
                caption_color=ctx.caption_color,
                caption_scale=ctx.caption_scale,
                text_overlays=effective_text_overlays,
                style_preset=ctx.style_preset,
                show_watermark=effective_show_watermark,
                channel_identity_snapshot=ctx.channel_identity_snapshot,
            )
            # Sync micro_cues back
            ctx.cues = micro_cues
            ctx.micro_cues = micro_cues
            ctx.hook_brand = effective_hook_brand
            ctx.hook_model = effective_hook_model
            ctx.hook_label = effective_hook_label
            print(f"   Subtitles created: {ass_path} ({len(micro_cues)} micro-bursts)")
        else:
            if not ctx.manifest:
                raise ValueError("Cannot reuse subtitles without manifest")
            ass_path = ctx.reuse("subtitles_ass", "ไฟล์ซับไตเติล")
            micro_cues = ctx.manifest["micro_cues"]
            saved_params = (ctx.manifest.get("render_params") or {}) if ctx.manifest else {}
            effective_overlays = ctx.overlays if ctx.overlays is not None else migrate_to_overlays(ctx.manifest or {})
            effective_overlays = _materialize_product_callouts(ctx, effective_overlays)
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
        ctx.callouts_materialized = True
