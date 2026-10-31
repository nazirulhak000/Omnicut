"""Deterministic style policy for auto-generated clip transitions.

The policy owns editorial restraint, while the existing transition picker
still owns the exact transition family chosen from zoom/tone context. Keeping
the budget here makes style a project-level data contract instead of another
inline if/else chain in the shot matcher.
"""

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from scripts.config import J_CUT_OFFSET_SECONDS, MAX_SHOT_DURATION, MIN_SHOT_DURATION

# Today's global beat-snap window (was a literal inside the shot matcher).
BEAT_SNAP_TOLERANCE = 0.15

# Pacing curve (roadmap M2). The opening seconds cut faster than the body of
# the clip, and no span may sit longer than max_static_sec without a cut, a
# transition or a camera move. Values per motion family:
#   (hook_max_shot, max_static_sec)
# [assumption, to be tuned from the Q6 watch-time data].
HOOK_WINDOW_SEC = 3.0
FAMILY_PACING = {
    "energetic": (1.0, 2.0),  # punch
    "adaptive": (1.3, 2.5),   # tech
    "smooth": (1.5, 3.0),
    "minimal": (1.8, 3.5),    # premium
    "compare": (1.3, 2.5),    # rhythmic wipe/slide alternation (tech_compare)
}
DEFAULT_FAMILY_PACING = FAMILY_PACING["adaptive"]

# Mirrors video_editor.CAMERA_EASINGS / timelineMath.js CAMERA_EASINGS.
CAMERA_EASING_NAMES = ("linear", "ease_in", "ease_out", "ease_in_out")
DEFAULT_CAMERA_EASING = "ease_in_out"


@dataclass(frozen=True)
class StyleMotionPolicy:
    """Small, serializable policy surface for a whole-clip visual style."""

    key: str
    transition_stride: int
    stylized_stride: int
    max_transition_duration: float
    transition_family: str
    camera_motion_stride: int
    camera_zoom_delta: float
    camera_pan_extent: float
    camera_min_duration: float
    # Renderer-facing visual tokens. These are kept beside motion policy so a
    # preset has one serializable contract across generated overlays and clips.
    accent_color: str
    status_color: str
    neutral_color: str
    # Cut rhythm of the auto shot planner. Defaults are the old global
    # constants, so a style that does not set them cuts exactly as before.
    # Invariant kept by every style: beat_snap_tolerance <= j_lead, so a beat
    # snap can pull a cut earlier but never in front of the voice onset
    # (reverse J-cut); j_lead stays within 0.17-0.22 s so that, after a cut
    # is rounded to the 1/30 s grid (+-17 ms), it is still inside the
    # 150-250 ms J-cut window.
    min_shot: float = MIN_SHOT_DURATION
    max_shot: float = MAX_SHOT_DURATION
    j_lead: float = J_CUT_OFFSET_SECONDS
    beat_snap_tolerance: float = BEAT_SNAP_TOLERANCE
    # Easing every auto-generated transition of this style plays with (see
    # apply_transition_budget). Calm styles settle softly (ease_in_out); the
    # punchy ones hit fast and decelerate (ease_out).
    transition_easing: str = "ease_in_out"
    # Pacing curve (M2). None means "derive from transition_family" via
    # FAMILY_PACING, so a policy written before these fields existed (or a
    # serialized one missing them) still resolves to sensible values.
    hook_window_sec: float = HOOK_WINDOW_SEC
    hook_max_shot: Optional[float] = None
    max_static_sec: Optional[float] = None
    # Easing of the generated camera push/pan (M5). It rides on the manifest
    # keyframe's own ``easing`` key, which the renderer and the preview both
    # already interpolate, so it needs no preview-side logic. The default is
    # the pre-M5 behaviour (soft start and settle); punchy styles use
    # ease_out so the push lands hard and then decelerates.
    camera_easing: str = DEFAULT_CAMERA_EASING

    def __post_init__(self) -> None:
        hook_default, static_default = FAMILY_PACING.get(self.transition_family, DEFAULT_FAMILY_PACING)
        if self.hook_max_shot is None:
            object.__setattr__(self, "hook_max_shot", hook_default)
        if self.max_static_sec is None:
            object.__setattr__(self, "max_static_sec", static_default)


