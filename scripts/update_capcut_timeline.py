import json
import uuid
from pathlib import Path

root = Path(r"C:\Users\Winon\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft")
project_folder = root / "TikTok_Esseger_Working"

with open(project_folder / "draft_content.json", "r", encoding="utf-8") as f:
    content = json.load(f)

# Keep the base materials schema intact, and update the paths and segments!
raw_video_path = "D:/Winona/Programmer/Capcut/01_Raw/20260812_Esseger-สายชาร์จแม่เหล็ก/Video/esseger_สายชาร์จ_raw.mov"
voice_audio_path = "D:/Winona/Programmer/Capcut/03_Projects/TikTok_สายชารจแมเหลก_3-in-1/voiceover.wav"
bgm_audio_path = "D:/Winona/Programmer/Capcut/02_Assets/Music/bgm_brass_funk.wav"

# Update video material 0 path
for v in content.get("materials", {}).get("videos", []):
    v["path"] = raw_video_path
    v["material_name"] = "esseger_สายชาร์จ_raw.mov"

# Add voiceover audio material
voice_mat_id = str(uuid.uuid4()).upper()
content["materials"]["audios"] = [
    {
        "id": voice_mat_id,
        "path": voice_audio_path,
        "type": "audio",
        "duration": 35166000,
        "name": "voiceover.wav"
    }
]

if Path(bgm_audio_path).exists():
    bgm_mat_id = str(uuid.uuid4()).upper()
    content["materials"]["audios"].append({
        "id": bgm_mat_id,
        "path": bgm_audio_path,
        "type": "audio",
        "duration": 35166000,
        "name": "bgm_brass_funk.wav"
    })
else:
    bgm_mat_id = None

# Update subtitle text contents in existing text materials
thai_lines = [
    "สายชาร์จแม่เหล็ก 3-in-1",
    "เสียบง่าย ดูดแน่น ชาร์จเร็ว 66W",
    "ข้อต่อหมุนได้ 540 องศา",
    "เล่นเกมไม่สะดุด ไม่ติดมือ",
    "หมดปัญหาสายขาดตรงคอ",
    "เสียบได้ในที่มืดสบายๆ",
    "มีไฟ LED แสดงสถานะ",
    "ชาร์จได้ทั้ง Type-C, Micro, Lightning",
    "ลดพิเศษวันนี้เพียง 149 บาท",
    "กดสั่งในตะกร้าสีเหลืองซ้ายล่างได้เลยครับ"
]

texts = content.get("materials", {}).get("texts", [])
for i, line in enumerate(thai_lines):
    if i < len(texts):
        t_mat = texts[i]
        try:
            inner = json.loads(t_mat["content"])
            inner["text"] = line
            if inner.get("styles"):
                inner["styles"][0]["range"] = [0, len(line)]
            t_mat["content"] = json.dumps(inner, ensure_ascii=False)
        except Exception:
            pass

# Save back to draft_content.json
with open(project_folder / "draft_content.json", "w", encoding="utf-8") as f:
    json.dump(content, f, ensure_ascii=False, indent=2)

print("Successfully injected video, voice, BGM, and Thai subtitles into TikTok_Esseger_Working!")
