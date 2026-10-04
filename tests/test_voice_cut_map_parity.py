"""scripts/voice_cut_map.py  <->  frontend/src/lib/voiceCutMap.js  value-for-value parity.

The voice file is never touched: ripple cuts live in the manifest as spans of the
ORIGINAL file and BOTH the render (ffmpeg atrim) and the editor (preview, plan)
convert between "source" and "program" time with these six functions. If the
two implementations drift by even one ulp a cut lands on a different frame in
preview and in the export, so the comparison is exact (`==`, no tolerance) over
500 seeded random cut sets, including the ugly ones: unsorted, overlapping,
out of range, shorter than a frame, numeric strings, junk entries.

Runs the JS side with node (skipped when node is missing) in a temp dir.
"""

import json
import math
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.voice_cut_map import (
    effective_duration,
    keep_ranges,
    normalize_cuts,
    program_to_source,
    shift_time,
    snap_to_frame,
    source_to_program,
)

ROOT = Path(__file__).resolve().parents[1]
JS_LIB = ROOT / "frontend" / "src" / "lib" / "voiceCutMap.js"
CASES = 500
SEED = 20261004

pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="needs node")

JS_RUNNER = """
import { readFileSync } from 'node:fs';
const lib = await import(new URL('file:///' + process.argv[2].replace(/\\\\/g, '/')).href);
const cases = JSON.parse(readFileSync(process.argv[3], 'utf8'));
const out = cases.map((c) => {
  const nc = lib.normalizeCuts(c.cuts, c.sd);
  return {
    nc,
    kr: lib.keepRanges(c.cuts, c.sd),
    ed: lib.effectiveDuration(c.cuts, c.sd),
    sp: c.probes.map((u) => lib.sourceToProgram(u, nc)),
    ps: c.probes.map((t) => lib.programToSource(t, nc)),
    st: c.shifts.map(([t, t0, t1]) => lib.shiftTime(t, t0, t1)),
    snap: c.probes.map((v) => lib.snapToFrameGrid(v)),
  };
});
console.log(JSON.stringify(out));
"""


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _random_source_duration(rng):
    kind = rng.random()
    if kind < 0.05:
        return rng.choice([0, -2.5, None, "abc", "", True, "6.5", " 12.25 "])
    if kind < 0.35:
        return rng.randint(30, 1800) / 30           # whole frames
    return round(rng.uniform(1, 60), rng.choice([1, 2, 3, 6]))


def _random_time(rng, low, high):
    kind = rng.random()
    if kind < 0.25:
        return rng.randint(int(low * 30) - 2, int(high * 30) + 2) / 30      # on the grid
    if kind < 0.40:
        return rng.randint(int(low * 60) - 2, int(high * 60) + 2) / 60      # exact half-frame ties
    if kind < 0.45:
        return str(round(rng.uniform(low, high), 3))                          # numeric string
    return rng.uniform(low, high)


def _random_cuts(rng, sd):
    base = float(sd) if _is_number(sd) and sd > 0 else 10.0
    cuts = []
    for index in range(rng.randint(0, 8)):
        roll = rng.random()
        if roll < 0.03:
            cuts.append(rng.choice([None, 7, "x", [1, 2], True]))
            continue
        start = _random_time(rng, -1.0, base + 1.0)
        length = rng.choice([0.0, rng.uniform(0, 0.02), rng.uniform(0.03, 1.0), rng.uniform(0.5, 5.0)])
        if roll < 0.10:
            end = None
        elif roll < 0.15:
            end = "abc"
        elif isinstance(start, str):
            end = round(float(start) + length, 3)
        else:
            end = start + length
        if rng.random() < 0.1 and not isinstance(start, str) and not isinstance(end, (str, type(None))):
            start, end = end, start                                           # reversed
        cut = {"id": f"c{index}", "start": start, "end": end}
        if rng.random() < 0.5:
            cut["reason"] = rng.choice(["manual", "silence", None])
        if rng.random() < 0.2:
            cut["removed"] = {"cues": index}
        cuts.append(cut)
    if rng.random() < 0.03:
        return None
    return cuts


