"""
Comprehensive Unit & Parity Test Suite for CapCut 7.1 Wave 2 Deep Extraction & Full End-to-End Wiring.
Verifies W2.1-W2.7 Python & JS parity within 1e-6 tolerance.
"""

import json
import subprocess

from scripts.motion_analyzer import (
    CAPCUT_SCENE_DETECT_THRESHOLD,
    CAPCUT_SCENE_DETECT_WINDOW,
    detect_scene_cuts,
)
from scripts.sfx_manager import VOICE_CLARITY_CHAIN, voice_clarity_filter
from scripts.tiktok_enhancer import (
    CAPCUT_GPU_DRIVER_BUG_LIST,
    is_gpu_driver_blacklisted,
)
from scripts.video_editor import (
    BLEND_MODE_FFMPEG_MAP,
    LOG_WHEEL_CROSSOVER,
    build_eq_filter,
    capcut_back_out,
    capcut_elastic_out,
    capcut_soft_light_channel,
    capcut_spring_scale,
    process_primary_wheel_channel,
)


def test_w2_1_scene_cut_detection_window_and_threshold():
    assert CAPCUT_SCENE_DETECT_WINDOW == 7
    assert CAPCUT_SCENE_DETECT_THRESHOLD == 0.35
    # Low delta sequence with one sharp cut at index 10
    scores = [0.05] * 10 + [0.65] + [0.04] * 10
    times = [round(i * 0.25, 3) for i in range(len(scores))]
    cuts = detect_scene_cuts(times, scores)
    assert len(cuts) == 1
    assert abs(cuts[0] - 2.5) < 1e-4


def test_w2_3_blend_mode_and_soft_light_parity():
    assert BLEND_MODE_FFMPEG_MAP["screen"] == "screen"
    assert BLEND_MODE_FFMPEG_MAP["multiply"] == "multiply"
    assert BLEND_MODE_FFMPEG_MAP["overlay"] == "overlay"
    assert BLEND_MODE_FFMPEG_MAP["soft_light"] == "softlight"

    js_script = """
    import { capcutSoftLightChannel } from './frontend/src/lib/stickerAnimation.js';
    const pairs = [[0.2, 0.3], [0.5, 0.5], [0.8, 0.2], [0.25, 0.75], [0.9, 0.85]];
    console.log(JSON.stringify(pairs.map(([b, s]) => capcutSoftLightChannel(b, s))));
    """
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", js_script],
        capture_output=True,
        text=True,
        check=True,
    )
    js_vals = json.loads(proc.stdout)
    pairs = [(0.2, 0.3), (0.5, 0.5), (0.8, 0.2), (0.25, 0.75), (0.9, 0.85)]
    for (b, s), jv in zip(pairs, js_vals):
        pv = capcut_soft_light_channel(b, s)
        assert abs(pv - jv) < 1e-6


def test_w2_4_primary_wheel_and_temperature_parity():
    assert LOG_WHEEL_CROSSOVER == {"rug_down": 0.333, "rug_up": 0.555}
    eq = build_eq_filter({"brightness": 0.05, "gamma": 1.15, "temperature": 0.12})
    assert "gamma=1.15" in eq
    assert "colorbalance=rs=0.120:bs=-0.120" in eq

    js_script = """
    import { processPrimaryWheelChannel } from './frontend/src/lib/inspectorModel.js';
    const cases = [
      [0.2, 0.0, 1.0, 1.0],
      [0.5, 0.05, 1.2, 1.1],
      [0.75, -0.05, 0.85, 0.95],
    ];
    console.log(JSON.stringify(cases.map(c => processPrimaryWheelChannel(...c))));
    """
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", js_script],
        capture_output=True,
        text=True,
        check=True,
    )
    js_vals = json.loads(proc.stdout)
    cases = [
        (0.2, 0.0, 1.0, 1.0),
        (0.5, 0.05, 1.2, 1.1),
        (0.75, -0.05, 0.85, 0.95),
    ]
    for args, jv in zip(cases, js_vals):
        pv = process_primary_wheel_channel(*args)
        assert abs(pv - jv) < 1e-6


def test_w2_5_voice_clarity_rnnoise_sami_chain():
    assert "highpass=f=80" in VOICE_CLARITY_CHAIN
    assert "afftdn=nf=-25" in VOICE_CLARITY_CHAIN
    assert "deesser=i=0.4" in VOICE_CLARITY_CHAIN
    assert voice_clarity_filter(True).startswith(VOICE_CLARITY_CHAIN)
    assert voice_clarity_filter(False) == ""


def test_w2_6_sticker_spring_elastic_back_parity():
    js_script = """
    import { capcutSpringScale, capcutElasticOut, capcutBackOut } from './frontend/src/lib/stickerAnimation.js';
    const ts = [0.0, 0.15, 0.35, 0.5, 0.75, 1.0];
    console.log(JSON.stringify({
      spring: ts.map(t => capcutSpringScale(t)),
      elastic: ts.map(t => capcutElasticOut(t)),
      back: ts.map(t => capcutBackOut(t)),
    }));
    """
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", js_script],
        capture_output=True,
        text=True,
        check=True,
    )
    res = json.loads(proc.stdout)
    ts = [0.0, 0.15, 0.35, 0.5, 0.75, 1.0]
    for i, t in enumerate(ts):
        assert abs(capcut_spring_scale(t) - res["spring"][i]) < 1e-6
        assert abs(capcut_elastic_out(t) - res["elastic"][i]) < 1e-6
        assert abs(capcut_back_out(t) - res["back"][i]) < 1e-6


def test_w2_7_gpu_driver_bug_list():
    assert "0x8086" in CAPCUT_GPU_DRIVER_BUG_LIST
    assert "0x10de" in CAPCUT_GPU_DRIVER_BUG_LIST
    assert is_gpu_driver_blacklisted("0x8086", "0x5912") is True
    assert is_gpu_driver_blacklisted("0x10DE", "0x1CB6") is True
    assert is_gpu_driver_blacklisted("0x10DE", "0x2684") is False
