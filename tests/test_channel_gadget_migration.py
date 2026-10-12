"""Explicit P3 Gadget migration, real scoped readers, temp-only recovery."""
import copy
import json

import pytest
from fastapi import FastAPI, Header
from fastapi.testclient import TestClient

from scripts import channel_migration as cm, config
from scripts.channel_store import ChannelError, ChannelStore
from scripts.gadget_media_campaign import CampaignStore, create_starter_campaign
from scripts.gadget_media_paths import GadgetMediaRoots
from scripts.gadget_media_project import ProductVideoProject
from scripts.gadget_media_repository import GadgetMediaRepository


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def legacy(isolated_storage):
    root = isolated_storage
    paths = cm.MigrationPaths.for_root(root)
    registry = ChannelStore(paths.channels_json, project_root=root)._implicit_document()
    second = copy.deepcopy(registry["channels"][0])
    second.update(id="second", display_name="second", handle="@second", status="active")
    registry["channels"].append(second)
    write(paths.channels_json, registry)
    campaign = create_starter_campaign(campaign_id="campaign-legacy").to_dict()
    campaign["unknown_metadata"] = {"keep": True}
    campaign["slots"][0]["product_project_id"] = "legacy-project"
    write(paths.campaigns_json, [campaign])
    project = ProductVideoProject(project_id="legacy-project", product_identity={"brand": "Fixture", "model": "Model"}).to_dict()
    project.update(channel_id=None, campaign_links=[{"campaign_id": "campaign-legacy", "slot_id": campaign["slots"][0]["slot_id"]}], unknown_metadata={"keep": True})
    write(paths.gadget_projects / "legacy-project/project.json", project)
    write(paths.gadget_projects / "legacy-project/product.json", {"project_id": "legacy-project", "channel_id": None, "unknown": "keep"})
    write(paths.gadget_projects / "legacy-project/story.json", {"unknown": "stage bytes stay"})
    write(paths.gadget_index, {"projects": [{"project_id": "legacy-project", "channel_id": None, "status": "brief", "unknown": "keep"}]})
    return root


def assignments(owner="main"):
    return [{"store": "gadget_media_campaigns", "id": "campaign-legacy", "channel_id": owner},
            {"store": "gadget_media_projects", "id": "legacy-project", "channel_id": owner}]


def apply(root, owner="main", hook=None):
    options = {"assignments": assignments(owner)}
    plan = cm.Migrator(root).dry_run(**options)["plan"]
    return cm.Migrator(root, hook=hook).apply(expect_plan=plan["plan_hash"], **options)


def test_unassigned_gadget_dry_run_is_read_only_and_never_infers_main(legacy):
    before = {p: p.read_bytes() for p in legacy.rglob("*.json")}
    result = cm.Migrator(legacy).dry_run(legacy_owner="main")
    assert result["plan"]["actions"] == []
    assert {d["status"] for d in result["plan"]["decisions"] if d["store"] in cm.GADGET_STORES} == {"unknown"}
    assert before == {p: p.read_bytes() for p in legacy.rglob("*.json")}


@pytest.mark.parametrize("owner", ["main", "second"])
@pytest.mark.parametrize("case", ["foreign_index", "own_companion", "foreign_project"])
def test_project_companion_ownership_matches_real_media_guard(legacy, monkeypatch, owner, case):
    from scripts.channel_scope import ChannelScope
    from scripts.channel_workflows import require_media_owner
    from scripts.db import DocumentTable

    paths = cm.MigrationPaths.for_root(legacy)
    project_path = paths.gadget_projects / "legacy-project/project.json"
    project = read(project_path)
    relative = "03_Projects/GadgetMedia/legacy-project/voice.wav"
    foreign = "second" if owner == "main" else "main"
    if case == "foreign_project":
        relative = "03_Projects/GadgetMedia/other-project/voice.wav"
        other = ProductVideoProject(project_id="other-project", product_identity={"brand": "Fixture", "model": "Other"}).to_dict()
        other["channel_id"] = foreign
        write(paths.gadget_projects / "other-project/project.json", other)
    project["artifacts"] = [{"artifact_id": "voice", "kind": "voice", "path": relative}]
    write(project_path, project)
    if case == "foreign_index":
        DocumentTable("channel_artifacts", lambda: paths.store_db, lambda: paths.docs / "channel_artifacts.json").save([
            {"id": "voice", "channel_id": foreign, "path": relative, "path_key": relative.casefold()}])
    before = {p: p.read_bytes() for p in legacy.rglob("*.json")}
    if case != "own_companion":
        with pytest.raises(cm.AssignmentError):
            cm.Migrator(legacy).dry_run(assignments=assignments(owner))
        assert before == {p: p.read_bytes() for p in legacy.rglob("*.json")}
        return
    apply(legacy, owner)
    monkeypatch.setenv(config.MULTI_CHANNEL_STRICT_ENV, "1")
    scope = ChannelScope(owner, "header", True, channel={"id": owner, "status": "active"})
    assert require_media_owner(scope, relative, base_dir=legacy) == (legacy / relative).resolve()


