"""Behavioral tests for scripts/image_motion_engine.py.

ImageMotionEngine.generate_motion_video_from_images builds a Ken-Burns
zoompan filter-graph per image segment and shells out to ffmpeg. It is
called from scripts/pipeline.py and scripts/stages/shot_matching_stage.py
whenever a project has no raw video and must fall back to a still-image
slideshow, so its output feeds straight into the same rendering pipeline
video_editor.py assembles from -- a bad zoom expression or a fractional/zero
frame count here would reach ffmpeg with no clamp at all.

BUG FOUND: as originally written, the per-segment loop referenced two local
variables -- `frames` (frame count for the zoompan `d=` parameter) and
`zoom_in` (alternates zoom direction) -- that were removed by a prior
refactor (commit 4048975, "improve text overlay parity...") but never
replaced. Every call that reached the loop body raised
`NameError: name 'frames' is not defined` before constructing any ffmpeg
command. Since generate_motion_video_from_images is a live call in both
pipeline.py and shot_matching_stage.py, any real image-source project would
have hit this crash. Fixed here by restoring the two missing lines
(`zoom_in = (idx % 2 == 0)`; `frames = int(math.ceil(dur * FPS))`), matching
what the diff shows was deleted. This is exactly the kind of bug this test
file exists to catch, so it's asserted directly below rather than only
inferred from a passing happy-path test.

All ffmpeg/ffprobe subprocess calls are mocked -- no real encoding runs.
Images are tiny synthetic PNGs written to tmp_path via Pillow.
"""
import math
import re
import subprocess
from pathlib import Path

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image

from scripts.image_motion_engine import ImageMotionEngine
import scripts.image_motion_engine as ime_mod

# Captured before the autouse fixture swaps subprocess.run, for the real-ffmpeg test.
_REAL_RUN = subprocess.run


def _make_image(path, size=(200, 300), color=(120, 60, 30)):
    Image.new("RGB", size, color).save(path)
    return path


class _FakeCompletedProcess:
    returncode = 0


def _make_fake_run(created_bytes=b"fake-mp4-bytes"):
    """Stands in for subprocess.run: records every invoked command and
    writes a placeholder file at the expected output path so downstream
    Path.exists()/concat logic in the real function keeps working without
    ever invoking a real ffmpeg binary."""
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        # The output path is always the last positional arg in this module's
        # ffmpeg/concat commands.
        out_path = cmd[-1]
        from pathlib import Path
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(created_bytes)
        return _FakeCompletedProcess()

    fake_run.calls = calls
    return fake_run


@pytest.fixture(autouse=True)
def _no_real_ffmpeg(monkeypatch):
    """Safety net: even if a test forgets to patch subprocess.run itself,
    never let a real ffmpeg process launch during this test module."""
    monkeypatch.setattr(subprocess, "run", _make_fake_run())


def _filter_complex_of(cmd):
    idx = cmd.index("-filter_complex")
    return cmd[idx + 1]


def _extract_zoompan_d(filter_str):
    m = re.search(r"zoompan=z='[^']*':d=(\d+)", filter_str)
    assert m, f"no zoompan d= found in filter string: {filter_str}"
    return int(m.group(1))


def _extract_zoom_bounds(filter_str):
    """Pull the two literal zoom bounds out of a zoompan z= expression like
    min(1.0+0.001250*on,1.15) or max(1.15-0.001250*on,1.00)."""
    m = re.search(r"z='(?:min|max)\(([\d.]+)[+-][\d.]+\*on,([\d.]+)\)'", filter_str)
    assert m, f"could not parse zoom expression from: {filter_str}"
    return float(m.group(1)), float(m.group(2))


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_raises_value_error_for_empty_image_list(tmp_path):
    with pytest.raises(ValueError):
        ImageMotionEngine.generate_motion_video_from_images(
            image_paths=[],
            cues=[],
            total_duration=5.0,
            output_video_path=str(tmp_path / "out.mp4"),
        )


