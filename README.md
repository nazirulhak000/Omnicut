# 🎬 OmniCut Pro Studio — AI Video Production Suite (CapCut Automation Pipeline)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React + Vite](https://img.shields.io/badge/Frontend-React%20+%20Vite-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev/)
[![FFmpeg](https://img.shields.io/badge/Media-FFmpeg-007808.svg?logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![CapCut Compatible](https://img.shields.io/badge/Integration-CapCut%20PC-00C4CC.svg)](https://www.capcut.com/)

ระบบอัตโนมัติสำหรับสร้างและตัดต่อวิดีโอสั้นแนวตั้ง **9:16 (1080x1920, 30 FPS)** สำหรับ TikTok, YouTube Shorts และ Reels ครอบคลุมข้อมูลสินค้า, AI draft, เสียงพากย์, ซับไทย/อังกฤษ, BGM/SFX, Editor แบบ multi-track, keyframes, partial reroll และไฟล์ H.264/AAC พร้อมโพสต์ โดยยังส่งต่อไป CapCut PC ได้เมื่อจำเป็น

เริ่มทำงานกับโค้ดให้อ่าน [AGENTS.md](AGENTS.md), [TODO.md](TODO.md) และ [ARCHITECTURE.md](ARCHITECTURE.md) ก่อน สถานะใน `TODO.md` ใหม่กว่าเอกสารสรุปอื่นเสมอ

---

## 🚀 ฟีเจอร์หลัก (Core Features)

- 🧑‍💼 **AI Producer Hub (เมนู 0):** ศูนย์บัญชาการรายวัน — Daily Mission, Spotlight Next Mission, Pacing Calculator, คลังไอเดียและเรฟ (Idea & Ref Vault พร้อม Visual Insights จาก Gemini Vision), Producer Notes ที่ปักหมุด/แก้ไขได้ และ Quick Ref สำหรับหน้าโรงถ่าย
- 🛍️ **Product Scraper & Store:** สกัดข้อมูลสินค้า จุดขาย ราคา โปรโมชั่นจาก Marketplace / URL เพื่อนำมาเขียน Hook & CTA
- ✍️ **AI Script Generator:** สร้างบทพูดรีวิว/ขายสินค้าที่กระชับ ตรงกลุ่มเป้าหมาย มี Hook 3 วินาทีแรก และ CTA ปิดท้าย
- 🎙️ **Multi-Engine TTS (ค่าเริ่มต้นคือ Gemini TTS):**
  - **Gemini Flash TTS (default):** พากย์เสียงไทยมีอารมณ์ จังหวะธรรมชาติ (เสียงเริ่มต้น Puck ชายพลังสูง) รองรับ Multi-Key Failover หลายคีย์อัตโนมัติ
  - **Edge-TTS:** ใช้เมื่อผู้ใช้เลือกเองเท่านั้น (`th-TH-PremwadeeNeural`, `th-TH-NiwatNeural`) สปีด +15% สำหรับสไตล์ TikTok
  - **gTTS:** ระบบสำรองสำหรับโหมดออฟไลน์
  - ⚠️ โหมด Gemini TTS จะ **ไม่สลับไป Edge-TTS แบบเงียบๆ** หากเจนไม่ผ่าน แต่แจ้ง Error ให้ผู้ใช้ทราบโดยตรง
- 📝 **Thai Subtitle Engine & Auto-Burst:** ตัดแบ่งคำภาษาไทยด้วย `pythainlp` จัดการปัญหาสระลอย/วรรณยุกต์ และสร้างซับไตเติล 2 ภาษา (ไทย-อังกฤษ)
- 🎨 **Universal 3D Badges & Sticker Sheet:** ระบบสร้างป้ายรีวิว 6 แบบมาตรฐาน (Pros, Cons, Warning, Pro Tip, Score, Verdict) ขอบ Die-cut ใช้งานซ้ำได้ทุกคลิป
- 🎵 **Smart SFX & BGM Ducking:** จัดการเสียงเอฟเฟกต์ (Whoosh, Pop, Ding) และปรับระดับเพลงพื้นหลังอัตโนมัติขณะมีเสียงพูด
- 🖥️ **Web UI Control Center:** แดชบอร์ด React + Vite ควบคุมทุกขั้นตอนและพรีวิวงานได้แบบเรียลไทม์
- 🎞️ **Flexible Timeline Editor:** รองรับหลาย Video/Overlay/Audio tracks, trim, split, duplicate, transition, ripple, snap, mute/solo/visibility และ undo/redo
- 💾 **Safe Project State:** Manifest migration, autosave แบบ latest-write-wins, flush ก่อนสลับโปรเจกต์ และ atomic save
- 🔁 **Partial Reroll:** เปลี่ยน Hook, Subtitle, BGM, Voice หรือ Video โดย reuse artifact ของ stage ก่อนหน้า
- 🎚️ **Preview = Render Contracts:** Canvas preview และ ASS/libass renderer ใช้ model/constant ที่ mirror กัน พร้อม source, behavior และ FFmpeg regression tests
- 🎨 **Hook Style & Style Preset 10 แบบ:** สไตล์การตัดต่อ 10 แบบผูกกับป้ายฮุก (สี + อนิเมชัน) แบบ 1-to-1 พร้อมตรวจจับสไตล์ที่เคยใช้กับสินค้านั้นแล้ว
- 🔒 **Permanent Watermark:** ลายน้ำช่อง (@rizanntry) ติดถาวรทั้งใน Render และ Preview
- 📊 **Analytics Hub 5 แท็บ:** Production, Performance (ผลงาน TikTok + คลิปปัง), Tokens, Storage (พร้อม Safe Cache Cleaner) และ Inventory
- 📈 **TikTok Stats Sync:** ดึงสถิติจาก TikTok Studio พร้อมจับคู่โพสต์แบบ manual และ milestone แจ้งเตือนคลิปปัง 10k+
- 🗂️ **Batch Render & Backup:** เรนเดอร์หลายคลิปพร้อมกัน, One-click Backup/Restore และตัวสแกนไฟล์สื่อซ้ำ
- 🧵 **Background Isolation:** ตัดพื้นหลัง/แยกตัวแบบ async พร้อมกู้งานค้างอัตโนมัติเมื่อรีสตาร์ตระบบ

---

## 🧭 เมนูหลัก 9 โมดูล (Navigation)

ระบบจัดเป็น 9 เมนูใน Sidebar (`frontend/src/components/Sidebar.jsx`) — รายละเอียดเชิงลึกอยู่ที่ [ARCHITECTURE.md](ARCHITECTURE.md):

| เมนู | ชื่อ | หน้าที่สั้นๆ |
| :--- | :--- | :--- |
| 0 | ผู้ช่วยโปรดิวเซอร์ | Daily Mission, คลังไอเดีย/เรฟ, Producer Notes, Quick Ref |
| 1 | สินค้า → คลิป | สแกนสินค้า + AI สร้าง Content Matrix 4-10 สคริปต์ พร้อมเวลาเสียงพากย์ |
| 2 | แทร็กเกอร์ 4 เฟส | ติดตามสถานะงาน 4 ขั้น + แผนถ่าย (Shot List) + หน้าถ่ายผ่านมือถือ |
| 3 | ตัดต่อ & สร้างคลิป | ไทม์ไลน์ Multi-track, SequencePlayer, Inspector, Keyframes |
| 4 | Export Gallery | คลิปสำเร็จรูป, Post Studio (ปก 3:4 / 9:16), มาร์คโพสต์ และ Auto-Post |
| 5 | Media Assets Hub | ฟอนต์, BGM, SFX, สติกเกอร์/ป้าย และ Color LUTs |
| 6 | สถิติ & วิเคราะห์รวม | 5 แท็บ: Production, Performance, Tokens, Storage, Inventory |
| 7 | ตั้งค่าระบบ | System Health, AI Providers, เสียงพากย์ และ QR เชื่อมต่อมือถือ |
| 8 | คู่มือใช้งาน | คู่มือในแอป (Sticky TOC, เช็กลิสต์, โฟลว์ 7 ขั้น, FAQ ค้นหาได้) |

---

## 📁 โครงสร้างโฟลเดอร์มาตรฐาน (Directory Structure)

```text
Capcut/
├── 00_Inbox/               # พักไฟล์ดิบ ไอเดีย และไฟล์วิดีโอที่ sync จากมือถือ
├── 01_Raw/                 # วัตถุดิบต้นฉบับ แยกตาม YYYYMMDD_ชื่อสินค้า-ประเด็น/
├── 02_Assets/              # Media Assets ส่วนกลาง
│   ├── Fonts/              # ฟอนต์มาตรฐาน (Kanit, Prompt, etc.)
│   ├── Music/              # เพลงประกอบ BGM (ปลอดลิขสิทธิ์ / Trending)
│   ├── SFX/                # เสียงเอฟเฟกต์ (Whoosh, Ding, Click)
│   ├── Stickers_Memes/     # สติกเกอร์และป้าย Badge PNG โปร่งใส
│   └── LUTs_ColorPresets/  # ค่าพรีเซ็ตสี
├── 03_Projects/            # ไฟล์สคริปต์ ดราฟต์ และบันทึกงานแต่ละโปรเจกต์
├── 04_Exports/             # วิดีโอที่ตัดต่อเสร็จพร้อมเผยแพร่
│   ├── Ready_to_post/      # คลิปที่เรนเดอร์เสร็จ รอการโพสต์
│   └── Posted/             # คลิปที่โพสต์ลงช่องทางแล้ว
├── 05_Covers_Thumbnails/   # รูปหน้าปกคลิปและ Thumbnail สัดส่วน 9:16
├── 06_Archive/             # สำรองข้อมูลไฟล์ Raw และโปรเจกต์เก่าเกิน 30 วัน
├── frontend/               # เว็บแอปพลิเคชัน React + Vite UI
├── scripts/                # FastAPI routers, pipeline stages, TTS, subtitle และ renderer
├── tools/                  # สคริปต์ Utility (Font Downloader, Badge Generator, Asset Builder)
├── tiktok_autopost_extension/ # Chrome Extension สำหรับ Auto-Post ขึ้น TikTok
├── tests/                  # Backend, contract, parity, render และ compatibility tests
├── _Docs/                  # PRD, prompt รายงานปฏิบัติการ และ runtime data (post_log ฯลฯ)
├── .agents/rules/          # กฎเฉพาะงานสำหรับคนและ AI Agent
├── AGENTS.md               # กฎเหล็กและคู่มือสำหรับ AI Coding Assistants
├── ARCHITECTURE.md         # แผนผังโมดูลและ data flow ปัจจุบัน
├── TODO.md                 # สถานะงานกลางและ handoff ระหว่างรอบ
├── requirements.txt        # รายการ Python dependencies
└── start_app.bat           # สคริปต์คลิกเดียวเพื่อเปิดใช้งาน Backend & Frontend
```

---

## 🔄 ลำดับการทำงาน (Pipeline Workflow)

```mermaid
flowchart LR
    A[00_Inbox\nSync จากมือถือ] --> B[01_Raw\nจัดหมวดหมู่สินค้า]
    B --> C[Scripts / AI Pipeline\nสคริปต์ + TTS + ซับ + SFX]
    C --> D[03_Projects / CapCut\nFine Cut & จัดวาง Layer]
    D --> E[04_Exports\nReady to post]
    E --> F[05_Covers\nทำปกคลิป]
    F --> G[06_Archive\nสำรองข้อมูลหลัง 30 วัน]
```

1. **ต้นน้ำ (Input & Script):**
   - นำไฟล์จากมือถือเข้า `00_Inbox` แล้วจัดเข้า `01_Raw/YYYYMMDD_ชื่อสินค้า-ประเด็น/`
   - ใช้ AI Scraper & Script Generator สร้างโครงเรื่อง Hook/CTA ใน `03_Projects/`
2. **กลางน้ำ (Processing & Assembly):**
   - รันระบบเสียงพากย์ (TTS) + ตัดคำซับไตเติลภาษาไทย + ใส่ SFX และ Sticker
   - เปิดตรวจสอบและปรับแต่งความละเอียดใน **CapCut PC** หรือ Web UI
3. **ปลายน้ำ (Export & Publish):**
   - Export คลิปขนาด 9:16 ลงใน `04_Exports/Ready_to_post/`
   - สร้างปกคลิปใน `05_Covers_Thumbnails/`
   - เมื่อโพสต์เสร็จ ย้ายไป `04_Exports/Posted/` และเก็บเข้า `06_Archive/` เมื่อครบ 30 วัน

---

## 🛠️ ความต้องการของระบบ (Prerequisites)

1. **Python 3.10 ขึ้นไป**
2. **Node.js 20.19+ หรือ 22.12+ & npm** (Vite 8; เครื่องที่ตรวจล่าสุดใช้ Node 24)
3. **FFmpeg & FFprobe:** ต้องติดตั้งและเพิ่มลงใน System `PATH` เรียบร้อยแล้ว (ทดสอบด้วย `ffmpeg -version`)
4. **CapCut for PC (Windows):** แนะนำติดตั้งเพื่อเปิดไฟล์ Draft ได้สะดวก

---

## ⚙️ การติดตั้งและตั้งค่า (Installation & Setup)

### 1. ติดตั้ง Python Dependencies
```bash
python -m venv .venv
# สำหรับ Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### 2. ติดตั้ง Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

### 3. การตั้งค่า Environment Variables (`.env`)
คัดลอกไฟล์ `.env.example` เป็น `.env` และกรอก API Key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## 🚀 วิธีการเปิดใช้งาน (Running the Application)

### วิธีที่ 1: รันด้วย One-Click Script (แนะนำบน Windows)
ดับเบิลคลิกที่ไฟล์:
```text
start_app.bat
```
*ระบบจะเปิด FastAPI Backend (Port 8000) และ React Frontend (Port 5173) พร้อมเปิด Browser ให้อัตโนมัติ*

### วิธีที่ 2: รันแยกทีละส่วน (Manual Mode)

**Terminal 1 (Backend API):**
```bash
python scripts/api_server.py
# หรือ uvicorn scripts.api_server:app --host 0.0.0.0 --port 8000 --reload
```
- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

**Terminal 2 (Frontend UI):**
```bash
cd frontend
npm run dev
```
- Web Application: [http://localhost:5173](http://localhost:5173)

---

## 🧪 การตรวจระบบ

```powershell
python -m compileall -q scripts
python -c "import scripts.api_server as app; print(len(app.app.routes))"
python -m pytest tests/ -q -p no:cacheprovider --tb=short
Set-Location frontend
npm test
npm run build
```

ผลตรวจล่าสุด 2026-09-15: Python pytest 1,514 passed / 5 skipped / 1 failed ที่ค้างมาก่อนแล้ว (`tests/test_style_motion_policy.py` — catalog 10 สไตล์แต่ test ยังยืนยัน 5), Frontend 246 tests ผ่าน, FastAPI 170 routes จาก 23 routers และ Vite build ผ่าน (2,007 modules) — อ่านชนิด test และข้อห้ามที่ [.agents/rules/testing_standard.md](.agents/rules/testing_standard.md)

---

## 🏷️ Naming Conventions

- **Raw Footage Folder:** `YYYYMMDD_ชื่อสินค้า-ประเด็นสั้นๆ`  
  *(ตัวอย่าง: `20260812_ลิปสติกABC-รีวิว`)*
- **Export File:** `YYYYMMDD_ชื่อสินค้า_hookสั้นๆ_vN.mp4`  
  *(ตัวอย่าง: `20260812_ลิปสติกABC_ทาแล้วลื่นมาก_v1.mp4`)*
- **CapCut Draft Name:** ตั้งชื่อตรงกับโฟลเดอร์โปรเจกต์เสมอ เพื่อป้องกันการสับสนเวลาสลับเครื่อง

---

## ✅ Checklist ก่อนโพสต์คลิป (Pre-Publish Checklist)

- [ ] **Hook 3 วินาทีแรก:** ภาพและเสียงสะดุดตา หยุดนิ้วคนดูได้ทันที
- [ ] **Subtitles & Spacing:** ข้อความซับไตเติลภาษาไทยถูกต้อง ไม่มีปัญหาสระลอยหรือวรรณยุกต์ซ้อน
- [ ] **Price & CTA:** ราคา โปรโมชั่น และพิกัดสั่งซื้อขึ้นชัดเจนบนหน้าจอ
- [ ] **Audio Balance:** ตรวจ Voice/SFX/BGM ตามค่าใน `scripts/config.py` และลองฟัง mute/ducking ใน Preview ก่อน Export
- [ ] **Safe Zone 9:16:** ข้อความ/สติกเกอร์ไม่ถูกบังด้วยปุ่ม Like/Comment/Share ของ TikTok
- [ ] **Cover / Thumbnail:** ตัวหนังสือบนหน้าปกอ่านง่าย สีสันดึงดูด

---

## 📄 ใบอนุญาตและการพัฒนา (License & Guidelines)
- กฎหลัก: [AGENTS.md](AGENTS.md)
- สถานะงานและ handoff: [TODO.md](TODO.md)
- โครงสร้างระบบ: [ARCHITECTURE.md](ARCHITECTURE.md)
- กฎทดสอบ: [.agents/rules/testing_standard.md](.agents/rules/testing_standard.md)
