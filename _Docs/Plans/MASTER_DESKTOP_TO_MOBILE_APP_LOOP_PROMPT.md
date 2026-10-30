# 🔄 AUTONOMOUS UX/UI REFINEMENT LOOP — DESKTOP STUDIO TO NATIVE MOBILE APP PERFECTION
# พรอมพ์ลูปยกระดับ "โหมดคอม (Desktop Studio Workspace)" สู่ Native Mobile App 100% ทีละเมนูทุกฟังก์ชัน

```markdown
คุณคือสุดยอดทีมพัฒนา Mobile App และ UI Architecture ประสบการณ์ระดับโลกที่รวม 3 ทักษะหลัก:
1. 🎨 `/impeccable` — Lead UI/Motion Designer ผู้เชี่ยวชาญการแปลงหน้าจอระดับ Professional Desktop ให้กลายเป็น UI มือถือที่หรูหรา คลีน สะกดสายตา และมี Micro-interactions สัมผัสพรีเมียม
2. 📱 `/ui-ux-pro-max` — Senior Native Mobile Architect ผู้เชี่ยวชาญ Apple Human Interface Guidelines (HIG), Thumb-Zone Reachability, 100dvh Viewport Locking, Touch Targets >=44px, และ Haptic Feedback
3. 🔍 `/scrutinize` — Principal Product QA & Real-User Roleplayer ผู้สวมบทบาทครีเอเตอร์ตัดต่อวิดีโอบน iPhone 15 Pro Max (430 × 932 pt) ตรวจจับทุกจุดที่ปุ่มเล็กเกินไป, ตัวหนังสือล้น, กวาดนิ้วไม่ติด, เมนูเลื่อนหลุดขอบ, หรือฟังก์ชันคอมที่ยังใช้งานบนมือถือได้ไม่คล่องตัว

---

## 🎯 ภารกิจหลัก (Objective)
แปลงและยกระดับ **"โหมดคอม (Desktop Studio Workspace)"** ซึ่งเป็นโหมดหลักที่มีฟังก์ชันการทำงานครบถ้วนที่สุดของ OmniCut Pro Studio ให้สามารถแสดงผลและใช้งานบนสมาร์ตโฟน (โฟกัส iPhone 15 Pro Max / Safari & PWA 430×932 pt) ได้แบบ **"100% Native Mobile App"** โดย:
1. **ไม่ตัดทอนฟังก์ชันโปรของโหมดคอมแม้แต่อย่างเดียว** (ยังคงครบทั้ง 20 Angles, NLE Timeline, Voice Waveform, Karaoke Subtitle, KanBan 4 เฟส, MPC Soundboard)
2. **ปรับแต่งการจัดวาง (Ergonomics) และพฤติกรรมสัมผัส (Touch Mechanics)** ให้เข้ากับมือเดียว นิ้วโป้งกวาดถึง รูดลื่น ไม่ดีดหลุดขอบ ไม่ซูมจอเอง
3. **ตรวจสอบทีละเมนู ทีละฟังก์ชันอย่างเป็นระบบ** วนซ้ำ (Recursive Loop) จากเมนูที่ 1 ถึงเมนูที่ 8 ไปเรื่อยๆ จนกว่าทุกเมนูจะได้คะแนน 10/10 สมบูรณ์แบบ 100%!

---

## 🗺️ แผนผังเมนูโหมดคอมที่ต้องวนรอบตรวจ (Desktop Workspace Menu Traversal Matrix)

ทุกรอบการวนลูป (Cycle) คุณต้องเข้าตรวจ ประเมิน และปรับโค้ดจริงตามลำดับ 8 สถานีนี้ ห้ามข้ามขั้นตอน:

```
[รอบ Cycle N: ตรวจโหมดคอมสู่โมบายแอพ]
  ├── สถานี 1: แถบหัว & นำทาง (Adaptive Dynamic Topbar & Floating Capsule Sidebar)
  ├── สถานี 2: สินค้า ➜ คลิป (ProductToClip.jsx — สคริปต์ 20 มุมมอง & ปรับจูน)
  ├── สถานี 3: แทร็กเกอร์ 4 เฟส (ContentTrackerHub.jsx — KanBan แดชบอร์ด & สั่งผลิต)
  ├── สถานี 4: ห้องตัดต่อ & ไทม์ไลน์ 9:16 (EditorShell.jsx, SequencePlayer.jsx, Timeline.jsx)
  ├── สถานี 5: คลังคลิปส่งออก (ExportGallery.jsx — 9:16 วิดีโอ, แคปชัน, เซฟเข้า Photos)
  ├── สถานี 6: คลังวัตถุดิบ & ซาวด์บอร์ด (MediaAssetsHub.jsx — MPC Pads & Audio Player)
  ├── สถานี 7: สถิติ, ตั้งค่า & คู่มือ (AnalyticsHub.jsx, SystemSettings.jsx, UserGuide.jsx)
  └── สถานี 8: ป๊อปอัป, หน้าต่าง & สัมผัสรวม (Modal.jsx, CoverStudio, Toast.jsx, index.css)
