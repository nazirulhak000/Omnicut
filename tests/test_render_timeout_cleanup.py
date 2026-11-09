"""Guards the fix for the CRITICAL bug in _Docs/SAAS_READINESS_PLAN.md 11b:

the streaming-progress render path (`VideoEditor.assemble_tiktok_video`,
`scripts/video_editor.py` around line 953) used a bare `subprocess.Popen` +
`proc.wait(timeout=300)` with no try/finally. A `TimeoutExpired` (or any other
exception) out of that block left the ffmpeg child running unattended --
burning CPU after `_RENDER_SLOT` had already been released -- and left a
partial .mp4 sitting at the output path for the next retry to trip over.

These tests drive `assemble_tiktok_video` with `progress_callback` set (the
real UI path, since `VideoAssemblyStage` always passes one) and a fake
`Popen` standing in for ffmpeg, so no real encode ever runs and no test takes
anywhere near 300s.
"""

import subprocess
from pathlib import Path

import pytest

from scripts.video_editor import VideoEditor

_REAL_POPEN = subprocess.Popen


FAKE_MEDIA_INFO = {
    "duration": 1.0,
    "width": 1080,
    "height": 1920,
    "rotation": 0,
    "fps": 30,
    "has_audio": False,
    "codec_name": "h264",
}


class _FakeStream:
    """Stands in for proc.stdout / proc.stderr: yields nothing, like an
    ffmpeg that has gone silent after startup."""

    def readline(self):
        return ""


class _FakePopenHangs:
    """Fake ffmpeg child whose `.wait()` always raises TimeoutExpired, like
    a real ffmpeg still encoding past the deadline. Records whether it was
    terminated/killed so the test can assert the fix's cleanup ran."""

    instances = []

    def __init__(self, cmd, **kwargs):
        self.args = cmd
        self.stdout = _FakeStream()
        self.stderr = _FakeStream()
        self.returncode = None
        self.terminated = False
        self.killed = False
        self._wait_calls = 0
        _FakePopenHangs.instances.append(self)

    def poll(self):
        return None if self.returncode is None else self.returncode

    def wait(self, timeout=None):
        self._wait_calls += 1
        if not self.terminated:
            # First wait() is the real `proc.wait(timeout=300)` call --
            # simulate ffmpeg still running past the deadline.
            raise subprocess.TimeoutExpired(cmd=self.args, timeout=timeout)
        # Post-terminate wait() succeeds immediately, as a real ffmpeg
        # normally exits promptly once signalled.
        self.returncode = -15
        return self.returncode

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True
        self.returncode = -9


def _common_kwargs(tmp_path, output):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"not a real video, never read by a mocked ffmpeg")
    audio = tmp_path / "mix.wav"
    audio.write_bytes(b"not real audio either")
    subtitles = tmp_path / "captions.ass"
    subtitles.write_text("[Script Info]\n", encoding="utf-8")

    return dict(
        raw_video_paths=[str(source)],
        total_duration=1.0,
        mixed_audio_path=str(audio),
        ass_subtitle_path=str(subtitles),
        output_mp4_path=str(output),
        clip_list=[{
            "source_path": str(source),
            "trim_start": 0.0,
            "trim_end": 1.0,
            "duration": 1.0,
        }],
        export_preset="draft",
    )


def _noop_progress(_current, _total):
    pass


