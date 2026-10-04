"""Round BG-SUBJECT-ISOLATION-3 renderer integration contract tests.

These tests capture the real FFmpeg argv assembled by ``VideoEditor``.  They
do not invoke rembg or encode media, but they do create valid RGBA PNG frames
so the renderer's fail-closed cache validation is exercised end to end.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

import scripts.video_editor as video_editor
from scripts.background_isolation_sequence_artifacts import (
    build_sequence_artifact_id,
    build_sequence_manifest,
)


def _stub_editor(monkeypatch, *, duration=4.0):
    calls = []

    monkeypatch.setattr(
        video_editor.VideoEditor,
        "get_media_info",
        classmethod(
            lambda cls, path: {
                "duration": duration,
                "width": 64,
                "height": 64,
                "rotation": 0,
                "fps": 30.0,
                "has_audio": False,
            }
        ),
    )

    def fake_run(command, *args, **kwargs):
        if command and str(command[0]).lower().endswith("ffmpeg"):
            calls.append(list(command))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(video_editor.subprocess, "run", fake_run)
    monkeypatch.setattr(
        video_editor.VideoEditor,
        "generate_poster_thumbnail",
        classmethod(lambda cls, video_path, poster_path=None: None),
    )
    return calls


def _make_sequence(
    monkeypatch,
    tmp_path,
    *,
    frame_count=8,
    fps=2,
    width=64,
    height=64,
    rotation=90,
    source_start=0.0,
    source_duration=None,
):
    projects_dir = tmp_path / "03_Projects"
    monkeypatch.setattr(video_editor, "PROJECTS_DIR", projects_dir)

    artifact_id = build_sequence_artifact_id(
        "source-fingerprint-1",
        fps=fps,
        timebase=f"1/{fps}",
        width=width,
        height=height,
        rotation=rotation,
    )
    manifest = build_sequence_manifest(
        artifact_id,
        source_fingerprint="source-fingerprint-1",
        algorithm="background-isolation-v1",
        engine="rembg",
        model="u2netp",
        quality="balanced",
        worker_version="sequence-rembg-worker-v1",
        frame_count=frame_count,
        fps=fps,
        timebase=f"1/{fps}",
        width=width,
        height=height,
        rotation=rotation,
        source_start=source_start,
        source_duration=source_duration,
        status="ready",
    )
    sequence_dir = projects_dir / ".cache" / "background-isolation-foreground-sequences" / artifact_id
    frames_dir = sequence_dir / "frames"
    frames_dir.mkdir(parents=True)
    for index in range(frame_count):
        image = Image.new("RGBA", (width, height), (20 + index, 30, 40, 255))
        image.save(frames_dir / f"frame_{index:06d}.png")
    (sequence_dir / "manifest.json").write_text(
        __import__("json").dumps(manifest),
        encoding="utf-8",
    )
    config = {
        "enabled": True,
        "mode": "cutout",
        "engine": "rembg",
        "model": "u2netp",
        "quality": "balanced",
        "fallback": "spotlight",
        "artifact": {
            "sequence_id": artifact_id,
            "status": "ready",
            "source_fingerprint": "source-fingerprint-1",
        },
        "sequence": manifest,
    }
    return config, artifact_id, sequence_dir


def _assemble(monkeypatch, tmp_path, *, clip_list, background_isolation=None, transitions=None):
    calls = _stub_editor(monkeypatch)
    source_bytes = b"source-must-not-be-mutated"
    sources = []
    for index, clip in enumerate(clip_list):
        source = Path(clip["source_path"])
        source.write_bytes(source_bytes + bytes([index]))
        sources.append(source)
    audio = tmp_path / "mix.wav"
    subtitles = tmp_path / "subs.ass"
    audio.write_bytes(b"audio")
    subtitles.write_text("[Script Info]\n", encoding="utf-8")

    video_editor.VideoEditor.assemble_tiktok_video(
        raw_video_paths=[],
        total_duration=4.0,
        mixed_audio_path=str(audio),
        ass_subtitle_path=str(subtitles),
        output_mp4_path=str(tmp_path / "out.mp4"),
        clip_list=clip_list,
        transitions=transitions,
        background_isolation=background_isolation,
    )
    assert calls
    return calls[-1], sources


def _filter(command):
    return command[command.index("-filter_complex") + 1]


def test_scoped_render_requires_artifact_for_active_id_only(monkeypatch, tmp_path):
    project = {"enabled": True, "scope_mode": "behind_text_windows",
               "active_clip_ids": ["active"],
               "active_intervals_by_clip": {"active": [{"start": 0, "end": 1}]}}
    with pytest.raises(ValueError, match="Cutout is not ready"):
        _assemble(monkeypatch, tmp_path,
                  clip_list=[{"id": "active", "source_path": str(tmp_path / "active.mp4"),
                              "trim_start": 0, "trim_end": 2}],
                  background_isolation=project)
    command, _ = _assemble(monkeypatch, tmp_path,
                           clip_list=[{"id": "inactive", "source_path": str(tmp_path / "inactive.mp4"),
                                       "trim_start": 0, "trim_end": 2}],
                           background_isolation={**project, "active_clip_ids": [],
                                                 "active_intervals_by_clip": {}})
    assert "alphamerge" not in _filter(command)


def test_scoped_render_rejects_clip_ids_lost_between_save_and_render(monkeypatch, tmp_path):
    project = {"enabled": True, "scope_mode": "behind_text_windows",
               "active_clip_ids": ["editor-a"],
               "active_intervals_by_clip": {"editor-a": [{"start": 0, "end": 1}]}}
    with pytest.raises(ValueError, match="no longer matches"):
        _assemble(monkeypatch, tmp_path,
                  clip_list=[{"source_path": str(tmp_path / "source.mp4"),
                              "trim_start": 0, "trim_end": 2}],
                  background_isolation=project)


def test_disabled_background_keeps_legacy_graph_and_source_untouched(monkeypatch, tmp_path):
    command, sources = _assemble(
        monkeypatch,
        tmp_path,
        clip_list=[{"source_path": str(tmp_path / "source.mp4"), "trim_start": 0.0, "trim_end": 2.0}],
        background_isolation=None,
    )

    graph = _filter(command)
    assert "alphamerge" not in graph
    assert "bg_subject" not in graph
    assert "background-isolation-foreground-sequences" not in command
    assert "-framerate" not in command
    assert sources[0].read_bytes() == b"source-must-not-be-mutated\x00"


@pytest.mark.parametrize(
    "override",
    [
        {"enabled": True, "artifact": {"status": "missing", "sequence_id": "bgseq1-0123456789abcdef"}},
        {"enabled": True, "artifact": {"status": "processing", "sequence_id": "bgseq1-0123456789abcdef"}},
        {"enabled": True, "artifact": {"status": "stale", "sequence_id": "bgseq1-0123456789abcdef"}},
        {"enabled": True, "artifact": {"status": "error", "sequence_id": "bgseq1-0123456789abcdef"}},
    ],
)
def test_requested_but_not_ready_background_blocks_render(monkeypatch, tmp_path, override):
    with pytest.raises(ValueError, match="Background Cutout is not ready"):
        _assemble(
            monkeypatch,
            tmp_path,
            clip_list=[{"source_path": str(tmp_path / "source.mp4"), "trim_start": 0.0, "trim_end": 2.0}],
            background_isolation=override,
        )


def test_arbitrary_foreground_path_is_rejected_even_with_ready_metadata(monkeypatch, tmp_path):
    config, _, _ = _make_sequence(monkeypatch, tmp_path)
    config["frames_path"] = str(tmp_path / "outside" / "frames")
    with pytest.raises(ValueError, match="Background Cutout is not ready"):
        _assemble(
            monkeypatch,
            tmp_path,
            clip_list=[{"source_path": str(tmp_path / "source.mp4"), "trim_start": 0.0, "trim_end": 2.0}],
            background_isolation=config,
        )


def test_ready_rgba_sequence_is_composited_per_clip_before_concat(monkeypatch, tmp_path):
    config, artifact_id, sequence_dir = _make_sequence(monkeypatch, tmp_path)
    command, sources = _assemble(
        monkeypatch,
        tmp_path,
        clip_list=[
            {
                "source_path": str(tmp_path / "source.mp4"),
                "trim_start": 1.0,
                "trim_end": 3.0,
                "rotation": 90,
                "mirror": True,
            }
        ],
        background_isolation=config,
    )

    graph = _filter(command)
    assert artifact_id in " ".join(command)
    assert str(sequence_dir / "frames" / "frame_%06d.png") in command
    assert command[command.index("-framerate") + 1] == "2/1"
    assert command[command.index("-start_number") + 1] == "2"
    assert "[2:v]" in graph
    assert graph.count("transpose=1") == 2
    assert "alphamerge" in graph
    assert "split=2[bg_subject_base_0][bg_subject_overlay_0]" in graph
    assert "drawbox=x=0:y=0:w=iw:h=ih:color=0x0B1220:t=fill" not in graph
    assert graph.index("clip_0_transformed") < graph.index("alphamerge") < graph.index("concat")
    assert graph.index("concat") < graph.index("_subject_hook.ass")
    assert graph.index("_subject_hook.ass") < graph.index("bg_subject_at_0")
    assert graph.index("bg_subject_at_0") < graph.rindex("subtitles=")
    assert sources[0].read_bytes() == b"source-must-not-be-mutated\x00"


def test_ready_cutout_with_worker_rounded_prompt_reaches_render_graph(monkeypatch, tmp_path):
    config, artifact_id, _ = _make_sequence(monkeypatch, tmp_path)
    config = {**config, "prompt_reference_source": "source.mp4", "prompt_reference_start": 0,
              "subject_points": [{"x": 0.34444, "y": 0.45237, "label": 1}]}
    project = {**config, "subject_points": [
        {"x": 0.3444365394719402, "y": 0.4523699183852115, "label": 1}]}
    command, _ = _assemble(monkeypatch, tmp_path, clip_list=[{
        "source_path": str(tmp_path / "source.mp4"), "trim_start": 0, "trim_end": 2,
        "background_isolation": config,
    }], background_isolation=project)
    assert artifact_id in " ".join(command)
    assert "alphamerge" in _filter(command)


def test_windowed_rgba_sequence_starts_from_artifact_local_frame_zero(monkeypatch, tmp_path):
    config, _, _ = _make_sequence(
        monkeypatch,
        tmp_path,
        frame_count=4,
        fps=2,
        source_start=8.0,
        source_duration=2.0,
    )
    command, _ = _assemble(
        monkeypatch,
        tmp_path,
        clip_list=[{
            "source_path": str(tmp_path / "source.mp4"),
            "trim_start": 8.0,
            "trim_end": 10.0,
        }],
        background_isolation=config,
    )

    assert command[command.index("-start_number") + 1] == "0"
    assert "alphamerge" in _filter(command)


def test_non_rgba_frame_fails_closed(monkeypatch, tmp_path):
    config, _, sequence_dir = _make_sequence(monkeypatch, tmp_path)
    Image.new("RGB", (64, 64), (255, 0, 0)).save(sequence_dir / "frames" / "frame_000003.png")
    with pytest.raises(ValueError, match="Background Cutout is not ready"):
        _assemble(
            monkeypatch,
            tmp_path,
            clip_list=[{"source_path": str(tmp_path / "source.mp4"), "trim_start": 0.0, "trim_end": 2.0}],
            background_isolation=config,
        )


def test_video_cutout_render_uses_alpha_decoder_and_artifact_local_seek(monkeypatch, tmp_path):
    import json

    project_root = tmp_path / "03_Projects"
    monkeypatch.setattr(video_editor, "PROJECTS_DIR", project_root)
    artifact_id = "bgseq1-0123456789abcdef"
    directory = project_root / ".cache" / "background-isolation-videos" / artifact_id
    directory.mkdir(parents=True)
    video = directory / "cutout.webm"
    video.write_bytes(b"nonempty-test-container")
    manifest = {
        "schema_version": 2, "artifact_id": artifact_id, "status": "ready",
        "video_file": "cutout.webm", "codec": "vp9-alpha",
        "source_fingerprint": "fixture", "source_start": 8.0,
        "source_duration": 4.0, "fps": "30/1", "frame_count": 120,
        "width": 64, "height": 64,
    }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    config = {"enabled": True, "artifact": {"id": artifact_id, "status": "ready",
                                            "source_fingerprint": "fixture"}}
    command, _ = _assemble(
        monkeypatch, tmp_path,
        clip_list=[{"source_path": str(tmp_path / "source.mp4"),
                    "trim_start": 9.0, "trim_end": 11.0}],
        background_isolation=config,
    )
    assert str(video) in command
    video_index = command.index(str(video))
    assert command[video_index - 5:video_index] == ["-c:v", "libvpx-vp9", "-ss", "1.0", "-i"]
    assert "frame_%06d.png" not in " ".join(command)
    assert "alphamerge" in _filter(command)
    assert "alphaextract[bg_fg_alpha_0]" in _filter(command)
    # The footage stays visible behind the hook text. Round
    # RESTORE-ORIGINAL-FOOTAGE-BG-FOR-CUTOUT-SANDWICH-20260925 removed this
    # fill from the PNG path and asserted it there, but the video path added
    # later reintroduced it -- the assertion never covered this branch, so the
    # background silently went solid again. Both paths are now guarded.
    assert "drawbox=x=0:y=0:w=iw:h=ih:color=0x0B1220:t=fill" not in _filter(command)
    assert "0x0B1220" not in _filter(command), "cutout must not flatten the background"


def test_blurred_background_conflict_blocks_cutout_render(monkeypatch, tmp_path):
    config, _, _ = _make_sequence(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="Background Cutout conflict"):
        _assemble(
            monkeypatch,
            tmp_path,
            clip_list=[{
                "source_path": str(tmp_path / "source.mp4"),
                "trim_start": 0.0,
                "trim_end": 2.0,
                "bg_blur": True,
            }],
            background_isolation=config,
        )


def test_each_ready_clip_gets_own_sequence_input_and_transition_stays_above_composite(monkeypatch, tmp_path):
    config, _, _ = _make_sequence(monkeypatch, tmp_path, frame_count=12)
    command, _ = _assemble(
        monkeypatch,
        tmp_path,
        clip_list=[
            {"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 2.0},
            {"source_path": str(tmp_path / "b.mp4"), "trim_start": 0.0, "trim_end": 2.0},
        ],
        transitions=[{"type": "fade", "duration": 0.4}],
        background_isolation=config,
    )
    graph = _filter(command)
    assert graph.count("alphamerge") == 2
    assert graph.count("[3:v]") > 0 and graph.count("[4:v]") > 0
    assert graph.rfind("alphamerge") < graph.index("xfade")
    assert graph.index("xfade") < graph.index("subtitles=")
    assert command.count("-framerate") == 2


def test_background_config_can_be_selected_per_clip(monkeypatch, tmp_path):
    config, _, _ = _make_sequence(monkeypatch, tmp_path, frame_count=12)
    command, _ = _assemble(
        monkeypatch,
        tmp_path,
        clip_list=[
            {
                "source_path": str(tmp_path / "a.mp4"),
                "trim_start": 0.0,
                "trim_end": 2.0,
                "background_isolation": config,
            },
            {"source_path": str(tmp_path / "b.mp4"), "trim_start": 0.0, "trim_end": 2.0},
        ],
    )
    graph = _filter(command)
    assert graph.count("alphamerge") == 1
    assert command.count("-framerate") == 1
    assert "concat=n=2" in graph


def test_project_disable_overrides_ready_per_clip_artifact(monkeypatch, tmp_path):
    config, _, _ = _make_sequence(monkeypatch, tmp_path, frame_count=12)
    command, _ = _assemble(
        monkeypatch,
        tmp_path,
        clip_list=[
            {
                "source_path": str(tmp_path / "source.mp4"),
                "trim_start": 0.0,
                "trim_end": 2.0,
                "background_isolation": config,
            }
        ],
        background_isolation={"enabled": False, "fallback": "original"},
    )

    graph = _filter(command)
    assert "alphamerge" not in graph
    assert "bg_subject" not in graph
    assert "background-isolation-foreground-sequences" not in command
    assert "-framerate" not in command


def test_subframe_tail_discretization_tolerance(monkeypatch, tmp_path):
    # A clip spanning 5.642s at 30 fps needs ceil(169.26) = 170 frames.
    # If the artifact contains 169 frames (the exact integral frames to the tail of the source),
    # the 1-frame difference is due to math.ceil() rounding of fractional sub-frames and should succeed.
    config, artifact_id, _ = _make_sequence(
        monkeypatch,
        tmp_path,
        frame_count=169,
        fps=30,
        source_start=0.0,
        source_duration=5.642,
    )
    command, _ = _assemble(
        monkeypatch,
        tmp_path,
        clip_list=[
            {
                "source_path": str(tmp_path / "source.mp4"),
                "trim_start": 0.0,
                "trim_end": 5.642,
                "background_isolation": config,
            }
        ],
        background_isolation={"enabled": True},
    )

    graph = _filter(command)
    assert artifact_id in " ".join(command)
    assert "alphamerge" in graph
