# 🎬 แผนแม่บทสถาปัตยกรรมและการผสาน HyperFrames Studio เข้ากับ OmniCut (HyperFrames Hybrid Studio Architecture & Implementation Plan)

- **รหัสรอบงาน:** `Round HYPERFRAMES-HYBRID-INTEGRATION-20261010`
- **ดำเนินการโดย:** Antigravity (Gemini 3.8 Flash High)
- **วันที่:** 2026-10-10
- **สถานะ:** วางแผนละเอียดระดับพิกเซลและโครงสร้าง (Detailed Architecture Plan — Ready for Review)

---

## 🎯 1. วิสัยทัศน์และเป้าหมายเชิงกลยุทธ์ (Strategic Objectives)

ผสานศักยภาพของ **HyperFrames** (Web-based Programmatic Video & Motion Animation Engine) เข้ากับ **OmniCut Pro Studio** (Python FastAPI + React NLE + CapCut Interop) ในรูปแบบ **สถาปัตยกรรมไฮบริด (Hybrid Architecture)** โดยมีเป้าหมาย:

1. **ไม่ทำลายระบบเดิม 100% (Zero Regression):**
   - แกนหลักการตัดต่อและเรนเดอร์ปกติด้วย FFmpeg + GPU NVENC + React SequencePlayer + CapCut Draft ยังคงทำงานเร็วระดับวินาทีและผ่าน Unit Tests เดิม 100% (853 frontend tests / ~2900 backend tests)
2. **ปลดล็อกขีดจำกัดครีเอทีฟ (Breakthrough Creative Freedom):**
   - เพิ่มสตูดิโอสร้างคลิปโมชั่นพิเศษใน OmniCut ให้ผู้ใช้สามารถเลือกผลิตคลิปใน 4 สไตล์ที่ผ่านการอนุมัติแล้ว:
     - 🌟 **POV Chat Story** (แชท LINE เด้งสมจริง ไม่ต้องใช้เสียงพากย์)
     - 🔥 **Meme-PAS** (รีวิวมีม ปัญหาเจ็บปวด → มีมฮา → ปรอทแตก → เปิดตัวสินค้า)
     - 🥊 **VS Battle** (HUD เกมต่อสู้ Street Fighter เปรียบเทียบสินค้า 3 ยก K.O.)
     - 📊 **Tech Explainer** (ไดอะแกรมและภาพจริงอธิบายเชิงลึกสไตล์ Vox)
3. **ระบบการส่งออกที่เป็นหนึ่งเดียว (Unified Export Pipeline):**
   - คลิปที่เรนเดอร์จาก HyperFrames จะถูกจัดส่งเข้า `04_Exports/` พร้อมภาพปก WebP และลงทะเบียนใน `_Docs/export_registry.json` อัตโนมัติ ทำให้ปรากฏใน **Export Gallery**, **Content Tracker Hub**, และ **TikTok Auto-post Extension** ทันทีอย่างไร้รอยต่อ
4. **โหมด Motion Overlay Ingestion (นำโมชั่นมาใช้ใน NLE):**
   - สามารถเรนเดอร์ท่อนโมชั่นกราฟิก/ไตเติล/HUD จาก HyperFrames ออกมาเป็น Overlay Asset นำไปวางบนไทม์ไลน์ปกติของ OmniCut ได้

---

## 🏗️ 2. สถาปัตยกรรมระบบไฮบริด (System Architecture)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            OmniCut Pro Studio (UI)                               │
├────────────────────────────────────────┬─────────────────────────────────────────┤
│    โหมด 1: NLE Timeline ปกติ          │    โหมด 2: Creative Studio (HyperFrames) │
│    - ลากตัดฟุตเทจดิบ (Split/Ripple)     │    - แคตตาล็อก 4 สไตล์อนุมัติ           │
│    - ซับไตเติล Mali Micro-Burst        │    - สร้างคลิปใหม่จาก Voiceover + สคริปต์ │
│    - พรีวิวสดบน SequencePlayer 30fps    │    - Web Preview Live Composition        │
│    - ส่งออกดราฟต์ CapCut PC             │    - เรนเดอร์ 9:16 ด้วย Chrome Headless   │
└───────────────────┬────────────────────┴────────────────────┬────────────────────┘
                    │                                         │
                    ▼                                         ▼