# M5 (user decision 2026-10-31): all ten presets stay selectable and each one
# must FEEL different, using only levers the renderer already honours. The
# punch / tech / smooth / premium motion families are the starting point; the
# per-preset notes say what separates a preset from its nearest sibling.
# `tests/test_style_distinctness.py` enforces it (pairwise distance, unique
# transition fingerprint). Colours/hook templates are untouched by M5.
STYLE_MOTION_POLICIES = {
    "clean_tech_review": StyleMotionPolicy(
        key="clean_tech_review",
        # Calm default. One movement transition every five boundaries keeps
        # roughly 80% of boundaries as hard cuts on short-form clips.
        transition_stride=5,
        # A circle/wipe is reserved for every tenth boundary; the other
        # transition slots are demoted to a restrained dissolve/fade.
        stylized_stride=10,
        max_transition_duration=0.35,
        transition_family="adaptive",
        # Animate only alternating, reasonably long shots. The quiet shots
        # remain still so motion has hierarchy instead of becoming wallpaper.
        camera_motion_stride=2,
        camera_zoom_delta=0.08,
        camera_pan_extent=0.14,
        camera_min_duration=0.8,
        # Cut rhythm: the golden master keeps the global defaults
        # (1.5-2.5 s shots, 0.18 s J-lead, 0.15 s beat snap) byte-for-byte.
        # M5: only the opening is tightened (1.3 -> 1.2 s hook shots) for
        # retention; the body of the clip is unchanged.
        hook_max_shot=1.2,
        accent_color="#FFE600",
        status_color="#25F4EE",
        neutral_color="#FFFFFF",
    ),
    "viral_punch": StyleMotionPolicy(
        key="viral_punch",
        # The base of the punch group: slide every second boundary, circle
        # every sixth, zoom AND pan on every shot. Unchanged by M5.
        transition_stride=2,
        stylized_stride=6,
        max_transition_duration=0.28,
        transition_family="energetic",
        camera_motion_stride=1,
        camera_zoom_delta=0.12,
        camera_pan_extent=0.18,
        camera_min_duration=0.65,
        # Cut rhythm: Fast-feed rhythm: shorter ceiling, the shortest J-lead that stays >= 150 ms after frame rounding, for a snappier cut; tighter beat lock (<= lead).
        min_shot=1.5,
        max_shot=2.2,
        j_lead=0.17,
        beat_snap_tolerance=0.12,
        transition_easing="ease_out",
        accent_color="#FE2C55",
        status_color="#25F4EE",
        neutral_color="#FFFFFF",
    ),
    "tech_product_showcase": StyleMotionPolicy(
        key="tech_product_showcase",
        # Steady, camera-forward product reveal: the picture travels (wide
        # pans, a light push) and the slide that joins two shots continues
        # that pan (orient_slide_to_pan). No circle reveals.
        transition_stride=3,
        stylized_stride=0,
        max_transition_duration=0.30,
        transition_family="energetic",
        camera_motion_stride=1,
        camera_zoom_delta=0.06,
        camera_pan_extent=0.24,
        camera_min_duration=0.9,
        # Cut rhythm: Detail shots need a beat longer to read a port or a texture; standard lead.
        min_shot=1.7,
        max_shot=2.6,
        j_lead=0.18,
        beat_snap_tolerance=0.10,
        hook_max_shot=1.2,
        accent_color="#FFCC33",
        status_color="#25F4EE",
        neutral_color="#FFFFFF",
    ),
    "smooth_showcase": StyleMotionPolicy(
        key="smooth_showcase",
        # Dissolve-led and gentle: the only preset whose joins are all
        # cross-dissolves. Unchanged by M5.
        transition_stride=3,
        stylized_stride=0,
        max_transition_duration=0.35,
        transition_family="smooth",
        camera_motion_stride=1,
        camera_zoom_delta=0.05,
        camera_pan_extent=0.08,
        camera_min_duration=1.0,
        # Cut rhythm: Smooth flow: longer holds and a softer, later picture change; music snap loosened.
        min_shot=1.8,
        max_shot=2.8,
        j_lead=0.21,
        beat_snap_tolerance=0.1,
        accent_color="#25F4EE",
        status_color="#FFE600",
        neutral_color="#FFFFFF",
    ),
    "premium_minimal": StyleMotionPolicy(
        key="premium_minimal",
        # The most restrained preset. Unchanged by M5.
        transition_stride=6,
        stylized_stride=0,
        max_transition_duration=0.3,
        transition_family="minimal",
        camera_motion_stride=3,
        camera_zoom_delta=0.04,
        camera_pan_extent=0.06,
        camera_min_duration=1.2,
        # Cut rhythm: Luxury pace: the longest holds the gadget rule allows (<= 3.0 s), the longest lead that stays <= 250 ms after frame rounding, almost no beat chasing.
        min_shot=1.8,
        max_shot=3.0,
        j_lead=0.22,
        beat_snap_tolerance=0.08,
        accent_color="#E6C24A",
        status_color="#D8C58A",
        neutral_color="#FFFFFF",
    ),
    "flash_deal": StyleMotionPolicy(
        key="flash_deal",
        # Urgency from the CUTS, not the camera: the shortest shots and the
        # tightest hook of any preset, a slide every second boundary and no
        # circle reveals, but a calmer camera (every other shot, small
        # push, short pan) so the energy is in the edit.
        transition_stride=2,
        stylized_stride=0,
        max_transition_duration=0.24,
        transition_family="energetic",
        camera_motion_stride=2,
        camera_zoom_delta=0.06,
        camera_pan_extent=0.10,
        camera_min_duration=0.9,
        # Cut rhythm: Hard-sell cadence: densest cutting still inside the 1.5 s floor.
        min_shot=1.5,
        max_shot=1.9,
        j_lead=0.17,
        beat_snap_tolerance=0.10,
        transition_easing="ease_out",
        hook_max_shot=0.9,
        camera_easing="ease_out",
        accent_color="#FF7A00",
        status_color="#25F4EE",
        neutral_color="#FFFFFF",
    ),
    "pain_punch": StyleMotionPolicy(
        key="pain_punch",
        # Heavy zoom-in impact: the biggest push of any preset (almost no
        # pan) that lands with ease_out, a circle reveal on every second
        # movement slot, and cuts slower than flash_deal so the problem line
        # is held and heard first.
        transition_stride=3,
        stylized_stride=6,
        max_transition_duration=0.24,
        transition_family="energetic",
        camera_motion_stride=1,
        camera_zoom_delta=0.20,
        camera_pan_extent=0.06,
        camera_min_duration=0.7,
        # Cut rhythm: Problem-agitation: slower cuts than flash_deal, a
        # later J-lead so the pain line is heard first, and a firmer beat lock
        # so the heavy zoom lands on the music.
        min_shot=1.7,
        max_shot=2.5,
        j_lead=0.19,
        beat_snap_tolerance=0.15,
        transition_easing="ease_out",
        hook_max_shot=1.2,
        max_static_sec=2.5,
        camera_easing="ease_out",
        accent_color="#FF2E93",
        status_color="#25F4EE",
        neutral_color="#FFFFFF",
    ),
    "tech_compare": StyleMotionPolicy(
        key="tech_compare",
        # Rhythmic A/B alternation: the "compare" family joins every third
        # boundary with a wipe, a slide, a wipe from the other side...
        # (see apply_transition_budget), on a camera that pans wide on
        # alternating shots, with an even 1.8-2.4 s shot cadence.
        transition_stride=3,
        stylized_stride=0,
        max_transition_duration=0.30,
        transition_family="compare",
        camera_motion_stride=2,
        camera_zoom_delta=0.06,
        camera_pan_extent=0.22,
        camera_min_duration=0.9,
        # Cut rhythm: Comparisons need time to read both sides: an even
        # 1.8-2.4 s cadence, lead above standard.
        min_shot=1.8,
        max_shot=2.4,
        j_lead=0.20,
        beat_snap_tolerance=0.16,
        hook_max_shot=1.3,
        max_static_sec=2.8,
        accent_color="#3B82F6",
        status_color="#FFE600",
        neutral_color="#FFFFFF",
    ),
    "smart_hack": StyleMotionPolicy(
        key="smart_hack",
        # Crisp, step-by-step: mostly hard cuts with a short slide only every
        # fourth boundary (no dissolve, no circle) and quick camera nudges
        # (short minimum, ease_out) so each step snaps into place.
        transition_stride=4,
        stylized_stride=0,
        max_transition_duration=0.20,
        transition_family="energetic",
        camera_motion_stride=1,
        camera_zoom_delta=0.07,
        camera_pan_extent=0.12,
        camera_min_duration=0.7,
        # Cut rhythm: Step-by-step hack: even cadence, light beat lock.
        min_shot=1.6,
        max_shot=2.3,
        j_lead=0.19,
        beat_snap_tolerance=0.14,
        transition_easing="ease_out",
        hook_max_shot=1.3,
        camera_easing="ease_out",
        accent_color="#84CC16",
        status_color="#25F4EE",
        neutral_color="#FFFFFF",
    ),
    "niche_focus": StyleMotionPolicy(
        key="niche_focus",
        # Tight push-ins with long holds: the deepest push of the calm
        # presets with almost no pan, on alternating long shots, joined by an
        # iris (circle) reveal every fourth boundary: "focus in".
        transition_stride=4,
        stylized_stride=4,
        max_transition_duration=0.32,
        transition_family="energetic",
        camera_motion_stride=2,
        camera_zoom_delta=0.16,
        camera_pan_extent=0.04,
        camera_min_duration=1.0,
        # Cut rhythm: Focused explainer: long holds so a function can be read, lead a bit above standard, light beat lock.
        min_shot=1.8,
        max_shot=2.8,
        j_lead=0.20,
        beat_snap_tolerance=0.09,
        hook_max_shot=1.4,
        max_static_sec=3.0,
        accent_color="#A855F7",
        status_color="#25F4EE",
        neutral_color="#FFFFFF",
    ),
}

