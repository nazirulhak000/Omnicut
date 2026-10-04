"""Tests for the hybrid SAM 2 auto-prompt derivation (scripts/cutout_prompt.py).

These cover the regression that made Cutout unusable on real footage: with no
prompt the SAM 2 worker fell back to the frame centre, so a hand-held product
sitting off centre was replaced by the hand (measured 38.74% mask vs 0.58% with
a product point).  Everything here is offline and deterministic.
"""

import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from scripts.background_isolation import normalize_background_isolation
from scripts.background_isolation_video_worker import derive_sam2_prompts, video_artifact_id
from scripts.cutout_prompt import (
    MAX_SUBJECT_POINTS,
    build_sam2_prompts,
    foreground_mask,
    format_prompt_points,
    normalize_subject_points,
    parse_prompt_points,
    subject_points_from_frame,
    subject_points_from_mask,
)

SKIN_COLOUR = (214, 168, 138)
PRODUCT_COLOUR = (48, 46, 52)
MERGED_PRODUCT = (70, 110, 40, 80)
SPLIT_HAND = (110, 190, 0, 120)
SPLIT_PRODUCT = (20, 60, 30, 70)


def _canvas(width: int = 120, height: int = 200) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def _paint(canvas: np.ndarray, box: tuple[int, int, int, int], colour: tuple[int, int, int]) -> None:
    y0, y1, x0, x1 = box
    canvas[y0:y1, x0:x1] = colour


def _mask_for(canvas: np.ndarray, boxes: list[tuple[int, int, int, int]]) -> np.ndarray:
    mask = np.zeros(canvas.shape[:2], dtype=bool)
    for y0, y1, x0, x1 in boxes:
        mask[y0:y1, x0:x1] = True
    return mask


def _hand_and_product(*, merged_blob: bool) -> tuple[np.ndarray, np.ndarray]:
    """A skin-toned hand with a dark product, either separate or in one blob.

    The merged case mirrors the measured real frame: isnet-general-use returned a
    single 25% blob because the earbuds touch the fingers, so the product has to
    be found as the colour-outlier region inside that blob.
    """
    canvas = _canvas()
    if merged_blob:
        hand_box = (40, 190, 0, 120)
        product_box = (70, 110, 40, 80)
        _paint(canvas, hand_box, SKIN_COLOUR)
        _paint(canvas, product_box, PRODUCT_COLOUR)
        return canvas, _mask_for(canvas, [hand_box])
    _paint(canvas, SPLIT_HAND, SKIN_COLOUR)
    _paint(canvas, SPLIT_PRODUCT, PRODUCT_COLOUR)
    return canvas, _mask_for(canvas, [SPLIT_HAND, SPLIT_PRODUCT])


def _in_box(point: dict[str, float], box: tuple[int, int, int, int], canvas: np.ndarray) -> bool:
    height, width = canvas.shape[:2]
    y0, y1, x0, x1 = box
    x = point["x"] * width
    y = point["y"] * height
    return x0 <= x < x1 and y0 <= y < y1


class _FakeRembg:
    def __init__(self, rgba: Image.Image) -> None:
        self._rgba = rgba
        self.calls: list[dict[str, object]] = []

    def remove(self, image: Image.Image, **kwargs: object) -> Image.Image:
        self.calls.append(kwargs)
        return self._rgba


class _FakeWorker:
    """Stands in for BackgroundIsolationWorker without loading rembg."""

    def __init__(self, rembg: object | None = None, error: Exception | None = None) -> None:
        self._rembg = rembg
        self._error = error
        self.models: list[str] = []

    def _get_session(self, model: str) -> tuple[object, None]:
        self.models.append(model)
        if self._error is not None:
            raise self._error
        return self._rembg, None


def _video_config(**extra: object) -> dict[str, object]:
    base: dict[str, object] = {
        "schema_version": 1,
        "enabled": True,
        "mode": "cutout",
        "engine": "sam2",
        "model": "sam2.1_hiera_tiny",
        "quality": "balanced",
        "fallback": "spotlight",
        "artifact": {"schema_version": 1, "id": None, "status": "missing"},
    }
    return {**base, **extra}


