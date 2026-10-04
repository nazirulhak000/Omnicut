# ภาพตามบท: ป้องกันการรวมท่อนจนหัวข้อหาย
ดำเนินการโดย: Codex (GPT-6) · วันที่: 2026-10-04

## ปัญหาและผลใหม่
สองท่อนยาว .8s/.8s มี AI match ต่างกัน (source 10s และ 30s) แต่ rhythmic minimum-duration grouping รวมเป็นกลุ่มเดียวและอ่านเฉพาะ match ของท่อนแรก ภาพหัวข้อที่สองจึงไม่แสดง

หลัง duration merge แบ่งกลุ่มตาม AI mapping ที่มีอยู่แล้ว หลาย cue ใน merged AI shot ใช้ object เดียวกันจึงยัง hold เป็นกลุ่มเดียว กลุ่มที่เปลี่ยน match หรือเปลี่ยนระหว่าง unmapped/mapped จะรักษาจุดเปลี่ยนภาพ ไม่สร้างคำตัดสินจากชื่อไฟล์หรือเดาความหมายใหม่

เสียง/ซับและระยะเวลารวมไม่เปลี่ยน จุดเปลี่ยนใช้ frame grid และ J-lead เดิมที่ลดตามความยาวท่อนสั้น สำหรับท่อนต่ำกว่า .2s จัดขอบให้มีอย่างน้อย 6 เฟรมโดยไม่ยืดเวลารวม ถ้าไม่พอสำหรับทุกหัวข้อ คงกลุ่มเดิมพร้อม log แจ้งข้อจำกัด Explicit editorial pacing ไม่เปลี่ยน

## ตรวจรับ
- Baseline ชุด R1/R2/R3: 131 passed; frontend 799 passed/build ผ่าน
- Regression จุดที่แก้รวม render: 31 passed รวม feature A/B สั้น .4/.8s, topic เดียว, unmapped lead, ท่อน .1s และกรณีเกินจำนวนช็อตที่เวลารวมรองรับ
- Offline timing probe แบบ seed คงที่ 40 สถานการณ์ ความยาวท่อน .1/.2/.4/.8/1.6s: ไม่พบเวลารวมเปลี่ยนเกิน .003s
- Render จริง: ใช้ source ที่แต่ละเฟรมมีรหัสสี 30fps, 1.6s, สองหัวข้อที่ source 2s/10s เปรียบเทียบ 48 output frames กับ production preview planner ทั้งต้น/รอยต่อ/ท้าย ความต่างไม่เกิน 1 source frame; หัวข้อที่สองเริ่ม frame 29 ตาม J-lead เดิม
- TemporaryDirectory ลบ source/audio/ASS/render/thumbnail ทันทีหลังเทส ไม่ส่งออกไฟล์จริง
- compileall ผ่าน; API 225 routes; diff --check ผ่าน
- Ripple browser เดิมรอ input slider ที่ถูกถอดจาก compact UI ปรับ probe ให้อ่าน production timecode จริง; rerun 2 passed ใน 39.18s ยังคงตรวจ audio clock drift <1 เฟรมตลอด 30s, kept ranges/fade และ pause stop ทุก node
- Full pytest รอบแรก: 2884 passed, 2 failed, 12 skipped, 54 warnings (796.94s); สอง failures คือ probe Ripple ที่ใช้ slider เดิม
- Full pytest โค้ดล่าสุดหลังแก้ probe และกรณีท่อนเล็ก: **2888 passed, 12 skipped, 54 warnings (790.80s)** ไม่มี failure
- Jev ก่อนเริ่ม noul=.89, confidence=null; ก่อน FFmpeg .64/null; ใช้ regression/measurement gate ที่ผู้ใช้อนุญาต ไม่มีการตี probability เป็น confidence
- Jev สรุปก่อน/หลังจากข้อความ noul=.76/confidence null; ไม่ใช่การตรวจภาพ
- ตรวจ API tasks ว่างก่อนรีสตาร์ตเฉพาะ backend เพื่อโหลด logic ล่าสุด

## ข้อจำกัดและงานถัดไป
ยังไม่มีคะแนนความถูกต้องจากคลิปจริงของผู้ใช้ การวัดครั้งนี้พิสูจน์ว่า planner ไม่ทิ้ง AI match ระหว่างการรวมท่อน ไม่พิสูจน์ว่า AI เลือกภาพถูกทุกกรณี

ยังมีกรณี source window สั้นกว่าบท: baseline เลือก 10–12s แต่ใช้ถึง 18s ต้องทำ source-window policy ต่อจากนี้ โดยรักษาเวลาเสียง/ซับและแจ้งกรณีวัตถุดิบไม่พอ หลีกเลี่ยง replay/slow-motion ที่เพิ่มโดยเงียบ