def test_raises_file_not_found_when_no_image_paths_exist(tmp_path):
    bogus = tmp_path / "does_not_exist.png"
    with pytest.raises(FileNotFoundError):
        ImageMotionEngine.generate_motion_video_from_images(
            image_paths=[str(bogus)],
            cues=[],
            total_duration=5.0,
            output_video_path=str(tmp_path / "out.mp4"),
        )


def test_skips_missing_images_but_uses_valid_ones(tmp_path, monkeypatch):
    """A mix of a real and a missing path should not raise -- only the
    valid ones are kept and cycled through."""
    fake_run = _make_fake_run()
    monkeypatch.setattr(subprocess, "run", fake_run)

    good = _make_image(tmp_path / "good.png")
    missing = tmp_path / "missing.png"
    out_path = tmp_path / "out.mp4"

    result = ImageMotionEngine.generate_motion_video_from_images(
        image_paths=[str(missing), str(good)],
        cues=[],
        total_duration=4.0,
        output_video_path=str(out_path),
    )
    assert result == str(out_path.resolve())
    assert out_path.exists()
    # At least one per-segment ffmpeg call plus the final concat call.
    assert len(fake_run.calls) >= 2


def test_ensure_motion_video_reuses_unchanged_visual_artifact(tmp_path, monkeypatch):
    image = _make_image(tmp_path / "product.png")
    output = tmp_path / "motion.mp4"
    calls = []

    def generate(cls, **kwargs):
        calls.append(kwargs)
        Path(kwargs["output_video_path"]).write_bytes(b"motion")
        return str(Path(kwargs["output_video_path"]).resolve())

    monkeypatch.setattr(ImageMotionEngine, "generate_motion_video_from_images", classmethod(generate))
    cues = [{"start": 0.0, "end": 2.0, "text": "first"}]

    first = ImageMotionEngine.ensure_motion_video_from_images([str(image)], cues, 2.0, str(output))
    second = ImageMotionEngine.ensure_motion_video_from_images([str(image)], cues, 2.0, str(output))

    assert first == second == str(output.resolve())
    assert len(calls) == 1


def test_ensure_motion_video_invalidates_when_cue_timing_changes(tmp_path, monkeypatch):
    image = _make_image(tmp_path / "product.png")
    output = tmp_path / "motion.mp4"
    calls = []

    def generate(cls, **kwargs):
        calls.append(kwargs)
        Path(kwargs["output_video_path"]).write_bytes(b"motion")
        return str(Path(kwargs["output_video_path"]).resolve())

    monkeypatch.setattr(ImageMotionEngine, "generate_motion_video_from_images", classmethod(generate))

    ImageMotionEngine.ensure_motion_video_from_images([str(image)], [{"start": 0.0, "end": 2.0}], 2.0, str(output))
    ImageMotionEngine.ensure_motion_video_from_images([str(image)], [{"start": 0.0, "end": 2.5}], 2.5, str(output))

    assert len(calls) == 2


# ---------------------------------------------------------------------------
# Regression test for the NameError bug (frames / zoom_in undefined)
# ---------------------------------------------------------------------------

def test_generate_motion_video_does_not_raise_nameerror(tmp_path, monkeypatch):
    """Direct regression test for the bug described in this file's module
    docstring: the per-segment loop must not reference undefined `frames`/
    `zoom_in` locals. Before the fix, this call raised NameError on the
    first image every single time -- i.e. the function was completely
    broken for any real caller (pipeline.py, shot_matching_stage.py)."""
    fake_run = _make_fake_run()
    monkeypatch.setattr(subprocess, "run", fake_run)

    img = _make_image(tmp_path / "product.png")
    out_path = tmp_path / "out.mp4"

    # Must not raise NameError (or anything else) for a plain single-image,
    # no-cues call -- the simplest possible real usage.
    result = ImageMotionEngine.generate_motion_video_from_images(
        image_paths=[str(img)],
        cues=[],
        total_duration=4.0,
        output_video_path=str(out_path),
    )
    assert result == str(out_path.resolve())
    assert len(fake_run.calls) >= 1


