"""Effective-value parity: ASS builder == preview evaluator == motion catalog
(round EDITOR-CUT-QUALITY-R2, lane E2c).

The sibling gates (test_text_motion_easing.py, test_motion_catalog_builder_tie.py)
compare the segment ENDS the builder emits.  They cannot see a segment that starts
at the wrong time: libass holds the initial override value until a ``\\t`` begins,
so a ramp that starts late renders a different curve than the preview/catalog even
though every ``\\t`` end time, value and accel is right.  That is exactly how
``elastic_bounce`` rendered ~40% scale for its first 40 ms (the scale segment
inherited the alpha channel's 40 ms keyframe as its start).

This module therefore evaluates the *effective* value at many times:

  * ``ass_effective`` -- a tiny libass-semantics evaluator: the state before a
    ``\\t`` is the value left by the override tags / earlier ``\\t`` segments, and
    ``\\t(t1,t2,accel,tags)`` moves the state towards its target by
    ``progress ** accel`` (0 before t1, 1 from t2 on; libass ``ass_parse.c``);
  * the preview evaluators of SequencePlayer.jsx (run under node);
  * the declarative catalog (``sample_motion_contract``).

It runs for every In / Out / Loop preset that has a ``\\t`` chain.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.subtitle.motion_contract import MOTION_PRESETS, sample_motion_contract
from scripts.subtitle.motion_effects import (
    HOOK_IN_ALIASES,
    HOOK_IN_BUILDERS,
    HOOK_LOOP_BUILDERS,
    HOOK_OUT_BUILDERS,
    _in_elastic_bounce,
)

ROOT = Path(__file__).resolve().parents[1]
SEQUENCE_PLAYER = ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx"

_T_RE = re.compile(r"\\t\((\d+),(\d+),(?:([\d.]+),)?((?:\\[a-z]+[^\\)]*)+)\)")
_PROP_RE = re.compile(r"\\([a-z]+)(&H[0-9A-Fa-f]+&|-?[\d.]+)")

# ASS property -> catalog/preview track; resting value of each track.
_TRACK_OF_PROP = {"fscx": "scale", "alpha": "alpha", "frz": "rotation", "blur": "blur"}
_PREVIEW_KEY = {"scale": "scale", "alpha": "alpha", "rotation": "rot", "blur": "blur"}
_REST = {"scale": 1.0, "alpha": 1.0, "rotation": 0.0, "blur": 0.0}
TOL = 1e-6

SAMPLE_FRACTIONS = [i / 20 for i in range(21)]
# Early-entrance probes: the render/preview split lives inside the first 160 ms.
EARLY_MS = (0, 20, 40, 100)

_IN_BUILDERS = {**HOOK_IN_BUILDERS, **HOOK_IN_ALIASES}
IN_NAMES = sorted(
    n for n in _IN_BUILDERS
    if f"hook.in.{n}" in MOTION_PRESETS and MOTION_PRESETS[f"hook.in.{n}"]["duration_ms"] > 0
)
OUT_NAMES = sorted(HOOK_OUT_BUILDERS)
LOOP_NAMES = ["pulse", "wave", "shake", "flicker"]


# ------------------------------------------------------------------ libass
def _ass_value(prop: str, raw: str) -> float:
    if prop == "alpha":  # &H00& opaque .. &HFF& invisible
        return 1 - int(raw.strip("&H"), 16) / 255
    if prop == "fscx":  # percent -> ratio (builders are called with target 100)
        return float(raw) / 100
    return float(raw)


def ass_effective(tag: str, t_ms: float) -> dict[str, float]:
    """Effective scale/alpha/rotation/blur of an override tag at ``t_ms`` (libass semantics)."""
    state = dict(_REST)
    for prop, raw in _PROP_RE.findall(_T_RE.sub("", tag)):
        if prop in _TRACK_OF_PROP:
            state[_TRACK_OF_PROP[prop]] = _ass_value(prop, raw)
    for t1, t2, accel, body in _T_RE.findall(tag):  # parse order, like libass
        t1, t2 = int(t1), int(t2)
        if t_ms < t1:
            k = 0.0
        elif t_ms >= t2:
            k = 1.0
        else:
            k = ((t_ms - t1) / (t2 - t1)) ** (float(accel) if accel else 1.0)
        for prop, raw in _PROP_RE.findall(body):
            if prop in _TRACK_OF_PROP:
                track = _TRACK_OF_PROP[prop]
                state[track] += (_ass_value(prop, raw) - state[track]) * k
    return state


# ----------------------------------------------------------------- catalog
def catalog_effective(preset_id: str, normalized_time: float) -> dict[str, float]:
    sampled = sample_motion_contract(MOTION_PRESETS[preset_id], normalized_time)
    return {track: float(sampled.get(track, rest)) for track, rest in _REST.items()}


# ----------------------------------------------------------------- preview
_JS_HARNESS = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
const start = src.indexOf('const ACCEL_SOFT_OUT');
const end = src.indexOf('// Motion contracts are deliberately opt-in.');
if (start < 0 || end < 0) throw new Error('motion region moved');
const api = new Function('HOOK_DIM_OPACITY', src.slice(start, end) +
  '; return { OVERLAY_IN_TRANSFORMS, OVERLAY_LOOP_TRANSFORMS, OVERLAY_OUT_TRANSFORMS };')(1 - 0x25 / 255);
const req = JSON.parse(process.argv[3]);
const out = {};
for (const [name, times] of Object.entries(req.in)) {
  out['in.' + name] = times.map((ms) => api.OVERLAY_IN_TRANSFORMS[name].at(ms));
}
for (const [name, spec] of Object.entries(req.out)) {
  out['out.' + name] = spec.times.map((ms) => api.OVERLAY_OUT_TRANSFORMS[name](ms / 1000, 0, spec.dur / 1000));
}
for (const [name, spec] of Object.entries(req.loop)) {
  out['loop.' + name] = spec.times.map((ms) => api.OVERLAY_LOOP_TRANSFORMS[name](ms / 1000, 0, spec.end / 1000));
}
process.stdout.write(JSON.stringify(out));
"""