DEFAULT_STYLE_MOTION_POLICY = STYLE_MOTION_POLICIES["clean_tech_review"]

_STYLIZED_TRANSITIONS = frozenset({
    "circleopen",
    "circleclose",
    "wipeleft",
    "wiperight",
    "wipeup",
    "wipedown",
})

# Types the policy may ease: video_editor.EASED_TRANSITIONS minus fadeblack and
# fadewhite, whose eased expression costs ~8-13 s of render per transition at
# 1080x1920 (fade +0.4 s, wipe +0.3 s, slide +0.9 s). dissolve, circle* and cut
# ignore easing in the renderer, so they never get one.
_POLICY_EASED_TRANSITIONS = frozenset({
    "fade",
    "wipeleft",
    "wiperight",
    "wipeup",
    "wipedown",
    "slideleft",
    "slideright",
    "slideup",
    "slidedown",
})


def _with_style_easing(candidate: Dict[str, Any], profile: StyleMotionPolicy) -> Dict[str, Any]:
    """Give a generated transition the style's easing when its type honours it.

    The key is `easing`, the render-side name (video_editor.normalize_transitions
    reads it; the editor maps it to clip.transition_easing on load). An easing
    already on the pick is kept; any other type carries none.
    """
    if str(candidate.get("type") or "cut") in _POLICY_EASED_TRANSITIONS:
        candidate.setdefault("easing", profile.transition_easing)
    else:
        candidate.pop("easing", None)
    return candidate


