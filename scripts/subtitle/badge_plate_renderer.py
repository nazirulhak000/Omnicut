"""
Badge, Pill, and Accent Decoration Renderer for Subtitle Engine.
Constructs vector drawing paths (\\p1) for pills, badges, shimmer lightsweeps, and glow underlines.
"""

import re
from typing import List, Optional, Tuple

from scripts.subtitle.font_metrics import _hook_line_width_px
from scripts.subtitle.translation_service import ass_escape_text


def ass_colour(hex_colour: str) -> str:
    """#RRGGBB -> &H00BBGGRR. Returns "" for anything unparseable."""
    if not hex_colour:
        return ""
    value = str(hex_colour).strip().lstrip("#")
    if len(value) != 6:
        return ""
    try:
        r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return ""
    return f"&H00{b:02X}{g:02X}{r:02X}"


def _pill_fill_to_ass(fill: Optional[str]) -> Tuple[str, float]:
    """
    A pill's CSS fill as (ASS colour, opacity 0..1).
    """
    text = (fill or "").strip()
    if not text:
        return "&H00000000", 1.0
    match = re.match(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)", text)
    if match:
        r, g, b = (int(round(float(match.group(i)))) for i in (1, 2, 3))
        alpha = float(match.group(4)) if match.group(4) is not None else 1.0
        return f"&H00{b:02X}{g:02X}{r:02X}", max(0.0, min(1.0, alpha))
    return ass_colour(text) or "&H00000000", 1.0


def _ass_rounded_pill_path(w: float, h: float, r: float) -> str:
    """
    Constructs a smooth vector rounded rectangle for ASS \\p1 drawing mode.
    Exact parity with HTML5 Canvas roundRect(x, y, w, h, radius).
    k = r * 0.5522847498.
    All coordinates are positive and anchored at top-left (\\an7).
    """
    r = max(1.0, min(r, w / 2, h / 2))
    k = r * 0.5522847498
    p = [
        f"m {r:.1f} 0",
        f"l {w - r:.1f} 0",
        f"b {w - r + k:.1f} 0 {w:.1f} {r - k:.1f} {w:.1f} {r:.1f}",
        f"l {w:.1f} {h - r:.1f}",
        f"b {w:.1f} {h - r + k:.1f} {w - r + k:.1f} {h:.1f} {w - r:.1f} {h:.1f}",
        f"l {r:.1f} {h:.1f}",
        f"b {r - k:.1f} {h:.1f} 0 {h - r + k:.1f} 0 {h - r:.1f}",
        f"l 0 {r:.1f}",
        f"b 0 {r - k:.1f} {r - k:.1f} 0 {r:.1f} 0",
    ]
    return " ".join(p)


def _hook_lightsweep_event(
    line: str, line_fs: int, y: int, x_center: int, resolved_font: str,
    start_t: str, end_t: str, sweep_start_ms: int, exit_start_ms: int, exit_end_ms: int,
    target_scale_pct: float, style_name: str = "HookHeader",
) -> Optional[str]:
    """
    Shimmer sweep: a second, brighter copy of the line drawn on top and
    clipped to a narrow vertical band that travels across it repeatedly.
    """
    half_w = _hook_line_width_px(line, resolved_font, line_fs)
    band_w = max(20, int(half_w * 0.7))
    left = x_center - half_w - band_w
    right = x_center + half_w
    top, bot = y - 5, y + line_fs + 5

    SWEEP_MS = 500
    segs = []
    t = sweep_start_ms
    while t + SWEEP_MS <= exit_start_ms:
        segs.append(f"\\t({t},{t + SWEEP_MS},\\clip({right - band_w:.0f},{top},{right:.0f},{bot}))")
        t += SWEEP_MS
        if t + 1 <= exit_start_ms:
            segs.append(f"\\t({t},{t + 1},\\clip({left:.0f},{top},{left + band_w:.0f},{bot}))")
            t += 1
    if not segs:
        return None

    target = round(target_scale_pct)
    tag = (
        f"{{\\an8\\pos({x_center},{y})\\fscx{target}\\fscy{target}"
        f"\\bord0\\shad0\\c&H00FFFFFF&\\alpha&H20&"
        f"\\clip({left:.0f},{top},{left + band_w:.0f},{bot})"
        f"{''.join(segs)}"
        f"\\t({exit_start_ms},{exit_end_ms},\\alpha&HFF&)}}"
    )
    # `line` is only measured (unescaped) above for pixel width -- escaped
    # here, at the final embed, since this text is scraper/user-controlled
    # product copy and must never be read as its own override tag.
    return f"Dialogue: 3,{start_t},{end_t},{style_name},,0,0,0,,{tag}{ass_escape_text(line)}"


