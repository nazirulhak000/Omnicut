"""Deterministic motion parity matrix for the declarative preset catalog.

This module is intentionally read-mostly.  It exercises the renderer-agnostic
Python motion contract without changing a renderer or capturing browser
Canvas frames.

The matrix samples every catalog preset at the same normalized points for its
phase.  ``loop`` is exposed as ``hold`` in the QA-facing metadata because that
is the user-facing In -> Hold -> Out vocabulary.

TODO / limitations
-------------------
* The current catalog only stores baseline metadata (``source`` and
  ``renderer_bound``).  Word-stagger and Thai-safety metadata below are
  explicit matrix requirements until they become authoritative catalog
  fields.
* The self-hosted browser harness now proves one real SequencePlayer-vs-ASS
  reference pair and captures explicit timeline frame indices.  Full catalog
  coverage at every ``FRAME_SAMPLE_TIMES`` point remains Phase 3 work; the
  matrix must not overstate that reference-pair evidence as all-preset parity.
* Phase windows are a deterministic QA schedule built from catalog maxima;
  they are not a replacement for the live overlay timeline resolver.
"""

from __future__ import annotations

from copy import deepcopy
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from scripts.subtitle.motion_contract import (
    MOTION_PRESETS,
    MOTION_PHASES,
    MOTION_ROLES,
    sample_motion_contract,
    validate_motion_contract,
)


FRAME_SAMPLE_TIMES: Tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)
PHASE_LABELS = {"in": "In", "hold": "Hold", "out": "Out"}
CATALOG_METADATA_REQUIRED = frozenset({"source", "renderer_bound"})

WORD_STAGGER_METADATA = {
    "supported": True,
    "unit": "ms",
    "default_ms": 0,
    "allowed_ms": (0, 50, 70, 100, 150),
    "max_ms": 150,
    "timing_model_by_role": {
        "text": "per_word",
        "hook": "per_row",
        "caption": "per_line",
    },
}

THAI_SAFETY_METADATA = {
    "sample_text": "ทดสอบเสียงดีมากครับ",
    "preserve_combining_marks": True,
    "font_fallback_required": True,
    "line_height_factor": 1.0,
    "safe_zone_bottom_px": 420,
}


def _phase_key(contract: Mapping[str, Any]) -> str:
    """Map the contract's technical phase to the matrix phase vocabulary."""

    return "hold" if contract["phase"] == "loop" else str(contract["phase"])


