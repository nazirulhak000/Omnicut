import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from scripts.hyperframes_project import HyperFramesProjects, HyperFramesProjectError


class Products:
    @staticmethod
    def get(product_id, *, channel_id):
        if product_id == "p" and channel_id == "main":
            return {"id": "p", "channel_id": "main", "angles": [{"id": "a"}]}
        return None


@pytest.fixture
def store(tmp_path):
    return HyperFramesProjects(tmp_path, product_store=Products)


def create(store, **kwargs):
    return store.create("main", {"type": "product_angle", "product_id": "p", "angle_id": "a"},
                        {"channel_id": "main", "handle": "@rizanntry"}, **kwargs)


def test_canonical_manifest_discovery_and_frozen_identity(store, tmp_path, monkeypatch):
    from scripts import project_manifest
    manifest = create(store)
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", tmp_path / "03_Projects")
    loaded = project_manifest.ProjectManifest.load(manifest["project_name"])
    assert loaded == manifest
    assert loaded["engine"] == "hyperframes"
    assert loaded["source_binding"]["angle_id"] == "a"
    assert loaded["channel_identity"]["handle"] == "@rizanntry"
    assert "timeline" not in loaded
    assert store.list("main") == [loaded]
    assert store.list("other") == []
    with pytest.raises(HyperFramesProjectError, match="not found"):
        store.get(manifest["project_id"], "other")


@pytest.mark.parametrize("binding", [
    {"type": "product_angle", "product_id": "p", "angle_id": "unknown"},
    {"type": "product_angle", "product_id": "other", "angle_id": "a"},
    {"type": "gadget_slot", "campaign_id": "c", "slot_id": "s"},
    {"type": "standalone"},
    {"type": "product_angle", "product_id": "p", "angle_id": "a", "channel_id": "other"},
])
def test_wrong_source_rejected_without_project_writes(store, tmp_path, binding):
    with pytest.raises(HyperFramesProjectError):
        store.create("main", binding, {"channel_id": "main"})
    assert not (tmp_path / "03_Projects").exists()


def test_explicit_standalone(store):
    manifest = store.create("main", {"type": "standalone"}, {"channel_id": "main"},
                            allow_standalone=True, inputs={"audio_mode": "silent", "total_duration": 10})
    assert manifest["inputs"]["audio_mode"] == "silent"


@pytest.mark.parametrize("mode", ["narration", "music_only", "silent"])
def test_audio_modes_without_dummy_audio(store, mode):
    manifest = create(store, inputs={"audio_mode": mode, "total_duration": 12})
    assert manifest["inputs"]["audio_mode"] == mode
    assert manifest["artifacts"] == {}


@pytest.mark.parametrize("inputs", [{"audio_mode": "invalid"}, {"total_duration": -1},
                                    {"total_duration": float("nan")}, {"total_duration": True}])
def test_invalid_inputs_do_not_create_manifests(store, tmp_path, inputs):
    with pytest.raises(HyperFramesProjectError):
        create(store, inputs=inputs)
    assert not list(tmp_path.rglob("project.json"))


def test_revision_cas_and_brief_invalidation(store):
    initial = create(store)
    updated = store.update(initial["project_id"], "main", 1,
                           {"accepted_revision": {"revision_id": "r1"}, "status": "preview_ready"})
    assert updated["revision"] == 2
    assert updated["project_revision"] != initial["project_revision"]
    with pytest.raises(HyperFramesProjectError) as error:
        store.update(initial["project_id"], "main", 1, {"status": "rendering"})
    assert error.value.code == "revision_conflict"
    edited = store.update(initial["project_id"], "main", 2, {"inputs": {"audio_mode": "silent"}})
    assert edited["brief_revision"] == 2
    assert edited["accepted_revision"] is None
    assert edited["status"] == "draft"
    assert store.get(initial["project_id"], "main") == edited


@pytest.mark.parametrize("changes", [{"channel_id": "other"}, {"source_binding": {}},
                                     {"channel_identity": {}}, {"project_name": "other/x"},
                                     {"revision": 20}])
def test_identity_and_parent_cannot_be_changed(store, changes):
    initial = create(store)
    with pytest.raises(HyperFramesProjectError):
        store.update(initial["project_id"], "main", 1, changes)
    assert store.get(initial["project_id"], "main") == initial


def test_two_store_instances_share_cas_lock(store, tmp_path):
    manifest = create(store)
    other = HyperFramesProjects(tmp_path, product_store=Products)

    def update(instance):
        try:
            return instance.update(manifest["project_id"], "main", 1, {"status": "authoring"})["revision"]
        except HyperFramesProjectError as error:
            return error.code

    with ThreadPoolExecutor(2) as executor:
        results = list(executor.map(update, [store, other]))
    assert sorted(map(str, results)) == ["2", "revision_conflict"]


@pytest.mark.parametrize("project_id,channel", [("../bad", "main"), ("a" * 32, "../other"),
                                                ("a" * 32, "main/other")])
def test_path_traversal_rejected(store, project_id, channel):
    with pytest.raises(HyperFramesProjectError):
        store.get(project_id, channel)


def test_manifest_owner_corruption_fails_closed(store):
    initial = create(store)
    path = store.directory(initial["project_id"], "main") / "project.json"
    changed = dict(initial, channel_id="other")
    path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(HyperFramesProjectError, match="mismatch"):
        store.get(initial["project_id"], "main")


def test_manifest_identity_corruption_fails_closed(store):
    initial = create(store)
    path = store.directory(initial["project_id"], "main") / "project.json"
    initial["channel_identity"]["channel_id"] = "other"
    path.write_text(json.dumps(initial), encoding="utf-8")
    with pytest.raises(HyperFramesProjectError, match="mismatch"):
        store.get(initial["project_id"], "main")


def test_new_inputs_cannot_reuse_approval_in_same_update(store):
    initial = create(store)
    with pytest.raises(HyperFramesProjectError, match="separate operation"):
        store.update(initial["project_id"], "main", 1,
                     {"inputs": {"audio_mode": "silent"}, "accepted_revision": {"revision_id": "old"}})
    assert store.get(initial["project_id"], "main") == initial


def test_nonproduction_root_cannot_fall_back_to_production_store(tmp_path):
    store = HyperFramesProjects(tmp_path)
    with pytest.raises(HyperFramesProjectError) as error:
        create(store)
    assert error.value.code == "source_store_required"
    assert not (tmp_path / "03_Projects").exists()


@pytest.mark.parametrize("change", [{"source_binding": {"type": "gadget_slot"}}, {"revision": "1"},
                                    {"brief_revision": 0}])
def test_corrupt_source_or_revision_is_rejected(store, change):
    initial = create(store)
    path = store.directory(initial["project_id"], "main") / "project.json"
    path.write_text(json.dumps(dict(initial, **change)), encoding="utf-8")
    with pytest.raises(HyperFramesProjectError):
        store.get(initial["project_id"], "main")
