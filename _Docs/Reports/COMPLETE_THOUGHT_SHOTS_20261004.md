# ภาพต่อเนื่องจนเล่าประเด็นครบ
ดำเนินการโดย: Codex (GPT-6)
วันที่: 2026-10-04

## ปัญหาและผลใหม่
ก่อนแก้ AI merged shot ที่ครอบคลุมซับสี่ช่วงและมีภาพพอ ยังถูกแบ่งเป็นสี่คลิปตาม rhythmic MIN/MAX แม้เป็นประเด็นเดียว การเล่น source เดินต่อ แต่ framing/camera และ transition ถูกสร้างใหม่ตาม slot ทำให้ตัดถี่และเปลี่ยนซูมกลางความคิด

หลังคืนกลุ่มของต่าง AI topic แล้ว รวมกลุ่มที่ใช้ AI match **object เดียวกัน** ข้ามขอบ rhythmic ที่ยังไม่ใช่จบประโยค ตัวอย่าง 8 วินาที/สี่ซับประเด็นเดียวจาก source 10–20s เปลี่ยนจาก **4 clips เป็น 1 clip** เล่น 10–18s ด้วย speed 1.0 ไม่ค้างภาพเมื่อวัตถุดิบพอ

ขอบที่ยังคงไว้คือการเปลี่ยน AI match หรือ sentence end ที่รู้จาก sentence_end, line_idx, parent-cue span และ suffix fallback ข้อมูล line/parent ที่ชัดเจนมีอำนาจเหนือคำลงท้าย: “ครับ” กลางบรรทัดไม่ถูกตีเป็นจบประเด็น ขณะ explicit sentence_end ยังมีลำดับสูงสุด

กลุ่มที่ unmapped หรือมีหลาย matches ปนไม่ถูกเหมารวมเป็นเรื่องเดียว Explicit editorial pacing ยังคงจุดตัดที่กำหนดไว้ ส่วน source-window shortage ยังคงเล่นครั้งเดียวและ freeze ต่อพร้อม notice ตามนโยบายที่ผู้ใช้เลือก ไม่แก้เสียง ซับ หรือฟอนต์

## ผลตรวจเฉพาะงาน
- Baseline: 53 passed (0.71s) รวม test เดิมที่ยืนยันสี่คลิปจาก AI shot เดียว
- Grouping/sentence metadata/source windows/pacing/style/transitions: **96 passed (0.96s)**
- Real FFmpeg CPU render + production JS preview: **8 passed (21.90s)**
- Source parity เฉพาะ cut/rhythm/pacing/voice/motion: **5 passed (0.46s)**
- รวม focused gate **109 passed**; compileall ผ่าน, API import 225 routes, diff check เฉพาะไฟล์รอบนี้ผ่าน ไม่รัน full suite/npm suiteตามคำสั่งผู้ใช้

เรนเดอร์ synthetic 12 วินาที/360 frames ครบสามกรณี:
1. ประเด็นเดียวตลอด รวมคำสุภาพกลางประโยค: 1 clip; source frames 60–419 เดินต่อเนื่องครบทั้งคลิป
2. AI match เดิม แต่จบประโยคที่ 8s: 2 clips; ขอบจริง/preview อยู่เฟรม 245 (8.167s) และ source ยังเดินต่อเนื่อง
3. เปลี่ยนฟีเจอร์ที่ 8s: ภาพแรกเล่นเฟรม 60–304 แล้วภาพใหม่เริ่มเฟรม 360 ที่ output frame 245 ไม่มีขอบเทียมระหว่างความคิดแรก

ตรวจเสียงที่ decode จาก output ครบหก onset และตรวจ J-lead ที่ขอบจริง Production preview และ render เลือก source frame ต่างกันไม่เกินหนึ่งเฟรม อีกห้ากรณีครอบคลุม source hold 30/60 FPS, short topics และ speech guard รอบก่อน โดยยังผ่านทั้งหมด

Test การเล่นต่อจาก AI shot เดียวหลังจบประโยคยังอยู่ โดยเพิ่ม sentence_end ให้ test data ระบุว่าเป็นคนละประโยคจริง Test ใหม่แยกกรณีไม่มี sentence end ซึ่งต้องค้างช็อตเดียว และตรวจ explicit/line_idx/parent/suffix รวมถึงคำสุภาพกลางประโยค

วิดีโอ/เสียง/ภาพ synthetic ทั้งหมดอยู่ใน TemporaryDirectory และถูกลบทันทีเมื่อจบ test ไม่สร้างหรือแก้ไฟล์ใน Raw/Assets/Projects/Exports จริง

## ขอบเขต
ไม่ใช่การประเมินความเข้าใจเนื้อหาของ AI ใหม่ ใช้ความสัมพันธ์ cue_ids ของ AI merged shot ที่มีอยู่ ต่าง matches ถูกเก็บแยก แม้ข้อความอาจพูดเรื่องคล้ายกัน เพราะไม่มีหลักฐานพอรวมเอง ไม่เพิ่มการเดาฟีเจอร์จากข้อความซับสั้น ไม่มี sentence metadata ก็ยังใช้ suffix fallback เดิม โปรเจกต์ clip_list ที่แก้ไว้แล้วไม่ถูกจัดภาพย้อนหลัง ต้องสร้างแผนช็อตใหม่เพื่อใช้ logic นี้

Jev ผ่าน tools/jev_advisor.py ก่อนเริ่มและก่อน FFmpeg: noul 0.71/0.69, confidence=null ใช้ focused regression/measurement gate ตามที่ผู้ใช้อนุญาต ตัวเลข noul ไม่ใช่ confidence และ Jev ไม่ได้รับรองภาพ

ตรวจข้อความรายงาน/เทียบก่อน–หลังหลังจบ: noul=0.82, confidence=null เช่นเดิม Backend ไม่มี active jobs ก่อนรีสตาร์ตแบบ Hidden และ process ใหม่ตอบ HTTP 200
