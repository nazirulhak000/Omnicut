# Cutout render: false stale prompt
ดำเนินการโดย: Codex (GPT-6) · วันที่: 2026-10-04

## สาเหตุและการแก้
โปรเจกต์ HOY01-เทียบของเดิม_1 มี artifact พร้อมจริงทั้ง 5 คลิป แต่ resolver เทียบ subject_points ดิบกับค่าที่ worker ปัดเหลือ 5 ตำแหน่ง เช่น x=0.3444365394719402 กับ x=0.34444 จึงตี stale ก่อนเรนเดอร์

แก้ scripts/background_isolation_compositor.py ให้เทียบผ่าน normalize_subject_points ที่ worker ใช้อยู่แล้ว ไม่เปลี่ยนการตรวจไฟล์หรือปิด Cutout การย้าย/ล้างจุด เปลี่ยน label/frame หรือ reference ยัง invalidates artifact ตามเดิม

## ผลตรวจ
- ก่อนแก้: reader อ่าน artifact ได้ 5/5 แต่ resolver/readiness ปฏิเสธ 5/5
- หลังแก้: resolver/readiness ยอมรับ 5/5 โดยอ่านโปรเจกต์จริงเท่านั้น ไม่เขียนไฟล์โปรเจกต์/วัตถุดิบ
- pytest compositor + render integration + video worker + API + config: 126 passed, 3 skipped
- เพิ่ม regression สอง scope และเส้นทางสร้าง FFmpeg graph ด้วย temp artifact ไม่ส่งออกคลิปจริง
- diff --check เฉพาะไฟล์ที่แก้ผ่าน; ทั้ง working tree มี blank EOF จากงานอื่นใน test_api_background_isolation.py
- API เดิม reload=false: ตรวจ tasks API ว่าไม่มีงาน queued/processing แล้วรีสตาร์ตเฉพาะ backend และตรวจ API ตอบกลับปกติ
- Jev ให้ noul=0.83, confidence=null; ใช้ regression/probe gate ตามข้อยกเว้นที่ผู้ใช้อนุญาตในงาน Cutout ต่อเนื่อง ไม่ตี noul เป็น confidence

ยังไม่ได้เรนเดอร์คลิปจริงของผู้ใช้ทั้งชิ้น ผลยืนยันครอบคลุมตัวบล็อก readiness และการสร้าง render graph ไม่อ้างว่า export จริงเสร็จแล้ว
