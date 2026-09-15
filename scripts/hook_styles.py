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
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CUSTOM_HOOK_TEMPLATES_FILE = BASE_DIR / "02_Assets" / "Templates" / "custom_hook_templates.json"

# Guards the read-modify-write cycles in save_custom_hook_template() and
# delete_custom_hook_template() below. API handlers here are sync `def`, so
# FastAPI runs them on a shared threadpool and two requests can genuinely
# race on this file.
_custom_templates_lock = threading.Lock()

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
        "motion": {"in": "bounce", "loop": "pulse", "out": "fade", "accent": "underline", "stagger": True},
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
        "motion": {"in": "bounce_soft", "loop": "wave", "out": "fade", "accent": "none", "stagger": True},
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
        "motion": {"in": "pop", "loop": "shake", "out": "zoom", "accent": "badge", "stagger": True},
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
        "motion": {"in": "fade", "loop": "none", "out": "fade", "accent": "none", "stagger": False},
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
        "motion": {"in": "slide_up", "loop": "lightsweep", "out": "fade", "accent": "none", "stagger": True},
    },
    "flash_sale": {
        "label_th": "โปรไฟลุก — แดงสด ป้ายส้มเหลืองสะดุดตา",
        "font": "Kanit",
        "tiers": {
            "brand": {"size_pct": 128, "color": "#FFFFFF", "outline_color": "#FE2C55",
                      "outline_px": 10.0, "upper": True, "pill": None},
            "model": {"size_pct": 112, "color": "#FFE04C", "outline_color": "#000000",
                      "outline_px": 8.0, "upper": False, "pill": None},
            "label": {"size_pct": 68, "color": "#FFFFFF", "outline_color": "#000000",
                      "outline_px": 0.0, "upper": False, "pill": "#FE2C55"},
        },
        "motion": {"in": "pop", "loop": "flicker", "out": "slide", "accent": "badge", "stagger": True},
    },
    "neon_cyber": {
        "label_th": "นีออน — ฟ้าไซเบอร์ ขอบมืดเรืองแสง",
        "font": "Chakra Petch",
        "tiers": {
            "brand": {"size_pct": 130, "color": "#FFFFFF", "outline_color": "#000000",
                      "outline_px": 8.0, "upper": True, "pill": None},
            "model": {"size_pct": 105, "color": "#25F4EE", "outline_color": "#000000",
                      "outline_px": 8.0, "upper": False, "pill": None},
            "label": {"size_pct": 64, "color": "#FFE04C", "outline_color": "#000000",
                      "outline_px": 4.0, "upper": False, "pill": None},
        },
        "motion": {"in": "pop_zoom", "loop": "wave", "out": "glitch", "accent": "underline", "stagger": True},
    },
    "minimal_luxury": {
        "label_th": "ลักชัวรี — ทองขาว คมชัด สไตล์แบรนด์เนม",
        "font": "Prompt",
        "tiers": {
            "brand": {"size_pct": 124, "color": "#FFFFFF", "outline_color": "#1A1A1A",
                      "outline_px": 4.0, "upper": True, "pill": None},
            "model": {"size_pct": 96, "color": "#E6C24A", "outline_color": "#1A1A1A",
                      "outline_px": 4.0, "upper": False, "pill": None},
            "label": {"size_pct": 60, "color": "#C8C8C8", "outline_color": "#1A1A1A",
                      "outline_px": 2.0, "upper": False, "pill": None},
        },
        "motion": {"in": "quick_fade", "loop": "lightsweep", "out": "fade", "accent": "underline", "stagger": True},
    },
    "b1_viral_red": {
        "label_th": "B1 (แดง+กระพริบ) — Viral Punch",
        "font": "Kanit",
        "tiers": {
            "brand": {"size_pct": 130, "color": "#FE2C55", "outline_color": "#0B0A0A",
                      "outline_px": 3.0, "upper": True, "pill": None},
            "model": {"size_pct": 107, "color": "#F7F7F7", "outline_color": "#0A0A0A",
                      "outline_px": 3.0, "upper": False, "pill": None},
            "label": {"size_pct": 60, "color": "#D0D0D0", "outline_color": "#101010",
                      "outline_px": 3.0, "upper": False, "pill": None},
        },
        "motion": {"in": "slide_up", "loop": "flicker", "out": "fade", "accent": "none", "stagger": True},
    },
    "b2_clean_yellow": {
        "label_th": "B2 (เหลือง+สั่น) — Clean Tech",
        "font": "Kanit",
        "tiers": {
            "brand": {"size_pct": 221, "color": "#FFE600", "outline_color": "#0A0A0A",
                      "outline_px": 3.0, "upper": True, "pill": None},
            "model": {"size_pct": 182, "color": "#F7F7F7", "outline_color": "#0A0A0A",
                      "outline_px": 3.0, "upper": False, "pill": None},
            "label": {"size_pct": 103, "color": "#D0D0D0", "outline_color": "#101010",
                      "outline_px": 3.0, "upper": False, "pill": None},
        },
        "motion": {"in": "slide_up", "loop": "shake", "out": "fade", "accent": "none", "stagger": True},
    },
    "b2_tech_cyan": {
        "label_th": "B2 (ฟ้า+สั่นเบา) — Tech Showcase",
        "font": "Kanit",
        "tiers": {
            "brand": {"size_pct": 207, "color": "#25F4EE", "outline_color": "#0B0A0A",
                      "outline_px": 3.0, "upper": True, "pill": None},
            "model": {"size_pct": 170, "color": "#F7F7F7", "outline_color": "#0A0A0A",
                      "outline_px": 3.0, "upper": False, "pill": None},
            "label": {"size_pct": 95, "color": "#D0D0D0", "outline_color": "#101010",
                      "outline_px": 3.0, "upper": False, "pill": None},
        },
        "motion": {"in": "slide_up", "loop": "wave", "out": "fade", "accent": "none", "stagger": True},
    },
    "b1_smooth_mint": {
        "label_th": "B1 (เขียวมิ้นต์+กวาดแสง) — Smooth",
        "font": "Kanit",
        "tiers": {
            "brand": {"size_pct": 170, "color": "#00F2AA", "outline_color": "#0A0A0A",
                      "outline_px": 3.0, "upper": True, "pill": None},
            "model": {"size_pct": 140, "color": "#F7F7F7", "outline_color": "#0A0A0A",
                      "outline_px": 3.0, "upper": False, "pill": None},
            "label": {"size_pct": 79, "color": "#D0D0D0", "outline_color": "#101010",
                      "outline_px": 3.0, "upper": False, "pill": None},
        },
        "motion": {"in": "slide_up", "loop": "lightsweep", "out": "fade", "accent": "none", "stagger": True},
    },
    "b2_premium_gold": {
        "label_th": "B2 (ทอง+สั่นเบา) — Premium",
        "font": "Kanit",
        "tiers": {
            "brand": {"size_pct": 207, "color": "#E6C24A", "outline_color": "#0A0A0A",
                      "outline_px": 3.0, "upper": True, "pill": None},
            "model": {"size_pct": 170, "color": "#F7F7F7", "outline_color": "#0A0A0A",
                      "outline_px": 3.0, "upper": False, "pill": None},
            "label": {"size_pct": 95, "color": "#D0D0D0", "outline_color": "#101010",
                      "outline_px": 3.0, "upper": False, "pill": None},
        },
        "motion": {"in": "slide_up", "loop": "wave", "out": "fade", "accent": "none", "stagger": True},
    },
}

