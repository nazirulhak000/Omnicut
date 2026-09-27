"""
Overlay ASS Events Generator.
Unifies ASS event emission for both Hook Banner (3-tier) and Freeform Text Overlays.
Mirrored by SequencePlayer.jsx:drawOneOverlay() on the frontend.
"""

from typing import Any, Dict, List, Optional, Tuple
from scripts.asset_registry import AssetRegistry
from scripts.overlay_model import ACCENT_COLOR, overlay_kind, resolve_look
from scripts.style_motion_policy import style_visual_palette
from scripts.subtitle.badge_plate_renderer import (
    ass_colour,
    _pill_fill_to_ass,
    _ass_rounded_pill_path,
    _hook_lightsweep_event,
    _hook_accent_events,
)
from scripts.subtitle.font_metrics import (
    _measure_text_width_px,
    _hook_line_width_px,
    ass_glyph_scale,
    ass_top_anchor_offset,
    repair_thai_stacked_marks,
    thai_overlay_line_offset,
    THAI_STACKED_MARK_RAISE_EM,
)
from scripts.subtitle.motion_effects import (
    _resolve_hook_motion,
    HOOK_IN_BUILDERS,
    HOOK_LOOP_BUILDERS,
    HOOK_OUT_BUILDERS,
    _in_bounce,
    resolve_hook_in_builder,
    _loop_pulse,
    _loop_none,
    _out_fade,
)
from scripts.subtitle.motion_ass_adapter import (
    build_ass_motion_segments,
    resolve_motion_contract_id,
)
from scripts.subtitle.translation_service import ass_escape_text, wrap_text_for_ass

LINE_HEIGHT_FACTOR = 1.0

TEXT_OVERLAY_POSITIONS = {
    "top": 0.20,
    "middle": 0.50,
    "bottom": 0.72,
}


def _motion_contract_for_phase(
    source: Dict[str, Any],
    role: str,
    phase: str,
) -> Optional[Dict[str, Any]]:
    """Resolve an opt-in contract without disturbing legacy animation fields."""

    animation = source.get("anim") if isinstance(source.get("anim"), dict) else {}
    containers = [
        source.get("motion_contracts"),
        source.get("contracts"),
        animation.get("motion_contracts"),
        animation.get("contracts"),
    ]
    for container in containers:
        if not isinstance(container, dict):
            continue
        candidate = container.get(phase)
        if isinstance(candidate, dict):
            return candidate
        if isinstance(candidate, str):
            resolved = resolve_motion_contract_id(candidate, role=role, phase=phase)
            if resolved is not None:
                return dict(resolved)

    for holder in (source, animation):
        candidate = holder.get(f"{phase}_contract")
        if isinstance(candidate, dict):
            return candidate
        candidate_id = holder.get(f"{phase}_contract_id")
        if candidate_id:
            resolved = resolve_motion_contract_id(candidate_id, role=role, phase=phase)
            if resolved is not None:
                return dict(resolved)

    for holder in (source, animation):
        candidate = holder.get("motion_contract") or holder.get("contract")
        if isinstance(candidate, dict):
            if candidate.get("phase") == phase and candidate.get("role") == role:
                return candidate
        candidate_id = holder.get("motion_contract_id") or holder.get("contract_id")
        if candidate_id:
            resolved = resolve_motion_contract_id(candidate_id, role=role, phase=phase)
            if resolved is not None:
                return dict(resolved)
    return None


def _build_contract_plan(
    source: Dict[str, Any],
    role: str,
    phase: str,
    *,
    start_ms: int,
    end_ms: int,
    base_scale: float = 100.0,
    base_position: Optional[Tuple[float, float]] = None,
    canvas_px_scale: float = 1.0,
):
    """Build an opt-in plan; unknown/malformed contracts keep legacy export alive."""

    contract = _motion_contract_for_phase(source, role, phase)
    if contract is None:
        return None
    try:
        plan = build_ass_motion_segments(
            contract,
            start_ms=start_ms,
            end_ms=end_ms,
            base_scale=base_scale,
            base_position=base_position,
            canvas_px_scale=canvas_px_scale,
            unsupported="report",
        )
    except (TypeError, ValueError):
        # Project files from before the contract migration must remain
        # renderable.  The legacy builder is the compatibility fallback.
        return None
    # Geometry-dependent tracks such as reveal must use the existing
    # overlay-aware builder. Omitting an unsupported track would silently
    # turn a selected animation into no animation in the export.
    return None if plan.unsupported else plan


def _ass_plan_has_position(plan: Any) -> bool:
    if plan is None:
        return False
    tags = plan.ass
    return "\\pos(" in tags or "\\move(" in tags


def _contract_duration_ms(source: Dict[str, Any], role: str, phase: str, fallback: int) -> int:
    contract = _motion_contract_for_phase(source, role, phase)
    if not contract:
        return fallback
    try:
        return max(0, int(round(float(contract.get("duration_ms", fallback)))))
    except (TypeError, ValueError):
        return fallback


def _format_ass_time(seconds: float) -> str:
    """Format seconds into ASS time string H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _is_product_callout(item: Dict[str, Any]) -> bool:
    """Opt into the callout-only Thai mark adapter without changing legacy text."""
    return str(item.get("role") or "").strip().lower() == "product_callout"


def _repair_callout_text(text: str, enabled: bool) -> Tuple[str, List[Tuple[str, str, str]]]:
    """Return layout-preserving body text plus detached tone companions."""
    if not enabled:
        return text, []
    return repair_thai_stacked_marks(text)


def _hidden_callout_mark_text(parts: Tuple[str, str, str]) -> str:
    """Keep the original run's advances while exposing only its tone mark."""
    before, tone, after = parts
    hidden = r"{\1a&HFF&\3a&HFF&\4a&HFF&}"
    visible = r"{\bord1\shad1\1a&HFF&\3a&HFF&\4a&HFF&\t(0,70,\1a&H00&\3a&H00&\4a&H00&)}"
    return f"{hidden}{ass_escape_text(before)}{visible}{ass_escape_text(tone)}{hidden}{ass_escape_text(after)}"


