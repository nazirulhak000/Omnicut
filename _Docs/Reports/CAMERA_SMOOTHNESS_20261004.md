# Camera / transition timing alignment
ดำเนินการโดย: Codex (GPT-6)
วันที่: 2026-10-04

## ผลที่แก้
1. ขั้นตอน `_centre_transition_overlaps` เพิ่ม source handle หัวคลิปเพื่อให้ midpoint ของ transition ตรง planned cut แต่เดิมไม่ได้เลื่อน camera keyframe ตาม จึงทำให้ซูม/แพนเริ่มก่อน source instant ที่วางไว้ ใน regression พบ phase error 100–200 ms ทั้ง 6 กรณี
2. เลื่อนเวลา keyframe ด้วย played head ที่เพิ่มจริง ไม่ใช้ source seconds หรือ overlap เต็ม รักษา trajectory/easing เดิม และค้าง first pose ระหว่าง handle หัวคลิป รองรับ mixed/property tracks, speed 0.5/1/2, handle ไม่ครบ และไม่ขยับซ้ำในการเรียกครั้งถัดไป
3. ShotMatchingStage บันทึก easing ของ boundary ลง `transition_easing` ของคลิปให้ preview ใช้ค่าเดียวกับ renderer; เส้นทาง assembly auto-fill บันทึกเช่นกันและล้างค่าเก่าใน cut slots ตรวจถึง manifest ที่ save
4. ของเดิมมี camera ease-in-out, split continuity และ slide orientation แล้ว รอบนี้แก้ timing/data propagation ไม่เพิ่ม transition ให้ทุกจุดตัด

## การตรวจรับ
- Unit/integration เฉพาะ shot/source-window/pacing/style/transition/keyframes: **108 passed**, 1.01s
- Scoped preview/render parity: **7 passed**, 0.52s
- Real render ใหม่: **1 passed**, เปรียบเทียบ reference 2s กับ transition 4s และ counterfactual เก่า; production JS ตรวจ 120 frame poses กับ Python และ ease-out alpha 43.75% ที่ progress 25%
- Real render regression เดิม: split zoom + transition midpoint **3 passed**, 9.72s; ease-out fade/slideleft/slideright **3 passed**, 0.67s
- รวม **122 passed**, ไม่มี skipped/warnings จาก pytest รอบนี้; compileall และ API import **225 routes** ผ่าน; scoped git diff --check ผ่าน (มี Git LF/CRLF notices)
- Render 4s ได้ **120 frames**, ไม่มี empty/black frames ใน synthetic grid; median mean absolute pixel difference เทียบ reference ณ source time เดียวกัน **3.775 หลังแก้ / 62.734 แบบ timing เดิม** (ระดับ gray 0–255)
- เกณฑ์ pixel test: max MAD <=8, median <=5 และ counterfactual error >10x ของผลใหม่ รองรับความต่างจาก encoder และ scale/crop rounding ระดับ 2px; ไม่อ้าง frame-identical จากค่า pose อย่างเดียว
- Baseline camera source-instant regression ก่อนแก้ **6 failed** หลังแก้ผ่านทั้งหมด
- ไม่รัน full pytest/npm/build ตามคำสั่งผู้ใช้และไม่มี frontend code changes
- Media ใหม่ใช้ TemporaryDirectory; regression เดิมรันใต้ temporary basetemp แล้ว cleanup ทั้งหมด ไม่แตะ real raw/assets/project/export/registry

## Jev และข้อจำกัด
- ก่อนเริ่ม: score 0.67; ก่อน render: 0.59; เปรียบเทียบก่อน/หลัง: 0.77; ตรวจเอกสาร: 0.35; confidence ทุกครั้ง = null
- ใช้ regression/measurement gate ตามที่ผู้ใช้อนุญาตไว้ คะแนน Jev ไม่ใช่ confidence หรือหลักฐานตรวจภาพ
- ผลนี้ยืนยันการรักษา timing และ parity ในสถานการณ์ทดสอบ ไม่รับรองความสวยงามหรือ retention ของคลิปจริง
- Camera head adjustment ใช้เมื่อสร้าง shot plan ใหม่และ compensate overlap ครั้งแรก โปรเจกต์เก่าที่บันทึก `_overlap_compensated` แล้วไม่ถูกแก้ย้อนหลัง; ต้องสร้างแผนช็อตใหม่จึงได้ timing นี้
- Backend idle ก่อน restart (0 active tasks); โหลดโค้ดรอบนี้ใหม่และตรวจ HTTP 200 หลัง restart
