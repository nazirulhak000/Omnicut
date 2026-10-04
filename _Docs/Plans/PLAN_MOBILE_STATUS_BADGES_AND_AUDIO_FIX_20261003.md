# 📱 แผนงานปรับปรุงโฟลว์มือถือ (Mobile Studio Polish: Status Badges, Attached Footage & Auto Guide Audio)

> **วันที่:** 2026-10-03\
> **ดำเนินการโดย:** Antigravity (Gemini 2.5 Pro)\
> **Jev Decision:** Choice A (Comprehensive Mobile Clarity & Audio Fix) — Confidence: 1.00 (`verdict: proceed`)\
> **เอกสารอ้างอิง:** [AGENTS.md](file:///d:/Programmer/All%20Project/Omnicut/AGENTS.md) • [TODO.md](file:///d:/Programmer/All%20Project/Omnicut/TODO.md)

---

## 🎯 ปัญหาที่พบจากผู้ใช้งาน (User Feedback Analysis)

1. **ไม่รู้ว่าสินค้า/มุมไหนตัดแล้วเรียบร้อย หรืออันไหนยังไม่ตัด:**
   - ในหน้าสเต็ป 1 ไม่มีป้ายกำกับสถานะว่ามุมไหนเรนเดอร์เป็นคลิปเสร็จแล้ว หรือมุมไหนยังไม่ได้ตัด ทำให้ผู้ใช้ต้องเดา
2. **ไม่ทราบว่าสคริปต์/มุมไหนมีคลิปวัตถุดิบแนบอยู่แล้ว:**
   - ในสเต็ป 1 และสเต็ป 2 ไม่บอกชื่อไฟล์คลิปที่แนบอยู่ (`attached_raw`) ทำให้ผู้ใช้ไม่รู้ว่ามุมนี้พร้อมกดเรนเดอร์ได้เลย หรือต้องถ่ายใหม่
3. **เสียงไกด์ในหน้า Guided Take (MobileFilmingPage) ไม่เล่นอัตโนมัติตั้งแต่ช็อตที่ 2 ขึ้นไป:**
   - เมื่ออัดช็อตที่ 1 เสร็จและกดยืนยัน พอเริ่มกดอัดช็อตที่ 2 เสียงพูดนำไม่เล่นออโต้ ต้องกดปุ่มฟังเสียงเอง
   - **สาเหตุเชิงลึก:** เกิดจาก Event Listener Leak ในฟังก์ชัน `playGuideAudioForBeat` ซึ่งผูกฟังก์ชัน `onTick` เข้ากับ `timeupdate` ของ `<audio>` โดยไม่ได้ถอดออกเมื่อช็อต 1 จบ พอช็อต 2 เริ่มเล่นที่ `currentTime = 5.2s` ตัว `onTick` เก่าของช็อต 1 (ที่คอยดัก `currentTime >= 5.2s`) จะทำงานทันทีแล้วสั่ง `audio.pause()` ภายในเสี้ยววินาที ทำให้เสียงหยุดเล่นทันที!

---

## 🛠️ แผนการแก้ปัญหาและขั้นตอนการทำงาน (Action Plan)

### เฟส 1: ยกระดับ Backend Catalog ให้ส่งสถานะและรายละเอียดคลิป (Backend Enrichment)
- **ไฟล์เป้าหมาย:** [scripts/mobile_quick_studio.py](file:///d:/Programmer/All%20Project/Omnicut/scripts/mobile_quick_studio.py)
- **การเปลี่ยนแปลง:**
  1. เพิ่มการตรวจสถานะการเรนเดอร์ของแต่ละมุม (`is_rendered`, `rendered_video_url`, `export_id`)
  2. เพิ่มรายละเอียดไฟล์คลิปที่แนบ (`has_footage`, `attached_raw_name`, `attached_raw_path`)
  3. สรุปภาพรวมระดับสินค้า (`rendered_count`, `footage_count`, `total_angles`) เพื่อให้หน้าเลือกรู้ได้ทันทีว่าตัดไปแล้วกี่มุม

### เฟส 2: แสดงป้ายสถานะและรายละเอียดคลิปในหน้าเลือกสินค้า (Step 1 UI)
- **ไฟล์เป้าหมาย:** [frontend/src/components/MobileQuickStudio.jsx](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/MobileQuickStudio.jsx)
- **การเปลี่ยนแปลง:**
  1. **การ์ดสินค้า:** แสดงตัวเลขสรุป เช่น `✅ ตัดเสร็จแล้ว 2/7 มุม • 📎 มีคลิป 5 มุม`
  2. **การ์ดมุมนำเสนอ (Angle Cards):**
     - หากตัดแล้ว: แสดงป้ายสีเขียวนีออน `✅ ตัดเสร็จแล้ว (พร้อมโพสต์)`
     - หากมีคลิปแนบแล้วแต่ยังไม่ตัด: แสดงป้ายสีฟ้า `📎 แนบคลิปแล้ว: [ชื่อไฟล์]`
     - หากยังไม่มีคลิป: แสดงป้ายสีเทา/ส้ม `⏳ ยังไม่ตัด (รอถ่ายคลิป)`

### เฟส 3: ป้ายแจ้งเตือนคลิปพร้อมใช้งานในหน้าถ่ายทำ/แนบไฟล์ (Step 2 UI)
- **ไฟล์เป้าหมาย:** [frontend/src/components/MobileQuickStudio.jsx](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/MobileQuickStudio.jsx)
- **การเปลี่ยนแปลง:**
  1. หากมุมนี้มีคลิปวัตถุดิบเดิมอยู่แล้ว (`attached_raw`):
     - แสดงกล่องแบนเนอร์สีเขียว/ฟ้า: `✅ คลิปวัตถุดิบพร้อมใช้งาน: [ชื่อไฟล์]`
     - อธิบายชัดเจน: `คุณสามารถกด "ประกอบคลิปและเรนเดอร์" ได้ทันที หรือจะถ่ายใหม่/เลือกคลิปใหม่ด้านล่างเพื่อแทนที่`
  2. หากยังไม่มีคลิป:
     - แสดงคำแนะนำสีส้ม: `⚠️ ยังไม่มีคลิปวัตถุดิบ: กรุณาถ่ายสดหน้ากล้อง หรือเลือกคลิปจากอัลบั้มมือถือ`
     - หากกดเรนเดอร์โดยไม่มีคลิป: แจ้งเตือนให้ถ่ายหรือเลือกคลิปก่อน ไม่ปล่อยให้ระบบแครช

### เฟส 4: แก้บั๊กเสียงไกด์ออโต้ใน Guided Take ช็อตที่ 2 ขึ้นไป (MobileFilmingPage Fix)
- **ไฟล์เป้าหมาย:** [frontend/src/components/MobileFilmingPage.jsx](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/MobileFilmingPage.jsx)
- **การเปลี่ยนแปลง:**
  1. สร้าง `activeAudioTickRef = useRef(null)` จัดการ Lifecycle ของ Event Listener ให้สะอาดยอดเยี่ยม
  2. สร้างฟังก์ชัน `stopGuideAudio()` ลบ listener เก่าและ pause เสียงอย่างปลอดภัย
  3. เรียก `stopGuideAudio()` ก่อนเริ่มเล่นเสียงใหม่ทุกครั้ง และใน `stopRecorder` เพื่อไม่ให้มี listener ตกค้าง
  4. ปรับ `handleStartRecording` ให้เรียกเล่นเสียงทันทีพร้อมดัก Play Promise บน iOS Safari อย่างราบรื่น

### เฟส 5: การทดสอบและการตรวจสอบ (Verification & Testing)
1. รัน Unit Tests: `pytest tests/test_mobile_quick_studio.py`
2. รัน Browser Tests: `pytest tests/motion_capture/test_mobile_studio_browser.py`
3. รัน Frontend Build: `npm run build` ใน `frontend/`
4. ทดสอบความถูกต้องด้วย Puppeteer และบน iPhone 15 Pro Max จริง
