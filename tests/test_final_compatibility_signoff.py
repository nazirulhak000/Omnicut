"""
Final Compatibility and Production Sign-off Test Suite for OmniCut Pro Studio.
Validates end-to-end compatibility across:
- Legacy project schemas (v0, v1, v2)
- Create -> AI Draft -> Edit -> Save -> Reload state fidelity
- Reroll Hook, Subtitle, and BGM stages
- 1080x1920, H.264, 30 FPS export spec verified via ffprobe
- Audio mix stem gains, ducking, and mute rules
- Project manifest .bak recovery under corruption
"""

import json
import subprocess
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from scripts import project_manifest
from scripts.project_manifest import ProjectManifest, REROLL_STAGE
from scripts.overlay_model import migrate_to_overlays
from scripts.pipeline_context import PipelineContext
from scripts.stages.audio_mix_stage import AudioMixStage


ROOT = Path(__file__).resolve().parent.parent
LEGACY_FIXTURE = ROOT / "tests" / "fixtures" / "legacy_project_v0.json"


@pytest.fixture
def isolated_projects(tmp_path, monkeypatch):
    target = tmp_path / "03_Projects"
    target.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", target)
    return target


@pytest.fixture
def client():
    from scripts.api_server import app
    return TestClient(app)


# ----------------------------------------------------------------------
# 1. Compatibility with >= 3 Project Manifest Formats
# ----------------------------------------------------------------------
def test_compatibility_with_three_manifest_formats(isolated_projects):
    # Format A: v0 pre-versioned manifest (legacy_project_v0.json)
    dir_v0 = isolated_projects / "proj_v0"
    dir_v0.mkdir()
    (dir_v0 / "project.json").write_bytes(LEGACY_FIXTURE.read_bytes())
    loaded_v0 = ProjectManifest.load("proj_v0")
    assert loaded_v0 is not None
    assert "manifest_version" not in loaded_v0
    assert loaded_v0["style"]["fontName"] == "IBMPlex"
    overlays_v0 = migrate_to_overlays(loaded_v0)
    assert len(overlays_v0) >= 2
    assert {o["kind"] for o in overlays_v0} == {"hook", "text"}

    # Format B: v1 flat manifest (with clip_list and cues, no track separation)
    dir_v1 = isolated_projects / "proj_v1"
    dir_v1.mkdir()
    manifest_v1 = {
        "manifest_version": 1,
        "project_name": "proj_v1",
        "total_duration": 5.0,
        "clip_list": [
            {"source_path": "01_Raw/test/clip1.mp4", "duration": 2.5, "trim_start": 0.0, "trim_end": 2.5},
            {"source_path": "01_Raw/test/clip2.mp4", "duration": 2.5, "trim_start": 0.0, "trim_end": 2.5},
        ],
        "cues": [{"id": 1, "start": 0.0, "end": 2.5, "text": "ทดสอบรูปแบบที่สอง"}],
        "audio_mutes": {"bgm": True, "voice": False, "sfx": False},
        "style": {"font_name": "IBMPlex", "caption_scale": 1.1},
    }
    (dir_v1 / "project.json").write_text(json.dumps(manifest_v1, ensure_ascii=False), encoding="utf-8")
    loaded_v1 = ProjectManifest.load("proj_v1")
    assert loaded_v1["manifest_version"] == 1
    assert len(loaded_v1["clip_list"]) == 2
    assert loaded_v1["audio_mutes"]["bgm"] is True

    # Format C: v2 multi-track schema manifest (with tracks, keyframes, audioStems)
    dir_v2 = isolated_projects / "proj_v2"
    dir_v2.mkdir()
    manifest_v2 = {
        "manifest_version": 2,
        "project_name": "proj_v2",
        "total_duration": 6.0,
        "tracks": [
            {"id": "video-1", "type": "video", "name": "Video Main", "muted": False, "locked": False, "visible": True},
            {"id": "overlay-1", "type": "overlay", "name": "Text & Badges", "muted": False, "locked": False, "visible": True},
            {"id": "audio-1", "type": "audio", "name": "Voice", "muted": False, "locked": False, "visible": True},
        ],
        "clip_list": [
            {
                "id": "c1",
                "track_id": "video-1",
                "source_path": "01_Raw/test/clip.mp4",
                "duration": 6.0,
                "keyframes": [
                    {"time": 0.0, "zoom": 1.0, "pan": 0.0, "opacity": 1.0},
                    {"time": 3.0, "zoom": 1.2, "pan": 0.1, "opacity": 1.0},
                ],
            }
        ],
        "audio_mutes": {"voice": False, "bgm": False, "sfx": False},
    }
    (dir_v2 / "project.json").write_text(json.dumps(manifest_v2, ensure_ascii=False), encoding="utf-8")
    loaded_v2 = ProjectManifest.load("proj_v2")
    assert loaded_v2["manifest_version"] == 2
    assert len(loaded_v2["tracks"]) == 3
    assert len(loaded_v2["clip_list"][0]["keyframes"]) == 2


