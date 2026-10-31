"""Viral Lint (roadmap M4): pure rules, score, speed and the API endpoint."""

import copy
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts import viral_lint
from scripts.style_motion_policy import resolve_style_motion_policy
from scripts.viral_lint import Issue, lint_manifest, lint_report, score

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "viral_lint_manifests.json").read_text(encoding="utf-8"))


def _clean():
    return copy.deepcopy(FIXTURES["clean"])


def _codes(issues, severities=("warn", "block")):
    return {issue.code for issue in issues if issue.severity in severities}


# --------------------------------------------------------------------------- fixtures


def test_clean_fixture_has_no_warn_or_block():
    issues = lint_manifest(_clean())
    assert [i for i in issues if i.severity in ("warn", "block")] == []
    assert lint_report(_clean())["score"] == 100


def test_planted_fixture_detects_all_eight_problems():
    issues = lint_manifest(copy.deepcopy(FIXTURES["planted"]))
    assert _codes(issues) == set(FIXTURES["planted_codes"])
    assert len(FIXTURES["planted_codes"]) == 8
    by_code = {}
    for issue in issues:
        by_code.setdefault(issue.code, []).append(issue)
    assert {i.detail for i in by_code["HOOK_SLOW"]} == {"text", "voice"}
    assert [(i.start, i.end) for i in by_code["DEAD_AIR"]] == [(5.0, 6.0)]
    assert [(i.start, i.end, i.clip_index) for i in by_code["LONG_SHOT"]] == [(3.2, 7.2, 2)]
    assert [(i.start, i.end, i.clip_index) for i in by_code["HOOK_PACING"]] == [(0.0, 2.0, 0)]
    assert [(i.start, i.end, i.clip_index) for i in by_code["STATIC_SPAN"]] == [(7.2, 10.2, 3)]
    assert [(i.start, i.end) for i in by_code["SFX_DENSE"]] == [(5.08, 6.0)]
    assert [(i.start, i.end) for i in by_code["LENGTH"]] == [(12.0, 16.5)]
    # The price sits in the cue, its beat cue and the script line: reported once, blocking.
    assert [(i.severity, i.detail, i.start) for i in by_code["COMPLIANCE"]] == [("block", "NO_PRICE", 12.2)]


def test_report_shape_and_summary():
    report = lint_report(copy.deepcopy(FIXTURES["planted"]))
    assert set(report) == {"issues", "summary", "score"}
    assert report["summary"] == {"block": 1, "warn": 8, "info": 0}
    assert set(report["issues"][0]) == {"code", "severity", "start", "end", "message_th", "clip_index", "detail"}
    starts = [i["start"] for i in report["issues"] if i["start"] is not None]
    assert starts == sorted(starts)
    assert 0 <= report["score"] < 100


def test_lint_is_deterministic_and_does_not_mutate_input():
    manifest = copy.deepcopy(FIXTURES["planted"])
    before = json.dumps(manifest, sort_keys=True)
    assert lint_report(manifest) == lint_report(manifest)
    assert json.dumps(manifest, sort_keys=True) == before


def test_non_mapping_and_empty_manifests():
    assert lint_manifest(None) == []
    assert lint_manifest([]) == []
    assert lint_report({}) == {"issues": [], "summary": {"block": 0, "warn": 0, "info": 0}, "score": 100}


# --------------------------------------------------------------------------- individual rules


def test_hold_reason_is_info_and_exempt_from_shot_caps():
    manifest = _clean()
    manifest["clip_list"][3]["trim_end"] = 4.4  # 4.4 s, far over the 3.125 s cap
    manifest["clip_list"][3]["hold_reason"] = "source_window_exhausted"
    manifest["clip_list"][3]["keyframes"][-1]["time"] = 4.4
    manifest["target_duration"] = None
    issues = lint_manifest(manifest)
    holds = [i for i in issues if i.code == "HOLD"]
    assert [(h.severity, h.clip_index, h.detail) for h in holds] == [("info", 3, "source_window_exhausted")]
    assert "LONG_SHOT" not in _codes(issues)


