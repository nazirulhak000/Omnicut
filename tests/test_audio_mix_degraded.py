"""
A full audio mix that fails must not fall back to voice-only in silence.

SFXManager.mix_audio_track still keeps the voice (so a render can finish), but
AudioMixStage now records mix_degraded in the stage result and the project
manifest, render_jobs hands it to the editor, and the next render mixes again
instead of reusing the file that has no music/SFX.

No real ffmpeg, no real 03_Projects: subprocess.run is faked and the manifest
lives in tmp_path.
"""

from types import SimpleNamespace

import pytest

from scripts import project_manifest, render_jobs
from scripts import sfx_manager as sfx_module
from scripts.pipeline_context import PipelineContext
from scripts.project_manifest import ProjectManifest
from scripts.sfx_manager import SFXManager
from scripts.stages.audio_mix_stage import AudioMixStage, MIX_DEGRADED_REASON


@pytest.fixture
def isolated_projects(tmp_path, monkeypatch):
    target = tmp_path / "03_Projects"
    target.mkdir()
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", target)
    return target


@pytest.fixture(autouse=True)
def _reset_mix_status():
    """last_mix_status is class-level state; leave it as it was found."""
    before = SFXManager.last_mix_status
    yield
    SFXManager.last_mix_status = before


@pytest.fixture
def quiet_assets(monkeypatch):
    """No SFX or BGM files are resolved, so only the voice input remains."""
    monkeypatch.setattr(SFXManager, "resolve", classmethod(lambda cls, name: None))
    monkeypatch.setattr(SFXManager, "resolve_bgm_path", classmethod(lambda cls, name=None: None))


def _fake_ffmpeg(monkeypatch, *, full_mix_ok=True, fallback_ok=True):
    calls = []

    def fake_run(command, **kwargs):
        is_full_mix = "-filter_complex" in command
        calls.append("full" if is_full_mix else "fallback")
        ok = full_mix_ok if is_full_mix else fallback_ok
        if ok:
            return SimpleNamespace(returncode=0, stderr="")
        return SimpleNamespace(
            returncode=1,
            stderr="ffmpeg banner\nError initializing filter 'amix' (simulated)\n",
        )

    monkeypatch.setattr(sfx_module.subprocess, "run", fake_run)
    return calls


def _ctx(tmp_path, project_name="mix_degraded_test", **overrides):
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"voice")
    project_dir = tmp_path / "03_Projects" / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    values = dict(
        product_name="Mix Degraded Test",
        raw_video_path="01_Raw/test/raw.mp4",
        project_name=project_name,
        project_dir=project_dir,
        export_mp4=True,
        total_duration=2.0,
        voice_audio_path=voice,
        micro_cues=[],
    )
    values.update(overrides)
    return PipelineContext(**values)


def test_failed_full_mix_is_flagged_not_silent(isolated_projects, quiet_assets, monkeypatch, tmp_path):
    calls = _fake_ffmpeg(monkeypatch, full_mix_ok=False, fallback_ok=True)
    ctx = _ctx(tmp_path)

    AudioMixStage.run(ctx)

    assert calls == ["full", "fallback"]  # the voice-only copy is still produced
    assert ctx.result_paths["mix_degraded"] is True
    assert ctx.result_paths["mix_degraded_reason"] == MIX_DEGRADED_REASON
    assert "amix" in ctx.result_paths["mix_degraded_detail"]  # the line that names the failure
    manifest = ProjectManifest.load("mix_degraded_test")
    assert manifest["mix_degraded"] is True
    assert manifest["mix_degraded_reason"] == MIX_DEGRADED_REASON


def test_healthy_mix_writes_no_flag_and_no_manifest(isolated_projects, quiet_assets, monkeypatch, tmp_path):
    _fake_ffmpeg(monkeypatch)
    ctx = _ctx(tmp_path)

    AudioMixStage.run(ctx)

    assert ctx.result_paths["mix_degraded"] is False
    assert "mix_degraded_reason" not in ctx.result_paths
    assert ProjectManifest.load("mix_degraded_test") is None  # nothing written for good-to-good


