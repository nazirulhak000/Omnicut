# Autopost Helper — บันทึกฟอร์มและแจ้งข้อมูลที่ขาด

วันที่: 2026-11-12 · รุ่น: 0.10.4 · ดำเนินการโดย: Codex (GPT-6)
Round CODEX-AUTOPOST-PREPARE-SAVE-FEEDBACK-20261112

## สาเหตุ

ฟอร์ม 0.10.3 ยังไม่มี persistence สำหรับสิ่งที่กรอกไว้ และใช้ native required validation ของวันที่/เวลา ซึ่งอาจหยุด submit ก่อนแสดงข้อความจากโปรแกรม
ภาพที่ผู้ใช้แจ้งยังมี `{product_name}` และเลือกตั้งเวลาโดยไม่มีวัน/เวลา จึงไม่ควรปล่อยผ่าน prepare แต่ผู้ใช้ต้องสามารถบันทึกข้อมูลที่ยังกรอกไม่ครบและเห็นสาเหตุได้

## สิ่งที่แก้

- เพิ่ม autosave และปุ่ม **บันทึกข้อมูล** ใน `prepare_form.js`: บันทึกได้แม้ข้อมูลไม่ครบ โดยไม่สร้าง job/อัปโหลด/โพสต์
- ใช้ `chrome.storage.local` แยก channel/export/queue row; ปิด เปิดใหม่ และ reload extension document แล้วคืนค่าเดิม แยกจากข้อมูลต้นฉบับของ server
- บอกชัดว่าบันทึกไว้ใน extension ของเครื่องนี้ **ไม่ใช่การเขียนทับคิวส่วนกลาง** และไม่ปรับ runtime JSON ของจริง
- เรียง storage writes เพื่อไม่ให้ข้อความรุ่นเก่าทับข้อความที่พิมพ์ล่าสุด; ถ้าบันทึกล้มเหลวแสดงข้อผิดพลาดและให้ลองใหม่
- ใช้ custom validation แทน native required blocker: แจ้ง placeholder ที่ค้างพร้อมวัน/เวลาที่ขาดในครั้งเดียว ทำเครื่องหมาย aria-invalid และ focus ช่องแรกที่ต้องแก้
- แทน `{product_name}` เฉพาะเมื่อมีชื่อสินค้าจริงจาก item metadata; ถ้าไม่มีชื่อหรือเป็น placeholder อื่น ให้ผู้ใช้กรอกเอง ไม่แต่งข้อมูล
- คง guard ก่อน prepare/publish: schedule ต้องมีเวลาล่วงหน้าอย่างน้อย 15 นาทีและเป็นช่วง 5 นาที; เลือก draft จึงไม่ต้องมีวัน/เวลา; ยังห้าม unresolved placeholders
- กัน submit ซ้ำระหว่างรอบบันทึก และไม่เตรียม snapshot เก่าหากผู้ใช้เปลี่ยนค่าระหว่างบันทึก
- ขยับรุ่นเป็น 0.10.4 เพื่อให้ reload แล้วรับ code ใหม่

## ผลตรวจ

- Node extension + conductor **270/270 ผ่าน**, fail 0, skip 0
- Docked sidebar ใน Chromium ที่โหลด extension จริง **33/33 ผ่าน** รวมเคสใหม่:
  - บันทึกข้อความที่มี `{product_name}` และไม่มีเวลาโดยไม่เรียก backend prepare
  - แสดงข้อผิดพลาดครบ Caption/Date/Time เมื่อกดเตรียมข้อมูลแบบในภาพ
  - ปิด/เปิดฟอร์มแล้วคืนค่าที่บันทึก แทนการทับด้วย server caption เดิม
  - reload extension document แล้วอ่านค่าเดิมจาก Chrome storage จริง
  - ใช้ชื่อสินค้า metadata จริงแทน `{product_name}`; กรอกครบแล้ว prepare/claim ต่อได้
  - axe ผ่านทั้งธีมมืดและสว่าง; ตรวจภาพจริงของ dialog ใน sidebar แคบแล้ว
- Read-only backend smoke **27/27 ผ่าน** ด้วย `--allow-original-thumbnails`; queue/exports/pending hashes ก่อน–หลังตรงกัน ไม่มี API write และไม่มี console/page errors
- ข้อจำกัด resize เดิม: backend ที่รันยังส่งภาพปกขนาดเต็มแม้ขอ 160px; ไม่ได้แก้ backend ในงานนี้
- Python diagnostic compile และ diff check ผ่าน; ลบ screenshots/download/state ชั่วคราวหลังตรวจ

## ขอบเขต

ไม่ได้โพสต์หรือบันทึก Draft บนบัญชี TikTok จริง การตรวจ worker/UI ใช้ fixture transport ตามที่เครื่องมือระบุ; backend จริงตรวจแบบอ่านอย่างเดียว
งานนี้ไม่เปลี่ยนข้อจำกัด debug session ของรอบก่อน และไม่ลองเปิด profile ที่ถูก policy ปฏิเสธซ้ำ
Chrome ของผู้ใช้ต้อง reload extension แล้วเปิด sidebar ใหม่เพื่อรับ 0.10.4

## Jev

ก่อนเริ่มเลือก persist partial edits พร้อม validation, confidence 1.00 จากข้อความสรุป ไม่ใช่หลักฐานตรวจ implementation
ก่อน commit เลือกเฉพาะ source/tests/tools/work records, confidence 1.00; disclosure score 2.98/3, confidence 0.98, verdict proceed จากสรุป/เอกสารที่ส่ง ไม่ใช่การอ่านโค้ดแทน regression tests
