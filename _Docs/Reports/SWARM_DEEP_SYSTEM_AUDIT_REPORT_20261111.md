# รายงาน Swarm Deep Audit ทั่วทั้งระบบ OmniCut Pro Studio

> **วันที่:** 2026-11-11 · **ดำเนินการโดย:** Swarm Multi-Agent Orchestration (Coordinator: Antigravity / Gemini 3.8 Flash High)
> **เอเจนต์ตรวจสอบ:**
> - `backend-auditor`: ตรวจสอบ Python / FastAPI backend (`scripts/`)
> - `frontend-auditor`: ตรวจสอบ React / Vite frontend (`frontend/src/`)
> - `parity-auditor`: ตรวจสอบ Parity ระหว่าง Web Preview กับ FFmpeg และ CapCut Exporter
> - `test-runner`: รันและวิเคราะห์ Pytest, Vitest, Linting, และ Test Coverage

---

## 1. ผลลัพธ์และข้อบกพร่องระดับวิกฤต (P0 / Critical & Security)

### 1.1 Backend Async Event Loop Blocking
- **ไฟล์:** `scripts/api_recording.py:103` (`upload_recording_segment`)
  - **ปัญหา:** เรียก `VideoEditor.get_media_info(str(dest_path))` แบบ synchronous ซึ่งภายในรัน `subprocess.run(["ffprobe", ...])` บน Main Event Loop Thread โดยตรง บล็อกทุก HTTP Request และ WebSocket ของเซิร์ฟเวอร์ค้าง 100ms - หลายวินาที
  - **วิธีแก้:** ครอบด้วย `await asyncio.to_thread(VideoEditor.get_media_info, str(dest_path))`
- **ไฟล์:** `scripts/api_producer.py:233` (`upload_ref_media`) และ `scripts/api_recording.py:98`
  - **ปัญหา:** เขียนไฟล์ขนาดใหญ่ `with open(...) as f: f.write(...)` แบบ synchronous ใน `async def` routes
  - **วิธีแก้:** ใช้ `asyncio.to_thread` หรือ `aiofiles` สำหรับ Disk I/O ขนาดใหญ่

### 1.2 การละเมิดกฎความปลอดภัย AGENTS.md (Rule 1 & Rule 3)
- **ไฟล์:** `scripts/api_videos.py:1208` (`delete_file`)
  - **ปัญหา:** ตัวแปร `allowed_roots` รวม `(BASE_DIR / "02_Assets").resolve()` ไว้ด้วย ทำให้ผู้ใช้หรือสคริปต์สามารถส่งคำสั่ง API ลบไฟล์ Asset ส่วนกลาง (Fonts, SFX, Stickers, LUTs) ได้ ขัดกับ AGENTS.md Rule 1 อย่างร้ายแรง
  - **วิธีแก้:** ถอด `02_Assets` ออกจาก `allowed_roots` ของ `delete_file()`
- **ไฟล์:** `scripts/agent/omnicut_agent_tools.py:528`
  - **ปัญหา:** คำสั่งเขียนไฟล์ `draft_content.json` เขียนทับโดยตรงโดยไม่มีการสร้าง `.bak` หรือ timestamped backup ขัดกับ AGENTS.md Rule 3 ("ห้ามแก้ไฟล์ดราฟต์ CapCut โดยไม่มี Backup")
  - **วิธีแก้:** เพิ่ม `shutil.copy2(content_file, content_file.with_suffix(".json.bak"))` ก่อนเขียน

### 1.3 Test Fixture Environment Leak (Pytest Failure)
- **ไฟล์:** `tests/test_security_boundary_agent.py::test_unconfigured_lan_bind_is_rejected`
  - **ปัญหา:** เทสล้มเหลว (Failed) เนื่องจาก fixture `_no_real_api_key_gate` ใน `conftest.py` ล้างเฉพาะ `OMNICUT_API_KEY` และ `OMNICUT_AUTH_DISABLED` แต่ไม่ได้ล้าง `OMNICUT_APP_PASSWORD` หากในเครื่องผู้พัฒนามีรหัสผ่านใน `.env` ฟังก์ชัน `auth.is_password_configured()` จะเป็น `True` ทำให้ bypass LAN bind check
  - **วิธีแก้:** เพิ่ม `monkeypatch.setenv("OMNICUT_APP_PASSWORD", "")` ใน autouse fixture ของ `conftest.py`

---

## 2. ผลลัพธ์ระดับสูง (P1 / High Priority)

### 2.1 Backend Error Handling & Validation
- **ไฟล์:** `scripts/api_server.py:191`
  - **ปัญหา:** ไม่มี Global `@app.exception_handler(Exception)` เมื่อเกิด unhandled exception ใดๆ Starlette จะคืนข้อความ plain-text `Internal Server Error` (500) ทำให้ frontend พังตอน `response.json()`
  - **วิธีแก้:** ลงทะเบียน `@app.exception_handler(Exception)` คืน JSON `{"success": False, "error": "internal_server_error", "detail": str(exc)}`
- **ไฟล์:** `scripts/api_schemas.py:1`
  - **ปัญหา:** ไฟล์มี UTF-8 BOM (`\xef\xbb\xbf`) ที่บรรทัดแรก ทำให้ Python AST Linters / Parsers บางตัวเตือน `SyntaxError: invalid non-printable character U+FEFF`
  - **วิธีแก้:** บันทึกไฟล์ใหม่เป็น UTF-8 (No BOM)
- **ไฟล์:** `scripts/api_posts.py`, `scripts/api_products.py`, `scripts/api_channels.py`, `scripts/api_shot_lists.py`
  - **ปัญหา:** Endpoint มากกว่า 15 จุด รับ `payload: Dict[str, Any]` หรือ `payload: Any = Body(...)` ทำให้ bypass Pydantic validation ทั้งหมด
  - **วิธีแก้:** ผูก Typed Pydantic Request Models ให้ครบถ้วน
