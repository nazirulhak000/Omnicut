"""Deterministic source-contract checks for Canvas SpotlightV1 preview."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
JS_SRC = (ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx").read_text(encoding="utf-8")
PY_SRC = (ROOT / "scripts" / "spotlight_effect.py").read_text(encoding="utf-8")
ASSET_PANEL_SRC = (ROOT / "frontend" / "src" / "components" / "editor" / "AssetPanel.jsx").read_text(encoding="utf-8")
EDITOR_SHELL_SRC = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
SEQUENCE_PLAYER_SRC = JS_SRC


def _number(source: str, pattern: str) -> float:
    match = re.search(pattern, source)
    assert match, f"Spotlight parity probe found no match for {pattern!r}"
    return float(match.group(1))


def test_spotlight_contract_constants_match_backend():
    assert _number(PY_SRC, r"SCHEMA_VERSION = (\d+)") == _number(JS_SRC, r"SPOTLIGHT_SCHEMA_VERSION = (\d+)")
    assert _number(PY_SRC, r"DEFAULT_DIM_OPACITY = ([\d.]+)") == _number(JS_SRC, r"SPOTLIGHT_DEFAULT_DIM_OPACITY = ([\d.]+)")
    assert _number(PY_SRC, r"DEFAULT_FEATHER = ([\d.]+)") == _number(JS_SRC, r"SPOTLIGHT_DEFAULT_FEATHER = ([\d.]+)")
    assert _number(PY_SRC, r"DEFAULT_CORNER_RADIUS = ([\d.]+)") == _number(JS_SRC, r"SPOTLIGHT_DEFAULT_CORNER_RADIUS = ([\d.]+)")
    assert _number(PY_SRC, r"MAX_DIM_OPACITY = ([\d.]+)") == _number(JS_SRC, r"SPOTLIGHT_MAX_DIM_OPACITY = ([\d.]+)")
    assert _number(PY_SRC, r"MAX_FEATHER = ([\d.]+)") == _number(JS_SRC, r"SPOTLIGHT_MAX_FEATHER = ([\d.]+)")
    assert "SUPPORTED_SHAPES = (\"ellipse\", \"rectangle\", \"rounded_rect\")" in PY_SRC
    assert "new Set(['ellipse', 'rectangle', 'rounded_rect'])" in JS_SRC
    assert "DEFAULT_FOCUS = {\"x\": 0.5, \"y\": 0.5, \"width\": 0.62, \"height\": 0.42}" in PY_SRC
    assert "SPOTLIGHT_DEFAULT_FOCUS = Object.freeze({ x: 0.5, y: 0.5, width: 0.62, height: 0.42 })" in JS_SRC


def test_spotlight_normalisation_is_opt_in_and_clamps_same_geometry():
    normalizer = JS_SRC.split("export function normalizeSpotlightPreview", 1)[1].split("function spotlightFromEffects", 1)[0]
    assert "if (!value || typeof value !== 'object' || Array.isArray(value)) return null;" in normalizer
    assert "const hasSchemaVersion = Object.prototype.hasOwnProperty.call(value, 'schema_version');" in normalizer
    assert "const hasShape = Object.prototype.hasOwnProperty.call(value, 'shape');" in normalizer
    assert "if (hasShape && typeof value.shape !== 'string') return null;" in normalizer
    assert "if (value.enabled !== true) return null;" in normalizer
    assert "if (!SPOTLIGHT_SHAPES.has(shape)) return null;" in normalizer
    assert "if (!rawFocus || typeof rawFocus !== 'object' || Array.isArray(rawFocus)) return null;" in normalizer
    assert "clampSpotlight(focusNumber('width', SPOTLIGHT_DEFAULT_FOCUS.width), 0.02, 1)" in normalizer
    assert "clampSpotlight(focusNumber('height', SPOTLIGHT_DEFAULT_FOCUS.height), 0.02, 1)" in normalizer
    assert "clampSpotlight(focusNumber('x', SPOTLIGHT_DEFAULT_FOCUS.x), width / 2, 1 - width / 2)" in normalizer
    assert "clampSpotlight(focusNumber('y', SPOTLIGHT_DEFAULT_FOCUS.y), height / 2, 1 - height / 2)" in normalizer
    assert "clampSpotlight(\n    finiteSpotlightNumber(value.dim_opacity) ?? SPOTLIGHT_DEFAULT_DIM_OPACITY,\n    0,\n    SPOTLIGHT_MAX_DIM_OPACITY," in normalizer


def test_focus_shape_and_feather_use_backend_coordinate_contract():
    drawer = JS_SRC.split("function drawSpotlightShape", 1)[1].split("function drawSpotlightHardCutout", 1)[0]
    assert "const cx = focus.x * width;" in drawer
    assert "const cy = focus.y * height;" in drawer
    assert "const halfWidth = focus.width * width / 2;" in drawer
    assert "const halfHeight = focus.height * height / 2;" in drawer
    assert "ctx.ellipse(cx, cy, halfWidth, halfHeight, 0, 0, Math.PI * 2);" in drawer
    assert "ctx.rect(left, top, shapeWidth, shapeHeight);" in drawer
    assert "effect.corner_radius * Math.min(width, height)" in drawer
    assert "maskCtx.filter = `blur(${effect.feather * Math.min(width, height)}px)`;" in JS_SRC
    assert "feather degrades to a clean hard" in JS_SRC


def test_spotlight_is_footage_pass_before_stickers_subtitles_and_overlays():
    render_at = JS_SRC.split("const renderAt = (t) =>", 1)[1].split("useEffect(() =>", 1)[0]
    assert render_at.index("drawSpotlight(ctx, previewSpotlight);") < render_at.index("drawStickers(")
    assert render_at.index("drawStickers(") < render_at.index("drawEffects(")
    assert render_at.index("drawEffects(") < render_at.index("drawCaption(")
    assert render_at.index("drawCaption(") < render_at.index("drawOverlays(")

    tick = JS_SRC.split("const tick = () =>", 1)[1].split("const now = performance.now();", 1)[0]
    assert tick.index("drawSpotlight(ctx, previewSpotlight);") < tick.index("drawStickers(")
    assert tick.index("drawStickers(") < tick.index("drawEffects(")
    assert tick.index("drawEffects(") < tick.index("drawCaption(")
    assert tick.index("drawCaption(") < tick.index("drawOverlays(")
    assert "spotlightKey" in JS_SRC


def test_editor_exposes_spotlight_controls_and_wires_the_same_state():
    assert "function SpotlightControls({ spotlight, onChange })" in ASSET_PANEL_SRC
    assert 'aria-label="Product Spotlight"' in ASSET_PANEL_SRC
    assert 'type="checkbox"' in ASSET_PANEL_SRC
    assert "shape: 'ellipse'" in ASSET_PANEL_SRC
    assert "value={Number(focus.x)}" in ASSET_PANEL_SRC
    assert "value={Number(focus.y)}" in ASSET_PANEL_SRC
    assert "value={Number(focus.width)}" in ASSET_PANEL_SRC
    assert "value={Number(focus.height)}" in ASSET_PANEL_SRC
    assert "dim_opacity" in ASSET_PANEL_SRC
    assert "feather" in ASSET_PANEL_SRC
    assert "const patchSpotlight = useCallback" in EDITOR_SHELL_SRC
    assert EDITOR_SHELL_SRC.count("onSpotlightChange={patchSpotlight}") == 4
    assert EDITOR_SHELL_SRC.count("onSpotlightChangeLive={patchSpotlightLive}") == 2
    assert EDITOR_SHELL_SRC.count("onBeginDrag={beginDrag}") >= 4
    assert EDITOR_SHELL_SRC.count("onEndDrag={endDrag}") >= 4
    assert EDITOR_SHELL_SRC.count("spotlight={spotlight}") >= 4


def test_spotlight_preview_supports_direct_focus_manipulation_without_playback_side_effects():
    assert "handleSpotlightDragStart" in SEQUENCE_PLAYER_SRC
    assert "onSpotlightChangeLive" in SEQUENCE_PLAYER_SRC
    assert "onBeginDrag?.()" in SEQUENCE_PLAYER_SRC
    assert "onEndDrag?.()" in SEQUENCE_PLAYER_SRC
    assert "handleSpotlightKeyDown" in SEQUENCE_PLAYER_SRC
    assert "ArrowLeft" in SEQUENCE_PLAYER_SRC
    assert "focus.width / 2" in SEQUENCE_PLAYER_SRC
    assert "focus.height / 2" in SEQUENCE_PLAYER_SRC
    assert 'aria-label="จุดโฟกัส Product Spotlight ลากเพื่อย้าย กดลูกศรเพื่อขยับ"' in SEQUENCE_PLAYER_SRC
    drag = SEQUENCE_PLAYER_SRC.split("const handleSpotlightDragStart", 1)[1].split("const handleContainerClick", 1)[0]
    assert "togglePlay()" not in drag