def test_popen_timeout_kills_process_and_removes_partial_output(tmp_path, monkeypatch):
    """A TimeoutExpired out of proc.wait() must: (1) terminate/kill the
    orphaned ffmpeg child, (2) delete the partial file this invocation was
    writing, and (3) still propagate so render_jobs.fail_job sees a failure."""
    _FakePopenHangs.instances.clear()
    output = tmp_path / "out" / "rendered.mp4"

    # Forces hardware_encoder() to short-circuit to libx264 without shelling
    # out to a real ffmpeg -- it uses plain subprocess.run, unrelated to the
    # Popen path under test, and would otherwise run for real.
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    monkeypatch.setattr(subprocess, "Popen", _FakePopenHangs)
    monkeypatch.setattr(VideoEditor, "get_media_info", staticmethod(lambda path: dict(FAKE_MEDIA_INFO)))

    def _write_partial_then_return(video_path, poster_path=None):
        return None

    monkeypatch.setattr(VideoEditor, "generate_poster_thumbnail", classmethod(lambda cls, *a, **k: None))

    # ffmpeg (real one) creates the .partial.mp4 target the moment it opens
    # it for writing with -y; the fake process can't do that, so the test
    # creates the partial file itself to prove the cleanup path deletes it
    # rather than assuming it never existed.
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name("rendered.partial.mp4")
    partial.write_bytes(b"partial ffmpeg output, half-encoded")

    with pytest.raises(subprocess.TimeoutExpired):
        VideoEditor.assemble_tiktok_video(
            progress_callback=_noop_progress,
            **_common_kwargs(tmp_path, output),
        )

    assert len(_FakePopenHangs.instances) == 1
    fake_proc = _FakePopenHangs.instances[0]
    assert fake_proc.terminated is True, "orphaned ffmpeg child must be terminate()'d on timeout"
    assert fake_proc.args[-1].endswith("rendered.partial.mp4"), "ffmpeg must encode to the .partial name"

    assert not partial.exists(), "partial .mp4 from the failed render must be removed"
    assert not output.exists(), "a failed render never appears under the final export name"


def test_popen_ffmpeg_error_returncode_also_cleans_up(tmp_path, monkeypatch):
    """A non-timeout failure (ffmpeg exits with a bad returncode, raising
    RuntimeError) must go through the same cleanup: no process left running,
    partial file removed, and the error still propagates."""

    class _FakePopenFails(_FakePopenHangs):
        def wait(self, timeout=None):
            self._wait_calls += 1
            self.returncode = 1
            return self.returncode

    _FakePopenHangs.instances.clear()
    output = tmp_path / "out2" / "rendered.mp4"

    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    monkeypatch.setattr(subprocess, "Popen", _FakePopenFails)
    monkeypatch.setattr(VideoEditor, "get_media_info", staticmethod(lambda path: dict(FAKE_MEDIA_INFO)))
    monkeypatch.setattr(VideoEditor, "generate_poster_thumbnail", classmethod(lambda cls, *a, **k: None))

    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name("rendered.partial.mp4")
    partial.write_bytes(b"partial ffmpeg output, half-encoded")

    with pytest.raises(RuntimeError, match="FFmpeg exit 1"):
        VideoEditor.assemble_tiktok_video(
            progress_callback=_noop_progress,
            **_common_kwargs(tmp_path, output),
        )

    assert not partial.exists(), "partial .mp4 from the failed render must be removed"
    assert not output.exists()


def test_successful_render_does_not_touch_output_file(tmp_path, monkeypatch):
    """Guardrail on the cleanup itself: when the (faked) render succeeds,
    the finally block must be a no-op -- it must not delete the very file
    the render just produced."""

    class _FakePopenSucceeds(_FakePopenHangs):
        def __new__(cls, cmd, **kwargs):
            # Only the final encode is faked; the media gate's ffprobe /
            # tail-decode run against the real tools.
            if "-filter_complex" not in cmd and not any("filter_complex_script" in str(c) for c in cmd):
                return _REAL_POPEN(cmd, **kwargs)
            return super().__new__(cls)

        def wait(self, timeout=None):
            self.returncode = 0
            return 0

    _FakePopenHangs.instances.clear()
    output = tmp_path / "out3" / "rendered.mp4"

    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    monkeypatch.setattr(subprocess, "Popen", _FakePopenSucceeds)
    monkeypatch.setattr(VideoEditor, "get_media_info", staticmethod(lambda path: dict(FAKE_MEDIA_INFO)))
    monkeypatch.setattr(VideoEditor, "generate_poster_thumbnail", classmethod(lambda cls, *a, **k: None))

    output.parent.mkdir(parents=True, exist_ok=True)
    # The real ffmpeg would have written the finished .partial.mp4 by the
    # time proc.wait() returns 0; the fake can't, so the test stands in for
    # it with a real draft-spec (720x1280 @ 30) clip that passes the gate.
    partial = output.with_name("rendered.partial.mp4")
    _make_real_clip(partial, "720x1280")
    finished = partial.read_bytes()

    result = VideoEditor.assemble_tiktok_video(
        progress_callback=_noop_progress,
        **_common_kwargs(tmp_path, output),
    )

    assert Path(result) == output.resolve()
    assert output.exists(), "a successful render's own output must survive the finally block"
    assert output.read_bytes() == finished
    assert not partial.exists(), "the validated partial is os.replace-d onto the export name"


