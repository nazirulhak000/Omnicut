"""
Download curated Style #1 tracks (LAKEY INSPIRED / Tech Chillhop / Modern Rhodes Beats):
1. LAKEY INSPIRED - The Process
2. LAKEY INSPIRED - Monroe
3. LAKEY INSPIRED - Warm Nights
4. LAKEY INSPIRED - Overjoyed
5. LAKEY INSPIRED - In My Clouds
6. Kronicle - 2 Hours Well Spent
"""
import subprocess
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MUSIC_DIR = PROJECT_ROOT / "02_Assets" / "Music"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

CHILLHOP_TRACKS = [
    {
        "id_name": "bgm_lakey_inspired_the_process",
        "title": "LAKEY INSPIRED - The Process",
        "query": "ytsearch1:LAKEY INSPIRED The Process audio",
        "genre": "Modern Tech Chillhop / Rhodes Groove",
        "mood": "คูล มั่นใจ จังหวะบีทเดินหน้าชัดเจน เหมาะกับโทรศัพท์รุ่นท็อปและฟังก์ชันสุดล้ำ",
        "highlight": "บีทกลองกระชับ คอร์ดเปียโน Rhodes ทันสมัย เท่มากๆ",
    },
    {
        "id_name": "bgm_lakey_inspired_monroe",
        "title": "LAKEY INSPIRED - Monroe",
        "query": "ytsearch1:LAKEY INSPIRED Monroe audio",
        "genre": "Sleek Tech Beat / Modern Hip-Hop",
        "mood": "พรีเมียม สไตลิช โมเดิร์น ลื่นไหล ชวนให้ดูคลิปจนจบ",
        "highlight": "เบสเดินสวย เมโลดี้คลีน ให้ความรู้สึกสมาร์ทโฟนดีไซน์หรูหรา",
    },
    {
        "id_name": "bgm_lakey_inspired_warm_nights",
        "title": "LAKEY INSPIRED - Warm Nights",
        "query": "ytsearch1:LAKEY INSPIRED Warm Nights audio",
        "genre": "Upbeat Melodic Chillhop",
        "mood": "สนุก สดใส อารมณ์ดี บีทสนุกสนานกระตุ้นความตื่นเต้น",
        "highlight": "เมโลดี้สดชื่น มีลูกเล่น เหมาะกับแกดเจ็ตที่เน้นความสนุกและกล้อง",
    },
    {
        "id_name": "bgm_lakey_inspired_overjoyed",
        "title": "LAKEY INSPIRED - Overjoyed",
        "query": "ytsearch1:LAKEY INSPIRED Overjoyed audio",
        "genre": "Bouncy Piano Chillhop",
        "mood": "มีชีวิตชีวา จังหวะเด้งสนุก สบายหู ฟังสบายไม่เครียด",
        "highlight": "เสียงเปียโนใส กรูฟบีทบ๊อบบี้ โยกตามจังหวะได้ดีมาก",
    },
    {
        "id_name": "bgm_lakey_inspired_in_my_clouds",
        "title": "LAKEY INSPIRED - In My Clouds",
        "query": "ytsearch1:LAKEY INSPIRED In My Clouds audio",
        "genre": "Futuristic Chillhop / Electronic Nu-Beat",
        "mood": "ล้ำสมัย สเปซไฮเทค นวัตกรรมใหม่ โทนโมเดิร์นแกดเจ็ตแท้ๆ",
        "highlight": "ซาวด์ลอยมีมิติ บีทหนักแน่น เสริมความคมชัดของภาพวิดีโอ",
    },
    {
        "id_name": "bgm_kronicle_2_hours_well_spent",
        "title": "Kronicle - 2 Hours Well Spent",
        "query": "ytsearch1:Kronicle 2 Hours Well Spent audio",
        "genre": "Classic Tech Vlog Boom-Bap",
        "mood": "คลาสสิกรีวิวไอที ฟังสบายขั้นสุด สไตล์ MKBHD และช่องรีวิวต่างประเทศ",
        "highlight": "เสียงกลองและคอร์ดอะคูสติกผสานไฟฟ้า นุ่มนวล ไม่ขัดหู",
    }
]

def probe_duration(file_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(res.stdout.strip())
    except Exception:
        return 0.0

def main():
    results = []
    for t in CHILLHOP_TRACKS:
        out_file = MUSIC_DIR / f"{t['id_name']}.mp3"
        if not out_file.exists() or out_file.stat().st_size < 500000:
            print(f"\nDownloading: {t['title']}...")
            cmd = [
                "yt-dlp",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "-o", str(MUSIC_DIR / f"{t['id_name']}.%(ext)s"),
                t["query"]
            ]
            try:
                subprocess.run(cmd, check=True)
                print(f"[SUCCESS] Downloaded {out_file.name}")
            except Exception as e:
                print(f"[ERROR] Failed to download {t['title']}: {e}")
                continue
        else:
            print(f"[EXISTS] {out_file.name}")
            
        if out_file.exists():
            dur = probe_duration(out_file)
            mins = int(dur // 60)
            secs = int(dur % 60)
            t["duration_str"] = f"{mins}:{secs:02d}"
            t["duration_seconds"] = dur
            t["file_path"] = str(out_file.resolve())
            t["file_name"] = out_file.name
            results.append(t)
            
    # Save chillhop collection catalog
    out_json = MUSIC_DIR / "bgm_chillhop_style1_collection.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nCatalog saved: {out_json} ({len(results)} tracks)")

if __name__ == "__main__":
    main()
