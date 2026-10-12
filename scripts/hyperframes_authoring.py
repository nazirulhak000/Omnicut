"""Durable external-session authoring. No default root or import-time writes.

Submission seals a local dependency snapshot; accepting it into a project is a
separate project CAS operation. This module never executes submitted code.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import secrets
import time
import uuid
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from scripts.db import DocumentTable


class AuthoringError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _fail(code, message):
    raise AuthoringError(code, message)


def _json(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _inside(root, path):
    root = Path(root).resolve()
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(root):
        _fail("path_outside_root", "Dependency must remain inside its explicit root")
    return resolved


def managed_work_path(root, relative):
    """Reject aliases before resolving: an in-root junction is still an escape."""
    root = Path(root).resolve()
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts or relative.parts[:3] != ("03_Projects", "_HyperFrames_Studio", "work"):
        _fail("work_path_invalid", "Work must use the managed Studio work directory")
    candidate = root / relative
    for path in (candidate, *candidate.parents):
        if path == root:
            break
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            _fail("work_path_alias", "Work directories cannot contain symlinks or junctions")
    _inside(root / "03_Projects/_HyperFrames_Studio/work", candidate)
    return candidate


def validate_inputs(root, inputs):
    """Validate real audio/style inputs. Assets are paths relative to explicit root."""
    inputs = _json(inputs)
    if not isinstance(inputs, dict):
        _fail("inputs_invalid", "Inputs must be a JSON object")
    mode = inputs.get("audio_mode")
    if mode not in {"narration", "music_only", "silent"}:
        _fail("audio_mode_required", "Choose narration, music_only or silent")
    profile = inputs.get("style_profile")
    if not isinstance(profile, dict) or not profile.get("id") or not profile.get("version") or not isinstance(profile.get("tokens"), dict) or not profile["tokens"]:
        _fail("style_profile_required", "An actual versioned style token profile is required")
    hashes = {}
    for key in ("voiceover_path", "music_path"):
        value = inputs.get(key)
        if value:
            if Path(value).is_absolute():
                _fail("asset_path_invalid", "Audio paths must be relative")
            path = _inside(root, Path(root) / value)
            if not path.is_file() or path.stat().st_size == 0:
                _fail("audio_asset_missing", key)
            hashes[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    references = inputs.get("media_refs", [])
    if not isinstance(references, list):
        _fail("media_refs_invalid", "Media references must be an array")
    seen = set()
    for reference in references:
        if not isinstance(reference, dict) or not isinstance(reference.get("path"), str):
            _fail("media_refs_invalid", "Each media reference needs a local path")
        value = reference["path"]
        if Path(value).is_absolute() or urlsplit(value).scheme or ".." in Path(value).parts:
            _fail("asset_path_invalid", "Media paths must be local and relative")
        path = _inside(root, Path(root) / value)
        if path in seen:
            _fail("media_duplicate", "Duplicate media reference")
        seen.add(path)
        if not path.is_file() or not path.stat().st_size:
            _fail("media_asset_missing", value)
        hashes["media:" + value] = hashlib.sha256(path.read_bytes()).hexdigest()
    if mode == "narration" and (not inputs.get("voiceover_path") or not str(inputs.get("script", "")).strip()):
        _fail("narration_required", "Narration requires a saved script and real voiceover")
    if mode == "music_only" and not inputs.get("music_path"):
        _fail("music_required", "Music-only requires a real music asset")
    if mode != "narration" and inputs.get("voiceover_path"):
        _fail("audio_mode_conflict", "No-voice modes cannot carry a voiceover")
    duration = inputs.get("duration_seconds")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        _fail("duration_required", "Explicit positive duration is required")
    return {"inputs": inputs, "asset_hashes": hashes, "input_hash": _hash({"inputs": inputs, "asset_hashes": hashes})}


class _References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("srcdoc"):
            _fail("unresolved_dependency", "Nested inline documents are unsupported")
        for key in ("src", "href", "poster", "data-src"):
            if values.get(key):
                self.refs.append(values[key])
        if values.get("srcset"):
            self.refs.extend(part.strip().split()[0] for part in values["srcset"].split(",") if part.strip())
        if tag == "base":
            _fail("unresolved_dependency", "HTML base URLs are unsupported")


_SUFFIXES = {".html", ".css", ".js", ".mjs", ".json", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".mp4", ".webm", ".wav", ".mp3", ".ogg", ".m4a", ".woff", ".woff2", ".ttf", ".otf"}


def freeze_dependencies(source_dir, destination, entrypoint="index.html"):
    """Seal a self-contained local bundle, rejecting network/dynamic resolution.

    Copy every supported local file, including timing JSON and fonts. Static
    references are checked before writing. Network/runtime loaders must first
    be vendored by the trusted app, never fetched by this function.
    """
    source = Path(source_dir).resolve()
    destination = Path(destination).resolve()
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        _fail("snapshot_overlap", "Snapshot and editable source must be separate")
    if destination.exists():
        _fail("snapshot_exists", "Immutable snapshots cannot be overwritten")
    if Path(entrypoint).is_absolute():
        _fail("entrypoint_invalid", "Entrypoint must be relative")
    entry = _inside(source, source / entrypoint)
    if not entry.is_file() or entry.suffix != ".html":
        _fail("entrypoint_missing", "A local HTML entrypoint is required")
    payloads = {}
    for path in source.rglob("*"):
        if path.is_symlink():
            _fail("symlink_dependency", "Symlinks cannot be sealed")
        if not path.is_file():
            continue
        path = _inside(source, path)
        if path.relative_to(source).as_posix() == "snapshot.json":
            _fail("reserved_dependency", "snapshot.json is reserved for the sealed manifest")
        if path.suffix.lower() not in _SUFFIXES:
            _fail("unsupported_dependency", str(path.relative_to(source)))
        payloads[path.relative_to(source).as_posix()] = path.read_bytes()
    for name, raw in payloads.items():
        suffix = Path(name).suffix.lower()
        if suffix not in {".html", ".css", ".js", ".mjs", ".json", ".svg"}:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            _fail("dependency_encoding", name)
        # All execution-bearing text is offline. Even JSON timing/media ledgers
        # may contain runtime references, so reject remote URLs there too.
        if re.search(r"(?:https?:|file:|wss?:|//[\w.-]+/)", text, re.I):
            _fail("network_dependency", name)
        if re.search(r"data:\s*(?:text/(?:html|javascript)|application/(?:javascript|x-javascript|wasm))", text, re.I):
            _fail("executable_data_dependency", name)
        if suffix in {".html", ".js", ".mjs"} and re.search(r"\b(?:fetch|eval|importScripts)\s*\(|\bimport\s*\(|\bnew\s+(?:Worker|XMLHttpRequest|WebSocket)|\.\s*(?:src|href)\s*=|setAttribute\s*\(\s*['\"](?:src|href)|\bimport\s*\{?[^;\n]*\bfrom\s*[^'\"]", text):
            _fail("unresolved_dependency", name)
        refs = []
        if suffix in {".html", ".svg"}:
            parser = _References()
            parser.feed(text)
            refs.extend(parser.refs)
        refs.extend(re.findall(r"url\(\s*['\"]?([^)'\"\s]+)", text))
        refs.extend(re.findall(r"@import\s+['\"]([^'\"]+)", text))
        if suffix in {".js", ".mjs", ".html"}:
            refs.extend(re.findall(r"\b(?:import|export)\s+(?:[^;\n]*?\s+from\s+)?['\"]([^'\"]+)['\"]", text))
        for ref in refs:
            if ref.startswith(("#", "data:")):
                continue
            parsed = urlsplit(ref)
            if parsed.scheme or parsed.netloc or ref.startswith("/"):
                _fail("network_dependency", ref)
            target = _inside(source, source / Path(name).parent / unquote(parsed.path))
            if not target.is_file() or target.relative_to(source).as_posix() not in payloads:
                _fail("missing_dependency", ref)
    files = [{"path": name, "sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)} for name, raw in sorted(payloads.items())]
    snapshot = {"schema_version": 1, "revision_dir": str(destination), "snapshot_path": str(destination), "entrypoint": entry.relative_to(source).as_posix(), "entry_path": str(destination / entry.relative_to(source)), "files": files, "dependency_hash": _hash(files)}
    destination.mkdir(parents=True)
    for name, raw in payloads.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (destination / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot


def verify_snapshot(snapshot):
    root = Path(snapshot["revision_dir"]).resolve()
    files = snapshot["files"]
    if _hash(files) != snapshot["dependency_hash"]:
        _fail("snapshot_modified", "Manifest hash differs")
    expected = {item["path"] for item in files} | {"snapshot.json"}
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual != expected:
        _fail("snapshot_modified", "Dependency set differs")
    for item in files:
        original = root / item["path"]
        path = _inside(root, original)
        if any(part.is_symlink() for part in [original, *original.parents] if part != root and part.is_relative_to(root)) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            _fail("snapshot_modified", item["path"])
    return True


class CreativeJobStore:
    def __init__(self, root, *, clock=time.time):
        self.root = Path(root).resolve()
        self.clock = clock
        self.table = DocumentTable("creative_jobs", lambda: self.root / "_Docs" / "store.db", lambda: self.root / "_Docs" / "creative_jobs.json")

    def _local_row(self, row):
        """Rehydrate sealed pointers from this root, never follow old root hints.

        Legacy absolute pointers are accepted only as one consistent managed
        revision identity. New durable rows store only the relative identity.
        This read does not rewrite the database, mirror, or archived hashes.
        """
        result = copy.deepcopy(row)
        snapshot = result.get("submitted_revision")
        if snapshot is None:
            return result
        if not isinstance(snapshot, dict) or snapshot.get("project_id") != row.get("project_id") or snapshot.get("channel_id") != row.get("channel_id") or snapshot.get("base_revision") != row.get("base_revision"):
            _fail("snapshot_scope_invalid", "Submitted revision differs from its job owner, project or base revision")
        revision_id = snapshot.get("id")
        if not isinstance(revision_id, str) or not re.fullmatch(r"hf_revision_[0-9a-f]{32}", revision_id):
            _fail("snapshot_path_invalid", "Submitted revision requires its exact managed identity")
        relative = f"03_Projects/_HyperFrames_Studio/revisions/{revision_id}"
        if snapshot.get("revision_relative_path") != relative:
            _fail("snapshot_path_invalid", "Submitted revision relative path differs from its identity")
        entrypoint = snapshot.get("entrypoint")
        if not isinstance(entrypoint, str) or not entrypoint or Path(entrypoint).is_absolute() or ".." in Path(entrypoint).parts or urlsplit(entrypoint).scheme:
            _fail("snapshot_path_invalid", "Submitted entrypoint must be a frozen local path")
        files = snapshot.get("files")
        if not isinstance(files, list) or not files or not all(isinstance(item, dict) and isinstance(item.get("path"), str) and item["path"] for item in files):
            _fail("snapshot_path_invalid", "Submitted frozen dependency list is malformed")
        if entrypoint not in {item["path"] for item in files}:
            _fail("snapshot_path_invalid", "Submitted entrypoint is absent from its frozen dependency set")
        pointers = ("revision_dir", "snapshot_path", "entry_path")
        if any(key in snapshot for key in pointers):
            if not all(isinstance(snapshot.get(key), str) and snapshot[key] for key in pointers):
                _fail("snapshot_path_invalid", "Legacy submitted pointers must have one consistent revision identity")
            old_directory = Path(snapshot["revision_dir"])
            if not old_directory.is_absolute() or ".." in old_directory.parts or old_directory.parts[-4:] != Path(relative).parts:
                _fail("snapshot_path_invalid", "Legacy submitted pointer is outside the managed revision namespace")
            for key, expected in (("snapshot_path", old_directory / "snapshot.json"), ("entry_path", old_directory / entrypoint)):
                valid = Path(snapshot[key]) == expected or (key == "snapshot_path" and Path(snapshot[key]) == old_directory)
                if not valid or ".." in Path(snapshot[key]).parts:
                    _fail("snapshot_path_invalid", "Legacy submitted pointers disagree with the exact recorded revision")
        directory = self.root / relative
        for parent in (directory, *directory.parents):
            if parent == self.root:
                break
            if parent.is_symlink() or getattr(parent, "is_junction", lambda: False)():
                _fail("snapshot_path_alias", "Submitted revision directories cannot use path aliases")
        _inside(self.root / "03_Projects/_HyperFrames_Studio/revisions", directory)
        snapshot.update(revision_dir=str(directory), snapshot_path=str(directory / "snapshot.json"), entry_path=str(directory / entrypoint))
        return result

    def get(self, job_id, channel_id):
        for row in self.table.scoped_load(channel_id):
            if row["id"] == job_id:
                return self._local_row(row)
        _fail("job_not_found", "No job in this channel")

    def list(self, channel_id):
        return [self._local_row(row) for row in self.table.scoped_load(channel_id)]

    def create(self, channel_id, project_id, expected_revision, input_packet, *, expected_source_revision=None):
        if not channel_id or not project_id or isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            _fail("job_scope_invalid", "Owner, project and base revision are required")
        packet = _json(input_packet)
        if not isinstance(packet, dict):
            _fail("packet_invalid", "Handoff inputs must be a JSON object")
        if any(packet.get(key) not in (None, value) for key, value in (("channel_id", channel_id), ("project_id", project_id))):
            _fail("job_scope_invalid", "Packet scope differs")
        row = {"id": "creative_" + uuid.uuid4().hex, "channel_id": channel_id, "project_id": project_id, "base_revision": expected_revision, "source_revision": expected_source_revision, "input_packet": packet, "input_hash": _hash(packet), "status": "queued", "generation": 0, "created_at": self.clock(), "updated_at": self.clock(), "checkpoint": None}
        row["work_path"] = "03_Projects/_HyperFrames_Studio/work/" + row["id"]
        with self.table.scoped_mutate(channel_id) as rows:
            rows.append(row)
        return copy.deepcopy(row)

    def handoff_packet(self, job_id, channel_id):
        row = self.get(job_id, channel_id)
        return {
            "schema_version": 1, "work_id": row["id"],
            "channel_id": channel_id, "project_id": row["project_id"],
            "base_revision": row["base_revision"], "source_revision": row["source_revision"],
            "input_hash": row["input_hash"], "inputs": row["input_packet"],
            "work_path": row["work_path"], "generation": row["generation"],
            "checkpoint": row["checkpoint"],
            "next_action": (row["checkpoint"] or {}).get("next_action", "Claim this work, then author a self-contained local composition"),
            "constraints": ["Write only inside work_path", "Use the app claim/heartbeat/checkpoint/submit API", "Do not write stores, alter owner, execute generated Python or publish", "Vendor dependencies before submitting; network and dynamic loaders are unsupported"],
        }

    def _row(self, rows, job_id):
        for row in rows:
            if row["id"] == job_id:
                return row
        _fail("job_not_found", "No job in this channel")

    def claim(self, job_id, channel_id, executor_id, expected_generation, *, lease_seconds=300):
        if not executor_id or not 1 <= lease_seconds <= 3600:
            _fail("lease_invalid", "Executor and bounded lease required")
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._row(rows, job_id)
            if row["generation"] != expected_generation or row["status"] == "submitted":
                _fail("stale_generation", "Claim generation is stale")
            if row["status"] == "authoring" and row["lease_expires_at"] > self.clock():
                _fail("lease_active", "Another session owns this job")
            row.update(status="authoring", generation=row["generation"] + 1, executor_id=executor_id, fence=secrets.token_hex(24), lease_expires_at=self.clock() + lease_seconds, updated_at=self.clock())
            result = copy.deepcopy(row)
        return result

    def _fenced(self, row, executor_id, generation, fence):
        if row["status"] != "authoring" or row.get("executor_id") != executor_id or row["generation"] != generation or row.get("fence") != fence or row["lease_expires_at"] <= self.clock():
            _fail("stale_executor", "Session fence or lease is stale")

    def heartbeat(self, job_id, channel_id, *, executor_id, generation, fence, lease_seconds=300):
        if not 1 <= lease_seconds <= 3600:
            _fail("lease_invalid", "Lease must be bounded")
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._row(rows, job_id)
            self._fenced(row, executor_id, generation, fence)
            row.update(lease_expires_at=self.clock() + lease_seconds, updated_at=self.clock())
            result = copy.deepcopy(row)
        return result

    def checkpoint(self, job_id, channel_id, *, executor_id, generation, fence, checkpoint):
        checkpoint = _json(checkpoint)
        if not isinstance(checkpoint, dict) or not checkpoint.get("next_action"):
            _fail("checkpoint_invalid", "Checkpoint requires next_action")
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._row(rows, job_id)
            self._fenced(row, executor_id, generation, fence)
            row.update(checkpoint=checkpoint, updated_at=self.clock())
            result = copy.deepcopy(row)
        return result

    def submit(self, job_id, channel_id, *, executor_id, generation, fence, current_revision, source_dir, entrypoint="index.html", current_source_revision=None, prepare_source=None):
        source_path = Path(source_dir)
        lexical_source = source_path if source_path.is_absolute() else self.root / source_path
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._row(rows, job_id)
            self._fenced(row, executor_id, generation, fence)
            managed = managed_work_path(self.root, row["work_path"])
            if lexical_source != managed:
                _fail("work_path_invalid", "Submission must use its exact managed work directory")
            source = managed.resolve()
            if row["base_revision"] != current_revision or row["source_revision"] != current_source_revision:
                _fail("stale_base_revision", "Saved project or source changed during authoring")
            if prepare_source is not None:
                prepare_source(source)
            revision_id = "hf_revision_" + uuid.uuid4().hex
            destination = self.root / "03_Projects/_HyperFrames_Studio" / "revisions" / revision_id
            for parent in (destination, *destination.parents):
                if parent == self.root:
                    break
                if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
                    _fail("snapshot_path_alias", "Revision store cannot use path aliases")
            snapshot = freeze_dependencies(source, destination, entrypoint)
            self._fenced(row, executor_id, generation, fence)
            snapshot.update(id=revision_id, project_id=row["project_id"], channel_id=channel_id, base_revision=row["base_revision"], input_hash=row["input_hash"])
            snapshot["revision_relative_path"] = destination.relative_to(self.root).as_posix()
            for key in ("revision_dir", "snapshot_path", "entry_path"):
                snapshot.pop(key, None)
            row.update(status="submitted", submitted_revision=snapshot, updated_at=self.clock(), lease_expires_at=self.clock())
            result = self._local_row(row)
        return result
