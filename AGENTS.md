# 🤖 AI Agent Guidelines & Project Rules (CapCut Video Production)

คู่มือและกฎเหล็กสำหรับ AI Coding Assistants (Claude Code, Cursor, Copilot, Gemini CLI, ChatGPT) ในการทำงาน พัฒนาโค้ด และส่งต่องานในโปรเจกต์นี้

> ## 🛑 อ่านก่อนแตะโค้ดบรรทัดแรก — ทุกครั้ง ทุกงาน ไม่ว่าเล็กหรือใหญ่
>
> 1. เปิด **[TODO.md](file:///d:/Winona/Programmer/Capcut/TODO.md)** ดูว่ารอบก่อนค้างอะไร
>    (รอบที่ปิดแล้วอยู่ใน **[HISTORY.md](file:///d:/Winona/Programmer/Capcut/HISTORY.md)**)
> 2. รัน `git status` ดูว่ามีงานของใครค้างใน working tree อยู่หรือเปล่า
> 3. **เขียนแผนของรอบนี้ลง `TODO.md` ก่อน** แล้วค่อยลงมือ — เอกสารแผนต้องอยู่ในโปรเจกต์เสมอ
>    ห้ามทิ้งไว้ใน `.claude/plans/` หรือโฟลเดอร์ชั่วคราว เพราะเจ้าของโปรเจกต์มองไม่เห็น
> 4. **ปิดรอบแล้วย้ายบล็อกไป `HISTORY.md`** เหลือชื่อรอบบรรทัดเดียวใน `TODO.md`
>
> รายละเอียดทั้งหมดอยู่ที่ **[.agents/rules/work_loop.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/work_loop.md)**
> — ถ้ามันไม่ได้อยู่ใน `TODO.md` แปลว่ามันไม่ได้เกิดขึ้น
>
> โครงสร้างระบบล่าสุดอยู่ที่ **[ARCHITECTURE.md](file:///d:/Winona/Programmer/Capcut/ARCHITECTURE.md)** และกฎทดสอบอยู่ที่ **[.agents/rules/testing_standard.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/testing_standard.md)**

---

## 🎯 1. ภาพรวม — **OmniCut Pro Studio**: pipeline อัตโนมัติทำคลิปแนวตั้ง **9:16 (1080x1920)** (Python/FastAPI/React/Vite + CapCut PC)

---

## 📁 2. โครงสร้างโฟลเดอร์ — ห้ามวางไฟล์นอกที่กำหนด: `00_Inbox/` ดิบ / `01_Raw/` วัตถุดิบ (`YYYYMMDD_ชื่อสินค้า-ประเด็น/`) / `02_Assets/` ของใช้ซ้ำ (Fonts/Music/SFX/Stickers/LUTs) / `03_Projects/` สคริปต์+ดราฟต์ / `04_Exports/` คลิปเสร็จ / `05_Covers_Thumbnails/` ปก 9:16 / `06_Archive/` เก็บเก่า (ถูก gitignore) / `scripts/` backend / `tools/` utility / `frontend/` UI / `_Docs/` PRD·prompt·รายงานปฏิบัติการ / `.tmp/` ของชั่วคราวจากเทส (ถูก gitignore) / `.agents/rules/` กฎเฉพาะทาง — **ไฟล์แผน/รายงานของรอบงาน (`*_PLAN.md`, `*_REPORT_*`, `*_AUDIT_*`, `*_VERIFY_*`) อยู่ที่รากโปรเจกต์ ห้ามย้าย**

---

## ⛔ 3. กฎเหล็ก: สิ่งที่ "ห้ามทำเด็ดขาด" (STRICT DON'Ts) — รายละเอียดเต็มดูไฟล์กฎที่อ้างท้ายข้อ

1. ❌ **ห้ามลบ/เขียนทับไฟล์ใน `01_Raw/` และ `02_Assets/`** โดยไม่ได้รับยืนยันจาก User
2. ❌ **ห้าม Hardcode Absolute Path** — ใช้ `pathlib.Path` หรือ `scripts/config.py` (ดูข้อ 2 โครงสร้างโฟลเดอร์)
3. ❌ **ห้ามแก้ไฟล์ดราฟต์ CapCut (`draft_content.json`/`.cloud_cache_*`) โดยไม่มี Backup**
4. ❌ **ห้ามรันคำสั่งทำลายล้าง/ล้างแคชหมู่** โดยไม่มี User Confirmation
5. ❌ **ห้ามติดตั้ง Global Python Package นอก `requirements.txt`** หรือนอก venv
6. ❌ **ห้ามสร้างสติกเกอร์ระบุข้อความเฉพาะสินค้า** — ทำเฉพาะ Universal Badges 6 แบบ (ดู [.agents/rules/sticker_generation.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/sticker_generation.md))
7. ❌ **ห้ามใส่ "..."/"…"/จุดไข่ปลาในบทพูดสคริปต์** — ใช้เว้นวรรคธรรมชาติ (กันหลุดเข้าซับ)
8. ❌ **ห้ามใส่สัญลักษณ์ซ้ำซ้อนในปุ่ม/UI** (เช่น `<Upload /> + แนบคลิป`) (ดู [.agents/rules/ui_clean_standard.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/ui_clean_standard.md))
9. ❌ **ห้ามทับศัพท์ชื่อแบรนด์/รุ่น/ศัพท์เทคนิคอังกฤษเป็นไทย** (เช่น ห้าม "บลูทูธ" ให้ใช้ "Bluetooth", "USB-C")
10. ❌ **ห้ามงานอื่นกระทบฟอนต์/ข้อความโดยไม่สั่ง** — ไม่เปลี่ยน family/ขนาด/weight/outline/ตัดบรรทัด/ตำแหน่ง/safe zone (ดู [.agents/rules/font_text_visual_contract.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/font_text_visual_contract.md))

---

## ✅ 4. กฎเหล็ก: สิ่งที่ "ต้องทำเสมอ" (STRICT DOs)

1. ✔️ **สเปกวิดีโอ 9:16** — `1080x1920`, `30 FPS`, ข้อความ/สติกเกอร์ห้ามชิดขอบขวา-ล่าง (กันปุ่ม TikTok บัง)
2. ✔️ **Naming Convention** — Raw: `YYYYMMDD_ชื่อสินค้า-ประเด็น` / Export: `YYYYMMDD_ชื่อสินค้า_hook_vN.mp4` / Draft ตรงชื่อโฟลเดอร์
3. ✔️ **ซับไทย Micro-Burst/Kinetic** — burst 2–4 คำ, ไฮไลต์ `#FFE600`, safe zone ล่าง 420px (ดู [.agents/rules/subtitle_kinetic_rules.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/subtitle_kinetic_rules.md))
4. ✔️ **สติกเกอร์** — เฉพาะ Universal Badges 6 แบบ, พื้นขาว `#FFFFFF` + ขอบ die-cut (ดู [.agents/rules/sticker_generation.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/sticker_generation.md))
5. ✔️ **TTS/Audio** — Edge-TTS ไทย `+15%`, ระดับเสียง Voice 1.0 / SFX 0.28 / BGM 0.12 ที่ `scripts/config.py`
6. ✔️ **Subprocess (FFmpeg/Rembg)** — รันผ่าน subprocess + error handling + log ไทย
7. ✔️ **J-Cut** — เสียงช็อตถัดไปมาก่อนภาพ 150–250ms (ดู [.agents/rules/j_cut_rules.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/j_cut_rules.md))
8. ✔️ **UI คลีน + สถานะตามจริง** — ปุ่มขึ้นต้นกริยาไม่มีสัญลักษณ์นำ, สถานะ `in_production`/`rendered` ตามของจริงเท่านั้น (ดู [.agents/rules/ui_clean_standard.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/ui_clean_standard.md))
9. ✔️ **Preview = Render** — แก้ `SequencePlayer.jsx`/`subtitle_engine.py` ต้องแก้คู่ + เทส `test_preview_render_parity.py` + เรนเดอร์ ffmpeg ดูเฟรมจริง (ดู [.agents/rules/preview_render_parity.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/preview_render_parity.md))
10. ✔️ **Plan-Before-Code** — เขียนแผนลง `TODO.md` ก่อนแตะโค้ด ปิดรอบย้ายเข้า `HISTORY.md` (ดู [.agents/rules/work_loop.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/work_loop.md))
11. ✔️ **Test ตามชนิดงาน** — deterministic/offline + temp storage ห้ามแตะข้อมูลจริง (ดู [.agents/rules/testing_standard.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/testing_standard.md))
12. ✔️ **Font/Text Golden Master** — caption 1080x1920: em 50px / ASS 82 / EN 68% / line 1.0 / margin ล่าง 420px ห้าม drift, probe ด้วย .venv (ดู font_text_visual_contract.md)
13. ✔️ **ประหยัดโทเคน** — ห้ามเปิดไฟล์ใหญ่/HISTORY.md ทั้งไฟล์, ส่องไม่เกิน 100 บรรทัด, ห้ามสกิลไม่เกี่ยว (ดู token-efficiency-guardian/SKILL.md)
14. ✔️ **ระบุตัวตนเอเจนต์+โมเดลทุกบล็อก** — ทั้งหัวบล็อกและสารบัญ (สืบย้อนว่าใครทำพังได้)
   - ในโปรเจกต์นี้มี AI หลายตัวทำขนานกัน ทุกบล็อกต้องมี `ดำเนินการโดย: <เอเจนต์> (<โมเดล>)`
   - **ทุกครั้งที่บันทึกรอบงานลง TODO/HISTORY** ทั้งหัวบล็อกและสารบัญต้องระบุชื่อเอเจนต์+โมเดล เช่น:
     - `ดำเนินการโดย: Antigravity (Gemini 2.5 Pro)`
     - `ดำเนินการโดย: Claude Code (Claude 3.7 Sonnet)`
     - `ดำเนินการโดย: Cursor (Claude 3.5 Sonnet)`
   - **วัตถุประสงค์:** โปร่งใส สืบย้อนได้ว่าโมเดลตัวไหนรับผิดชอบงานนั้น

---

## 🧩 5. แผนผังโมดูลสำคัญ — ดู [ARCHITECTURE.md](file:///d:/Winona/Programmer/Capcut/ARCHITECTURE.md) (backend: `scripts/config.py`, `pipeline.py`, `stages/`, `subtitle_engine.py` / frontend: `SequencePlayer.jsx`, `editorProjectState.js`, `hooks/`)

---

## 💻 6. วิธีรัน+เทส — ดู [.agents/rules/testing_standard.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/testing_standard.md) (รันเต็ม: `start_app.bat` / `pytest tests/` + `npm test` + `build`)

---

## 🗣️ 7. แนวทางการสื่อสารของ AI (Communication Guidelines)

- ตอบคำถามและอธิบายงานเป็น **ภาษาไทย** สุภาพ ชัดเจน กระชับ และตรงประเด็น
- เมื่อเสนอโค้ด ให้ระบุ Path แบบเต็มและอธิบายเหตุผลของการเปลี่ยนแปลงสั้นๆ
- หากพบความเสี่ยงที่อาจทำให้ไฟล์สูญหาย ต้องหยุดและแจ้งเตือนผู้ใช้ก่อนเสมอ
