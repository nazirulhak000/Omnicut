"""
The colour of the word being spoken, taken from the clip's own hook.

Progressive Ghost Reveal lit the active word neon green (`#66FF00`) whatever the
clip looked like, so a red Viral Punch hook sat above green captions. This picks
the hook's accent instead, so the opening nameplate and the captions share one
tone for the whole clip.

Pure functions only: they read the overlay list the subtitle stage already holds
and return a hex string or `None` (keep the SOP green). The browser mirrors the
same rules in `frontend/src/lib/revealColor.js` so the preview lights the same
colour the export burns in; `tests/test_preview_render_parity.py` pins both.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Optional, Sequence

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# A hook tier is "the accent" only if it is clearly coloured. White and grey
# tiers (the model / label lines of every T1 template) are body text, not tone.
MIN_SATURATION = 0.35
MIN_VALUE = 0.40
# Below this relative luminance a colour sinks into a dark frame even with the
# caption's black outline, so it is lifted toward white by LIFT_TOWARD_WHITE.
MIN_LUMINANCE = 0.15
LIFT_TOWARD_WHITE = 0.30


def _rgb(hex_colour: str):
    h = hex_colour.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _is_chromatic(hex_colour: str) -> bool:
    r, g, b = (c / 255.0 for c in _rgb(hex_colour))
    hi, lo = max(r, g, b), min(r, g, b)
    if hi < MIN_VALUE:
        return False
    saturation = 0.0 if hi == 0 else (hi - lo) / hi
    return saturation >= MIN_SATURATION


def _luminance(hex_colour: str) -> float:
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(c / 255.0) for c in _rgb(hex_colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _lift(hex_colour: str) -> str:
    r, g, b = _rgb(hex_colour)
    # floor(x + 0.5), not round(): Python rounds halves to even and JS rounds
    # them up, and the two must agree to the last digit of the hex.
    mix = [int(c + (255 - c) * LIFT_TOWARD_WHITE + 0.5) for c in (r, g, b)]
    return "#{:02X}{:02X}{:02X}".format(*mix)


def legible_reveal_hex(hex_colour: str) -> str:
    """`hex_colour` upper-cased, lifted toward white when too dark to read."""
    out = hex_colour.upper()
    return _lift(out) if _luminance(out) < MIN_LUMINANCE else out


def pick_reveal_hex(overlays: Optional[Sequence[Mapping[str, Any]]]) -> Optional[str]:
    """
    The hook's accent as `#RRGGBB`, or None when the hook has no coloured tier.

    Reads the first visible `kind: "hook"` overlay and takes its first
    chromatic tier colour in brand, model, label order -- the order the
    nameplate stacks them. Reading the overlay (not the template) means a hook
    the user recoloured in the editor drives the captions too.
    """
    for overlay in overlays or []:
        if not isinstance(overlay, Mapping):
            continue
        if overlay.get("kind") != "hook" or overlay.get("hidden"):
            continue
        for tier in overlay.get("tiers") or []:
            look = tier.get("look") if isinstance(tier, Mapping) else None
            colour = look.get("color") if isinstance(look, Mapping) else None
            if isinstance(colour, str) and _HEX_RE.match(colour) and _is_chromatic(colour):
                return legible_reveal_hex(colour)
        return None
    return None
