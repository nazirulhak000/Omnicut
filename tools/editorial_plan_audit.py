"""Bounded, read-only saved-plan metadata audit; never opens media or rewrites plans.

Usage: python tools/editorial_plan_audit.py path/to/project.json
JSON goes to stdout. Missing metadata stays unknown; overlap is a planned source
span fact, not evidence that a rendered frame or its topic is wrong.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

MAX_BYTES = 8 * 1024 * 1024
MAX_ITEMS = 10000
EPSILON = 1e-6


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _union(spans):
    result = []
    for start, end in sorted(spans):
        if end <= start:
            continue
        if result and start <= result[-1][1] + EPSILON:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result


def _gaps(start, end, covered):
    gaps, cursor = [], start
    for first, stop in _union(covered):
        if stop <= cursor or first >= end:
            continue
        if first > cursor + EPSILON:
            gaps.append([cursor, min(first, end)])
        cursor = max(cursor, stop)
    if end > cursor + EPSILON:
        gaps.append([cursor, end])
    return gaps


def _bounded_records(value, label):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    if len(value) > MAX_ITEMS:
        raise ValueError(f"{label} exceeds {MAX_ITEMS} items")
    return value


def _source_key(path):
    # Lexical only: no existence checks or media filesystem traversal. Windows
    # paths are case-insensitive; POSIX paths retain their case.
    path = str(path or "").replace("\\", "/")
    return path.casefold() if len(path) > 1 and path[1] == ":" else path


def audit_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Audit the saved render plan and its explicit timed cues/sentences."""
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be an object")
    params = manifest.get("render_params") or {}
    if not isinstance(params, dict):
        raise ValueError("render_params must be an object")
    clips = _bounded_records(manifest.get("clip_list", params.get("clip_list")), "clip_list")
    cues = _bounded_records(manifest.get("cues"), "cues")
    sentences = _bounded_records(manifest.get("sentences"), "sentences")
    report = {"schema_version": "editorial-plan-audit.v1", "read_only": True,
              "evidence": "saved_metadata_only", "project_name": manifest.get("project_name"),
              "clips": [], "reuses": [], "holds": [], "issues": [], "cue_coverage": [],
              "sentence_coverage": [], "unknowns": ["visual_topic_accuracy", "decoded_frame_repetition",
                                                        "source_file_duration_and_availability"]}
    summary = {"clip_count": len(clips), "valid_clip_count": 0, "source_count": 0,
               "reused_source_seconds": 0.0, "replay_risk_count": 0, "manual_reuse_count": 0,
               "intentional_reuse_count": 0, "hold_count": 0, "hold_seconds": 0.0,
               "declared_shortage_count": 0, "bounded_window_count": 0,
               "manual_pinned_count": 0, "cue_count": len(cues), "sentence_count": len(sentences)}
    report["summary"] = summary
    source_spans, durations = {}, []
    timing_complete = True
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict):
            report["issues"].append({"kind": "invalid_clip", "clip_index": index})
            timing_complete = False
            continue
        start, end, speed = (_number(clip.get("trim_start", 0)), _number(clip.get("trim_end")),
                             _number(clip.get("speed", 1)))
        freeze = _number(clip.get("freeze_tail", 0))
        summary["manual_pinned_count"] += bool(clip.get("manual_pinned"))
        source = _source_key(clip.get("source_path"))
        if not source or start is None or end is None or speed is None or freeze is None or start < 0 or end <= start or speed <= 0 or freeze < 0:
            report["issues"].append({"kind": "unknown_or_invalid_clip_timing", "clip_index": index})
            timing_complete = False
            continue
        freeze_used = min(10, freeze)
        if freeze > 10:
            report["issues"].append({"kind": "freeze_clamped", "clip_index": index, "declared": freeze, "effective": 10})
        declared_speed = speed
        speed = min(4, max(.25, speed))
        if speed != declared_speed:
            report["issues"].append({"kind": "speed_clamped_by_renderer", "clip_index": index,
                                      "declared": declared_speed, "effective": speed})
        minimum_span = 1 / 30 if isinstance(clip.get("source_window"), dict) else .2
        source_span = max(minimum_span, end - start)
        if source_span > end - start + EPSILON:
            report["issues"].append({"kind": "source_span_expanded_by_renderer", "clip_index": index,
                                      "declared": end - start, "effective": source_span})
            if "expanded_source_span_replay_analysis" not in report["unknowns"]:
                report["unknowns"].append("expanded_source_span_replay_analysis")
        duration = max(minimum_span, source_span / speed) + freeze_used
        if not math.isfinite(duration):
            report["issues"].append({"kind": "unknown_or_invalid_clip_timing", "clip_index": index})
            timing_complete = False
            continue
        durations.append(duration)
        summary["valid_clip_count"] += 1
        row = {"clip_index": index, "source": source, "trim_start": start, "trim_end": end,
               "speed": speed, "played_duration": duration, "manual_pinned": bool(clip.get("manual_pinned"))}
        report["clips"].append(row)
        declared = _number(clip.get("duration"))
        if declared is not None and abs(declared - duration) > 1 / 30:
            report["issues"].append({"kind": "saved_duration_differs_from_trim_speed", "clip_index": index,
                                      "saved": declared, "effective": duration})
        window = clip.get("source_window")
        if isinstance(window, dict):
            low, high = _number(window.get("start")), _number(window.get("end"))
            if low is not None and high is not None and high > low:
                summary["bounded_window_count"] += 1
                if start < low - EPSILON or end > high + EPSILON:
                    report["issues"].append({"kind": "semantic_window_bounds_violation", "clip_index": index,
                                              "window": [low, high], "trim": [start, end]})
            else:
                report["issues"].append({"kind": "invalid_source_window", "clip_index": index})
        shortage = clip.get("footage_shortage")
        if isinstance(shortage, dict):
            summary["declared_shortage_count"] += 1
        raw_held = clip.get("held_source_time")
        held = _number(raw_held) if isinstance(raw_held, (int, float)) and not isinstance(raw_held, bool) else None
        if raw_held is not None and held is None:
            report["issues"].append({"kind": "unrecognized_held_source_time", "clip_index": index})
        if held is not None and freeze_used > 0:
            if held < start - EPSILON or held >= end:
                report["issues"].append({"kind": "held_frame_outside_trim", "clip_index": index, "held_source_time": held})
            row["held_source_time"] = held
        if freeze_used > 0:
            summary["hold_count"] += 1
            summary["hold_seconds"] += freeze_used
            reason = shortage.get("reason") if isinstance(shortage, dict) else None
            report["holds"].append({"clip_index": index, "seconds": freeze_used,
                                    "classification": "exhaustion_hold_as_declared" if reason == "source_window_exhausted" else "declared_freeze",
                                    "held_source_time": held})
        previous = source_spans.setdefault(source, [])
        # A held-only continuation seeks one frame to reproduce the saved hold;
        # it is excluded from moving-source replay counts.
        held_only = held is not None and freeze_used > 0 and source_span <= 1 / 30 + EPSILON
        if not held_only:
            overlaps = [[max(start, a), min(end, b)] for a, b in _union(previous)
                        if min(end, b) > max(start, a) + EPSILON]
            reused = sum(b - a for a, b in overlaps)
            if reused > EPSILON:
                if clip.get("allow_source_reuse") is True or clip.get("repeat_intent"):
                    classification = "intentional_reuse"
                    summary["intentional_reuse_count"] += 1
                elif clip.get("manual_pinned"):
                    classification = "manual_reuse_review"
                    summary["manual_reuse_count"] += 1
                else:
                    classification = "unmarked_replay_risk"
                    summary["replay_risk_count"] += 1
                report["reuses"].append({"clip_index": index, "classification": classification,
                                        "source_intervals": overlaps, "source_seconds": reused,
                                        "previous_clip_indices": [prior["clip_index"] for prior in report["clips"][:-1]
                                            if prior["source"] == source and min(end, prior["trim_end"]) > max(start, prior["trim_start"]) + EPSILON]})
                summary["reused_source_seconds"] += reused
            previous.append([start, end])
    summary["source_count"] = len(source_spans)
    expected = _number(manifest.get("total_duration"))
    report["expected_duration"] = expected
    tracks = {clip.get("track_id", "video-1") for clip in clips if isinstance(clip, dict)}
    if len(tracks) > 1 or any(isinstance(clip, dict) and any(k in clip for k in ("timeline_start", "timeline_offset")) for clip in clips):
        timing_complete = False
        report["unknowns"].append("multitrack_or_explicit_timeline_layout")
    if timing_complete:
        # Reuse production whole-frame layout, without calling any media probes.
        from scripts.video_editor import normalize_transitions, plan_sequence_frames
        explicit = manifest.get("transitions", params.get("transitions"))
        if explicit is None:
            explicit = [{"type": clip.get("transition_in", "cut"),
                         "duration": clip.get("transition_duration", .4)} for clip in clips[1:]]
        explicit = _bounded_records(explicit, "transitions")
        boundaries = normalize_transitions(explicit)
        plan = plan_sequence_frames(durations, boundaries)
        covered = [[a / 30, b / 30] for a, b in zip(plan["start"], plan["end"])]
        for row, span in zip(report["clips"], covered):
            row["timeline_start"], row["timeline_end"] = span
        timeline_end = max((b for _, b in covered), default=0)
        report["planned_timeline_end"] = timeline_end
        # Output is quantized to frames. A subframe discrepancy in a saved audio
        # duration is not a demonstrated uncovered picture frame.
        horizon = math.floor(expected * 30 + .5) / 30 if expected is not None and expected >= 0 else timeline_end
        report["output_horizon"] = horizon
        covered = [[a, min(b, horizon)] for a, b in covered if a < horizon]
        report["timeline_gaps"] = _gaps(0, horizon, covered)
        summary["transition_handle_reuse_count"] = 0
        for reuse in report["reuses"]:
            index = reuse["clip_index"]
            if index == 0 or reuse["previous_clip_indices"] != [index - 1] or plan["overlap"][index] <= 0:
                continue
            outgoing, incoming = report["clips"][index - 1:index + 1]
            handle_s = plan["overlap"][index] / 30
            # Only the shared outgoing tail/incoming head can be a handle.
            # Replaying an older middle region under a fade remains a risk.
            is_handle = all(a >= outgoing["trim_end"] - handle_s * outgoing["speed"] - 1 / 30
                            and b <= incoming["trim_start"] + handle_s * incoming["speed"] + 1 / 30
                            for a, b in reuse["source_intervals"])
            if is_handle and reuse["classification"] == "unmarked_replay_risk":
                reuse["classification"] = "transition_handle_overlap"
                summary["replay_risk_count"] -= 1
                summary["transition_handle_reuse_count"] += 1
        for label, records, destination in (("cue", cues, "cue_coverage"), ("sentence", sentences, "sentence_coverage")):
            for index, record in enumerate(records):
                start = _number(record.get("start")) if isinstance(record, dict) else None
                end = _number(record.get("end")) if isinstance(record, dict) else None
                if start is None or end is None or start < 0 or end <= start:
                    report["issues"].append({"kind": f"invalid_{label}_timing", "index": index})
                    continue
                first_frame, stop_frame = math.floor(start * 30 + .5), math.floor(end * 30 + .5)
                gaps = _gaps(first_frame / 30, stop_frame / 30, covered)
                report[destination].append({"index": index, "id": record.get("id"),
                                            "start": start, "end": end, "frame_start": first_frame,
                                            "frame_end": stop_frame, "uncovered": gaps})
        if explicit and any("transition_in" not in clip for clip in clips[1:]):
            report["issues"].append({"kind": "legacy_transition_metadata", "detail": "top-level transitions used; incoming clip metadata is absent"})
    else:
        report["planned_timeline_end"] = None
        report["timeline_gaps"] = None
        report["unknowns"].append("timeline_and_timed_text_coverage")
    if not sentences:
        report["unknowns"].append("sentence_boundaries_not_explicit")
    if not cues:
        report["unknowns"].append("timed_cues_not_present")
    for label, records in (("cue", cues), ("sentence", sentences)):
        coverage = report[f"{label}_coverage"]
        summary[f"valid_timed_{label}_count"] = len(coverage)
        summary[f"uncovered_{label}_count"] = (sum(bool(item["uncovered"]) for item in coverage)
                                                 if records and len(coverage) == len(records) else None)
    for key in ("reused_source_seconds", "hold_seconds"):
        summary[key] = round(summary[key], 6)
    return report


def audit_file(path: Path, max_bytes: int = MAX_BYTES) -> dict[str, Any]:
    """Bounded metadata read with SHA-256 for reproducible audit identity."""
    if max_bytes <= 0 or path.stat().st_size > max_bytes:
        raise ValueError("manifest exceeds configured byte limit")
    with path.open("rb") as stream:
        content = stream.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError("manifest exceeds configured byte limit")
    report = audit_manifest(json.loads(content.decode("utf-8-sig")))
    report["manifest_path"] = str(path)
    report["manifest_bytes"] = len(content)
    report["manifest_sha256"] = hashlib.sha256(content).hexdigest()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit_file(args.manifest)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f"Metadata audit failed: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    raise SystemExit(main())