def _rgba_image(canvas: np.ndarray, mask: np.ndarray) -> Image.Image:
    return Image.fromarray(np.dstack([canvas, (mask * 255).astype(np.uint8)]), "RGBA")


def test_normalize_subject_points_clamps_caps_and_drops_junk():
    assert normalize_subject_points([
        {"x": 1.5, "y": -0.2},
        [0.4, 0.6],
        {"x": "bad", "y": 0.5},
        "nope",
        {"x": 0.2, "y": 0.3, "label": 0},
    ]) == [
        {"x": 1.0, "y": 0.0, "label": 1},
        {"x": 0.4, "y": 0.6, "label": 1},
        {"x": 0.2, "y": 0.3, "label": 0},
    ]
    flooded = [{"x": index / 50, "y": 0.5} for index in range(20)]
    assert len(normalize_subject_points(flooded)) == MAX_SUBJECT_POINTS
    assert normalize_subject_points("0.5,0.5") == []
    assert normalize_subject_points(None) == []


def test_prompt_points_format_round_trips_through_the_command_line():
    points = [{"x": 0.34383, "y": 0.46389, "label": 1}, {"x": 0.99815, "y": 0.99687, "label": 0}]
    text = format_prompt_points(points)
    assert text == "0.34383,0.46389,1;0.99815,0.99687,0"
    assert '"' not in text and " " not in text
    assert parse_prompt_points(text) == points
    assert parse_prompt_points("") == []
    assert parse_prompt_points("garbage") == []
    assert parse_prompt_points(None) == []


def test_prompt_points_with_frame_index_round_trips():
    points = [
        {"x": 0.5, "y": 0.5, "label": 1, "frame": 0},
        {"x": 0.2, "y": 0.8, "label": 1, "frame": 150},
        {"x": 0.95, "y": 0.95, "label": 0, "frame": 150},
    ]
    text = format_prompt_points(points)
    assert text == "0.5,0.5,1,0;0.2,0.8,1,150;0.95,0.95,0,150"
    parsed = parse_prompt_points(text)
    assert parsed == points



def test_build_sam2_prompts_wraps_points_into_the_worker_payload():
    assert build_sam2_prompts(subject_points=[{"x": 0.25, "y": 0.5}]) == [
        {"object_id": 1, "points": [[0.25, 0.5]], "labels": [1]},
    ]
    assert build_sam2_prompts(subject_points=[]) is None
    assert build_sam2_prompts(subject_points=None, mask=None) is None


def test_auto_prompt_prefers_the_product_when_the_model_separated_it():
    canvas, mask = _hand_and_product(merged_blob=False)
    points = subject_points_from_mask(mask, canvas)
    assert len(points) == 1
    assert _in_box(points[0], SPLIT_PRODUCT, canvas), points


def test_auto_prompt_finds_the_product_inside_one_merged_blob():
    """Regression: the measured real frame was a single hand+product blob."""
    canvas, mask = _hand_and_product(merged_blob=True)
    points = subject_points_from_mask(mask, canvas)
    assert len(points) == 1
    assert _in_box(points[0], MERGED_PRODUCT, canvas), points


def test_auto_prompt_refuses_a_whole_frame_mask():
    """The centre-point fallback produced a 100% opaque 'cutout'; derive nothing."""
    canvas = _canvas()
    _paint(canvas, (0, 200, 0, 120), SKIN_COLOUR)
    assert subject_points_from_mask(np.ones(canvas.shape[:2], dtype=bool), canvas) == []


def test_auto_prompt_returns_nothing_without_a_subject():
    canvas = _canvas()
    assert subject_points_from_mask(np.zeros(canvas.shape[:2], dtype=bool), canvas) == []
    assert subject_points_from_mask(np.zeros((0, 0), dtype=bool)) == []


