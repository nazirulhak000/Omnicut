from copy import deepcopy
import hashlib
from pathlib import Path

import pytest
from PIL import Image

from scripts.channel_store import ChannelError
from scripts.hyperframes_finalize import HyperFramesFinalizer, _fingerprint
from scripts.hyperframes_project import HyperFramesProjects
from scripts.hyperframes_render import HyperFramesRenderJobs


class Products:
    def __init__(self):
        self.product = {"id": "p", "channel_id": "main", "angles": [{"id": "a", "status": "scripted"}]}

    def get(self, product_id, *, channel_id):
        return deepcopy(self.product) if product_id == "p" and channel_id == "main" else None

    def compare_and_set_angle(self, channel, product, angle_id, fingerprint, fields):
        angle = self.product["angles"][0]
        if angle.get("export_id") == fields["export_id"]:
            return True
        if _fingerprint(angle) != fingerprint:
            return False
        angle.update(deepcopy(fields))
        return True


class Registry:
    def __init__(self):
        self.rows = []

    def ensure_many(self, entries, *, channel_id, job_scope):
        result = []
        for entry in entries:
            row = next((r for r in self.rows if r["path"] == entry["path"]), None)
            if row is None:
                row = {**deepcopy(entry), "id": f"exp_{len(self.rows)}", "channel_id": channel_id}
                self.rows.append(row)
            result.append(deepcopy(row))
        return result

    def find_by_path(self, path, *, channel_id):
        return deepcopy(next((r for r in self.rows if r["path"] == path and r["channel_id"] == channel_id), None))


@pytest.fixture
def context(tmp_path):
    products, registry = Products(), Registry()
    projects = HyperFramesProjects(tmp_path, product_store=products)
    project = projects.create("main", {"type": "product_angle", "product_id": "p", "angle_id": "a"},
                              {"channel_id": "main", "handle": "@rizanntry"},
                              {"audio_mode": "silent", "total_duration": 1, "tiktok_product_id": "basket"})
    directory = tmp_path / ".tmp/hyperframes/render/hfr_test/1"
    directory.mkdir(parents=True)
    (directory / "video.mp4").write_bytes(b"qc-verified-video")
    Image.new("RGB", (9, 16), "blue").save(directory / "thumbnail.webp")
    artifact = {"path": (directory / "video.mp4").relative_to(tmp_path).as_posix(),
                "sha256": hashlib.sha256(b"qc-verified-video").hexdigest(),
                "thumbnail_path": (directory / "thumbnail.webp").relative_to(tmp_path).as_posix(),
                "thumbnail_sha256": hashlib.sha256((directory / "thumbnail.webp").read_bytes()).hexdigest()}
    jobs = HyperFramesRenderJobs(tmp_path)
    row = {"id": "hfr_test", "channel_id": "main", "project_id": project["project_id"],
           "project_name": project["project_name"], "project_revision": project["revision"],
           "source_binding": project["source_binding"], "source_angle_snapshot": deepcopy(products.product["angles"][0]),
           "snapshot": {"id": "revision1"}, "channel_identity_snapshot": project["channel_identity"],
           "artifact": artifact, "revision": 1, "status": "qc_ready", "finalize_intent": None}
    with jobs.table.mutate() as rows:
        rows.append(row)
    finalizer = HyperFramesFinalizer(tmp_path, jobs=jobs, projects=projects, registry=registry, product_store=products)
    return finalizer, jobs, projects, products, registry, row, tmp_path


def finish(ctx, **kwargs):
    finalizer, _, _, _, _, row, _ = ctx
    return finalizer.finalize("main", row["id"], 1, row["artifact"]["sha256"], kwargs)


def test_product_fact_change_blocks_reviewed_export(context):
    finalizer, jobs, _, products, registry, row, _ = context
    with jobs.table.mutate() as rows:
        rows[0]["source_product_snapshot"] = finalizer._product_facts(products.product)
    products.product["specs"] = {"battery": "changed"}
    with pytest.raises(ChannelError) as error:
        finish(context, tiktok_product_id="basket")
    assert error.value.code == "hyperframes_product_changed"
    assert not registry.rows
    assert jobs.get("main", row["id"])["status"] == "qc_ready"


