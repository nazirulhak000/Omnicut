"""
Download curated royalty-free BGM tracks for tech/gadget videos:
1. LAKEY INSPIRED - Chill Day (Chillhop, Rhodes piano, modern cool)
2. Joakim Karud - Dreams (Jazzy hip-hop, groovy swing, smart and fun)
3. MBB - Feel Good (Upbeat summer pop, energetic, bright gadget vibe)
4. Ikson - Anywhere (Melodic future vlog beat, driving tempo, innovative)
5. LiQWYD - Glow (Chill electronic synth, premium flagship tech aesthetic)
6. LAKEY INSPIRED - Better Days (Warm soul beat, smooth, very pleasant)
"""
import subprocess
import json
from pathlib import Path

PROJECT_ROOT = Path("d:/Winona/Programmer/Capcut")
MUSIC_DIR = PROJECT_ROOT / "02_Assets" / "Music"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

TRACKS = [
    {
        "id_name": "bgm_lakey_inspired_chill_day",
        "title": "LAKEY INSPIRED - Chill Day",
        "query": "ytsearch1:LAKEY INSPIRED Chill Day",
        "genre": "Chillhop / Modern Rhodes",
        "mood": "ฟังสบาย คูล ทันสมัย กรูฟชัด ไม่น่าเบื่อ (Signature Tech Vlog)",
        "best_for": "รีวิวสเปกทั่วไป, แกะกล่อง, บรรยายฟีเจอร์",
        "energy": "⭐⭐⭐⭐ (ปานกลาง-คึกคัก)",
    },
    {
        "id_name": "bgm_joakim_karud_dreams",
        "title": "Joakim Karud - Dreams",
        "query": "ytsearch1:Joakim Karud Dreams audio",
        "genre": "Jazzy Hip-Hop / Swing Groove",
        "mood": "สนุกสนาน มีสไตล์ สดใส ฉลาด น่าติดตาม (สไตล์ Casey / MKBHD)",
        "best_for": "คลิปไฮป์, สรุปจุดเด่นเร็วๆ, Hands-on ตัวเครื่อง",
        "energy": "⭐⭐⭐⭐⭐ (สนุก มีจังหวะชัด)",
    },
    {
        "id_name": "bgm_mbb_feel_good",
        "title": "MBB - Feel Good",
        "query": "ytsearch1:MBB Feel Good audio",
        "genre": "Tropical Pop / Upbeat Melodic",
        "mood": "สดใส สนุกสนาน พลังบวก ฟังสบาย เพลิดเพลิน",
        "best_for": "แกดเจ็ต Lifestyle, อุปกรณ์เสริม, ฟีเจอร์กล้องและสีสัน",
        "energy": "⭐⭐⭐⭐ (สดใส มีชีวิตชีวา)",
    },
    {
        "id_name": "bgm_ikson_anywhere",
        "title": "Ikson - Anywhere",
        "query": "ytsearch1:Ikson Anywhere audio",
        "genre": "Modern Vlog Beat / Electro Melodic",
        "mood": "ล้ำสมัย จังหวะขับเคลื่อน มีแรงส่ง ไฮเทค",
        "best_for": "การประมวลผล ชิปเซ็ตความเร็วสูง เกมมิ่ง และระบบระบายความร้อน",
        "energy": "⭐⭐⭐⭐⭐ (กระฉับกระเฉง โมเดิร์น)",
    },
    {
        "id_name": "bgm_liqwyd_glow",
        "title": "LiQWYD - Glow",
        "query": "ytsearch1:LiQWYD Glow audio",
        "genre": "Chill House / Futuristic Synth",
        "mood": "พรีเมียม สวยหรู สเปซไฮเทค นุ่มนวลแต่ทันสมัย",
        "best_for": "สมาร์ทโฟนระดับเรือธง, จอพับ, ดีไซน์ลักชูรี และระบบเลนส์ระดับโปร",
        "energy": "⭐⭐⭐ (นุ่มหรู ฟังสบายขั้นสุด)",
    },
    {
        "id_name": "bgm_lakey_inspired_better_days",
        "title": "LAKEY INSPIRED - Better Days",
        "query": "ytsearch1:LAKEY INSPIRED Better Days audio",
        "genre": "Warm Soul Hop / Smooth Beat",
        "mood": "อบอุ่น ผ่อนคลาย จังหวะโยกตามเบาๆ ไม่กลบเสียงพากย์ 100%",
        "best_for": "คลิปแนะนำการใช้งานจริง, สรุปราคาและความคุ้มค่า",
        "energy": "⭐⭐⭐ (สบายตา สบายหู)",
    },
]

def download_track(track):
    out_file = MUSIC_DIR / f"{track['id_name']}.mp3"
    if out_file.exists() and out_file.stat().st_size > 500000:
        print(f"[ALREADY EXISTS] {out_file.name} ({out_file.stat().st_size / 1024 / 1024:.2f} MB)")
        return str(out_file)
        
    print(f"\nDownloading: {track['title']}...")
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", str(MUSIC_DIR / f"{track['id_name']}.%(ext)s"),
        track["query"]
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"[SUCCESS] Downloaded {out_file.name}")
        return str(out_file)
    except Exception as e:
        print(f"[ERROR] Failed to download {track['title']}: {e}")
        return None

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
    for t in TRACKS:
        p = download_track(t)
        if p and Path(p).exists():
            dur = probe_duration(p)
            mins = int(dur // 60)
            secs = int(dur % 60)
            t["duration_str"] = f"{mins}:{secs:02d}"
            t["duration_seconds"] = dur
            t["file_path"] = str(Path(p).resolve())
            t["file_name"] = Path(p).name
            results.append(t)
            
    manifest_path = MUSIC_DIR / "bgm_catalog.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\nCatalog saved: {manifest_path} ({len(results)} tracks)")

if __name__ == "__main__":
    main()
