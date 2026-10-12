"""Durable HyperFrames rendering. Production registration is a separate commit.

The input is an accepted, closed dependency snapshot, never the editable Studio
HTML. SQLite holds the lifecycle; process handles are only cancellation helpers.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import uuid

from scripts.channel_store import ChannelError
from scripts.db import DocumentTable

_processes = {}
_process_lock = threading.Lock()


class _CLIStopError(RuntimeError):
    pass


def _stop_cli_process(process):
    """Stop only the process tree launched for this worker invocation."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            result = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                    capture_output=True, timeout=15,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, subprocess.TimeoutExpired) as error:
            raise _CLIStopError("could not verify that the job-owned renderer stopped") from error
        if result.returncode and process.poll() is None:
            raise _CLIStopError("could not stop the job-owned renderer process tree")
    else:
        import signal
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            # Successful taskkill /T already killed descendants; reap wrapper.
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired as error:
            raise _CLIStopError("renderer has not stopped; cancellation requires recovery") from error


def _process_identity(pid):
    """Read a process creation marker; never send Windows process signals.

    Unknown/access-denied markers are conservative: liveness still prevents
    recovery, but an accessible marker can detect a recycled PID after restart.
    """
    if not isinstance(pid, int) or pid <= 0:
        return None
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME),
                                          ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME),
                                          ctypes.POINTER(wintypes.FILETIME)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            created, exited, system, user = (wintypes.FILETIME() for _ in range(4))
            if kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(system), ctypes.byref(user)):
                return str((created.dwHighDateTime << 32) | created.dwLowDateTime)
        finally:
            kernel.CloseHandle(handle)
        return None
    try:
        # Linux /proc's creation ticks remain stable while the PID is alive.
        return Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split()[19]
    except (OSError, IndexError):
        return None


def _executor_alive(row):
    from scripts.maintenance_lock import _pid_alive
    pid = row.get("executor_pid")
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5
        try:
            code = wintypes.DWORD()
            if kernel.GetExitCodeProcess(handle, ctypes.byref(code)) and code.value != 259:
                return False
        finally:
            kernel.CloseHandle(handle)
    elif not _pid_alive(pid):
        return False
    expected = row.get("executor_creation")
    current = _process_identity(pid)
    return not expected or not current or expected == current


def _now():
    return datetime.now(timezone.utc).isoformat()


