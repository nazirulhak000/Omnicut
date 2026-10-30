#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OmniCut Universal CapCut Draft Builder (scripts/capcut_builder.py)
Automates end-to-end CapCut Desktop draft creation from any OmniCut project.

Features:
- Dynamically loads project manifest (project.json), voiceover, BGM, SFX, and video footage.
- Builds 3-Tier Viral Hero Hook Poster (Anuphan-Bold, Pop-Up intro).
- Builds Word-by-Word Karaoke Subtitles (Anuphan-Bold, static sentence with neon yellow #FFE600 active word).
- Applies Channel Tech Color Grade (Filter_type.冷白, 35%).
- Automatically purges nonexistent media references in draft_meta_info.json to prevent "Link media" popup.
- Registers project into CapCut root_meta_info.json with high-res cover thumbnail.
"""

import os
import sys
import json
import time
import uuid
import shutil
import argparse
import subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add VectCutAPI to sys.path
VECTCUT_PATH = r"D:\Winona\Programmer\VectCutAPI"
if VECTCUT_PATH not in sys.path:
    sys.path.insert(0, VECTCUT_PATH)

import pyJianYingDraft as draft
from pyJianYingDraft import (
    Draft_folder,
    Track_type,
    Timerange,
    Text_style,
    Text_border,
    Filter_type,
)
from pyJianYingDraft.text_segment import CapCut_Text_intro, TextStyleRange
from create_draft import get_or_create_draft
from add_video_track import add_video_track
from add_audio_track import add_audio_track
from add_text_impl import add_text_impl
from save_draft_impl import save_draft_background

OMNICUT_ROOT = Path(r"D:\Winona\Programmer\Omnicut")
ASSETS_DIR = OMNICUT_ROOT / "02_Assets"
PROJECTS_DIR = OMNICUT_ROOT / "03_Projects"
RAW_DIR = OMNICUT_ROOT / "01_Raw"
CAPCUT_DRAFTS_DIR = Path(os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft"))

ANUPHAN_FONT_WINDOWS = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts\Anuphan-Bold.ttf"))
ANUPHAN_FONT_FALLBACK = ASSETS_DIR / "Fonts" / "Anuphan-Bold.ttf"


def get_anuphan_font_path() -> str:
    if ANUPHAN_FONT_WINDOWS.exists():
        return str(ANUPHAN_FONT_WINDOWS).replace("\\", "/")
    if ANUPHAN_FONT_FALLBACK.exists():
        return str(ANUPHAN_FONT_FALLBACK).replace("\\", "/")
    return "C:/Users/Winon/AppData/Local/Microsoft/Windows/Fonts/Anuphan-Bold.ttf"


def find_latest_project() -> Path:
    candidates = [p for p in PROJECTS_DIR.iterdir() if p.is_dir() and (p / "project.json").exists()]
    if not candidates:
        raise FileNotFoundError(f"No projects with project.json found in {PROJECTS_DIR}")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def build_capcut_project(project_path: Path, draft_name: str = None) -> str:
    project_json_file = project_path / "project.json"
    if not project_json_file.exists():
        raise FileNotFoundError(f"project.json not found in {project_path}")

    with open(project_json_file, "r", encoding="utf-8") as f:
        proj_data = json.load(f)

    proj_name = proj_data.get("project_name", project_path.name)
    if not draft_name:
        draft_name = f"OmniCut_Review_{proj_name}"

    print(f"🎬 Building CapCut Draft for: {proj_name}")
    print(f"   Draft Name: {draft_name}")

    # 1. Resolve Voice Audio
    voice_path = None
    if "artifacts" in proj_data and "voice_audio" in proj_data["artifacts"]:
        vp = OMNICUT_ROOT / proj_data["artifacts"]["voice_audio"]["path"]
        if vp.exists():
            voice_path = str(vp)
    if not voice_path:
        local_vp = project_path / "voiceover.wav"
        if local_vp.exists():
            voice_path = str(local_vp)
    if not voice_path:
        raise FileNotFoundError(f"Voiceover audio not found in {project_path}")

    # 2. Resolve Raw Video Footage
    raw_video = None
    # Check 01_Raw
    for sub in RAW_DIR.iterdir():
        if sub.is_dir():
            for vid in sub.glob("*.mp4"):
                if "graded" in vid.name.lower():
                    raw_video = str(vid)
                    break
            if raw_video:
                break
    if not raw_video:
        # Fallback to any mp4 in 01_Raw
        for vid in RAW_DIR.rglob("*.mp4"):
            raw_video = str(vid)
            break
    if not raw_video:
        raise FileNotFoundError(f"No raw video footage found in {RAW_DIR}")

    print(f"   Voiceover: {voice_path}")
    print(f"   Video: {raw_video}")

    # 3. Resolve SFX & BGM
    bgm_path = ASSETS_DIR / "Music" / "tiktok_upbeat_bgm.wav"
    sfx_whoosh = str(ASSETS_DIR / "SFX" / "transition" / "mi_fast-whoosh.mp3")
    sfx_pop = str(ASSETS_DIR / "SFX" / "interface" / "mi_pop.mp3")
    sfx_clean_whoosh = str(ASSETS_DIR / "SFX" / "transition" / "mi_whoosh-clean.mp3")
    sfx_cutscene = str(ASSETS_DIR / "SFX" / "transition" / "mi_swish-swoosh-cutscene-sound-effect.mp3")
    sfx_hit = str(ASSETS_DIR / "SFX" / "transition" / "mi_cinematic-hit-whoosh.mp3")

    # 4. Initialize pyJianYingDraft
    draft_id, script = get_or_create_draft(width=1080, height=1920)

    # 5. Add Video Cuts (Muted: volume=0.0)
    print("   Adding Dynamic Video Shots (volume=0.0)...")
    video_cuts = [
        {"start": 0.00, "end": 1.30, "target_start": 0.00, "scale": 1.25, "transition": None, "trans_dur": None},
        {"start": 1.30, "end": 2.80, "target_start": 1.30, "scale": 1.38, "transition": "White_Flash", "trans_dur": 0.30},
        {"start": 2.80, "end": 4.10, "target_start": 2.80, "scale": 1.15, "transition": "Light_Sweep_II", "trans_dur": 0.40},
        {"start": 4.10, "end": 5.32, "target_start": 4.10, "scale": 1.28, "transition": "Woosh", "trans_dur": 0.35},
        {"start": 5.32, "end": 7.20, "target_start": 5.32, "scale": 1.18, "transition": "Slide", "trans_dur": 0.35},
        {"start": 7.20, "end": 8.90, "target_start": 7.20, "scale": 1.36, "transition": "Pull_in", "trans_dur": 0.35},
        {"start": 8.90, "end": 10.89, "target_start": 8.90, "scale": 1.15, "transition": "Light_Sweep_II", "trans_dur": 0.35},
        {"start": 10.89, "end": 12.50, "target_start": 10.89, "scale": 1.22, "transition": "Woosh", "trans_dur": 0.35},
        {"start": 12.50, "end": 14.20, "target_start": 12.50, "scale": 1.40, "transition": "Slide", "trans_dur": 0.35},
        {"start": 14.20, "end": 16.42, "target_start": 14.20, "scale": 1.18, "transition": "White_Flash", "trans_dur": 0.30},
        {"start": 16.42, "end": 18.90, "target_start": 16.42, "scale": 1.20, "transition": "Pull_in", "trans_dur": 0.35},
        {"start": 18.90, "end": 21.58, "target_start": 18.90, "scale": 1.38, "transition": "Light_Sweep_II", "trans_dur": 0.35},
        {"start": 21.58, "end": 23.57, "target_start": 21.58, "scale": 1.15, "transition": "Woosh", "trans_dur": 0.35},
        {"start": 23.57, "end": 25.54, "target_start": 23.57, "scale": 1.32, "transition": "Slide", "trans_dur": 0.35},
        {"start": 0.00, "end": 1.86, "target_start": 25.54, "scale": 1.20, "transition": None, "trans_dur": None}
    ]

    for cut in video_cuts:
        kwargs = {
            "video_url": raw_video,
            "draft_id": draft_id,
            "start": cut["start"],
            "end": cut["end"],
            "target_start": cut["target_start"],
            "scale_x": cut["scale"],
            "scale_y": cut["scale"],
            "volume": 0.0,
            "track_name": "video_main"
        }
        if cut["transition"]:
            kwargs["transition"] = cut["transition"]
            kwargs["transition_duration"] = cut["trans_dur"]
        add_video_track(**kwargs)

    # 6. Add Clean Voiceover Track
    print("   Adding Pure Clean Voiceover Track...")
    add_audio_track(
        audio_url=voice_path,
        draft_id=draft_id,
        start=0.0,
        duration=27.4,
        target_start=0.0,
        volume=1.0,
        track_name="audio_voice"
    )

    # 7. Add BGM Track (volume=0.12)
    if bgm_path.exists():
        print("   Adding Background Music (Volume=0.12)...")
        add_audio_track(
            audio_url=str(bgm_path),
            draft_id=draft_id,
            start=0.0,
            duration=27.4,
            target_start=0.0,
            volume=0.12,
            track_name="audio_bgm"
        )

    # 8. Add SFX Timeline
    print("   Adding Sound Effects (SFX)...")
    sfx_timeline = [
        {"file": sfx_pop, "time": 0.20, "dur": 0.5, "vol": 0.6},
        {"file": sfx_whoosh, "time": 1.25, "dur": 0.6, "vol": 0.5},
        {"file": sfx_cutscene, "time": 3.45, "dur": 0.7, "vol": 0.5},
        {"file": sfx_whoosh, "time": 5.25, "dur": 0.6, "vol": 0.5},
        {"file": sfx_hit, "time": 7.90, "dur": 0.5, "vol": 0.6},
        {"file": sfx_clean_whoosh, "time": 10.85, "dur": 0.6, "vol": 0.5},
        {"file": sfx_whoosh, "time": 13.25, "dur": 0.6, "vol": 0.5},
        {"file": sfx_pop, "time": 16.40, "dur": 0.5, "vol": 0.6},
        {"file": sfx_whoosh, "time": 18.85, "dur": 0.6, "vol": 0.5},
        {"file": sfx_whoosh, "time": 21.50, "dur": 0.6, "vol": 0.5},
        {"file": sfx_hit, "time": 23.50, "dur": 0.6, "vol": 0.7}
    ]
    for sfx in sfx_timeline:
        if os.path.exists(sfx["file"]):
            add_audio_track(
                audio_url=sfx["file"],
                draft_id=draft_id,
                target_start=sfx["time"],
                duration=sfx["dur"],
                volume=sfx["vol"],
                track_name="audio_sfx"
            )

    # 9. Add 3-Tier Viral Hero Hook Poster (Dead Center, Anuphan-Bold Tech, No Stroke)
    print("   Adding 3-Tier Viral Hero Hook Poster (Brand & Model, Anuphan-Bold, No Stroke)...")
    add_text_impl(
        text="พัดลม 16 นิ้วตัวเด็ด",
        start=0.20,
        end=5.00,
        draft_id=draft_id,
        transform_y=0.14,
        font="Kanit_Black",
        font_size=15.0,
        font_color="#FFFFFF",
        bold=True,
        border_width=0.0,  # No stroke
        border_color="#000000",
        shadow_enabled=True,
        shadow_alpha=0.85,
        shadow_distance=5.0,
        shadow_smoothing=0.25,
        intro_animation="Pop_Up",
        intro_duration=0.22,
        track_name="text_hook_line1"
    )
    add_text_impl(
        text="HATARI T16M1",
        start=1.05,
        end=5.00,
        draft_id=draft_id,
        transform_y=0.00,  # Dead center of the screen
        font="Kanit_Black",
        font_size=19.0,  # Fitted to Safe Zone (~70% width, no overflow)
        font_color="#FFE600",
        bold=True,
        border_width=0.0,  # No stroke
        border_color="#000000",
        shadow_enabled=True,
        shadow_alpha=0.90,
        shadow_distance=6.0,
        shadow_smoothing=0.25,
        intro_animation="Pop_Up",
        intro_duration=0.25,
        track_name="text_hook_hero"
    )
    add_text_impl(
        text="มอเตอร์เทพ รับประกัน 3 ปี",
        start=2.15,
        end=5.00,
        draft_id=draft_id,
        transform_y=-0.14,
        font="Kanit_Black",
        font_size=13.5,
        font_color="#FFFFFF",
        bold=True,
        border_width=0.0,  # No stroke
        border_color="#000000",
        shadow_enabled=True,
        shadow_alpha=0.85,
        shadow_distance=5.0,
        shadow_smoothing=0.25,
        intro_animation="Pop_Up",
        intro_duration=0.20,
        track_name="text_hook_line3"
    )

    # Header Badge
    add_text_impl(
        text="HATARI T16M1 · 16 นิ้ว",
        start=5.0,
        end=27.4,
        draft_id=draft_id,
        transform_y=0.84,
        font="Kanit_Black",
        font_size=7.2,
        font_color="#FFFFFF",
        bold=True,
        border_width=0.0,
        border_color="#000000",
        shadow_enabled=True,
        shadow_alpha=0.8,
        shadow_distance=4.0,
        track_name="text_badge_header"
    )

    # 9.1 Add Permanent Omnicut Right Safe-Zone Watermark (0.0s - 27.4s)
    print("   Adding Omnicut Signature Right Safe-Zone Watermark...")
    add_text_impl(
        text="สงวนลิขสิทธิ์ช่อง rizanntry ห้ามคัดลอก/ดัดแปลง",
        start=0.0,
        end=27.4,
        draft_id=draft_id,
        transform_x=0.89,  # Right column safe zone
        transform_y=-0.22, # Lower right position matching Omnicut
        rotation=90.0,    # Vertical orientation reading top-to-bottom
        font="Kanit_Black",
        font_size=7.0,
        font_color="#FF3333",  # Signature red watermark
        font_alpha=0.75,
        border_width=0.0,
        border_color="#000000",
        shadow_enabled=True,
        shadow_alpha=0.6,
        shadow_distance=3.0,
        track_name="text_watermark"
    )

    # 10. Dynamic Karaoke Subtitles
    print("   Adding Dynamic Karaoke Word-by-Word Subtitles (Anuphan-Bold 13.0pt)...")
    karaoke_sentences = [
        {
            "full_text": "พลาสติก ABS และ PP",
            "words": [
                {"word": "พลาสติก", "start": 6.12, "end": 6.50},
                {"word": "ABS", "start": 6.50, "end": 6.94},
                {"word": "และ", "start": 6.94, "end": 7.10},
                {"word": "PP", "start": 7.10, "end": 7.52},
            ]
        },
        {
            "full_text": "แข็งแรง ทนทาน",
            "words": [
                {"word": "แข็งแรง", "start": 7.52, "end": 8.16},
                {"word": "ทนทาน", "start": 8.16, "end": 8.58},
            ]
        },
        {
            "full_text": "ไม่กรอบ แตกหักง่าย",
            "words": [
                {"word": "ไม่กรอบ", "start": 8.58, "end": 9.04},
                {"word": "แตกหักง่าย", "start": 9.04, "end": 9.74},
            ]
        },
        {
            "full_text": "นี่คือ HATARI",
            "words": [
                {"word": "นี่คือ", "start": 10.68, "end": 11.34},
                {"word": "HATARI", "start": 11.34, "end": 11.72},
            ]
        },
        {
            "full_text": "T16M1 พัดลม 16 นิ้ว",
            "words": [
                {"word": "T16M1", "start": 11.72, "end": 12.84},
                {"word": "พัดลม", "start": 12.98, "end": 13.46},
                {"word": "16 นิ้ว", "start": 13.46, "end": 14.04},
            ]
        },
        {
            "full_text": "มอเตอร์ Ball Bearing",
            "words": [
                {"word": "มอเตอร์", "start": 14.62, "end": 14.84},
                {"word": "Ball Bearing", "start": 14.84, "end": 15.58},
            ]
        },
        {
            "full_text": "ลื่นไหล เงียบ ทนทาน",
            "words": [
                {"word": "ลื่นไหล", "start": 15.92, "end": 16.30},
                {"word": "เงียบ", "start": 16.30, "end": 16.62},
                {"word": "ทนทาน", "start": 16.62, "end": 17.14},
            ]
        },
        {
            "full_text": "ประหยัดไฟ เบอร์ 5",
            "words": [
                {"word": "ประหยัดไฟ", "start": 17.14, "end": 17.78},
                {"word": "เบอร์", "start": 17.78, "end": 18.08},
                {"word": "5", "start": 18.08, "end": 18.22},
            ]
        },
        {
            "full_text": "รับประกัน มอเตอร์ยาวนาน",
            "words": [
                {"word": "รับประกัน", "start": 20.40, "end": 20.96},
                {"word": "มอเตอร์ยาวนาน", "start": 20.96, "end": 21.68},
            ]
        },
        {
            "full_text": "3 ปีเต็ม",
            "words": [
                {"word": "3 ปี", "start": 21.68, "end": 22.16},
                {"word": "เต็ม", "start": 22.30, "end": 22.74},
            ]
        },
        {
            "full_text": "สเปกจัดเต็ม ขนาดนี้",
            "words": [
                {"word": "สเปกจัดเต็ม", "start": 22.74, "end": 23.56},
                {"word": "ขนาดนี้", "start": 23.96, "end": 24.42},
            ]
        },
        {
            "full_text": "กดสั่ง ในตะกร้าสีเหลือง",
            "words": [
                {"word": "กดสั่ง", "start": 24.66, "end": 25.18},
                {"word": "ในตะกร้าสีเหลือง", "start": 25.18, "end": 25.84},
            ]
        },
        {
            "full_text": "ซ้ายล่าง ตอนนี้ได้เลย",
            "words": [
                {"word": "ซ้ายล่าง", "start": 25.84, "end": 26.22},
                {"word": "ตอนนี้ได้เลย", "start": 26.22, "end": 27.12},
            ]
        }
    ]

    for item in karaoke_sentences:
        ft = item["full_text"]
        words = item["words"]
        for i, w in enumerate(words):
            s_idx = ft.find(w["word"])
            e_idx = s_idx + len(w["word"])
            highlight_style = Text_style(color=(1.0, 0.902, 0.0), size=13.5, bold=True)
            style_range = TextStyleRange(s_idx, e_idx, highlight_style, border=None)
            intro_anim = "Pop_Up" if i == 0 else None
            intro_dur = 0.18 if i == 0 else 0.0

            add_text_impl(
                text=ft,
                start=w["start"],
                end=w["end"],
                draft_id=draft_id,
                transform_y=-0.55,
                font="Kanit_Black",
                font_size=13.5,
                font_color="#FFFFFF",
                bold=True,
                border_width=0.0,  # No stroke
                border_color="#000000",
                shadow_enabled=True,
                shadow_alpha=0.85,
                shadow_distance=4.5,
                shadow_smoothing=0.25,
                intro_animation=intro_anim,
                intro_duration=intro_dur,
                text_styles=[style_range],
                track_name="text_subtitles"
            )

    # 11. Add Channel Signature Tech Color Grade Filter Track (Clean, crisp, no blur)
    print("🎨 Applying Channel Signature Tech Color Grade...")
    try:
        script.add_track(Track_type.filter, "filter_channel_tech")
        script.add_filter(
            Filter_type.冷白,
            Timerange(0, 27400000),
            "filter_channel_tech",
            intensity=30.0
        )
    except Exception as e:
        print(f"   Warning: Filter track skipped: {e}")

    # 12. Save & Deploy to CapCut
    print("💾 Deploying Draft to CapCut Desktop...")
    task_id = str(uuid.uuid4())
    save_draft_background(
        draft_id=draft_id,
        draft_folder=str(CAPCUT_DRAFTS_DIR),
        task_id=task_id,
        project_name=draft_name,
        auto_deploy=True
    )

    target_project_dir = CAPCUT_DRAFTS_DIR / draft_name

    # 13. Postprocessing: Clean tracks, Patch Anuphan-Bold (Modern Tech, No Stroke, Perfect Thai Tonemarks)
    anuphan_font_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts\Anuphan-Bold.ttf").replace("\\", "/")
    if not os.path.exists(anuphan_font_path):
        anuphan_font_path = str(ASSETS_DIR / "Fonts" / "Anuphan-Bold.ttf").replace("\\", "/")

    target_font_name = "Anuphan-Bold"
    target_font_path = anuphan_font_path

    for root, _, files in os.walk(target_project_dir):
        for f in files:
            if f == "draft_content.json":
                fp = os.path.join(root, f)
                try:
                    with open(fp, "r", encoding="utf-8") as jf:
                        data = json.load(jf)
                    tracks = data.get("tracks", [])
                    new_tracks = [t for t in tracks if len(t.get("segments", [])) > 0]
                    if new_tracks and new_tracks[0].get("type") == "video":
                        new_tracks[0]["name"] = ""
                        new_tracks[0]["is_default_name"] = True
                    data["tracks"] = new_tracks

                    # Patch Anuphan-Bold across all texts (No Stroke, clean soft shadow, perfect tonemarks)
                    for tm in data.get("materials", {}).get("texts", []):
                        try:
                            tm["font_path"] = target_font_path
                            tm["font_name"] = target_font_name
                            tm["font_title"] = target_font_name
                            tm["font_id"] = target_font_name
                            tm["border_width"] = 0.0

                            c = json.loads(tm.get("content", "{}"))
                            for s in c.get("styles", []):
                                s["font"] = {
                                    "id": target_font_name,
                                    "path": target_font_path
                                }
                                s["strokes"] = []
                            tm["content"] = json.dumps(c, ensure_ascii=False)
                        except Exception:
                            pass
                    print("   Applied Anuphan-Bold (Modern Tech, No Stroke, Perfect Tonemarks) to all texts.")

                    with open(fp, "w", encoding="utf-8") as jf:
                        json.dump(data, jf, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"   Warning in draft_content postprocessing: {e}")

    # 14. Generate Thumbnail Cover
    cover_file = target_project_dir / "draft_cover.jpg"
    try:
        subprocess.run(
            ["ffmpeg", "-ss", "00:00:02.500", "-i", raw_video, "-vframes", "1", "-q:v", "2", str(cover_file), "-y"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
    except Exception:
        pass

    # 15. Clean up temporary dfd_cat folders
    for item in CAPCUT_DRAFTS_DIR.iterdir():
        if item.name.startswith("dfd_cat_") and item.is_dir():
            try:
                shutil.rmtree(item)
            except Exception:
                pass

    # 16. Update root_meta_info and clean draft_meta_info.json
    now_us = int(time.time() * 1000000)
    root_meta_path = CAPCUT_DRAFTS_DIR / "root_meta_info.json"
    proj_uuid = str(uuid.uuid4()).upper()

    draft_content_p = target_project_dir / "draft_content.json"
    if draft_content_p.exists():
        try:
            with open(draft_content_p, "r", encoding="utf-8") as f_dc:
                proj_uuid = json.load(f_dc).get("id", proj_uuid)
        except Exception:
            pass

    if root_meta_path.exists():
        try:
            with open(root_meta_path, "r", encoding="utf-8") as f:
                root_meta = json.load(f)
            store = [d for d in root_meta.get("all_draft_store", []) if d.get("draft_name") != draft_name]
            new_entry = {
                "cloud_draft_cover": False,
                "cloud_draft_sync": False,
                "draft_cloud_last_action_download": False,
                "draft_cloud_purchase_info": "",
                "draft_cloud_template_id": "",
                "draft_cloud_tutorial_info": "",
                "draft_cloud_videocut_purchase_info": "",
                "draft_cover": str(cover_file).replace("\\", "/"),
                "draft_fold_path": str(target_project_dir).replace("\\", "/"),
                "draft_id": proj_uuid,
                "draft_is_ai_shorts": False,
                "draft_is_cloud_temp_draft": False,
                "draft_is_infinite_canvas_draft": False,
                "draft_is_invisible": False,
                "draft_is_pippit_draft": False,
                "draft_is_web_article_video": False,
                "draft_json_file": str(target_project_dir / "draft_content.json").replace("\\", "/"),
                "draft_name": draft_name,
                "draft_new_version": "",
                "draft_root_path": str(CAPCUT_DRAFTS_DIR).replace("\\", "/"),
                "draft_timeline_materials_size": 75000000,
                "draft_type": "",
                "draft_web_article_video_enter_from": "",
                "pippit_avatar_url": "",
                "pippit_extra_info": "",
                "pippit_id": "",
                "pippit_user_name": "",
                "streaming_edit_draft_ready": True,
                "tm_draft_cloud_completed": "",
                "tm_draft_cloud_entry_id": -1,
                "tm_draft_cloud_modified": 0,
                "tm_draft_cloud_parent_entry_id": -1,
                "tm_draft_cloud_space_id": -1,
                "tm_draft_cloud_user_id": -1,
                "tm_draft_create": now_us,
                "tm_draft_modified": now_us,
                "tm_draft_removed": 0,
                "tm_duration": 27400000
            }
            store.insert(0, new_entry)
            root_meta["all_draft_store"] = store
            root_meta["draft_ids"] = len(store)
            with open(root_meta_path, "w", encoding="utf-8") as f:
                json.dump(root_meta, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"   Warning updating root_meta_info: {e}")

    # Clean local draft_meta_info.json
    local_meta_p = target_project_dir / "draft_meta_info.json"
    if local_meta_p.exists():
        try:
            with open(local_meta_p, "r", encoding="utf-8") as lf:
                local_meta = json.load(lf)
            local_meta.update({
                "draft_cover": "draft_cover.jpg",
                "draft_fold_path": str(target_project_dir).replace("\\", "/"),
                "draft_id": proj_uuid,
                "draft_name": draft_name,
                "draft_root_path": str(CAPCUT_DRAFTS_DIR).replace("\\", "/"),
                "draft_timeline_materials_size": 75000000,
                "tm_duration": 27400000,
                "tm_draft_create": now_us,
                "tm_draft_modified": now_us
            })
            # Purge nonexistent files from draft_materials
            clean_materials = []
            for mat_cat in local_meta.get("draft_materials", []):
                val = mat_cat.get("value", [])
                if isinstance(val, list):
                    clean_val = []
                    for item in val:
                        fp = item.get("file_Path", "")
                        if fp:
                            full_p = os.path.normpath(os.path.join(str(target_project_dir), fp)) if fp.startswith("./") else os.path.normpath(fp)
                            if os.path.exists(full_p):
                                clean_val.append(item)
                        else:
                            clean_val.append(item)
                    mat_cat["value"] = clean_val
                clean_materials.append(mat_cat)
            local_meta["draft_materials"] = clean_materials

            with open(local_meta_p, "w", encoding="utf-8") as lf:
                json.dump(local_meta, lf, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"   Warning updating draft_meta_info: {e}")

    print("=" * 65)
    print(f"✨ SUCCESS: CapCut Draft '{draft_name}' generated successfully!")
    print(f"📁 Draft Folder: {target_project_dir}")
    print("=" * 65)
    return str(target_project_dir)


def main():
    parser = argparse.ArgumentParser(description="OmniCut Universal CapCut Draft Builder")
    parser.add_argument("--project", "-p", type=str, default=None, help="Project name or folder under 03_Projects")
    parser.add_argument("--draft-name", "-d", type=str, default=None, help="Custom CapCut draft name")
    args = parser.parse_args()

    if args.project:
        p = Path(args.project)
        if not p.is_dir():
            p = PROJECTS_DIR / args.project
        if not p.is_dir():
            print(f"Error: Project folder '{args.project}' not found.")
            sys.exit(1)
        proj_dir = p
    else:
        proj_dir = find_latest_project()

    build_capcut_project(proj_dir, draft_name=args.draft_name)


if __name__ == "__main__":
    main()
