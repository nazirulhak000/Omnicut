import os
import sys
import json
import uuid
import time
import shutil
from pathlib import Path

root = Path(r"C:\Users\Winon\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft")
src = root / "0812(1)"
dst = root / "TikTok_Esseger_Working"

if dst.exists():
    shutil.rmtree(dst)

# Copy all metadata and supporting files from working template
shutil.copytree(src, dst)

new_id = str(uuid.uuid4()).upper()
folder_posix = str(dst).replace("\\", "/")

# 1. Update draft_meta_info.json
with open(dst / "draft_meta_info.json", "r", encoding="utf-8") as f:
    meta = json.load(f)

meta["draft_id"] = new_id
meta["draft_name"] = "TikTok_Esseger_Working"
meta["draft_fold_path"] = folder_posix

with open(dst / "draft_meta_info.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False)

# 2. Update draft_content.json
with open(dst / "draft_content.json", "r", encoding="utf-8") as f:
    content = json.load(f)

content["id"] = new_id
content["name"] = "TikTok_Esseger_Working"

with open(dst / "draft_content.json", "w", encoding="utf-8") as f:
    json.dump(content, f, ensure_ascii=False)

# 3. Update root_meta_info.json
with open(root / "root_meta_info.json", "r", encoding="utf-8") as f:
    root_meta = json.load(f)

entry = {
    "cloud_draft_cover": False,
    "cloud_draft_sync": False,
    "draft_cloud_last_action_download": False,
    "draft_cloud_purchase_info": "",
    "draft_cloud_template_id": "",
    "draft_cloud_tutorial_info": "",
    "draft_cloud_videocut_purchase_info": "",
    "draft_cover": f"{folder_posix}\\draft_cover.jpg",
    "draft_fold_path": folder_posix,
    "draft_id": new_id,
    "draft_is_ai_shorts": False,
    "draft_is_cloud_temp_draft": False,
    "draft_is_invisible": False,
    "draft_is_pippit_draft": False,
    "draft_is_web_article_video": False,
    "draft_json_file": f"{folder_posix}\\draft_content.json",
    "draft_name": "TikTok_Esseger_Working",
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
    "tm_draft_cloud_modified": int(time.time() * 1000000),
    "tm_draft_cloud_parent_entry_id": -1,
    "tm_draft_cloud_space_id": 7104242274585805082,
    "tm_draft_cloud_user_id": 7030937065295479809,
    "tm_draft_create": int(time.time() * 1000000),
    "tm_draft_modified": int(time.time() * 1000000),
    "tm_draft_removed": 0,
    "tm_duration": 58000000
}

existing = [x for x in root_meta.get("all_draft_store", []) if x.get("draft_name") != "TikTok_Esseger_Working"]
existing.insert(0, entry)
root_meta["all_draft_store"] = existing
root_meta["draft_ids"] = len(existing)

with open(root / "root_meta_info.json", "w", encoding="utf-8") as f:
    json.dump(root_meta, f, ensure_ascii=False)

print("Duplicated and registered TikTok_Esseger_Working successfully!")
