"""Prototype for burning subtitles in a second pass (scripts/subtitle_second_pass.py).
Pure command construction: no ffmpeg, no project data."""
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
