"""Pytest collection guard for manual rendering and external-service scripts.

The ignored modules are runnable diagnostics kept in ``tests/`` for historical
reasons.  They execute work at import time, so collecting them can render media
or call an external API before pytest starts the automated test suite.
"""
import os
import gc
from pathlib import Path
import sys
import tempfile
from threading import Thread as _RealThread
from concurrent.futures import ThreadPoolExecutor

import pytest


# This must run during conftest import, BEFORE test collection imports any store.
# An autouse fixture alone cannot prevent TaskManager.initialize() writing a
# recovered registry when its module is imported during collection.
SOURCE_ROOT = Path(__file__).resolve().parent.parent
_collection_storage = tempfile.TemporaryDirectory(prefix="omnicut-pytest-", ignore_cleanup_errors=True)
COLLECTION_ROOT = Path(_collection_storage.name)
_STORAGE_ROOTS = {COLLECTION_ROOT}
os.environ["OMNICUT_DATA_ROOT"] = str(COLLECTION_ROOT)
os.environ["OMNICUT_API_KEY"] = ""
os.environ["OMNICUT_MULTI_CHANNEL_STRICT"] = ""
sys.dont_write_bytecode = True

_DATA_DIR_NAMES = ("00_Inbox", "01_Raw", "02_Assets", "03_Projects", "04_Exports", "05_Covers_Thumbnails", "06_Archive", "_Docs")
_PROTECTED_ROOTS = tuple(SOURCE_ROOT / name for name in _DATA_DIR_NAMES)


def _protected_path(value):
    if not isinstance(value, (str, bytes, os.PathLike)):
        return False
    value = os.fsdecode(value)
    if value.startswith("file:"):  # sqlite URI paths are still filesystem access.
        from urllib.parse import unquote
        value = unquote(value[5:].split("?", 1)[0])
        if os.name == "nt" and value.startswith("///"):
            value = value.lstrip("/")
    path = Path(value).resolve(strict=False)
    return any(path == root or root in path.parents for root in _PROTECTED_ROOTS)


