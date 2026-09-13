"""Opt-in CoverScene wiring tests; legacy cover rendering stays untouched."""

from pathlib import Path

import pytest
from PIL import Image

import scripts.api_covers as covers
from scripts.cover_scene import CoverSceneValidationError


def _scene_layers():
    return [
        {"id": "background", "type": "background", "z_index": 0},
        {
            "id": "title", "type": "text", "role": "model", "text": "SCENE TITLE",
            "bounds": {"x": 0.12, "y": 0.10, "width": 0.76, "height": 0.12}, "z_index": 10,
        },
    ]


def test_legacy_request_keeps_identical_pixels(tmp_path, monkeypatch):
    monkeypatch.setattr(covers, "COVERS_DIR", tmp_path / "covers")
    first, _ = covers.render_pro_cover(export_stem="legacy-a")
    second, _ = covers.render_pro_cover(export_stem="legacy-b")

    assert first.read_bytes() == second.read_bytes()


@pytest.mark.parametrize("kwargs", [
    {"scene": {"layers": _scene_layers()}},
    {"layers": _scene_layers()},
    {"template": "product_front_text_under", "enable_hook_text": True, "hook_text": "รุ่นใหม่"},
])
def test_scene_dispatch_is_opt_in_and_reaches_scene_renderer(tmp_path, monkeypatch, kwargs):
    monkeypatch.setattr(covers, "COVERS_DIR", tmp_path / "covers")
    calls = []

    def fake_renderer(canvas, scene, font_path):
        calls.append(scene)
        return canvas

    monkeypatch.setattr(covers, "_render_cover_scene", fake_renderer)
    covers.render_pro_cover(export_stem="scene-dispatch", **kwargs)

    assert len(calls) == 1
    assert calls[0]["layer_order"][0].endswith("background")


def test_scene_layer_order_places_text_under_product(tmp_path, monkeypatch):
    output_dir = tmp_path / "covers"
    product_path = tmp_path / "product.png"
    Image.new("RGBA", (120, 120), (220, 30, 40, 255)).save(product_path)
    monkeypatch.setattr(covers, "COVERS_DIR", output_dir)
    monkeypatch.setattr(covers, "_resolve_media", lambda raw: product_path if raw == "product.png" else Path(raw))

    primary, _ = covers.render_pro_cover(
        export_stem="layer-order",
        layers=[
            {"id": "background", "type": "background", "z_index": 0},
            {
                "id": "under-title", "type": "text", "role": "model", "text": "UNDER",
                "placement": "behind", "z_index": 10,
                "bounds": {"x": 0.25, "y": 0.35, "width": 0.50, "height": 0.12},
            },
            {
                "id": "product", "type": "product", "z_index": 20, "fit": "stretch",
                "source": {"asset_path": "product.png"},
                "bounds": {"x": 0.25, "y": 0.35, "width": 0.50, "height": 0.12},
            },
        ],
    )

    with Image.open(primary) as image:
        pixel = image.convert("RGB").getpixel((540, round(0.41 * 1920)))
    assert pixel[0] > 180 and pixel[1] < 80 and pixel[2] < 80


def test_invalid_scene_rejects_before_writing_cover(tmp_path, monkeypatch):
    output_dir = tmp_path / "covers"
    monkeypatch.setattr(covers, "COVERS_DIR", output_dir)

    with pytest.raises(CoverSceneValidationError, match="exceeds safe zone"):
        covers.render_pro_cover(
            export_stem="invalid-scene",
            scene={
                "layers": [{
                    "id": "unsafe", "type": "text", "text": "unsafe",
                    "bounds": {"x": 0.06, "y": 0.80, "width": 0.5, "height": 0.05},
                }],
            },
        )

    assert not list(output_dir.glob("*_cover.jpg"))
