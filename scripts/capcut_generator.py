"""
CapCut Desktop Draft Project Generator (.draft_content.json)
Generates rich, multi-track native CapCut projects with:
- Main Video cuts (Rhythmic & Punch-Zoom)
- Crystal Voiceover Track
- Looping BGM with Auto-Ducking
- Timed SFX Tracks (Boom, Pop, Ding, Cash)
- Kanit Bold Subtitles
- Top Hook Banner Overlay
- Bottom CTA Sticker Overlay (Yellow Basket Arrow)
- Automatic registration in CapCut's root_meta_info.json
"""

import os
import sys
import json
import uuid
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import CAPCUT_DRAFT_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, FPS, ASSETS_DIR, MUSIC_DIR, SFX_DIR
from scripts.make_perfect_capcut import PerfectCapCutBuilder

CAPCUT_EXE = Path(os.environ.get("LOCALAPPDATA", "")) / "CapCut" / "Apps" / "CapCut.exe"

class CapCutDraftGenerator:
    """Generates studio-grade, ready-to-open CapCut Desktop projects."""

    @staticmethod
    def _gen_id() -> str:
        return str(uuid.uuid4()).upper()

    @classmethod
    def create_project(
        cls,
        project_name: str,
        raw_video_path: str,
        voice_audio_path: str,
        cues: List[Dict],
        total_duration: float,
        bgm_path: Optional[str] = None,
        hook_title: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> str:
        return PerfectCapCutBuilder.generate(
            project_name=project_name,
            raw_video_path=raw_video_path,
            voice_audio_path=voice_audio_path,
            cues=cues,
            total_duration=total_duration,
            bgm_path=bgm_path,
            hook_title=hook_title
        )

    @classmethod
    def open_capcut(cls):
        """Launches CapCut Desktop."""
        if CAPCUT_EXE.exists():
            subprocess.Popen([str(CAPCUT_EXE)], shell=True)
            return True
        return False
        """
        Creates a full CapCut draft folder containing draft_content.json, draft_meta_info.json,
        and draft_cover.jpg, and registers it in CapCut's root_meta_info.json.
        """
        if output_dir:
            draft_folder = Path(output_dir) / project_name
        else:
            draft_folder = CAPCUT_DRAFT_DIR / project_name

        draft_folder.mkdir(parents=True, exist_ok=True)
        raw_video = Path(raw_video_path).resolve()
        voice_audio = Path(voice_audio_path).resolve()
        
        total_duration_us = int(total_duration * 1_000_000)

        # 1. Base Materials Container
        materials = {
            "videos": [],
            "audios": [],
            "speeds": [],
            "texts": [],
            "canvases": [],
            "transitions": [],
            "stickers": [],
            "material_colors": [],
            "sound_channel_mappings": []
        }

        # Video Material
        video_mat_id = cls._gen_id()
        materials["videos"].append({
            "id": video_mat_id,
            "path": str(raw_video),
            "type": "video",
            "duration": total_duration_us * 3,
            "width": VIDEO_WIDTH,
            "height": VIDEO_HEIGHT,
            "material_name": raw_video.name
        })

        # Voice Material
        voice_mat_id = cls._gen_id()
        materials["audios"].append({
            "id": voice_mat_id,
            "path": str(voice_audio),
            "type": "audio",
            "duration": total_duration_us,
            "name": "voiceover.wav"
        })

        # BGM Material
        bgm_mat_id = None
        if bgm_path and Path(bgm_path).exists():
            bgm_mat_id = cls._gen_id()
            materials["audios"].append({
                "id": bgm_mat_id,
                "path": str(Path(bgm_path).resolve()),
                "type": "audio",
                "duration": total_duration_us,
                "name": Path(bgm_path).name
            })

        # SFX Materials
        sfx_boom_path = SFX_DIR / "sfx_vine_boom.wav"
        sfx_pop_path = SFX_DIR / "sfx_pop_bubble.wav"
        sfx_ding_path = SFX_DIR / "sfx_bell_ding.wav"
        sfx_cash_path = SFX_DIR / "sfx_cash_register.wav"

        def _add_audio_mat(p: Path, name: str) -> Optional[str]:
            if p.exists():
                mat_id = cls._gen_id()
                materials["audios"].append({
                    "id": mat_id,
                    "path": str(p.resolve()),
                    "type": "audio",
                    "duration": 1_000_000,
                    "name": name
                })
                return mat_id
            return None

        sfx_boom_id = _add_audio_mat(sfx_boom_path, "sfx_boom.wav")
        sfx_pop_id = _add_audio_mat(sfx_pop_path, "sfx_pop.wav")
        sfx_ding_id = _add_audio_mat(sfx_ding_path, "sfx_ding.wav")
        sfx_cash_id = _add_audio_mat(sfx_cash_path, "sfx_cash.wav")

        # Top Hook Banner Image Material
        hook_banner_path = TEMPLATES_DIR / "banner_hook_neon_yellow.png"
        hook_banner_id = None
        if hook_banner_path.exists():
            hook_banner_id = cls._gen_id()
            materials["videos"].append({
                "id": hook_banner_id,
                "path": str(hook_banner_path.resolve()),
                "type": "photo",
                "duration": 3_500_000,
                "width": 1080,
                "height": 160,
                "material_name": "banner_hook.png"
            })

        # CTA Basket Arrow Sticker Material
        basket_arrow_path = STICKERS_DIR / "sticker_yellow_basket_arrow.png"
        basket_arrow_id = None
        if basket_arrow_path.exists():
            basket_arrow_id = cls._gen_id()
            materials["videos"].append({
                "id": basket_arrow_id,
                "path": str(basket_arrow_path.resolve()),
                "type": "photo",
                "duration": 5_000_000,
                "width": 400,
                "height": 400,
                "material_name": "basket_arrow.png"
            })

        # 2. Build Segments
        video_segments = []
        text_segments = []
        sfx_segments = []

        # Rhythmic video cuts
        shot_scales = [1.25, 1.0, 1.35, 1.08]
        for idx, cue in enumerate(cues):
            start_us = int(cue["start"] * 1_000_000)
            end_us = int(cue["end"] * 1_000_000)
            dur_us = max(100_000, end_us - start_us)
            src_start_us = int(((idx * 2.5) % 30.0) * 1_000_000)

            # Video segment
            scale = shot_scales[idx % len(shot_scales)]
            video_segments.append({
                "id": cls._gen_id(),
                "material_id": video_mat_id,
                "source_timerange": {"start": src_start_us, "duration": dur_us},
                "target_timerange": {"start": start_us, "duration": dur_us},
                "speed": 1.0,
                "volume": 0.0,
                "clip": {
                    "scale": {"x": scale, "y": scale},
                    "transform": {"x": 0.0, "y": 0.0}
                },
                "render_index": 0
            })

            # Subtitle segment
            text_mat_id = cls._gen_id()
            text_content_obj = {
                "text": cue["text"],
                "styles": [
                    {
                        "fill": {"alpha": 1.0, "content": {"solid": {"color": [1.0, 1.0, 1.0]}}},
                        "font": {"path": "Kanit", "family": "Kanit"},
                        "size": 17.0,
                        "bold": True,
                        "stroke": {"alpha": 1.0, "color": [0.0, 0.0, 0.0], "width": 8.0}
                    }
                ]
            }
            materials["texts"].append({
                "id": text_mat_id,
                "content": json.dumps(text_content_obj, ensure_ascii=False),
                "type": "text"
            })

            text_segments.append({
                "id": cls._gen_id(),
                "material_id": text_mat_id,
                "target_timerange": {"start": start_us, "duration": dur_us},
                "clip": {
                    "scale": {"x": 1.5, "y": 1.5},
                    "transform": {"x": 0.0, "y": -0.72}
                }
            })

            # SFX Triggers
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

        # 3. Overlay Tracks
        overlay_segments = []
        if hook_banner_id:
            banner_dur = min(3_500_000, total_duration_us)
            overlay_segments.append({
                "id": cls._gen_id(),
                "material_id": hook_banner_id,
                "source_timerange": {"start": 0, "duration": banner_dur},
                "target_timerange": {"start": 0, "duration": banner_dur},
                "clip": {
                    "scale": {"x": 1.0, "y": 1.0},
                    "transform": {"x": 0.0, "y": 0.86}
                },
                "render_index": 100
            })

        if basket_arrow_id and total_duration_us > 4_000_000:
            arrow_start = total_duration_us - 4_000_000
            overlay_segments.append({
                "id": cls._gen_id(),
                "material_id": basket_arrow_id,
                "source_timerange": {"start": 0, "duration": 4_000_000},
                "target_timerange": {"start": arrow_start, "duration": 4_000_000},
                "clip": {
                    "scale": {"x": 0.8, "y": 0.8},
                    "transform": {"x": -0.60, "y": -0.65}
                },
                "render_index": 101
            })

        # Voice track segment
        voice_segment = {
            "id": cls._gen_id(),
            "material_id": voice_mat_id,
            "source_timerange": {"start": 0, "duration": total_duration_us},
            "target_timerange": {"start": 0, "duration": total_duration_us},
            "volume": 1.0
        }

        # 4. Multi-Track Structure
        tracks = [
            {
                "id": cls._gen_id(),
                "type": "video",
                "segments": video_segments,
                "flag": 0
            }
        ]

        if overlay_segments:
            tracks.append({
                "id": cls._gen_id(),
                "type": "video",
                "segments": overlay_segments,
                "flag": 0
            })

        tracks.append({
            "id": cls._gen_id(),
            "type": "text",
            "segments": text_segments,
            "flag": 0
        })

        tracks.append({
            "id": cls._gen_id(),
            "type": "audio",
            "segments": [voice_segment],
            "flag": 0
        })

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
                "volume": 0.15 # BGM Ducking
            }
            tracks.append({
                "id": cls._gen_id(),
                "type": "audio",
                "segments": [bgm_segment],
                "flag": 0
            })

        # Draft Content JSON
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

        # Meta Info JSON
        meta_info = {
            "draft_id": draft_content["id"],
            "draft_name": project_name,
            "draft_fold_path": str(draft_folder).replace("\\", "/"),
            "draft_timeline_materials_size_": 0,
            "tm_draft_create": int(time.time() * 1_000_000),
            "tm_draft_modified": int(time.time() * 1_000_000),
            "draft_root_path": str(CAPCUT_DRAFT_DIR).replace("\\", "/")
        }

        # Save files
        with open(draft_folder / "draft_content.json", "w", encoding="utf-8") as f:
            json.dump(draft_content, f, ensure_ascii=False, indent=2)

        with open(draft_folder / "draft_meta_info.json", "w", encoding="utf-8") as f:
            json.dump(meta_info, f, ensure_ascii=False, indent=2)

        # Generate Cover Thumbnail
        cover_path = draft_folder / "draft_cover.jpg"
        try:
            cov_img = Image.new("RGB", (540, 960), (20, 20, 30))
            cov_img.save(cover_path, "JPEG")
        except Exception:
            pass

        # 5. Register in root_meta_info.json
        cls._register_in_root_meta(project_name, str(draft_folder), draft_content["id"], total_duration_us)

        print(f"✅ CapCut native draft created & registered: {draft_folder}")
        return str(draft_folder)

    @classmethod
    def _register_in_root_meta(cls, draft_name: str, draft_folder: str, draft_id: str, duration_us: int):
        """Prepends the new project to CapCut's root_meta_info.json so it shows first."""
        root_meta_file = CAPCUT_DRAFT_DIR / "root_meta_info.json"
        now_us = int(time.time() * 1_000_000)
        norm_folder = draft_folder.replace("\\", "/")
        
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
            "draft_id": draft_id,
            "draft_is_ai_shorts": False,
            "draft_is_cloud_temp_draft": False,
            "draft_is_invisible": False,
            "draft_is_pippit_draft": False,
            "draft_is_web_article_video": False,
            "draft_json_file": f"{norm_folder}/draft_content.json",
            "draft_name": draft_name,
            "draft_new_version": "181.0.0",
            "draft_root_path": str(CAPCUT_DRAFT_DIR).replace("\\", "/"),
            "draft_timeline_materials_size": 10000000,
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
            "tm_duration": duration_us
        }

        try:
            if root_meta_file.exists():
                with open(root_meta_file, "r", encoding="utf-8") as f:
                    root_data = json.load(f)
            else:
                root_data = {"all_draft_store": [], "draft_ids": 1, "root_path": str(CAPCUT_DRAFT_DIR).replace("\\", "/")}

            existing = [item for item in root_data.get("all_draft_store", []) if item.get("draft_name") != draft_name]
            existing.insert(0, entry)
            root_data["all_draft_store"] = existing
            root_data["draft_ids"] = len(existing)

            with open(root_meta_file, "w", encoding="utf-8") as f:
                json.dump(root_data, f, ensure_ascii=False)
            print("   ✓ Updated CapCut root_meta_info.json")
        except Exception as e:
            print(f"   Warning: Could not update root_meta_info.json: {e}")

    @classmethod
    def open_capcut(cls):
        """Launches CapCut Desktop."""
        if CAPCUT_EXE.exists():
            subprocess.Popen([str(CAPCUT_EXE)], shell=True)
            return True
        return False

if __name__ == "__main__":
    print("CapCutDraftGenerator ready.")
