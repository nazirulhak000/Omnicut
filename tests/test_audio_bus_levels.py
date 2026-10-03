"""
Per-project voice/SFX levels from the editor's Track Mix (L4-05).

The project stores ``voice_volume`` / ``sfx_volume`` (style -> manifest top
level + render_params). AudioMixStage hands them to SFXManager.mix_audio_track,
the mix-stage fingerprint includes them so a change re-mixes instead of reusing
the old mixed_audio.wav, and the default levels change nothing at all: same
mix call, same fingerprint as a manifest that never had the fields.

No real ffmpeg, no real 03_Projects: subprocess.run is faked and every file
lives in tmp_path.
"""

from types import SimpleNamespace

import pytest

from scripts import project_manifest
from scripts import sfx_manager as sfx_module
from scripts.config import SFX_VOLUME, VOICE_VOLUME
from scripts.pipeline_context import (
    PipelineContext,
    _payload_fingerprint,
    _stage_payload_from_manifest,
    bus_volume_override,
)
from scripts.sfx_manager import SFXManager
from scripts.stages.audio_mix_stage import AudioMixStage


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    target = tmp_path / "03_Projects"
    target.mkdir()
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", target)
    before = SFXManager.last_mix_status
    yield
    SFXManager.last_mix_status = before


def _ctx(tmp_path, manifest=None, **overrides):
    voice = tmp_path / "voice.wav"
    if not voice.exists():  # rewriting it would change its fingerprint (mtime)
        voice.write_bytes(b"voice")
    project_dir = tmp_path / "03_Projects" / "bus_levels_test"
    project_dir.mkdir(parents=True, exist_ok=True)
    values = dict(
        product_name="Bus Levels Test",
        raw_video_path="01_Raw/test/raw.mp4",
        project_name="bus_levels_test",
        project_dir=project_dir,
        export_mp4=True,
        total_duration=2.0,
        voice_audio_path=voice,
        micro_cues=[],
        manifest=manifest,
    )
    values.update(overrides)
    return PipelineContext(**values)


def _capture_mix_kwargs(monkeypatch):
    seen = {}

    def fake_mix(**kwargs):
        seen.update(kwargs)
        return kwargs["output_audio_path"]

    import scripts.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod.SFXManager, "mix_audio_track", staticmethod(fake_mix))
    return seen


def _mix_fp(manifest):
    return _payload_fingerprint(_stage_payload_from_manifest(manifest, "mix", {}))


# ---------------------------------------------------------------- resolution

def test_defaults_and_missing_fields_mean_not_set():
    assert bus_volume_override({}, "voice_volume") is None
    assert bus_volume_override(None, "sfx_volume") is None
    assert bus_volume_override({"voice_volume": VOICE_VOLUME}, "voice_volume") is None
    assert bus_volume_override({"sfx_volume": SFX_VOLUME}, "sfx_volume") is None


def test_levels_are_clamped_to_the_policy_ceiling():
    assert bus_volume_override({"voice_volume": 0.6}, "voice_volume") == 0.6
    assert bus_volume_override({"render_params": {"sfx_volume": "0.5"}}, "sfx_volume") == 0.5
    # Above the [0, 1] ceiling clamps to 1.0 -- which for voice is the default.
    assert bus_volume_override({"voice_volume": 4}, "voice_volume") is None
    assert bus_volume_override({"sfx_volume": 4}, "sfx_volume") == 1.0
    assert bus_volume_override({"sfx_volume": -2}, "sfx_volume") == 0.0
    for bad in ("abc", float("nan"), float("inf"), True, [], {}):
        assert bus_volume_override({"sfx_volume": bad}, "sfx_volume") is None


# ----------------------------------------------------------------- the stage