def test_product_fact_change_during_finalize_preserves_parent(context):
    finalizer, jobs, _, products, registry, row, _ = context
    with jobs.table.mutate() as rows:
        rows[0]["source_product_snapshot"] = finalizer._product_facts(products.product)
    def change_facts(phase):
        if phase == "intent":
            products.product["price_note"] = "new price"
    finalizer.fault_hook = change_facts
    with pytest.raises(ChannelError) as error:
        finish(context, tiktok_product_id="basket")
    assert error.value.code == "hyperframes_product_changed"
    assert jobs.get("main", row["id"])["status"] == "recovery_required"
    assert "export_id" not in products.product["angles"][0]
    assert len(registry.rows) == 1  # Verified historical output remains recoverable.


def test_finalize_unique_registered_manifest_angle_and_package(context):
    finalizer, jobs, projects, products, registry, row, root = context
    result = finish(context, caption="Reviewed", hashtags=["#tech"], tiktok_product_id="basket")
    assert result["status"] == "finalized"
    assert len(registry.rows) == 1
    package = result["finalize_intent"]["publish_package"]
    assert (root / package["video_path"]).read_bytes() == b"qc-verified-video"
    assert (root / package["thumbnail_path"]).is_file()
    assert projects.get(row["project_id"], "main")["publish_package"] == package
    assert products.product["angles"][0]["export_id"] == result["export_id"]
    assert products.product["angles"][0]["cover_path"] is None
    assert package["source_binding"] == row["source_binding"]
    assert finalizer.finalize("main", row["id"], 1, row["artifact"]["sha256"],
                              {"caption": "Reviewed", "hashtags": ["#tech"], "tiktok_product_id": "basket"}) == result
    assert len(registry.rows) == 1


class Crash(BaseException):
    pass


@pytest.mark.parametrize("phase", ["intent", "promotion", "registration", "manifest", "parent"])
def test_process_crash_replay_never_duplicates_or_rerenders(context, phase):
    finalizer, jobs, projects, products, registry, row, root = context
    def crash(actual):
        if actual == phase:
            raise Crash()
    finalizer.fault_hook = crash
    with pytest.raises(Crash):
        finish(context)
    repaired = HyperFramesFinalizer(root, jobs=jobs, projects=projects, registry=registry, product_store=products)
    result = repaired.resume("main", row["id"])
    assert result["status"] == "finalized"
    assert len(registry.rows) == 1
    assert len(list((root / "04_Exports/Ready_to_post/main").glob("*.mp4"))) == 1
    assert len(projects.get(row["project_id"], "main")["publish_package_refs"]) == 1
    assert repaired.resume("main", row["id"])["export_id"] == result["export_id"]


@pytest.mark.parametrize("revision,digest", [(0, "original"), (1, "wrong")])
def test_stale_review_or_wrong_hash_rejected_before_output(context, revision, digest):
    finalizer, jobs, _, _, registry, row, root = context
    digest = row["artifact"]["sha256"] if digest == "original" else digest
    with pytest.raises(ChannelError):
        finalizer.finalize("main", row["id"], revision, digest, {})
    assert jobs.get("main", row["id"])["status"] == "qc_ready"
    assert registry.rows == []
    assert not (root / "04_Exports").exists()


def test_wrong_channel_rejected(context):
    finalizer, _, _, _, registry, row, _ = context
    with pytest.raises(ChannelError):
        finalizer.finalize("other", row["id"], 1, row["artifact"]["sha256"], {})
    assert registry.rows == []


def test_project_changed_before_finalize_rejects(context):
    _, _, projects, _, registry, row, _ = context
    projects.update(row["project_id"], "main", 1, {"inputs": {"audio_mode": "silent", "brief": "changed"}})
    with pytest.raises(ChannelError):
        finish(context)
    assert registry.rows == []


def test_angle_changed_after_render_rejects(context):
    _, _, _, products, registry, _, _ = context
    products.product["angles"][0]["script"] = "edited after render"
    with pytest.raises(ChannelError):
        finish(context)
    assert registry.rows == []


