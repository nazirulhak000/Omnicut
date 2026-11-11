# Autopost Helper — เตรียมคลิปและเพิ่มความเสถียร

วันที่: 2026-11-12 · รุ่น: 0.10.3 · ดำเนินการโดย: Codex (GPT-6)
Round CODEX-AUTOPOST-PREPARE-AND-HARDENING-20261112

## ปัญหาที่ผู้ใช้แจ้งและพฤติกรรมใหม่

การ์ดมีปุ่มเตรียมคลิป แต่ caption ที่มี placeholder ถูก guard ปฏิเสธก่อนมีโอกาสแก้ข้อมูล ส่วนข้อความ “ใช้ไม่ได้” จากเงื่อนไข batch ทำให้เข้าใจว่าการเตรียมด้วยมือใช้ไม่ได้ด้วย

- กด **เตรียมคลิปนี้** เปิด native dialog ให้แก้ caption/hashtags และเลือก **ตั้งเวลาโพสต์** หรือ **บันทึกแบบร่าง** อย่างชัดเจน
- ถ้าตั้งเวลา ต้องระบุวัน/เวลาในอนาคตอย่างน้อย 15 นาที; caption ที่ยังมี placeholder ยังคงถูกห้าม และไฟล์ missing/posted/QC-rejected ไม่ถูกปล่อยผ่าน
- ยืนยันแล้วจึงส่ง prepare และ claim งาน ข้อมูลที่แก้ใช้กับ snapshot ของงานนั้น ไม่แก้คิวทั้งชุดหรือแต่งข้อความสินค้าแทนผู้ใช้
- ช่องเวลาเก่าถูกล้างเมื่อเลือก draft; ขั้นสุดท้ายใช้ Save draft และแสดงข้อความว่าไม่เผยแพร่ แทนการใช้ Post
- ข้อความบนการ์ดเปลี่ยนเป็น “ก่อนรันอัตโนมัติ” พร้อมบอกให้กดเตรียมเพื่อแก้ข้อมูล
- แยก validation/ฟอร์มเป็น `prepare_form.js` พร้อม behavioral tests; รักษาสไตล์เดิมและตรวจภาพ dialog บน sidebar จริง

## งานเสถียรภาพที่ทำต่อจากแผน

| ประเด็น | สิ่งที่แก้ |
| --- | --- |
| F3 Smart quota | เมื่อ schedule เต็มแต่ draft ว่าง preflight ยอมให้ Smart ใช้ draft ต่อ; schedule-only ยังคงต้องมีช่องตั้งเวลา |
| F4 Run ownership | ใช้ Web Locks serialize การแก้ lock ข้าม extension documents; worker ปฏิเสธ action จากแผงอื่นระหว่างรอบ; heartbeat หายต้องหยุดเริ่มขั้นตอนใหม่ |
| F5 Draft scan | ตรวจจำนวน Drafts ก่อน–หลัง scan ให้ครบ และอ่านบัญชีก่อน–หลัง; เมื่อ Drafts ไม่ครบ ห้ามสรุป deleted/posted-outside จากการไม่พบ |
| F6 Run context | ตรึงสำเนารายการก่อนรัน ป้องกันเปลี่ยนช่อง/โหมดระหว่างเริ่ม และตรวจ channel epoch หลัง await; แสดงข้อผิดพลาดแทน unhandled rejection |
| F7 Recovery | คง orphan marker จนคำสั่งพักงานสำเร็จ; ความล้มเหลวแสดงตามจริง ไม่ขึ้นว่าพักแล้ว |
| F8 บางส่วน | เพิ่ม deadline 30 วินาทีใน scoped panel fetch และแยกฟอร์ม/row evidence เป็นโมดูลทดสอบได้; การแยก DOM automation ทั้งก้อนเป็นงานโครงสร้างภายหลัง ไม่จำเป็นต่อการแก้ปุ่มนี้ |

คง posting protocol/attempt fence/receipt และการห้ามคลิกซ้ำหลัง attempt เดิมทั้งหมด