def _callout_center_position(
    x: float,
    y: float,
    tone_raise: int,
    anim_in: str,
    move_dy_out: Optional[float],
    exit_start_ms: int,
    exit_end_ms: int,
) -> str:
    """Mirror the parent text event's motion with the detached tone raised."""
    raised_y = y - tone_raise
    if anim_in == "rise":
        return f"\\an5\\move({x},{y + 40 - tone_raise},{x},{raised_y},0,200)"
    if move_dy_out is not None:
        return f"\\an5\\move({x},{raised_y},{x},{raised_y + move_dy_out},{exit_start_ms},{exit_end_ms})"
    return f"\\an5\\pos({x},{raised_y})"


def _callout_word_position(
    x: float,
    y: float,
    tone_raise: int,
    anim_in: str,
    move_dy_out: Optional[float],
    exit_start_ms: int,
    exit_end_ms: int,
    word_t0: int,
    word_t1: int,
    dx: float,
    dy: float,
) -> str:
    """Word-level equivalent of ``_callout_center_position`` for \an7."""
    x += dx
    y += dy
    raised_y = y - tone_raise
    if anim_in == "rise":
        return f"\\q2\\an7\\move({x:.1f},{y + 40 - tone_raise:.1f},{x:.1f},{raised_y:.1f},{word_t0},{word_t1})"
    if move_dy_out is not None:
        return f"\\q2\\an7\\move({x:.1f},{raised_y:.1f},{x:.1f},{raised_y + move_dy_out:.1f},{exit_start_ms},{exit_end_ms})"
    return f"\\q2\\an7\\pos({x:.1f},{raised_y:.1f})"


def overlay_events(overlay: Dict[str, Any], ctx: Dict[str, Any]) -> List[str]:
    """
    Generate all ASS Dialogue events for a given overlay dictionary.
    Supports both 'hook' (3-tier product poster banner) and 'text' (single or multi-line text overlay).
    """
    if not overlay:
        return []

    handlers = {
        "hook": _hook_overlay_events,
        "text": _text_overlay_events,
    }
    handler = handlers.get(overlay_kind(overlay))
    if not handler:
        return []
    from scripts.background_isolation_compositor import subject_layer_for_overlay
    marker = "OCBEHIND" if subject_layer_for_overlay(overlay) == "behind" else "OCFRONT"
    tagged = []
    for event in handler(overlay, ctx):
        fields = event.split(",", 9)
        if event.startswith("Dialogue:") and len(fields) == 10:
            fields[4] = marker
            event = ",".join(fields)
        tagged.append(event)
    return tagged