def test_angle_changed_during_commit_preserves_history_and_current_angle(context):
    finalizer, jobs, projects, products, registry, row, root = context
    def edit(phase):
        if phase == "registration":
            products.product["angles"][0]["script"] = "new script"
    finalizer.fault_hook = edit
    with pytest.raises(ChannelError):
        finish(context)
    result = jobs.get("main", row["id"])
    assert result["status"] == "recovery_required"
    assert len(registry.rows) == 1
    assert (root / registry.rows[0]["path"]).is_file()
    assert len(projects.get(row["project_id"], "main")["publish_package_refs"]) == 1
    assert "export_id" not in products.product["angles"][0]
    assert products.product["angles"][0]["script"] == "new script"


def test_project_changed_during_commit_keeps_registered_artifact(context):
    finalizer, jobs, projects, products, registry, row, root = context
    def edit(phase):
        if phase == "registration":
            projects.update(row["project_id"], "main", 1, {"inputs": {"audio_mode": "silent", "brief": "new"}})
    finalizer.fault_hook = edit
    with pytest.raises(ChannelError):
        finish(context)
    assert jobs.get("main", row["id"])["status"] == "recovery_required"
    assert len(registry.rows) == 1
    assert "export_id" not in products.product["angles"][0]
    assert projects.get(row["project_id"], "main")["publish_package"] is None


def test_missing_actual_thumbnail_rejected(context):
    _, _, _, _, registry, row, root = context
    (root / row["artifact"]["thumbnail_path"]).unlink()
    with pytest.raises(ChannelError):
        finish(context)
    assert registry.rows == []


def test_cover_is_frozen_separately_from_render_thumbnail(context):
    _, _, _, products, _, row, root = context
    cover = root / "05_Covers_Thumbnails/main/user.png"
    cover.parent.mkdir(parents=True)
    Image.new("RGB", (9, 16), "red").save(cover)
    result = finish(context, cover_path=cover.relative_to(root).as_posix())
    package = result["finalize_intent"]["publish_package"]
    assert package["cover_path"] != cover.relative_to(root).as_posix()
    assert package["cover_path"] != package["thumbnail_path"]
    assert (root / package["cover_path"]).read_bytes() == cover.read_bytes()
    assert products.product["angles"][0]["cover_path"] == package["cover_path"]


@pytest.mark.parametrize("package", [{"channel_id": "other"}, {"export_id": "injected"},
                                      {"tiktok_product_id": "wrong"}, {"hashtags": "bad"}])
def test_untrusted_package_fields_rejected(context, package):
    with pytest.raises(ChannelError):
        finish(context, **package)


def test_conflicting_repeated_approval_rejected(context):
    finish(context, caption="first")
    with pytest.raises(ChannelError):
        finish(context, caption="different")


def test_recovery_uses_promoted_files_after_temp_cleanup(context):
    finalizer, jobs, projects, products, registry, row, root = context
    def crash(phase):
        if phase == "promotion":
            raise Crash()
    finalizer.fault_hook = crash
    with pytest.raises(Crash):
        finish(context)
    (root / row["artifact"]["path"]).unlink()
    (root / row["artifact"]["thumbnail_path"]).unlink()
    finalizer.fault_hook = lambda phase: None
    assert finalizer.resume("main", row["id"])["status"] == "finalized"


def test_replay_preserves_registry_posted_status(context):
    finalizer, _, _, _, registry, row, _ = context
    def crash(phase):
        if phase == "registration":
            raise Crash()
    finalizer.fault_hook = crash
    with pytest.raises(Crash):
        finish(context)
    registry.rows[0]["status"] = "posted"
    finalizer.fault_hook = lambda phase: None
    assert finalizer.resume("main", row["id"])["status"] == "finalized"
    assert registry.rows[0]["status"] == "posted"


def test_new_project_edit_after_partial_manifest_commit_blocks_parent_update(context):
    finalizer, jobs, projects, products, registry, row, _ = context
    def crash(phase):
        if phase == "manifest":
            raise Crash()
    finalizer.fault_hook = crash
    with pytest.raises(Crash):
        finish(context)
    projects.update(row["project_id"], "main", 2, {"inputs": {"audio_mode": "silent", "brief": "next"}})
    finalizer.fault_hook = lambda phase: None
    with pytest.raises(ChannelError):
        finalizer.resume("main", row["id"])
    assert jobs.get("main", row["id"])["status"] == "recovery_required"
    assert "export_id" not in products.product["angles"][0]
    assert len(registry.rows) == 1
