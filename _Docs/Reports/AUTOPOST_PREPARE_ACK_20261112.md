# Autopost Helper — รอผลเตรียมงานและแสดงสาเหตุในฟอร์ม

วันที่: 2026-11-12 · รุ่น: 0.10.5 · ดำเนินการโดย: Codex (GPT-6)
Round CODEX-AUTOPOST-PREPARE-ACK-20261112

## สิ่งที่ตรวจพบ

- อ่าน export ของ MONSTER AC530 แบบ read-only และทดสอบ caption/hashtags ที่แทนชื่อแล้วกับ guard จริง: ผ่านเมื่อกำหนด 2026-11-12 06:40 ณ เวลา 01:00 Bangkok
- จึงไม่ถือว่าชุดข้อความที่ผู้ใช้กรอกผิดหรือเวลาไม่พอ โดยยังไม่ทราบ error ของการคลิกครั้งจริงใน Chrome ของผู้ใช้
- โค้ดเดิมปิด dialog ก่อนเริ่ม await backend prepare/claim; ข้อผิดพลาดภายหลังไปอยู่ใน status นอก dialog แทนที่จะอยู่กับข้อมูลที่กำลังแก้
- worker อาจถือ job เดิมจาก session ก่อน แม้ panel ไม่มี active card; manual prepare เดิมยังไม่มี guarded handoff แบบ batch

## สิ่งที่แก้

1. ปุ่ม Prepare เรียก handler โดยตรง พร้อมคง submit handler สำหรับการเรียกผ่าน form; แสดงความคืบหน้าและจับ unexpected error ใน dialog
2. dialog รอ `onPrepare` จน backend prepare และ worker claim สำเร็จ ก่อนปิดและไป checklist
3. เมื่อ backend/claim ปฏิเสธ คง dialog และข้อมูลที่บันทึกไว้ แสดงเหตุผลจริงพร้อมคืน controls ให้ลองใหม่ ไม่รายงานสำเร็จหรือปิดทิ้ง
4. ระหว่างรอยืนยัน ปิด controls และกัน submit ซ้ำ รวมถึงป้องกันปิด dialog กลาง handoff
5. `prepareClip` คืนผลสำเร็จจริง/throw เมื่อ caller ต้องการ; อ่าน structured API validation errors เป็นข้อความพร้อมชื่อ field
6. manual prepare ใช้ release/park guard เดิมก่อนรับ job ใหม่เช่นเดียวกับ batch; งานที่มี attempt ไม่ถูก force-release และยังอยู่ใน unresolved/reconcile path
7. diagnostic browser test ใช้ CDP mouse press/release บนปุ่มจริง และ real-backend check รอรายการโหลดแบบมี timeout แทนยึด 6 วินาทีตายตัว

## ผลตรวจ

- Node extension + conductor **272/272 ผ่าน**, fail 0, skip 0
- Docked sidebar จริงใน Chromium profile แยก **38/38 ผ่าน** รวม:
  - กดปุ่มด้วย mouse events จริงแล้วจำลอง backend 422 → error อยู่ใน modal, ข้อมูลไม่หาย, retry ได้
  - หน่วง response → dialog รอและปุ่ม disabled; กดซ้ำไม่เกิด request เพิ่ม
  - ปล่อย response → prepare/claim สำเร็จจึงปิด dialog
  - manual handoff ถูกเรียกก่อน claim; guards เดิมของ release/park ครอบคลุมใน Node suite
  - เคส persistence, placeholders, draft confirmation, run ownership, recovery และ axe dark/light เดิมยังผ่าน
- Backend read-only smoke **27/27 ผ่าน** ด้วย `--allow-original-thumbnails`; queue/exports/pending hashes ก่อน–หลังเท่ากัน ไม่มี write request/console/page errors
- รอบ smoke แรกมี 3 checks จับขณะยัง Checking/ไม่มี card เพราะ backend โหลดเกิน fixed wait 6 วินาที; เปลี่ยนเครื่องมือให้รอ card หรือ error อย่างมี timeout แล้วรันใหม่ผ่าน
- Python diagnostic compile และ diff check ผ่าน; ตรวจ screenshot error ใน dialog แล้ว และลบภาพทดสอบหลังตรวจ

## ข้อจำกัด

ยังไม่รู้ข้อความ backend error ของการคลิกจริงที่ผู้ใช้แจ้ง จึงไม่สรุปว่าความล้มเหลวครั้งนั้นเกิดจาก API รหัสใด
ไม่ได้เตรียม/claim/โพสต์คลิปในคิวจริงเพื่อทดสอบ; worker/UI test ใช้ fixture transport ส่วน backend จริงเป็น read-only
backend ภาพย่อยังใช้ original-image compatibility ตามข้อจำกัดเดิม; ไม่มีการเปิด debug profile ที่ถูก policy ปฏิเสธซ้ำ
การเปิด upload tab ไม่สำเร็จหลัง job ถูก claim จะคง job ที่เตรียมแล้วและแจ้งเตือน ไม่สร้าง job ซ้ำเพราะการเปิดแท็บล้มเหลว
ผู้ใช้ต้อง reload extension และเปิด sidebar ใหม่เพื่อรับ 0.10.5

## Jev

ก่อนเริ่มเลือก await acknowledgement + inline error, confidence 1.00 จากสรุปข้อความ ไม่ใช่หลักฐานตรวจโค้ด
ก่อน commit เลือก scoped source/tests/tools/work records, confidence 1.00; report disclosure 2.94/3, confidence 0.95, verdict proceed จากข้อความ/ผลตรวจที่ส่งให้
