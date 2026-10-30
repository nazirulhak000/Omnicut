# 🔄📱 MASTER PROMPT: Continuous Menu-by-Menu Native Mobile Refinement Loop
# พรอมพ์ลูปยกระดับ UX/UI มือถือทีละเมนู วนซ้ำจนสมบูรณ์แบบ 100% (Native Mobile App Standard)

```markdown
คุณคือสุดยอดทีมพัฒนา Mobile App ประสบการณ์ระดับโลกที่รวม 3 ทักษะหลัก:
1. 🎨 `/impeccable` — Lead UI/Motion Designer ผู้ออกแบบความงาม สัมผัส Micro-interactions และ Frosted Glass แสงเงาขั้นเทพ
2. 📱 `/ui-ux-pro-max` — Senior iOS/Android Native Architect ผู้เชี่ยวชาญ Apple Human Interface Guidelines (HIG), Thumb-zone ergonomics, 100dvh viewport locking และ Haptic Touch
3. 🔍 `/scrutinize` — Principal Product QA & Real-User Roleplayer ผู้ตรวจจับทุกความหน่วง จุดสะดุด จุดที่นิ้วเอื้อมไม่ถึง และฟังก์ชันที่ยังขาดสัมผัส Native App

---

## 🎯 ภารกิจหลัก (Objective)
ยกระดับประสบการณ์การใช้งาน OmniCut บนสมาร์ตโฟน (โฟกัส iPhone 15 Pro Max / Safari & PWA 430×932pt) ให้มีความรู้สึก ลื่นไหล คลีน และตอบสนองเหมือน **"Native Mobile App แท้ 100%"** 
โดยต้อง **"ตรวจสอบและปรับแต่งทีละเมนู ทีละฟังก์ชันอย่างละเอียด"** และ **"วนลูปกลับมาเช็กซ้ำทุกเมนูไปเรื่อยๆ"** จนกว่าทุกเมนูจะได้คะแนนเต็ม 10/10 และไม่มีจุดสะดุดแม้แต่นิดเดียว!

---

## 🗺️ แผนผังเมนูและฟังก์ชันที่ต้องวนรอบตรวจ (Menu Traversal Matrix)

ทุกรอบการวนลูป (Cycle) คุณต้องเข้าตรวจและปรับปรุงตามลำดับ 6 สถานีนี้ ห้ามข้ามขั้นตอน:

### 📍 สถานีที่ 1: เมนูแท็บ "วันนี้" (`TodayScreen.jsx` + `ProductionJobCard.jsx`)
- [ ] **1.1 Connection & Engine Status**: ป้ายสถานะเครื่อง PC / Colab ชัดเจน มี Ping latency และสถานะสลีป/ตื่น
- [ ] **1.2 Realtime SSE Production Job Cards**: การ์ดแสดงสถานะผลิตคลิปแบบสด มี Progress bar สีเขียวนีออน สเตจงาน 4 ขั้น (พากย์เสียง ➜ ถอดคำ ➜ ซับ ➜ เรนเดอร์) พร้อม ETA นับถอยหลัง
- [ ] **1.3 Action Required Queue**: รายการ "คลิปที่รอคุณอนุมัติ" มี badge ตัวเลขนีออนเตือน แตะแล้วกระโดดไปหน้าตรวจได้ทันที
- [ ] **1.4 Quick Stats & Storage**: สรุปจำนวนคลิปที่พร้อมโพสต์วันนี้ และพื้นที่แคชคงเหลือ
- [ ] **1.5 Server Sleeping / Wake Banner**: แถบแจ้งเตือนเมื่อเซิร์ฟเวอร์ยังไม่ตอบสนอง พร้อมปุ่มปลุกและแอนิเมชัน Pulse

### 📍 สถานีที่ 2: เมนูแท็บ "สร้าง" (`IntakeScreen.jsx` + `ScriptReviewDeck.jsx`)
- [ ] **2.1 1-Tap Clipboard Paste**: ปุ่มใหญ่เต็มมือนิ้วโป้ง `วางลิงก์จากคลิปบอร์ด` กดปุ๊บอ่าน `navigator.clipboard.readText()` และดึงข้อมูลอัตโนมัติ ไม่ต้องแตะค้างวางเอง
- [ ] **2.2 Hero Image & Spec Extractor**: สกัดรูปสินค้าแบบ High-res และจุดขายทันที มีแผ่น Sheet ให้แตะเลือกรูป Hero สวยๆ
- [ ] **2.3 Hook Angle Selector**: ชิปเลือกแนวทางการเล่าเรื่อง (POV ดราม่าคู่รัก, แก้ปัญหา, เคล็ดลับด่วน, ช็อกราคา) แตะสลับง่ายด้วยนิ้วโป้ง
- [ ] **2.4 Script Review Deck (20 บท)**: การ์ดเต็มจอ `100dvh` สไตล์ Stories/Tinder กวาดนิ้วตรวจ ปัดขึ้นหรือแตะ `อนุมัติ` / `แก้บท` / `สุ่มใหม่`
- [ ] **2.5 Live Thai Subtitle Linter**: เช็กคำต้องห้ามตามกฎ (ห้ามมีจุดไข่ปลา `...`, ห้ามคำทับศัพท์อังกฤษที่สะกดเพี้ยน) แจ้งเตือนแบบ Inline
- [ ] **2.6 Floating 5s Undo Snackbar**: เมื่อกดอนุมัติหรือข้าม จะมีแถบย้อนกลับ 5 วินาทีลอยขึ้นมาให้แตะเปลี่ยนใจได้
- [ ] **2.7 Batch Produce Sticky Action**: แถบลอยล่างติดเหนือ Tab bar สำหรับกด `ผลิตคลิปที่ผ่านทั้งหมด` พร้อมแสดงเวลารวมโดยประมาณ

### 📍 สถานีที่ 3: เมนูแท็บ "ตรวจ" (`ReviewQueue.jsx` + `ReviewSheet.jsx`)
- [ ] **3.1 Queue Filter Chips**: ตัวกรอง "รอตรวจ", "อนุมัติแล้ว", "พร้อมโพสต์" สลับได้ทันทีแบบไม่ต้องโหลดใหม่
- [ ] **3.2 In-View 540p Proxy Player**: วิดีโอแนวตั้ง 9:16 เล่นอัตโนมัติแบบเบาเครื่อง (`playsinline muted loop`) เมื่อเลื่อนมาหยุดที่การ์ด
- [ ] **3.3 Fullscreen QC Sheet**: แตะการ์ดแล้วเปิด Sheet เต็มจอ ตรวจซับตัวหนังสือ, สีไฮไลต์ `#66FF00`, และ Safe Zone ขอบล่าง 420px
- [ ] **3.4 Split Frame Comparison**: สลับดูเฟรมเปิด Hook ➜ เฟรมแชท ➜ เฟรมปิดท้าย CTA ได้ใน 1 แตะ
- [ ] **3.5 Rapid Text Polish Stepper**: แตะเพื่อแก้คำผิดในบทพูดสั้นๆ ได้ทันทีโดยไม่ต้องเข้าหน้า Desktop
- [ ] **3.6 Sticky Decision Bar**: ปุ่มคู่ขนาดใหญ่เต็มมือนิ้วโป้ง: `อนุมัติส่งออก` (สีเขียว) และ `สั่งแก้ใหม่` (สีแดงเข้ม)

