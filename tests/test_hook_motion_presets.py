"""Behavioral tests for scripts/hook_motion_presets.py.

This module is a pure data table: four dicts of {preset_id: {label_th,
label_en}} served to the editor's motion pickers via hook_motion_catalog(),
plus consumed by an API route (see test_phase1_smoke.py's
test_preset_catalog_matches_the_builder_registries, which already guards
that these keys stay in lockstep with subtitle_engine.py's HOOK_*_BUILDERS
registries -- that cross-module contract is intentionally NOT duplicated
here). This file is scoped to hook_motion_presets.py's own surface: is every
preset structurally valid, does the assembled catalog have the shape the
frontend/API expects, and does every category carry the "none" fallback key
a caller would fall back to for an unrecognized preset id.

No imports of scripts.subtitle_engine or scripts.subtitle here -- those are
being edited by another agent in this session, per task scope.
"""
import pytest

from scripts.hook_motion_presets import (
    HOOK_IN_PRESETS,
    HOOK_REVEAL_PRESETS,
    HOOK_LOOP_PRESETS,
    HOOK_OUT_PRESETS,
    HOOK_ACCENT_PRESETS,
    hook_motion_catalog,
)

ALL_CATEGORY_TABLES = {
    "in": HOOK_IN_PRESETS,
    "reveal": HOOK_REVEAL_PRESETS,
    "loop": HOOK_LOOP_PRESETS,
    "out": HOOK_OUT_PRESETS,
    "accent": HOOK_ACCENT_PRESETS,
}


@pytest.mark.parametrize("category, table", ALL_CATEGORY_TABLES.items())
def test_every_preset_has_both_language_labels(category, table):
    assert table, f"{category} preset table is empty"
    for preset_id, entry in table.items():
        assert isinstance(entry, dict), f"{category}.{preset_id} is not a dict"
        assert "label_th" in entry, f"{category}.{preset_id} missing label_th"
        assert "label_en" in entry, f"{category}.{preset_id} missing label_en"
        assert isinstance(entry["label_th"], str) and entry["label_th"].strip()
        assert isinstance(entry["label_en"], str) and entry["label_en"].strip()


@pytest.mark.parametrize("category, table", ALL_CATEGORY_TABLES.items())
def test_preset_ids_are_non_empty_strings_with_no_duplicates(category, table):
    ids = list(table.keys())
    assert all(isinstance(i, str) and i for i in ids)
    assert len(ids) == len(set(ids)), f"{category} has duplicate preset ids"


@pytest.mark.parametrize("category, table", ALL_CATEGORY_TABLES.items())
def test_every_category_has_a_none_fallback(category, table):
    """A consumer resolving an unrecognized preset name is expected to fall
    back to "none" (see subtitle_engine.py's _resolve_hook_motion pattern)
    rather than KeyError deep in a render -- that fallback only behaves
    predictably if "none" always exists as a real entry in every category.
    This is the concrete guarantee this data module owes its consumers."""
    assert "none" in table, f"{category} preset table has no 'none' fallback entry"


def test_hook_motion_catalog_shape_matches_the_pickers():
    catalog = hook_motion_catalog()
    assert set(catalog.keys()) == {"in", "reveal", "loop", "out", "accent"}
    assert catalog["in"] is HOOK_IN_PRESETS
    assert catalog["reveal"] is HOOK_REVEAL_PRESETS
    assert catalog["loop"] is HOOK_LOOP_PRESETS
    assert catalog["out"] is HOOK_OUT_PRESETS
    assert catalog["accent"] is HOOK_ACCENT_PRESETS


def test_hook_motion_catalog_is_json_serializable():
    """The catalog is served over an API route to the frontend -- anything
    that can't round-trip through json would break that response."""
    import json
    catalog = hook_motion_catalog()
    encoded = json.dumps(catalog, ensure_ascii=False)
    decoded = json.loads(encoded)
    assert decoded == catalog


def test_lookup_by_unknown_preset_id_returns_none_not_keyerror():
    """Documents the expected consumer pattern for an invalid/unknown preset
    name: dict.get(name) returns None rather than raising, and a caller that
    falls back to the "none" entry on a falsy get() gets a real, valid
    entry rather than KeyError deep in a render. This module itself has no
    lookup function -- it's a plain dict -- so this test exercises the
    exact access pattern a consumer is expected to use."""
    for category, table in ALL_CATEGORY_TABLES.items():
        result = table.get("totally_made_up_preset_name")
        assert result is None
        fallback = table.get("totally_made_up_preset_name") or table["none"]
        assert fallback == table["none"]
