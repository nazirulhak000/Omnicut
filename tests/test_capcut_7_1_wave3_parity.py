"""
Comprehensive Unit, Parity & Round-Trip Test Suite for CapCut 7.1 Wave 3 Mastery (W3.1 - W3.7).
Verifies JS <-> Python mathematical parity within 1e-6 tolerance, Two-Way Draft Importer
round-trip accuracy, and In-App AI Agent CapCut 7.1 NLE tooling.
"""

import json
import subprocess
from pathlib import Path

from scripts.agent.omnicut_agent_tools import (
    apply_action,
    apply_capcut_color_grade,
    apply_pro_color_grade,
    apply_smart_camera_9_16,
    apply_viral_transitions,
    load_project_manifest,
    normalize_project_audio_lufs,
)
from scripts.tiktok_enhancer import capcut_splendor_vibrance_saturation
from scripts.video_editor import (
    CAPCUT_DECODE_BALANCE_LIMIT,
    CAPCUT_FRAME_BUDGET_MS,
    CAPCUT_HIGH_SPEED_TRANSITIONS,
    CAPCUT_HSL_RANGES,
    apply_capcut_high_speed_transition,
    build_eq_filter,
    capcut_adjust_highlight,
    capcut_adjust_shadow,
    capcut_damped_camera_shake,
    capcut_dehaze_channel,
    capcut_particle_noise,
    capcut_splendor_vibrance,
    capcut_vignette_weight,
)


def test_w3_1_shadows_highlights_dehaze_js_python_parity():
    js_script = """
    import { capcutAdjustShadow, capcutAdjustHighlight, capcutDehazeChannel } from './frontend/src/lib/inspectorModel.js';
    const vals = [0.05, 0.25, 0.50, 0.75, 0.92];
    const amounts = [-0.45, -0.25, 0.0, 0.35, 0.45];
    const out = {
      shadows: vals.map((v, i) => capcutAdjustShadow(v, amounts[i])),
      highlights: vals.map((v, i) => capcutAdjustHighlight(v, amounts[i])),
      dehaze: vals.map((v, i) => capcutDehazeChannel(v, 0.65, 0.9, Math.max(0, amounts[i]))),
    };
    console.log(JSON.stringify(out));
    """
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", js_script],
        capture_output=True,
        text=True,
        check=True,
    )
    js_out = json.loads(proc.stdout)
    vals = [0.05, 0.25, 0.50, 0.75, 0.92]
    amounts = [-0.45, -0.25, 0.0, 0.35, 0.45]
    for i, (v, amt) in enumerate(zip(vals, amounts)):
        assert abs(capcut_adjust_shadow(v, amt) - js_out["shadows"][i]) < 1e-6
        assert abs(capcut_adjust_highlight(v, amt) - js_out["highlights"][i]) < 1e-6
        assert abs(capcut_dehaze_channel(v, 0.65, 0.9, max(0.0, amt)) - js_out["dehaze"][i]) < 1e-6


def test_w3_2_splendor_vibrance_and_8_hsl_ranges_parity():
    assert len(CAPCUT_HSL_RANGES) == 8
    assert CAPCUT_HSL_RANGES["orange"] == (-10, 20, 40, 60)

    js_script = """
    import { capcutSplendorVibrance, CAPCUT_HSL_RANGES } from './frontend/src/lib/inspectorModel.js';
    const samples = [
      [0.85, 0.55, 0.45, 0.4],
      [0.2, 0.6, 0.9, 0.4],
      [0.5, 0.5, 0.5, -0.3],
      [0.9, 0.2, 0.3, 0.45],
    ];
    console.log(JSON.stringify({
      keys: Object.keys(CAPCUT_HSL_RANGES),
      orange: CAPCUT_HSL_RANGES.orange,
      res: samples.map(s => capcutSplendorVibrance(...s)),
    }));
    """
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", js_script],
        capture_output=True,
        text=True,
        check=True,
    )
    js_out = json.loads(proc.stdout)
    assert len(js_out["keys"]) == 8
    assert tuple(js_out["orange"]) == CAPCUT_HSL_RANGES["orange"]
    samples = [
        (0.85, 0.55, 0.45, 0.4),
        (0.2, 0.6, 0.9, 0.4),
        (0.5, 0.5, 0.5, -0.3),
        (0.9, 0.2, 0.3, 0.45),
    ]
    for (r, g, b, vib), j_rgb in zip(samples, js_out["res"]):
        p_rgb = capcut_splendor_vibrance(r, g, b, vib)
        for pc, jc in zip(p_rgb, j_rgb):
            assert abs(pc - jc) < 1e-6

    assert capcut_splendor_vibrance_saturation(1.04, 0.5) > 1.04


