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

## 🎯 1. ภาพรวมโปรเจกต์ (Project Overview)

โปรเจกต์นี้คือ **OmniCut Pro Studio** (AI Video Production Suite) — ระบบ Automation Pipeline สำหรับสร้างและตัดต่อวิดีโอสั้นแนวตั้ง **9:16 (1080x1920)** อัตโนมัติด้วย Python, FastAPI, React/Vite และเชื่อมโยงกับ CapCut PC เพื่อผลิตคลิปรีวิวและขายสินค้าอย่างมีประสิทธิภาพ

---

## 📁 2. โครงสร้างโฟลเดอร์มาตรฐาน (Directory Structure)

AI ทุกตัว**ต้องเคารพโครงสร้างโฟลเดอร์นี้อย่างเคร่งครัด** ห้ามวางไฟล์กระจัดกระจายนอกโฟลเดอร์ที่กำหนด:

- `00_Inbox/`: ไฟล์ดิบ ไอเดีย สคริปต์ย่อ และไฟล์วิดีโอที่ sync จากมือถือ
- `01_Raw/`: วัตถุดิบต้นฉบับแยกตามโฟลเดอร์ `YYYYMMDD_ชื่อสินค้า-ประเด็น/`
- `02_Assets/`: Media Assets ส่วนกลางสำหรับนำไปใช้ซ้ำ
  - `Fonts/`: ฟอนต์มาตรฐาน (Kanit, Prompt, etc.)
  - `Music/`: เพลงประกอบ BGM
  - `SFX/`: เสียงเอฟเฟกต์ (Whoosh, Ding, Pop)
  - `Stickers_Memes/`: สติกเกอร์และป้าย Badge PNG โปร่งใส
  - `LUTs_ColorPresets/`: พรีเซ็ตสีวิดีโอ
- `03_Projects/`: ไฟล์โปรเจกต์ สคริปต์ (`script_brief.md`, `caption_draft.txt`) และดราฟต์งาน
- `04_Exports/`: วิดีโอที่ตัดต่อเสร็จ (`Ready_to_post/`, `Posted/`)
- `05_Covers_Thumbnails/`: ปกคลิปและ Thumbnail สัดส่วน 9:16
- `06_Archive/`: พื้นที่เก็บประวัติและสำรองไฟล์เก่าหลังโพสต์ 30 วัน
- `scripts/`: Backend Engine & Pipeline หลัก (FastAPI, TTS, Subtitles, Scraper, Editor)
- `tools/`: สคริปต์ Utility เสริม (ดาวน์โหลดฟอนต์, เจนป้าย 3D, จัดการ Asset)
- `frontend/`: Web Application UI (React + Vite)
- `.agents/rules/`: กฎเฉพาะทาง เช่น การเจนสติกเกอร์ ([sticker_generation.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/sticker_generation.md)), มาตรฐาน UI คลีนไร้สัญลักษณ์ซ้ำซ้อน ([ui_clean_standard.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/ui_clean_standard.md)) และ **กฎ Preview = Render** ([preview_render_parity.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/preview_render_parity.md))

---

## ⛔ 3. กฎเหล็ก: สิ่งที่ "ห้ามทำเด็ดขาด" (STRICT DON'Ts)

