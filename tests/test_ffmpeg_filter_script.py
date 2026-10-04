"""
Long ffmpeg filter graphs travel through a file instead of the command line.

Windows CreateProcess rejects a command line over 32,767 characters
(`[WinError 206] The filename or extension is too long`). The timeline render
graph grows with the clip count, so scripts/ffmpeg_graph.py moves
`-filter_complex <graph>` into a UTF-8 temp file once the command passes a
threshold. These tests pin:

* below the threshold the command is untouched (same list, no temp file);
* above it `-filter_complex <graph>` becomes `-/filter_complex <file>` (ffmpeg
  >= 7) or `-filter_complex_script <file>` and the file holds the exact graph;
* the temp file is removed on success, on a failing runner and on a failing
  ffmpeg, for the render in video_editor.py and the audio mix in sfx_manager.py;
* a real ffmpeg render through the file matches the inline render.

Everything lives under tmp_path (tempfile.tempdir is redirected there); the
real-ffmpeg test renders a few tiny synthetic clips.
"""

import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import ffmpeg_graph
from scripts.ffmpeg_graph import (
    cleanup_graph_file,
    cmdline_length,
    externalize_filter_graph,
    filter_graph_file_flag,
    filter_graph_via_file,
    supports_slash_option,
)


@pytest.fixture(autouse=True)
def _fresh_capability_cache():
    """supports_slash_option is cached per process; every test starts clean."""
    supports_slash_option.cache_clear()
    yield
    supports_slash_option.cache_clear()


