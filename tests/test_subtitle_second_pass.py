"""Burning subtitles in a second pass (scripts/subtitle_second_pass.py).
Command construction and cache helpers first, then one real render through
VideoEditor on synthetic media under tmp_path. No project data."""
import pytest

from scripts import subtitle_second_pass as sp

SUBS = "subtitles='D\\:/proj/x/subtitles.ass':fontsdir='D\\:/assets/Fonts'"
VIDEO = "[0:v]trim=duration=2,setpts=PTS-STARTPTS[clip_0];[clip_0]null[v_gradient_3];"


def test_split_cuts_at_the_final_subtitles_filter():
    split = sp.split_graph(f"{VIDEO}[v_gradient_3]{SUBS}[v_final]")
    assert split.pre_graph == f"{VIDEO}[v_gradient_3]null[v_pre_subs]"
    assert split.burn_chain == f"[0:v]{SUBS}[v_final]"
    assert split.ass_path == "D\\:/proj/x/subtitles.ass"


def test_split_keeps_audio_chains_in_pass_one():
    audio = ";[1:a]adelay=500|500[a_at];[a_at][2:a]amix=inputs=2[a_out]"
    split = sp.split_graph(f"{VIDEO}[v_gradient_3]{SUBS}[v_final]{audio}")
    assert split.pre_graph.endswith(f"[v_gradient_3]null[v_pre_subs]{audio}")
    assert "amix" not in split.burn_chain


def test_split_moves_the_draft_downscale_into_pass_two():
    graph = f"{VIDEO}[v_gradient_3]{SUBS}[v_subbed];[v_subbed]scale=540:960:flags=bilinear[v_final]"
    split = sp.split_graph(graph)
    assert split.pre_graph == f"{VIDEO}[v_gradient_3]null[v_pre_subs]"
    assert split.burn_chain == f"[0:v]{SUBS},scale=540:960:flags=bilinear[v_final]"


def test_hook_layer_under_an_isolated_subject_stays_in_pass_one():
    hook = "[v_gradient_3]subtitles='D\\:/proj/x/hook.ass':fontsdir='D\\:/assets/Fonts'[v_hook_subbed];"
    subject = "[v_hook_subbed][bg_subject_at_0]overlay=x=0:y=0[v_subject_0];"
    split = sp.split_graph(f"{VIDEO}{hook}{subject}[v_subject_0]{SUBS}[v_final]")
    assert "hook.ass" in split.pre_graph
    assert "hook.ass" not in split.burn_chain
    assert split.ass_path.endswith("subtitles.ass")


@pytest.mark.parametrize("graph", [
    f"{VIDEO}[v_gradient_3]null[v_final]",
    f"{VIDEO}[v_gradient_3]{SUBS}[v_subbed];[v_subbed]hflip[v_final]",
    f"{VIDEO}[v_gradient_3]{SUBS}[v_final];[v_final]hflip[v_final]",
])
def test_split_refuses_graphs_it_does_not_understand(graph):
    with pytest.raises(sp.SecondPassUnavailable):
        sp.split_graph(graph)


def test_key_ignores_the_subtitle_file_but_follows_everything_under_it(tmp_path):
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"a" * 2048)
    lut = tmp_path / "look.cube"
    lut.write_text("LUT_3D_SIZE 2", encoding="utf-8")
    ass = tmp_path / "subtitles.ass"
    ass.write_text("first", encoding="utf-8")

    def key(graph_text):
        split = sp.split_graph(graph_text)
        return sp.intermediate_key(["-i", str(clip), "-filter_complex", split.pre_graph], [clip], [lut])

    graph = f"{VIDEO}[v_gradient_3]subtitles='{ass.as_posix()}'[v_final]"
    base = key(graph)

    ass.write_text("caption fixed", encoding="utf-8")
    assert key(graph) == base, "a caption edit must reuse the intermediate"
    other_ass = f"{VIDEO}[v_gradient_3]subtitles='{(tmp_path / 'subtitles_v2.ass').as_posix()}'[v_final]"
    assert key(other_ass) == base, "a re-roll writes subtitles_vN.ass; the name must not matter either"

    assert key(graph.replace("trim=duration=2", "trim=duration=3")) != base
    lut.write_text("LUT_3D_SIZE 4", encoding="utf-8")
    assert key(graph) != base, "a LUT rewritten in place under the same name changes the picture"
    lut.write_text("LUT_3D_SIZE 2", encoding="utf-8")
    assert key(graph) == base
    clip.write_bytes(b"b" * 4096)
    assert key(graph) != base