```

---

### 📍 สถานีที่ 1: แถบหัว & แถบนำทาง (Adaptive Dynamic Topbar & Sidebar Navigation)
- [ ] **1.1 Slimline 44pt Topbar**: ความสูงแถบบนต้องเพรียวบาง 44pt เว้นระยะ `env(safe-area-inset-top)` รับ Dynamic Island พอดี ไม่กินพื้นที่จอ OLED
- [ ] **1.2 Connection & Engine Pill**: ป้ายสถานะ Engine/PC กะทัดรัด แตะเพื่อดู Latency Ping ได้
- [ ] **1.3 Project Switcher Dropdown**: กล่องเลือกโปรเจกต์ขนาดใหญ่ แตะง่าย ไม่ล้นขอบจอ
- [ ] **1.4 Floating Capsule / Bottom Bar**: เมนูเปลี่ยนหน้าหลัก 8 เมนู ปรับเป็น Floating Capsule ลอยล่างหรือลิ้นชักที่เปิดปิดได้ด้วยนิ้วโป้ง พร้อม Haptic Tick 10ms เมื่อแตะเปลี่ยนหน้า

### 📍 สถานีที่ 2: สินค้า ➜ คลิป (`ProductToClip.jsx`)
- [ ] **2.1 1-Tap Paste Button**: ปุ่มใหญ่ `วางลิงก์จากคลิปบอร์ด` กว้างเต็มจอ แตะทีเดียวอ่าน `navigator.clipboard.readText()` สกัดชื่อสินค้าและรูป Hero ทันที
- [ ] **2.2 Input Font >= 16px**: ทุกช่องกรอก (URL, ชื่อสินค้า, ราคา, บรีฟ) บังคับขนาดฟอนต์ 16px ห้าม Safari ซูมหน้าจอเอง
- [ ] **2.3 20-Angle Selector Pills**: ชิปเลือก 20 มุมมองเลื่อนแนวนอนแบบ Snap แตะเลือกได้ด้วยนิ้วโป้ง มีตัวเลขบอกมุมมองที่เลือก
- [ ] **2.4 Character & Voice Tuner**: สลับตัวละคร (น้องนุ้ย / พี่บ่าว) และปรับสไตล์เสียงด้วยปุ่มความสูงไม่ต่ำกว่า 48px
- [ ] **2.5 Script Review & Live Linter**: กล่องตรวจสคริปต์แบบการ์ด แสดงคำเตือนคำต้องห้าม (เช่น `...` หรือคำทับศัพท์อังกฤษ) ชัดเจน
- [ ] **2.6 SessionStorage Auto-Restore**: พิมพ์บทหรือวางลิงก์ค้างไว้ สลับไปแอปอื่นแล้วกลับมา ข้อมูลต้องไม่หาย

### 📍 สถานีที่ 3: แทร็กเกอร์ 4 เฟส (`ContentTrackerHub.jsx`)
- [ ] **3.1 Mobile Segmented Phase Bar**: แถบแท็บ 4 เฟส (สคริปต์ ➜ เสียง ➜ วิดีโอ ➜ เสร็จ) ติดหนึบด้านบน (Sticky) มีตัวเลข Badge สรุปจำนวนคลิปในแต่ละเฟส
- [ ] **3.2 Swipeable KanBan Columns**: คอลัมน์กว้าง 88vw-90vw กวาดนิ้วปัดซ้าย-ขวาแบบ Snap เลื่อนดูแต่ละเฟสได้ลื่นไหล
- [ ] **3.3 Job Progress & Live Status**: การ์ดแสดงสถานะ SSE มี Progress Bar สีนีออนชัดเจน พร้อมปุ่มสั่งผลิตและยกเลิกที่แตะง่าย
- [ ] **3.4 Quick Action Drawer**: แตะการ์ดแล้วเปิด Bottom Sheet แสดงรายละเอียดและปุ่มลัด ไม่บังสายตา

### 📍 สถานีที่ 4: ห้องตัดต่อ & สร้างคลิป (`EditorShell.jsx` + `SequencePlayer.jsx` + `Timeline.jsx`)
- [ ] **4.1 9:16 Vertical Stage**: หน้าจอพรีวิว 9:16 ขนาดใหญ่เต็มตาสัดส่วนถูกต้อง มีขอบ Safe Zone TikTok ด้านขวาและด้านล่าง
- [ ] **4.2 Double-Tap Play/Pause**: แตะ 2 ครั้งบนวิดีโอเพื่อสั่งเล่นหรือหยุดทันที สไตล์ Instagram/TikTok
- [ ] **4.3 Timeline Touch Ergonomics**: แถบไทม์ไลน์ใส่ `touch-action: none` เพื่อให้ลาก Playhead ได้แม่นยำ Safari ไม่แย่งเลื่อนหน้าจอ
- [ ] **4.4 Scrubbing Playhead**: หัวอ่าน Playhead หนา 3.5px สีขาวเด่น จับลากง่ายแม้นิ้วใหญ่
- [ ] **4.5 Mobile Toolbar (Cut / Trim / Split)**: ปุ่มตัดหัว (Q), ตัดท้าย (W), แยกช็อต ปรับเป็นปุ่มสัมผัสขนาดใหญ่ $\ge 44\text{px}$ เหนือไทม์ไลน์
- [ ] **4.6 Subtitle Karaoke QC**: แสดงตัวอย่างซับไตเติล `Mali-Bold` ไฮไลต์คำสีเขียวนีออน `#66FF00` ตรงตามเฟรมจริง 100%

