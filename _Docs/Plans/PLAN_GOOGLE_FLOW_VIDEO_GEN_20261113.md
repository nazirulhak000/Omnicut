# แผนงานพัฒนาระบบสร้างวิดีโอด้วย Google Flow (Veo) สำหรับ OmniCut Pro Studio
วันที่: 2026-11-13  
กิ่ง Git: `feat/google-flow-video-gen`  
เครื่องยนต์หลัก: `flow-mcp` (Playwright-core + Chrome DevTools Protocol + Local REST API)  
ดำเนินการโดย: Antigravity (Gemini 2.5 Flash)

---

## 🎯 1. ที่มาและเป้าหมาย
เปิดความสามารถให้ OmniCut Pro Studio สร้างวิดีโอ B-roll และฉากเคลื่อนไหวของสินค้าด้วย **Google Flow** (สตูดิโอ AI วิดีโอของ Google Labs ที่ขับเคลื่อนด้วยโมเดล Veo) โดย:
1. ใช้ **โควตาฟรีประจำวัน (50 Credits/วัน)** ของ Google Account โดยไม่ต้องเสียค่าบริการ Google Cloud API
2. ขับเคลื่อนเบื้องหลังด้วย **`tools/flow-mcp/`** ผ่าน Chrome DevTools Protocol (CDP) และ Chrome Profile ถาวร (`~/.flow-mcp/chrome-profile`) ไม่ต้องทำ Chrome Extension แยก และข้ามปัญหา Google Login/2FA ได้ 100%
3. ดึงคลิปที่สร้างเสร็จแล้วเข้ามาเป็นวัตถุดิบตัดต่อในไทม์ไลน์ 9:16 ของ Omnicut แบบอัตโนมัติ (Auto-Ingest เข้า `01_Raw/<product_id>/AI_Flow/`)

---

## 🧭 2. สรุปสถาปัตยกรรมระบบ (Architecture Decisions)

1. **Automation Engine (`tools/flow-mcp/`):**
   * บรรจุ `flow-mcp` (TypeScript / Node.js) เข้ามาเป็น Service ประจำโปรเจกต์
   * ใช้ Chrome DevTools Protocol สั่งงาน `flow.google.com` โดยตรง
   * มี Local HTTP REST API บนพอร์ต 8787 (`/api/generate`, `/api/wait`, `/api/status`, `/api/upload`)
   * มี MCP Server (`stdio`) สำหรับเรียกผ่าน AI Agent

2. **รูปแบบการสร้างวิดีโอ (Generation Capabilities):**
   * **Text-to-Video:** สร้าง B-roll จาก Prompt ตามบทและสตอรี่บอร์ด
   * **Image-to-Video:** ดึงภาพสินค้าจริงจาก `01_Raw/<product_id>/` อัปโหลดผ่าน `/api/upload` ไปเป็น Start Frame / Reference Image ใน Google Flow

3. **Backend Integration (`scripts/`):**
   * `scripts/flow_client.py`: คลาสเชื่อมต่อ Local HTTP REST API (port 8787) ของ `flow-mcp`
   * `scripts/flow_prompt_engine.py`: ใช้ Gemini Flash แปลงช็อตลิสต์ไทยเป็น Cinematic English Prompts ปรับแต่งสำหรับ Veo/Flow
   * `scripts/flow_service.py`: จัดการคิวงาน, ตรวจสอบสถานะ, ดาวน์โหลดไฟล์วิดีโอเข้า `01_Raw/<product_id>/AI_Flow/`
   * FastAPI Endpoints ใน `scripts/api_server.py`:
     - `GET /api/flow/status` (เช็คสถานะการล็อกอิน, โควตาเครดิตคงเหลือ, เซิร์ฟเวอร์ flow-mcp)
     - `POST /api/flow/prompt/expand` (แปลงช็อตไทยเป็น Prompt ภาษาอังกฤษ)
     - `POST /api/flow/jobs` (ส่งคิวเจนวิดีโอ)
     - `GET /api/flow/jobs` (ดูรายการงานและสถานะ)
     - `POST /api/flow/ingest` (บันทึกคลิปเข้าคลังสินค้าและอัปเดต Shot List)

4. **Frontend Integration (`frontend/`):**
   * สร้าง `GoogleFlowModal.jsx` ในหน้า `ProductToClip` และ `ShotList`
   * แสดงเครดิตคงเหลือ และสถานะการล็อกอิน Google Flow
   * ระบบแสดงผล Prompt พร้อมช่องเลือกภาพสินค้า
   * แผง Review & Approve สำหรับดูคลิปที่เพิ่งดูดกลับมา ก่อนกด "นำเข้าไทม์ไลน์"

5. **การจัดการความปลอดภัยและโควตา (Rate-Limit & Quota Guard):**
   * `flow-mcp` มีระบบ Pacing & Human-like Delay ในตัว
   * ตรวจสอบเครดิตคงเหลือก่อนสั่งงานทุกครั้ง ป้องกันเครดิตติดลบหรือไม่พอ

---

## 🛠️ 3. แผนการดำเนินงานตามลำดับเฟส (Implementation Roadmap)

- [ ] **เฟส 1: ติดตั้งและตั้งค่า Core Engine (`tools/flow-mcp/`)**
  - นำ `flow-mcp` เข้ามาใน `tools/flow-mcp/` พร้อม config ให้ทำงานเข้ากับ Omnicut
  - คอมไพล์ TypeScript (`dist/`) และตรวจ dependencies
- [ ] **เฟส 2: Backend Client & Data Contract (`scripts/`)**
  - สร้าง `scripts/flow_client.py` สื่อสารกับ REST API (Port 8787)
  - สร้าง `scripts/flow_prompt_engine.py` (Gemini Flash translation & cinematic expansion)
  - สร้าง `scripts/flow_service.py` (Queue & Ingestion pipeline)
  - เพิ่ม API endpoints ใน `scripts/api_server.py`
  - เขียน Unit tests ทดสอบ Client & Endpoints (Mock server)
- [ ] **เฟส 3: Frontend Omnicut Studio UI (`frontend/`)**
  - สร้าง `GoogleFlowModal.jsx` เชื่อมต่อ API Backend
  - เพิ่มปุ่มเรียกใช้งานใน `ShotListModal.jsx` และ `ProductToClip.jsx`
  - ตรวจสอบความสะอาด UI (Rules 3.8 / 4.8 / Obsidian Pro Dark tokens)
- [ ] **เฟส 4: ทดสอบระบบและการทำงานร่วมกัน (End-to-End & Parity)**
  - ทดสอบ Flow Status & Login check
  - ทดสอบ Ingestion เข้า `01_Raw/<product_id>/AI_Flow/`
  - ทำความสะอาดไฟล์ทดสอบ 100% (Rule 3.11 / 4.15)
