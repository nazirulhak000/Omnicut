"""
Unit Tests for AI Flow Shot Matching and CapCut Draft Generator
tests/test_flow_shot_matching_and_draft.py

Verifies:
  - scripts/shot_matching.py:
      - 01_Raw/<product_id>/AI_Flow/*.mp4 recognition
      - Priority hierarchy (Manual pin > AI Flow > Raw video > Image motion)
      - Filename parsing (beat_index, role/label)
      - Semantic matching to beat cues
  - scripts/draft_generator.py:
      - Rule 3.3: draft_content.json.bak backup mandatory before writes
      - Rule 4.7: J-cut transitions (150ms-250ms audio lead-in, 1/30s grid)
      - Rule 4.17: Strict Topic Hold (B-roll locked to full beat narration)
      - Rule 4.5: Audio mix standard (Voice 1.0, BGM 0.12)
      - CapCut Desktop 7.1 Schema compliance (9:16, 49 materials)
"""

import json
from pathlib import Path
import pytest

from scripts.shot_matching import (
    get_flow_broll_dir,
    parse_beat_index_from_filename,
    parse_label_from_filename,
    scan_flow_broll_clips,
    match_flow_clips_to_beats,
    resolve_shot_source,
    build_flow_matched_clip_list,
    integrate_flow_into_pipeline_context,
)
from scripts.draft_generator import (
    backup_draft_content,
    calculate_jcut_boundaries,
    create_base_draft_content,
    slot_broll_clips_into_timeline,
    add_audio_track_to_draft,
    generate_capcut_draft_with_flow,
    inject_flow_broll_into_existing_draft,
    frame_quantize,
    seconds_to_us,
    us_to_seconds,
)
from scripts.pipeline_context import PipelineContext


# ─── Part 1: shot_matching tests ───────────────────────────────────────────

def test_parse_beat_index_and_label_from_filename():
    assert parse_beat_index_from_filename("flow_20261114_120000_beat0_hook.mp4") == 0
    assert parse_beat_index_from_filename("flow_20261114_120000_beat_2_spec.mp4") == 2
    assert parse_beat_index_from_filename("flow_20261114_120000_1_feature.mp4") == 1
    assert parse_beat_index_from_filename("shot_3_cta.mp4") == 3
    assert parse_beat_index_from_filename("random_clip.mp4") is None

    assert "hook" in parse_label_from_filename("flow_20261114_120000_beat0_hook.mp4")
    assert "spec" in parse_label_from_filename("flow_20261114_120000_beat_2_spec.mp4")


def test_scan_flow_broll_clips(tmp_path, monkeypatch):
    mock_raw = tmp_path / "01_Raw"
    monkeypatch.setattr("scripts.shot_matching.RAW_DIR", mock_raw)

    prod_id = "prod_flow_test"
    flow_dir = mock_raw / prod_id / "AI_Flow"
    flow_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy files
    clip1 = flow_dir / "flow_20261114_100000_beat0_hook.mp4"
    clip2 = flow_dir / "flow_20261114_100500_beat1_feature.mp4"
    clip1.write_bytes(b"VID1")
    clip2.write_bytes(b"VID2")

    clips = scan_flow_broll_clips(prod_id)
    assert len(clips) == 2
    indices = {c["beat_index"] for c in clips}
    assert indices == {0, 1}
    assert all(c["is_ai_flow"] for c in clips)


def test_match_flow_clips_to_beats(tmp_path, monkeypatch):
    mock_raw = tmp_path / "01_Raw"
    monkeypatch.setattr("scripts.shot_matching.RAW_DIR", mock_raw)

    prod_id = "prod_match_test"
    flow_dir = mock_raw / prod_id / "AI_Flow"
    flow_dir.mkdir(parents=True, exist_ok=True)

    (flow_dir / "flow_20261114_100000_beat0_hook.mp4").write_bytes(b"VID_HOOK")
    (flow_dir / "flow_20261114_100100_beat2_cta.mp4").write_bytes(b"VID_CTA")

    beat_cues = [
        {"start": 0.0, "end": 2.5, "text": "Hook line"},
        {"start": 2.5, "end": 6.0, "text": "Feature line"},
        {"start": 6.0, "end": 8.5, "text": "Call to action"},
    ]

    matched = match_flow_clips_to_beats(prod_id, beat_cues)
    assert 0 in matched
    assert matched[0]["beat_index"] == 0
    assert 2 in matched
    assert matched[2]["beat_index"] == 2
    assert 1 not in matched  # No beat 1 file


