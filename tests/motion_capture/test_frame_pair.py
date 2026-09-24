"""Targeted gate for the real P1-F motion frame pair."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from PIL import Image, ImageDraw
import pytest

from tests.motion_capture.ass_fixture import (
    ComparisonThresholds,
    compare_frames,
    write_frame_diff_artifacts,
)
from tests.motion_capture.frame_pair import (
    CaptionPairSpec,
    FramePairSpec,
    compare_live_caption_pair,
    compare_live_frame_pair,
    default_pair_config,
)
from tests.motion_capture.capture import temp_capture_dir


def _fixture_url_for_spec(base_url: str, spec: FramePairSpec) -> str:
    parts = urlsplit(base_url)
    phase_key = "loop" if spec.phase == "loop" else spec.phase
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in {phase_key, "line"}
    ]
    query.append((phase_key, spec.preset_id))
    query.extend(("line", line) for line in spec.text_layers)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _assert_live_pair_passes(result: dict) -> None:
    assert result["pair_identity"]["all_match"] is True
    comparison = result["comparison"]
    assert result["status"] == "passed", (
        f"mask_iou={comparison['mask_iou']}, "
        f"raw_mask_iou={comparison['raw_mask_iou']}, "
        f"bbox_edge_delta_px={comparison['bbox_edge_delta_px']}, "
        f"centroid_delta_px={comparison['centroid_delta_px']}, "
        f"mean_abs_error={comparison['mean_abs_error']}"
    )
    assert result["pixel_parity_claim"] is True
    assert result["comparison"]["passed"] is True
    assert result["runtime"]["clean"] is True


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


@pytest.mark.parametrize(
    "text",
    [
        "นั่งนิ่งจริงครับ",
        "Motion Preview",
        "ยอดขาย 1,125 ชิ้น",
        "บรรทัดหนึ่ง\nLINE TWO\nราคา 9,990 บาท",
    ],
    ids=["thai", "english", "numbers", "three_lines"],
)
def test_live_caption_pair_passes_production_caption_gate(motion_fixture_url: str, text: str):
    spec = CaptionPairSpec(text=text)
    parts = urlsplit(motion_fixture_url)
    url = urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path,
        urlencode({"mode": "caption", "caption": spec.text}),
        parts.fragment,
    ))
    with temp_capture_dir("caption-live-pair-") as temp_root:
        result = compare_live_caption_pair(
            default_pair_config(url, Path(temp_root) / "pair"),
            spec,
        )

        assert result["pair_identity"]["all_match"] is True
        assert result["status"] == "passed", (
            f"mask_iou={result['comparison']['mask_iou']}, "
            f"bbox_edge_delta_px={result['comparison']['bbox_edge_delta_px']}, "
            f"centroid_delta_px={result['comparison']['centroid_delta_px']}, "
            f"mean_abs_error={result['comparison']['mean_abs_error']}"
        )
        assert result["pixel_parity_claim"] is True
        assert result["runtime"]["clean"] is True


@pytest.mark.parametrize(
    ("case_name", "text_layers"),
    [
        ("thai_marks", ("ทดสอบวรรณยุกต์ไทย", "นั่งนิ่งจริงครับ")),
        ("english", ("Motion Preview", "Render Parity")),
        ("numbers_emoji", ("ยอดขาย 1,125 ชิ้น", "เร็วขึ้น 2× 🚀")),
        ("three_lines", ("บรรทัดหนึ่ง", "LINE TWO", "ราคา 9,990 บาท")),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_live_language_and_line_count_matrix_passes_strict_gate(
    motion_fixture_url: str,
    case_name: str,
    text_layers: tuple[str, ...],
):
    spec = FramePairSpec(
        preset_id="hook.loop.none",
        phase="loop",
        frame_index=18,
        timestamp_ms=600,
        phase_window_ms=(450, 1850),
        text_layers=text_layers,
    )
    with temp_capture_dir(f"motion-language-{case_name}-") as temp_root:
        url = _fixture_url_for_spec(motion_fixture_url, spec)
        result = compare_live_frame_pair(
            default_pair_config(url, Path(temp_root) / "pair"),
            spec,
        )

        _assert_live_pair_passes(result)


@pytest.mark.parametrize(
    ("case_name", "preset_id", "phase", "frame_index", "timestamp_ms", "phase_window_ms"),
    [
        ("in_start", "hook.in.bounce", "in", 3, 100, (0, 450)),
        ("in_middle", "hook.in.bounce", "in", 7, 233, (0, 450)),
        ("in_end", "hook.in.bounce", "in", 12, 400, (0, 450)),
        ("hold_start", "hook.loop.pulse", "loop", 15, 500, (450, 1850)),
        ("hold_middle", "hook.loop.pulse", "loop", 34, 1133, (450, 1850)),
        ("hold_end", "hook.loop.pulse", "loop", 54, 1800, (450, 1850)),
        ("out_start", "hook.out.fade", "out", 56, 1867, (1850, 2000)),
        ("out_middle", "hook.out.fade", "out", 58, 1933, (1850, 2000)),
        ("out_end", "hook.out.fade", "out", 59, 1967, (1850, 2000)),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_live_in_hold_out_start_middle_end_frames_pass_strict_gate(
    motion_fixture_url: str,
    case_name: str,
    preset_id: str,
    phase: str,
    frame_index: int,
    timestamp_ms: int,
    phase_window_ms: tuple[int, int],
):
    spec = FramePairSpec(
        preset_id=preset_id,
        phase=phase,
        frame_index=frame_index,
        timestamp_ms=timestamp_ms,
        phase_window_ms=phase_window_ms,
    )
    with temp_capture_dir(f"motion-phase-{case_name}-") as temp_root:
        url = _fixture_url_for_spec(motion_fixture_url, spec)
        result = compare_live_frame_pair(
            default_pair_config(url, Path(temp_root) / "pair"),
            spec,
        )

        _assert_live_pair_passes(result)
