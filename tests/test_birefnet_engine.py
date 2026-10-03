"""Unit tests for BiRefNet Engine and 3D Die-Cut Sticker Pipeline."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.birefnet_engine import (
    BiRefNetEngine,
    DEFAULT_MODEL,
    SUPPORTED_MODELS,
    _setup_cuda_dll_directory,
    _has_cuda_provider,
)
from tools.build_3d_pro_badges import (
    draw_3d_glossy_circle_badge,
    generate_universal_badges,
    generate_ecommerce_badges,
)


class TestBiRefNetEngineInitialization:
    """Test engine setup, model validation, and provider configuration."""

    def test_default_initialization(self) -> None:
        engine = BiRefNetEngine()
        assert engine.default_model == DEFAULT_MODEL
        assert engine.prefer_gpu is True
        assert engine.gpu_device_id == 0

    def test_custom_model_selection(self) -> None:
        engine = BiRefNetEngine(default_model="birefnet-general-lite")
        assert engine.default_model == "birefnet-general-lite"

    def test_unsupported_model_falls_back(self) -> None:
        engine = BiRefNetEngine(default_model="invalid-model-xyz")
        assert engine.default_model == DEFAULT_MODEL

    def test_is_cuda_available_returns_bool(self) -> None:
        engine = BiRefNetEngine()
        assert isinstance(engine.is_cuda_available, bool)

    def test_setup_cuda_dll_directory(self) -> None:
        # Should execute safely on all platforms without raising
        result = _setup_cuda_dll_directory()
        assert isinstance(result, bool)

    def test_provider_spec_cpu_when_gpu_disabled(self) -> None:
        engine = BiRefNetEngine(prefer_gpu=False)
        providers = engine._get_provider_spec()
        assert providers == ["CPUExecutionProvider"]


class TestDiecutStickerGeneration:
    """Test pure image synthesis of 3D die-cut white contours and drop shadows."""

    @pytest.fixture
    def sample_rgba_subject(self) -> Image.Image:
        """Create a transparent image with a 100x100 colored disc in the center."""
        img = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([50, 50, 150, 150], fill=(220, 50, 50, 255))
        return img

    def test_create_diecut_sticker_expands_and_composites(self, sample_rgba_subject: Image.Image) -> None:
        sticker = BiRefNetEngine.create_diecut_sticker(
            sample_rgba_subject,
            border_width=14,
            border_color=(255, 255, 255, 255),
            shadow_blur=16,
            shadow_offset=(0, 10),
            shadow_opacity=140,
        )

        assert isinstance(sticker, Image.Image)
        assert sticker.mode == "RGBA"
        # Content was 100x100 (50 to 150). With border and shadow, sticker should be > 100x100
        content_box = sample_rgba_subject.getbbox()
        assert content_box is not None
        content_w = content_box[2] - content_box[0]
        assert sticker.size[0] > content_w
        assert sticker.size[1] > content_w

        # Verify white die-cut border exists in the output
        get_pixels = getattr(sticker, "get_flattened_data", sticker.getdata)
        flat = list(get_pixels())
        # Convert flat RGBA list if flattened or tuples
        if flat and isinstance(flat[0], int):
            pixels = [tuple(flat[i:i+4]) for i in range(0, len(flat), 4)]
        else:
            pixels = flat
        has_white_border = any(
            p[0] == 255 and p[1] == 255 and p[2] == 255 and p[3] > 200
            for p in pixels
        )
        assert has_white_border, "Die-cut white border was not found in composite."

        # Verify soft shadow exists (pixels with alpha > 0 and RGB near black)
        has_shadow = any(
            p[0] < 50 and p[1] < 50 and p[2] < 50 and 0 < p[3] < 150
            for p in pixels
        )
        assert has_shadow, "Soft drop shadow was not found in composite."

    def test_create_diecut_sticker_empty_alpha(self) -> None:
        empty_img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        sticker = BiRefNetEngine.create_diecut_sticker(empty_img)
        assert sticker.mode == "RGBA"


class TestFileProcessingAndCLI:
    """Test file operations, atomic replacement, and error handling."""

    def test_process_file_missing_source_raises(self, tmp_path: Path) -> None:
        engine = BiRefNetEngine()
        non_existent = tmp_path / "does_not_exist.png"
        output = tmp_path / "output.png"
        with pytest.raises(FileNotFoundError):
            engine.process_file(non_existent, output)

    def test_process_file_with_mocked_removal(self, tmp_path: Path) -> None:
        engine = BiRefNetEngine()
        input_file = tmp_path / "input.png"
        output_file = tmp_path / "output.png"

        src_img = Image.new("RGBA", (120, 120), (100, 150, 200, 255))
        src_img.save(input_file)

        mock_cutout = Image.new("RGBA", (120, 120), (100, 150, 200, 255))
        with patch.object(engine, "remove_background", return_value=mock_cutout):
            out_p = engine.process_file(input_file, output_file, add_diecut=True, border_width=10)
            assert out_p == output_file
            assert output_file.exists()
            with Image.open(output_file) as loaded:
                assert loaded.mode == "RGBA"
                assert loaded.size[0] > 0


class TestUniversalBadgesGeneration:
    """Test generating the 6 canonical universal review badges."""

    def test_draw_3d_glossy_circle_badge(self, tmp_path: Path) -> None:
        badge_path = draw_3d_glossy_circle_badge(
            title_top="",
            title_main="TEST",
            title_sub="SUBTITLE",
            theme_color=(34, 197, 94),
            theme_dark=(21, 128, 61),
            icon_type="check",
            output_filename="test_badge.png",
            size=300,
            output_dir=tmp_path,
            add_diecut=True,
            border_width=10,
        )
        assert badge_path.exists()
        with Image.open(badge_path) as img:
            assert img.mode == "RGBA"
            assert img.size[0] >= 300
            assert img.size[1] >= 300

    def test_generate_universal_badges_creates_all_six(self, tmp_path: Path) -> None:
        paths = generate_universal_badges(output_dir=tmp_path, add_diecut=True)
        assert len(paths) == 6

        expected_filenames = {
            "badge_pros_review.png",
            "badge_cons_review.png",
            "badge_warning_review.png",
            "badge_pro_tip_review.png",
            "badge_verdict_review.png",
            "badge_score_review.png",
        }
        created_filenames = {p.name for p in paths}
        assert created_filenames == expected_filenames

        for p in paths:
            assert p.exists()
            with Image.open(p) as img:
                assert img.mode == "RGBA"
                assert img.size[0] > 0
                assert img.size[1] > 0