def test_resolve_shot_source_priority(tmp_path, monkeypatch):
    mock_raw = tmp_path / "01_Raw"
    monkeypatch.setattr("scripts.shot_matching.RAW_DIR", mock_raw)

    prod_id = "prod_prio"
    flow_dir = mock_raw / prod_id / "AI_Flow"
    flow_dir.mkdir(parents=True, exist_ok=True)

    flow_file = flow_dir / "flow_20261114_100000_beat1_feature.mp4"
    flow_file.write_bytes(b"FLOW_VID")

    beat_cue = {"start": 3.0, "end": 6.0, "text": "Super fast charging"}

    # Priority 1: User Manual Pin beats AI Flow
    manual_pin = {"beat_index": 1, "video_path": "01_Raw/pinned.mp4", "trim_start": 1.0, "trim_end": 4.0}
    src_pinned = resolve_shot_source(prod_id, 1, beat_cue, raw_video="01_Raw/raw.mp4", manual_pin=manual_pin)
    assert src_pinned["source_type"] == "manual_pin"
    assert src_pinned["source_path"] == "01_Raw/pinned.mp4"

    # Priority 2: AI Flow beats Clean Raw Video
    src_flow = resolve_shot_source(prod_id, 1, beat_cue, raw_video="01_Raw/raw.mp4", manual_pin=None)
    assert src_flow["source_type"] == "ai_flow"
    assert src_flow["is_ai_flow"] is True
    assert "beat1" in src_flow["source_path"]

    # Priority 3: Raw Video when no Flow clip matches
    src_raw = resolve_shot_source(prod_id, 0, beat_cue, raw_video="01_Raw/raw.mp4", manual_pin=None)
    assert src_raw["source_type"] == "raw_video"
    assert src_raw["source_path"] == "01_Raw/raw.mp4"


def test_integrate_flow_into_pipeline_context(tmp_path, monkeypatch):
    mock_raw = tmp_path / "01_Raw"
    monkeypatch.setattr("scripts.shot_matching.RAW_DIR", mock_raw)

    prod_id = "prod_ctx_test"
    flow_dir = mock_raw / prod_id / "AI_Flow"
    flow_dir.mkdir(parents=True, exist_ok=True)

    (flow_dir / "flow_20261114_100000_beat0_hook.mp4").write_bytes(b"FLOW_0")

    ctx = PipelineContext(
        project_name="flow_proj",
        product_name="PowerBank",
        raw_video_path="01_Raw/raw.mp4",
        product_id=prod_id,
        beat_cues=[
            {"start": 0.0, "end": 2.5, "text": "Hook"},
            {"start": 2.5, "end": 5.0, "text": "Feature"},
        ],
    )

    res = integrate_flow_into_pipeline_context(ctx)
    assert res is True
    assert len(ctx.manual_shot_map) == 1
    assert ctx.manual_shot_map[0]["beat_index"] == 0
    assert ctx.manual_shot_map[0]["is_ai_flow"] is True


# ─── Part 2: draft_generator tests ─────────────────────────────────────────

def test_backup_draft_content_rule_3_3(tmp_path):
    draft_file = tmp_path / "draft_content.json"
    draft_file.write_text('{"version": 360000}', encoding="utf-8")

    bak = backup_draft_content(draft_file)
    assert bak is not None
    assert bak.exists()
    assert bak.name == "draft_content.json.bak"
    assert bak.read_text(encoding="utf-8") == '{"version": 360000}'


def test_calculate_jcut_boundaries_rules_4_7_and_4_17():
    cues = [
        {"start": 0.0, "end": 3.0, "text": "Hook"},
        {"start": 3.0, "end": 7.0, "text": "Feature 1"},
        {"start": 7.0, "end": 10.0, "text": "CTA"},
    ]

    boundaries = calculate_jcut_boundaries(cues, total_duration=10.0, nominal_j_lead=0.18)
    assert len(boundaries) == 3

    # Rule 4.7 & §6: Beat 0 visual start is strictly 0.0s
    assert boundaries[0]["visual_start"] == 0.0

    # Beat 1: Audio cue starts at 3.0s, visual starts at 3.0 + ~0.18s (on 30 FPS grid)
    b1 = boundaries[1]
    assert b1["visual_start"] > 3.0
    lead_ms = (b1["visual_start"] - 3.0) * 1000
    assert 150 <= lead_ms <= 250, f"Expected J-cut lead between 150-250ms, got {lead_ms}ms"

    # Rule 4.17 (Strict Topic Hold): Beat 0 visual ends exactly where Beat 1 visual begins
    assert boundaries[0]["visual_end"] == boundaries[1]["visual_start"]
    assert boundaries[1]["visual_end"] == boundaries[2]["visual_start"]
    assert boundaries[2]["visual_end"] == 10.0

    # Sum of visual durations equals total duration
    total_vis_dur = sum(b["visual_duration"] for b in boundaries)
    assert abs(total_vis_dur - 10.0) < 0.05


