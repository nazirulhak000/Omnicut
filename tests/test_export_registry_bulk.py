"""Regression tests for one-transaction export identity hydration."""

from scripts import export_registry
import json


def test_ensure_many_preserves_identity_and_enriches_records(monkeypatch, tmp_path):
    """Bulk hydration must create stable IDs once and enrich them later."""
    monkeypatch.setattr(export_registry, "BASE_DIR", tmp_path)
    monkeypatch.setattr(export_registry, "REGISTRY_PATH", tmp_path / "_Docs" / "export_registry.json")

    first = tmp_path / "04_Exports" / "Ready_to_post" / "first.mp4"
    second = tmp_path / "04_Exports" / "Ready_to_post" / "second.mp4"
    first.parent.mkdir(parents=True)
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    created = export_registry.ExportRegistry.ensure_many([
        {"path": first, "product_id": "p1", "angle_id": "a1", "status": "rendered"},
        {"path": second, "product_id": "p2", "angle_id": "a2", "status": "rendered"},
    ])

    assert len(created) == 2
    assert len({row["id"] for row in created}) == 2

    enriched = export_registry.ExportRegistry.ensure_many([
        {"path": first, "project_name": "project-first", "status": "posted", "posted_at": "2026-09-14T12:00:00"},
        {"path": second, "project_name": "project-second", "status": "rendered"},
    ])

    assert [row["id"] for row in enriched] == [row["id"] for row in created]
    assert enriched[0]["project_name"] == "project-first"
    assert enriched[0]["status"] == "posted"
    assert enriched[1]["project_name"] == "project-second"
    assert export_registry.ExportRegistry.path_index()[enriched[0]["path_key"]] == enriched[0]["id"]


def test_path_index_invalidates_and_updates_after_path_mutations(monkeypatch, tmp_path):
    """Schedule reads must see export moves, renames, and removals immediately."""
    monkeypatch.setattr(export_registry, "BASE_DIR", tmp_path)
    monkeypatch.setattr(export_registry, "REGISTRY_PATH", tmp_path / "_Docs" / "export_registry.json")
    export_registry.ExportRegistry._path_index = None

    source = tmp_path / "04_Exports" / "Ready_to_post" / "source.mp4"
    posted = tmp_path / "Posted" / "source.mp4"
    renamed = tmp_path / "Posted" / "renamed.mp4"
    source.parent.mkdir(parents=True)
    posted.parent.mkdir(parents=True)
    source.write_bytes(b"source")
    posted.write_bytes(b"source")
    renamed.write_bytes(b"source")

    record = export_registry.ExportRegistry.ensure(source, product_id="p1", angle_id="a1")
    source_key = record["path_key"]
    assert export_registry.ExportRegistry.path_index()[source_key] == record["id"]

    moved = export_registry.ExportRegistry.move_and_mark_posted(record["id"], posted)
    posted_key = export_registry._normalise_path(posted)
    assert moved["path_key"] == posted_key
    index_after_move = export_registry.ExportRegistry.path_index()
    assert index_after_move.get(source_key) is None
    assert index_after_move[posted_key] == record["id"]

    renamed_record = export_registry.ExportRegistry.update_path(record["id"], renamed)
    renamed_key = export_registry._normalise_path(renamed)
    assert renamed_record["path_key"] == renamed_key
    index_after_rename = export_registry.ExportRegistry.path_index()
    assert index_after_rename.get(posted_key) is None
    assert index_after_rename[renamed_key] == record["id"]

    export_registry.ExportRegistry.remove(record["id"])
    assert renamed_key not in export_registry.ExportRegistry.path_index()


def test_path_index_refreshes_after_external_json_mirror_edit(monkeypatch, tmp_path):
    """A direct mirror edit must not leave schedule lookups on stale data."""
    monkeypatch.setattr(export_registry, "BASE_DIR", tmp_path)
    registry_path = tmp_path / "_Docs" / "export_registry.json"
    monkeypatch.setattr(export_registry, "REGISTRY_PATH", registry_path)
    export_registry.ExportRegistry._path_index = None
    export_registry.ExportRegistry._path_index_signature = None

    source = tmp_path / "04_Exports" / "Ready_to_post" / "source.mp4"
    replacement = tmp_path / "Posted" / "replacement.mp4"
    source.parent.mkdir(parents=True)
    replacement.parent.mkdir(parents=True)
    source.write_bytes(b"source")
    replacement.write_bytes(b"source")
    record = export_registry.ExportRegistry.ensure(source, product_id="p1", angle_id="a1")
    source_key = record["path_key"]
    assert export_registry.ExportRegistry.path_index()[source_key] == record["id"]

    rows = json.loads(registry_path.read_text(encoding="utf-8"))
    rows[0]["path"] = str(replacement)
    rows[0]["path_key"] = export_registry._normalise_path(replacement)
    registry_path.write_text(json.dumps(rows), encoding="utf-8")

    replacement_key = rows[0]["path_key"]
    index = export_registry.ExportRegistry.path_index()
    assert index.get(source_key) is None
    assert index[replacement_key] == record["id"]