┌────────────────────────────────────────┐ ┌───────────────────────────────────────┐
│     FastAPI Core Backend               │ │    FastAPI HyperFrames Router         │
│     (scripts/api_server.py)            │ │    (scripts/api_hyperframes.py)       │
├────────────────────────────────────────┤ ├───────────────────────────────────────┤
│  - /api/editor (Timeline state)        │ │  - GET  /api/hyperframes/compositions │
│  - /api/render (FFmpeg + NVENC)        │ │  - GET  /api/hyperframes/styles       │
│  - /api/videos (Asset management)      │ │  - POST /api/hyperframes/create-clip  │
│  - /api/products (Product Store)       │ │  - POST /api/hyperframes/render       │
│  - /api/exports (Export registry)      │ │  - POST /api/hyperframes/open-studio  │
└───────────────────┬────────────────────┘ └───────────────────┬───────────────────┘
                    │                                          │
                    │               ┌──────────────────────────┘
                    ▼               ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      04_Exports/ + _Docs/export_registry.json                    │
│      (พร้อมส่งต่อให้ Export Gallery, Content Tracker, TikTok Auto-post)         │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 3. การวิเคราะห์จุดเสี่ยงเชิงเทคนิคและการป้องกันบั๊ก 100% (Zero-Bug Guardrails)

