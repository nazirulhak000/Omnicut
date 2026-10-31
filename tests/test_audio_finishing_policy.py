"""Focused, offline tests for the Phase 4 audio-finishing seam."""

from types import SimpleNamespace

import pytest

import scripts.sfx_manager as sfx_module
from scripts.config import BGM_VOLUME, SFX_VOLUME, VOICE_VOLUME
from scripts.sfx_manager import (
    DEFAULT_LOUDNESS_I,
    DEFAULT_LOUDNESS_LRA,
    DEFAULT_TRUE_PEAK,
    SFXManager,
    build_audio_finishing_policy,
    is_sfx_event_eligible,
    loudness_filter,
)


def test_policy_preserves_preview_mix_defaults_and_clamps_gains():
    policy = build_audio_finishing_policy(
        bgm_vol=4,
        voice_vol=-1,
        sfx_vol="not-a-number",
        bgm_ducking=True,
    )

    assert policy.voice_volume == 0.0
    assert policy.bgm_volume == 1.0
    assert policy.sfx_volume == SFX_VOLUME
    defaults = build_audio_finishing_policy()
    assert (defaults.bgm_volume, defaults.voice_volume) == (BGM_VOLUME, VOICE_VOLUME)
    assert policy.bgm_ducking is True


def test_invalid_loudness_overrides_fall_back_to_established_render_target():
    policy = build_audio_finishing_policy(
        loudness_i=-100,
        true_peak=float("nan"),
        loudness_lra=0,
    )

    assert (policy.loudness_i, policy.true_peak, policy.loudness_lra) == (
        DEFAULT_LOUDNESS_I,
        DEFAULT_TRUE_PEAK,
        DEFAULT_LOUDNESS_LRA,
    )
    assert loudness_filter(policy) == "loudnorm=I=-14:TP=-1.0:LRA=8"


def test_loudness_filter_rejects_a_manually_constructed_invalid_policy():
    policy = build_audio_finishing_policy()
    invalid = policy.__class__(
        voice_volume=policy.voice_volume,
        bgm_volume=policy.bgm_volume,
        sfx_volume=policy.sfx_volume,
        bgm_ducking=policy.bgm_ducking,
        loudness_i=-100,
        true_peak=policy.true_peak,
        loudness_lra=policy.loudness_lra,
    )

    with pytest.raises(ValueError, match="Invalid audio loudness policy"):
        loudness_filter(invalid)


@pytest.mark.parametrize(
    "event, duration, default_start, expected",
    [
        ({"sfx": "pop", "start": 0.5}, 2.0, None, True),
        ({"sfx": "pop", "start": "0.5"}, 2.0, None, True),
        ({"sfx": "pop", "start": 0.5, "sfx_enabled": False}, 2.0, None, False),
        ({"sfx": "pop", "start": -0.1}, 2.0, None, False),
        ({"sfx": "pop", "start": 2.1}, 2.0, None, False),
        ({"sfx": "pop", "start": 1.0, "end": 0.9}, 2.0, None, False),
        ({"sfx": "pop"}, 2.0, 0.0, True),
        ({"sfx": "pop"}, 2.0, None, False),
        ({"sfx": ""}, 2.0, 0.0, False),
        (None, 2.0, 0.0, False),
    ],
)
def test_sfx_event_eligibility_is_deterministic(
    event, duration, default_start, expected
):
    assert is_sfx_event_eligible(
        event,
        total_duration=duration,
        default_start=default_start,
    ) is expected


def test_mix_graph_skips_invalid_events_but_keeps_legacy_valid_events(
    monkeypatch, tmp_path
):
    voice = tmp_path / "voice.wav"
    sfx = tmp_path / "pop.wav"
    voice.write_bytes(b"voice")
    sfx.write_bytes(b"sfx")

    def resolve(cls, name):
        return sfx if name == "pop" else None

    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(SFXManager, "resolve", classmethod(resolve))
    monkeypatch.setattr(SFXManager, "resolve_bgm_path", classmethod(lambda cls, name=None: None))
    monkeypatch.setattr(sfx_module.subprocess, "run", fake_run)

    result = SFXManager.mix_audio_track(
        voice_audio_path=str(voice),
        # The valid cue sits 2.5 s after the legacy start-less overlay (0.0) so
        # the SFX density gap (SFX_MIN_GAP_S = 2.0) keeps both; 3.0 is still
        # past the end of the clip.
        cues=[
            {"sfx": "pop", "start": 2.5},
            {"sfx": "pop"},
            {"sfx": "pop", "start": 0.2, "sfx_enabled": False},
            {"sfx": "pop", "start": 3.0},
        ],
        total_duration=2.8,
        output_audio_path=str(tmp_path / "mix.wav"),
        sfx_vol=0.5,
        overlays=[{"sfx": "pop"}],
    )

    filter_arg = captured["command"][captured["command"].index("-filter_complex") + 1]
    assert result == str((tmp_path / "mix.wav").resolve())
    assert "[sfx_0]" in filter_arg
    assert "[sfx_1]" not in filter_arg
    assert "[sfx_2]" not in filter_arg
    assert "[sfx_3]" not in filter_arg
    assert "[sfx_txt_0]" in filter_arg
    assert "volume=0.5" in filter_arg
    assert "loudnorm=I=-14:TP=-1.0:LRA=8" in filter_arg


def test_ducking_graph_uses_the_policy_parameters_without_changing_mix_contract(
    monkeypatch, tmp_path
):
    voice = tmp_path / "voice.wav"
    bgm = tmp_path / "bgm.wav"
    voice.write_bytes(b"voice")
    bgm.write_bytes(b"bgm")
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(SFXManager, "resolve", classmethod(lambda cls, name: None))
    monkeypatch.setattr(
        SFXManager,
        "resolve_bgm_path",
        classmethod(lambda cls, name=None: bgm),
    )
    monkeypatch.setattr(sfx_module.subprocess, "run", fake_run)

    SFXManager.mix_audio_track(
        voice_audio_path=str(voice),
        cues=[],
        total_duration=2.0,
        output_audio_path=str(tmp_path / "mix.wav"),
        bgm_ducking=True,
    )

    filter_arg = captured["command"][captured["command"].index("-filter_complex") + 1]
    assert "asplit=2[voice_padded][voice_key]" in filter_arg
    assert "threshold=0.02:ratio=12:attack=20:release=300:makeup=1" in filter_arg
    assert "loudnorm=I=-14:TP=-1.0:LRA=8" in filter_arg


def test_mix_audio_track_fallback_records_status(monkeypatch, tmp_path):
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"voice")

    def failing_run(command, **kwargs):
        if "-filter_complex" in command:
            return SimpleNamespace(returncode=1, stderr="filter graph error simulated")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(SFXManager, "resolve", classmethod(lambda cls, name: None))
    monkeypatch.setattr(SFXManager, "resolve_bgm_path", classmethod(lambda cls, name=None: None))
    monkeypatch.setattr(sfx_module.subprocess, "run", failing_run)

    out = tmp_path / "mix.wav"
    result = SFXManager.mix_audio_track(
        voice_audio_path=str(voice),
        cues=[],
        total_duration=1.0,
        output_audio_path=str(out),
    )

    assert result == str(out.resolve())
    assert SFXManager.last_mix_status["success"] is False
    assert SFXManager.last_mix_status["fallback"] is True
    assert "filter graph error simulated" in SFXManager.last_mix_status["error"]
