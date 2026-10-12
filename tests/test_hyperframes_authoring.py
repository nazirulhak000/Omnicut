from pathlib import Path
import os
import subprocess

import pytest

from scripts.hyperframes_authoring import (
    AuthoringError, CreativeJobStore, freeze_dependencies, validate_inputs,
    verify_snapshot,
)


def bundle(root, directory="work"):
    source = root / directory
    source.mkdir(parents=True)
    (source / "index.html").write_text('<link href="style.css" rel="stylesheet"><script src="main.js"></script><video src="clip.mp4"></video>', encoding="utf8")
    (source / "style.css").write_text('@font-face {font-family: local;src:url(font.woff2)}', encoding="utf8")
    (source / "main.js").write_text('import "./timing.js";', encoding="utf8")
    (source / "timing.js").write_text('export const duration=10;', encoding="utf8")
    (source / "timing.json").write_text('{"duration":10}', encoding="utf8")
    (source / "font.woff2").write_bytes(b"fixture font")
    (source / "clip.mp4").write_bytes(b"fixture media")
    return source


def inputs(mode="silent"):
    return {"audio_mode": mode, "duration_seconds": 10, "style_profile": {"id": "pov", "version": 1, "tokens": {"background": "#111"}}}


def test_real_audio_inputs(tmp_path):
    assert validate_inputs(tmp_path, inputs())["asset_hashes"] == {}
    with pytest.raises(AuthoringError, match="Narration"):
        validate_inputs(tmp_path, inputs("narration"))
    with pytest.raises(AuthoringError, match="Music-only"):
        validate_inputs(tmp_path, inputs("music_only"))
    (tmp_path / "voice.wav").write_bytes(b"real bytes")
    packet = inputs("narration") | {"voiceover_path": "voice.wav", "script": "Saved script"}
    one = validate_inputs(tmp_path, packet)
    (tmp_path / "voice.wav").write_bytes(b"changed bytes")
    assert validate_inputs(tmp_path, packet)["input_hash"] != one["input_hash"]
    with pytest.raises(AuthoringError):
        validate_inputs(tmp_path, packet | {"audio_mode": "silent"})


def test_media_refs_exact_hash_and_duplicates(tmp_path):
    (tmp_path / "clip.mp4").write_bytes(b"real media")
    packet = inputs() | {"media_refs": [{"path": "clip.mp4"}]}
    one = validate_inputs(tmp_path, packet)
    (tmp_path / "clip.mp4").write_bytes(b"updated media")
    assert one["input_hash"] != validate_inputs(tmp_path, packet)["input_hash"]
    with pytest.raises(AuthoringError, match="Duplicate"):
        validate_inputs(tmp_path, inputs() | {"media_refs": [{"path": "clip.mp4"}, {"path": "clip.mp4"}]})


def test_executable_data_url_cannot_hide_dependencies(tmp_path):
    source = tmp_path / "work"
    source.mkdir()
    (source / "index.html").write_text('<html><head></head><body><iframe src="data:text/html;base64,SGVsbG8="></iframe></body></html>', encoding="utf-8")
    with pytest.raises(AuthoringError, match="index.html"):
        freeze_dependencies(source, tmp_path / "revision")


def test_work_alias_is_rejected_before_prepare_can_touch_raw(tmp_path):
    store = CreativeJobStore(tmp_path)
    job = store.create("main", "project", 1, {"brief": "Saved"})
    claim = store.claim(job["id"], "main", "session", 0)
    raw = tmp_path / "01_Raw"
    raw.mkdir()
    original = raw / "index.html"
    original.write_text("protected original", encoding="utf-8")
    work = tmp_path / job["work_path"]
    work.parent.mkdir(parents=True)
    if os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(work), str(raw)], capture_output=True)
        if result.returncode:
            pytest.skip("Junction creation unavailable")
    else:
        work.symlink_to(raw, target_is_directory=True)
    touched = []
    try:
        with pytest.raises(AuthoringError) as error:
            store.submit(job["id"], "main", **{key: claim[key] for key in ("executor_id", "generation", "fence")}, current_revision=1, source_dir=work,
                         prepare_source=lambda source: (touched.append(source), (source / "index.html").write_text("modified", encoding="utf-8")))
        assert error.value.code == "work_path_alias"
        assert touched == []
        assert original.read_text(encoding="utf-8") == "protected original"
    finally:
        if os.name == "nt":
            os.rmdir(work)
        else:
            work.unlink()


@pytest.mark.parametrize("change", [{"style_profile": "pov"}, {"duration_seconds": 0}, {"duration_seconds": True}, {"audio_mode": "dummy"}, {"music_path": "../outside.wav"}])
def test_invalid_inputs(tmp_path, change):
    with pytest.raises(AuthoringError):
        validate_inputs(tmp_path, inputs() | change)


def test_snapshot_seals_entire_local_bundle(tmp_path):
    source = bundle(tmp_path)
    snapshot = freeze_dependencies(source, tmp_path / "revision")
    assert len(snapshot["files"]) == 7
    assert verify_snapshot(snapshot)
    (source / "timing.js").write_text("changed")
    assert verify_snapshot(snapshot)
    (tmp_path / "revision" / "style.css").write_text("changed")
    with pytest.raises(AuthoringError) as error:
        verify_snapshot(snapshot)
    assert error.value.code == "snapshot_modified"