@pytest.fixture
def temp_in_tmp_path(tmp_path, monkeypatch):
    """Route tempfile.mkstemp (no dir given) into tmp_path so leaks are visible."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    return tmp_path


def _graph_files(folder: Path):
    return sorted(folder.glob("omnicut_filtergraph_*.txt"))


def _cmd(graph: str):
    return ["ffmpeg", "-y", "-i", "in.mp4", "-filter_complex", graph,
            "-map", "[v]", "out.mp4"]


# --------------------------------------------------------------------------
# helper: threshold behaviour
# --------------------------------------------------------------------------

def test_below_threshold_returns_the_same_command_untouched(temp_in_tmp_path):
    cmd = _cmd("[0:v]null[v]")
    snapshot = list(cmd)

    new_cmd, graph_file = externalize_filter_graph(cmd, "[0:v]null[v]")

    assert graph_file is None
    assert new_cmd is cmd
    assert new_cmd == snapshot
    assert _graph_files(temp_in_tmp_path) == []


def test_exactly_at_threshold_stays_inline(temp_in_tmp_path):
    cmd = _cmd("[0:v]null[v]")
    new_cmd, graph_file = externalize_filter_graph(
        cmd, "[0:v]null[v]", threshold=cmdline_length(cmd))
    assert graph_file is None and new_cmd is cmd


def test_default_threshold_sits_below_the_windows_limit():
    assert ffmpeg_graph.FILTER_GRAPH_SCRIPT_THRESHOLD < ffmpeg_graph.WINDOWS_CMDLINE_LIMIT
    # keeps real headroom for -progress pipe:1 -nostats and path quoting
    assert ffmpeg_graph.WINDOWS_CMDLINE_LIMIT - ffmpeg_graph.FILTER_GRAPH_SCRIPT_THRESHOLD >= 2000


def test_above_threshold_moves_graph_to_file_and_keeps_other_args(temp_in_tmp_path, monkeypatch):
    monkeypatch.setattr(ffmpeg_graph, "supports_slash_option", lambda ffmpeg_bin="ffmpeg": True)
    graph = "[0:v]null[v];" + ("[0:v]null[x];" * 3000)
    cmd = _cmd(graph)

    new_cmd, graph_file = externalize_filter_graph(cmd, graph)
    try:
        assert graph_file is not None and graph_file.exists()
        assert graph_file.parent == temp_in_tmp_path
        assert new_cmd is not cmd
        assert cmd == _cmd(graph), "the caller's list must not be mutated"
        i = new_cmd.index("-/filter_complex")
        assert new_cmd[i + 1] == str(graph_file)
        # everything else is where it was
        assert new_cmd[:i] == cmd[:i]
        assert new_cmd[i + 2:] == cmd[i + 2:]
        assert graph not in new_cmd
        assert cmdline_length(new_cmd) < cmdline_length(cmd)
        assert graph_file.read_bytes() == graph.encode("utf-8")
    finally:
        cleanup_graph_file(graph_file)
    assert not graph_file.exists()


def test_threshold_zero_forces_the_file_path(temp_in_tmp_path):
    cmd = _cmd("[0:v]null[v]")
    new_cmd, graph_file = externalize_filter_graph(cmd, "[0:v]null[v]", threshold=0)
    try:
        assert graph_file is not None
        assert "-filter_complex" not in new_cmd
    finally:
        cleanup_graph_file(graph_file)


def test_command_without_the_graph_pair_is_left_alone(temp_in_tmp_path):
    cmd = ["ffmpeg", "-y", "-i", "in.mp4", "out.mp4"]
    new_cmd, graph_file = externalize_filter_graph(cmd, "[0:v]null[v]", threshold=0)
    assert new_cmd is cmd and graph_file is None
    assert _graph_files(temp_in_tmp_path) == []


def test_temp_dir_argument_is_honoured(tmp_path):
    target = tmp_path / "graphs"
    target.mkdir()
    cmd = _cmd("[0:v]null[v]")
    _, graph_file = externalize_filter_graph(cmd, "[0:v]null[v]", threshold=0, temp_dir=target)
    try:
        assert graph_file.parent == target
    finally:
        cleanup_graph_file(graph_file)


def test_thai_notice_is_printed_when_the_file_path_is_used(temp_in_tmp_path, capsys):
    cmd = _cmd("[0:v]null[v]")
    _, graph_file = externalize_filter_graph(cmd, "[0:v]null[v]", threshold=0)
    cleanup_graph_file(graph_file)
    out = capsys.readouterr().out
    assert "ย้าย filter graph" in out and graph_file.name in out


# --------------------------------------------------------------------------
# helper: which flag, for both ffmpeg capability outcomes
# --------------------------------------------------------------------------

def test_flag_is_slash_option_when_ffmpeg_supports_it(monkeypatch):
    monkeypatch.setattr(ffmpeg_graph, "supports_slash_option", lambda ffmpeg_bin="ffmpeg": True)
    assert filter_graph_file_flag() == "-/filter_complex"


def test_flag_is_filter_complex_script_when_ffmpeg_is_older(monkeypatch):
    monkeypatch.setattr(ffmpeg_graph, "supports_slash_option", lambda ffmpeg_bin="ffmpeg": False)
    assert filter_graph_file_flag() == "-filter_complex_script"


@pytest.mark.parametrize("supported, expected", [
    (True, "-/filter_complex"),
    (False, "-filter_complex_script"),
])
def test_externalized_command_uses_the_detected_flag(temp_in_tmp_path, monkeypatch, supported, expected):
    monkeypatch.setattr(ffmpeg_graph, "supports_slash_option", lambda ffmpeg_bin="ffmpeg": supported)
    new_cmd, graph_file = externalize_filter_graph(_cmd("[0:v]null[v]"), "[0:v]null[v]", threshold=0)
    try:
        assert expected in new_cmd
        assert new_cmd[new_cmd.index(expected) + 1] == str(graph_file)
    finally:
        cleanup_graph_file(graph_file)


def _fake_probe(monkeypatch, *, returncode=1, stdout="", stderr="", raises=None, calls=None):
    def fake_run(cmd, *args, **kwargs):
        if calls is not None:
            calls.append(list(cmd))
        if raises is not None:
            raise raises
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(ffmpeg_graph.subprocess, "run", fake_run)


def test_probe_old_ffmpeg_reports_unrecognized_option(monkeypatch):
    _fake_probe(monkeypatch, stderr="Unrecognized option '/filter_complex'.\n")
    assert supports_slash_option("ffmpeg") is False


def test_probe_new_ffmpeg_fails_on_the_missing_file_not_the_option(monkeypatch):
    _fake_probe(monkeypatch, stderr=(
        "Error opening file omnicut_filter_graph_probe_missing.txt.\n"
        "Error reading the value for option 'filter_complex' from file: x\n"
    ))
    assert supports_slash_option("ffmpeg") is True


@pytest.mark.parametrize("raises", [
    FileNotFoundError("ffmpeg"),
    subprocess.TimeoutExpired("ffmpeg", 15),
    OSError("boom"),
])
def test_probe_failure_never_crashes_and_falls_back_to_script_flag(monkeypatch, raises):
    _fake_probe(monkeypatch, raises=raises)
    assert supports_slash_option("ffmpeg") is False
    assert filter_graph_file_flag("ffmpeg") == "-filter_complex_script"


def test_probe_result_is_cached_per_binary(monkeypatch):
    calls = []
    _fake_probe(monkeypatch, stderr="Error reading the value for option 'filter_complex'", calls=calls)
    assert supports_slash_option("ffmpeg") is True
    assert supports_slash_option("ffmpeg") is True
    assert filter_graph_file_flag("ffmpeg") == "-/filter_complex"
    assert len(calls) == 1


def test_probe_on_the_installed_ffmpeg_gives_a_usable_flag():
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg is not installed")
    assert filter_graph_file_flag() in ("-/filter_complex", "-filter_complex_script")


# --------------------------------------------------------------------------
# helper: file content and cleanup
# --------------------------------------------------------------------------

def test_unicode_graph_round_trips_as_utf8_without_bom(temp_in_tmp_path):
    graph = ("[0:v]drawtext=text='ราคาพิเศษ ฿1,990 ✓ 🔥 Bluetooth':x=10:y=10[v];\n"
             "[v]null[v2]")
    new_cmd, graph_file = externalize_filter_graph(_cmd(graph), graph, threshold=0)
    try:
        raw = graph_file.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), "BOM would corrupt the first filter label"
        assert b"\r\n" not in raw, "newlines must not be rewritten to CRLF"
        assert raw.decode("utf-8") == graph
    finally:
        cleanup_graph_file(graph_file)


def test_context_manager_removes_the_file_after_success(temp_in_tmp_path):
    seen = {}
    with filter_graph_via_file(_cmd("[0:v]null[v]"), "[0:v]null[v]", threshold=0) as run_cmd:
        flag = next(a for a in run_cmd if a in ("-/filter_complex", "-filter_complex_script"))
        path = Path(run_cmd[run_cmd.index(flag) + 1])
        seen["existed_during_run"] = path.exists()
        seen["path"] = path
    assert seen["existed_during_run"] is True
    assert not seen["path"].exists()
    assert _graph_files(temp_in_tmp_path) == []


def test_context_manager_removes_the_file_when_the_runner_raises(temp_in_tmp_path):
    with pytest.raises(RuntimeError, match="ffmpeg died"):
        with filter_graph_via_file(_cmd("[0:v]null[v]"), "[0:v]null[v]", threshold=0):
            assert len(_graph_files(temp_in_tmp_path)) == 1
            raise RuntimeError("ffmpeg died")
    assert _graph_files(temp_in_tmp_path) == []


def test_context_manager_below_threshold_creates_no_file(temp_in_tmp_path):
    cmd = _cmd("[0:v]null[v]")
    with filter_graph_via_file(cmd, "[0:v]null[v]") as run_cmd:
        assert run_cmd is cmd
        assert _graph_files(temp_in_tmp_path) == []


def test_cleanup_tolerates_none_and_missing_files(tmp_path):
    cleanup_graph_file(None)
    cleanup_graph_file(tmp_path / "never_existed.txt")


def test_write_failure_leaves_no_temp_file(temp_in_tmp_path, monkeypatch):
    real_fdopen = os.fdopen

    def exploding_fdopen(fd, *args, **kwargs):
        handle = real_fdopen(fd, *args, **kwargs)
        handle.close()
        raise OSError("disk full")

    monkeypatch.setattr(ffmpeg_graph.os, "fdopen", exploding_fdopen)
    with pytest.raises(OSError, match="disk full"):
        externalize_filter_graph(_cmd("[0:v]null[v]"), "[0:v]null[v]", threshold=0)
    assert _graph_files(temp_in_tmp_path) == []


# --------------------------------------------------------------------------
# video_editor.assemble_tiktok_video (stubbed ffmpeg)
# --------------------------------------------------------------------------

from scripts.video_editor import VideoEditor  # noqa: E402  (after helper tests)


class _Done:
    def __init__(self, returncode=0, stderr=""):
        self.returncode = returncode
        self.stdout = ""
        self.stderr = stderr


class _FakeProc:
    """Popen stand-in: no output lines, exits at once."""

    def __init__(self, returncode=0):
        import io
        self.returncode = returncode
        self.stdout = io.StringIO("")
        self.stderr = io.StringIO("")

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode

    def terminate(self):
        pass

    def kill(self):
        pass


def _stub_media(monkeypatch):
    monkeypatch.setattr(
        VideoEditor, "get_media_info",
        classmethod(lambda cls, path: {"duration": 10.0, "width": 1080, "height": 1920, "fps": 30.0}),
    )


def _probe_answer(slash_supported):
    """What `ffmpeg -/filter_complex <missing file>` prints on new / old ffmpeg."""
    stderr = ("Error reading the value for option 'filter_complex' from file: x" if slash_supported
              else "Unrecognized option '/filter_complex'.")
    return SimpleNamespace(returncode=1, stdout="", stderr=stderr)


def _render_with_stubs(tmp_path, monkeypatch, clip_count, *, progress=False, returncode=0,
                       popen_raises=None, inspect_file=True, slash_supported=True):
    """Run assemble_tiktok_video with ffmpeg faked; return what the fake saw."""
    _stub_media(monkeypatch)
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    seen = {}

    def read_graph_file(cmd):
        for flag in ("-/filter_complex", "-filter_complex_script"):
            if flag in cmd:
                path = Path(cmd[cmd.index(flag) + 1])
                seen["flag"] = flag
                seen["file"] = path
                seen["file_existed_during_run"] = path.exists()
                if inspect_file and path.exists():
                    seen["graph"] = path.read_bytes().decode("utf-8")
                return
        seen["flag"] = "-filter_complex"

    def fake_run(cmd, *a, **k):
        if cmd and "-hide_banner" in cmd and "-/filter_complex" in cmd:
            return _probe_answer(slash_supported)  # capability probe, not the render
        if cmd and "ffmpeg" in str(cmd[0]).lower():
            seen["cmd"] = list(cmd)
            read_graph_file(cmd)
            return _Done(returncode, "simulated ffmpeg failure" if returncode else "")
        return _Done()

    def fake_popen(cmd, **k):
        if popen_raises is not None:
            raise popen_raises
        seen["cmd"] = list(cmd)
        read_graph_file(cmd)
        return _FakeProc(returncode)

    monkeypatch.setattr("scripts.video_editor.subprocess.run", fake_run)
    monkeypatch.setattr("scripts.video_editor.subprocess.Popen", fake_popen)

    src = tmp_path / "clip.mp4"
    src.write_bytes(b"fake")
    audio = tmp_path / "mixed.wav"
    audio.write_bytes(b"fake")
    subs = tmp_path / "subs.ass"
    subs.write_text("[Script Info]\n", encoding="utf-8")
    out = tmp_path / "out.mp4"
    clips = [{"source_path": str(src), "trim_start": 1.0, "trim_end": 3.0}
             for _ in range(clip_count)]
    kwargs = {"progress_callback": (lambda a, b: None)} if progress else {}
    error = None
    try:
        VideoEditor.assemble_tiktok_video(
            raw_video_paths=[str(src)],
            total_duration=float(2 * clip_count),
            mixed_audio_path=str(audio),
            ass_subtitle_path=str(subs),
            output_mp4_path=str(out),
            clip_list=clips,
            **kwargs,
        )
    except Exception as exc:  # noqa: BLE001 - failure paths are asserted by callers
        error = exc
    seen["error"] = error
    return seen


@pytest.mark.parametrize("progress", [False, True])
def test_ten_clip_render_command_stays_inline(tmp_path, monkeypatch, temp_in_tmp_path, progress):
    seen = _render_with_stubs(tmp_path, monkeypatch, 10, progress=progress)
    cmd = seen["cmd"]
    assert "-filter_complex" in cmd
    assert "-filter_complex_script" not in cmd and "-/filter_complex" not in cmd
    assert cmdline_length(cmd) < ffmpeg_graph.FILTER_GRAPH_SCRIPT_THRESHOLD
    assert _graph_files(temp_in_tmp_path) == []


@pytest.mark.parametrize("slash_supported, expected_flag", [
    (True, "-/filter_complex"),
    (False, "-filter_complex_script"),
])
@pytest.mark.parametrize("progress", [False, True])
def test_hundred_clip_render_fits_the_windows_limit_via_graph_file(
        tmp_path, monkeypatch, temp_in_tmp_path, progress, slash_supported, expected_flag):
    seen = _render_with_stubs(tmp_path, monkeypatch, 100, progress=progress,
                              slash_supported=slash_supported)
    cmd = seen["cmd"]

    assert seen["error"] is None, seen["error"]
    assert seen["flag"] == expected_flag
    assert "-filter_complex" not in cmd, "the 20k-char graph must not stay on the command line"
    assert cmdline_length(cmd) < ffmpeg_graph.WINDOWS_CMDLINE_LIMIT
    assert seen["file_existed_during_run"] is True
    # the file carried the real graph: one scale/trim chain per clip + the final label
    assert seen["graph"].count("[99:v]") >= 1
    assert "[v_final]" in seen["graph"]
    assert not seen["file"].exists(), "graph temp file must be deleted after the render"
    assert _graph_files(temp_in_tmp_path) == []


def test_graph_in_file_equals_the_graph_that_was_inline(tmp_path, monkeypatch, temp_in_tmp_path):
    """Same inputs, threshold forced both ways: only the delivery differs."""
    monkeypatch.setattr(ffmpeg_graph, "FILTER_GRAPH_SCRIPT_THRESHOLD", 10**9)
    inline = _render_with_stubs(tmp_path, monkeypatch, 12)
    inline_graph = inline["cmd"][inline["cmd"].index("-filter_complex") + 1]

    monkeypatch.setattr(ffmpeg_graph, "FILTER_GRAPH_SCRIPT_THRESHOLD", 0)
    via_file = _render_with_stubs(tmp_path, monkeypatch, 12)

    assert via_file["graph"] == inline_graph
    flag = via_file["flag"]
    stripped = [a for a in via_file["cmd"]]
    i = stripped.index(flag)
    # Every other argument is identical, in the same order.
    assert stripped[:i] == inline["cmd"][:i]
    assert stripped[i + 2:] == inline["cmd"][i + 2:]


@pytest.mark.parametrize("progress", [False, True])
def test_graph_file_is_removed_when_ffmpeg_fails(tmp_path, monkeypatch, temp_in_tmp_path, progress):
    monkeypatch.setattr(ffmpeg_graph, "FILTER_GRAPH_SCRIPT_THRESHOLD", 0)
    # the fake ffmpeg exits non-zero; the render raises, the temp file must go
    seen = _render_with_stubs(tmp_path, monkeypatch, 3, progress=progress, returncode=1)
    assert isinstance(seen["error"], RuntimeError)
    assert seen["file_existed_during_run"] is True
    assert not seen["file"].exists()
    assert _graph_files(temp_in_tmp_path) == []


def test_graph_file_is_removed_when_ffmpeg_cannot_even_start(tmp_path, monkeypatch, temp_in_tmp_path):
    monkeypatch.setattr(ffmpeg_graph, "FILTER_GRAPH_SCRIPT_THRESHOLD", 0)
    seen = _render_with_stubs(
        tmp_path, monkeypatch, 3, progress=True,
        popen_raises=FileNotFoundError("[WinError 206] The filename or extension is too long"),
        inspect_file=False,
    )
    assert isinstance(seen["error"], FileNotFoundError)
    assert _graph_files(temp_in_tmp_path) == []


# --------------------------------------------------------------------------
# sfx_manager.mix_audio_track (stubbed ffmpeg)
# --------------------------------------------------------------------------

from scripts import sfx_manager as sfx_module  # noqa: E402
from scripts.sfx_manager import SFXManager  # noqa: E402


@pytest.fixture
def sfx_env(tmp_path, monkeypatch):
    sfx_file = tmp_path / "whoosh.wav"
    sfx_file.write_bytes(b"sfx")
    monkeypatch.setattr(SFXManager, "resolve", classmethod(lambda cls, name: sfx_file))
    monkeypatch.setattr(SFXManager, "resolve_bgm_path", classmethod(lambda cls, name=None: None))
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"voice")
    before = SFXManager.last_mix_status
    yield SimpleNamespace(voice=voice, out=tmp_path / "mix.wav")
    SFXManager.last_mix_status = before


def _fake_mix_ffmpeg(monkeypatch, seen, returncode=0):
    def fake_run(cmd, **kwargs):
        if "-hide_banner" in cmd and "-/filter_complex" in cmd:
            return _probe_answer(True)  # capability probe, not the mix
        if "-filter_complex" in cmd or "-/filter_complex" in cmd or "-filter_complex_script" in cmd:
            seen["cmd"] = list(cmd)
            for flag in ("-/filter_complex", "-filter_complex_script"):
                if flag in cmd:
                    path = Path(cmd[cmd.index(flag) + 1])
                    seen["flag"] = flag
                    seen["file"] = path
                    seen["graph"] = path.read_bytes().decode("utf-8")
            return SimpleNamespace(returncode=returncode, stderr="" if returncode == 0 else "simulated")
        return SimpleNamespace(returncode=0, stderr="")  # voice-only fallback

    monkeypatch.setattr(sfx_module.subprocess, "run", fake_run)


def test_audio_mix_with_many_sfx_uses_a_graph_file(sfx_env, monkeypatch, temp_in_tmp_path):
    seen = {}
    _fake_mix_ffmpeg(monkeypatch, seen)
    cues = [{"sfx": "whoosh", "start": 0.1 * i} for i in range(250)]

    SFXManager.mix_audio_track(str(sfx_env.voice), cues, 30.0, str(sfx_env.out))

    assert seen["flag"] in ("-/filter_complex", "-filter_complex_script")
    assert "-filter_complex" not in seen["cmd"]
    assert "[aout]" in seen["graph"] and "[sfx_249]" in seen["graph"]
    assert cmdline_length(seen["cmd"]) < ffmpeg_graph.WINDOWS_CMDLINE_LIMIT
    assert not seen["file"].exists()
    assert _graph_files(temp_in_tmp_path) == []


def test_audio_mix_with_few_sfx_stays_inline(sfx_env, monkeypatch, temp_in_tmp_path):
    seen = {}
    _fake_mix_ffmpeg(monkeypatch, seen)
    cues = [{"sfx": "whoosh", "start": 0.5 * i} for i in range(5)]

    SFXManager.mix_audio_track(str(sfx_env.voice), cues, 30.0, str(sfx_env.out))

    assert "-filter_complex" in seen["cmd"]
    assert "flag" not in seen
    assert _graph_files(temp_in_tmp_path) == []


def test_audio_mix_graph_file_is_removed_when_the_mix_fails(sfx_env, monkeypatch, temp_in_tmp_path):
    seen = {}
    _fake_mix_ffmpeg(monkeypatch, seen, returncode=1)
    monkeypatch.setattr(ffmpeg_graph, "FILTER_GRAPH_SCRIPT_THRESHOLD", 0)

    SFXManager.mix_audio_track(str(sfx_env.voice), [{"sfx": "whoosh", "start": 1.0}], 30.0,
                               str(sfx_env.out))

    assert SFXManager.last_mix_status["fallback"] is True
    assert not seen["file"].exists()
    assert _graph_files(temp_in_tmp_path) == []


# --------------------------------------------------------------------------
# Real ffmpeg: file-delivered graph renders the same video as the inline graph
# --------------------------------------------------------------------------

_REAL = pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg and FFprobe are required for the real render comparison",
)


def _run(cmd):
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if done.returncode:
        raise RuntimeError(done.stderr[-800:])
    return done.stdout


def _make_source(path: Path, color: str):
    _run([shutil.which("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error",
          "-f", "lavfi", "-i", f"testsrc2=size=360x640:rate=30:duration=2",
          "-vf", f"hue=h={color}",
          "-an", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(path)])


def _silence(path: Path, seconds: float):
    with wave.open(str(path), "wb") as sound:
        sound.setnchannels(2)
        sound.setsampwidth(2)
        sound.setframerate(48000)
        sound.writeframes(b"\x00" * int(48000 * 4 * seconds))


def _ass(path: Path):
    path.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,40,40,420,1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n",
        encoding="utf-8", newline="\n")


def _probe_video(path: Path):
    out = _run([shutil.which("ffprobe"), "-v", "error", "-count_frames", "-select_streams", "v:0",
                "-show_entries", "stream=nb_read_frames,width,height,duration",
                "-of", "default=noprint_wrappers=1", str(path)])
    return dict(line.split("=", 1) for line in out.strip().splitlines())


def _frame_values(path: Path):
    """Every frame decoded to a tiny gray raster (bytes) for a pixel comparison."""
    done = subprocess.run(
        [shutil.which("ffmpeg"), "-v", "error", "-i", str(path), "-vf", "scale=54:96,format=gray",
         "-f", "rawvideo", "-"],
        capture_output=True, check=True)
    return done.stdout


def _render_real(tmp_path, monkeypatch, label, sources, audio, subs):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    out = tmp_path / f"{label}.mp4"
    clips = [
        {"source_path": str(sources[0]), "trim_start": 0.0, "trim_end": 0.6, "speed": 1},
        {"source_path": str(sources[1]), "trim_start": 0.4, "trim_end": 1.1, "speed": 1},
        {"source_path": str(sources[0]), "trim_start": 1.0, "trim_end": 1.5, "speed": 1},
    ]
    VideoEditor.assemble_tiktok_video(
        raw_video_paths=[str(sources[0])],
        total_duration=1.8,
        mixed_audio_path=str(audio),
        ass_subtitle_path=str(subs),
        output_mp4_path=str(out),
        clip_list=clips,
        export_preset="draft",
        style_preset="clean_tech_review",
    )
    return out


@_REAL
@pytest.mark.render_regression
@pytest.mark.parametrize("flag_choice", ["-/filter_complex", "-filter_complex_script"])
def test_real_ffmpeg_graph_file_render_matches_inline_render(
        tmp_path, monkeypatch, temp_in_tmp_path, flag_choice):
    # Is the flag actually available in the ffmpeg that runs here?
    if flag_choice == "-/filter_complex" and not supports_slash_option("ffmpeg"):
        pytest.skip("installed ffmpeg predates -/filter_complex")

    sources = [tmp_path / "a.mp4", tmp_path / "b.mp4"]
    _make_source(sources[0], "0")
    _make_source(sources[1], "120")
    audio = tmp_path / "mixed.wav"
    _silence(audio, 2.5)
    subs = tmp_path / "subs.ass"
    _ass(subs)

    # inline: threshold far above any command length
    monkeypatch.setattr(ffmpeg_graph, "FILTER_GRAPH_SCRIPT_THRESHOLD", 10**9)
    inline_out = _render_real(tmp_path, monkeypatch, "inline", sources, audio, subs)

    # file: threshold forced to 0, the flag chosen by the capability probe stubbed
    monkeypatch.setattr(ffmpeg_graph, "FILTER_GRAPH_SCRIPT_THRESHOLD", 0)
    monkeypatch.setattr(ffmpeg_graph, "supports_slash_option",
                        lambda ffmpeg_bin="ffmpeg": flag_choice == "-/filter_complex")
    used = {}
    real_externalize = ffmpeg_graph.externalize_filter_graph

    def spy(cmd, graph, **kwargs):
        new_cmd, graph_file = real_externalize(cmd, graph, **kwargs)
        used["flag"] = next((a for a in new_cmd if a in ("-/filter_complex", "-filter_complex_script")), None)
        used["file"] = graph_file
        return new_cmd, graph_file

    monkeypatch.setattr("scripts.video_editor.externalize_filter_graph", spy)
    file_out = _render_real(tmp_path, monkeypatch, "scriptfile", sources, audio, subs)

    assert used["flag"] == flag_choice
    assert used["file"] is not None and not used["file"].exists()
    assert _graph_files(temp_in_tmp_path) == []

    a, b = _probe_video(inline_out), _probe_video(file_out)
    assert b["nb_read_frames"] == a["nb_read_frames"]
    assert (b["width"], b["height"]) == (a["width"], a["height"])
    assert abs(float(b["duration"]) - float(a["duration"])) < 0.001

    frames_a, frames_b = _frame_values(inline_out), _frame_values(file_out)
    assert len(frames_a) == len(frames_b) > 0
    mean_abs_diff = sum(abs(x - y) for x, y in zip(frames_a, frames_b)) / len(frames_a)
    assert mean_abs_diff < 0.5, f"graph file changed the picture (mean abs diff {mean_abs_diff})"
