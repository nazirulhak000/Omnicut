# 📱 แผนงานระบบอัปโหลดคลิปดิบผ่านมือถือแบบแบ่งพาร์ททนทานต่อเน็ตช้า (Resumable Chunked Mobile Upload System)

> **วันที่จัดทำ:** 2026-11-15  
> **รอบงาน:** `ANTIGRAVITY-MOBILE-RESUMABLE-CHUNKED-UPLOAD-20261115`  
> **ผู้รับผิดชอบ:** Swarm Team (@coordinator, @backend, @frontend, @verifier, @monitor)  
> **ดำเนินการโดย:** Antigravity (Gemini 3.8 Flash High)

---

## 1. ที่มาและปัญหา (Problem Statement)
ผู้ใช้งานต้องการอัปโหลดคลิปดิบ (Raw Videos) จากมือถือ (เช่น iPhone / Android) เข้าสู่ระบบ OmniCut Studio แต่เมื่อเน็ตช้าหรือไฟล์มีขนาดใหญ่ (100MB – 1GB+ สำหรับคลิป 1080p/4K) จะเกิดปัญหาดังนี้:
1. **Monolithic Multipart Upload**: ระบบ UI เดิมยิง `POST /api/upload` รวดเดียวทั้งไฟล์ หากเน็ตสะดุดหรือหลุดที่ 90% ข้อมูลจะสูญเปล่าทั้งหมด ต้องเริ่มนับ 1 ใหม่ตั้งแต่ 0%
2. **Client/Server Timeout**: Axios Client จำกัดเวลาที่ 5 นาที (`timeout: 300000ms`) หากเน็ตช้าจนเกินเวลา จะถูกตัดการเชื่อมต่อทันที
3. **Mobile OS Screen Sleep**: บน iOS Safari หรือ Android เมื่อหน้าจอดับ (Screen Lock) หรือสลับแอป ระบบปฏิบัติการจะ Freeze การเชื่อมต่อเครือข่ายของเบราว์เซอร์ทันที
4. **Cloudflare Tunnel Limit**: Cloudflare Tunnel บล็อกคำขอที่มี Request Body เกิน 100 MB และมี HTTP timeout 100 วินาที ทำให้ไฟล์ใหญ่ล้มเหลวแน่นอน

---

## 2. เป้าหมาย (Goal & Deliverables)
1. เชื่อมต่อระบบ **Resumable Chunked Upload (8MB Chunks)** ระหว่าง Frontend และ Backend ให้สมบูรณ์ 100%
2. ปรับปรุง `scripts/api_uploads.py`:
   - รองรับพารามิเตอร์ `product_id` และ `target_dir` (`raw` หรือ `inbox`)
   - จัดเก็บไฟล์ลง `01_Raw/<product_id UUID>/` ตามมาตรฐาน Rule 2 & 4
   - ตรวจสอบความถูกต้องของไฟล์ (Magic Bytes) และตรวจจับไฟล์ซ้ำ (Rule 13 SHA-256 Deduplication)
   - ผูกไฟล์เข้ากับ `ProductStore.add_video_to_product()` อัตโนมัติ พร้อมส่งคืน `file_info` รูปแบบมาตรฐาน
3. คืนชีพและเชื่อมต่อ `UploadTray.jsx` และ `uploadQueue.js`:
   - ระบบ Screen WakeLock (`navigator.wakeLock.request('screen')`) ป้องกันหน้าจอมือถือดับระหว่างอัปโหลด
   - จัดเก็บสถานะลง IndexedDB รองรับการเปิดหน้าจอใหม่แล้วส่งต่อได้
   - แสดงผลถาดอัปโหลดลอย (Upload Tray) ที่มีปุ่มสัมผัสขนาด ≥44px (Pause, Resume, Retry)
4. เชื่อมโยงเข้ากับ UI:
   - `MediaPickerModal.jsx` (ปุ่มอัปโหลดคลิปในสตูดิโอ)
   - `ProductToClip.jsx` (ปุ่มลาก/แนบคลิปดิบประจำสินค้า)
5. การทดสอบครอบคลุม (Deterministic Offline Tests):
   - Unit tests ใน `tests/test_mobile_chunked_upload_parity.py`
   - Frontend build verification (`npm run build`)

---

## 3. สถาปัตยกรรมและการแบ่งงาน (Swarm Work Breakdown)

### Agent 1: `@backend` (Backend Engineer)
- **ไฟล์เป้าหมาย:** `scripts/api_uploads.py`
- **ภารกิจ:**
  1. อัปเดต `UploadInitRequest` ให้รับ `product_id: Optional[str]` และ `target_dir: Optional[str] = "raw"`
  2. ใน `complete_chunked_upload`:
     - เมื่อ `target_dir == "raw"` และมี `product_id`: กำหนดปลายทางเป็น `RAW_DIR / product_id`
     - นำไฟล์ออกจาก staging ย้ายเข้าโฟลเดอร์เป้าหมาย
     - รัน `get_file_info(final_path)` เพื่อสกัดความยาวและขนาด
     - เรียก `ProductStore.add_video_to_product(product_id, file_info)`
     - ตอบกลับ JSON โครงสร้าง `{ ok: true, message: "Upload successful", file: file_info, deduplicated: bool, sha256: str }`

### Agent 2: `@frontend` (Frontend Engineer)
- **ไฟล์เป้าหมาย:** `frontend/src/lib/uploadQueue.js`, `frontend/src/components/mobile/UploadTray.jsx`, `frontend/src/App.jsx`, `frontend/src/components/MediaPickerModal.jsx`
- **ภารกิจ:**
  1. ปรับปรุง `uploadQueue.js` ให้รองรับ `product_id` และ `target_dir` และส่งคืน `file_info` เมื่องานเสร็จสิ้น
  2. สร้าง/คืนชีพ `UploadTray.jsx` ดีไซน์พรีเมียม Dark Mode ปุ่มกดขนาด ≥44px สำหรับมือถือ
  3. ติดตั้ง `<UploadTray />` ใน `frontend/src/App.jsx`
  4. ปรับ `MediaPickerModal.jsx` ให้สามารถสลับมาใช้ Chunked Upload ผ่าน `uploadQueue` ได้อย่างราบรื่น

### Agent 3: `@verifier` (Quality & Safety Verifier)
- **ไฟล์เป้าหมาย:** `tests/test_mobile_chunked_upload_parity.py`
- **ภารกิจ:**
  1. เขียนเทสจำลองการส่ง Chunked Upload (Init -> Patch 1 -> Drop -> Resume Patch 2 -> Complete)
  2. ตรวจสอบว่าไฟล์ถูกจัดเก็บใน `01_Raw/<product_id>/` จริง
  3. ตรวจสอบว่า `ProductStore` มีรายการคลิปผูกติดกับสินค้าถูกต้อง
  4. ตรวจสอบ Rule 13 SHA-256 Deduplication
  5. รัน `npm run build` ตรวจสอบ Frontend ไม่พัง
  6. ทำความสะอาด Test Artifacts 100% ตามกฎ Rule 11 & 15

### Agent 4: `@monitor` (Stall Monitor)
- ตรวจจับความคืบหน้าของ Swarm และแจ้งเตือนเมื่อเกิดคอขวด
