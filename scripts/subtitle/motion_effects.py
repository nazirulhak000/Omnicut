"""
Motion Effects and Animation Preset Builders for Subtitle Engine.
Constructs ASS override tags for In (entrance), Loop (hold period), and Out (exit) animations.
"""

from typing import Dict, List, Optional, Tuple

DEFAULT_HOOK_MOTION = {
    "in": "bounce",
    "stagger": True,
    "loop": "pulse",
    "out": "fade",
    "accent": "underline",
    "reveal": "simultaneous",
}
DEFAULT_HOOK_STEP_DELAY_MS = 350


def _resolve_hook_motion(hook_motion: Optional[Dict[str, object]]) -> Dict[str, object]:
    resolved = dict(DEFAULT_HOOK_MOTION)
    resolved["step_delay_ms"] = DEFAULT_HOOK_STEP_DELAY_MS
    if hook_motion:
        for k in DEFAULT_HOOK_MOTION:
            v = hook_motion.get(k)
            if v is not None:
                resolved[k] = v
        if "step_delay_ms" in hook_motion and hook_motion["step_delay_ms"] is not None:
            try:
                resolved["step_delay_ms"] = int(hook_motion["step_delay_ms"])
            except (TypeError, ValueError):
                resolved["step_delay_ms"] = DEFAULT_HOOK_STEP_DELAY_MS
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


ACCEL_SOFT_OUT = 0.6
ACCEL_SNAP_IN = 2.2


def serialize_keyframes(keyframes: List[Tuple[int, Dict[str, object], float]]) -> str:
    """
    Serialize keyframe list into ASS override tags.
    Format: [(t_ms, {prop: value}, accel), ...]
    Keyframe 0 sets initial property values (before animation starts).
    Subsequent keyframes emit \\t(t_prev, t_curr, [accel], tags).
    If accel == 1.0, standard linear \\t(t1,t2,tags) is emitted (byte-identical with legacy).
    """
    if not keyframes:
        return ""
    initial_tags = "".join(f"\\{prop}{val}" for prop, val in keyframes[0][1].items())
    segs = []
    for i in range(1, len(keyframes)):
        t_prev, _, _ = keyframes[i - 1]
        t_curr, props, accel = keyframes[i]
        prop_str = "".join(f"\\{prop}{val}" for prop, val in props.items())
        if accel == 1.0:
            segs.append(f"\\t({t_prev},{t_curr},{prop_str})")
        else:
            segs.append(f"\\t({t_prev},{t_curr},{accel:g},{prop_str})")
    return initial_tags + "".join(segs)


# ---- In (entrance) builders -------------------------------------------

