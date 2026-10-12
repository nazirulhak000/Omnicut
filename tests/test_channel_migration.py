"""Channel-ownership migration tool + maintenance lock (multi-channel P2.3).

Plan: _Docs/Plans/PLAN_MULTI_CHANNEL_20261010.md §8, §10 (AC13, AC17), §11.
Runbook: _Docs/Plans/MIGRATION_RUNBOOK_MULTI_CHANNEL_20261010.md.

Offline + tmp roots only.  Every DocumentTable connection is asserted to live
under pytest's temp dir, and ``test_root_isolation_audit`` proves with a
``sys.addaudithook`` that a ``--root <tmp>`` run never opens/writes the real
project data.  Fixture shapes follow the real stores described in
_Docs/Reports/MULTI_CHANNEL_P0_STORE_INVENTORY_20261010.json.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict

import pytest

from scripts import channel_migration as cm
from scripts import config, db, maintenance_lock
from scripts.db import DocumentTable
from scripts.maintenance_lock import MaintenanceModeError

REPO = Path(__file__).resolve().parent.parent
MAIN_URL = "https://www.tiktok.com/@rizanntry/video/{}"


# --------------------------------------------------------------------------- guards


@pytest.fixture(autouse=True)
def _only_tmp_databases(tmp_path_factory, monkeypatch):
    """Fail loudly if anything here opens a store database outside pytest's
    temp area (e.g. the real _Docs/store.db)."""
    real = db._connection_for
    base = tmp_path_factory.getbasetemp().resolve()

    def guarded(db_path):
        resolved = Path(db_path).resolve()
        assert base in resolved.parents, f"opened a non-tmp database: {resolved}"
        return real(db_path)

    monkeypatch.setattr(db, "_connection_for", guarded)
    monkeypatch.delenv(config.MULTI_CHANNEL_STRICT_ENV, raising=False)
    yield
    cache = getattr(db._local, "conns", None) or {}
    for key in list(cache):
        if base in Path(key).parents:
            cache.pop(key).close()
            db._wal_enabled_paths.discard(key)


# --------------------------------------------------------------------------- fixture world

PRODUCTS = [
    {
        "id": "p1", "name": "Prod One", "url": "https://shop.example/p1", "product_code": "PRO01", "status": "posted",
        "angles": [{"angle_id": "spec_review", "batch": 1, "status": "posted", "project_name": "P1-spec_1"}],
        "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-02T00:00:00",
    },
    {
        "id": "p2", "name": "Prod Two", "url": "https://shop.example/p2", "product_code": "PRO02", "status": "scripted",
        "angles": [{"angle_id": "spec_review", "batch": 1, "status": "rendered"}],
        "created_at": "2026-01-03T00:00:00", "updated_at": "2026-01-04T00:00:00",
    },
]
EXPORTS = [
    {"id": "exp_1", "path": "04_Exports/Posted/P1_spec_v1.mp4", "path_key": "04_exports/posted/p1_spec_v1.mp4", "product_id": "p1", "angle_id": "spec_review", "project_name": "P1-spec_1", "status": "posted", "created_at": "2026-01-05T00:00:00", "updated_at": "2026-01-05T00:00:00"},
    {"id": "exp_2", "path": "04_Exports/Ready_to_post/P1_other_v1.mp4", "product_id": None, "project_name": "P1-spec_1", "status": "rendered", "created_at": "2026-01-05T00:00:00"},
    {"id": "exp_3", "path": "04_Exports/Ready_to_post/ghost_v1.mp4", "project_name": "ghost_1", "status": "rendered", "created_at": "2026-01-05T00:00:00"},
    {"id": "exp_4", "path": "04_Exports/Posted/orphan_v1.mp4", "product_id": "gone", "status": "posted", "created_at": "2026-01-05T00:00:00"},
    {"id": "exp_5", "path": "04_Exports/Posted/dup.mp4", "product_id": "p1", "status": "posted", "created_at": "2026-01-05T00:00:00"},
    {"id": "exp_6", "path": "04_Exports/Ready_to_post/dup.mp4", "product_id": "p2", "status": "rendered", "created_at": "2026-01-05T00:00:00"},
    {"id": "exp_7", "path": "04_Exports/Posted/P2_spec_v1.mp4", "product_id": "p2", "project_name": "P2-spec_1", "status": "posted", "created_at": "2026-01-05T00:00:00"},
]
POSTS = [
    {"id": "post_1", "clip_file": "C:\\old\\04_Exports\\Posted\\P1_spec_v1.mp4", "tiktok_url": MAIN_URL.format(1), "posted_at": "2026-01-06T00:00:00", "source": "tiktok_stats_auto"},
    {"id": "post_2", "clip_file": "clip.mp4", "tiktok_url": MAIN_URL.format(2), "posted_at": "2026-01-06T00:00:00", "source": "tiktok_stats_auto"},
    {"id": "post_3", "clip_file": "dup.mp4", "tiktok_url": MAIN_URL.format(3), "posted_at": "2026-01-06T00:00:00"},
    {"id": "post_4", "clip_file": "P2_spec_v1.mp4", "export_id": "exp_7", "tiktok_url": MAIN_URL.format(4), "posted_at": "2026-01-06T00:00:00"},
    {"id": "post_5", "clip_file": "nomatch.mp4", "tiktok_url": MAIN_URL.format(5), "posted_at": "2026-01-06T00:00:00"},
]
QUEUE = [
    {"id": "q1", "export_id": "exp_1", "product_id": "p1", "scheduled_at": "2026-01-07T19:00:00+07:00", "status": "posted", "created_at": "2026-01-06T00:00:00"},
    {"id": "q2", "product_id": "p2", "scheduled_at": "2026-01-08T19:00:00+07:00", "status": "planned", "created_at": "2026-01-06T00:00:00"},
    {"id": "q3", "scheduled_at": "2026-01-09T19:00:00+07:00", "status": "planned", "created_at": "2026-01-06T00:00:00"},
]
TEMPLATES = [
    {"id": "default", "days": {"mon": ["19:00"]}, "updated_at": "2026-01-01T00:00:00"},
    {"id": "week:2026-09-07", "days": {"mon": ["20:00"]}, "week_start": "2026-09-07", "updated_at": "2026-09-01T00:00:00"},
]
SHOT_LISTS = [
    {"id": "p1:spec_review", "product_id": "p1", "angle_id": "spec_review", "shot_list": [], "updated_at": "2026-01-02T00:00:00"},
    {"id": "ghost:spec_review", "product_id": "ghost", "angle_id": "spec_review", "shot_list": [], "updated_at": "2026-01-02T00:00:00"},
]
RECORDINGS = [{"id": "rec_1", "product_id": "p1", "angle_id": "spec_review", "status": "finalized", "segments": [], "created_at": "2026-01-02T00:00:00"}]
BATCHES = [
    {"id": "b1", "batch_id": "b1", "product_id": "p1", "status": "completed", "items": [], "created_at": 1},
    {"id": "b2", "batch_id": "b2", "product_id": "ghost", "status": "completed", "items": [], "created_at": 2},
]
TASKS = {
    "t1": {"id": "t1", "type": "render", "status": "completed", "payload": {"product_id": "p1"}, "created_at": "2026-01-02T00:00:00"},
    "t2": {"id": "t2", "type": "voice", "status": "completed", "payload": {}, "created_at": "2026-01-02T00:00:00"},
}
MANIFESTS = {
    "P1-spec_1": {"manifest_version": 1, "project_name": "P1-spec_1", "created_at": "2026-01-02T00:00:00", "artifacts": {"video": {"path": "04_Exports/Posted/P1_spec_v1.mp4"}}, "export_id": "exp_1", "render_params": {"product_id": "p1", "angle_id": "spec_review"}, "updated_at": "2026-01-03T00:00:00"},
    "P2-spec_1": {"manifest_version": 1, "project_name": "P2-spec_1", "render_params": {"product_id": "p2", "angle_id": "spec_review"}, "_editor_revision": 4},
    "Weird_1": {"manifest_version": 1, "project_name": "Weird_1", "render_params": {}},
}
CAMPAIGNS = [{"campaign_id": "c1", "name": "Gadget", "account_role": "gadget_media", "slots": [{"slot_id": "s1"}]}]

EXPECTED_BACKFILL = {
    "products": {"p1", "p2"},
    "export_registry": {"exp_1", "exp_2", "exp_5", "exp_6", "exp_7"},
    "posts": {"post_1", "post_4"},
    "schedule_queue": {"q1", "q2"},
    "shot_lists": {"p1:spec_review"},
    "recording_sessions": {"rec_1"},
    "batch_render_queue": {"b1"},
    "task_registry": {"t1"},
    "manifests": {"P1-spec_1", "P2-spec_1"},
}
EXPECTED_UNKNOWN = {
    ("gadget_media_campaigns", "c1"): "gadget_owner_required",
    ("export_registry", "exp_3"): "manifest_missing",
    ("export_registry", "exp_4"): "product_not_found",
    ("posts", "post_2"): "generic_clip_name",
    ("posts", "post_3"): "ambiguous_basename",
    ("posts", "post_5"): "no_matching_export",
    ("schedule_queue", "q3"): "no_parent_reference",
    ("shot_lists", "ghost:spec_review"): "product_not_found",
    ("batch_render_queue", "b2"): "product_not_found",
    ("task_registry", "t2"): "no_parent_reference",
    ("manifests", "Weird_1"): "no_parent_reference",
}


def _table(root: Path, spec: cm.TableSpec) -> DocumentTable:
    paths = cm.MigrationPaths.for_root(root)
    return DocumentTable(spec.table, lambda: paths.db_for(spec), lambda: paths.mirror_for(spec))


def build_root(root: Path, *, posts=None, products=None, registry: bool = False) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "_Docs").mkdir(exist_ok=True)
    data = {
        "products": products if products is not None else PRODUCTS,
        "export_registry": EXPORTS,
        "posts": posts if posts is not None else POSTS,
        "schedule_queue": QUEUE,
        "schedule_templates": TEMPLATES,
        "shot_lists": SHOT_LISTS,
        "recording_sessions": RECORDINGS,
        "tiktok_pending": [],
        "batch_render_queue": BATCHES,
    }
    for name, rows in data.items():
        _table(root, cm.TABLE_BY_NAME[name]).save(json.loads(json.dumps(rows)))
    projects = root / "03_Projects"
    projects.mkdir(exist_ok=True)
    (projects / "task_registry.json").write_text(json.dumps(TASKS, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, manifest in MANIFESTS.items():
        (projects / name).mkdir(exist_ok=True)
        (projects / name / "project.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (projects / "NoManifest_1").mkdir(exist_ok=True)
    (projects / "NoManifest_1" / "voiceover.txt").write_text("vo", encoding="utf-8")
    (root / "_Docs" / "gadget_media_campaigns.json").write_text(json.dumps(CAMPAIGNS, indent=2), encoding="utf-8")
    cm._close_cached_connections(root)
    return root


def tree_state(root: Path, *, skip_archive: bool = True) -> Dict[str, tuple]:
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not (skip_archive and "06_Archive" in path.parts):
            st = path.stat()
            out[path.relative_to(root).as_posix()] = (st.st_size, st.st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
    return out


def data_state(root: Path) -> Dict[str, Any]:
    """Logical content of every store (+ byte hashes of mirrors/manifests/tasks)."""
    world = cm.load_world(cm.MigrationPaths.for_root(root))
    paths = cm.MigrationPaths.for_root(root)
    return {
        "tables": {name: {str(r["id"]): cm.canon(r) for r in (rows or [])} for name, rows in world.tables.items()},
        "manifests": {name: doc.sha256 for name, doc in world.manifests.items()},
        "tasks": world.tasks.sha256,
        "mirrors": {spec.name: (hashlib.sha256(paths.mirror_for(spec).read_bytes()).hexdigest() if paths.mirror_for(spec).exists() else None) for spec in cm.TABLES},
    }


def plan_hash(root: Path, **options) -> str:
    return cm.Migrator(root).dry_run(**options)["plan"]["plan_hash"]


def apply(root: Path, **options) -> Dict[str, Any]:
    migrator = cm.Migrator(root)
    return migrator.apply(expect_plan=plan_hash(root, **options), **options)


def _writer_in_thread(root: Path) -> BaseException | None:
    """Try a real write from another thread (no bypass); return its error."""
    box: list = []

    def run():
        try:
            table = _table(root, cm.TABLE_BY_NAME["products"])
            with table.mutate() as rows:
                rows.append({"id": "intruder", "name": "x"})
        except BaseException as exc:  # noqa: BLE001
            box.append(exc)
        finally:
            cm._close_cached_connections(root)

    thread = threading.Thread(target=run)
    thread.start()
    thread.join(30)
    return box[0] if box else None


@pytest.fixture
def root(tmp_path) -> Path:
    return build_root(tmp_path / "root")


@pytest.fixture(scope="module")
def reference(tmp_path_factory) -> Dict[str, Any]:
    """Pre-state and clean-apply end state of the fixture world."""
    base = tmp_path_factory.mktemp("reference")
    pre_root = build_root(base / "pre")
    pre = data_state(pre_root)
    done_root = build_root(base / "done")
    result = apply(done_root)
    assert result["status"] == "applied"
    post = data_state(done_root)
    cm._close_cached_connections(base)
    return {"pre": pre, "post": post}


# --------------------------------------------------------------------------- planning


def test_dry_run_backfills_by_evidence_and_reports_unknowns(root):
    result = cm.Migrator(root).dry_run()
    plan = result["plan"]
    assert result["preflight"]["blockers"] == 0
    assert plan["evidence"]["legacy_owner"] == "main"
    assert plan["evidence"]["post_handles"] == {"@rizanntry": 5}
    backfill: Dict[str, set] = {}
    for action in plan["actions"]:
        assert action["owner"] == "main"
        backfill.setdefault(action["store"], set()).add(action["id"])
    assert backfill == EXPECTED_BACKFILL
    unknown = {(d["store"], d["id"]): d["reason"] for d in plan["decisions"] if d["status"] == "unknown"}
    assert unknown == EXPECTED_UNKNOWN
    for d in plan["decisions"]:
        if d["status"] == "unknown":
            assert d["reason_th"] and d.get("suggested_action")
    # parent-derived evidence is recorded
    by_key = {(d["store"], d["id"]): d for d in plan["decisions"]}
    assert by_key[("posts", "post_3")]["detail"]["candidate_exports"] == ["exp_5", "exp_6"]
    assert by_key[("posts", "post_2")]["detail"]["handle_matches_channel"] == ["main"]
    templates = {d["id"]: d for d in plan["decisions"] if d["store"] == "schedule_templates"}
    assert {d["status"] for d in templates.values()} == {"deferred"}
    assert plan["stores"]["gadget_media_campaigns"]["unknown"] == 1
    assert result["inventory"]["project_dirs_without_manifest"] == ["NoManifest_1"]
    report_text = cm.render_report_markdown(result)
    assert plan["plan_hash"] in report_text and "clip.mp4" in report_text


def test_dry_run_is_read_only(root, tmp_path):
    before = tree_state(root, skip_archive=False)
    report = tmp_path / "out" / "report"
    (tmp_path / "out").mkdir()
    for _ in range(2):  # twice: nothing may accumulate either
        result = cm.Migrator(root).dry_run()
        cm.write_report(result, report)
    assert tree_state(root, skip_archive=False) == before
    assert not any(p.name.endswith(("-wal", "-shm", "-journal")) for p in root.rglob("*"))
    assert (tmp_path / "out" / "report.md").exists() and (tmp_path / "out" / "report.json").exists()
    assert "token" not in (tmp_path / "out" / "report.json").read_text(encoding="utf-8").lower().replace("token_", "")


def test_dry_run_with_live_wal_creates_no_files(root):
    """A WAL db with -wal/-shm present (live server) is read via mode=ro."""
    conn = db._connection_for(cm.MigrationPaths.for_root(root).store_db)
    conn.execute("SELECT 1 FROM products").fetchall()
    wal_names = sorted(p.name for p in (root / "_Docs").iterdir())
    before = tree_state(root / "_Docs")
    cm.Migrator(root).dry_run()
    assert sorted(p.name for p in (root / "_Docs").iterdir()) == wal_names
    after = tree_state(root / "_Docs")
    assert {k: v for k, v in after.items() if not k.endswith("-shm")} == {k: v for k, v in before.items() if not k.endswith("-shm")}


def test_conflicting_handle_disables_legacy_cohort(tmp_path):
    posts = json.loads(json.dumps(POSTS))
    posts[0]["tiktok_url"] = "https://www.tiktok.com/@someone_else/video/9"
    root = build_root(tmp_path / "r", posts=posts)
    plan = cm.Migrator(root).dry_run()["plan"]
    assert plan["evidence"]["legacy_owner"] is None
    statuses = {(d["store"], d["id"]): (d["status"], d["reason"]) for d in plan["decisions"]}
    assert statuses[("products", "p1")] == ("unknown", "legacy_owner_undecided")
    # nothing below an unknown product is derived
    assert statuses[("export_registry", "exp_1")] == ("unknown", "parent_unknown")
    assert plan["actions"] == []
    # explicit owner decision re-enables it, and the foreign-handle post is a conflict
    plan2 = cm.Migrator(root).dry_run(legacy_owner="main")["plan"]
    statuses2 = {(d["store"], d["id"]): (d["status"], d["reason"]) for d in plan2["decisions"]}
    assert statuses2[("posts", "post_1")] == ("conflict", "handle_mismatch")
    assert statuses2[("products", "p1")] == ("backfill", "legacy_owner_option")


def test_existing_owner_kept_and_unregistered_owner_is_conflict(tmp_path):
    products = json.loads(json.dumps(PRODUCTS))
    products[0]["channel_id"] = "main"
    products[1]["channel_id"] = "ghostchan"
    root = build_root(tmp_path / "r", products=products)
    plan = cm.Migrator(root).dry_run()["plan"]
    statuses = {(d["store"], d["id"]): (d["status"], d["reason"]) for d in plan["decisions"]}
    assert ("products", "p1") not in statuses  # already owned -> not pending
    assert statuses[("products", "p2")] == ("conflict", "unregistered_channel_id")
    assert {a["id"] for a in plan["actions"] if a["store"] == "products"} == set()
    assert statuses[("export_registry", "exp_7")] == ("unknown", "parent_unknown")


# --------------------------------------------------------------------------- apply


def test_apply_backfills_parents_before_children_and_validates(root):
    result = apply(root)
    assert result["status"] == "applied" and result["rows"] == 17
    world = cm.load_world(cm.MigrationPaths.for_root(root))
    for store, ids in EXPECTED_BACKFILL.items():
        if store == "task_registry":
            rows = {k: v for k, v in world.tasks.data.items()}
        elif store == "manifests":
            rows = {k: v.data for k, v in world.manifests.items()}
        else:
            rows = {str(r["id"]): r for r in world.rows(store)}
        for rid, row in rows.items():
            if rid in ids:
                assert row.get("channel_id") == "main", (store, rid)
            else:
                assert "channel_id" not in row, (store, rid)
    for product in world.rows("products"):
        assert all("channel_id" not in a for a in product["angles"])  # angles inherit
    assert cm.ownership_violations(world) == []
    for spec in cm.TABLES:
        assert cm._mirror_matches(world, spec.name) in (True, None), spec.name
    assert world.integrity == {"store": "ok", "batch": "ok"}
    journal = cm.Journal(cm.MigrationPaths.for_root(root).run_dir(result["run_id"]) / "journal.jsonl", [root])
    done = [e["step"] for e in journal.events() if e.get("event") == "done"]
    order = [s for s in cm.STEP_ORDER if s in done]
    assert done == order  # journal follows parent -> child order
    for event in journal.events():
        if event.get("event") == "done" and event["step"] in ("products", "posts"):
            for row in event["rows"]:
                assert row["added"] == {"channel_id": "main"} and row["before_hash"] != row["after_hash"]
    assert not maintenance_lock.is_locked(root)
    state = cm.Migrator(root).current_run()
    assert state["status"] == "applied" and state["post_fingerprint"] == cm.fingerprint(cm.MigrationPaths.for_root(root))


def test_manifest_rewrite_is_minimal_atomic_and_journaled(root):
    path = root / "03_Projects" / "P1-spec_1" / "project.json"
    original = path.read_bytes()
    result = apply(root)
    new = path.read_bytes()
    newline = b"\r\n" if original[1:3] == b"\r\n" else b"\n"  # fixture follows the OS text mode
    segment = newline + b'  "channel_id": "main",'
    assert new == original[:1] + segment + original[1:]
    assert not list(path.parent.glob("*.bak*")) and not list(path.parent.glob("*tmp*"))
    other = root / "03_Projects" / "Weird_1" / "project.json"
    assert json.loads(other.read_text(encoding="utf-8")) == MANIFESTS["Weird_1"]
    journal = cm.Journal(cm.MigrationPaths.for_root(root).run_dir(result["run_id"]) / "journal.jsonl", [root])
    items = {e["id"]: e for e in journal.events() if e.get("event") == "item"}
    assert items["P1-spec_1"]["before_hash"] == hashlib.sha256(original).hexdigest()
    assert items["P1-spec_1"]["after_hash"] == hashlib.sha256(new).hexdigest()


@pytest.mark.parametrize(
    "text",
    [
        '{\n  "a": 1\n}',
        '{\r\n    "a": [1, 2]\r\n}\r\n',
        '\ufeff{\n\t"a": 1\n}',
        '{"a":1,"b":{"c":2}}',
        "{}",
        "  {  }",
    ],
)
def test_insert_top_level_key_changes_nothing_else(text):
    new, segment = cm.insert_top_level_key(text, "channel_id", "main")
    assert new.replace(segment, "", 1) == text
    data = json.loads(new.lstrip("\ufeff"))
    assert data.pop("channel_id") == "main"
    assert data == json.loads(text.lstrip("\ufeff"))


def test_second_apply_is_noop_and_byte_identical(root):
    apply(root)
    before = tree_state(root, skip_archive=False)
    second = apply(root)
    assert second == {"status": "noop", "writes": 0, "plan_hash": second["plan_hash"], "message": second["message"]}
    assert tree_state(root, skip_archive=False) == before
    assert not maintenance_lock.is_locked(root)


def test_apply_refuses_unreviewed_plan(root):
    before = tree_state(root, skip_archive=False)
    with pytest.raises(cm.PlanMismatch):
        cm.Migrator(root).apply(expect_plan="0" * 64)
    with pytest.raises(cm.PlanMismatch):
        cm.Migrator(root).apply(expect_plan="")
    # the plan hash changes with any owner decision
    assert plan_hash(root) != plan_hash(root, rename_templates=True)
    assert tree_state(root, skip_archive=False) == before


def test_template_rename_is_opt_in_and_reversible(root):
    templates_mirror = root / "_Docs" / "schedule_templates.json"
    original = templates_mirror.read_bytes()
    apply(root)
    ids = {r["id"] for r in json.loads(templates_mirror.read_text(encoding="utf-8"))}
    assert ids == {"default", "week:2026-09-07"}  # deferred by default
    apply(root, rename_templates=True)
    rows = {r["id"]: r for r in json.loads(templates_mirror.read_text(encoding="utf-8"))}
    assert set(rows) == {"main:default", "main:week:2026-09-07"}
    assert rows["main:week:2026-09-07"]["legacy_id"] == "week:2026-09-07"
    assert rows["main:week:2026-09-07"]["channel_id"] == "main"
    assert rows["main:week:2026-09-07"]["days"] == TEMPLATES[1]["days"]
    result = cm.Migrator(root).rollback()
    assert result["status"] == "rolled_back" and result["exact"] == 2
    restored = {r["id"]: r for r in json.loads(templates_mirror.read_text(encoding="utf-8"))}
    assert restored == {t["id"]: t for t in TEMPLATES}
    assert {cm.canon(r) for r in json.loads(original)} == {cm.canon(r) for r in restored.values()}


def test_assign_mapping_is_row_level_and_validated(root, tmp_path):
    mapping = tmp_path / "assign.json"
    mapping.write_text(json.dumps({
        "schema": "omnicut.channel_assign.v1",
        "assignments": [
            {"store": "posts", "id": "post_2", "channel_id": "main", "note": "ตรวจบน TikTok แล้ว"},
            {"store": "shot_lists", "id": "ghost:spec_review", "channel_id": "main"},
        ],
    }), encoding="utf-8")
    assignments = cm.load_assignments(mapping)
    plan = cm.Migrator(root).dry_run(assignments=assignments)["plan"]
    assert plan["plan_hash"] != plan_hash(root)
    by = {(a["store"], a["id"]): a for a in plan["actions"]}
    assert by[("posts", "post_2")]["owner"] == "main"
    assert ("posts", "post_3") not in by  # still unknown: nothing wholesale
    cm.Migrator(root).apply(expect_plan=plan["plan_hash"], assignments=assignments)
    posts = {r["id"]: r for r in cm.load_world(cm.MigrationPaths.for_root(root)).rows("posts")}
    assert posts["post_2"]["channel_id"] == "main" and "channel_id" not in posts["post_3"]

    def bad(*items):
        return cm.Migrator(root).dry_run(assignments=[dict(i) for i in items])

    with pytest.raises(cm.AssignmentError, match="ไม่รู้จัก store"):
        bad({"store": "nope", "id": "x", "channel_id": "main"})
    with pytest.raises(cm.AssignmentError, match="ไม่มีช่อง"):
        bad({"store": "posts", "id": "post_3", "channel_id": "second"})
    with pytest.raises(cm.AssignmentError, match="ไม่พบแถว"):
        bad({"store": "posts", "id": "post_404", "channel_id": "main"})
    with pytest.raises(cm.AssignmentError, match="Gadget schema/layout"):
        bad({"store": "gadget_media_campaigns", "id": "c1", "channel_id": "main"})
    # repeating the existing owner is a harmless no-op
    assert bad({"store": "products", "id": "p1", "channel_id": "main"})["plan"]["actions"] == []
    broken = tmp_path / "broken.json"
    broken.write_text('{"assignments": [{"store": "posts"}]}', encoding="utf-8")
    with pytest.raises(cm.AssignmentError):
        cm.load_assignments(broken)


def test_assign_rejects_owner_contradicting_evidence(tmp_path):
    from scripts.channel_store import ChannelStore

    root = build_root(tmp_path / "r")
    store = ChannelStore(root / "_Docs" / "channels.json", project_root=root)
    store.seed()
    store.create({"id": "second", "display_name": "Second"})
    # registry now has 2 channels -> legacy cohort needs an explicit decision
    plan = cm.Migrator(root).dry_run()["plan"]
    assert plan["evidence"]["legacy_owner"] is None and plan["actions"] == []
    with pytest.raises(cm.AssignmentError, match="ขัดกับหลักฐาน|ไม่ตรงกับเจ้าของ parent"):
        cm.Migrator(root).dry_run(legacy_owner="main", assignments=[{"store": "export_registry", "id": "exp_1", "channel_id": "second"}])
    plan2 = cm.Migrator(root).dry_run(legacy_owner="main", assignments=[{"store": "posts", "id": "post_2", "channel_id": "second"}])["plan"]
    assert {(a["id"], a["owner"]) for a in plan2["actions"] if a["store"] == "posts"} == {("post_1", "main"), ("post_4", "main"), ("post_2", "second")}


# --------------------------------------------------------------------------- crash / resume / rollback

CRASH_POINTS = [
    ("snapshot", "before"), ("snapshot", "after"),
    ("products", "before"), ("products", "after_commit"), ("products", "after"),
    ("export_registry", "after_commit"), ("posts", "before"), ("posts", "after_commit"),
    ("schedule_queue", "after"), ("shot_lists", "after_commit"), ("recording_sessions", "before"),
    ("batch_render_queue", "after_commit"),
    ("task_registry", "before"), ("task_registry", "after_commit"), ("task_registry", "after"),
    ("manifests", "before"), ("manifests", "after_item"), ("manifests", "after"),
    ("validate", "before"), ("release", "before"),
]


@pytest.mark.parametrize("step,when", CRASH_POINTS)
def test_crash_at_any_step_then_resume_or_rollback(tmp_path, reference, step, when):
    root = build_root(tmp_path / "r")
    expected = plan_hash(root)

    def hook(s, w):
        if (s, w) == (step, when):
            raise cm.SimulatedCrash(f"{s}:{w}")

    with pytest.raises(cm.SimulatedCrash):
        cm.Migrator(root, hook=hook).apply(expect_plan=expected)
    # killed mid-way: lock stays, every other writer is refused
    assert maintenance_lock.is_locked(root)
    err = _writer_in_thread(root)
    assert isinstance(err, MaintenanceModeError)
    with pytest.raises(cm.PreflightBlocked):
        cm.Migrator(root).apply(expect_plan=expected)

    resumed = cm.Migrator(root).resume()
    assert resumed["status"] == "applied"
    assert not maintenance_lock.is_locked(root)
    state = data_state(root)
    assert state["tables"] == reference["post"]["tables"]
    assert state["manifests"] == reference["post"]["manifests"]
    assert state["tasks"] == reference["post"]["tasks"]
    for name, digest in reference["post"]["mirrors"].items():
        assert state["mirrors"][name] == digest, name
    assert cm.Migrator(root).dry_run()["plan"]["actions"] == []  # nothing lost or duplicated

    rolled = cm.Migrator(root).rollback()
    assert rolled["kept_newer"] == 0 and rolled["skipped"] == []
    assert data_state(root) == reference["pre"]


@pytest.mark.parametrize("step,when", [("posts", "after_commit"), ("manifests", "after_item"), ("task_registry", "after_commit")])
def test_rollback_directly_after_crash_restores_pre_state(tmp_path, reference, step, when):
    root = build_root(tmp_path / "r")

    def hook(s, w):
        if (s, w) == (step, when):
            raise cm.SimulatedCrash()

    with pytest.raises(cm.SimulatedCrash):
        cm.Migrator(root, hook=hook).apply(expect_plan=plan_hash(root))
    cm.Migrator(root).rollback()
    assert data_state(root) == reference["pre"]
    assert not maintenance_lock.is_locked(root)


def test_crash_between_commit_and_mirror_write_is_repaired(tmp_path, reference, monkeypatch):
    root = build_root(tmp_path / "r")
    real = DocumentTable._write_json_mirror
    calls = {"n": 0}

    def flaky(self, conn):
        if self._table == "posts" and calls["n"] == 0:
            calls["n"] += 1
            raise cm.SimulatedCrash("killed before mirror write")
        return real(self, conn)

    monkeypatch.setattr(DocumentTable, "_write_json_mirror", flaky)
    with pytest.raises(cm.SimulatedCrash):
        cm.Migrator(root).apply(expect_plan=plan_hash(root))
    # P2.4a (scripts/db.py mirror atomicity): the mirror + marker are written
    # inside the posts write transaction, so a crash in the mirror write rolls
    # the rows back with it -- the old "DB committed, mirror old" window no
    # longer exists.  DB and mirror stay equal (pre-migration) and nothing is
    # pending import; resume then applies posts normally.
    world = cm.load_world(cm.MigrationPaths.for_root(root))
    assert cm._mirror_matches(world, "posts") is True and world.mirror_pending["posts"] is False
    assert data_state(root)["tables"]["posts"] == reference["pre"]["tables"]["posts"]
    cm.Migrator(root).resume()
    assert data_state(root)["tables"] == reference["post"]["tables"]
    assert data_state(root)["mirrors"]["posts"] == reference["post"]["mirrors"]["posts"]


def test_failure_before_any_write_releases_lock(root):
    def hook(step, when):
        if step == "snapshot" and when == "before":
            raise RuntimeError("disk error")

    before = data_state(root)
    with pytest.raises(RuntimeError):
        cm.Migrator(root, hook=hook).apply(expect_plan=plan_hash(root))
    assert not maintenance_lock.is_locked(root)
    assert cm.Migrator(root).current_run()["status"] == "failed_clean"
    assert data_state(root) == before
    assert apply(root)["status"] == "applied"  # a new run can start


def test_failure_after_writes_keeps_lock_until_resume(root, reference):
    def hook(step, when):
        if step == "schedule_queue" and when == "before":
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        cm.Migrator(root, hook=hook).apply(expect_plan=plan_hash(root))
    assert maintenance_lock.is_locked(root)  # fail closed: half-migrated
    assert cm.Migrator(root).current_run()["status"] == "needs_attention"
    assert isinstance(_writer_in_thread(root), MaintenanceModeError)
    cm.Migrator(root).resume()
    assert data_state(root)["tables"] == reference["post"]["tables"]


def test_drift_between_plan_and_apply_is_refused(root):
    expected = plan_hash(root)

    def hook(step, when):
        if step == "posts" and when == "before":
            with maintenance_lock.bypass(maintenance_lock.read_lock(root)["token"]):
                with _table(root, cm.TABLE_BY_NAME["posts"]).mutate() as rows:
                    rows[0]["caption"] = "edited during migration"

    with pytest.raises(cm.DriftError):
        cm.Migrator(root, hook=hook).apply(expect_plan=expected)
    posts = {r["id"]: r for r in cm.load_world(cm.MigrationPaths.for_root(root)).rows("posts")}
    assert all("channel_id" not in r for r in posts.values())  # store transaction rolled back


def test_rollback_after_new_work_keeps_new_data(root):
    apply(root)
    # traffic after cutover: a changed row, a new row, an edited manifest
    with _table(root, cm.TABLE_BY_NAME["products"]).mutate() as rows:
        rows[0]["status"] = "archived_by_user"
        rows.append({"id": "p_new", "name": "New", "channel_id": "main"})
    manifest = root / "03_Projects" / "P2-spec_1" / "project.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["caption_scale"] = 1.2
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    cm._close_cached_connections(root)

    with pytest.raises(cm.MigrationError, match="fingerprint"):
        cm.Migrator(root).restore_snapshot_in_place()
    result = cm.Migrator(root).rollback()
    assert result["kept_newer"] == 2 and result["skipped"] == []
    products = {r["id"]: r for r in cm.load_world(cm.MigrationPaths.for_root(root)).rows("products")}
    assert products["p_new"]["channel_id"] == "main"  # created after cutover: untouched
    assert products[PRODUCTS[0]["id"]]["status"] == "archived_by_user"  # newer edit kept
    assert "channel_id" not in products["p1"] and "channel_id" not in products["p2"]
    restored = json.loads(manifest.read_text(encoding="utf-8"))
    assert restored["caption_scale"] == 1.2 and "channel_id" not in restored


def test_restore_snapshot_in_place_only_without_newer_data(root, reference):
    apply(root)
    result = cm.Migrator(root).restore_snapshot_in_place()
    assert result["status"] == "restored"
    state = data_state(root)
    assert state["tables"] == reference["pre"]["tables"]
    assert state["manifests"] == reference["pre"]["manifests"] and state["tasks"] == reference["pre"]["tasks"]
    assert not maintenance_lock.is_locked(root)


# --------------------------------------------------------------------------- AC13: JSON mirror interplay


def test_pending_mirror_edit_blocks_apply(root):
    mirror = root / "_Docs" / "products.json"
    rows = json.loads(mirror.read_text(encoding="utf-8"))
    rows[0]["name"] = "hand edited"
    mirror.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    result = cm.Migrator(root).dry_run()
    failing = [c["name"] for c in result["preflight"]["checks"] if c["level"] == "blocker" and not c["ok"]]
    assert failing == ["mirror_products"]
    with pytest.raises(cm.PreflightBlocked):
        cm.Migrator(root).apply(expect_plan=result["plan"]["plan_hash"])
    assert not maintenance_lock.is_locked(root)


def test_json_reimport_after_cutover_is_caught_and_rerun(root):
    apply(root)
    # an old tool rewrites the mirror from a pre-migration copy (no channel_id)
    mirror = root / "_Docs" / "products.json"
    legacy = [{k: v for k, v in r.items() if k != "channel_id"} for r in json.loads(mirror.read_text(encoding="utf-8"))]
    mirror.write_text(json.dumps(legacy, ensure_ascii=False, indent=2), encoding="utf-8")
    loaded = _table(root, cm.TABLE_BY_NAME["products"]).load()  # auto-import
    cm._close_cached_connections(root)
    assert all("channel_id" not in r for r in loaded)
    plan = cm.Migrator(root).dry_run()["plan"]
    assert {a["id"] for a in plan["actions"]} == {"p1", "p2"}
    apply(root)
    world = cm.load_world(cm.MigrationPaths.for_root(root))
    assert {r["channel_id"] for r in world.rows("products")} == {"main"}
    assert len(world.rows("products")) == len(PRODUCTS)
    assert cm._mirror_matches(world, "products") is True


def test_mirror_is_not_imported_while_locked(root):
    info = maintenance_lock.acquire(root, owner="test", reason="test")
    try:
        mirror = root / "_Docs" / "products.json"
        mirror.write_text("[]", encoding="utf-8")
        assert len(_table(root, cm.TABLE_BY_NAME["products"]).load()) == len(PRODUCTS)
    finally:
        maintenance_lock.release(root, info["token"])
        cm._close_cached_connections(root)


# --------------------------------------------------------------------------- maintenance lock


def test_lock_blocks_writers_but_not_reads_or_noop_blocks(root):
    table = _table(root, cm.TABLE_BY_NAME["products"])
    info = maintenance_lock.acquire(root, owner="test", reason="ทดสอบ", run_id="r1")
    try:
        assert len(table.load()) == len(PRODUCTS)
        with table.mutate() as rows:  # no change -> commits fine (reads that might write)
            assert len(rows) == len(PRODUCTS)
        with pytest.raises(MaintenanceModeError) as exc:
            table.save([])
        assert exc.value.status_code == 503 and "maintenance" in str(exc.value)
        with pytest.raises(MaintenanceModeError):
            with table.mutate() as rows:
                rows.append({"id": "x"})
        with pytest.raises(MaintenanceModeError):
            with table.scoped_mutate("main", include_legacy=True) as rows:
                rows[0]["name"] = "changed"
        assert isinstance(_writer_in_thread(root), MaintenanceModeError)
        # the lock holder writes through its token; other threads stay blocked
        with maintenance_lock.bypass(info["token"]):
            with table.mutate() as rows:
                rows[0]["name"] = "by migration"
            assert isinstance(_writer_in_thread(root), MaintenanceModeError)
        assert {r["id"] for r in table.load()} == {p["id"] for p in PRODUCTS}
    finally:
        assert maintenance_lock.release(root, info["token"])
    assert _writer_in_thread(root) is None
    cm._close_cached_connections(root)


def test_lock_file_contents_and_busy(root):
    info = maintenance_lock.acquire(root, owner="o", reason="r", run_id="run")
    try:
        stored = maintenance_lock.read_lock(root)
        assert stored["pid"] == os.getpid() and stored["host"] == socket.gethostname()
        assert stored["stale"] is False and stored["started_at"]
        with pytest.raises(maintenance_lock.MaintenanceLockBusy):
            maintenance_lock.acquire(root, owner="o2", reason="r2")
        with pytest.raises(maintenance_lock.MaintenanceLockBusy):
            maintenance_lock.acquire(root, owner="o2", reason="r2", take_over_stale=True)
        assert maintenance_lock.release(root, "wrong-token") is False
        assert maintenance_lock.is_locked(root)
    finally:
        assert maintenance_lock.release(root, info["token"])


def _dead_pid() -> int:
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


def test_stale_lock_still_blocks_and_needs_explicit_release(root):
    lock = maintenance_lock.lock_path(root)
    lock.write_text(json.dumps({"owner": "crashed", "pid": _dead_pid(), "host": socket.gethostname(), "token": "t0", "started_at": "x"}), encoding="utf-8")
    info = maintenance_lock.read_lock(root)
    assert info["stale"] is True
    assert isinstance(_writer_in_thread(root), MaintenanceModeError)  # fail closed
    with pytest.raises(maintenance_lock.MaintenanceLockBusy):
        maintenance_lock.acquire(root, owner="x", reason="y")
    assert cm.Migrator(root).release_stale_lock()["status"] == "released"
    assert not maintenance_lock.is_locked(root)


def test_stale_lock_of_unfinished_run_cannot_be_released(tmp_path):
    root = build_root(tmp_path / "r")

    def hook(step, when):
        if step == "posts" and when == "before":
            raise cm.SimulatedCrash()

    with pytest.raises(cm.SimulatedCrash):
        cm.Migrator(root, hook=hook).apply(expect_plan=plan_hash(root))
    lock = json.loads(maintenance_lock.lock_path(root).read_text(encoding="utf-8"))
    lock["pid"] = _dead_pid()
    maintenance_lock.lock_path(root).write_text(json.dumps(lock), encoding="utf-8")
    with pytest.raises(cm.MigrationError, match="resume"):
        cm.Migrator(root).release_stale_lock()
    assert cm.Migrator(root).resume()["status"] == "applied"


def test_corrupt_lock_blocks_writers(root):
    maintenance_lock.lock_path(root).write_text("{not json", encoding="utf-8")
    assert maintenance_lock.read_lock(root)["corrupt"] is True
    assert isinstance(_writer_in_thread(root), MaintenanceModeError)
    maintenance_lock.lock_path(root).unlink()


def test_api_gate_returns_503_for_writes_only(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    lock_root = tmp_path / "apiroot"
    (lock_root / "_Docs").mkdir(parents=True)
    app = FastAPI()

    @app.get("/r")
    def read():
        return {"ok": True}

    @app.post("/w")
    def write():
        return {"ok": True}

    @app.get("/reconcile")
    def reconcile():
        maintenance_lock.assert_writable(lock_root)
        return {"ok": True}

    maintenance_lock.install_maintenance_gate(app, root_fn=lambda: lock_root)
    client = TestClient(app)
    assert client.post("/w").status_code == 200
    info = maintenance_lock.acquire(lock_root, owner="t", reason="ทดสอบ")
    try:
        assert client.get("/r").status_code == 200
        for method in ("post", "put", "patch", "delete"):
            response = getattr(client, method)("/w")
            assert response.status_code in (503, 405)
        response = client.post("/w")
        assert response.status_code == 503
        assert response.json()["code"] == "maintenance_mode"
        assert response.headers["X-OmniCut-Error-Code"] == "maintenance_mode"
        assert "maintenance" in response.json()["detail"]
        response = client.get("/reconcile")  # a GET that wants to write -> 503 not 500
        assert response.status_code == 503 and response.json()["code"] == "maintenance_mode"
    finally:
        maintenance_lock.release(lock_root, info["token"])
    assert client.post("/w").status_code == 200


def test_real_app_has_gate_and_no_new_routes():
    import scripts.api_server as api_server

    names = [m.cls.__name__ for m in api_server.app.user_middleware]
    assert "MaintenanceGateMiddleware" in names
    assert names[-1] == "MaintenanceGateMiddleware"  # innermost
    assert MaintenanceModeError in api_server.app.exception_handlers
    assert not [r for r in api_server.app.routes if getattr(getattr(r, "endpoint", None), "__module__", "") == "scripts.maintenance_lock"]


def test_workers_refuse_new_jobs(root, monkeypatch):
    from scripts import batch_queue_store, task_manager
    from scripts.batch_render import BatchRenderManager

    monkeypatch.setattr(task_manager, "TASKS_FILE", root / "03_Projects" / "task_registry.json")
    monkeypatch.setattr(batch_queue_store, "BATCH_QUEUE_PATH", root / "03_Projects" / "batch_render_queue.json")
    before = tree_state(root)
    info = maintenance_lock.acquire(root, owner="t", reason="r")
    try:
        with pytest.raises(MaintenanceModeError):
            task_manager.TaskManager.create_task("render", "x")
        with pytest.raises(MaintenanceModeError):
            BatchRenderManager.create_batch("p1")
        assert BatchRenderManager.recover_pending_batches() == 0
        BatchRenderManager._dispatch_pending_batches()  # returns at once, starts nothing
    finally:
        maintenance_lock.release(root, info["token"])
    assert {k: v for k, v in tree_state(root).items() if not k.endswith(".lock")} == before


# --------------------------------------------------------------------------- AC17: backup / restore rehearsal


def test_restore_rehearsal_and_verify(root, tmp_path):
    before = tree_state(root, skip_archive=False)
    verdict = cm.rehearse_restore(root, tmp_path / "rehearsal")
    assert verdict["ok"], verdict["problems"]
    assert verdict["stores_opened"]["products"] == len(PRODUCTS)
    assert verdict["stores_opened"]["batch_render_queue"] == len(BATCHES)
    assert tree_state(root, skip_archive=False) == before  # read-only on the source
    manifest = json.loads((tmp_path / "rehearsal" / "snapshot" / "manifest.json").read_text(encoding="utf-8"))
    kinds = {e["rel"]: e["kind"] for e in manifest["files"]}
    assert kinds["_Docs/store.db"] == "sqlite" and kinds["03_Projects/batch_render_queue.db"] == "sqlite"
    assert "03_Projects/P1-spec_1/project.json" in kinds and "03_Projects/task_registry.json" in kinds
    assert all(len(e["sha256"]) == 64 for e in manifest["files"])
    # a tampered snapshot is detected
    target = tmp_path / "rehearsal" / "snapshot" / "_Docs" / "products.json"
    target.write_text("[]", encoding="utf-8")
    with pytest.raises(cm.MigrationError, match="เสีย"):
        cm.restore_snapshot(tmp_path / "rehearsal" / "snapshot" / "manifest.json", tmp_path / "again")
    verdict2 = cm.verify_restore(tmp_path / "rehearsal" / "snapshot" / "manifest.json", tmp_path / "rehearsal" / "restored")
    assert verdict2["ok"]  # restored copy itself is intact
    with pytest.raises(cm.MigrationError, match="นอก root"):
        cm.rehearse_restore(root, root / "inside")


def test_restore_refuses_to_overwrite(root, tmp_path):
    verdict = cm.rehearse_restore(root, tmp_path / "w")
    with pytest.raises(cm.MigrationError, match="ไม่เขียนทับ"):
        cm.restore_snapshot(Path(verdict["snapshot"]) / "manifest.json", Path(verdict["restored_root"]))


def test_apply_snapshot_is_wal_consistent(root):
    # uncommitted-to-main-file pages live in -wal while a connection is open
    conn = db._connection_for(cm.MigrationPaths.for_root(root).store_db)
    conn.execute("PRAGMA wal_autocheckpoint=0")
    with _table(root, cm.TABLE_BY_NAME["products"]).mutate() as rows:
        rows.append({"id": "p_wal", "name": "only in wal"})
    assert (root / "_Docs" / "store.db-wal").stat().st_size > 0
    result = apply(root)
    snap = root / Path(cm.Migrator(root).current_run()["snapshot_manifest"]).parent
    with cm.ro_connect(snap / "_Docs" / "store.db") as snap_conn:
        ids = {r["id"] for r in cm._read_rows(snap_conn, "products")}
    assert "p_wal" in ids and result["status"] == "applied"


# --------------------------------------------------------------------------- isolation


def test_atomic_write_refuses_outside_root(tmp_path):
    with pytest.raises(cm.RootViolation):
        cm.atomic_write_bytes(tmp_path / "outside.json", b"{}", allowed_roots=[tmp_path / "root"])
    assert not (tmp_path / "outside.json").exists()


_AUDIT: Dict[str, Any] = {"on": False, "events": []}
_AUDIT_EVENTS = {"open", "sqlite3.connect", "os.replace", "os.rename", "os.remove", "os.unlink", "os.mkdir", "os.rmdir", "shutil.copyfile", "shutil.rmtree"}


def _audit_hook(event, args):
    if _AUDIT["on"] and event in _AUDIT_EVENTS:
        paths = []
        for arg in args:
            if isinstance(arg, (str, bytes, os.PathLike)):
                try:
                    paths.append(os.fsdecode(arg))
                except TypeError:
                    pass
        mode = args[1] if event == "open" and len(args) > 1 else None
        _AUDIT["events"].append((event, paths, mode))


sys.addaudithook(_audit_hook)


def test_root_isolation_audit(tmp_path):
    """A --root <tmp> run (dry-run, apply, rollback, rehearsal) never opens
    the real project data and writes only under tmp."""
    from tools import migrate_channels

    root = build_root(tmp_path / "root")
    report = tmp_path / "reports" / "dry"
    (tmp_path / "reports").mkdir()
    protected = [Path(config.BASE_DIR) / name for name in ("_Docs", "03_Projects", "04_Exports", "05_Covers_Thumbnails", "06_Archive", "01_Raw", "00_Inbox")]
    _AUDIT["events"].clear()
    _AUDIT["on"] = True
    try:
        assert migrate_channels.main(["--root", str(root), "--report", str(report)]) == 0
        expected = json.loads(report.with_suffix(".json").read_text(encoding="utf-8"))["plan"]["plan_hash"]
        assert migrate_channels.main(["--root", str(root), "--apply", "--expect-plan", expected]) == 0
        assert migrate_channels.main(["--root", str(root), "--status"]) == 0
        assert migrate_channels.main(["--root", str(root), "--rollback"]) == 0
        assert migrate_channels.main(["--root", str(root), "--rehearse-restore", str(tmp_path / "rehearse")]) == 0
        assert migrate_channels.main(["--root", str(root), "--apply"]) == 2  # missing --expect-plan
    finally:
        _AUDIT["on"] = False
        cm._close_cached_connections(root)
    events = list(_AUDIT["events"])
    assert events, "audit hook saw nothing"
    tmp = tmp_path.resolve()
    sqlite_in_root = [p for e, ps, _ in events if e == "sqlite3.connect" for p in ps if str(root.resolve().as_posix()) in p.replace("\\", "/")]
    assert sqlite_in_root, "expected sqlite connections to the tmp root"
    for event, paths, mode in events:
        for raw in paths:
            if not raw or raw == ":memory:":
                continue
            path = Path(raw[len("file:"):].split("?", 1)[0]) if raw.startswith("file:") else Path(raw)
            if not path.is_absolute():
                continue
            resolved = Path(os.path.abspath(path))
            for guard in protected:
                assert not cm._is_within(resolved, guard), f"{event} touched real data: {resolved}"
            is_write = event != "open" or (isinstance(mode, str) and any(c in mode for c in "wax+"))
            if event == "sqlite3.connect":
                is_write = "mode=ro" not in raw
            if is_write and event not in ("os.mkdir",):
                assert cm._is_within(resolved, tmp) or cm._is_within(resolved, Path(os.environ.get("TEMP", tmp))), f"{event} wrote outside tmp: {resolved}"