def test_foreground_mask_accepts_a_boolean_mask_or_an_alpha_plane():
    """Regression: True > 32 is False, which silently emptied every derived point."""
    boolean = np.zeros((4, 4), dtype=bool)
    boolean[1:3, 1:3] = True
    assert foreground_mask(boolean).sum() == 4
    alpha = (boolean * 255).astype(np.uint8)
    assert np.array_equal(foreground_mask(alpha), boolean)
    rgba = np.dstack([np.zeros((4, 4, 3), np.uint8), alpha])
    assert np.array_equal(foreground_mask(rgba), boolean)
    assert foreground_mask(np.zeros((0, 0), dtype=bool)).shape == (0, 0)


def test_subject_points_from_frame_uses_the_injected_cutout_model():
    canvas, mask = _hand_and_product(merged_blob=True)
    remover = _FakeRembg(_rgba_image(canvas, mask))
    points = subject_points_from_frame(
        Image.fromarray(canvas, "RGB"), remove_background=remover.remove,
    )
    assert points is not None and len(points) == 2
    assert _in_box(points[0], MERGED_PRODUCT, canvas), points
    assert points[1]["label"] == 0
    assert remover.calls == [{}]


def test_subject_points_from_frame_degrades_instead_of_raising():
    def boom(_image: Image.Image) -> Image.Image:
        raise RuntimeError("rembg ไม่พร้อมใช้งาน")

    assert subject_points_from_frame(Image.new("RGB", (10, 10)), remove_background=boom) is None
    assert subject_points_from_frame(Image.new("RGB", (10, 10)), remove_background=None) is None


def test_derive_sam2_prompts_uses_the_frame_derivation(monkeypatch, tmp_path):
    canvas, mask = _hand_and_product(merged_blob=True)
    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(list(command))
        _rgba_image(canvas, mask).convert("RGB").save(Path(command[-1]), "JPEG")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    worker = _FakeWorker(_FakeRembg(_rgba_image(canvas, mask)))
    points = derive_sam2_prompts(
        _video_config(), Path("01_Raw") / "clip.mov", tmp_path,
        start=2.0, width=120, height=200, worker=worker,
    )

    assert points is not None and _in_box(points[0], MERGED_PRODUCT, canvas)
    assert worker.models == ["isnet-general-use"]
    assert calls and calls[0][calls[0].index("-ss") + 1] == "2.0"
    assert not (tmp_path / ".prompt_frame.jpg").exists()


def test_derive_sam2_prompts_prefers_editor_points_over_the_model(monkeypatch, tmp_path):
    def explode(*_args, **_kwargs):
        raise AssertionError("ffmpeg must not run when the editor picked a point")

    monkeypatch.setattr(subprocess, "run", explode)
    worker = _FakeWorker(error=AssertionError("rembg must not load"))
    points = derive_sam2_prompts(
        _video_config(subject_points=[{"x": 0.36, "y": 0.47, "label": 1}]),
        Path("01_Raw") / "clip.mov", tmp_path,
        start=0.0, width=120, height=200, worker=worker,
    )

    assert points == [{"x": 0.36, "y": 0.47, "label": 1}]
    assert worker.models == []


def test_derive_sam2_prompts_degrades_even_when_stdout_cannot_print_thai(monkeypatch, tmp_path):
    """A cp1252 stdout made the warning print raise out of the except handler."""
    import builtins

    real_print = builtins.print

    def ascii_only_print(*args, **kwargs):
        for arg in args:
            str(arg).encode("ascii")  # raises UnicodeEncodeError like a cp1252 pipe
        return real_print(*args, **kwargs)

    def fail_ffmpeg(*_args, **_kwargs):
        raise RuntimeError("ffmpeg ไม่พร้อมใช้งาน")

    monkeypatch.setattr(subprocess, "run", fail_ffmpeg)
    monkeypatch.setattr(builtins, "print", ascii_only_print)

    points = derive_sam2_prompts(
        _video_config(), Path("01_Raw") / "clip.mov", tmp_path,
        start=0.0, width=120, height=200, worker=_FakeWorker(error=AssertionError("rembg must not load")),
    )

    assert points is None


