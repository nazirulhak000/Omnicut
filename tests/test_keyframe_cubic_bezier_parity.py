"""
Comprehensive Parity Test for CapCut 7.1 Parametric Cubic-Bezier and Smart Camera Motion.
Verifies that Python (scripts/keyframe_engine.py) and JavaScript (frontend/src/lib/keyframeModel.js)
produce identical results within 1e-6 tolerance.
"""

import subprocess
import json
from scripts.keyframe_engine import (
    solve_cubic_bezier,
    CUBIC_BEZIER_PRESETS,
    generate_smart_camera_keyframes,
    interpolate_numeric_keyframes,
)


def test_cubic_bezier_parity_against_node_eval():
    # Evaluate across 21 test points [0.0, 0.05, ..., 1.0] for all presets
    test_points = [round(i * 0.05, 2) for i in range(21)]
    presets = list(CUBIC_BEZIER_PRESETS.keys())

    # Run JS evaluation in Node
    js_script = """
    import { solveCubicBezier, CUBIC_BEZIER_PRESETS } from './frontend/src/lib/keyframeModel.js';
    const testPoints = %s;
    const presets = %s;
    const results = {};
    for (const p of presets) {
        const [x1, y1, x2, y2] = CUBIC_BEZIER_PRESETS[p];
        results[p] = testPoints.map(t => solveCubicBezier(x1, y1, x2, y2, t));
    }
    console.log(JSON.stringify(results));
    """ % (json.dumps(test_points), json.dumps(presets))

    proc = subprocess.run(
        ["node", "--input-type=module", "-e", js_script],
        capture_output=True,
        text=True,
        check=True,
    )
    js_results = json.loads(proc.stdout)

    for preset, pts in CUBIC_BEZIER_PRESETS.items():
        x1, y1, x2, y2 = pts
        js_values = js_results[preset]
        for t, js_val in zip(test_points, js_values):
            py_val = solve_cubic_bezier(x1, y1, x2, y2, t)
            diff = abs(py_val - js_val)
            assert diff < 1e-6, f"Preset {preset} at t={t}: Py={py_val}, JS={js_val}, diff={diff}"


def test_smart_camera_keyframes_generation():
    for preset in ["slow_push", "slow_pull", "pan_left", "pan_right"]:
        kfs = generate_smart_camera_keyframes(5.0, preset)
        assert len(kfs) == 2
        assert kfs[0]["time"] == 0.0
        assert kfs[1]["time"] == 5.0
        assert kfs[0]["zoom"] >= 1.25  # Base crop 0.8 -> 1.25x