def _build_cases():
    rng = random.Random(SEED)
    cases = []
    for _ in range(CASES):
        sd = _random_source_duration(rng)
        cuts = _random_cuts(rng, sd)
        base = float(sd) if _is_number(sd) and sd > 0 else 10.0
        nc = normalize_cuts(cuts, sd)
        probes = [0, base, base / 2, -0.5, base + 3]
        for cut in nc:
            for edge in (cut["start"], cut["end"]):
                probes += [edge, edge - 1e-9, edge + 1e-9, edge - 1 / 30, edge + 1 / 30]
        probes += [rng.uniform(-1.0, base + 2.0) for _ in range(6)]
        probes += [_random_time(rng, 0, base) for _ in range(4)]
        shifts = []
        for _ in range(8):
            t0 = _random_time(rng, 0, base)
            t1 = t0 + rng.choice([0.0, 1 / 30, rng.uniform(0.03, 3.0)]) if _is_number(t0) else 2.0
            t = rng.choice([t0, t1, rng.uniform(-1.0, base + 2.0), _random_time(rng, 0, base)])
            shifts.append([t, t0, t1])
        shifts.append([1.0, "x", 2.0])
        shifts.append(["y", 1.0, 2.0])
        shifts.append([2.0, 2.0, 2.5])
        shifts.append([2.5, 2.0, 2.5])
        cases.append({"sd": sd, "cuts": cuts, "probes": probes, "shifts": shifts})
    return cases


def _python_side(case):
    sd, cuts = case["sd"], case["cuts"]
    nc = normalize_cuts(cuts, sd)
    return {
        "nc": nc,
        "kr": [
            {"srcStart": r["src_start"], "srcEnd": r["src_end"], "progStart": r["prog_start"]}
            for r in keep_ranges(cuts, sd)
        ],
        "ed": effective_duration(cuts, sd),
        "sp": [source_to_program(u, nc) for u in case["probes"]],
        "ps": [program_to_source(t, nc) for t in case["probes"]],
        "st": [shift_time(t, t0, t1) for t, t0, t1 in case["shifts"]],
        "snap": [snap_to_frame(v) for v in case["probes"]],
    }


def test_python_and_js_agree_on_every_value(tmp_path):
    cases = _build_cases()
    assert len(cases) == CASES

    script = tmp_path / "parity.mjs"
    script.write_text(JS_RUNNER, encoding="utf-8")
    data = tmp_path / "cases.json"
    data.write_text(json.dumps(cases), encoding="utf-8")
    proc = subprocess.run(
        ["node", str(script), str(JS_LIB), str(data)],
        capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    js_results = json.loads(proc.stdout)
    assert len(js_results) == CASES

    compared = 0
    non_trivial = 0
    for index, (case, js) in enumerate(zip(cases, js_results)):
        py = _python_side(case)
        # The JSON round trip is the only thing the JS side sees, so run Python
        # through it too (a tuple/-0.0 difference must not hide a real one).
        py = json.loads(json.dumps(py))
        for key in ("nc", "kr", "ed", "sp", "ps", "st", "snap"):
            assert py[key] == js[key], f"case {index} ({key}): sd={case['sd']!r} cuts={case['cuts']!r}\npy={py[key]!r}\njs={js[key]!r}"
            compared += 1
        if py["nc"]:
            non_trivial += 1
    assert compared == CASES * 7
    assert non_trivial > CASES * 0.6, "the generator must produce mostly real cut sets"


def test_docstring_examples_hold_on_both_sides(tmp_path):
    """The worked examples copied into voiceCutMap.js docstrings from voice_cut_map.py."""
    cuts = [{"id": "a", "start": 2.0, "end": 2.5}]
    assert normalize_cuts([{"id": "a", "start": 2.01, "end": 2.49}], 6.0) == cuts
    assert keep_ranges(cuts, 6.0) == [
        {"src_start": 0.0, "src_end": 2.0, "prog_start": 0.0},
        {"src_start": 2.5, "src_end": 6.0, "prog_start": 2.0},
    ]
    assert source_to_program(2.25, cuts) == 2.0 and program_to_source(2.0, cuts) == 2.5
    assert effective_duration(cuts, 6.0) == 5.5
    assert shift_time(3.0, 2.0, 2.5) == 2.5