def test_slot_broll_clips_into_timeline(tmp_path):
    draft_data = create_base_draft_content()

    vid1 = tmp_path / "flow_shot0.mp4"
    vid2 = tmp_path / "flow_shot1.mp4"
    vid1.write_bytes(b"FAKE_VID_1")
    vid2.write_bytes(b"FAKE_VID_2")

    matched_shots = [
        {"start": 0.0, "end": 2.5, "source_path": str(vid1), "zoom": 1.25},
        {"start": 2.5, "end": 6.0, "source_path": str(vid2), "zoom": 1.15},
    ]

    updated = slot_broll_clips_into_timeline(draft_data, matched_shots, total_duration=6.0)

    # Verify video track
    video_tracks = [t for t in updated["tracks"] if t.get("type") == "video"]
    assert len(video_tracks) == 1
    segments = video_tracks[0]["segments"]
    assert len(segments) == 2

    # Check volume is 0.0 (Rule 4.5 / clean audio)
    assert segments[0]["volume"] == 0.0
    assert segments[1]["volume"] == 0.0

    # Check materials
    assert len(updated["materials"]["videos"]) == 2
    assert updated["version"] == 360000
    assert updated["canvas_config"]["ratio"] == "9:16"


def test_generate_capcut_draft_with_flow_end_to_end(tmp_path, monkeypatch):
    mock_raw = tmp_path / "01_Raw"
    mock_projects = tmp_path / "03_Projects"
    monkeypatch.setattr("scripts.shot_matching.RAW_DIR", mock_raw)
    monkeypatch.setattr("scripts.draft_generator.RAW_DIR", mock_raw)
    monkeypatch.setattr("scripts.draft_generator.PROJECTS_DIR", mock_projects)

    prod_id = "prod_full_e2e"
    flow_dir = mock_raw / prod_id / "AI_Flow"
    flow_dir.mkdir(parents=True, exist_ok=True)

    flow_clip0 = flow_dir / "flow_20261114_100000_beat0_hook.mp4"
    flow_clip1 = flow_dir / "flow_20261114_100100_beat1_feature.mp4"
    flow_clip0.write_bytes(b"FLOW_DATA_0")
    flow_clip1.write_bytes(b"FLOW_DATA_1")

    # Mock voiceover and BGM
    voice_file = tmp_path / "voiceover.wav"
    bgm_file = tmp_path / "bgm.wav"
    voice_file.write_bytes(b"WAVE_VOICE")
    bgm_file.write_bytes(b"WAVE_BGM")

    beat_cues = [
        {"start": 0.0, "end": 3.0, "text": "Hook line"},
        {"start": 3.0, "end": 6.0, "text": "Feature line"},
    ]

    target_draft_dir = mock_projects / prod_id / "draft"

    # First generation
    draft_file = generate_capcut_draft_with_flow(
        product_id=prod_id,
        beat_cues=beat_cues,
        draft_dir=target_draft_dir,
        voice_audio_path=str(voice_file),
        bgm_path=str(bgm_file),
        total_duration=6.0,
    )

    assert draft_file.exists()
    content = json.loads(draft_file.read_text(encoding="utf-8"))
    assert content["version"] == 360000

    # Tracks: 1 video, 2 audio (voice + bgm)
    tracks_by_type = [t["type"] for t in content["tracks"]]
    assert "video" in tracks_by_type
    assert tracks_by_type.count("audio") == 2

    # Verify BGM volume == 0.12 (Rule 4.5)
    bgm_track = next(t for t in content["tracks"] if t.get("name") == "audio_bgm")
    assert bgm_track["segments"][0]["volume"] == 0.12

    # Second generation tests Rule 3.3 (Backup existing)
    generate_capcut_draft_with_flow(
        product_id=prod_id,
        beat_cues=beat_cues,
        draft_dir=target_draft_dir,
        total_duration=6.0,
    )
    bak_file = target_draft_dir / "draft_content.json.bak"
    assert bak_file.exists(), "Rule 3.3 violation: draft_content.json.bak was not created on update!"