def resolve_style_motion_policy(style_preset: Optional[str]) -> StyleMotionPolicy:
    """Resolve a requested style, safely falling back to the Golden Master."""
    key = str(style_preset or DEFAULT_STYLE_MOTION_POLICY.key).strip().lower()
    return STYLE_MOTION_POLICIES.get(key, DEFAULT_STYLE_MOTION_POLICY)


def apply_transition_budget(
    pick: Optional[Dict[str, Any]],
    *,
    style_preset: Optional[str],
    boundary_index: int,
) -> Dict[str, Any]:
    """Apply style restraint to one auto-generated transition decision.

    ``boundary_index`` is one-based. A non-budget slot becomes an explicit
    cut, which is understood identically by the clip-list preview and FFmpeg
    renderer. Manual transition lists never call this function. A pick whose
    final type honours easing (fade, wipe*, slide*) also gets the style's
    ``easing``; cut, dissolve, circle*, fadeblack and fadewhite never do.
    """
    candidate = dict(pick or {})
    profile = resolve_style_motion_policy(style_preset)
    if profile.key == "legacy":
        return candidate

    if profile.transition_stride <= 0 or boundary_index % profile.transition_stride:
        return {"type": "cut", "duration": 0.0}

    kind = str(candidate.get("type") or "cut")
    if profile.transition_family == "smooth":
        candidate["type"] = "dissolve"
    elif profile.transition_family == "minimal":
        candidate["type"] = "fade"
    elif profile.transition_family == "compare":
        # Rhythmic A/B alternation at a regular stride: a wipe, then a slide,
        # then a wipe from the other side. Deterministic in the slot number
        # alone (no dependence on the picker's pick), so the plan is the same
        # for the render and for the preview that plays its manifest.
        slot = boundary_index // max(1, profile.transition_stride)
        if slot % 2:
            candidate["type"] = "wipeleft" if (slot // 2) % 2 == 0 else "wiperight"
        else:
            candidate["type"] = "slideleft"
    elif profile.transition_family == "energetic":
        if profile.stylized_stride > 0 and boundary_index % profile.stylized_stride == 0:
            candidate["type"] = "circleopen"
        else:
            slot = boundary_index // max(1, profile.transition_stride)
            candidate["type"] = "slideleft" if slot % 2 else "slideright"
    elif kind in _STYLIZED_TRANSITIONS and (
        profile.stylized_stride <= 0 or boundary_index % profile.stylized_stride
    ):
        candidate["type"] = "dissolve"
        candidate["duration"] = min(0.25, profile.max_transition_duration)
        return _with_style_easing(candidate, profile)

    try:
        duration = float(candidate.get("duration", profile.max_transition_duration))
    except (TypeError, ValueError):
        duration = profile.max_transition_duration
    candidate["duration"] = min(profile.max_transition_duration, max(0.1, duration))
    return _with_style_easing(candidate, profile)


def camera_keyframes_for_clip(
    base_zoom: Any,
    duration: Any,
    clip_index: int,
    *,
    style_preset: Optional[str],
) -> list:
    """Build a restrained deterministic push/pan for an auto-generated clip.

    The generated clip keeps its static zoom as the midpoint of the move. A
    stride and minimum duration keep short-form motion legible and leave quiet
    shots available as visual rests. Manual clip keyframes never call this
    helper; their authored keyframes remain user-owned.
    """
    profile = resolve_style_motion_policy(style_preset)
    if profile.camera_motion_stride <= 0 or clip_index % profile.camera_motion_stride:
        return []
    try:
        zoom = float(base_zoom)
        span = float(duration)
    except (TypeError, ValueError):
        return []
    if span < profile.camera_min_duration:
        return []

    zoom = min(3.0, max(1.0, zoom))
    half_delta = profile.camera_zoom_delta / 2.0
    start_zoom = min(3.0, max(1.0, zoom - half_delta))
    end_zoom = min(3.0, max(1.0, zoom + half_delta))
    direction = 1.0 if (clip_index // profile.camera_motion_stride) % 2 == 0 else -1.0
    start_pan = -direction * profile.camera_pan_extent
    end_pan = direction * profile.camera_pan_extent
    return [
        {
            "time": 0.0,
            "zoom": round(start_zoom, 4),
            "pan_x": round(start_pan, 4),
            "pan_y": 0.0,
        },
        {
            "time": round(span, 4),
            "zoom": round(end_zoom, 4),
            "pan_x": round(end_pan, 4),
            "pan_y": 0.0,
            # Shapes the segment ending here (video_editor.CAMERA_EASINGS):
            # the style's easing (soft settle by default, ease_out to land a
            # punch) instead of a constant-speed crawl.
            "easing": profile.camera_easing if profile.camera_easing in CAMERA_EASING_NAMES else DEFAULT_CAMERA_EASING,
        },
    ]


_SLIDE_PAIR = frozenset({"slideleft", "slideright"})


def _pan_x_direction_at_end(keyframes: Any) -> int:
    """Sign of the outgoing clip's last pan_x segment: +1, -1 or 0 (no pan).

    Reads both keyframe shapes video_editor._camera_track understands
    ({"time", "pan_x"} and {"time", "property": "pan_x", "value"}).
    """
    track = []
    for point in keyframes if isinstance(keyframes, list) else []:
        if not isinstance(point, dict):
            continue
        value = point.get("pan_x") if "pan_x" in point else (
            point.get("value") if point.get("property") == "pan_x" else None
        )
        try:
            track.append((float(point.get("time")), float(value)))
        except (TypeError, ValueError):
            continue
    track.sort(key=lambda item: item[0])
    for (_, before), (_, after) in zip(reversed(track[:-1]), reversed(track[1:])):
        if abs(after - before) > 1e-6:
            return 1 if after > before else -1
    return 0


def orient_slide_to_pan(pick: Any, outgoing_keyframes: Any) -> Any:
    """Point a slide transition the way the outgoing shot's camera was moving.

    Sign convention (video_editor.dynamic_camera_filter): the crop window's x
    is room/2 * (1 + pan_x), so a rising pan_x moves the window right -- the
    camera pans right and the content on screen travels LEFT. ffmpeg's
    ``slideleft`` moves both frames left (the new shot enters from the right),
    so it continues that motion:

        pan_x rising  (camera right, content left)  -> slideleft
        pan_x falling (camera left,  content right) -> slideright
        no pan_x motion                             -> pick unchanged

    Only slideleft/slideright picks are touched; every other type, and any
    non-dict pick, is returned as is.
    """
    if not isinstance(pick, dict) or pick.get("type") not in _SLIDE_PAIR:
        return pick
    direction = _pan_x_direction_at_end(outgoing_keyframes)
    if direction == 0:
        return pick
    oriented = dict(pick)
    oriented["type"] = "slideleft" if direction > 0 else "slideright"
    return oriented


def style_motion_catalog() -> Dict[str, Dict[str, Any]]:
    """Return the JSON-safe policies mirrored by the frontend style picker."""
    return {
        key: {
            "key": policy.key,
            "transition_stride": policy.transition_stride,
            "stylized_stride": policy.stylized_stride,
            "max_transition_duration": policy.max_transition_duration,
            "transition_family": policy.transition_family,
            "camera_motion_stride": policy.camera_motion_stride,
            "camera_zoom_delta": policy.camera_zoom_delta,
            "camera_pan_extent": policy.camera_pan_extent,
            "camera_min_duration": policy.camera_min_duration,
            "accent_color": policy.accent_color,
            "status_color": policy.status_color,
            "neutral_color": policy.neutral_color,
            "min_shot": policy.min_shot,
            "max_shot": policy.max_shot,
            "j_lead": policy.j_lead,
            "beat_snap_tolerance": policy.beat_snap_tolerance,
            "transition_easing": policy.transition_easing,
            "hook_window_sec": policy.hook_window_sec,
            "hook_max_shot": policy.hook_max_shot,
            "max_static_sec": policy.max_static_sec,
            "camera_easing": policy.camera_easing,
        }
        for key, policy in STYLE_MOTION_POLICIES.items()
    }


def style_motion_policy_from_dict(data: Optional[Mapping[str, Any]]) -> StyleMotionPolicy:
    """Rebuild a policy from a serialized catalog entry.

    Unknown keys are ignored and missing keys fall back to the registered
    policy of the same ``key`` (or the Golden Master), so entries saved before
    the pacing-curve fields existed load unchanged.
    """
    from dataclasses import fields, replace

    if not isinstance(data, Mapping):
        return DEFAULT_STYLE_MOTION_POLICY
    base = resolve_style_motion_policy(data.get("key"))
    known = {f.name for f in fields(StyleMotionPolicy)} - {"key"}
    overrides = {name: data[name] for name in known if name in data and data[name] is not None}
    if "camera_easing" not in data and overrides:
        # A serialized policy older than M5 played every generated camera move
        # with the old fixed easing; the registered preset may now ease
        # differently, so a legacy entry keeps the legacy value.
        overrides["camera_easing"] = DEFAULT_CAMERA_EASING
    return replace(base, **overrides) if overrides else base


def style_visual_palette(style_preset: Optional[str]) -> Dict[str, str]:
    """Return the validated visual tokens for a project style preset."""
    policy = resolve_style_motion_policy(style_preset)
    return {
        "accent_color": policy.accent_color,
        "status_color": policy.status_color,
        "neutral_color": policy.neutral_color,
    }


__all__ = [
    "DEFAULT_STYLE_MOTION_POLICY",
    "STYLE_MOTION_POLICIES",
    "StyleMotionPolicy",
    "apply_transition_budget",
    "camera_keyframes_for_clip",
    "orient_slide_to_pan",
    "resolve_style_motion_policy",
    "style_motion_catalog",
    "style_motion_policy_from_dict",
    "style_visual_palette",
]