def test_long_shot_cap_follows_style_policy():
    manifest = _clean()
    manifest["clip_list"][4]["trim_end"] = 3.0
    manifest["clip_list"][4]["keyframes"][-1]["time"] = 3.0
    assert "LONG_SHOT" not in _codes(lint_manifest(manifest))  # 3.0 <= 2.5 x 1.25
    manifest["style_preset"] = "viral_punch"                   # max_shot 2.2 -> cap 2.75
    assert "LONG_SHOT" in _codes(lint_manifest(manifest))
    # An explicit policy wins over style_preset: viral_punch (energetic family)
    # caps hook shots at 1.0 s, so the clean fixture's 1.2 s hook shots now warn.
    punch = resolve_style_motion_policy("viral_punch")
    assert punch.hook_max_shot == pytest.approx(1.0)
    explicit = lint_manifest(_clean(), policy=punch)
    assert [i.clip_index for i in explicit if i.code == "HOOK_PACING"] == [0, 1, 2]
    assert "HOOK_PACING" in _codes(lint_manifest(_clean(), policy=punch.__dict__))


def test_transition_and_keyframe_vocabularies_break_static_spans():
    manifest = _clean()
    manifest["clip_list"][4].pop("keyframes")  # 2.4 s static: under the 2.5 s limit
    assert "STATIC_SPAN" not in _codes(lint_manifest(manifest))
    manifest["clip_list"][4]["trim_end"] = 3.0
    assert "STATIC_SPAN" in _codes(lint_manifest(manifest))
    # property/value keyframes (the second vocabulary) move the camera too
    manifest["clip_list"][4]["keyframes"] = [
        {"time": 0.0, "property": "zoom", "value": 1.0},
        {"time": 1.5, "property": "zoom", "value": 1.1},
    ]
    assert "STATIC_SPAN" not in _codes(lint_manifest(manifest))
    # a transition overlap at either edge counts as motion
    manifest["clip_list"][4].pop("keyframes")
    manifest["transitions"][4] = {"type": "fade", "duration": 0.6}
    assert "STATIC_SPAN" not in _codes(lint_manifest(manifest))


def test_editor_clips_with_transition_in_are_laid_out_with_overlap():
    manifest = _clean()
    manifest.pop("transitions")
    manifest["clip_list"][1]["transition_in"] = "fade"
    manifest["clip_list"][1]["transition_duration"] = 0.4
    segments = viral_lint.layout_clips(manifest)
    assert segments[1]["start"] == pytest.approx(0.8)
    assert segments[1]["overlap"] == pytest.approx(0.4)


def test_dead_air_threshold():
    manifest = _clean()
    manifest["cues"][2]["start"] = 6.2  # 0.4 s gap: allowed
    assert "DEAD_AIR" not in _codes(lint_manifest(manifest))
    manifest["cues"][2]["start"] = 6.25
    assert "DEAD_AIR" in _codes(lint_manifest(manifest))


def test_word_timings_take_precedence_for_first_voice():
    manifest = _clean()
    manifest["word_timings"] = [{"start": 0.45, "end": 0.7, "word": "พาวเวอร์แบงก์"}]
    issues = [i for i in lint_manifest(manifest) if i.code == "HOOK_SLOW"]
    assert [i.detail for i in issues] == ["voice"]


def test_length_needs_target_and_reads_render_params():
    manifest = _clean()
    manifest.pop("target_duration")
    assert "LENGTH" not in _codes(lint_manifest(manifest))
    manifest["render_params"] = {"target_duration": 10}
    assert "LENGTH" in _codes(lint_manifest(manifest))


def test_structure_and_opener_warnings():
    manifest = _clean()
    manifest["script_data"]["lines"][0]["text"] = "หยุดดูก่อน พาวเวอร์แบงก์ตัวนี้ชาร์จได้สามรอบ"
    manifest["script_data"]["lines"][1]["text"] = "บอดี้บางเบาพกง่าย"
    manifest["script_data"]["lines"][3]["text"] = "บอดี้อะลูมิเนียมบางพกง่ายมาก"
    issues = lint_manifest(manifest)
    details = {(i.code, i.severity, i.detail) for i in issues}
    assert ("COMPLIANCE", "warn", "NO_FILLER_OPENER") in details
    assert ("STRUCTURE", "warn", "STRUCT_NO_OPEN_LOOP") in details
    assert ("STRUCTURE", "warn", "STRUCT_NO_COMMENT_QUESTION") in details
    assert not [i for i in issues if i.severity == "block"]