| จุดเสี่ยงที่อาจเกิดบั๊ก | สาเหตุรากเหง้า (Root Cause) | มาตรการป้องกันเด็ดขาด (Guaranteed Prevention) |
|---|---|---|
| **1. CWD & Path Resolution Bug** | HyperFrames คำนวณ path สัมพัทธ์จาก root ของ studio (`assets/`, `kit/`, `compositions/`) หาก subprocess รันจากไดเรกทอรีอื่นจะหาไฟล์ไม่พบ | ทุกคำสั่ง CLI ของ HyperFrames บังคับใช้ `cwd = PROJECT_ROOT / "03_Projects" / "_HyperFrames_Studio"` ผ่าน `pathlib.Path` เสมอ |
| **2. Windows Colon / Backslash Bug** | คำสั่ง FFmpeg filter หรือ Node บน Windows มักพังเมื่อเจอ `D:\` หรือเครื่องหมาย `\` | บังคับแปลง path ทั้งหมดในไฟล์ HTML/JSON ของ HyperFrames ให้เป็น Forward Slash (`/`) และ relative to studio root |
| **3. Port Conflict Bug** | `hyperframes preview` ใช้พอร์ตดีฟอลต์ 3000 ซึ่งอาจชนกับ Vite (5173), API (8000), หรือแอปอื่น | ตรวจสอบพอร์ตว่างก่อนรัน preview หรือระบุ `--port 3100` พร้อมมีตัวเลือกเปิด Studio ในหน้าต่างใหม่แบบปลอดภัย |
| **4. Subprocess Blocking & Buffer Overflow** | การเรนเดอร์วิดีโอผ่าน Chrome Headless ใช้เวลา 1-3 นาที หากใช้ `subprocess.run(capture_output=True)` ตรงๆ จะบล็อก FastAPI event loop หรือเกิด deadlock buffer ล้น | รันการเรนเดอร์ใน Background Worker ผ่าน `asyncio.to_thread` / `TaskContext` สตรีม Log ลงไฟล์ `.tmp/` และแจ้งความคืบหน้าแบบ Real-time |
| **5. Whisper Concurrent Memory Bug** | โมเดล `large-v3-turbo` กิน RAM ~1.6 GB หากผู้ใช้กดเจนพร้อมกันหลายงาน RAM จะเต็ม | ใช้ Threading Lock ใน `scripts/api_hyperframes.py` จำกัดให้ถอดเสียง Whisper ทีละ 1 คิวบน CPU |
| **6. Stale/Ghost Exports Bug (Rule 3.11 & 4.15)** | งานเรนเดอร์ทดสอบตกค้างในโฟลเดอร์จริง | การเรนเดอร์ทดสอบ (Test/Draft) กำหนดให้ออกไปยัง `.tmp/` เสมอ เฉพาะคำสั่ง Final Export เท่านั้นที่ส่งไปยัง `04_Exports/` พร้อม thumbnail |
| **7. Safe Zone Clashing (Rule 4.1)** | ตัวหนังสือหรือมีมโดนปุ่มขวา/แถบล่าง TikTok บัง | บังคับใช้ Safe Zone CSS ใน `kit/kit.css`: Margin Bottom ≥ 420px, Margin Right ≥ 120px ตามข้อกำหนดอย่างเคร่งครัด |
| **8. Font & Styling Drift (Rule 3.10 & 4.12)** | ฟอนต์ไทยตกหล่นหรือแสดงผลเพี้ยน | ใช้ฟอนต์มาตรฐานที่ฝังมาใน `kit/fonts/` (Anuphan-Bold สำหรับซับ, Kanit-Black สำหรับหัวข้อ) ไม่พึ่งพาฟอนต์ระบบภายนอก |

---

## 🛠️ 4. แผนการพัฒนารายขั้นตอน (Step-by-Step Implementation Work Packages)

### **Package W1: Backend Integration Router (`scripts/api_hyperframes.py`)**
1. **สร้างโมดูล Router ใหม่:** `scripts/api_hyperframes.py`
   - เชื่อมต่อ `APIRouter(prefix="/api/hyperframes", tags=["HyperFrames"])`
   - รันตรวจสอบความพร้อมของสภาพแวดล้อม (Node, FFmpeg, faster-whisper, HyperFrames CLI)
2. **Endpoints ที่ต้องพัฒนา:**
   - `GET /api/hyperframes/status`: เช็คความพร้อมของ HyperFrames Studio (เวอร์ชัน, node, ffmpeg, studio path)
   - `GET /api/hyperframes/styles`: ส่งรายการสไตล์ที่อนุมัติ 4 แบบ (Meme-PAS, Tech Explainer, VS Battle, POV Chat Story) พร้อมคำอธิบายและคลิปอ้างอิง
   - `GET /api/hyperframes/compositions`: ดึงรายการ compositions ที่มีอยู่ในสตูดิโอ (ชื่อ, ความยาว, สินค้า, วันที่แก้ไข)
   - `POST /api/hyperframes/create-clip`: รับพารามิเตอร์ `clip_id`, `product`, `vo_path`, `script_path` เรียกใช้ `kit/new_clip.py` อย่างปลอดภัย
   - `POST /api/hyperframes/render`: สั่งเรนเดอร์ composition เป็นไฟล์วิดีโอ 9:16:
     - ส่ง log ลง `.tmp/`
     - สกัดภาพปก `.webp`
     - ลงทะเบียนเข้า `_Docs/export_registry.json`
   - `POST /api/hyperframes/open-studio`: รันคำสั่งเปิด HyperFrames Studio preview บนเบราว์เซอร์
3. **ติดตั้งใน Server:** นำ `router` ไป mount ใน `scripts/api_server.py`
4. **Unit Tests:** พัฒนา `tests/test_api_hyperframes.py` ครอบคลุม Mocking CLI, Validation, Error Handling

---

### **Package W2: Frontend Integration View (`HyperFramesHub.jsx`)**
1. **สร้างคอมโพเนนต์หลัก:** `frontend/src/components/hyperframes/HyperFramesHub.jsx`
   - **แท็บ 1: แคตตาล็อกสไตล์ (Approved Styles):**
     - การ์ดแนะนำ 4 สไตล์ (POV Chat, Meme-PAS, VS Battle, Tech Explainer)
     - ระบุจุดเด่น, ความยาวที่เหมาะสม, ตัวอย่างคลิป, และข้อควรระวัง
   - **แท็บ 2: คลังคลิป Compositions (Project Gallery):**
     - ตารางรายการคลิปใน `compositions/` (เช่น `hat01-meme-45s`, `ess02-battery-36s`, `ess02-pov-chat-28s`)
     - ปุ่ม **"เปิดดูใน Studio"** (`open_studio.bat` / Preview URL)
     - ปุ่ม **"เรนเดอร์คลิป Final (MP4)"** พร้อม progress indicator
     - แสดงสถานะการเรนเดอร์แบบ Real-time
   - **แท็บ 3: เริ่มสร้างคลิปใหม่ (New Creative Clip):**
     - ดึงสินค้าจาก `ProductStore` และเลือกเสียงพากย์จากโปรเจกต์เดิมใน `03_Projects/`
     - ฟอร์มกรอกชื่อคลิปและเลือกสไตล์
     - ปุ่มสั่งสร้างดราฟต์ใหม่ผ่าน `kit/new_clip.py`
2. **ผูกเข้ากับระบบนำทาง (Navigation):**
   - เพิ่มรายการใน `Sidebar.jsx` (Desktop Nav Item: `{ id: 'creative', icon: Sparkles, label: '3.1 Creative Studio', shortLabel: 'Creative' }`)
   - นำเข้าแบบ Lazy Load ใน `frontend/src/App.jsx`
3. **ดีไซน์ตามมาตรฐาน UI Clean Standard (Rule 3.8 & 4.8):**
   - ใช้โทนสี Obsidian / Dark Frosted Glass เข้าคู่กับ OmniCut Pro
   - ปุ่ม Action ขึ้นต้นด้วยคำกริยา ไม่มีอีโมจินำหน้า

---

### **Package W3: Export Registry & Lifecycle Synchronization**
1. **เชื่อมต่อกับ Export Gallery:**
   - เมื่อคลิปจาก HyperFrames เรนเดอร์เสร็จสิ้นใน `04_Exports/` ฟังก์ชันจะเรียก `register_export()`:
     - บันทึก metadata: `product_id`, `angle_id`, `style` (เช่น `hyperframes_meme`), `duration`, `rendered_at`
     - สกัด thumbnail WebP อัตโนมัติที่วินาทีที่ 1.5
   - คลิปจะปรากฏในแท็บ **Export Gallery** ทันที สามารถกดเล่น, ดูข้อมูลสเปก, หรือก๊อปปี้เส้นทางไฟล์ได้
2. **เชื่อมต่อกับ TikTok Post Helper Extension:**
   - วิดีโอที่ได้สามารถดึงขึ้นมาตั้งเวลาโพสต์ผ่าน Chrome Extension ได้เหมือนคลิปที่ตัดจาก FFmpeg ทุกประการ

---

### **Package W4: Verification Gates & Quality Assurance (QA)**
1. **Automated Backend Tests:**
   - รัน `pytest tests/test_api_hyperframes.py` (ผ่าน 100%)
   - รัน `pytest tests/test_api_exports.py` (ตรวจ Parity ของ Export Registry)
2. **Automated Frontend Tests:**
   - รัน `npm run build --prefix frontend` (คอมไพล์ผ่าน 100% ไม่มี TypeScript/JSX error)
3. **HyperFrames Engine Diagnostics:**
   - รัน `npx hyperframes check` ใน `03_Projects/_HyperFrames_Studio` (ผ่าน 0 errors)
4. **Test Cleanup 100% (Rule 3.11 & 4.15):**
   - ทุกไฟล์ทดสอบถูกลบออกจาก `.tmp/` และถอนออกจาก `export_registry.json` สะอาดหมดจด

---

## 📋 5. แผน Todo สำหรับบันทึกลง TODO.md

```markdown
- [ ] Round HYPERFRAMES-HYBRID-INTEGRATION-20261010 · ดำเนินการโดย: Antigravity (Gemini 3.8 Flash High)
  - [ ] W1. Backend Router (`scripts/api_hyperframes.py` + mount ใน `scripts/api_server.py`)
  - [ ] W2. Frontend View (`frontend/src/components/hyperframes/HyperFramesHub.jsx` + `Sidebar.jsx` + `App.jsx`)
  - [ ] W3. Export Registry Bridge (ลงทะเบียนผลงาน HyperFrames เข้า `_Docs/export_registry.json` อัตโนมัติ)
  - [ ] W4. Automated Unit Tests & Frontend Build Validation (ผ่าน 100%)
  - [ ] W5. End-to-End Test & 100% Cleanup
```