### 📍 สถานีที่ 4: เมนูแท็บ "โพสต์" (`MobilePostNext.jsx` + ตารางเวลาโพสต์)
- [ ] **4.1 Next-Due Post Hero Card**: การ์ดแสดงคลิปที่ต้องโพสต์เป็นอันดับถัดไป พร้อมเวลานับถอยหลังถึงเวลาโพสต์ทองคำ (เช่น 18:00 น.)
- [ ] **4.2 1-Tap Copy Caption & Tags**: ปุ่มกดทีเดียวก๊อปปี้แคปชันขายของ + แฮชแท็กติดเทรนด์ทั้งหมดเข้าคลิปบอร์ด พร้อม Haptic ตอบสนอง
- [ ] **4.3 1-Tap Copy Product Code**: ปุ่มก๊อปปี้รหัสสินค้า TikTok Shop เพื่อเอาไปแปะใน Showcase ได้ในพริบตา
- [ ] **4.4 Direct TikTok Deep Link**: ปุ่ม `เปิดแอป TikTok` ยิงตรงเข้าแอป TikTok ผ่าน Custom Scheme (`snssdk1180://`) พร้อม Fallback เป็นเว็บ
- [ ] **4.5 Pre-Post Safety Checklist Modal**: แผ่นเช็กลิสต์เด้งเตือน 3 ข้อก่อนกดโพสต์ (ติดตะกร้าหรือยัง, ซาวด์ตรงไหม, ลบคลิปทดสอบแล้วหรือยัง)
- [ ] **4.6 Daily Post Schedule Agenda**: รายการไทม์ไลน์โพสต์ประจำวัน (รอบเช้า, รอบบ่าย, รอบค่ำ) อัปเดตสถานะอัตโนมัติ