def _hook_overlay_events(hook_overlay: Dict[str, Any], ctx: Dict[str, Any]) -> List[str]:
    events = []
    video_width = ctx.get("video_width", 1080)
    video_height = ctx.get("video_height", 1920)
    hook_fs = ctx.get("hook_fs", 75)
    hook_font = ctx.get("hook_font", "Kanit")
    caption_color = ctx.get("caption_color", "#0000E6FF")
    palette = style_visual_palette(ctx.get("style_preset"))
    accent_color = ctx.get("accent_color") or palette["accent_color"]
    canvas_px_scale = max(0.01, float(video_width) / 540.0)

    hook_start = float(hook_overlay.get("start") or 0.0)
    hook_end = float(hook_overlay.get("end") or (hook_start + 3.0))
    hook_duration = max(0.1, hook_end - hook_start)
    hook_tier_texts = [
        str((t or {}).get("text") or "") for t in (hook_overlay.get("tiers") or [])
    ]
    while len(hook_tier_texts) < 3:
        hook_tier_texts.append("")
    hook_brand, hook_model, hook_label = hook_tier_texts[:3]
    motion = _resolve_hook_motion(hook_overlay.get("anim"))
    start_t = _format_ass_time(hook_start)
    end_t = _format_ass_time(hook_end)

    exit_end_ms = int(hook_duration * 1000)
    exit_start_ms = max(120, exit_end_ms - 150)
    if exit_start_ms >= exit_end_ms:
        exit_start_ms = max(0, exit_end_ms - 50)

    tier_looks = [
        resolve_look(hook_overlay.get("look"), (t or {}).get("look"))
        for t in (hook_overlay.get("tiers") or [])
    ]
    while len(tier_looks) < 3:
        tier_looks.append(resolve_look(hook_overlay.get("look"), None))

    def tier_colour(idx: int, fallback: str) -> str:
        colour = tier_looks[idx]["color"]
        if colour == ACCENT_COLOR:
            return ass_colour(accent_color) or fallback
        return ass_colour(colour) or fallback

    brand_colour = tier_colour(0, "&H00FFFFFF")
    # The semantic accent is a style token. Explicit tier colour still wins;
    # caption colour is a separate caption contract and must not leak into a
    # hook/text overlay when the selected preset supplies its accent.
    model_colour = tier_colour(1, ass_colour(accent_color) or "&H0000E6FF")
    label_colour = tier_colour(2, "&H00E0E0E0")
    hook_tier_specs = [
        (hook_brand, int(tier_looks[0]["size_pct"]), brand_colour, 0),
        (hook_model, int(tier_looks[1]["size_pct"]), model_colour, 1),
        (hook_label, int(tier_looks[2]["size_pct"]), label_colour, 2),
    ]
    tiers = {"brand": tier_looks[0], "model": tier_looks[1], "label": tier_looks[2]}
    tier_key_by_idx = {0: "brand", 1: "model", 2: "label"}

    master_look = resolve_look(hook_overlay.get("look"), None)
    master_scale = max(0.2, min(3.0, float(master_look.get("size_pct", 100)) / 100.0))

    tier_lines = []
    model_last_line = None
    for raw_text, scale_pct, colour, tier_idx in hook_tier_specs:
        text = str(raw_text or "").strip()
        if not text:
            continue
        if tiers[tier_key_by_idx[tier_idx]]["upper"]:
            text = text.upper()
        tier_font = tier_looks[tier_idx].get("font") or hook_font
        scaled_pct = round(scale_pct * master_scale)
        tier_fs = max(16, int(round(hook_fs * scaled_pct / 100)))
        max_w_px = int(video_width * 0.85)

        # Mirrors wrapCanvasText(text, ctx, maxW) in SequencePlayer.jsx:
        # 1. Split manual line breaks (\N or \n) first.
        # 2. For each line, if advance width <= safe boundary (max_w_px * 1.01),
        #    do NOT wrap (stay on 1 line, exactly as preview canvas does).
        # 3. Only wrap lines that genuinely exceed the safe boundary.
        raw_paras = str(text).replace("\\N", "\n").split("\n")
        para_lines = []
        for para in raw_paras:
            clean = para.strip()
            if not clean:
                continue
            para_w = _measure_text_width_px(clean, tier_font, tier_fs)
            if para_w is not None and para_w <= int(max_w_px * 1.01):
                para_lines.append(clean)
            elif para_w is not None and para_w > max_w_px and len(clean) > 0:
                avg_char_w = max(1.0, para_w / len(clean))
                dyn_max_chars = max(6, int(max_w_px / avg_char_w))
                para_lines.extend(wrap_text_for_ass(clean, max_chars_per_line=dyn_max_chars).split("\\N"))
            else:
                dyn_max_chars = max(6, int(round(1550 / tier_fs)))
                para_lines.extend(wrap_text_for_ass(clean, max_chars_per_line=dyn_max_chars).split("\\N"))

        for line in para_lines:
            tier_lines.append((line, scaled_pct, colour, tier_idx))
        if tier_idx == 1 and para_lines:
            model_last_line = para_lines[-1]

    if not tier_lines:
        return []

    HOOK_COMFORTABLE_LINES = 4
    shrink = max(0.7, min(1.0, HOOK_COMFORTABLE_LINES / len(tier_lines)))

    reveal_mode = str(motion.get("reveal") or "simultaneous").strip().lower()
    is_cumulative = reveal_mode in ("cumulative", "tier_step")
    step_delay_ms = int(motion.get("step_delay_ms") or 350)

    STAGGER_STEP_MS = 150
    anim_speed = (hook_overlay.get("anim") or {}).get("speed", "normal")
    speed_factor = 0.6 if anim_speed == "fast" else (1.5 if anim_speed == "smooth" else 1.0)
    effective_stagger_ms = max(50, int(round(STAGGER_STEP_MS * speed_factor)))

    x_center = video_width // 2
    if "x" in hook_overlay and hook_overlay.get("x") is not None:
        try:
            x_center = int(round(video_width * float(hook_overlay["x"])))
        except (TypeError, ValueError):
            x_center = video_width // 2

    cursor_y = 180  # HookHeader top anchor
    if "y" in hook_overlay and hook_overlay.get("y") is not None:
        try:
            cursor_y = int(round(video_height * float(hook_overlay["y"])))
        except (TypeError, ValueError):
            cursor_y = 180
    # Canvas anchors a top-aligned hook at the em square while libass \an8
    # anchors the taller Windows line box.  The ASS style intentionally boosts
    # Fontsize to restore the em size, so remove only the added ascent here.
    cursor_y -= ass_top_anchor_offset(hook_font, hook_fs)

    # HookHeader/HookHeaderShadow/HookHeaderPill's Style Fontsize (set in
    # subtitle_engine.py's header) already carries this boost, so every
    # \fscx/\fscy this function and its builders compute below must be
    # divided by it instead of multiplied -- rasterizing the glyph fresh at
    # its boosted Fontsize instead of transforming it afterward via fscx/
    # fscy is what keeps the GPOS mark-to-mark anchor ั+่ ("นั่ง") from
    # colliding, regardless of scale or Bold (see subtitle_engine.py's
    # font_size_boosted comment for the full empirical diagnosis).
    HOOK_SCALE_BOOST = 1.0 / ass_glyph_scale(hook_font)

    in_builder = resolve_hook_in_builder(motion["in"])
    loop_builder = HOOK_LOOP_BUILDERS.get(motion["loop"], _loop_pulse)
    out_builder = HOOK_OUT_BUILDERS.get(motion["out"], _out_fade)
    is_typewriter = motion["in"] == "typewriter"

    line_records = []
    max_entry_end_ms = 0
    model_line_fs = None
    model_y = None
    for idx, (line, scale_pct, colour, tier_idx) in enumerate(tier_lines):
        layout_pct = round(scale_pct * shrink)
        # \fscx/\fscy stay at the plain (unboosted) percent now that
        # Fontsize (Style block in subtitle_engine.py) carries this font's
        # boost -- see that file's font_size_boosted comment.
        target = layout_pct
        line_fs = max(16, int(round(hook_fs * layout_pct / 100)))
        if is_cumulative:
            t0_ms = tier_idx * step_delay_ms
        else:
            t0_ms = tier_idx * effective_stagger_ms if motion["stagger"] else 0
        contract_in = _build_contract_plan(
            hook_overlay,
            "hook",
            "in",
            start_ms=t0_ms,
            end_ms=min(
                exit_start_ms,
                t0_ms + _contract_duration_ms(hook_overlay, "hook", "in", 0),
            ),
            base_scale=target,
            base_position=(x_center, cursor_y),
            canvas_px_scale=canvas_px_scale,
        )
        if contract_in is not None:
            in_tag, entry_end_ms, move_dy_in = (
                contract_in.ass,
                contract_in.window_ms["end"],
                None,
            )
            has_contract_position = _ass_plan_has_position(contract_in)
        elif is_typewriter:
            in_tag, entry_end_ms, move_dy_in = None, t0_ms + 400, None
            has_contract_position = False
        else:
            in_tag, entry_end_ms, move_dy_in = in_builder(target, t0_ms)
            has_contract_position = False
            if move_dy_in is not None:
                move_dy_in = int(round(move_dy_in * canvas_px_scale))
        max_entry_end_ms = max(max_entry_end_ms, entry_end_ms)
        tier_font = tier_looks[tier_idx].get("font") or hook_font
        line_records.append({
            "line": line, "target": target, "line_fs": line_fs, "colour": colour,
            "tier": tier_key_by_idx[tier_idx], "tier_idx": tier_idx,
            "tier_font": tier_font,
            "t0_ms": t0_ms, "in_tag": in_tag, "entry_end_ms": entry_end_ms,
            "move_dy_in": move_dy_in,
            # Canvas keeps one em-sized line box while libass positions the
            # Thai mark ink higher inside that box.  Apply the measured
            # optical correction to the ASS line position only; line spacing,
            # font metrics and the canonical text remain unchanged.
            "y": cursor_y + thai_overlay_line_offset(line, line_fs),
            "has_contract_position": has_contract_position,
        })
        if tier_idx == 1:
            model_line_fs = line_fs
            model_y = cursor_y
        cursor_y += round(line_fs * LINE_HEIGHT_FACTOR)

        is_last_model_line = tier_idx == 1 and (
            idx + 1 >= len(tier_lines) or tier_lines[idx + 1][3] != 1
        )
        if is_last_model_line and motion["accent"] != "none":
            reserve = 0.22 if motion["accent"] != "badge" else 0.08
            cursor_y += round(line_fs * reserve)

    contract_out_duration = _contract_duration_ms(
        hook_overlay,
        "hook",
        "out",
        max(0, exit_end_ms - exit_start_ms),
    )
    contract_exit_start_ms = (
        max(0, exit_end_ms - contract_out_duration)
        if _motion_contract_for_phase(hook_overlay, "hook", "out") is not None
        else exit_start_ms
    )
    contract_loop = _build_contract_plan(
        hook_overlay,
        "hook",
        "loop",
        start_ms=max_entry_end_ms,
        end_ms=contract_exit_start_ms,
        canvas_px_scale=canvas_px_scale,
    )
    loop_tag = contract_loop.ass if contract_loop is not None else loop_builder(max_entry_end_ms, exit_start_ms)

    for rec in line_records:
        contract_out = _build_contract_plan(
            hook_overlay,
            "hook",
            "out",
            start_ms=contract_exit_start_ms,
            end_ms=exit_end_ms,
            base_scale=rec["target"],
            base_position=(x_center, rec["y"]),
            canvas_px_scale=canvas_px_scale,
        )
        if contract_out is not None:
            out_tag, move_dy_out = contract_out.ass, None
            has_contract_out_position = _ass_plan_has_position(contract_out)
        else:
            out_tag, move_dy_out = out_builder(exit_start_ms, exit_end_ms, rec["target"])
            has_contract_out_position = False
            if move_dy_out is not None:
                move_dy_out = int(round(move_dy_out * canvas_px_scale))

        if is_typewriter:
            half_w = _hook_line_width_px(rec["line"], hook_font, rec["line_fs"])
            # Full vertical clearance (0 to video_height) so typewriter reveals left-to-right
            # without clipping font ascenders, descenders, or boosted glyph heights.
            top, bot = 0, video_height
            x_from, x_to = x_center - half_w, x_center + half_w
            in_tag = (
                f"\\clip({x_from:.0f},{top},{x_from:.0f},{bot})"
                f"\\t({rec['t0_ms']},{rec['entry_end_ms']},"
                f"\\clip({x_from:.0f},{top},{x_to:.0f},{bot}))"
            )
            if is_cumulative and rec["t0_ms"] > 0:
                in_tag = f"\\alpha&HFF&\\t({rec['t0_ms']},{rec['t0_ms']},\\alpha&H00&)" + in_tag
        else:
            in_tag = rec["in_tag"]
            if is_cumulative and rec["t0_ms"] > 0 and "\\alpha&HFF&" not in in_tag:
                in_tag = f"\\alpha&HFF&\\t({rec['t0_ms']},{rec['t0_ms']},\\alpha&H00&)" + in_tag

        if rec["has_contract_position"] or has_contract_out_position:
            pos_tag = ""
        elif rec["move_dy_in"] is not None:
            pos_tag = (
                f"\\move({x_center},{rec['y'] + rec['move_dy_in']},"
                f"{x_center},{rec['y']},{rec['t0_ms']},{rec['entry_end_ms']})"
            )
        elif move_dy_out is not None:
            pos_tag = (
                f"\\move({x_center},{rec['y']},{x_center},{rec['y'] + move_dy_out},"
                f"{exit_start_ms},{exit_end_ms})"
            )
        else:
            pos_tag = f"\\pos({x_center},{rec['y']})"
        font_override = f"\\fn{rec['tier_font']}" if rec.get("tier_font") and rec["tier_font"] != hook_font else ""
        tier_style = tiers[rec["tier"]]
        style_tags = ""
        if tier_style.get("bold"):
            style_tags += "\\b1"
        if tier_style.get("italic"):
            style_tags += "\\i1"
        if tier_style.get("underline"):
            style_tags += "\\u1"
        common = f"\\an8{pos_tag}{font_override}{style_tags}{in_tag}{loop_tag}{out_tag}"
        outline_colour = ass_colour(tier_style["outline_color"]) or "&H00000000"
        edge_tag = (
            f"\\3c{outline_colour}&"
            f"\\bord{float(tier_style['outline_px']):.1f}"
        )
        pill = tier_style["pill"] or {}
        if isinstance(pill, str):
            pill = {"fill": pill, "border": None, "pad_x_em": 0.342, "pad_y_em": 0.171}
        pill_colour = ass_colour(pill.get("fill"))
        if pill_colour:
            pill_pad = int(round(hook_fs * float(pill.get("pad_x_em") or 0.342)))
            edge_tag = f"\\3c{pill_colour}&\\bord{pill_pad}\\shad0"
            # BorderStyle 3 paints it with the outline colour.
            #
            # rec["line"] stays unescaped everywhere above (width measurement,
            # typewriter \clip math) and only gets escaped right here, at the
            # last moment it is embedded after a `{...}` override block --
            # product/brand/model/label text is scraper- and user-controlled,
            # so a literal `{`/`}`/`\` in it must never be read as its own
            # override tag by libass.
            events.append(
                f"Dialogue: 1,{start_t},{end_t},HookHeaderPill,,0,0,0,,"
                f"{{{common}{edge_tag}\\c{rec['colour']}&}}{ass_escape_text(rec['line'])}"
            )

        shadow_alpha = (
            f"\\alpha&HFF&\\t({rec['t0_ms']},{rec['t0_ms']},\\alpha&H40&)"
            if (is_cumulative and rec["t0_ms"] > 0)
            else "\\alpha&H40&"
        )
        events.append(
            f"Dialogue: 1,{start_t},{end_t},HookHeaderShadow,,0,0,0,,"
            f"{{{common}\\blur5{shadow_alpha}}}{ass_escape_text(rec['line'])}"
        )
        events.append(
            f"Dialogue: 2,{start_t},{end_t},HookHeader,,0,0,0,,"
            f"{{{common}{edge_tag}\\c{rec['colour']}&}}{ass_escape_text(rec['line'])}"
        )

        if motion["loop"] == "lightsweep":
            sweep = _hook_lightsweep_event(
                rec["line"], rec["line_fs"], rec["y"], x_center, hook_font,
                start_t, end_t, max_entry_end_ms, exit_start_ms, exit_end_ms,
                rec["target"],
            )
            if sweep:
                events.append(sweep)

    if motion["accent"] != "none" and model_last_line and model_line_fs:
        accent_color_override = (hook_overlay.get("look") or {}).get("accent_color") or (tier_looks[1] or {}).get("accent_color") or (motion or {}).get("accent_color")
        resolved_accent_colour = ass_colour(accent_color_override) if accent_color_override else model_colour
        model_reveal_start = (1 * step_delay_ms) if is_cumulative else None
        events.extend(_hook_accent_events(
            motion["accent"], model_last_line, model_line_fs, model_y, resolved_accent_colour,
            x_center, hook_font, start_t, end_t,
            exit_start_ms, exit_end_ms, motion["stagger"],
            reveal_start=model_reveal_start,
        ))

    return events


