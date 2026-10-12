"""Generated-media boundaries and immutable export identity provenance."""
import pytest

from scripts import config
from scripts.channel_scope import ChannelScope
from scripts.channel_store import ChannelError
from scripts.channel_workflows import require_media_owner, require_project_owner
from scripts.export_registry import ExportRegistry
from scripts.product_store import ProductStore
from scripts.project_manifest import ProjectManifest


def scope(owner):
    return ChannelScope(owner, "header", False, channel={"id": owner, "status": "active"})


def write(rel):
    path = config.BASE_DIR / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fixture")
    return path


def test_shared_sources_and_owned_project_media():
    raw = write("01_Raw/fixture/source.mp4")
    assert require_media_owner(scope("second"), raw) == raw
    ProjectManifest.save("owned", channel_id="second")
    private = write("03_Projects/owned/voice.wav")
    assert require_media_owner(scope("second"), private) == private
    with pytest.raises(ChannelError):
        require_media_owner(scope("main"), private)
    with pytest.raises(ChannelError):
        require_media_owner(scope("second"), config.BASE_DIR.parent / "outside.mp4")


def test_flat_registered_export_cannot_be_claimed_by_legacy_main():
    video = write("04_Exports/Ready_to_post/clip.mp4")
    ExportRegistry.ensure(video, channel_id="second")
    with pytest.raises(ChannelError):
        require_media_owner(scope("main"), video)
    assert require_media_owner(scope("second"), video) == video


def test_render_params_parent_product_must_match_manifest_owner():
    foreign = ProductStore.add("Foreign", channel_id="main")
    ProjectManifest.save("owned", channel_id="second", render_params={"product_id": foreign["id"]})
    with pytest.raises(ChannelError):
        require_project_owner(scope("second"), "owned")


def test_export_identity_is_copied_and_cannot_change_in_place():
    video = write("04_Exports/Ready_to_post/second/clip.mp4")
    pinned = {"channel_id": "second", "channel_revision": 2, "channel_identity_hash": "hash-a",
              "channel_identity_snapshot": {"display_name": "Original"}}
    row = ExportRegistry.ensure(video, channel_id="second", job_scope=pinned)
    pinned["channel_identity_snapshot"]["display_name"] = "Changed"
    assert ExportRegistry.get(row["id"], channel_id="second")["channel_identity_snapshot"]["display_name"] == "Original"
    with pytest.raises(ChannelError) as error:
        ExportRegistry.ensure(video, channel_id="second", job_scope={**pinned, "channel_identity_hash": "hash-b"})
    assert error.value.status_code == 409
    assert ExportRegistry.get(row["id"], channel_id="second")["channel_identity_hash"] == "hash-a"


def test_export_scope_mismatch_does_not_insert():
    video = write("04_Exports/clip.mp4")
    with pytest.raises(ChannelError):
        ExportRegistry.ensure(video, channel_id="main", job_scope={"channel_id": "second"})
    assert ExportRegistry.all(channel_id="main") == []


def test_legacy_posted_and_configured_drafts_are_not_shared_with_secondary(tmp_path):
    archived = write("06_Archive/Posted/legacy.mp4")
    draft_root = tmp_path / "external-drafts"
    draft = draft_root / "project/resources/source.mp4"
    draft.parent.mkdir(parents=True)
    draft.write_bytes(b"legacy draft")
    for path, roots in [(archived, ()), (draft, (draft_root,))]:
        assert require_media_owner(scope("main"), path, legacy_roots=roots) == path
        with pytest.raises(ChannelError):
            require_media_owner(scope("second"), path, legacy_roots=roots)
        with pytest.raises(ChannelError):
            require_media_owner(ChannelScope("main", "header", True), path, legacy_roots=roots)
    ExportRegistry.ensure(archived, channel_id="second")
    with pytest.raises(ChannelError):
        require_media_owner(scope("main"), archived)
    assert require_media_owner(scope("second"), archived) == archived
