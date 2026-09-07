"""
The filter graph must never consume a label it does not also define.

An audit suspected that a transition requested on a single-clip render
would leave [v_concat] dangling: the transition branch folds clips
left-to-right, so with one clip its loop never runs, while the code after
it sets current_v to [v_concat] regardless. Checking the assembled graph
showed the suspicion was wrong -- the single clip falls through to
`concat=n=1`, which defines the label. These tests pin that down so a
future change to the reduction branch cannot quietly break it.

They read the assembled filter graph rather than rendering, so they need
no real footage and no ffmpeg run.
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.video_editor import VideoEditor


class _FakeCompleted:
    def __init__(self):
        self.returncode = 0
        self.stdout = ""
        self.stderr = ""


def _build(tmp_path, monkeypatch, clip_count, transitions):
    """Assemble a render command without running ffmpeg; return its filtergraph."""
    monkeypatch.setattr(
        VideoEditor,
        "get_media_info",
        classmethod(lambda cls, path: {
            "duration": 10.0, "width": 1080, "height": 1920, "fps": 30.0,
        }),
    )
    # Skip the hardware-encoder probe, which shells out to ffmpeg.
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")

    captured = {}

    def fake_run(cmd, *args, **kwargs):
        if cmd and "ffmpeg" in str(cmd[0]).lower():
            captured["cmd"] = list(cmd)
        return _FakeCompleted()

    monkeypatch.setattr("scripts.video_editor.subprocess.run", fake_run)

    sources = []
    for i in range(clip_count):
        src = tmp_path / f"clip{i}.mp4"
        src.write_bytes(b"fake")
        sources.append(src)

    audio = tmp_path / "mixed.wav"
    audio.write_bytes(b"fake")
    subs = tmp_path / "subs.ass"
    subs.write_text("[Script Info]\n", encoding="utf-8")

    clip_list = [
        {"source_path": str(src), "trim_start": 0.0, "trim_end": 3.0}
        for src in sources
    ]

    try:
        VideoEditor.assemble_tiktok_video(
            raw_video_paths=[str(s) for s in sources],
            total_duration=float(3 * clip_count),
            mixed_audio_path=str(audio),
            ass_subtitle_path=str(subs),
            output_mp4_path=str(tmp_path / "out.mp4"),
            clip_list=clip_list,
            transitions=transitions,
        )
    except Exception:
        # A stubbed ffmpeg writes no output file, so the caller may object
        # after building the command. The argv is what these tests read.
        pass

    cmd = captured.get("cmd")
    assert cmd, "ffmpeg was never invoked"
    return cmd[cmd.index("-filter_complex") + 1]


def _dangling_labels(graph: str) -> set:
    """Labels the graph reads but never writes.

    A filtergraph writes a label as `...[name];` (or at the very end) and
    reads it as `[name]filter`. An input stream is `[N:v]`, which never
    needs defining.
    """
    written = set(re.findall(r"\[([A-Za-z_]\w*)\](?=\s*;|\s*$)", graph))
    read = set(re.findall(r"\[([A-Za-z_]\w*)\](?=[A-Za-z])", graph))
    return read - written


@pytest.mark.parametrize("clip_count", [1, 2, 3])
@pytest.mark.parametrize("transition", [
    None,
    [{"type": "cut", "duration": 0.4}],
    [{"type": "fade", "duration": 0.4}],
])
def test_no_filter_label_is_consumed_without_being_defined(
    tmp_path, monkeypatch, clip_count, transition
):
    """Every clip count crossed with every transition kind stays well-formed."""
    graph = _build(tmp_path, monkeypatch, clip_count, transition)
    dangling = _dangling_labels(graph)
    assert not dangling, f"labels read but never written: {dangling}\n{graph}"


def test_single_clip_with_a_fade_defines_v_concat(tmp_path, monkeypatch):
    """The case the audit flagged: one clip still defines the label it uses.

    The transition reduction is skipped (nothing to fade between) and the
    clip goes through `concat=n=1`, which writes [v_concat].
    """
    graph = _build(tmp_path, monkeypatch, 1, [{"type": "fade", "duration": 0.4}])
    assert "[v_concat]" in graph
    assert "concat=n=1" in graph
    assert "xfade" not in graph


def test_two_clips_with_a_fade_reach_xfade(tmp_path, monkeypatch):
    """A fade between two clips must still produce a real transition."""
    graph = _build(tmp_path, monkeypatch, 2, [{"type": "fade", "duration": 0.4}])
    assert "xfade" in graph