def test_derive_sam2_prompts_honours_auto_prompt_off(monkeypatch, tmp_path):
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: pytest.fail("no ffmpeg"))
    assert derive_sam2_prompts(
        _video_config(auto_prompt=False), Path("01_Raw") / "clip.mov", tmp_path,
        start=0.0, width=120, height=200, worker=_FakeWorker(),
    ) is None


def test_derive_sam2_prompts_degrades_when_the_derivation_breaks(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess, "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0),
    )
    worker = _FakeWorker(error=RuntimeError("ไม่มีโมเดล"))
    assert derive_sam2_prompts(
        _video_config(), Path("01_Raw") / "clip.mov", tmp_path,
        start=0.0, width=120, height=200, worker=worker,
    ) is None


def test_artifact_id_changes_only_when_the_points_change():
    kwargs = dict(
        start=0.0, duration=1.0, fps=30.0, timebase="1/30", width=540, height=960, rotation=0,
    )
    base = video_artifact_id("fingerprint", _video_config(), **kwargs)
    points = [{"x": 0.3, "y": 0.5, "label": 1}]
    with_points = video_artifact_id("fingerprint", _video_config(subject_points=points), **kwargs)
    repeated = video_artifact_id("fingerprint", _video_config(subject_points=list(points)), **kwargs)
    moved = video_artifact_id(
        "fingerprint", _video_config(subject_points=[{"x": 0.4, "y": 0.5, "label": 1}]), **kwargs,
    )

    assert with_points == repeated
    assert with_points != base
    assert moved != with_points
    assert video_artifact_id("fingerprint", _video_config(auto_prompt=False), **kwargs) != base


def test_contract_keeps_subject_points_and_auto_prompt():
    normalized = normalize_background_isolation(_video_config(
        subject_points=[{"x": 1.4, "y": 0.5}, {"x": "bad", "y": 0.2}], auto_prompt=False,
    ))

    assert normalized["enabled"] is True
    assert normalized["subject_points"] == [{"x": 1.0, "y": 0.5, "label": 1}]
    assert normalized["auto_prompt"] is False
    assert "subject_points" not in normalize_background_isolation(_video_config())
    assert "auto_prompt" not in normalize_background_isolation(_video_config(auto_prompt=True))


def test_contract_rejects_a_non_boolean_auto_prompt():
    assert normalize_background_isolation(_video_config(auto_prompt="yes"))["enabled"] is False


def test_derive_sam2_prompts_smart_fallback_for_subsequent_clip(monkeypatch, tmp_path):
    canvas, mask = _hand_and_product(merged_blob=True)
    calls = []

    def fake_run(command, **_kwargs):
        calls.append(list(command))
        dest = Path(command[command.index("-y") + 1])
        Image.fromarray(canvas).save(dest)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    worker = _FakeWorker(_FakeRembg(_rgba_image(canvas, mask)))

    explicit = [{"x": 0.1, "y": 0.1, "label": 1}]
    config = _video_config(subject_points=explicit, prompt_reference_start=0.0)

    # 1. Clip 1 at start=0.0: matches reference -> uses explicit points
    points_clip1 = derive_sam2_prompts(
        config, Path("01_Raw") / "clip.mov", tmp_path,
        start=0.0, width=120, height=200, worker=worker,
    )
    assert points_clip1 == explicit
    assert len(calls) == 0

    # 2. Clip 2 at start=5.0: subsequent shot -> falls back to auto-detection at 5.0s
    points_clip2 = derive_sam2_prompts(
        config, Path("01_Raw") / "clip.mov", tmp_path,
        start=5.0, width=120, height=200, worker=worker,
    )
    assert points_clip2 is not None
    assert points_clip2 != explicit  # does NOT blindly use clip 1's coords
    assert len(calls) == 1
    assert calls[0][calls[0].index("-ss") + 1] == "5.0"


