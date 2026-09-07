"""
Overlay ASS Events Generator.
Unifies ASS event emission for both Hook Banner (3-tier) and Freeform Text Overlays.
Mirrored by SequencePlayer.jsx:drawOneOverlay() on the frontend.
"""

from typing import Any, Dict, List, Optional
from scripts.asset_registry import AssetRegistry
from scripts.overlay_model import resolve_look, ACCENT_COLOR
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
)
from scripts.subtitle.motion_effects import (
    _resolve_hook_motion,
    HOOK_IN_BUILDERS,
    HOOK_LOOP_BUILDERS,
    HOOK_OUT_BUILDERS,
    _in_bounce,
    _loop_pulse,
    _loop_none,
    _out_fade,
)
from scripts.subtitle.translation_service import ass_escape_text, wrap_text_for_ass

LINE_HEIGHT_FACTOR = 1.0
TEXT_SCALE_BOOST = 1.08

TEXT_OVERLAY_POSITIONS = {
    "top": 0.20,
    "middle": 0.50,
    "bottom": 0.72,
}


def _format_ass_time(seconds: float) -> str:
    """Format seconds into ASS time string H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def overlay_events(overlay: Dict[str, Any], ctx: Dict[str, Any]) -> List[str]:
    """
    Generate all ASS Dialogue events for a given overlay dictionary.
    Supports both 'hook' (3-tier product poster banner) and 'text' (single or multi-line text overlay).
    """
    if not overlay:
        return []

    kind = overlay.get("kind") or overlay.get("type")
    if kind in ("hook", "hook_header"):
        return _hook_overlay_events(overlay, ctx)
    elif kind in ("text", "text_overlay"):
        return _text_overlay_events(overlay, ctx)
    return []


def _hook_overlay_events(hook_overlay: Dict[str, Any], ctx: Dict[str, Any]) -> List[str]:
    events = []
    video_width = ctx.get("video_width", 1080)
    video_height = ctx.get("video_height", 1920)
    hook_fs = ctx.get("hook_fs", 75)
    hook_font = ctx.get("hook_font", "Kanit")
    caption_color = ctx.get("caption_color", "#0000E6FF")

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
            return fallback
        return ass_colour(colour) or fallback

    brand_colour = tier_colour(0, "&H00FFFFFF")
    model_colour = tier_colour(1, ass_colour(caption_color) or "&H0000E6FF")
    label_colour = tier_colour(2, "&H00E0E0E0")
    hook_tier_specs = [
        (hook_brand, int(tier_looks[0]["size_pct"]), brand_colour, 0),
        (hook_model, int(tier_looks[1]["size_pct"]), model_colour, 1),
        (hook_label, int(tier_looks[2]["size_pct"]), label_colour, 2),
    ]
    tiers = {"brand": tier_looks[0], "model": tier_looks[1], "label": tier_looks[2]}
    tier_key_by_idx = {0: "brand", 1: "model", 2: "label"}

    tier_lines = []
    model_last_line = None
    for raw_text, scale_pct, colour, tier_idx in hook_tier_specs:
        text = str(raw_text or "").strip()
        if not text:
            continue
        if tiers[tier_key_by_idx[tier_idx]]["upper"]:
            text = text.upper()
        tier_fs = max(20, int(round(hook_fs * scale_pct / 100)))
        dyn_max_chars = max(8, int(round(2600 / tier_fs)))
        wrapped = wrap_text_for_ass(text, max_chars_per_line=dyn_max_chars)
        lines = wrapped.split("\\N")
        for line in lines:
            tier_lines.append((line, scale_pct, colour, tier_idx))
        if tier_idx == 1:
            model_last_line = lines[-1]

    if not tier_lines:
        return []

    HOOK_COMFORTABLE_LINES = 4
    shrink = max(0.7, min(1.0, HOOK_COMFORTABLE_LINES / len(tier_lines)))
    STAGGER_STEP_MS = 150
    x_center = video_width // 2
    HOOK_SCALE_BOOST = 1.0 / ass_glyph_scale(hook_font)

    in_builder = HOOK_IN_BUILDERS.get(motion["in"], _in_bounce)
    loop_builder = HOOK_LOOP_BUILDERS.get(motion["loop"], _loop_pulse)
    out_builder = HOOK_OUT_BUILDERS.get(motion["out"], _out_fade)
    is_typewriter = motion["in"] == "typewriter"

    cursor_y = 260  # HookHeader top anchor
    line_records = []
    max_entry_end_ms = 0
    model_line_fs = None
    model_y = None
    for idx, (line, scale_pct, colour, tier_idx) in enumerate(tier_lines):
        layout_pct = round(scale_pct * shrink)
        target = round(layout_pct * HOOK_SCALE_BOOST)
        line_fs = max(20, int(round(hook_fs * layout_pct / 100)))
        t0_ms = tier_idx * STAGGER_STEP_MS if motion["stagger"] else 0
        if is_typewriter:
            in_tag, entry_end_ms, move_dy_in = None, t0_ms + 400, None
        else:
            in_tag, entry_end_ms, move_dy_in = in_builder(target, t0_ms)
        max_entry_end_ms = max(max_entry_end_ms, entry_end_ms)
        line_records.append({
            "line": line, "target": target, "line_fs": line_fs, "colour": colour,
            "tier": tier_key_by_idx[tier_idx],
            "t0_ms": t0_ms, "in_tag": in_tag, "entry_end_ms": entry_end_ms,
            "move_dy_in": move_dy_in, "y": cursor_y,
        })
        if tier_idx == 1:
            model_line_fs = line_fs
            model_y = cursor_y
        cursor_y += round(line_fs * LINE_HEIGHT_FACTOR)

        is_last_model_line = tier_idx == 1 and (
            idx + 1 >= len(tier_lines) or tier_lines[idx + 1][3] != 1
        )
        if is_last_model_line and motion["accent"] != "none":
            reserve = 0.80 if motion["accent"] != "badge" else 0.45
            cursor_y += round(line_fs * reserve)

    loop_tag = loop_builder(max_entry_end_ms, exit_start_ms)

    for rec in line_records:
        out_tag, move_dy_out = out_builder(exit_start_ms, exit_end_ms, rec["target"])

        if is_typewriter:
            half_w = _hook_line_width_px(rec["line"], hook_font, rec["line_fs"])
            top, bot = rec["y"] - 5, rec["y"] + rec["line_fs"] + 5
            x_from, x_to = x_center - half_w, x_center + half_w
            in_tag = (
                f"\\clip({x_from:.0f},{top},{x_from:.0f},{bot})"
                f"\\t({rec['t0_ms']},{rec['entry_end_ms']},"
                f"\\clip({x_from:.0f},{top},{x_to:.0f},{bot}))"
            )
        else:
            in_tag = rec["in_tag"]

        if rec["move_dy_in"] is not None:
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

        common = f"\\an8{pos_tag}{in_tag}{loop_tag}{out_tag}"
        tier_style = tiers[rec["tier"]]
        outline_colour = ass_colour(tier_style["outline_color"]) or "&H00000000"
        edge_tag = (
            f"\\3c{outline_colour}&"
            f"\\bord{float(tier_style['outline_px']):.1f}"
        )
        pill = tier_style["pill"] or {}
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

        events.append(
            f"Dialogue: 1,{start_t},{end_t},HookHeaderShadow,,0,0,0,,"
            f"{{{common}\\blur5\\alpha&H40&}}{ass_escape_text(rec['line'])}"
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
        events.extend(_hook_accent_events(
            motion["accent"], model_last_line, model_line_fs, model_y, model_colour,
            x_center, hook_font, start_t, end_t,
            exit_start_ms, exit_end_ms, motion["stagger"],
        ))

    return events


def _text_overlay_events(item: Dict[str, Any], ctx: Dict[str, Any]) -> List[str]:
    events = []
    video_width = ctx.get("video_width", 1080)
    video_height = ctx.get("video_height", 1920)
    base_fs = ctx.get("base_fs", 50)
    resolved_font = ctx.get("resolved_font", "Kanit")
    font_map = ctx.get("font_map", {})
    caption_color = ctx.get("caption_color", "#0000E6FF")

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
        colour_value = caption_color
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

    target_scale = int(round(100 * scale * TEXT_SCALE_BOOST))
    pos_tag = f"\\an5\\pos({x_pos},{y_pos})"

    in_dur_map = {
        "snap": 70, "pop_zoom": 100, "stamp": 80, "quick_fade": 150, "rise": 200, "none": 0,
        "bounce": 450, "bounce_soft": 450, "pop": 200, "pop_soft": 200, "fade": 250, "zoom": 300,
        "slide_up": 300, "blur": 350,
    }
    in_dur = in_dur_map.get(anim_in, 100)

    anim = anim_in
    if anim == "snap":
        snap_from = int(round(target_scale * 1.25))
        anim_tag = f"\\fscx{snap_from}\\fscy{snap_from}\\t(0,70,\\fscx{target_scale}\\fscy{target_scale})"
    elif anim == "pop_zoom":
        snap_from = int(round(target_scale * 1.45))
        anim_tag = f"\\fscx{snap_from}\\fscy{snap_from}\\t(0,100,\\fscx{target_scale}\\fscy{target_scale})"
    elif anim == "stamp":
        snap_from = int(round(target_scale * 1.65))
        anim_tag = f"\\fscx{snap_from}\\fscy{snap_from}\\t(0,80,\\fscx{target_scale}\\fscy{target_scale})"
    elif anim == "quick_fade":
        anim_tag = f"\\fscx{target_scale}\\fscy{target_scale}\\alpha&HFF&\\t(0,150,\\alpha&H00&)"
    elif anim == "rise":
        pos_tag = f"\\an5\\move({x_pos},{y_pos + 40},{x_pos},{y_pos},0,200)"
        anim_tag = f"\\fscx{target_scale}\\fscy{target_scale}\\alpha&HFF&\\t(0,200,\\alpha&H00&)"
    else:  # none or other
        anim_tag = f"\\fscx{target_scale}\\fscy{target_scale}"

    render_fs = int(round(base_fs * scale))
    line_list = [l.strip() for l in txt.split("\n") if l.strip()]
    clean_lines = "\\N".join(line_list)

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
    max_entry_end_ms = min(max_entry_end_ms, exit_start_ms)

    loop_builder = HOOK_LOOP_BUILDERS.get(anim_loop, _loop_none)
    loop_tag = loop_builder(max_entry_end_ms, exit_start_ms)

    out_builder = HOOK_OUT_BUILDERS.get(anim_out, _out_fade)
    out_tag, move_dy_out = out_builder(exit_start_ms, exit_end_ms, target_scale)

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

    font_tag = f"\\fn{item_font}" if item_font else ""
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

                if anim_in == "snap":
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
                w_text_safe = ass_escape_text(w_text)
                if shadow and shad_color:
                    if anim_in == "rise":
                        s_pos = f"\\q2\\an7\\move({w_x + shad_dx:.1f},{line_y + shad_dy + 40:.1f},{w_x + shad_dx:.1f},{line_y + shad_dy:.1f},{word_t0},{t1})"
                    elif move_dy_out is not None:
                        s_pos = f"\\q2\\an7\\move({w_x + shad_dx:.1f},{line_y + shad_dy:.1f},{w_x + shad_dx:.1f},{line_y + shad_dy + move_dy_out:.1f},{exit_start_ms},{exit_end_ms})"
                    else:
                        s_pos = f"\\q2\\an7\\pos({w_x + shad_dx:.1f},{line_y + shad_dy:.1f})"
                    s_tag = f"{s_pos}{font_tag}{skew_tag}{w_anim}{loop_tag}\\c{shad_color}&\\blur{shad_blur:.1f}{out_tag}"
                    events.append(f"Dialogue: 3,{start_t},{end_t},TextOverlayShadow,,0,0,0,,{{{s_tag}}}{w_text_safe}")

                w_content_tag = f"{w_pos}{font_tag}{skew_tag}{w_anim}{loop_tag}\\c{color_hex}&{outline_tag}{out_tag}"
                events.append(f"Dialogue: 4,{start_t},{end_t},TextOverlayMain,,0,0,0,,{{{w_content_tag}}}{w_text_safe}")

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
        if anim_in == "rise":
            pos_tag = f"\\an5\\move({x_pos},{y_pos + 40},{x_pos},{y_pos},0,200)"
        elif move_dy_out is not None:
            pos_tag = f"\\an5\\move({x_pos},{y_pos},{x_pos},{y_pos + move_dy_out},{exit_start_ms},{exit_end_ms})"
        else:
            pos_tag = f"\\an5\\pos({x_pos},{y_pos})"

        content_tag = f"{pos_tag}{font_tag}{skew_tag}{anim_tag}{loop_tag}\\c{color_hex}&{outline_tag}{out_tag}"
        events.append(f"Dialogue: 4,{start_t},{end_t},TextOverlayMain,,0,0,0,,{{{content_tag}}}{ass_escape_text(clean_lines)}")

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
