"""
One shape for every piece of text burned into the frame.

The editor grew two of these independently. The hook banner was three loose
scalars (hook_brand/hook_model/hook_label) plus three style dicts, always at
t=0, drawn by its own canvas function and its own ASS emitter. Text overlays
were an array of flat items with a different vocabulary for the same ideas --
`scale` where the hook said `size_pct`, `bgStyle`+`badgeColor` where the hook
said `pill`, a single `anim` string where the hook had four motion channels --
and no outline fields at all, so a text overlay could never reach the look a
hook template could. Two spellings of one picture, and the thinner one always
looked cheaper.

This module is that one spelling. An overlay is a stack of tiers; a hook has
three, an ordinary text overlay has one. Everything else is shared.

Mirrored in frontend/src/lib/overlayModel.js -- the canvas preview reads that
one, the ASS writer reads this one, and tests/test_preview_render_parity.py
compares them field by field. A field that exists on only one side is a
preview that lies about the render.
"""
from typing import Any, Dict, List, Optional, Tuple

from scripts.hook_styles import (
    DEFAULT_HOOK_TEMPLATE,
    HOOK_TEMPLATES,
    TIER_KEYS,
    resolve_hook_style,
)

# ---------------------------------------------------------------- geometry
# Canvas is 540x960, the render is 1080x1920 -- exactly half. Anything
# measured in render pixels is halved for the preview (parity rule 2.3).
# `outline_px` is the documented exception: ASS grows an outline outward only
# while ctx.strokeText centres its stroke, so half the same number lands
# outside, and the two sides carry the identical figure (parity rule 2.6).
CANVAS_SCALE = 0.5

# Base font size as a fraction of frame width. A banner and a body line have
# different natural sizes, so the ratio rides on the overlay rather than on
# the look, and `size_pct` stays a number the user recognises: the hook's
# brand tier reads 130%, not the 182% it would take to say the same thing
# against the caption's base.
HOOK_FS_RATIO = 0.065

# How long the nameplate (brand / model / label) stays up by default. It was 5.0
# until M1 (2026-10-31): the first 1.8 s now belong to the hook line, and the
# nameplate follows it for 3.0 s. An explicit hook_duration still wins.
HOOK_NAMEPLATE_DEFAULT_SEC = 3.0
TEXT_FS_RATIO = 0.0463

# Weight per family, previously HOOK_FONT_WEIGHTS in SequencePlayer.jsx and
# an unconditional Bold=1 on the ASS side. Ask a face for a weight it does
# not ship and the browser synthesises one heavier than the render's, so a
# family that only has a regular cut says 400 here.
#
# The last three are the ids the editor stores rather than family names --
# a text overlay saves fontName 'IBMPlex', not 'IBM Plex Sans Thai'.
FONT_WEIGHTS: Dict[str, int] = {
    "Kanit": 700,
    "Prompt": 700,
    "Chakra Petch": 700,
    "Anuphan": 400,
    "IBM Plex Sans Thai": 700,
    "Bai Jamjuree": 700,
    "Krub": 700,
    "Mitr": 700,
    "Pridi": 700,
    "Sarabun": 700,
    "Mali": 700,
    "Itim": 400,
    "Chonburi": 400,
    "IBMPlex": 700,
    "Noto Sans Thai": 400,
    "NotoSansThai": 400,
}
DEFAULT_FONT_WEIGHT = 700

# ---------------------------------------------------------------- TextLook
# The hook's per-tier style, generalised so a text overlay can say the same
# things. `pill` and `shadow` are objects rather than bare colours because
# both kinds carried extra geometry that a colour string could not hold.
TEXT_LOOK_FIELDS: Tuple[str, ...] = (
    "font", "size_pct", "color",
    "outline_color", "outline_px",
    "shadow", "pill", "upper", "skew",
    "bold", "italic", "underline",
    "accent_color",
)

