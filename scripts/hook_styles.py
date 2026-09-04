"""
Hook Header looks: named templates, each fully overridable.

The banner used to have exactly one appearance -- white wordmark, accent model
line, muted label, a black 6px outline on all three, in whatever font the
captions were using. Every part of that was a literal in the ASS writer, so a
brand with its own type, or any of the looks that actually get used on TikTok
(white text with a thick pink outline, magenta with a heavy white one, heavy
sans with no outline at all), was simply not reachable.

A template names a whole look; anything in it can still be overridden field by
field, so the templates are starting points rather than five fixed choices.

This table is mirrored in frontend/src/lib/hookStyles.js, which the canvas
preview reads. The two are compared field by field in
tests/test_preview_render_parity.py -- a look that only exists on one side is a
preview that lies about the render.
"""
from typing import Any, Dict, Optional

# Colour of `None` on the model tier means "use the caption accent colour",
# which is what the banner did before any of this existed.
ACCENT = None

HOOK_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "tech": {
        "label_th": "เทค — แบรนด์ขาว รุ่นสีจัด (ของเดิม)",
        "font": "Chakra Petch",
        "tiers": {
            "brand": {"size_pct": 130, "color": "#FFFFFF", "outline_color": "#000000",
                      "outline_px": 6.0, "upper": True, "pill": None},
            "model": {"size_pct": 100, "color": ACCENT, "outline_color": "#000000",
                      "outline_px": 6.0, "upper": False, "pill": None},
            "label": {"size_pct": 58, "color": "#E0E0E0", "outline_color": "#000000",
                      "outline_px": 6.0, "upper": False, "pill": None},
        },
    },
    "cute": {
        "label_th": "คิ้วท์ — ตัวขาว ขอบชมพูหนา",
        "font": "Itim",
        "tiers": {
            "brand": {"size_pct": 118, "color": "#FFFFFF", "outline_color": "#E86BC7",
                      "outline_px": 10.0, "upper": False, "pill": None},
            "model": {"size_pct": 100, "color": "#FFFFFF", "outline_color": "#E86BC7",
                      "outline_px": 10.0, "upper": False, "pill": None},
            "label": {"size_pct": 62, "color": "#FFFFFF", "outline_color": "#E86BC7",
                      "outline_px": 0.0, "upper": False, "pill": "#E86BC7"},
        },
    },
    "bold_pop": {
        "label_th": "ป็อปตัวหนา — บานเย็น ขอบขาวหนา",
        "font": "Kanit",
        "tiers": {
            "brand": {"size_pct": 122, "color": "#E038D8", "outline_color": "#FFFFFF",
                      "outline_px": 14.0, "upper": False, "pill": None},
            "model": {"size_pct": 110, "color": "#FFE04C", "outline_color": "#FFFFFF",
                      "outline_px": 12.0, "upper": False, "pill": None},
            "label": {"size_pct": 78, "color": "#4CE0FF", "outline_color": "#FFFFFF",
                      "outline_px": 10.0, "upper": False, "pill": None},
        },
    },
    "plain": {
        "label_th": "เรียบ — ขาวหนา ไม่มีขอบ",
        "font": "Prompt",
        "tiers": {
            "brand": {"size_pct": 130, "color": "#FFFFFF", "outline_color": "#000000",
                      "outline_px": 0.0, "upper": False, "pill": None},
            "model": {"size_pct": 82, "color": ACCENT, "outline_color": "#000000",
                      "outline_px": 0.0, "upper": False, "pill": None},
            "label": {"size_pct": 58, "color": "#C8C8C8", "outline_color": "#000000",
                      "outline_px": 0.0, "upper": False, "pill": None},
        },
    },
    "clean": {
        "label_th": "คลีน — ขาว ขอบดำบาง",
        "font": "Anuphan",
        "tiers": {
            "brand": {"size_pct": 126, "color": "#FFFFFF", "outline_color": "#101010",
                      "outline_px": 3.0, "upper": True, "pill": None},
            "model": {"size_pct": 100, "color": "#FFFFFF", "outline_color": "#101010",
                      "outline_px": 3.0, "upper": False, "pill": None},
            "label": {"size_pct": 60, "color": "#D0D0D0", "outline_color": "#101010",
                      "outline_px": 3.0, "upper": False, "pill": None},
        },
    },
}

DEFAULT_HOOK_TEMPLATE = "tech"
TIER_KEYS = ("brand", "model", "label")
TIER_FIELDS = ("size_pct", "color", "outline_color", "outline_px", "upper", "pill")


def resolve_hook_style(
    template: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
    colors: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    A template plus its overrides, flattened into one style the writers can use.

    `overrides` may carry `font` and a `tiers` map of partial tier dicts --
    anything absent keeps the template's value, so a project that only wants a
    different outline colour says only that.

    `colors` is the older per-tier colour map, which predates templates and is
    still what the colour pickers write. It wins over both, so an existing
    project keeps the colours it was saved with.
    """
    base = HOOK_TEMPLATES.get(template or DEFAULT_HOOK_TEMPLATE) \
        or HOOK_TEMPLATES[DEFAULT_HOOK_TEMPLATE]
    over = overrides or {}
    over_tiers = over.get("tiers") or {}
    picked_colors = colors or {}

    resolved = {
        "template": template if template in HOOK_TEMPLATES else DEFAULT_HOOK_TEMPLATE,
        "font": over.get("font") or base["font"],
        "tiers": {},
    }
    for key in TIER_KEYS:
        tier = dict(base["tiers"][key])
        for field in TIER_FIELDS:
            value = (over_tiers.get(key) or {}).get(field)
            if value is not None:
                tier[field] = value
        if picked_colors.get(key):
            tier["color"] = picked_colors[key]
        resolved["tiers"][key] = tier
    return resolved
