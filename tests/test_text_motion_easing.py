"""Text/hook motion easing + frame-grid gates (round EDITOR-CUT-QUALITY-R2, lane E2).

Checks, for the eased presets, that
  * the ASS emitted by motion_effects.py (\\t with accel, which libass applies
    as progress ** accel) samples to the same curve as motion_contract's
    ``power`` easing,
  * the preview evaluator in SequencePlayer.jsx (hookKeyframeAt, run under
    node) gives the identical values at the same times,
  * resting (end) states are exactly the pre-easing values,
  * shake / glitch step lengths sit on the 30 fps frame grid (+-1 ms).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.subtitle.motion_contract import _easing_progress
from scripts.subtitle.motion_effects import (
    ACCEL_SNAP_IN,
    ACCEL_SOFT_OUT,
    GLITCH_STEP_MS,
    _in_bounce,
    _in_pop,
    _in_zoom,
    _loop_shake,
    _out_fade,
    _out_glitch,
    _out_zoom,
)

ROOT = Path(__file__).resolve().parents[1]
SEQUENCE_PLAYER = ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx"
FRAME_MS = 1000 / 30
SAMPLE_FRACTIONS = (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)

_T_RE = re.compile(r"\\t\((\d+),(\d+),(?:([\d.]+),)?((?:\\[a-z]+[^\\)]*)+)\)")


def _scale_track(tag: str) -> list[tuple[int, float, float]]:
    """Parse an In tag into [(t_ms, scale_pct, accel)] for the \\fscx channel."""
    initial = float(re.match(r"\\fscx(\d+)", tag).group(1))
    track = []
    first_t = None
    for t1, t2, accel, body in _T_RE.findall(tag):
        m = re.search(r"\\fscx(\d+)", body)
        if not m:
            continue
        if first_t is None:
            first_t = int(t1)
            track.append((first_t, initial, 1.0))
        track.append((int(t2), float(m.group(1)), float(accel) if accel else 1.0))
    return track


def _sample_contract(track, ms: float) -> float:
    if ms <= track[0][0]:
        return track[0][1]
    for (t1, v1, _), (t2, v2, accel) in zip(track, track[1:]):
        if ms <= t2:
            p = (ms - t1) / (t2 - t1)
            return v1 + (v2 - v1) * _easing_progress({"name": "power", "exponent": accel}, p)
    return track[-1][1]


@pytest.mark.parametrize(
    "builder, accels, rest_pct",
    [
        (_in_bounce, [ACCEL_SOFT_OUT] * 4, 100),
        (_in_pop, [ACCEL_SOFT_OUT] * 2, 100),
        (_in_zoom, [ACCEL_SOFT_OUT], 100),
    ],
)
def test_in_presets_emit_eased_accel_and_keep_their_resting_scale(builder, accels, rest_pct):
    tag, end_ms, dy = builder(100.0, 0)
    track = _scale_track(tag)
    assert [a for _, _, a in track[1:]] == accels
    # resting geometry unchanged: last scale keyframe is the target, at end_ms
    assert track[-1][:2] == (end_ms, rest_pct)
    assert dy is None


def test_eased_in_values_differ_from_linear_only_inside_segments():
    tag, _, _ = _in_bounce(100.0, 0)
    track = _scale_track(tag)
    for (t1, v1, _), (t2, v2, accel) in zip(track, track[1:]):
        # endpoints identical to the old linear keyframes
        assert _sample_contract(track, t1) == pytest.approx(v1)
        assert _sample_contract(track, t2) == pytest.approx(v2)
        mid = (t1 + t2) / 2
        linear_mid = (v1 + v2) / 2
        eased_mid = v1 + (v2 - v1) * 0.5 ** accel
        assert _sample_contract(track, mid) == pytest.approx(eased_mid)
        assert eased_mid != pytest.approx(linear_mid)


def test_out_presets_ease_in_and_end_fully_transparent():
    fade, _ = _out_fade(1000, 1150, 100)
    assert fade == rf"\t(1000,1150,{ACCEL_SNAP_IN},\alpha&HFF&)"
    zoom, _ = _out_zoom(1000, 1150, 100)
    assert zoom == rf"\t(1000,1150,{ACCEL_SNAP_IN},\fscx140\fscy140\alpha&HFF&)"


def _step_lengths(tag: str) -> list[int]:
    return [int(t2) - int(t1) for t1, t2, _, _ in _T_RE.findall(tag)]


def test_shake_and_glitch_steps_are_whole_frames_at_30fps():
    shake_steps = _step_lengths(_loop_shake(0, 2000))
    assert shake_steps and set(shake_steps) == {100}
    glitch, _ = _out_glitch(2850, 3000, 100)
    glitch_steps = _step_lengths(glitch)
    assert glitch_steps and set(glitch_steps) == {GLITCH_STEP_MS}
    for step in set(shake_steps) | set(glitch_steps):
        frames = max(1, round(step / FRAME_MS))
        assert abs(step - frames * FRAME_MS) <= 1.0, f"{step} ms is off the 30 fps grid"


# ---------------------------------------------------------------- JS side
_JS_HARNESS = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
const start = src.indexOf('const ACCEL_SOFT_OUT');
const end = src.indexOf('// Motion contracts are deliberately opt-in.');
if (start < 0 || end < 0) throw new Error('motion region moved');
const region = src.slice(start, end);
const api = new Function('HOOK_DIM_OPACITY', region +
  '; return { hookKeyframeAt, OVERLAY_IN_TRANSFORMS, OVERLAY_LOOP_TRANSFORMS, OVERLAY_OUT_TRANSFORMS };')(0.85);
const req = JSON.parse(process.argv[3]);
const out = {};
for (const [name, times] of Object.entries(req.in)) {
  out['in.' + name] = times.map((ms) => api.OVERLAY_IN_TRANSFORMS[name].at(ms).scale);
}
for (const [name, times] of Object.entries(req.out)) {
  out['out.' + name] = times.map((t) => api.OVERLAY_OUT_TRANSFORMS[name](t, 1.0, 1.15));
}
out.shake = req.shake.map((t) => api.OVERLAY_LOOP_TRANSFORMS.shake(t, 0, 2).rot);
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js_samples(tmp_path_factory):
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available")
    harness = tmp_path_factory.mktemp("e2_js") / "harness.cjs"
    harness.write_text(_JS_HARNESS, encoding="utf-8")
    durations = {"bounce": 450, "pop": 200, "zoom": 300}
    request = {
        "in": {name: [round(f * dur, 3) for f in SAMPLE_FRACTIONS] for name, dur in durations.items()},
        "out": {"fade": [1.0 + f * 0.15 for f in SAMPLE_FRACTIONS], "zoom": [1.0 + f * 0.15 for f in SAMPLE_FRACTIONS]},
        "shake": [0.05, 0.1, 0.15, 0.2, 0.25, 0.35],
    }
    proc = subprocess.run(
        [node, str(harness), str(SEQUENCE_PLAYER), json.dumps(request)],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return request, json.loads(proc.stdout)


@pytest.mark.parametrize("name, builder", [("bounce", _in_bounce), ("pop", _in_pop), ("zoom", _in_zoom)])
def test_preview_in_curve_equals_ass_accel_and_contract_power(js_samples, name, builder):
    request, samples = js_samples
    tag, _, _ = builder(100.0, 0)
    track = _scale_track(tag)
    for ms, js_scale in zip(request["in"][name], samples[f"in.{name}"]):
        # ASS scales are integer percent; compare at that precision.
        assert js_scale * 100 == pytest.approx(_sample_contract(track, ms), abs=0.51), (name, ms)
    assert samples[f"in.{name}"][-1] == 1.0


def test_preview_out_curves_use_the_same_snap_in_power(js_samples):
    request, samples = js_samples
    for t, fade, zoom in zip(request["out"]["fade"], samples["out.fade"], samples["out.zoom"]):
        p = min(1.0, max(0.0, (t - 1.0) / 0.15))
        eased = _easing_progress({"name": "power", "exponent": ACCEL_SNAP_IN}, p)
        assert fade["alpha"] == pytest.approx(1 - eased, abs=1e-9)
        assert zoom["alpha"] == pytest.approx(1 - eased, abs=1e-9)
        assert zoom["scale"] == pytest.approx(1 + 0.4 * eased, abs=1e-9)
    assert samples["out.fade"][-1]["alpha"] == pytest.approx(0)
    assert samples["out.zoom"][-1]["scale"] == pytest.approx(1.4)


def test_preview_shake_steps_match_render_step(js_samples):
    request, samples = js_samples
    # 100 ms steps: -3 reached at 0.1 s, 3 at 0.2 s; halfway points are linear.
    expected = {0.05: -1.5, 0.1: -3.0, 0.15: 0.0, 0.2: 3.0, 0.25: 0.5, 0.35: 0.0}
    for t, rot in zip(request["shake"], samples["shake"]):
        assert rot == pytest.approx(expected[t], abs=1e-9), t
