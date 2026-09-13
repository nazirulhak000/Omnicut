"""Backend materialization tests for editable product callout overlays."""

from copy import deepcopy
from unittest.mock import patch

from scripts.pipeline_context import PipelineContext
from scripts.stages.subtitle_stage import (
    SubtitleStage,
    _materialize_product_callouts,
)
from scripts.subtitle_engine import SubtitleEngine


def _context(**kwargs):
    values = {
        "product_name": "Soundcore Q45",
        "raw_video_path": "unused.mp4",
    }
    values.update(kwargs)
    return PipelineContext(**values)


def _callouts(overlays):
    return [item for item in overlays if item.get("role") == "product_callout"]


def _text(item):
    tiers = item.get("tiers") or []
    return str((tiers[0] if tiers else {}).get("text") or item.get("text") or "")


def test_materializes_brand_model_and_feature_callouts_from_product_and_on_screen():
    ctx = _context(
        product_meta={
            "brand": "Anker",
            "model": "Soundcore Q45",
        },
        beat_cues=[
            {"id": "intro", "start": 0.0, "end": 1.2, "on_screen": ""},
            {"id": "feature", "start": 1.2, "end": 2.4, "on_screen": "Adaptive ANC"},
        ],
        cues=[
            {"start": 0.0, "end": 0.4, "on_screen": "wrong fallback"},
        ],
    )

    result = _materialize_product_callouts(ctx, [])
    callouts = _callouts(result)
    identities = {(item["callout_type"], _text(item)) for item in callouts}

    assert identities == {
        ("brand", "Anker"),
        ("model", "Soundcore Q45"),
        ("feature", "Adaptive ANC"),
    }
    by_text = {_text(item): item for item in callouts}
    assert (by_text["Anker"]["start"], by_text["Anker"]["end"]) == (0.0, 1.2)
    assert (by_text["Adaptive ANC"]["start"], by_text["Adaptive ANC"]["end"]) == (1.2, 2.4)


def test_manual_callout_wins_by_semantic_identity_and_does_not_mutate_input():
    manual = {
        "id": "manual-anc",
        "kind": "text",
        "role": "product_callout",
        "callout_type": "feature",
        "origin": "manual",
        "start": 0.7,
        "end": 1.7,
        "tiers": [{"text": "ANC", "look": {"color": "#00FFAA"}}],
    }
    generic = {"id": "existing-text", "kind": "text", "text": "ไม่ใช่ callout"}
    existing = [manual, generic]
    original = deepcopy(existing)
    ctx = _context(
        product_meta={"features": ["ANC", "Fast charge"]},
        beat_cues=[{"start": 0.0, "end": 2.0, "on_screen": "ANC"}],
        overlays=existing,
    )

    result = _materialize_product_callouts(ctx, existing)
    callouts = _callouts(result)
    anc = [item for item in callouts if _text(item) == "ANC"]
    fast_charge = [item for item in callouts if _text(item) == "Fast charge"]

    assert len(anc) == 1
    assert anc[0]["id"] == "manual-anc"
    assert (anc[0]["start"], anc[0]["end"]) == (0.7, 1.7)
    assert len(fast_charge) == 1
    assert any(item.get("id") == "existing-text" for item in result)
    assert existing == original
    assert result is not existing


def test_falls_back_to_clause_cues_only_when_beats_have_no_on_screen():
    ctx = _context(
        beat_cues=[{"id": "beat", "start": 4.0, "end": 5.0, "on_screen": ""}],
        cues=[{"start": 0.25, "end": 0.9, "on_screen": "20W fast charge"}],
    )

    result = _materialize_product_callouts(ctx, [])
    callouts = _callouts(result)

    by_text = {_text(item): item for item in callouts}
    assert by_text["20W fast charge"]["callout_type"] == "spec"
    assert (by_text["20W fast charge"]["start"], by_text["20W fast charge"]["end"]) == (0.25, 0.9)


def test_infers_brand_and_model_when_render_request_has_no_product_record():
    ctx = _context(
        product_name="Anker Soundcore Q45",
        beat_cues=[{"start": 0.0, "end": 1.0, "on_screen": "Adaptive ANC"}],
    )

    callouts = _callouts(_materialize_product_callouts(ctx, []))
    assert {(_text(item), item["callout_type"]) for item in callouts} == {
        ("Anker", "brand"),
        ("Soundcore Q45", "model"),
        ("Adaptive ANC", "feature"),
    }


def test_reuse_reads_manifest_cues_and_is_idempotent():
    manifest = {
        "beat_cues": [{"id": "manifest-beat", "start": 2.0, "end": 3.0, "on_screen": "IPX5"}],
        "cues": [{"start": 0.0, "end": 0.5, "on_screen": "wrong fallback"}],
        "product": {"brand": "JBL"},
    }
    ctx = _context(manifest=manifest, beat_cues=[], cues=[], overlays=None)

    first = _materialize_product_callouts(ctx, [])
    second = _materialize_product_callouts(ctx, first)

    assert first == second
    callouts = _callouts(first)
    assert len(callouts) == 3
    assert {(item["callout_type"], _text(item)) for item in callouts} == {
        ("model", "Q45"),
        ("brand", "JBL"),
        ("spec", "IPX5"),
    }
    assert all((item["start"], item["end"]) == (2.0, 3.0) for item in callouts)


def test_subtitle_stage_passes_materialized_callouts_to_renderer(tmp_path):
    ctx = _context(
        project_dir=tmp_path,
        total_duration=2.0,
        beat_cues=[{"start": 0.0, "end": 2.0, "on_screen": "20000mAh"}],
        cues=[{"start": 0.0, "end": 2.0, "text": "พาวเวอร์แบงก์"}],
        overlays=[],
    )

    with patch.object(SubtitleEngine, "generate_ass", return_value=(None, [])) as generate_ass:
        SubtitleStage.run(ctx)

    passed_overlays = generate_ass.call_args.kwargs["overlays"]
    callouts = _callouts(passed_overlays)
    assert {(_text(item), item["callout_type"]) for item in callouts} == {
        ("Soundcore", "brand"),
        ("Q45", "model"),
        ("20000mAh", "spec"),
    }
    assert ctx.effective_overlays == passed_overlays
