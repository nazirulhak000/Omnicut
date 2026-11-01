"""Unit and Integration Tests for Native In-App Antigravity AI Agent."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.agent.agy_bridge import (
    CURRENT_CONVERSATION_ID,
    get_bridge_status,
    parse_action_proposals,
)
from scripts.agent.omnicut_agent_tools import (
    apply_action,
    apply_pro_color_grade,
    apply_viral_transitions,
    get_timeline_summary,
    load_project_manifest,
    propose_audio_mix,
    propose_split_clip,
    propose_subtitles_style,
    save_project_manifest,
)
from scripts.api_server import app


def test_agent_bridge_status():
    status = get_bridge_status()
    assert "status" in status
    assert status["current_conversation_id"] == CURRENT_CONVERSATION_ID
    assert "keys_count" in status
    assert status["engine_mode"] == "antigravity_hybrid"


def test_timeline_summary_and_inspection():
    summary = get_timeline_summary("HAT01-คำนวณคุ้มค่า_1")
    assert summary["project_name"] == "HAT01-คำนวณคุ้มค่า_1"
    assert summary["total_duration"] > 0
    assert "clip_count" in summary
    assert "audio_levels" in summary
    assert "style" in summary


def test_action_proposal_parsing():
    text = "ผมขอเสนอให้ [ACTION:split_clip split_time=5.5] และ [ACTION:audio_mix voice=1.0 sfx=0.25 bgm=0.10] ครับ"
    proposals = parse_action_proposals(text, "HAT01-คำนวณคุ้มค่า_1")
    assert len(proposals) >= 2

    types = [p["action_type"] for p in proposals]
    assert "split_clip" in types
    assert "audio_mix" in types


def test_propose_and_apply_actions_isolated(tmp_path, monkeypatch):
    # Setup temporary project isolated from real production files
    fake_proj_name = "TEST_ISOLATED_PROJ"
    fake_proj_dir = tmp_path / fake_proj_name
    fake_proj_dir.mkdir(parents=True)
    proj_json = fake_proj_dir / "project.json"

    initial_data = {
        "project_name": fake_proj_name,
        "total_duration": 10.0,
        "voice_volume": 1.0,
        "sfx_volume": 0.28,
        "bgm_volume": 0.12,
        "font_name": "Mali-Bold",
        "clip_list": [
            {"file_path": "clip1.mp4", "duration": 5.0, "target_start": 0.0, "target_end": 5.0},
            {"file_path": "clip2.mp4", "duration": 5.0, "target_start": 5.0, "target_end": 10.0},
        ],
    }
    with open(proj_json, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)

    # Monkeypatch PROJECTS_DIR to tmp_path
    monkeypatch.setattr("scripts.agent.omnicut_agent_tools.PROJECTS_DIR", tmp_path)

    # Test propose audio mix
    mix_prop = propose_audio_mix(fake_proj_name, voice_volume=0.95, sfx_volume=0.20, bgm_volume=0.08)
    res = apply_action(mix_prop)
    assert res["success"] is True

    # Verify manifest updated
    updated = load_project_manifest(fake_proj_name)
    assert updated["voice_volume"] == 0.95
    assert updated["sfx_volume"] == 0.20
    assert updated["bgm_volume"] == 0.08

    # Test propose split clip
    split_prop = propose_split_clip(fake_proj_name, split_time=2.5)
    split_res = apply_action(split_prop)
    assert split_res["success"] is True

    updated_after_split = load_project_manifest(fake_proj_name)
    assert len(updated_after_split["clip_list"]) == 3
    assert updated_after_split["clip_list"][0]["duration"] == 2.5
    assert updated_after_split["clip_list"][1]["duration"] == 2.5

    # Test propose subtitle style
    sub_prop = propose_subtitles_style(fake_proj_name, font_name="Prompt-Bold", caption_scale=1.2)
    sub_res = apply_action(sub_prop)
    assert sub_res["success"] is True
    updated_sub = load_project_manifest(fake_proj_name)
    assert updated_sub["font_name"] == "Prompt-Bold"
    assert updated_sub["caption_scale"] == 1.2


def test_api_agent_fastapi_endpoints():
    client = TestClient(app)

    # GET /api/agent/status
    res = client.get("/api/agent/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert data["engine_mode"] == "antigravity_hybrid"

    # GET /api/agent/timeline/HAT01-คำนวณคุ้มค่า_1
    res_tl = client.get("/api/agent/timeline/HAT01-คำนวณคุ้มค่า_1")
    assert res_tl.status_code == 200
    assert res_tl.json()["project_name"] == "HAT01-คำนวณคุ้มค่า_1"

    # POST /api/agent/stream with empty message -> 400
    res_bad = client.post("/api/agent/stream", json={"message": ""})
    assert res_bad.status_code == 400

def test_inapp_agent_pro_color_and_viral_transitions(tmp_path, monkeypatch):
    fake_proj_name = "TEST_INAPP_PRO_SUITE"
    fake_proj_dir = tmp_path / fake_proj_name
    fake_proj_dir.mkdir(parents=True)
    proj_json = fake_proj_dir / "project.json"

    initial_data = {
        "project_name": fake_proj_name,
        "total_duration": 12.0,
        "clip_list": [
            {"id": "c1", "file_path": "shot1.mp4", "duration": 4.0, "target_start": 0.0, "target_end": 4.0},
            {"id": "c2", "file_path": "shot2.mp4", "duration": 4.0, "target_start": 4.0, "target_end": 8.0},
            {"id": "c3", "file_path": "shot3.mp4", "duration": 4.0, "target_start": 8.0, "target_end": 12.0},
        ],
    }
    proj_json.write_text(json.dumps(initial_data, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr("scripts.agent.omnicut_agent_tools.PROJECTS_DIR", tmp_path)

    # 1. Test Pro Color Grade
    col_prop = apply_pro_color_grade(fake_proj_name, clip_index=0, shadows=0.35, highlights=-0.2, vibrance=0.45, vignette=0.3)
    res_col = apply_action(col_prop)
    assert res_col["success"] is True

    # 2. Test Viral Transitions
    trans_prop = apply_viral_transitions(fake_proj_name, transition_name="zoom_in_punch", duration=0.45)
    res_trans = apply_action(trans_prop)
    assert res_trans["success"] is True

    # Verify updated manifest
    updated = load_project_manifest(fake_proj_name)
    assert updated["clip_list"][0]["shadows"] == 0.35
    assert updated["clip_list"][0]["highlights"] == -0.2
    assert updated["clip_list"][0]["vibrance"] == 0.45
    assert updated["clip_list"][0]["vignette"] == 0.3
    # Check transitions on subsequent clips
    assert updated["clip_list"][1]["transition_in"] == "zoom_in_punch"
    assert updated["clip_list"][1]["transition_duration"] == 0.45
    assert updated["clip_list"][2]["transition_in"] == "zoom_in_punch"
    assert updated["clip_list"][2]["transition_duration"] == 0.45