def _in_times(name: str) -> list[float]:
    dur = MOTION_PRESETS[f"hook.in.{name}"]["duration_ms"]
    times = {float(m) for m in EARLY_MS if m <= dur + 100}
    times |= {round(f * dur, 3) for f in SAMPLE_FRACTIONS}
    times |= {float(dur + 100)}  # resting
    return sorted(times)


def _out_times(name: str) -> list[float]:
    dur = MOTION_PRESETS[f"hook.out.{name}"]["duration_ms"]
    if name == "none":  # 1 ms hard cut: the edge itself is not comparable across engines
        return [-50.0, float(dur + 50)]
    return sorted({round(f * dur, 3) for f in SAMPLE_FRACTIONS})


def _loop_times(name: str) -> list[float]:
    cycle = MOTION_PRESETS[f"hook.loop.{name}"]["duration_ms"]
    return [round(c * cycle + f * cycle, 3) for c in (0, 1) for f in SAMPLE_FRACTIONS if f < 1]


@pytest.fixture(scope="module")
def preview(tmp_path_factory):
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available")
    harness = tmp_path_factory.mktemp("e2c_js") / "harness.cjs"
    harness.write_text(_JS_HARNESS, encoding="utf-8")
    request = {
        "in": {n: _in_times(n) for n in IN_NAMES},
        "out": {n: {"times": _out_times(n), "dur": MOTION_PRESETS[f"hook.out.{n}"]["duration_ms"]} for n in OUT_NAMES},
        "loop": {n: {"times": _loop_times(n), "end": 3 * MOTION_PRESETS[f"hook.loop.{n}"]["duration_ms"]} for n in LOOP_NAMES},
    }
    proc = subprocess.run(
        [node, str(harness), str(SEQUENCE_PLAYER), json.dumps(request)],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return request, json.loads(proc.stdout)


def _preview_effective(sample: dict) -> dict[str, float]:
    return {track: float(sample.get(key, rest)) for (track, key), rest in zip(_PREVIEW_KEY.items(), _REST.values())}


def _assert_three_way(label: str, ms: float, builder: dict, preview_: dict, catalog: dict) -> None:
    for track in _REST:
        b, p, c = builder[track], preview_[track], catalog[track]
        assert b == pytest.approx(p, abs=TOL) and b == pytest.approx(c, abs=TOL), (
            f"{label}.{track} @ {ms} ms: render(libass)={b:.4f} preview={p:.4f} catalog={c:.4f}"
        )


# ------------------------------------------------------------------- tests
@pytest.mark.parametrize("t0_ms", [0, 350])
@pytest.mark.parametrize("name", IN_NAMES)
def test_in_effective_values_match_across_render_preview_catalog(preview, name, t0_ms):
    request, samples = preview
    contract = MOTION_PRESETS[f"hook.in.{name}"]
    tag, end_ms, _dy = _IN_BUILDERS[name](100.0, t0_ms)
    assert end_ms - t0_ms == contract["duration_ms"]
    for ms, sample in zip(request["in"][name], samples[f"in.{name}"]):
        _assert_three_way(
            f"hook.in.{name}(t0={t0_ms})", ms,
            ass_effective(tag, t0_ms + ms),
            _preview_effective(sample),
            catalog_effective(f"hook.in.{name}", ms / contract["duration_ms"]),
        )


@pytest.mark.parametrize("name", OUT_NAMES)
def test_out_effective_values_match_across_render_preview_catalog(preview, name):
    request, samples = preview
    contract = MOTION_PRESETS[f"hook.out.{name}"]
    dur = contract["duration_ms"]
    exit_start = 1000
    tag, _dy = HOOK_OUT_BUILDERS[name](exit_start, exit_start + int(dur), 100.0)
    for ms, sample in zip(request["out"][name]["times"], samples[f"out.{name}"]):
        _assert_three_way(
            f"hook.out.{name}", ms,
            ass_effective(tag, exit_start + ms),
            _preview_effective(sample),
            catalog_effective(f"hook.out.{name}", ms / dur),
        )


@pytest.mark.parametrize("name", LOOP_NAMES)
def test_loop_effective_values_match_across_render_preview_catalog(preview, name):
    request, samples = preview
    contract = MOTION_PRESETS[f"hook.loop.{name}"]
    cycle = contract["duration_ms"]
    tag = HOOK_LOOP_BUILDERS[name](0, 3 * int(cycle))
    for ms, sample in zip(request["loop"][name]["times"], samples[f"loop.{name}"]):
        _assert_three_way(
            f"hook.loop.{name}", ms,
            ass_effective(tag, ms),
            _preview_effective(sample),
            catalog_effective(f"hook.loop.{name}", (ms % cycle) / cycle),
        )


def test_elastic_bounce_scale_ramps_from_t0_not_from_the_alpha_keyframe():
    """Regression: render held ~40% scale for 40 ms, then ramped over 120 ms instead of 160 ms."""
    tag, end_ms, _ = _in_elastic_bounce(100.0, 0)
    assert end_ms == 520
    # catalog: scale 0.4 -> 1.28 over 160 ms with power 0.6, resting on 1.0 at 520 ms
    for ms in EARLY_MS:
        expected = 0.4 + (1.28 - 0.4) * (ms / 160) ** 0.6
        assert ass_effective(tag, ms)["scale"] == pytest.approx(expected, abs=TOL), ms
    assert ass_effective(tag, 0)["scale"] == pytest.approx(0.4)
    assert ass_effective(tag, 20)["scale"] > 0.6  # was held at 0.40 by the bug
    # alpha still fades in over the first 40 ms and the rest state is untouched
    assert ass_effective(tag, 0)["alpha"] == pytest.approx(0.0)
    assert ass_effective(tag, 20)["alpha"] == pytest.approx(0.5)
    assert ass_effective(tag, 40)["alpha"] == pytest.approx(1.0)
    assert ass_effective(tag, end_ms) == {"scale": 1.0, "alpha": 1.0, "rotation": 0.0, "blur": 0.0}
    assert ass_effective(tag, end_ms + 500)["scale"] == 1.0


def test_effective_value_evaluator_follows_libass_semantics():
    """The evaluator itself: hold initial value before t1, ease with k**accel, chain sequentially."""
    tag = r"\fscx40\fscy40\alpha&HFF&\t(0,40,\alpha&H00&)\t(40,160,0.6,\fscx128\fscy128)"
    assert ass_effective(tag, 0)["scale"] == pytest.approx(0.4)
    assert ass_effective(tag, 39)["scale"] == pytest.approx(0.4)  # held until the scale \t starts
    assert ass_effective(tag, 100)["scale"] == pytest.approx(0.4 + 0.88 * (60 / 120) ** 0.6)
    assert ass_effective(tag, 160)["scale"] == pytest.approx(1.28)
    assert ass_effective(tag, 20)["alpha"] == pytest.approx(0.5)