def _production_write_guard(event, args):
    """Fail closed even for paths a local test forgot to monkeypatch.

    Read-only fonts/assets remain available. sqlite connections are denied even
    for SELECT because WAL/setup can write before the first explicit mutation.
    This audit hook also covers thread-pool workers and direct os/sqlite calls.
    """
    paths = ()
    if event == "open":
        path, mode, flags = args
        if (mode and any(character in mode for character in "wax+")) or (flags and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
            paths = (path,)
    elif event in {"os.mkdir", "os.remove", "os.rmdir", "os.truncate", "os.chmod", "os.utime", "sqlite3.connect", "shutil.rmtree"}:
        paths = args[:1]
    elif event in {"os.rename", "os.link", "os.symlink"}:
        paths = args[:2]
    if any(_protected_path(path) for path in paths):
        raise PermissionError(f"pytest production storage write blocked: {event}")


sys.addaudithook(_production_write_guard)

# Import only config now: its mkdir side effects use the isolated environment.
from scripts import config as _storage_config
from scripts import task_manager as _task_bootstrap

# Font probes are read-only golden-master checks and need the real font files.
# Production writes to this tree are still blocked by the audit hook above.
_PACKAGED_ASSET_DIRS = {
    "FONTS_DIR": "Fonts", "SFX_DIR": "SFX", "MUSIC_DIR": "Music",
    "STICKERS_DIR": "Stickers_Memes", "LUTS_DIR": "LUTs_ColorPresets", "EFFECTS_DIR": "Effects",
}
_PACKAGED_ASSET_FILES = {
    "TYPOGRAPHY_PRESETS_PATH": SOURCE_ROOT / "02_Assets" / "Templates" / "typography_presets.json",
}
for _attribute, _directory in _PACKAGED_ASSET_DIRS.items():
    setattr(_storage_config, _attribute, SOURCE_ROOT / "02_Assets" / _directory)


def _redirect_loaded_paths(monkeypatch, root):
    """Retarget imported config aliases and dynamic DocumentTable providers.

    Path providers are intentionally not replaced with fixed lambdas: existing
    tests remain free to monkeypatch STORE_PATH/LOG_PATH and have the DB follow.
    Code roots and __file__ remain actual source paths for source contract tests.
    """
    for name, module in tuple(sys.modules.items()):
        if not name.startswith("scripts.") or module is None:
            continue
        for attribute, value in tuple(vars(module).items()):
            if not isinstance(value, Path) or attribute in {"__file__", "SOURCE_ROOT"}:
                continue
            replacement = None
            if value == SOURCE_ROOT and attribute == "BASE_DIR":
                replacement = root
            else:
                previous_root = next((parent for parent in (value, *value.parents) if parent in _STORAGE_ROOTS), None)
                if previous_root is not None:
                    replacement = root / value.relative_to(previous_root)
                else:
                    # Retarget independently computed data paths (e.g. hooks).
                    for directory in _PROTECTED_ROOTS:
                        if directory.name == "02_Assets" and attribute in _PACKAGED_ASSET_DIRS:
                            continue
                        try:
                            replacement = root / directory.name / value.relative_to(directory)
                            break
                        except ValueError:
                            continue
            if attribute == "CAPCUT_DRAFT_DIR":
                replacement = root / "capcut_drafts"
            if attribute in _PACKAGED_ASSET_DIRS:
                # Shared packaged bytes are read-only. Registry caches and
                # generated artifacts still use the per-test data root.
                replacement = SOURCE_ROOT / "02_Assets" / _PACKAGED_ASSET_DIRS[attribute]
            if attribute in _PACKAGED_ASSET_FILES:
                replacement = _PACKAGED_ASSET_FILES[attribute]
            if replacement is not None:
                monkeypatch.setattr(module, attribute, replacement)


@pytest.fixture(autouse=True)
def isolated_storage(monkeypatch):
    """Every test starts with empty, independent durable and in-memory stores."""
    # Keep infrastructure files out of the caller's tmp_path: tests can assert
    # their own filesystem effects without seeing unrelated store directories.
    storage = tempfile.TemporaryDirectory(prefix="omnicut-test-storage-")
    root = Path(storage.name)
    _STORAGE_ROOTS.add(root)
    for name in _DATA_DIR_NAMES:
        (root / name).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OMNICUT_DATA_ROOT", str(root))
    monkeypatch.setenv("OMNICUT_MULTI_CHANNEL_STRICT", "")
    _redirect_loaded_paths(monkeypatch, root)
    task_module = sys.modules.get("scripts.task_manager")
    worker_pool = None
    if task_module is not None:
        monkeypatch.setattr(task_module.TaskManager, "_tasks", {})
        monkeypatch.setattr(task_module.TaskManager, "_initialized", False)
        worker_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pytest-omnicut")
        monkeypatch.setattr(task_module, "_WORKER_POOL", worker_pool)
    for module_name, attribute in (("scripts.batch_render", "BATCH_REGISTRY"), ("scripts.render_jobs", "ACTIVE_JOBS")):
        module = sys.modules.get(module_name)
        if module is not None:
            monkeypatch.setattr(module, attribute, {})
    tracker = sys.modules.get("scripts.token_tracker")
    if tracker is not None:
        monkeypatch.setattr(tracker.TokenTracker, "_cache", None)
        monkeypatch.setattr(tracker.TokenTracker, "_cache_stamp", (0, -1))
    repository_api = sys.modules.get("scripts.api_gadget_media_projects")
    if repository_api is not None:
        from scripts.gadget_media_paths import GadgetMediaRoots
        from scripts.gadget_media_repository import GadgetMediaRepository
        monkeypatch.setattr(repository_api, "PROJECT_REPOSITORY", GadgetMediaRepository(GadgetMediaRoots.under(root)))
    yield root
    if worker_pool is not None:
        worker_pool.shutdown(wait=True, cancel_futures=True)
    batch = sys.modules.get("scripts.batch_render")
    dispatcher = getattr(batch, "_DISPATCHER_THREAD", None) if batch is not None else None
    # Dispatcher tests replace Thread with inert fakes. Only actual worker
    # threads can hold storage handles and need the strict teardown barrier.
    if isinstance(dispatcher, _RealThread) and dispatcher.is_alive():
        dispatcher.join(timeout=5)
        if dispatcher.is_alive():
            pytest.fail("batch dispatcher leaked past test teardown; cannot restore storage paths safely")
    # Close only the current thread's isolated SQLite connections. Existing
    # worker tests own/join their threads; audit protection remains process-wide.
    db = sys.modules.get("scripts.db")
    if db is not None:
        connections = getattr(db._local, "conns", {})
        for key, connection in tuple(connections.items()):
            if Path(key).is_relative_to(root):
                connection.close()
                del connections[key]
    # Starlette request workers have exited, but their SQLite objects can be
    # cyclic garbage (statement caches). Release those handles before Windows
    # removes the per-test directory rather than hiding cleanup failures.
    if any(root.rglob("*.db")):
        gc.collect()
    storage.cleanup()


def pytest_sessionfinish(session, exitstatus):
    """Release bootstrap SQLite handles before removing collection temp files."""
    _task_bootstrap._WORKER_POOL.shutdown(wait=True, cancel_futures=True)
    db = sys.modules.get("scripts.db")
    if db is not None:
        connections = getattr(db._local, "conns", {})
        for key, connection in tuple(connections.items()):
            if any(Path(key).is_relative_to(root) for root in _STORAGE_ROOTS):
                connection.close()
                del connections[key]
    _collection_storage.cleanup()

collect_ignore = [
    "test_all_thai_fonts.py",
    "test_all_vowels.py",
    "test_bilingual_ass.py",
    "test_bilingual_subtitles.py",
    "test_clause_segmenter.py",
    "test_clean_trans.py",
    "test_drawtext.py",
    "test_fixed_thai_fonts.py",
    "test_full_vision_render.py",
    "test_gemini_vision_match.py",
    "test_noto.py",
    "test_perfect_sync_voice.py",
    "test_pillow_thai.py",
    "test_script_lab_ai.py",
    "test_thai_chunking.py",
    "test_translator_script.py",
    "test_unicode_thai.py",
    "test_voice_pacing.py",
    "test_vowel_rendering.py",
]


@pytest.fixture(autouse=True)
def _no_real_api_key_gate(monkeypatch):
    """Every test starts from a known state: no OMNICUT_API_KEY configured.

    Without this, whatever a developer's real .env happens to set leaks into
    every TestClient request across the whole suite -- scripts/auth.py's
    middleware would then 401 every call that doesn't carry X-API-Key,
    which almost none of the ~19 files with their own `client` fixture do.
    tests/test_api_auth.py already had this exact fixture, file-scoped; this
    promotes the same isolation to the whole suite so passing locally never
    depends on whether OMNICUT_API_KEY happens to be unset in .env.
    """
    monkeypatch.setenv("OMNICUT_API_KEY", "")


@pytest.fixture(autouse=True)
def _isolated_trash_dir(monkeypatch, tmp_path):
    """Deleting a clip through the API moves it to 06_Archive/.trash.

    Without this, every test that deletes a fixture file through the API would
    drop that file into the developer's real trash folder.
    """
    try:
        from scripts import api_videos
    except ImportError:  # pragma: no cover - optional deps missing
        return
    monkeypatch.setattr(api_videos, "ARCHIVE_DIR", tmp_path / "_isolated_archive")