# A dark copy of the glyphs, offset down-right. The render draws it as its own
# dialogue line (the old HookHeaderShadow style) or as the ASS Shadow value;
# the preview draws it with ctx.shadow*. Offsets are RENDER pixels -- halve
# them for canvas. Mechanism differs by engine, so the blur will never match
# exactly; position, size and colour must (parity rule 5).
DEFAULT_SHADOW: Dict[str, Any] = {"dx": 1.5, "dy": 2.0, "blur": 4.0, "color": "#000000"}
# The banner's heavier halo: the old HookHeaderShadow style, Outline 7.0 at
# MarginL 62 / MarginV 257 against the main style's 60 / 260.
HOOK_SHADOW: Dict[str, Any] = {"dx": 2.0, "dy": 3.0, "blur": 7.0, "color": "#000000"}

# Padding is a multiple of the line's own font size so a pill follows the text
# when the size changes. The text overlay already worked this way; the hook's
# pill used a flat 12px, which is 0.342em at the banner's 100% size -- carried
# over as that ratio, so a hook pill now grows with its tier instead of
# staying put. Radius caps in render pixels.
PILL_PAD_X_EM = 0.6
PILL_PAD_Y_EM = 0.35
PILL_RADIUS_MAX_PX = 28.0
HOOK_PILL_PAD_X_EM = 0.342
HOOK_PILL_PAD_Y_EM = 0.171

DEFAULT_TEXT_LOOK: Dict[str, Any] = {
    "font": "Kanit",
    "size_pct": 100,
    "color": "#FFFFFF",
    "outline_color": "#000000",
    # The TextOverlayMain style's own Outline. The canvas used to derive its
    # own number from the font size (max(2, fs*0.12) -- 3px where the render
    # burned 5), so the preview under-drew every text overlay's outline. One
    # number now, and the render's is the one that was true.
    "outline_px": 5.0,
    "shadow": DEFAULT_SHADOW,
    "pill": None,
    "upper": False,
    "skew": 0.0,
    "bold": False,
    "italic": False,
    "underline": False,
    "accent_color": None,
}

# ------------------------------------------------------- legacy vocabulary
# bgStyle + badgeColor collapse into one pill object. Values read off
# drawTextOverlays in SequencePlayer.jsx.
LEGACY_BG_STYLES: Dict[str, Optional[Dict[str, Any]]] = {
    "none": None,
    "pill": {"fill": "rgba(0, 0, 0, 0.65)", "border": None},
    "badge_red": {"fill": "#FE2C55", "border": None},
    "badge_yellow": {"fill": "#FFE600", "border": None},
    "badge_cyan": {"fill": "rgba(37, 244, 238, 0.2)", "border": "#25F4EE"},
}

# A text overlay's single `anim` was always an entrance; the exit was a
# hardcoded 150ms fade it had no way to name. That fade runs over the last
# 150ms, which is exactly what the banner's `out: fade` already did, so the
# two exits were the same picture under two spellings and only the entrance
# needed reconciling.
DEFAULT_ANIM: Dict[str, Any] = {
    "in": "snap", "loop": "none", "out": "fade", "accent": "none", "stagger": False, "word_stagger_ms": 0,
}
# The banner's defaults, previously DEFAULT_HOOK_MOTION in subtitle_engine.py.
HOOK_ANIM: Dict[str, Any] = {
    "in": "bounce", "loop": "pulse", "out": "fade", "accent": "underline", "stagger": True, "reveal": "simultaneous",
}

