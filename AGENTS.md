# 🤖 AI Agent Guidelines & Project Rules (CapCut Video Production)

คู่มือและกฎเหล็กสำหรับ AI Coding Assistants (Claude Code, Cursor, Copilot, Gemini CLI, ChatGPT) ในการทำงาน พัฒนาโค้ด และส่งต่องานในโปรเจกต์นี้

---

## 🎯 1. ภาพรวมโปรเจกต์ (Project Overview)

โปรเจกต์นี้คือ **TikTok Auto-Cutter Pro Studio** — ระบบ Automation Pipeline สำหรับสร้างและตัดต่อวิดีโอสั้นแนวตั้ง **9:16 (1080x1920)** อัตโนมัติด้วย Python, FastAPI, React/Vite และเชื่อมโยงกับ CapCut PC เพื่อผลิตคลิปรีวิวและขายสินค้าอย่างมีประสิทธิภาพ

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
- `.agents/rules/`: กฎเฉพาะทาง เช่น การเจนสติกเกอร์ ([sticker_generation.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/sticker_generation.md))

---

## ⛔ 3. กฎเหล็ก: สิ่งที่ "ห้ามทำเด็ดขาด" (STRICT DON'Ts)

1. ❌ **ห้ามลบหรือเขียนทับไฟล์ใน `01_Raw/` และ `02_Assets/`** โดยไม่ได้รับการยืนยันจาก User โดยเด็ดขาด เพราะเป็นไฟล์วัตถุดิบต้นฉบับ
2. ❌ **ห้าม Hardcode Absolute Path แบบตายตัว** (เช่น `C:\Users\...` หรือ `D:\Winona\...`) ให้ใช้ `pathlib.Path` หรือดึงค่าจาก `scripts/config.py` เสมอ เพื่อให้รันได้ทุกเครื่อง
3. ❌ **ห้ามแก้ไขไฟล์ดราฟต์ของ CapCut (`draft_content.json` หรือ `.cloud_cache_*`) โดยไม่มีการ Backup** เพราะโครงสร้าง JSON ของ CapCut ไวต่อความผิดพลาดมาก หากไฟล์เสียจะกู้คืนไม่ได้
4. ❌ **ห้ามรันคำสั่งทำลายล้างหรือล้างแคชหมู่** (เช่น ลบโฟลเดอร์ทั้งชุด) โดยไม่มี User Confirmation
5. ❌ **ห้ามติดตั้ง Global Python Package นอกเหนือจาก `requirements.txt`** หรือติดตั้งโดยไม่ผ่าน Virtual Environment
6. ❌ **ห้ามสร้างสติกเกอร์ที่ระบุข้อความเจาะจงเฉพาะสินค้า** (เช่น เขียนชื่อรุ่นสินค้าลงในรูป) ให้สร้างเฉพาะ **Universal Reusable Badges (6 รูปแบบมาตรฐาน)** เพื่อให้ใช้ซ้ำได้กับทุกคลิป
7. ❌ **ห้ามใส่จุดไข่ปลา หรือ "..." หรือ "…" ในบทพูดสคริปต์เด็ดขาด** ให้ใช้การเว้นวรรคตามธรรมชาติ เพราะจุดไข่ปลาจะหลุดไปติดในซับไตเติลบนหน้าจอ ทำให้ดูรกและผู้ใช้ต้องมานั่งลบเอง

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
   - ระดับเสียง: Voice = 1.0, SFX = 0.6, BGM = 0.15 (-16dB)
6. ✔️ **Code Reliability & Subprocess:**
   - การเรียกใช้ FFmpeg / ImageMagick / Rembg ต้องรันผ่าน subprocess พร้อม error handling และ log ข้อความภาษาไทยที่เข้าใจง่าย
7. ✔️ **มาตรฐานการตัดต่อแบบ J-Cut (Audio Lead-in Standard):**
   - ต้องปฏิบัติตาม [.agents/rules/j_cut_rules.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/j_cut_rules.md)
   - ใช้เทคนิค **J-Cut** ในการตัดต่อสลับช็อต B-roll: เสียงประโยคถัดไป (หรือ SFX Whoosh ข้ามฉาก) ต้องดังขึ้นก่อนภาพตัดเปลี่ยน 150 – 250ms เพื่อลดความแข็งกระด้างของการตัดแบบกระตุก (Avoid Jarring Jump Cuts) และสร้างความอยากรู้ล่วงหน้า (Anticipation) ให้คนดูติดตามต่อจนจบ

---

## 🧩 5. แผนผังโมดูลสำคัญ (Key Modules Reference)

| โมดูล / สคริปต์ | หน้าที่การทำงาน |
| :--- | :--- |
| `scripts/config.py` | ศูนย์รวมการตั้งค่า Path, สเปกวิดีโอ, เสียง TTS, และระดับเสียง |
| `scripts/api_server.py` | FastAPI Server ให้บริการ Endpoint สำหรับ Web UI และคำสั่ง Pipeline |
| `scripts/pipeline.py` | Orchestrator หลัก ควบคุมลำดับงานตั้งแต่สคริปต์จนถึงการตัดต่อ |
| `scripts/voice_engine.py` | ตัวจัดการสร้างเสียงสังเคราะห์ (Edge-TTS / gTTS) |
| `scripts/gemini_tts_engine.py` | โมดูลแปลงเสียงด้วย Gemini Flash Audio Model |
| `scripts/subtitle_engine.py` | ตัดแบ่งคำภาษาไทย สร้างไฟล์ `.srt` / `.ass` และเรนเดอร์ซับไตเติล |
| `scripts/product_scraper.py` | ดึงข้อมูล รายละเอียด และจุดขายสินค้าจากลิงก์ |
| `tools/build_3d_pro_badges.py` | สร้างและตัดแยกชุดป้ายรีวิว 3D อัตโนมัติ |
| `frontend/` | Dashboard React + Vite สำหรับพรีวิวและควบคุมโปรเจกต์ |

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
- **รันชุดทดสอบ (Unit Tests):**
  ```bash
  pytest tests/
  ```

---

## 🗣️ 7. แนวทางการสื่อสารของ AI (Communication Guidelines)

- ตอบคำถามและอธิบายงานเป็น **ภาษาไทย** สุภาพ ชัดเจน กระชับ และตรงประเด็น
- เมื่อเสนอโค้ด ให้ระบุ Path แบบเต็มและอธิบายเหตุผลของการเปลี่ยนแปลงสั้นๆ
- หากพบความเสี่ยงที่อาจทำให้ไฟล์สูญหาย ต้องหยุดและแจ้งเตือนผู้ใช้ก่อนเสมอ