def _text_overlay_events(item: Dict[str, Any], ctx: Dict[str, Any]) -> List[str]:
    events = []
    is_product_callout = _is_product_callout(item)
    video_width = ctx.get("video_width", 1080)
    video_height = ctx.get("video_height", 1920)
    base_fs = ctx.get("base_fs", 50)
    resolved_font = ctx.get("resolved_font", "Kanit")
    font_map = ctx.get("font_map", {})
    caption_color = ctx.get("caption_color", "#0000E6FF")
    palette = style_visual_palette(ctx.get("style_preset"))
    accent_color = ctx.get("accent_color") or palette["accent_color"]
    canvas_px_scale = max(0.01, float(video_width) / 540.0)

    look = resolve_look(item.get("look"), ((item.get("tiers") or [{}])[0] or {}).get("look"))
    txt = str(((item.get("tiers") or [{}])[0] or {}).get("text") or item.get("text") or "").strip()
    if look["upper"]:
        txt = txt.upper()
    if not txt:
        return []

    try:
        start_sec = float(item.get("start", 0.0))
    except (TypeError, ValueError):
        start_sec = 0.0
    try:
        end_sec = float(item.get("end", start_sec + 2.5))
    except (TypeError, ValueError):
        end_sec = start_sec + 2.5
    if end_sec <= start_sec:
        end_sec = start_sec + 1.0

    start_t = _format_ass_time(start_sec)
    end_t = _format_ass_time(end_sec)

    if "x" in item and item.get("x") is not None and "y" in item and item.get("y") is not None:
        try:
            x_pos = int(round(video_width * float(item["x"])))
            y_pos = int(round(video_height * float(item["y"])))
        except (TypeError, ValueError):
            pos = item.get("position", "middle")
            y_ratio = TEXT_OVERLAY_POSITIONS.get(pos, 0.50)
            y_pos = int(round(video_height * y_ratio))
            x_pos = video_width // 2
    else:
        pos = item.get("position", "middle")
        y_ratio = TEXT_OVERLAY_POSITIONS.get(pos, 0.50)
        y_pos = int(round(video_height * y_ratio))
        x_pos = video_width // 2

    scale = min(2.5, max(0.4, float(look["size_pct"]) / 100.0))
    colour_value = look["color"]
    if colour_value == ACCENT_COLOR:
        colour_value = accent_color
    color_hex = ass_colour(colour_value) or "&H00FFFFFF"
    outline_hex = ass_colour(look["outline_color"]) or "&H00000000"
    outline_px = float(look["outline_px"])
    item_font = font_map.get(look["font"], look["font"])
    if item_font not in {f["family"] for f in AssetRegistry.fonts()}:
        item_font = resolved_font
    pill = look["pill"] or None
    anim_data = item.get("anim") or {}
    anim_in = anim_data.get("in") or "snap"
    anim_loop = anim_data.get("loop") or "none"
    anim_out = anim_data.get("out") or "fade"
    word_stagger_ms = int(anim_data.get("word_stagger_ms") or 0)

    skew = float(look.get("skew") or 0.0)
    skew_tag = f"\\fax{skew:.2f}" if abs(skew) > 0.001 else ""

    dur_ms = int(round((end_sec - start_sec) * 1000))
    exit_end_ms = dur_ms
    exit_start_ms = max(120, exit_end_ms - 150)
    if exit_start_ms >= exit_end_ms:
        exit_start_ms = max(0, exit_end_ms - 50)

    # Fontsize can't be boosted at the shared TextOverlayMain/Pill Style
    # level per-item (each item can carry its own font), so a per-event \fs
    # override carries this item's own boost instead. \fscx/\fscy below stay
    # at the plain (unboosted) percent -- used to be multiplied by a flat
    # 1.08 regardless of the item's actual font, which was itself a latent
    # bug -- since rasterizing fresh at the boosted Fontsize instead of
    # transforming the glyph afterward via fscx/fscy is what keeps the GPOS
    # mark-to-mark anchor ั+่ ("นั่ง") from colliding (see subtitle_engine.py's
    # font_size_boosted comment).
    item_boost = 1.0 / ass_glyph_scale(item_font)
    item_fs = int(round(base_fs * item_boost))
    fs_tag = f"\\fs{item_fs}"
    target_scale = int(round(100 * scale))
    pos_tag = f"\\an5\\pos({x_pos},{y_pos})"

    in_dur_map = {
        "snap": 70, "pop_zoom": 100, "stamp": 80, "quick_fade": 150, "rise": 200, "none": 0,
        "bounce": 450, "bounce_soft": 450, "pop": 200, "pop_soft": 200, "fade": 250, "zoom": 300,
        "slide_up": 300, "blur": 350,
    }
    in_dur = in_dur_map.get(anim_in, 100)
    contract_in = _build_contract_plan(
        item,
        "text",
        "in",
        start_ms=0,
        end_ms=_contract_duration_ms(item, "text", "in", in_dur),
        base_scale=target_scale,
        base_position=(x_pos, y_pos),
        canvas_px_scale=canvas_px_scale,
    )
    if contract_in is not None:
        in_dur = contract_in.window_ms["end"] - contract_in.window_ms["start"]

    anim = anim_in
    contract_in_has_position = False
    if contract_in is not None:
        anim_tag = contract_in.ass
        contract_in_has_position = _ass_plan_has_position(contract_in)
    elif anim == "snap":
        snap_from = int(round(target_scale * 1.25))
        anim_tag = f"\\fscx{snap_from}\\fscy{snap_from}\\t(0,70,\\fscx{target_scale}\\fscy{target_scale})"
        contract_in_has_position = False
    elif anim == "pop_zoom":
        snap_from = int(round(target_scale * 1.45))
        anim_tag = f"\\fscx{snap_from}\\fscy{snap_from}\\t(0,100,\\fscx{target_scale}\\fscy{target_scale})"
    elif anim == "stamp":
        snap_from = int(round(target_scale * 1.65))
        anim_tag = f"\\fscx{snap_from}\\fscy{snap_from}\\t(0,80,\\fscx{target_scale}\\fscy{target_scale})"
    elif anim == "quick_fade":
        anim_tag = f"\\fscx{target_scale}\\fscy{target_scale}\\alpha&HFF&\\t(0,150,\\alpha&H00&)"
    elif anim == "rise":
        rise_dy = int(round(40 * canvas_px_scale))
        pos_tag = f"\\an5\\move({x_pos},{y_pos + rise_dy},{x_pos},{y_pos},0,200)"
        anim_tag = f"\\fscx{target_scale}\\fscy{target_scale}\\alpha&HFF&\\t(0,200,\\alpha&H00&)"
        contract_in_has_position = False
    else:  # none or other
        anim_tag = f"\\fscx{target_scale}\\fscy{target_scale}"
        contract_in_has_position = False

    render_fs = int(round(base_fs * scale))
    line_list = [l.strip() for l in txt.split("\n") if l.strip()]
    clean_lines = "\\N".join(line_list)
    # The canvas uses the em-sized render mirror (25px at 1080p); this is the
    # corresponding PlayRes-sized optical raise for the detached tone event.
    # Do not apply this to legacy text overlays: their existing glyph output is
    # part of the compatibility contract.
    tone_raise = max(6, int(round(render_fs * THAI_STACKED_MARK_RAISE_EM)))

    from scripts.subtitle.word_layout import layout_overlay
    overlay_layout = item.get("layout")
    if not overlay_layout:
        overlay_layout = layout_overlay(
            text=txt,
            font_name=item_font,
            font_size_px=render_fs,
            norm_x=x_pos / video_width,
            norm_y=y_pos / video_height,
            video_w=video_width,
            video_h=video_height,
        )
        item["layout"] = overlay_layout

    lines_data = overlay_layout.get("lines", [])
    has_words = any(line.get("words") for line in lines_data)

    total_words_count = sum(len(line_info.get("words", [])) for line_info in lines_data)
    if word_stagger_ms > 0 and total_words_count > 0:
        max_entry_end_ms = (total_words_count - 1) * word_stagger_ms + in_dur
    else:
        max_entry_end_ms = in_dur
    contract_out_duration = _contract_duration_ms(
        item,
        "text",
        "out",
        max(0, exit_end_ms - exit_start_ms),
    )
    contract_exit_start_ms = (
        max(0, exit_end_ms - contract_out_duration)
        if _motion_contract_for_phase(item, "text", "out") is not None
        else exit_start_ms
    )
    max_entry_end_ms = min(max_entry_end_ms, contract_exit_start_ms)

    loop_builder = HOOK_LOOP_BUILDERS.get(anim_loop, _loop_none)
    contract_loop = _build_contract_plan(
        item,
        "text",
        "loop",
        start_ms=max_entry_end_ms,
        end_ms=contract_exit_start_ms,
        base_scale=target_scale,
        base_position=(x_pos, y_pos),
        canvas_px_scale=canvas_px_scale,
    )
    loop_tag = contract_loop.ass if contract_loop is not None else loop_builder(max_entry_end_ms, exit_start_ms)

    out_builder = HOOK_OUT_BUILDERS.get(anim_out, _out_fade)
    contract_out = _build_contract_plan(
        item,
        "text",
        "out",
        start_ms=contract_exit_start_ms,
        end_ms=exit_end_ms,
        base_scale=target_scale,
        base_position=(x_pos, y_pos),
        canvas_px_scale=canvas_px_scale,
    )
    if contract_out is not None:
        out_tag, move_dy_out = contract_out.ass, None
        contract_out_has_position = _ass_plan_has_position(contract_out)
    else:
        out_tag, move_dy_out = out_builder(exit_start_ms, exit_end_ms, target_scale)
        contract_out_has_position = False
        if move_dy_out is not None:
            move_dy_out = int(round(move_dy_out * canvas_px_scale))

    # Layer 3: a rounded pill behind the block, when the look has one
    if pill and line_list:
        line_h = round(render_fs * LINE_HEIGHT_FACTOR)
        total_h = len(line_list) * line_h
        max_line_w = 0
        for l in line_list:
            w = _measure_text_width_px(l, item_font, render_fs)
            if w is None:
                w = int(len(l) * render_fs * 0.55)
            if w > max_line_w:
                max_line_w = w
        pad_x = round(render_fs * float(pill.get("pad_x_em") or 0.6))
        pad_y = round(render_fs * float(pill.get("pad_y_em") or 0.35))
        pill_w = max_line_w + pad_x * 2
        pill_h = total_h + pad_y * 2
        pill_x = x_pos - pill_w / 2
        pill_y = y_pos - total_h / 2 - pad_y
        radius = min(round(pill_h / 2), 28)
        pill_path = _ass_rounded_pill_path(pill_w, pill_h, radius)

        pill_hex, pill_opacity = _pill_fill_to_ass(pill.get("fill"))
        base_alpha = f"&H{int(round((1 - pill_opacity) * 255)):02X}&"

        if anim_in == "rise":
            pill_pos = f"\\an7\\move({pill_x:.0f},{pill_y + 40:.0f},{pill_x:.0f},{pill_y:.0f},0,200)"
            pill_anim = f"\\alpha&HFF&\\t(0,200,\\alpha{base_alpha})"
        elif move_dy_out is not None:
            pill_pos = f"\\an7\\move({pill_x:.0f},{pill_y:.0f},{pill_x:.0f},{pill_y + move_dy_out:.0f},{exit_start_ms},{exit_end_ms})"
            pill_anim = f"\\alpha{base_alpha}"
        elif anim_in == "quick_fade":
            pill_pos = f"\\an7\\pos({pill_x:.0f},{pill_y:.0f})"
            pill_anim = f"\\alpha&HFF&\\t(0,150,\\alpha{base_alpha})"
        elif anim_in in ("snap", "pop_zoom", "stamp"):
            pill_pos = f"\\an7\\pos({pill_x:.0f},{pill_y:.0f})"
            dur_anim = 70 if anim_in == "snap" else (100 if anim_in == "pop_zoom" else 80)
            pill_anim = f"\\alpha&HFF&\\t(0,{dur_anim},\\alpha{base_alpha})"
        else:  # none
            pill_pos = f"\\an7\\pos({pill_x:.0f},{pill_y:.0f})"
            pill_anim = f"\\alpha{base_alpha}"

        border_hex = ass_colour(pill.get("border")) if pill.get("border") else None
        edge = f"\\bord3\\3c{border_hex}&" if border_hex else "\\bord0"
        pill_tag = f"{pill_pos}\\p1{edge}\\shad0\\c{pill_hex}&{pill_anim}{out_tag}"
        events.append(f"Dialogue: 3,{start_t},{end_t},TextOverlayMain,,0,0,0,,{{{pill_tag}}}{pill_path}")

    font_tag = f"\\fn{item_font}{fs_tag}" if item_font else fs_tag
    outline_tag = f"\\3c{outline_hex}&\\bord{outline_px:.1f}"

    if has_words:
        line_h = round(render_fs * LINE_HEIGHT_FACTOR)
        total_h = len(lines_data) * line_h
        block_top = y_pos - total_h / 2

        shadow = look.get("shadow")
        shad_color = ass_colour(shadow.get("color")) if shadow and shadow.get("color") else None
        shad_dx = float(shadow.get("dx") or 0.0) if shadow else 0.0
        shad_dy = float(shadow.get("dy") or 0.0) if shadow else 0.0
        shad_blur = float(shadow.get("blur") or 0.0) if shadow else 0.0

        g_word_idx = 0
        for line_info in lines_data:
            line_idx = line_info.get("line_idx", 0)
            line_y = block_top + line_idx * line_h

            for word in line_info.get("words", []):
                w_x = word["abs_x"]
                w_w = word["abs_w"]
                w_text = word["text"]
                w_cx = w_x + w_w / 2.0
                w_cy = line_y + line_h / 2.0

                word_t0 = g_word_idx * word_stagger_ms if word_stagger_ms > 0 else 0
                g_word_idx += 1

                if anim_in == "rise":
                    dur = 200
                    t1 = word_t0 + dur
                    w_pos = f"\\q2\\an7\\move({w_x:.1f},{line_y + 40:.1f},{w_x:.1f},{line_y:.1f},{word_t0},{t1})"
                elif move_dy_out is not None:
                    w_pos = f"\\q2\\an7\\move({w_x:.1f},{line_y:.1f},{w_x:.1f},{line_y + move_dy_out:.1f},{exit_start_ms},{exit_end_ms})"
                else:
                    w_pos = f"\\q2\\an7\\pos({w_x:.1f},{line_y:.1f})"

                word_contract_in = _build_contract_plan(
                    item,
                    "text",
                    "in",
                    start_ms=word_t0,
                    end_ms=word_t0 + in_dur,
                    base_scale=target_scale,
                    base_position=(w_x, line_y),
                    canvas_px_scale=canvas_px_scale,
                )
                if word_contract_in is not None:
                    t1 = word_t0 + in_dur
                    w_anim = word_contract_in.ass
                    if _ass_plan_has_position(word_contract_in):
                        w_pos = "\\q2\\an7"
                elif anim_in == "snap":
                    snap_from = int(round(target_scale * 1.25))
                    dur = 70
                    t1 = word_t0 + dur
                    if word_t0 > 0:
                        w_anim = f"\\org({w_cx:.1f},{w_cy:.1f})\\alpha&HFF&\\fscx{snap_from}\\fscy{snap_from}\\t({word_t0},{word_t0+10},\\alpha&H00&)\\t({word_t0},{t1},\\fscx{target_scale}\\fscy{target_scale})"
                    else:
                        w_anim = f"\\org({w_cx:.1f},{w_cy:.1f})\\fscx{snap_from}\\fscy{snap_from}\\t(0,{dur},\\fscx{target_scale}\\fscy{target_scale})"
                elif anim_in == "pop_zoom":
                    snap_from = int(round(target_scale * 1.45))
                    dur = 100
                    t1 = word_t0 + dur
                    if word_t0 > 0:
                        w_anim = f"\\org({w_cx:.1f},{w_cy:.1f})\\alpha&HFF&\\fscx{snap_from}\\fscy{snap_from}\\t({word_t0},{word_t0+70},\\alpha&H00&)\\t({word_t0},{t1},\\fscx{target_scale}\\fscy{target_scale})"
                    else:
                        w_anim = f"\\org({w_cx:.1f},{w_cy:.1f})\\fscx{snap_from}\\fscy{snap_from}\\t(0,100,\\fscx{target_scale}\\fscy{target_scale})"
                elif anim_in == "stamp":
                    snap_from = int(round(target_scale * 1.65))
                    dur = 80
                    t1 = word_t0 + dur
                    if word_t0 > 0:
                        w_anim = f"\\org({w_cx:.1f},{w_cy:.1f})\\alpha&HFF&\\fscx{snap_from}\\fscy{snap_from}\\t({word_t0},{word_t0+15},\\alpha&H00&)\\t({word_t0},{t1},\\fscx{target_scale}\\fscy{target_scale})"
                    else:
                        w_anim = f"\\org({w_cx:.1f},{w_cy:.1f})\\fscx{snap_from}\\fscy{snap_from}\\t(0,{dur},\\fscx{target_scale}\\fscy{target_scale})"
                elif anim_in == "quick_fade":
                    dur = 150
                    t1 = word_t0 + dur
                    w_anim = f"\\fscx{target_scale}\\fscy{target_scale}\\alpha&HFF&\\t({word_t0},{t1},\\alpha&H00&)"
                elif anim_in == "rise":
                    dur = 200
                    t1 = word_t0 + dur
                    w_anim = f"\\fscx{target_scale}\\fscy{target_scale}\\alpha&HFF&\\t({word_t0},{t1},\\alpha&H00&)"
                else:  # none or other
                    if word_t0 > 0:
                        w_anim = f"\\fscx{target_scale}\\fscy{target_scale}\\alpha&HFF&\\t({word_t0},{word_t0+10},\\alpha&H00&)"
                    else:
                        w_anim = f"\\fscx{target_scale}\\fscy{target_scale}"

                # w_text is free-form user overlay text (word["abs_x"]/["abs_w"]
                # were already measured against the unescaped word by
                # layout_overlay(), so escaping only here -- at the final embed
                # -- doesn't disturb that positioning math).
                repaired_word, word_companions = _repair_callout_text(w_text, is_product_callout)
                w_text_safe = ass_escape_text(repaired_word)
                if shadow and shad_color:
                    if anim_in == "rise":
                        s_pos = f"\\q2\\an7\\move({w_x + shad_dx:.1f},{line_y + shad_dy + 40:.1f},{w_x + shad_dx:.1f},{line_y + shad_dy:.1f},{word_t0},{t1})"
                    elif move_dy_out is not None:
                        s_pos = f"\\q2\\an7\\move({w_x + shad_dx:.1f},{line_y + shad_dy:.1f},{w_x + shad_dx:.1f},{line_y + shad_dy + move_dy_out:.1f},{exit_start_ms},{exit_end_ms})"
                    else:
                        s_pos = f"\\q2\\an7\\pos({w_x + shad_dx:.1f},{line_y + shad_dy:.1f})"
                    s_tag = f"{s_pos}{font_tag}{skew_tag}{w_anim}{loop_tag}\\c{shad_color}&\\blur{shad_blur:.1f}{out_tag}"
                    events.append(f"Dialogue: 3,{start_t},{end_t},TextOverlayShadow,,0,0,0,,{{{s_tag}}}{w_text_safe}")
                    for parts in word_companions:
                        tone_s_pos = _callout_word_position(
                            w_x, line_y, tone_raise, anim_in, move_dy_out,
                            exit_start_ms, exit_end_ms, word_t0, word_t0 + in_dur,
                            shad_dx, shad_dy,
                        )
                        tone_s_tag = f"{tone_s_pos}{font_tag}{skew_tag}{w_anim}{loop_tag}\\c{shad_color}&\\blur{shad_blur:.1f}{out_tag}"
                        events.append(
                            f"Dialogue: 3,{start_t},{end_t},TextOverlayShadow,,0,0,0,,"
                            f"{{{tone_s_tag}}}{_hidden_callout_mark_text(parts)}"
                        )

                w_content_tag = f"{w_pos}{font_tag}{skew_tag}{w_anim}{loop_tag}\\c{color_hex}&{outline_tag}{out_tag}"
                events.append(f"Dialogue: 4,{start_t},{end_t},TextOverlayMain,,0,0,0,,{{{w_content_tag}}}{w_text_safe}")
                for parts in word_companions:
                    tone_pos = _callout_word_position(
                        w_x, line_y, tone_raise, anim_in, move_dy_out,
                        exit_start_ms, exit_end_ms, word_t0, word_t0 + in_dur,
                        0.0, 0.0,
                    )
                    tone_tag = f"{tone_pos}{font_tag}{skew_tag}{w_anim}{loop_tag}\\c{color_hex}&{outline_tag}{out_tag}"
                    events.append(
                        f"Dialogue: 4,{start_t},{end_t},TextOverlayMain,,0,0,0,,"
                        f"{{{tone_tag}}}{_hidden_callout_mark_text(parts)}"
                    )

        if anim_loop == "lightsweep":
            for line_info in lines_data:
                line_idx = line_info.get("line_idx", 0)
                l_y = int(round(block_top + line_idx * line_h))
                sweep = _hook_lightsweep_event(
                    line_info.get("text", ""), render_fs, l_y, x_pos, item_font,
                    start_t, end_t, max_entry_end_ms, exit_start_ms, exit_end_ms,
                    target_scale, style_name="TextOverlayMain",
                )
                if sweep:
                    events.append(sweep)
    else:
        if contract_in_has_position or contract_out_has_position:
            pos_tag = "\\an5"
        elif anim_in == "rise":
            pos_tag = f"\\an5\\move({x_pos},{y_pos + 40},{x_pos},{y_pos},0,200)"
        elif move_dy_out is not None:
            pos_tag = f"\\an5\\move({x_pos},{y_pos},{x_pos},{y_pos + move_dy_out},{exit_start_ms},{exit_end_ms})"
        else:
            pos_tag = f"\\an5\\pos({x_pos},{y_pos})"

        content_tag = f"{pos_tag}{font_tag}{skew_tag}{anim_tag}{loop_tag}\\c{color_hex}&{outline_tag}{out_tag}"
        repaired_lines = []
        line_companions = []
        for line_index, raw_line in enumerate(line_list):
            repaired_line, companions = _repair_callout_text(raw_line, is_product_callout)
            repaired_lines.append(repaired_line)
            line_companions.append((line_index, companions))
        clean_lines = "\\N".join(repaired_lines)
        events.append(f"Dialogue: 4,{start_t},{end_t},TextOverlayMain,,0,0,0,,{{{content_tag}}}{ass_escape_text(clean_lines)}")

        if is_product_callout and any(companions for _, companions in line_companions):
            line_h = round(render_fs * LINE_HEIGHT_FACTOR)
            total_h = len(line_list) * line_h
            block_top = y_pos - total_h / 2
            for line_index, companions in line_companions:
                line_y = block_top + line_index * line_h + line_h / 2
                for parts in companions:
                    tone_pos = _callout_center_position(
                        x_pos, line_y, tone_raise, anim_in, move_dy_out,
                        exit_start_ms, exit_end_ms,
                    )
                    tone_tag = f"{tone_pos}{font_tag}{skew_tag}{anim_tag}{loop_tag}\\c{color_hex}&{outline_tag}{out_tag}"
                    events.append(
                        f"Dialogue: 4,{start_t},{end_t},TextOverlayMain,,0,0,0,,"
                        f"{{{tone_tag}}}{_hidden_callout_mark_text(parts)}"
                    )

        if anim_loop == "lightsweep":
            line_h = round(render_fs * LINE_HEIGHT_FACTOR)
            total_h = len(line_list) * line_h
            b_top = y_pos - total_h / 2
            for i, l_text in enumerate(line_list):
                l_y = int(round(b_top + i * line_h))
                sweep = _hook_lightsweep_event(
                    l_text, render_fs, l_y, x_pos, item_font,
                    start_t, end_t, max_entry_end_ms, exit_start_ms, exit_end_ms,
                    target_scale, style_name="TextOverlayMain",
                )
                if sweep:
                    events.append(sweep)

    return events