DEFAULT_HOOK_TEMPLATE = "tech"
TIER_KEYS = ("brand", "model", "label")
TIER_FIELDS = ("size_pct", "color", "outline_color", "outline_px", "upper", "pill")


def load_custom_hook_templates() -> Dict[str, Dict[str, Any]]:
    """Load user-saved custom hook templates from 02_Assets/Templates/custom_hook_templates.json."""
    if not CUSTOM_HOOK_TEMPLATES_FILE.exists():
        return {}
    try:
        with open(CUSTOM_HOOK_TEMPLATES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("templates", {})
    except Exception as e:
        logger.warning("Failed to load custom hook templates: %s", e)
        return {}


def get_all_hook_templates() -> Dict[str, Dict[str, Any]]:
    """Return both built-in templates and user custom templates merged."""
    custom = load_custom_hook_templates()
    merged = dict(HOOK_TEMPLATES)
    merged.update(custom)
    return merged


def save_custom_hook_template(template_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save or update a custom hook template.
    template_id is sanitized and ensured to start with custom_.
    """
    clean_id = (template_id or "").strip()
    if not clean_id.startswith("custom_"):
        clean_id = f"custom_{clean_id or 'template'}"

    base = HOOK_TEMPLATES[DEFAULT_HOOK_TEMPLATE]
    tiers = {}
    input_tiers = data.get("tiers") or {}
    for key in TIER_KEYS:
        tier_data = dict(base["tiers"][key])
        if key in input_tiers:
            for field in TIER_FIELDS:
                if field in input_tiers[key] and input_tiers[key][field] is not None:
                    tier_data[field] = input_tiers[key][field]
        tiers[key] = tier_data

    entry = {
        "id": clean_id,
        "label_th": data.get("label_th") or data.get("name") or f"สไตล์ของฉัน ({clean_id})",
        "font": data.get("font") or base["font"],
        "tiers": tiers,
        "motion": dict(data.get("motion") or base.get("motion") or {}),
        "is_custom": True,
    }

    CUSTOM_HOOK_TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    # The whole load-mutate-write cycle is under the lock, not just the
    # write: two concurrent saves (different threads, same threadpool) that
    # both load() before either writes would otherwise silently lose
    # whichever one's write lands first, even for two different template
    # ids. Unique tmp name (pid + thread id, matching scripts/db.py's
    # JsonMirror pattern at db.py:329) so two threads never step on the same
    # fixed ".tmp" path even in the brief window before the lock below
    # actually serializes them.
    with _custom_templates_lock:
        current_templates = load_custom_hook_templates()
        current_templates[clean_id] = entry

        tmp_file = CUSTOM_HOOK_TEMPLATES_FILE.parent / f"{CUSTOM_HOOK_TEMPLATES_FILE.stem}.{os.getpid()}.{threading.get_ident()}.tmp"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump({"version": "1.0", "templates": current_templates}, f, ensure_ascii=False, indent=2)
            tmp_file.replace(CUSTOM_HOOK_TEMPLATES_FILE)
        finally:
            tmp_file.unlink(missing_ok=True)

    return entry


def delete_custom_hook_template(template_id: str) -> bool:
    """Delete a custom hook template. Cannot delete built-in templates."""
    if template_id in HOOK_TEMPLATES:
        return False
    # Same locked read-modify-write + unique tmp name as
    # save_custom_hook_template() above, and for the same reason.
    with _custom_templates_lock:
        current_templates = load_custom_hook_templates()
        if template_id not in current_templates:
            return False
        del current_templates[template_id]
        tmp_file = CUSTOM_HOOK_TEMPLATES_FILE.parent / f"{CUSTOM_HOOK_TEMPLATES_FILE.stem}.{os.getpid()}.{threading.get_ident()}.tmp"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump({"version": "1.0", "templates": current_templates}, f, ensure_ascii=False, indent=2)
            tmp_file.replace(CUSTOM_HOOK_TEMPLATES_FILE)
        finally:
            tmp_file.unlink(missing_ok=True)
    return True


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
    all_templates = get_all_hook_templates()
    base = all_templates.get(template or DEFAULT_HOOK_TEMPLATE) \
        or HOOK_TEMPLATES[DEFAULT_HOOK_TEMPLATE]
    over = overrides or {}
    over_tiers = over.get("tiers") or {}
    picked_colors = colors or {}

    resolved = {
        "template": template if template in all_templates else DEFAULT_HOOK_TEMPLATE,
        "font": over.get("font") or base["font"],
        "tiers": {},
        "motion": dict(over.get("motion") or base.get("motion") or {}),
    }
    for key in TIER_KEYS:
        tier = dict(base["tiers"][key])
        for field in TIER_FIELDS:
            value = (over_tiers.get(key) or {}).get(field)
            if value is not None:
                tier[field] = value
        if (over_tiers.get(key) or {}).get("font"):
            tier["font"] = over_tiers[key]["font"]
        if picked_colors.get(key):
            tier["color"] = picked_colors[key]
        resolved["tiers"][key] = tier
    return resolved