### 📍 สถานีที่ 5: เมนูแท็บ "อื่นๆ" & หน้าย่อย (More Hub & Sub-Screens)
- [ ] **5.1 Vertical Video Library (`MobileClipLibrary.jsx`)**: กริดวิดีโอ 9:16 สไตล์ iOS Photos แสดง Thumbnail คมชัด, ตัวกรองสินค้า, แตะค้างเพื่อเข้าโหมดเลือกหลายรายการ
- [ ] **5.2 Native Save to Camera Roll**: ใช้ `navigator.share({ files })` ยิงคลิปตรงเข้า Share Sheet ของ iOS ให้ผู้ใช้แตะบันทึกเข้า Photos ได้โดยตรง
- [ ] **5.3 9:16 Cover Sheet Generator (`CoverSheet.jsx`)**: ดูตัวอย่างหน้าปกคลิปพร้อม Safe Zone Overlay จำลองปุ่ม TikTok ด้านขวาและด้านล่าง
- [ ] **5.4 AI Command Center (`CommandCenter.jsx`)**: ศูนย์สั่งการด้วยชิปคำสั่งลัด เช่น `ล้างแคชเก่า`, `เช็กการเชื่อมต่อ`, `รีเฟรชคลังสินค้า`
- [ ] **5.5 Resumable Chunk Upload Tray (`UploadTray.jsx`)**: ถาดอัปโหลดวิดีโอดิบจากกล้องมือถือ แบ่ง Chunk อัปโหลดไม่หลุดแม้เน็ตช้า มีวงแหวน Progress สวยงาม

### 📍 สถานีที่ 6: เปลือกแอปและสัมผัสพื้นฐาน (Global Shell & Primitives)
- [ ] **6.1 Frosted Glass Tab Bar (`MobileShell.jsx`)**: แถบนำทางด้านล่างพื้นหลังโปร่งแสง `#07090E/85` เบลอ 24px (`backdrop-blur-2xl`) มีไฟนีออน Active และเว้นระยะ `env(safe-area-inset-bottom)`
- [ ] **6.2 Dynamic Island Toast Capsule (`Toast.jsx`)**: Toast ลอยลงมาจากขอบจอบน (`top-[calc(env(safe-area-inset-top)+8px)]`) สไตล์ Dynamic Island ไม่บังแท็บล่าง
- [ ] **6.3 Swipe Down to Dismiss Bottom Sheets**: Modal และ Sheet ทุกตัวต้องมีแถบจับด้านบน (`w-12 h-1.5 rounded-full bg-white/20`) และรองรับการปัดลงเพื่อปิด
- [ ] **6.4 Haptic Touch on All Actions**: ใส่ `navigator.vibrate?.([10])` ในทุกปุ่มกดหลักและการสลับแท็บ
- [ ] **6.5 100dvh Lock & No Auto-Zoom**: ล็อกหน้าจอด้วย `100dvh`, ป้องกันการเลื่อนหลุดขอบ (`overscroll-behavior: none`), บังคับฟอนต์ Input ทุกช่องไม่ต่ำกว่า 16px
- [ ] **6.6 Button Verbal Cleanliness**: ปุ่มทุกปุ่มต้องขึ้นต้นด้วยคำกริยาและไม่มีไอคอนหรือสัญลักษณ์นำหน้าเด็ดขาด ตามกฎ Rule 3.8 / 4.8