def _in_bounce(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    """Elastic overshoot/undershoot/settle via \\fscx/\\fscy, ~450ms.

    Every segment decelerates into its extreme (power 0.6 = ACCEL_SOFT_OUT), so
    the scale eases into each peak/trough and settles softly onto the resting
    size. Keyframe times and values are unchanged; only the curve is eased.
    bounce_soft keeps its own mix (eased first/last, linear middle).
    """
    target = round(target_scale_pct)
    over = round(target * 1.25)
    under = round(target * 0.92)
    settle_over = round(target * 1.05)
    end_ms = t0_ms + 450
    entry_from = round(target * 0.6)
    kfs = [
        (t0_ms, {"fscx": entry_from, "fscy": entry_from}, 1.0),
        (t0_ms + 150, {"fscx": over, "fscy": over}, ACCEL_SOFT_OUT),
        (t0_ms + 280, {"fscx": under, "fscy": under}, ACCEL_SOFT_OUT),
        (t0_ms + 380, {"fscx": settle_over, "fscy": settle_over}, ACCEL_SOFT_OUT),
        (end_ms, {"fscx": target, "fscy": target}, ACCEL_SOFT_OUT),
    ]
    return serialize_keyframes(kfs), end_ms, None


def _in_bounce_soft(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    """Soft bounce easing without harsh linear reversal at peaks."""
    target = round(target_scale_pct)
    over = round(target * 1.25)
    under = round(target * 0.92)
    settle_over = round(target * 1.05)
    end_ms = t0_ms + 450
    entry_from = round(target * 0.6)
    kfs = [
        (t0_ms, {"fscx": entry_from, "fscy": entry_from}, 1.0),
        (t0_ms + 150, {"fscx": over, "fscy": over}, ACCEL_SOFT_OUT),
        (t0_ms + 280, {"fscx": under, "fscy": under}, 1.0),
        (t0_ms + 380, {"fscx": settle_over, "fscy": settle_over}, 1.0),
        (end_ms, {"fscx": target, "fscy": target}, ACCEL_SOFT_OUT),
    ]
    return serialize_keyframes(kfs), end_ms, None


def _in_pop(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    """Snappier one-bounce version of bounce -- single overshoot, ~200ms.

    Both segments ease out (ACCEL_SOFT_OUT): decelerate into the overshoot,
    then settle softly onto the resting size. pop_soft snaps in instead.
    """
    target = round(target_scale_pct)
    over = round(target * 1.18)
    entry_from = round(target * 0.55)
    end_ms = t0_ms + 200
    kfs = [
        (t0_ms, {"fscx": entry_from, "fscy": entry_from}, 1.0),
        (t0_ms + 120, {"fscx": over, "fscy": over}, ACCEL_SOFT_OUT),
        (end_ms, {"fscx": target, "fscy": target}, ACCEL_SOFT_OUT),
    ]
    return serialize_keyframes(kfs), end_ms, None


def _in_pop_soft(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    """Soft deceleration pop using ACCEL_SOFT_OUT and ACCEL_SNAP_IN."""
    target = round(target_scale_pct)
    over = round(target * 1.18)
    entry_from = round(target * 0.55)
    end_ms = t0_ms + 200
    kfs = [
        (t0_ms, {"fscx": entry_from, "fscy": entry_from}, 1.0),
        (t0_ms + 120, {"fscx": over, "fscy": over}, ACCEL_SOFT_OUT),
        (end_ms, {"fscx": target, "fscy": target}, ACCEL_SNAP_IN),
    ]
    return serialize_keyframes(kfs), end_ms, None


def _in_fade(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    end_ms = t0_ms + 250
    kfs = [
        (t0_ms, {"fscx": target, "fscy": target, "alpha": "&HFF&"}, 1.0),
        (end_ms, {"alpha": "&H00&"}, 1.0),
    ]
    return serialize_keyframes(kfs), end_ms, None


def _in_zoom(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    entry_from = round(target * 1.8)
    end_ms = t0_ms + 300
    tag = (
        f"\\fscx{entry_from}\\fscy{entry_from}\\alpha&HFF&"
        f"\\t({t0_ms},{t0_ms + 150},\\alpha&H00&)"
        f"\\t({t0_ms},{end_ms},{ACCEL_SOFT_OUT},\\fscx{target}\\fscy{target})"
    )
    return tag, end_ms, None


def _in_slide_up(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    end_ms = t0_ms + 300
    kfs = [
        (t0_ms, {"fscx": target, "fscy": target, "alpha": "&HFF&"}, 1.0),
        (end_ms, {"alpha": "&H00&"}, 1.0),
    ]
    tag = serialize_keyframes(kfs)
    return tag, end_ms, 60  # slides up from 60px below


def _in_blur(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    end_ms = t0_ms + 350
    kfs = [
        (t0_ms, {"fscx": target, "fscy": target, "alpha": "&HFF&", "blur": "12"}, 1.0),
        (end_ms, {"alpha": "&H00&", "blur": "0"}, 1.0),
    ]
    return serialize_keyframes(kfs), end_ms, None


def _in_none(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    return f"\\fscx{target}\\fscy{target}", t0_ms, None


def _in_slam(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    """Heavy 3D impact from 220% scale with rapid alpha fade-in."""
    target = round(target_scale_pct)
    entry_from = round(target * 2.2)
    end_ms = t0_ms + 180
    tag = (
        f"\\fscx{entry_from}\\fscy{entry_from}\\alpha&HFF&"
        f"\\t({t0_ms},{t0_ms + 50},\\alpha&H00&)"
        f"\\t({t0_ms},{end_ms},{ACCEL_SNAP_IN},\\fscx{target}\\fscy{target})"
    )
    return tag, end_ms, None


def _in_elastic_bounce(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    """Elastic spring overshoot/undershoot settling."""
    target = round(target_scale_pct)
    entry_from = round(target * 0.4)
    over1 = round(target * 1.28)
    under1 = round(target * 0.88)
    over2 = round(target * 1.08)
    under2 = round(target * 0.98)
    end_ms = t0_ms + 520
    # Scale and alpha run on separate keyframe grids, so each gets its own chain:
    # one shared list would start the first scale segment at the alpha keyframe
    # (t0+40) and libass would hold the entry scale for 40 ms.
    scale_head = f"\\fscx{entry_from}\\fscy{entry_from}"
    scale_kfs = [
        (t0_ms, {"fscx": entry_from, "fscy": entry_from}, 1.0),
        (t0_ms + 160, {"fscx": over1, "fscy": over1}, ACCEL_SOFT_OUT),
        (t0_ms + 290, {"fscx": under1, "fscy": under1}, 1.0),
        (t0_ms + 390, {"fscx": over2, "fscy": over2}, 1.0),
        (t0_ms + 460, {"fscx": under2, "fscy": under2}, 1.0),
        (end_ms, {"fscx": target, "fscy": target}, ACCEL_SOFT_OUT),
    ]
    alpha_kfs = [
        (t0_ms, {"alpha": "&HFF&"}, 1.0),
        (t0_ms + 40, {"alpha": "&H00&"}, 1.0),
    ]
    scale_chain = serialize_keyframes(scale_kfs).removeprefix(scale_head)
    return scale_head + serialize_keyframes(alpha_kfs) + scale_chain, end_ms, None


def _in_pop_zoom(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    entry_from = round(target * 1.45)
    end_ms = t0_ms + 100
    tag = (
        f"\\fscx{entry_from}\\fscy{entry_from}\\alpha&HFF&"
        f"\\t({t0_ms},{t0_ms + 70},\\alpha&H00&)"
        f"\\t({t0_ms},{end_ms},\\fscx{target}\\fscy{target})"
    )
    return tag, end_ms, None


def _in_quick_fade(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    end_ms = t0_ms + 150
    kfs = [
        (t0_ms, {"fscx": target, "fscy": target, "alpha": "&HFF&"}, 1.0),
        (end_ms, {"alpha": "&H00&"}, 1.0),
    ]
    return serialize_keyframes(kfs), end_ms, None


def _in_snap(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    entry_from = round(target * 1.25)
    end_ms = t0_ms + 70
    tag = f"\\fscx{entry_from}\\fscy{entry_from}\\t({t0_ms},{end_ms},\\fscx{target}\\fscy{target})"
    return tag, end_ms, None


def _in_stamp(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    entry_from = round(target * 1.65)
    end_ms = t0_ms + 80
    tag = f"\\fscx{entry_from}\\fscy{entry_from}\\t({t0_ms},{end_ms},\\fscx{target}\\fscy{target})"
    return tag, end_ms, None


def _in_rise(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    end_ms = t0_ms + 200
    kfs = [
        (t0_ms, {"fscx": target, "fscy": target, "alpha": "&HFF&"}, 1.0),
        (end_ms, {"alpha": "&H00&"}, 1.0),
    ]
    return serialize_keyframes(kfs), end_ms, 40


HOOK_IN_BUILDERS = {
    "bounce": _in_bounce, "bounce_soft": _in_bounce_soft,
    "elastic_bounce": _in_elastic_bounce,
    "pop": _in_pop, "pop_soft": _in_pop_soft,
    "slam": _in_slam,
    "fade": _in_fade, "zoom": _in_zoom,
    "slide_up": _in_slide_up, "blur": _in_blur, "none": _in_none,
}

HOOK_IN_ALIASES = {
    "pop_zoom": _in_pop_zoom,
    "quick_fade": _in_quick_fade,
    "snap": _in_snap,
    "stamp": _in_stamp,
    "rise": _in_rise,
}


def resolve_hook_in_builder(name: str):
    return HOOK_IN_BUILDERS.get(name) or HOOK_IN_ALIASES.get(name, _in_bounce)


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
    """Sharp jitter via \\frz, 100ms/step (3 whole frames at 30 fps)."""
    return _chained_keyframes("frz", start_ms, exit_start_ms, 100, ["-3", "3", "-2", "2", "0"])


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
    # Exit eases in (ACCEL_SNAP_IN): holds near opaque, then accelerates away.
    return f"\\t({exit_start_ms},{exit_end_ms},{ACCEL_SNAP_IN},\\alpha&HFF&)", None


def _out_slide(exit_start_ms: int, exit_end_ms: int, target_scale_pct: float) -> Tuple[str, Optional[int]]:
    return f"\\t({exit_start_ms},{exit_end_ms},\\alpha&HFF&)", 60


def _out_zoom(exit_start_ms: int, exit_end_ms: int, target_scale_pct: float) -> Tuple[str, Optional[int]]:
    target = round(target_scale_pct)
    grown = round(target * 1.4)
    return f"\\t({exit_start_ms},{exit_end_ms},{ACCEL_SNAP_IN},\\fscx{grown}\\fscy{grown}\\alpha&HFF&)", None


GLITCH_STEP_MS = 33  # one frame at 30 fps (33.3 ms, within 1 ms)


def _out_glitch(exit_start_ms: int, exit_end_ms: int, target_scale_pct: float) -> Tuple[str, Optional[int]]:
    """Quick \\frz jitter steps (one frame each) packed into the short exit window, then a hard cut."""
    jitter = _chained_keyframes("frz", exit_start_ms, max(exit_start_ms + 1, exit_end_ms - GLITCH_STEP_MS), GLITCH_STEP_MS, ["-3", "3", "0"])
    return f"{jitter}\\t({exit_end_ms - GLITCH_STEP_MS},{exit_end_ms},\\frz0\\alpha&HFF&)", None


def _out_none(exit_start_ms: int, exit_end_ms: int, target_scale_pct: float) -> Tuple[str, Optional[int]]:
    return f"\\t({max(exit_start_ms, exit_end_ms - 1)},{exit_end_ms},\\alpha&HFF&)", None


HOOK_OUT_BUILDERS = {
    "fade": _out_fade, "slide": _out_slide, "zoom": _out_zoom,
    "glitch": _out_glitch, "none": _out_none,
}
