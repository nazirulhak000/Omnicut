"""Voice ripple cuts at MIX time (round EDITOR-CUT-QUALITY-R3, lane RB).

The voice file is never rewritten: `SFXManager.mix_audio_track(voice_cuts=...)`
drops the cut ranges (source seconds) from the voice with atrim+asetpts+afade+
concat. Real ffmpeg in tmp_path measures the OUTPUT: onset times, length and the
absence of clicks at the joins. Without cuts the command must be exactly what it
was before this feature (the golden below was captured from the pre-change code).

Offline and deterministic; everything lives under pytest's tmp_path.
"""

import re
import shutil
import tempfile
import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import ffmpeg_graph
from scripts import sfx_manager as sfx_module
from scripts.sfx_manager import SFXManager, build_voice_cut_graph
from scripts.voice_cut_map import keep_ranges
from tests.test_real_render_cut_alignment import SR, _decoded_audio, _onsets, _write_voice

FPS = 30
FRAME = 1.0 / FPS
ONSET_TOLERANCE = 0.005        # +-5 ms

REAL = pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg and FFprobe are required for the real mix measurements",
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mix_env(tmp_path, monkeypatch):
    """No SFX, no BGM, no loudness stage: the voice is the only thing in the mix."""
    missing = tmp_path / "missing.wav"
    monkeypatch.setattr(SFXManager, "resolve", classmethod(lambda cls, name: missing))
    monkeypatch.setattr(SFXManager, "resolve_bgm_path", classmethod(lambda cls, name=None: None))
    monkeypatch.setattr(sfx_module, "loudness_filter", lambda policy: "anull")
    previous = SFXManager.last_mix_status
    yield tmp_path
    SFXManager.last_mix_status = previous


def _mix(tmp_path, voice, cuts, *, total=10.0, name="mix.wav", source_duration="auto", **kwargs):
    """Run the real mix. `total` is large by default so `-t total+0.2` never truncates:
    the output is then exactly the (cut) voice plus apad's 1.0 s of silence."""
    out = tmp_path / name
    extra = dict(kwargs)
    if source_duration == "auto":
        with wave.open(str(voice), "rb") as source:
            source_duration = source.getnframes() / source.getframerate()
    if source_duration is not None:
        extra["voice_source_duration"] = source_duration
    SFXManager.mix_audio_track(
        voice_audio_path=str(voice), cues=[], total_duration=total,
        output_audio_path=str(out), voice_cuts=cuts, **extra,
    )
    assert SFXManager.last_mix_status["fallback"] is False, SFXManager.last_mix_status
    return out


def _cut(start, end, cid="c"):
    return {"id": cid, "start": start, "end": end}


def _assert_onsets(samples, expected):
    got = _onsets(samples)
    assert len(got) == len(expected), f"onsets {got} vs expected {expected}"
    for actual, wanted in zip(got, expected):
        assert abs(actual - wanted) <= ONSET_TOLERANCE, f"onsets {got} vs expected {expected}"


def _assert_length(samples, seconds):
    assert abs(len(samples) / SR - seconds) <= FRAME, f"length {len(samples) / SR:.4f}s vs {seconds}s"


