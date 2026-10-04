"""
Download tracks that hit the hook/beat instantly from 0:00 - 0:02:
1. LAKEY INSPIRED - Me 2 (feat. Julian Avila) -> Instant bouncy groove from second 1
2. LAKEY INSPIRED - Blue Boi -> Iconic instant rhodes + head-nodding beat
3. LAKEY INSPIRED - Days Like These -> Instant driving beat & bright melody
4. Joakim Karud - Rock Angel -> Instant boom-bap swing & saxophone hook from second 0
5. DJ Quads - Punch -> Instant punchy hip-hop groove
"""
import subprocess
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MUSIC_DIR = PROJECT_ROOT / "02_Assets" / "Music"

INSTANT_HOOK_TRACKS = [
    {
        "id_name": "bgm_lakey_inspired_me_2",
        "title": "LAKEY INSPIRED - Me 2 (feat. Julian Avila)",
        "query": "ytsearch1:LAKEY INSPIRED Me 2 audio",
        "hook_start": "0:01 (เข้าบีททันทีใน 1 วิแรก)",
        "vibe": "กรูฟสนุกสนาน โยกหัวทันที คอร์ด Rhodes + กีตาร์โมเดิร์น สไตล์รีวิวแกดเจ็ตตัวท็อป",
    },
    {
        "id_name": "bgm_lakey_inspired_blue_boi",
        "title": "LAKEY INSPIRED - Blue Boi",
        "query": "ytsearch1:LAKEY INSPIRED Blue Boi audio",
        "hook_start": "0:01 (คอร์ดเปียโนและบีทตบเข้าตั้งแต่ต้น)",
        "vibe": "ทันสมัย ชิลล์แต่กระปรี้กระเปร่า มีลูกเล่น ดึงดูดความสนใจตั้งแต่เฟรมแรก",
    },
    {
        "id_name": "bgm_lakey_inspired_days_like_these",
        "title": "LAKEY INSPIRED - Days Like These",
        "query": "ytsearch1:LAKEY INSPIRED Days Like These audio",
        "hook_start": "0:00 (บีทและเมโลดี้หลักขึ้นทันทีตั้งแต่วินาทีที่ 0)",
        "vibe": "จังหวะเดินเร็ว สดใส มีพลังส่ง พาสายตาและอารมณ์คนดูไหลไปกับคลิป",
    },
    {
        "id_name": "bgm_joakim_karud_rock_angel",
        "title": "Joakim Karud - Rock Angel",
        "query": "ytsearch1:Joakim Karud Rock Angel audio",
        "hook_start": "0:00 (แซกโซโฟนและกลองสวิงระเบิดตั้งแต่เสี้ยววินาทีแรก)",
        "vibe": "เท่ มีเสน่ห์ ไฮป์ สนุกสนาน คลาสสิก เหมาะกับงานเปิดตัวสินค้าและแกดเจ็ตเท่ๆ",
    },
    {
        "id_name": "bgm_dj_quads_punch",
        "title": "DJ Quads - Punch",
        "query": "ytsearch1:DJ Quads Punch audio",
        "hook_start": "0:01 (บีท Hip-Hop หมัดเด็ดเข้าตั้งแต่ต้น)",
        "vibe": "หมัดหนัก กระชับ แน่น โมเดิร์นไอที vlog ระดับโลก",
    }
]

def main():
    results = []
    for t in INSTANT_HOOK_TRACKS:
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
            t["file_path"] = str(out_file.resolve())
            t["file_name"] = out_file.name
            results.append(t)
            
    out_json = MUSIC_DIR / "bgm_instant_hook_collection.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved catalog: {out_json} ({len(results)} tracks)")

if __name__ == "__main__":
    main()
