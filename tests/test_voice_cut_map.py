"""scripts/voice_cut_map.py -- the source<->program time map of voice ripple cuts.

Pure unit tests (no ffmpeg, no files except the node rounding probe). The JS
twin (frontend/src/lib/voiceCutMap.js, lane RM) implements the same contract
and a later parity test compares both; the worked examples here are that contract.
"""

import doctest
import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import voice_cut_map
from scripts.voice_cut_map import (
    FPS,
    VoiceEditError,
    effective_duration,
    keep_ranges,
    normalize_cuts,
    program_to_source,
    resolve_voice_cuts,
    shift_time,
    snap_to_frame,
    source_matches,
    source_to_program,
    validate_voice_edit,
)

ROOT = Path(__file__).resolve().parents[1]
FRAME = 1.0 / FPS


def cut(start, end, cid="c", **extra):
    return {"id": cid, "start": start, "end": end, **extra}


# ---------------------------------------------------------------------------
# docstring examples ARE the contract lane RM mirrors
# ---------------------------------------------------------------------------

def test_every_docstring_example_runs():
    result = doctest.testmod(voice_cut_map)
    assert result.attempted >= 20
    assert result.failed == 0


# ---------------------------------------------------------------------------
# rounding
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value, expected", [
    (0.0, 0.0),
    (2.01, 2.0),
    (2.49, 2.5),
    (2.5, 2.5),
    (-0.01, 0.0),
    (1 / 60, 1 / 30),          # exact half frame rounds UP
    (31.2, 31.2),
    (None, 0.0),
    (float("nan"), 0.0),
    (float("inf"), 0.0),
    ("abc", 0.0),
])
def test_snap_to_frame_rounds_half_up_and_never_returns_negative_zero(value, expected):
    result = snap_to_frame(value)
    assert result == pytest.approx(expected, abs=1e-12)
    assert str(result) != "-0.0"


