"""
Motion Effects and Animation Preset Builders for Subtitle Engine.
Constructs ASS override tags for In (entrance), Loop (hold period), and Out (exit) animations.
"""

from typing import Dict, List, Optional, Tuple

DEFAULT_HOOK_MOTION = {"in": "bounce", "stagger": True, "loop": "pulse", "out": "fade", "accent": "underline"}


def _resolve_hook_motion(hook_motion: Optional[Dict[str, object]]) -> Dict[str, object]:
    resolved = dict(DEFAULT_HOOK_MOTION)
    if hook_motion:
        for k in DEFAULT_HOOK_MOTION:
            v = hook_motion.get(k)
            if v is not None:
                resolved[k] = v
    resolved["stagger"] = bool(resolved["stagger"])
    return resolved


def _chained_keyframes(prop: str, start_ms: int, end_ms: int, seg_ms: int, values: List[str]) -> str:
    """
    Generic cycling \\t chain animating a single ASS property through `values` in order.
    """
    segs = []
    t = start_ms
    i = 0
    while t + seg_ms <= end_ms:
        segs.append(f"\\t({t},{t + seg_ms},\\{prop}{values[i % len(values)]})")
        t += seg_ms
        i += 1
    return "".join(segs)


# ---- In (entrance) builders -------------------------------------------

