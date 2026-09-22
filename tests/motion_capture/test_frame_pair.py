"""Targeted gate for the real P1-F motion frame pair."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from tests.motion_capture.ass_fixture import (
    ComparisonThresholds,
    compare_frames,
    write_frame_diff_artifacts,
)
from tests.motion_capture.frame_pair import (
    compare_live_frame_pair,
    default_pair_config,
)
from tests.motion_capture.capture import temp_capture_dir


def test_compare_frames_emits_metrics_for_a_real_png_pair():
    """The metric seam is deterministic and writes images only under .tmp."""

    with temp_capture_dir("motion-metric-") as temp_root:
        root = Path(temp_root)
        left = root / "left.png"
        right = root / "right.png"
        for path in (left, right):
            image = Image.new("RGB", (32, 24), "black")
            ImageDraw.Draw(image).rectangle((8, 6, 23, 17), fill="white")
            image.save(path, format="PNG", optimize=False)

        result = compare_frames(left, right, ComparisonThresholds())

        assert result.exact_pixel_match is True
        assert result.passed is True
        assert result.raw_mask_iou == 1.0
        assert result.mask_iou == 1.0
        assert result.bbox_edge_delta_px == 0
        assert result.centroid_delta_px == 0


def test_visual_diff_artifacts_make_a_failed_comparison_inspectable():
    with temp_capture_dir("motion-diff-") as temp_root:
        root = Path(temp_root)
        reference = root / "reference.png"
        candidate = root / "candidate.png"
        left = Image.new("RGB", (32, 24), "black")
        right = Image.new("RGB", (32, 24), "black")
        ImageDraw.Draw(left).rectangle((6, 6, 17, 17), fill="white")
        ImageDraw.Draw(right).rectangle((12, 6, 23, 17), fill="white")
        left.save(reference, format="PNG", optimize=False)
        right.save(candidate, format="PNG", optimize=False)

        comparison = compare_frames(reference, candidate, ComparisonThresholds())
        artifacts = write_frame_diff_artifacts(reference, candidate, root / "diff")

        assert comparison.passed is False
        assert set(artifacts) == {"absolute_diff", "heatmap", "reference_mask", "candidate_mask"}
        assert all((root / "diff" / artifact["path"]).exists() for artifact in artifacts.values())


def test_self_hosted_live_pair_passes_the_production_motion_layout_gate(motion_fixture_url: str):
    """The real Canvas and production ASS paths share one layout contract."""

    with temp_capture_dir("motion-live-pair-") as temp_root:
        output_dir = Path(temp_root) / "pair"
        config = default_pair_config(motion_fixture_url, output_dir)
        result = compare_live_frame_pair(config)

        assert result["pair_identity"]["all_match"] is True
        assert result["comparison"]["width"] > 0
        assert result["comparison"]["height"] > 0
        assert result["status"] == "passed"
        assert result["pixel_parity_claim"] is True
        assert result["comparison"]["passed"] is True
        assert result["comparison"]["raw_mask_iou"] < result["comparison"]["mask_iou"]
        assert result["runtime"]["clean"] is True
        assert (output_dir / "pair_result.json").exists()
        assert all(
            (output_dir / "diff" / artifact["path"]).exists()
            for artifact in result["diff_artifacts"].values()
        )