- **ไฟล์:** `scripts/api_schemas.py:31` (`VoicePreviewRequest`)
  - **ปัญหา:** ตัวแปร `speed` ไม่มีขอบเขต `Field(ge=0.5, le=3.0)` หากยิงค่าผิดปกติ (เช่น ติดลบ) จะทำให้ FFmpeg แคชล้มเหลวทันที

### 2.2 Hardcoded Absolute Paths (AGENTS.md Rule 2)
- `scripts/capcut_builder.py:31`: มี `VECTCUT_PATH = r"D:\Winona\Programmer\VectCutAPI"`
- `scripts/api_mobile_posting.py:204`: มี `Path(r"G:\My Drive\Omnicut_Exports")`
- `scripts/api_recording.py:6` และ `scripts/api_shot_lists.py:5`: Docstrings อ้างอิง `C:\Users\Winon\.claude\plans\...`

---

## 3. ผลลัพธ์ระดับกลาง (P2 / Medium Priority)

### 3.1 Pipeline & Preview Parity
- **ไฟล์:** `frontend/src/components/SequencePlayer.jsx:1653, 1655, 1659`
  - **ปัญหา:** พิกัดแกน Y สำรองของสติกเกอร์ใน Canvas Preview (ขนาด 540x960) คัดลอกค่า `420` มาจาก FFmpeg (`H-h-420` ของ 1920) โดยไม่ได้สเกลตามความสูง Canvas ทำให้สติกเกอร์ใน Canvas ลอยขึ้นไปอยู่เกือบกึ่งกลางจอ (43.75%) แทนที่จะอยู่ชิดเส้น Safe Zone ล่าง (21.88%)
  - **วิธีแก้:** ปรับเป็น `Math.round(420 * (CANVAS_H / 1920))` (หรือ 210)
- **ไฟล์:** `scripts/capcut_builder.py:315-331` (`_create_draft_content`)
  - **ปัญหา:** ไทม์ไลน์ CapCut ที่สร้างส่งออกมีเฉพาะแทร็กวิดีโอ, เสียงพากย์, ซับ, และสติกเกอร์ แต่ดรอปแทร็ก BGM และ SFX หายไปทั้งหมด
  - **วิธีแก้:** เพิ่มการแปลงแทร็ก BGM และ SFX ลงใน `tracks` ของ CapCut draft
- **ไฟล์:** `scripts/capcut_builder.py:375-493` (`import_capcut_draft_to_manifest`)
  - **ปัญหา:** การนำเข้าดราฟต์ CapCut กลับเข้าสู่ระบบ OmniCut ไม่ประมวลผลแทร็กเสียง ทำให้การปรับเสียงใน CapCut สูญหาย (Round-trip data loss)

### 3.2 Frontend UI/UX & State Guards
- **Double-Click Vulnerability / ขาด disabled state:**
  - `ContentTrackerHub.jsx:2328`: `handleQcFailConfirm` ยิง network mutation โดยไม่มีปุ่ม disabled
  - `ContentTrackerHub.jsx:2902`: ปุ่ม Refresh หมุนไอคอนตอน `loading` แต่ขาด `disabled={loading}`
  - `ProductToClip.jsx:4561`: `handleBatchUnhideAll` ยิง batch `Promise.all` ไม่มี loading/disabled guard
  - `ProductToClip.jsx:4683`, `MediaAssetsHub.jsx:575`, `ScheduleAgenda.jsx:1098`, `SystemAssets.jsx:190`: ปุ่ม Refresh ขาด `disabled={loading}`
- **Dead Code / Linter Cleanliness:**
  - `SequencePlayer.jsx:5780-5782`: Dead JSX `) : (null && <div><span></span></div>)}`
  - `overlayBoxGeometry.js:154`: `if (false) { nextX = 0.5; snapX = 0.5; }`
  - `PresetsBar.jsx:121`: ข้อความปุ่มมีสัญลักษณ์นำ `✕ ปิดสินค้านี้` (ขัดกับ Rule 3.8/4.8)
- **Unslop Obsidian Dark (#0A0D14) Compliance:**
  - พบแถบ Gradient สีรุ้ง `from-[#FE2C55] to-[#25F4EE]` หลงเหลืออยู่ใน:
    - `EditorShell.jsx:3120, 3871` (Render progress bar)
    - `FindReplaceModal.jsx:312`
    - `ErrorBoundary.jsx:80`
    - `AIBridgePanel.jsx:119`
    - `Sidebar.jsx:454`
    - `MediaAssetsHub.jsx:1118, 1129`

---

## 4. สถานะชุดทดสอบและการทดสอบถดถอย (Test Suite Health)

1. **Vitest (Frontend)**: ผ่าน 1,280 / 1,280 ข้อ (100% Green, 4.41s)
   - *จุดสังเกต:* ทั้ง 1,280 ข้ออยู่ใน `src/lib/` ทั้งหมด — ยังไม่มี Component Testing สำหรับ `src/components/` เพื่อตรวจจับ Button state / Gradient regressions
2. **Vite Production Build**: ผ่านสมบูรณ์ (2,105 modules ใน 943ms)
3. **Pytest (Backend)**: ผ่าน 892 ข้อ, **ล้มเหลว 1 ข้อ** (`test_security_boundary_agent.py::test_unconfigured_lan_bind_is_rejected` จากสาเหตุในข้อ 1.3)
4. **Gitignore / Linter Bug**: ใน `frontend/.gitignore` มี `# dist` คอมเมนต์อยู่ ทำให้ oxlint เผลอสแกนไฟล์ bundle ใน `dist/`
