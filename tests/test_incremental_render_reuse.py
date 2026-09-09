"""Deterministic contracts for incremental render fingerprints and reuse."""

import pytest

from scripts import pipeline_context, project_manifest, render_jobs
from scripts.pipeline_context import (
    PipelineContext,
    build_incremental_render_metadata,
    stage_for_change,
)
from scripts.project_manifest import ProjectManifest


@pytest.fixture
def isolated_manifest(tmp_path, monkeypatch):
    projects_dir = tmp_path / "03_Projects"
    projects_dir.mkdir()
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", projects_dir)
    monkeypatch.setattr(project_manifest, "BASE_DIR", tmp_path)
    monkeypatch.setattr(pipeline_context, "BASE_DIR", tmp_path)
    return tmp_path, projects_dir


def _strict_project(isolated_manifest):
    base_dir, projects_dir = isolated_manifest
    project_name = "fingerprint-demo"
    project_dir = projects_dir / project_name
    project_dir.mkdir()

    raw_video = base_dir / "01_Raw" / "source.mp4"
    raw_video.parent.mkdir()
    raw_video.write_bytes(b"source-v1")

    voice = project_dir / "voiceover.wav"
    mixed = project_dir / "mixed_audio.wav"
    subtitles = project_dir / "subtitles.ass"
    mp4 = base_dir / "04_Exports" / "final.mp4"
    mp4.parent.mkdir()
    voice.write_bytes(b"voice-v1")
    mixed.write_bytes(b"mix-v1")
    subtitles.write_text("[Script Info]\n", encoding="utf-8")
    mp4.write_bytes(b"mp4-v1")

    cues = [{"start": 0.0, "end": 1.0, "text": "hello", "sfx": "boom"}]
    script_data = {
        "hook": "hello",
        "lines": [{"text": "hello", "sfx": "boom", "on_screen": ""}],
        "full_text": "hello",
    }
    clip_list = [{
        "id": "clip_0",
        "source_path": str(raw_video),
        "trim_start": 0.0,
        "trim_end": 1.0,
        "duration": 1.0,
        "speed": 1.0,
    }]
    render_params = {
        "product_name": "Product",
        "raw_video_path": str(raw_video),
        "key_features": "feature",
        "pain_point": "pain",
        "price_deal": "deal",
        "custom_script": "hello",
        "script_overlays": [""],
        "voice": "female",
        "voice_rate": "+15%",
        "voice_engine_type": "edge_tts",
        "voice_engine_used": "edge_tts",
        "voice_preset": "gemini_puck_male_hype",
        "ad_tone": "commercial_premium",
        "font_name": "IBMPlex",
        "bilingual_subtitles": True,
        "bgm_name": None,
        "bgm_volume": None,
        "bgm_ducking": True,
        "audio_mutes": {},
        "lut_name": None,
        "lut_intensity": 1.0,
        "caption_position": "bottom",
        "caption_color": None,
        "caption_scale": 1.0,
        "sticker_position": "top_right",
        "sticker_scale": 1.0,
        "sticker_start_time": None,
        "sticker_end_time": None,
        "sticker_norm_x": None,
        "sticker_norm_y": None,
        "clip_list": clip_list,
        "transitions": [],
        "overlays": [],
        "text_overlays": None,
        "stickers": None,
        "effects": None,
        "sticker_path": None,
        "human_voice_audio_path": None,
    }
    manifest = ProjectManifest.save(
        project_name,
        script_data=script_data,
        cues=cues,
        micro_cues=cues,
        total_duration=1.0,
        clip_list=clip_list,
        transitions=[],
        overlays=[],
        render_params=render_params,
        artifacts={
            "voice_audio": {"path": str(voice)},
            "mixed_audio": {"path": str(mixed)},
            "subtitles_ass": {"path": str(subtitles)},
            "mp4_video": {"path": str(mp4)},
        },
    )
    metadata = build_incremental_render_metadata(manifest)
    manifest = ProjectManifest.save(project_name, incremental_render=metadata)
    return project_name, project_dir, raw_video, manifest


def _context_for(project_name, project_dir, raw_video, manifest, **overrides):
    values = {
        "product_name": "Product",
        "raw_video_path": str(raw_video),
        "project_name": project_name,
        "key_features": "feature",
        "pain_point": "pain",
        "price_deal": "deal",
        "custom_script": "hello",
        "script_overlays": [""],
        "voice": "female",
        "voice_rate": "+15%",
        "voice_engine_type": "edge_tts",
        "voice_preset": "gemini_puck_male_hype",
        "ad_tone": "commercial_premium",
        "font_name": "IBMPlex",
        "bilingual_subtitles": True,
        "bgm_ducking": True,
        "caption_position": "bottom",
        "caption_scale": 1.0,
        "sticker_position": "top_right",
        "sticker_scale": 1.0,
        "lut_intensity": 1.0,
        "resume_from": "subtitles",
        "manifest": manifest,
        "project_dir": project_dir,
    }
    values.update(overrides)
    return PipelineContext(**values)