def test_derive_sam2_prompts_multi_interval_seeds_subsequent_intervals(monkeypatch, tmp_path):
    canvas, mask = _hand_and_product(merged_blob=True)
    calls = []

    def fake_run(command, **_kwargs):
        calls.append(list(command))
        dest = Path(command[command.index("-y") + 1])
        Image.fromarray(canvas).save(dest)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    worker = _FakeWorker(_FakeRembg(_rgba_image(canvas, mask)))

    explicit = [{"x": 0.5, "y": 0.5, "label": 1}]
    config = _video_config(subject_points=explicit)
    intervals = [(0.0, 2.0), (4.0, 6.0)]

    points = derive_sam2_prompts(
        config, Path("01_Raw") / "clip.mov", tmp_path,
        start=0.0, width=120, height=200, worker=worker,
        active_intervals=intervals, fps=30.0,
    )
    assert points is not None
    # Interval 0 has frame 0
    assert any(p.get("frame") == 0 for p in points)
    # Interval 1 has frame 120 (4.0s * 30fps)
    assert any(p.get("frame") == 120 for p in points)
    assert len(calls) == 1
    assert calls[0][calls[0].index("-ss") + 1] == "4.0"


def test_artifact_id_changes_when_prompt_reference_start_changes():
    kwargs = dict(
        start=0.0, duration=1.0, fps=30.0, timebase="1/30", width=540, height=960, rotation=0,
    )
    points = [{"x": 0.3, "y": 0.5, "label": 1}]
    ref_0 = video_artifact_id("fingerprint", _video_config(subject_points=points, prompt_reference_start=0.0), **kwargs)
    ref_5 = video_artifact_id("fingerprint", _video_config(subject_points=points, prompt_reference_start=5.0), **kwargs)

    assert ref_0 != ref_5


@pytest.mark.parametrize("job_start,reference_source", [(0.1, "a/clip.mp4"), (0.0, "b/clip.mp4")])
def test_prompts_never_reuse_other_window_or_same_basename_source(monkeypatch, tmp_path, job_start, reference_source):
    monkeypatch.setattr("scripts.background_isolation_video_worker._derive_points_for_timestamp", lambda *_: None)
    config = _video_config(subject_points=[{"x": 0.1, "y": 0.2}],
                           prompt_reference_start=0.0, prompt_reference_source=reference_source)
    assert derive_sam2_prompts(config, Path("a/clip.mp4"), tmp_path, start=job_start,
                              width=100, height=100, worker=_FakeWorker()) is None


def test_scoped_first_interval_after_trim_keeps_manual_frame_zero_and_seeds_interval(monkeypatch, tmp_path):
    calls = []
    def derive(_source, _staged, timestamp, *_args):
        calls.append(timestamp)
        return [{"x": 0.7, "y": 0.8, "label": 1}]
    monkeypatch.setattr("scripts.background_isolation_video_worker._derive_points_for_timestamp", derive)
    points = derive_sam2_prompts(_video_config(subject_points=[{"x": 0.1, "y": 0.2}], prompt_reference_start=2),
        Path("clip.mp4"), tmp_path, start=2, width=100, height=100, worker=_FakeWorker(),
        active_intervals=[(3, 4)], fps=30)
    assert points == [{"x": 0.1, "y": 0.2, "label": 1, "frame": 0},
                      {"x": 0.7, "y": 0.8, "label": 1, "frame": 30}]
    assert calls == [3]


def test_auto_seeds_every_interval_even_when_first_derivation_fails(monkeypatch, tmp_path):
    calls = []
    def derive(_source, _staged, timestamp, *_args):
        calls.append(timestamp)
        return [{"x": 0.7, "y": 0.8, "label": 1}] if timestamp else None
    monkeypatch.setattr("scripts.background_isolation_video_worker._derive_points_for_timestamp", derive)
    points = derive_sam2_prompts(_video_config(subject_points=[{"x": 0.1, "y": 0.2}], prompt_reference_start=5),
        Path("clip.mp4"), tmp_path, start=0, width=100, height=100, worker=_FakeWorker(),
        active_intervals=[(1, 2), (3, 4)], fps=30)
    assert calls == [0, 1, 3]
    assert [point["frame"] for point in points] == [0, 30, 90]
    assert points[0]["x"] == 0.5  # explicit point from another window never leaks


