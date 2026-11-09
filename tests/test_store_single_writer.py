"""Single-writer contract for the JSON-mirrored stores (audit S1-01, S6-01,
X-01, S1-16).  Every fixture lives in tmp_path; no real store is touched."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from scripts import store_io

REPO = Path(__file__).resolve().parents[1]
MIRRORS = ("products", "export_registry", "export_cover_bindings")
_MIRROR_RE = "|".join(MIRRORS)

# Store modules that own the mirrors (they publish them under the SQLite
# write lock) plus the channel migration, which rewrites them atomically
# under its own maintenance lock.
OWNERS = {
    "scripts/db.py",
    "scripts/store_io.py",
    "scripts/product_store.py",
    "scripts/export_registry.py",
    "scripts/export_cover_bindings.py",
    "scripts/channel_migration.py",
}

# Known direct writers outside the scope of fix/store-single-writer (other
# owners). Pending migration to scripts.store_io -- this list may only
# shrink: an entry that no longer writes directly fails the test so it is
# removed here.
PENDING = {
    "scripts/gdrive_archive_engine.py",
    "scripts/ssd_reconcile_engine.py",
    "tools/batch_schedule_non_couple_exports.py",
    "tools/clean_products_data.py",
    "tools/generate_essager_20_scripts.py",
    "tools/generate_essager_covers_20.py",
    "tools/generate_goojodoq_20_scripts.py",
    "tools/generate_hatari_16inch_20_scripts.py",
    "tools/generate_hatari_cyclone_20_scripts.py",
    "tools/generate_hoyaup_20_scripts.py",
    "tools/generate_jeep_ew011_20_scripts.py",
    "tools/generate_orsen_20_scripts.py",
    "tools/generate_redmi_buds8_20_scripts.py",
    "tools/generate_ttz_k106_20_scripts.py",
    "tools/produce_hatari16_benchmark.py",
    "tools/reschedule_all_old_non_couple_clips.py",
    "tools/upgrade_hat01_cta_and_cover.py",
}


def _direct_mirror_writes(source: str) -> list[str]:
    """Heuristic: names bound to a mirror path, then written to directly."""
    names = set(re.findall(
        rf"^\s*(\w+)\s*=\s*[^\n]*[\"'](?:{_MIRROR_RE})\.json[\"']", source, re.M))
    hits = []
    if re.search(rf"[\"'](?:{_MIRROR_RE})\.json[\"']\)\s*\.write_(?:text|bytes)\(", source):
        hits.append("inline write_text")
    for name in names:
        patterns = [
            rf"\b{name}\.write_(?:text|bytes)\(",
            rf"\bopen\(\s*{name}\s*,\s*[\"'][wax]",
            rf"\b{name}\.open\(\s*[\"'][wax]",
            rf"os\.replace\([^)\n]*,\s*{name}\s*\)",
            rf"\.replace\(\s*{name}\s*\)",
            rf"_atomic_write_json\(\s*{name}\b",
        ]
        hits += [f"{name}: {p}" for p in patterns if re.search(p, source)]
    return hits


def _python_files():
    for folder in ("scripts", "tools"):
        for path in sorted((REPO / folder).rglob("*.py")):
            yield path.relative_to(REPO).as_posix(), path


def test_no_new_direct_json_mirror_writers():
    offenders = {}
    for rel, path in _python_files():
        if rel in OWNERS:
            continue
        hits = _direct_mirror_writes(path.read_text(encoding="utf-8", errors="replace"))
        if hits:
            offenders[rel] = hits
    unexpected = sorted(set(offenders) - PENDING)
    assert unexpected == [], (
        "เขียน products.json / export_registry.json / export_cover_bindings.json ตรง "
        f"ต้องผ่าน scripts.store_io แทน: {unexpected}")
    resolved = sorted(PENDING - set(offenders))
    assert resolved == [], f"ไฟล์เหล่านี้ไม่เขียนตรงแล้ว ให้ลบออกจาก PENDING: {resolved}"


def test_lint_heuristic_catches_the_old_tool_pattern():
    old = (
        'registry_file = DOCS_DIR / "export_registry.json"\n'
        'registry_file.write_text(json.dumps(entries), encoding="utf-8")\n'
        'products_file = ROOT / "_Docs" / "products.json"\n'
        'with open(products_file, "w", encoding="utf-8") as f:\n'
        '    json.dump(products, f)\n'
    )
    assert len(_direct_mirror_writes(old)) == 2
    assert _direct_mirror_writes('p = DOCS / "products.json"\nrows = json.loads(p.read_text())\n') == []


def _stamp_after(path: Path, base_ns: int, step: int) -> None:
    os.utime(path, ns=(base_ns + step, base_ns + step))


@pytest.mark.parametrize("table", MIRRORS)
def test_stale_snapshot_written_back_does_not_drop_new_rows(tmp_path, table):
    """S1-01 / S6-01 / X-01 repro: read the mirror, the app adds a row, a
    tool writes its old copy back -> the new row must survive."""
    docs = tmp_path / "_Docs"
    with store_io.mutate(table, docs) as rows:
        rows.append({"id": "A", "updated_at": "2026-11-01T00:00:00"})
    mirror = docs / f"{table}.json"
    stale_copy = mirror.read_text(encoding="utf-8")
    base_ns = mirror.stat().st_mtime_ns

    with store_io.mutate(table, docs) as rows:
        rows.append({"id": "B", "updated_at": "2026-11-02T00:00:00"})

    mirror.write_text(stale_copy, encoding="utf-8")  # the old tool behaviour
    _stamp_after(mirror, base_ns, 5_000_000)

    assert {r["id"] for r in store_io.load(table, docs)} == {"A", "B"}
    assert {r["id"] for r in json.loads(mirror.read_text(encoding="utf-8"))} == {"A", "B"}


def test_newer_external_row_edit_still_wins(tmp_path):
    docs = tmp_path / "_Docs"
    with store_io.mutate_products(docs) as rows:
        rows.append({"id": "p1", "name": "old", "updated_at": "2026-11-01T00:00:00"})
    mirror = docs / "products.json"
    base_ns = mirror.stat().st_mtime_ns
    mirror.write_text(json.dumps([{"id": "p1", "name": "new", "updated_at": "2026-11-05T00:00:00"}]),
                      encoding="utf-8")
    _stamp_after(mirror, base_ns, 5_000_000)
    assert store_io.load_products(docs) == [{"id": "p1", "name": "new", "updated_at": "2026-11-05T00:00:00"}]


def test_corrupt_mirror_never_becomes_empty_write(tmp_path):
    docs = tmp_path / "_Docs"
    with store_io.mutate_export_registry(docs) as rows:
        rows.append({"id": "exp_1", "path": "04_Exports/Ready_to_post/a.mp4"})
    mirror = docs / "export_registry.json"
    base_ns = mirror.stat().st_mtime_ns
    mirror.write_text("[", encoding="utf-8")  # half-written by someone else
    _stamp_after(mirror, base_ns, 5_000_000)

    eid = store_io.upsert_rendered_export(
        "04_Exports/Ready_to_post/b.mp4", product_id="p1", angle_id="a1",
        project_name="_HyperFrames_Studio/b", docs_dir=docs)
    ids = {r["id"] for r in store_io.load_export_registry(docs)}
    assert ids == {"exp_1", eid}


def test_upsert_rendered_export_and_cover_binding(tmp_path):
    docs = tmp_path / "_Docs"
    rel = "04_Exports/Ready_to_post/clip.mp4"
    eid = store_io.upsert_rendered_export(
        rel, product_id="p1", angle_id="a1", project_name="_HyperFrames_Studio/clip",
        docs_dir=docs, new_fields={"resolution": "1080x1920"})
    again = store_io.upsert_rendered_export(
        rel, product_id="p1", angle_id="a2", project_name="x", docs_dir=docs)
    assert again == eid
    (row,) = store_io.load_export_registry(docs)
    assert row["angle_id"] == "a2" and row["status"] == "rendered" and row["resolution"] == "1080x1920"

    sel = {"9:16": {"path": "05_Covers_Thumbnails/c.jpg", "sha256": "1", "format": "9:16"}}
    first = store_io.upsert_cover_binding(eid, rel, sel, docs_dir=docs, clock=lambda: 1.0)
    assert first["id"] == store_io.default_binding_id("main", eid) and first["revision"] == 1
    sel34 = {"3:4": {"path": "05_Covers_Thumbnails/c34.jpg", "sha256": "2", "format": "3:4"}}
    second = store_io.upsert_cover_binding(eid, rel, sel34, bump_revision=True, docs_dir=docs, clock=lambda: 2.0)
    assert set(second["selections"]) == {"9:16", "3:4"} and second["revision"] == 2
    assert len(store_io.load_cover_bindings(docs)) == 1


def test_mutate_deletions_reach_the_store(tmp_path):
    docs = tmp_path / "_Docs"
    with store_io.mutate_cover_bindings(docs) as rows:
        rows.extend([{"id": "b1", "video_path": "x_20261020_goo01"}, {"id": "b2", "video_path": "keep"}])
    with store_io.mutate_cover_bindings(docs) as rows:
        rows[:] = [r for r in rows if r["id"] != "b1"]
    assert [r["id"] for r in store_io.load_cover_bindings(docs)] == ["b2"]


def test_finalize_stores_relative_video_url(tmp_path):
    """S1-16: finalize writes BASE_DIR-relative paths and goes through the stores."""
    from scripts.couple_engine.finalize import finalize_clip_export

    docs = tmp_path / "_Docs"
    exports = tmp_path / "04_Exports" / "Ready_to_post"
    exports.mkdir(parents=True)
    mp4 = exports / "20261109_tst01-pov-s01_v1.mp4"
    mp4.write_bytes(b"synthetic")
    result = finalize_clip_export("tst01-pov-s01", mp4, "TST01", "ang_tst_01",
                                  registry_dir=docs, gdrive_sync=False)

    (product,) = store_io.load_products(docs)
    (angle,) = product["angles"]
    assert angle["video_url"] == "04_Exports/Ready_to_post/20261109_tst01-pov-s01_v1.mp4"
    assert angle["cover_url"] == "04_Exports/Ready_to_post/20261109_tst01-pov-s01_v1.webp"
    assert [r["id"] for r in store_io.load_export_registry(docs)] == [result["export_id"]]
    (binding,) = store_io.load_cover_bindings(docs)
    assert binding["export_id"] == result["export_id"] and binding["id"]
    assert not (docs / ".export_finalize.lock").exists()