@pytest.mark.parametrize("owner", ["main", "second"])
def test_explicit_assignment_preserves_raw_fields_and_is_visible_via_actual_api(legacy, monkeypatch, owner):
    from scripts import api_gadget_media, api_gadget_media_projects
    from scripts.channel_scope import ChannelScope, channel_error_handler
    from scripts.channel_workflows import get_workflow_scope
    paths = cm.MigrationPaths.for_root(legacy)
    stage = (paths.gadget_projects / "legacy-project/story.json").read_bytes()
    result = apply(legacy, owner)
    assert result["status"] == "applied" and result["rows"] == 2
    assert read(paths.campaigns_json)[0]["unknown_metadata"] == {"keep": True}
    assert read(paths.gadget_projects / "legacy-project/project.json")["unknown_metadata"] == {"keep": True}
    assert read(paths.gadget_projects / "legacy-project/product.json")["channel_id"] == owner
    assert read(paths.gadget_index)["projects"][0]["channel_id"] == owner
    assert (paths.gadget_projects / "legacy-project/story.json").read_bytes() == stage
    assert cm.Migrator(legacy).dry_run(assignments=assignments(owner))["plan"]["actions"] == []
    monkeypatch.setenv(config.MULTI_CHANNEL_STRICT_ENV, "1")
    repo = GadgetMediaRepository(GadgetMediaRoots.under(legacy))
    assert repo.for_channel(owner).get("legacy-project").channel_id == owner
    assert [p.project_id for p in repo.for_channel(owner).list()] == ["legacy-project"]
    assert CampaignStore(paths.campaigns_json, channel_id=owner).get("campaign-legacy").channel_id == owner
    monkeypatch.setattr(api_gadget_media, "CAMPAIGNS_FILE", paths.campaigns_json)
    monkeypatch.setattr(api_gadget_media_projects, "PROJECT_REPOSITORY", repo)
    app = FastAPI()
    app.add_exception_handler(ChannelError, channel_error_handler)
    def scope(channel: str = Header(alias="X-OmniCut-Channel")):
        return ChannelScope(channel, "header", True, channel={"id": channel, "status": "active"})
    app.dependency_overrides[get_workflow_scope] = scope
    app.include_router(api_gadget_media.router)
    app.include_router(api_gadget_media_projects.router)
    with TestClient(app) as client:
        for endpoint in ("/api/gadget-media/campaigns/campaign-legacy", "/api/gadget-media/projects/legacy-project"):
            assert client.get(endpoint, headers={"X-OmniCut-Channel": owner}).status_code == 200
            assert client.get(endpoint, headers={"X-OmniCut-Channel": "second" if owner == "main" else "main"}).status_code == 404


