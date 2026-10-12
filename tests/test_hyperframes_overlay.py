from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.channel_store import ChannelError
from scripts.hyperframes_overlay import HyperFramesOverlay, _sha


@pytest.fixture(autouse=True)
def cleanup_owned_overlay_test_storage(tmp_path, tmp_path_factory):
    yield
    root, base = tmp_path.resolve(), tmp_path_factory.getbasetemp().resolve()
    assert root.parent == base and root.name.startswith("test_")
    from scripts import db
    connections = getattr(db._local, "conns", {})
    for key, connection in tuple(connections.items()):
        if Path(key).is_relative_to(root):
            connection.close()
            del connections[key]
    import gc
    gc.collect()
    if root.exists():
        shutil.rmtree(root)


def fixture(root, *, audio=True):
    media = root / "03_Projects/main/Gadget_example/master.mp4"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"approved-master")
    row = dict(approved=True, channel_id="main", project_id="gadget_example", artifact_id="master_one",
               revision="revision_one", path=media.relative_to(root).as_posix(), sha256=_sha(media))
    specs = dict(width=1080, height=1920, fps=30, duration=1, audio=audio)
    service = HyperFramesOverlay(root, resolver=lambda c, b: deepcopy(row), probe=lambda p: deepcopy(specs))
    binding = {"type": "gadget_project", "project_id": "gadget_example"}
    return service, row, specs, binding


def freeze(service, binding):
    info = service.inspect("main", binding)
    return service.freeze("main", "03_Projects/main/HF_" + "a" * 32, binding,
                          approval={"approved": True, "master_digest": info["master_digest"]})


def test_approval_exact_revision_hash_and_owner(tmp_path):
    service, row, specs, binding = fixture(tmp_path)
    info = service.inspect("main", binding)
    row["revision"] = "revision_two"
    with pytest.raises(ChannelError, match="Explicit approval"):
        service.freeze("main", "03_Projects/main/HF_" + "a" * 32, binding,
                       approval={"approved": True, "master_digest": info["master_digest"]})
    with pytest.raises(ChannelError) as error:
        service.inspect("second", binding)
    assert error.value.status_code == 404
    assert not list(tmp_path.glob("03_Projects/main/HF_*/overlay_inputs"))


def test_no_implicit_approval_and_no_original_mutation(tmp_path):
    service, row, specs, binding = fixture(tmp_path)
    original = tmp_path / row["path"]
    before = original.read_bytes()
    for approval in ({}, {"approved": False}, {"approved": True, "master_digest": "bad"}):
        with pytest.raises(ChannelError):
            service.freeze("main", "03_Projects/main/HF_" + "a" * 32, binding, approval=approval)
    frozen = freeze(service, binding)
    assert original.read_bytes() == before
    assert (tmp_path / frozen["frozen_path"]).read_bytes() == before
    assert freeze(service, binding) == frozen


@pytest.mark.parametrize("change", ["bytes", "approval", "owner", "fps", "geometry", "duration"])
def test_reject_changed_or_unsupported_master(tmp_path, change):
    service, row, specs, binding = fixture(tmp_path)
    if change == "bytes":
        (tmp_path / row["path"]).write_bytes(b"changed")
    elif change == "approval":
        row["approved"] = False
    elif change == "owner":
        row["channel_id"] = "second"
    elif change == "fps":
        specs["fps"] = 60
    elif change == "geometry":
        specs["width"] = 1920
    elif change == "duration":
        specs["duration"] = float("nan")
    with pytest.raises(ChannelError):
        service.inspect("main", binding)


def test_backup_detects_manifest_race_and_removes_own_partial_copy(tmp_path):
    service, row, specs, binding = fixture(tmp_path)
    calls = 0
    def racing_resolver(c, b):
        nonlocal calls
        calls += 1
        result = deepcopy(row)
        if calls >= 3:
            result["revision"] = "changed-during-backup"
        return result
    service.resolver = racing_resolver
    info = service.inspect("main", binding)
    with pytest.raises(ChannelError, match="changed while"):
        service.freeze("main", "03_Projects/main/HF_" + "a" * 32, binding,
                       approval={"approved": True, "master_digest": info["master_digest"]})
    assert not list(tmp_path.glob("03_Projects/main/HF_*/overlay_inputs/*/master.mp4"))
    assert (tmp_path / row["path"]).read_bytes() == b"approved-master"


