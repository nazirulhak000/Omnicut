"""Validate the Editor UI-to-render feature coverage contract."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = REPO_ROOT / "_Docs" / "Reports" / "EDITOR_FEATURE_COVERAGE_MATRIX_20260922.json"
READINESS = {"PASS", "APPROXIMATION", "BLOCKED", "UNTESTED"}
RENDERABILITY_STAGES = {
    "rendered": {"ui", "state", "persistence", "render_payload", "preview", "render"},
    "playback_only": {"ui", "state", "persistence", "preview"},
    "orchestration": {"ui", "state", "persistence", "render_payload"},
    "editor_only": {"ui", "state"},
}


def load_matrix(path: Path = DEFAULT_MATRIX) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_source_reference(
    record: Mapping[str, Any],
    *,
    feature_id: str,
    location: str,
) -> list[str]:
    errors: list[str] = []
    relative_path = str(record.get("path") or "").strip()
    if not relative_path:
        return [f"{feature_id}:{location} has no path"]
    source_path = (REPO_ROOT / relative_path).resolve()
    if not source_path.is_relative_to(REPO_ROOT):
        return [f"{feature_id}:{location} escapes repository root: {relative_path}"]
    if not source_path.is_file():
        return [f"{feature_id}:{location} path does not exist: {relative_path}"]
    source = source_path.read_text(encoding="utf-8", errors="replace")
    tokens = record.get("tokens")
    if not isinstance(tokens, list) or not tokens:
        errors.append(f"{feature_id}:{location} must declare at least one source token")
    else:
        for token in tokens:
            if not isinstance(token, str) or not token:
                errors.append(f"{feature_id}:{location} contains an invalid token")
            elif token not in source:
                errors.append(f"{feature_id}:{location} token not found in {relative_path}: {token!r}")
    return errors


def validate_matrix(matrix: Mapping[str, Any], *, check_sources: bool = True) -> list[str]:
    errors: list[str] = []
    if matrix.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    features = matrix.get("features")
    if not isinstance(features, list) or not features:
        return errors + ["features must be a non-empty list"]

    identifiers: list[str] = []
    claimed_clip_fields: list[str] = []
    for index, feature in enumerate(features):
        if not isinstance(feature, Mapping):
            errors.append(f"features[{index}] must be an object")
            continue
        feature_id = str(feature.get("id") or "").strip()
        if not feature_id:
            errors.append(f"features[{index}] has no id")
            feature_id = f"features[{index}]"
        identifiers.append(feature_id)

        readiness = feature.get("readiness")
        if readiness not in READINESS:
            errors.append(f"{feature_id} has unknown readiness: {readiness!r}")
        renderability = feature.get("renderability")
        required_stages = RENDERABILITY_STAGES.get(str(renderability))
        if required_stages is None:
            errors.append(f"{feature_id} has unknown renderability: {renderability!r}")
            required_stages = set()

        blockers = feature.get("blockers")
        if not isinstance(blockers, list):
            errors.append(f"{feature_id} blockers must be a list")
            blockers = []
        if readiness == "PASS" and blockers:
            errors.append(f"{feature_id} cannot be PASS while blockers are present")
        if readiness in {"BLOCKED", "UNTESTED"} and not blockers:
            errors.append(f"{feature_id} {readiness} must explain at least one blocker")
        if readiness == "APPROXIMATION":
            if not str(feature.get("approximation_reason") or "").strip():
                errors.append(f"{feature_id} approximation_reason is required")
            if not str(feature.get("ui_disclosure_policy") or "").strip():
                errors.append(f"{feature_id} ui_disclosure_policy is required")

        clip_fields = feature.get("clip_fields")
        if not isinstance(clip_fields, list):
            errors.append(f"{feature_id} clip_fields must be a list")
        else:
            claimed_clip_fields.extend(str(field) for field in clip_fields)

        consumers = feature.get("consumers")
        if not isinstance(consumers, Mapping):
            errors.append(f"{feature_id} consumers must be an object")
            consumers = {}
        missing_stages = sorted(required_stages - set(consumers))
        if missing_stages:
            errors.append(f"{feature_id} missing consumer stages: {', '.join(missing_stages)}")
        for stage, records in consumers.items():
            if not isinstance(records, list) or not records:
                errors.append(f"{feature_id}:{stage} must be a non-empty list")
                continue
            if check_sources:
                for record_index, record in enumerate(records):
                    if not isinstance(record, Mapping):
                        errors.append(f"{feature_id}:{stage}[{record_index}] must be an object")
                    else:
                        errors.extend(
                            _validate_source_reference(
                                record,
                                feature_id=feature_id,
                                location=f"{stage}[{record_index}]",
                            )
                        )

        evidence = feature.get("automated_evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{feature_id} must declare automated_evidence")
        elif check_sources:
            for evidence_index, record in enumerate(evidence):
                if not isinstance(record, Mapping):
                    errors.append(f"{feature_id}:automated_evidence[{evidence_index}] must be an object")
                else:
                    errors.extend(
                        _validate_source_reference(
                            record,
                            feature_id=feature_id,
                            location=f"automated_evidence[{evidence_index}]",
                        )
                    )

    duplicate_ids = sorted(identifier for identifier, count in Counter(identifiers).items() if count > 1)
    if duplicate_ids:
        errors.append(f"duplicate feature ids: {', '.join(duplicate_ids)}")
    duplicate_fields = sorted(field for field, count in Counter(claimed_clip_fields).items() if count > 1)
    if duplicate_fields:
        errors.append(f"clip fields claimed by more than one feature: {', '.join(duplicate_fields)}")
    return errors


def readiness_counts(matrix: Mapping[str, Any]) -> dict[str, int]:
    counts = Counter(str(feature.get("readiness")) for feature in matrix.get("features", []))
    return {status: counts.get(status, 0) for status in sorted(READINESS)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the Editor feature coverage matrix")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    args = parser.parse_args(argv)
    matrix = load_matrix(args.matrix)
    errors = validate_matrix(matrix)
    output = {
        "ok": not errors,
        "feature_count": len(matrix.get("features", [])),
        "readiness": readiness_counts(matrix),
        "errors": errors,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