# ---------------------------------------------------------------------------
# zoompan filter numeric sanity: frame counts and zoom bounds
# ---------------------------------------------------------------------------

def test_zoompan_frame_count_is_positive_integer_matching_duration_and_fps(tmp_path, monkeypatch):
    fake_run = _make_fake_run()
    monkeypatch.setattr(subprocess, "run", fake_run)

    img = _make_image(tmp_path / "product.png")
    out_path = tmp_path / "out.mp4"
    total_duration = 6.0

    ImageMotionEngine.generate_motion_video_from_images(
        image_paths=[str(img)],
        cues=[],
        total_duration=total_duration,
        output_video_path=str(out_path),
    )

    # First recorded call is the per-segment ffmpeg encode (concat is last).
    segment_cmd = fake_run.calls[0]
    filter_str = _filter_complex_of(segment_cmd)
    d_frames = _extract_zoompan_d(filter_str)

    assert d_frames > 0
    assert isinstance(d_frames, int)
    # segment duration for a single image, no cues: max(2.0, total_duration/1)
    expected_dur = max(2.0, total_duration / 1)
    expected_frames = int(math.ceil(expected_dur * ime_mod.FPS))
    assert d_frames == expected_frames


def test_zoompan_frame_count_never_zero_for_degenerate_cue_duration(tmp_path, monkeypatch):
    """A cue with end <= start (bad upstream data -- e.g. a matching bug
    that emits a zero-width or inverted shot) must not produce a zero or
    negative frame count for zoompan's d= parameter, which ffmpeg would
    either reject or render as a single frozen/black frame. The
    max(1.5, ...) clamp in the source is what prevents this -- this test
    guards that clamp stays in place."""
    fake_run = _make_fake_run()
    monkeypatch.setattr(subprocess, "run", fake_run)

    img = _make_image(tmp_path / "product.png")
    out_path = tmp_path / "out.mp4"

    bad_cues = [{"start": 5.0, "end": 2.0}]  # end before start
    ImageMotionEngine.generate_motion_video_from_images(
        image_paths=[str(img)],
        cues=bad_cues,
        total_duration=10.0,
        output_video_path=str(out_path),
    )

    segment_cmd = fake_run.calls[0]
    filter_str = _filter_complex_of(segment_cmd)
    d_frames = _extract_zoompan_d(filter_str)
    assert d_frames > 0
    # dur is clamped to at least 1.5s regardless of the bad cue window.
    assert d_frames == int(math.ceil(1.5 * ime_mod.FPS))


def test_zoom_bounds_stay_within_configured_range_across_segments(tmp_path, monkeypatch):
    """Across multiple images/segments (alternating zoom-in/zoom-out), the
    literal zoom bounds embedded in the filter string must always be the
    same finite min/max -- 1.00 and 1.15 -- regardless of which direction
    a given segment alternates to. A value outside this range reaching
    ffmpeg unclamped would over- or under-zoom the source image, and an
    extreme value could crop past the image's real content."""
    fake_run = _make_fake_run()
    monkeypatch.setattr(subprocess, "run", fake_run)

    imgs = [_make_image(tmp_path / f"p{i}.png") for i in range(4)]
    out_path = tmp_path / "out.mp4"
    cues = [{"start": float(i), "end": float(i) + 2.0} for i in range(4)]

    ImageMotionEngine.generate_motion_video_from_images(
        image_paths=[str(p) for p in imgs],
        cues=cues,
        total_duration=8.0,
        output_video_path=str(out_path),
    )

    segment_cmds = fake_run.calls[:-1]  # last call is the concat
    assert len(segment_cmds) == 4
    for cmd in segment_cmds:
        filter_str = _filter_complex_of(cmd)
        lo, hi = _extract_zoom_bounds(filter_str)
        bounds = sorted([lo, hi])
        assert bounds == pytest.approx([1.00, 1.15])
        assert all(math.isfinite(b) for b in bounds)


