# 📱 แผนงานสถาปัตยกรรม: OmniCut Mobile Studio Pro (End-to-End Mobile Pipeline)
> **เอกสารแผนงานทางเทคนิค:** รองรับโฟลว์ผลิตคลิปแนวตั้ง 9:16 จบสมบูรณ์ 100% บนมือถือ\
> **วันที่:** 2026-10-03\
> **ดำเนินการโดย:** Antigravity (Gemini 3.8 Flash)\
> **Jev Decision:** Choice A (Comprehensive Mobile Flow with Fallback Angles & Media Upload, Confidence: 1.00)

---

## 🎯 1. วัตถุประสงค์และปัญหาที่พบ (Problem Statement & Goals)
1. **แก้ปัญหาคอขวดหลัก (Blocker):** สินค้าที่ไม่มีมุม (`angles: []`) ทำให้ปุ่มดราฟต์ถูกปิดใช้งาน (`disabled`) ผู้ใช้บนมือถือไม่สามารถก้าวต่อไปยังหน้าถ่ายทำหรือเรนเดอร์ได้
2. **สร้าง Complete End-to-End Mobile Workflow:**
   - **หาสินค้า / เพิ่มสินค้าใหม่:** รองรับการแปะลิงก์ TikTok Shop หรือพิมพ์ชื่อสินค้าเพื่อดึงสเปกและคิดมุมผ่านมือถือ
   - **จัดการมุม & สคริปต์:** รองรับทั้ง (1) มุม AI อัตโนมัติ (2) เขียนมุม/สคริปต์สั้นเอง (3) ถ่ายด่วนฟรีสไตล์ (Instant Free-Take Fallback) เมื่อไม่มีมุม จะไม่บล็อกผู้ใช้เด็ดขาด
   - **แนบคลิป / ถ่ายคลิป:** รองรับทั้งการเปิดกล้องอัดสดผ่าน Guided Teleprompter และการอัปโหลดคลิปจากอัลบั้มมือถือ (Camera Roll / Files)
   - **เจนเสียง & พรีวิว:** พรีวิวเสียงสคริปต์พากย์ Fenrir (Commercial Premium) และคุม BGM ได้จากหน้าจอมือถือ
   - **ประกอบร่าง & เรนเดอร์:** ปุ่มเดียว Auto-Assemble & SOP Render ตามมาตรฐานแกดเจ็ต 9:16 (Mali-Bold Ghost Reveal + สเปกสีส้ม #FF6622 + Topic Hold)
   - **แชร์ & โพสต์:** One-tap Share เข้า TikTok ผ่าน Web Share API พร้อม Auto-copy Caption

---

## 🏗️ 2. แผนการแบ่งงานสถาปัตยกรรม (Module Breakdown)

### 🧩 เอเจนต์ที่ 1: Backend Pipeline & Mobile APIs (`scripts/mobile_quick_studio.py`, `scripts/api_mobile_studio.py`)
1. **Dynamic / Fallback Angle Engine:**
   - เมื่อสร้างเซสชันหรือประกอบคลิป หาก `angle_id` เป็น `"quick_take"` หรือสินค้าไม่มีมุม ระบบจะสร้าง Dynamic Angle รองรับทันที:
     - Hook Title: "รีวิวสินค้าแบบเรียลๆ ของดีบอกต่อ"
     - Script: สคริปต์รีวิวแกดเจ็ตมาตรฐาน 60 วินาที หรือข้อความที่ผู้ใช้กรอกเข้ามา
     - Shot List: สร้าง Shot List อัตโนมัติด้วย `generate_shot_list_for_angle`
2. **Mobile Direct Media Upload API:**
   - สร้างเอนด์พอยต์ `POST /api/mobile-studio/upload-video` รองรับ `multipart/form-data`
   - บันทึกไฟล์วิดีโอลงใน `01_Raw/<product_dir>/` พร้อมคำนวณ Checksum / ตรวจสอบความสะอาด
   - ผูกเข้ากับ ProductStore และ Session อัตโนมัติ
3. **Quick Product Intake API:**
   - สร้างเอนด์พอยต์ `POST /api/mobile-studio/products/quick-add` รองรับการเพิ่มสินค้าใหม่หรือส่งลิงก์ TikTok เข้าคิว AI Content Plan
4. **Voice Preview API:**
   - สร้างเอนด์พอยต์ `POST /api/mobile-studio/preview-voice` เจนเสียงตัวอย่าง 5 วินาทีของสคริปต์ให้ฟังก่อนเรนเดอร์

---

### 🎨 เอเจนต์ที่ 2: Mobile Touch UI & Interaction (`frontend/src/components/MobileQuickStudio.jsx`)
1. **แถบค้นหา & ปุ่ม "+ เพิ่มสินค้าใหม่" ในสเต็ป 1:**
   - มี Modal ป๊อปอัปให้วางลิงก์ TikTok Shop หรือกรอกชื่อสินค้า ดึงข้อมูลแบบเรียลไทม์
2. **การ์ด Empty-State สำหรับสินค้าที่ไม่มีมุม:**
   - แสดงข้อความและปุ่ม 3 ทางเลือก:
     - `[ ⚡ ถ่ายด่วนฟรีสไตล์ (Instant Free Take) ]` ➔ สร้างมุมเริ่มต้นและข้ามไปสเต็ป 2 ทันที
     - `[ ➕ สร้างมุม / ใส่สคริปต์เอง ]` ➔ เปิดแผ่นชีทพิมพ์ Hook + บทย่อ 3 บรรทัด
     - `[ ✨ ให้ AI คิด 7 มุมอัตโนมัติ ]` ➔ เรียก AI แพลนเนอร์
   - ปลดล็อคปุ่มยืนยันสเต็ป 1 ให้สามารถกดดราฟต์ได้ 100% เสมอ
3. **ฟังก์ชันอัปโหลดคลิปจากอัลบั้มในสเต็ป 2:**
   - เพิ่มปุ่ม `📁 แนบคลิปจากมือถือ (Camera Roll / Files)` คู่กับปุ่ม `📹 กดเปิดกล้องถ่ายทำ (Guided Take)`
   - แสดงหลอด Progress การอัปโหลด พร้อมวิดีโอพรีวิวตัวอย่าง
4. **ส่วนควบคุมเสียงพากย์และ BGM ก่อนเรนเดอร์:**
   - ปุ่ม `🔊 ฟังเสียงพากย์ Fenrir` ทดสอบฟังก่อนตัดต่อ
   - สวิตช์สลับเสียงเพลงประกอบไอที

---

### 🧪 เอเจนต์ที่ 3: Testing & Parity Verification
1. **Automated Unit & Integration Tests:**
   - เขียนเทส `tests/test_mobile_end_to_end_flow.py`:
     - Test 1: สร้างเซสชันและดราฟต์จากสินค้าที่ไม่มีมุม (`empty_angles`) ➔ ต้องสำเร็จ 100%
     - Test 2: เพิ่มสินค้าด่วนผ่าน API ➔ ถูกบันทึกลง ProductStore
     - Test 3: อัปโหลดคลิปจากมือถือจำลอง ➔ ผูกเข้าเซสชันและเรนเดอร์ได้
     - Test 4: Regression suite ตรวจสอบความเข้ากันได้กับ Desktop Pro Editor
2. **Puppeteer Mobile Verification:**
   - จำลองหน้าจอ iPhone 15 Pro Max ทดสอบการกดถ่ายด่วนฟรีสไตล์ และการเปลี่ยนสเต็ป

---

## 🔒 กฎเหล็กที่ต้องยึดถือ (Strict Constraints)
- **Rule 10/18:** Dual-Mode Additive Only — ห้ามแตะต้องฟังก์ชันเดิมของ Desktop Pro Timeline
- **Rule 11/15:** ห้ามทิ้งไฟล์ขยะทดสอบไว้ใน `04_Exports/` หรือระบบ
- **Rule 17:** มาตรฐานซับ `Mali-Bold` 88px, กล่องสเปกสีส้ม `#FF6622`, เสียง Fenrir
