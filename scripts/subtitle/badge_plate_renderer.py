"""
Badge, Pill, and Accent Decoration Renderer for Subtitle Engine.
Constructs vector drawing paths (\\p1) for pills, badges, shimmer lightsweeps, and glow underlines.
"""

import re
from typing import List, Optional, Tuple

from scripts.subtitle.font_metrics import _hook_line_width_px


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
        f"\\bord0\\shad0\\c&H00FFFFFF&\\alpha&H60&"
        f"\\clip({left:.0f},{top},{left + band_w:.0f},{bot})"
        f"{''.join(segs)}"
        f"\\t({exit_start_ms},{exit_end_ms},\\alpha&HFF&)}}"
    )
    return f"Dialogue: 3,{start_t},{end_t},{style_name},,0,0,0,,{tag}{line}"


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
        draw = f"m 0 0 l {bw:.0f} 0 l {bw:.0f} {bh:.0f} l 0 {bh:.0f}"
        tag = (
            f"{{\\an7\\pos({x_center - bw / 2:.0f},{model_y - pad_y})\\p1\\bord0\\shad0"
            f"\\c{model_colour}&\\alpha&HB0&\\fscx0"
            f"\\t({reveal_start},{reveal_end},\\fscx100){exit_tag}}}"
        )
        return [f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{tag}{draw}"]

    # Accent bar (default with glow blur behind)
    gap = round(model_line_fs * 0.50)
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