def test_overlay_text_compliance_blocks():
    manifest = _clean()
    manifest["overlays"].append({"id": "ovl_spec", "kind": "callout", "start": 4.0, "end": 6.0,
                                 "title": "ขายดีที่สุด", "value": "30000mAh"})
    blocks = [i for i in lint_manifest(manifest) if i.severity == "block"]
    assert [(i.detail, i.start, i.end) for i in blocks] == [("NO_EXAGGERATED_CLAIM", 4.0, 6.0)]


def test_score_formula_caps_each_code():
    def issues(code, severity, n):
        return [Issue(code, severity, float(k), float(k) + 1, "x") for k in range(n)]

    assert score([]) == 100
    assert score(issues("LONG_SHOT", "warn", 2)) == 88
    assert score(issues("LONG_SHOT", "warn", 10)) == 100 - 3 * 6
    assert score(issues("HOLD", "info", 5)) == 97
    assert score(issues("COMPLIANCE", "block", 4)) == 10
    assert score(issues("COMPLIANCE", "block", 3) + issues("LONG_SHOT", "warn", 3)) == 0


def test_typical_manifest_lints_under_50ms():
    base = copy.deepcopy(FIXTURES["planted"])
    clips, cues = [], []
    t = 0.0
    for k in range(24):  # ~45 s clip, 24 shots, 24 cues, overlays from the fixture
        clips.append(copy.deepcopy(base["clip_list"][k % len(base["clip_list"])]))
        cue = copy.deepcopy(base["cues"][k % len(base["cues"])])
        cue["start"], cue["end"] = round(t, 3), round(t + 1.7, 3)
        cues.append(cue)
        t += 1.9
    base.update(clip_list=clips, cues=cues, beat_cues=copy.deepcopy(cues),
                transitions=[{"type": "fade" if k % 5 == 0 else "cut", "duration": 0.3} for k in range(23)])
    base["script_data"]["lines"] = [{"text": c["text"]} for c in cues]
    lint_manifest(base)  # warm caches/imports
    best = min(_timed(lambda: lint_manifest(base)) for _ in range(15))
    assert best < 0.050, f"lint took {best * 1000:.1f} ms"


def _timed(fn):
    started = time.perf_counter()
    fn()
    return time.perf_counter() - started


# --------------------------------------------------------------------------- API


@pytest.fixture()
def client():
    from scripts.api_server import app

    return TestClient(app)


def test_api_lints_posted_manifest(client):
    response = client.post("/api/viral-lint", json={"manifest": FIXTURES["planted"]})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"] == {"block": 1, "warn": 8, "info": 0}
    assert {i["code"] for i in body["issues"]} == set(FIXTURES["planted_codes"])


def test_api_merges_editor_state_over_stored_project(client, monkeypatch):
    import scripts.api_viral_lint as api

    stored = copy.deepcopy(FIXTURES["planted"])
    seen = {}

    def fake_owner(scope, project_name, **_kwargs):
        seen["project"] = project_name
        return copy.deepcopy(stored)

    monkeypatch.setattr(api, "require_project_owner", fake_owner)
    clean = _clean()
    editor_state = {key: clean[key] for key in ("clip_list", "transitions", "cues", "overlays")}
    editor_state["beat_cues"] = clean["beat_cues"]
    response = client.post("/api/viral-lint", json={"project_name": " fixture ", "manifest": editor_state})
    assert response.status_code == 200, response.text
    assert seen["project"] == "fixture"
    codes = {i["code"] for i in response.json()["issues"]}
    # timeline problems are gone; the stored script still carries the price, target still 12 s
    assert "LONG_SHOT" not in codes and "DEAD_AIR" not in codes
    assert "COMPLIANCE" in codes and "LENGTH" in codes


def test_api_requires_project_or_manifest(client):
    assert client.post("/api/viral-lint", json={}).status_code == 422


def test_api_unknown_project_is_404(client):
    response = client.post("/api/viral-lint", json={"project_name": "no-such-project-viral-lint"})
    assert response.status_code == 404
