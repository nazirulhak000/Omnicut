"""Pure contract tests for the layered Cover Scene foundation."""

import copy

import pytest

from scripts.cover_scene import (
    LAYOUT_PRODUCT_FRONT_TEXT_UNDER,
    SAFE_ZONES,
    CoverSceneValidationError,
    bounds_for_output,
    normalize_scene,
    validate_scene,
)


def _scene(*layers, outputs=("9:16",)):
    return {
        "schema_version": 1,
        "outputs": list(outputs),
        "layout": {"preset": LAYOUT_PRODUCT_FRONT_TEXT_UNDER},
        "layers": list(layers),
    }


def test_normalizes_layer_order_by_z_index_and_exposes_render_order():
    scene = normalize_scene(_scene(
        {"id": "front", "type": "text", "role": "feature", "z_index": 30},
        {"id": "product", "type": "product", "z_index": 20},
        {"id": "behind", "type": "text", "placement": "behind", "z_index": 10},
        {"id": "background", "type": "background", "z_index": 0},
    ))

    assert scene["layer_order"] == ["background", "behind", "product", "front"]
    assert [layer["id"] for layer in scene["layers"]] == scene["layer_order"]


def test_rejects_duplicate_ids_and_behind_text_without_product():
    raw = _scene(
        {"id": "same", "type": "text", "placement": "behind", "z_index": 10},
        {"id": "same", "type": "text", "z_index": 20},
    )
    errors = validate_scene(raw)
    assert "layer ids must be unique" in errors
    assert any("requires a product layer" in error for error in errors)


@pytest.mark.parametrize("bad_layer", [
    {"id": "negative", "type": "text", "bounds": {"x": -0.01, "y": 0, "width": 0.2, "height": 0.2}},
    {"id": "overflow", "type": "text", "bounds": {"x": 0.8, "y": 0, "width": 0.3, "height": 0.2}},
    {"id": "zero", "type": "text", "bounds": {"x": 0, "y": 0, "width": 0, "height": 0.2}},
    {"id": "nan", "type": "text", "bounds": {"x": float("nan"), "y": 0, "width": 0.2, "height": 0.2}},
    {"id": "bad-z", "type": "text", "z_index": "front"},
])
def test_rejects_invalid_normalized_values(bad_layer):
    with pytest.raises(CoverSceneValidationError):
        normalize_scene(_scene(bad_layer))


def test_safe_zone_is_returned_and_content_outside_it_is_rejected():
    raw = _scene({
        "id": "title",
        "type": "text",
        "bounds": {"x": SAFE_ZONES["9:16"]["x"], "y": 0.80, "width": 0.5, "height": 0.05},
    })
    errors = validate_scene(raw)
    assert any("exceeds safe zone" in error for error in errors)

    valid = normalize_scene(_scene({"id": "title", "type": "text"}))
    assert valid["safe_zones"]["9:16"] == SAFE_ZONES["9:16"]


def test_legacy_cover_fields_get_a_deterministic_layer_fallback():
    legacy = {
        "custom_image_path": "03_Projects/demo/frame.jpg",
        "aspect_ratio": "both",
        "hook_text": "Soundcore Boom Go 3i",
        "sub_text": "กันน้ำ IPX7",
        "hook_position": "top",
        "template": "neon",
    }
    first = normalize_scene(legacy)
    second = normalize_scene(copy.deepcopy(legacy))

    assert first == second
    assert first["legacy_fallback"] is True
    assert first["outputs"] == ["9:16", "3:4"]
    assert first["layers"][0]["id"] == "legacy-background"
    assert [layer["role"] for layer in first["layers"]] == ["background", "model", "feature"]
    assert first["layers"][1]["text"] == "Soundcore Boom Go 3i"


def test_normalization_does_not_mutate_input_and_rounds_coordinates():
    raw = _scene({
        "id": "product",
        "type": "product",
        "bounds": {"x": 0.123456789, "y": 0.2, "width": 0.4, "height": 0.3},
        "source": {"asset_path": "product.png"},
    })
    before = copy.deepcopy(raw)
    normalized = normalize_scene(raw)

    assert raw == before
    assert normalized["layers"][0]["bounds"]["x"] == 0.123457
    normalized["layers"][0]["source"]["asset_path"] = "changed.png"
    assert raw["layers"][0]["source"]["asset_path"] == "product.png"


def test_accepts_flat_normalized_coordinates_and_emits_nested_bounds():
    scene = normalize_scene(_scene({
        "id": "product",
        "type": "product",
        "x": 0.1,
        "y": 0.2,
        "width": 0.5,
        "height": 0.4,
    }))
    assert scene["layers"][0]["bounds"] == {
        "x": 0.1,
        "y": 0.2,
        "width": 0.5,
        "height": 0.4,
    }


@pytest.mark.parametrize("output,size", [("9:16", (1080, 1920)), ("3:4", (1080, 1440))])
def test_supports_both_output_ratios(output, size):
    scene = normalize_scene(_scene({"id": "background", "type": "background"}, outputs=(output,)))
    assert scene["outputs"] == [output]
    canvas = bounds_for_output(scene, output)
    assert (canvas["width"], canvas["height"]) == size


def test_rejects_unknown_layout_and_output():
    errors = validate_scene({"outputs": ["1:1"], "layout": {"preset": "freeform"}, "layers": []})
    assert "unsupported output: '1:1'" in errors
    assert "unsupported layout preset: 'freeform'" in errors
