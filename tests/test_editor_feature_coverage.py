"""Regression gates for the Editor UI-to-render coverage contract."""

from __future__ import annotations

from copy import deepcopy
import re

from tools.editor_feature_coverage import (
    DEFAULT_MATRIX,
    load_matrix,
    readiness_counts,
    validate_matrix,
)


def _inspector_render_clip_fields() -> set[str]:
    source = (DEFAULT_MATRIX.parents[2] / "frontend" / "src" / "components" / "editor" / "Inspector.jsx").read_text(encoding="utf-8")
    match = re.search(r"export const RENDER_CLIP_FIELDS = \[(.*?)\];", source, re.DOTALL)
    assert match, "Inspector.jsx must keep an explicit RENDER_CLIP_FIELDS contract"
    return set(re.findall(r"['\"]([a-z_]+)['\"]", match.group(1)))


def test_real_coverage_matrix_is_complete_and_source_backed():
    matrix = load_matrix()
    assert validate_matrix(matrix) == []


def test_every_inspector_render_clip_field_has_exactly_one_feature_owner():
    matrix = load_matrix()
    claimed = [
        field
        for feature in matrix["features"]
        for field in feature.get("clip_fields", [])
    ]
    assert set(claimed) == _inspector_render_clip_fields()
    assert len(claimed) == len(set(claimed))


def test_missing_render_consumer_fails_the_gate():
    matrix = load_matrix()
    broken = deepcopy(matrix)
    feature = next(item for item in broken["features"] if item["id"] == "spotlight")
    feature["consumers"].pop("render")
    errors = validate_matrix(broken, check_sources=False)
    assert any("spotlight missing consumer stages: render" in error for error in errors)


def test_approximation_without_reason_or_disclosure_fails_the_gate():
    matrix = load_matrix()
    broken = deepcopy(matrix)
    feature = next(item for item in broken["features"] if item["id"] == "clip_color")
    feature.pop("approximation_reason")
    feature.pop("ui_disclosure_policy")
    errors = validate_matrix(broken, check_sources=False)
    assert any("clip_color approximation_reason is required" in error for error in errors)
    assert any("clip_color ui_disclosure_policy is required" in error for error in errors)


def test_editor_only_feature_does_not_require_preview_or_render_consumers():
    matrix = load_matrix()
    feature = next(item for item in matrix["features"] if item["id"] == "editor_ux_controls")
    assert set(feature["consumers"]) == {"ui", "state"}
    assert not [error for error in validate_matrix(matrix, check_sources=False) if error.startswith("editor_ux_controls missing")]


def test_blocked_and_untested_features_are_not_counted_as_ready():
    counts = readiness_counts(load_matrix())
    ready = counts["PASS"] + counts["APPROXIMATION"]
    not_ready = counts["BLOCKED"] + counts["UNTESTED"]
    assert ready + not_ready == sum(counts.values())
    assert counts["BLOCKED"] > 0
    assert counts["UNTESTED"] > 0