@pytest.mark.parametrize("text", ['<script src="https://cdn.example/runtime.js"></script>', '<script src="missing.js"></script>', '<script>fetch("dynamic.json")</script>', '<script>import("./dynamic.js")</script>', '<script>video.src = userValue</script>', '<link href="../outside.css">'])
def test_reject_unfrozen_dependencies_before_writing(tmp_path, text):
    source = bundle(tmp_path)
    (source / "index.html").write_text(text)
    with pytest.raises(AuthoringError):
        freeze_dependencies(source, tmp_path / "revision")
    assert not (tmp_path / "revision").exists()


def test_snapshot_cannot_overwrite_or_add_files(tmp_path):
    source = bundle(tmp_path)
    snapshot = freeze_dependencies(source, tmp_path / "revision")
    with pytest.raises(AuthoringError) as error:
        freeze_dependencies(source, tmp_path / "revision")
    assert error.value.code == "snapshot_exists"
    (tmp_path / "revision" / "untracked.js").write_text("unexpected")
    with pytest.raises(AuthoringError):
        verify_snapshot(snapshot)


def test_restart_resume_fence_and_checkpoint(tmp_path):
    now = [1000]
    store = CreativeJobStore(tmp_path, clock=lambda: now[0])
    job = store.create("main", "project", 3, {"brief": "Make scene"}, expected_source_revision="source1")
    claim = store.claim(job["id"], "main", "session1", 0, lease_seconds=10)
    fence = {key: claim[key] for key in ("executor_id", "generation", "fence")}
    store.checkpoint(job["id"], "main", **fence, checkpoint={"next_action": "Finish scene 2"})
    restored = CreativeJobStore(tmp_path, clock=lambda: now[0])
    assert restored.get(job["id"], "main")["checkpoint"]["next_action"] == "Finish scene 2"
    with pytest.raises(AuthoringError) as error:
        restored.claim(job["id"], "main", "session2", 1)
    assert error.value.code == "lease_active"
    now[0] += 11
    next_claim = restored.claim(job["id"], "main", "session2", 1)
    assert next_claim["generation"] == 2
    with pytest.raises(AuthoringError) as error:
        store.heartbeat(job["id"], "main", **fence)
    assert error.value.code == "stale_executor"
    assert restored.get(job["id"], "main")["input_hash"] == job["input_hash"]
    with pytest.raises(AuthoringError):
        restored.get(job["id"], "second")


def test_submit_stale_revision_and_immutable_snapshot(tmp_path):
    store = CreativeJobStore(tmp_path)
    job = store.create("main", "project", 3, {"brief": "Make scene"}, expected_source_revision="source1")
    source = bundle(tmp_path, job["work_path"])
    claim = store.claim(job["id"], "main", "session1", 0)
    fence = {key: claim[key] for key in ("executor_id", "generation", "fence")}
    for revision, source_revision in ((4, "source1"), (3, "source2")):
        with pytest.raises(AuthoringError) as error:
            store.submit(job["id"], "main", **fence, current_revision=revision, current_source_revision=source_revision, source_dir=source)
        assert error.value.code == "stale_base_revision"
    assert not (tmp_path / "_HyperFrames_Studio" / "revisions").exists()
    submitted = store.submit(job["id"], "main", **fence, current_revision=3, current_source_revision="source1", source_dir=source)
    assert submitted["status"] == "submitted"
    snapshot = submitted["submitted_revision"]
    assert snapshot["channel_id"] == "main" and snapshot["base_revision"] == 3
    (source / "clip.mp4").write_bytes(b"changed media")
    assert verify_snapshot(snapshot)
    with pytest.raises(AuthoringError):
        store.submit(job["id"], "main", **fence, current_revision=3, current_source_revision="source1", source_dir=source)


def test_create_scope_conflict(tmp_path):
    store = CreativeJobStore(tmp_path)
    with pytest.raises(AuthoringError):
        store.create("main", "project", 1, {"channel_id": "second"})


def test_source_outside_root(tmp_path):
    store = CreativeJobStore(tmp_path / "app")
    job = store.create("main", "project", 1, {})
    claim = store.claim(job["id"], "main", "session", 0)
    with pytest.raises(AuthoringError):
        store.submit(job["id"], "main", **{key: claim[key] for key in ("executor_id", "generation", "fence")}, current_revision=1, source_dir=bundle(tmp_path))


def test_job_work_scope_and_handoff(tmp_path):
    store = CreativeJobStore(tmp_path)
    job = store.create("main", "project", 1, {"brief": "Saved brief"})
    handoff = store.handoff_packet(job["id"], "main")
    assert handoff["work_path"] == job["work_path"]
    assert handoff["input_hash"] == job["input_hash"]
    claim = store.claim(job["id"], "main", "session", 0)
    with pytest.raises(AuthoringError) as error:
        store.submit(job["id"], "main", **{key: claim[key] for key in ("executor_id", "generation", "fence")}, current_revision=1, source_dir=bundle(tmp_path))
    assert error.value.code == "work_path_invalid"


def test_reserved_snapshot_name(tmp_path):
    source = bundle(tmp_path)
    (source / "snapshot.json").write_text("{}")
    with pytest.raises(AuthoringError) as error:
        freeze_dependencies(source, tmp_path / "revision")
    assert error.value.code == "reserved_dependency"