### 📍 สถานีที่ 5: คลังคลิปส่งออก (`ExportGallery.jsx`)
- [ ] **5.1 9:16 Video Card Grid**: จัดเรียงการ์ดวิดีโอ 9:16 ขอบมน มี Thumbnail คมชัด และตัวบอกระยะเวลา
- [ ] **5.2 Floating Batch Action Bar**: แถบคำสั่งแบบกลุ่มลอยเหนือขอบล่าง มีปุ่มเลือกทั้งหมด, ดาวน์โหลด, และส่งต่อ
- [ ] **5.3 1-Tap Copy Caption & Tags**: ปุ่มคัดลอกแคปชันขายของพร้อมแฮชแท็ก แตะแล้วสั่น Haptic 15ms ตอบสนองทันที
- [ ] **5.4 Save Direct to Photos (Camera Roll)**: รองรับ Web Share API (`navigator.share({ files })`) ให้ผู้ใช้บันทึกลง Photos ได้ใน 1 แตะ
- [ ] **5.5 TikTok Showcase ID Copy**: ปุ่มคัดลอกรหัสสินค้า TikTok Shop แตะปุ๊บพร้อมเปิดแอป TikTok สลับไปโพสต์ได้ทันที

### 📍 สถานีที่ 6: คลังวัตถุดิบ & ซาวด์บอร์ด (`MediaAssetsHub.jsx`)
- [ ] **6.1 2-Column MPC Soundboard Pads**: ปุ่มเล่น SFX และเพลง จัดเป็นตาราง 2 คอลัมน์สัมผัสเต็มมือ กดแล้วมีเสียงทันทีแบบไม่มีดีเลย์
- [ ] **6.2 Sticky Mini Audio Player**: แถบเล่นเสียงย่อส่วนติดหนึบด้านล่าง แสดงชื่อเสียงที่กำลังเล่น พร้อมปุ่ม Stop และปรับความดัง
- [ ] **6.3 Clean B-Roll Browser**: แสดงรายการฟุตเทจสะอาดไร้ซับจีน จัดหมวดหมู่ชัดเจน แตะเพื่อพรีวิวได้ทันที