def layer(root):
    from PIL import Image
    path = root / "02_Assets/overlay.png"
    path.parent.mkdir(exist_ok=True)
    Image.new("RGB", (64, 64), "red").save(path)
    return {"path": path.relative_to(root).as_posix(), "sha256": _sha(path),
            "x": 48, "y": 48, "width": 100, "height": 100, "start": .2, "duration": .4}


def test_composer_pins_media_and_preserves_master_clock(tmp_path):
    service, row, specs, binding = fixture(tmp_path)
    snapshot = freeze(service, binding)
    image = layer(tmp_path)
    output = service.compose(snapshot, "03_Projects/main/HF_" + "a" * 32 + "/overlay_compositions/one", [image])
    document = (tmp_path / output["source_dir"] / "index.html").read_text()
    assert 'id="master-video"' in document and 'data-duration="1.0"' in document
    assert 'id="master-audio"' in document and 'data-volume="1"' in document
    assert "font" not in document and "script" not in document
    assert output["asset_contract"]["required_audio"][0]["sha256"] == row["sha256"]
    assert output["asset_contract"]["approved_master_overlay"]["composition_sha256"] == _sha(tmp_path / output["source_dir"] / "index.html")
    assert (tmp_path / row["path"]).read_bytes() == b"approved-master"
    with pytest.raises(ChannelError, match="new revision"):
        service.compose(snapshot, output["source_dir"], [image])


@pytest.mark.parametrize("change", ["text", "script", "safezone", "timing", "owner", "hash", "nan"])
def test_visual_layers_cannot_modify_fonts_audio_or_original_geometry(tmp_path, change):
    service, row, specs, binding = fixture(tmp_path)
    snapshot = freeze(service, binding)
    image = layer(tmp_path)
    if change in {"text", "script"}:
        image[change] = "forbidden"
    elif change == "safezone":
        image["x"] = 950
    elif change == "timing":
        image["duration"] = 10
    elif change == "hash":
        image["sha256"] = "0" * 64
    elif change == "nan":
        image["x"] = float("nan")
    elif change == "owner":
        alien = tmp_path / "03_Projects/second/image.png"
        alien.parent.mkdir(parents=True)
        shutil.copyfile(tmp_path / image["path"], alien)
        image["path"] = alien.relative_to(tmp_path).as_posix()
    with pytest.raises(ChannelError):
        service.compose(snapshot, "03_Projects/main/HF_" + "a" * 32 + "/overlay_compositions/one", [image])


def test_frozen_backup_tampering_is_not_silently_replaced(tmp_path):
    service, row, specs, binding = fixture(tmp_path)
    snapshot = freeze(service, binding)
    media = tmp_path / snapshot["frozen_path"]
    media.write_bytes(b"tampered")
    with pytest.raises(ChannelError):
        freeze(service, binding)
    assert media.read_bytes() == b"tampered"
    with pytest.raises(ChannelError):
        service.compose(snapshot, "03_Projects/main/HF_" + "a" * 32 + "/overlay_compositions/one", [])


def test_gadget_master_namespace_is_owner_validated_by_resolver(tmp_path):
    service, row, specs, binding = fixture(tmp_path)
    actual = tmp_path / "04_Exports/Ready_to_post/GadgetMedia/gadget_example/master.mp4"
    actual.parent.mkdir(parents=True)
    shutil.copyfile(tmp_path / row["path"], actual)
    row["path"] = actual.relative_to(tmp_path).as_posix()
    snapshot = freeze(service, binding)
    assert snapshot["path"] == row["path"]
    row["channel_id"] = "second"
    with pytest.raises(ChannelError):
        service.inspect("main", binding)


@pytest.mark.parametrize("target", ["01_Raw/master.mp4", "04_Exports/Ready_to_post/second/master.mp4", "../outside.mp4"])
def test_paths_cannot_target_raw_or_other_channel(tmp_path, target):
    service, row, specs, binding = fixture(tmp_path)
    row["path"] = target
    with pytest.raises(ChannelError):
        service.inspect("main", binding)