def _hook_accent_events(
    accent_id: str, model_line: str, model_line_fs: int, model_y: int, model_colour: str,
    x_center: int, resolved_font: str, start_t: str, end_t: str,
    exit_start_ms: int, exit_end_ms: int, stagger: bool,
) -> List[str]:
    """
    Decorative shape tied to the model tier: an accent bar under it, or a filled badge behind it.
    """
    half_w = _hook_line_width_px(model_line, resolved_font, model_line_fs)
    reveal_start = 300 if stagger else 0
    reveal_end = reveal_start + 300
    exit_tag = f"\\t({exit_start_ms},{exit_end_ms},\\alpha&HFF&)"

    if accent_id == "badge":
        pad_x = round(model_line_fs * 0.38)
        pad_y = round(model_line_fs * 0.20)
        bw = (half_w + pad_x) * 2
        bh = model_line_fs + pad_y * 2
        r = min(12.0, bh / 3.0)
        draw = _ass_rounded_pill_path(bw, bh, r)
        tag = (
            f"{{\\an7\\pos({x_center - bw / 2:.0f},{model_y - pad_y})\\p1\\bord0\\shad0"
            f"\\c{model_colour}&\\alpha&HB0&\\fscx0"
            f"\\t({reveal_start},{reveal_end},\\fscx100){exit_tag}}}"
        )
        return [f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{tag}{draw}"]

    if accent_id == "bracket":
        pad_x = round(model_line_fs * 0.25)
        pad_y = round(model_line_fs * 0.08)
        bracket_w = max(6, round(model_line_fs * 0.16))
        thickness = max(3, round(model_line_fs * 0.08))
        h = model_line_fs + pad_y * 2
        top_y = model_y - pad_y
        left_x = x_center - half_w - pad_x
        right_x = x_center + half_w + pad_x - bracket_w
        draw_l = f"m 0 0 l {bracket_w} 0 l {bracket_w} {thickness} l {thickness} {thickness} l {thickness} {h - thickness} l {bracket_w} {h - thickness} l {bracket_w} {h} l 0 {h}"
        draw_r = f"m 0 0 l {bracket_w} 0 l {bracket_w} {h} l 0 {h} l 0 {h - thickness} l {bracket_w - thickness} {h - thickness} l {bracket_w - thickness} {thickness} l 0 {thickness}"
        reveal = f"\\alpha&HFF&\\t({reveal_start},{reveal_end},\\alpha&H00&)"
        tag_l = f"{{\\an7\\pos({left_x:.0f},{top_y})\\p1\\bord0\\shad0\\c{model_colour}&{reveal}{exit_tag}}}"
        tag_r = f"{{\\an7\\pos({right_x:.0f},{top_y})\\p1\\bord0\\shad0\\c{model_colour}&{reveal}{exit_tag}}}"
        return [
            f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{tag_l}{draw_l}",
            f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{tag_r}{draw_r}",
        ]

    if accent_id == "glow_box":
        pad_x = round(model_line_fs * 0.30)
        pad_y = round(model_line_fs * 0.12)
        bw = (half_w + pad_x) * 2
        bh = model_line_fs + pad_y * 2
        thickness = max(3, round(model_line_fs * 0.07))
        draw = f"m 0 0 l {bw:.0f} 0 l {bw:.0f} {bh:.0f} l 0 {bh:.0f} l 0 0 m {thickness} {thickness} l {thickness} {bh - thickness:.0f} l {bw - thickness:.0f} {bh - thickness:.0f} l {bw - thickness:.0f} {thickness} l {thickness} {thickness}"
        reveal = f"\\alpha&HFF&\\t({reveal_start},{reveal_end},\\alpha&H00&)"
        box_x = x_center - bw / 2
        box_y = model_y - pad_y
        glow_tag = f"{{\\an7\\pos({box_x:.0f},{box_y})\\p1\\bord0\\shad0\\blur6\\c{model_colour}&\\alpha&H60&{reveal}{exit_tag}}}"
        box_tag = f"{{\\an7\\pos({box_x:.0f},{box_y})\\p1\\bord0\\shad0\\c{model_colour}&{reveal}{exit_tag}}}"
        return [
            f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{glow_tag}{draw}",
            f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{box_tag}{draw}",
        ]

    if accent_id == "double_bar":
        gap = round(model_line_fs * 0.12)
        thickness = max(3, round(model_line_fs * 0.08))
        bar_w = half_w * 2
        left_x = x_center - half_w
        top_bar_y = model_y - gap - thickness
        bot_bar_y = model_y + model_line_fs + gap
        draw = f"m 0 0 l {bar_w:.0f} 0 l {bar_w:.0f} {thickness} l 0 {thickness}"
        reveal = f"\\fscx0\\t({reveal_start},{reveal_end},\\fscx100)"
        tag_top = f"{{\\an7\\pos({left_x:.0f},{top_bar_y})\\p1\\bord0\\shad0\\c{model_colour}&{reveal}{exit_tag}}}"
        tag_bot = f"{{\\an7\\pos({left_x:.0f},{bot_bar_y})\\p1\\bord0\\shad0\\c{model_colour}&{reveal}{exit_tag}}}"
        return [
            f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{tag_top}{draw}",
            f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{tag_bot}{draw}",
        ]

    if accent_id == "sale_tag":
        pad_x = round(model_line_fs * 0.36)
        pad_y = round(model_line_fs * 0.12)
        bw = (half_w + pad_x) * 2
        bh = model_line_fs + pad_y * 2
        notch = round(bh * 0.40)
        draw = f"m 0 {bh / 2:.1f} l {notch:.1f} 0 l {bw:.1f} 0 l {bw:.1f} {bh:.1f} l {notch:.1f} {bh:.1f} l 0 {bh / 2:.1f}"
        reveal = f"\\alpha&HFF&\\t({reveal_start},{reveal_end},\\alpha&H00&)"
        tag_x = x_center - bw / 2
        tag_y = model_y - pad_y
        tag = f"{{\\an7\\pos({tag_x:.0f},{tag_y})\\p1\\bord0\\shad0\\c{model_colour}&\\alpha&HB8&{reveal}{exit_tag}}}"
        return [f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{tag}{draw}"]

    if accent_id == "pill_badge":
        pad_x = round(model_line_fs * 0.35)
        pad_y = round(model_line_fs * 0.14)
        bw = (half_w + pad_x) * 2
        bh = model_line_fs + pad_y * 2
        r = bh / 2.0
        thickness = max(3, round(model_line_fs * 0.07))
        draw_outer = _ass_rounded_pill_path(bw, bh, r)
        reveal = f"\\alpha&HFF&\\t({reveal_start},{reveal_end},\\alpha&H00&)"
        box_x = x_center - bw / 2
        box_y = model_y - pad_y
        tag = f"{{\\an7\\pos({box_x:.0f},{box_y})\\p1\\bord{thickness}\\shad0\\3c{model_colour}&\\1a&HFF&{reveal}{exit_tag}}}"
        return [f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{tag}{draw_outer}"]

    if accent_id == "marker":
        pad_x = round(model_line_fs * 0.22)
        bw = (half_w + pad_x) * 2
        bh = round(model_line_fs * 0.46)
        marker_y = model_y + round(model_line_fs * 0.42)
        r = min(6.0, bh / 3.0)
        draw = _ass_rounded_pill_path(bw, bh, r)
        reveal = f"\\fscx0\\t({reveal_start},{reveal_end},\\fscx100)"
        tag = f"{{\\an7\\pos({x_center - bw / 2:.0f},{marker_y})\\p1\\bord0\\shad0\\c{model_colour}&\\alpha&HA0&{reveal}{exit_tag}}}"
        return [f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{tag}{draw}"]

    if accent_id == "bold_quotes":
        pad_x = round(model_line_fs * 0.28)
        quote_fs = round(model_line_fs * 1.15)
        left_x = x_center - half_w - pad_x
        right_x = x_center + half_w + round(pad_x * 0.3)
        reveal = f"\\alpha&HFF&\\t({reveal_start},{reveal_end},\\alpha&H00&)"
        tag_l = f"{{\\an7\\pos({left_x:.0f},{model_y - round(model_line_fs * 0.15)})\\fs{quote_fs}\\bord0\\shad0\\c{model_colour}&{reveal}{exit_tag}}}"
        tag_r = f"{{\\an7\\pos({right_x:.0f},{model_y - round(model_line_fs * 0.15)})\\fs{quote_fs}\\bord0\\shad0\\c{model_colour}&{reveal}{exit_tag}}}"
        return [
            f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{tag_l}“",
            f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{tag_r}”",
        ]

    if accent_id == "dashed_box":
        pad_x = round(model_line_fs * 0.28)
        pad_y = round(model_line_fs * 0.10)
        bw = (half_w + pad_x) * 2
        bh = model_line_fs + pad_y * 2
        clen = max(8, round(model_line_fs * 0.22))
        thickness = max(3, round(model_line_fs * 0.07))
        box_x = x_center - bw / 2
        box_y = model_y - pad_y
        draw_tl = f"m 0 0 l {clen} 0 l {clen} {thickness} l {thickness} {thickness} l {thickness} {clen} l 0 {clen}"
        draw_tr = f"m {bw - clen} 0 l {bw} 0 l {bw} {clen} l {bw - thickness} {clen} l {bw - thickness} {thickness} l {bw - clen} {thickness}"
        draw_bl = f"m 0 {bh - clen} l {thickness} {bh - clen} l {thickness} {bh - thickness} l {clen} {bh - thickness} l {clen} {bh} l 0 {bh}"
        draw_br = f"m {bw - clen} {bh} l {bw - clen} {bh - thickness} l {bw - thickness} {bh - thickness} l {bw - thickness} {bh - clen} l {bw} {bh - clen} l {bw} {bh}"
        draw = f"{draw_tl} {draw_tr} {draw_bl} {draw_br}"
        reveal = f"\\alpha&HFF&\\t({reveal_start},{reveal_end},\\alpha&H00&)"
        tag = f"{{\\an7\\pos({box_x:.0f},{box_y})\\p1\\bord0\\shad0\\c{model_colour}&{reveal}{exit_tag}}}"
        return [f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{tag}{draw}"]

    if accent_id == "speed_slash":
        pad_x = round(model_line_fs * 0.26)
        pad_y = round(model_line_fs * 0.08)
        h = model_line_fs + pad_y * 2
        sw = max(4, round(model_line_fs * 0.08))
        gap_s = max(3, round(model_line_fs * 0.06))
        skew_dx = round(h * 0.28)
        draw_slash = f"m {skew_dx} 0 l {skew_dx + sw} 0 l {sw} {h} l 0 {h}"
        draw_pair = f"{draw_slash} m {skew_dx + sw + gap_s} 0 l {skew_dx + sw * 2 + gap_s} 0 l {sw * 2 + gap_s} {h} l {sw + gap_s} {h}"
        pair_w = skew_dx + sw * 2 + gap_s
        left_x = x_center - half_w - pad_x - pair_w
        right_x = x_center + half_w + pad_x
        reveal = f"\\alpha&HFF&\\t({reveal_start},{reveal_end},\\alpha&H00&)"
        top_y = model_y - pad_y
        tag_l = f"{{\\an7\\pos({left_x:.0f},{top_y})\\p1\\bord0\\shad0\\c{model_colour}&{reveal}{exit_tag}}}"
        tag_r = f"{{\\an7\\pos({right_x:.0f},{top_y})\\p1\\bord0\\shad0\\c{model_colour}&{reveal}{exit_tag}}}"
        return [
            f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{tag_l}{draw_pair}",
            f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{tag_r}{draw_pair}",
        ]

    if accent_id == "gradient_line":
        gap = round(model_line_fs * 0.12)
        underline_y = model_y + model_line_fs + gap
        thickness = max(2, round(model_line_fs * 0.06))
        bar_w = half_w * 2
        left_x = x_center - half_w
        draw = f"m 0 0 l {bar_w:.0f} 0 l {bar_w:.0f} {thickness} l 0 {thickness}"
        reveal = f"\\fscx0\\t({reveal_start},{reveal_end},\\fscx100)"
        bar_tag = f"{{\\an7\\pos({left_x:.0f},{underline_y})\\p1\\bord0\\shad0\\c{model_colour}&\\alpha&H40&{reveal}{exit_tag}}}"
        return [f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{bar_tag}{draw}"]

    # Accent bar (default with glow blur behind)
    gap = round(model_line_fs * 0.12)
    underline_y = model_y + model_line_fs + gap
    thickness = max(4, round(model_line_fs * 0.10))
    bar_w = half_w * 2
    left_x = x_center - half_w
    draw = f"m 0 0 l {bar_w:.0f} 0 l {bar_w:.0f} {thickness} l 0 {thickness}"
    reveal = f"\\fscx0\\t({reveal_start},{reveal_end},\\fscx100)"
    glow_tag = (
        f"{{\\an7\\pos({left_x:.0f},{underline_y})\\p1\\bord0\\shad0\\blur7"
        f"\\c{model_colour}&\\alpha&H60&{reveal}{exit_tag}}}"
    )
    bar_tag = (
        f"{{\\an7\\pos({left_x:.0f},{underline_y})\\p1\\bord0\\shad0"
        f"\\c{model_colour}&{reveal}{exit_tag}}}"
    )
    return [
        f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{glow_tag}{draw}",
        f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{bar_tag}{draw}",
    ]
