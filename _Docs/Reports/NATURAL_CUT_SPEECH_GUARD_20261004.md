# จังหวะตัด: ให้เสียงเป็นข้อจำกัดของ beat/motion snap
ดำเนินการโดย: Codex (GPT-6)
วันที่: 2026-10-04

## สิ่งที่แก้
R2 เดิมเลือก beat ที่ใกล้ที่สุดก่อนและยอมให้ motion เลื่อนขอบตามเฟรมที่นิ่ง โดยไม่ตรวจช่วงเวลาที่ภาพสัมพันธ์กับเสียงหลังเลื่อนจริง ตัวอย่าง baseline: onset 4.0s ถูก beat เลื่อนภาพไป 4.3s และ onset 2.0s ถูก motion เลื่อนไป 2.3s

ใช้ guard ร่วมกันสำหรับ beat/motion/voice valley: จุดตัดปกติต้องอยู่หลังเสียงเริ่ม 150–250 ms เลือก beat หรือ motion ที่ผ่าน guard ก่อนจัดอันดับ จึงใช้ตัวเลือกที่เข้ากับเสียงได้แม้ตัวเลือกที่ใกล้ที่สุด/นิ่งที่สุดจะใช้ไม่ได้ Short shots ที่จงใจลด J-lead รักษาเฟรมเดิม; ถ้าไม่มี onset ยังใช้พฤติกรรม media-only เดิม

ไม่ได้เปลี่ยนเสียง ซับ ฟอนต์ หรือ style defaults และไม่เปลี่ยน source-window/hold policy ที่ผู้ใช้เลือกไว้ ไม่รับรองว่ากำจัดทุกจุดตัดกลางคำ เพราะภาพแบบ J-cut อาจเปลี่ยนหลังเสียงคำถัดไปเริ่มแล้ว การตัดไฟล์เสียงไม่ใช่ส่วนที่แก้ในรอบนี้

## Gate เฉพาะงานตามคำสั่งผู้ใช้
- Baseline 54 passed (0.75s) ก่อนแก้
- Shot quality/source window/editorial pacing/transition: 59 passed (0.82s)
- Style motion policy: 28 passed (0.45s)
- Source parity เฉพาะ cut/rhythm/pacing/voice/motion: 5 passed (0.36s)
- FFmpeg CPU render + production JS preview: 4 passed (9.04s)
- รวม focused acceptance **96 passed** ไม่มี full suite/npm suite รอบนี้ เพราะเปลี่ยนเฉพาะ Python planner และ tests; JS ที่ตรวจใช้ production timelineMath เดิม
- Compileall scripts ผ่าน, API import 225 routes, diff check เฉพาะไฟล์รอบนี้ผ่าน; whitespace ของ tests/test_gemini_tts_engine.py เป็นงานขนาน ไม่เขียนทับ

คลิป synthetic 8 วินาที/240 output frames: motion ที่ขัดเสียงถูกกรองและเลือกตัวเลือกที่ยังสัมพันธ์กับเสียง, beat ที่ใกล้แต่เร็วเกินถูกกรองและเลือก beat ที่ใช้ได้ จุดตัดจริงเป็นเฟรม **66/127/185** (2.200/4.233/6.167s); ตรวจ lead เทียบเสียงที่ decode จาก output และตรงกับ production preview ภายในหนึ่ง source frame

เรนเดอร์อีกสามกรณีตรวจ source-window hold ที่ 8/12 วินาทีจากต้นฉบับ 30/60 FPS ยังค้างเฟรมเดิมต่อเนื่องและไม่เข้าฟีเจอร์ถัดไป ไฟล์ทั้งหมดอยู่ใน TemporaryDirectory และลบทันทีเมื่อจบ test ไม่มีไฟล์ทดสอบใน Raw/Assets/Projects/Exports จริง

Jev เรียกผ่าน tools/jev_advisor.py ก่อนเริ่มและก่อน FFmpeg: noul 0.74/0.81, confidence=null ใช้ focused regression และ measurement เป็น gate ตามที่ผู้ใช้อนุญาต ตัวเลข noul ไม่ใช่ confidence และไม่ใช้ Jev รับรองภาพ

ตรวจรายงาน/เทียบก่อน–หลังรอบสุดท้าย: noul=0.80, confidence=null เช่นเดิม Backend ไม่มี active jobs ก่อนรีสตาร์ตแบบ Hidden และ process ใหม่ตอบ HTTP 200