def test_successful_exit_with_truncated_output_is_rejected(tmp_path, monkeypatch):
    """S6-04: exit code 0 is not proof -- a truncated file fails the gate,
    is deleted, and never reaches the export name."""

    class _FakePopenSucceeds(_FakePopenHangs):
        def __new__(cls, cmd, **kwargs):
            # Only the final encode is faked; the media gate's ffprobe /
            # tail-decode run against the real tools.
            if "-filter_complex" not in cmd and not any("filter_complex_script" in str(c) for c in cmd):
                return _REAL_POPEN(cmd, **kwargs)
            return super().__new__(cls)

        def wait(self, timeout=None):
            self.returncode = 0
            return 0

    _FakePopenHangs.instances.clear()
    output = tmp_path / "out4" / "rendered.mp4"
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    monkeypatch.setattr(subprocess, "Popen", _FakePopenSucceeds)
    monkeypatch.setattr(VideoEditor, "get_media_info", staticmethod(lambda path: dict(FAKE_MEDIA_INFO)))
    monkeypatch.setattr(VideoEditor, "generate_poster_thumbnail", classmethod(lambda cls, *a, **k: None))

    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name("rendered.partial.mp4")
    _make_real_clip(partial, "720x1280", seconds=2.0)
    data = partial.read_bytes()
    partial.write_bytes(data[: len(data) // 2])

    with pytest.raises(RuntimeError):
        VideoEditor.assemble_tiktok_video(
            progress_callback=_noop_progress,
            **_common_kwargs(tmp_path, output),
        )
    assert not partial.exists()
    assert not output.exists()


def _make_real_clip(path, size, seconds=1.0):
    real_popen = _REAL_POPEN
    proc = real_popen([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=30:duration={seconds}",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(path),
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert proc.wait(timeout=120) == 0


def test_nvenc_open_failure_retries_on_libx264_inside_session_pool(tmp_path, monkeypatch):
    """S6-09: a final encode that cannot open an NVENC session is re-run on
    libx264 instead of failing the export, and NVENC runs hold the shared pool."""
    from scripts import media_validation

    codecs = []

    class _Lines:
        def __init__(self, lines):
            self._lines = list(lines)

        def readline(self):
            return self._lines.pop(0) if self._lines else ""

    class _FakeEncode(_FakePopenHangs):
        def __new__(cls, cmd, **kwargs):
            if "-filter_complex" not in cmd and not any("filter_complex_script" in str(c) for c in cmd):
                return _REAL_POPEN(cmd, **kwargs)
            return super().__new__(cls)

        def __init__(self, cmd, **kwargs):
            super().__init__(cmd, **kwargs)
            codec = cmd[cmd.index("-c:v") + 1]
            codecs.append(codec)
            if codec == "h264_nvenc":
                assert media_validation.NVENC_SESSIONS._value < media_validation.NVENC_MAX_SESSIONS
                self.stderr = _Lines(["[h264_nvenc @ 0x1] OpenEncodeSessionEx failed: out of memory (10)\n"])
                self._rc = 1
            else:
                _make_real_clip(Path(cmd[-1]), "720x1280")
                self._rc = 0

        def wait(self, timeout=None):
            self.returncode = self._rc
            return self._rc

    output = tmp_path / "out5" / "rendered.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OMNICUT_ENCODER", "h264_nvenc")
    monkeypatch.setattr(subprocess, "Popen", _FakeEncode)
    monkeypatch.setattr(VideoEditor, "get_media_info", staticmethod(lambda path: dict(FAKE_MEDIA_INFO)))
    monkeypatch.setattr(VideoEditor, "generate_poster_thumbnail", classmethod(lambda cls, *a, **k: None))

    result = VideoEditor.assemble_tiktok_video(progress_callback=_noop_progress, **_common_kwargs(tmp_path, output))
    assert codecs == ["h264_nvenc", "libx264"]
    assert Path(result) == output.resolve() and output.is_file()
