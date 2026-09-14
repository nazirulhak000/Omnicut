"""Regression tests for one-transaction export identity hydration."""

from scripts import export_registry


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
