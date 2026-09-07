"""
Regression test for the sticker overlay's ffmpeg input index.

The index was computed as `len(cmd_inputs) // 2`, which assumes every input
spends exactly two slots in the argument list ("-i", path). A clip_list
render breaks that assumption: each trimmed clip spends six slots
("-ss", val, "-t", val, "-i", path), so the divide-by-two inflated the
index to 3N+1 instead of N+1 and the overlay referenced a stream ffmpeg
never received.

The test reads the assembled filter_complex rather than rendering, so it
needs no real footage and no ffmpeg run.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.video_editor import VideoEditor


class _FakeCompleted:
    """Stands in for subprocess.run's result on the non-progress path."""

    def __init__(self):
        self.returncode = 0
        self.stdout = ""
        self.stderr = ""


def _capture_ffmpeg_cmd(monkeypatch):
    """Run assemble_tiktok_video without ffmpeg, returning the argv it built."""
    captured = {}

    def fake_run(cmd, *args, **kwargs):
        # The media-probe calls (ffprobe) must still answer with a duration,
        # so only intercept the ffmpeg render itself.
        if cmd and "ffmpeg" in str(cmd[0]).lower():
            captured["cmd"] = list(cmd)
            out = kwargs.get("stdout")
            # Leave an output file behind so the caller's existence check passes.
            return _FakeCompleted()
        return _FakeCompleted()

    monkeypatch.setattr("scripts.video_editor.subprocess.run", fake_run)
    return captured


def _stub_media_info(monkeypatch, duration=10.0):
    monkeypatch.setattr(
        VideoEditor,
        "get_media_info",
        classmethod(lambda cls, path: {
            "duration": duration, "width": 1080, "height": 1920, "fps": 30.0,
        }),
    )


def _sticker_stream_index(filter_complex_arg: str) -> int:
    """Pull N out of the `[N:v]scale=...[sticker_scaled]` node."""
    import re

    match = re.search(r"\[(\d+):v\]scale=[^\[]*\[sticker_scaled\]", filter_complex_arg)
    assert match, f"no sticker scale node in filter graph:\n{filter_complex_arg}"
    return int(match.group(1))


def _count_real_inputs(cmd: list) -> int:
    return sum(1 for i, token in enumerate(cmd) if token == "-i")


@pytest.mark.parametrize("clip_count", [1, 2, 3, 5])
def test_sticker_index_points_at_the_sticker_input(tmp_path, monkeypatch, clip_count):
    """With trimmed clips, the sticker's index must be the last real input."""
    _stub_media_info(monkeypatch)
    captured = _capture_ffmpeg_cmd(monkeypatch)

    sources = []
    for i in range(clip_count):
        src = tmp_path / f"clip{i}.mp4"
        src.write_bytes(b"fake")
        sources.append(src)

    audio = tmp_path / "mixed.wav"
    audio.write_bytes(b"fake")
    subs = tmp_path / "subs.ass"
    subs.write_text("[Script Info]\n", encoding="utf-8")
    badge = tmp_path / "badge.png"
    badge.write_bytes(b"fake")
    out = tmp_path / "out.mp4"

    # Every clip carries a trim, which is what puts "-ss"/"-t" before "-i"
    # and made the old divide-by-two wrong.
    clip_list = [
        {"source_path": str(src), "trim_start": 1.0, "trim_end": 3.0}
        for src in sources
    ]

    try:
        VideoEditor.assemble_tiktok_video(
            raw_video_paths=[str(s) for s in sources],
            total_duration=float(2 * clip_count),
            mixed_audio_path=str(audio),
            ass_subtitle_path=str(subs),
            output_mp4_path=str(out),
            clip_list=clip_list,
            sticker_path=str(badge),
        )
    except Exception:
        # A stubbed ffmpeg leaves no output file, so the caller may object
        # after the command is built. The argv is what this test is about.
        pass

    cmd = captured.get("cmd")
    assert cmd, "ffmpeg was never invoked"

    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    st_idx = _sticker_stream_index(filter_arg)

    # Inputs are the N clips, then the mixed audio, then the sticker.
    assert st_idx == clip_count + 1, (
        f"{clip_count} trimmed clips: sticker index {st_idx}, expected {clip_count + 1}"
    )
    # And that index must actually exist among the inputs ffmpeg received.
    assert st_idx < _count_real_inputs(cmd), (
        f"sticker index {st_idx} exceeds the {_count_real_inputs(cmd)} inputs passed"
    )


def test_sticker_index_survives_untrimmed_clips(tmp_path, monkeypatch):
    """A clip with no trim spends two slots; the index must still be right."""
    _stub_media_info(monkeypatch)
    captured = _capture_ffmpeg_cmd(monkeypatch)

    src = tmp_path / "clip.mp4"
    src.write_bytes(b"fake")
    audio = tmp_path / "mixed.wav"
    audio.write_bytes(b"fake")
    subs = tmp_path / "subs.ass"
    subs.write_text("[Script Info]\n", encoding="utf-8")
    badge = tmp_path / "badge.png"
    badge.write_bytes(b"fake")
    out = tmp_path / "out.mp4"

    try:
        VideoEditor.assemble_tiktok_video(
            raw_video_paths=[str(src)],
            total_duration=5.0,
            mixed_audio_path=str(audio),
            ass_subtitle_path=str(subs),
            output_mp4_path=str(out),
            sticker_path=str(badge),
        )
    except Exception:
        pass

    cmd = captured.get("cmd")
    assert cmd, "ffmpeg was never invoked"

    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    st_idx = _sticker_stream_index(filter_arg)

    assert st_idx == 2, f"one clip + audio + sticker: expected index 2, got {st_idx}"
    assert st_idx < _count_real_inputs(cmd)
