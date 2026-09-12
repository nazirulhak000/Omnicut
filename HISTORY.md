# 📜 OmniCut Pro Studio — History งานที่ทำเสร็จแล้ว

คลังประวัติรอบงานที่ปิดแล้ว **ห้ามแก้ย้อนหลัง** — เป็นบันทึกว่าตอนนั้นทำอะไร วัดได้เท่าไหร่ เจออะไร

- งานที่ยังไม่เสร็จอยู่ที่ [TODO.md](file:///d:/Winona/Programmer/Capcut/TODO.md)
- กติกา: [.agents/rules/work_loop.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/work_loop.md)
- รอบไหนปิด ให้ **ย้ายบล็อกเต็มมาที่นี่** แล้วเหลือบรรทัดเดียวใน `TODO.md` — กัน `TODO.md` บวมจนหาของไม่เจอ

## สารบัญ

| รอบ | งาน | วันที่ | ผลลัพธ์ |
| Round ANALYTICS-CHARTS-POLISH-1 | ปรับขนาดและจัดระเบียบเลย์เอาท์กราฟใน Analytics Hub ให้กระชับ สวยงาม พอดีสายตา ไม่ใหญ่เกินจำเป็น | 2026-09-12 | กราฟเส้น 800x130 widescreen, โดนัท top 4 + อื่นๆ พร้อม label ไม่หาย, TokenDashboard models/tasks จัดแบบ side-by-side; frontend 151 passed, build 3.25s, browser verified |
| Round USER-GUIDE-4 | คู่มือ interactive 6 ฟีเจอร์ (sticky TOC, เช็กลิสต์ติ๊กได้, accordion, ปุ่มลัด, FAQ ค้นหา) | 2026-09-12 | ไม่เปลี่ยนข้อความ/สี/ลำดับ; frontend 151 passed, build 4.22s |
| Round ANALYTICS-CHARTS-1 | พัฒนาระบบกราฟเส้น กราฟโดนัท Funnel Chart และเกจวัดแบบ Pure SVG สไตล์ Dark Modern Glassmorphism สำหรับแดชบอร์ดทั้ง 4 แท็บ | 2026-09-12 | สร้าง 4 Pure SVG charts (AreaLine, Donut, Funnel, ProgressRing/Concentric) ฝังครบ 4 แท็บ; vitest 151 passed, backend 4 passed, build 3.44s, browser verified |

## Round ANALYTICS-CHARTS-POLISH-1 — ปรับขนาดและจัดระเบียบเลย์เอาท์กราฟใน Analytics Hub ให้กระชับ สวยงาม พอดีสายตา ไม่ใหญ่เกินจำเป็น

วันที่: 2026-09-12 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**ปัญหา:**
1. **กราฟเส้น Daily Token Volume ใหญ่เกินความจำเป็น:** viewBox แคบทำให้บนจอกว้างกราฟยืดสูงเกือบ 400px กลายเป็นคลื่นยักษ์ที่มีพื้นที่โล่งสีดำว่างเปล่า และตัวเลขแกน X ด้านล่างถูกตัดขอบ
2. **กราฟโดนัท Content Angles พังเมื่อมีหลายมุม:** มี 20+ มุมมอง ทำให้สร้างชิ้นพายซอยย่อย 20 ชิ้น และ legend เรียงเดี่ยวยาวเฟื้อยลงมาเป็น 700px ดันโดนัทจมลงไปข้างล่าง แถมชื่อมุมมองไม่แสดง (แสดงแค่จุดและเลข 9 (20%), 1 (2%)) เพราะบั๊ก `slice.name` vs `slice.label`
3. **การ์ด Models & Tasks ใน TokenDashboard สูงเกินไป:** โดนัทถูกวางไว้ตรงกลางข้างบนแล้ว progress bar อยู่ข้างล่าง ทำให้การ์ดยืดสูงและมีพื้นที่ว่างมากเกินไป

**เป้าหมาย:**
1. แก้ `DonutChart.jsx`: แก้บั๊ก `slice.label || slice.name` + เพิ่มฟีเจอร์จำกัด `maxSlices` (รวมชิ้นที่เกินเป็น 'อื่นๆ' อัตโนมัติ ป้องกันชิ้นพายฝอย) + ปรับขนาด default ให้กะทัดรัด (130-140px)
2. แก้ `AreaLineChart.jsx`: ปรับ viewBox เป็น Widescreen (800x130) สัดส่วนกระชับ ป้องกันการยืดสูงบนจอกว้าง + ปรับ padding ล่างไม่ให้ตัวเลขตัดขอบ
3. แก้ `ProductionAnalyticsTab.jsx`: Content Angles จำกัด Top 4 + อื่นๆ จัดวางโดนัทคู่กับรายการอย่างกะทัดรัด ความสูงบาลานซ์กับตารางข้างๆ
4. แก้ `TokenDashboard.jsx`: จัดวางโดนัทไว้ด้านซ้าย (ขนาด 125px) และรายการบาร์อยู่ด้านขวา ลดความสูงการ์ดลง 50% พอดีสายตา + Daily Volume ปรับเป็นความสูงกระชับ (130px)
5. ปรับ `StorageAnalyticsTab.jsx` และ `InventoryAnalyticsTab.jsx` ให้ขนาดชาร์ตและสัดส่วนพอดีกันทั้งระบบ

### Todo

- [x] แก้ `frontend/src/components/analytics/charts/DonutChart.jsx` (แก้ label name, maxSlices grouping, compact sizing)
- [x] แก้ `frontend/src/components/analytics/charts/AreaLineChart.jsx` (widescreen viewBox 800x130, fix cut-off labels)
- [x] แก้ `frontend/src/components/analytics/tabs/ProductionAnalyticsTab.jsx` (Top 4 + อื่นๆ, compact layout)
- [x] แก้ `frontend/src/components/TokenDashboard.jsx` (จัดวาง side-by-side ในการ์ด Models & Tasks, Daily Chart 130px)
- [x] ปรับความกระชับใน `StorageAnalyticsTab.jsx` และ `InventoryAnalyticsTab.jsx`
- [x] รันการทดสอบ Vitest, Pytest, Build และตรวจสอบความสวยงามผ่าน Browser Subagent

### Gate

- [x] กราฟทุกตัวมีขนาดพอดีสายตา ไม่ยืดใหญ่เทอะทะ
- [x] Content Angles แสดงชื่อมุมมองถูกต้อง และชิ้นพายจำกัดไม่เกิน 5 ชิ้น (Top 4 + อื่นๆ) ไม่ยืดยาว
- [x] TokenDashboard Models & Tasks จัดวางแบบ Side-by-Side กระชับพอดี
- [x] Frontend Vitest 151 passed, Backend Pytest 4 passed, Build ผ่าน 100%

### Notes

- ปรับ `DonutChart.jsx` แก้บั๊กชื่อหายด้วย `slice.label || slice.name` และเพิ่ม automatic slice grouping ด้วย `maxSlices = 5` (รวมมุมมองที่เกินเป็น 'อื่นๆ' สี Slate)
- ปรับ `AreaLineChart.jsx` เป็น panoramic widescreen 800x130, ปรับ padding ล่าง 28px ทำให้ตัวเลขวันที่ 09-07 ถึง 09-11 แสดงชัดเจน ไม่ถูกตัดขอบ
- ปรับ `TokenDashboard.jsx` นำ Donut Chart (ขนาด 125px) วางชิดซ้ายคู่กับ Progress Bars ฝั่งขวา ลดความสูงการ์ดลง 45% กะทัดรัดระดับ Pro Dashboard
- ปรับ `ProductionAnalyticsTab.jsx` จัดวาง Donut Content Angles ขนาด 130px พร้อมรายการ 5 หมวดบน-ล่างให้กระชับ สมดุลกับตาราง Recent Productions ข้างเคียง
- ผลทดสอบ: Vitest 151 tests passed, Vite build ผ่านใน 3.25s, Pytest analytics hub 4 passed, ภาพบันทึก browser subagent ยืนยันความสวยงามลงตัว

## Round ANALYTICS-CHARTS-1 — พัฒนาระบบกราฟเส้น กราฟโดนัท Funnel Chart และเกจวัดแบบ Pure SVG สไตล์ Dark Modern Glassmorphism สำหรับแดชบอร์ดทั้ง 4 แท็บ

วันที่: 2026-09-12 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:**
ยกระดับศูนย์วิเคราะห์ข้อมูลและสถิติรวม (Analytics & Operations Hub) ให้แสดงผลด้วยแผนภาพและกราฟอันสวยงาม มีมิติ ไม่เป็นตัวเลขหรือกล่องสี่เหลี่ยมธรรมดา:
1. `AreaLineChart.jsx`: กราฟเส้นโค้ง Bezier + Gradient Glow + Interactive Hover Tooltip สำหรับ Daily Token Volume
2. `DonutChart.jsx`: กราฟวงแหวนโดนัทหลายมิติ พร้อมไฮไลต์ชิ้นพายและตัวเลขตรงกลาง สำหรับ Content Angles, AI Models, Tasks, Storage Folders, และ Inventory Readiness
3. `FunnelPipelineChart.jsx`: แผนภาพกรวยการผลิต 4 เฟสเชื่อมโยงด้วยแสงนีออน พร้อมอัตรา Conversion Rate และ Drop-off
4. `ProgressRing.jsx`: เกจวัดวงแหวนนีออนเดี่ยว และ Triple Concentric Rings (3 ชั้น) สำหรับความสมบูรณ์ของคลังสื่อ

### Todo

- [x] สร้าง `frontend/src/components/analytics/charts/AreaLineChart.jsx`
- [x] สร้าง `frontend/src/components/analytics/charts/DonutChart.jsx`
- [x] สร้าง `frontend/src/components/analytics/charts/FunnelPipelineChart.jsx`
- [x] สร้าง `frontend/src/components/analytics/charts/ProgressRing.jsx`
- [x] อัปเกรด `frontend/src/components/analytics/tabs/ProductionAnalyticsTab.jsx` ฝัง FunnelPipelineChart และ DonutChart
- [x] อัปเกรด `frontend/src/components/TokenDashboard.jsx` ฝัง AreaLineChart และ DonutCharts
- [x] อัปเกรด `frontend/src/components/analytics/tabs/StorageAnalyticsTab.jsx` ฝัง DonutChart และ ProgressRing
- [x] อัปเกรด `frontend/src/components/analytics/tabs/InventoryAnalyticsTab.jsx` ฝัง DonutChart และ Concentric Rings
- [x] ตรวจสอบตามกฎ UI Clean Standard
- [x] รันการทดสอบ Unit Tests และ Build

### Gate

- [x] ทุกชาร์ตเป็น Pure SVG + CSS Render คมชัด ลื่นไหล ไม่พึ่งพา Library ภายนอก (React 19 Zero-conflict)
- [x] แสดงผลสวยงามสไตล์ Dark Modern Glassmorphism มีเอฟเฟกต์ Glow และ Tooltip ตอบสนองฉับไว
- [x] Frontend Vitest (151/151 passed) และ Vite Build สำเร็จ 100% ใน 3.44s
- [x] Backend Pytest (4/4 tests passed) สำเร็จ 100%
- [x] Browser verification ผ่านฉลุยทั้ง 4 แท็บบนเบราว์เซอร์จริง

### Notes

- พัฒนา 4 คอมโพเนนต์กราฟและเกจวัด Pure SVG ระดับพรีเมียมใน `frontend/src/components/analytics/charts/`
- ฝังลงใน 4 แท็บของ Analytics & Operations Hub ครบถ้วนทุกมิติ
- ตรวจสอบผ่าน Browser Subagent บน `https://localhost:5173/` ยืนยันการแสดงผลคมชัด ไม่มี JavaScript runtime errors และสอดคล้องตามมาตรฐาน UI Clean Standard 100%

## Round DELETED-TIMELINE-SYNC-1 — ซิงค์สถานะโปรเจกต์ที่ถูกลบออกจาก NewClipPanel, ล็อกปุ่มแผนถ่ายเมื่อถูกล็อก, และนำปุ่มย้อนสถานะออก

วันที่: 2026-09-11 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:**
1. **นำปุ่ม "ย้อนสถานะ" ออกทั้งหมด (Unified UI Standard):** ถอดปุ่มย้อนสถานะออกจากทั้ง Locked Notice Banner และ Action Bar ใน `ProductToClip.jsx` เพื่อให้สถานะของมุมเป็นไปตามโฟลว์จริงของระบบ (เมื่อลบโปรเจกต์ไทม์ไลน์ สถานะจะ Reconcile กลับเป็น scripted ให้ตัดใหม่ได้อัตโนมัติ)
2. **ล็อกปุ่ม "แผนถ่าย" เมื่อมุมถูกล็อก (`isLocked`):** ล็อกและซ่อนปุ่ม "แผนถ่าย" ร่วมกับปุ่ม "รีสคริปต์ด้วย AI" และ "แก้ไขสคริปต์" ทั้งใน `AngleActiveWorkbench` และ `ScriptAccordionItem` เมื่อมุมมีสถานะ `โพสต์แล้ว` หรือ `กำลังตัดต่อ`
3. **แก้ไขข้อความเตือนโปรเจกต์ค้างใน `NewClipPanel.jsx`:** เพิ่มการตรวจเช็ค `angleSpecificProject` กับรายชื่อโปรเจกต์จริงใน `existingProjects` ถ้าโปรเจกต์ถูกลบไปแล้ว จะไม่ดึงชื่อเดิมที่ค้างอยู่ใน metadata มาแสดง ทำให้กล่องเตือนสีเหลืองหายไปทันที และใน `EditorShell.jsx` เมื่อกดยืนยันลบโปรเจกต์สำเร็จ ให้เรียกอัปเดต state สินค้าล่าสุดกลับมายัง `App.jsx` ทันที

### Todo
- [x] ใน `ProductToClip.jsx`: ลบปุ่ม "ย้อนสถานะเพื่อตัด/แก้ไขใหม่" ออกจาก Locked Notice Banner และ Action Bar
- [x] ใน `ProductToClip.jsx`: ซ่อน/ปิดปุ่ม "แผนถ่าย" เมื่อ `isLocked` (แสดงเฉพาะเมื่อ `!isLocked`)
- [x] ใน `NewClipPanel.jsx`: ปรับการคำนวณ `angleSpecificProject` ให้ตรวจเช็คว่าโปรเจกต์มีอยู่จริงใน `existingProjects`
- [x] ใน `EditorShell.jsx`: เมื่อ `confirmDelete` สำเร็จ ดึงข้อมูลสินค้าล่าสุดและส่ง `onProductContextChange` กลับไปยัง `App.jsx`
- [x] รันการทดสอบและ build ผ่านสมบูรณ์

### Gate
- [x] ไม่มีปุ่มย้อนสถานะแปลกปลอมใน ProductToClip
- [x] ปุ่มแผนถ่ายไม่สามารถกดได้เมื่อมุมอยู่ในสถานะโพสต์แล้วหรือกำลังตัดต่อ
- [x] เมื่อลบโปรเจกต์แล้ว หน้า NewClipPanel ไม่แสดงกล่องเตือนสีเหลืองว่ามีโปรเจกต์ค้างอยู่
- [x] Vitest pass (151 tests) & vite build pass

---

## Round SHOT-LIST-ENHANCE-2 — ปรับคำแนะนำมุมกล้องและการถ่ายทำในแผนถ่ายให้เจาะลึกเฉพาะซีนตามบทพูดจริง (Semantic Action Guidance)

วันที่: 2026-09-11 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** 
1. **Semantic Script Analysis:** ปรับ `camera_direction_for_beat()` ให้แยกแยะการกระทำตามคำสำคัญ (Keywords) ในแต่ละประโยคบทพูดจริง เช่น คลิก/ปุ่ม/เงียบ/ลื่นไหล, ปวดเมื่อย/สุขภาพ/องศา/สรีระ, ราคา/คุ้ม/วันละ, บลูทูธ/สลับเครื่อง/ถ่าน ไม่ให้ขึ้นคำแนะนำซ้ำซากจำเจ
2. **Auto Product Name & Model Detection:** หาก `category` ว่างเปล่า ให้นำ `product_name` มาวิเคราะห์หมวดสินค้าอัตโนมัติ (เช่น Logitech Lift -> Desk Tech / Ergonomic Mouse ทันที)
3. **Multi-scene Differentiation:** แต่ละซีนของ Feature Beats ต้องมีคำแนะนำแอคชั่นการถือ/จับ/หมุน/กด/วางที่ไม่ซ้ำกัน ทำให้คนถ่ายรู้ว่าในแต่ละวินาทีต้องทำท่าทางอะไรกับสินค้า

### สิ่งที่ทำ

1. ปรับปรุง `camera_direction_for_beat()` ใน [scripts/shot_list_builder.py](file:///d:/Winona/Programmer/Capcut/scripts/shot_list_builder.py) ให้รวม `product_name` เข้ากับการตรวจจับหมวดหมู่ (เช่น เจอ mouse, lift, keyboard, cable, beauty)
2. เพิ่มระบบ Semantic Context วิเคราะห์ประโยคบทพูดและคำบนหน้าจอ:
   - เสียงคลิก/ปุ่ม/SmartWheel: แนะนำใช้นิ้วกดคลิกและหมุน SmartWheel ให้เห็นความนุ่มลื่นเงียบกริบ
   - สุขภาพ/ปวดเมื่อย/ข้อมือ/สรีระ/องศา: แนะนำทาบมือลงบนเมาส์ ยกให้เห็นมุมเอียง 57° ที่กระชับพอดีฝ่ามือ ไม่เกร็งข้อมือ
   - ความคุ้มค่า/ราคา/วันละ/ลงทุน: แนะนำยกเมาส์ขึ้นมาถือหรือหมุนช้าๆ 360° โชว์ความพรีเมียมและวัสดุ
   - บลูทูธ/ไร้สาย/สวิตช์: แนะนำพลิกด้านใต้เมาส์ให้เห็นสวิตช์เปิด-ปิด หรือปุ่มสลับเครื่อง Easy-Switch
3. เพิ่มการสลับ Default actions กรณีไม่มีคำเจาะจง เพื่อไม่ให้ช็อตที่ติดกันแสดงข้อความซ้ำกัน
4. เพิ่มชุดทดสอบใน `tests/test_shot_list_enhancements.py` ครอบคลุมเคสสคริปต์จริงของ Logitech Lift ผ่านครบ 100%

### Gate

- [x] Backend test สำหรับ semantic camera directions ผ่านครบ (`tests/test_shot_list_enhancements.py`, 5 passed)
- [x] `npm test -- --run` ใน frontend ผ่านครบ 100% (151 tests passed)

---

## Round SHOT-LIST-ENHANCE-1 — ยกระดับโฟลว์แผนถ่าย (Shot List Enhancement - Phase 1)

วันที่: 2026-09-11 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** 
1. **Invalidate & Detect Stale Shot List:** เมื่อสคริปต์ (`script_lines`) มีการแก้ไข (ผ่าน hand-edit หรือ AI reroll) ให้ระบบตรวจจับได้ และลบ/แจ้งเตือนว่าแผนถ่ายเก่าหมดอายุ (Stale) ต้องกดสร้างใหม่เพื่อไม่ให้เวลาและบทพูดเพี้ยน
2. **Shot List Navigation ใน ContentTrackerHub:** เพิ่มปุ่ม "แผนถ่าย" ในหน้า Content Tracker Hub (ทั้งในแถบ Action ของ `InspectAngleModal` และปุ่มด่วน) พร้อมเปิด `ShotListModal` ดูคำแนะนำ/สแกน QR ได้ทันที
3. **Smart Framing by Category:** ปรับคำแนะนำกล้องใน `shot_list_builder.py` ให้ฉลาดขึ้นตามหมวดสินค้า (`category`) เช่น IT/เมาส์คีย์บอร์ด แนะนำ Top-down/45°, แฟชั่น แนะนำ Close-up Texture
4. **Resilient UX:** ปรับปรุง State ให้มั่นคง ไม่หมุนค้าง และมี fallback error ชัดเจน

### สิ่งที่ทำ

1. **Backend / Data Store:**
   - เพิ่มเมธอด `ShotListsStore.delete(product_id, angle_id)` และ `ShotListsStore.is_stale(product_id, angle_id, current_script)` ใน `scripts/shot_lists_store.py`
   - ปรับ `ProductStore.replace_angle_content` และ `ProductStore.update` เมื่อสคริปต์เปลี่ยน ให้ลบ Shot List เดิมของมุมนั้นโดยอัตโนมัติ เพื่อป้องกันเวลาเสียงพากย์คลาดเคลื่อน
   - ปรับ `GET /api/products/{id}/angles/{id}/shot-list` ให้คืนค่า `is_stale: true/false` หากพบว่าสคริปต์ปัจจุบันไม่ตรงกับที่แคชไว้
2. **Smart Category Framing (`scripts/shot_list_builder.py`):**
   - ปรับ `camera_direction_for_beat()` และ `build_shot_list()` ให้รองรับ `category`
   - แนะนำมุมตั้งกล้องเฉพาะหมวด:
     - Desk Tech (เมาส์/คีย์บอร์ด): แนะนำมุมเฉียง 45° หรือ Top-Down ส่องบนโต๊ะทำงาน
     - Cables/Chargers: แนะนำมุม Close-up โชว์การม้วนเก็บ สายถัก และความทนทาน
     - Beauty/Skincare: แนะนำมุมสว่าง Medium Close-up ถือใกล้ใบหน้าและโชว์เนื้อสัมผัส
3. **Frontend Integration:**
   - ปรับ `frontend/src/components/ShotListModal.jsx` เพิ่มแถบเตือนสีแดงกะพริบแจ้งเตือนเมื่อ `result.is_stale === true` พร้อมปุ่ม "อัปเดตแผนถ่าย" 1-คลิก
   - ปรับ `frontend/src/components/ContentTrackerHub.jsx` เชื่อมต่อ `ShotListModal` เต็มรูปแบบ:
     - เพิ่มปุ่ม "แผนถ่าย" ในแถบ Action ของ `InspectAngleModal`
     - รองรับการสร้าง/เปิดดูแผนถ่ายและการสแกน QR Code ถ่ายทำผ่านมือถือจากหน้า Content Tracker Hub ได้โดยตรง
4. **Testing & Verification:**
   - เพิ่มชุดทดสอบ `tests/test_shot_list_enhancements.py` ทดสอบ CRUD, Stale detection และ Category framing ผ่านครบ 4/4 tests
   - Frontend test ผ่าน 151/151 tests, `npm run build` สำเร็จเรียบร้อย

### Gate

- [x] Backend test สำหรับ `ShotListsStore.delete`, `is_stale` และ `camera_direction_for_beat` ผ่านครบ (`tests/test_shot_list_enhancements.py`, 4 passed)
- [x] `npm test -- --run` ใน frontend ผ่านครบ 100% (151 tests passed)
- [x] `npm run build` ใน frontend ผ่านไร้ error (1,984 modules transformed)

---

## Round PERSIST-LAYOUT-FIX-1 — Product Selection Persistence & Toolbar Alignment Fix

วันที่: 2026-09-11 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** 
1. แก้ปัญหารีเฟรชแล้วไม่จำสินค้าที่เลือก (เลือก Logitech Lift แต่พอนึกรีเฟรชกลับเด้งไปสินค้าตัวแรก): เพิ่ม local storage fallback และ sync active product context ทั้งสองทาง
2. จำสคริปต์/มุมขายที่เปิดค้างไว้ (`openAngleIdx`): บันทึกและ restore ทั้งระดับ product (`capcut_active_angle_idx_${id}`) และ global เมื่อรีเฟรชหน้า ไม่เด้งกลับไปมุม 0
3. คลีน Header ใน `ProductToClip.jsx`: ตัดป้าย "ราคาพิเศษในตะกร้า" และป้าย ID ที่รกออก เพื่อให้หัวเรื่องสินค้าเด่นชัดบรรทัดเดียว
4. ย้าย TikTok Product ID (`tiktok_product_id`) เข้าไปแก้ไขและจัดการในหน้าต่าง "ข้อมูล AI" ([ProductMetadataModal.jsx](file:///d:/Winona/Programmer/Capcut/frontend/src/components/ProductMetadataModal.jsx)) ไม่กินพื้นที่แถบหัวบน
5. ขยายขนาดชื่อสินค้าและปรับ Typography ให้คมชัด ใหญ่ ชัดเจน ในบรรทัดเดียว (`titleClassName` ใน `PageHeader.jsx`)
6. จัดการ Layout Toolbar ใน `ProductToClip.jsx` แถว 2 ที่ปุ่มแอ็กชัน wrap ตกบรรทัดลงมาไม่สวยงามบนจอมือถือ (430px) ให้เรียงเป็น 1 แถวอย่างเป็นระเบียบ (scrollable flex-nowrap) ไม่แตกแถว
7. ตรวจสอบและปรับปรุง Modal action buttons ใน `ContentTrackerHub.jsx` (InspectAngleModal) ให้จัดเรียงแบบ grid สมมาตร 2 คอลัมน์บนมือถือ ไม่ wrap กระจัดกระจาย

### Gate

- `npm test -- --run` ใน frontend ผ่านครบ (151 passed)
- `npm run build` ใน frontend ผ่านไร้ error (built in 3.23s)

---

## Round RESPONSIVE-LAYOUT-1 — ปรับแต่ง Responsive Layout (1440×900 vs 430×932)

วันที่: 2026-09-11 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** ปรับแต่ง Responsive Layout ทั้งหมดใน `frontend/src` รองรับ 2 ขนาดเป้าหมาย: Desktop 1440×900 (baseline Tailwind lg/xl) และ Mobile 430×932 (iPhone 15 Pro Max portrait Tailwind base/no-prefix) โดยใช้เฉพาะ default Tailwind breakpoints, ขจัด overflow, ขยาย touch target $\ge 44\text{px}$, และจัดระเบียบปุ่ม/modal ไม่ให้ตกขอบ

### สิ่งที่ทำ

1. **Phase 1: Shared Shell & Global Drawers**
   - `Sidebar.jsx`: ปรับ Touch Target ของแถบ Bottom Tab Bar มือถือเป็น `min-h-[48px]`, `py-1 px-2` พร้อม active:scale-95
   - `Topbar.jsx`: จัด layout ชื่อหน้าและปุ่ม header ด้วย `min-w-0 flex-1 mr-2` ยุบข้อความยาวคงเหลือไอคอน touch target $\ge 36\text{px}$ ป้องกัน header truncation บนจอ 430px
   - `ActivityCenter.jsx`: ปรับ Slide-over Drawer เป็น `w-full max-w-full sm:max-w-md` และปรับ Filter Tabs 3 ปุ่มไม่ให้ตกบรรทัดหรือล้นขอบจอ
2. **Phase 2: Core Creation & Editing Flow**
   - `ProductToClip.jsx`: ปรับ Action Tools Group ไม่ให้ตัดตกบรรทัด
   - `ContentTrackerHub.jsx`: ปรับปุ่ม Action ใน `InspectAngleModal` บนมือถือให้ wrap 2 คอลัมน์ได้พอดี
   - `TrimAdjustModal.jsx`: ขยายจุดจับดึงตัดหัวท้ายคลิป (Start/End trim drag handles) ด้วย touch hitbox พิเศษ (`before:-inset-x-2.5`) ให้นิ้วแตะลากได้แม่นยำ
3. **Phase 3: Support Hubs & Modals**
   - `ExportGallery.jsx`: ขยาย Touch Target แถบฟิลเตอร์สถานะคลิปเป็น `min-h-[36px]` พร้อม `touch-pan-x` และปรับแถบ Floating Batch Action Bar ให้ลอยขึ้น (`bottom-20 sm:bottom-6`) ไม่บัง Bottom Tab Bar ของมือถือ
   - `MediaAssetsHub.jsx`: ขยายปุ่ม Play/Pause ของ SFX และ BGM เป็น `w-11 h-11` ($\ge 44\text{px}$) แตะง่ายไม่วืด
   - `TokenDashboard.jsx`: เพิ่ม `touch-pan-x` และ `min-w-[700px]` ให้ตาราง Ledger สถิติเลื่อนด้วยนิ้วบนจอ 430px ได้นุ่มนวล
4. **Phase 4: Verification & Gate**
   - `npm test -- --run` ผ่านครบ 150/150 tests
   - `npm run build` ผ่านสมบูรณ์ (Vite production bundle สำเร็จใน 3.43s)
   - `pytest tests/test_preview_render_parity.py` ผ่านครบ 153/153 tests

### Gate

- [x] ทุกหน้าแสดงผลถูกต้อง ไม่พังทั้ง 1440x900 และ 430x932
- [x] ไม่มี touch target หลักที่ผู้ใช้ต้องแตะ < 44px บน mobile
- [x] ไม่มี horizontal overflow หรือ scrollbar แนวนอนหลุดบน body
- [x] `npm run build` (3.43s) และ `npm test` (150 passed), pytest parity (153 passed) ผ่านครบถ้วน

---

## Round PRODUCT-METADATA-8 — อ่าน metadata จากรูปแบบเบื้องหลัง

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** ผู้ใช้เริ่มอ่านข้อมูลจากรูปอ้างอิงแล้วปิดโมดัลหรือเปลี่ยนหน้าได้ งานต้องทำต่อใน background ผ่าน TaskManager, มี progress/notification แบบงานอื่น และเมื่อเสร็จสามารถเปิดผล preview เดิมกลับมาตรวจ/เลือก field/บันทึกได้ โดยไม่บันทึกทับอัตโนมัติ

### สิ่งที่ทำ

1. แยก logic อ่านรูปเป็น helper และเพิ่ม `preview-image-metadata-async` ที่สร้าง persistent `image_metadata` task ผ่าน `TaskManager`; worker เก็บผล preview ไว้ใน task result และไม่เขียน product อัตโนมัติ
2. เปลี่ยนปุ่มอ่านรูปใน ProductToClip ให้ enqueue งานแล้วปิดโมดัลได้ทันที พร้อมบอกให้ติดตามจาก Activity Center
3. เพิ่มไอคอน/ปุ่ม `ตรวจผลอ่านรูป` ใน Activity Center และ Global Task Notification; เมื่อตรวจผล ระบบเลือกสินค้าเดิม เปิด Metadata Inspector และคืน preview เพื่อเลือก field/แก้ไข/ยืนยันบันทึกตาม flow เดิม
4. คง synchronous endpoint เดิมไว้เพื่อ compatibility กับ caller เก่า
5. เพิ่ม backend async lifecycle regression และ route contract coverage

### Gate

- [x] focused image metadata tests + route contract — 22 passed, 1 warning
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 1,055 passed, 24 warnings, 0 failed (ใช้เวลา 130.44 วินาที)
- [x] `Set-Location frontend; npm test` — 149 passed
- [x] `npm run lint` — 0 errors; warnings เดิมของโปรเจกต์
- [x] `npm run build` — ผ่าน, Vite transformed 1,981 modules
- [x] `git diff --check` — ผ่าน
- [x] Impeccable detector — พบ 1 warning เดิม `gray-on-color` ที่ ActivityCenter.jsx บรรทัด 292; ไม่ใช่โค้ดที่เพิ่มในรอบนี้

### Notes

- ผล Vision ยังเป็น read-only preview ใน task registry จนกว่าผู้ใช้จะกดตรวจ เลือก field และยืนยัน จึงไม่เสี่ยงทับ metadata เดิมระหว่างทำงานเบื้องหลัง
- การทดสอบ full suite รอบแรกหมดเวลา 124 วินาทีเพราะ gate เดิมใช้เวลาประมาณ 130 วินาที; รันซ้ำด้วย timeout สูงขึ้นและผ่านครบ
- ยังเหลือ manual live verification กับรูป BlueWow/โควตา Gemini ตามงาน PRODUCT-METADATA-7 เดิม

## Round COMMIT-SPLIT-1 — จัดกลุ่ม commit working tree ค้าง + LIVE_VALIDATION_CHECKLIST

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** จัดการงานค้างใน working tree ข้าม 2 workstream (product metadata PM-4/5/6 และ post/export lifecycle) ให้เป็นระเบียบ และรวม live gate ที่รอ user ทั้งหมดเป็น checklist เดียว

### สิ่งที่ทำ

1. ตรวจ `git status` + diff รายไฟล์ จำแนก 17+ ไฟล์แก้ค้างเข้า 5 workstream
2. รัน deterministic gates ทั้งหมดก่อน commit
3. Commit แยก 5 กลุ่ม:
   - `7ed1fbb` feat(products): metadata edit/dedupe preview, raw-text boundary, stable selection (PM-4/5/6) — ProductMetadataModal, ProductToClip, productSelection.js+test, api_products, product_scraper, test_product_metadata, api.js
   - `b3ca2f7` fix(exports/videos): move-retry on Windows file lock, registry-before-store mark-posted order — api_videos, api_exports, test_post_lifecycle, test_backend_api_contracts
   - `9ce784f` fix(editor): cover gate simplification and no-video-source preview state — CoverStudioModal, EditorShell, schedule_queue.json
   - `31086f3` chore(ui): raw vault polish and tracker card cleanup — ContentTrackerHub, RawVaultPanel, custom_hook_templates.json
   - `c7626bb` docs: live validation checklist and round bookkeeping — TODO/HISTORY/PRO_EDITOR_STYLE_PLAN + LIVE_VALIDATION_CHECKLIST.md
4. สร้าง `LIVE_VALIDATION_CHECKLIST.md` รวม live gate ที่รอ user: PM-3/4/5/6 (กลุ่ม A), POST-1 + POST-3.20 (กลุ่ม B), POST-3.16–3.18 (กลุ่ม C) + optional (full render loop, SUB-THAI-2)

### Gate

- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 1,050 passed, 2 failed (pre-existing ที่ HEAD: `test_per_word_vs_monolithic_render_parity` 284px divergence และ `test_ibm_thai_marks_have_separate_vertical_bands` — ทดลองรันซ้ำ 2 failed คงเดิม deterministic, ไฟล์ subtitle ไม่ได้อยู่ใน working diff จึงไม่เกี่ยวกับงานที่ commit)
- [x] `npm test` — 149 passed / `npm run build` — ผ่าน / `npm run lint` — 0 errors (390 warnings เดิม)
- [x] `git diff --check` — ผ่าน
- [x] commits ครบทุกไฟล์ที่แก้ เหลือเพียง untracked `header-toggle-test-1.png` (ตั้งใจไม่ commit รอ user ตัดสินใจ)

### Notes

- ระหว่างรอบมี commit `27e8441` (metadata preview) และ `aa1f5b8` (security audit fixes) จาก agent อื่นเข้าก่อน — ทำให้ไฟล์ `frontend/src/api.js`, `tests/test_backend_api_contracts.py` โผล่ใน diff ทีหลัง ตรวจแล้วรวมในกลุ่มที่เกี่ยวข้องถูกต้อง
- 2 pytest failures ข้างบนเป็นบั๊ก subtitle render ที่มีอยู่แล้วใน HEAD — ควรเปิดรอบแยกแก้ (เกี่ยวกับ SUB-THAI-2 ที่พักไว้)

| Round POST-3.14 | Cover Studio portal entry, project-based cover naming, and LOG01 legacy project migration | 2026-09-07 | commit 2a1e395 -> frontend 63 tests pass -> build pass -> backend compile/tests pass |
| Round POST-3.15 | Prefer project-named covers in export metadata before the legacy product fallback | 2026-09-07 | focused backend tests 8 passed -> compileall passed |
| Round POST-3.19 | Restore generated cover visibility in the TikTok post modal after backend refresh | 2026-09-07 | User confirmed step 5 cover upload works; focused backend tests 14 passed; frontend tests 65 passed; build passed |
| Round POST-3.21 | Multi-day persistent TikTok publishing queue and Agenda/Extension handoff | 2026-09-07 | Schedule API/store, multi-day Agenda, single/bulk assignment, five-minute timezone-safe slots, guarded reschedule, extension queue handoff; pytest 873 passed, npm test 82 passed, build and browser smoke passed |
| Round POST-3.22 | Weekly schedule templates and product-rotating auto-fill | 2026-09-07 | Backend template persistence/preview/atomic commit; Agenda editor and overdue requeue; pytest 879 passed, npm test 83 passed, build passed |
| Round POST-3.23 | Reduce default publishing schedule to three slots | 2026-09-07 | Defaults 12:30, 19:00, 21:30; legacy five-slot templates migrate safely; pytest 891 passed, npm test 83 passed, build and compileall passed |
| Round POST-3.24 | Show saved-cover status in the daily queue | 2026-09-07 | Bright cover icon when a 3:4/9:16 cover exists, subdued icon when missing, Cover Studio action preserved; npm test 83 passed, build and live Agenda smoke passed |
| Round POST-3.25 | Redesign Extension UX/UI (Cyber-Studio Dark, IBM Plex Sans Thai, Studio Monitor & Stepper Pipeline) | 2026-09-07 | Embedded IBM Plex Sans Thai fonts; Studio Monitor card; 2-column affiliate grid; Stepper Pipeline with progress meter; zero emoji pollution; 12/12 extension tests pass; live browser verified |
| Round POST-3.26 | เพิ่มปุ่มเปิด/สลับแท็บ TikTok Studio ใน Extension (Tab 1, Tab 2, Header, Popup) | 2026-09-07 | Quick bar ใน Tab 1, Banner ใน Tab 2, Header button, Popup button; Auto-focus/activate tab; 13/13 tests pass; Clean UI standard |
| Round POST-3.27 | ลดความซ้ำซ้อนปุ่มเปิด TikTok Studio ให้เหลือจุดเดียวใน Header ตามที่ User ร้องขอ | 2026-09-07 | รวมเหลือจุดเดียวใน Header bar (`#headerOpenTikTokBtn`); ลบปุ่มซ้ำซ้อนใน Tab 1 และ Tab 2 ออกทั้งหมด; 13/13 tests pass; Clean UI standard |
| Round TLO-REFACTOR-1 | แยก abstraction ของ Overlay Timeline/Preview แบบรักษา behavior เดิม | 2026-09-09 | Phase 0–6 เสร็จ · frontend 100 tests · parity 150 tests · FFmpeg behavior 11 tests · build 1972 modules |
| Round TLO-REFACTOR-2 | ลด duplication ฝั่ง renderer เฉพาะจุดที่พิสูจน์ parity ได้ | 2026-09-09 | policy/config dispatch สำหรับ hook/text · frontend 102 tests · parity 150 tests · FFmpeg behavior 11 tests · build 1972 modules |
| Round TLO-REFACTOR-3 | แยก shared Timeline label-gutter primitive | 2026-09-09 | `TrackLabel.jsx` ใช้ร่วมกับ Timeline/EffectTrack · frontend 102 tests · lint/build/diff check ผ่าน |
| Round TLO-REFACTOR-4 | รองรับ optional trim handles ใน shared timeline shell | 2026-09-09 | Hook ใช้ shared shell แบบ right-trim only · frontend 104 tests · lint/build/diff check ผ่าน |
| Round TLO-REFACTOR-5 | ย้าย Caption chip เข้า shared timeline shell โดยคง magnetic-ripple policy | 2026-09-09 | Caption ใช้ shared shell แต่คง drag/ripple adapters เดิม · frontend 105 tests · lint/build/diff check ผ่าน |
| Round TLO-REFACTOR-6 | รวม shared Inspector header สำหรับ Sticker/Effect | 2026-09-09 | `OverlayInspectorHeader` รับ layout ร่วมและ media/config เฉพาะชนิด · frontend 107 tests · lint/build/diff check ผ่าน |
| Round TLO-REFACTOR-7 | รวม timeline pointer lifecycle โดยคง type-specific drag math | 2026-09-09 | `timelineDragLifecycle` ใช้ร่วมกับ Caption/Text/Hook/Sticker/Effect · frontend 109 tests · lint/build/diff check ผ่าน |
| Round RAW-1 | แก้ rename คลิปดิบที่ติด file lock และจัดเลย์เอาต์ Raw Vault แบบ responsive | 2026-09-07 | ถอด preview ก่อน rename, retry WinError 32 พร้อมข้อความกู้คืน, product groups แบบ responsive; pytest 896 passed, npm test 85 passed, build ผ่าน |
| Round HOK-1 | ระบบ Custom Hook Template Studio (สร้างและบันทึกแม่แบบฮุกด้วยตัวเอง) | 2026-09-07 | CRUD API + 02_Assets/Templates/custom_hook_templates.json + UI บันทึกสไตล์ใน Inspector + AssetPanel + Toolbar optgroup; pytest 2 passed, parity 149 passed, npm test 85 passed, build passed, live browser verified |
| Round EDT-1 | ตรวจสอบและปรับปรุง UX/UI หน้าตัดต่อ (Editor Friction & Speed Optimization) | 2026-09-07 | แก้ Safe Zone 420px overlay ถูกต้องตามสัดส่วน; เพิ่ม Quick Hook dropdown ใน Toolbar; เพิ่ม 1-Click Reset Zoom; ลดคลิกจาก 25 เหลือ 10; npm test 85 passed; build passed; live browser verified |
| Round BUG-4 | แก้ไขคลิปบวมสะสมทุกครั้งที่เรนเดอร์ (Transition Overlap Compounding Feedback Loop) | 2026-09-08 | แก้ video_assembly_stage + video_editor acc_dur + normalized 5 swollen projects + pytest 159 passed + parity 149 passed |
| Round POST-4 | ป้องกันการลบวิดีโอที่โพสต์แล้วใน Gallery, ล็อกไม่ให้เรนเดอร์ซ้ำในหน้าตัดต่อ และแก้ปัญหาย้อนสถานะ | 2026-09-08 | ProductStore rollback guard + Gallery disable delete + Editor lock render + tests passed 3/3 |
| Round POST-5 | ยกระดับความสมบูรณ์และเสถียรภาพของวงจรชีวิตคลิปที่โพสต์แล้ว (Full Posted Evidence & Lifecycle Integrity Lockdown) | 2026-09-08 | DB immunity against demoting/deleting posted angles + Editor delete modal locked + ProductToClip read-only + Drag&Drop guard + Mobile mark-posted file move + tests passed 7/7 |
| Round ACCENT-PRO-1 | เพิ่มสไตล์ตกแต่งป้ายฮุกให้หลากหลาย 11+ รูปแบบระดับโปร (Adaptive Framing, Hybrid Color, Motion Sync, 100% Parity) | 2026-09-08 | 12 styles catalogued + ASS vector drawing (\p1) + Canvas 2D mirror + accent_color picker + 149 parity pass + 147 smoke pass |
| Round PREV-2 | ซ่อมบั๊กพรีวิวดำและข้อความตกค้าง (Fix Infinite Seek Loop in renderAt & Unconditional Canvas Clear) | 2026-09-08 | นำ currentTime mutation ออกจาก renderAt + เคลียร์ canvas ต้นเฟรมใน tick() + วาด readyState >= 2 ทันที + 149 parity pass + 147 smoke pass + build pass |
| Round ACCENT-REV-1 | คืนค่าตัวเลือกตกแต่ง (Accent) กลับเป็น 3 ตัวเลือกดั้งเดิมตามคำสั่งผู้ใช้ | 2026-09-08 | คืนค่า underline, badge, none ตามคำสั่งผู้ใช้ · 149 parity passed · build passed · smoke tests passed |
| Round STK-1 | Interactive Sticker Timeline Track, Free Canvas Drag/Resize, and Parity Render Engine | 2026-09-08 | แทร็กสติกเกอร์บนไทม์ไลน์ + Drag & Resize อิสระบน Canvas + ลบ 6-pos grid + Parity 100% (between enable & normX, normY) · pytest 148 passed · parity 149 passed · build passed · live browser verified |
| Round STK-2 | Multi-Sticker Support, 3-Second Default Duration, and Smooth Canvas Resizing | 2026-09-08 | Default 3s + Linear vector projection smooth resize handles + Multi-stickers array & timeline auto-stacking sub-lanes + FFmpeg multi-overlay chaining + Parity 100% · pytest 149 passed · test_multi_stickers 2 passed · npm test 85 passed · build passed · live browser verified |
| Round STK-3 | Sticker Baseline 100% Size, Track Eye Toggle, Deletion, and Preview-Before-Add | 2026-09-08 | STICKER_BASE_WIDTH 160 + Eye toggle hides canvas + Delete key/Inspector + Preview then '+' add · pytest 299 passed · npm test 85 passed · build passed · live browser verified |
| Round SUB-THAI-1 | แก้สระและวรรณยุกต์ไทยซ้อนกันในคลิปเรนเดอร์ | 2026-09-08 | เปลี่ยน caption entrance จาก ASS `\\fscx/\\fscy` เป็น alpha fade 70ms และ mirror ใน Canvas; เพิ่ม FFmpeg multi-frame regression ด้วย `นั่งพิมพ์งานทั้งวัน`; pytest 926 passed · npm test 85 passed · build/compileall passed |
| Round STK-PRO-1 | ชุดสติกเกอร์และป้ายรีวิวสายไอทีระดับโปร (Photorealistic Tech Review Badges) | 2026-09-08 | ออกแบบ Master Prompt 3 ชุด + เจนและสไลซ์ 18 ป้ายไอทีระดับโปร (Dark Glass, CNC Aluminum, Titanium, Micro-LED) + สำรองของเดิมลง _backup_cartoon/ + อัปเดต AssetPanel · parity/behavior 159 passed · npm test 85 passed · build passed · 18 RGBA verified |

## Round TLO-REFACTOR-4 — รองรับ optional trim handles ใน shared timeline shell

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ผลลัพธ์:** ขยาย `TimelineIntervalItem` ให้รองรับ trim handle แบบเลือกด้านได้ แล้ว migrate Hook chip ซึ่งมี right-trim เท่านั้น โดยคง behavior เดิม

### สิ่งที่ทำ

- เพิ่ม `showLeftHandle`/`showRightHandle` แบบ default เป็น `true` ที่ `TimelineIntervalItem.jsx`
- ปรับ Hook track ใน `Timeline.jsx` ให้ใช้ shared shell โดยปิด left handle และคง right-trim callback/title/hover color เดิม
- คง Caption แยกไว้ เพราะใช้ cue ripple/apply-to-all และไม่มี trim policy เดียวกับ interval tracks
- เพิ่ม `timelineIntervalContract.test.js` กัน default two-handle regression และยืนยัน Hook single-sided contract

### Gate

- [x] `Set-Location frontend; npm test` — 104 passed
- [x] `Set-Location frontend; npm run lint` — exit 0, มี warnings เดิมของ repo
- [x] `Set-Location frontend; npm run build` — ผ่าน, 1973 modules transformed
- [x] `git diff --check` — ผ่าน ไม่มี error

### Notes

- ไม่เปลี่ยน Hook duration clamp (`1.0–8.0s`), click-to-seek, selection หรือ Caption ripple
- งานเดิมที่ค้างก่อนเริ่มยังคง untouched: sample sticker 3 ไฟล์ถูกลบ และ untracked `tools/test_scrape_titles.py`

## Round TLO-REFACTOR-7 — รวม timeline pointer lifecycle โดยคง type-specific drag math

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ผลลัพธ์:** รวม pointer capture/release และ movement threshold 3px ของ timeline drag ไว้ใน `timelineDragLifecycle.js` โดยไม่รวม geometry หรือ type-specific policy

### สิ่งที่ทำ

- เพิ่ม `timelineDragLifecycle.js` สำหรับ `capturePointer`, `releasePointer` และ `beginDragAfterThreshold`
- ปรับ `useTimelineDrag.js` ให้ใช้ lifecycle module เดียวกับ Caption, Text, Hook, Sticker และ Effect
- คง state shape, callback order, 3px threshold, snap, clamp, rounding, field mapping และ Caption ripple เดิม
- เพิ่ม deterministic unit tests ตรวจ threshold, เรียก `dragBegin` ครั้งเดียว และ pointer capture/release ที่ tolerate synthetic events

### Gate

- [x] `Set-Location frontend; npm test` — 109 passed
- [x] `Set-Location frontend; npm run lint` — exit 0, มี warnings เดิมของ repo
- [x] `Set-Location frontend; npm run build` — ผ่าน, 1975 modules transformed
- [x] `git diff --check` — ผ่าน ไม่มี error

### Notes

- เป็น lifecycle extraction เท่านั้น ไม่เปลี่ยน timing/geometry behavior ของ overlay ใด
- งานเดิมที่ค้างก่อนเริ่มยังคง untouched: sample sticker 3 ไฟล์ถูกลบ และ untracked `tools/test_scrape_titles.py`

## Round TLO-REFACTOR-6 — รวม shared Inspector header สำหรับ Sticker/Effect

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ผลลัพธ์:** รวม layout ของ preview header, identity label และ timing metadata ของ Sticker/Effect ไว้ใน `OverlayInspectorHeader` โดยคง media preview และ visual config ที่ต่างกันไว้เป็น props

### สิ่งที่ทำ

- เพิ่ม `OverlayInspectorHeader.jsx` สำหรับ preview frame, icon/label, title และ duration metadata ร่วม
- ปรับ `StickerInspector.jsx` ให้ส่ง image preview, `Smile`, cyan accent และ label เดิม
- ปรับ `EffectInspector.jsx` ให้ส่ง video preview, multiply blend, `Sparkles`, fuchsia accent และ label เดิม
- เพิ่ม `overlayInspectorHeaderContract.test.js` ยืนยัน shared layout และ media-specific config ของทั้งสอง Inspector
- คง Position, timing/scale callbacks และ delete actions ตาม policy เดิมของแต่ละชนิด

### Gate

- [x] `Set-Location frontend; npm test` — 107 passed
- [x] `Set-Location frontend; npm run lint` — exit 0, มี warnings เดิมของ repo
- [x] `Set-Location frontend; npm run build` — ผ่าน, 1974 modules transformed
- [x] `git diff --check` — ผ่าน ไม่มี error

### Notes

- เป็น structural extraction/config seam เท่านั้น ไม่เปลี่ยน renderer, preview canvas, timeline drag หรือ visual timing
- งานเดิมที่ค้างก่อนเริ่มยังคง untouched: sample sticker 3 ไฟล์ถูกลบ และ untracked `tools/test_scrape_titles.py`

## Round TLO-REFACTOR-5 — ย้าย Caption chip เข้า shared timeline shell โดยคง magnetic-ripple policy

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ผลลัพธ์:** ย้ายโครงสร้าง Caption chip, trim handles และ body drag เข้า `TimelineIntervalItem` โดยคง behavior-specific drag policy ของ Caption ไว้ใน `useTimelineDrag.js`

### สิ่งที่ทำ

- ปรับ Caption track ใน `Timeline.jsx:1123-1165` ให้ใช้ shared shell เดียวกับ Hook/Sticker/Effect/Text
- ส่ง `startTrim`, `moveTrim`, `endTrim` และ `startCaptionBodyDrag`/`moveCaptionBodyDrag`/`endCaptionBodyDrag` ผ่าน adapter callbacks โดยไม่ย้ายหรือเปลี่ยน geometry math
- คง previous-cue clamp, magnetic ripple/apply-to-all, click-to-select, titles และสีของ Caption เดิม
- เพิ่ม contract test ใน `timelineIntervalContract.test.js` เพื่อยืนยันการใช้ shell และการคง caption-specific callbacks

### Gate

- [x] `Set-Location frontend; npm test` — 105 passed
- [x] `Set-Location frontend; npm run lint` — exit 0, มี warnings เดิมของ repo
- [x] `Set-Location frontend; npm run build` — ผ่าน, 1973 modules transformed
- [x] `git diff --check` — ผ่าน ไม่มี error

### Notes

- ไม่รวม Caption drag math, previous-cue clamp หรือ magnetic ripple เข้า shared core เพราะเป็น behavioral divergence จริง
- ไม่แตะ renderer, preview, timing constants หรือ audio lanes
- งานเดิมที่ค้างก่อนเริ่มยังคง untouched: sample sticker 3 ไฟล์ถูกลบ และ untracked `tools/test_scrape_titles.py`

## Round TLO-REFACTOR-3 — แยก shared Timeline label-gutter primitive

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ผลลัพธ์:** ย้าย `TrackLabel` ออกจาก `Timeline.jsx` ไปเป็น primitive กลาง เพื่อให้ label gutter ของ Timeline และ EffectTrack ใช้ implementation เดียวกัน โดยคง callback, icon slot, fold control, action slot, width/dense sizing และ event propagation เดิม

### สิ่งที่ทำ

- เพิ่ม [TrackLabel.jsx](frontend/src/components/editor/timeline/TrackLabel.jsx) เป็น shared label-gutter component
- ปรับ `Timeline.jsx:1-10,142-191,662-664` ให้ import และใช้งาน primitive กลาง โดยลบ implementation inline เดิม
- ปรับ `EffectTrack.jsx:1-30` ให้ import โดยตรง และลบ prop injection `TrackLabel`
- ไม่รวม visibility action หรือ label text เพราะแต่ละ track มี callback/title/color และเงื่อนไขการแสดงผลต่างกัน

### Gate

- [x] `Set-Location frontend; npm test` — 102 passed
- [x] `Set-Location frontend; npm run lint` — exit 0, มี warnings เดิมของ repo
- [x] `Set-Location frontend; npm run build` — ผ่าน, 1973 modules transformed
- [x] `git diff --check` — ผ่าน ไม่มี error

### Notes

- เป็น structural extraction เท่านั้น ไม่เปลี่ยน renderer output, timeline timing, drag handlers หรือ overlay geometry
- งานเดิมที่ค้างก่อนเริ่มยังคง untouched: sample sticker 3 ไฟล์ถูกลบ และ untracked `tools/test_scrape_titles.py`

## Round TLO-REFACTOR-2 — ลด duplication ฝั่ง renderer เฉพาะจุดที่พิสูจน์ parity ได้

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ผลลัพธ์:** ตรวจ duplication ที่เหลือใน Canvas/ASS renderer และรวมเฉพาะ policy/dispatch ที่มี contract ร่วมกันจริง โดยคง drawing policy ที่ต่างกันไว้แยก

### สิ่งที่ทำ

- เพิ่ม `OVERLAY_RENDER_PROFILES` และ `overlayRenderProfile()` ใน `frontend/src/lib/overlayModel.js` เพื่อเก็บความต่างของ hook/text เป็น data: default animation, word-stagger, layout clearing และ bounds type
- เปลี่ยน `SequencePlayer.jsx:1486-1641` ให้ใช้ profile เดียว โดยรักษา fallback ของ unknown frontend kind ไป text path
- เพิ่ม `overlay_kind()` ใน `scripts/overlay_model.py` และใช้ handler map ใน `scripts/subtitle/overlay_events.py:54-67` เพื่อ normalize `kind`/`type` และ legacy aliases โดยไม่แตะ geometry หรือ ASS drawing math
- เพิ่ม frontend/Python dispatch tests และปรับ source parity assertion ให้ตรวจ policy contract ใหม่
- ยืนยันจาก inventory ว่า Caption/Hook/Text/Sticker/Effect drawing, anchor, alpha, blend, legacy fields, font metrics และ motion timing ยังเป็น behavior-specific; ไม่ genericize ต่อในรอบนี้

### Gate

- [x] `Set-Location frontend; npm test` — 102 passed
- [x] `Set-Location frontend; npm run build` — ผ่าน, 1972 modules transformed
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `python -m pytest tests/test_overlay_render_dispatch.py -q -p no:cacheprovider --tb=short` — 2 passed
- [x] `python -m pytest tests/test_preview_render_parity.py -q -p no:cacheprovider --tb=short` — 150 passed
- [x] `python -m pytest tests/test_preview_render_behavior.py -q -p no:cacheprovider --tb=short` — 11 passed, Pillow deprecation warnings 2 รายการเดิม
- [x] `git diff --check` — ผ่าน ไม่มี error

### Notes

- ไม่แก้ `scripts/subtitle_engine.py`, drawing constants หรือ output geometry เพราะไม่มีการเปลี่ยนภาพที่พิสูจน์ว่าปลอดภัยในรอบนี้
- งานเดิมที่ค้างก่อนเริ่มยังคง untouched: sample sticker 3 ไฟล์ถูกลบ และ untracked `tools/test_scrape_titles.py`

## Round TLO-REFACTOR-1 — แยก abstraction ของ Overlay Timeline/Preview แบบรักษา behavior เดิม

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** ลดโค้ดซ้ำของ Hook, Sticker, Effect, Caption และ Text Overlay ใน timeline/drag/preview โดยแยกเฉพาะ geometry และ lifecycle ที่เหมือนกันออกมาเป็น shared core/config พร้อมคง field names, legacy fallback, clamp, snap, ripple, anchor, audio/visual parity และ selection semantics เดิมทุกประการ

### ผลลัพธ์ตามเฟส

- [x] Phase 0 — สำรวจ contract และบันทึก behavior divergence ของ Timeline, drag hook, SequencePlayer, EditorShell, selection, commands, Inspector และ timeline model
- [x] Phase 1 — เพิ่ม `packTimedLanes` และคง wrapper contract ของ `packTextOverlays`/`packStickers` ใน `timelineTrackModel.js`
- [x] Phase 2 — เพิ่ม `TimelineIntervalItem.jsx` และย้าย Sticker, Effect, Text overlay ไปใช้ shell เดียวกัน โดยคง Hook/Caption ที่มี policy ต่างกันไว้แยก
- [x] Phase 3 — เพิ่ม shared timed-interval drag core ใน `useTimelineDrag.js` สำหรับ Sticker/Effect พร้อม adapter ของ Sticker legacy aliases/signature และ Effect modern fields
- [x] Phase 4 — เพิ่ม `overlayBoxGeometry.js` และ `pointerDragLifecycle.js` สำหรับ selected-box fallback, clamp/snap/resize, field mapping และ window pointer lifecycle โดยคง Caption-specific callbacks
- [x] Phase 5 — เพิ่ม `selectionResolver.js`, `collectionOperations.js`, `OverlayTimingControls.jsx` และ `OverlayScaleControl.jsx`; คง Sticker style mirror/single-slot fallback, Effect overlap placement และ Position block ที่ต่างจริง
- [x] Phase 6 — แก้ parity test baseline ที่ stale จาก 6 เป็น 7 occurrences หลังยืนยันว่า `HEAD` และ current source ตรงกัน และรัน render/behavior gates

### Gate

- [x] `Set-Location frontend; npm test` — 100 passed
- [x] `Set-Location frontend; npm run build` — ผ่าน, 1972 modules transformed
- [x] `python -m pytest tests/test_preview_render_parity.py -q -p no:cacheprovider` — 150 passed
- [x] `python -m pytest tests/test_preview_render_behavior.py -q -p no:cacheprovider` — 11 passed, Pillow deprecation warnings 2 รายการ
- [x] `git diff --check` — ผ่าน ไม่มี error
- [x] ตรวจว่าไม่แตะ `01_Raw/`, `02_Assets/`, `03_Projects/` หรือ `_Docs/post_log.json`

### Notes

- การ genericize จงใจหยุดที่ pure math, lifecycle, selection lookup, collection operations และ Inspector controls ที่มี contract ร่วมกันจริง
- Caption magnetic ripple/apply-to-all, Hook 1–8 second end-only trim, Text policy, Sticker legacy mirror/single-slot fallback, Effect overlap-slot placement และ Position UI ที่ต่างกันยังคงเป็น behavior-specific adapters
- parity baseline drift ที่พบเป็น test expectation เดิม ไม่ใช่ production regression: `Timeline.jsx` มี `slotWidth` 7 occurrences ทั้งใน `HEAD` และ current source
- งานเดิมที่มีอยู่ก่อนรอบนี้ยังคงไม่ถูกแตะ: sample sticker 3 ไฟล์ที่ถูกลบ และ untracked `tools/test_scrape_titles.py`

## Round SFX-TITLES-1 — ดึงชื่อภาษาไทย/ชื่อจริงที่แสดงบน Myinstants มาใส่เป็น label ใน asset_metadata.json

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** ดึง Display Name จากหน้าเว็บ Myinstants ทั้งหมด 50 หน้า บันทึกลงใน `02_Assets/asset_metadata.json` เพื่อให้ชื่อเสียงที่แสดงบนหน้าเว็บ (UI) ทั้ง Media Assets Hub และ AssetPanel แสดงเป็นชื่อภาษาไทย/ชื่อจริงที่อ่านออกและตรงกับหน้าเว็บเป๊ะ

### สิ่งที่ทำ

1. **สร้างสคริปต์ `tools/scrape_myinstants_titles.py`:**
   - ดึงคู่ `(sound_filename, display_title)` จาก 50 หน้าของ Myinstants Thailand
   - รวมชื่อที่ได้ 1,774 รายการบันทึกลงใน `02_Assets/asset_metadata.json` ภายใต้คีย์ `label` และ `label_th` โดยไม่ลบ metadata เดิมของระบบ
2. **อัปเกรด `scripts/asset_registry.py`:**
   - Map ค่า `label` และ `label_th` เข้าสู่ entry ของ SFX และ BGM ทุกชิ้น
3. **อัปเดต Frontend UI (`MediaAssetsHub.jsx` & `AssetPanel.jsx`):**
   - แสดงผล `label` นำหน้าเสมอ และแสดงชื่อไฟล์เป็น secondary info
   - รองรับการค้นหา (Search Query) ด้วยชื่อภาษาไทยและชื่อจริงบนเว็บ

### Gate

- [x] ดึง metadata สำเร็จครบ 50 หน้า (อัปเดต 1,774 รายการ)
- [x] `AssetRegistry.rebuild()` โหลดชื่อ label เข้า sfx สำเร็จ
- [x] `python -m compileall -q scripts tools` — ผ่าน
- [x] `npm test` และ `npm run build` — 86 tests passed, build สำเร็จ

---

## Round SFX-HUB-1 — สแกน SFX แบบ Recursive เข้า AssetRegistry และเพิ่มตัวกรองหมวดหมู่ SFX ใน Media Assets Hub

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** ให้ระบบ AssetRegistry และ Backend API สแกนไฟล์เสียง SFX ทุกโฟลเดอร์ย่อยใน `02_Assets/SFX/` แบบ recursive และแสดงผลใน Media Assets Hub พร้อมตัวกรองหมวดหมู่ย่อย (Sub-category Pills) ให้เปิดฟังและเลือกใช้ได้ครบทั้ง 1,822 ไฟล์

### สิ่งที่ทำ

1. **แก้ไข `scripts/asset_registry.py`:**
   - ปรับ `_scan_sfx()` ให้ใช้ `rglob` สแกนทั้งโฟลเดอร์รูทและโฟลเดอร์ย่อยทั้งหมด
   - ดึงชื่อโฟลเดอร์ย่อย (เช่น `thai/`, `game/`, `meme/`, `horror/` ฯลฯ) มาเป็น `category` ของไฟล์นั้นโดยอัตโนมัติ
   - ปรับ `_cache_is_fresh()` ให้ตรวจสอบการเปลี่ยนแปลงของไฟล์ในโฟลเดอร์ย่อยแบบ recursive
2. **แก้ไข `scripts/api_videos.py`:**
   - ปรับ `/api/sfx` ให้ส่งรายการไฟล์ SFX ผ่าน `AssetRegistry.sfx()` เพื่อให้ได้ชุดข้อมูลที่ครบถ้วนตรงกันทั้งระบบ
3. **อัปเกรด `frontend/src/components/MediaAssetsHub.jsx`:**
   - เพิ่มตัวกรองหมวดหมู่ย่อย (Sub-category Pills: ทั้งหมด, เสียงไทย/ตลก, เกม, มีม, รีแอ็กชัน, แจ้งเตือน/UI, ท่อนเพลง, สยองขวัญ, อนิเมะ, เปลี่ยนฉาก/Whoosh, อื่นๆ)
   - เชื่อมโยงตัวกรองเข้ากับช่องค้นหา (Search Query) ค้นหาได้ทั้งชื่อไฟล์และหมวดหมู่
4. **อัปเดต `frontend/src/components/editor/AssetPanel.jsx`:**
   - ปรับการระบุพาธเสียง preview ให้รองรับ `rel_path` จากโฟลเดอร์ย่อยได้โดยตรง

### Gate

- [x] `python -m compileall -q scripts` — ผ่าน
- [x] pytest `test_preview_render_parity.py` — 150 passed
- [x] `npm test` และ `npm run build` — 86 tests passed, build สำเร็จ
- [x] ตรวจสอบ `AssetRegistry.rebuild()` — พบ SFX ทั้งหมด **1,822 ไฟล์** ตรงตามไฟล์จริงบนดิสก์

---

## Round SFX-CAT-1 — จัดหมวดหมู่ไฟล์เสียง mi_xxx 1,775 ไฟล์ เป็น 10 หมวดใน 02_Assets/SFX/

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** จัดระเบียบไฟล์เสียงเอฟเฟกต์ที่โหลดจาก Myinstants (มีคำนำหน้า `mi_*.mp3`) จำนวน 1,775 ไฟล์ เข้า 10 โฟลเดอร์หมวดหมู่ย่อยใน `02_Assets/SFX/` ตามชื่อและคีย์เวิร์ด เพื่อให้ค้นหาและนำไปใช้งานง่าย โดยไม่กระทบกับไฟล์เสียงเดิม 47 ไฟล์ที่อยู่ในรูท

### สิ่งที่ทำ

1. **สร้างสคริปต์ `tools/categorize_myinstants_sfx.py`:**
   - กำหนด 10 หมวดหมู่หลัก: `transition/`, `notification/`, `game/`, `anime/`, `music/`, `reaction/`, `horror/`, `meme/`, `thai/`, `other/`
   - ใช้ Regex Patterns ครอบคลุมคีย์เวิร์ดภาษาอังกฤษ, ศัพท์เฉพาะวงการเกม/อนิเมะ/มีม และรูปแบบการถอดเสียงภาษาไทยเป็นอักษรโรมัน (Romanized Thai Patterns)
   - ป้องกันไฟล์เสียงเดิม: เฉพาะไฟล์ `mi_*.mp3` เท่านั้นที่จะถูกจัดหมวด ไฟล์เสียงต้นฉบับ 47 ไฟล์คงอยู่ที่รูท `02_Assets/SFX/` เสมอ
2. **รันจัดหมวดหมู่จริง:**
   - ย้ายไฟล์ 1,775 ไฟล์เข้าโฟลเดอร์ย่อยครบ 100% ไม่มี error

### ผลลัพธ์การจัดหมวดหมู่

| หมวดหมู่ | โฟลเดอร์ | จำนวนไฟล์ |
| :--- | :--- | :--- |
| **Anime** | `02_Assets/SFX/anime/` | 65 ไฟล์ |
| **Game** | `02_Assets/SFX/game/` | 114 ไฟล์ |
| **Horror** | `02_Assets/SFX/horror/` | 71 ไฟล์ |
| **Meme** | `02_Assets/SFX/meme/` | 114 ไฟล์ |
| **Music** | `02_Assets/SFX/music/` | 90 ไฟล์ |
| **Notification** | `02_Assets/SFX/notification/` | 80 ไฟล์ |
| **Reaction** | `02_Assets/SFX/reaction/` | 79 ไฟล์ |
| **Thai** | `02_Assets/SFX/thai/` | 179 ไฟล์ |
| **Transition** | `02_Assets/SFX/transition/` | 26 ไฟล์ |
| **Other** | `02_Assets/SFX/other/` | 957 ไฟล์ |
| **Original SFX** | `02_Assets/SFX/` (Root) | 47 ไฟล์ (คงเดิม) |
| **รวมทั้งหมด** | | **1,821 ไฟล์** |

### Gate

- [x] ย้ายไฟล์ครบ 1,775 ไฟล์ (`moved=1775, skipped=0, errors=0`)
- [x] ไฟล์เดิม 47 ไฟล์ในรูทปลอดภัย ไม่ถูกย้ายหรือแก้ไข
- [x] สร้างสคริปต์ `tools/categorize_myinstants_sfx.py` พร้อมโหมด `--report` และ `--dry-run`

---

## Round STK-PRO-1 — ชุดสติกเกอร์และป้ายรีวิวสายไอทีระดับโปร (Photorealistic Tech Review Badges)

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาและสิ่งที่ทำ:**

1. **ออกแบบ Master Prompts สาย Tech ฮาร์ดแวร์จริง 3 ชุด (18 ป้าย):**
   - ผู้ใช้แจ้งว่าสติกเกอร์ชุดก่อนหน้าดูเป็นการ์ตูน/ของเล่นพลาสติก ไม่เข้ากับคลิปรีวิวสินค้าไอที จึงออกแบบ Master Prompts ใหม่ทั้งหมด โดยเน้นวัสดุระดับสูง (Photorealistic Industrial Design): Smoked Tempered Glass, CNC-machined Space Gray Aluminum, Brushed Titanium, Laser-etched typography, Micro-LED telemetry lights, Multi-layer circuit traces และ Cyber HUD callouts ปราศจากตัวการ์ตูนหรือกราฟิกคอมิกส์ 100%
   - **Sheet 1 (Core Review Badges):** PROS (Matte obsidian pill, neon green LED), CONS (Space gray aluminum, crimson LED), WARNING (Titanium hex plate, amber hazard stripes), PRO TIP (Dark glassmorphism, cyan cyber circuit trace), PERFORMANCE (PCB chip plate, neon speedometer gauge), VERDICT (Matte black ceramic plaque, gold rating bars)
   - **Sheet 2 (Tech Specs & Callouts):** BATTERY LIFE (Dark glass lithium cell, emerald power LEDs), BUILD QUALITY (Brushed titanium shield, chamfered bevels), SPECS (PCB telemetry tag, cyan LEDs), BEST VALUE (Obsidian plaque with gold trim and diamond), TECH ARROW (Aerodynamic titanium pointer with cyan neon edge), HUD CALLOUT (Cyber camera viewfinder reticle frame)
   - **Sheet 3 (Hardware Features & Rating):** SCORE (9.8/10 digital OLED segment display with 5 gauge dots), MUST BUY (Brushed titanium award medal, gold rim), DISPLAY (OLED deep black screen, liquid HDR wave), AUDIO (CNC perforated speaker grille, cyan soundwave), CAMERA (Leica-style camera lens module, aperture blades), CONNECTIVITY (Glass badge, cyan Wi-Fi lightning bolt)
2. **เจนรูปภาพความละเอียดสูง 3 แผ่นและสไลซ์โปร่งใส (Alpha Cutout):**
   - เจนภาพ 3 แผ่นด้วย `generate_image` บน Solid Pure White (`#FFFFFF`) พร้อม Thick Die-cut Border ตามกฎ `sticker_generation.md`
   - สร้างสคริปต์ `tools/slice_pro_tech_stickers.py` ตัดแยกแต่ละป้ายและตัดพื้นหลังโปร่งใสด้วย AI `rembg` ได้ PNG คมกริบขนาด ~500-600px พร้อม Bounding box ที่กระชับพอดี
   - สำรองสติกเกอร์การ์ตูนเดิม 12 ชิ้นไว้ใน `02_Assets/Stickers_Memes/_backup_cartoon/` ตามกฎเหล็กข้อ 1 (Strict Rule 1)
   - ปล่อยไฟล์ PNG โปร่งใสทั้ง 18 ป้ายลงใน `02_Assets/Stickers_Memes/`
3. **อัปเดตชื่อภาษาไทยใน Frontend UI (AssetPanel.jsx):**
   - อัปเดตดิคชันนารี `STICKER_TITLES` ใน `frontend/src/components/editor/AssetPanel.jsx` ให้ครอบคลุมสติกเกอร์ใหม่ทั้งหมด 18 ชิ้นด้วยชื่อภาษาไทยทางการ สะอาด ปราศจากอีโมจิหรือสัญลักษณ์ซ้ำซ้อนตามกฎเหล็กข้อ 8

### Gate

- [x] `python -m compileall -q scripts` (ผ่าน: 0 errors)
- [x] `python -m pytest tests/test_preview_render_parity.py tests/test_preview_render_behavior.py -q -p no:cacheprovider` (ผ่าน: 159 passed, 2 warnings in 8.55s)
- [x] `npm --prefix frontend test` (ผ่าน: 85 passed in 1.60s)
- [x] `npm --prefix frontend run build` (ผ่าน: 1963 modules built in 3.30s)
- [x] ตรวจสอบไฟล์ PNG โปร่งใสทั้ง 18 รายการใน `02_Assets/Stickers_Memes/` (ผ่าน: ครบ 18 ชิ้น โหมด RGBA มี Alpha โปร่งใส 100%)

### Notes

- สติกเกอร์เดิม 12 ชิ้นที่เป็นภาพการ์ตูนได้รับการสำรองไว้อย่างปลอดภัยที่ `02_Assets/Stickers_Memes/_backup_cartoon/`
- ป้ายทั้งหมด 18 ชิ้นเป็น Universal Reusable Badges ไม่ระบุรุ่นสินค้าหรือยี่ห้อ สามารถนำไปใช้กับคลิปรีวิวไอทีและแกดเจ็ตได้ทุกตัว
- ใน Editor หน้า AssetPanel แสดงชื่อภาษาไทยชัดเจน เช่น "จุดเด่น (PROS)", "ข้อสังเกต (CONS)", "อายุแบตเตอรี่ (Battery)", "คะแนนรีวิว 9.8 (Score)", "ชิปประมวลผล (Performance)" เป็นต้น

## Round SUB-THAI-1 — แก้สระและวรรณยุกต์ไทยซ้อนกันในคลิปเรนเดอร์

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาและสิ่งที่ทำ:**

1. ตรวจ repro ด้วยข้อความ `นั่งพิมพ์งานทั้งวัน` ซึ่งมีคู่เครื่องหมายซ้อน `ั + ่` และพบว่า caption ใช้ `\\fscx125/\\fscy125` ในช่วง 70ms แรก การขยาย raster หลัง libass จัดตำแหน่ง mark แล้วทำให้เครื่องหมายชนกันได้ในเฟรมต้น ๆ
2. เปลี่ยน caption entrance ใน `scripts/subtitle_engine.py` เป็น `\\alpha&HFF&\\t(0,70,\\alpha&H00&)` ซึ่งไม่เปลี่ยนเรขาคณิตของ glyph และจัดลำดับ tag ให้ shadow fade ไปพร้อมกับตัวอักษร
3. เปลี่ยน Canvas ใน `frontend/src/components/SequencePlayer.jsx` ให้ใช้ `globalAlpha` fade 70ms และคงขนาด/ตำแหน่ง glyph เท่าเฟรม settled เพื่อรักษา Preview = Render
4. เพิ่ม source parity test และ FFmpeg behavioral render test ที่ตรวจเฟรมซ่อน, เฟรมแรกที่มองเห็น และเฟรม settled โดย bounding box ของข้อความต่างกันไม่เกิน 4px

### Gate

- [x] `python -m compileall -q scripts` (ผ่าน)
- [x] Focused subtitle/preview tests: 165 passed, 2 warnings
- [x] Full backend tests: 926 passed, 6 warnings, 110.92s
- [x] `npm test`: 85 passed
- [x] `npm run build`: ผ่าน, 1963 modules built
- [x] FFmpeg behavioral render: stacked Thai marks ผ่าน multi-frame geometry check

Notes: ไม่แตะ `01_Raw/` หรือ `02_Assets/`; ใช้ synthetic fixture ใน temp storage และตรวจภาพจาก FFmpeg จริง

## Round STK-3 — ปรับขนาดสติกเกอร์ 100% เท่ากับขนาดจอที่ผู้ใช้ต้องการ, ซ่อมปุ่มปิดตาแทร็กสติกเกอร์, ลบสติกเกอร์ได้ทุกช่องทาง และระบบพรีวิวก่อนกดบวกเหมือนข้อความ

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาและสิ่งที่ทำ (4 ข้อตามคำสั่ง User):**

1. **ไอคอนขนาดนี้อยากให้เป็น 100% (Baseline 100% Scale):**
   - ขนาดที่ผู้ใช้ชี้ในภาพหน้าจอเดิมมี Scale 40% (~152-160px) ถูกตั้งเป็นขนาดมาตรฐาน 100% (`scale = 1.0`)
   - แก้ไข `STICKER_BASE_WIDTH = 160` ใน `scripts/video_editor.py` และ `baseW = 160` ใน `frontend/src/components/SequencePlayer.jsx`
   - ปรับ scale clamp ให้รองรับได้กว้าง 30% ถึง 350% ลื่นไหลเป็นธรรมชาติ
   - ปรับการทดสอบ Parity ใน `tests/test_phase1_smoke.py`
2. **กดปิดตา สตก ที่ไทมไลน์ไม่ได้อ่ะ (Track Eye Toggle):**
   - ใน `EditorShell.jsx` เพิ่ม state `isStickerHidden` และฟังก์ชัน `handleToggleHideSticker`
   - เชื่อมต่อส่งไปยัง `<Timeline />` (ทั้งโหมดเดสก์ท็อปและมือถือ) และ `<SequencePlayer />`
   - ใน `SequencePlayer.jsx`: เมื่อ `isStickerHidden` เป็นจริง จะหยุดวาดสติกเกอร์บน Canvas ทันที พร้อมป้องกันการคลิก/ลากย้ายสติกเกอร์ที่ถูกซ่อน
3. **เพิ่มได้แต่ลบไม่ได้อ่ะ (Multi-Way Sticker Deletion):**
   - ใน `useEditorCommands.js` ในฟังก์ชัน `deleteSelected()` เพิ่มเงื่อนไข `selection?.type === 'sticker'` ให้ลบออกจากอาเรย์ `stickers: [...]` รองรับปุ่ม `Delete`/`Backspace` บนคีย์บอร์ด และปุ่มถังขยะบน Toolbar
   - สร้างคอมโพเนนต์ `StickerInspector.jsx` แสดงข้อมูลสติกเกอร์ (เวลาเริ่ม, เวลาจบ, สเกล %, พิกัด) พร้อมปุ่มลบสีแดงเด่นชัด `ลบสติกเกอร์`
   - เชื่อมต่อ `StickerInspector` ใน `Inspector.jsx` เมื่อเลือกสติกเกอร์บนไทม์ไลน์
4. **ตอนกดให้พรีวิวก่อน ถ้าอยากให้ลงไทมไลน์ ค่อยกด + เหมือน ข้อความอ่ะ (Preview First & Plus Button Add):**
   - ใน `AssetPanel.jsx` แท็บสติกเกอร์: คลิกที่การ์ดสติกเกอร์จะเป็นการพรีวิว (`onPreviewSticker(s.name)`) โดยยังไม่เพิ่มลงไทม์ไลน์
   - บนหน้าจอวิดีโอ Canvas จะแสดงภาพสติกเกอร์ตัวอย่างกึ่งกลางจอ พร้อมกรอบประสีฟ้านีออนและป้าย `พรีวิวสติกเกอร์` แบบ Ephemeral ชั่วคราว (คลิกนอกกล่องจะปิดพรีวิวอัตโนมัติ)
   - บนการ์ดสติกเกอร์ มีปุ่ม `+` มุมขวาบน (สไตล์เดียวกับ Text Template) เมื่อกดปุ่ม `+` จึงจะเพิ่มสติกเกอร์ลงบนไทม์ไลน์ที่ตำแหน่ง Playhead (ความยาว 3.0s)
   - เพิ่มปุ่มกดด้านล่าง `เพิ่ม [ชื่อสติกเกอร์] ลงไทม์ไลน์` ให้กดเพิ่มได้สะดวกอีกทางหนึ่ง

### Gate

- [x] `python -m compileall -q scripts` (Pass)
- [x] `python -m pytest tests/test_preview_render_parity.py tests/test_multi_stickers.py tests/test_phase1_smoke.py -q -p no:cacheprovider` (299 passed in 41.66s)
- [x] `npm test` ใน `frontend/` (85 passed in 1.78s)
- [x] `npm run build` ใน `frontend/` (Pass, 1963 modules built in 4.25s)
- [x] Live Browser Verification (Recorded video `verify_stk3_features_1788859163223.webp`):
  1. ขนาด 100% เท่ากับขนาด 160px บนหน้าจอวิดีโอ
  2. พรีวิวก่อนเพิ่มได้ และมีป้าย "พรีวิว"
  3. กดปุ่ม `+` เพื่อเพิ่มลงไทม์ไลน์ 3.0s
  4. ปุ่มตา [👁️] ซ่อน/แสดงสติกเกอร์บนวิดีโอได้จริง
  5. ลบสติกเกอร์ได้จริงทุกช่องทาง ทั้งปุ่มลบในแผงและปุ่ม Del

## Round STK-2 — Multi-Sticker Support, 3-Second Default Duration, and Smooth Canvas Resizing

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาและสิ่งที่ทำ:**

1. **Default 3 sec:** กำหนดเวลาเริ่มต้นของสติกเกอร์ที่เพิ่มใหม่เป็น 3.0 วินาทีเสมอ (`start = playhead`, `end = min(totalDuration, playhead + 3.0)`)
2. **การยืดขยายให้สมูท (Smooth Linear Resizing):** แก้ไขจาก Euclidean radial distance (`Math.hypot`) ที่กระตุกและสะบัดขยายผิดธรรมชาติเมื่อข้ามแกน มาเป็น Linear Vector Projection (`projectedDelta = deltaX * dirX + deltaY * dirY`, `scaleFactor = 1 + projectedDelta / initialDist`) ทำให้การลากย่อขยายลื่นไหล ติดนิ้ว 1:1 ทุก Handle
3. **รองรับสติกเกอร์หลายตัวพร้อมกัน (Multi-Stickers Array):** เปลี่ยนโมเดลเป็น `stickers: [...]` แสดงบนไทม์ไลน์พร้อมกัน และสามารถทับซ้อนเวลาเดียวกันได้ (Overlapping Stickers) โดยมีอัลกอริทึม `packStickers(stickers)` จัดเรียงแยก sub-lanes อัตโนมัติ
4. **Preview = Render Parity 100%:**
   - ฝั่ง Frontend (`SequencePlayer.jsx`): โหลดและแคชภาพสติกเกอร์ทุกตัวใน `stickerImagesRef`, แสดงสติกเกอร์ทั้งหมดที่อยู่ในช่วงเวลา `t`, รองรับการคลิกเลือกเพื่อย้าย/ย่อขยายแต่ละตัว
   - ฝั่ง Backend (`video_editor.py`, `video_assembly_stage.py`, `pipeline.py`, `api_schemas.py`): รองรับ `stickers: List[Dict]` สร้าง filter complex overlay ต่อเนื่อง `[v_stickered_{i}]` พร้อม `enable='between(t,start,end)'` และขนาด/พิกัดเฉพาะตัว
5. **UI คลีนตาม Rule 8:** ใน `AssetPanel.jsx` แสดงตัวควบคุมสติกเกอร์ที่ถูกเลือก (Inspect Duration, Scale, Center Reset, Delete), รายการชิปสติกเกอร์ทั้งหมดในวิดีโอ, และปุ่มล้างสติกเกอร์ทั้งหมด

### Gate

- [x] `python -m compileall -q scripts` (Pass)
- [x] `pytest tests/test_preview_render_parity.py` (149 passed in 4.74s)
- [x] `pytest tests/test_phase1_smoke.py -k sticker` (3 passed in 1.02s)
- [x] `pytest tests/test_multi_stickers.py` (2 passed in 0.26s)
- [x] `npm --prefix frontend run build` (Pass, 1962 modules transformed, built in 4.88s)
- [x] `npm --prefix frontend test` (85 passed in 1.76s)
- [x] Browser Subagent live visual verification on `LOG01-ปัญหาก่อนใช้_1` (Added 2 overlapping stickers: 3.0s alert badge + 2.3s arrow pointer, verified simultaneous canvas rendering on video, auto-stacked timeline sub-lanes, and smooth resize handles).

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาและสิ่งที่ทำ:**

- ผู้ใช้สั่ง: "ถ้าแค่เพิ่มข้อความมา ซ้าย ขวา บน ล่าง แล้วเรียกตกแต่งแล้ว ก็พอเถอะ เหมือนเดิม"
- คืนค่าตัวเลือกการตกแต่งป้ายฮุก (Accent) ให้กลับมาสะอาด กระชับ คลีน เหมือนเดิม โดยมีเพียง 3 ตัวเลือกหลักดั้งเดิม:
  1. `underline` ("เส้นใต้เรืองแสง" / Accent Bar)
  2. `badge` ("แถบไฮไลต์" / Badge)
  3. `none` ("ไม่มี" / None)
- ไฟล์ที่อัปเดต:
  - `scripts/hook_motion_presets.py`: คืนค่า `HOOK_ACCENT_PRESETS` เหลือ 3 ตัวเลือกดั้งเดิม
  - `frontend/src/components/editor/inspector/OverlayInspector.jsx`: คืนค่า `FALLBACK_ACCENT_OPTIONS` เหลือ 3 ตัวเลือกดั้งเดิม
  - รีสตาร์ต Backend API Server เพื่อให้ serving ค่าใหม่ทันที
- การทดสอบและ Gate:
  - `python -m compileall -q scripts`: ผ่าน 100%
  - `python -m pytest tests/test_preview_render_parity.py -q -p no:cacheprovider`: ผ่านครบ 149/149 passed
  - `npm --prefix frontend run build`: ผ่านสะอาด 100%
  - `python -m pytest tests/test_phase1_smoke.py -k "accent or hook_motion" -q -p no:cacheprovider`: ผ่าน 8/8 passed

## Round PREV-2 — ซ่อมบั๊กพรีวิวดำและข้อความตกค้าง (Fix Infinite Seek Loop in renderAt & Unconditional Canvas Clear)

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาและสาเหตุ:**

1. **ภาพวิดีโอดำ (Black Screen):** ใน `renderAt(t)` มีการสั่ง `video.currentTime = entry.localTime` เมื่อตรวจพบความคลาดเคลื่อนเกิน 0.08s แต่ `renderAt` ถูกผูกเป็น listener ของ `onSeeked` ทำให้เกิด **Infinite Seek Loop** (seeked -> renderAt -> seek -> seeked) ส่งผลให้ `<video>` ติดสถานะ `seeking = true` ตลอดเวลา ไม่ยอมส่งเฟรมภาพที่ถอดรหัสแล้วออกมายัง Canvas
2. **ข้อความฮุกและซับไตเติลค้าง/ซ้อนทับเป็นภาพซ้อน (Ghosting / Overlay Echo):** ใน `tick()` การสั่ง `ctx.clearRect(0, 0, CANVAS_W, CANVAS_H)` ถูกครอบไว้ใต้เงื่อนไข `if (video.readyState >= 2 && !video.seeking) { if (!framePainted) ctx.clearRect(...) }` เมื่อวิดีโอติด seeking หรือยังไม่มีเฟรมใหม่ `ctx.clearRect` จะไม่ถูกเรียกเลย ทำให้ภาพข้อความของวินาทีก่อนหน้า (เช่น ป้ายฮุกช่วง 0-3s) ค้างอยู่บน Canvas ถาวร ไม่หายไปแม้วินาทีที่เล่นอยู่จะเกิน 3s แล้วก็ตาม

**ผลลัพธ์:**

- `frontend/src/components/SequencePlayer.jsx`:
  - นำ `video.currentTime = ...` ออกจาก `renderAt(t)` 100% ทำให้ `renderAt` ทำหน้าที่วาดเฟรมบริสุทธิ์ หยุดการเกิด Infinite Seek Loop โดยสิ้นเชิง
  - ย้าย `ctx.clearRect(0, 0, CANVAS_W, CANVAS_H)` ขึ้นมาทำงานที่จุดเริ่มต้นของรอบวาดใน `tick()` แบบ Unconditional ทุกเฟรม ลบล้างข้อความ/ซับไตเติลของวินาทีก่อนหน้าที่หมดอายุไปแล้ว ไม่ให้หลงเหลือ ghosting หรือภาพซ้อนบนจอ
  - ปรับปรุงการวาดเฟรมวิดีโอให้วาดทันทีเมื่อ `video.readyState >= 2` โดยไม่ถูกสกัดกั้นด้วยสถานะ `video.seeking` ในคลิปเดียวกัน
  - ลดความซ้ำซ้อนของ event listeners บน `<video>` ให้เหลือเฉพาะ `onLoadedData` และ `onSeeked`
- ตรวจสอบ Gate ผ่านทั้งหมด: Parity 149/149 passed, Smoke 147/147 passed, npm run build passed

## Round ACCENT-PRO-1 — เพิ่มสไตล์ตกแต่งป้ายฮุกให้หลากหลาย 11+ รูปแบบระดับโปร (Adaptive Framing, Hybrid Color, Motion Sync, 100% Parity)

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาและขอบเขตงาน:**

1. เมนูตกแต่ง ("ตกแต่ง" ใน Inspector) มีเพียง 2-3 แบบ และในบางครั้งไม่โหลดบนหน้าเว็บ ผู้ใช้ต้องการความหลากหลายที่สวยงามระดับมืออาชีพสำหรับคลิป TikTok/Shorts
2. เพิ่มชุดสไตล์ตกแต่ง 11+ รูปแบบ:
   - `bracket` (กรอบมุมไซเบอร์ Tech Brackets `[ ]`), `glow_box` (กล่องนีออนเรืองแสง), `double_bar` (เส้นคู่บนล่าง)
   - `sale_tag` (ป้ายแท็กสินค้าราคาพิเศษ), `pill_badge` (ป้ายแคปซูลโมเดิร์น), `marker` (ไฮไลต์ปากกาเมจิก)
   - `bold_quotes` (เครื่องหมายคำพูดใหญ่ “ ”), `dashed_box` (กรอบเส้นประโฟกัส), `speed_slash` (ขีดเฉียงสปอร์ต //)
   - `gradient_line` (เส้นไล่เฉดมินิมอล), `underline` (เส้นใต้เรืองแสง), `badge` (แถบไฮไลต์), `none` (ไม่มี)
3. ระบบจัดวางอัจฉริยะ (Adaptive Placement): รูปแบบกรอบครอบทั้งป้าย, รูปแบบเส้นเน้นเฉพาะบรรทัดหลัก, รูปแบบแท็ก/คำพูดโอบล้อมข้อความ
4. สีไฮบริด (Hybrid Color): ซิงก์สีอัตโนมัติตามสีไฮไลต์ของป้าย พร้อมให้เลือกสีเฉพาะของตกแต่งได้อิสระใน Inspector (พร้อมปุ่มคืนค่าอัตโนมัติ)
5. Local Catalog Fallback: ให้เมนูหน้าเว็บแสดงครบทั้ง 12 รายการทันทีโดยไม่ต้องรอรีสตาร์ตเซิร์ฟเวอร์
6. Preview = Render Parity 100%: วาดรูปทรงเรขาคณิตตรงกันทั้ง Canvas 2D และ ASS Vector Drawing (`\p1`)

**ผลลัพธ์:**

- `scripts/hook_motion_presets.py`: ลงทะเบียนครบ 12 สไตล์ใน `HOOK_ACCENT_PRESETS`
- `scripts/overlay_model.py` & `frontend/src/lib/overlayModel.js`: เพิ่มฟิลด์ `accent_color` ใน Overlay Look
- `frontend/src/components/editor/inspector/OverlayInspector.jsx`: เพิ่ม `FALLBACK_ACCENT_OPTIONS` และ Accent Color Picker UI พร้อมสวอทช์สียอดนิยม
- `scripts/subtitle/badge_plate_renderer.py`: เพิ่มการสร้างคำสั่งวาดเส้นเวกเตอร์ ASS (`\p1`) ครบทั้ง 11+ สไตล์
- `scripts/subtitle/overlay_events.py`: ซิงก์ Accent เข้ากับไทม์ไลน์และส่งผ่านสี `accent_color` อย่างถูกต้อง
- `frontend/src/components/SequencePlayer.jsx`: รองรับการวาด Canvas 2D ครบทุกสไตล์ตรงกับ ASS 100%
- ผ่าน Gate ตรวจสอบครบทุกตัว: `compileall` ผ่าน, `pytest test_preview_render_parity.py` ผ่าน 149/149 ข้อ, `npm run build` ผ่านสมบูรณ์, `test_phase1_smoke.py` ผ่าน 147/147 ข้อ

## Round POST-5 — ยกระดับความสมบูรณ์และเสถียรภาพของวงจรชีวิตคลิปที่โพสต์แล้ว (Full Posted Evidence & Lifecycle Integrity Lockdown)

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหาที่ตรวจพบเพิ่มเติม:**

1. ในหน้า Editor (`EditorShell.jsx` + `api_phase1.py`) ตัวเลือกการลบโปรเจกต์แบบ `angle` และ `product` ยังเปิดให้ลบมุมหรือสินค้าที่โพสต์แล้วได้ ทำให้ประวัติสคริปต์และข้อมูลปักตะกร้าหายไปจาก Tracker
2. ในหน้าสินค้า (`ProductToClip.jsx` + `api_products.py`) ยังเปิดให้แก้ไขสคริปต์, แทนที่คำ, และกดรีสคริปต์ AI (Reroll) ในมุมที่โพสต์ไปแล้วได้ ซึ่งทำให้สคริปต์ไม่ตรงกับวิดีโอที่ออนไลน์บน TikTok
3. ในหน้า Tracker (`ContentTrackerHub.jsx`) ฟังก์ชัน Drag & Drop ยังยอมให้ลากการ์ดที่โพสต์แล้วย้อนกลับไปคอลัมน์อื่นได้
4. ใน `ProductStore.py` ฟังก์ชัน `update_angle_status()` และ `remove_angle()` ยังไม่มีการบล็อกการลดสถานะหรือลบมุมที่โพสต์แล้วที่ระดับฐานข้อมูล
5. ในมือถือ (`MobileQuickPostPage.jsx`) การมาร์กโพสต์ยังไม่สั่งย้ายไฟล์จริงจาก `04_Exports/Ready_to_post/` ไป `04_Exports/Posted/`

**ผลลัพธ์:**

- `scripts/product_store.py`: ใน `update_angle_status()` ปฏิเสธการลดสถานะของมุมที่โพสต์แล้ว และใน `remove_angle()` / `delete()` ยกเลิกคำขอลบมุม/สินค้าที่โพสต์แล้ว
- `scripts/api_products.py`: ใน `/api/products/{id}/angles/{aid}/reroll-script` ปฏิเสธการรีสคริปต์มุมที่โพสต์แล้วด้วย HTTP 400
- `scripts/api_phase1.py` และ `frontend/src/components/editor/EditorShell.jsx`: บล็อกการลบแบบ `angle` และ `product` ในหน้าต่าง Delete Project หากมุมนั้นโพสต์แล้ว เหลือเฉพาะการลบไฟล์ตัดต่อดราฟต์ (`project`) คืนพื้นที่ดิสก์
- `frontend/src/components/ProductToClip.jsx`: ล็อกมุมที่โพสต์แล้วเป็น Read-Only (ปิดการแก้ไขบทพูด, ซ่อนปุ่มแทนที่คำ/รีสคริปต์ AI/ตัดใหม่ และแสดงป้ายโพสต์แล้ว)
- `frontend/src/components/ContentTrackerHub.jsx`: ป้องกัน Drag & Drop ไม่ให้ลากการ์ดออกจากคอลัมน์ "โพสต์แล้ว"
- `frontend/src/components/MobileQuickPostPage.jsx` และ `scripts/api_exports.py`: ให้การมาร์กโพสต์ย้ายไฟล์ MP4 เข้า `04_Exports/Posted/` และรับรู้สถานะ `is_posted` ทั้งจากโฟลเดอร์และจากสถานะมุม
- Gate: `python -m compileall -q scripts` ผ่าน, `python -m pytest tests/test_posted_protection.py` ผ่าน 7/7, `npm run build` ผ่าน 100%

## Round POST-4 — ป้องกันการลบวิดีโอที่โพสต์แล้วใน Gallery, ล็อกไม่ให้เรนเดอร์ซ้ำในหน้าตัดต่อ และแก้ปัญหาย้อนสถานะ

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหา:**

1. เมื่อลบวิดีโอหรือลบเวอร์ชันเก่าในหน้า Gallery ระบบเรียก `rollback_by_video_or_project` ทำให้คลิปที่โพสต์ไปแล้ว (`status == "posted"`) ถูกย้อนสถานะกลับมาเป็น `in_production` (กำลังตัดต่อ)
2. หน้า Gallery ยังไม่มีการล็อกไม่ให้ลบคลิปที่โพสต์แล้ว (ต้องเก็บเป็นหลักฐาน)
3. ในหน้าตัดต่อ (Editor) ยังเปิดให้กดเรนเดอร์ซ้ำได้ แม้คลิปนั้นจะโพสต์ไปแล้ว

**ผลลัพธ์:**

- แก้ไข `scripts/product_store.py`: `_roll()` และ `reconcile_existing_projects()` ป้องกันสถานะ `posted` อย่างเข้มงวด
- แก้ไข `scripts/api_videos.py`: บล็อกการลบวิดีโอใน `04_Exports/Posted/` หรือคลิปที่โพสต์แล้ว โดยตอบกลับ HTTP 400
- แก้ไข `scripts/api_render.py` และ `scripts/api_phase1.py`: บล็อกเรนเดอร์/reroll ซ้ำสำหรับโปรเจกต์ที่โพสต์แล้ว โดยตอบกลับ HTTP 400
- ปรับปรุง `frontend/src/components/ExportGallery.jsx`: ซ่อน/disable ปุ่มลบสำหรับคลิปที่โพสต์แล้ว พร้อมแสดงป้าย `โพสต์แล้ว (ห้ามลบ)`
- ปรับปรุง `frontend/src/components/editor/`: เพิ่ม prop `isPosted` ให้ปุ่มเรนเดอร์กลายเป็น `โพสต์แล้ว (ล็อก)` เมื่อคลิปถูกโพสต์แล้ว
- Gate: `python -m compileall -q scripts` ผ่าน, `pytest tests/test_posted_protection.py` ผ่าน 3/3

## Round BUG-4 — แก้ไขคลิปบวมสะสมทุกครั้งที่เรนเดอร์ (Transition Overlap Compounding Feedback Loop)

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**ปัญหา:**
ทุกครั้งที่กด Render ซ้ำหรือเข้าโปรเจกต์เดิมมาเรนเดอร์ใหม่ คลิปในไทม์ไลน์จะยาวขึ้นเรื่อยๆ เกินความยาวเสียงจริง (เช่น `LOG01-สเปก_1` เสียงจริง 27.24s แต่คลิปบวมไปถึง 44.28s) เกิดจาก `video_assembly_stage.py` ไปบวก transition overlap (+0.25s ต่อรอยต่อ) เข้ากับ `clip["duration"]` และ `clip["trim_end"]` ซ้ำทุกครั้งที่เรนเดอร์ แล้วเซฟกลับลง `project.json`

**ผลลัพธ์:**

- แยกระหว่างคลิปที่เจนใหม่สด (`is_newly_generated_clips = True`) กับคลิปที่ส่งมาจาก Editor ใน `shot_matching_stage.py` / `video_assembly_stage.py`
- ป้องกันไม่ให้ `video_assembly_stage.py` ขยาย duration/trim_end ซ้ำกับคลิปที่มีอยู่แล้ว
- แก้ไขการคำนวณ `video_span` ใน `scripts/video_editor.py` ให้ใช้ `acc_dur` เพื่อคำนวณ `tail_gap` และ `tpad` ให้ตรงกับความยาวจริงหลัง xfade
- รัน `tools/repair_swollen_projects.py` เพื่อ normalize duration ของโปรเจกต์เดิมทั้งหมดใน `03_Projects/` กลับมาสอดคล้องกับ audio duration จริง
- Gate: `pytest tests/test_preview_render_parity.py` ผ่าน 149, `pytest tests/test_clip_compounding_render.py` ผ่าน 2, `pytest tests/test_transition_single_clip.py tests/test_phase1_smoke.py` ผ่าน 159

## Round HOK-1 — ระบบ Custom Hook Template Studio (สร้างและบันทึกแม่แบบฮุกด้วยตัวเอง)

วันที่: 2026-09-07 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**ผลลัพธ์:**

- **Custom Template Storage & CRUD Backend:**
  - สร้างไฟล์เก็บข้อมูล `02_Assets/Templates/custom_hook_templates.json` รองรับการเก็บสไตล์ฮุกส่วนตัว (font, size, colors, motion, layout, text tiers)
  - พัฒนาโมดูล `scripts/hook_styles.py` ให้มีฟังก์ชัน `load_custom_hook_templates()`, `save_custom_hook_template()`, `delete_custom_hook_template()` พร้อม atomic write
  - เพิ่ม API routes ใน `scripts/api_editor.py`: `GET /api/editor/hook-templates`, `POST /api/editor/hook-templates`, `DELETE /api/editor/hook-templates/{template_id}`
- **Frontend Sync & Dynamic Registration:**
  - เพิ่ม API client ใน `frontend/src/api.js`: `getHookTemplates()`, `saveCustomHookTemplate()`, `deleteCustomHookTemplate()`
  - อัปเดต `frontend/src/lib/hookStyles.js` ให้มีฟังก์ชัน `registerCustomHookTemplates()` รวมแม่แบบส่วนตัวเข้ากับ Built-in 8 รูปแบบแบบไร้รอยต่อ
- **Inspector & Quick Save UI:**
  - เพิ่มการ์ด "บันทึกเป็นสไตล์ของฉัน" ใน `OverlayInspector.jsx` พร้อมช่องกรอกชื่อและปุ่มบันทึก
  - เมื่อบันทึกสำเร็จ แม่แบบจะขึ้นในการ์ดเลือกสไตล์ทันที พร้อมกรอบสีนีออนไซเบอร์ `#25F4EE`, ป้ายชื่อ, แท็ก motion, และปุ่มถังขยะลบแม่แบบ
- **AssetPanel & Toolbar Integration:**
  - แถบ "ข้อความ" ใน `AssetPanel.jsx` แบ่งหมวดหมู่ชัดเจน: "แม่แบบของฉัน" และ "แม่แบบมาตรฐาน" พร้อมปุ่มลบ
  - เมนูดรอปดาวน์ `ฮุก:` บน Quick Toolbar ใน `Toolbar.jsx` แสดง `<optgroup label="🌟 แม่แบบของฉัน">` และ `<optgroup label="⚡ แม่แบบมาตรฐาน">` ซิงก์ข้อมูลอัตโนมัติ
- **Gates & Verification:**
  - `pytest tests/test_hook_templates_custom.py` ผ่าน 2/2 tests
  - `pytest tests/test_preview_render_parity.py` ผ่าน 149/149 tests
  - `python -m compileall -q scripts` ผ่าน
  - `npm test` ใน frontend ผ่าน 85/85 tests
  - `npm run build` ผ่านใน 3.22 วินาที
  - ทดสอบสดบนเบราว์เซอร์จริงผ่าน `browser_subagent` (บันทึกคลิป `hook_template_studio_1788801788848.webp`) สร้างแม่แบบ `Cyber Neon Pro` สำเร็จ แสดงผลใน Inspector, AssetPanel, และ Toolbar ครบถ้วน

## Round EDT-1 — ตรวจสอบและปรับปรุง UX/UI หน้าตัดต่อ (Editor Friction & Speed Optimization)

วันที่: 2026-09-07 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**ผลลัพธ์:**

- **Friction Audit:** ตรวจสอบหน้าตัดต่อบนเบราว์เซอร์จริงกับโปรเจกต์ `LOG01-ปัญหาหลังใช้_1` พบว่ากระบวนการตัดต่อ 1 คลิปเดิมใช้ 22–28 คลิก ปรับปรุงลดลงเหลือ 9–12 คลิก (ลดลงกว่า 55%)
- **Safe Zone 420px Parity & Guide:**
  - แก้ไขการคำนวณและเลย์เอาต์ Safe Zone ใน `SequencePlayer.jsx` จากเดิมที่ใช้ `top-[56.25%]` (ทำให้เส้นแดงพาดกลางสินค้า/จอ) เปลี่ยนเป็น:
    - พื้นที่อันตรายล่าง (Bottom Danger Zone): `bottom-0`, ความสูง `21.9%` (420px ของ 1920px) พร้อมเส้นประแดง `#FE2C55` และป้ายเตือน Safe Zone 420px ชัดเจน
    - พื้นที่อันตรายขวา (Right Action Icons Zone): ความกว้าง `11.1%` (120px ของ 1080px) พร้อม Ghost icons ของ TikTok
    - พื้นที่หัวคลิปบน (Top Margin): ความสูง `9.4%` (180px ของ 1920px)
    - กล่อง Safe Zone เขียวนีออนตรงกลางจอ สัดส่วนปลอดภัย 9:16
  - เพิ่มปุ่มลัด `Safe Zone` ใน Timeline Toolbar ทำงาน Sync สองทางกับปุ่มบน Preview Stage
- **Quick Action Toolbar:**
  - เพิ่มปุ่ม `รีเซ็ตซูม` (RotateCcw) ใน Toolbar: เมื่อคลิปถูกครอบตัดหรือซูม/เลื่อนตำแหน่ง ปุ่มจะไฮไลต์ และสามารถคลิก 1 ครั้งเพื่อคืนค่าซูม 100% และตำแหน่ง (x:0, y:0) ทันที (เดิมต้องเปิด Inspector และเลื่อนหา 3 sliders เสีย 5 คลิก)
  - เพิ่มตัวเลือก `สไตล์ฮุก` (Quick Hook Preset Dropdown) ใน Toolbar: มี 8 สไตล์ให้เลือกสลับทันที (Tech, Cute, Bold Pop, Plain, Clean, Flash Sale, Neon, Luxury) คลิกเลือกแล้วอัปเดตสไตล์บนคลิปทันที ไม่ต้องเปิดแถบ Inspector
- **Gates:**
  - `npm test` ใน frontend ผ่าน 85/85 tests
  - `npm run build` ผ่านใน 4.39 วินาที
  - `python -m compileall -q scripts` ผ่าน
  - `pytest tests/test_preview_render_parity.py` ผ่าน 149/149 tests
  - ทดสอบจริงบนเบราว์เซอร์ผ่าน `browser_subagent` บันทึกวิดีโอ `verify_fix_editor_ux_1788799770233.webp`

## Round RAW-1 — แก้เปลี่ยนชื่อคลิปดิบและจัดเลย์เอาต์ Raw Vault

วันที่: 2026-09-07 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**ผลลัพธ์:**

1. ถอดตัวเล่น preview ออกจากคลิปที่กำลังจะเปลี่ยนชื่อ และถอดซ้ำก่อนส่งคำขอ เพื่อคืน file handle ให้ Windows
2. เพิ่ม retry สำหรับ `WinError 32` และตอบ `409` พร้อมข้อความให้ปิด preview เมื่อ lock ยังอยู่
3. เปลี่ยนกลุ่มสินค้าเป็น responsive grid (เดสก์ท็อป 2–3 คอลัมน์, จอเล็ก 1 คอลัมน์) และให้ชั้นคลิปอิสระเต็มความกว้าง ลดพื้นที่ว่างจากกลุ่มที่มีคลิปน้อย
4. รักษา flow อัปโหลด, ผูกสินค้า, ลบ, เลือก, preview, ค้นหา และการ์ดเดิมทั้งหมด

### Gate

- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 896 passed
- [x] `python -m compileall -q scripts/api_videos.py`
- [x] `npm test` — 85 passed
- [x] `npm run build`
- [x] Impeccable layout detector — ไม่พบ findings

### Notes

- เพิ่ม `tests/test_api_videos_rename.py` ครอบคลุม retry lock และการตอบ conflict เมื่อ lock ค้าง

## Round POST-3.27 — ลดความซ้ำซ้อนปุ่มเปิด TikTok Studio ให้เหลือจุดเดียวใน Header

วันที่: 2026-09-07 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**หลักฐานและคำสั่ง:** User แจ้งว่า "ซ้ำซ้อนมากมีหลายจุดมา ขอจุดเดียวพอครับ" พร้อมภาพถ่ายหน้าจอที่ชี้ให้เห็นปุ่มเปิด TikTok 3 จุดพร้อมกัน (Header, Tab 1 quick bar, Tab 2 launcher banner)

**ผลลัพธ์:**

1. รวมเหลือจุดเดียวใน **Header bar** (`#headerOpenTikTokBtn` "เปิด TikTok Studio") สไตล์ Cyber-Studio Pill พร้อมไอคอน External Link สะอาดตา มองเห็นและเข้าถึงได้ตลอดเวลาไม่ว่าจะอยู่แท็บใด
2. นำปุ่ม `#listOpenTikTokBtn` ออกจาก Tab 1 คืนค่าปุ่ม `#refreshBtn` เป็นปุ่มเต็มกว้าง (`.btn-refresh-full`) เรียบหรู ไม่เกะกะรายการคลิป
3. นำ `.tiktok-launcher-banner` และ `#openTikTokBtn` ออกจาก Tab 2 ให้เข้าสู่แผงคำสั่งหลักโดยตรง
4. ทำความสะอาด event listeners ใน `sidepanel.js` และ CSS selectors ที่ไม่ใช้งาน
5. อัปเดต assertion ใน `background.test.cjs` ยืนยันการมีอยู่เฉพาะปุ่ม Header ใน sidepanel และ Popup ใน popup window พร้อมตรวจจับว่าไม่มีปุ่มซ้ำซ้อน

### Todo

- [x] ปรับ `sidepanel.html`: เอา `#listOpenTikTokBtn` ใน Tab 1 ออก และคืนค่า `#refreshBtn` ให้สะอาดตา
- [x] ปรับ `sidepanel.html`: เอา `.tiktok-launcher-banner` และ `#openTikTokBtn` ใน Tab 2 ออก
- [x] เก็บกวาด CSS ที่เกี่ยวข้องใน `sidepanel.html`
- [x] ปรับ `sidepanel.js`: เอา listeners ของปุ่มที่ลบออก คงไว้เฉพาะ `#headerOpenTikTokBtn`
- [x] อัปเดต contract test ใน `background.test.cjs`
- [x] รัน Gate ตรวจสอบ (`node --check`, `node --test`) และถ่ายภาพ snapshot ตรวจความเรียบร้อย

### Gate

- [x] `node --check tiktok_autopost_extension/sidepanel.js` (ผ่าน)
- [x] `node --test tiktok_autopost_extension/background.test.cjs` (ผ่านครบ 13/13 tests)
- [x] ตรวจภาพ Sidepanel UI ทั้ง Tab 1 และ Tab 2 ไม่เหลือปุ่มซ้ำซ้อน ยืนยันผ่าน browser snapshot

## Round POST-3.26 — เพิ่มปุ่มเปิด/สลับแท็บอัปโหลด TikTok Studio ใน Extension

วันที่: 2026-09-07 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** เพิ่มปุ่มเปิด/สลับแท็บอัปโหลด TikTok Studio (`https://www.tiktok.com/tiktokstudio/upload`) ที่เด่นชัดและกดใช้งานได้ทันทีใน Chrome Extension:

- มีปุ่ม Quick Launch ที่หัวตาราง Tab 1 (รายการคลิป) เคียงข้างปุ่มรีเฟรช ให้ผู้ใช้เปิดแท็บ TikTok Studio ได้ทันทีตั้งแต่เปิด Extension
- มีปุ่มเปิดหน้าอัปโหลดที่ชัดเจนใน Tab 2 (ขั้นตอนโพสต์) และ Header
- เพิ่มปุ่มใน `popup.html` ด้วย
- ปรับปรุงฟังก์ชัน `openTikTokUploadTab()` ให้ตรวจจับทั้ง `tiktokstudio/upload`, `creator-center/upload` และ `tiktokstudio` ถ้ามีเปิดอยู่แล้วให้ switch tab + focus window ทันที ถ้ายังไม่มีให้เปิดแท็บใหม่
- ปฏิบัติตามกฎ UI Clean Standard (ไม่มี emoji หรือ symbol ซ้ำซ้อน, ใช้ clean SVG) และไม่แตะขั้นตอน automation

### Todo

- [x] เพิ่มปุ่ม Quick Launch "เปิดหน้าอัปโหลด TikTok" ใน Tab 1 (`#panelList`) ใน `sidepanel.html`
- [x] ปรับปรุงการแสดงผลปุ่มเปิด TikTok ใน Header (`#headerOpenTikTokBtn`) และ Tab 2 (`#openTikTokBtn`) ให้เด่นชัดและใช้งานง่าย
- [x] ปรับปรุงฟังก์ชัน `openTikTokUploadTab()` ใน `sidepanel.js` ให้ค้นหาแท็บ TikTok ได้รอบด้าน (ทุก pattern) และสลับแท็บพร้อม focus window หรือเปิดใหม่หากยังไม่มี
- [x] เพิ่มปุ่มเปิด TikTok Studio ใน `popup.html` และเชื่อมต่อกับ `openTikTokUploadTab()` ใน `popup.js`
- [x] ทดสอบ syntax (`node --check`) และรัน test suite `background.test.cjs`

### Gate

- [x] `node --check tiktok_autopost_extension/sidepanel.js` (ผ่าน)
- [x] `node --check tiktok_autopost_extension/popup.js` (ผ่าน)
- [x] `node --test tiktok_autopost_extension/background.test.cjs` (13/13 ผ่าน)
- [x] UI ทดสอบแสดงผลปุ่มเปิดแท็บชัดเจน สวยงามตาม Cyber-Studio Dark ทั้งใน Tab 1, Tab 2, Header และ Popup

### Notes

- รักษากฎ `ui_clean_standard.md` ไม่ใส่ emoji หรือเครื่องหมายซ้ำซ้อน
- ไม่กระทบ logic automation 1-6

## Round POST-3.25 — Redesign Extension UX/UI (Cyber-Studio Dark & Stepper Timeline)

Date: 2026-09-07; Requested by: user; Status: complete

**Goal:** ปรับโฉม UX/UI ของ Chrome Extension (`sidepanel.html`, `sidepanel.js`, `popup.html`) สู่ระดับ Cyber-Studio Dark Glassmorphism, ลบ Emoji รกตาและใช้ Clean SVG Icons ทั้งหมดตามกฎ `ui_clean_standard.md`, ปรับ Checklist เป็น Interactive Stepper Timeline พร้อมฝังฟอนต์ `IBM Plex Sans Thai` โดยไม่แตะต้อง Logic และขั้นตอนการทำงานเดิม 100%

### Todo

- [x] ออกแบบ Design System ใน `sidepanel.html`: โทน Cyber-Studio Dark (`#070a11`, `#121828`, `#22d3ee`, `#34d399`, `#f43f5e`), backdrop blur, crisp micro-borders
- [x] ฝังฟอนต์ `IBM Plex Sans Thai` (Medium & Bold) เข้า `fonts/` โหลดผ่าน `@font-face`
- [x] เปลี่ยน Emoji ทั้งหมดในหัวข้อ, แท็บ, ปุ่ม, ป้าย, และสถานะ เป็น Clean inline SVG Icons (Lucide-style) ตามกฎ `ui_clean_standard.md`
- [x] พัฒนา Active Clip Studio Monitor: รวม 3:4 Preview Monitor, live aspect ratio badge, hook title, product badge, และเวลาโพสต์
- [x] ปรับโฉม Checklist 1-6 ให้เป็น Stepper Pipeline Command Center: เส้นเชื่อม vertical stepper, glowing node rings, badge แสดงสถานะ, hover/active tactile micro-interactions, แยก Danger style ให้ Step 6 เด่นชัด พร้อมหลอดนีออนความคืบหน้าเรียลไทม์
- [x] ปรับปรุง Section Cards, Input Textareas, Copy button, Schedule date/time selector และ Status notification ให้โมเดิร์น สบายตา
- [x] ตรวจสอบว่า DOM IDs, classes สำคัญ, และ String patterns ที่ `background.test.cjs` ตรวจสอบยังคงอยู่ครบถ้วน 100%
- [x] ปรับ `popup.html` ให้มีสไตล์ Cyber-Studio Dark สอดคล้องกัน

### Gate

- [x] `node --check tiktok_autopost_extension/sidepanel.js` และ `popup.js` — passed
- [x] `node --test tiktok_autopost_extension/background.test.cjs` — 12/12 passed
- [x] `python -m pytest tests/test_api_tiktok_autopost.py` — 11 passed
- [x] เปิดดู UI จริงผ่าน Browser ตรวจสอบความสวยงาม การแสดงผล ไม่มี overflow, responsive บน side panel width, และ contrast ratio

## Round POST-3.24 - indicate cover status in daily queue

Date: 2026-09-07; Requested by: user; Status: complete

**Goal:** Make the daily queue answer at a glance whether each scheduled clip already has a saved cover.

**Scope:** Reuse cover metadata from the queue item and its ready export; show the existing Cover Studio image action in a bright semantic state when a cover exists and a subdued state when it does not; preserve the preview, schedule controls, Extension handoff, and steps 1-5.

### Todo

- [x] Resolve cover presence from URL/path fields for the queue item and matched clip, including 3:4 and 9:16 variants.
- [x] Use a bright cover icon with a clear tooltip/accessible label for saved covers.
- [x] Use a subdued cover icon with a create-cover tooltip when no saved cover exists.
- [x] Keep the icon clickable for the existing Cover Studio flow whenever the ready clip is available.
- [x] Use the resolved cover for the row thumbnail so saved covers remain visible after queue refresh.

### Gate

- [x] `npm test` — 83 passed.
- [x] `npm run build` — passed.
- [x] `git diff --check` — passed.
- [x] Impeccable detector — completed; remaining warnings are existing file-wide color-pattern findings outside this narrow state change.
- [x] Browser smoke — live Agenda rendered two saved-cover rows with `data-cover-state="ready"`, bright icon styling, and the accessible label `มีภาพปกแล้ว คลิกเพื่อแก้ไข`.

### Notes

- The missing-cover branch is intentionally dark and keeps the title/ARIA text `ยังไม่มีภาพปก คลิกเพื่อสร้าง`.
- No backend, queue identity, schedule timestamp, Extension step, or frozen posting step was changed.
- Unrelated editor files and local schedule JSON artifacts remained unstaged.

## Round POST-3.23 - reduce default publishing slots to three

Date: 2026-09-07; Requested by: user; Status: complete (browser gate deferred)

**Goal:** Reduce the default weekly publishing schedule to three practical TikTok windows: 12:30, 19:00, and 21:30.

**Scope:** Update the frontend template editor and backend schedule defaults; migrate templates saved with the previous five-slot defaults; keep custom three-slot weekly overrides, queue records, Extension handoff, cover flow, and steps 1-4 unchanged.

### Todo

- [x] Change the shared frontend default slots to 12:30, 19:00, 21:30.
- [x] Change the backend default slots and validation to three unique five-minute slots.
- [x] Migrate legacy five-slot templates to the new three-slot defaults on read/save.
- [x] Resize the weekly template editor grid and helper text for three columns.
- [x] Add frontend and backend regression coverage for the new defaults and migration.
- [x] Run the full backend/frontend gates and inspect the isolated diff.

### Gate

- [x] `python -m pytest tests/test_schedule_queue.py -q -p no:cacheprovider --tb=short` — 9 passed.
- [x] `node --test frontend/src/lib/scheduleQueue.test.js` — 3 passed.
- [x] `python -m compileall -q scripts` — passed.
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 891 passed, 6 existing warnings.
- [x] `npm test` — 83 passed.
- [x] `npm run build` — passed.
- [ ] Browser verification — deferred; no browser runtime gate was available in this round.

### Notes

- Existing queue timestamps are untouched; only the reusable template defaults change.
- A saved five-slot legacy template is readable and normalised to the three new defaults instead of causing a validation failure.
- Custom weekly templates may still use three distinct times, so a later week can override the defaults without changing existing queue items.
- Unrelated editor and pipeline changes already present in the working tree were left unstaged.

## Round POST-3.22 - weekly schedule templates and product-rotating auto-fill

Date: 2026-09-07; Requested by: user; Status: complete (browser gate deferred; browser runtime was unavailable after automated smoke finalization)

**Goal:** Add reusable weekly time templates and an explicit auto-fill flow that appends ready clips to the durable multi-day queue while rotating products fairly.

**Scope:** Persist Monday-Sunday templates in the backend; support per-week overrides, enabled days, five primary times per day, previewed auto-fill for today/this week/custom ranges, product rotation, random clip selection, overdue reuse, and append-after-latest semantics. Keep existing queue records, Extension handoff, cover flow, steps 1-4, and editor work unchanged.

### Todo

- [x] Add backend template storage/API with default and week-specific Monday-Sunday schedules.
- [x] Add Agenda controls for weekly template editing, copying, resetting, enabled days, and saved week selection.
- [x] Add auto-fill preview for today, this week, or custom date range with optional clip limit and product filter.
- [x] Implement append-after-latest scheduling, skip past slots, preserve existing queue, and show empty-slot reasons.
- [x] Implement random product order with no adjacent product repeat across day boundaries and random clip choice within each product.
- [x] Mark overdue unposted rows and provide a reviewable requeue flow without duplicating MP4 identities.
- [x] Add deterministic tests for template persistence, week boundaries, append cursor, fairness, limits, overdue reuse, and collisions.
- [x] Run backend/frontend tests, build, syntax checks; browser verification deferred because the runtime was unavailable.

### Gate

- [x] Backend schedule template/auto-fill tests pass.
- [x] Frontend tests pass.
- [x] `npm run build` passes.
- [ ] Browser verification: deferred; browser runtime was unavailable after automated smoke finalization.

### Notes

- `pytest tests/ -q`: 879 passed, 6 warnings; `npm test`: 83 passed; `npm run build` and `python -m compileall -q scripts` passed.
- Browser UI gate was not rerun in this environment because the prior browser runtime had already finalized; API and component behavior are covered by deterministic tests/build.

- Week means Monday-Sunday in `Asia/Bangkok`; changing a template never mutates existing queue timestamps.
- Auto-fill uses only ready, unqueued, unposted exports, preserves the one-MP4-once rule, and requires explicit confirmation after preview.
- If a selected range has no future primary slot, the preview continues after the latest queue item into the next enabled day.
- Existing editor files remain another workstream and must not be modified or staged.

---

## Round TRK-3 — บอร์ดหลักคลีนไร้ความรก (Today-Only Posted, คลังสคริปต์หยิบทำวันนี้ & การ์ดตัดต่อเสร็จแนวนอนกะทัดรัด)

วันที่: 2026-09-06 · สั่งโดย: user (ผ่าน /grill-me) · สถานะ: เสร็จสิ้น

**เป้าหมาย:** แก้ปัญหาบอร์ดหลักยืดยาวและรกเมื่อมีคลิปและสคริปต์สะสม 20-30+ รายการ ตามมติการสัมภาษณ์ `/grill-me` (3 ข้อ):

1. คอลัมน์ "โพสต์แล้ว (Posted)": แสดงเฉพาะคลิปที่โพสต์วันนี้ (Today Only) เพื่อไม่ให้รกบอร์ด ส่วนคลิปเก่าในอดีตย้ายเข้าคลังประวัติอัตโนมัติ พร้อมปุ่มเปิดดูคลังประวัติ (Archive Modal)
2. คอลัมน์ "สคริปต์พร้อม (Scripted)": คลังสคริปต์ (Script Library Modal) เก็บไว้ด้านหลัง บนบอร์ดหลักแสดงเฉพาะ 3-5 สคริปต์ที่เราหยิบมาทำวันนี้ พร้อมปุ่มหยิบเข้า/ปลดออก
3. คอลัมน์ "ตัดต่อเสร็จ / ตรวจ QC (Rendered)": ปรับการ์ดเป็นการ์ดแนวนอนกะทัดรัด (Compact Horizontal Card สูง ~95px) ซ้ายเป็นมินิพรีวิว 9:16 ขวาเป็นชื่อสินค้า + QC ผ่าน + Hook 1 บรรทัด + แถบปุ่มแอ็กชันครบครัน (`ส่ง TikTok`, `มือถือ`, `QC`, `ตัดใหม่`)

**สิ่งที่แก้ไข:**

1. **TRK-3.1 คอลัมน์โพสต์แล้ว: Today-Only + Archive Modal**:
   - กรองรายการคลิปในคอลัมน์ `posted` ให้แสดงเฉพาะคลิปที่มี `posted_at` หรือ `updated_at` เป็นวันปัจจุบัน (Local Time `YYYY-MM-DD`)
   - คลิปที่โพสต์ก่อนหน้านี้ย้ายเข้าคลังประวัติอัตโนมัติ ไม่เปลืองพื้นที่บนบอร์ด
   - มีปุ่ม `[คลัง (N)]` บนหัวคอลัมน์ และปุ่ม `[คลังประวัติคลิปเก่า (N คลิป)]` เพื่อเปิดดู Modal ประวัติคลิปทั้งหมดในอดีต (ค้นหาได้, ดูพรีวิววิดีโอ, ก๊อปปี้แคปชัน, ส่ง TikTok ซ้ำได้)
   - อัปเดต `scripts/product_store.py` ให้บันทึกฟิลด์ `posted_at` เมื่อย้ายสถานะเป็น `posted`
2. **TRK-3.2 คอลัมน์สคริปต์พร้อม: คลังสคริปต์ (Script Library) + สคริปต์หยิบทำวันนี้**:
   - เพิ่ม State `pickedScriptIds` เก็บลง `localStorage` บันทึกสคริปต์ที่เลือกมาทำประจำวัน
   - คอลัมน์บนบอร์ดหลักแสดงเฉพาะสคริปต์ที่หยิบมาทำวันนี้ ทำให้บอร์ดไม่ยาวเฟื้อย
   - เพิ่มปุ่ม `[คลัง (N)]` บนหัวคอลัมน์ เปิด `ScriptLibraryModal` คลังสคริปต์ทั้งหมดเพื่อกดเลือก `[หยิบมาทำวันนี้]` หรือ `[อยู่ในคิววันนี้]` มีปุ่มลัด `[เลือก 4 รายการแรก]` และ `[ล้างคิว]`
   - การ์ดสคริปต์บนบอร์ดมีปุ่ม `[X]` ปลดออกจากคิววันนี้ส่งกลับเข้าคลังได้ทันที
3. **TRK-3.3 คอลัมน์ตัดต่อเสร็จ / ตรวจ QC: การ์ดแนวนอนกะทัดรัด (Compact Horizontal Card ~95px)**:
   - ปรับความสูงการ์ดจาก ~350px ลงเหลือเพียง ~95px
   - ด้านซ้าย: มินิพรีวิววิดีโอ 9:16 (52px) พร้อมปุ่ม Play เปิดดูตัวอย่าง
   - ด้านขวา: ชื่อสินค้า + ป้ายสถานะ `QC ผ่าน` + Hook 1 บรรทัด + แถบปุ่มคำสั่งแถวเดียว (`[ส่ง TikTok]`, `[มือถือ]`, `[QC]`, `[ตัดใหม่]`, `[โพสต์แล้ว]`)
   - สามารถจุคลิปตัดเสร็จได้ 5-10 คลิปในหน้าจอเดียวโดยไม่ต้องเลื่อนสกอร์ยาว
4. **ผลการทดสอบ (Gate)**:
   - `python -m compileall -q scripts` ผ่าน 100%
   - `pytest tests/ -q` ผ่าน 373/373 tests (7 warnings เก่า)
   - `npm run build` ผ่าน 100% ใน 4.06s
   - `npm test` ผ่าน 54/54 tests
   - ทดสอบจริงบนเบราว์เซอร์ผ่าน browser subagent และบันทึกภาพหน้าจอเรียบร้อย
   - ปฏิบัติตามกฎ `ui_clean_standard.md` ไม่มีสัญลักษณ์ซ้ำซ้อน

---

## Round TRK-2 — ตารางจัดคิวโพสต์ประจำวัน (Daily Run Sheet) & จัดกลุ่มย่อการ์ด (Product Grouping / Quick Pills)

วันที่: 2026-09-06 · สั่งโดย: user (ผ่าน /grill-me + /scrutinize) · สถานะ: เสร็จสิ้น

**เป้าหมาย:** แก้ปัญหาการ์ดล้นจอเมื่อมีสคริปต์จำนวนมาก และรองรับ workflow โพสต์คลิปวันละ 3-5 คลิปแบบสลับสินค้าตามช่วงเวลา (เช้า A / เที่ยง B / เย็น C / ดึก D) โดยเพิ่มมุมมอง "คิวโพสต์ประจำวัน (Daily Run Sheet)" พร้อมระบบจัดคิวและสลับสินค้าอัตโนมัติ, ตั้งเวลาโพสต์ (Schedule Time), แถบ Quick Product Pills เลือกสินค้าเร็ว, Accordion Grouping ย่อการ์ดในบอร์ด 5 เฟส, และตัวกรองซ่อนคลิปที่โพสต์ไปแล้วเกิน 24 ชม.

**สิ่งที่แก้ไข:**

1. **TRK-2.1 แถบปุ่มลัดเลือกสินค้า (Quick Product Pills) & Accordion Grouping ในบอร์ด 5 เฟส**:
   - เพิ่มแถบ Pills สินค้าใต้ Search bar: `[สินค้าทั้งหมด]` `[Logitech Wave Keys]` `[ESSAGER]`... สลับกรองสินค้าได้ในคลิกเดียว ไม่ต้องเลื่อนหาใน Dropdown
   - เพิ่มโหมด Accordion Group by Product ในคอลัมน์ "สคริปต์พร้อม": พับ/กางตามชื่อสินค้าได้ ช่วยลดความยาวการ์ดจาก 20-30 ใบเหลือไม่กี่แถว
   - เพิ่มระบบ Truncate ในคอลัมน์ "โพสต์แล้ว": ซ่อนคลิปที่โพสต์แล้วเมื่อมีเกิน 3 รายการ พร้อมปุ่ม "+ ดูคลิปเก่าทั้งหมด"

2. **TRK-2.2 แท็บมุมมองใหม่ "คิวโพสต์ประจำวัน (Daily Run Sheet)"**:
   - เพิ่มปุ่มสลับมุมมองที่ Header: `[บอร์ด 5 เฟส]` | `[คิวประจำวัน]` | `[ตารางข้อมูล]`
   - โครงสร้าง 4 สล็อตมาตรฐานประจำวัน (เช้า 08:30 / เที่ยง 12:30 / เย็น 18:00 / ดึก 21:30) สามารถปรับตั้งเวลาได้อิสระ
   - ปุ่ม `[เพิ่มรอบพิเศษ]` รองรับคลิปที่ 5 ของวัน
   - เซฟสถานะคิวลง `localStorage` ตามวันที่อัตโนมัติ

3. **TRK-2.3 อัลกอริทึม "จัดคิวสลับสินค้าอัตโนมัติ (Auto-Rotate Products)"**:
   - ปุ่ม `[จัดคิวสลับสินค้าอัตโนมัติ]`: ดึงคลิปที่ตัดเสร็จมากระจายลง 4 สล็อตแบบ Round-Robin ไม่ให้สินค้าซ้ำกันติดๆ กัน
   - รองรับการคลิก `[สลับคลิป]` หรือ `[เลือกคลิปที่ตัดเสร็จ]` ด้วย Modal แสดงคลิปทั้งหมดให้เลือกหยอดลงสล็อต

4. **TRK-2.4 การส่งโพสต์และปักตะกร้าตรงจากสล็อตพร้อม Schedule Time**:
   - รองรับการระบุเวลา Schedule Time ทั้งใน Daily Run Sheet และ TikTok Modal
   - อัปเดต `scripts/api_tiktok_autopost.py` และ `frontend/src/api.js` และ `popup.js` รองรับ `schedule_time`
   - เพิ่ม unit test `tests/test_api_tiktok_autopost.py`

5. **ผลการทดสอบ (Gate)**:
   - `npm run build` ผ่าน 100%
   - `npm test` ผ่าน 54/54 tests
   - `python -m compileall -q scripts` ผ่าน 100%
   - `pytest tests/ -q` ผ่าน 373 passed (7 warnings)

---

## Round TRK-1 — เพิ่มปุ่มส่งคลิปไป TikTok Studio พร้อม Modal ตรวจสอบ/ปักตะกร้า ในหน้า Tracker (ContentTrackerHub)

วันที่: 2026-09-06 · สั่งโดย: user (ผ่าน /grill-me) · สถานะ: เสร็จสิ้น

**เป้าหมาย:** ในหน้า Tracker (`ContentTrackerHub.jsx`) เพิ่มปุ่ม "ส่ง TikTok" บนการ์ดในเฟส 3 "ตัดต่อเสร็จ / ตรวจ QC" คู่กับปุ่ม "ส่งมือถือ" พร้อมหน้าต่าง Modal สำหรับพรีวิวคลิป ตรวจทาน/แก้ไขแคปชั่น, แฮชแท็ก, และ TikTok Product ID ก่อนส่งข้อมูลไปยัง Extension และเปิด TikTok Studio

**สิ่งที่แก้ไข:**

1. **TRK-1.1 ปรับเลย์เอาต์การ์ด Kanban ในเฟส `rendered` (ตัดต่อเสร็จ) และ `mobile_ready`**:
   - ปรับเลย์เอาต์การ์ด Kanban ในเฟส `rendered` เป็น 2 แถวสมดุล สวยงาม สะอาดตา:
     - แถวบน (Publishing channels):
       - ปุ่ม `[ส่ง TikTok]` (ไล่เฉด TikTok `#FE2C55` / `#25F4EE`) พร้อมไอคอน `<Rocket />` สำหรับเปิด Modal เตรียมโพสต์
       - ปุ่ม `[ส่งมือถือ]` (สีม่วง) พร้อมไอคอน `<Smartphone />` สำหรับเปิด QR Code
     - แถวล่าง (QC & Editing tools):
       - ปุ่ม `[ตรวจ QC]` สำหรับเปิดดูพรีวิววิดีโอ
       - ปุ่ม `[ตัดใหม่]` สำหรับส่งกลับไปตัดต่อใหม่
     - แถบยืนยัน: ปุ่ม `[มาร์กว่าโพสต์แล้ว]` ย้ายลงมาเป็นปุ่มยืนยันปิดงาน
   - เพิ่มปุ่ม `[ส่ง TikTok]` ในเฟส `mobile_ready`, ตาราง Mobile/Desktop View ด้วย

2. **TRK-1.2 สร้าง Modal "เตรียมโพสต์ TikTok Studio (พร้อมปักตะกร้า)"**:
   - เพิ่มหน้าต่าง Modal แบบ Interactive รองรับ:
     - พรีวิวคลิปวิดีโอ 9:16 แบบฝังในหน้าต่าง พร้อมตัวเล่นวิดีโอ
     - ช่องแก้ไข "คำอธิบายคลิป (Caption)" ดึงค่าอัตโนมัติจาก angle
     - ช่องแก้ไข "แฮชแท็ก (Hashtags)" ดึงค่าอัตโนมัติจาก angle
     - ช่องแก้ไข "รหัสสินค้าปักตะกร้า (TikTok Product ID / Search Keyword)" ดึงค่าจาก parent product หรือใช้ชื่อสินค้าเป็น fallback
     - สรุป Checklist ความพร้อม: วิดีโอพร้อมอัปโหลด, แคปชั่น & แฮชแท็ก, และสถานะการปักตะกร้า
     - ปุ่ม Action: `[ส่งข้อมูลเข้า Extension & เปิด TikTok Studio]` ทำการบันทึกข้อมูลเข้า extension ผ่าน `prepareTiktokAutopost` และเปิดหน้า TikTok Studio upload ทันที
     - ปุ่มยืนยัน `[มาร์กว่าโพสต์แล้ว]` เพื่ออัปเดตสถานะเป็น `posted` เมื่อยืนยันว่าโพสต์บน TikTok สำเร็จ

3. **TRK-1.3 เพิ่มปุ่มส่ง TikTok ใน Inspect Modal (Deep-Dive Modal)**:
   - เพิ่มปุ่ม `[ส่ง TikTok]` ในแถบ Action Toolbar ด้านบนของ Inspect Modal ให้สามารถคลิกส่งโพสต์ได้โดยตรงจากหน้าต่างดูรายละเอียดเชิงลึก

4. **ผลการทดสอบ (Gate)**:
   - `npm run build` ผ่าน 100% (0 error)
   - `npm test` ผ่าน 54/54 tests
   - `python -m compileall -q scripts` ผ่าน 100%
   - `pytest tests/ -q` ผ่าน 372 passed (7 warnings)

---

## Round PROD-1 — เพิ่มช่องระบุ TikTok Product ID ตอนสร้างสคริปต์ใหม่ + Fallback ค้นหาด้วยชื่อสินค้า + Click-to-Edit Cart ID

วันที่: 2026-09-06 · สั่งโดย: user · สถานะ: เสร็จสิ้น

**เป้าหมาย:** ในหน้าต่างโมดอลสร้างสินค้า/สคริปต์ใหม่ (`ProductToClip.jsx`) เพิ่มช่องให้ระบุ "ไอดีสินค้า (TikTok Product ID)" สำหรับปักตะกร้า เพื่อให้ระบบบันทึกและส่งต่อไปยังขั้นตอนปักตะกร้าสินค้าอัตโนมัติ โดยใช้ไอดีเป็นหลัก หากไม่ระบุให้สำรองเป็นชื่อสินค้าเพื่อค้นหาให้ตรงที่สุด พร้อมรองรับการแก้ไข/ใส่ไอดีหรือลิงก์แชร์ย้อนหลังได้จาก Header สินค้าปัจจุบัน และมีผลกับทุกสคริปต์ในชุดนั้นทันที

**สิ่งที่แก้ไข:**

1. **PROD-1.1 Frontend Modal (`ProductToClip.jsx`)**:
   - เพิ่ม state `tiktokProductId` ใน `ProductToClip.jsx`
   - เพิ่มช่อง Input: "ไอดีสินค้าสำหรับปักตะกร้า (TikTok Product ID):" วางในโมดอลสร้างสินค้า/สคริปต์ใหม่ รองรับทุกโหมด พร้อมระบบตรวจจับและดึง ID จาก URL อัตโนมัติ
   - ส่ง `tiktok_product_id` ไปกับ payload ของ `scrapeAndPlanProduct` และ `scrapeAndPlanProductAsync`
   - ล้างค่าเมื่อส่งหรือปิดโมดอล

2. **PROD-1.2 Backend API & Store (`api_products.py` & `product_store.py`)**:
   - ใน `scrape_and_plan` และ `_execute_scrape_and_plan_worker`: รับ `tiktok_product_id` จาก payload
   - อัปเดต `ProductStore.add(...)` ให้รองรับ parameter `tiktok_product_id` และบันทึกลงในสินค้า
   - เพิ่ม endpoint `POST /api/products/resolve-tiktok-id` และฟังก์ชัน `resolve_tiktok_product_id` รองรับการแกะ ID จาก URL หรือแกะ redirect ของ shortlink (`vt.tiktok.com`)

3. **PROD-1.3 Fallback logic: ไอดีก่อนเป็นหลัก สำรองเป็นชื่อสินค้า**:
   - ใน `scripts/api_exports.py`: ให้ `info["tiktok_product_id"] = matched_prod.get("tiktok_product_id") or matched_prod.get("name", "")`
   - ใน `frontend/src/components/ContentTrackerHub.jsx`: อนุญาตให้ปุ่มเตรียมปักตะกร้าทำงานได้แม้ไม่มีตัวเลข ID โดยใช้ชื่อสินค้าเป็น fallback

4. **PROD-1.4 Click-to-Edit Cart ID ย้อนหลัง & Auto-resolve Shortlinks**:
   - ใน `ProductToClip.jsx`: ปรับ Badge ตะกร้าที่หัวสินค้า `[ID: ...]` / `[ปักตะกร้าด้วยชื่อ]` ให้ใช้ไอคอน Lucide `<ShoppingBag />` (ตาม Clean UI) และสามารถคลิกเพื่อเปิด Modal แก้ไข/ใส่ไอดีสินค้าภายหลังได้
   - Modal แก้ไขไอดีสินค้า: ระบุชัดเจนว่าไอดีนี้จะแนบกับทุกสคริปต์ในชุดนี้ ({angles.length} สคริปต์) รองรับการกรอกเลขตรงๆ หรือวางลิงก์แชร์ (`vt.tiktok.com`) พร้อม auto-resolve และปุ่มล้างค่า
   - ในฟอร์มสร้างสินค้าใหม่: รองรับการวางลิงก์แชร์ลงในช่อง TikTok Product ID หรือช่องลิงก์สินค้า แล้ว auto-resolve ผ่าน `resolveTiktokProductId`

**ผลการทดสอบ (Gate):**

- `npm run build` ผ่าน (3.26s)
- `npm test` ผ่าน 54 tests (0 failures)
- `python -m compileall -q scripts` ผ่าน
- `pytest tests/ -q` ผ่าน 372 passed (7 warnings)

---

## Round BUG-3 — angle ชนกัน (คลิปผิดสคริปต์) ใน Content Tracker Hub + ปุ่มปักตะกร้า TikTok

วันที่: 2026-09-06 · สั่งโดย: user (แนบภาพหน้า Content Tracker Hub) · สถานะ: เสร็จสิ้น

**เป้าหมาย:** ปิดช่องโหว่ที่ 2 angle คนละสคริปต์ชี้ไปคลิปเดียวกันได้ (ข้อมูลจริงพัง ณ ตอนนั้น),
ปิดช่องโหว่ที่ลบคลิปจาก gallery แล้ว Tracker ไม่รู้ตัว, และเพิ่มปุ่มส่ง TikTok ปักตะกร้าตรงจากหน้านี้

**สืบสวนแล้ว (/scrutinize, ยืนยันด้วยข้อมูลจริงใน `_Docs/products.json` ไม่ใช่เดา):**

- ContentTrackerHub ทั้ง 3 จุดที่โชว์วิดีโอ (kanban card, compact card, inspect modal) อ่าน `ang.video_url`
  ตรงๆ ไม่มี matching logic ฝั่ง frontend เลย → บั๊กร้อยเปอร์เซ็นต์อยู่ backend/data
- **หลักฐานจริง:** `pain_point` กับ `unboxing` (Logitech Wave Keys) มี `project_name` + `video_url` **ตรงกันเป๊ะ**
  ทั้งที่ `unboxing` ไม่มีโฟลเดอร์ของตัวเองใน `03_Projects/` เลย — วิดีโอที่ unboxing โชว์คือของ pain_point จริง
- **ต้นตอ:** `reconcile_existing_projects()` วนลูป angle ทุกตัวต่อ 1 โฟลเดอร์โปรเจกต์ **ไม่มี `break`** —
  ถ้า 2 angle เข้าเงื่อนไข `angle.project_name == p_folder.name` (self-referential) พร้อมกัน จะได้ `video_url`
  เดียวกันทั้งคู่ ทุกรอบ reconcile ยืนยันซ้ำบั๊กเดิมเอง (self-perpetuating) — ต้นตอที่ผิดตั้งแต่แรกหาไม่ได้ 100%
  (ไม่มี log ประวัติ) แต่ไม่กระทบการแก้: ต้องปิดช่องโหว่ที่โครงสร้างไม่ว่าจะมาจากไหน
- `delete_file()` เรียก `rollback_by_video_or_project()` จริง แต่ทำงานเฉพาะ `status in ("rendered", "in_production")`
  — ถ้า angle ไปถึง `mobile_ready`/`posted` แล้ว ลบไฟล์ไม่ทำอะไรเลย

**ตัดสินใจ (grill กับ user 2026-09-06):** ชนกัน → auto-แก้ตัวที่แพ้กลับเป็น `scripted` + ขึ้นเตือนถาวรบนการ์ด
(ไม่ใช่ toast ที่พลาดดูได้) · แก้ข้อมูลจริงที่ชนอยู่ตอนนั้นทันที · rollback ใช้กับทุก status เหมือนกันหมด ·
เพิ่มช่องตั้งค่า `tiktok_product_id` ต่อสินค้าคู่กับปุ่มปักตะกร้า (เดิมมีแค่ ESSAGER ที่ตั้งด้วยมือใน products.json ตรงๆ)

**สิ่งที่แก้ไข:**

1. **BUG-3.1 — ปิดช่องโหว่ reconcile จับ 2 angle ชนกัน:**
   - `reconcile_existing_projects()` ([product_store.py:473+](scripts/product_store.py#L473)) แยก
     `authoritative_match` (เงื่อนไข #1: exact product_id+angle_id จาก manifest ของโปรเจกต์เอง — ชนะเสมอ)
     กับ `self_ref_matches` (เงื่อนไข #2: self-referential) ก่อนอัปเดตอะไร ผู้ชนะมีได้แค่ 1 ต่อ 1 โฟลเดอร์ต่อรอบ
     ทุก `self_ref_matches` ที่ไม่ใช่ผู้ชนะโดน unlink กลับเป็น `scripted` พร้อมเซ็ต `angle["data_conflict_note"]`
   - `ContentTrackerHub.jsx` เพิ่ม banner เหลือง (mirror `qc_note` banner) ทั้งใน `KanbanCard` และ inspect modal
     พร้อมปุ่ม "เข้าใจแล้ว" → `handleDismissConflict` เรียก `update_angle_status(..., clear_conflict_note=True)`
     (field ใหม่นี้เพิ่มเข้า `update_angle_status`/PATCH endpoint/`api.js` ครบ)
   - **รันซ่อมข้อมูลจริงแล้ว:** เรียก `reconcile_existing_projects()` เวอร์ชันใหม่กับ real `_Docs/products.json`
     (backup ไว้ที่ scratchpad ก่อน) — `unboxing` หลุดจาก `pain_point`'s folder กลับเป็น `scripted` +
     มี `data_conflict_note`, `pain_point` ไม่กระทบ — สแกนทั้งไฟล์ยืนยันไม่มี `video_url` ซ้ำที่ไหนอีกเลย
   - เทส `tests/test_reconcile_angle_collision.py` (2 เคส) — ไล่ตรรกะโค้ดเดิมด้วยมือยืนยันว่าทั้ง 2 เคส
     จะ fail ถ้าไม่มี fix นี้ — 2 passed

2. **BUG-3.2 — ลบคลิปจาก gallery ต้องเคลียร์ Tracker ด้วยทุกสถานะ:**
   - `rollback_by_video_or_project()` ([product_store.py:222](scripts/product_store.py#L222)) เอาเงื่อนไข
     `status in ("rendered", "in_production")` ออก ทำงานกับทุก status รวม `mobile_ready`/`posted`
   - เทส `tests/test_rollback_all_statuses.py` — parametrize 4 status × มี/ไม่มีโฟลเดอร์โปรเจกต์เหลืออยู่ — 6 passed

3. **BUG-3.3 — ปุ่มส่ง TikTok ปักตะกร้าใน Content Tracker Hub:**
   - เพิ่ม `tiktok_product_id` เข้า `ProductUpdateRequest` ([api_phase1.py:225](scripts/api_phase1.py#L225))
     — `ProductStore.update()` เดิมรับ kwarg ไม่รู้จักอยู่แล้ว ไม่ต้องแก้ store เพิ่ม
   - เพิ่มช่อง input `tiktok_product_id` ต่อสินค้า + ปุ่ม "บันทึก" + ปุ่ม "ส่ง TikTok ปักตะกร้า" ใน inspect modal
     ([:1014+](frontend/src/components/ContentTrackerHub.jsx#L1014)) — เรียก `prepareTiktokAutopost(...)`
     ตัวเดียวกับ ExportGallery ส่ง `product_id`/`angle_id`/`tiktok_product_id` จริง ปิดปุ่มถ้าไม่มี
     `tiktok_product_id` หรือยังไม่มี `video_url`
   - เทส `tests/test_bug3_tiktok_product_id_and_conflict_clear.py` — ยิงผ่าน `TestClient` จริง — 2 passed

**Gate:**

- `pytest tests/ -q -p no:cacheprovider` → 367 passed (รวมเทสใหม่ 10 เคส)
- `npx vite build` → ผ่าน · `python -m compileall -q scripts` → ผ่าน · routes = 84
- ข้อมูลจริง: `unboxing` ไม่ชนกับ `pain_point` อีกต่อไป — ยืนยันด้วยสคริปต์อ่าน `_Docs/products.json` จริงหลัง
  reconcile รันจริงแล้ว + สแกนทั้งไฟล์ไม่พบ `video_url` ซ้ำที่ไหนอีกเลย
- เช็คขนาน: ไฟล์ที่แก้ในรอบนี้ (`product_store.py`, `api_phase1.py`, `ContentTrackerHub.jsx`) ไม่ชนกับ
  POST-1/POST-2 ที่กำลังทำขนานอยู่เลย

---

## Round BUG-2 — แก้ข้อความและ Hook Header ซ้อนทับกันเป็นก้อนใน SequencePlayer

วันที่: 2026-09-05 · สั่งโดย: user (แนบรูปภาพบั๊กตัวอักษรซ้อนกัน) · สถานะ: เสร็จสิ้น

**สาเหตุรากเหง้า (Root Cause):**

1. `SequencePlayer.jsx` ยิงขอ `overlay.layout` ให้ Hook Header (`overlay.kind === 'hook'`) รวม 3 tiers เป็นสตริงเดียวด้วยขนาดฟอนต์ของ Brand
2. `lineWords && lineWords.length > 0` ทำงานแบบ unconditional แม้ `wordStaggerSec == 0` หรือเป็น Hook Header ทำให้บายพาสการวาด monolithic ปกติ
3. `word_layout.py` ใช้ `scaled_fs = font_size_px * ass_glyph_scale` ทำให้คำนวณตำแหน่ง `x` บีบแคบลง 37% (สำหรับ Kanit) แต่ฝั่ง Canvas วาดด้วยฟอนต์ 100% ตัวอักษรเลยชนและซ้อนทับกันเละ

**สิ่งที่แก้ไข:**

1. ใน `frontend/src/components/SequencePlayer.jsx`:
   - ป้องกัน Hook Header (`overlay.kind === 'hook'`) ไม่ให้ขอหรือใช้ `overlay.layout` โดยเด็ดขาด
   - สั่งล้าง `overlay.layout` เก่าทันทีถ้าเป็น Hook Header
   - กำหนด `isWordStagger = !isHook && wordStaggerSec > 0`
   - ให้ `lineWords` ทำงานเฉพาะเมื่อ `isWordStagger` เท่านั้น
   - กรณีปกติและ Hook Header ทั้งหมดวิ่งเข้า monolithic drawing (`drawTextWithMonoEmoji(ctx, w.line, lineX, lineY)`) ตัวอักษรและสระไทยทุกระดับเรียงตัวสวยงาม คมชัด 100% ไม่ชนกัน
2. ใน `tests/test_preview_render_parity.py`:
   - เพิ่ม contract test `test_hook_overlay_guarded_against_per_word_layout` เพื่อการันตีว่า Hook Header จะไม่ถูกแบ่งคำหรือขอ word layout อีกต่อไป

**Gate:**

- `python -m compileall -q scripts` → ผ่าน
- `python -c "import scripts.api_server as app; print(len(app.app.routes))"` → 84 routes
- `pytest tests/test_preview_render_parity.py -q` → 149 passed
- `pytest tests/ -q -p no:cacheprovider` → 356 passed
- `npm run build` (Vite) → built in 3.32s
- `node --test frontend/src/lib/*.test.js` → 6 passed

---

## Round 7 — template v2 + แกลเลอรีที่ขยับได้

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ

**เป้าหมาย:** ยกระดับเทมเพลตข้อความให้มี motion personality ครบวงจร (Template v2) พร้อมสร้าง Animated Template Gallery ใน Inspector ที่แสดงการเคลื่อนไหวจริง (Micro-animation) ให้ผู้ใช้เห็นภาพก่อนเลือก ปลดล็อกป้ายฮุกและข้อความระดับไวรัล CapCut ทั้งใน Renderer และ Preview 100%

### Todo

- [x] Template v2 Models & Motion Presets:
  - เพิ่ม template ใหม่ใน `HOOK_TEMPLATES` ทั้งฝั่ง `scripts/hook_styles.py` และ `frontend/src/lib/hookStyles.js`:
    - `flash_sale` (โปรไฟลุก — แดงสด ป้ายส้มเหลืองสะดุดตา): Kanit, แดงสดตัดเหลือง ขอบหนาป้ายแดง, motion: pop + flicker + slide + badge + stagger
    - `neon_cyber` (นีออน — ฟ้าไซเบอร์ ขอบมืดเรืองแสง): Chakra Petch, ฟ้านีออน Glow ขอบดำ, motion: pop_zoom + wave + glitch + underline + stagger
    - `minimal_luxury` (ลักชัวรี — ทองขาว คมชัด สไตล์แบรนด์เนม): Prompt, ขาว/ทอง ขอบบางเรียบหรู, motion: quick_fade + lightsweep + fade + underline + stagger
  - กำหนด signature motion preset ประจำแต่ละ template ครบทั้ง 8 templates ใน `HOOK_TEMPLATES` (`motion: { in, loop, out, accent, stagger }`)
  - รองรับการ sync เมื่อเลือก template: `withHookTemplate` และ `withHookTemplateReset` นำ template motion ไปใส่ใน `overlay.anim`
  - รองรับ `motion` ใน `resolve_hook_style` (Python) และ `resolveHookStyle` (JS) ให้ได้ dict เดียวกันแบบ parity 100%
- [x] Animated Template Gallery (แกลเลอรีที่ขยับได้ใน Inspector):
  - ปรับปรุง UI แกลเลอรีสไตล์ใน `frontend/src/components/editor/inspector/OverlayInspector.jsx`:
    - แทนที่ปุ่มข้อความแบบเดิมด้วยการ์ด Template Preview เกรดโปร (Dark Card + Glow Border + Font tag + Motion badge)
    - แสดงภาพจำลอง 3 ชั้น (Brand, Model, Label) พร้อมสี, ฟอนต์, outline และ pill badge จริงผ่าน `TextLookPreview`
    - ใส่ CSS Micro-animations ใน `frontend/src/index.css` (`templatePulse`, `templateWave`, `templateShake`, `templateFlicker`, `templateLightsweep`, `templatePopZoom`)
    - รองรับ Interactive Hover: เมื่อเอาเมาส์ชี้ การ์ดจะเล่น motion preview ทันที
  - ยกระดับ Text Template Preview ใน `AssetPanel.jsx`:
    - แสดง motion badge พร้อม micro-animation preview ตอน hover สำหรับ Hook templates
    - เพิ่ม 3 templates ใหม่ลงใน `TEXT_TEMPLATES`: `tpl_hook_flash_sale`, `tpl_hook_neon_cyber`, `tpl_hook_minimal_luxury`
  - ยกระดับ Text Overlay Preset Styles ใน Inspector:
    - เพิ่ม micro-animation scale และ glow shadow เมื่อ hover
- [x] Automated Tests & Verification:
  - Parity test `test_hook_templates_are_identical_on_both_sides` และ `test_both_resolvers_agree_on_templates_overrides_and_colours` ตรวจสอบทั้ง 8 templates และ motion preset
  - Multi-frame FFmpeg behavioral render test `test_new_hook_templates_render_with_ffmpeg` ใน `tests/test_preview_render_behavior.py` ยืนยันการเรนเดอร์ template ใหม่ทั้ง 3 ตัวด้วย FFmpeg
  - Pass all gates: compileall, 78+ routes, pytest 356 passed, npm test 54 passed, npm run build passed

### Gate

- [x] `python -m compileall -q scripts` — ผ่าน 0 error
- [x] `python -c "import scripts.api_server as app; print(len(app.app.routes))"` — 80 routes
- [x] `python -m pytest tests/ -q -p no:cacheprovider` — 356 passed, 0 failed
- [x] `npm test` — 54 passed, 0 failed
- [x] `npm run build` — ผ่านฉลุย 0 warning (built in 3.18s)
- [x] FFmpeg behavioral render ดึงเฟรมตรวจสอบ visual output ของ template v2 (`test_new_hook_templates_render_with_ffmpeg` ผ่าน 100%)

### Notes

- การรวม motion preset เข้ากับแต่ละ template ทำให้การสลับลุคเพียงคลิกเดียวได้ทั้ง typography hierarchy และ dynamic motion behavior ที่เข้ากันโดยอัตโนมัติ
- สไตล์แอนิเมชัน CSS ฝั่ง preview มี timing และ easing สอดคล้องกับพฤติกรรมของ FFmpeg/libass ASS tags ตามหลัก Preview = Render Parity

---

## Round 6 — ช่องใหม่ที่ mirror ได้เป๊ะ (Full Motion Pipeline + Tier A Skew)

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ

**เป้าหมาย:** เชื่อมต่อช่อง Animation ที่เหลือ (`loop`, `out`) ให้ Text Overlay ทำงานได้เต็มรูปเหมือน Hook Header ทั้งใน Renderer (libass) และ Preview (Canvas 2D) พร้อมเพิ่มช่องสไตล์ Tier A `skew` (`\fax`) สำหรับข้อความเอียงที่ไม่มีผลกระทบต่อ layout advance และต่อ UI Inspector ให้ผู้ใช้ปรับแต่งได้อย่างสมบูรณ์

### Todo

- [x] Model channels:
  - เพิ่ม `skew` (float, default 0.0) ใน `TEXT_LOOK_FIELDS` และ `DEFAULT_TEXT_LOOK` ทั้งใน `scripts/overlay_model.py` และ `frontend/src/lib/overlayModel.js`
  - ตรวจสอบ `DEFAULT_ANIM` และ contract ให้มี parity 100%
- [x] Backend ASS writer (`scripts/subtitle/overlay_events.py`):
  - ใน `_text_overlay_events`:
    - อ่าน `loop` จาก `anim` (default `none`) และเรียก `loop_builder(max_entry_end_ms, exit_start_ms)`
    - อ่าน `out` จาก `anim` (default `fade`) และเรียก `out_builder(exit_start_ms, exit_end_ms, target_scale)`
    - ผูก `loop_tag` และ `out_tag` (รวมถึง `move_dy_out` สำหรับ `slide` out) เข้ากับ main text และ shadow layers
    - รองรับ `loop == 'lightsweep'` สำหรับ text overlay
    - รองรับ `look.get("skew")`: ถ้ามีค่า skew ให้ใส่ `\fax{skew:.2f}` ลงในแท็ก ASS
- [x] Frontend Canvas mirror (`frontend/src/components/SequencePlayer.jsx`):
  - ใน `drawOneOverlay`:
    - ยืนยันการผสาน `loopFx` และ `outFx` ให้ครบทุก preset สำหรับ text overlay ทั้งระดับคำและระดับบรรทัด
    - รองรับ `w.look.skew`: ทำ affine skew ผ่าน `ctx.transform(1, 0, w.look.skew, 1, 0, 0)` รอบจุดกึ่งกลางคำ/บรรทัด
    - รองรับ skew ใน lightsweep highlight pass
- [x] UI Inspector (`frontend/src/components/editor/inspector/OverlayInspector.jsx`):
  - เพิ่มตัวเลือกแอนิเมชันตอนค้าง (Loop Animation): None, Pulse, Wave, Shake, Flicker, Light Sweep
  - เพิ่มตัวเลือกแอนิเมชันตอนออก (Out Animation): Fade, Slide, Zoom, Glitch, Cut
  - เพิ่มตัวเลือกความเร็วการทยอยเข้าของคำ (Word Stagger): 0ms (พร้อมกัน), 50ms (เร็ว), 70ms (ปานกลาง), 100ms (ช้า)
  - เชื่อมปุ่ม "I" (Italic) ให้สลับค่า `skew` (0.0 <-> -0.25) เพื่อให้ข้อความเอียงจริงทั้งในพรีวิวและเรนเดอร์
- [x] Automated tests & behavioral validation:
  - Parity test ใน `tests/test_preview_render_parity.py` ยืนยัน `TEXT_LOOK_FIELDS` และ `DEFAULT_TEXT_LOOK`
  - Contract test ยืนยัน ASS tags สำหรับ `loop`, `out`, และ `\fax` (`test_text_overlay_events_wires_loop_out_and_skew`)
  - Multi-frame FFmpeg behavioral render test ยืนยัน visual output ของ `loop` (pulse), `out` (slide), และ `skew` (`\fax-0.25`)
  - Zero-regression test สำหรับ overlay ที่ใช้ค่า default

### Gate

- [x] `python -m compileall -q scripts` — ผ่าน 0 error
- [x] `python -c "import scripts.api_server as app; print(len(app.app.routes))"` — 78 routes
- [x] `python -m pytest tests/ -q -p no:cacheprovider` — 351 passed, 0 failed
- [x] `npm test` — 54 passed, 0 failed
- [x] `npm run build` — ผ่านฉลุย 0 warning (built in 3.38s)
- [x] FFmpeg behavioral render ดึงเฟรมตรวจสอบ:
  - Skew: `\fax-0.25` ให้ forward italic slant โดย top pixels เลื่อนขวามากกว่า bottom pixels เมื่อเทียบกับ straight text (`d_top - d_bot = +6.68px`)
  - Loop pulse: hold phase มี alpha modulation ชัดเจน (`diff_pixels > 50`)
  - Out slide: exit phase เลื่อนลงด้านล่างตามแกน Y อย่างถูกต้อง (`exit_y > hold_y + 5.0px`)

### Notes

- การใช้ affine shear `\fax` ใน libass และ `ctx.transform(1, 0, skew, 1, 0, 0)` ใน Canvas 2D ช่วยแก้ปัญหาการขาดแคลน native italic font cut ของฟอนต์ไทยบน Google Fonts (Kanit, Prompt, Chakra Petch) ได้อย่างสมบูรณ์แบบ
- การทำ shear รอบจุดกึ่งกลางคำ/บรรทัดไม่กระทบต่อ layout advance width หรือ word bounding measurement ใดๆ ทำให้ zero-regression invariant ยังคงอยู่อย่างสมบูรณ์

---

## Round 5 — per-word animation (คำทยอยเข้าทีละคำ)

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ

**เป้าหมาย:** ทำ Animation ให้ข้อความทยอยเข้าทีละคำ (Word Stagger Animation) โดยใช้พิกัดจาก Word Layout Engine ของ Round 4 เพื่อให้ทั้ง Preview (Canvas 2D) และ Render (libass) แสดงผลการทยอยเข้าของคำด้วยจังหวะเวลา (Timing) และทรานส์ฟอร์มเดียวกัน 100%

### Todo

- [x] `anim.word_stagger_ms`: เพิ่มช่องพารามิเตอร์ `word_stagger_ms` ใน overlay model (`anim`) ค่าเริ่มต้น ~60-80ms สำหรับ per-word animation (default 0)
- [x] Backend ASS writer (`scripts/subtitle/overlay_events.py`):
  - ใน `_text_overlay_events` เมื่อมี `word_stagger_ms > 0`:
  - คำนวณ `t_word_in = word_idx * word_stagger_ms`
  - ก่อน `t_word_in` คำจะซ่อนอยู่ (`\alpha&HFF&`)
  - เมื่อถึง `t_word_in` คำจะเริ่มเล่น in-animation ตาม preset (`snap`, `pop_zoom`, `stamp`, `quick_fade`, `rise`, `none`)
  - กำหนด transform origin `\org(w_cx, w_cy)` ต่อคำเพื่อให้ scale และ rotate รอบจุดกึ่งกลางคำของตัวเอง
  - Duplicate shadow events ให้มี timing ตรงกับ main text ของคำนั้นๆ
  - ถ้า `word_stagger_ms == 0` หรือไม่ระบุ ให้รักษารูปแบบพร้อมกันทุกคำ (เหมือน Round 4 เป๊ะ)
- [x] Frontend Canvas mirror (`frontend/src/components/SequencePlayer.jsx`):
  - ใน `drawOneOverlay` อ่าน `motion.word_stagger_ms` และคำนวณ `wordStaggerSec`
  - ใน word drawing loop คำนวณ `wordT0` และ `wordTRel = tRel - wordT0`
  - ถ้า `wordTRel < 0` คำนั้นยังไม่แสดง (ข้ามการวาด)
  - เมื่อ `wordTRel >= 0` ให้คำนวณ `wordInFx = inPreset.at(wordTRel * 1000)` แยกเฉพาะคำนั้น (ทั้ง scale, dy, alpha, blur)
  - ทำ affine transform `translate(wordCx, wordCy) -> scale(wordScale) -> translate(-wordCx, -wordCy)` รอบจุดกึ่งกลางคำ ตรงกับ `\org` ของ libass ASS
- [x] Automated tests & behavioral validation:
  - Contract test `test_text_overlay_word_stagger_events` ยืนยัน ASS tags `\t`, `\org` และ `\alpha` ของแต่ละคำ
  - Multi-frame FFmpeg behavioral render test `test_text_overlay_word_stagger_multi_frame_render` (w40=63px < w120=127px < w600=191px)
  - Zero regression: `test_word_stagger_zero_regression` (0 differing pixels between settled staggered and static overlay)

### Gate

- [x] `python -m compileall -q scripts` — ผ่าน 0 error
- [x] `python -c "import scripts.api_server as app; print(len(app.app.routes))"` — 77 routes
- [x] `python -m pytest tests/ -q -p no:cacheprovider` — 347 passed, 0 failed
- [x] `npm test` — 54 passed, 0 failed
- [x] `npm run build` — ผ่านฉลุย 0 warning (built in 3.15s)
- [x] FFmpeg behavioral render ดึงเฟรมตรวจสอบ:
  - เฟรมแรก (40ms): แสดงเฉพาะคำแรก คำถัดไปยังไม่ปรากฏ (w40=63px)
  - เฟรมกลาง (120ms): คำแรก settle แล้ว คำถัดมากำลังเข้า (w120=127px)
  - เฟรมสุดท้าย (600ms): ทุกคำปรากฏครบถ้วน (w600=191px)
  - Zero regression: เฟรม settled มีพิกเซลต่างกัน 0 พิกเซล (100% pixel-perfect)

### Notes

- ค้นพบว่า libass สามารถ animate การทยอยเข้าของคำได้อิสระด้วยการกำหนด `\alpha&HFF&` สำหรับช่วงก่อนเวลา `word_t0` แล้วใช้ `\t(word_t0, word_t0+dur, \fscx...\fscy...)` ร่วมกับ `\org(w_cx, w_cy)` เพื่อให้แต่ละคำ scale ขยาย/ยุบรอบจุดศูนย์กลางของคำตัวเอง
- ฝั่ง Canvas 2D จำลองพฤติกรรมนี้ได้อย่างแม่นยำ 100% ผ่าน `ctx.translate(wordCx, wordCy); ctx.scale(scale, scale); ctx.translate(-wordCx, -wordCy);` โดยข้ามการวาด (skip render) สำหรับคำที่ `wordTRel < 0`
- Zero-regression invariant ได้รับการพิสูจน์แล้วผ่าน `test_word_stagger_zero_regression` ซึ่งเปรียบเทียบเฟรมที่ render จาก FFmpeg พบว่าไม่มีความแตกต่างของพิกเซลแม้แต่พิกเซลเดียว (diff_pixels == 0) เมื่อคำเข้าสู่สถานะ settled

---

## Round 4 — per-word layout (static, พิสูจน์ว่าเหมือนเดิมเป๊ะ)

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ

**เป้าหมาย:** แตกคำได้โดยภาพ**ไม่เปลี่ยนเลย** — วางรากฐาน Static per-word layout engine เพื่อให้ libass (Renderer) และ Canvas 2D (Preview) แสดงผลคำในพิกัดเดียวกันด้วยความคลาดเคลื่อน $\le 1.5\text{px}$ ก่อนต่อยอดใส่ Animation ใน Round 5

### Todo

- [x] `scripts/subtitle/word_layout.py` — สร้าง `layout_overlay(text, font, em_px, max_w) -> {lines:[{y_offset, words:[{text, x, w}]}]}` ในหน่วย normalised (`x / video_width`)
- [x] ตัดคำ: whitespace สำหรับ Latin · `pythainlp` newmm สำหรับไทย · กักกันสระ/วรรณยุกต์ลอย
- [x] guard: รวม token ที่เป็นช่องว่างล้วน · reject จุดตัดที่ตัวถัดไปเป็น combining mark (`unicodedata.combining != 0` หรืออยู่ใน `U+0E31, U+0E34–U+0E3A, U+0E47–U+0E4E`) แล้วรวมเข้ากับคำก่อนหน้า
- [x] Latin: ความกว้างคำไม่รวมช่องว่างท้าย — advance ของช่องว่างไปอยู่ต้นคำถัดไป
- [x] ASS writer กิน layout ตรงๆ · 1 Dialogue ต่อคำ + `\an7\pos(x_i, y)` + `\q2` + shadow layer duplicate ต่อคำ
- [x] API คืน `layout` ติดมากับ overlay + เพิ่ม endpoint `POST /api/editor/overlay/layout`
- [x] `frontend/src/lib/overlayLayoutClient.js` — ทำ debounce ~120ms + cache ด้วย key `(text, font, em_px, max_w)`
- [x] `drawOneOverlay` ใน `SequencePlayer.jsx` อ่าน `overlay.layout` คูณ `CANVAS_W` — วาดแยกรายคำเมื่อมี layout และ fallback เป็น `measureText` ทั้งบรรทัด
- [x] รัน visual regression test ด้วย FFmpeg ดึงเฟรมจริงมาเปรียบเทียบพิกเซล

### Gate

- [x] **invariant หลัก:** ปิด animation หมด → เรนเดอร์แบบแตกคำกับแบบไม่แตก Bounding box กว้างต่างกันไม่เกิน 3px (>99.8% pixel identity บน 1080x1920 canvas)
- [x] fixture ระบายสีต่อคำ (`\1c` คนละสี) แล้วสแกน min/max x ต่อสีด้วย PIL — `|measured_left_i − x_i| ≤ 1.5px` (ตรงตาม Left Side Bearing ของฟอนต์)
- [x] วาง regression ไว้ที่ `tests/test_preview_render_behavior.py` ใต้ `@pytest.mark.render_regression`
- [x] `python -m compileall -q scripts` — ผ่าน 0 error
- [x] `python -c "import scripts.api_server as app; print(len(app.app.routes))"` — 77 routes
- [x] `python -m pytest tests/ -q -p no:cacheprovider` — 344 passed, 0 failed
- [x] `npm test` ใน frontend — 54 passed, 0 failed
- [x] `npm run build` ใน frontend — ผ่านฉลุย 0 warning

### Notes

- ค้นพบข้อจำกัดสำคัญของ Pillow กับ libass Fontsize: libass คิด Fontsize ตาม line box (`usWinAscent + usWinDescent`) ขณะที่ Pillow FreeType คิดตาม EM size ต้องสเกลด้วย `ass_glyph_scale(font) = unitsPerEm / (usWinAscent + usWinDescent)` (เช่น Kanit สเกล ~0.6329) หากไม่สเกลค่า advance จะกว้างเกินจริง 1.58 เท่า
- การคำนวณตำแหน่งคำแบบ cumulative advances ร่วมกับการกัน combining marks ทำให้คำภาษาไทยที่มีสระบน/ล่างและวรรณยุกต์ไม่แตกกระจัดกระจายและไม่เกิดสระลอย
- การทดสอบด้วย FFmpeg render จริงพบว่าการเริ่มคำ (Word Start) คลาดเคลื่อนจากหมึกจริงเพียง 0.5 – 1.5 px ซึ่งเทียบเท่ากับ Left Side Bearing ของตัวอักษรพอดี ปลอดภัยและพร้อมสำหรับการทำ per-word animations ใน Round 5 ต่อไป

---

## Round BUG-1 — แก้ปุ่มสร้างคลิปใหม่กดไม่ได้ (executeRender ใน useRenderJob)

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ

**เป้าหมาย:** ให้หน้าสร้างคลิปใหม่ (`NewClipPanel.jsx`) กดสร้างคลิปได้ปกติ โดยเพิ่ม `executeRender` และ telemetry props (`rendering`, `jobProjectName`, `displayPercent`, `elapsedSeconds`, `estimatedRemainingSeconds`, `renderError`) กลับเข้าสู่ `useRenderJob` พร้อมคง contract ของ `EditorShell` ไว้อย่างสมบูรณ์

### Todo

- [x] คืนชีพและเชื่อมต่อ `executeRender`, `rendering`, `jobProjectName`, `displayPercent`, `elapsedSeconds`, `estimatedRemainingSeconds`, `renderError`, `renderResult` ใน `frontend/src/hooks/useRenderJob.js`
- [x] ให้ `fetchStatus` มี default fallback เป็น `getRenderStatus` จาก `../api.js` และ `executeRender` เรียก `startRender`
- [x] เพิ่ม unit test ครอบคลุมทั้งกรณี `startJob` (สำหรับ EditorShell) และ `executeRender` (สำหรับ NewClipPanel)
- [x] รัน gate: `npm test` และ `npm run build`

### Gate

- [x] `npm test` — 52 passed, 0 failed
- [x] `npm run build` — ผ่าน (1,953 modules transformed)
- [x] `python -m pytest tests/ -q` — 336 passed, 0 failed
- [x] ไม่มี error `executeRender is not a function` ในเบราว์เซอร์

### Notes

- สาเหตุเกิดจากการ refactor `useRenderJob` ในรอบก่อนหน้าให้ `EditorShell` ใช้งานผ่าน `startJob` / `stopJob` โดยไม่ได้คง interface เดิมที่ `NewClipPanel` ใช้งานผ่าน `executeRender` ส่งผลให้เมื่อกด "สร้างคลิป & เข้าสู่ไทม์ไลน์" เกิด `TypeError: executeRender is not a function`
- แก้ไขโดยการเชื่อมต่อ `startRender` และ `getRenderStatus` จาก `api.js` เข้ากับ `useRenderJob` พร้อมทั้งคำนวณ `elapsedSeconds`, `displayPercent` และ `estimatedRemainingSeconds` เพื่อให้ UI แสดงผล Dashboard แบบ Live ขณะเรนเดอร์ได้อย่างสมบูรณ์ทั้งสองหน้าจอ
- เพิ่ม test case ใน `renderJobController.test.js` ป้องกันการ regression ในอนาคต

## Round 1 — รวม hook banner กับ text overlay เป็นโมเดลเดียว

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ · commit: `20e2cc5`

**เป้าหมาย:** ให้ป้ายฮุก (พาเนลขวา) กับข้อความ (พาเนลซ้าย) ใช้ shape เดียว renderer เดียว
คำศัพท์ชุดเดียว — ฝั่งซ้ายจะได้สวยเท่าฝั่งขวา และป้ายฮุกแก้ขนาด/สีได้จริง

### Todo

- [x] P1 — สร้างโมเดลกลาง `scripts/overlay_model.py` + `frontend/src/lib/overlayModel.js` (mirrored pair)
- [x] P1 — migration อ่าน legacy ตลอดไป เขียนเฉพาะ `overlays[]` (โปรเจกต์เก่าไม่ถูกแตะ)
- [x] P2 — รวม canvas renderer 3 ตัวเป็นตัวเดียว (`drawHookHeader` + `drawTextOverlays` + `drawTextTemplatePreview` → `drawOverlays`)
- [x] P3 — ASS อ่าน look ต่อ tier, ใส่ `\fn` `\3c` `\bord` ต่อ overlay
- [x] P3 — pipeline / video_editor (`hook_duration` → `scrim_spans`) / API / sfx_manager รับ `overlays`
- [x] P3 — overlays เข้า undo history
- [x] P4 — AI แยก brand/model/label + `ad_tone` → hook template อัตโนมัติ
- [x] P5 — tier editor 3 แถวพับได้ + `TextLookPreview` + หมวด "ป้ายฮุก" ฝั่งซ้าย
- [x] P5 — ลบ `cssPreview` ทั้ง 21 อัน · ลากการ์ดลง timeline ได้

### Gate

- [x] `pytest tests/` — 294 passed, 0 failed (parity 141 · phase1 smoke 148 · อื่นๆ)
- [x] `npm test` — 14 passed, 0 failed
- [x] `npm run build` ผ่าน
- [x] `oxlint` — 0 error
- [x] เรนเดอร์ ffmpeg จริงแล้วดูเฟรม — ป้าย bold_pop ออกถูก, `\fn` ติด, pill cyan โปร่ง+มีขอบ
- [x] เปิด editor จริงในเบราว์เซอร์ โหลดโปรเจกต์เก่า — 0 console error, canvas วาดป้ายถูก
- [x] save → reload — ค่า `size_pct 165` + สี `#00FF88` ต่อ tier รอด, legacy key ไม่ถูกแตะ

### Notes

**บั๊กที่ปิดไป 12 ตัว** — 5 ตัวตามแผนเดิม + 7 ตัวที่เจอตอนวัดค่า:
outline พรีวิว 3px vs render 5.0 · ระยะบรรทัด 1.2 vs libass 1.0 (ASS pill สูงเกิน 20% ด้วย) ·
ตารางน้ำหนักฟอนต์ไม่ครบ · ลำดับวาด sticker/scrim กลับด้านกับ render ·
hook อยู่ใต้ sticker ในพรีวิวแต่อยู่บนใน render · badge_cyan ทึบ 0.65 แทน 0.2 และไม่มีขอบ ·
ลากการ์ดลง timeline ไม่ทำงาน

**พฤติกรรมที่เปลี่ยนไปจากเดิม (แจ้ง user แล้ว):**

1. ขอบ text overlay ในพรีวิวหนาขึ้น 3px → 5.0 (ยึดเลขของ render เป็นจริง ไฟล์ที่ออกไม่เปลี่ยน)
2. pill ของป้ายฮุกโตตามขนาด tier (12px คงที่ → 0.342em) — ที่ 100% เท่าเดิมเป๊ะ
3. `badge_cyan` ในไฟล์ที่เรนเดอร์จะโปร่งขึ้น (0.65 → 0.2) และมีขอบ cyan ตามที่พรีวิวเคยวาด

**เรื่องที่ต้องรู้:**

- commit `20e2cc5` **มีงานสองชุดปนกัน** — งานนี้ + editor refactor ของ Codex (REFACTOR_PLAN Phase 0–2 ตอนนั้น)
  แยกไม่ได้เพราะ `EditorShell.jsx` มีทั้งสองในไฟล์เดียว → บันทึกไว้ท้าย commit message แล้ว
  **บทเรียน: ครั้งหน้าเช็ค `git status` ก่อนเริ่ม** (เข้ากฎข้อ 6 ของ work_loop.md แล้ว)
- ต้อง restart backend port 8000 หลัง pull — server เก่ายังไม่รู้จัก `overlays`
- เจอบั๊กวรรณยุกต์ไทยของ libass ระหว่างตรวจ → ย้ายเข้า Backlog แล้ว ไม่ได้แก้ในรอบนี้

---

## Round 2 — วางกฎรอบงาน + ตั้ง Todo กลาง

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ

**เป้าหมาย:** ทุกงานหลังจากนี้ต้องมีแผนเขียนลงที่เดียวก่อนลงมือ และเห็นความคืบหน้าได้จากไฟล์เดียว

### Todo

- [x] เขียนกฎรอบงาน `.agents/rules/work_loop.md` (ลำดับบังคับ 7 ขั้น + กฎการติ๊ก + กฎงานขนาน)
- [x] สร้าง `TODO.md` เป็นไฟล์กลาง ใช้ฟอร์แมตเดียวกับ `REFACTOR_PLAN.md`
- [x] เก็บงาน Round 1 และของค้างจริงลง Backlog ให้ไฟล์เริ่มด้วยข้อมูลจริง ไม่ใช่ template เปล่า
- [x] ผูกเข้า `AGENTS.md` — บล็อกเตือนบนสุด + ข้อ 10 ในหมวด STRICT DOs

### Gate

- [x] `AGENTS.md` ชี้ไป `work_loop.md` และ `TODO.md` ครบทั้งบนสุดและในหมวดกฎ
- [x] ไม่มีไฟล์ todo ซ้ำซ้อนในโปรเจกต์ (ที่เดียวคือ `TODO.md`)
- [x] ไม่แตะโค้ดที่รันจริง — งานรอบนี้เป็นเอกสารล้วน ไม่ต้องรัน build/test

### Notes

- ไม่แตะ `REFACTOR_PLAN.md` / `REFACTOR_BASELINE.md` — เป็นงานของ Codex ที่ปิดแล้ว เก็บไว้อ้างอิง
- ไม่สร้าง `CLAUDE.md` เพิ่ม เพราะ repo ใช้ `AGENTS.md` เป็นกฎแม่อยู่แล้ว
  การมีสองไฟล์จะขัดกับกฎ "ไฟล์เดียว" ที่เพิ่งเขียนเอง
- บทเรียนจาก Round 1 ที่ถูกเขียนเป็นกฎข้อ 6: ต้องเช็ค `git status` ก่อนเริ่ม
  เพราะเคยมีสอง session แก้ `EditorShell.jsx` พร้อมกันจนแยก commit ไม่ได้

---

## Round 3 — ซ่อมฐาน + รวม writer + easing

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: กำลังทำ

**เป้าหมาย:** ทำให้ per-word เป็นไปได้ — วัดเพดานจริง ซ่อม drift ปิดช่องที่ปิดอยู่ และใส่ easing แบบไม่กระทบของเดิม

### 3.1 Spike วัดเพดาน libass (ทำก่อนอย่างอื่นทั้งหมด)

ทุกข้อยิงด้วย `force_style` ไม่ต้องสร้าง fixture ใหม่ · **ทุกคำสั่งต้องมี `fontsdir=02_Assets/Fonts`** (parity rule 2.0.1) · path ของ `.ass` ต้องเป็น relative

- [x] mid-line `\t` สอง window ต่างกันในบรรทัดเดียว ทำงานจริงไหม (ทำงานจริง PASS: 250ms->265px, 500ms->329px, 750ms->373px, 1000ms->417px พร้อม state reset)
- [x] `accel` 0.5 vs 1.0 vs 3.0 — วัด scale delta ที่กึ่งกลางด้วย PIL (`pow(p, accel)` ยืนยันตรงตามทฤษฎี)
- [x] `Spacing` scale ตาม `\fscx` ไหม (scale ตามเป๊ะ 2.0x width scaling ที่ `\fscx200`)
- [x] `Spacing` คิดต่อ glyph หรือต่อ cluster สำหรับไทย (คิดต่อ glyph ทำให้สระและวรรณยุกต์แยกตัวหลุดจากพยัญชนะ)
- [x] mid-line `{\1c}` ตัด HarfBuzz run ไหม (ไม่ตัด HarfBuzz run ไม่กระทบการเชื่อมคำ)
- [x] `\pos` event ยัง wrap ที่ MarginL/R ไหม (wrap ที่ Margin เว้นแต่ระบุ `\q2`)
- [x] libass เลือก face ไหนจริงสำหรับ `\fn Kanit` + `Bold=1` (resolve เป็น `Kanit-Bold.ttf` weight 700)
- [x] **บั๊กวรรณยุกต์ไทยรอดจาก `force_style='Spacing=0'` ไหม** (รอด! การตั้ง `Spacing=0` ปิดปัญหาการยืดระยะของสระและวรรณยุกต์)

### 3.2 ซ่อม drift 3 ตัว

- [x] `Spacing: 0.5` → `0` ใน Style ทั้ง 11 แถว (`scripts/subtitle_engine.py`)
- [x] `_measure_text_width_px` ใช้ `getlength()` (advance) แทน `getbbox()` (ink) — เพิ่ม `prefix_advances()` ไว้ที่เดียวกัน (`scripts/subtitle/font_metrics.py`)
- [x] `FONT_WEIGHTS` (`frontend/src/lib/overlayModel.js`) แก้ให้ตรงกับที่ libass resolve จริง + ทำ mirror ฝั่ง Python
- [x] เพิ่ม parity assertion ล็อกทั้ง 3 ค่าไว้

### 3.3 รวม ASS writer เป็นตัวเดียว

- [x] แยก `scripts/subtitle/overlay_events.py` → `overlay_events(overlay, ctx) -> [str]`
- [x] route ทั้ง hook block (`:540-800`) และ text-overlay block (`:930-1080`) ผ่านตัวนี้
- [x] ผลพลอยได้: `loop`/`out`/`accent`/`stagger` ของ text overlay เปิดใช้ได้เอง
- [x] แก้ docstring ค้างที่ `SequencePlayer.jsx:1246` ที่อ้าง `_overlay_events()` ซึ่งไม่มีอยู่จริง

### 3.4 wrapper ตัวเดียว

- [x] คืนดี `wrap_text_for_ass` (`scripts/subtitle/translation_service.py`) กับ `wrapCanvasText` (`frontend/src/components/SequencePlayer.jsx`) — ใช้ตรรกะเดียว แหล่งเดียว

### 3.5 easing เป็นช่องใหม่ ไม่ทับของเดิม

- [x] `HOOK_*_BUILDERS` (`scripts/subtitle/motion_effects.py`) คืน keyframe list `[(t_ms, {prop: value}, accel), …]` + serialiser เดียวที่ emit `\t(t1,t2,accel,…)`
- [x] `accel = 1.0` ต้องได้ ASS byte-identical กับวันนี้ — assert ไว้
- [x] mirror ที่ `hookKeyframeAt` (`SequencePlayer.jsx:1081`): `v1 + (v2-v1) * Math.pow(p, accel)`
- [x] ค่าคงที่มีชื่อทั้งสองฝั่ง (`ACCEL_SOFT_OUT = 0.6`, `ACCEL_SNAP_IN = 2.2`) ห้าม inline float
- [x] preset ใหม่ที่ใช้ accel (`bounce_soft`, `pop_soft`) — ของเดิมไม่แตะ default เฉพาะ overlay ใหม่
- [x] ระวังกับดัก: `_in_bounce` แกล้งทำ ease ด้วย 4 segment อยู่แล้ว ใส่ accel ทับ = ease ซ้อน ต้องจูนราย segment
- [x] ห้ามตั้งชื่อ `ease_out` — ชนกับ `keyframe_engine.py` ที่นิยาม `t*(2-t)` ไว้แล้ว

### Gate

- [x] `pytest tests/ -q` 336 passed, 0 failed · `npm test` 51 passed, 0 failed · `npm run build` ผ่าน
- [x] `accel=1.0` ให้ ASS เท่าเดิมทุก byte (asserted in `test_easing_accel_constants_and_byte_identity_parity`)
- [x] เรนเดอร์ ffmpeg เทียบก่อน/หลังซ่อม Spacing — ยืนยันว่า Spacing=0.5 ยืดเกินไป 24px (666px vs 642px) โดย Spacing=0 ตรงกับ Canvas advance
- [x] text overlay รับ `in` (`pop_soft`), `loop` (`wave`), `out` (`zoom`) ได้จริง — เรนเดอร์ FFmpeg จริงผ่านทั้ง 3 เฟรม (0.10s, 1.00s, 2.92s)
- [x] บันทึกผล spike ทั้ง 8 ข้อลง `TODO.md` Notes

### Notes

1. **ผล Spike Libass (8/8 ข้อ):**
   - Mid-line `\t`: tag override ไหลไปข้างหน้า ต้อง explicit reset ด้วย `\fscx100` หรือ initial value ก่อนขึ้นคำถัดไป
   - `accel` math: libass ใช้ power curve `pow(p, accel)` ตรงกับ `Math.pow(p, accel)` ของ JS canvas
   - Spacing: libass Spacing คิดต่อ glyph (ไม่ใช่ HarfBuzz cluster) ทำให้ upper vowel/tone mark ในภาษาไทยโดนแทรก spacing จนเพี้ยน การปรับ `Spacing: 0` ช่วยให้ตำแหน่งการแสดงผลถูกต้อง 100%
   - HarfBuzz clusters: span `{\1c}` ตรงรอยต่อคำไม่ทำลาย cluster shaping
   - Margin wrap: `\pos` dialogue wrap ตาม Margin เสมอ ต้องใช้ `\q2` ทุก Dialogue
   - Kanit bold font: `\fn Kanit\b1` ผูกกับ `Kanit-Bold.ttf` (weight 700) ไม่ใช่ Black (900)
2. **การซ่อม Drift:**
   - Style ทั้ง 11 แถวใน `subtitle_engine.py` เปลี่ยน `Spacing: 0.5` -> `0`
   - Advance measurement: `font.getlength()` แทน ink bounding box และเพิ่ม `prefix_advances()` ใน `font_metrics.py`
   - Weight mapping: `FONT_WEIGHTS` ปรับเป็น 700 สำหรับ Kanit/Prompt และ 400 สำหรับ Anuphan/Noto
3. **Unified Overlay Events:**
   - สร้าง `scripts/subtitle/overlay_events.py` รับหน้าที่ render ASS Dialogue events ร่วมกันระหว่าง 3-tier hook banner และ freeform text overlay
   - รองรับ in/loop/out/stagger ครบวงจร
4. **Easing Architecture:**
   - นิยาม `ACCEL_SOFT_OUT = 0.6` และ `ACCEL_SNAP_IN = 2.2` ทั้งสองฝั่ง
   - `serialize_keyframes()` ปล่อย linear `\t(t1,t2,...)` byte-identical 100% เมื่อ `accel == 1.0`
   - เพิ่มพรีเซ็ตใหม่ `bounce_soft` และ `pop_soft` ไม่กระทบพรีเซ็ตเดิม

---

## Round DOC-1 — ตรวจโค้ดและอัปเดตเอกสารหลัง Refactor

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: เสร็จ

**เป้าหมาย:** ให้ผู้ใช้และ Agent รอบถัดไปเข้าใจโครงสร้างจริง วิธีทดสอบ กฎแก้โค้ด และงานที่ยังค้างจากเอกสารชุดเดียวกัน

### Todo

- [x] ตรวจ entry points, routers, pipeline stages, Editor state, autosave, render job, timeline และ subtitle modules จากโค้ดจริง
- [x] เพิ่ม `ARCHITECTURE.md` เป็นแผนผังระบบและจุดส่งต่องาน
- [x] ปรับ `README.md` ให้ตรงกับความสามารถและคำสั่งปัจจุบัน
- [x] แทนที่ `frontend/README.md` แบบ Vite template ด้วยคู่มือ frontend ของโปรเจกต์
- [x] เพิ่มกฎการเขียนและรัน test ใน `.agents/rules/testing_standard.md`
- [x] อัปเดต `AGENTS.md` และ `tests/README.md` ให้ชี้ไปยังเอกสารใหม่
- [x] บันทึกข้อเท็จจริงว่า Round 3 ยังเป็น Working Tree ที่ไม่ commit และห้าม Agent รอบใหม่เขียนทับ

### Gate

- [x] `python -m compileall -q scripts` ผ่าน
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` ผ่าน
- [x] `npm test` ผ่าน
- [x] `npm run build` ผ่าน
- [x] ลิงก์ไฟล์ในเอกสารชี้ไปยังไฟล์ที่มีอยู่จริง
- [x] `git diff --check` ผ่าน

### Notes

- Baseline ก่อนแก้เอกสาร: Python `336 passed, 5 warnings in 44.08s`; Frontend `51 passed`; Vite build ผ่าน 1,953 modules; FastAPI 76 routes
- ระหว่าง audit พบและแก้ preset catalog ขาด `bounce_soft`/`pop_soft`; render regression บังคับ CPU เพื่อไม่พึ่ง hardware encoder ของเครื่องทดสอบ
- เอกสารที่เพิ่ม/อัปเดต: `ARCHITECTURE.md`, `README.md`, `frontend/README.md`, `tests/README.md`, `AGENTS.md`, `.agents/rules/testing_standard.md`, `_Docs/README.md`
- Round 3 subtitle/writer/easing เสร็จสมบูรณ์แล้ว ผ่าน gates ทุกข้อ (pytest 336, npm test 51, build ผ่าน, Spacing render 0 vs 0.5 ยืนยัน drift หายไป 24px, overlay motion render ผ่าน 3 เฟรม)

---

## Round POST-3.4 — แก้การส่งกำหนดเวลาและภาพปกจาก Side Panel ไป TikTok

วันที่: 2026-09-07  
ผลลัพธ์: commit `bfeb7e6`; เพิ่ม endpoint refresh cover, จำกัด modal/file input ล่าสุด, รองรับเวลาแบบมีหรือไม่มีศูนย์นำหน้า; Node 7 passed, backend 5 passed

## Round POST-3.5 - Fix product search scoping

Date: 2026-09-07
Result: commit `33210f2`; Product ID search and search icon are scoped to the latest Product Selector dialog; Node regression suite passed 7/7.

## Round POST-3.6 - Fix schedule mode targeting and five-minute time input

Date: 2026-09-07
Result: Schedule step now clicks only TikTok's schedule radio and never the final publish button; requested times are normalized to TikTok's five-minute increments and the Side Panel date/time controls were restyled. Node regression suite passed 8/8; live TikTok verification remains pending after extension reload.

## Round POST-3.6 verification - Schedule step confirmed by user

Date: 2026-09-07
Result: User confirmed that step 4 changes TikTok's date and time without publishing automatically. Step 4 is frozen; cover upload verification remains the only pending part of this round.

## Round POST-3.7 - Harden Cover Studio upload targeting

Date: 2026-09-07
Result: Cover upload now scopes file input and save button to TikTok's visible `CoverEditor__root`, enables the CDP Runtime domain, and verifies the editor closes after saving. Node regression suite passed 8/8; live upload verification remains pending after extension reload.

## Round POST-3.8 - Improve schedule time picker and completion state

Date: 2026-09-07
Result: Side Panel time selection now offers five-minute increments only, enforces a 15-minute lead time for today, and displays a durable completed style on successful steps. Product attachment and publication flows were unchanged; Node regression suite passed 8/8.

## Round POST-3.10 - Keep open TikTok pickers stable and expose cover-step failures

Date: 2026-09-07
Result: `setScheduleDateTime` now detects an already-open date/time picker and avoids toggling it closed before choosing the requested value. Cover automation errors now identify the failing step, while existing Cover Studio targeting remains scoped to the latest modal. Live inspection confirmed TikTok supports five-minute values and the edit-cover control opens `CoverEditor__root`; file transmission still requires a direct extension test because the browser controller blocks local file injection. Node regression suite passed 8/8.

## Round POST-3.11 - Scroll TikTok time options before selecting

Date: 2026-09-07
Result: Time selection now searches all TikTok hour/minute options and scrolls the requested option into view before clicking. This fixes the recorded case where Side Panel selected `10:00` but TikTok stayed at `10:40` because `00` was outside the visible virtual-scroll window. Node regression suite passed 8/8.

## Round POST-3.12 - Find Cover Studio Save outside the editor root

Date: 2026-09-07
Result: Cover automation now includes TikTok's `cover-editor-container` and prefers that outer container when locating the Save button. The live DOM showed Save is a sibling of `CoverEditor__root`, which explained why the modal opened but the automation could not finish. Node regression suite passed 8/8; local file injection remains pending a direct extension test.

## Round POST-3.13 - Persist schedule completion and resolve saved product covers


## Round USER-GUIDE-1 — เมนูใหม่ "คู่มือใช้งาน" ในโปรแกรม + โฟลว์หลักครบ 7 เมนู

วันที่: 2026-09-12 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:**

## Round USER-GUIDE-2 — การ์ดเมนูกระชับ วางหลายใบต่อแถว

วันที่: 2026-09-12 · สั่งโดย: user (feedback จากภาพ: การ์ดข้อความสั้นแต่กล่องกว้างเต็มแถว) · สถานะ: เสร็จสมบูรณ์

**สิ่งที่ทำ:**
- `frontend/src/components/UserGuide.jsx` ส่วน `#ug-menus`: จาก `space-y` 1 คอลัมน์เต็มความกว้าง → `grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-2.5 items-start` การ์ดสูงตามข้อความจริง ไม่ยืดตามเพื่อนร่วมแถว
- ลด padding การ์ด `p-4 sm:p-5` → `p-4` กล่องกระชับขึ้น

**ผล:** จอกว้างเห็นเมนู 1+2 ข้างกัน เมนู 3+4 ข้างกัน ไม่ต้องเลื่อนจอยาว มือถือยัง 1 คอลัมน์เหมือนเดิม


## Round USER-GUIDE-3 — กระชับทุกกล่องในคู่มือ

วันที่: 2026-09-12 · สั่งโดย: user (feedback: กล่องอื่นก็โล่งเหมือนกัน + /impeccable /ux-ui-promax) · สถานะ: เสร็จสมบูรณ์

**แนวทาง (impeccable refinement):** เก็บ rhythm เดิมทั้งหมด (PageHeader, การ์ด #0B0F19, chip สี, ลำดับ section, ข้อความ) แล้วลดความสูงด้วย multi-column grids + items-start + padding กระชับเท่านั้น


## Round USER-GUIDE-4 — คู่มือ interactive ใช้งานได้จริง

วันที่: 2026-09-12 · สั่งโดย: user (จัดการแบบละเอียด) · สถานะ: เสร็จสมบูรณ์

**แนวทาง:** impeccable refinement — ไม่เปลี่ยนข้อความ สี ลำดับ section ใดๆ เพิ่มแค่ interaction 6 ฟีเจอร์ใน `frontend/src/components/UserGuide.jsx` (160 → 257 บรรทัด)

**สิ่งที่ทำ:**
1. Sticky TOC ลอยติดบน (`sticky top-52/56px` ตรงความสูง Topbar) + scrollspy ด้วย IntersectionObserver ไฮไลต์หัวข้อที่อ่านอยู่เป็นสี cyan
2. เช็กลิสต์กดติ๊กได้จริง: ปุ่ม toggle ต่อข้อ + แถบความคืบหน้า gradient + ป้าย n/6 + ข้อความพร้อมโพสต์เมื่อครบ + จำค่า localStorage (`omnicut_guide_checklist_v1`) + ปุ่มล้าง
3. การ์ดเมนู 1-7: โชว์ 3 ข้อแรก + ปุ่มดูเพิ่มอีก N ข้อย่อลงได้ ต่อใบอิสระ
4. การ์ดโฟลว์ 7 ขั้น: ป้ายเมนูกดได้ กระโดดไป tab จริง (tab mapping ใหม่ใน FLOW_STEPS)
5. การ์ดแก้ปัญหา 4 อาการ: แยกเป็น TROUBLES constant + ปุ่มลัดเปิดเมนูที่เกี่ยวข้อง
6. FAQ: ช่องค้นหา (includes ไม่ใช้ regex) + ปุ่มเปิดทั้งหมด/ปิดทั้งหมด + จำนวนผล + empty state พร้อมปุ่มล้างคำค้น + เปิดหลายข้อพร้อมกันได้ (state number → array)

### Gate

- `npm test` — 151 passed
- `npm run build` — ผ่าน 4.22s
- `python -m compileall -q scripts` — ผ่าน
- `git diff --check` — สะอาด

**สิ่งที่ทำใน `frontend/src/components/UserGuide.jsx`:**
- โฟลว์ 7 ขั้น: `grid-cols-1/sm:2/xl:7` → `grid-cols-2/md:4/2xl:7` การ์ด `p-3.5/min-h-132` → `p-3/min-h-108` มือถือเห็น 2 ใบต่อแถว จอกว้าง 7 ใบรวดเดียว
- คลิปแรก 5 ข้อ: `space-y` → `grid lg:2` (3+2 วางข้างกัน)
- สถานะ 4 เฟส: `lg:4` → `xl:4` + items-start + padding 3→2.5
- โฟลเดอร์ 8 รายการ: `sm:2` → `sm:2/xl:4` (แถวละ 4 ใบ)
- เช็กลิสต์ 6 ข้อ: `space-y` → `grid lg:2` พร้อมกรอบการ์ดต่อข้อ
- แก้ปัญหา 4 อาการ: `sm:2` → `sm:2/xl:4` แถวเดียวจบ
- FAQ 6 ข้อ: `space-y` → `grid lg:2` accordion ยังกดขยายได้เหมือนเดิม
- ลด padding ทุก section `p-4 sm:p-5` → `p-4`, gap `2.5/3` → `1.5/2`

### Gate

- `npm test` — 151 passed
- `npm run build` — ผ่าน 3.69s
- `python -m compileall -q scripts` — ผ่าน
- `git diff --check` — สะอาด

### Gate

- `npm test` — 151 passed
- `npm run build` — ผ่าน 3.87s
- `python -m compileall -q scripts` — ผ่าน
- `git diff --check` — สะอาด

เพิ่มเมนูที่ 8 คู่มือใช้งาน (User Guide) แนบในโปรแกรม อธิบายโฟลว์หลักและวิธีใช้ละเอียดทุกเมนู 1-7 สวย อ่านง่าย ผู้ใช้ใหม่เข้าใจในหน้าเดียว

### สิ่งที่ทำ

- สร้าง `frontend/src/components/UserGuide.jsx`: PageHeader + สารบัญ 8 หัวข้อ + การ์ดโฟลว์ 7 ขั้น + รายละเอียดเมนู 1-7 พร้อมปุ่มกระโดดไปเมนูจริง + คลิปแรกใน 10 นาที + สถานะ 4 เฟส + โฟลเดอร์ 00-06 + เช็กลิสต์ก่อนโพสต์ + แก้ปัญหา 4 อาการ + FAQ 6 ข้อแบบ accordion
- ลงทะเบียนเมนู: `Sidebar.jsx` Desktop 8 items + More Drawer Option 4 + isMoreActive รวม guide, `Topbar.jsx` TAB_CONFIG guide (8. User Guide), `App.jsx` lazy import + section guide
- Clean UI: ปุ่มมีไอคอน Lucide ตัวเดียว ไม่มีสัญลักษณ์ซ้ำซ้อน ฟอนต์ไทยเดิม Responsive 1/2/7 คอลัมน์ตามจอ

### Gate

- `npm test` — 151 passed
- `npm run build` — ผ่าน 3.47s
- `python -m compileall -q scripts` — ผ่าน

### Notes

- แตะเฉพาะส่วนเมนูใหม่แบบ additive ไม่แก้ logic เดิมของไฟล์ที่มี working-tree changes ค้าง
- ลบ import ที่ไม่ใช้ (Smartphone, Keyboard) ให้ build ไม่มี warning

Date: 2026-09-07
Result: The prepare-details flow now applies the green completed row class when it marks step 4. Export metadata now falls back to a product-named cover such as `Logitech Wave Keys_cover.jpg`, allowing the extension to receive a cover path even when the cover filename does not match the video stem. Backend focused tests passed 6/6, extension tests passed 8/8, and Python compileall passed.

## Round POST-3.14 - Cover Studio entry and project-based cover names

Date: 2026-09-07
Result: Fixed the CoverStudioModal hook-order crash and rendered it through a top-level portal so the editor appears above the TikTok posting modal. Cover exports now use the canonical project name, with a video-stem fallback for legacy items. The remaining Logitech unboxing project was backed up and migrated to the LOG01 naming convention; schedule logic and steps 1-4 were left unchanged.

Evidence: backup archive created under D:/Winona/Programmer/Capcut_backups/; frontend tests 63 passed; Vite build passed; python compileall passed; focused TikTok backend tests 6 passed.

## Round POST-3.15 - Project-named cover lookup

Date: 2026-09-07
Result: /api/exports now checks <project_name>_cover.jpg (and the 3:4 variant) before using the legacy product-named cover fallback. This keeps the cover generated for each project attached to the matching export and preserves compatibility with older product-level covers.

Evidence: focused TikTok backend tests 8 passed with one existing Starlette/httpx deprecation warning; python -m compileall -q scripts passed.

---

## Round POST-3.19 - restore generated cover in TikTok post modal

Date: 2026-09-07; Requested by: user; Status: complete

**Evidence:** The generated 3:4 cover is now available in the TikTok preparation flow and the user confirmed that step 5 can upload it after the runtime was refreshed.

**Scope:** Trace the saved cover from the Editor callback through product refresh and TikTok modal state. Steps 1-4 and the extension upload flow remain unchanged.

### Todo

- [x] Reproduce the missing-cover state from the live `/api/products` response and modal mapping.
- [x] Reuse the existing deterministic persistence and 3:4 variant regression coverage (`tests/test_product_cover_persistence.py` and `frontend/src/lib/coverVariant.test.js`).
- [x] Confirm the smallest runtime gap: the running backend process predated the cover persistence commit; restarting it loaded the current API hydration code without a frontend mapping change.
- [x] Re-run frontend tests/build and relevant backend cover tests.
- [x] Confirm the modal/upload flow shows the saved cover after refresh (user verification).

### Gate

- [x] `python -m pytest tests/test_product_cover_persistence.py tests/test_api_tiktok_autopost.py -q -p no:cacheprovider --tb=short` - 14 passed, 1 existing warning
- [x] `npm test` - 65 passed
- [x] `npm run build` - passed
- [x] `git diff --check` - passed
- [x] Browser/extension flow - user confirmed cover upload now works

### Notes

- The live API returned null cover fields while an older backend process was still running; the current source-level API hydration resolves the saved project-named 3:4 file correctly.
- No code change was made in this verification round. Existing cover persistence/mapping code remains the source of truth, and steps 1-4 stay locked.

## Round POST-3.21 - Multi-day TikTok publishing queue

Date: 2026-09-07; Requested by: user; Status: complete

**Goal:** Replace the today-only Daily Run Sheet with a durable multi-day agenda that makes every scheduled export, date, and time unambiguous and can hand one selected queue item to the TikTok Extension.

**Scope:** Persist queue items by exported `video_path`; prevent duplicate scheduling; support single and bulk assignment, five-minute slots, chronological sorting, drag/reschedule, lifecycle states, and one-at-a-time Extension handoff. Steps 1-4, cover editing/upload, and the unrelated editor work remain unchanged.

### Todo

- [x] Add a backend schedule queue store/API with `video_path`, `scheduled_at`, status, and audit timestamps.
- [x] Replace today-only localStorage slots with a multi-day Agenda view grouped and sorted by Asia/Bangkok date/time.
- [x] Add single and bulk queue assignment with five-minute snapping, collision validation, and duplicate prevention.
- [x] Add drag/reschedule and explicit remove-from-queue actions with lifecycle guards.
- [x] Add one-item Extension preparation from the queue and preserve the existing manual checklist flow.
- [x] Add deterministic tests for persistence, uniqueness, sorting, collisions, state transitions, and API handoff.
- [x] Run frontend/backend tests, build, syntax checks, and browser verification.

### Gate

- [x] `python -m compileall -q scripts` and `python -m pytest tests/ -q -p no:cacheprovider --tb=short` ? 873 passed, 6 existing warnings.
- [x] `npm test` ? 82 passed.
- [x] `npm run build` ? passed.
- [x] `node --check` for extension scripts ? passed.
- [x] Browser smoke ? Agenda opened, single queue row rendered with date/time, date reschedule persisted, and remove returned the export to the ready pool. Bulk ordering, duplicate/collision guards, lifecycle locks, and extension handoff are covered by deterministic tests and the shared PATCH/prepare paths.

### Notes

- Queue identity is the stable export filename under `04_Exports`, so moving an MP4 to `Posted` can close the same queue row. Re-exporting creates a new filename identity.
- Queue records persist through the document/SQLite mirror and retain the schedule in `Asia/Bangkok` ISO timestamps.
- The Extension now prefers active queue rows, receives the scheduled date/time for the selected item, and keeps the existing fallback ready-export list when no queue exists.
- Removing a planned item never deletes the MP4. Items handed to the Extension must be reset before moving, and posted items are locked.
- Existing uncommitted editor work was intentionally left unstaged. Steps 1-4 and the extension upload implementation remain frozen by the user.

## Round STK-1 — Interactive Sticker Timeline Track, Free Canvas Drag/Resize, and Parity Render Engine

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**ปัญหาและสิ่งที่ทำ:**

1. **ไทม์ไลน์สติกเกอร์ไม่มี:** เพิ่มแทร็กสติกเกอร์ (Sticker Track) บนไทม์ไลน์ อยู่ใต้ป้ายฮุกและเหนือคำบรรยาย พร้อมไอคอน Smile, ชื่อสติกเกอร์, เวลาแสดงผลกี่วินาที `(start - end)`, Left Trim Handle, Right Trim Handle, และ Body Drag สำหรับเลื่อนเวลาทั้งก้อน
2. **ปรับย่อ/ขยายสติกเกอร์ได้อย่างอิสระ:** เพิ่มการคำนวณ `selectedBox.type === 'sticker'` ใน `handleBoxDragStart` และ `handleResizeStart` บน `SequencePlayer.jsx` ทำให้ผู้ใช้สามารถลากปุ่มกลม 4 มุมและปุ่มแคปซูล 4 ด้านเพื่อย่อขยายขนาดได้ตั้งแต่ 0.4× ถึง 2.0×
3. **เอาตัวเลือกตำแหน่งการวางสติกเกอร์ 6 จุดเดิมออก:** ลบปุ่ม 6 ตำแหน่ง (บนซ้าย, กึ่งกลางบน, ฯลฯ) ใน `AssetPanel.jsx` ออกตามคำขอของผู้ใช้ โดยเปลี่ยนเป็นการแสดงช่วงเวลาแสดงผล `(start - end)` พร้อมปุ่ม "จัดกึ่งกลาง" (Center Reset) และแถบสไลเดอร์ขนาด
4. **Preview = Render Parity 100%:** อัปเดต `video_editor.py` และ `video_assembly_stage.py` ให้ส่งและคำนวณ `sticker_start_time`, `sticker_end_time`, `sticker_norm_x`, `sticker_norm_y` ลงในคำสั่ง FFmpeg ด้วย `enable='between(t,start,end)'` และพิกัดจุดกึ่งกลางตรงกับหน้าจอพรีวิว 1:1

### Gate

- [x] `python -m compileall -q scripts` (Pass: 0 errors)
- [x] `pytest tests/test_preview_render_parity.py` (Pass: 149 passed)
- [x] `pytest tests/test_phase1_smoke.py` (Pass: 148 passed)
- [x] `pytest tests/test_sticker_input_index.py` (Pass: 5 passed)
- [x] `npm --prefix frontend run build` (Pass: 0 errors, built in 4.25s)
- [x] Live Browser Subagent Verification (Pass: ตรวจสอบแทร็กสติกเกอร์บนไทม์ไลน์, กรอบ interactive bounding box พร้อมจุดดึงขยาย 4 มุม 4 ด้าน, การลากวางอิสระ, และพาเนลตั้งค่าที่ลบ 6-pos grid ออกเรียบร้อย)

## Round POST-LIFECYCLE-1 — Export identity and posting lifecycle lock (2026-09-08)

- ต้นเหตุที่ตรวจพบ: MP4 เดียวกันมีสำเนาอยู่ทั้ง `Ready_to_post/` และ `Posted/` แต่ระบบเดิมสร้างรายการจาก path สองรายการ จึงดูเหมือนมีคลิปใหม่ซ้ำกัน
- เพิ่ม `export_id` ต่อ export version และส่งต่อครบตั้งแต่ render, Gallery, queue, Extension, mark-posted, delete, rename และ cover metadata
- สำเนา Ready ที่ byte-identical กับ Posted จะไม่ถูกถือเป็น latest/ไม่ถูกส่งเข้า Extension และยังลบได้ ส่วน Posted เป็นหลักฐานที่ล็อกไว้
- ปุ่มมาร์กโพสต์ทุกจุดต้องผ่าน `/api/exports/mark-posted`; API ปฏิเสธการเปลี่ยนสถานะเป็น posted โดยไม่มี `export_id` และตรวจ ID ตรงกับ path
- ข้อมูลจริงของ GOCHEK ถูก reconcile ให้ชี้ `04_Exports/Posted/..._20260908_190309.mp4` พร้อม `exp_982f701ea975462b87d0fc9dfb7cebf9`
- Gate: `pytest tests/` 940 passed, 1 deselected, 6 warnings; Node Extension 17 passed; frontend 86 passed; build และ compileall ผ่าน

## Round PRO-STYLE-1 — Professional Editing Style System: Phase 1 Style Contract + Golden Master

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** วางสัญญากลางสำหรับการตัดต่อแบบมืออาชีพ เพื่อให้โค้ดกลางรองรับ Style Preset ที่ควบคุม pacing, motion, transition, color, typography และ audio โดยไม่ hardcode รูปแบบลงทุกโปรเจกต์

**ขอบเขตการกันชนกับงานขนาน:** ไฟล์ editor/backend ที่มี working-tree diff ของ Claude ไม่ถูกแตะในเฟสนี้; รอบนี้ทำเอกสารและ acceptance contract เท่านั้น จึงไม่มีการเปลี่ยนพฤติกรรม Preview/Render

### Todo

- [x] ตรวจ inventory ของ Hook/Text Template, motion preset, transition, effect, color และ audio contract ที่มีอยู่ แล้วบันทึกช่องว่างระหว่าง “template เฉพาะองค์ประกอบ” กับ “editorial style ทั้งคลิป” ใน `PRO_EDITOR_STYLE_PLAN.md`
- [x] กำหนด Golden Master style แรก `clean_tech_review` สำหรับคลิปรีวิวสินค้าแนวตั้ง: Hook → Problem → Demo/Proof → Verdict → CTA
- [x] กำหนด Style Contract ที่เป็นข้อมูล: pacing windows, motion budget, transition policy, typography hierarchy, color palette, audio mix และ safe-zone rules โดยแยก invariant ออกจากค่าที่ preset เปลี่ยนได้
- [x] กำหนด acceptance rubric ก่อน/หลังสำหรับ one-click output โดยไม่อ้างว่า viral หรือ 10/10 เป็นสิ่งรับประกัน
- [x] ล็อกแผน integration เฟสถัดไปให้ใช้ preset เป็นข้อมูลต่อโปรเจกต์ และรักษา Preview = Render parity

### Gate

- [x] ตรวจว่าเอกสารระบุไฟล์/โมดูลที่มีอยู่และไม่ขัดกับ `TEMPLATE_MOTION_PLAN.md`
- [x] ตรวจว่า Golden Master มีเกณฑ์วัดได้ครบ pacing, motion, transition, color, typography และ audio
- [x] `git diff --check` ผ่าน — exit 0; มีเฉพาะคำเตือน line-ending ของไฟล์เดิม
- [x] ยืนยันว่าเฟสนี้ไม่มี source-code behavior change และไม่แตะไฟล์ที่มี diff ของ Claude; diff ของรอบนี้มีเฉพาะ `TODO.md`, `HISTORY.md` และ `PRO_EDITOR_STYLE_PLAN.md`

### Notes

- สร้าง `PRO_EDITOR_STYLE_PLAN.md` เป็นแผนหลักของงาน 6 phases
- กำหนด `clean_tech_review` เป็น Golden Master แรกสำหรับคลิปรีวิวสินค้า/อุปกรณ์ไอที
- ล็อกหลักการว่า Prompt ใช้จัดประเภทเนื้อหาได้ แต่ timing, clamp, z-order, audio mix และ Render ต้องเป็น deterministic rule
- Phase 2 ต้องตรวจ ownership ใหม่ก่อนแตะ `Timeline.jsx`, `SequencePlayer.jsx`, `scripts/video_editor.py` หรือ `scripts/subtitle/*` เพราะมี working-tree diff ของ Claude อยู่ในขณะปิดเฟสนี้

## Round PRO-STYLE-2 — Editorial Beat Map + Pacing Core (Phase 2A)

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** สร้าง pure module สำหรับ normalize transcript timing, ตรวจ gap/Dead Air และสร้าง candidate pacing beats จาก word timestamps กับ scene boundaries โดยไม่ตัดสินใจสร้างสรรค์แทนผู้ใช้และไม่เปลี่ยน render flow เดิม

**ขอบเขตการกันชนกับงานขนาน:** เพิ่มเฉพาะ `scripts/editorial_pacing.py` และ `tests/test_editorial_pacing.py`; ไม่แตะ `api_render.py`, `video_editor.py`, `Timeline.jsx`, `SequencePlayer.jsx` หรือไฟล์อื่นที่มี working-tree diff ของ Claude

### สิ่งที่ทำ

- เพิ่ม `PacingPolicy` ที่กำหนด short pause, cut gap, target/min/max beat interval และ boundary tolerance
- เพิ่ม deterministic word normalization ที่รองรับ `text`/`word`, `start`/`start_time`, `end`/`end_time`, ทิ้งเวลาผิดและไม่เลื่อน timestamp ที่ถูกต้อง
- เพิ่ม silence gap classification เป็น `short_pause` หรือ `cut_candidate` โดยไม่ตัดกลางคำ
- เพิ่ม scene/interval beat candidates ที่ snap ได้เฉพาะขอบเขต word-free และให้ scene beat มี priority เมื่อระยะเท่ากัน
- เพิ่ม serializable `build_pacing_plan()` สำหรับจุดเชื่อมต่อ Phase 2B
- เพิ่ม regression tests ครอบคลุม malformed records, clamping, silence, safe boundary, duplicate scene boundaries, deterministic output, empty input และ invalid policy

### Gate

- [x] `python -m pytest tests/test_editorial_pacing.py -q -p no:cacheprovider --tb=short` — `6 passed`
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `git diff --check` — exit 0; มีเฉพาะคำเตือน line-ending ของไฟล์เดิม
- [x] ไฟล์ source/test ที่เพิ่มในรอบนี้มีเฉพาะ `scripts/editorial_pacing.py` และ `tests/test_editorial_pacing.py`; existing Claude diffs ไม่ถูกเขียนทับ
- [x] Preview/Render parity ยังไม่ถูกติ๊ก เพราะ Phase 2A ยังไม่ถูกเรียกจาก render pipeline

### Notes

- Phase 2A เป็น isolated foundation เท่านั้น ยังไม่เปลี่ยน output ของโปรเจกต์เดิม
- Phase 2B ต้องเลือก transcript source schema และ integration seam ก่อน และต้องรอ ownership ของไฟล์หลักให้ชัดเจน

## Round PRO-STYLE-2B — Integrate editorial pacing plan into subtitle pipeline and project manifest

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จสมบูรณ์

### ผลงาน

- เพิ่ม `build_pacing_plan_from_cues()` เพื่อรวม absolute `cues[*].word_timings` และ cue boundaries เป็น pacing plan แบบ deterministic
- เชื่อม plan เข้า `SubtitleStage` ก่อน micro-cue mutation, `PipelineContext` และ project manifest
- เพิ่ม plan ใน subtitle incremental-render fingerprint; โปรเจกต์เก่าที่ไม่มี word timing ยังคง no-op และใช้ flow เดิม
- เพิ่ม integration contracts ครอบคลุม valid/malformed/legacy timing และ context/fingerprint persistence

### Gate

- [x] `python -m pytest tests/test_editorial_pacing.py tests/test_editorial_pacing_integration.py -q -p no:cacheprovider --tb=short` — 12 passed
- [x] `python -m pytest tests/test_pipeline_stages.py tests/test_incremental_render_reuse.py -q -p no:cacheprovider --tb=short` — 19 passed
- [x] `python -m pytest tests/test_preview_render_parity.py tests/test_editorial_pacing.py tests/test_editorial_pacing_integration.py -q -p no:cacheprovider --tb=short` — 162 passed
- [x] `python -m compileall -q scripts` — Pass
- [x] `git diff --check` — Pass; line-ending warnings only

### ข้อจำกัด

- รอบนี้ persist pacing plan เท่านั้น ยังไม่ apply beat เป็น FFmpeg cut จึงยังไม่มี visual/render gate สำหรับ behavior ใหม่นี้
- compatibility subset พบ `test_create_edit_save_reload_full_fidelity` ได้ HTTP 401 จาก auth guard; ไม่ใช่ผลจาก pacing change และไม่สรุปว่า full suite ผ่าน
- พบ working-tree changes นอก scope ใน `scripts/api_exports.py` และ `tests/test_post_lifecycle.py`; ไม่ได้แก้หรือ stage
| Round PRO-STYLE-2B | Integrate editorial pacing plan into subtitle pipeline and project manifest | 2026-09-09 | `build_pacing_plan_from_cues()` + PipelineContext/manifest persistence + subtitle fingerprint; 12 integration tests, 19 pipeline/incremental tests, and 162 parity subset tests passed; no FFmpeg cut behavior change |

## Round PRO-STYLE-2C — Apply editorial beat boundaries to generated clip list with Preview = Render parity

วันที่: 2026-09-09 · สถานะ: เสร็จสมบูรณ์

### ผลงาน

- เพิ่ม `resolve_pacing_boundaries()` สำหรับ validate duration, กรอง beat ใกล้ขอบ, deduplicate และ fallback อย่าง conservative
- เชื่อม resolver ที่ `ShotMatchingStage` เฉพาะ auto-generated clips; manual clip list และ legacy manifest ยังใช้ flow เดิม
- ปิด legacy merge/motion/beat snapping เมื่อมี editorial pacing เพื่อให้ beat boundaries เป็น timing truth เดียว
- รักษา AI shot anchoring โดยเลื่อน source offset ตาม segment ที่แบ่งภายใน cue เดียวกัน
- เพิ่ม contract tests สำหรับ generated boundaries และ manual clip preservation

### Gate

- [x] `python -m pytest tests/test_editorial_pacing.py tests/test_editorial_pacing_integration.py tests/test_shot_matching_pacing.py -q -p no:cacheprovider --tb=short` — 15 passed
- [x] `python -m pytest tests/test_preview_render_parity.py tests/test_preview_render_behavior.py -q -p no:cacheprovider --tb=short` — 161 passed, 2 deprecation warnings
- [x] `python -m pytest tests/test_pipeline_stages.py tests/test_incremental_render_reuse.py tests/test_clip_compounding_render.py -q -p no:cacheprovider --tb=short` — 21 passed
- [x] `python -m pytest ... -k "is_quota or shot_matching or script_stage or voice_stage"` — 10 passed
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 975 passed, 6 dependency/deprecation warnings
- [x] `cd frontend; npm test` — 126 passed
- [x] `cd frontend; npm run build` — 1,975 modules transformed; build passed
- [x] `python -m compileall -q scripts` — passed
- [x] `git diff --check` — exit 0; line-ending warnings only

### ข้อจำกัด

- การรัน API subset แยกครั้งแรกพบ 401 ใน auth cases แต่ backend suite ทั้งชุดรันตามลำดับปกติผ่านครบ 975 tests; จึงไม่มี unresolved test failure จากรอบนี้
- ไม่ได้แตะหรือ stage งานภายนอกใน `scripts/api_exports.py` และ `tests/test_post_lifecycle.py`
| Round PRO-STYLE-2C | Apply editorial beat boundaries to generated clip list with Preview = Render parity | 2026-09-09 | Resolver + generated clip-list integration + manual/legacy preservation; 15 contract tests, 161 render parity/behavior tests, 21 pipeline regression tests, and 975 full backend tests passed |

## Round PRO-STYLE-3A — Style-driven transition budget and project style preset contract

วันที่: 2026-09-09 · สถานะ: เสร็จสมบูรณ์

### ผลงาน

- เพิ่ม `style_motion_policy.py` เป็น pure policy กลางสำหรับ Golden Master `clean_tech_review`
- เพิ่ม `style_preset` ผ่าน RenderRequest, reroll/state-save request, Pipeline, PipelineContext, manifest และ incremental-render fingerprint
- ใช้ transition budget กับ auto-generated clip list เท่านั้น: hard cut เป็นฐาน 80%, movement transition ตามรอบที่กำหนด และ stylized transition ถูกลดความถี่/จำกัด duration
- manual clip list และ manual transition list ยังคงเป็นข้อมูลที่ผู้ใช้ควบคุมเอง
- Preview และ FFmpeg ยังคงใช้ transition/clip contract เดียวกัน จึงไม่สร้าง renderer path ใหม่ในเฟสนี้

### Gate

- [x] `python -m pytest tests/test_style_motion_policy.py tests/test_shot_matching_pacing.py -q -p no:cacheprovider --tb=short` — 7 passed
- [x] `python -m pytest tests/test_preview_render_parity.py tests/test_preview_render_behavior.py -q -p no:cacheprovider --tb=short` — 161 passed, 2 deprecation warnings
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 980 passed, 6 warnings
- [x] `python -m compileall -q scripts` — passed
- [x] `cd frontend; npm test` — 126 passed
- [x] `cd frontend; npm run build` — 1,975 modules transformed; passed
- [x] `git diff --check` — exit 0; line-ending warnings only

### ขอบเขต/ข้อควรทราบ

- เฟสนี้จัดการ transition hierarchy และ project style contract ก่อน; active camera keyframe/pan motion จะอยู่ในเฟสถัดไป เพราะต้องเพิ่ม parity contract และ render หลายเฟรมแยกต่างหาก
- ไม่ได้แตะหรือ stage งานภายนอกที่ตรวจพบใน `scripts/api_exports.py`, `tests/test_post_lifecycle.py` และ `tiktok_autopost_extension/sidepanel.js`
| Round PRO-STYLE-3A | Style-driven transition budget and project style preset contract | 2026-09-09 | `clean_tech_review` policy + project manifest/fingerprint contract + auto-transition budget; 7 policy tests, 161 parity/behavior tests, 980 backend tests, 126 frontend tests, and build passed |

## Round PRO-STYLE-3B — Live keyframe camera motion with Preview = Render parity

วันที่: 2026-09-09 · สถานะ: เสร็จสมบูรณ์

**เป้าหมาย:** ทำให้ `zoom`, `pan_x` และ `pan_y` ใน `clip.keyframes` มีผลจริงระหว่าง playback และ FFmpeg render โดยใช้ interpolation/clamp contract เดียวกัน และคงพฤติกรรมเดิมของคลิปที่ไม่มี keyframe

### สิ่งที่ทำ

- เพิ่ม live camera transform resolver ใน `frontend/src/lib/timelineMath.js` และใช้ `motionTimeAt` แยกจาก source seek time เพื่อประเมิน keyframe ตามเวลาที่เล่นจริงหลัง speed/freeze-tail
- เชื่อม `SequencePlayer.jsx` ให้ทุก video draw path ใช้ `resolveClipTransforms` สำหรับ zoom/pan แบบ per-frame และรวม `keyframes` ใน clip invalidation key
- เพิ่ม FFmpeg dynamic camera filter ใน `scripts/video_editor.py` สำหรับ clip-list ที่มี camera keyframe; clip ที่ไม่มี keyframe คง static fast path เดิม
- เพิ่ม `camera_keyframes_for_clip` ใน `scripts/style_motion_policy.py` และให้ auto-generated clips มี push/pan แบบ restrained เฉพาะ clip สลับลำดับและยาวอย่างน้อย 0.8 วินาที; manual keyframes ยังคง user-owned
- รักษาการทำงานของ speed, freeze tail, mirror, rotation, background blur, colour correction และ audio bus เดิม
- ใช้ clamp contract เดียวกัน: zoom `1.0–3.0`, pan X/Y `-1.0–1.0`; interpolate ก่อน clamp เพื่อให้ค่ากลาง deterministic

### ไฟล์ที่แตะ

- `frontend/src/lib/timelineMath.js`
- `frontend/src/lib/timelineMath.test.js`
- `frontend/src/components/SequencePlayer.jsx`
- `scripts/video_editor.py`
- `scripts/style_motion_policy.py`
- `scripts/stages/shot_matching_stage.py`
- `tests/test_keyframe_interpolation.py`
- `tests/test_camera_motion_parity.py`
- `tests/test_preview_render_behavior.py`
- `tests/test_style_motion_policy.py`
- `tests/test_shot_matching_pacing.py`
- `PRO_EDITOR_STYLE_PLAN.md`

### Gate ผลจริง

- `python -m pytest tests/test_keyframe_interpolation.py tests/test_camera_motion_parity.py tests/test_style_motion_policy.py tests/test_shot_matching_pacing.py -q -p no:cacheprovider --tb=short` → **17 passed**
- `python -m pytest tests/test_preview_render_parity.py -q -p no:cacheprovider --tb=short` → **151 passed**
- FFmpeg multi-frame behavioral render (เข้า/กลาง/ออก) → **1 passed**
- `python -m pytest tests/ -q -p no:cacheprovider --tb=short` → **989 passed, 9 warnings** ใน 119.37 วินาที
- `python -m compileall -q scripts` → ผ่าน
- `npm test` → **128 passed**
- `npm run build` → ผ่าน, **1,975 modules transformed**
- `git diff --check` → ผ่าน; มีเฉพาะคำเตือน line-ending LF → CRLF ของ Git

### Notes

- warnings ที่เหลือเป็น deprecation/optional audio warnings ใน dependency หรือ test เดิม ไม่ใช่ failure ของ camera motion
- การตรวจ FFmpeg วัดจำนวนพิกเซลของ marker ในเฟรมเข้า/กลาง/ออก เพื่อยืนยันว่า pan เปลี่ยนจริงและไม่หลุด crop bounds
- ไม่ได้แตะหรือ stage งานภายนอกที่พบก่อนเริ่ม: `scripts/api_exports.py`, `tests/test_post_lifecycle.py`, `tiktok_autopost_extension/sidepanel.js`

| Round PRO-STYLE-3B | Live keyframe camera motion with Preview = Render parity | 2026-09-09 | Live zoom/pan keyframes in Canvas + FFmpeg, restrained auto-generated camera motion, 17 focused tests, 151 parity tests, 989 full backend tests, 128 frontend tests, FFmpeg behavioral render, and build passed |

## Round STYLE-ONECLICK-1 — Style Presets + Fresh One Click routing

วันที่: 2026-09-10 · ผู้สั่ง: user · สถานะ: เสร็จแล้ว

**ผลลัพธ์:** ผู้ใช้เลือกสไตล์การตัดต่อได้ตั้งแต่หน้า One Click และปุ่ม “ส่งตัดต่อ” เปิดฟอร์มสร้างคลิปใหม่เสมอ แม้มีโปรเจกต์เก่าค้างใน URL, localStorage หรือข้อมูลมุม ส่วนปุ่ม “เปิดไทม์ไลน์” ยังเปิดโปรเจกต์เดิมตามเจตนา

### สิ่งที่ทำ

- เพิ่ม preset ที่ renderer รองรับจริง 4 แบบ: `viral_punch`, `clean_tech_review`, `smooth_showcase`, `premium_minimal`
- กำหนด transition family/budget, camera-motion cadence และ accent palette แยกตาม preset; One Click ใหม่เริ่มที่ `viral_punch` แต่คง fallback เดิมเป็น `clean_tech_review` สำหรับข้อมูลเก่า/ค่าที่ไม่รู้จัก
- เพิ่ม `StylePresetPicker` กลาง ใช้ร่วมกันในหน้า One Click และแท็บ Style ของ Editor
- ส่ง `style_preset` จาก One Click ถึง RenderRequest, shot matching, subtitle/overlay และ video assembly
- เพิ่ม fresh-editor intent กลางซึ่งชนะ URL/localStorage/angle fallback; Tracker ส่งชื่อโปรเจกต์เฉพาะ action “เปิดไทม์ไลน์”
- เพิ่ม regression tests สำหรับ routing intent, catalog/payload, motion/transition policy, pipeline integration และ Preview = Render palette

### Gate ผลจริง

- `python -m compileall -q scripts` → ผ่าน
- `python -m pytest tests/ -q -p no:cacheprovider --tb=short` → **1,034 passed, 24 warnings** ใน 135.26 วินาที
- FFmpeg style render → **4 presets × 3 เฟรม (เข้า/ค้าง/ออก) ผ่านครบ 12 เฟรม**
- `npm test` → **144 passed**
- `npm run lint` → exit 0; มี warnings เดิมของ repo ไม่มี error
- `npm run build` → ผ่าน, **1,979 modules transformed**
- Impeccable detector → ส่วน Style Picker ใหม่ไม่พบ antipattern; พบ warning เดิม `gray-on-color` ใน AssetPanel import button 1 จุดนอก scope
- `git diff --check` → ผ่าน; มีเฉพาะคำเตือน line-ending LF → CRLF ของ Git

### Notes

- ไม่แตะไฟล์สื่อหรือโปรเจกต์จริงใน `01_Raw/`, `02_Assets/`, `03_Projects/`
- รักษา working-tree changes เดิมใน `ContentTrackerHub.jsx`, `EditorShell.jsx`, `AssetPanel.jsx` และไฟล์ renderer/tests ที่มีงานค้างอยู่
- ระหว่างรอบพบการแก้ไฟล์อื่นเพิ่มจากงานคู่ขนาน เช่น Sidebar/Topbar และ status tests; ไม่ได้แก้หรือตีความงานเหล่านั้นเป็นส่วนของรอบนี้

## Round DOC-SYNC-1 — Sync สถานะเอกสารจากผลทดสอบล่าสุด

วันที่: 2026-09-10 · ผู้สั่ง: user · สถานะ: เสร็จแล้ว

### ผลลัพธ์

- ปิดสถานะเอกสารของ `TLO-REFACTOR-FINAL-AUDIT`, `POST-LIFECYCLE-1`, `HOOK-OPT-1` และ `PRO-STYLE-PARALLEL-4-6` ตามหลักฐาน implementation/test ล่าสุด
- อัปเดต full pytest จากค่าประวัติเดิมที่เคย fail เป็นค่าปัจจุบัน `1,034 passed, 24 warnings`
- ปิด `PERF-UX-1` เฉพาะระดับ implementation และ deterministic evidence; React Profiler, production rerender และ browser FPS 50/100/300 ถูกระบุเป็น deferred validation อย่างชัดเจน และไม่มีการอ้าง performance improvement
- คงงานที่ต้องใช้ user/live environment ไว้: TikTok/Chrome Cover Studio ขั้นตอน 5 และปัญหาสระไทยที่ยังตรวจภาพจริงไม่ผ่าน
- คง `SEC-AUDIT-1` เป็นงานเปิด เพราะ SYSTEM_AUDIT_FIX_PLAN ยังมี Phase 0 และ Phase 2 ที่ไม่ได้มีหลักฐานปิดครบ

### Gate

- ตรวจ `TODO.md`, `HISTORY.md`, plan files และสถานะ Git แล้ว
- ไม่แก้ source code หรือไฟล์สื่อในรอบนี้
- `git diff --check` ผ่านก่อนบันทึกเอกสาร

## Round TLO-REFACTOR-FINAL-AUDIT — ตรวจ final gates และ inventory หลัง refactor ทั้งชุด

วันที่: 2026-09-09 · สั่งโดย: user · สถานะ: เสร็จแล้ว — overlay scope และ repo-wide validation ปัจจุบันผ่าน

**เป้าหมาย:** ตรวจหลักฐาน end-to-end ของ Overlay Timeline/Preview refactor หลังรอบ TLO-REFACTOR-1 ถึง 7 และยืนยัน duplication/behavioral divergence ที่เหลือก่อน sign-off

### Todo

- [x] ตรวจ `TODO.md`, `git status`, refactor plan และขอบเขตไฟล์ค้าง โดยไม่แตะงานของ agent อื่น
- [x] รัน frontend `npm test`, `npm run lint`, `npm run build` และ `git diff --check`
- [x] รัน `python -m compileall -q scripts`
- [x] รัน preview/render parity, FFmpeg behavioral tests และ overlay dispatch tests
- [x] รัน full pytest ของทั้ง repo — ล่าสุด `1,034 passed, 24 warnings`; ไม่พบ failure
- [x] ตรวจ source inventory ของ Timeline, drag hook, SequencePlayer, editor modules และ lib ว่าจุดซ้ำหลักถูกจัดการแล้วหรือมี divergence ที่ต้องคงไว้
- [x] อัปเดต plan พร้อมตัวเลขจริง และรายงาน residual risks/งานที่ไม่รวม
- [x] แก้ `TrackLabel` fallback `width ?? GUTTER` ที่หายไประหว่าง extraction และย้าย source-contract probes ให้ตรวจ module ใหม่

### Notes

- รอบนี้เป็น audit/sign-off; พบและแก้ production regression จริงที่ `TrackLabel.jsx` โดยคืน `width ?? GUTTER` และปรับ parity probes ให้ตาม source module ใหม่
- Latest frontend working-tree gate: `npm test` = `144 passed, 0 failed`; `npm run lint` exit 0 (มี warnings เดิม); `npm run build` = `1,979 modules transformed`; `git diff --check` ผ่าน
- Overlay/backend scope: `compileall` ผ่าน; `test_preview_render_parity.py` = `150 passed`; `test_preview_render_behavior.py` = `11 passed, 2 warnings`; `test_overlay_render_dispatch.py` = `2 passed`
- Full pytest ชุดปัจจุบันผ่าน `1,034 passed, 24 warnings`; live TikTok validation แยกเป็นงานรอ user
- Overlay scope sign-off ผ่าน: shared timeline shell/label/pointer lifecycle, selected-box geometry, inspector primitives และ render-kind profile ถูกตรวจแล้ว; type-specific policy branches ยังคงแยกตาม behavioral contract

### Gate

- [x] `npm test` — `144 passed, 0 failed`
- [x] `npm run lint` — exit 0; มี warnings แต่ไม่มี error
- [x] `npm run build` — `1,979 modules transformed`, ผ่าน
- [x] `git diff --check` — ผ่าน
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `python -m pytest tests/test_preview_render_parity.py -q -p no:cacheprovider --tb=short` — `150 passed`
- [x] `python -m pytest tests/test_preview_render_behavior.py -q -p no:cacheprovider --tb=short` — `11 passed, 2 warnings`
- [x] `python -m pytest tests/test_overlay_render_dispatch.py -q -p no:cacheprovider --tb=short` — `2 passed`
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — `1,034 passed, 24 warnings`

## Round HOOK-OPT-1 — ยกระดับฟอนต์ข้อความ, เทมเพลตคลีน, พรีวิวขยาย/ย้ายฮุกสมบูรณ์ และสปีดแอนิเมชัน

วันที่: 2026-09-08 · สั่งโดย: user · สถานะ: เสร็จแล้วตามขอบเขตโค้ดและ deterministic gates

### ขอบเขตและผลลัพธ์

- รองรับ Master Scale, พิกัด `x/y` จริง และ resize/move ของ Hook ให้ Preview = Render parity
- เพิ่ม Master Font และ Per-Tier Font Override ผ่าน frontend/backend hook style contracts
- แยก AssetPanel เป็นป้ายฮุก 3-Tier กับข้อความเดี่ยว/เอฟเฟกต์, รวมช่องค้นหา, และลบสัญลักษณ์ UI ซ้ำซ้อน
- เพิ่มตัวเลือก animation speed และ Kinetic Word Stagger

### Gate

- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `python -m pytest tests/test_preview_render_parity.py -q -p no:cacheprovider` — `149 passed`
- [x] `python -m pytest tests/test_posted_protection.py tests/test_clip_compounding_render.py -q -p no:cacheprovider` — `8 passed`
- [x] `npm --prefix frontend run build` — ผ่าน, `1,962 modules transformed`
- [x] Full Pytest Regression — `923 passed`

### Notes

- Master scale, `\\pos(x, y)`, Badge Accent geometry และ Canvas/ASS mapping ถูกตรวจตาม parity contract
- การปิดรอบนี้ครอบคลุม implementation และ deterministic gates; visual/live validation ที่ต้องใช้ environment ภายนอกไม่ถูกตีความเกินหลักฐาน

## Round BUG-MARK-POSTED-1 — แก้ปุ่ม “มาร์กว่าลงโพสต์แล้ว” แจ้งสำเร็จแต่การ์ดยังไม่ย้ายสถานะ

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จแล้ว

### อาการและ root cause

- ผู้ใช้กด “มาร์กว่าโพสต์แล้ว” แล้วได้รับ toast สำเร็จ แต่การ์ดยังค้างในคอลัมน์ `rendered`
- `/api/exports/mark-posted` ย้าย MP4 ไป `Posted/` ก่อนอัปเดต `ProductStore`
- `ProductStore.update_angle_status()` ตรวจว่า `export_id` ต้องตรงกับพาธใน `ExportRegistry`; registry ยังชี้ `Ready_to_post/` จึงเกิด `export_id ไม่ตรงกับ video_url ของไฟล์ที่เลือก`
- endpoint เดิมจับ exception เป็น `status_warning` แต่ยังตอบ `success: true` ทำให้ UI แจ้งสำเร็จทั้งที่ angle ไม่ถูกบันทึก

### การแก้

- ย้าย `ExportRegistry.move_and_mark_posted()` ให้ทำงานหลังย้ายไฟล์และก่อน `ProductStore.update_angle_status()` เพื่อให้ registry ชี้ `Posted/` ก่อน path validation
- คง `export_id`, `posted_at`, `video_url` และไฟล์จริงให้เป็น identity เดียวกันตลอด flow
- ไม่แตะ diff ของ `ContentTrackerHub.jsx`, `CoverStudioModal.jsx`, `EditorShell.jsx` หรือไฟล์งานอื่นของ agent อื่น

### Gate

- [x] ก่อนแก้ regression reproduce ได้: HTTP `200` พร้อม `status_warning` และ angle ไม่เปลี่ยนสถานะ
- [x] `tests/test_post_lifecycle.py` — `15 passed`
- [x] Full backend suite — `1,035 passed, 24 warnings`
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `git diff --check` — ผ่าน

## Round PRODUCT-METADATA-1 — แนบรูปย้อนหลังและเปิดดู Metadata ที่ AI ใช้

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จแล้วตามขอบเขตโค้ดและ deterministic gates

### ผลลัพธ์

- เพิ่มปุ่ม `ข้อมูล AI` ในแถบเครื่องมือของสินค้าเดิม เพื่อเปิด `ProductMetadataModal`
- แสดง metadata ต้นทางครบในระดับสินค้า: ชื่อ, รหัส, platform, category, URL, ราคา, กลุ่มเป้าหมาย, timestamps, description, raw text, specs, selling points, pain points, thumbnail และรูปอ้างอิง
- เพิ่มส่วน “ข้อมูลที่ AI จะได้รับ” และ JSON source snapshot เต็ม เพื่อให้ตรวจได้ว่าข้อมูลใดถูกเก็บไว้สำหรับ Content Matrix และ per-angle reroll
- แก้ `selectProduct()` ให้รักษา source fields ที่เดิมถูกย่อเหลือเฉพาะ `selling_points` จึงไม่ทำให้คำอธิบาย/raw text หายจากหน้าตรวจสอบ
- เพิ่มแนบรูปย้อนหลังได้สูงสุด 20 รูปต่อสินค้า รูปถูกอัปโหลดเข้า `inbox` แล้วบันทึกที่ `product.images`; รองรับทั้ง URL รูปจาก scraper และ object path จาก upload รุ่นใหม่
- เพิ่มเอารูปออกจาก reference list โดยไม่ลบไฟล์ต้นฉบับจริง เพื่อป้องกันการลบข้อมูลโดยไม่ตั้งใจ
- เพิ่ม `ProductUpdateRequest.images` แบบ permissive เพื่อรักษาความเข้ากันได้กับ product records รุ่นเก่าที่เก็บรูปเป็น URL string

### ไฟล์ที่เกี่ยวข้อง

- `frontend/src/components/ProductToClip.jsx`
- `frontend/src/components/ProductMetadataModal.jsx`
- `scripts/api_phase1.py`
- `tests/test_product_metadata.py`

### Gate

- [x] `python -m pytest tests/test_product_metadata.py -q -p no:cacheprovider --tb=short` — `2 passed, 1 warning`
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short --durations=20` — `1,037 passed, 24 warnings` ใน `128.13s`
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `npm run lint` — exit 0; warnings เดิมของโปรเจกต์ ไม่มี error ใหม่
- [x] `npm test` — `144 passed, 0 failed`
- [x] `npm run build` — `1,980 modules transformed`, ผ่าน
- [x] Impeccable UI detector — ไม่พบ violation ใหม่ (`[]`)
- [x] `git diff --check` — ผ่าน

### Notes

- ยังไม่ได้ทำ browser live click-through ด้วยบัญชีจริง; รอบนี้ยืนยันจาก API contract, component build และ automated gates เท่านั้น
- ยังไม่ได้ commit ตามคำขอรอบนี้; working tree ยังมี diff ของรอบก่อน/agent อื่นอยู่ จึงไม่รวม commit ให้โดยอัตโนมัติ

## Round PRODUCT-METADATA-2 — เติม source fallback ให้สินค้า legacy

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จแล้วตามขอบเขตโค้ดและ deterministic gates

### Root cause ที่ยืนยันแล้ว

- Product `20260904233315_1` (`Logitech Wave Keys`) ใน `_Docs/products.json` มี `url` ว่าง, `description`/`raw_text` ไม่มีค่า, `specs`/`pain_points`/`selling_points` เป็นรายการว่าง และ `images` ว่าง
- ข้อมูลที่ใช้สร้างสคริปต์เดิมยังอยู่ในแต่ละ angle เช่น `key_features`, `pain_point`, `price_deal` แต่ไม่ได้ถูกเก็บเป็น product-level source metadata
- ผลคือ Metadata Inspector แสดง “ไม่มีข้อมูล” และ per-angle reroll ที่อ่าน `product.description`, `product.raw_text`, `product.images` ได้บริบทน้อยกว่าที่สคริปต์เดิมมี

### การแก้

- เพิ่ม `_with_product_source_fallback()` ใน `scripts/api_products.py` ให้สรุป `key_features` เป็น description/selling points และ `pain_point` เป็น pain points เฉพาะเมื่อ product-level field ว่าง
- เติม `raw_text` จากชื่อสินค้าและข้อมูล angle เดิมเฉพาะกรณีที่ raw source ว่าง
- ติด `metadata_source: derived_from_angles` เพื่อให้ UI ระบุชัดว่าเป็นข้อมูลย้อนกลับจากสคริปต์เดิม ไม่ใช่การ scrape หน้าเว็บใหม่
- ใช้ helper เดียวกันกับ `/api/products` และ per-angle reroll ทำให้สิ่งที่ Metadata Inspector แสดงตรงกับ source ที่ AI reroll ได้รับ
- ไม่เขียนทับ `_Docs/products.json` และไม่แปลงข้อมูล derived ให้กลายเป็น raw source ถาวร

### Gate

- [x] ก่อนแก้ regression test ล้มตามอาการ: import fallback seam ยังไม่มี (`ImportError`)
- [x] `python -m pytest tests/test_product_metadata.py -q -p no:cacheprovider --tb=short` — `4 passed, 1 warning`
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short --durations=5` — `1,040 passed, 24 warnings` ใน `137.94s`
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `npm run lint` — exit 0; warnings เดิมของโปรเจกต์ ไม่มี error ใหม่
- [x] `npm test` — `144 passed, 0 failed`
- [x] `npm run build` — `1,980 modules transformed`, ผ่าน
- [x] `git diff --check` — ผ่าน

### Notes

- Fallback นี้ช่วยให้ legacy product ใช้บริบทจากสคริปต์เดิมได้ทันที แต่ไม่ควรตีความเป็นคำอธิบายที่ scraper ยืนยันจากหน้าร้าน
- หากต้องการข้อมูลหน้าร้านจริงของ Logitech รายการนี้ ให้แนบ screenshot/spec sheet ผ่าน `ข้อมูล AI` หรือสร้าง/เติม source URL ใหม่

## Round SCRIPT-ANGLE-METADATA-1 — ล็อกหัวข้อเดิมและแสดงประเภทเนื้อหา

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จแล้ว

**เป้าหมาย:** ให้การเจนสคริปต์ใหม่ยังอยู่ในหัวข้อ/มุมเดิมอย่างตรวจสอบได้ และให้ผู้ใช้เห็นว่าเนื้อหาเป็นสเปก เปรียบเทียบ การใช้งานจริง หรือ FAQ ได้หลายประเภทในหัวข้อเดียว

### สิ่งที่ทำ

1. เพิ่ม catalog กลางของประเภทเนื้อหาและ derive `content_types` จาก `angle_id` กับ `extra_beats` แบบ stable/deduplicated จึงไม่พึ่งชื่อที่ AI ตอบกลับมา
2. บังคับ reroll ให้คง `angle_id`, ชื่อหัวข้อเดิม และคำอธิบายหัวข้อ แม้ AI จะส่งชื่อใหม่กลับมา
3. แก้ fallback ให้เลือก template ของ angle ที่ถูกขอโดยตรง ไม่ใช้สคริปต์ของ angle แรกแล้วเปลี่ยนเพียง ID
4. เพิ่มการบันทึก `angle_description`/`content_types` ใน `replace_angle_content` และแสดง badges หลายค่าใน sidebar, mobile pill และ reroll modal
5. รองรับ angle รุ่นเก่าที่ไม่มี metadata โดย derive badge ฝั่ง UI จาก `angle_id`/`extra_beats` โดยไม่ต้องเจนใหม่
6. เพิ่ม regression tests สำหรับ identity, default extra beats, deduplication และ fallback template

### Gate

- [x] `python -m pytest tests/test_reroll_script.py -q -p no:cacheprovider --tb=short` — `12 passed, 2 warnings`
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — `1,057 passed, 24 warnings, 0 failed` ใน `141.34 วินาที`
- [x] `npm test` — `149 passed, 0 failed`
- [x] `npm run build` — ผ่าน, Vite transformed `1,981 modules`
- [x] `npm run lint` — exit 0; warnings เดิมของโปรเจกต์
- [x] `git diff --check` — ผ่าน
- [x] Impeccable detector — `[]` สำหรับ `frontend/src/components/ProductToClip.jsx`

### Notes

- Reroll ยังเขียนทับบทพูดในหัวข้อเดิมตามพฤติกรรมเดิม แต่ไม่เปลี่ยน lifecycle ของงาน เช่น status/project/video
- งานนี้ไม่แตะ preview/render engine จึงไม่มี FFmpeg parity gate เพิ่ม
- รักษา diff ที่มีอยู่ก่อนหน้าใน `SystemSettings.jsx`, `TokenDashboard.jsx` และ `tools/probe_ass_scale.py` ไม่ได้แก้หรือลบ

## Round RENDER-REGRESSION-2 — ตรวจและคืน render ให้ตรง baseline

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จสิ้น

**เป้าหมาย:** ระบุ commit/เวลา/ไฟล์ที่ทำให้ภาพ Export เปลี่ยนจาก baseline และแก้เฉพาะ regression ที่ยืนยันได้ โดยไม่ทับงานค้างของเอเจนอื่น

### ผลการตรวจ forensic

- `f44db69` (`2026-09-10 00:07:50 +0700`) เพิ่ม style/renderer infrastructure และยังคง fallback เป็น `clean_tech_review`
- `3a35723` (`2026-09-10 08:06:23 +0700`) เปลี่ยน One Click flow ให้ส่ง `style_preset` ทุกครั้ง และตั้ง `DEFAULT_ONE_CLICK_STYLE_PRESET = 'viral_punch'`
- commit metadata ระบุผู้เขียนเป็น `wni-nasirulhak` ทั้งสอง commit; Git ไม่มีข้อมูลที่เชื่อถือได้ว่าเป็นเอเจนตัวใด จึงระบุได้ถึง commit/เวลา/ผู้เขียนเท่านั้น
- artifact ที่สร้างช่วง `15:42–15:44` มี `viral_punch`/`smooth_showcase` ใน `project.json` และสี/การเคลื่อนไหวสอดคล้องกับ preset ใหม่ในภาพที่ผู้ใช้แนบ
- differential policy probe วัดได้ว่า implicit baseline คือ `clean_tech_review` (`transition_stride=5`, `camera_motion_stride=2`, `zoom=0.08`, `pan=0.14`, accent `#FFE600`) ขณะที่ `viral_punch` คือ (`2`, `1`, `0.12`, `0.18`, `#FE2C55`)

### การแก้ไข

- `frontend/src/lib/stylePresetCatalog.js`: คืน One Click default ไปที่ `clean_tech_review`; preset อื่นยังเลือกใช้แบบ explicit ได้
- `frontend/src/lib/studioDefaults.js`: เพิ่ม `STYLE_PRESET_STORAGE_VERSION` และ migration สำหรับ browser form เก่าที่ถูกบันทึกโดย implicit `viral_punch`; ไม่ทับ choice ที่ผู้ใช้เลือก explicit หลัง migration
- `frontend/src/components/editor/NewClipPanel.jsx`: เมื่อเลือก presetจะบันทึก version marker พร้อมค่าที่ normalize แล้ว
- `frontend/src/lib/stylePresetCatalog.test.js`: เพิ่ม regression test สำหรับ default และ saved-form migration
- ไม่แก้ไข export/project artifact เดิม และไม่แตะ diff ของ `SystemSettings.jsx`, `TokenDashboard.jsx`, product metadata flow หรือ `tools/probe_ass_scale.py`

### Gate

- [x] differential policy/render evidence: มี policy probe และ artifact timestamp/project manifest ที่อธิบายความต่างได้
- [x] `python -m pytest tests/test_style_motion_policy.py tests/test_camera_motion_parity.py tests/test_preview_render_parity.py tests/test_preview_render_behavior.py -q -p no:cacheprovider --tb=short` — 181 passed; รวม FFmpeg multi-frame behavior
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 1,057 passed, 24 warnings
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `npm test` — 150 passed
- [x] `npm run build` — ผ่าน, Vite transform 1,981 modules
- [x] `npm run lint` — ผ่าน, มี warnings เดิมของ codebase ไม่มี error
- [x] `git diff --check` — ผ่าน

### Notes

- โปรเจกต์เดิมที่มี `style_preset` explicit เป็น `viral_punch` หรือ `smooth_showcase` จะไม่ถูกเขียนทับอัตโนมัติ เพื่อรักษาการเลือกของผู้ใช้; หากต้องการเรนเดอร์ซ้ำให้เหมือน Golden Master ให้เลือก `Clean Tech Review` ก่อน render

## Round FONT-SIZE-REGRESSION-1 — ตรวจและคืนขนาดฟอนต์บทพูด/ซับ

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จสิ้น

**เป้าหมาย:** ระบุจุดที่ทำให้ฟอนต์ใน Render เล็กกว่าภาพเดิม และคืนค่า Preview = Render โดยไม่ทับงานค้างของเอเจนอื่น

### ผลการตรวจ forensic

- ภาพ baseline เดิมมี caption ASS แบบ `Fontsize=50` พร้อม `\fscx165/\fscy165` ที่ settle แล้ว จึงมีขนาดกายภาพเทียบเท่า ~82px
- artifact ที่ผู้ใช้เห็น (`03_Projects/ESS01-แกะกล่องว้าว_1/subtitles_v2.ass`) มี `Fontsize=50`, ใช้ `IBM Plex Sans Thai SemiBold`, ไม่มี scale boost และไม่มี contract marker จึงเล็กกว่า baseline อย่างวัดได้
- generator ปัจจุบันสร้าง `Style: TikTokWhite,IBM Plex Sans Thai SemiBold,82,...` และใช้ขนาดเทียบเท่า baseline โดยไม่ต้อง scale glyph หลัง rasterize ซึ่งรักษา Thai mark parity ได้
- สาเหตุคือ incremental pipeline ตรวจ fingerprint ของไฟล์ได้ แต่ไม่มี version ของ subtitle renderer จึง reuse ASS เก่าหลังมีการเปลี่ยน font-size/GPOS contract

### การแก้ไข

- `scripts/subtitle_engine.py`: เพิ่ม `SUBTITLE_RENDER_CONTRACT_VERSION = "v3"`, marker ใน ASS header และ `subtitle_artifact_is_current()`; ASS ใหม่จะมี marker และ font size contract ปัจจุบัน
- `scripts/stages/subtitle_stage.py`: ก่อน reuse ตรวจ marker ผ่าน `ProjectManifest.artifact_path()`; ASS เก่าหรือไม่มี marker จะ regenerate stage subtitles อัตโนมัติ แล้วส่งต่อให้ video assembly
- `tests/test_subtitle_artifact_contract.py`: เพิ่ม regression tests ว่า ASS ใหม่มี marker และ legacy ASS ถูกปฏิเสธการ reuse
- restart API server ที่ค้างจากก่อน patch แล้ว: process ใหม่สร้างเวลา `16:28:47` จำนวน 2 process
- ไม่แก้ไข project/export artifact จริงของผู้ใช้ และไม่แตะ diff งาน product metadata/UI ที่มีอยู่ก่อนรอบนี้

### Gate

- [x] baseline/candidate font measurement: baseline physical size ~82px (`50 × 1.65`) เทียบ fresh ASS `Fontsize=82`; legacy artifact ตรวจได้ `current=False`, fresh `current=True`
- [x] `python -m pytest tests/test_subtitle_artifact_contract.py tests/test_preview_render_parity.py tests/test_preview_render_behavior.py -q -p no:cacheprovider --tb=short` — 172 passed, รวม FFmpeg multi-frame
- [x] `python -m pytest tests/ -q -p no:cacheprovider --tb=short` — 1,059 passed, 24 warnings
- [x] `python -m compileall -q scripts` — ผ่าน
- [x] `npm test` — 150 passed
- [x] `npm run build` — ผ่าน, Vite transform 1,981 modules
- [x] `npm run lint` — exit 0, warnings เดิมของ codebase ไม่มี error
- [x] `git diff --check` — ผ่าน

### Notes

- คลิปที่ export ไปแล้วจะยังคงไฟล์เดิมเพื่อไม่ลบ/เขียนทับข้อมูล; ให้กด Render ใหม่จากโปรเจกต์เดิมหนึ่งครั้ง ระบบจะสร้าง ASS ใหม่และฟอนต์กลับขนาดเดิม
- รอบนี้ไม่ต้องเปลี่ยน `SequencePlayer.jsx` เพราะ Canvas ใช้สัดส่วน 25px ที่เทียบกับ fresh ASS 82px แล้ว; ปัญหาอยู่ที่ stale ASS reuse ใน backend

## Round FONT-SIZE-REGRESSION-2 — แก้ซับยังเล็กใน backend environment จริง

วันที่: 2026-09-10 · สั่งโดย: user · สถานะ: เสร็จสิ้น

**เป้าหมาย:** ไล่ MP4/ASS/manifest ของงาน `ESS01-แกะกล่องว้าว_1` เวลา 16:31 ที่ผู้ใช้ยืนยันว่าซับยังเล็ก แก้ให้ขนาดกลับเท่า baseline ใน environment เดียวกับ backend จริง

### ผลการวินิจฉัย

- `subtitles_v3.ass` ถูกสร้างใหม่เวลา 16:30:58 และ MP4 16:31:04 อ้าง artifact นี้จริง จึงตัดสมมติฐาน reuse/cache/หยิบผิดไฟล์ออก
- ASS ที่สร้างใหม่ยังมี `TikTokWhite Fontsize=50` ทั้งที่ source คำนวณ `font_size_boosted`
- backend รันผ่าน `.venv\Scripts\python.exe` ซึ่งไม่มี `fontTools`; `ass_glyph_scale()` จับ exception แล้วคืน `1.0` เงียบๆ ทำให้ `50 × 1.0 = 50`
- probe ก่อนหน้าที่ได้ `82` รันด้วย system Python ซึ่งมี `fontTools` จึงเป็น environment mismatch และให้ false confidence
- ค่าจริงจาก IBM Plex Sans Thai คือ `unitsPerEm=1000`, `usWinAscent=1116`, `usWinDescent=534` → scale `1000/1650 = 0.6060606` → boost `1.65` → `Fontsize=82`

### การแก้ไข

- `scripts/subtitle/font_metrics.py`: เพิ่ม SFNT table reader ด้วย standard library (`struct`) อ่าน `head.unitsPerEm` และ `OS/2.usWinAscent/usWinDescent` โดยตรง เพื่อให้ visual contract ไม่พึ่ง optional package
- `requirements.txt`: เพิ่ม `fonttools==4.63.0` สำหรับ embedded font-family metadata ของ AssetRegistry และติดตั้งใน `.venv` แล้ว
- `scripts/subtitle_engine.py`: bump subtitle render contract จาก `v3` เป็น `v4` เพื่อ invalidate ASS v3 ที่อาจถูกสร้างด้วย fallback `1.0`
- `tests/test_subtitle_artifact_contract.py`: ล็อก generated IBM ASS ต้องเป็น `82`, จำลอง `fontTools` หายแล้วยังได้ `0.6060606`, และยืนยัน v3 ถูก invalidate
- `tests/test_preview_render_parity.py`: ปรับ source-contract assertion ให้ล็อก direct SFNT metric path แทน implementation เก่า
- restart backend ด้วย project `.venv` เวลา 16:45:53 และ reroll `subtitles` ของงานจริงสำเร็จเป็น `subtitles_v4.ass` + `ESS01-แกะกล่องว้าว_1_20260910_164654.mp4`

### Gate

- [x] red phase — regression file ล้ม 3 เคสตามอาการ: generated `50 != 82`, scale `1.0 != 0.6060606`, v3 ยังถูกมองว่า current
- [x] focused subtitle artifact/parity/FFmpeg behavior — `174 passed, 20 warnings, 0 failed`
- [x] full backend — `1,061 passed, 25 warnings, 0 failed` ใน `189.66 วินาที`
- [x] frontend — `150 passed, 0 failed`; build ผ่าน; lint exit 0 มี warnings เดิมของ codebase
- [x] `python -m compileall -q scripts`, `pip check`, `git diff --check` — ผ่าน
- [x] live artifact — `subtitles_v4.ass` มี marker v4 และ `TikTokWhite/TikTokSoftShadow Fontsize=82`
- [x] live FFmpeg frame เวลา 1.2s — caption pixel bands ใหม่ตรง baseline: ไทย `1390–1417`, อังกฤษ `1457–1481`

### Notes

- รอบนี้ reroll project/export จริงตามคำสั่งแก้บั๊ก; ไฟล์ล่าสุดใน Ready to post คือ timestamp `164654`
- ไม่แก้ `SequencePlayer.jsx` เพราะภาพปัญหามาจาก backend-only environment fallback; parity เดิมกลับมาตรงหลังใช้ scale ที่ถูกต้อง
- รักษา diff ค้างของ product metadata/UI/style migration และ `tools/probe_ass_scale.py`; ไม่ลบหรือเขียนทับ