def test_voice_only_copy_failing_too_stops_the_render_with_the_reason(
    isolated_projects, quiet_assets, monkeypatch, tmp_path
):
    _fake_ffmpeg(monkeypatch, full_mix_ok=False, fallback_ok=False)

    with pytest.raises(RuntimeError, match="ทั้งแบบเต็มและแบบเสียงพากย์อย่างเดียว"):
        AudioMixStage.run(_ctx(tmp_path))


def test_a_degraded_mix_is_not_reused_and_a_good_remix_clears_the_flag(
    isolated_projects, quiet_assets, monkeypatch, tmp_path
):
    # The earlier render left a voice-only mix on disk and flagged it. This
    # render resumes from "subtitles", which would normally reuse the mix.
    stale = tmp_path / "03_Projects" / "mix_degraded_test" / "mixed_audio.wav"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_bytes(b"voice only")
    ProjectManifest.save(
        "mix_degraded_test",
        mix_degraded=True,
        mix_degraded_reason=MIX_DEGRADED_REASON,
        artifacts={"mixed_audio": {"path": str(stale)}},
    )
    calls = _fake_ffmpeg(monkeypatch)
    ctx = _ctx(
        tmp_path,
        resume_from="subtitles",
        manifest=ProjectManifest.load("mix_degraded_test"),
    )

    AudioMixStage.run(ctx)

    assert calls == ["full"], "a degraded mix must be mixed again, not reused"
    assert ctx.result_paths["mix_degraded"] is False
    saved = ProjectManifest.load("mix_degraded_test")
    assert saved["mix_degraded"] is False
    assert saved["mix_degraded_reason"] is None


def test_a_mocked_mixer_does_not_inherit_an_earlier_failure(isolated_projects, monkeypatch, tmp_path):
    SFXManager.last_mix_status = {"success": False, "fallback": True, "error": "left over from another test"}
    monkeypatch.setattr(SFXManager, "mix_audio_track", classmethod(lambda cls, **kwargs: None))
    ctx = _ctx(tmp_path)

    AudioMixStage.run(ctx)

    assert ctx.result_paths["mix_degraded"] is False


def test_mix_audio_track_resets_its_status_each_call(quiet_assets, monkeypatch, tmp_path):
    _fake_ffmpeg(monkeypatch, full_mix_ok=False)
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"voice")
    SFXManager.mix_audio_track(
        voice_audio_path=str(voice), cues=[], total_duration=1.0,
        output_audio_path=str(tmp_path / "a.wav"),
    )
    assert SFXManager.last_mix_status["fallback"] is True

    _fake_ffmpeg(monkeypatch)
    SFXManager.mix_audio_track(
        voice_audio_path=str(voice), cues=[], total_duration=1.0,
        output_audio_path=str(tmp_path / "b.wav"),
    )
    assert SFXManager.last_mix_status == {"success": True, "fallback": False, "error": None}


def test_job_result_carries_the_flag_to_the_editor():
    render_jobs.ACTIVE_JOBS.pop("mix-degraded-job", None)
    render_jobs.create_job("mix-degraded-job")
    render_jobs.complete_job(
        "mix-degraded-job",
        {"mix_degraded": True, "mix_degraded_reason": MIX_DEGRADED_REASON},
    )
    result = render_jobs.ACTIVE_JOBS["mix-degraded-job"]["result"]
    assert result["mix_degraded"] is True
    assert result["mix_degraded_reason"] == MIX_DEGRADED_REASON

    render_jobs.ACTIVE_JOBS.pop("mix-ok-job", None)
    render_jobs.create_job("mix-ok-job")
    render_jobs.complete_job("mix-ok-job", {})
    ok = render_jobs.ACTIVE_JOBS["mix-ok-job"]["result"]
    assert ok["mix_degraded"] is False
    assert ok["mix_degraded_reason"] is None
    render_jobs.ACTIVE_JOBS.pop("mix-degraded-job", None)
    render_jobs.ACTIVE_JOBS.pop("mix-ok-job", None)