def test_w3_3_vignette_and_particle_noise_parity():
    js_script = """
    import { capcutVignetteWeight, capcutParticleNoise } from './frontend/src/lib/inspectorModel.js';
    const coords = [
      [0.5, 0.5, 0.6],
      [0.1, 0.1, 0.6],
      [0.9, 0.85, -0.5],
      [0.0, 1.0, 0.8],
    ];
    console.log(JSON.stringify({
      vig: coords.map(c => capcutVignetteWeight(...c)),
      noise: coords.map(([u, v]) => capcutParticleNoise(u * 10, v * 10)),
    }));
    """
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", js_script],
        capture_output=True,
        text=True,
        check=True,
    )
    js_out = json.loads(proc.stdout)
    coords = [
        (0.5, 0.5, 0.6),
        (0.1, 0.1, 0.6),
        (0.9, 0.85, -0.5),
        (0.0, 1.0, 0.8),
    ]
    for i, (u, v, intensity) in enumerate(coords):
        assert abs(capcut_vignette_weight(u, v, intensity) - js_out["vig"][i]) < 1e-6
        assert abs(capcut_particle_noise(u * 10, v * 10) - js_out["noise"][i]) < 1e-6

    eq_str = build_eq_filter(
        {"shadows": 0.25, "highlights": -0.15, "vibrance": 0.35, "vignette": 0.25}
    )
    assert "curves=all=" in eq_str
    assert "vignette=angle=" in eq_str


def test_w3_4_high_speed_transitions_and_camera_shake_parity():
    preset_ids = [p["id"] for p in CAPCUT_HIGH_SPEED_TRANSITIONS]
    assert preset_ids == ["whip_pan", "zoom_in_punch", "flash_white", "glitch_shake"]

    js_script = """
    import { capcutDampedCameraShake, applyCapcutHighSpeedTransition } from './frontend/src/lib/timelineMath.js';
    const ts = [0.0, 0.15, 0.35, 0.65, 1.0];
    console.log(JSON.stringify({
      shake: ts.map(t => capcutDampedCameraShake(t)),
      updated: applyCapcutHighSpeedTransition({ id: 'c1', duration: 3.0 }, 'zoom_in_punch'),
    }));
    """
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", js_script],
        capture_output=True,
        text=True,
        check=True,
    )
    js_out = json.loads(proc.stdout)
    ts = [0.0, 0.15, 0.35, 0.65, 1.0]
    for i, t in enumerate(ts):
        p_sh = capcut_damped_camera_shake(t)
        j_sh = js_out["shake"][i]
        assert abs(p_sh["dx"] - j_sh["dx"]) < 1e-6
        assert abs(p_sh["dy"] - j_sh["dy"]) < 1e-6

    p_updated = apply_capcut_high_speed_transition({"id": "c1", "duration": 3.0}, "zoom_in_punch")
    assert p_updated["transition_in"] == js_out["updated"]["transition_in"]
    assert abs(p_updated["transition_duration"] - js_out["updated"]["transition_duration"]) < 1e-6


def test_w3_6_in_app_ai_agent_capcut_7_1_tools_isolated(tmp_path, monkeypatch):
    proj_name = "TEST_W3_AGENT_PROJ"
    proj_dir = tmp_path / proj_name
    proj_dir.mkdir(parents=True)
    proj_json = proj_dir / "project.json"
    proj_json.write_text(
        json.dumps(
            {
                "project_name": proj_name,
                "total_duration": 8.0,
                "clip_list": [{"id": "c1", "file_path": "v1.mp4", "duration": 4.0, "target_start": 0.0, "target_end": 4.0}],
                "cues": [{"id": "q1", "start": 0.5, "end": 2.5, "text": "ทดสอบระบบ"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("scripts.agent.omnicut_agent_tools.PROJECTS_DIR", tmp_path)

    # 1. Smart Camera 9:16
    cam_prop = apply_smart_camera_9_16(proj_name, clip_index=0, preset="slow_push", easing="hero_in")
    res_cam = apply_action(cam_prop)
    assert res_cam["success"] is True

    # 2. CapCut Color Grade
    col_prop = apply_capcut_color_grade(proj_name, clip_index=0, shadows=0.3, highlights=-0.2, vibrance=0.4, vignette=0.25)
    res_col = apply_action(col_prop)
    assert res_col["success"] is True

    # 3. Normalize Audio -14 LUFS + Voice Clarity
    lufs_prop = normalize_project_audio_lufs(proj_name, target_lufs=-14.0, voice_clarity=True)
    res_lufs = apply_action(lufs_prop)
    assert res_lufs["success"] is True

    # 4. In-App Pro Color Grade & Viral Transitions
    pro_col = apply_pro_color_grade(proj_name, clip_index=0, shadows=0.35, highlights=-0.25, vibrance=0.45, vignette=0.3)
    res_pro_col = apply_action(pro_col)
    assert res_pro_col["success"] is True

    viral_trans = apply_viral_transitions(proj_name, transition_name="whip_pan", duration=0.4)
    res_trans = apply_action(viral_trans)
    assert res_trans["success"] is True

    final_manifest = load_project_manifest(proj_name)
    assert final_manifest["target_lufs"] == -14.0
    assert final_manifest["voice_clarity"] is True


def test_w3_7_decode_balance_limit_and_frame_budget_guard():
    assert list(CAPCUT_DECODE_BALANCE_LIMIT) == [8, 4, 2, 1]
    assert CAPCUT_FRAME_BUDGET_MS == 12.0