def test_many_interval_seeds_survive_worker_cli_without_32_point_truncation():
    points = [{"x": round(0.1 + index / 20, 5), "y": 0.4, "label": index % 2, "frame": frame * 30}
              for frame in range(6) for index in range(8)]
    assert parse_prompt_points(format_prompt_points(points)) == points


@pytest.mark.parametrize("frame", [float("inf"), float("nan"), {}, "junk"])
def test_malformed_prompt_frame_cannot_raise_or_become_frame_zero(frame):
    assert normalize_subject_points([{"x": 0.3, "y": 0.4, "frame": frame}]) == []


@pytest.mark.parametrize("start", [float("inf"), float("nan"), True, -1])
def test_nonfinite_or_invalid_prompt_reference_fails_closed(start):
    assert not normalize_background_isolation(_video_config(prompt_reference_start=start))["enabled"]


def test_cache_reference_identity_keeps_precision_and_source_scope():
    args = dict(start=0, duration=1, fps=30, timebase="1/30", width=16, height=16, rotation=0)
    config = _video_config(subject_points=[{"x": 0.3, "y": 0.4}], prompt_reference_start=0.001,
                           prompt_reference_source="a/clip.mp4")
    first = video_artifact_id("fingerprint", config, **args)
    assert first != video_artifact_id("fingerprint", {**config, "prompt_reference_start": 0.004}, **args)
    assert first != video_artifact_id("fingerprint", {**config, "prompt_reference_source": "b/clip.mp4"}, **args)


@pytest.mark.parametrize("auto_prompt", [False, True])
def test_legacy_points_without_reference_nonzero_start_use_safe_fallback(monkeypatch, tmp_path, auto_prompt):
    explicit = [{"x": 0.1, "y": 0.2, "label": 1}]
    fresh = [{"x": 0.7, "y": 0.8, "label": 1}]
    timestamps = []
    def derive(_source, _staged, timestamp, *_args):
        timestamps.append(timestamp)
        return fresh
    monkeypatch.setattr("scripts.background_isolation_video_worker._derive_points_for_timestamp", derive)
    points = derive_sam2_prompts(_video_config(subject_points=explicit, auto_prompt=auto_prompt),
        Path("clip.mp4"), tmp_path, start=5, width=100, height=100, worker=_FakeWorker())
    assert points == (fresh if auto_prompt else None)
    assert timestamps == ([5] if auto_prompt else [])
    # Re-picking gives an actual reference, restoring the manual choice even
    # when automatic discovery is intentionally switched off.
    referenced = derive_sam2_prompts(_video_config(subject_points=explicit, auto_prompt=False,
        prompt_reference_start=5, prompt_reference_source="clip.mp4"), Path("clip.mp4"), tmp_path,
        start=5, width=100, height=100, worker=_FakeWorker())
    assert referenced == explicit


def test_sam2_fallback_semantic_change_invalidates_v2_cache_without_touching_rembg():
    args = dict(start=5, duration=1, fps=30, timebase="1/30", width=540, height=960, rotation=0)
    config = {"enabled": True, "engine": "sam2", "model": "sam2.1_hiera_tiny",
              "subject_points": [{"x": 0.1, "y": 0.2, "label": 1}], "auto_prompt": False}
    # IDs recorded from the delivered v2 worker before its cache bump. The
    # existing masks are immutable; preparing SAM2 must publish a fresh ID.
    assert video_artifact_id("legacy-no-reference-fixture", config, **args) != "bgseq1-01a76ca14cea3ef0"
    rembg = {**config, "engine": "rembg", "model": "u2net"}
    assert video_artifact_id("legacy-no-reference-fixture", rembg, **args) == "bgseq1-1b0ab8632cd3e690"
