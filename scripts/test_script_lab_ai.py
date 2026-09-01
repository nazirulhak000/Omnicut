import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

load_dotenv()
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

prompt = """คุณเป็นสุดยอด Copywriter และผู้เชี่ยวชาญการทำคลิป TikTok Shop / Affiliate มือโปร
กรุณาแต่งสคริปต์วิดีโอรีวิวป้ายยา 4 มุมมอง (4 Angles) สำหรับสินค้า:
- ชื่อสินค้า: Esseger สายชาร์จแม่เหล็ก 3-in-1
- จุดเด่น: แม่เหล็กดูดแรงมาก หมุนได้ 540 องศา ชาร์จไว 66W สายถักไนลอนทนทาน
- ปัญหาที่แก้: สายชาร์จพังง่ายตรงคอ เสียบยากในที่มืด เล่นเกมสายเกะกะมือ
- ราคา/โปร: 149 บาท กดในตะกร้าซ้ายล่าง

กรุณาแต่งสคริปต์ภาษาพูดคนรีวิวจริง (ไม่เอาภาษาโฆษณาแข็งๆ) 4 รูปแบบ:
1. เตือนภัย / จี้จุดเจ็บ (Stop Scroll / Pain Point)
2. โชว์ฟังก์ชันสุดล้ำ / ว้าว (Tech Feature Hype)
3. โปรเดือด / ความคุ้มค่า (FOMO / Price Value)
4. ชีวิตดีขึ้น / เปรียบเทียบ (Transformation / Social Proof)

ตอบกลับเป็น JSON Format:
```json
{
  "angles": [
    {
      "angle_id": "pain_point",
      "angle_name": "🚫 เตือนห้ามซื้อ / จี้จุดเจ็บ",
      "badge_color": "red",
      "hook_title": "อย่าเพิ่งซื้อสายชาร์จ ถ้ายังไม่เห็นตัวนี้!",
      "estimated_sec": 26,
      "script_text": "ทุกคน! อย่าเพิ่งซื้อสายชาร์จธรรมดา ถ้ายังไม่เห็นตัวนี้\\nใครที่เบื่อกับสายชาร์จพังตรงคอ เสียบยากในที่มืด บอกเลยว่าตัวนี้จบ\\nEsseger สายชาร์จแม่เหล็ก 3-in-1 ดูดแน่นมากก ชาร์จไว 66W\\nแถมหมุนได้ 540 องศา นอนเล่นเกมดูซีรีส์ไม่เกะกะมือเลยครับ\\nพิกัดราคาพิเศษวันนี้แค่ 149 บาท กดในตะกร้าซ้ายล่างได้เลยครับ!",
      "caption": "สายชาร์จแม่เหล็ก 3-in-1 หมุนได้ 540 องศา ไม่เกะกะมือ!",
      "hashtags": ["#สายชาร์จแม่เหล็ก", "#esseger", "#รีวิวของใช้", "#ของดีบอกต่อ", "#tiktokshop"]
    }
  ]
}
```
"""

try:
    print("Calling Gemini 2.5 Flash for Script Lab...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    print("\n🎉 GEMINI RESPONSE:")
    print(response.text)
except Exception as e:
    print("Error:", e)