1. ❌ **ห้ามลบหรือเขียนทับไฟล์ใน `01_Raw/` และ `02_Assets/`** โดยไม่ได้รับการยืนยันจาก User โดยเด็ดขาด เพราะเป็นไฟล์วัตถุดิบต้นฉบับ
2. ❌ **ห้าม Hardcode Absolute Path แบบตายตัว** (เช่น `C:\Users\...` หรือ `D:\Winona\...`) ให้ใช้ `pathlib.Path` หรือดึงค่าจาก `scripts/config.py` เสมอ เพื่อให้รันได้ทุกเครื่อง
3. ❌ **ห้ามแก้ไขไฟล์ดราฟต์ของ CapCut (`draft_content.json` หรือ `.cloud_cache_*`) โดยไม่มีการ Backup** เพราะโครงสร้าง JSON ของ CapCut ไวต่อความผิดพลาดมาก หากไฟล์เสียจะกู้คืนไม่ได้
4. ❌ **ห้ามรันคำสั่งทำลายล้างหรือล้างแคชหมู่** (เช่น ลบโฟลเดอร์ทั้งชุด) โดยไม่มี User Confirmation
5. ❌ **ห้ามติดตั้ง Global Python Package นอกเหนือจาก `requirements.txt`** หรือติดตั้งโดยไม่ผ่าน Virtual Environment
6. ❌ **ห้ามสร้างสติกเกอร์ที่ระบุข้อความเจาะจงเฉพาะสินค้า** (เช่น เขียนชื่อรุ่นสินค้าลงในรูป) ให้สร้างเฉพาะ **Universal Reusable Badges (6 รูปแบบมาตรฐาน)** เพื่อให้ใช้ซ้ำได้กับทุกคลิป
7. ❌ **ห้ามใส่จุดไข่ปลา หรือ "..." หรือ "…" ในบทพูดสคริปต์เด็ดขาด** ให้ใช้การเว้นวรรคตามธรรมชาติ เพราะจุดไข่ปลาจะหลุดไปติดในซับไตเติลบนหน้าจอ ทำให้ดูรกและผู้ใช้ต้องมานั่งลบเอง
8. ❌ **ห้ามใส่สัญลักษณ์หรือตัวอักษรซ้ำซ้อนในปุ่มหรือ UI เด็ดขาด (Strict No-Redundant Symbols in UI):** ห้ามใส่เครื่องหมายบวก `+` นำหน้าข้อความเมื่อมีไอคอน `<Upload />` หรือ `<Plus />` อยู่แล้ว และห้ามใส่อีโมจิซ้อนหน้าข้อความเมื่อมีไอคอน Lucide แสดงอยู่แล้ว (เช่น ห้ามทำ `<Upload /> + แนบคลิป` หรือ `<Play /> ▶️ เปิดดู`) ต้องปฏิบัติตาม [.agents/rules/ui_clean_standard.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/ui_clean_standard.md) เสมอ ทั้งระบบต้องเป็นมาตรฐานเดียวกัน 100% ห้ามมีซ้ำซ้อน
9. ❌ **ห้ามทับศัพท์ชื่อแบรนด์ ชื่อรุ่น หรือศัพท์เทคนิคเฉพาะทางที่เป็นภาษาอังกฤษให้เป็นภาษาไทยเด็ดขาด (Strict English Retention for Brands & Tech Specs):** ในบทพูดสคริปต์ ซับไตเติล และข้อความพากย์ ห้ามแปลงชื่อแบรนด์ ชื่อรุ่น หรือศัพท์เฉพาะเป็นภาษาไทยทับศัพท์เพี้ยนๆ (เช่น ห้ามเขียน "โลจิเทค เวฟ คีย์ส", "โลจิ โบลต์", "บลูทูธ", "ยูเอสบีซี") ต้องคงรูปภาษาอังกฤษทางการไว้เสมอ (เช่น "Logitech Wave Keys", "Logi Bolt", "Bluetooth", "USB-C", "iPad", "Mac") เพื่อความน่าเชื่อถือ ตรงปก และแสดงผลบนหน้าจอได้อย่างมืออาชีพ

---

## ✅ 4. กฎเหล็ก: สิ่งที่ "ต้องทำเสมอ" (STRICT DOs)

1. ✔️ **คุมสเปกวิดีโอมาตรฐาน 9:16:**
   - ความละเอียด: `1080x1920` พิกเซล
   - เฟรมเรต: `30 FPS`
   - Safe Zone: เลเยอร์ข้อความ/สติกเกอร์ต้องไม่ชิดขอบจอขวาหรือล่าง เพื่อไม่ให้ถูกปุ่ม TikTok บดบัง
2. ✔️ **ตั้งชื่อตาม Naming Convention เสมอ:**
   - โฟลเดอร์ Raw: `YYYYMMDD_ชื่อสินค้า-ประเด็น` (เช่น `20260812_ลิปสติกABC-รีวิว`)
   - ไฟล์ Export: `YYYYMMDD_ชื่อสินค้า_hookสั้นๆ_vN.mp4`
   - ชื่อ CapCut Draft ต้องตรงกับชื่อโฟลเดอร์โปรเจกต์
