"""Converted legacy batch tools write through scripts.store_io (audit S1-01,
S6-01, X-01 follow-up).  Everything lives in tmp_path; no real store or
_Docs file is touched."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from scripts import store_io
from scripts.gdrive_archive_engine import GDriveArchiveEngine, _resolve_under, _safe_component


def _seed_products(docs: Path, rows):
    with store_io.mutate_products(docs) as products:
        products.extend(rows)


def _load_tool(name: str, monkeypatch, docs: Path, attr: str = "DOCS"):
    module = importlib.import_module(f"tools.{name}")
    monkeypatch.setattr(module, attr, docs)
    return module


# ---------------------------------------------------------------- generate_*

@pytest.mark.parametrize("tool, seed, sync", [
    ("generate_essager_20_scripts", {"id": "9505b042d58640f5aa58015bb86be097", "angles": []},
     lambda m: m.sync_to_products_json(m.SCRIPTS)),
    ("generate_goojodoq_20_scripts", {"id": "goo", "product_code": "GOO01", "angles": []},
     lambda m: m.sync_to_products_json(m.SCRIPTS)),
    ("generate_jeep_ew011_20_scripts", {"id": "other", "name": "x", "angles": []},
     lambda m: m.sync_to_products_json(m.SCRIPTS)),
])
def test_script_generators_sync_angles_through_store(tmp_path, monkeypatch, tool, seed, sync):
    docs = tmp_path / "_Docs"
    _seed_products(docs, [dict(seed, updated_at="2026-11-01T00:00:00"),
                          {"id": "keep", "name": "keep me", "updated_at": "2026-11-01T00:00:00"}])
    module = _load_tool(tool, monkeypatch, docs)
    sync(module)
    rows = {r["id"]: r for r in store_io.load_products(docs)}
    assert "keep" in rows
    synced = [r for r in rows.values() if r.get("angles")]
    assert synced and len(synced[0]["angles"]) == len(module.SCRIPTS)
    # the JSON mirror is republished by the store, not hand-written
    mirror = json.loads((docs / "products.json").read_text(encoding="utf-8"))
    assert {r["id"] for r in mirror} == set(rows)


def test_script_generator_does_not_drop_row_added_after_read(tmp_path, monkeypatch):
    """S1-01 shape: a product added by the app while the tool runs survives."""
    docs = tmp_path / "_Docs"
    _seed_products(docs, [{"id": "9505b042d58640f5aa58015bb86be097", "angles": []}])
    module = _load_tool("generate_essager_20_scripts", monkeypatch, docs)
    module.sync_to_products_json(module.SCRIPTS)
    _seed_products(docs, [{"id": "added-by-app", "name": "new"}])
    module.sync_to_products_json(module.SCRIPTS)   # second run: idempotent, no loss
    ids = {r["id"] for r in store_io.load_products(docs)}
    assert ids == {"9505b042d58640f5aa58015bb86be097", "added-by-app"}
    target = next(r for r in store_io.load_products(docs) if r["id"].startswith("9505"))
    assert len(target["angles"]) == len(module.SCRIPTS)


def test_redmi_creates_missing_product_through_store(tmp_path, monkeypatch):
    docs = tmp_path / "_Docs"
    _seed_products(docs, [{"id": "keep", "name": "keep me"}])
    module = _load_tool("generate_redmi_buds8_20_scripts", monkeypatch, docs)
    module.sync_to_products_json(module.SCRIPTS)
    rows = store_io.load_products(docs)
    red = next(r for r in rows if r.get("product_code") == "RED01")
    assert len(red["angles"]) == len(module.SCRIPTS)
    assert any(r["id"] == "keep" for r in rows)


def test_hatari16_sync_uses_store(tmp_path, monkeypatch):
    docs = tmp_path / "_Docs"
    _seed_products(docs, [{"id": "h1", "product_code": "HAT01", "angles": []}])
    module = _load_tool("generate_hatari_16inch_20_scripts", monkeypatch, docs)
    module.sync_products_json()
    hat = store_io.load_products(docs)[0]
    assert hat["total_angles"] == len(module.SCRIPTS) == len(hat["angles"])


@pytest.mark.parametrize("tool, attr, entry, seed", [
    ("generate_hoyaup_20_scripts", "DOCS", "main", {"id": "hoy", "product_code": "HOY01", "angles": []}),
    ("generate_orsen_20_scripts", "DOCS", "main",
     {"id": "37521e0dae1a419e8037e159254d4fdf", "angles": []}),
    ("generate_hatari_cyclone_20_scripts", "DOCS_DIR", "main",
     {"id": "cde38b1c07e54ea69a3d50a6c1bb3f18", "angles": []}),
    ("generate_ttz_k106_20_scripts", "DOCS", "validate_and_save", {"id": "TTZ01", "angles": []}),
])
def test_other_generators_write_only_through_store(tmp_path, monkeypatch, tool, attr, entry, seed):
    docs = tmp_path / "_Docs"
    _seed_products(docs, [seed, {"id": "keep", "name": "keep me"}])
    module = _load_tool(tool, monkeypatch, docs, attr)
    getattr(module, entry)()
    rows = {r["id"]: r for r in store_io.load_products(docs)}
    assert "keep" in rows
    assert len(rows[seed["id"]]["angles"]) == len(module.SCRIPTS)


# ------------------------------------------------------------ other tools

def test_clean_products_data_goes_through_store(tmp_path, monkeypatch):
    docs = tmp_path / "_Docs"
    _seed_products(docs, [{"id": "p1", "name": "Logitech บลูทูธ",
                           "angles": [{"angle_id": "a1", "script_lines": ["สวัสดีค่ะ"]}]}])
    module = importlib.import_module("tools.clean_products_data")
    monkeypatch.setattr(module, "PRODUCTS_FILE", docs / "products.json")
    monkeypatch.setattr(module, "BASE_DIR", tmp_path)
    module.clean_products_json()
    row = store_io.load_products(docs)[0]
    assert row["id"] == "p1"
    assert "บลูทูธ" not in row["name"]


def test_upgrade_hat01_sync_updates_rows_in_place(tmp_path, monkeypatch):
    docs = tmp_path / "_Docs"
    module = importlib.import_module("tools.upgrade_hat01_cta_and_cover")
    monkeypatch.setattr(module, "DOCS_DIR", docs)
    with store_io.mutate_export_registry(docs) as reg:
        reg.append({"id": "e1", "composition_id": module.CID, "status": "ready"})
        reg.append({"id": "e2", "composition_id": "other", "status": "ready"})
    with store_io.mutate_cover_bindings(docs) as binds:
        binds.append({"id": "b1", "video_path": "x/hat01-pov-s01_v1.mp4",
                      "selections": {"9:16": {}, "3:4": {}}})
    video = tmp_path / "v.mp4"
    c1, c2 = tmp_path / "c1.jpg", tmp_path / "c2.jpg"
    for f, body in ((video, b"v"), (c1, b"1"), (c2, b"2")):
        f.write_bytes(body)
    module.sync_registry_and_bindings(video, c1, c2)
    reg = {r["id"]: r for r in store_io.load_export_registry(docs)}
    assert reg["e1"]["status"] == "rendered" and reg["e2"]["status"] == "ready"
    assert store_io.load_cover_bindings(docs)[0]["selections"]["9:16"]["sha256"]


def test_apply_row_changes_merges_only_changed_fields(tmp_path):
    docs = tmp_path / "_Docs"
    with store_io.mutate_export_registry(docs) as rows:
        rows.append({"id": "e1", "status": "ready", "note": "a"})
    baseline = store_io.load_export_registry(docs)
    work = [dict(r) for r in baseline]
    work[0]["status"] = "posted"
    # the app edits another field and adds a row after the tool read its copy
    with store_io.mutate_export_registry(docs) as rows:
        rows[0]["note"] = "edited-by-app"
        rows.append({"id": "e2", "status": "ready"})
    assert store_io.apply_row_changes(store_io.EXPORT_REGISTRY, baseline, work, docs) == 1
    final = {r["id"]: r for r in store_io.load_export_registry(docs)}
    assert final["e1"] == {"id": "e1", "status": "posted", "note": "edited-by-app"}
    assert "e2" in final


# ----------------------------------------------- gdrive path-traversal guard

@pytest.mark.parametrize("bad", ["", ".", "..", "../x", "a/b", "a\\b", "C:/x", "/abs", "x:y", " pad"])
def test_safe_component_rejects_traversal(bad):
    with pytest.raises(ValueError):
        _safe_component(bad)


def test_safe_component_accepts_plain_thai_names():
    assert _safe_component("20261014_พัดลม-hook") == "20261014_พัดลม-hook"


def test_resolve_under_blocks_escape_and_root(tmp_path):
    base = tmp_path / "01_Raw"
    base.mkdir()
    assert _resolve_under(base, "ok") == (base / "ok").resolve()
    for bad in ("..", "../outside", "", str(tmp_path / "abs")):
        with pytest.raises(ValueError):
            _resolve_under(base, bad)


def test_full_archive_never_rmtrees_outside_raw_dir(tmp_path):
    """A registry row with project_name='..' must not delete the project root."""
    root = tmp_path / "home"
    (root / "04_Exports" / "Posted").mkdir(parents=True)
    (root / "01_Raw" / "keep").mkdir(parents=True)
    (root / "01_Raw" / "keep" / "raw.txt").write_text("raw", encoding="utf-8")
    video = root / "04_Exports" / "Posted" / "a.mp4"
    video.write_bytes(b"video")
    stray = tmp_path / "stray.mp4"
    stray.write_bytes(b"not-ours")
    outside = root / "03_Projects"
    outside.mkdir()
    (outside / "marker.txt").write_text("m", encoding="utf-8")
    docs = root / "_Docs"
    with store_io.mutate_export_registry(docs) as rows:
        rows.append({"id": "e_bad", "status": "posted", "path": "04_Exports/Posted/a.mp4",
                     "project_name": "..", "product_id": "p"})
        rows.append({"id": "e_abs", "status": "posted", "path": str(stray),
                     "project_name": "ok", "product_id": "p"})
    vault = tmp_path / "gdrive"
    vault.mkdir()
    result = GDriveArchiveEngine.archive_clips(
        scope="full", base_dir=root, custom_gdrive_root=vault)
    assert result["archived_count"] == 0
    assert {s["export_id"] for s in result["skipped_unsafe"]} == {"e_bad", "e_abs"}
    assert video.exists() and stray.exists()
    assert (root / "01_Raw" / "keep" / "raw.txt").exists()
    assert (outside / "marker.txt").exists()


def test_archive_writes_breadcrumb_through_store(tmp_path):
    root = tmp_path / "home"
    (root / "04_Exports" / "Posted").mkdir(parents=True)
    video = root / "04_Exports" / "Posted" / "a.mp4"
    video.write_bytes(b"video-bytes")
    docs = root / "_Docs"
    with store_io.mutate_export_registry(docs) as rows:
        rows.append({"id": "e1", "status": "posted", "path": "04_Exports/Posted/a.mp4",
                     "project_name": "PROD", "product_id": "p"})
    vault = tmp_path / "gdrive"
    vault.mkdir()
    result = GDriveArchiveEngine.archive_clips(base_dir=root, custom_gdrive_root=vault)
    assert result["archived_count"] == 1
    assert not video.exists()
    row = store_io.load_export_registry(docs)[0]
    assert row["cloud_status"] == "archived_gdrive"
    assert (vault / "PROD" / "Videos" / "a.mp4").read_bytes() == b"video-bytes"
