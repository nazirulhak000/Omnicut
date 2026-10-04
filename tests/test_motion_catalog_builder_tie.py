"""Declarative motion catalog <-> ASS builder tie (round EDITOR-CUT-QUALITY-R2, lane E2b).

scripts/subtitle/motion_contract.py (MOTION_PRESETS) and
frontend/src/lib/motion/motionPresets.js describe the same hook/text presets that
motion_effects.py builds as ASS ``\\t`` chains.  libass eases a ``\\t(t1,t2,accel,..)``
segment with ``progress ** accel``, which the contract spells as
``{"name": "power", "exponent": accel}`` on the keyframe that ENDS the segment.

These gates stop the catalogs drifting from the builders again:
  * every segment end the builder emits has a catalog keyframe at the same time with
    the same value and the same exponent (accel 1.0 <-> linear),
  * no catalog keyframe carries an easing the builder does not emit,
  * catalog durations / loop cycles equal what the builders run,
  * the Python and JS catalogs are identical.

Segment START times are not compared: serialize_keyframes starts each segment at the
previous keyframe, which can differ from the catalog for presets that animate two
channels with different keyframe grids (see elastic_bounce note in the E2b report).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.subtitle.motion_contract import MOTION_PRESETS
from scripts.subtitle.motion_effects import (
    HOOK_IN_ALIASES,
    HOOK_IN_BUILDERS,
    HOOK_LOOP_BUILDERS,
    HOOK_OUT_BUILDERS,
)

ROOT = Path(__file__).resolve().parents[1]
MOTION_PRESETS_JS = ROOT / "frontend" / "src" / "lib" / "motion" / "motionPresets.js"

# ASS property -> catalog track name (properties the catalog can express).
_TRACK_OF_PROP = {"fscx": "scale", "alpha": "alpha", "frz": "rotation", "blur": "blur"}

_SEG_RE = re.compile(r"\\t\((\d+),(\d+),(?:([\d.]+),)?((?:\\[a-z]+[^\\)]*)+)\)")
_PROP_RE = re.compile(r"\\([a-z]+)(&H[0-9A-Fa-f]+&|-?[\d.]+)")


def _value(prop: str, raw: str) -> float:
    if prop == "alpha":  # ASS alpha is transparency: &H00& opaque .. &HFF& invisible
        return 1 - int(raw.strip("&H"), 16) / 255
    if prop == "fscx":  # percent -> ratio (target scale is 100)
        return float(raw) / 100
    return float(raw)


def _segments(tag: str) -> dict[str, list[tuple[int, int, float, float]]]:
    """track -> [(t1_ms, t2_ms, accel, value)] for every ``\\t`` segment of an override tag."""
    out: dict[str, list[tuple[int, int, float, float]]] = {}
    for t1, t2, accel, body in _SEG_RE.findall(tag):
        for prop, raw in _PROP_RE.findall(body):
            track = _TRACK_OF_PROP.get(prop)
            if track:
                out.setdefault(track, []).append((int(t1), int(t2), float(accel) if accel else 1.0, _value(prop, raw)))
    return out


def _exponent(easing) -> float:
    """Catalog easing -> libass accel; anything not expressible as a power law is a failure."""
    if easing in (None, "linear"):
        return 1.0
    spec = easing if isinstance(easing, dict) else {"name": easing}
    assert spec.get("name") == "power", f"easing {easing!r} has no libass accel equivalent"
    return float(spec["exponent"])


def _assert_tied(preset_id: str, tag: str, duration_ms: float) -> None:
    contract = MOTION_PRESETS[preset_id]
    segments = _segments(tag)
    for track_name, segs in segments.items():
        track = contract["tracks"].get(track_name)
        assert track is not None, f"{preset_id}: builder animates {track_name} but the catalog has no such track"
        keyframes = track["keyframes"]
        for _t1, t2, accel, value in segs:
            key = t2 / duration_ms
            match = [k for k in keyframes if abs(k["t"] - key) < 1e-6]
            assert match, f"{preset_id}.{track_name}: no catalog keyframe at {t2} ms (t={key:.4f})"
            assert match[0]["value"] == pytest.approx(value, abs=1e-6), f"{preset_id}.{track_name}@{t2} ms value"
            assert _exponent(match[0].get("easing")) == pytest.approx(accel), f"{preset_id}.{track_name}@{t2} ms easing"
    # converse: an eased catalog keyframe must be backed by a builder segment with that accel
    for track_name, track in contract["tracks"].items():
        if track_name not in segments:
            continue
        ends = {round(t2 / duration_ms, 6): accel for _t1, t2, accel, _v in segments[track_name]}
        for keyframe in track["keyframes"][1:]:
            exponent = _exponent(keyframe.get("easing"))
            if exponent != 1.0:
                assert ends.get(round(keyframe["t"], 6)) == pytest.approx(exponent), (
                    f"{preset_id}.{track_name}: catalog easing at t={keyframe['t']:.4f} is not emitted by the builder"
                )


_IN_BUILDERS = {**HOOK_IN_BUILDERS, **HOOK_IN_ALIASES}


@pytest.mark.parametrize("name", sorted(_IN_BUILDERS))
def test_in_catalog_matches_builder_easing_values_and_duration(name):
    tag, end_ms, _dy = _IN_BUILDERS[name](100.0, 0)
    ids = [i for i in (f"hook.in.{name}", f"text.in.{name}") if i in MOTION_PRESETS]
    assert ids, f"hook.in.{name} missing from the catalog"
    for preset_id in ids:
        assert MOTION_PRESETS[preset_id]["duration_ms"] == end_ms, f"{preset_id} duration"
        if end_ms:
            _assert_tied(preset_id, tag, end_ms)


@pytest.mark.parametrize("name", sorted(HOOK_OUT_BUILDERS))
def test_out_catalog_matches_builder_easing_values_and_duration(name):
    contract = MOTION_PRESETS[f"hook.out.{name}"]
    duration = contract["duration_ms"]
    tag, _dy = HOOK_OUT_BUILDERS[name](0, int(duration), 100.0)
    _assert_tied(f"hook.out.{name}", tag, duration)


@pytest.mark.parametrize("name", ["pulse", "wave", "shake", "flicker"])
def test_loop_catalog_cycle_matches_builder_chain(name):
    contract = MOTION_PRESETS[f"hook.loop.{name}"]
    cycle = contract["duration_ms"]
    (track_name, track), = contract["tracks"].items()
    assert track["cycle_duration_ms"] == cycle
    segs = _segments(HOOK_LOOP_BUILDERS[name](0, int(cycle * 3)))[track_name]
    keyframes = track["keyframes"]
    n = len(keyframes) - 1
    assert len(segs) == 3 * n, f"{name}: builder chain is not {n} steps per cycle"
    for i, (_t1, t2, accel, value) in enumerate(segs):
        keyframe = keyframes[i % n + 1]
        assert t2 == pytest.approx(cycle * (i // n + keyframe["t"]), abs=1.0), f"{name} step {i} time"
        assert value == pytest.approx(keyframe["value"], abs=0.01), f"{name} step {i} value"
        assert accel == 1.0 and _exponent(keyframe.get("easing")) == 1.0


def test_python_and_js_catalogs_are_identical():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available")
    script = (
        "import(process.argv[1]).then(m => process.stdout.write(JSON.stringify(m.MOTION_PRESETS)))"
        ".catch(e => { console.error(e); process.exit(1); })"
    )
    proc = subprocess.run(
        [node, "-e", script, MOTION_PRESETS_JS.as_uri()],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    js_catalog = json.loads(proc.stdout)
    assert set(js_catalog) == set(MOTION_PRESETS)
    for preset_id, python_preset in MOTION_PRESETS.items():
        js_preset = js_catalog[preset_id]
        assert js_preset["duration_ms"] == python_preset["duration_ms"], f"{preset_id} duration_ms"
        assert js_preset["tracks"] == python_preset["tracks"], f"{preset_id} tracks"
