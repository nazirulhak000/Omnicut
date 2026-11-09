"""Audit S3-03: a clip whose source runs out early is padded to its planned
frame count (last frame held), so every later cut stays on the voice; a clip
starting past the end of its file is rejected before ffmpeg runs."""

import pytest

from scripts.error_handler import AppError
from scripts.video_editor import VideoEditor
from tests.test_real_render_cut_alignment import (
    _decoded_indices,
    _write_empty_ass,
    _write_index_coded_source,
    _write_voice,
    pytestmark,  # noqa: F401  (ffmpeg skip + render_regression marker)
)


def test_short_source_holds_last_frame_for_planned_frames(tmp_path):
    short = tmp_path / "short.mp4"   # 1.0 s: frames 0..29
    long = tmp_path / "long.mp4"
    _write_index_coded_source(short, n_frames=30)
    _write_index_coded_source(long, n_frames=512)
    voice, ass, out = tmp_path / "voice.wav", tmp_path / "subs.ass", tmp_path / "out.mp4"
    _write_voice(voice, [0.0, 2.0], 3.0)
    _write_empty_ass(ass)
    clips = [
        # Planned 2.0 s from 0.5 s, but only 0.5 s of picture exists.
        {"id": "a", "source_path": str(short), "trim_start": 0.5, "trim_end": 2.5, "duration": 2.0,
         "speed": 1.0, "zoom": 1.0, "transition_in": "cut"},
        {"id": "b", "source_path": str(long), "trim_start": 10.0, "trim_end": 11.0, "duration": 1.0,
         "speed": 1.0, "zoom": 1.0, "transition_in": "cut"},
    ]
    VideoEditor.assemble_tiktok_video(
        raw_video_paths=[str(short)], total_duration=3.0, mixed_audio_path=str(voice),
        ass_subtitle_path=str(ass), output_mp4_path=str(out), clip_list=clips,
        transitions=["cut"], export_preset="draft",
    )
    indices = _decoded_indices(out)
    assert len(indices) == 90
    # The draft encode is lossy, so a flat-colour index can decode one level
    # off now and then; the boundary itself is unambiguous (<30 vs >=290).
    assert all(i < 100 for i in indices[:60]), "clip A fills all 60 planned frames"
    assert all(i >= 290 for i in indices[60:]), "clip B starts on its planned frame 60"
    assert sum(a == b for a, b in zip(indices[:15], range(15, 30))) >= 12
    assert sum(i == 29 for i in indices[15:60]) >= 40, "missing footage is a held last frame"


def test_trim_start_past_source_end_is_rejected_in_thai(tmp_path):
    short = tmp_path / "short.mp4"
    _write_index_coded_source(short, n_frames=30)
    voice, ass = tmp_path / "voice.wav", tmp_path / "subs.ass"
    _write_voice(voice, [0.0], 2.0)
    _write_empty_ass(ass)
    clips = [{"id": "a", "source_path": str(short), "trim_start": 5.0, "trim_end": 7.0, "duration": 2.0,
              "speed": 1.0, "transition_in": "cut"}]
    with pytest.raises(AppError) as exc_info:
        VideoEditor.assemble_tiktok_video(
            raw_video_paths=[str(short)], total_duration=2.0, mixed_audio_path=str(voice),
            ass_subtitle_path=str(ass), output_mp4_path=str(tmp_path / "out.mp4"), clip_list=clips,
            transitions=[], export_preset="draft",
        )
    assert exc_info.value.code == "CLIP_TRIM_BEYOND_SOURCE"
    assert not (tmp_path / "out.mp4").exists()