## ผลตรวจ

- Node extension + conductor: **266/266 ผ่าน**, fail 0, skip 0
- `tools/extension_p0_check.py`: **28/28 ผ่าน** บน docked sidebar ที่เปิดจริงใน Chromium profile แยก
  - ตรวจ P0 เดิม, กดปุ่มเตรียมการ์ดที่ข้อมูลไม่ครบ, แก้ caption/slot แล้ว prepare/claim ได้, ห้าม placeholder/ไม่มีเวลา
  - สอง extension documents แย่ง lock ได้เจ้าของเดียว; foreign manual action ถูก worker ปฏิเสธ
  - Recovery ล้มเหลวเก็บ marker; สำเร็จจึงล้าง
  - Save draft ผ่าน CDP click/DOM fixture จริง, baseline/unknown/no-duplicate และ cleanup
  - ฟอร์มอยู่ในขอบ sidebar และมีพื้นหลังทึบ; axe ไม่มี violation ทั้งธีมมืด/สว่างหลังรอ theme transition จบ
- `tools/extension_real_check.py`: **27/27 ผ่าน** ต่อ backend จริง ด้วย `--allow-original-thumbnails`; queue/exports/pending hashes ก่อน–หลังเท่ากัน ไม่มี API writes หรือ console/page errors
- Backend ที่รันยังตอบภาพปก 1080px แม้ขอ 160px; ภาพแสดงได้ตาม fallback แต่ยังไม่ผ่าน strict resize optimization เดิม
- Python diagnostic tools compile และ `git diff --check` ผ่าน
- Impeccable detector รันแล้ว: พบคำเตือน placeholder contrast ของ UI เดิม; ไม่เปลี่ยน palette/ตัวอักษรทั้งระบบในงานแก้ปุ่มนี้ ส่วน dialog ใหม่ตรวจ axe ผ่านทั้งสองธีม

## ขอบเขตที่ยังไม่ยืนยัน

การเผยแพร่และอ่าน Drafts บนบัญชี TikTok ที่ล็อกอินจริงยังไม่ได้ทดสอบ: การเปิด profile เดิมพร้อม debug ถูก policy ปฏิเสธในรอบก่อน ไม่มี session debug ที่เปิดไว้ และไม่ได้ลองข้ามข้อจำกัดนี้
การทดสอบปุ่มและ worker ใช้ HTTP/protocol fixtures ตามที่ระบุในเครื่องมือ ส่วน real-backend check เป็น read-only ไม่ใช่การโพสต์จริง

ผู้ใช้ต้อง reload extension ที่ `chrome://extensions` แล้วเปิด sidebar ใหม่เพื่อรับ 0.10.3; ไม่ได้ปิด/รีสตาร์ต Chrome หรือ backend ของผู้ใช้
ไม่เขียนทับไฟล์ runtime เดิมที่ dirty และไม่สร้างวิดีโอทดสอบในโฟลเดอร์ผลงาน

## Jev

ก่อนเริ่มเลือกแนวแก้แบบแก้ข้อมูลก่อนเตรียมโดยคง guards, confidence 1.00 จากสรุปข้อความ ไม่ใช่หลักฐานตรวจโค้ด
ตรวจเอกสาร: disclosure score 2.98/3, confidence 0.99; จัดประเภท protected paths ก่อน commit ได้ 0.62/2, confidence 0.08 → escalate ตามกฎโปรเจกต์
รายการ staged ที่ตรวจจริงมี 23 ไฟล์ เฉพาะ extension source/tests, diagnostic tools และ work records ไม่มี runtime JSON หรือ raw/assets; ขอคำยืนยันผู้ใช้ก่อน commit/merge และไม่เรียก Jev ซ้ำเพื่อเปลี่ยน gate
ผู้ใช้ตอบ “Commit และรวมกลับ main” เมื่อ 2026-11-12 จึงดำเนินการตามรายการที่ตรวจไว้ โดยเว้น runtime dirty ทุกไฟล์
