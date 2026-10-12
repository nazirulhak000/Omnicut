"""Behavioral guards against pytest touching production stores at any phase."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from scripts import (
    batch_queue_store, config, export_registry, post_log, product_store,
    recording_sessions, schedule_store, shot_lists_store, task_manager,
    tiktok_pending,
)

# These imports execute during collection, before the autouse fixture runs.
COLLECTED_DATA_ROOT = config.BASE_DIR
COLLECTED_TASK_FILE = task_manager.TASKS_FILE
COLLECTED_PROVIDERS = tuple(
    (table._db_path_fn(), table._json_path_fn())
    for module in (product_store, export_registry, post_log, schedule_store,
                   shot_lists_store, recording_sessions, tiktok_pending, batch_queue_store)
    for table in vars(module).values()
    if isinstance(table, product_store.DocumentTable)
)


def test_collection_imports_already_use_temporary_storage(isolated_storage):
    assert COLLECTED_DATA_ROOT != config.SOURCE_ROOT
    assert COLLECTED_TASK_FILE.is_relative_to(COLLECTED_DATA_ROOT)
    assert COLLECTED_PROVIDERS
    for database, mirror in COLLECTED_PROVIDERS:
        assert database.is_relative_to(COLLECTED_DATA_ROOT)
        assert mirror.is_relative_to(COLLECTED_DATA_ROOT)
    assert task_manager.TASKS_FILE.is_relative_to(isolated_storage)


def test_infrastructure_storage_does_not_pollute_test_tmp_path(isolated_storage, tmp_path):
    assert not isolated_storage.is_relative_to(tmp_path)
    assert list(tmp_path.iterdir()) == []
    product_store._TABLE.save([{"id": "infrastructure-only", "channel_id": "main"}])
    assert product_store.STORE_PATH.is_relative_to(isolated_storage)
    assert list(tmp_path.iterdir()) == []


def test_packaged_typography_presets_remain_readonly(isolated_storage):
    from scripts.subtitle import font_metrics
    expected = config.SOURCE_ROOT / "02_Assets" / "Templates" / "typography_presets.json"
    assert font_metrics.TYPOGRAPHY_PRESETS_PATH == expected
    assert expected.is_file()
    assert "mitr_minimal" in font_metrics._load_font_family_map()
    with pytest.raises(PermissionError, match="production storage write blocked"):
        expected.open("ab")


@pytest.mark.parametrize("iteration", [1, 2])
def test_all_default_tables_start_empty_and_write_only_the_current_test(isolated_storage, iteration):
    tables = [
        value
        for module in (product_store, export_registry, post_log, schedule_store,
                       shot_lists_store, recording_sessions, tiktok_pending, batch_queue_store)
        for value in vars(module).values()
        if isinstance(value, product_store.DocumentTable)
    ]
    for table in tables:
        assert table.load() == []
        row = {"id": f"isolated-{iteration}-{table._table}", "channel_id": "main"}
        table.save([row])
        assert table.load() == [row]
        assert table._db_path_fn().is_relative_to(isolated_storage)
        assert table._json_path_fn().is_relative_to(isolated_storage)
        assert json.loads(table._json_path_fn().read_text(encoding="utf-8")) == [row]


@pytest.mark.parametrize("iteration", [1, 2])
def test_task_registry_and_batch_memory_are_clean_between_tests(isolated_storage, iteration):
    assert task_manager.TaskManager._tasks == {}
    task_manager.TaskManager.initialize()
    task_manager.TaskManager._tasks[f"task-{iteration}"] = {"status": "completed"}
    task_manager.TaskManager._save_to_disk_locked()
    assert task_manager.TASKS_FILE.is_relative_to(isolated_storage)
    assert f"task-{iteration}" in json.loads(task_manager.TASKS_FILE.read_text(encoding="utf-8"))


def test_existing_store_monkeypatch_still_controls_database_and_mirror(monkeypatch, tmp_path):
    mirror = tmp_path / "custom-fixture" / "products.json"
    monkeypatch.setattr(product_store, "STORE_PATH", mirror)
    product_store._TABLE.save([{"id": "custom"}])
    assert product_store._TABLE._db_path_fn() == mirror.parent / "store.db"
    assert mirror.exists()
    assert product_store._TABLE.load() == [{"id": "custom"}]


def test_packaged_assets_readonly_and_catalog_cache_stays_isolated(isolated_storage):
    from scripts import asset_registry
    from scripts.asset_registry import AssetRegistry
    from scripts.sfx_manager import SFXManager
    resolved = SFXManager.resolve("pop")
    assert resolved is not None and Path(resolved).is_file()
    assert Path(resolved).is_relative_to(config.SOURCE_ROOT / "02_Assets")
    info = AssetRegistry._file_info(Path(resolved))
    assert info["rel_path"].startswith("02_Assets/")
    assert asset_registry.REGISTRY_PATH.is_relative_to(isolated_storage)
    assert asset_registry.METADATA_PATH.is_relative_to(isolated_storage)
    assert asset_registry.REGISTRY_PATH.exists()
    with pytest.raises(PermissionError, match="production storage write blocked"):
        Path(resolved).open("ab")


def test_gadget_repository_default_and_api_singleton_use_current_test(isolated_storage):
    from scripts.gadget_media_repository import GadgetMediaRepository
    from scripts import api_gadget_media_projects
    for repository in (GadgetMediaRepository(), api_gadget_media_projects.PROJECT_REPOSITORY):
        assert repository.roots.docs.is_relative_to(isolated_storage)
        assert repository.roots.projects.is_relative_to(isolated_storage)


def test_audit_hook_blocks_direct_writes_moves_and_sqlite_without_harming_readonly_assets(monkeypatch, tmp_path):
    from tests import conftest
    protected = tmp_path / "fake-production"
    protected.mkdir()
    sentinel = protected / "sentinel.json"
    sentinel.write_text("unchanged", encoding="utf-8")
    monkeypatch.setattr(conftest, "_PROTECTED_ROOTS", (*conftest._PROTECTED_ROOTS, protected))
    assert sentinel.read_text(encoding="utf-8") == "unchanged"
    operations = [
        lambda: sentinel.write_text("overwrite", encoding="utf-8"),
        lambda: sentinel.unlink(),
        lambda: sentinel.replace(tmp_path / "moved.json"),
        lambda: (protected / "child").mkdir(),
        lambda: sqlite3.connect(protected / "store.db"),
        lambda: sqlite3.connect((protected / "store.db").as_uri() + "?mode=ro", uri=True),
    ]
    for operation in operations:
        with pytest.raises(PermissionError, match="production storage write blocked"):
            operation()
    assert sentinel.read_text(encoding="utf-8") == "unchanged"
    assert not (protected / "store.db").exists()


def test_fresh_process_task_import_recovers_only_the_explicit_data_root(tmp_path):
    root = tmp_path / "subprocess-storage"
    projects = root / "03_Projects"
    projects.mkdir(parents=True)
    registry = projects / "task_registry.json"
    registry.write_text(json.dumps({"fixture-task": {"id": "fixture-task", "status": "processing", "type": "fixture", "created_at": "2099-01-01 00:00:00"}}), encoding="utf-8")
    env = dict(os.environ, OMNICUT_DATA_ROOT=str(root), OMNICUT_API_KEY="", PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    script = (
        "import json; from scripts import config,task_manager; "
        "print('ISOLATION_RESULT='+json.dumps({'root':str(config.BASE_DIR),"
        "'tasks':str(task_manager.TASKS_FILE),'source':str(config.SOURCE_ROOT)}))"
    )
    result = subprocess.run([sys.executable, "-c", script], cwd=config.SOURCE_ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stderr
    line = next(line for line in result.stdout.splitlines() if line.startswith("ISOLATION_RESULT="))
    paths = json.loads(line.split("=", 1)[1])
    assert Path(paths["root"]) == root
    assert Path(paths["tasks"]) == registry
    assert Path(paths["source"]) == config.SOURCE_ROOT
    assert json.loads(registry.read_text(encoding="utf-8"))["fixture-task"]["status"] == "failed"


def test_direct_task_manager_script_keeps_source_imports_with_separate_data_root(tmp_path):
    root = tmp_path / "direct-script-storage"
    env = dict(os.environ, OMNICUT_DATA_ROOT=str(root), PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    result = subprocess.run([sys.executable, str(config.SOURCE_ROOT / "scripts" / "task_manager.py")], cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stderr
    assert (root / "03_Projects").is_dir()
