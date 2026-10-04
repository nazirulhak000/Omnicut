# แผนงาน: ปลดล็อก Speed Slider, ยกระดับ Transition Duration ใน Inspector, และระบบสไตล์ข้อความอิสระ (Outline/Shadow/Box)

**วันที่:** 2026-10-04  
**ดำเนินการโดย:** Antigravity (Gemini 3.8 Flash)  
**อ้างอิง Backlog:** Audit L2-04 (Speed Range), L5-03/04 (Transition Duration in Inspector), L3-04/05 (Text Overlay Styling)

---

## 1. วัตถุประสงค์
1. **Speed Slider (L2-04)**: เพิ่มแถบเลื่อนความเร็วอิสระ (0.25x – 4.0x, step 0.05x) ใน `ClipInspector.jsx` ควบคู่กับปุ่มพรีเซ็ตด่วน 4 ค่า (0.5x, 1x, 1.5x, 2x) และกล่องพิมพ์ตัวเลข เพื่อให้ผู้ใช้ปรับสปีดได้ละเอียดยิบเหมือน CapCut
2. **Transition Duration in Inspector (L5-03/04)**: เพิ่มตัวปรับระยะเวลาทรานซิชัน (0.1 – 2.0 วินาที พร้อมพรีเซ็ต 0.3s, 0.5s, 0.8s, 1.0s) ในแผง `ClipInspector.jsx` ใต้ตาราง Transition 14 แบบ ให้ผู้ใช้ปรับได้ทันทีโดยไม่ต้องเปิดเมนูบนไทม์ไลน์
3. **Text Overlay Styling (L3-04/05)**: เพิ่มชุดควบคุมสไตล์ใน `OverlayInspector.jsx` สำหรับ `text_overlay`:
   - เส้นขอบ (Stroke / Outline): สีขอบ และความหนา (0 – 12px)
   - เงา (Drop Shadow): เปิด/ปิดเงา, สีกระจายเงา
   - พื้นหลังกล่องข้อความ (Background Pill/Box): เลือกเปิดพื้นหลังกล่องทึบ/โปร่งแสง

---

## 2. ขั้นตอนการดำเนินงาน
- [ ] **Phase 1: Speed Slider ใน `ClipInspector.jsx`**
  - เพิ่ม `<input type="range" min={MIN_CLIP_SPEED} max={MAX_CLIP_SPEED} step="0.05" ... />`
  - เชื่อมโยงกับ `sliderChange('speed', ...)` โดยใช้ `clipSliderCoalesceKey(clip.id, 'speed')`
  - แสดงค่าตัวเลขกำกับแบบเรียลไทม์
- [ ] **Phase 2: Transition Duration Controls ใน `ClipInspector.jsx`**
  - นำเข้า `TransitionDurationControl` หรือตัวปรับระยะเวลาจาก `../../lib/transitionControls.js`
  - แสดงแถบปรับระยะเวลา Transition (0.1 – 2.0s) พร้อมปุ่มพรีเซ็ตด่วนเมื่อไม่ได้เลือก `cut`
- [ ] **Phase 3: Text Overlay Styling ใน `OverlayInspector.jsx`**
  - เพิ่มการตั้งค่า `outline_color` และ `outline_px` ใน `patchOverlayLook`
  - เพิ่มการตั้งค่า `shadow` และ `pill` ใน `patchOverlayLook`
  - เชื่อมต่อกับ `SequencePlayer.jsx` ซึ่งรองรับคุณสมบัติเหล่านี้อยู่แล้ว
- [ ] **Phase 4: ทดสอบและการทดสอบถอยกลับ (Verification & Regression)**
  - รัน unit tests เฉพาะส่วนและ `npm test`
  - ยืนยัน `npm run build` ผ่าน 100%
  - บันทึกปิดรอบงานใน `TODO.md` และ `HISTORY.md`