def test_composition_cannot_output_into_existing_master_namespace(tmp_path):
    service, row, specs, binding = fixture(tmp_path)
    snapshot = freeze(service, binding)
    for target in ("04_Exports/Ready_to_post/main/new.mp4", "03_Projects/main/Gadget_example/HF_fake/overlay_compositions/one", "03_Projects/main/HF_" + "a" * 32 + "/overlay_compositions/deeper/one"):
        with pytest.raises(ChannelError):
            service.compose(snapshot, target, [])
    assert (tmp_path / row["path"]).read_bytes() == b"approved-master"


def test_copy_race_cleans_only_new_composition(tmp_path, monkeypatch):
    service, row, specs, binding = fixture(tmp_path)
    snapshot = freeze(service, binding)
    image = layer(tmp_path)
    original_copy = shutil.copyfileobj
    calls = 0
    def tamper_copy(source, output, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            output.write(b"raced-image-bytes")
        else:
            original_copy(source, output, *args, **kwargs)
    monkeypatch.setattr(shutil, "copyfileobj", tamper_copy)
    destination = "03_Projects/main/HF_" + "a" * 32 + "/overlay_compositions/one"
    with pytest.raises(ChannelError, match="changed during"):
        service.compose(snapshot, destination, [image])
    assert not (tmp_path / destination).exists()
    assert (tmp_path / row["path"]).read_bytes() == b"approved-master"
    assert (tmp_path / snapshot["frozen_path"]).read_bytes() == b"approved-master"


def test_corrupt_raster_returns_domain_error_before_output(tmp_path):
    service, row, specs, binding = fixture(tmp_path)
    snapshot = freeze(service, binding)
    image = layer(tmp_path)
    path = tmp_path / image["path"]
    path.write_bytes(b"not-an-image")
    image["sha256"] = _sha(path)
    with pytest.raises(ChannelError, match="valid single raster"):
        service.compose(snapshot, "03_Projects/main/HF_" + "a" * 32 + "/overlay_compositions/one", [image])


def test_animated_raster_is_not_an_unsafe_clock_source(tmp_path):
    from PIL import Image
    service, row, specs, binding = fixture(tmp_path)
    snapshot = freeze(service, binding)
    image = layer(tmp_path)
    path = tmp_path / image["path"]
    Image.new("RGB", (64, 64), "red").save(path, save_all=True, append_images=[Image.new("RGB", (64, 64), "blue")], duration=100, loop=0)
    image["sha256"] = _sha(path)
    with pytest.raises(ChannelError, match="single raster"):
        service.compose(snapshot, "03_Projects/main/HF_" + "a" * 32 + "/overlay_compositions/one", [image])


def test_preflight_is_readonly_and_does_not_mutate_requested_layers(tmp_path):
    service, row, specs, binding = fixture(tmp_path)
    image = layer(tmp_path)
    digest = image.pop("sha256")
    original = deepcopy(image)
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    normalized = service.validate_layers("main", 1, [image])
    assert normalized[0]["sha256"] == digest and image == original
    assert sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")) == before
    assert not list(tmp_path.glob("03_Projects/main/HF_*"))


def test_preflight_missing_file_fails_without_creating_draft(tmp_path):
    service, row, specs, binding = fixture(tmp_path)
    image = layer(tmp_path)
    (tmp_path / image["path"]).unlink()
    with pytest.raises(ChannelError) as error:
        service.validate_layers("main", 1, [image])
    assert error.value.status_code == 422
    assert not list(tmp_path.glob("03_Projects/main/HF_*"))


def test_worker_guard_rejects_altered_composition_or_master(tmp_path):
    service, row, specs, binding = fixture(tmp_path)
    output = service.compose(freeze(service, binding), "03_Projects/main/HF_" + "a" * 32 + "/overlay_compositions/one", [])
    spec = {"asset_contract": output["asset_contract"], "files": output["files"],
            "duration_seconds": 1, "audio_mode": "music_only"}
    guard = (Path(__file__).resolve().parents[1] / "tools/hyperframes_overlay_guard.mjs").as_uri()
    code = f"import {{validateApprovedMasterOverlay}} from {json.dumps(guard)};const s=JSON.parse(process.argv[1]);validateApprovedMasterOverlay(s);"
    assert subprocess.run([shutil.which("node"), "--input-type=module", "-e", code, json.dumps(spec)], capture_output=True).returncode == 0
    for field in ("composition_sha256", "master_sha256", "duration_seconds", "audio"):
        modified = deepcopy(spec)
        modified["asset_contract"]["approved_master_overlay"][field] = "bad"
        result = subprocess.run([shutil.which("node"), "--input-type=module", "-e", code, json.dumps(modified)], capture_output=True)
        assert result.returncode != 0 and b"overlay_contract_changed" in result.stderr


@pytest.mark.skipif(os.environ.get("OMNICUT_HF_REAL_RENDER_SMOKE") != "1", reason="Actual isolated SDK + FFmpeg opt-in")
def test_actual_sdk_overlay_keeps_master_audio_and_pixels(tmp_path):
    from scripts.hyperframes_authoring import freeze_dependencies
    from scripts.hyperframes_render import HyperFramesRenderJobs, probe_video
    service, row, specs, binding = fixture(tmp_path)
    media = tmp_path / row["path"]
    ffmpeg = shutil.which("ffmpeg")
    subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x00aa00:s=1080x1920:r=30:d=1", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(media)], check=True, timeout=30)
    row["sha256"] = _sha(media)
    service.probe = probe_video
    snapshot = freeze(service, binding)
    output = service.compose(snapshot, "03_Projects/main/HF_" + "a" * 32 + "/overlay_compositions/one", [layer(tmp_path)])
    revision = freeze_dependencies(tmp_path / output["source_dir"], tmp_path / "03_Projects/main/revisions/overlay")
    revision.update(id="overlay_revision", project_id="overlay_project", channel_id="main")
    project = {"project_id": "overlay_project", "project_name": "main/HF_overlay", "channel_id": "main", "revision": 1,
               "source_binding": {"type": "standalone"}, "channel_identity": {"channel_id": "main"}, "inputs": output["inputs"]}
    jobs = HyperFramesRenderJobs(tmp_path)
    job = jobs.create("main", project, revision, idempotency_key="overlay-test", asset_contract=output["asset_contract"])
    result = jobs.execute("main", job["id"])
    if result["status"] != "qc_ready":
        log = tmp_path / f".tmp/hyperframes/render/{job['id']}/1/render.log"
        pytest.fail(f"{result.get('error')}\n{log.read_text(errors='replace')[-6000:] if log.exists() else ''}")
    rendered = tmp_path / result["artifact"]["path"]
    assert probe_video(rendered)["audio"] and _sha(media) == row["sha256"]
    # Probe untouched master pixels and bounded overlay during its exact clip window.
    for time, overlay in ((.1, False), (.3, True), (.8, False)):
        frame = subprocess.run([ffmpeg, "-v", "error", "-ss", str(time), "-i", str(rendered), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"], capture_output=True, check=True, timeout=20).stdout
        center = frame[(900 * 1080 + 600) * 3:(900 * 1080 + 600) * 3 + 3]
        corner = frame[(80 * 1080 + 80) * 3:(80 * 1080 + 80) * 3 + 3]
        assert center[1] > 130 and center[0] < 40
        assert (corner[0] > 150 and corner[1] < 80) if overlay else (corner[1] > 130 and corner[0] < 40)
    # Original audio frequency remains, with no mute or unintended additional tracks.
    import array
    audio = subprocess.run([ffmpeg, "-v", "error", "-i", str(rendered), "-vn", "-ac", "1", "-ar", "48000", "-f", "s16le", "pipe:1"], capture_output=True, check=True, timeout=20).stdout
    samples = array.array("h", audio)
    assert max(abs(n) for n in samples) > 1000
    crossings = sum(samples[i - 1] <= 0 < samples[i] for i in range(4800, min(43200, len(samples))))
    assert abs(crossings / .8 - 440) < 5
    import math
    original_pcm = subprocess.run([ffmpeg, "-v", "error", "-i", str(media), "-vn", "-ac", "1", "-ar", "48000", "-f", "s16le", "pipe:1"], capture_output=True, check=True, timeout=20).stdout
    original_samples = array.array("h", original_pcm)
    def rms(values):
        return math.sqrt(sum(n * n for n in values[4800:43200]) / len(values[4800:43200]))
    assert .9 <= rms(samples) / rms(original_samples) <= 1.1
