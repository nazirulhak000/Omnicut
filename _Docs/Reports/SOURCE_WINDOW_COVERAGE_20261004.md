# Source window coverage และนโยบายภาพไม่พอ
ดำเนินการโดย: Codex (GPT-6)
วันที่: 2026-10-04
สถานะ: ผ่าน full regression gate

ผู้ใช้เลือกให้ค้างภาพสุดท้ายของช็อตเดิม พร้อมแจ้งว่าภาพไม่พอ เมื่อภาพตรงฟีเจอร์มีไม่พอสำหรับบท และอนุญาต regression/measurement gate เมื่อ Jev confidence=null สำหรับแผนนี้

## ปัญหาและพฤติกรรมใหม่
- Catalog matcher เคยขยายฉากสั้นให้ยาวขั้นต่ำ 1.8 วินาที และ allocator เล่นตามความยาวบทโดยไม่ยึด end_time ทำให้ไหลเข้าภาพหัวข้อถัดไป
- จำกัดช่วงตั้งแต่ catalog, เติม scene_end ให้ cache เก่าในหน่วยความจำ และจัดสรรบนกริด 30 FPS หลังปรับรอยตัดแล้ว
- กลุ่มต่อเนื่องที่ใช้ AI shot เดียวกันและภาพไม่พอเล่นช่วงภาพครั้งเดียว แล้วใช้ freeze_tail จนครบเสียง; ช่วงยาวแบ่งเป็นคลิปค้างที่รักษาเฟรมและ camera pose เดิม ไม่วนภาพหรือเปลี่ยน speed
- บันทึก source_window/footage_shortage ในคลิป แจ้งระยะเวลาภาพไม่พอบน editor และแสดงช่วงภาพตรงบทใน Inspector; metadata ยังอยู่หลัง save/load
- Transition อัตโนมัติที่ต้องใช้ภาพนอกช่วงเปลี่ยนเป็น hard cut การคำนวณความยาวสุดท้ายรวม freeze_tail เพื่อไม่ขยาย trim_end เกินหัวข้อ และ rerender ไม่เติม transition ที่ต้องใช้ภาพที่ไม่มี
- FFmpeg seek ลงก่อนขอบเฟรมเล็กน้อยเพื่อป้องกันปัดไปเฟรมหัวข้อถัดไป; ต้นฉบับ 60 FPS แปลงลงกริด 30 FPS ก่อนค้างภาพ เพื่อไม่สลับเฟรมเมื่อเข้าสู่ช่วงค้างถัดไป
- Browser regression พบ callback งานตัดช่วงเงียบจากงานขนานอ่าน showToast ก่อน declaration และทำให้ editor เปิดไม่ได้ ย้าย declaration ขึ้นก่อน callbacks โดยรักษา logic ของเจ้าของงาน

## การตรวจจริง
- Synthetic source encode หมายเลขเฟรมลง RGB; production FFmpeg renderer และ production JS getDrawPlan ตรวจทุก output frame ที่ 8/12 วินาที รวมรอยต่อคลิปค้าง
- ต้นฉบับ 30 FPS: source 2–4 วินาที เล่นเฟรม 60–119 แล้วค้างเฟรม 119 ทั้งหมด Preview/Render ตรงกันทุกเฟรม ไม่แสดงเฟรม 120 ของฟีเจอร์ถัดไป
- ต้นฉบับ 60 FPS: output 30 FPS เล่น 120,122,…,238 แล้วค้าง 238 ต่อเนื่อง ความคลาดจากตัวแทนเวลาของ preview ไม่เกินหนึ่ง source frame และไม่ถึงเฟรม 240 ของฟีเจอร์ถัดไป
- วัดภาพช่วงค้างหลัง camera settling: mean absolute pixel difference <1/255 ไม่มี camera ramp เริ่มใหม่ที่แบ่งคลิป
- Browser จริงที่ความกว้าง 390/1600: เปิด editor และ reload แล้วยังแจ้งภาพขาด 6.00 วินาที ไม่มี page error
- Integration/parity/real-render/browser: 234 passed; allocator/grouping/assembly targeted gate หลัง refactor: 44 passed
- Frontend หลังรวมงานขนาน Clipboard: 804 passed, build ผ่าน; compileall ผ่าน, API import 225 routes, git diff --check ผ่าน
- Full Python รอบยืนยัน: **2907 passed, 12 skipped, 54 warnings ใน 784.24 วินาที**; warnings เดิมจาก dependency/test rendering ไม่ได้เพิ่มจากงานนี้
- Backend ตรวจไม่มี queued/processing/running jobs ก่อนรีสตาร์ต ตรวจ command line/PID ว่าเป็น scripts/api_server.py ของ workspace นี้ แล้วเปิดแบบ Hidden; backend ใหม่ตอบ HTTP 200
- Jev ผ่าน `tools/jev_advisor.py`: ก่อนทดสอบ noul=0.84, หลังเขียนรายงาน/เทียบก่อน–หลัง noul=0.76, confidence=null ทั้งคู่ ตัวเลข noul ไม่ใช่ confidence ใช้ regression/measurement gate ตามที่ผู้ใช้อนุญาต ไม่ใช้ Jev รับรองเฟรมภาพ
- ตรวจข้อความรายงานรอบสุดท้ายหลัง full gate/runtime: noul=0.70, confidence=null; ใช้ผลทดสอบจริงตามข้อยกเว้นที่ผู้ใช้อนุญาตเช่นเดิม
- Full gate รอบแรกพบ coverage matrix ยังไม่มี source_window และ browser context-menu selector เลือกสองปุ่มเมื่ออีกเอเจนต์เพิ่มปุ่มใน Inspector; ลงทะเบียน field ตามพฤติกรรมจริงและระบุ shortcut ใน accessible name ให้เลือกเมนูตามวัตถุประสงค์เดิม Focused regression 7 passed โดยยังตรวจ copy/paste ทุกคลิปและ undo/redo ครบ

## ขอบเขตของผล
นี่คือการรักษาช่วงภาพที่ AI เลือกแล้ว ไม่ใช่ผลวัดความแม่นยำในการเข้าใจภาพของ AI หรือ retention ของคลิปจริง Legacy matches ที่ไม่มี end_time ยังใช้เส้นทางเดิม เพราะไม่มีข้อมูลพออนุมานขอบเขตหัวข้อ การค้างภาพนานเป็นพฤติกรรมที่ผู้ใช้เลือกและมี notice; ยังไม่เพิ่มการค้นหาช็อตทดแทนอัตโนมัติ

การจัดสรรใหม่นี้ใช้ตอนสร้างแผนช็อตใหม่ โปรเจกต์ที่มี clip_list เดิมอยู่แล้วไม่ถูกแก้ช่วงภาพย้อนหลังเอง ต้องสร้างแผนช็อตใหม่เพื่อใช้ source_window/footage_shortage; การเรนเดอร์ซ้ำอย่างเดียวรักษาคลิปที่ผู้ใช้แก้ไว้

ทุกวิดีโอ/ภาพทดสอบอยู่ใน TemporaryDirectory/temp_capture_dir และถูกลบทันทีเมื่อจบ test ไม่ใช้ Raw/Assets/Projects/Exports จริง ไม่แก้ฟอนต์หรือซับในวิดีโอ
