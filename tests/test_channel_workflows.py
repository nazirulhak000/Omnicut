"""Ownership helpers operate on fixtures, never the live project directory."""
from copy import deepcopy

import pytest

from scripts.channel_scope import ChannelScope
from scripts.channel_store import ChannelError
from scripts.channel_workflows import (
    api_store_kwargs, capture_job_scope, owner_path_component,
    require_project_owner, require_record_owner,
)


def scope(channel_id="main", strict=False):
    return ChannelScope(channel_id, "header", strict, channel={
        "id": channel_id, "status": "active", "revision": 4,
        "identity_hash": "pinned", "display_name": "Fixture",
        "avatar_asset_path": "", "avatar_sha256": "fixture-hash",
    })


def test_implicit_main_api_calls_always_filter_foreign_rows():
    current = scope()
    current.source = "default"
    assert api_store_kwargs(current) == {"channel_id": "main"}
    assert require_record_owner(current, {"id": "legacy"})["id"] == "legacy"
    with pytest.raises(ChannelError) as error:
        require_record_owner(current, {"id": "foreign", "channel_id": "second"})
    assert error.value.status_code == 404


@pytest.mark.parametrize("current", [scope("second"), scope("main", True)])
def test_ownerless_records_are_not_secondary_or_strict_resources(current):
    with pytest.raises(ChannelError):
        require_record_owner(current, {"id": "legacy"})


def test_project_checks_manifest_and_parent_product_before_edit(monkeypatch):
    from scripts.project_manifest import ProjectManifest
    from scripts.product_store import ProductStore
    current = scope("second")
    manifest = {"channel_id": "second", "product": {"id": "parent"}}
    monkeypatch.setattr(ProjectManifest, "load", lambda name: deepcopy(manifest))
    calls = []
    def get(product_id, **kwargs):
        calls.append((product_id, kwargs))
        return {"id": product_id, "channel_id": "second"}
    monkeypatch.setattr(ProductStore, "get", get)
    assert require_project_owner(current, "fixture", writable=True) == manifest
    assert calls == [("parent", {"channel_id": "second"})]
    monkeypatch.setattr(ProductStore, "get", lambda *args, **kwargs: None)
    with pytest.raises(ChannelError):
        require_project_owner(current, "fixture")


def test_foreign_manifest_and_invalid_project_path_are_not_disclosed(monkeypatch):
    from scripts.project_manifest import ProjectManifest
    monkeypatch.setattr(ProjectManifest, "load", lambda name: {"channel_id": "second"})
    with pytest.raises(ChannelError):
        require_project_owner(scope(), "foreign")
    def invalid(name):
        raise ValueError("escape")
    monkeypatch.setattr(ProjectManifest, "load", invalid)
    with pytest.raises(ChannelError) as error:
        require_project_owner(scope(), "../escape")
    assert error.value.status_code == 404


def test_job_provenance_is_captured_before_registry_changes():
    current = scope("second")
    captured = capture_job_scope(current)
    current.channel["revision"] = 5
    current.channel["avatar_asset_path"] = "changed.png"
    assert captured["channel_id"] == "second"
    assert captured["channel_revision"] == 4
    assert captured["channel_identity_snapshot"]["avatar_asset_path"] == ""
    assert captured["channel_identity_snapshot"]["avatar_sha256"] == "fixture-hash"
    assert "status" not in captured["channel_identity_snapshot"]
    assert captured["channel_status"] == "active"
    assert owner_path_component(current) == "second"
    assert owner_path_component(scope()) == ""