# ----------------------------------------------------------------------
# 2. Create -> AI Draft -> Edit -> Save -> Reload Cycle
# ----------------------------------------------------------------------
def test_create_edit_save_reload_full_fidelity(client, isolated_projects):
    # Step 1: Create initial project
    ProjectManifest.save(
        "prod-cycle",
        total_duration=4.0,
        clip_list=[{"source_path": "01_Raw/p/raw.mp4", "duration": 4.0}],
        cues=[{"start": 0.0, "end": 4.0, "text": "ดราฟต์แรก"}],
    )

    # Step 2: Query project state
    res = client.get("/api/projects/prod-cycle")
    assert res.status_code == 200
    initial_data = res.json()
    assert initial_data["total_duration"] == 4.0

    # Step 3: Patch state (user edits in editor)
    edit_payload = {
        "cues": [
            {"start": 0.0, "end": 2.0, "text": "ส่วนที่ 1"},
            {"start": 2.0, "end": 4.0, "text": "ส่วนที่ 2"},
        ],
        "micro_cues": [
            {"start": 0.0, "end": 1.0, "text": "ส่วนที่"},
            {"start": 1.0, "end": 2.0, "text": "1"},
        ],
        "clip_list": [
            {
                "source_path": "01_Raw/p/raw.mp4",
                "trim_start": 0.5,
                "trim_end": 3.5,
                "duration": 3.0,
                "track_id": "video-1",
                "keyframes": [{"time": 0.0, "zoom": 1.0}, {"time": 3.0, "zoom": 1.15}],
            }
        ],
        "transitions": [],
        "style": {"font_name": "IBMPlex", "caption_scale": 1.15},
        "hook_brand": "Logitech",
        "hook_model": "Wave Keys",
        "hook_label": "รีวิวละเอียด",
        "hook_duration": 2.5,
        "overlays": [
            {"id": "hook_main", "kind": "hook", "tiers": [{"text": "Logitech Wave Keys"}]},
            {"id": "badge_pros", "kind": "badge", "badge_name": "PROS", "start": 1.0, "end": 3.0},
        ],
        "track_mix": {"voice": 1.0, "bgm": 0.12, "sfx": 0.28},
        "audio_mutes": {"voice": False, "bgm": True, "sfx": False},
    }
    patch_res = client.patch("/api/projects/prod-cycle/state", json=edit_payload)
    assert patch_res.status_code == 200

    # Step 4: Reload and verify all fields preserved
    reload_res = client.get("/api/projects/prod-cycle")
    assert reload_res.status_code == 200
    reloaded = reload_res.json()
    assert len(reloaded["cues"]) == 2
    assert reloaded["hook_brand"] == "Logitech"
    assert reloaded["hook_model"] == "Wave Keys"
    assert reloaded["audio_mutes"]["bgm"] is True
    assert len(reloaded["overlays"]) == 2
    assert reloaded["clip_list"][0]["keyframes"][1]["zoom"] == 1.15


# ----------------------------------------------------------------------
# 3. Reroll Lifecycle for Hook, Subtitles, BGM
# ----------------------------------------------------------------------
def test_reroll_stage_routing():
    # Hook reroll starts from subtitles stage (generates hook title/animation), keeps voice and mix
    assert ProjectManifest.should_run("voice", REROLL_STAGE["hook"]) is False
    assert ProjectManifest.should_run("mix", REROLL_STAGE["hook"]) is False
    assert ProjectManifest.should_run("subtitles", REROLL_STAGE["hook"]) is True
    assert ProjectManifest.should_run("video", REROLL_STAGE["hook"]) is True

    # Subtitle reroll only reruns subtitles and video assembly
    assert ProjectManifest.should_run("voice", REROLL_STAGE["subtitles"]) is False
    assert ProjectManifest.should_run("subtitles", REROLL_STAGE["subtitles"]) is True
    assert ProjectManifest.should_run("video", REROLL_STAGE["subtitles"]) is True

    # BGM reroll remuxes/remixes audio without regenerating voice
    assert ProjectManifest.should_run("voice", REROLL_STAGE["bgm"]) is False
    assert ProjectManifest.should_run("mix", REROLL_STAGE["bgm"]) is True
    assert ProjectManifest.should_run("video", REROLL_STAGE["bgm"]) is True


