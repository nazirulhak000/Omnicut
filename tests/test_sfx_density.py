"""SFX density (roadmap Q4): min 2.0 s between hits, one opener, priority kept.

Offline and deterministic: the planner is pure; the mix test fakes ffmpeg and
SFX files in tmp_path.
"""

import re
from itertools import combinations
from types import SimpleNamespace

import scripts.sfx_manager as sfx_module
from scripts.sfx_manager import SFX_MIN_GAP_S, SFXManager, plan_sfx_events


def _cue(start, sfx, end=None):
    return {"start": start, "end": start + 1.0 if end is None else end, "text": "ข้อความ", "sfx": sfx}


def _assert_min_gap(plan):
    gated = [e for e in plan if not e["exempt"]]
    for a, b in combinations(gated, 2):
        assert abs(a["fire"] - b["fire"]) >= SFX_MIN_GAP_S - 1e-9, (a, b)


def test_fixture_timeline_has_no_pair_closer_than_two_seconds():
    cues = [_cue(t, "pop") for t in (0.8, 1.5, 2.2, 3.0, 4.1, 4.9, 6.5, 7.0, 9.4)]
    overlays = [{"start": 3.2, "end": 5.0, "sfx": "ding"}, {"start": 8.0, "end": 9.0, "sfx": "ding"}]
    plan = plan_sfx_events(cues, overlays, total_duration=12.0)
    _assert_min_gap(plan)
    assert plan, "density filter must not silence the whole clip"


def test_no_second_boom_when_hook_line_carries_opener():
    cues = [_cue(0.0, "sfx_vine_boom"), _cue(3.0, "pop")]
    plan = plan_sfx_events(cues, total_duration=6.0)
    assert not any(e["source"] == "boom" for e in plan)
    opener = [e for e in plan if e["role"] == "opener"]
    assert len(opener) == 1 and opener[0]["source"] == "cue" and opener[0]["index"] == 0


def test_boom_is_opener_when_hook_line_has_no_sfx_and_beats_nearby_line():
    cues = [_cue(0.0, None), _cue(1.0, "pop"), _cue(3.0, "pop")]
    plan = plan_sfx_events(cues, total_duration=6.0)
    sources = [(e["source"], e["index"]) for e in plan]
    assert ("boom", None) in sources
    assert ("cue", 1) not in sources  # 1.0 s after the boom -> dropped
    assert ("cue", 2) in sources


def test_closer_wins_over_earlier_line_within_gap():
    cues = [_cue(0.0, "boom"), _cue(4.0, "pop"), _cue(5.0, "pop"), _cue(5.5, "cash")]
    plan = plan_sfx_events(cues, total_duration=8.0)
    kept = {e["index"]: e["role"] for e in plan if e["source"] == "cue"}
    assert kept.get(3) == "closer"
    assert 2 not in kept  # 0.5 s before the closer
    assert 1 not in kept  # 1.5 s before the closer
    _assert_min_gap(plan)


def test_transition_whoosh_bound_to_cut_is_exempt():
    cues = [_cue(0.0, "boom"), _cue(3.0, "pop"), _cue(3.5, "sfx_whoosh_fast"), _cue(7.0, "cash")]
    unbound = plan_sfx_events(cues, total_duration=9.0)
    assert 2 not in {e["index"] for e in unbound if e["source"] == "cue"}

    bound = plan_sfx_events(cues, total_duration=9.0, cut_times=[3.5])
    kept = {e["index"]: e for e in bound if e["source"] == "cue"}
    assert kept[2]["exempt"] is True and 1 in kept

    flagged = [dict(c) for c in cues]
    flagged[2]["cut_bound"] = True
    assert 2 in {e["index"] for e in plan_sfx_events(flagged, total_duration=9.0) if e["source"] == "cue"}


def test_missing_file_never_takes_a_slot():
    cues = [_cue(0.0, None), _cue(2.5, "missing"), _cue(3.0, "pop")]
    plan = plan_sfx_events(
        cues, total_duration=6.0,
        sfx_filename=lambda tag: None if tag == "missing" else f"{tag}.wav",
    )
    assert {e["index"] for e in plan if e["source"] == "cue"} == {2}


def test_plan_is_deterministic_and_keeps_mix_order():
    cues = [_cue(t, "pop") for t in (0.0, 2.0, 4.0, 6.0)]
    overlays = [{"start": 5.0, "sfx": "ding"}]
    a = plan_sfx_events(cues, overlays, total_duration=8.0)
    b = plan_sfx_events(list(cues), list(overlays), total_duration=8.0)
    assert a == b
    order = [(e["source"], e["index"]) for e in a]
    assert order == sorted(order, key=lambda x: ({"boom": 0, "cue": 1, "overlay": 2}[x[0]], x[1] or -1))


def test_mix_graph_applies_density_plan(monkeypatch, tmp_path):
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"voice")
    files = {}
    for name in ("boom", "pop", "ding"):
        f = tmp_path / f"sfx_{name}.wav"
        f.write_bytes(b"x")
        files[name] = f
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(SFXManager, "resolve", classmethod(lambda cls, name: files.get(name)))
    monkeypatch.setattr(SFXManager, "resolve_bgm_path", classmethod(lambda cls, name=None: None))
    monkeypatch.setattr(sfx_module.subprocess, "run", fake_run)

    cues = [_cue(0.0, None), _cue(0.9, "pop"), _cue(2.4, "pop"), _cue(5.0, "pop")]
    overlays = [{"start": 5.6, "end": 7.0, "sfx": "ding"}]
    SFXManager.mix_audio_track(
        voice_audio_path=str(voice), cues=cues, total_duration=8.0,
        output_audio_path=str(tmp_path / "mix.wav"), overlays=overlays,
    )
    graph = captured["command"][captured["command"].index("-filter_complex") + 1]
    assert "[sfx_boom]" in graph
    assert "[sfx_1]" not in graph      # 0.9 s after the boom
    assert "[sfx_2]" in graph and "[sfx_3]" in graph
    assert "[sfx_txt_0]" not in graph  # 0.6 s after the closer
    delays = [int(d) / 1000 for d in re.findall(r"adelay=(\d+)\|", graph)]
    fires = sorted([0.0] + delays)
    assert all(b - a >= SFX_MIN_GAP_S - 1e-9 for a, b in zip(fires, fires[1:]))
    assert "amix=inputs=4:" in graph  # voice + boom + 2 cues