def test_successful_job_stamps_artifact_and_stage_fingerprints(isolated_manifest):
    project_name, _, _, manifest = _strict_project(isolated_manifest)
    render_jobs.ACTIVE_JOBS.pop("fingerprint-job", None)
    render_jobs.create_job("fingerprint-job")

    render_jobs.complete_job("fingerprint-job", {"project_name": project_name})

    updated = ProjectManifest.load(project_name)
    metadata = updated["incremental_render"]
    assert metadata["schema_version"] == 1
    assert set(metadata["stage_fingerprints"]) == {"script", "voice", "mix", "subtitles", "video"}
    assert set(metadata["artifact_fingerprints"]) == {
        "voice_audio", "mixed_audio", "subtitles_ass", "mp4_video"
    }
    assert metadata["artifact_fingerprints"]["voice_audio"]["valid"] is True
    assert render_jobs.ACTIVE_JOBS["fingerprint-job"]["incremental_render"]["schema_version"] == 1


def test_completed_job_metadata_drives_the_next_rerender(isolated_manifest):
    project_name, project_dir, raw_video, _ = _strict_project(isolated_manifest)
    render_jobs.ACTIVE_JOBS.pop("rerender-flow-job", None)
    render_jobs.create_job("rerender-flow-job")

    # First successful job writes the real artifact fingerprints that the
    # following partial rerender must consume.
    render_jobs.complete_job("rerender-flow-job", {"project_name": project_name})
    completed_manifest = ProjectManifest.load(project_name)
    rerender = _context_for(
        project_name,
        project_dir,
        raw_video,
        completed_manifest,
        resume_from="subtitles",
    )

    assert rerender.should_run("script") is False
    assert rerender.should_run("voice") is False
    assert rerender.should_run("mix") is False
    assert rerender.should_run("subtitles") is True
    assert rerender.reuse("voice_audio", "voice") == project_dir / "voiceover.wav"


def test_strict_reuse_matches_stage_and_artifact_contract(isolated_manifest):
    project_name, project_dir, raw_video, manifest = _strict_project(isolated_manifest)
    ctx = _context_for(project_name, project_dir, raw_video, manifest)

    assert ctx.should_run("script") is False
    assert ctx.should_run("voice") is False
    assert ctx.should_run("mix") is False
    assert ctx.should_run("subtitles") is True
    assert ctx.reuse("voice_audio", "voice") == project_dir / "voiceover.wav"


def test_changed_input_forces_earlier_stage_to_run(isolated_manifest):
    project_name, project_dir, raw_video, manifest = _strict_project(isolated_manifest)
    ctx = _context_for(
        project_name,
        project_dir,
        raw_video,
        manifest,
        voice_rate="+20%",
    )

    assert ctx.should_run("voice") is True
    with pytest.raises(FileNotFoundError, match="fingerprint mismatch"):
        ctx.reuse("voice_audio", "voice")


def test_mutated_artifact_cannot_be_reused(isolated_manifest):
    project_name, project_dir, raw_video, manifest = _strict_project(isolated_manifest)
    voice = project_dir / "voiceover.wav"
    voice.write_bytes(b"voice-tampered")
    ctx = _context_for(project_name, project_dir, raw_video, manifest)

    assert ctx.should_run("voice") is True
    with pytest.raises(FileNotFoundError, match="artifact fingerprint mismatch"):
        ctx.reuse("voice_audio", "voice")


def test_empty_legacy_artifact_is_rejected_even_without_metadata(isolated_manifest):
    base_dir, projects_dir = isolated_manifest
    project_name = "legacy-empty"
    project_dir = projects_dir / project_name
    project_dir.mkdir()
    empty_voice = project_dir / "voiceover.wav"
    empty_voice.touch()
    manifest = ProjectManifest.save(
        project_name,
        artifacts={"voice_audio": {"path": str(empty_voice)}},
    )
    ctx = _context_for(
        project_name,
        project_dir,
        base_dir / "source.mp4",
        manifest,
    )

    with pytest.raises(FileNotFoundError, match="missing, empty, or not a file"):
        ctx.reuse("voice_audio", "voice")


def test_empty_legacy_mix_forces_mix_stage_to_run(isolated_manifest):
    base_dir, projects_dir = isolated_manifest
    project_name = "legacy-empty-mix"
    project_dir = projects_dir / project_name
    project_dir.mkdir()
    empty_mix = project_dir / "mixed_audio.wav"
    empty_mix.touch()
    manifest = ProjectManifest.save(
        project_name,
        artifacts={"mixed_audio": {"path": str(empty_mix)}},
    )
    ctx = _context_for(
        project_name,
        project_dir,
        base_dir / "source.mp4",
        manifest,
    )

    assert ctx.should_run("mix") is True


@pytest.mark.parametrize(
    "change_class, expected_stage",
    [
        ("hook", "subtitles"),
        ("subtitles", "subtitles"),
        ("voice", "voice"),
        ("bgm", "mix"),
        ("script", "script"),
        ("video", "video"),
    ],
)
def test_change_class_uses_canonical_reroll_policy(change_class, expected_stage):
    assert stage_for_change(change_class) == expected_stage
    assert PipelineContext.stage_for_change(change_class) == expected_stage


def test_unknown_change_class_is_not_silently_mapped():
    with pytest.raises(ValueError, match="Unknown change class"):
        stage_for_change("unknown")