### 📍 สถานีที่ 7: สถิติ, ตั้งค่า & คู่มือ (`AnalyticsHub.jsx`, `SystemSettings.jsx`, `UserGuide.jsx`)
- [ ] **7.1 Responsive Analytics**: ชาร์ตและตารางสรุปยอดคลิป รองรับการเลื่อนแนวนอน (Horizontal Scroll) สบายตา ไม่บีบตัวหนังสือ
- [ ] **7.2 System Settings Pills**: เมนูตั้งค่าจัดเป็นหมวดหมู่แบบ Horizontal Carousel Pills แตะสลับหัวข้อได้ด้วยนิ้วเดียว
- [ ] **7.3 User Guide Touch Accordion**: หัวข้อคู่มือและ FAQ ขยาย-ยุบได้ด้วยพื้นที่สัมผัส $\ge 48\text{px}$ พร้อมตัวค้นหาด่วน

### 📍 สถานีที่ 8: ป๊อปอัป, หน้าต่าง & สัมผัสรวม (Global Modals, Sheets & Shell)
- [ ] **8.1 iOS Bottom Sheet Conversion**: Modal ทุกตัว (เช่น `CoverStudioModal`, `ShortcutsModal`, `MediaPickerModal`) แปลงเป็น Bottom Sheet สไตล์ iOS
- [ ] **8.2 Drag Handle & Swipe to Dismiss**: ทุก Sheet มีขีดจับตรงกลาง (`w-12 h-1.5 rounded-full bg-white/20`) และรองรับการปัดรูดลงเพื่อปิด
- [ ] **8.3 Dynamic Island Capsule Toast (`Toast.jsx`)**: การแจ้งเตือน Toast ย้ายไปอยู่ติ่งบนสุด สไลด์ลงมาจาก Dynamic Island ไม่บังปุ่มด้านล่าง
- [ ] **8.4 100dvh Lock & No Elastic Rubber-banding**: ล็อกหน้าจอด้วย `100dvh` และ `overscroll-behavior: none` กำจัดอาการหน้าจอดึ๋งหลุดขอบของ Safari
- [ ] **8.5 Verb-First Button Cleanliness**: ปุ่มทุกปุ่มในโหมดคอมต้องขึ้นต้นด้วยคำกริยาและไม่มีไอคอนหรือสัญลักษณ์นำหน้า ตามกฎ Rule 3.8 / 4.8

---

## 🔁 ระเบียบการวนลูปทีละเมนู (Sequential Execution Loop)

ทุกครั้งที่สั่งรัน ให้ AI ดำเนินการตามลูปนี้:

```
[ขั้นตอนที่ 1] สวมบทบาทผู้ใช้ iPhone 15 Pro Max เข้าตรวจสถานีปัจจุบัน (เช่น สถานีที่ 1)
[ขั้นตอนที่ 2] ตรวจสอบตามเช็กลิสต์ย่อยทุกข้อ และให้คะแนน (เต็ม 100 คะแนน)
[ขั้นตอนที่ 3] หากข้อใดได้คะแนนตกหรือไม่ลื่นไหล ให้ลงมือแก้โค้ดจริงในไฟล์ทันที
[ขั้นตอนที่ 4] รันเทส `cd frontend; npm test -- --run` ให้ผ่าน 100%
[ขั้นตอนที่ 5] สรุปผลของสถานีนั้น แล้วขยับไปสถานีถัดไป (สถานีที่ 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8)
[ขั้นตอนที่ 6] เมื่อครบทั้ง 8 สถานี ตรวจสอบว่ามีสถานีไหนได้ต่ำกว่า 98/100 หรือไม่ 
             หากมี ➜ วนรอบใหม่ (Cycle N+1) เจาะแก้จุดนั้นจนกว่าทุกสถานีจะสมบูรณ์แบบ 100%!
```

### เกณฑ์การให้คะแนนแต่ละเมนู (10 มิติ มิติละ 10 คะแนน รวม 100 คะแนน / ผ่านเกณฑ์ที่ 98 คะแนน):
1. **Thumb Reachability (10):** ปุ่มคำสั่งหลักอยู่ในโซนนิ้วโป้งเอื้อมถึงในมือเดียว
2. **Visual Ergonomics & Spacing (10):** ตัวหนังสือไม่ล้นขอบ ฟอนต์คมชัด คอนทราสต์สูง
3. **Touch Sensation & Haptics (10):** มีการยุบตัวเมื่อกด (`active:scale-[0.98]`) และสั่น Haptic ตอบสนอง
4. **Desktop Pro Power Preserved (10):** ฟังก์ชันโปรของโหมดคอมอยู่ครบ 100% ไม่ถูกตัดทิ้ง
5. **Safari & Viewport Lock (10):** จอไม่ดึ๋งหลุดขอบ ไม่ซูมเองเมื่อแตะพิมพ์ (ฟอนต์ $\ge 16\text{px}$)
6. **Timeline & Scrubbing Precision (10):** ลากตัดต่อได้แม่นยำ ไม่กระตุก Safari ไม่แย่งเลื่อน
7. **Bottom Sheet & Gestures (10):** ป๊อปอัปเป็น Sheet ปัดลงปิดได้ มี Drag Handle ชัดเจน
8. **Verbal Button Cleanliness (10):** ปุ่มเป็นคำกริยา ไม่มีไอคอนสัญลักษณ์นำหน้า (Rule 3.8 / 4.8)
9. **Zero Accidental Actions (10):** ข้อมูลไม่หายเมื่อสลับแอป มีปุ่ม Undo หรือ Confirm ป้องกันพลาด
10. **Native App Joy (10):** ความรู้สึกลื่นไหลเทียบเท่าแอปแท้ที่ดาวน์โหลดจาก App Store

---

## 🛑 เงื่อนไขการบรรลุเป้าหมาย (Completion Gate)
1. ทุกสถานี (สถานีที่ 1 ถึง 8) ผ่านการตรวจและได้คะแนน **>= 98/100** ครบทุกสถานี
2. ผ่านการทดสอบ Vitest ใน `frontend` ครบ 100% (1,055/1,055 tests pass)
3. รัน `npm run build` สำเร็จ ผลิต Production Bundle สมบูรณ์ ไร้ข้อผิดพลาด
4. บันทึกความคืบหน้าลงใน `TODO.md` และสรุปผลเข้า `HISTORY.md` โดยระบุ `ดำเนินการโดย: <Agent> (<Model>)` ตามกฎ Rule 4.14

**เริ่มการวนลูปสถานีที่ 1 ได้ทันที!**
```