# Three entrance names meant different animations on the two sides -- a text
# overlay's `pop` snapped 1.25x down in 70ms while the banner's overshot to
# 1.18x over 200ms. Both are worth keeping, so the text ones are renamed
# rather than merged, and every existing project keeps the motion it had.
# The user picks from Thai labels, so these ids never surface.
LEGACY_TEXT_ANIM: Dict[str, str] = {
    "pop": "snap",         # 1.25 -> 1.0 over 70ms
    "zoom": "pop_zoom",    # 1.45 -> 1.0 over 100ms, alpha over 70ms
    "stamp": "stamp",      # 1.65 -> 1.0 over 80ms
    "fade": "quick_fade",  # alpha over 150ms
    "slide": "rise",       # dy 40 -> 0 over 200ms, alpha with it
    "none": "none",
}
LEGACY_TEXT_ANIM_REVERSE: Dict[str, str] = {v: k for k, v in LEGACY_TEXT_ANIM.items()}

# Which banner look a clip's narration tone asks for. The tone is already
# chosen per angle by the script AI and carried through angleToForm.js, so a
# first render can dress its banner to match the voice instead of landing on
# the same 'tech' every time. Whatever the user picks by hand still wins.
AD_TONE_TO_TEMPLATE: Dict[str, str] = {
    "commercial_expert": "tech",
    "commercial_hype": "bold_pop",
    "commercial_aesthetic": "plain",
    "commercial_premium": "clean",
    "tech_journalism_calm": "tech",
}

STYLE_PRESET_TO_TEMPLATE: Dict[str, str] = {
    "viral_punch": "b1_viral_red",
    "clean_tech_review": "b2_clean_yellow",
    "tech_product_showcase": "b2_tech_cyan",
    "smooth_showcase": "b1_smooth_mint",
    "premium_minimal": "b2_premium_gold",
    "flash_deal": "b1_deal_orange",
    "pain_punch": "b1_pain_pink",
    "tech_compare": "b2_compare_blue",
    "smart_hack": "b1_hack_lime",
    "niche_focus": "b2_niche_purple",
}


def template_for_ad_tone(ad_tone: Optional[str]) -> str:
    """The banner look that matches a narration tone, or the default."""
    return AD_TONE_TO_TEMPLATE.get(ad_tone or "", DEFAULT_HOOK_TEMPLATE)


def template_for_style_preset(style_preset: Optional[str]) -> Optional[str]:
    """The banner look that matches an editorial style preset."""
    return STYLE_PRESET_TO_TEMPLATE.get(style_preset or "")