def test_snap_uses_floor_x30_plus_half_over_30():
    rng = random.Random(7)
    for _ in range(2000):
        x = rng.uniform(-3.0, 120.0)
        import math
        assert snap_to_frame(x) == math.floor(x * 30 + 0.5) / 30 + 0.0


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_rounding_equals_the_frontend_timeline_math(tmp_path):
    """snap_to_frame == JS snapToFrame == sequenceFrameIndex(x)/30, incl. exact ties."""
    rng = random.Random(20261004)
    values = [rng.uniform(-2.0, 120.0) for _ in range(1500)]
    values += [k / 60 for k in range(0, 500)]                # exact half-frame ties
    values += [k / 60 + 1e-9 for k in range(0, 200)]
    values += [k / 60 - 1e-9 for k in range(1, 200)]
    values += [0.0, 0.5, 2.0, 5.9667, 31.2, 59.99]
    script = tmp_path / "snap.mjs"
    script.write_text(
        "import { readFileSync } from 'node:fs';\n"
        "const lib = await import(new URL('file:///' + process.argv[2].replace(/\\\\/g, '/')).href);\n"
        "const vals = JSON.parse(readFileSync(process.argv[3], 'utf8'));\n"
        "console.log(JSON.stringify(vals.map(v => [lib.snapToFrame(v), lib.sequenceFrameIndex(v) / 30])));\n",
        encoding="utf-8",
    )
    data = tmp_path / "values.json"
    data.write_text(json.dumps(values), encoding="utf-8")
    proc = subprocess.run(
        ["node", str(script), str(ROOT / "frontend" / "src" / "lib" / "timelineMath.js"), str(data)],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    js = json.loads(proc.stdout)
    assert len(js) == len(values)
    for value, (snap_js, index_js) in zip(values, js):
        mine = snap_to_frame(value)
        assert mine == pytest.approx(index_js, abs=0), f"{value}: py {mine!r} vs sequenceFrameIndex {index_js!r}"
        assert mine == pytest.approx(snap_js, abs=0), f"{value}: py {mine!r} vs snapToFrame {snap_js!r}"


# ---------------------------------------------------------------------------
# normalize_cuts
# ---------------------------------------------------------------------------

def test_normalize_snaps_to_the_frame_grid():
    assert normalize_cuts([cut(2.01, 2.49, "a")], 6.0) == [cut(2.0, 2.5, "a")]


def test_normalize_drops_cuts_that_snap_to_zero_length():
    assert normalize_cuts([cut(1.0, 1.01)], 6.0) == []
    assert normalize_cuts([cut(1.0, 1.0)], 6.0) == []
    assert normalize_cuts([cut(2.0, 1.0)], 6.0) == []


def test_normalize_clamps_to_the_source_duration():
    assert normalize_cuts([cut(5.5, 9.0, "a")], 6.0) == [cut(5.5, 6.0, "a")]
    assert normalize_cuts([cut(-3.0, 0.5, "a")], 6.0) == [cut(0.0, 0.5, "a")]
    assert normalize_cuts([cut(7.0, 9.0)], 6.0) == []          # fully outside


def test_normalize_keeps_an_off_grid_file_end_for_a_tail_cut():
    # 5.99 s file: the tail cut ends at the file end, not at a frame boundary
    assert normalize_cuts([cut(5.5, 6.5, "a")], 5.99) == [cut(5.5, 5.99, "a")]


def test_normalize_merges_overlapping_and_touching_cuts_keeping_the_first_id():
    merged = normalize_cuts([
        cut(1.5, 3.0, "b"),
        cut(1.0, 2.0, "a"),
        cut(3.0, 3.5, "c"),          # touches b's end
        cut(5.0, 5.5, "d"),
    ], 6.0)
    assert merged == [cut(1.0, 3.5, "a"), cut(5.0, 5.5, "d")]


def test_normalize_merges_cuts_that_only_touch_after_snapping():
    merged = normalize_cuts([cut(2.0, 2.5, "a"), cut(2.51, 3.0, "b")], 6.0)
    assert merged == [cut(2.0, 3.0, "a")]


def test_normalize_sorts_by_start():
    result = normalize_cuts([cut(4.0, 4.5, "late"), cut(1.0, 1.5, "early")], 6.0)
    assert [item["id"] for item in result] == ["early", "late"]


def test_normalize_skips_unusable_items_and_bad_durations():
    assert normalize_cuts([None, "x", {"start": "a", "end": 1}, {"start": 1}, cut(1.0, 2.0, "ok")], 6.0) == [
        cut(1.0, 2.0, "ok")
    ]
    assert normalize_cuts(None, 6.0) == []
    for bad in (0, -1, None, float("nan"), "abc"):
        assert normalize_cuts([cut(1.0, 2.0)], bad) == []


def test_normalize_is_idempotent_pure_and_keeps_extra_keys():
    original = [cut(2.01, 2.49, "a", reason="silence", removed={"cues": 2})]
    snapshot = json.loads(json.dumps(original))
    once = normalize_cuts(original, 6.0)
    assert original == snapshot                                  # input untouched
    assert once == [cut(2.0, 2.5, "a", reason="silence", removed={"cues": 2})]
    assert normalize_cuts(once, 6.0) == once


# ---------------------------------------------------------------------------
# keep_ranges / effective_duration
# ---------------------------------------------------------------------------

def test_keep_ranges_worked_examples():
    assert keep_ranges([], 6.0) == [{"src_start": 0.0, "src_end": 6.0, "prog_start": 0.0}]
    assert keep_ranges([cut(2.0, 2.5)], 6.0) == [
        {"src_start": 0.0, "src_end": 2.0, "prog_start": 0.0},
        {"src_start": 2.5, "src_end": 6.0, "prog_start": 2.0},
    ]
    assert keep_ranges([cut(0.0, 1.0)], 6.0) == [{"src_start": 1.0, "src_end": 6.0, "prog_start": 0.0}]
    assert keep_ranges([cut(5.0, 6.0)], 6.0) == [{"src_start": 0.0, "src_end": 5.0, "prog_start": 0.0}]
    assert keep_ranges([cut(0.0, 6.0)], 6.0) == []
    assert keep_ranges([cut(0.0, 9.0)], 6.0) == []               # clamped to everything


def test_keep_ranges_two_cuts():
    ranges = keep_ranges([cut(2.0, 2.5, "a"), cut(4.0, 4.2, "b")], 6.0)
    assert [(r["src_start"], r["src_end"]) for r in ranges] == [(0.0, 2.0), (2.5, 4.0), (4.2, 6.0)]
    assert [r["prog_start"] for r in ranges] == pytest.approx([0.0, 2.0, 3.5])


def test_keep_ranges_bad_duration_gives_nothing():
    assert keep_ranges([cut(1.0, 2.0)], 0) == []
    assert keep_ranges([cut(1.0, 2.0)], None) == []


def test_keep_ranges_are_contiguous_on_the_program_timeline_and_sum_to_effective_duration():
    rng = random.Random(11)
    for _ in range(300):
        duration = rng.uniform(5.0, 60.0)
        raw = []
        for _i in range(rng.randint(0, 6)):
            a = rng.uniform(0, duration)
            raw.append(cut(a, a + rng.uniform(0.0, 4.0), f"c{_i}"))
        ranges = keep_ranges(raw, duration)
        total = sum(r["src_end"] - r["src_start"] for r in ranges)
        assert total == pytest.approx(effective_duration(raw, duration), abs=1e-9)
        for left, right in zip(ranges, ranges[1:]):
            assert right["prog_start"] == pytest.approx(left["prog_start"] + left["src_end"] - left["src_start"], abs=1e-12)
            assert right["src_start"] > left["src_end"]          # a real gap (the cut) between them


def test_effective_duration_worked_examples():
    assert effective_duration([], 6.0) == 6.0
    assert effective_duration([cut(2.0, 2.5)], 6.0) == 5.5
    assert effective_duration([cut(2.0, 2.5), cut(4.0, 4.2)], 6.0) == pytest.approx(5.3)
    assert effective_duration([cut(0.0, 9.0)], 6.0) == 0.0
    assert effective_duration([cut(1.0, 2.0)], 0) == 0.0
    assert effective_duration([cut(1.0, 2.0)], 31.2) == pytest.approx(30.2)      # file length stays off-grid


# ---------------------------------------------------------------------------
# source <-> program
# ---------------------------------------------------------------------------

ONE_CUT = [cut(2.0, 2.5)]
TWO_CUTS = [cut(2.0, 2.5, "a"), cut(4.0, 4.2, "b")]


@pytest.mark.parametrize("u, expected", [
    (0.0, 0.0), (1.0, 1.0), (2.0, 2.0),
    (2.25, 2.0),                # inside the cut: collapses onto the join
    (2.5, 2.0),
    (3.0, 2.5), (6.0, 5.5),
])
def test_source_to_program_one_cut(u, expected):
    assert source_to_program(u, ONE_CUT) == pytest.approx(expected)


@pytest.mark.parametrize("t, expected", [
    (0.0, 0.0), (1.0, 1.0),
    (2.0, 2.5),                 # exactly on the join -> AFTER the cut
    (2.5, 3.0), (5.5, 6.0),
])
def test_program_to_source_one_cut(t, expected):
    assert program_to_source(t, ONE_CUT) == pytest.approx(expected)


def test_two_cut_examples():
    assert source_to_program(5.0, TWO_CUTS) == pytest.approx(4.3)
    assert source_to_program(4.1, TWO_CUTS) == pytest.approx(3.5)
    assert program_to_source(3.5, TWO_CUTS) == pytest.approx(4.2)
    assert program_to_source(2.0, TWO_CUTS) == pytest.approx(2.5)
    assert program_to_source(1.9, TWO_CUTS) == pytest.approx(1.9)


def test_no_cuts_is_the_identity():
    for value in (0.0, 1.234, 59.9):
        assert source_to_program(value, []) == value
        assert source_to_program(value, None) == value
        assert program_to_source(value, []) == value


def test_non_finite_input_maps_to_zero():
    assert source_to_program(None, ONE_CUT) == 0.0
    assert program_to_source(float("nan"), ONE_CUT) == 0.0


def test_program_round_trip_is_exact_and_source_round_trip_lands_after_the_cut():
    rng = random.Random(5)
    for _ in range(300):
        duration = rng.uniform(10.0, 60.0)
        cuts = normalize_cuts(
            [cut(a, a + rng.uniform(0.1, 3.0), f"c{i}") for i, a in enumerate(sorted(rng.uniform(0, duration) for _ in range(rng.randint(0, 5))))],
            duration,
        )
        total = effective_duration(cuts, duration)
        for _i in range(20):
            t = rng.uniform(0.0, total)
            u = program_to_source(t, cuts)
            assert source_to_program(u, cuts) == pytest.approx(t, abs=1e-9)
            # u is never inside a cut (it is on the kept side)
            assert not any(c["start"] + 1e-9 < u < c["end"] - 1e-9 for c in cuts)


def test_source_to_program_is_monotonic_and_collapses_each_cut():
    cuts = normalize_cuts(TWO_CUTS, 6.0)
    previous = -1.0
    for step in range(0, 601):
        u = step / 100
        t = source_to_program(u, cuts)
        assert t >= previous - 1e-12
        previous = t
    # a point anywhere inside a cut maps to its join, whatever the position inside
    join = source_to_program(2.0, cuts)
    assert all(source_to_program(u, cuts) == pytest.approx(join) for u in (2.0, 2.1, 2.25, 2.49, 2.5))


def test_total_program_length_matches_the_last_keep_range():
    cuts = normalize_cuts(TWO_CUTS, 6.0)
    ranges = keep_ranges(cuts, 6.0)
    last = ranges[-1]
    assert last["prog_start"] + last["src_end"] - last["src_start"] == pytest.approx(effective_duration(cuts, 6.0))
    assert source_to_program(6.0, cuts) == pytest.approx(effective_duration(cuts, 6.0))


# ---------------------------------------------------------------------------
# shift_time
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("t, expected", [
    (0.0, 0.0), (1.0, 1.0), (2.0, 2.0),
    (2.25, 2.0), (2.5, 2.0),
    (3.0, 2.5), (10.0, 9.5),
])
def test_shift_time_worked_examples(t, expected):
    assert shift_time(t, 2.0, 2.5) == pytest.approx(expected)


def test_shift_time_is_continuous_and_monotonic_across_the_range():
    values = [shift_time(step / 100, 2.0, 2.5) for step in range(0, 801)]
    assert all(b >= a - 1e-12 for a, b in zip(values, values[1:]))
    assert max(abs(b - a) for a, b in zip(values, values[1:])) <= 0.01 + 1e-9


def test_shift_time_degenerate_arguments():
    assert shift_time(None, 2.0, 2.5) == 0.0
    assert shift_time(3.0, None, 2.5) == 3.0


# ---------------------------------------------------------------------------
# validate_voice_edit (strict, backend only)
# ---------------------------------------------------------------------------

def edit(cuts, duration=31.2, **source):
    return {
        "schema_version": 1,
        "source": {"path": "03_Projects/x/voiceover.wav", "size": 10, "mtime_ns": 20, "duration": duration, **source},
        "cuts": cuts,
    }


def test_validate_accepts_and_normalizes_a_good_edit():
    out = validate_voice_edit(edit([cut(4.01, 4.59, "a", reason="silence"), cut(10.0, 10.5, "b")]))
    assert out["schema_version"] == 1
    assert out["source"] == {"path": "03_Projects/x/voiceover.wav", "size": 10, "mtime_ns": 20, "duration": 31.2}
    assert out["cuts"] == [cut(4.0, 4.6, "a", reason="silence"), cut(10.0, 10.5, "b", reason="manual")]


def test_validate_empty_or_none_clears():
    assert validate_voice_edit(None) is None
    assert validate_voice_edit(edit([])) is None
    assert validate_voice_edit({"source": {"duration": 5}, "cuts": None}) is None


def test_validate_stamps_only_what_the_client_left_out():
    stamp = {"path": "03_Projects/x/voiceover.wav", "size": 99, "mtime_ns": 77}
    raw = {"source": {"duration": 31.2}, "cuts": [cut(1.0, 2.0)]}
    assert validate_voice_edit(raw, stamp=stamp)["source"] == {**stamp, "duration": 31.2}

    # same path, size omitted -> filled from the current file
    partial = {"source": {"path": "03_Projects/x/voiceover.wav", "duration": 31.2}, "cuts": [cut(1.0, 2.0)]}
    assert validate_voice_edit(partial, stamp=stamp)["source"]["size"] == 99

    # a DIFFERENT file keeps its own fingerprint (and is judged stale later), never mixed
    other = {"source": {"path": "03_Projects/x/voiceover_v2.wav", "size": 5, "duration": 31.2}, "cuts": [cut(1.0, 2.0)]}
    out = validate_voice_edit(other, stamp=stamp)["source"]
    assert (out["path"], out["size"], out["mtime_ns"]) == ("03_Projects/x/voiceover_v2.wav", 5, None)


@pytest.mark.parametrize("raw, fragment", [
    ("nope", "อ็อบเจกต์"),
    ({"schema_version": 2, "source": {"duration": 9}, "cuts": [cut(1, 2)]}, "schema_version"),
    ({"source": {"duration": 9}, "cuts": "x"}, "cuts ต้องเป็นรายการ"),
    ({"cuts": [cut(1, 2)]}, "source"),
    ({"source": {"duration": 0}, "cuts": [cut(1, 2)]}, "duration"),
    ({"source": {"duration": "x"}, "cuts": [cut(1, 2)]}, "duration"),
    (edit([{"start": 1, "end": 2}]), "id"),
    (edit([cut(1, 2, "")]), "id"),
    (edit([cut(1, 2, "a"), cut(3, 4, "a")]), "ซ้ำ"),
    (edit([cut("x", 2, "a")]), "ตัวเลข"),
    (edit([cut(3, 2, "a")]), "end ต้องมากกว่า start"),
    (edit([cut(-1, 2, "a")]), "อยู่ในความยาว"),
    (edit([cut(1, 40, "a")]), "อยู่ในความยาว"),
    (edit([cut(1.0, 1.01, "a")]), "สั้นกว่า 1 เฟรม"),
    (edit([cut(4, 5, "a"), cut(1, 2, "b")]), "เรียงตามเวลา"),
    (edit([cut(1, 3, "a"), cut(2, 4, "b")]), "ซ้อนกับ"),
    (edit([cut(1, 2, "a", reason="x" * 100)]), "reason"),
    (edit([cut(1, 2, "a")], size="big"), "จำนวนเต็ม"),
    (edit([cut(1, 2, "a")], path=5), "path"),
    (edit([cut(0.0, 6.5, "a")], duration=7.0), "ขั้นต่ำ"),             # leaves 0.5 s < 1 s
    (edit([cut(0.0, 31.2, "a")]), "ขั้นต่ำ"),                          # everything cut
])
def test_validate_rejects_bad_edits_with_a_thai_reason(raw, fragment):
    with pytest.raises(VoiceEditError) as info:
        validate_voice_edit(raw)
    assert fragment in str(info.value)


def test_validate_rejects_too_many_cuts():
    many = [cut(i * 0.5, i * 0.5 + 0.2, f"c{i}") for i in range(1001)]
    with pytest.raises(VoiceEditError, match="มากเกินไป"):
        validate_voice_edit(edit(many, duration=900.0))


def test_validate_allows_a_tail_cut_shorter_than_a_frame_only_when_it_reaches_the_file_end():
    with pytest.raises(VoiceEditError, match="สั้นกว่า 1 เฟรม"):
        validate_voice_edit(edit([cut(5.97, 5.99, "a")], duration=6.99))      # 20 ms in the middle
    tail = validate_voice_edit(edit([cut(7.97, 7.99, "a")], duration=7.99))   # 20 ms that ends the file
    assert tail["cuts"][0]["end"] == pytest.approx(7.99)


# ---------------------------------------------------------------------------
# source_matches / resolve_voice_cuts
# ---------------------------------------------------------------------------

def test_source_matches_needs_path_size_and_mtime(tmp_path, monkeypatch):
    monkeypatch.setattr(voice_cut_map, "BASE_DIR", tmp_path)
    voice = tmp_path / "03_Projects" / "p" / "voiceover.wav"
    voice.parent.mkdir(parents=True)
    voice.write_bytes(b"voice")
    current = voice_cut_map.voice_file_identity("03_Projects/p/voiceover.wav")
    assert current["size"] == 5
    source = {"path": "03_Projects/p/voiceover.wav", "size": current["size"], "mtime_ns": current["mtime_ns"]}
    assert source_matches(source, current) is True
    # pipeline_context fingerprints spell the size `size_bytes`
    assert source_matches(source, {**current, "size_bytes": current["size"], "size": None}) is False
    assert source_matches(source, {"path": current["path"], "size_bytes": current["size"],
                                   "mtime_ns": current["mtime_ns"]}) is True
    for broken in ({**source, "size": 6}, {**source, "mtime_ns": 1}, {**source, "path": "03_Projects/p/other.wav"},
                   {"path": source["path"]}, {**source, "size": None}):
        assert source_matches(broken, current) is False
    assert source_matches(source, None) is False
    assert source_matches(None, current) is False


def test_resolve_voice_cuts_cases(tmp_path, monkeypatch):
    monkeypatch.setattr(voice_cut_map, "BASE_DIR", tmp_path)
    voice = tmp_path / "voiceover.wav"
    voice.write_bytes(b"voice-v1")
    current = voice_cut_map.voice_file_identity(voice)
    source = {"path": "voiceover.wav", "size": current["size"], "mtime_ns": current["mtime_ns"]}
    good = {"schema_version": 1, "source": {**source, "duration": 10.0}, "cuts": [cut(2.01, 2.49, "a")]}

    cuts, problem, duration = resolve_voice_cuts(good, current)
    assert problem is None and duration == 10.0
    assert cuts == [cut(2.0, 2.5, "a", reason="manual")]

    assert resolve_voice_cuts(None, current) == ([], None, 0.0)
    assert resolve_voice_cuts({}, current) == ([], None, 0.0)
    assert resolve_voice_cuts({**good, "cuts": []}, current) == ([], None, 0.0)

    voice.write_bytes(b"voice-v2-longer")                       # the file was replaced
    replaced = voice_cut_map.voice_file_identity(voice)
    assert resolve_voice_cuts(good, replaced) == ([], "stale", 10.0)

    assert resolve_voice_cuts({"source": "x", "cuts": [cut(1, 2)]}, current)[1] == "invalid"
    assert resolve_voice_cuts(good, None)[1] == "stale"       # no voice file to compare with
