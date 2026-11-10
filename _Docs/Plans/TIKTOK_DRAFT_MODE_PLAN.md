# แผน: โหมด "บันทึกแบบร่าง" จริงในแผงข้าง extension (Draft Only + Smart Queue)

ผู้สั่ง: เจ้าของโปรเจกต์ (2026-11-10) · ดำเนินการโดย: Claude Code (Claude Sonnet 5.5)

## 1. ที่มา / ปัญหา
- แผงข้างเคยมีตัวเลือก Draft Only / Smart (ตั้งเวลา + แบบร่าง) แต่โค้ดไม่มีขั้น "บันทึกแบบร่าง" เลย: ขั้นส่งเรียก `click-post-only` ซึ่งกดปุ่ม Post → ถ้าไม่ได้ตั้งเวลา TikTok **โพสต์สดทันที**
- v0.3.10 เลยตัดตัวเลือกแบบร่างออกและให้ตัวรันหยุดเมื่อต้องเป็นแบบร่าง (กันโพสต์สดพลั้ง) → แผนนี้ทำของจริงให้ครบ

## 2. ข้อเท็จจริงจากหน้า TikTok จริง (ทดสอบ 2026-11-10 บัญชีเดียวกับงานจริง, ลบแบบร่างทดสอบแล้ว)
- ปุ่ม `button[data-e2e="save_draft_button"]` (ข้อความ "Save draft") อยู่ข้างปุ่ม Post (`post_video_button`) และ Discard (`discard_post_button`)
- กดแล้ว **ไม่มี toast** แต่หน้า navigate ภายใน ~1 วินาทีไป `/tiktokstudio/content?tab=draft`
- แท็บเปลี่ยนเป็น "Drafts N", มีแถวแบบร่าง: ภาพย่อ · ชื่อ = ข้อความคำอธิบาย · "Last update Nov 10, 2026, 12:05PM" · ปุ่มแก้ไข/ตัดต่อ/ลบ
- ข้อความบนหน้า: "You can save up to 30 drafts ... Drafts expire after 60 days" → เพดานแบบร่างจริง 30
- ลบแบบร่าง: ถังขยะ → "Delete draft?" → ปุ่ม Delete

## 3. การออกแบบ (ทุกชั้นสมเหตุสมผลกัน)
### 3.1 Backend (protocol v2)
- ผลลัพธ์ใหม่ `draft_saved` (final, ไม่ใช่โพสต์): หลักฐานที่ยอมรับ = `drafts_page_confirmed` (extension เห็น URL `tab=draft` + แถวแบบร่างตรง caption) หรือข้อความ "Draft saved"/"บันทึกแบบร่างแล้ว" หรือการยืนยันโดยคน; ต้องมี confirmation_token ตรงกับการกดของงานนี้ (เหมือนเดิม)
- งานแบบร่างต้อง **ไม่มีเวลานัด** (schedule_date/time ว่าง) และหลักฐานของ published/scheduled ห้ามใช้ `drafts_page_confirmed`
- คิว: สถานะใหม่ `draft_on_platform` ("บันทึกเป็นแบบร่างบน TikTok แล้ว") ไม่ใช่ posted · export ไม่ถูกย้ายไป Posted และไม่ถูกมาร์กโพสต์
- กันซ้ำ: งาน draft_saved ยัง "ไม่ cancelled" → prepare ซ้ำของ export เดียวกันถูกปฏิเสธ (ไม่สร้างแบบร่างซ้ำ)
- ทางกลับ (เมื่อผู้ใช้ลบแบบร่างบน TikTok แล้ว): PATCH สถานะ `planned` จาก `draft_on_platform` ได้ → ยกเลิก job แบบร่างพร้อม audit
### 3.2 Extension (worker)
- action `save-draft-only`: ตรวจบัญชี+ล็อกงานเหมือนกดโพสต์ (`beginPublish`) → กด `save_draft_button` (สำรอง: ข้อความ Save draft/บันทึกแบบร่าง) → รอ URL `tab=draft` (≤15 วิ) → ตรวจแถวแบบร่างในรายการ → ack `draft_saved` กับ backend
- action `verify-draft-content`: หลักฐานที่สอง — เปิด Content > Drafts หาแถว caption ตรงและ Last update ภายใน 15 นาที; ต้องไม่หลุดไป "Posts"
- ห้ามกดปุ่ม Post ในโหมดแบบร่างโดยเด็ดขาด (ตัวป้องกัน: ถ้าตั้งเวลา/เลือก Schedule อยู่ ไม่ใช่งานแบบร่าง → ล้ม)
### 3.3 แผงข้าง / orchestrator
- ขั้นส่งเลือก `save-draft-only` เมื่อ targetMode = draft, ไม่งั้น `click-post-only`; ตรวจซ้ำด้วย verify ตามชนิด
- ขั้นตั้งเวลาข้ามในโหมดแบบร่าง; guard เวลา (slot ผ่านแล้ว) ไม่ใช้กับแบบร่าง
- ตัวเลือกกลับมา: Schedule Only · Smart Queue (ตั้งเวลาจนโควตาเต็ม แล้วบันทึกแบบร่าง) · Draft Only
- โควตา: schedule เหลือ = 30 − ตั้งเวลาแล้ว; draft เหลือ = 30 − แบบร่าง (อ่านจากแท็บ "Drafts N" ที่มีอยู่แล้ว); smart = รวมสอง cap 30/รอบ; หยุดเมื่อแบบร่างเต็ม; Draft Only หยุดเมื่อแบบร่างเต็ม
- orchestrator เปิด `allowDraft: true` เฉพาะจากแผงข้าง (ค่าเริ่มต้นยังปฏิเสธ)
## 4. ขั้นตอน
1. backend + pytest → 2. worker + node tests → 3. แผงข้าง/orchestrator + tests → 4. e2e จริงบน TikTok: บันทึกแบบร่างจริง 1 คลิป, ตรวจหลักฐาน, ลบแบบร่าง, คืนคิว → 5. เอกสาร (ARCHITECTURE/TODO), ยก manifest 0.4.0
## 5. ความเสี่ยง
- ทดสอบจริงสร้างแบบร่างบนบัญชีจริง 1 อัน (เป็นส่วนตัว) ลบทิ้งหลังทดสอบ
- โครงหน้า TikTok เปลี่ยนได้ → ถ้าไม่เจอปุ่ม/แถว ให้ล้มพร้อมข้อความ ไม่เดา และไม่กดปุ่มอื่น
- frontend หลัก (React) แสดงสถานะคิวใหม่ไม่ได้แก้ในรอบนี้ ถ้าไม่มี fallback จะเห็นเป็นรหัสสถานะ
