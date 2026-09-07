# 📜 OmniCut Pro Studio — History งานที่ทำเสร็จแล้ว

คลังประวัติรอบงานที่ปิดแล้ว **ห้ามแก้ย้อนหลัง** — เป็นบันทึกว่าตอนนั้นทำอะไร วัดได้เท่าไหร่ เจออะไร

- งานที่ยังไม่เสร็จอยู่ที่ [TODO.md](file:///d:/Winona/Programmer/Capcut/TODO.md)
- กติกา: [.agents/rules/work_loop.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/work_loop.md)
- รอบไหนปิด ให้ **ย้ายบล็อกเต็มมาที่นี่** แล้วเหลือบรรทัดเดียวใน `TODO.md` — กัน `TODO.md` บวมจนหาของไม่เจอ

## สารบัญ

| รอบ | งาน | วันที่ | ผลลัพธ์ |
| :--- | :--- | :--- | :--- |
| Round 1 | รวม hook banner กับ text overlay เป็นโมเดลเดียว | 2026-09-05 | ปิดบั๊ก 12 ตัว · commit `20e2cc5` |
| Round 2 | วางกฎรอบงาน + ตั้ง Todo กลาง | 2026-09-05 | `work_loop.md` + `TODO.md` |
| Round 3 | ซ่อมฐาน + รวม writer + easing | 2026-09-05 | ซ่อม drift 3 ตัว · `overlay_events.py` · accel |
| Round DOC-1 | ตรวจโค้ดและอัปเดตเอกสารหลัง Refactor | 2026-09-05 | `ARCHITECTURE.md` + `testing_standard.md` |
| Round BUG-1 | แก้ปุ่มสร้างคลิปใหม่กดไม่ได้ (executeRender ใน useRenderJob) | 2026-09-05 | คืนชีพ executeRender & telemetry · npm test 52 pass · build pass |
| Round 4 | per-word layout (static, พิสูจน์ว่าเหมือนเดิมเป๊ะ) | 2026-09-05 | word_layout.py + overlayLayoutClient.js · pytest 344 pass · npm test 54 pass · render parity pass |
| Round 5 | per-word animation (คำทยอยเข้าทีละคำ) | 2026-09-05 | word_stagger_ms · ASS \org & \t · Canvas 2D mirror · pytest 347 pass · npm test 54 pass · build pass |
| Round 6 | ช่องใหม่ที่ mirror ได้เป๊ะ (Loop/Out + Tier A Skew) | 2026-09-05 | Full motion pipeline + Skew \fax / Canvas transform · pytest 351 pass · npm test 54 pass · build pass |
| Round 7 | template v2 + แกลเลอรีที่ขยับได้ | 2026-09-05 | 8 templates + motion presets · Animated gallery · pytest 356 pass · npm test 54 pass · build pass |
| Round BUG-2 | แก้ข้อความซ้อนทับกันเป็นก้อนใน SequencePlayer (Hook / Text clumping) | 2026-09-05 | Guard Hook header & non-staggered overlays to monolithic · Contract test · pytest 356 pass · npm test 54 pass · build pass |
| Round BUG-3 | angle ชนกัน (คลิปผิดสคริปต์) ใน Content Tracker Hub + ปุ่มปักตะกร้า TikTok | 2026-09-06 | reconcile collision guard + data_conflict_note · rollback ครอบทุก status · tiktok_product_id UI · pytest 367 pass · build pass |
| Round TRK-3 | บอร์ดหลักคลีนไร้ความรก (Today-Only Posted, คลังสคริปต์ & การ์ดตัดต่อเสร็จแนวนอน) | 2026-09-06 | Today-Only posted + Archive Modal · Script Library Modal (หยิบทำวันนี้) · Compact Rendered Cards ~95px · pytest 373 pass · build pass |
| Round TRK-2 | ตารางจัดคิวโพสต์ประจำวัน (Daily Run Sheet) & จัดกลุ่มย่อการ์ด (Product Grouping / Quick Pills) | 2026-09-06 | Daily Run Sheet tab (4 slots + auto-rotate + schedule time) + Quick Pills + Accordion · pytest 373 pass · npm test 54 pass · build pass |
| Round TRK-1 | เพิ่มปุ่มส่งคลิปไป TikTok Studio พร้อม Modal ตรวจสอบ/ปักตะกร้า ในหน้า Tracker | 2026-09-06 | ContentTrackerHub 2-row buttons + Post Modal + Inspect toolbar · pytest 372 pass · npm test 54 pass · build pass |
| Round PROD-1 | เพิ่มช่อง TikTok Product ID ตอนสร้างสคริปต์ + Fallback ค้นหาด้วยชื่อ + Click-to-Edit Cart ID ย้อนหลัง | 2026-09-06 | ProductToClip modal + Header badge edit + auto-resolve shortlinks · pytest 372 pass · npm test 54 pass · build pass |

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
