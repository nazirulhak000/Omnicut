"""Parity/UX verification gates for the declarative motion catalog.

This file intentionally tests contracts and adapters only.  It must not import
or modify the live Canvas/ASS renderer implementations.
"""

from __future__ import annotations

import math
import unicodedata

from scripts.subtitle.motion_contract import (
    MOTION_PHASES,
    MOTION_PRESETS,
    MOTION_ROLES,
    LEGACY_MOTION_IDS,
    resolve_legacy_motion_id,
    sample_motion_contract,
)
from tests.motion_frame_matrix import (
    FRAME_SAMPLE_TIMES,
    MOTION_FRAME_MATRIX,
    THAI_SAFETY_METADATA,
)


EXPECTED_PRESET_IDS = frozenset(
    {
        "hook.in.blur",
        "hook.in.bounce",
        "hook.in.bounce_soft",
        "hook.in.elastic_bounce",
        "hook.in.fade",
        "hook.in.none",
        "hook.in.pop",
        "hook.in.pop_soft",
        "hook.in.pop_zoom",
        "hook.in.quick_fade",
        "hook.in.rise",
        "hook.in.slam",
        "hook.in.slide_up",
        "hook.in.snap",
        "hook.in.stamp",
        "hook.in.typewriter",
        "hook.in.zoom",
        "hook.loop.flicker",
        "hook.loop.lightsweep",
        "hook.loop.none",
        "hook.loop.pulse",
        "hook.loop.shake",
        "hook.loop.wave",
        "hook.out.fade",
        "hook.out.glitch",
        "hook.out.none",
        "hook.out.slide",
        "hook.out.zoom",
        "text.in.none",
        "text.in.pop_zoom",
        "text.in.quick_fade",
        "text.in.rise",
        "text.in.snap",
        "text.in.stamp",
    }
)

EXPECTED_TEXT_LEGACY_MAP = {
    "pop": "snap",
    "zoom": "pop_zoom",
    "stamp": "stamp",
    "fade": "quick_fade",
    "slide": "rise",
    "none": "none",
}


def _assert_finite_tree(value):
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        assert math.isfinite(value)
        return
    if isinstance(value, dict):
        for child in value.values():
            _assert_finite_tree(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _assert_finite_tree(child)


def test_catalog_is_exactly_the_34_preset_parity_surface():
    assert len(MOTION_PRESETS) == 34
    assert set(MOTION_PRESETS) == EXPECTED_PRESET_IDS
    assert {entry["id"] for entry in MOTION_FRAME_MATRIX} == EXPECTED_PRESET_IDS


def test_all_34_presets_sample_at_the_shared_frame_times_without_non_finite_state():
    for identifier, preset in MOTION_PRESETS.items():
        for normalized_time in FRAME_SAMPLE_TIMES:
            sampled = sample_motion_contract(preset, normalized_time)
            _assert_finite_tree(sampled)


def test_phase_order_is_explicit_and_uses_hold_as_the_ui_alias_for_loop():
    assert MOTION_PHASES == ("in", "loop", "out")
    assert [entry["phase"] for entry in MOTION_FRAME_MATRIX if entry["id"] == "hook.in.snap"] == ["in"]
    assert {entry["phase_label"] for entry in MOTION_FRAME_MATRIX if entry["source_phase"] == "loop"} == {"Hold"}
    assert {entry["phase_label"] for entry in MOTION_FRAME_MATRIX if entry["source_phase"] == "in"} == {"In"}
    assert {entry["phase_label"] for entry in MOTION_FRAME_MATRIX if entry["source_phase"] == "out"} == {"Out"}


def test_legacy_mapping_is_exhaustive_and_role_scoped():
    assert LEGACY_MOTION_IDS["text"]["in"] == EXPECTED_TEXT_LEGACY_MAP
    for legacy_id, canonical_id in EXPECTED_TEXT_LEGACY_MAP.items():
        assert resolve_legacy_motion_id("text", "in", legacy_id) == canonical_id

    for role in MOTION_ROLES:
        for phase in MOTION_PHASES:
            assert resolve_legacy_motion_id(role, phase, "unknown_motion_id") == "unknown_motion_id"
    assert resolve_legacy_motion_id("hook", "in", "pop") == "pop"
    assert resolve_legacy_motion_id("hook", "loop", "wave") == "wave"
    assert resolve_legacy_motion_id("hook", "out", "glitch") == "glitch"


def test_short_duration_presets_are_explicitly_tested_and_never_collapse_nonzero_windows():
    short = {
        identifier: preset
        for identifier, preset in MOTION_PRESETS.items()
        if 0 < float(preset["duration_ms"]) < 120
    }
    assert set(short) == {
        "hook.in.pop_zoom",
        "hook.in.snap",
        "hook.in.stamp",
        "hook.out.none",
        "text.in.pop_zoom",
        "text.in.snap",
        "text.in.stamp",
    }

    for preset in short.values():
        assert float(preset["duration_ms"]) > 0
        for normalized_time in (0.0, 0.5, 1.0):
            _assert_finite_tree(sample_motion_contract(preset, normalized_time))

    zero_duration = [preset for preset in MOTION_PRESETS.values() if float(preset["duration_ms"]) == 0]
    assert zero_duration
    assert all(not preset["tracks"] for preset in zero_duration)


def test_thai_text_safety_fixture_contains_combining_marks_and_declares_safe_zone():
    sample = "\u0e17\u0e14\u0e2a\u0e2d\u0e1a\u0e40\u0e2a\u0e35\u0e22\u0e07\u0e14\u0e35\u0e21\u0e32\u0e01\u0e04\u0e23\u0e31\u0e1a"
    thai_mark_ranges = ((0x0E31, 0x0E3A), (0x0E47, 0x0E4E))
    assert any(any(start <= ord(character) <= end for start, end in thai_mark_ranges) for character in sample)
    assert THAI_SAFETY_METADATA["preserve_combining_marks"] is True
    assert THAI_SAFETY_METADATA["font_fallback_required"] is True
    assert THAI_SAFETY_METADATA["safe_zone_bottom_px"] == 420

    # A parity fixture must preserve the source text through Unicode NFC/NFD
    # normalization; the renderers are not allowed to strip Thai marks.
    assert unicodedata.normalize("NFC", sample) == sample
    assert unicodedata.normalize("NFD", unicodedata.normalize("NFC", sample)) == unicodedata.normalize("NFD", sample)
    for entry in MOTION_FRAME_MATRIX:
        assert entry["thai_safety"]["preserve_combining_marks"] is True


def test_catalog_metadata_declares_contract_binding_and_the_one_geometry_fallback():
    fallback_ids = {
        identifier
        for identifier, preset in MOTION_PRESETS.items()
        if not preset["metadata"]["renderer_bound"]
    }
    assert fallback_ids == {"hook.in.typewriter"}
    assert MOTION_PRESETS["hook.in.typewriter"]["metadata"]["unsupported_tracks"] == ["reveal"]
    for identifier, preset in MOTION_PRESETS.items():
        assert preset["metadata"]["parity_level"] in {"exact", "bounded", "legacy_fallback"}, identifier