def test_output_frame_size_matches_configured_video_dimensions(tmp_path, monkeypatch):
    """The background/foreground scale targets in the filter string must
    match the configured 1080x1920 vertical frame -- an image smaller than
    this, or an extreme aspect-ratio mismatch, is handled by ffmpeg's own
    scale+crop/boxblur composition rather than by this module doing any
    dimension math itself, so this test pins down that the module always
    asks for the same fixed canvas regardless of source image shape."""
    fake_run = _make_fake_run()
    monkeypatch.setattr(subprocess, "run", fake_run)

    # A tiny image, smaller than the output frame in both dimensions, and
    # an extreme aspect ratio (very wide, very short).
    tiny_img = _make_image(tmp_path / "tiny.png", size=(40, 20))
    out_path = tmp_path / "out.mp4"

    ImageMotionEngine.generate_motion_video_from_images(
        image_paths=[str(tiny_img)],
        cues=[],
        total_duration=3.0,
        output_video_path=str(out_path),
    )

    filter_str = _filter_complex_of(fake_run.calls[0])
    assert "scale=1080:1920" in filter_str
    # Foreground is pre-upscaled (lanczos) and zoompan renders it at the 960x1280 box.
    assert "flags=lanczos" in filter_str
    assert "s=960x1280" in filter_str
    assert f"fps={ime_mod.FPS}" in filter_str


def test_segment_duration_clamped_when_no_cues_and_zero_total_duration(tmp_path, monkeypatch):
    """total_duration=0 with no cues must not collapse the per-image
    segment duration to zero (which would mean a 0-frame zoompan) -- the
    max(2.0, ...) clamp guards this."""
    fake_run = _make_fake_run()
    monkeypatch.setattr(subprocess, "run", fake_run)

    img = _make_image(tmp_path / "product.png")
    out_path = tmp_path / "out.mp4"

    ImageMotionEngine.generate_motion_video_from_images(
        image_paths=[str(img)],
        cues=[],
        total_duration=0.0,
        output_video_path=str(out_path),
    )

    seg_cmd = fake_run.calls[0]
    # The segment length is capped by the output `-frames:v` (input is a single still).
    frames_idx = seg_cmd.index("-frames:v")
    assert int(seg_cmd[frames_idx + 1]) >= int(math.ceil(2.0 * ime_mod.FPS))


def test_progress_callback_invoked_per_segment(tmp_path, monkeypatch):
    fake_run = _make_fake_run()
    monkeypatch.setattr(subprocess, "run", fake_run)

    img1 = _make_image(tmp_path / "p1.png")
    img2 = _make_image(tmp_path / "p2.png")
    out_path = tmp_path / "out.mp4"

    progress_events = []

    def on_progress(curr, total, msg):
        progress_events.append((curr, total, msg))

    cues = [
        {"start": 0.0, "end": 2.0},
        {"start": 2.0, "end": 4.5},
        {"start": 4.5, "end": 7.0},
    ]

    ImageMotionEngine.generate_motion_video_from_images(
        image_paths=[str(img1), str(img2)],
        cues=cues,
        total_duration=7.0,
        output_video_path=str(out_path),
        progress_callback=on_progress,
    )

    assert len(progress_events) == 3
    assert progress_events[0] == (1, 3, "ช็อตที่ 1/3")
    assert progress_events[1] == (2, 3, "ช็อตที่ 2/3")
    assert progress_events[2] == (3, 3, "ช็อตที่ 3/3")


# ---------------------------------------------------------------------------
# B1 (EDITOR-CUT-QUALITY-R1): a still must become exactly ceil(dur * FPS) frames
# ---------------------------------------------------------------------------

