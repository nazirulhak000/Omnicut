"""Preview voice-cut scheduler  <->  render voice-cut graph parity.

frontend/src/lib/voiceCutScheduler.js decides which spans of the decoded voice
the preview plays (one AudioBufferSourceNode each) and where the 8 ms ramps go.
The render truth is scripts/sfx_manager.py `build_voice_cut_graph` fed by
scripts/voice_cut_map.py `keep_ranges`, and `SFXManager._voice_cut_graph`
deciding whether any cut applies at all. Over 300 seeded random cut sets this
checks, per kept range: the same source interval (exact vs keep_ranges, and vs
the graph's atrim to its 6-decimal print), fade-in / fade-out on exactly the
same edges, the fade-out start (afade st), and the same "cuts anything" verdict.
It also checks that the first node of a mid-play start sits at
program_to_source(t). Runs the JS side with node (skipped when node is missing).
"""

import json
import random
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from scripts.sfx_manager import VOICE_CUT_FADE_S, SFXManager, build_voice_cut_graph
from scripts.voice_cut_map import keep_ranges, normalize_cuts, program_to_source

ROOT = Path(__file__).resolve().parents[1]
JS_LIB = ROOT / "frontend" / "src" / "lib" / "voiceCutScheduler.js"
JS_MAP = ROOT / "frontend" / "src" / "lib" / "voiceCutMap.js"
CASES = 300
SEED = 20261004

pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="needs node")

JS_RUNNER = """
import { readFileSync } from 'node:fs';
const toUrl = (p) => new URL('file:///' + p.replace(/\\\\/g, '/')).href;
const sched = await import(toUrl(process.argv[2]));
const map = await import(toUrl(process.argv[3]));
const cases = JSON.parse(readFileSync(process.argv[4], 'utf8'));
console.log(JSON.stringify({
  fade: sched.VOICE_CUT_FADE_S,
  out: cases.map((c) => {
    const ranges = map.keepRanges(c.cuts, c.sd);
    return {
      any: sched.voiceEditCutsAnything({ source: { duration: c.sd }, cuts: c.cuts }),
      full: sched.scheduleVoiceCut(ranges, { t: 0, ctxNow: 0, sourceDuration: c.sd }),
      probes: c.probes.map((t) => sched.scheduleVoiceCut(ranges, { t, ctxNow: 0, sourceDuration: c.sd })[0] || null),
    };
  }),
}));
"""

_CHAIN = re.compile(
    r"atrim=start=(?P<s>[0-9.]+)(?::end=(?P<e>[0-9.]+))?,asetpts=PTS-STARTPTS"
    r"(?P<fin>,afade=t=in:st=0:d=[0-9.]+)?(?:,afade=t=out:st=(?P<ost>[0-9.]+):d=[0-9.]+)?\["
)


def _random_case(rng):
    sd = rng.choice([rng.randint(60, 1800) / 30, round(rng.uniform(2, 60), rng.choice([1, 2, 3, 6]))])
    cuts = []
    for _ in range(rng.randint(1, 8)):
        start = rng.uniform(-0.5, sd + 0.5)
        cuts.append({"id": f"c{len(cuts)}", "start": start, "end": start + rng.uniform(0.0, 3.0), "reason": "manual"})
    if rng.random() < 0.15:
        cuts.append({"id": "head", "start": 0, "end": rng.uniform(0.1, 1.0)})
    if rng.random() < 0.15:
        cuts.append({"id": "tail", "start": sd - rng.uniform(0.1, 1.0), "end": sd + 1})
    probes = [rng.uniform(0, sd) for _ in range(4)]
    return {"sd": sd, "cuts": cuts, "probes": probes}


def _run_js(cases):
    with tempfile.TemporaryDirectory() as tmp:
        runner = Path(tmp) / "sched.mjs"
        data = Path(tmp) / "cases.json"
        runner.write_text(JS_RUNNER, encoding="utf-8")
        data.write_text(json.dumps(cases), encoding="utf-8")
        proc = subprocess.run(
            ["node", str(runner), str(JS_LIB), str(JS_MAP), str(data)],
            capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_scheduler_matches_render_voice_cut_graph():
    rng = random.Random(SEED)
    cases = [_random_case(rng) for _ in range(CASES)]
    result = _run_js(cases)
    assert result["fade"] == VOICE_CUT_FADE_S

    applied = 0
    for case, js in zip(cases, result["out"]):
        sd = case["sd"]
        keep = keep_ranges(case["cuts"], sd)
        graph = SFXManager._voice_cut_graph(Path("unused.wav"), case["cuts"], sd)
        assert js["any"] == bool(graph), case
        if not keep:
            assert js["full"] == []
            continue

        # Same kept intervals as keep_ranges, bit for bit.
        assert [(n["srcStart"], n["srcEnd"], n["progStart"]) for n in js["full"]] == [
            (r["src_start"], r["src_end"], r["prog_start"]) for r in keep
        ]
        for node, rng_ in zip(js["full"], keep):
            assert node["offset"] == rng_["src_start"]
            assert abs(node["duration"] - (rng_["src_end"] - rng_["src_start"])) < 1e-12

        # Same ramps on the same edges as the ffmpeg graph actually built.
        chains = list(_CHAIN.finditer(build_voice_cut_graph(keep, sd)))
        assert len(chains) == len(keep)
        for node, chain in zip(js["full"], chains):
            assert abs(float(chain["s"]) - node["srcStart"]) <= 5e-7
            if chain["e"] is not None:
                assert abs(float(chain["e"]) - node["srcEnd"]) <= 5e-7
            assert (node["fadeIn"] > 0) == bool(chain["fin"]) == node["rangeFadeIn"]
            assert (node["fadeOut"] > 0) == (chain["ost"] is not None) == node["rangeFadeOut"]
            if node["fadeIn"] > 0:
                assert node["fadeIn"] == VOICE_CUT_FADE_S
            if chain["ost"] is not None:
                assert abs(float(chain["ost"]) - (node["duration"] - node["fadeOut"])) <= 5e-7
        applied += bool(graph)

        # Mid-play start: the first node plays program_to_source(t).
        normalized = normalize_cuts(case["cuts"], sd)
        total = sum(r["src_end"] - r["src_start"] for r in keep)
        for t, first in zip(case["probes"], js["probes"]):
            if t >= total - 1e-9:
                continue
            assert first is not None
            assert abs(first["offset"] - program_to_source(t, normalized)) < 1e-9
            assert first["when"] == 0
    assert applied > CASES // 2, "the random cases should mostly produce a real cut graph"
