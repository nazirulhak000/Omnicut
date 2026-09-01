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

script = """1. ทุกคน! อย่าเพิ่งซื้อสายชาร์จธรรมดา ถ้ายังไม่เห็นตัวนี้
2. บอกเลยว่า Esseger สายชาร์จแม่เหล็ก 3-in-1 คือดูดแน่นมากกก ชาร์จไว 66W
3. แถมข้อต่อยังหมุนได้ 540 องศา จะนอนเล่นเกมหรือดูซีรีส์ก็ไม่เกะกะมือ
4. หมดปัญหาสายหักตรงคอ เสียบในที่มืดได้สบายๆ เลยครับ
5. พิกัดราคาพิเศษวันนี้แค่ 149 บาท กดในตะกร้าซ้ายล่างได้เลยครับ!"""

prompt = f"""คุณเป็น AI ผู้กำกับและตัดต่อวิดีโอระดับมืออาชีพสำหรับ TikTok Shop / Reels
กรุณาดูวิดีโอคลิปนี้อย่างละเอียด
และวิเคราะห์เลือกช่วงเวลา (start_time, end_time ในหน่วยวินาที) จากคลิปดิบ ที่มีภาพหรือการเคลื่อนไหวของมือ/สินค้า ที่ตรงกับความหมายของแต่ละท่อนในสคริปต์มากที่สุด

สคริปต์ที่ต้องจับคู่:
{script}

ตอบกลับเป็น JSON format เท่านั้น:
```json
{{
  "matched_shots": [
    {{
      "line_num": 1,
      "text": "ประโยคสคริปต์",
      "start_time": 0.0,
      "end_time": 3.0,
      "visual_reason": "เหตุผลที่เลือกช่วงนี้ เช่น เห็นมือถือสายชาร์จและหัวต่อชัดเจน",
      "zoom_scale": 1.15
    }}
  ]
}}
```
"""

try:
    print("Calling Gemini 2.5 Flash Vision...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            client.files.get(name="files/tmw3m0q1vifb"),
            prompt
        ]
    )
    print("\n🎉 GEMINI 2.5 FLASH VISION RESPONSE:")
    print(response.text)
except Exception as e:
    print("Error calling Gemini:", e)