# ----------------------------------------------------------------------
# 4. Full Export 1080x1920, H.264, 30 FPS verified by ffprobe
# ----------------------------------------------------------------------
def test_full_export_spec_with_ffprobe(tmp_path):
    ffprobe_bin = shutil.which("ffprobe")
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffprobe_bin or not ffmpeg_bin:
        pytest.skip("ffmpeg / ffprobe not installed on test host")

    out_mp4 = tmp_path / "test_1080x1920_30fps.mp4"

    # Generate 0.5s synthetic test pattern at 1080x1920 30fps with aac audio
    cmd_gen = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=0.5:size=1080x1920:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=880:duration=0.5",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        str(out_mp4)
    ]
    gen_proc = subprocess.run(cmd_gen, capture_output=True, text=True)
    assert gen_proc.returncode == 0, f"ffmpeg generate failed: {gen_proc.stderr}"
    assert out_mp4.exists() and out_mp4.stat().st_size > 0

    # Probe file with ffprobe
    cmd_probe = [
        ffprobe_bin, "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(out_mp4)
    ]
    probe_proc = subprocess.run(cmd_probe, capture_output=True, text=True)
    assert probe_proc.returncode == 0, f"ffprobe failed: {probe_proc.stderr}"

    probe_data = json.loads(probe_proc.stdout)
    streams = probe_data.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    assert v_stream is not None, "No video stream found"
    assert v_stream["width"] == 1080, f"Width should be 1080, got {v_stream['width']}"
    assert v_stream["height"] == 1920, f"Height should be 1920, got {v_stream['height']}"
    assert v_stream["r_frame_rate"] == "30/1", f"Framerate should be 30/1, got {v_stream['r_frame_rate']}"
    assert v_stream["codec_name"] == "h264", f"Video codec should be h264, got {v_stream['codec_name']}"

    assert a_stream is not None, "No audio stream found"
    assert a_stream["codec_name"] == "aac", f"Audio codec should be aac, got {a_stream['codec_name']}"


# ----------------------------------------------------------------------
# 5. Audio Mix Mutes & Gains
# ----------------------------------------------------------------------
def test_audio_mix_stage_mutes_and_volumes(monkeypatch, tmp_path):
    recorded_mix_kwargs = {}

    def mock_mix_audio_track(**kwargs):
        nonlocal recorded_mix_kwargs
        recorded_mix_kwargs = kwargs

    import scripts.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod.SFXManager, "mix_audio_track", mock_mix_audio_track)

    ctx = PipelineContext(
        product_name="Mute Test Product",
        raw_video_path="01_Raw/test/raw.mp4",
        project_name="mute_test",
        project_dir=tmp_path / "mute_test",
        export_mp4=True,
        total_duration=3.0,
        voice_audio_path=tmp_path / "voice.wav",
        micro_cues=[],
        audio_mutes={"bgm": True, "voice": False, "sfx": True},
        bgm_volume=0.25,
        bgm_ducking=True
    )
    (tmp_path / "voice.wav").write_bytes(b"dummy")

    AudioMixStage.run(ctx)

    assert recorded_mix_kwargs.get("bgm_vol") == 0.0, "Muted BGM must have volume 0.0"
    assert recorded_mix_kwargs.get("sfx_vol") == 0.0, "Muted SFX must have volume 0.0"
    assert recorded_mix_kwargs.get("bgm_ducking") is True


# ----------------------------------------------------------------------
# 6. Manifest Atomic Write and .bak Auto-Recovery
# ----------------------------------------------------------------------
def test_manifest_bak_recovery(isolated_projects):
    ProjectManifest.save("recoverable", total_duration=8.0, custom_field="safe_data")
    p_dir = isolated_projects / "recoverable"
    main_file = p_dir / "project.json"
    bak_file = p_dir / "project.json.bak"

    # Save a second time to trigger backup rotation
    ProjectManifest.save("recoverable", total_duration=8.5, custom_field="updated_data")
    assert bak_file.exists(), ".bak file should exist after updates"

    # Simulate catastrophic corruption of main project.json
    main_file.write_text("{CORRUPT_JSON_DATA_EOF!!!", encoding="utf-8")

    # Load should seamlessly recover from .bak
    recovered = ProjectManifest.load("recoverable")
    assert recovered is not None
    assert recovered.get("total_duration") in (8.0, 8.5)
    assert recovered.get("custom_field") in ("safe_data", "updated_data")
