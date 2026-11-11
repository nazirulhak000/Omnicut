# Autopost Helper P0 — ผลแก้และทดสอบ

วันที่ตรวจ: 2026-11-12 · รุ่น: 0.10.2 · ดำเนินการโดย: Codex (GPT-6)
รอบงาน: CODEX-AUTOPOST-P0-IMPLEMENTATION-20261111 (เริ่มก่อนเปลี่ยนวัน)

## พฤติกรรมที่แก้

1. **F1 — ตรวจแบบร่างไม่สำเร็จต้องหยุด:** `sidepanel.js` ตรวจ `check.ok` ก่อนกล่องยืนยันและ prepare; `draft_sync.js` ตรวจผลให้ครบทุก id ไม่ซ้ำ ไม่เกินขอบเขต และเป็นสถานะที่รู้จัก ผล unknown/error/ไม่ครบหรือเปลี่ยนช่องระหว่างตรวจต้องไม่เริ่มรัน
2. **F2 — ต้องยืนยันแบบร่างของคลิปนี้:** `draft_evidence.js` อ่านเฉพาะแถว Drafts ใช้ EP ที่ตรงกัน หรือ caption เต็มที่ตรงหนึ่งบรรทัด ไม่ค้น prefix ในข้อความทั้งหน้า ไม่ใช้ URL/count ยืนยันแทนคลิป และไม่ยอมรับหลายแถว/หลักฐานว่าง
3. ก่อน Save draft เปิดแท็บเบื้องหลังชั่วคราว อ่านรายการให้ครบตามจำนวนบนหน้าและตรวจบัญชี โดยรักษาฟอร์มอัปโหลดเดิม ต้องไม่มีรายการเดิมที่อาจเป็นคลิปนี้ แล้วเก็บ inventory ผูก job/channel ใน durable posting state ก่อน attempt
4. หลังคลิกต้องพบแถวที่ระบุคลิปได้หนึ่งแถวและไม่มีใน inventory เดิม บัญชีต้องตรงกับก่อนตรวจ; ถ้าหลักฐานไม่พอให้ `confirmation_unknown` ห้ามคลิกซ้ำ การ reconcile อัตโนมัติใช้เงื่อนไขเดียวกัน
5. งาน draft เก่าที่ไม่มี inventory ก่อนคลิกต้องตรวจและยืนยันด้วย flow manual เดิม ไม่เปลี่ยนข้อมูลเก่าเอง
6. แท็บ inventory ถูกปิดทั้งสำเร็จและล้มเหลว; bump manifest/Engine เป็น 0.10.2

## Gates

- Node extension + conductor regression suite: **259/259 ผ่าน**, fail 0, skip 0
  - คำสั่ง: `node --test --test-reporter=tap tiktok_autopost_extension/*.test.cjs tools/autopost_conductor/conductor.test.cjs`
  - ครอบคลุม response ขาด/ซ้ำ/ผิด id/สถานะ, หลักฐานเก่า/EP ต่าง/หลายแถว/ไม่มี baseline, inventory ล้มเหลว, บัญชีเปลี่ยน และงานเดิมของ extension/conductor
- **Sidebar ที่เปิด dock ข้างหน้าต่าง Chromium จริง: 17/17 ผ่าน** — `tools/extension_p0_check.py`
  - โหลด unpacked extension และ service worker จริง ใช้ runtime/storage/chrome.debugger จริง กด batch-start และกล่องยืนยันบน sidebar จริง
  - worker หลุด, ผลขาด, unknown ต้องไม่ผ่าน; ผลครบเปิดยืนยันได้; cancel ไม่ส่ง prepare
  - Save draft ผ่าน CDP DOM click จริงบนหน้า fixture; อ่าน inventory/new row จริง, เก็บผลครั้งเดียว, พบของเดิมไม่คลิกซ้ำ, inventory ไม่ครบไม่ consume attempt, ปิดแท็บชั่วคราวแม้ล้มเหลว
  - การคลิกที่ไม่สร้างคลิปใหม่แต่มีรายการเก่าคำขึ้นต้นเหมือนกันต้องบันทึก unknown ไม่ retry
  - HTTP/protocol และ preflight/upload-processing บางส่วนเป็น fixtures; ไม่ใช่การโพสต์ TikTok จริง