def _in_bounce(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    """Elastic overshoot/undershoot/settle via \\fscx/\\fscy, ~450ms."""
    target = round(target_scale_pct)
    over = round(target * 1.25)
    under = round(target * 0.92)
    settle_over = round(target * 1.05)
    t1, t2, t3, t4 = t0_ms, t0_ms + 150, t0_ms + 280, t0_ms + 380
    end_ms = t0_ms + 450
    entry_from = round(target * 0.6)
    tag = (
        f"\\fscx{entry_from}\\fscy{entry_from}"
        f"\\t({t1},{t2},\\fscx{over}\\fscy{over})"
        f"\\t({t2},{t3},\\fscx{under}\\fscy{under})"
        f"\\t({t3},{t4},\\fscx{settle_over}\\fscy{settle_over})"
        f"\\t({t4},{end_ms},\\fscx{target}\\fscy{target})"
    )
    return tag, end_ms, None


def _in_pop(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    """Snappier one-bounce version of bounce -- single overshoot, ~200ms."""
    target = round(target_scale_pct)
    over = round(target * 1.18)
    entry_from = round(target * 0.55)
    end_ms = t0_ms + 200
    tag = (
        f"\\fscx{entry_from}\\fscy{entry_from}"
        f"\\t({t0_ms},{t0_ms + 120},\\fscx{over}\\fscy{over})"
        f"\\t({t0_ms + 120},{end_ms},\\fscx{target}\\fscy{target})"
    )
    return tag, end_ms, None


def _in_fade(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    end_ms = t0_ms + 250
    tag = f"\\fscx{target}\\fscy{target}\\alpha&HFF&\\t({t0_ms},{end_ms},\\alpha&H00&)"
    return tag, end_ms, None


def _in_zoom(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    entry_from = round(target * 1.8)
    end_ms = t0_ms + 300
    tag = (
        f"\\fscx{entry_from}\\fscy{entry_from}\\alpha&HFF&"
        f"\\t({t0_ms},{t0_ms + 150},\\alpha&H00&)"
        f"\\t({t0_ms},{end_ms},\\fscx{target}\\fscy{target})"
    )
    return tag, end_ms, None


def _in_slide_up(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    end_ms = t0_ms + 300
    tag = f"\\fscx{target}\\fscy{target}\\alpha&HFF&\\t({t0_ms},{end_ms},\\alpha&H00&)"
    return tag, end_ms, 60  # slides up from 60px below


def _in_blur(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    end_ms = t0_ms + 350
    tag = (
        f"\\fscx{target}\\fscy{target}\\alpha&HFF&\\blur12"
        f"\\t({t0_ms},{end_ms},\\alpha&H00&\\blur0)"
    )
    return tag, end_ms, None


def _in_none(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    return f"\\fscx{target}\\fscy{target}", t0_ms, None


HOOK_IN_BUILDERS = {
    "bounce": _in_bounce, "pop": _in_pop, "fade": _in_fade, "zoom": _in_zoom,
    "slide_up": _in_slide_up, "blur": _in_blur, "none": _in_none,
}


# ---- Loop (hold-period) builders ---------------------------------------

def _loop_pulse(start_ms: int, exit_start_ms: int) -> str:
    """Breathing alpha oscillation, opaque <-> dim (~85% opacity), 350ms/step."""
    return _chained_keyframes("alpha", start_ms, exit_start_ms, 350, ["&H25&", "&H00&"])


def _loop_wave(start_ms: int, exit_start_ms: int) -> str:
    """
    Gentle sway via small \\frz rotation, 400ms/step.
    Signed negative angle ("-3") avoids wrapping around 180 deg.
    """
    return _chained_keyframes("frz", start_ms, exit_start_ms, 400, ["-3", "3", "0"])


def _loop_shake(start_ms: int, exit_start_ms: int) -> str:
    """Sharp jitter via \\frz, 90ms/step."""
    return _chained_keyframes("frz", start_ms, exit_start_ms, 90, ["-3", "3", "-2", "2", "0"])


def _loop_flicker(start_ms: int, exit_start_ms: int) -> str:
    """Uneven alpha flicker."""
    pattern = [(80, "&H30&"), (150, "&H00&"), (60, "&H45&"), (200, "&H00&"), (90, "&H20&"), (180, "&H00&")]
    segs = []
    t = start_ms
    i = 0
    while True:
        dur, alpha = pattern[i % len(pattern)]
        if t + dur > exit_start_ms:
            break
        segs.append(f"\\t({t},{t + dur},\\alpha{alpha})")
        t += dur
        i += 1
    return "".join(segs)


def _loop_none(start_ms: int, exit_start_ms: int) -> str:
    return ""


HOOK_LOOP_BUILDERS = {
    "pulse": _loop_pulse, "wave": _loop_wave, "shake": _loop_shake,
    "flicker": _loop_flicker, "lightsweep": _loop_none, "none": _loop_none,
}


# ---- Out (exit) builders -------------------------------------------------

def _out_fade(exit_start_ms: int, exit_end_ms: int, target_scale_pct: float) -> Tuple[str, Optional[int]]:
    return f"\\t({exit_start_ms},{exit_end_ms},\\alpha&HFF&)", None


def _out_slide(exit_start_ms: int, exit_end_ms: int, target_scale_pct: float) -> Tuple[str, Optional[int]]:
    return f"\\t({exit_start_ms},{exit_end_ms},\\alpha&HFF&)", 60


def _out_zoom(exit_start_ms: int, exit_end_ms: int, target_scale_pct: float) -> Tuple[str, Optional[int]]:
    target = round(target_scale_pct)
    grown = round(target * 1.4)
    return f"\\t({exit_start_ms},{exit_end_ms},\\fscx{grown}\\fscy{grown}\\alpha&HFF&)", None


def _out_glitch(exit_start_ms: int, exit_end_ms: int, target_scale_pct: float) -> Tuple[str, Optional[int]]:
    """Quick \\frz jitter steps packed into the short exit window, then a hard cut."""
    jitter = _chained_keyframes("frz", exit_start_ms, max(exit_start_ms + 1, exit_end_ms - 40), 40, ["-3", "3", "0"])
    return f"{jitter}\\t({exit_end_ms - 40},{exit_end_ms},\\frz0\\alpha&HFF&)", None


def _out_none(exit_start_ms: int, exit_end_ms: int, target_scale_pct: float) -> Tuple[str, Optional[int]]:
    return f"\\t({max(exit_start_ms, exit_end_ms - 1)},{exit_end_ms},\\alpha&HFF&)", None


HOOK_OUT_BUILDERS = {
    "fade": _out_fade, "slide": _out_slide, "zoom": _out_zoom,
    "glitch": _out_glitch, "none": _out_none,
}