@pytest.mark.parametrize("case", ["foreign_parent", "unknown_parent", "foreign_mirror", "nested", "duplicate", "foreign_identity", "unowned_media", "foreign_media", "unknown_channel", "archived_channel"])
def test_assignments_fail_closed_before_mutations(legacy, case):
    paths = cm.MigrationPaths.for_root(legacy)
    project_path = paths.gadget_projects / "legacy-project/project.json"
    project = read(project_path)
    options = assignments("second")
    if case == "foreign_parent":
        options[0]["channel_id"] = "main"
    elif case == "unknown_parent":
        options = options[1:]
    elif case == "foreign_mirror":
        mirror = paths.gadget_projects / "legacy-project/product.json"
        write(mirror, {**read(mirror), "channel_id": "main"})
    elif case in ("nested", "duplicate"):
        write(paths.gadget_projects / "nested/legacy-project/project.json", project)
        if case == "nested":
            project_path.unlink()
            options[1]["id"] = "nested/legacy-project"
    elif case == "foreign_identity":
        project["presentation"]["channel_identity_snapshot"] = {"channel_id": "main", "style": {"keep": True}}
        write(project_path, project)
    elif case in ("unowned_media", "foreign_media"):
        project["artifacts"] = [{"artifact_id": "render", "kind": "render", "path": "04_Exports/GadgetMedia/legacy-project/old.mp4"}]
        write(project_path, project)
        if case == "foreign_media":
            from scripts.db import DocumentTable
            DocumentTable("channel_artifacts", lambda: paths.store_db, lambda: paths.docs / "channel_artifacts.json").save([
                {"id": "artifact", "channel_id": "main", "path": project["artifacts"][0]["path"], "path_key": project["artifacts"][0]["path"].casefold()}])
    elif case == "unknown_channel":
        options[0]["channel_id"] = "missing"
    else:
        registry = read(paths.channels_json)
        registry["channels"][1]["status"] = "archived"
        write(paths.channels_json, registry)
    before = {p: p.read_bytes() for p in legacy.rglob("*.json")}
    with pytest.raises(cm.AssignmentError):
        cm.Migrator(legacy).dry_run(assignments=options)
    assert before == {p: p.read_bytes() for p in legacy.rglob("*.json")}


@pytest.mark.parametrize("step", ["gadget_media_campaigns", "gadget_media_projects"])
@pytest.mark.parametrize("recover", ["resume", "rollback"])
def test_partial_file_crash_resume_and_byte_exact_rollback(legacy, step, recover):
    before = {p: p.read_bytes() for p in legacy.rglob("*.json")}
    def hook(actual, when):
        if (actual, when) == (step, "after_item"):
            raise cm.SimulatedCrash()
    with pytest.raises(cm.SimulatedCrash):
        apply(legacy, hook=hook)
    migrator = cm.Migrator(legacy)
    if recover == "resume":
        assert migrator.resume()["status"] == "applied"
    assert migrator.rollback()["status"] == "rolled_back"
    assert all(path.read_bytes() == value for path, value in before.items())


def test_rollback_restores_null_owner_and_preserves_newer_edits_and_records(legacy):
    apply(legacy)
    paths = cm.MigrationPaths.for_root(legacy)
    project_path = paths.gadget_projects / "legacy-project/project.json"
    write(project_path, {**read(project_path), "audience": "newer edit", "new_field": "keep"})
    campaigns = read(paths.campaigns_json)
    campaigns[0]["name"] = "newer campaign"
    campaigns.append({"campaign_id": "newer", "channel_id": "second", "unknown": "keep"})
    write(paths.campaigns_json, campaigns)
    assert cm.Migrator(legacy).rollback()["status"] == "rolled_back"
    project = read(project_path)
    assert "channel_id" in project and project["channel_id"] is None
    assert project["audience"] == "newer edit" and project["new_field"] == "keep"
    campaigns = read(paths.campaigns_json)
    assert "channel_id" not in campaigns[0] and campaigns[0]["name"] == "newer campaign"
    assert campaigns[1]["channel_id"] == "second" and campaigns[1]["unknown"] == "keep"


def test_gadget_snapshot_relocation_and_newer_record_restore_guard(legacy, tmp_path):
    apply(legacy)
    migrator = cm.Migrator(legacy)
    state = migrator.current_run()
    manifest = legacy / state["snapshot_manifest"]
    restored = tmp_path / "restored"
    cm.restore_snapshot(manifest, restored)
    assert cm.verify_restore(manifest, restored)["ok"]
    assert read(restored / "03_Projects/GadgetMedia/legacy-project/project.json")["channel_id"] is None
    project_path = legacy / "03_Projects/GadgetMedia/legacy-project/project.json"
    write(project_path, {**read(project_path), "audience": "new work"})
    with pytest.raises(cm.MigrationError, match="ข้อมูลใหม่"):
        migrator.restore_snapshot_in_place()