def _write_tone(path, seconds=6.0, freq=1000.0, amp=0.5):
    t = np.arange(int(seconds * SR)) / SR
    x = (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def _write_bgm(path):
    t = np.arange(int(2.0 * 44100)) / 44100
    x = (0.5 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes((x * 32767).astype("<i2").tobytes())


# ---------------------------------------------------------------------------
# the cut graph itself (pure strings)
# ---------------------------------------------------------------------------

def test_graph_for_a_middle_cut_trims_ramps_and_concats():
    keep = keep_ranges([_cut(2.0, 2.5)], 6.0)
    graph = build_voice_cut_graph(keep, 6.0)
    assert graph == (
        "[0:a]asplit=2[vs0][vs1];"
        "[vs0]atrim=start=0.000000:end=2.000000,asetpts=PTS-STARTPTS,afade=t=out:st=1.992000:d=0.008[vk0];"
        "[vs1]atrim=start=2.500000,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.008[vk1];"
        "[vk0][vk1]concat=n=2:v=0:a=1[voice_cut];"
    )


def test_graph_never_fades_the_files_own_head_or_tail():
    head = build_voice_cut_graph(keep_ranges([_cut(0.0, 1.0)], 6.0), 6.0)
    assert head == "[0:a]atrim=start=1.000000,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.008[voice_cut];"
    tail = build_voice_cut_graph(keep_ranges([_cut(5.0, 6.0)], 6.0), 6.0)
    assert tail == (
        "[0:a]atrim=start=0.000000:end=5.000000,asetpts=PTS-STARTPTS,afade=t=out:st=4.992000:d=0.008[voice_cut];"
    )


def test_graph_for_three_ranges_uses_one_split_and_one_concat():
    keep = keep_ranges([_cut(2.0, 2.5, "a"), _cut(4.0, 4.2, "b")], 6.0)
    graph = build_voice_cut_graph(keep, 6.0)
    assert graph.startswith("[0:a]asplit=3[vs0][vs1][vs2];")
    assert graph.count("atrim=") == 3 and graph.count("concat=") == 1
    assert graph.endswith("[vk0][vk1][vk2]concat=n=3:v=0:a=1[voice_cut];")
    assert "aselect" not in graph and "acrossfade" not in graph       # both measured wrong (see plan 2.4)


def test_cut_graph_feeds_the_normal_voice_chain_with_and_without_ducking(mix_env, monkeypatch):
    seen = []
    monkeypatch.setattr(sfx_module.subprocess, "run",
                        lambda cmd, **kw: seen.append(list(cmd)) or SimpleNamespace(returncode=0, stderr=""))
    voice = mix_env / "voice.wav"
    voice.write_bytes(b"x")
    cuts = [_cut(2.0, 2.5)]
    for ducking in (False, True):
        SFXManager.mix_audio_track(str(voice), [], 5.5, str(mix_env / "o.wav"), bgm_ducking=ducking,
                                   voice_cuts=cuts, voice_source_duration=6.0)
        graph = seen[-1][seen[-1].index("-filter_complex") + 1]
        tail = ("apad=pad_dur=1.0,asplit=2[voice_padded][voice_key];" if ducking
                else "apad=pad_dur=1.0[voice_padded];")
        assert "[voice_cut]volume=1.0," + tail in graph
        assert graph.index("concat=n=2") < graph.index("[voice_cut]volume")
        assert "[0:a]volume" not in graph                              # the raw head is gone


# ---------------------------------------------------------------------------
# no cuts -> the command is exactly what it was (golden from the pre-change code)
# ---------------------------------------------------------------------------

# Fixed scenarios, identical to the ones captured before this feature existed.
_GOLDEN_CUES = [
    {"start": 0.0, "end": 1.2, "text": "สวัสดีครับ", "sfx": "whoosh"},
    {"start": 2.0, "end": 3.5, "text": "abc def ghi", "sfx": "pop"},
    {"start": 4.0, "end": 5.0, "text": "no sfx here"},
]
_GOLDEN_OVERLAYS = [{"start": 1.5, "end": 2.5, "text": "x", "sfx": "pop"}]
_GOLDEN_SCENARIOS = {
    "plain_bgm": dict(ducking=False, bgm=True),
    "ducking_bgm": dict(ducking=True, bgm=True),
    "ducking_no_bgm": dict(ducking=True, bgm=False),
    "plain_no_bgm_vol0.8": dict(ducking=False, bgm=False, voice_vol=0.8),
    "plain_bgm_fail_fallback": dict(ducking=False, bgm=True, fail=True),
    "ducking_bgm_fail_fallback": dict(ducking=True, bgm=True, fail=True),
}


def _capture(tmp_path, monkeypatch, label, **call_extra):
    spec = dict(_GOLDEN_SCENARIOS[label])
    ducking, bgm, fail = spec.pop("ducking"), spec.pop("bgm"), spec.pop("fail", False)
    for name in ("boom.wav", "whoosh.wav", "pop.wav", "bed.wav", "voice.wav"):
        (tmp_path / name).write_bytes(b"x")
    monkeypatch.setattr(SFXManager, "resolve", classmethod(lambda cls, name: tmp_path / f"{name}.wav"))
    monkeypatch.setattr(SFXManager, "resolve_bgm_path",
                        classmethod(lambda cls, name=None: (tmp_path / "bed.wav") if bgm else None))
    seen = []

    def fake_run(cmd, **kwargs):
        seen.append(list(cmd))
        return SimpleNamespace(returncode=1 if fail and len(seen) == 1 else 0, stderr="sim", stdout="")

    monkeypatch.setattr(sfx_module.subprocess, "run", fake_run)
    SFXManager.mix_audio_track(
        str(tmp_path / "voice.wav"), _GOLDEN_CUES, 6.0, str(tmp_path / "mix.wav"),
        bgm_ducking=ducking, overlays=_GOLDEN_OVERLAYS, **spec, **call_extra,
    )
    root = str(tmp_path)
    return [[str(part).replace(root, "<TMP>").replace("\\", "/") for part in cmd] for cmd in seen]


@pytest.fixture
def restore_status():
    previous = SFXManager.last_mix_status
    yield
    SFXManager.last_mix_status = previous


@pytest.mark.parametrize("label", list(_GOLDEN_SCENARIOS))
def test_no_cuts_command_is_byte_identical_to_the_pre_change_golden(tmp_path, monkeypatch, restore_status, label):
    assert _capture(tmp_path, monkeypatch, label) == GOLDEN_NO_CUT_COMMANDS[label]


@pytest.mark.parametrize("empty", [None, [], [{"id": "z", "start": 3.0, "end": 3.0}],
                                   [{"id": "z", "start": 9.0, "end": 12.0}]])
@pytest.mark.parametrize("label", ["plain_bgm", "ducking_bgm", "plain_bgm_fail_fallback"])
def test_empty_or_vanishing_cuts_keep_the_graph_identical_too(tmp_path, monkeypatch, restore_status, label, empty):
    got = _capture(tmp_path, monkeypatch, label, voice_cuts=empty, voice_source_duration=6.0)
    assert got == GOLDEN_NO_CUT_COMMANDS[label]


def test_unknown_source_duration_ignores_the_cuts_instead_of_guessing(tmp_path, monkeypatch, restore_status, caplog):
    monkeypatch.setattr(SFXManager, "_probe_voice_duration", staticmethod(lambda path: None))
    got = _capture(tmp_path, monkeypatch, "plain_bgm", voice_cuts=[_cut(2.0, 2.5)])
    assert got == GOLDEN_NO_CUT_COMMANDS["plain_bgm"]
    assert "duration is unknown" in caplog.text


# ---------------------------------------------------------------------------
# real ffmpeg: where do the sounds land after the cut?
# ---------------------------------------------------------------------------

@REAL
@pytest.mark.render_regression
@pytest.mark.parametrize("ducking", [False, True], ids=["plain", "ducking+bgm"])
def test_middle_cut_removes_the_range_and_shifts_later_onsets(mix_env, monkeypatch, ducking):
    voice = mix_env / "voice.wav"
    _write_voice(voice, [1.0, 3.0, 5.0], 6.0)
    extra = {}
    if ducking:
        bgm = mix_env / "bed.wav"
        _write_bgm(bgm)
        monkeypatch.setattr(SFXManager, "resolve_bgm_path", classmethod(lambda cls, name=None: bgm))
        extra = dict(bgm_ducking=True, bgm_vol=0.01)          # music peak ~0.005, far under the onset threshold

    cut_out = _decoded_audio(_mix(mix_env, voice, [_cut(2.0, 2.5)], **extra))
    _assert_onsets(cut_out, [1.0, 2.5, 4.5])
    _assert_length(cut_out, 6.5)                              # 6.0 - 0.5 cut + apad 1.0

    uncut = _decoded_audio(_mix(mix_env, voice, None, name="uncut.wav", **extra))
    _assert_onsets(uncut, [1.0, 3.0, 5.0])
    _assert_length(uncut, 7.0)


@REAL
@pytest.mark.render_regression
def test_two_cuts(mix_env):
    voice = mix_env / "voice.wav"
    _write_voice(voice, [1.0, 3.0, 5.0], 6.0)
    out = _decoded_audio(_mix(mix_env, voice, [_cut(2.0, 2.5, "a"), _cut(4.0, 4.2, "b")]))
    _assert_onsets(out, [1.0, 2.5, 4.3])
    _assert_length(out, 6.0 - 0.7 + 1.0)


@REAL
@pytest.mark.render_regression
def test_cut_snaps_off_grid_input_and_duplicates_to_the_frame_grid(mix_env):
    voice = mix_env / "voice.wav"
    _write_voice(voice, [1.0, 3.0, 5.0], 6.0)
    # off-grid, overlapping and unsorted: normalises to the single range [2.0, 2.5]
    cuts = [_cut(2.2, 2.51, "b"), _cut(2.01, 2.3, "a")]
    out = _decoded_audio(_mix(mix_env, voice, cuts))
    _assert_onsets(out, [1.0, 2.5, 4.5])
    _assert_length(out, 6.5)


@REAL
@pytest.mark.render_regression
@pytest.mark.parametrize("cuts, onsets, kept", [
    ([_cut(0.0, 0.5)], [0.5, 2.5, 4.5], 5.5),                  # head cut: one range, open-ended tail
    ([_cut(5.5, 6.0)], [1.0, 3.0, 5.0], 5.5),                  # tail cut: one range, trimmed end
    ([_cut(2.0, 2.5, "a"), _cut(5.5, 6.0, "b")], [1.0, 2.5, 4.5], 5.0),
], ids=["head", "tail", "middle+tail"])
def test_head_and_tail_cuts(mix_env, cuts, onsets, kept):
    voice = mix_env / "voice.wav"
    _write_voice(voice, [1.0, 3.0, 5.0], 6.0)
    out = _decoded_audio(_mix(mix_env, voice, cuts))
    _assert_onsets(out, onsets)
    _assert_length(out, kept + 1.0)


@REAL
@pytest.mark.render_regression
def test_a_burst_right_after_the_cut_keeps_its_onset_despite_the_8ms_ramp(mix_env):
    voice = mix_env / "voice.wav"
    _write_voice(voice, [1.0, 2.5, 4.0], 6.0)                  # the 2nd burst starts exactly where the cut ends
    out = _decoded_audio(_mix(mix_env, voice, [_cut(2.0, 2.5)]))
    _assert_onsets(out, [1.0, 2.0, 3.5])
    # reference level: the same burst in an UNCUT render (mono->stereo->mono scales it, so no absolute 0.5)
    uncut = _decoded_audio(_mix(mix_env, voice, None, name="uncut.wav"))
    peak = float(np.max(np.abs(uncut[int(2.6 * SR):int(2.8 * SR)])))
    assert peak > 0.3
    # the body of the burst is untouched ...
    assert float(np.max(np.abs(out[int(2.1 * SR):int(2.3 * SR)]))) == pytest.approx(peak, rel=0.02)
    # ... while the ramp is really there: 3 ms into it the level is still far under the peak
    assert float(np.max(np.abs(out[int(2.0 * SR):int(2.003 * SR)]))) < 0.6 * peak


@REAL
@pytest.mark.render_regression
def test_probes_the_voice_length_when_the_caller_does_not_pass_it(mix_env):
    voice = mix_env / "voice.wav"
    _write_voice(voice, [1.0, 3.0, 5.0], 6.0)
    out = _decoded_audio(_mix(mix_env, voice, [_cut(2.0, 2.5)], source_duration=None))
    _assert_onsets(out, [1.0, 2.5, 4.5])
    _assert_length(out, 6.5)


@REAL
@pytest.mark.render_regression
def test_with_the_real_loudness_stage_the_result_is_still_right(tmp_path, monkeypatch, restore_status):
    voice = tmp_path / "voice.wav"
    _write_voice(voice, [1.0, 3.0, 5.0], 6.0)
    monkeypatch.setattr(SFXManager, "resolve", classmethod(lambda cls, name: tmp_path / "missing.wav"))
    monkeypatch.setattr(SFXManager, "resolve_bgm_path", classmethod(lambda cls, name=None: None))
    out = _decoded_audio(_mix(tmp_path, voice, [_cut(2.0, 2.5)], total=5.5))   # the realistic call: post-cut total
    assert len(out) / SR == pytest.approx(5.7, abs=FRAME)                     # -t total + 0.2
    onsets = _onsets(out)
    assert len(onsets) == 3
    for actual, wanted in zip(onsets, [1.0, 2.5, 4.5]):
        assert abs(actual - wanted) <= ONSET_TOLERANCE


# --- clicks ---------------------------------------------------------------

def _max_step(samples):
    return float(np.max(np.abs(np.diff(samples))))


@REAL
@pytest.mark.render_regression
def test_joins_are_click_free_and_the_metric_does_catch_a_click(mix_env, monkeypatch):
    """A 1 kHz tone cut by 14 frames (466.67 cycles) joins 240 degrees out of phase: without
    ramps the sample-to-sample jump is ~0.43 against a natural max step of 0.065.

    Metric: the largest |x[n+1]-x[n]| of the decoded output, relative to the same metric on
    the UNCUT render of the same tone (so resampling ripple cancels out)."""
    voice = mix_env / "tone.wav"
    _write_tone(voice)
    cut_range = [_cut(2.0, 2.0 + 14 / FPS)]
    baseline = _max_step(_decoded_audio(_mix(mix_env, voice, None, name="base.wav")))
    assert 0.03 < baseline < 0.08          # a 1 kHz tone's natural step (~0.05 here), not 0.4

    with_ramps = _max_step(_decoded_audio(_mix(mix_env, voice, cut_range, name="ramps.wav")))
    assert with_ramps <= 1.2 * baseline, f"click at the join: {with_ramps:.4f} vs natural {baseline:.4f}"

    # control: the same graph with its ramps stripped -> the very same metric must light up
    with_fades = sfx_module.build_voice_cut_graph
    monkeypatch.setattr(
        sfx_module, "build_voice_cut_graph",
        lambda *args, **kwargs: re.sub(r",afade=t=(?:in|out):st=[0-9.]+:d=[0-9.]+", "", with_fades(*args, **kwargs)),
    )
    hard = _max_step(_decoded_audio(_mix(mix_env, voice, cut_range, name="hard.wav")))
    assert hard >= 3 * baseline, f"control did not click ({hard:.4f}) so the metric proves nothing"


# --- fallback and the graph-file path -------------------------------------

@REAL
@pytest.mark.render_regression
def test_voice_only_fallback_still_applies_the_cuts(mix_env, monkeypatch):
    voice = mix_env / "voice.wav"
    _write_voice(voice, [1.0, 3.0, 5.0], 6.0)
    real_run = sfx_module.subprocess.run
    commands = []

    def fail_the_full_mix(cmd, **kwargs):
        commands.append(list(cmd))
        if "-filter_complex" in cmd and "[aout]" in cmd[cmd.index("-filter_complex") + 1]:
            return SimpleNamespace(returncode=1, stderr="simulated advanced-mix failure", stdout="")
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(sfx_module.subprocess, "run", fail_the_full_mix)
    out = mix_env / "fallback.wav"
    SFXManager.mix_audio_track(str(voice), [], 10.0, str(out), voice_cuts=[_cut(2.0, 2.5)],
                               voice_source_duration=6.0)
    assert SFXManager.last_mix_status["fallback"] is True
    assert "fallback_error" not in SFXManager.last_mix_status
    fallback = commands[-1]
    assert "[voice_fb]" in fallback[fallback.index("-filter_complex") + 1]
    samples = _decoded_audio(out)
    _assert_onsets(samples, [1.0, 2.5, 4.5])
    _assert_length(samples, 6.5)


@REAL
@pytest.mark.render_regression
def test_cut_graph_travels_through_the_graph_file_when_forced(mix_env, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(mix_env))
    monkeypatch.setattr(ffmpeg_graph, "FILTER_GRAPH_SCRIPT_THRESHOLD", 0)
    voice = mix_env / "voice.wav"
    _write_voice(voice, [1.0, 3.0, 5.0], 6.0)
    out = _decoded_audio(_mix(mix_env, voice, [_cut(2.0, 2.5, "a"), _cut(4.0, 4.2, "b")]))
    _assert_onsets(out, [1.0, 2.5, 4.3])
    assert not list(mix_env.glob("omnicut_filtergraph_*"))             # temp graph file removed


# ---------------------------------------------------------------------------
# GOLDEN: commands captured from the pre-change scripts/sfx_manager.py
# ('<TMP>' stands for pytest's tmp_path, separators normalised to '/')
# ---------------------------------------------------------------------------

GOLDEN_NO_CUT_COMMANDS = {'plain_bgm': [['ffmpeg',
                '-y',
                '-i',
                '<TMP>/voice.wav',
                '-i',
                '<TMP>/boom.wav',
                '-i',
                '<TMP>/whoosh.wav',
                '-i',
                '<TMP>/pop.wav',
                '-i',
                '<TMP>/pop.wav',
                '-stream_loop',
                '-1',
                '-i',
                '<TMP>/bed.wav',
                '-filter_complex',
                '[0:a]volume=1.0,apad=pad_dur=1.0[voice_padded];[1:a]volume=0.28[sfx_boom];[2:a]volume=0.28,adelay=20|20[sfx_0];[3:a]volume=0.28,adelay=2000|2000[sfx_1];[4:a]volume=0.28,adelay=1500|1500[sfx_txt_0];[5:a]atempo=0.920,volume=0.12,atrim=0:6.5,afade=t=out:st=5.650:d=0.35[bgm_bed];[bgm_bed]anull[bgm];[voice_padded][sfx_boom][sfx_0][sfx_1][sfx_txt_0][bgm]amix=inputs=6:normalize=0:duration=first,loudnorm=I=-14:TP=-1.0:LRA=8[aout]',
                '-map',
                '[aout]',
                '-ac',
                '2',
                '-ar',
                '44100',
                '-t',
                '6.2',
                '<TMP>/mix.wav']],
 'ducking_bgm': [['ffmpeg',
                  '-y',
                  '-i',
                  '<TMP>/voice.wav',
                  '-i',
                  '<TMP>/boom.wav',
                  '-i',
                  '<TMP>/whoosh.wav',
                  '-i',
                  '<TMP>/pop.wav',
                  '-i',
                  '<TMP>/pop.wav',
                  '-stream_loop',
                  '-1',
                  '-i',
                  '<TMP>/bed.wav',
                  '-filter_complex',
                  '[0:a]volume=1.0,apad=pad_dur=1.0,asplit=2[voice_padded][voice_key];[1:a]volume=0.28[sfx_boom];[2:a]volume=0.28,adelay=20|20[sfx_0];[3:a]volume=0.28,adelay=2000|2000[sfx_1];[4:a]volume=0.28,adelay=1500|1500[sfx_txt_0];[5:a]atempo=0.920,volume=0.12,atrim=0:6.5,afade=t=out:st=5.650:d=0.35[bgm_bed];[bgm_bed]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[bgm_fmt];[voice_key]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[key_fmt];[bgm_fmt][key_fmt]sidechaincompress=threshold=0.02:ratio=12:attack=20:release=300:makeup=1[bgm];[voice_padded][sfx_boom][sfx_0][sfx_1][sfx_txt_0][bgm]amix=inputs=6:normalize=0:duration=first,loudnorm=I=-14:TP=-1.0:LRA=8[aout]',
                  '-map',
                  '[aout]',
                  '-ac',
                  '2',
                  '-ar',
                  '44100',
                  '-t',
                  '6.2',
                  '<TMP>/mix.wav']],
 'ducking_no_bgm': [['ffmpeg',
                     '-y',
                     '-i',
                     '<TMP>/voice.wav',
                     '-i',
                     '<TMP>/boom.wav',
                     '-i',
                     '<TMP>/whoosh.wav',
                     '-i',
                     '<TMP>/pop.wav',
                     '-i',
                     '<TMP>/pop.wav',
                     '-filter_complex',
                     '[0:a]volume=1.0,apad=pad_dur=1.0,asplit=2[voice_padded][voice_key];[1:a]volume=0.28[sfx_boom];[2:a]volume=0.28,adelay=20|20[sfx_0];[3:a]volume=0.28,adelay=2000|2000[sfx_1];[4:a]volume=0.28,adelay=1500|1500[sfx_txt_0];[voice_key]anullsink;[voice_padded][sfx_boom][sfx_0][sfx_1][sfx_txt_0]amix=inputs=5:normalize=0:duration=first,loudnorm=I=-14:TP=-1.0:LRA=8[aout]',
                     '-map',
                     '[aout]',
                     '-ac',
                     '2',
                     '-ar',
                     '44100',
                     '-t',
                     '6.2',
                     '<TMP>/mix.wav']],
 'plain_no_bgm_vol0.8': [['ffmpeg',
                          '-y',
                          '-i',
                          '<TMP>/voice.wav',
                          '-i',
                          '<TMP>/boom.wav',
                          '-i',
                          '<TMP>/whoosh.wav',
                          '-i',
                          '<TMP>/pop.wav',
                          '-i',
                          '<TMP>/pop.wav',
                          '-filter_complex',
                          '[0:a]volume=0.8,apad=pad_dur=1.0[voice_padded];[1:a]volume=0.28[sfx_boom];[2:a]volume=0.28,adelay=20|20[sfx_0];[3:a]volume=0.28,adelay=2000|2000[sfx_1];[4:a]volume=0.28,adelay=1500|1500[sfx_txt_0];[voice_padded][sfx_boom][sfx_0][sfx_1][sfx_txt_0]amix=inputs=5:normalize=0:duration=first,loudnorm=I=-14:TP=-1.0:LRA=8[aout]',
                          '-map',
                          '[aout]',
                          '-ac',
                          '2',
                          '-ar',
                          '44100',
                          '-t',
                          '6.2',
                          '<TMP>/mix.wav']],
 'plain_bgm_fail_fallback': [['ffmpeg',
                              '-y',
                              '-i',
                              '<TMP>/voice.wav',
                              '-i',
                              '<TMP>/boom.wav',
                              '-i',
                              '<TMP>/whoosh.wav',
                              '-i',
                              '<TMP>/pop.wav',
                              '-i',
                              '<TMP>/pop.wav',
                              '-stream_loop',
                              '-1',
                              '-i',
                              '<TMP>/bed.wav',
                              '-filter_complex',
                              '[0:a]volume=1.0,apad=pad_dur=1.0[voice_padded];[1:a]volume=0.28[sfx_boom];[2:a]volume=0.28,adelay=20|20[sfx_0];[3:a]volume=0.28,adelay=2000|2000[sfx_1];[4:a]volume=0.28,adelay=1500|1500[sfx_txt_0];[5:a]atempo=0.920,volume=0.12,atrim=0:6.5,afade=t=out:st=5.650:d=0.35[bgm_bed];[bgm_bed]anull[bgm];[voice_padded][sfx_boom][sfx_0][sfx_1][sfx_txt_0][bgm]amix=inputs=6:normalize=0:duration=first,loudnorm=I=-14:TP=-1.0:LRA=8[aout]',
                              '-map',
                              '[aout]',
                              '-ac',
                              '2',
                              '-ar',
                              '44100',
                              '-t',
                              '6.2',
                              '<TMP>/mix.wav'],
                             ['ffmpeg',
                              '-y',
                              '-i',
                              '<TMP>/voice.wav',
                              '-af',
                              'volume=1.0,apad=pad_dur=1.0',
                              '-ac',
                              '2',
                              '-ar',
                              '44100',
                              '-t',
                              '6.2',
                              '<TMP>/mix.wav']],
 'ducking_bgm_fail_fallback': [['ffmpeg',
                                '-y',
                                '-i',
                                '<TMP>/voice.wav',
                                '-i',
                                '<TMP>/boom.wav',
                                '-i',
                                '<TMP>/whoosh.wav',
                                '-i',
                                '<TMP>/pop.wav',
                                '-i',
                                '<TMP>/pop.wav',
                                '-stream_loop',
                                '-1',
                                '-i',
                                '<TMP>/bed.wav',
                                '-filter_complex',
                                '[0:a]volume=1.0,apad=pad_dur=1.0,asplit=2[voice_padded][voice_key];[1:a]volume=0.28[sfx_boom];[2:a]volume=0.28,adelay=20|20[sfx_0];[3:a]volume=0.28,adelay=2000|2000[sfx_1];[4:a]volume=0.28,adelay=1500|1500[sfx_txt_0];[5:a]atempo=0.920,volume=0.12,atrim=0:6.5,afade=t=out:st=5.650:d=0.35[bgm_bed];[bgm_bed]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[bgm_fmt];[voice_key]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[key_fmt];[bgm_fmt][key_fmt]sidechaincompress=threshold=0.02:ratio=12:attack=20:release=300:makeup=1[bgm];[voice_padded][sfx_boom][sfx_0][sfx_1][sfx_txt_0][bgm]amix=inputs=6:normalize=0:duration=first,loudnorm=I=-14:TP=-1.0:LRA=8[aout]',
                                '-map',
                                '[aout]',
                                '-ac',
                                '2',
                                '-ar',
                                '44100',
                                '-t',
                                '6.2',
                                '<TMP>/mix.wav'],
                               ['ffmpeg',
                                '-y',
                                '-i',
                                '<TMP>/voice.wav',
                                '-af',
                                'volume=1.0,apad=pad_dur=1.0',
                                '-ac',
                                '2',
                                '-ar',
                                '44100',
                                '-t',
                                '6.2',
                                '<TMP>/mix.wav']]}
