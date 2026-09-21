"""Tests for HyperFramesEngine."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.hyperframes_engine import HyperFramesEngine


def test_is_available():
    """Verify is_available returns a boolean."""
    avail = HyperFramesEngine.is_available()
    assert isinstance(avail, bool)


def test_generate_spec_card_html():
    """Verify HTML generation with specs and GSAP animation."""
    specs = {
        "processor": "Snapdragon 8 Gen 3",
        "camera": "50MP Leica Dual",
        "battery": "4,780 mAh / 67W"
    }
    html = HyperFramesEngine._generate_spec_card_html(
        product_name="Xiaomi MIX Flip",
        specs=specs,
        duration=6.0
    )
    assert "Xiaomi MIX Flip" in html
    assert "Snapdragon 8 Gen 3" in html
    assert "50MP Leica Dual" in html
    assert "4,780 mAh / 67W" in html
    assert 'data-resolution="portrait"' in html
    assert 'data-width="1080"' in html
    assert 'data-height="1920"' in html
    assert "gsap.timeline" in html
    assert "window.__timelines" in html


@patch("subprocess.run")
def test_render_composition_success(mock_run, tmp_path):
    """Verify render_composition executes npx hyperframes correctly."""
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    
    out_webm = tmp_path / "test_out.webm"
    out_webm.write_bytes(b"fake webm data")

    success = HyperFramesEngine.render_composition(
        project_dir=tmp_path,
        output_path=out_webm,
        format_type="webm",
        resolution="portrait",
        low_memory_mode=True
    )
    assert success is True
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "hyperframes" in cmd
    assert "--format" in cmd
    assert "webm" in cmd
    assert "--resolution=portrait" in cmd
    assert "--low-memory-mode" in cmd


@patch("subprocess.run")
def test_render_composition_failure(mock_run, tmp_path):
    """Verify render_composition handles CLI failures gracefully."""
    mock_run.return_value = MagicMock(returncode=1, stderr="Render error occurred")
    
    out_webm = tmp_path / "test_out.webm"
    success = HyperFramesEngine.render_composition(
        project_dir=tmp_path,
        output_path=out_webm,
        format_type="webm"
    )
    assert success is False
