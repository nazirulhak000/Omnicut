"""Production-path frame gates for Sticker, Effect, and Spotlight overlays."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import pytest

from tests.motion_capture.overlay_pair import (
    compare_overlay_pair,
    create_empty_ass,
    create_overlay_source,
    create_silent_audio,
)
from tests.motion_capture.capture import temp_capture_dir


def _assert_pair_passes(result):
    assert result.live_contract, "the live fixture did not expose its overlay contract"
    # The browser decodes the source directly while the export is encoded as
    # H.264 before extraction. Sticker uses a fixed ROI; Spotlight and video
    # effects use the full production frame. The comparison is still the
    # structural gate, with delta metrics retained for diagnosis.
    assert result.comparison["passed"] is True, (
        f"full_or_roi={result.comparison}; delta={result.delta_comparison}"
    )
    assert result.comparison["mask_iou"] >= 0.90
    assert result.comparison["bbox_edge_delta_px"] <= 6
    assert result.comparison["centroid_delta_px"] <= 4
    assert result.comparison["mean_abs_error"] <= 0.08


def _fixture_inputs(tmp_root: Path):
    source = create_overlay_source(tmp_root)
    audio = create_silent_audio(tmp_root)
    ass = create_empty_ass(tmp_root)
    return source, audio, ass


def test_live_sticker_pair_matches_production_render(motion_fixture_url: str, monkeypatch):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    sticker = Path("02_Assets/Stickers_Memes/arrow_pointer_cyan_3d.png").resolve()
    with temp_capture_dir("overlay-sticker-pair-") as temp_root:
        root = Path(temp_root)
        source, audio, ass = _fixture_inputs(root)
        result = compare_overlay_pair(
            base_url=urlsplit(motion_fixture_url)._replace(query="").geturl(),
            output_dir=root / "pair",
            feature="sticker",
            source=source,
            audio=audio,
            ass=ass,
            asset=sticker,
        )
        _assert_pair_passes(result)


def test_live_spotlight_pair_matches_production_render(motion_fixture_url: str, monkeypatch):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    spotlight = {
        "schema_version": 1,
        "enabled": True,
        "shape": "ellipse",
        "focus": {"x": 0.5, "y": 0.45, "width": 0.52, "height": 0.34},
        "dim_opacity": 0.42,
        "feather": 0.02,
        "corner_radius": 0.08,
    }
    with temp_capture_dir("overlay-spotlight-pair-") as temp_root:
        root = Path(temp_root)
        source, audio, ass = _fixture_inputs(root)
        result = compare_overlay_pair(
            base_url=urlsplit(motion_fixture_url)._replace(query="").geturl(),
            output_dir=root / "pair",
            feature="spotlight",
            source=source,
            audio=audio,
            ass=ass,
            spotlight=spotlight,
        )
        _assert_pair_passes(result)


@pytest.mark.parametrize("effect_name", ["fx_checkmark_01.webm", "fx_arrow_01.webm"])
def test_live_effect_pair_matches_production_render(motion_fixture_url: str, monkeypatch, effect_name: str):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    effect = Path("02_Assets/Effects") / effect_name
    with temp_capture_dir(f"overlay-effect-{effect.stem}-") as temp_root:
        root = Path(temp_root)
        source, audio, ass = _fixture_inputs(root)
        result = compare_overlay_pair(
            base_url=urlsplit(motion_fixture_url)._replace(query="").geturl(),
            output_dir=root / "pair",
            feature="effect",
            source=source,
            audio=audio,
            ass=ass,
            asset=effect.resolve(),
        )
        _assert_pair_passes(result)
