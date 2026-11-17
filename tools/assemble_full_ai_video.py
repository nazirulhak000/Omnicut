"""
Assemble Full AI Video Script for OmniCut Pro Studio.
Combines all 5 pure AI Veo B-roll clips from Google Flow with Fenrir TTS voiceover,
Kinetic bilingual subtitles, TikTok upbeat BGM (0.12), and SFX into a 1080x1920 9:16 video.
"""

import sys
import json
import hashlib
import datetime
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.config import BASE_DIR, RAW_DIR, EXPORTS_DIR, PROJECTS_DIR
from scripts.video_editor import VideoEditor
from scripts.project_manifest import ProjectManifest
from scripts.export_registry import ExportRegistry


def assemble_full_ai_video():
    product_id = "431165f167284094959bdf0f0e806899"
    project_name = "ESS04-ปัญหาก่อนใช้_1"
    ai_flow_dir = RAW_DIR / product_id / "AI_Flow"
    project_dir = PROJECTS_DIR / project_name

    # 1. Pinned 5 AI Flow clips
    shot1_file = ai_flow_dir / "flow_20261114_225938_scene-02.mp4"
    shot2_file = ai_flow_dir / "flow_20261114_233050_scene-01.mp4"
    shot3_file = ai_flow_dir / "flow_20261114_233258_scene-02.mp4"
    shot4_file = ai_flow_dir / "flow_20261114_233539_scene-03.mp4"
    shot5_file = ai_flow_dir / "flow_20261114_233744_scene-04.mp4"

    raw_clips = [shot1_file, shot2_file, shot3_file, shot4_file, shot5_file]
    for idx, c in enumerate(raw_clips):
        if not c.is_file():
            raise FileNotFoundError(f"Missing clip {idx+1}: {c}")
        print(f"  Shot {idx + 1}: {c.name} ({c.stat().st_size:,} bytes)")

    # 2. Timing based on beat cues
    # Beat durations: 4.796, 4.796, 5.729, 5.396, 5.0748
    mixed_audio = project_dir / "mixed_audio_v1.wav"
    ass_subtitle = project_dir / "subtitles_v1.ass"
    if not mixed_audio.exists():
        raise FileNotFoundError(f"Mixed audio not found: {mixed_audio}")
    if not ass_subtitle.exists():
        raise FileNotFoundError(f"Subtitles not found: {ass_subtitle}")

    total_duration = 25.35

    clip_list = [
        {
            "source_path": str(shot1_file),
            "trim_start": 0.0,
            "trim_end": 4.796,
            "duration": 4.796,
            "speed": 1.0,
            "zoom": 1.05,
            "shot_index": 0,
            "track_id": "video-1",
            "keyframes": [
                {"time": 0.0, "zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0},
                {"time": 4.796, "zoom": 1.1, "pan_x": 0.02, "pan_y": 0.0, "easing": "ease_out"},
            ],
            "transition_in": "cut",
            "pan_x": 0.0,
            "pan_y": 0.0,
        },
        {
            "source_path": str(shot2_file),
            "trim_start": 0.0,
            "trim_end": 4.796,
            "duration": 4.796,
            "speed": 1.0,
            "zoom": 1.05,
            "shot_index": 1,
            "track_id": "video-1",
            "keyframes": [
                {"time": 0.0, "zoom": 1.05, "pan_x": -0.02, "pan_y": 0.0},
                {"time": 4.796, "zoom": 1.15, "pan_x": 0.02, "pan_y": 0.0, "easing": "ease_out"},
            ],
            "transition_in": "cut",
            "pan_x": 0.0,
            "pan_y": 0.0,
        },
        {
            "source_path": str(shot3_file),
            "trim_start": 0.0,
            "trim_end": 5.729,
            "duration": 5.729,
            "speed": 1.0,
            "zoom": 1.05,
            "shot_index": 2,
            "track_id": "video-1",
            "keyframes": [
                {"time": 0.0, "zoom": 1.1, "pan_x": 0.0, "pan_y": 0.0},
                {"time": 5.729, "zoom": 1.25, "pan_x": 0.0, "pan_y": -0.02, "easing": "ease_out"},
            ],
            "transition_in": "cut",
            "pan_x": 0.0,
            "pan_y": 0.0,
        },
        {
            "source_path": str(shot4_file),
            "trim_start": 0.0,
            "trim_end": 5.396,
            "duration": 5.396,
            "speed": 1.0,
            "zoom": 1.05,
            "shot_index": 3,
            "track_id": "video-1",
            "keyframes": [
                {"time": 0.0, "zoom": 1.0, "pan_x": -0.04, "pan_y": 0.0},
                {"time": 5.396, "zoom": 1.15, "pan_x": 0.04, "pan_y": 0.0, "easing": "ease_out"},
            ],
            "transition_in": "cut",
            "pan_x": 0.0,
            "pan_y": 0.0,
        },
        {
            "source_path": str(shot5_file),
            "trim_start": 0.0,
            "trim_end": 4.633,
            "duration": 4.633,
            "speed": 1.0,
            "zoom": 1.05,
            "shot_index": 4,
            "track_id": "video-1",
            "keyframes": [
                {"time": 0.0, "zoom": 1.05, "pan_x": 0.0, "pan_y": 0.0},
                {"time": 4.633, "zoom": 1.15, "pan_x": 0.0, "pan_y": 0.02, "easing": "ease_out"},
            ],
            "transition_in": "cut",
            "pan_x": 0.0,
            "pan_y": 0.0,
        },
    ]

    transitions = [
        {"type": "cut", "duration": 0.0},
        {"type": "cut", "duration": 0.0},
        {"type": "cut", "duration": 0.0},
        {"type": "cut", "duration": 0.0},
    ]

    # Output directory per Rule 4.2
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_mp4 = EXPORTS_DIR / f"{timestamp}_สายชาร์จเร็ว_Essager_100W_pain_point_AI_Veo_v1.mp4"

    print(f"Starting Video Assembly -> {out_mp4.name} ...")
    start_t = datetime.datetime.now()

    editor = VideoEditor()
    res = editor.assemble_tiktok_video(
        raw_video_paths=[str(p) for p in raw_clips],
        total_duration=total_duration,
        mixed_audio_path=str(mixed_audio),
        ass_subtitle_path=str(ass_subtitle),
        output_mp4_path=str(out_mp4),
        clip_list=clip_list,
        transitions=transitions,
        style_preset="pain_punch",
        export_preset="post",
    )

    elapsed = (datetime.datetime.now() - start_t).total_seconds()
    print(f"Video assembly finished in {elapsed:.2f}s!")
    print(f"Output MP4: {res}")

    # Register in ExportRegistry and ProductStore
    export_entry = ExportRegistry.ensure(
        path=out_mp4,
        product_id=product_id,
        angle_id="pain_point",
        project_name=project_name,
        status="rendered",
    )
    from scripts.product_store import ProductStore
    ProductStore.update_angle(
        product_id,
        "pain_point",
        export_id=export_entry["export_id"],
        video_url=str(out_mp4.relative_to(BASE_DIR)).replace("\\", "/"),
        status="rendered",
    )
    from scripts.cover_service import ensure_default_cover
    ensure_default_cover(
        export_id=export_entry["export_id"],
        product_id=product_id,
        angle_id="pain_point",
    )
    print(f"Registered export: {export_entry['export_id']}")
    return res


if __name__ == "__main__":
    assemble_full_ai_video()
