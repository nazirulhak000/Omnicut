import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()
from scripts.pipeline import TikTokAutoCutterPipeline

script = """ทุกคน! อย่าเพิ่งซื้อสายชาร์จธรรมดา ถ้ายังไม่เห็นตัวนี้
บอกเลยว่า Esseger สายชาร์จแม่เหล็ก 3-in-1 คือดูดแน่นมากกก ชาร์จไว 66W
แถมข้อต่อยังหมุนได้ 540 องศา จะนอนเล่นเกมหรือดูซีรีส์ก็ไม่เกะกะมือ
หมดปัญหาสายหักตรงคอ เสียบในที่มืดได้สบายๆ เลยครับ
พิกัดราคาพิเศษวันนี้แค่ 149 บาท กดในตะกร้าซ้ายล่างได้เลยครับ!"""

res = TikTokAutoCutterPipeline.run(
    product_name="Esseger สายชาร์จแม่เหล็ก",
    raw_video_path="01_Raw/20260812_Esseger-สายชาร์จแม่เหล็ก/Video/esseger_สายชาร์จ_raw.mov",
    custom_script=script,
    hook_title="สายชาร์จแม่เหล็ก 3-in-1\nตัวเดียวจบทุกปัญหา!",
    voice="th-TH-NiwatNeural",
    voice_rate="+20%",
    font_name="IBMPlex",
    bilingual_subtitles=True,
    use_ai_vision=True,
    export_mp4=True
)

print("\n🎉 AI VISION DIRECTED VIDEO COMPLETED!")
print("Video File:", res.get("mp4_video"))
if res.get("ai_matched_shots"):
    print(f"Matched Shots: {len(res['ai_matched_shots'])}")
    for i, s in enumerate(res["ai_matched_shots"]):
        print(f"  [{i+1}] {s.get('start_time')}s - {s.get('end_time')}s ({s.get('punch_zoom')}x) : {s.get('visual_reason')}")
