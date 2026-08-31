"""
Perfect CapCut Project Builder
Builds 100% native CapCut Desktop 9.x projects with real cover thumbnails,
exact material schemas, tracks, and root_meta_info.json integration.
"""

import os
import sys
import json
import uuid
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import CAPCUT_DRAFT_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, FPS, ASSETS_DIR, MUSIC_DIR, SFX_DIR

TEMPLATE_DRAFT_DIR = CAPCUT_DRAFT_DIR / "0812(1)"
CAPCUT_EXE = Path(os.environ.get("LOCALAPPDATA", "")) / "CapCut" / "Apps" / "CapCut.exe"

class PerfectCapCutBuilder:
    @staticmethod
    def _gen_id() -> str:
        return str(uuid.uuid4()).upper()

    @classmethod
    def generate(
        cls,
        project_name: str,
        raw_video_path: str,
        voice_audio_path: str,
        cues: List[Dict],
        total_duration: float,
        bgm_path: Optional[str] = None,
        hook_title: Optional[str] = None
    ) -> str:
        raw_video = Path(raw_video_path).resolve()
        voice_audio = Path(voice_audio_path).resolve()
        draft_folder = CAPCUT_DRAFT_DIR / project_name
        draft_folder.mkdir(parents=True, exist_ok=True)

        norm_folder = str(draft_folder).replace("\\", "/")
        norm_raw = str(raw_video).replace("\\", "/")
        norm_voice = str(voice_audio).replace("\\", "/")
        
        total_duration_us = int(total_duration * 1_000_000)
        video_size = raw_video.stat().st_size if raw_video.exists() else 100_000_000

        # 1. Extract Real Video Frame for draft_cover.jpg
        cover_path = draft_folder / "draft_cover.jpg"
        try:
            cmd = [
                "ffmpeg", "-y", "-ss", "00:00:01.5",
                "-i", str(raw_video),
                "-vframes", "1",
                "-q:v", "2",
                str(cover_path)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            print(f"   ✓ Extracted cover thumbnail: {cover_path}")
        except Exception as e:
            print(f"   Notice: ffmpeg cover extract fallback: {e}")

        # 2. Materials
        video_mat_id = cls._gen_id()
        voice_mat_id = cls._gen_id()
        bgm_mat_id = cls._gen_id() if bgm_path else None
        speed_mat_id = cls._gen_id()
        canvas_mat_id = cls._gen_id()
        color_mat_id = cls._gen_id()

        materials = {
            "videos": [
                {
                    "id": video_mat_id,
                    "path": norm_raw,
                    "type": "video",
                    "duration": total_duration_us * 3,
                    "width": VIDEO_WIDTH,
                    "height": VIDEO_HEIGHT,
                    "material_name": raw_video.name
                }
            ],
            "audios": [
                {
                    "id": voice_mat_id,
                    "path": norm_voice,
                    "type": "audio",
                    "duration": total_duration_us,
                    "name": "voiceover.wav"
                }
            ],
            "speeds": [
                {
                    "id": speed_mat_id,
                    "mode": 0,
                    "speed": 1.0,
                    "type": "speed"
                }
            ],
            "canvases": [
                {
                    "id": canvas_mat_id,
                    "type": "canvas_color",
                    "color": "",
                    "blur": 0.0,
                    "image": "",
                    "album_image": "",
                    "image_id": "",
                    "image_name": "",
                    "source_platform": 0,
                    "team_id": ""
                }
            ],
            "material_colors": [
                {
                    "id": color_mat_id,
                    "is_color_clip": False,
                    "is_gradient": False,
                    "solid_color": "",
                    "gradient_colors": [],
                    "gradient_percents": [],
                    "gradient_angle": 90.0,
                    "width": 0.0,
                    "height": 0.0
                }
            ],
            "texts": [],
            "transitions": [],
            "stickers": [],
            "sound_channel_mappings": []
        }

        if bgm_path and Path(bgm_path).exists():
            materials["audios"].append({
                "id": bgm_mat_id,
                "path": str(Path(bgm_path).resolve()).replace("\\", "/"),
                "type": "audio",
                "duration": total_duration_us,
                "name": Path(bgm_path).name
            })

        # SFX Materials
        sfx_boom_path = SFX_DIR / "sfx_vine_boom.wav"
        sfx_pop_path = SFX_DIR / "sfx_pop_bubble.wav"
        sfx_cash_path = SFX_DIR / "sfx_cash_register.wav"

        def _add_sfx(p: Path, name: str) -> Optional[str]:
            if p.exists():
                mid = cls._gen_id()
                materials["audios"].append({
                    "id": mid,
                    "path": str(p.resolve()).replace("\\", "/"),
                    "type": "audio",
                    "duration": 1_000_000,
                    "name": name
                })
                return mid
            return None

        sfx_boom_id = _add_sfx(sfx_boom_path, "sfx_boom.wav")
        sfx_pop_id = _add_sfx(sfx_pop_path, "sfx_pop.wav")
        sfx_cash_id = _add_sfx(sfx_cash_path, "sfx_cash.wav")

        # 3. Segments
        video_segments = []
        text_segments = []
        sfx_segments = []

        shot_scales = [1.20, 1.0, 1.30, 1.05]
        for idx, cue in enumerate(cues):
            start_us = int(cue["start"] * 1_000_000)
            end_us = int(cue["end"] * 1_000_000)
            dur_us = max(100_000, end_us - start_us)
            src_start_us = int(((idx * 2.5) % 30.0) * 1_000_000)

            # Video segment
            scale = shot_scales[idx % len(shot_scales)]
            v_seg_id = cls._gen_id()
            video_segments.append({
                "id": v_seg_id,
                "material_id": video_mat_id,
                "source_timerange": {"start": src_start_us, "duration": dur_us},
                "target_timerange": {"start": start_us, "duration": dur_us},
                "speed": 1.0,
                "volume": 0.0,
                "clip": {
                    "scale": {"x": scale, "y": scale},
                    "rotation": 0.0,
                    "transform": {"x": 0.0, "y": 0.0},
                    "flip": {"vertical": False, "horizontal": False},
                    "alpha": 1.0
                },
                "extra_material_refs": [speed_mat_id, canvas_mat_id, color_mat_id],
                "render_index": 0
            })

            # Subtitle segment
            text_mat_id = cls._gen_id()
            text_str = cue["text"]
            
            # CapCut inner text style object
            inner_content = {
                "styles": [
                    {
                        "fill": {
                            "alpha": 1.0,
                            "content": {
                                "render_type": "solid",
                                "solid": {"alpha": 1.0, "color": [1.0, 1.0, 1.0]}
                            }
                        },
                        "font": {
                            "id": "",
                            "path": "C:/Users/Winon/AppData/Local/CapCut/Apps/9.2.0.3931/Resources/Font/SystemFont/en.ttf"
                        },
                        "range": [0, len(text_str)],
                        "size": 13.0,
                        "strokes": [
                            {
                                "alpha": 1.0,
                                "content": {
                                    "render_type": "solid",
                                    "solid": {"alpha": 1.0, "color": [0.0, 0.0, 0.0]}
                                },
                                "width": 0.08
                            }
                        ],
                        "useLetterColor": True
                    }
                ],
                "text": text_str
            }

            materials["texts"].append({
                "id": text_mat_id,
                "type": "subtitle",
                "content": json.dumps(inner_content, ensure_ascii=False),
                "text_color": "#ffffff",
                "border_color": "#000000",
                "border_width": 0.08,
                "border_alpha": 1.0,
                "font_size": 13.0,
                "alignment": 1,
                "layer_weight": 1
            })

            t_seg_id = cls._gen_id()
            text_segments.append({
                "id": t_seg_id,
                "material_id": text_mat_id,
                "target_timerange": {"start": start_us, "duration": dur_us},
                "clip": {
                    "scale": {"x": 1.4, "y": 1.4},
                    "rotation": 0.0,
                    "transform": {"x": 0.0, "y": -0.72},
                    "flip": {"vertical": False, "horizontal": False},
                    "alpha": 1.0
                },
                "render_index": 14000 + idx
            })

            # SFX triggers
            if idx == 0 and sfx_boom_id:
                sfx_segments.append({
                    "id": cls._gen_id(),
                    "material_id": sfx_boom_id,
                    "source_timerange": {"start": 0, "duration": 800_000},
                    "target_timerange": {"start": 0, "duration": 800_000},
                    "volume": 0.8
                })
            elif idx == len(cues) - 1 and sfx_cash_id:
                sfx_segments.append({
                    "id": cls._gen_id(),
                    "material_id": sfx_cash_id,
                    "source_timerange": {"start": 0, "duration": 1_000_000},
                    "target_timerange": {"start": start_us, "duration": 1_000_000},
                    "volume": 0.85
                })
            elif sfx_pop_id and idx % 2 == 1:
                sfx_segments.append({
                    "id": cls._gen_id(),
                    "material_id": sfx_pop_id,
                    "source_timerange": {"start": 0, "duration": 200_000},
                    "target_timerange": {"start": start_us, "duration": 200_000},
                    "volume": 0.6
                })

        # Voice track
        voice_segment = {
            "id": cls._gen_id(),
            "material_id": voice_mat_id,
            "source_timerange": {"start": 0, "duration": total_duration_us},
            "target_timerange": {"start": 0, "duration": total_duration_us},
            "volume": 1.0
        }

        # 4. Tracks
        tracks = [
            {
                "id": cls._gen_id(),
                "type": "video",
                "segments": video_segments,
                "flag": 0
            },
            {
                "id": cls._gen_id(),
                "type": "text",
                "segments": text_segments,
                "flag": 0
            },
            {
                "id": cls._gen_id(),
                "type": "audio",
                "segments": [voice_segment],
                "flag": 0
            }
        ]

        if sfx_segments:
            tracks.append({
                "id": cls._gen_id(),
                "type": "audio",
                "segments": sfx_segments,
                "flag": 0
            })

        if bgm_mat_id:
            bgm_segment = {
                "id": cls._gen_id(),
                "material_id": bgm_mat_id,
                "source_timerange": {"start": 0, "duration": total_duration_us},
                "target_timerange": {"start": 0, "duration": total_duration_us},
                "volume": 0.15
            }
            tracks.append({
                "id": cls._gen_id(),
                "type": "audio",
                "segments": [bgm_segment],
                "flag": 0
            })

        # 5. Draft Content JSON
        draft_content = {
            "id": cls._gen_id(),
            "version": 360000,
            "new_version": "181.0.0",
            "name": project_name,
            "duration": total_duration_us,
            "create_time": int(time.time()),
            "update_time": int(time.time()),
            "fps": FPS,
            "canvas_config": {
                "width": VIDEO_WIDTH,
                "height": VIDEO_HEIGHT,
                "ratio": "9:16"
            },
            "materials": materials,
            "tracks": tracks
        }

        # 6. Draft Meta Info JSON
        now_us = int(time.time() * 1_000_000)
        meta_info = {
            "cloud_draft_cover": False,
            "cloud_draft_sync": False,
            "draft_cover": "draft_cover.jpg",
            "draft_fold_path": norm_folder,
            "draft_id": draft_content["id"],
            "draft_materials": [
                {
                    "type": 0,
                    "value": [
                        {
                            "ai_group_type": "",
                            "create_time": int(time.time()),
                            "duration": total_duration_us,
                            "enter_from": 0,
                            "extra_info": raw_video.name,
                            "file_Path": norm_raw,
                            "height": 1920,
                            "id": cls._gen_id().lower(),
                            "import_time": int(time.time()),
                            "import_time_ms": now_us,
                            "item_source": 1,
                            "material_color_tag": "",
                            "md5": "",
                            "metetype": "video",
                            "roughcut_time_range": {"duration": total_duration_us, "start": 0},
                            "sub_time_range": {"duration": -1, "start": -1},
                            "type": 0,
                            "width": 1080
                        }
                    ]
                }
            ],
            "draft_name": project_name,
            "draft_new_version": "181.0.0",
            "draft_root_path": str(CAPCUT_DRAFT_DIR).replace("\\", "/"),
            "draft_timeline_materials_size_": video_size,
            "tm_draft_create": now_us,
            "tm_draft_modified": now_us,
            "tm_draft_removed": 0,
            "tm_duration": total_duration_us
        }

        # Save files
        with open(draft_folder / "draft_content.json", "w", encoding="utf-8") as f:
            json.dump(draft_content, f, ensure_ascii=False, indent=2)

        with open(draft_folder / "draft_meta_info.json", "w", encoding="utf-8") as f:
            json.dump(meta_info, f, ensure_ascii=False, indent=2)

        # 7. Update root_meta_info.json
        root_meta_file = CAPCUT_DRAFT_DIR / "root_meta_info.json"
        entry = {
            "cloud_draft_cover": False,
            "cloud_draft_sync": False,
            "draft_cloud_last_action_download": False,
            "draft_cloud_purchase_info": "",
            "draft_cloud_template_id": "",
            "draft_cloud_tutorial_info": "",
            "draft_cloud_videocut_purchase_info": "",
            "draft_cover": f"{norm_folder}/draft_cover.jpg",
            "draft_fold_path": norm_folder,
            "draft_id": draft_content["id"],
            "draft_is_ai_shorts": False,
            "draft_is_cloud_temp_draft": False,
            "draft_is_invisible": False,
            "draft_is_pippit_draft": False,
            "draft_is_web_article_video": False,
            "draft_json_file": f"{norm_folder}/draft_content.json",
            "draft_name": project_name,
            "draft_new_version": "181.0.0",
            "draft_root_path": str(CAPCUT_DRAFT_DIR).replace("\\", "/"),
            "draft_timeline_materials_size": video_size,
            "draft_type": "",
            "draft_web_article_video_enter_from": "",
            "pippit_avatar_url": "",
            "pippit_extra_info": "",
            "pippit_id": "",
            "pippit_user_name": "",
            "streaming_edit_draft_ready": True,
            "tm_draft_create": now_us,
            "tm_draft_modified": now_us,
            "tm_draft_removed": 0,
            "tm_duration": total_duration_us
        }

        try:
            if root_meta_file.exists():
                with open(root_meta_file, "r", encoding="utf-8") as f:
                    root_data = json.load(f)
            else:
                root_data = {"all_draft_store": [], "draft_ids": 1, "root_path": str(CAPCUT_DRAFT_DIR).replace("\\", "/")}

            existing = [item for item in root_data.get("all_draft_store", []) if item.get("draft_name") != project_name]
            existing.insert(0, entry)
            root_data["all_draft_store"] = existing
            root_data["draft_ids"] = len(existing)

            with open(root_meta_file, "w", encoding="utf-8") as f:
                json.dump(root_data, f, ensure_ascii=False, indent=2)
            print("   ✓ Updated CapCut root_meta_info.json")
        except Exception as e:
            print(f"   Warning updating root_meta_info: {e}")

        print(f"🎉 Perfect CapCut project generated at: {draft_folder}")
        return str(draft_folder)

if __name__ == "__main__":
    from scripts.subtitle_engine import SubtitleEngine
    from scripts.voice_engine import VoiceEngine

    raw = PROJECT_ROOT / "01_Raw" / "20260812_Esseger-สายชาร์จแม่เหล็ก" / "Video" / "esseger_สายชาร์จ_raw.mov"
    voice = PROJECT_ROOT / "03_Projects" / "TikTok_สายชารจแมเหลก_3-in-1" / "voiceover.wav"
    bgm = MUSIC_DIR / "bgm_brass_funk.wav"
    
    cues = [
        {"start": 0.0, "end": 2.5, "text": "สายชาร์จแม่เหล็ก 3-in-1"},
        {"start": 2.5, "end": 5.5, "text": "ดูดแน่น ชาร์จเร็ว 66W"},
        {"start": 5.5, "end": 8.5, "text": "หมุนได้ 540 องศา"},
        {"start": 8.5, "end": 12.0, "text": "เล่นเกมไม่สะดุด ไม่ติดมือ"},
        {"start": 12.0, "end": 15.0, "text": "ลดพิเศษวันนี้ 149 บาท"},
        {"start": 15.0, "end": 18.0, "text": "กดสั่งที่ตะกร้าซ้ายล่างเลยครับ"}
    ]

    PerfectCapCutBuilder.generate(
        project_name="TikTok_Esseger_Pro_Draft",
        raw_video_path=str(raw),
        voice_audio_path=str(voice),
        cues=cues,
        total_duration=18.0,
        bgm_path=str(bgm)
    )
