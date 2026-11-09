# -*- coding: utf-8 -*-
"""Audit S3-11: post-render black / frozen frame scan + still-window skip."""
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import media_validation as mv
from scripts.stages.shot_matching_stage import ShotMatchingStage, STILL_MOTION_THRESHOLD

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg required")


def _make_clip(path: Path, *, black=False, frozen=False) -> Path:
    """2s moving + (1s black | 2s frozen) + 1s moving, 270x480 lavfi clip."""
    moving = "testsrc2=s=270x480:r=30:d={d}"
    inputs = ["-f", "lavfi", "-i", moving.format(d=2)]
    if black:
        inputs += ["-f", "lavfi", "-i", "color=c=black:s=270x480:r=30:d=1"]
    if frozen:
        inputs += ["-f", "lavfi", "-i", "testsrc2=s=270x480:r=30:d=1"]
    inputs += ["-f", "lavfi", "-i", moving.format(d=1)]
    n = 1 + int(black) + int(frozen) + 1
    if frozen:
        fx = f"[{1 + int(black)}:v]trim=0:0.1,loop=loop=60:size=1:start=0,trim=duration=2,setpts=PTS-STARTPTS[fr];"
        labels = "".join(
            f"[{i}:v]" if not (frozen and i == 1 + int(black)) else "[fr]" for i in range(n)
        )
    else:
        fx = ""
        labels = "".join(f"[{i}:v]" for i in range(n))
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-v", "error", *inputs,
           "-filter_complex", f"{fx}{labels}concat=n={n}:v=1:a=0", "-pix_fmt", "yuv420p",
           "-c:v", "libx264", "-preset", "ultrafast", str(path)]
    subprocess.run(cmd, check=True, timeout=120)
    return path


def test_parse_output_closes_open_freeze_at_duration():
    log = (
        "[blackdetect @ 1] black_start:2 black_end:3 black_duration:1\n"
        "[freezedetect @ 2] lavfi.freezedetect.freeze_start: 3\n"
    )
    out = mv.parse_qa_scan_output(log, duration=5.0)
    assert out["black"] == [(2.0, 3.0)]
    assert out["frozen"] == [(3.0, 5.0)]
    closed = mv.parse_qa_scan_output(
        "lavfi.freezedetect.freeze_start: 1\nlavfi.freezedetect.freeze_end: 2.5\n", duration=9.0
    )
    assert closed["frozen"] == [(1.0, 2.5)]


def test_black_segment_is_flagged_in_thai(tmp_path):
    clip = _make_clip(tmp_path / "black.mp4", black=True)
    warnings = mv.qa_scan_render(clip)
    assert any("เฟรมดำ" in w and "2.0-3.0" in w for w in warnings), warnings


def test_frozen_segment_is_flagged_unless_it_is_a_declared_hold(tmp_path):
    clip = _make_clip(tmp_path / "frozen.mp4", frozen=True)
    warnings = mv.qa_scan_render(clip)
    assert any("ภาพค้างนิ่ง" in w for w in warnings), warnings
    # The same span declared as a hold_reason clip (2.0-4.0s) is excused.
    assert not [w for w in mv.qa_scan_render(clip, hold_ranges=[(2.0, 4.0)]) if "ภาพค้างนิ่ง" in w]


def test_clean_clip_has_no_warnings(tmp_path):
    clip = _make_clip(tmp_path / "clean.mp4")
    assert mv.qa_scan_render(clip) == []


def test_scan_never_raises_on_missing_file_or_timeout(tmp_path):
    assert any("ไม่พบไฟล์" in w for w in mv.qa_scan_render(tmp_path / "nope.mp4"))
    clip = _make_clip(tmp_path / "t.mp4")
    scan = mv.scan_black_and_frozen(clip, timeout=0.001)
    assert scan["error"] and scan["black"] == [] and scan["frozen"] == []


def test_black_span_not_double_reported_as_freeze():
    scan = {"black": [(1.0, 4.0)], "frozen": [(1.0, 4.0)], "error": None}
    warnings = mv.build_qa_warnings(scan)
    assert len(warnings) == 1 and "เฟรมดำ" in warnings[0]


def test_short_spans_are_ignored():
    scan = {"black": [(1.0, 1.2)], "frozen": [(2.0, 3.2)], "error": None}
    assert mv.build_qa_warnings(scan) == []


def test_hold_ranges_from_clips_and_registry():
    from scripts.video_editor import VideoEditor, hold_ranges_from_clips

    clips = [{"id": "a"}, {"id": "b", "hold_reason": "source_window_exhausted"}, {"id": "c", "held_source_time": 1.0}]
    assert hold_ranges_from_clips(clips, [0.0, 2.0, 5.0], [2.0, 3.0, 1.0]) == [(2.0, 5.0), (5.0, 6.0)]
    assert hold_ranges_from_clips(clips, None, None) == []
    out = Path("x_qa.mp4")
    VideoEditor._store_qa_warnings(out, ["w"])
    assert VideoEditor.pop_qa_warnings(out) == ["w"]
    assert VideoEditor.pop_qa_warnings(out) == []


def test_api_render_collects_warnings_from_result(tmp_path):
    from scripts.api_render import collect_qa_warnings
    from scripts.video_editor import VideoEditor

    out = tmp_path / "f.mp4"
    VideoEditor._store_qa_warnings(out, ["เฟรมดำ"])
    assert collect_qa_warnings({"mp4_video": str(out)}) == ["เฟรมดำ"]
    assert collect_qa_warnings({}) == []


def test_fallback_offset_skips_still_windows():
    times = [round(i * 0.5, 2) for i in range(40)]
    # A lone spike at t=10 has the single highest score (the old pick) but the
    # 3s window starting there is mostly still; a sustained moving stretch at
    # 5.0-8.5 must win instead.
    scores = [0.2 if 5.0 <= t < 8.5 else 0.01 for t in times]
    scores[times.index(10.0)] = 0.5
    offset = ShotMatchingStage._compute_smart_fallback_offset(
        g_idx=1, total_groups=2, raw_duration=20.0, c_dur=3.0,
        motion_times=times, motion_scores=scores, previous_offsets=[],
    )
    assert offset != 10.0
    window = [s for t, s in zip(times, scores) if offset <= t < offset + 3.0]
    assert sum(window) / len(window) >= STILL_MOTION_THRESHOLD


def test_fallback_offset_keeps_old_pick_when_everything_is_still():
    times = [round(i * 0.5, 2) for i in range(40)]
    scores = [0.01] * 40
    scores[times.index(10.0)] = 0.05
    offset = ShotMatchingStage._compute_smart_fallback_offset(
        g_idx=1, total_groups=2, raw_duration=20.0, c_dur=3.0,
        motion_times=times, motion_scores=scores, previous_offsets=[],
    )
    assert offset == 10.0