3. ✔️ **การจัดการภาษาไทยและซับไตเติล (Micro-Burst & Kinetic Subtitles):**
   - ต้องปฏิบัติตาม [.agents/rules/subtitle_kinetic_rules.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/subtitle_kinetic_rules.md)
   - ใช้ `pythainlp` ในการตัดคำสำหรับ Subtitle Bursts สั้นกระชับ (2–4 คำ / 16–24 ตัวอักษร)
   - ไฮไลต์สีคำสำคัญแบบไดนามิกคู่ขนานทั้งไทยและอังกฤษ (Bilingual Dynamic Kinetic Highlighting เช่น เหลืองนีออน `#FFE600` บน Pain Point และราคา)
   - ตรวจสอบปัญหาสระลอย/วรรณยุกต์ซ้อน และระยะห่างการแสดงผล Safe Zone ล่าง 420px เสมอ
4. ✔️ **การเจนสติกเกอร์และป้าย (Sticker Rules):**
   - ต้องปฏิบัติตาม [.agents/rules/sticker_generation.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/sticker_generation.md)
   - เจน 1 รูปได้ 6 ป้าย (Grid 2x3: PROS, CONS, WARNING, PRO TIP, SCORE, VERDICT)
   - พื้นหลังต้องเป็น **Solid Pure White (#FFFFFF)** ขอบ **Thick White Die-cut Border** เพื่อให้ตัดพื้นหลังโปร่งใสด้วย `rembg` ได้เนียน 100%
5. ✔️ **TTS & Audio Standards:**
   - เสียงพากย์หลัก: Edge-TTS ภาษาไทย (`th-TH-PremwadeeNeural`, `th-TH-NiwatNeural`) ความเร็ว `+15%`
   - มีระบบ Fallback ไปยัง Gemini Flash TTS หรือ gTTS เมื่อจำเป็น
   - ระดับเสียง (แหล่งเดียวที่ `scripts/config.py`): Voice = 1.0, SFX = 0.28, BGM = 0.12 — พรีวิวใช้ค่าเดียวกันผ่าน `AUDIO_MIX` ใน `SequencePlayer.jsx` และมีเทสยึดไว้ที่ `tests/test_preview_render_parity.py`
6. ✔️ **Code Reliability & Subprocess:**
   - การเรียกใช้ FFmpeg / ImageMagick / Rembg ต้องรันผ่าน subprocess พร้อม error handling และ log ข้อความภาษาไทยที่เข้าใจง่าย
7. ✔️ **มาตรฐานการตัดต่อแบบ J-Cut (Audio Lead-in Standard):**
   - ต้องปฏิบัติตาม [.agents/rules/j_cut_rules.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/j_cut_rules.md)
   - ใช้เทคนิค **J-Cut** ในการตัดต่อสลับช็อต B-roll: เสียงประโยคถัดไป (หรือ SFX Whoosh ข้ามฉาก) ต้องดังขึ้นก่อนภาพตัดเปลี่ยน 150 – 250ms เพื่อลดความแข็งกระด้างของการตัดแบบกระตุก (Avoid Jarring Jump Cuts) และสร้างความอยากรู้ล่วงหน้า (Anticipation) ให้คนดูติดตามต่อจนจบ
8. ✔️ **มาตรฐาน UI คลีนและสถานะตามโฟลว์จริง (Clean & Unified UI Standard):**
   - ต้องปฏิบัติตาม [.agents/rules/ui_clean_standard.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/ui_clean_standard.md)
   - ข้อความปุ่มต้องกระชับ ตรงไปตรงมา ขึ้นต้นด้วยคำกริยาแอ็กชันทันทีโดยไม่มีสัญลักษณ์นำหน้า
   - สถานะคลิปต้องสะท้อนความเป็นจริงเท่านั้น: มีโฟลเดอร์โปรเจกต์ในไทม์ไลน์แต่ยังไม่เรนเดอร์ = `กำลังตัดต่อ` (`in_production`), มีไฟล์ MP4 ที่ Export เสร็จสิ้นจริง = `ตัดต่อเสร็จ` (`rendered`) ห้ามมีปุ่มเลื่อนข้ามสถานะเองโดยไม่ผ่านการทำงานจริง
9. ✔️ **กฎ Preview = Render (บังคับทุกครั้งที่เพิ่ม/แก้ฟีเจอร์ในหน้า Editor ที่มีผลต่อภาพในวิดีโอ):**
   - **ต้องอ่านและปฏิบัติตาม [.agents/rules/preview_render_parity.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/preview_render_parity.md) ทุกรอบ** ก่อนแตะ `frontend/src/components/SequencePlayer.jsx` หรือ `scripts/subtitle_engine.py`
   - ระบบมี 2 engine วาดภาพเดียวกันคนละทาง (Canvas 2D ฝั่งพรีวิว / ASS+libass ฝั่งเรนเดอร์) — **ห้ามแก้ข้างเดียว** ต้องแก้คู่กันในงานเดียว
   - ค่าคงที่ทุกตัวที่กำหนดภาพ (ratio, ระยะเวลา ms, factor, องศา, ความทึบ) ต้องเทียบกันได้เป็นตัวเลข และมี assertion ใน `tests/test_preview_render_parity.py`
   - กับดักที่เคยหลุดจริงและต้องระวังทุกครั้ง: ASS `\alpha` = ความ**โปร่ง** (ต้องแปลง `1 - 0xNN/255` ไม่ใช่ก็อปเลข), องศาหมุนต้องใช้เลขติดลบ (`-3` ไม่ใช่ `357` เพราะ `\t` จะกวาดอ้อม 180°), `strokeText` วางเส้นกึ่งกลางจึงต้องคูณสองจาก ASS Outline, libass เดินบรรทัดละ 1.0× font size พอดี
   - ห้ามสรุปว่า "ตรงแล้ว" จากการอ่านโค้ด — ต้อง **เรนเดอร์จริงด้วย ffmpeg แล้วดึงเฟรมมาดู/วัดพิกเซล** (motion ต้องดูหลายเฟรม: เข้า/ค้าง/ออก)
10. ✔️ **วางแผนลง Todo กลางก่อนลงมือ ทุกรอบ (Plan-Before-Code):**
   - **ต้องอ่านและปฏิบัติตาม [.agents/rules/work_loop.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/work_loop.md) ทุกรอบ**
   - ไฟล์ Todo กลางมีที่เดียวคือ [TODO.md](file:///d:/Winona/Programmer/Capcut/TODO.md) — **ห้ามแตกไฟล์ todo ใหม่**
   - **แผนต้องอยู่ในโปรเจกต์** ห้ามทิ้งไว้ใน `.claude/plans/` (เป็นแค่กระดาษทดของเครื่องมือ User มองไม่เห็น) — งานใหญ่ให้เพิ่มไฟล์ `<ชื่องาน>_PLAN.md` ที่รากโปรเจกต์
   - **ปิดรอบแล้วต้องย้ายบล็อกเต็มไป [HISTORY.md](file:///d:/Winona/Programmer/Capcut/HISTORY.md)** + เพิ่มแถวในตารางสารบัญ แล้วเหลือชื่อรอบบรรทัดเดียวใน `TODO.md`
   - ลำดับบังคับ: อ่าน `TODO.md` + `git status` → **เขียนแผนรอบนี้ลง `TODO.md` ก่อนแตะโค้ด** → ทำ → รัน Gate จริง → ติ๊กเฉพาะที่ผ่าน → เขียน Notes ที่มีตัวเลขจริง
   - **ห้ามติ๊ก `[x]` เพราะเขียนโค้ดเสร็จ** ต้องผ่าน Gate ของข้อนั้นก่อน และห้ามลบข้อที่ทำไม่สำเร็จทิ้ง
   - **งานใหม่ที่โผล่กลางทาง (บั๊กที่เจอ / user สั่งเพิ่ม) ต้องเขียนลง `TODO.md` ทันที** แล้วตัดสินใจว่าทำรอบนี้หรือคาไว้ใน Backlog พร้อมเหตุผล — ห้ามทำเงียบๆ
   - ก่อนเริ่มต้องเช็คว่ามี AI หรือคนอื่นแก้ไฟล์เดียวกันค้างอยู่ไหม ถ้าซ้ำให้ถาม User ก่อน (เคยเกิดจริงจนแยก commit ไม่ได้)
11. ✔️ **เขียนและรัน Test ตามชนิดงาน:**
   - ต้องอ่านและทำตาม [.agents/rules/testing_standard.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/testing_standard.md)
   - Test ต้อง deterministic/offline และใช้ temp storage ห้ามแก้ข้อมูลจริงใน `01_Raw/`, `02_Assets/`, `03_Projects/` หรือ `_Docs/post_log.json`
   - ห้ามเพิ่ม manual script ที่มี side effect เป็น `tests/test_*.py`; ให้ย้ายไป `tools/`
   - การแก้ visual contract ต้องมีทั้ง parity test และ FFmpeg behavioral render พร้อมตรวจหลายเฟรม

---

## 🧩 5. แผนผังโมดูลสำคัญ (Key Modules Reference)

| โมดูล / สคริปต์ | หน้าที่การทำงาน |
| :--- | :--- |
| `scripts/config.py` | ศูนย์รวมการตั้งค่า Path, สเปกวิดีโอ, เสียง TTS, และระดับเสียง |
| `scripts/api_server.py` | FastAPI app factory/mount point; route จริงแยกอยู่ใน `scripts/api_*.py` |
| `scripts/api_schemas.py` | Pydantic request schemas ที่ router ใช้ร่วมกัน |
| `scripts/media_service.py` | Path validation, metadata, streaming helpers |
| `scripts/pipeline.py` | Orchestrator ที่ส่งงานผ่าน modular stages |
| `scripts/pipeline_context.py` | State และ artifact contract ระหว่าง pipeline stages |
| `scripts/stages/` | Source, Script, Voice, Subtitle, Audio Mix, Shot Matching และ Video Assembly |
| `scripts/voice_engine.py` | ตัวจัดการสร้างเสียงสังเคราะห์ (Edge-TTS / gTTS) |
| `scripts/gemini_tts_engine.py` | โมดูลแปลงเสียงด้วย Gemini Flash Audio Model |
| `scripts/subtitle_engine.py` | Facade สำหรับสร้าง `.srt` / `.ass`; implementation ย่อยอยู่ใน `scripts/subtitle/` |
| `scripts/overlay_model.py` | Overlay model ฝั่ง renderer ที่ mirror กับ frontend |
| `scripts/product_scraper.py` | ดึงข้อมูล รายละเอียด และจุดขายสินค้าจากลิงก์ |
| `tools/build_3d_pro_badges.py` | สร้างและตัดแยกชุดป้ายรีวิว 3D อัตโนมัติ |
| `frontend/src/lib/editorProjectState.js` | Manifest migration และ serializer กลางของ Save/Autosave |
| `frontend/src/hooks/` | Project load/autosave, render job, commands, selection, layout และ cleanup |
| `frontend/src/lib/timelineSchema.js` | Timeline Document v2 และ in-memory legacy migration |
| `frontend/src/components/SequencePlayer.jsx` | Canvas/audio preview ที่ต้องรักษา parity กับ renderer |

---

## 💻 6. วิธีการรันระบบและคำสั่งทดสอบ (Run & Test Commands)

- **รันระบบทั้งหมด (One-Click):**
  ```bat
  start_app.bat
  ```
- **รันเฉพาะ Backend API:**
  ```bash
  python scripts/api_server.py
  ```
- **รันเฉพาะ Frontend UI:**
  ```bash
  cd frontend
  npm run dev
  ```
- **รัน Gate มาตรฐาน:**
  ```powershell
  python -m compileall -q scripts
  python -m pytest tests/ -q -p no:cacheprovider --tb=short
  Set-Location frontend
  npm test
  npm run build
  ```

---

## 🗣️ 7. แนวทางการสื่อสารของ AI (Communication Guidelines)

- ตอบคำถามและอธิบายงานเป็น **ภาษาไทย** สุภาพ ชัดเจน กระชับ และตรงประเด็น
- เมื่อเสนอโค้ด ให้ระบุ Path แบบเต็มและอธิบายเหตุผลของการเปลี่ยนแปลงสั้นๆ
- หากพบความเสี่ยงที่อาจทำให้ไฟล์สูญหาย ต้องหยุดและแจ้งเตือนผู้ใช้ก่อนเสมอ