def test_segment_command_uses_single_input_frame_and_exact_frame_cap(tmp_path, monkeypatch):
    """`-loop 1 -t dur` + zoompan d=frames made ~dur*FPS*frames output frames (about
    100 s for a 2 s cue) because zoompan emits `d` frames per input frame. The input
    must be one still, and the output frame count must be capped explicitly."""
    fake_run = _make_fake_run()
    monkeypatch.setattr(subprocess, "run", fake_run)

    img = _make_image(tmp_path / "product.png")
    ImageMotionEngine.generate_motion_video_from_images(
        image_paths=[str(img)],
        cues=[{"start": 0.0, "end": 2.5}],
        total_duration=2.5,
        output_video_path=str(tmp_path / "out.mp4"),
    )

    cmd = fake_run.calls[0]
    expected_frames = int(math.ceil(2.5 * ime_mod.FPS))
    assert "-loop" not in cmd
    assert "-t" not in cmd
    assert cmd.index("-frames:v") > cmd.index("-i")  # output option, not an input option
    assert int(cmd[cmd.index("-frames:v") + 1]) == expected_frames
    assert _extract_zoompan_d(_filter_complex_of(cmd)) == expected_frames


def test_segment_files_are_keyed_so_stale_segments_are_not_resumed(tmp_path, monkeypatch):
    fake_run = _make_fake_run(created_bytes=b"x" * 20000)  # > resume size threshold
    monkeypatch.setattr(subprocess, "run", fake_run)

    img = _make_image(tmp_path / "product.png")
    work = tmp_path / "work"
    work.mkdir()
    # A legacy (schema 1) segment from the buggy engine: big enough to look reusable.
    (work / "seg_000.mp4").write_bytes(b"y" * 20000)

    def run(end):
        fake_run.calls.clear()
        ImageMotionEngine.generate_motion_video_from_images(
            image_paths=[str(img)],
            cues=[{"start": 0.0, "end": end}],
            total_duration=end,
            output_video_path=str(tmp_path / "out.mp4"),
            project_dir=work,
        )
        return [c for c in fake_run.calls if "-filter_complex" in c]

    assert len(run(2.0)) == 1, "legacy seg_000.mp4 must not be reused"
    assert len(run(2.0)) == 0, "identical segment is resumed"
    assert len(run(3.0)) == 1, "a different length must re-render"


def _real_ffmpeg_or_skip():
    import shutil
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg/ffprobe not installed")


def _probe_video(path):
    out = _REAL_RUN(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames,width,height", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    import json
    stream = json.loads(out)["streams"][0]
    return int(stream["nb_read_frames"]), int(stream["width"]), int(stream["height"])


def test_real_ffmpeg_segments_have_exactly_ceil_dur_times_fps_frames(tmp_path, monkeypatch):
    """Real ffmpeg on tiny synthetic stills (portrait + landscape): every segment, and
    the concatenated output, must carry exactly ceil(dur * FPS) frames at 1080x1920."""
    _real_ffmpeg_or_skip()
    monkeypatch.setattr(subprocess, "run", _REAL_RUN)

    portrait = _make_image(tmp_path / "portrait.png", size=(120, 160))
    landscape = _make_image(tmp_path / "landscape.png", size=(160, 90), color=(20, 90, 160))
    work = tmp_path / "work"
    out = tmp_path / "out.mp4"
    cues = [
        {"start": 0.0, "end": 2.0},   # clamp-free, 60 frames
        {"start": 2.0, "end": 3.5},   # 1.5 s, 45 frames (zoom-out segment)
        {"start": 3.5, "end": 6.0},   # 2.5 s, 75 frames
    ]
    durs = [2.0, 1.5, 2.5]

    ImageMotionEngine.generate_motion_video_from_images(
        image_paths=[str(portrait), str(landscape)],
        cues=cues,
        total_duration=6.0,
        output_video_path=str(out),
        project_dir=work,
    )

    segments = sorted(work.glob("motion_seg_*.mp4"))
    assert len(segments) == 3
    for seg, dur in zip(segments, durs):
        frames, width, height = _probe_video(seg)
        assert frames == int(math.ceil(dur * ime_mod.FPS)), seg.name
        assert (width, height) == (1080, 1920)

    total_frames, width, height = _probe_video(out)
    assert total_frames == sum(int(math.ceil(d * ime_mod.FPS)) for d in durs)
    assert (width, height) == (1080, 1920)
