"""Audit S3-07 / X-04 / S3-08: a voice/script reroll re-plans an auto cut plan
but keeps a user-edited one; editor saves clamp clip speed to the render range."""

import pytest
from pydantic import ValidationError

from scripts import product_store, project_manifest, render_jobs
from scripts.api_phase1 import (
    UpdateClipsRequest,
    _carry_auto_generated_flags,
    _execute_reroll,
)
from scripts.project_manifest import ProjectManifest

AUTO = [
    {"id": "clip_0", "source_path": "raw.mp4", "trim_start": 0.0, "trim_end": 2.0, "duration": 2.0,
     "speed": 1.0, "zoom": 1.25, "auto_generated": True},
    {"id": "clip_1", "source_path": "raw.mp4", "trim_start": 5.0, "trim_end": 7.0, "duration": 2.0,
     "speed": 1.0, "zoom": 1.0, "auto_generated": True},
]


@pytest.fixture
def projects_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(product_store, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    monkeypatch.setattr(product_store, "BASE_DIR", tmp_path)
    target = tmp_path / "03_Projects"
    target.mkdir()
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", target)
    return target


def _reroll(monkeypatch, project_name, stage, clip_list):
    ProjectManifest.save(
        project_name, script_data={"lines": [{"text": "a"}]}, cues=[], micro_cues=[], total_duration=4.0,
        clip_list=clip_list,
        render_params={"raw_video_path": "raw.mp4", "clip_list": clip_list, "transitions": [{"type": "fade"}]},
    )
    seen = {}

    def fake_run(cls, **kwargs):
        seen.update(kwargs)
        return {"mp4_video": "", "project_name": project_name}

    import scripts.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod.TikTokAutoCutterPipeline, "run", classmethod(fake_run))
    job_id = f"job_{project_name}_{stage}"
    render_jobs.create_job(job_id)
    _execute_reroll(job_id, project_name, stage, {})
    return seen


@pytest.mark.parametrize("stage", ["voice", "script"])
def test_voice_or_script_reroll_drops_auto_plan(projects_dir, monkeypatch, stage):
    seen = _reroll(monkeypatch, f"auto_{stage}", stage, [dict(c) for c in AUTO])
    assert seen["resume_from"] == stage
    assert seen["clip_list"] is None
    assert seen["transitions"] is None


def test_voice_reroll_keeps_user_plan_and_warns(projects_dir, monkeypatch, capsys):
    user_plan = [dict(AUTO[0], auto_generated=None), dict(AUTO[1])]
    seen = _reroll(monkeypatch, "user_voice", "voice", user_plan)
    assert len(seen["clip_list"]) == 2
    assert "ใช้แผนตัดต่อที่คุณแก้ไว้เดิม" in capsys.readouterr().out


def test_video_reroll_keeps_auto_plan(projects_dir, monkeypatch):
    seen = _reroll(monkeypatch, "auto_video", "video", [dict(c) for c in AUTO])
    assert len(seen["clip_list"]) == 2


def test_editor_save_keeps_flag_only_for_unchanged_clips():
    stored = [dict(c) for c in AUTO]
    # Unchanged round trip (editor strips id, adds track_id/keyframes/mirror).
    incoming = [{k: v for k, v in c.items() if k not in ("id", "auto_generated")} | {"track_id": "video-1", "keyframes": [], "mirror": False}
                for c in AUTO]
    assert all(c.get("auto_generated") for c in _carry_auto_generated_flags(incoming, stored))
    # A real trim edit makes that clip user-authored.
    edited = [dict(c) for c in incoming]
    edited[1]["trim_end"] = 6.5
    result = _carry_auto_generated_flags(edited, stored)
    assert result[0].get("auto_generated") is True and "auto_generated" not in result[1]
    # A client cannot claim a clip is auto-generated on its own.
    forged = [dict(AUTO[0], trim_end=9.0)]
    assert "auto_generated" not in _carry_auto_generated_flags(forged, [dict(AUTO[0])])[0]


def test_update_clips_request_clamps_speed_to_render_range():
    req = UpdateClipsRequest(clip_list=[
        {"source_path": "a.mp4", "speed": 8}, {"source_path": "b.mp4", "speed": 0.1},
        {"source_path": "c.mp4", "speed": -2}, {"source_path": "d.mp4", "speed": 0},
        {"source_path": "e.mp4"},
    ])
    assert [c.get("speed") for c in req.clip_list] == [4.0, 0.25, 0.25, 1.0, None]
    with pytest.raises(ValidationError, match="ความเร็วของคลิปที่ 1"):
        UpdateClipsRequest(clip_list=[{"source_path": "a.mp4", "speed": "fast"}])