def test_default_levels_leave_the_mix_call_unchanged(tmp_path, monkeypatch):
    for manifest in (None, {}, {"voice_volume": 1.0, "sfx_volume": 0.28}):
        seen = _capture_mix_kwargs(monkeypatch)
        AudioMixStage.run(_ctx(tmp_path, manifest=manifest))
        assert "voice_vol" not in seen, manifest
        assert "sfx_vol" not in seen, manifest


def test_set_levels_reach_the_mix_call_clamped(tmp_path, monkeypatch):
    seen = _capture_mix_kwargs(monkeypatch)
    manifest = {"voice_volume": 0.6, "render_params": {"voice_volume": 0.6, "sfx_volume": 3}}
    AudioMixStage.run(_ctx(tmp_path, manifest=manifest))
    assert seen["voice_vol"] == 0.6
    assert seen["sfx_vol"] == 1.0


def test_mute_still_wins_over_a_level(tmp_path, monkeypatch):
    seen = _capture_mix_kwargs(monkeypatch)
    manifest = {"voice_volume": 0.6, "sfx_volume": 0.5}
    AudioMixStage.run(_ctx(tmp_path, manifest=manifest, audio_mutes={"voice": True, "sfx": True}))
    assert seen["voice_vol"] == 0.0
    assert seen["sfx_vol"] == 0.0


def test_levels_land_in_the_ffmpeg_filter_graph(tmp_path, monkeypatch):
    boom = tmp_path / "sfx_vine_boom.wav"
    boom.write_bytes(b"boom")
    monkeypatch.setattr(SFXManager, "resolve", classmethod(lambda cls, name: boom if name == "boom" else None))
    monkeypatch.setattr(SFXManager, "resolve_bgm_path", classmethod(lambda cls, name=None: None))
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(sfx_module.subprocess, "run", fake_run)

    def graph(manifest):
        commands.clear()
        AudioMixStage.run(_ctx(tmp_path, manifest=manifest))
        full = [c for c in commands if "-filter_complex" in c]
        assert full, "the full mix never ran"
        return full[0][full[0].index("-filter_complex") + 1]

    default_graph = graph({})
    assert f"[0:a]volume={VOICE_VOLUME}," in default_graph
    assert f"volume={SFX_VOLUME}[sfx_boom]" in default_graph

    set_graph = graph({"voice_volume": 0.6, "sfx_volume": 0.5})
    assert "[0:a]volume=0.6," in set_graph
    assert "volume=0.5[sfx_boom]" in set_graph
    # The finishing loudness stage is untouched by the levels.
    assert "loudnorm=I=-14:TP=-1.0:LRA=8" in set_graph


# ----------------------------------------------------------- fingerprints

def test_old_manifest_and_default_levels_share_the_mix_fingerprint():
    old = {"bgm_name": None, "micro_cues": []}
    explicit = {**old, "voice_volume": 1.0, "sfx_volume": 0.28,
                "render_params": {"voice_volume": 1.0, "sfx_volume": 0.28}}
    assert _mix_fp(old) == _mix_fp(explicit)
    assert "voice_volume" not in _stage_payload_from_manifest(explicit, "mix", {})["inputs"]


def test_changing_a_level_changes_the_mix_fingerprint():
    base = {"bgm_name": None, "micro_cues": []}
    fp_default = _mix_fp(base)
    fp_voice = _mix_fp({**base, "voice_volume": 0.6})
    fp_voice2 = _mix_fp({**base, "voice_volume": 0.7})
    fp_sfx = _mix_fp({**base, "render_params": {"sfx_volume": 0.5}})
    assert len({fp_default, fp_voice, fp_voice2, fp_sfx}) == 4


def test_context_expected_fingerprint_follows_the_manifest_level(tmp_path):
    a = _ctx(tmp_path, manifest={"voice_volume": 1.0}).expected_stage_fingerprint("mix")
    b = _ctx(tmp_path, manifest={"voice_volume": 0.5}).expected_stage_fingerprint("mix")
    c = _ctx(tmp_path, manifest={}).expected_stage_fingerprint("mix")
    assert a == c
    assert a != b
