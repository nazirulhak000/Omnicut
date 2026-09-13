"""Deterministic style policy for auto-generated clip transitions.

The policy owns editorial restraint, while the existing transition picker
still owns the exact transition family chosen from zoom/tone context. Keeping
the budget here makes style a project-level data contract instead of another
inline if/else chain in the shot matcher.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


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


STYLE_MOTION_POLICIES = {
    "clean_tech_review": StyleMotionPolicy(
        key="clean_tech_review",
        # One movement transition every five boundaries keeps roughly 80% of
        # boundaries as hard cuts on normal-length short-form clips.
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
        accent_color="#FFE600",
        status_color="#25F4EE",
        neutral_color="#FFFFFF",
    ),
    "viral_punch": StyleMotionPolicy(
        key="viral_punch",
        transition_stride=2,
        stylized_stride=6,
        max_transition_duration=0.28,
        transition_family="energetic",
        camera_motion_stride=1,
        camera_zoom_delta=0.12,
        camera_pan_extent=0.18,
        camera_min_duration=0.65,
        accent_color="#FE2C55",
        status_color="#25F4EE",
        neutral_color="#FFFFFF",
    ),
    "tech_product_showcase": StyleMotionPolicy(
        key="tech_product_showcase",
        # Product cards get a visible but deliberate movement rhythm: two
        # clean cuts, then one directional transition for the next detail.
        transition_stride=3,
        # Reserve the stronger circle reveal for every second movement slot.
        stylized_stride=6,
        max_transition_duration=0.30,
        transition_family="energetic",
        # Every usable product shot gets a restrained hero push/pan. The
        # smaller delta leaves room for large product titles and callouts.
        camera_motion_stride=1,
        camera_zoom_delta=0.10,
        camera_pan_extent=0.16,
        camera_min_duration=0.75,
        accent_color="#FFCC33",
        status_color="#25F4EE",
        neutral_color="#FFFFFF",
    ),
    "smooth_showcase": StyleMotionPolicy(
        key="smooth_showcase",
        transition_stride=3,
        stylized_stride=0,
        max_transition_duration=0.35,
        transition_family="smooth",
        camera_motion_stride=1,
        camera_zoom_delta=0.05,
        camera_pan_extent=0.08,
        camera_min_duration=1.0,
        accent_color="#25F4EE",
        status_color="#FFE600",
        neutral_color="#FFFFFF",
    ),
    "premium_minimal": StyleMotionPolicy(
        key="premium_minimal",
        transition_stride=6,
        stylized_stride=0,
        max_transition_duration=0.3,
        transition_family="minimal",
        camera_motion_stride=3,
        camera_zoom_delta=0.04,
        camera_pan_extent=0.06,
        camera_min_duration=1.2,
        accent_color="#E6C24A",
        status_color="#D8C58A",
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
    renderer. Manual transition lists never call this function.
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
        return candidate

    try:
        duration = float(candidate.get("duration", profile.max_transition_duration))
    except (TypeError, ValueError):
        duration = profile.max_transition_duration
    candidate["duration"] = min(profile.max_transition_duration, max(0.1, duration))
    return candidate


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
        },
    ]


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
        }
        for key, policy in STYLE_MOTION_POLICIES.items()
    }


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
    "resolve_style_motion_policy",
    "style_motion_catalog",
    "style_visual_palette",
]