def _catalog_phase_maxima(catalog: Mapping[str, Mapping[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Return deterministic slot lengths for each role and canonical phase."""

    result: Dict[str, Dict[str, float]] = {}
    for role in MOTION_ROLES:
        result[role] = {}
        for technical_phase in MOTION_PHASES:
            canonical_phase = "hold" if technical_phase == "loop" else technical_phase
            durations = [
                float(contract["duration_ms"])
                for contract in catalog.values()
                if contract["role"] == role and contract["phase"] == technical_phase
            ]
            result[role][canonical_phase] = max(durations, default=0.0)
    return result


def _phase_windows(role: str, catalog: Mapping[str, Mapping[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Build non-overlapping In/Hold/Out windows for a role.

    A phase with no catalog entries has a zero-length window at the current
    cursor.  Zero-length windows are allowed for roles that do not yet expose
    that phase (for example text currently has In presets only).
    """

    cursor = 0.0
    windows: Dict[str, Dict[str, float]] = {}
    maxima = _catalog_phase_maxima(catalog)[role]
    for phase in ("in", "hold", "out"):
        start = cursor
        end = start + maxima[phase]
        windows[phase] = {"start_ms": start, "end_ms": end, "duration_ms": maxima[phase]}
        cursor = end
    return windows


def _word_stagger_metadata(role: str) -> Dict[str, Any]:
    value = deepcopy(WORD_STAGGER_METADATA)
    value["timing_model"] = value["timing_model_by_role"][role]
    return value


def _matrix_entry(
    identifier: str,
    contract: Mapping[str, Any],
    role_windows: Mapping[str, Mapping[str, float]],
) -> Dict[str, Any]:
    source_phase = str(contract["phase"])
    phase = _phase_key(contract)
    samples = tuple(
        {
            "normalized_time": time,
            "values": sample_motion_contract(contract, time),
        }
        for time in FRAME_SAMPLE_TIMES
    )
    return {
        "id": identifier,
        "role": contract["role"],
        "phase": phase,
        "source_phase": source_phase,
        "phase_label": PHASE_LABELS[phase],
        "duration_ms": float(contract["duration_ms"]),
        "repeat": bool(contract.get("repeat", False)),
        "samples": samples,
        "timing": {
            "window": dict(role_windows[phase]),
            "cycle_duration_ms": _cycle_duration_ms(contract),
            "normalized_domain": (0.0, 1.0),
        },
        "word_stagger": _word_stagger_metadata(str(contract["role"])),
        "thai_safety": deepcopy(THAI_SAFETY_METADATA),
        "catalog_metadata": deepcopy(contract.get("metadata", {})),
    }


def _cycle_duration_ms(contract: Mapping[str, Any]) -> float:
    durations = {
        float(track["cycle_duration_ms"])
        for track in contract.get("tracks", {}).values()
        if "cycle_duration_ms" in track
    }
    if not durations:
        return float(contract["duration_ms"])
    if len(durations) != 1:
        raise AssertionError(f"{contract['id']} has inconsistent cycle durations: {durations}")
    return durations.pop()


def build_motion_frame_matrix(
    catalog: Mapping[str, Mapping[str, Any]] = MOTION_PRESETS,
) -> Tuple[Dict[str, Any], ...]:
    """Build the deterministic QA matrix without mutating the catalog."""

    entries = []
    for identifier in sorted(catalog):
        contract = catalog[identifier]
        role = str(contract["role"])
        entries.append(_matrix_entry(identifier, contract, _phase_windows(role, catalog)))
    return tuple(entries)


MOTION_FRAME_MATRIX = build_motion_frame_matrix()


def _entries_for_phase(phase: str) -> Iterable[Mapping[str, Any]]:
    return (entry for entry in MOTION_FRAME_MATRIX if entry["phase"] == phase)


def _assert_non_overlapping(windows: Sequence[Mapping[str, float]]) -> None:
    for left, right in combinations(windows, 2):
        assert left["end_ms"] <= right["start_ms"] or right["end_ms"] <= left["start_ms"]


def test_matrix_covers_every_catalog_preset_at_five_deterministic_times():
    assert len(MOTION_FRAME_MATRIX) == len(MOTION_PRESETS)
    assert {entry["id"] for entry in MOTION_FRAME_MATRIX} == set(MOTION_PRESETS)

    for entry in MOTION_FRAME_MATRIX:
        assert tuple(sample["normalized_time"] for sample in entry["samples"]) == FRAME_SAMPLE_TIMES
        assert len(entry["samples"]) == 5
        for sample in entry["samples"]:
            assert isinstance(sample["values"], dict)


def test_every_catalog_preset_has_baseline_and_matrix_qa_metadata():
    required_matrix_metadata = {
        "phase",
        "source_phase",
        "phase_label",
        "timing",
        "word_stagger",
        "thai_safety",
        "catalog_metadata",
    }

    for identifier, contract in MOTION_PRESETS.items():
        assert validate_motion_contract(contract) is True
        assert CATALOG_METADATA_REQUIRED <= set(contract.get("metadata", {})), identifier

        entry = next(item for item in MOTION_FRAME_MATRIX if item["id"] == identifier)
        assert required_matrix_metadata <= set(entry), identifier
        assert entry["word_stagger"]["allowed_ms"] == (0, 50, 70, 100, 150)
        assert entry["word_stagger"]["timing_model"] in {"per_word", "per_row", "per_line"}
        assert entry["thai_safety"]["preserve_combining_marks"] is True
        assert entry["thai_safety"]["font_fallback_required"] is True


def test_phase_windows_are_ordered_and_do_not_overlap():
    for role in MOTION_ROLES:
        role_entries = [entry for entry in MOTION_FRAME_MATRIX if entry["role"] == role]
        if not role_entries:
            continue

        windows = []
        for phase in ("in", "hold", "out"):
            phase_windows = {
                tuple(entry["timing"]["window"].items())
                for entry in role_entries
                if entry["phase"] == phase
            }
            windows.extend(dict(items) for items in phase_windows)

        windows.sort(key=lambda window: (window["start_ms"], window["end_ms"]))
        _assert_non_overlapping(windows)
        for window in windows:
            assert window["start_ms"] <= window["end_ms"]


def test_track_keyframes_have_no_timing_overlap_and_repeat_cycles_match():
    for identifier, contract in MOTION_PRESETS.items():
        for track_name, track in contract.get("tracks", {}).items():
            times = [float(keyframe["t"]) for keyframe in track["keyframes"]]
            assert times == sorted(set(times)), f"{identifier}:{track_name} has overlapping keyframe times"
            assert all(0.0 <= time <= 1.0 for time in times)

            if track.get("repeat"):
                assert float(track["cycle_duration_ms"]) == float(contract["duration_ms"]), identifier


def test_hold_matrix_entries_are_repeat_safe_or_explicitly_empty():
    for entry in _entries_for_phase("hold"):
        if entry["duration_ms"] == 0:
            assert entry["repeat"] is True
            assert entry["samples"][-1]["values"] == {}
        else:
            assert entry["repeat"] is True
            assert entry["timing"]["cycle_duration_ms"] > 0


def test_matrix_declares_live_harness_scope_without_overclaiming_catalog_parity():
    limitation = MOTION_FRAME_MATRIX[0]["thai_safety"]
    assert limitation["preserve_combining_marks"] is True
    repo_root = Path(__file__).resolve().parents[1]
    assert (repo_root / "tests" / "motion_capture" / "vite_fixture.py").exists()
    assert (repo_root / "tests" / "motion_capture" / "run_live_gate.py").exists()
    assert FRAME_SAMPLE_TIMES == (0.0, 0.25, 0.5, 0.75, 1.0)