def resolve_look(base: Optional[Dict[str, Any]], override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    An overlay's look plus one tier's overrides, flattened. Absent and None
    both mean "keep the base", so a tier that only wants a different colour
    says only that -- same contract as resolve_hook_style().
    """
    look = dict(DEFAULT_TEXT_LOOK)
    for source in (base or {}, override or {}):
        for field in TEXT_LOOK_FIELDS:
            value = source.get(field)
            if value is not None:
                look[field] = value
    return look


def font_weight(font: Optional[str]) -> int:
    return FONT_WEIGHTS.get(font or "", DEFAULT_FONT_WEIGHT)


def base_fs_ratio(kind: str) -> float:
    return HOOK_FS_RATIO if kind == "hook" else TEXT_FS_RATIO


OVERLAY_KIND_ALIASES = {
    "hook": "hook",
    "hook_header": "hook",
    "text": "text",
    "text_overlay": "text",
}


def overlay_kind(overlay: Optional[Dict[str, Any]]) -> Optional[str]:
    """Resolve the persisted kind/type spelling used by the ASS dispatcher."""
    if not isinstance(overlay, dict):
        return None
    raw_kind = overlay.get("kind") or overlay.get("type")
    return OVERLAY_KIND_ALIASES.get(raw_kind)


# ---------------------------------------------------------------- position
# The banner's block is anchored to the top of the frame: ASS MarginV 180 of
# 1920, canvas y 90 of 960 (top Safe Zone 9.4%) -- the same fraction, per parity rule 2.8.
HOOK_TOP_Y = 180.0 / 1920.0
TEXT_POSITIONS: Dict[str, float] = {"top": 0.20, "middle": 0.50, "bottom": 0.72}

# Which edge of the block `y` names, which is what an ASS Alignment says.
# Parity rule 2.8: a multi-line block anchored at the wrong edge slides by
# half its own height, so this cannot default to "centre everything".
ANCHOR_TOP = "top"        # ASS Alignment 8 -- the banner
ANCHOR_MIDDLE = "middle"  # ASS Alignment 5 -- text overlays
ASS_ALIGNMENT = {ANCHOR_TOP: 8, ANCHOR_MIDDLE: 5}

# Past this many wrapped lines the block shrinks (to a floor of 0.7) rather
# than growing unbounded. The banner needs it because it shares the top of
# the frame with the sticker badge; a text overlay is placed by hand and has
# no neighbour to crowd, so it says None and keeps the size it was given.
HOOK_COMFORTABLE_LINES = 4

# ASS Layer: lower numbers paint first, so this is z-order. The banner sat on
# layers 1-2 and the text overlays on 3-4, which is why a text overlay has
# always covered the banner rather than the other way round. Captions are
# layer 0 and paint under both.
HOOK_LAYER = 2
TEXT_LAYER = 4

# The model tier's colour is `None` in the template table, meaning "use the
# caption accent colour". None also means "inherit" everywhere else in this
# module, so the two are spelled apart: the accent is a value, not an absence.
ACCENT_COLOR = "accent"

LEGACY_HOOK_KEYS = (
    "hook_brand", "hook_model", "hook_label", "hook_duration",
    "hook_motion", "hook_colors", "hook_style",
)


def _manifest_get(manifest: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Top level first, then render_params -- the order the editor reads in."""
    if manifest.get(key) is not None:
        return manifest[key]
    params = manifest.get("render_params") or {}
    value = params.get(key)
    return default if value is None else value


def _pill_from_legacy(bg_style: Optional[str], badge_color: Optional[str]) -> Optional[Dict[str, Any]]:
    """bgStyle + badgeColor -> one pill. A badgeColor with no matching preset
    is an arbitrary fill, which is what drawTextOverlays did with it."""
    style = bg_style or "none"
    if style in LEGACY_BG_STYLES and LEGACY_BG_STYLES[style] is not None:
        preset = dict(LEGACY_BG_STYLES[style])
        # A badgeColor naming a different colour than its preset overrides the
        # fill but keeps the preset's border, matching the old branch order.
        if badge_color and badge_color not in ("#FE2C55", "#FFE600", "#25F4EE"):
            preset["fill"] = badge_color
        return {**preset, "pad_x_em": PILL_PAD_X_EM, "pad_y_em": PILL_PAD_Y_EM}
    if style == "none" and badge_color:
        return {"fill": badge_color, "border": None,
                "pad_x_em": PILL_PAD_X_EM, "pad_y_em": PILL_PAD_Y_EM}
    return None


def _hook_tier_look(resolved_font: str, tier: Dict[str, Any]) -> Dict[str, Any]:
    """One resolved hook tier, in TextLook spelling."""
    tier_font = tier.get("font") or resolved_font
    pill = None
    if tier.get("pill"):
        pill = {"fill": tier["pill"], "border": None,
                "pad_x_em": HOOK_PILL_PAD_X_EM, "pad_y_em": HOOK_PILL_PAD_Y_EM}
    return {
        "font": tier_font,
        "size_pct": tier["size_pct"],
        "color": ACCENT_COLOR if tier.get("color") is None else tier["color"],
        "outline_color": tier["outline_color"],
        "outline_px": float(tier["outline_px"]),
        "shadow": dict(HOOK_SHADOW),
        "pill": pill,
        "upper": bool(tier.get("upper")),
        "bold": bool(tier.get("bold")),
        "italic": bool(tier.get("italic")),
        "underline": bool(tier.get("underline")),
    }


def hook_overlay_from_legacy(
    brand: str,
    model: str,
    label: str,
    duration: float = HOOK_NAMEPLATE_DEFAULT_SEC,
    motion: Optional[Dict[str, Any]] = None,
    colors: Optional[Dict[str, str]] = None,
    style: Optional[Dict[str, Any]] = None,
    style_preset: Optional[str] = None,
    ad_tone: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    The three banner scalars as one overlay. Returns None when all three tiers
    are empty -- an overlay that says nothing is simply not in the array,
    which is what `showHookHeader` used to be for.
    """
    texts = [brand or "", model or "", label or ""]
    if not any(t.strip() for t in texts):
        return None
    style = style or {}
    template = (
        style.get("template")
        or template_for_style_preset(style_preset)
        or template_for_ad_tone(ad_tone)
        or DEFAULT_HOOK_TEMPLATE
    )
    resolved = resolve_hook_style(template, style, colors)
    dur = float(duration or HOOK_NAMEPLATE_DEFAULT_SEC)
    return {
        "id": "ovl_hook",
        "kind": "hook",
        "template": resolved["template"],
        "start": 0.0,
        "end": round(dur, 3),
        "position": "top",
        "anchor": ANCHOR_TOP,
        "comfortable_lines": HOOK_COMFORTABLE_LINES,
        "layer": HOOK_LAYER,
        "x": 0.5,
        "y": HOOK_TOP_Y,
        "base_fs_ratio": HOOK_FS_RATIO,
        "look": {"font": resolved["font"], "shadow": dict(HOOK_SHADOW)},
        "tiers": [
            {"text": texts[i], "look": _hook_tier_look(resolved["font"], resolved["tiers"][key])}
            for i, key in enumerate(TIER_KEYS)
        ],
        "anim": {**HOOK_ANIM, **(resolved.get("motion") or {}), **(motion or {})},
        # The banner is what the top gradient was always for; it is a property
        # of this overlay now rather than a second reading of hook_duration.
        "scrim": True,
        "sfx": None,
        "sfx_label": None,
        "template_id": None,
        "hidden": False,
    }


def text_overlay_from_legacy(item: Dict[str, Any]) -> Dict[str, Any]:
    """One flat text_overlays[] entry as an overlay with a single tier."""
    scale = item.get("scale")
    scale = 1.0 if scale is None else float(scale)
    legacy_anim = item.get("anim") or "pop"
    anim_in = LEGACY_TEXT_ANIM.get(legacy_anim, legacy_anim)
    return {
        "id": item.get("id") or "ovl_text",
        "kind": "text",
        "template": None,
        "start": float(item.get("start") or 0.0),
        "end": float(item.get("end") or 0.0),
        "position": item.get("position") or "middle",
        "anchor": ANCHOR_MIDDLE,
        "comfortable_lines": None,
        "layer": TEXT_LAYER,
        "x": item.get("x"),
        "y": item.get("y"),
        "base_fs_ratio": TEXT_FS_RATIO,
        "look": {
            # fontName was written by the inspector and read by nobody: the
            # canvas took the caption's font and the ASS writer never looked.
            # It is the look's font now, on the one path that draws anything.
            "font": item.get("fontName") or item.get("font") or DEFAULT_TEXT_LOOK["font"],
            "size_pct": int(round(scale * 100)),
            "color": item.get("color") or DEFAULT_TEXT_LOOK["color"],
            "outline_color": DEFAULT_TEXT_LOOK["outline_color"],
            "outline_px": DEFAULT_TEXT_LOOK["outline_px"],
            "shadow": dict(DEFAULT_SHADOW),
            "pill": _pill_from_legacy(item.get("bgStyle"), item.get("badgeColor")),
            "upper": False,
        },
        "tiers": [{"text": item.get("text") or "", "look": {}}],
        "anim": {**DEFAULT_ANIM, "in": anim_in},
        "scrim": False,
        "sfx": item.get("sfx"),
        "sfx_label": item.get("sfxLabel") or item.get("sfx_label"),
        "template_id": item.get("templateId") or item.get("template_id"),
        "hidden": False,
    }


def migrate_to_overlays(manifest: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Every overlay in a project, whichever era it was saved in.

    A manifest that already carries `overlays` is returned as-is. Otherwise
    the banner scalars and text_overlays[] are read and converted. Legacy keys
    are read forever and never written again, so an old project opens without
    anyone touching the file on disk.
    """
    manifest = manifest or {}
    existing = _manifest_get(manifest, "overlays")
    if isinstance(existing, list):
        return [dict(o) for o in existing]

    overlays: List[Dict[str, Any]] = []
    hook = hook_overlay_from_legacy(
        _manifest_get(manifest, "hook_brand", "") or "",
        _manifest_get(manifest, "hook_model", "") or "",
        _manifest_get(manifest, "hook_label", "") or "",
        _manifest_get(manifest, "hook_duration", HOOK_NAMEPLATE_DEFAULT_SEC) or HOOK_NAMEPLATE_DEFAULT_SEC,
        _manifest_get(manifest, "hook_motion") or {},
        _manifest_get(manifest, "hook_colors") or {},
        _manifest_get(manifest, "hook_style") or {},
        style_preset=_manifest_get(manifest, "style_preset"),
        ad_tone=_manifest_get(manifest, "ad_tone"),
    )
    if hook:
        overlays.append(hook)
    raw_text = _manifest_get(manifest, "text_overlays") or []
    if isinstance(raw_text, list):
        overlays.extend(text_overlay_from_legacy(t) for t in raw_text if isinstance(t, dict))
    return overlays


# ------------------------------------------------------------- round-trip
# Only the tests and the deprecated request shims need to speak legacy back.
# Nothing in the write path calls these.

def _legacy_bg_style(pill: Optional[Dict[str, Any]]) -> Tuple[str, Optional[str]]:
    if not pill:
        return "none", None
    for name, preset in LEGACY_BG_STYLES.items():
        if preset and preset["fill"] == pill.get("fill") and preset["border"] == pill.get("border"):
            return name, None
    return "none", pill.get("fill")


def overlay_to_legacy_text(overlay: Dict[str, Any]) -> Dict[str, Any]:
    look = resolve_look(overlay.get("look"), (overlay.get("tiers") or [{}])[0].get("look"))
    bg_style, badge_color = _legacy_bg_style(look.get("pill"))
    return {
        "id": overlay.get("id"),
        "text": (overlay.get("tiers") or [{}])[0].get("text", ""),
        "start": overlay.get("start"),
        "end": overlay.get("end"),
        "position": overlay.get("position"),
        "x": overlay.get("x"),
        "y": overlay.get("y"),
        "scale": round(look["size_pct"] / 100.0, 4),
        "color": look["color"],
        "fontName": look["font"],
        "bgStyle": bg_style,
        "badgeColor": badge_color,
        "anim": LEGACY_TEXT_ANIM_REVERSE.get(
            (overlay.get("anim") or {}).get("in"), (overlay.get("anim") or {}).get("in")),
        "sfx": overlay.get("sfx"),
        "sfxLabel": overlay.get("sfx_label"),
        "templateId": overlay.get("template_id"),
    }


def overlay_to_legacy_hook(overlay: Dict[str, Any]) -> Dict[str, Any]:
    tiers = overlay.get("tiers") or []
    texts = [(tiers[i].get("text") if i < len(tiers) else "") or "" for i in range(3)]
    style_tiers: Dict[str, Any] = {}
    for i, key in enumerate(TIER_KEYS):
        look = resolve_look(overlay.get("look"), tiers[i].get("look") if i < len(tiers) else None)
        style_tiers[key] = {
            "size_pct": look["size_pct"],
            "color": None if look["color"] == ACCENT_COLOR else look["color"],
            "outline_color": look["outline_color"],
            "outline_px": look["outline_px"],
            "upper": look["upper"],
            "pill": (look["pill"] or {}).get("fill"),
        }
    base_look = resolve_look(overlay.get("look"), None)
    return {
        "hook_brand": texts[0],
        "hook_model": texts[1],
        "hook_label": texts[2],
        "hook_duration": round(float(overlay.get("end") or 0.0) - float(overlay.get("start") or 0.0), 3),
        "hook_motion": dict(overlay.get("anim") or {}),
        # Colours live in the tiers now; the separate map only ever existed so
        # the pickers had somewhere to write before templates did.
        "hook_colors": {},
        "hook_style": {"template": overlay.get("template") or DEFAULT_HOOK_TEMPLATE,
                       "font": base_look["font"], "tiers": style_tiers},
    }


def overlays_to_legacy(overlays: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Everything a pre-overlays reader expects, rebuilt from the array."""
    legacy: Dict[str, Any] = {
        "hook_brand": "", "hook_model": "", "hook_label": "", "hook_duration": HOOK_NAMEPLATE_DEFAULT_SEC,
        "hook_motion": {}, "hook_colors": {}, "hook_style": {"template": DEFAULT_HOOK_TEMPLATE},
        "text_overlays": [],
    }
    for overlay in overlays or []:
        if overlay.get("kind") == "hook":
            legacy.update(overlay_to_legacy_hook(overlay))
        else:
            legacy["text_overlays"].append(overlay_to_legacy_text(overlay))
    return legacy


def guess_brand_model(product_name: Optional[str]) -> Tuple[str, str]:
    """
    Best-effort brand/model split from a free-text product name -- assumes the
    common "Brand Model" word order (Logitech Wave Keys, Apple iPhone 15).
    Wrong for names that do not lead with a brand, so it only ever pre-fills a
    banner tier that is still empty: a wrong guess costs one edit, never a
    silent wrong render. Mirrors guessBrandModel() in overlayModel.js.
    """
    trimmed = (product_name or "").strip()
    if not trimmed:
        return "", ""
    parts = trimmed.split()
    if len(parts) <= 1:
        return trimmed, ""
    return parts[0], " ".join(parts[1:])


# ------------------------------------------------------------ constructors
# Both sides make overlays: the editor when the user adds one, the render API
# when a first generate arrives with nothing but the three banner strings.

def new_text_overlay(
    overlay_id: str,
    text: str = "",
    start: float = 0.0,
    end: float = 2.5,
    look: Optional[Dict[str, Any]] = None,
    anim_in: Optional[str] = None,
    sfx: Optional[str] = None,
    sfx_label: Optional[str] = None,
    template_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": overlay_id,
        "kind": "text",
        "template": None,
        "start": round(float(start), 3),
        "end": round(float(end), 3),
        "position": "middle",
        "anchor": ANCHOR_MIDDLE,
        "comfortable_lines": None,
        "layer": TEXT_LAYER,
        "x": 0.5,
        "y": 0.5,
        "base_fs_ratio": TEXT_FS_RATIO,
        "look": {**{k: v for k, v in DEFAULT_TEXT_LOOK.items()}, **(look or {})},
        "tiers": [{"text": text, "look": {}}],
        "anim": {**DEFAULT_ANIM, **({"in": anim_in} if anim_in else {})},
        "scrim": False,
        "sfx": sfx,
        "sfx_label": sfx_label,
        "template_id": template_id,
        "hidden": False,
    }


def new_hook_overlay(
    brand: str = "",
    model: str = "",
    label: str = "",
    template: Optional[str] = None,
    start: float = 0.0,
    duration: float = 3.0,
) -> Optional[Dict[str, Any]]:
    """The banner as an overlay, dressed in `template`. None when it is blank."""
    overlay = hook_overlay_from_legacy(
        brand, model, label, duration, None, None,
        {"template": template or DEFAULT_HOOK_TEMPLATE},
    )
    if overlay and start:
        overlay["start"] = round(float(start), 3)
        overlay["end"] = round(float(start) + float(duration), 3)
    return overlay