---

## 🔁 ระเบียบการวนลูปปรับแต่ง (Iterative Refinement Protocol)

ในแต่ละรอบ ให้ปฏิบัติตามลูป 5 ขั้นตอนนี้อย่างเคร่งครัด:

```
[รอบที่ N]
  ├── 1. ประเมินสถานีปัจจุบัน (Audit: Scrutinize & HIG Checklist)
  ├── 2. ระบุจุดบกพร่อง (Friction & UX Debt Identification)
  ├── 3. ลงมือแก้โค้ดจริง (Surgical Patching with Impeccable Craft)
  ├── 4. รันชุดทดสอบความถูกต้อง (Test: Vitest + Pytest)
  └── 5. ขยับไปสถานีถัดไป ➜ วนจนครบสถานีที่ 1 ถึง 6 ➜ สรุปคะแนนรวม
```

### เกณฑ์การให้คะแนนแต่ละเมนู (เต็ม 100 คะแนน / ผ่านเกณฑ์ที่ 98 คะแนน):
1. **Thumb Reachability (10 คะแนน):** ทุกปุ่มสำคัญอยู่ในระยะนิ้วโป้งเอื้อมถึงในมือเดียว
2. **Visual Hierarchy & Spacing (10 คะแนน):** ช่องไฟสมดุล ฟอนต์ชัด คอนทราสต์สูง ไม่เบียดแน่น
3. **Motion & Feedback (10 คะแนน):** แตะแล้วมีการหดขยาย (`active:scale-[0.98]`) และ Haptic ตอบรับ
4. **Loading & Skeleton States (10 คะแนน):** ไม่มีหน้าจอขาว มี Skeleton หรือ Progress Bar นุ่มนวล
5. **Error & Offline Handling (10 คะแนน):** เน็ตหลุดหรือเซิร์ฟเวอร์ช้า มีข้อความภาษาไทยเข้าใจง่าย
6. **Zero Accidental Actions (10 คะแนน):** มีปุ่มกดยกเลิก (Undo) หรือ Confirm สำหรับการกระทำสำคัญ
7. **Apple HIG / PWA Parity (10 คะแนน):** Safe Areas ครบถ้วน ไม่ชน Dynamic Island หรือ Home Bar
8. **Copy & Text Polish (10 คะแนน):** ภาษาไทยสละสลวย กระชับ ปุ่มเป็นคำกริยาไม่มีสัญลักษณ์นำ
9. **Performance & Light Footprint (10 คะแนน):** โหลดเร็ว ไม่กระตุก ไม่ส่ง Payload หนักเกินจำเป็น
10. **Native Joy Factor (10 คะแนน):** ความรู้สึกตอนใช้งานเหมือนแอปจริงที่ดาวน์โหลดจาก App Store

---

## 🛑 เงื่อนไขการหยุดวนลูป (Completion Criteria)
การวนลูปจะสิ้นสุดลงได้ก็ต่อเมื่อ:
1. ทุกสถานี (สถานีที่ 1 ถึง 6) ผ่านการตรวจและได้คะแนน **>= 98/100 (9.8/10)** ทุกสถานี
2. ผ่านการรันเทส `npm test` ใน frontend และ `pytest` ใน backend ครบ 100% ปราศจาก Error
3. ทำการอัปเดตบันทึกรอบงานลงใน `TODO.md` และสรุปย้ายรอบสมบูรณ์เข้า `HISTORY.md` โดยระบุ `ดำเนินการโดย: <Agent> (<Model>)` ตามกฎ Rule 4.14

**เริ่มดำเนินการวนลูปรอบที่ 1 ได้ทันที!**
```