def _hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_video(path):
    command = [shutil.which("ffprobe") or "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise ChannelError(422, "hyperframes_video_invalid", "ตรวจไฟล์วิดีโอไม่ผ่าน")
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if not video:
        raise ChannelError(422, "hyperframes_video_invalid", "ไม่พบภาพในไฟล์วิดีโอ")
    rate = video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1"
    numerator, denominator = (float(number) for number in rate.split("/"))
    return {"width": video.get("width"), "height": video.get("height"),
            "fps": numerator / denominator if denominator else 0,
            "duration": float(data.get("format", {}).get("duration") or video.get("duration") or 0),
            "audio": any(stream.get("codec_type") == "audio" for stream in streams)}


def extract_thumbnail(video, destination, duration):
    seek = max(0, min(1.5, duration - 1 / 30))
    result = subprocess.run([shutil.which("ffmpeg") or "ffmpeg", "-y", "-v", "error", "-ss", str(seek),
                             "-i", str(video), "-frames:v", "1", str(destination)],
                            capture_output=True, text=True, timeout=30)
    if result.returncode or not destination.is_file() or not destination.stat().st_size:
        raise ValueError("thumbnail extraction failed")


class HyperFramesRenderJobs:
    def __init__(self, root, *, runner=None, probe=None, thumbnailer=None, cli_version="0.8.143"):
        self.root = Path(root).resolve()
        self.table = DocumentTable("hyperframes_render_jobs", lambda: self.root / "_Docs/store.db",
                                   lambda: self.root / "_Docs/hyperframes_render_jobs.json")
        self.runner = runner or self._run_sdk
        self.probe = probe or probe_video
        self.thumbnailer = thumbnailer or extract_thumbnail
        self.cli_version = cli_version

    def _path(self, relative):
        candidate = self.root / relative
        if ".." in candidate.parts or not candidate.is_relative_to(self.root):
            raise ChannelError(422, "hyperframes_path_invalid", "Managed render paths must remain inside the project")
        for component in (candidate, *candidate.parents):
            if component == self.root:
                break
            if component.is_symlink() or getattr(component, "is_junction", lambda: False)():
                raise ChannelError(422, "hyperframes_path_alias", "Managed render paths cannot contain symlinks or junctions")
        path = candidate.resolve()
        if not path.is_relative_to(self.root):
            raise ChannelError(422, "hyperframes_path_invalid", "ไฟล์งานอยู่นอกพื้นที่โปรเจกต์")
        return path

    def get(self, channel_id, job_id):
        record = next((row for row in self.table.scoped_load(channel_id) if row["id"] == job_id), None)
        if record is None:
            raise ChannelError(404, "hyperframes_job_not_found", "ไม่พบงานเรนเดอร์ของช่องนี้")
        return deepcopy(record)

    def list(self, channel_id, project_id=None):
        return [deepcopy(row) for row in self.table.scoped_load(channel_id)
                if project_id is None or row["project_id"] == project_id]

    def _verify(self, snapshot):
        directory = self._path(snapshot["revision_path"])
        from scripts.hyperframes_authoring import verify_snapshot
        verify_snapshot({**snapshot, "revision_dir": str(directory)})
        for file in snapshot["files"]:
            path = self._path(directory / file["path"])
            if not path.is_relative_to(directory) or not path.is_file() or _hash(path) != file["sha256"]:
                raise ChannelError(409, "hyperframes_snapshot_changed", "ไฟล์ revision เปลี่ยนหรือหาย ต้องส่ง revision ใหม่")
        entry = self._path(directory / snapshot["entrypoint"])
        if not entry.is_relative_to(directory) or not entry.is_file():
            raise ChannelError(422, "hyperframes_entry_invalid", "ไม่พบ composition ใน revision")
        return directory, entry

    def create(self, channel_id, project, snapshot, *, idempotency_key, source_angle_snapshot=None, source_product_snapshot=None, asset_contract=None):
        if project.get("channel_id") != channel_id or snapshot.get("channel_id") != channel_id:
            raise ChannelError(422, "channel_scope_conflict", "ช่องของงานไม่ตรงกัน")
        if snapshot.get("project_id") != project["project_id"]:
            raise ChannelError(422, "hyperframes_parent_conflict", "revision ไม่ใช่ของโปรเจกต์นี้")
        if project["source_binding"].get("type") == "product_angle" and not isinstance(source_angle_snapshot, dict):
            raise ChannelError(422, "hyperframes_source_revision_missing", "ต้องตรึง Angle ก่อนเริ่มเรนเดอร์")
        revision_reference = snapshot.get("revision_dir") or snapshot.get("snapshot_path") or snapshot.get("revision_path")
        if not revision_reference:
            raise ChannelError(422, "hyperframes_revision_path_missing", "Accepted revision has no managed path")
        revision_dir = self._path(str(revision_reference))
        if revision_dir.is_file():
            revision_dir = revision_dir.parent
        if not revision_dir.is_relative_to(self.root):
            raise ChannelError(422, "hyperframes_path_invalid", "revision อยู่นอกพื้นที่โปรเจกต์")
        frozen = {"revision_path": revision_dir.relative_to(self.root).as_posix(),
                  "entrypoint": snapshot["entrypoint"], "files": deepcopy(snapshot["files"]),
                  "dependency_hash": snapshot["dependency_hash"], "id": snapshot["id"],
                  "asset_hashes": deepcopy(snapshot.get("asset_hashes") or {})}
        self._verify(frozen)
        if not idempotency_key or len(idempotency_key) > 200:
            raise ChannelError(422, "hyperframes_idempotency_invalid", "ต้องระบุรหัสคำขอที่ถูกต้อง")
        inputs = deepcopy(project.get("inputs") or {})
        pinned = {"project_id": project["project_id"], "project_name": project["project_name"],
                  "project_revision": project["revision"], "channel_id": channel_id,
                  "source_binding": deepcopy(project["source_binding"]),
                  "channel_identity_snapshot": deepcopy(project.get("channel_identity_snapshot") or project.get("channel_identity")),
                  "inputs": inputs, "snapshot": frozen, "cli_version": self.cli_version}
        pinned["source_angle_snapshot"] = deepcopy(source_angle_snapshot)
        pinned["source_product_snapshot"] = deepcopy(source_product_snapshot)
        if asset_contract is None:
            required = []
            keys = [("voiceover", "voiceover_path")] if inputs.get("audio_mode", "narration") == "narration" else []
            if inputs.get("audio_mode") == "music_only" or (inputs.get("audio_mode", "narration") == "narration" and inputs.get("music_path")):
                keys.append(("music", "music_path"))
            for role, key in keys:
                if inputs.get(key):
                    accepted_hash = frozen["asset_hashes"].get(key)
                    if not accepted_hash:
                        source = self._path(inputs[key])
                        if not source.is_file():
                            raise ChannelError(422, "hyperframes_audio_asset_missing", "Required saved audio asset is missing")
                        accepted_hash = _hash(source)
                    required.append({"role": role, "sha256": accepted_hash})
            asset_contract = {"required_audio": required}
        pinned["asset_contract"] = deepcopy(asset_contract)
        input_hash = hashlib.sha256(json.dumps(pinned, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self.table.mutate() as rows:
            existing = next((row for row in rows if row.get("channel_id") == channel_id and row.get("idempotency_key") == idempotency_key), None)
            if existing:
                if existing["input_hash"] != input_hash:
                    raise ChannelError(409, "hyperframes_request_conflict", "รหัสคำขอนี้ใช้กับ input คนละรุ่น")
                return deepcopy(existing)
            row = {"id": "hfr_" + uuid.uuid4().hex, **pinned, "input_hash": input_hash,
                   "idempotency_key": idempotency_key, "status": "queued", "phase": "queued",
                   "attempt": 0, "revision": 1, "cancel_requested": False,
                   "created_at": _now(), "updated_at": _now(), "error": None,
                   "artifact": None, "export_id": None, "finalize_intent": None}
            rows.append(row)
            return deepcopy(row)

    def _change(self, channel_id, job_id, mutation):
        with self.table.mutate() as rows:
            row = next((item for item in rows if item.get("channel_id") == channel_id and item["id"] == job_id), None)
            if row is None:
                raise ChannelError(404, "hyperframes_job_not_found", "ไม่พบงานเรนเดอร์")
            mutation(row)
            row["revision"] += 1
            row["updated_at"] = _now()
            return deepcopy(row)

    def execute(self, channel_id, job_id):
        token = uuid.uuid4().hex
        def start(row):
            if row["status"] != "queued":
                raise ChannelError(409, "hyperframes_job_state", "งานนี้ไม่ได้รอเรนเดอร์")
            row.update(status="rendering", phase="validating_snapshot", attempt=row["attempt"] + 1,
                       executor_token=token, executor_pid=os.getpid(), executor_creation=_process_identity(os.getpid()),
                       cancel_requested=False, error=None)
        job = self._change(channel_id, job_id, start)
        try:
            directory = self._path(f".tmp/hyperframes/render/{job_id}/{job['attempt']}")
            directory.mkdir(parents=True, exist_ok=True)
            target = directory / "video.mp4"
            revision_dir, entry = self._verify(job["snapshot"])
            work = directory / "composition"
            work.mkdir()
            for file in job["snapshot"]["files"]:
                destination = work / file["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(revision_dir / file["path"], destination)
                if _hash(destination) != file["sha256"]:
                    raise ChannelError(409, "hyperframes_snapshot_changed", "Dependency changed during staging")
            self.runner(job, work, work / job["snapshot"]["entrypoint"], target)
            if self.get(channel_id, job_id)["cancel_requested"]:
                raise InterruptedError("render cancelled")
            if not target.is_file() or target.stat().st_size == 0:
                raise ValueError("renderer did not produce a video")
            specs = self.probe(target)
            if (specs["width"] != 1080 or specs["height"] != 1920
                    or not math.isfinite(specs["fps"]) or not math.isfinite(specs["duration"])
                    or abs(specs["fps"] - 30) > 0.01 or specs["duration"] <= 0):
                raise ValueError("video must be 1080x1920, 30 FPS, with positive duration")
            mode = job["inputs"].get("audio_mode", "narration")
            if mode != "silent" and not specs.get("audio"):
                raise ValueError("declared audio is missing")
            expected = job["inputs"].get("duration_seconds") or job["inputs"].get("total_duration")
            if expected and abs(specs["duration"] - float(expected)) > max(0.15, 2 / 30):
                raise ValueError("video duration differs from the accepted brief")
            self._verify(job["snapshot"])
            thumbnail = directory / "thumbnail.webp"
            self.thumbnailer(target, thumbnail, specs["duration"])
            if not thumbnail.is_file() or not thumbnail.stat().st_size:
                raise ValueError("thumbnail is missing")
            artifact = {"path": target.relative_to(self.root).as_posix(), "sha256": _hash(target),
                        "size_bytes": target.stat().st_size, "specs": specs,
                        "composition_revision": job["snapshot"]["id"], "input_hash": job["input_hash"]}
            artifact.update(thumbnail_path=thumbnail.relative_to(self.root).as_posix(), thumbnail_sha256=_hash(thumbnail))
            def finish(row):
                if row.get("executor_token") != token or row.get("cancel_requested"):
                    raise InterruptedError("render superseded or cancelled")
                row.update(status="qc_ready", phase="awaiting_final_review", artifact=artifact)
            return self._change(channel_id, job_id, finish)
        except Exception as error:
            def fail(row):
                if row.get("executor_token") == token:
                    status = "interrupted" if isinstance(error, _CLIStopError) else "cancelled" if row.get("cancel_requested") else "failed"
                    row.update(status=status, phase=status, error=str(error)[-1500:], error_code=getattr(error, "code", None),
                               executor_stop_unconfirmed=isinstance(error, _CLIStopError))
            self._change(channel_id, job_id, fail)
            return self.get(channel_id, job_id)

    def queue_retry(self, channel_id, job_id):
        def retry(row):
            if row["status"] not in {"failed", "interrupted"} or row.get("finalize_intent"):
                raise ChannelError(409, "hyperframes_retry_state", "Only failed or interrupted renders can be retried")
            with _process_lock:
                handle = _processes.get((str(self.root), job_id))
                if handle is not None and handle.poll() is None:
                    raise ChannelError(409, "hyperframes_worker_active", "The prior renderer is still running")
            if row["status"] == "interrupted" and _executor_alive(row):
                raise ChannelError(409, "hyperframes_worker_active", "The interrupted executor is still alive; verify it stopped before retry")
            row.update(status="queued", phase="queued", cancel_requested=False, error=None, error_code=None,
                       executor_stop_unconfirmed=False, artifact=None)
            for field in ("executor_token", "executor_pid", "executor_creation"):
                row.pop(field, None)
        return self._change(channel_id, job_id, retry)

    def cancel(self, channel_id, job_id):
        def cancel(row):
            if row["status"] in {"finalizing", "finalized", "recovery_required"}:
                raise ChannelError(409, "hyperframes_finalize_active", "งานกำลังส่งออก ต้องตรวจผลก่อนยกเลิก")
            row["cancel_requested"] = True
            if row["status"] != "rendering":
                row.update(status="cancelled", phase="cancelled")
        row = self._change(channel_id, job_id, cancel)
        return row

    def recover_interrupted(self, channel_id, *, alive=None):
        recovered = []
        with self.table.mutate() as rows:
            for row in rows:
                if row.get("channel_id") != channel_id or row["status"] != "rendering":
                    continue
                living = alive(row.get("executor_pid")) if alive else _executor_alive(row)
                if not living:
                    row.update(status="interrupted", phase="interrupted", error="worker stopped; retry the immutable revision",
                               revision=row["revision"] + 1, updated_at=_now())
                    recovered.append(row["id"])
        return recovered

    def _run_sdk(self, job, revision_dir, entry, target):
        if entry != revision_dir / "index.html":
            raise ChannelError(422, "hyperframes_check_entry_unsupported",
                               "Submit a canonical root index.html entrypoint")
        if job.get("cli_version", "0.8.143") != "0.8.143":
            raise ChannelError(422, "hyperframes_runtime_version_unsupported", "This guarded worker supports the pinned SDK 0.8.143 only")
        node = shutil.which("node")
        worker = Path(__file__).resolve().parents[1] / "tools" / "hyperframes_render_worker.mjs"
        runtime = worker.parent / "hyperframes-runtime" / "node_modules" / "@hyperframes" / "engine"
        if not node or not runtime.is_dir():
            raise RuntimeError("Guarded HyperFrames SDK runtime is unavailable; install the pinned tools/hyperframes-runtime lockfile")
        spec = {"project_dir": str(revision_dir), "output_path": str(target),
                "entrypoint": entry.relative_to(revision_dir).as_posix(), "files": job["snapshot"]["files"],
                "asset_contract": job.get("asset_contract") or {},
                "duration_seconds": job["inputs"].get("duration_seconds") or job["inputs"].get("total_duration"),
                "audio_mode": job["inputs"].get("audio_mode", "narration")}
        request = target.parent / "worker-input.json"
        request.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        log = target.parent / "render.log"
        commands = [[node, str(worker), str(request)]]
        with log.open("w", encoding="utf-8") as output:
            for command in commands:
                current = self.get(job["channel_id"], job["id"])
                if current.get("cancel_requested") or current.get("executor_token") != job["executor_token"]:
                    raise InterruptedError("render superseded or cancelled")
                started = time.monotonic()
                process = subprocess.Popen(command, cwd=revision_dir, stdout=output, stderr=subprocess.STDOUT,
                                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                                           start_new_session=os.name != "nt")
                key = (str(self.root), job["id"])
                with _process_lock:
                    _processes[key] = process
                try:
                    while process.poll() is None:
                        if self.get(job["channel_id"], job["id"])["cancel_requested"] or time.monotonic() - started > 600:
                            _stop_cli_process(process)
                            raise RuntimeError("render cancelled or timed out")
                        time.sleep(0.2)
                    if process.returncode:
                        audit_path = target.parent / "network-audit.json"
                        if audit_path.is_file():
                            audit = json.loads(audit_path.read_text(encoding="utf-8"))
                            if audit.get("blocked"):
                                raise ChannelError(422, "hyperframes_network_blocked", "Composition attempted prohibited network/execution; vendor dependencies and submit a new revision")
                            if audit.get("error_code"):
                                raise ChannelError(422, audit["error_code"], audit.get("error_message") or "Guarded render validation failed")
                        raise RuntimeError(f"Guarded HyperFrames worker failed ({process.returncode}); see the job log")
                finally:
                    try:
                        # A database/check failure must also stop spawned tools.
                        _stop_cli_process(process)
                    finally:
                        with _process_lock:
                            _processes.pop(key, None)

    # Older integrations used this name. Never execute an unguarded CLI check.
    _run_cli = _run_sdk
