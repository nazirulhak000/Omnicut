import os
import sys
import json
import shutil
from pathlib import Path

root = Path(r"C:\Users\Winon\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft")

# Remove all folders except 0812(1)
for p in root.iterdir():
    if p.is_dir() and not p.name.startswith("."):
        if p.name != "0812(1)":
            try:
                shutil.rmtree(p, ignore_errors=True)
                print(f"Removed: {p.name}")
            except Exception as e:
                print(f"Error removing {p.name}: {e}")

# Rebuild clean root_meta_info.json containing only 0812(1)
orig_draft = root / "0812(1)"
clean_root = {
    "all_draft_store": [
        {
            "cloud_draft_cover": False,
            "cloud_draft_sync": False,
            "draft_cloud_last_action_download": False,
            "draft_cloud_purchase_info": "",
            "draft_cloud_template_id": "",
            "draft_cloud_tutorial_info": "",
            "draft_cloud_videocut_purchase_info": "",
            "draft_cover": "C:/Users/Winon/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/0812(1)\\draft_cover.jpg",
            "draft_fold_path": "C:/Users/Winon/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/0812(1)",
            "draft_id": "A776B8B0-D65E-40a8-8B5B-4BACE3DF4664",
            "draft_is_ai_shorts": False,
            "draft_is_cloud_temp_draft": False,
            "draft_is_invisible": False,
            "draft_is_pippit_draft": False,
            "draft_is_web_article_video": False,
            "draft_json_file": "C:/Users/Winon/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/0812(1)\\draft_content.json",
            "draft_name": "0812(1)",
            "draft_new_version": "",
            "draft_root_path": "C:\\Users\\Winon\\AppData\\Local\\CapCut\\User Data\\Projects\\com.lveditor.draft",
            "draft_timeline_materials_size": 123435977,
            "draft_type": "",
            "draft_web_article_video_enter_from": "",
            "pippit_avatar_url": "",
            "pippit_extra_info": "",
            "pippit_id": "",
            "pippit_user_name": "",
            "streaming_edit_draft_ready": True,
            "tm_draft_cloud_completed": "1786543697000",
            "tm_draft_cloud_entry_id": 7673146754283340305,
            "tm_draft_cloud_modified": 1786543690991671,
            "tm_draft_cloud_parent_entry_id": -1,
            "tm_draft_cloud_space_id": 7104242274585805082,
            "tm_draft_cloud_user_id": 7030937065295479809,
            "tm_draft_create": 1786540835568755,
            "tm_draft_modified": 1786545837297209,
            "tm_draft_removed": 0,
            "tm_duration": 58000000
        }
    ],
    "draft_ids": 1,
    "root_path": "C:/Users/Winon/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft"
}

with open(root / "root_meta_info.json", "w", encoding="utf-8") as f:
    json.dump(clean_root, f, ensure_ascii=False, indent=2)

print("CapCut database reset to clean 0812(1) project!")