- **Extension ต่อ backend จริง: 27/27 ผ่านในโหมด compatibility รูปปก** — `tools/extension_real_check.py`
  - โหลดรายการจาก server จริง, version UI ตรง manifest, พรีวิววิดีโอจริง, keyboard tabs, theme/storage/reload, dialog/focus/Escape/Enter และ axe ในหน้าที่เครื่องมือทดสอบ
  - ไม่มี console/page error; ไม่ส่ง write request; hash ของ queue/exports/pending ก่อนและหลังตรงกัน
  - คำสั่ง: `.venv/Scripts/python.exe tools/extension_real_check.py .tmp/autopost-axe.min.js .tmp/autopost-real --allow-original-thumbnails`
  - **ข้อจำกัดที่เปิดเผย:** strict thumbnail resize gate ยังไม่ผ่าน เพราะ backend ที่รันอยู่ตอบภาพ 1080px แม้ขอ `w=160` การโหลด/แสดงภาพใช้งานได้; เครื่องมือคง strict mode เป็นค่าเริ่มต้น และต้องเปิด compatibility flag โดยชัดเจนจึงยอมรับภาพเต็ม
- Python diagnostic tools compile ผ่าน; `git diff --check` ผ่าน; ตรวจ screenshot ของ sidebar ด้วยตาแล้ว และลบภาพทดสอบหลังตรวจ

## ขอบเขตและงานค้าง

- ไม่ทดสอบการเผยแพร่/ตั้งเวลาบนบัญชี TikTok จริง และไม่ปรับคิว/exports/job ของจริงเพื่อทดสอบ
- ไม่ได้รัน full backend/frontend suite เพราะไม่มี backend/frontend app code เปลี่ยน; regression ที่รันครอบคลุม extension และ conductor ซึ่งใช้ worker เดียวกัน
- Caption ที่ถูกตัดจนไม่เห็น EP และระบุคลิปไม่ได้ชัดเจนยังต้อง unknown; ไม่ลดเงื่อนไขเพื่อรายงานสำเร็จ
- F3–F8 ในแผนยังเป็นงานรอบถัดไป รวม Smart quota, run-lock atomicity และ completeness ของ draft sync ทั้งสองฝั่ง
- ไม่รีสตาร์ต backend ที่กำลังทำงานเพื่อแก้ภาพย่อ; เป็นงาน performance แยกจาก P0
- Chrome ของผู้ใช้ต้อง reload extension ที่ `chrome://extensions` และเปิด sidebar ใหม่เพื่อรับ worker รุ่น 0.10.2; ไม่มีการปิดเบราว์เซอร์หรือรบกวน session ของผู้ใช้
- รักษา dirty runtime เดิมทั้งหมด รวม `_Docs/channel_artifacts.json`, `copilot_sessions.json`, `episodes.json`, `post_log.json`, `posting_jobs.json`, `schedule_queue.json`

## Jev

ก่อนเริ่มเลือกขอบเขต P0 confidence 1.00 จากข้อความสรุป ไม่ได้ตรวจไฟล์เอง และไม่ใช้แทน test evidence
ตรวจความพร้อมของสรุป implementation/เอกสาร: 3.16/4, confidence 0.58, verdict escalate (ส่งขณะผลทดสอบรอบสุดท้ายยังรอเก็บผล; ภายหลังเก็บผลได้ 259/259 และ 17/17 ตามข้างต้น)
ตาม confidence gate ใน `.agents/rules/jev_decision_layer.md` ต้องให้ผู้ใช้ตัดสินใจ จึงยังไม่ commit/merge หรือปิดรอบใน HISTORY จนกว่าจะได้รับคำตอบ ไม่เรียกซ้ำเพื่อเปลี่ยนคำตัดสิน

## การตรวจบัญชีจริงเพิ่มเติมตามคำตัดสินผู้ใช้

- 2026-11-12 ผู้ใช้เลือก “ทดสอบบัญชี TikTok จริงเพิ่มเติม” จึงขยายขอบเขตจาก fixtures ไปตรวจ session จริงแบบ read-only ก่อน
- ตรวจพบโปรไฟล์ `tools/tiktok_browser_profile` แต่ไม่มี Chrome process ที่เปิด debug session ของโปรไฟล์นี้ให้เชื่อมต่อ
- คำสั่ง `Start-Process` เปิด Chrome พร้อมโปรไฟล์ดังกล่าวและ `--remote-debugging-port=9333` ถูกระบบอนุมัติอัตโนมัติปฏิเสธก่อนรัน: `blocked by policy` ไม่มีเหตุผลละเอียดกว่านี้จากเครื่องมือ
- ไม่พยายามใช้วิธีอื่นเปิด debug session เดิมเพื่อข้ามการปฏิเสธ และไม่คัดลอก cookies/session ไปโปรไฟล์อื่น
- **สถานะ: ยังตรวจบัญชีจริงไม่ได้**; ผล 259/259, 17/17 และ 27/27 ข้างต้นยังเป็นผลตามขอบเขตที่อธิบายไว้ ไม่ใช่ผลเผยแพร่หรืออ่าน Drafts จากบัญชีจริง
- รอบยังเปิดใน TODO และยังไม่ commit/merge; งาน implementation พร้อม แต่การตรวจบัญชีจริงที่ผู้ใช้เพิ่มยังค้าง