def test_find_reusable_needs_a_complete_file(tmp_path):
    key = "k" * 32
    assert sp.find_reusable(tmp_path, key) is None
    target = sp.intermediate_path(tmp_path, key)
    target.write_bytes(b"")
    assert sp.find_reusable(tmp_path, key) is None
    target.write_bytes(b"x" * 4096)
    assert sp.find_reusable(tmp_path, key) == target
    assert sp.find_reusable(tmp_path, "z" * 32) is None


def test_pass_two_copies_audio_and_reencodes_video(tmp_path):
    cmd = sp.build_pass2_cmd(["ffmpeg", "-y"], tmp_path / "pre.mp4", f"[0:v]{SUBS}[v_final]", True,
                             ["-c:v", "h264_nvenc"], "30", tmp_path / "out.mp4")
    assert cmd[cmd.index("-c:a") + 1] == "copy"
    assert cmd[cmd.index("-c:v") + 1] == "h264_nvenc"
    assert cmd[-1].endswith("out.mp4")
    silent = sp.build_pass2_cmd(["ffmpeg"], tmp_path / "pre.mp4", "[0:v]null[v_final]", False, [], "30", tmp_path / "o.mp4")
    assert "-c:a" not in silent


def test_prune_lists_everything_but_the_newest(tmp_path):
    import os
    names = []
    for i in range(3):
        path = sp.intermediate_path(tmp_path, f"{i}" * 32)
        path.write_bytes(b"x" * 2048)
        os.utime(path, (1_000_000 + i, 1_000_000 + i))
        names.append(path)
    assert sp.prune(tmp_path, keep=1) == names[:2]
    assert all(path.exists() for path in names), "prune only reports; it never deletes"


# ------------------------------------------------------- renderer helpers
def test_render_key_survives_an_identical_rewrite_of_the_mixed_audio(tmp_path):
    import os
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"v" * 4096)
    audio = tmp_path / "mixed_audio.wav"
    audio.write_bytes(b"a" * 4096)
    inputs = ["-ss", "0.000", "-t", "2.000", "-i", str(clip), "-i", str(audio)]

    def key():
        return sp.render_key(["ffmpeg", *inputs, "graph"], inputs, footage_count=1)

    base = key()
    audio.write_bytes(b"a" * 4096)                    # the mix stage rewrote the same bytes
    os.utime(audio, (2_000_000, 2_000_000))
    assert key() == base
    audio.write_bytes(b"b" * 4096)                    # same size, different sound
    assert key() != base
    audio.write_bytes(b"a" * 4096)
    os.utime(clip, (3_000_000, 3_000_000))            # footage is identified by size + mtime
    assert key() != base


def test_inputs_without_a_plain_file_keep_the_single_pass(tmp_path):
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"v")
    assert sp.input_files(["-i", str(clip)]) == [clip]
    with pytest.raises(sp.SecondPassUnavailable):
        sp.input_files(["-i", str(clip), "-framerate", "30", "-i", str(tmp_path / "frame_%05d.png")])


def test_old_intermediates_are_dropped_but_a_running_pass_one_is_left_alone(tmp_path):
    import os
    finished = []
    for i in range(4):
        path = sp.intermediate_path(tmp_path, f"{i}" * 32)
        path.write_bytes(b"x" * 2048)
        os.utime(path, (1_000_000 + i, 1_000_000 + i))
        finished.append(path)
    running = tmp_path / "pre_subtitles_running.partial.mp4"
    running.write_bytes(b"x")
    os.utime(running, (1, 1))                          # older than everything
    other = tmp_path / "unrelated.mp4"
    other.write_bytes(b"x")

    sp.mark_used(finished[0])                          # reused just now -> newest
    assert sp.drop_old_intermediates(tmp_path, keep=2) == [finished[1], finished[2]]
    assert finished[0].exists() and finished[3].exists()
    assert running.exists() and other.exists()


@pytest.mark.parametrize("value,off", [("0", True), ("off", True), ("", False), ("1", False)])
def test_environment_switch(monkeypatch, value, off):
    monkeypatch.setenv(sp.ENV_SWITCH, value)
    assert sp.switched_off() is off


# ------------------------------------------------------------ real render
import shutil      # noqa: E402
import subprocess  # noqa: E402
import wave        # noqa: E402

needs_ffmpeg = pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg and FFprobe are required for real renders",
)

ASS_HEAD = (
    "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n[V4+ Styles]\n"
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
    "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
    "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
    "Style: Default,Arial,120,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,40,40,420,1\n"
    "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
)


def _frames_md5(path):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v", "-f", "md5", "-"],
                         check=True, capture_output=True, text=True).stdout
    return out.strip()


def _probe(path, entries, stream):
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", stream,
                          "-show_entries", f"stream={entries}", "-of", "csv=p=0", str(path)],
                         check=True, capture_output=True, text=True).stdout
    return out.strip().strip(",")


@pytest.mark.render_regression
@needs_ffmpeg
def test_renderer_reuses_the_picture_when_only_the_subtitles_change(tmp_path, monkeypatch):
    from scripts import video_editor
    from scripts.video_editor import VideoEditor

    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    monkeypatch.delenv(sp.ENV_SWITCH, raising=False)
    cache = tmp_path / "cache"
    monkeypatch.setattr(sp, "cache_dir", lambda: cache)

    source = tmp_path / "source.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=270x480:r=30:d=6",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(source)], check=True)
    audio = tmp_path / "mixed_audio.wav"
    with wave.open(str(audio), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(b"\x00\x00" * 48000 * 4)
    ass = tmp_path / "subtitles.ass"

    passes = []
    real_run = video_editor.subprocess.run

    def counting_run(cmd, *args, **kwargs):
        if cmd and str(cmd[0]) == "ffmpeg" and "-filter_complex" in cmd:
            passes.append("pass1" if "[v_pre_subs]" in cmd else "burn" if "copy" in cmd else "single")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(video_editor.subprocess, "run", counting_run)

    def render(name, text, clips, two_pass=True):
        ass.write_text(ASS_HEAD + f"Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{text}\n", encoding="utf-8")
        out = tmp_path / name
        passes.clear()
        VideoEditor.assemble_tiktok_video(
            raw_video_paths=[str(source)], total_duration=2.0, mixed_audio_path=str(audio),
            ass_subtitle_path=str(ass), output_mp4_path=str(out), clip_list=clips,
            transitions=["cut"], subtitle_second_pass_enabled=two_pass,
        )
        return out, list(passes)

    clips = [{"source_path": str(source), "trim_start": 0.0, "trim_end": 1.0},
             {"source_path": str(source), "trim_start": 3.0, "trim_end": 4.0}]

    single, ran = render("single.mp4", "FIRST", clips, two_pass=False)
    assert ran == ["single"] and not cache.exists()

    first, ran = render("first.mp4", "FIRST", clips)
    assert ran == ["pass1", "burn"]
    intermediates = sorted(cache.glob("pre_subtitles_*.mp4"))
    assert len(intermediates) == 1 and not list(cache.glob("*.partial.mp4"))
    assert _probe(first, "nb_read_frames", "v:0") == _probe(single, "nb_read_frames", "v:0") == "60"
    assert _probe(first, "codec_name", "a:0") == "aac"
    assert _probe(first, "width,height", "v:0") == "1080,1920"

    edited, ran = render("edited.mp4", "SECOND", clips)
    assert ran == ["burn"], "a caption edit must not redo the picture"
    assert sorted(cache.glob("pre_subtitles_*.mp4")) == intermediates
    assert _frames_md5(edited) != _frames_md5(first), "the new caption must be on screen"

    again, ran = render("again.mp4", "FIRST", clips)
    assert ran == ["burn"] and _frames_md5(again) == _frames_md5(first)

    retimed = [dict(clips[0], trim_start=0.5, trim_end=1.5), clips[1]]
    _, ran = render("retimed.mp4", "FIRST", retimed)
    assert ran == ["pass1", "burn"], "a timeline change must not reuse the old picture"
    assert len(list(cache.glob("pre_subtitles_*.mp4"))) == 2

    monkeypatch.setenv(sp.ENV_SWITCH, "0")
    _, ran = render("switched_off.mp4", "FIRST", clips)
    assert ran == ["single"]


def test_only_a_rerender_of_an_existing_project_asks_for_the_second_pass():
    """A first production render keeps the single pass (owner decision 2026-11-12)."""
    import inspect
    from scripts.stages import video_assembly_stage
    from scripts.video_editor import VideoEditor

    source = inspect.getsource(video_assembly_stage)
    assert 'if getattr(ctx, "resume_from", None):\n                assemble_kwargs["subtitle_second_pass_enabled"] = True' in source
    parameter = inspect.signature(VideoEditor.assemble_tiktok_video).parameters["subtitle_second_pass_enabled"]
    assert parameter.default is False
