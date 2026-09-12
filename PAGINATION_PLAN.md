# 📄 PAGINATION_PLAN.md — เพิ่ม limit/pagination ให้ list endpoint ทั่วระบบ

อ้างอิงจาก [.agents/rules/work_loop.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/work_loop.md) — งานนี้กินหลายรอบ แยกเป็น Phase ตามความเร่งด่วน
`TODO.md` ชี้มาไฟล์นี้ ห้ามเขียนแผนซ้ำสองที่

## ที่มา

ผู้ใช้สังเกตว่า Export Gallery ตอนนี้มี 10 คลิปยังโอเค แต่ถามว่าเมื่อถึงหลักร้อยจะช้าไหม —
ตรวจโค้ดยืนยันว่า `GET /api/exports` (`scripts/api_exports.py:180`) ไม่มี limit/offset เลย
ดึงทุกแถวทุกครั้ง และ `ExportGallery.jsx` render ทุกการ์ดลง DOM พร้อมกันหมด ไม่มี virtualization

สั่งให้สำรวจทั้งระบบ (ผ่าน Explore agent) พบว่า **นี่คือ pattern ทั่วทั้งแอป ไม่ใช่จุดเดียว** —
ทุก endpoint ที่คืนค่าเป็น list ต่อ record (สินค้า/มุมสคริปต์/ฟุตเทจ/คิวโพสต์/สถิติ) ไม่มี pagination เลยสักที่
ยกเว้น `GET /tokens/history` (`scripts/api_tokens.py:23`) ที่มี `limit: int = Query(50, ge=1, le=500)` อยู่แล้ว
— **ใช้ endpoint นี้เป็นต้นแบบมาตรฐานสำหรับทุก endpoint ที่จะแก้**

ไม่มี dependency virtualization ใดๆ ติดตั้งอยู่ในโปรเจกต์ (`react-window`/`react-virtualized`) —
เลือกวิธี **backend limit/offset + frontend "โหลดเพิ่ม" (load more)** แทนการดึง lib ใหม่ เพื่อคงหลัก
"ไม่เพิ่ม dependency โดยไม่จำเป็น"

## ⚠️ ข้อค้นพบระหว่างลงมือจริง (แก้มาตรฐานด้านล่าง)

ตอนเริ่มแก้ `/api/exports` จริง พบว่า `exportsList` (จาก `getExports()`) ไม่ได้ใช้แค่ render grid —
`App.jsx` ดึงครั้งเดียวตอน mount เก็บ global state ส่งต่อเป็น prop, และ `ContentTrackerHub.jsx`
ดึงซ้ำเองอีกรอบเพื่อ **merge cover metadata เข้าทุก product/angle** (`mergeCoverMetadata`) —
ถ้า backend ตัด limit ที่ source เลย จะทำให้ product ที่ export ตกอยู่นอกหน้าแรกไม่ได้ cover metadata
มา merge เป็นบั๊กจริง ไม่ใช่แค่ performance. `ExportGallery.jsx` เองก็คำนวณ `counts`/`productTags`/ยอดขนาดรวม
จาก **ทั้ง list** เช่นกัน (ไม่ใช่แค่หน้าที่ render)

**สรุปเกณฑ์ใหม่ ต้องเช็คทีละ endpoint ก่อนเลือกวิธี:**
- ถ้า array นั้นถูกใช้แค่จุดเดียวเพื่อ render list/grid เฉยๆ → **backend limit/offset** ตามมาตรฐานเดิมด้านล่างได้เลย
- ถ้า array ถูกใช้ร่วมกันหลายจุด (cross-reference, aggregate count, merge metadata) → **ห้ามตัด limit ที่ backend**
  ใช้ **client-side windowed rendering** แทน (ดึงข้อมูลเต็มเหมือนเดิม แต่ render ลง DOM แค่บางส่วน
  + ปุ่ม "โหลดเพิ่ม" ขยาย window ในเบราว์เซอร์ ไม่ใช่ fetch หน้าใหม่จาก server) — แก้ปัญหา DOM หนักได้เหมือนกัน
  โดยไม่เสี่ยงพังจุดที่ merge ข้อมูลข้ามคอมโพเนนต์

## มาตรฐานที่ใช้ร่วมกันทุก endpoint (Contract)

- Backend: query params `limit: int = Query(DEFAULT, ge=1, le=MAX)` + `offset: int = Query(0, ge=0)`
  response ห่อด้วย `{ items: [...], total: <int>, limit, offset }` (มี `total` ให้ frontend รู้ว่ายังเหลือไหม)
- Frontend: ปุ่ม "โหลดเพิ่ม N รายการ" ท้าย grid/list (ไม่ทำ infinite-scroll อัตโนมัติในรอบแรก เพราะกดเองคุมง่ายกว่า
  และไม่ต้องผูก IntersectionObserver เพิ่ม) — เก็บ state `items` แบบ append, ปุ่มหายเมื่อ `items.length >= total`
- ค่า default page size: 24 สำหรับ grid การ์ด (มี thumbnail), 50 สำหรับ list แถวข้อความล้วน (ตาม `/tokens/history`)
- Breaking change กับ frontend เดิม: ทุกจุดที่เรียก endpoint เหล่านี้ต้องแก้พร้อมกันในรอบเดียวกัน ห้ามครึ่งๆ กลางๆ

---

## Phase 1 (High) — endpoint ที่โตเร็วสุด ควรทำก่อน

โตทุกครั้งที่ถ่าย/โพสต์คลิป มีโอกาสถึงหลักร้อยภายในปีเดียวตามการใช้งานจริง

### Todo
- [x] `GET /api/exports` (`scripts/api_exports.py:180`) — จุดที่คุยกันตอนแรก, consumer: `ExportGallery.jsx` → client-side windowed (24/page)
- [x] `GET /api/products` (`scripts/api_phase1.py:441`) — คืน products พร้อม nested `angles[]`, consumer: `ContentTrackerHub.jsx` (kanban 20/col + table 40/page), `ProductToClip.jsx`, `RawVaultPanel.jsx` (dropdown, ไม่แตะ — แค่ dropdown เลือกสินค้า ไม่ใช่ list render)
- [x] `GET /api/videos` (`scripts/api_videos.py:111`) — consumer จริงคือ `MediaPickerModal.jsx` (audit เดิมชี้ผิดว่าเป็น `MediaAssetsHub.jsx`) → client-side windowed (40/page)
- [x] `GET /api/raw-vault` (`scripts/api_videos.py:298`) — เช็คโค้ดจริงแล้วพบว่า O(products×files) ที่กังวลไว้ **ถูกแก้เป็น O(products+files) ไปแล้ว** ในรอบก่อนหน้า (docstring เป็นบันทึกการแก้ ไม่ใช่คำเตือนเปิดอยู่) — เหลือแค่ pagination, consumer: `RawVaultPanel.jsx` → client-side windowed (40/page)
- [x] Schedule-queue root (`scripts/api_schedule_queue.py:586`) — calendar view (7 วัน) และ list view (`activeQueue`, เฉพาะยังไม่โพสต์) ปลอดภัยโดยธรรมชาติ ความเสี่ยงจริงอยู่ที่ modal "โพสต์แล้ว" (`postedQueue`, ไม่เคย prune), consumer: `ScheduleAgenda.jsx` → client-side windowed เฉพาะ modal นั้น (50/page)
- [x] `GET /api/tiktok-stats/latest` (`scripts/api_tiktok_stats.py:120`) — KPI การ์ดยังอ่านข้อมูลเต็ม ตารางแสดงผล windowed (50/page), consumer: `PerformanceAnalyticsTab.jsx`

**สรุป Phase 1:** ทุก endpoint เลือก **client-side windowing** ไม่มี endpoint ไหนใช้ backend limit/offset เลย — เพราะทุกตัวมี aggregate/cross-component dependency (ดูหัวข้อ "ข้อค้นพบระหว่างลงมือจริง" ด้านบน) กลายเป็นมาตรฐานจริงของรอบนี้ ต่างจาก Contract เดิมที่ตั้งใจไว้

### Gate (Phase 1 — เสร็จหมด)
- [x] pytest เต็มระบบ 1126 passed (ไม่กระทบ เพราะไม่แตะ backend เลยทั้ง Phase 1)
- [x] `npm run build` ผ่านทุกจุดที่แก้ (vitest 158 passed ทุกรอบ)
- [ ] Browser verify: ยังไม่ได้ทำ — dev server ไม่ตอบ HTTP ตลอด session นี้ ต้องเปิดแอปเช็คจริงทีหลัง

---

## Phase 2 (Medium) — โตช้ากว่า แต่ยังเป็นความเสี่ยงในระยะยาว

- [x] `GET /api/tiktok-stats/clip-candidates` (`scripts/api_tiktok_stats.py:146`) — consumer: `PerformanceAnalyticsTab.jsx` ใช้ populate native `<select>` dropdown สำหรับจับคู่ manual **ไม่ใช่ custom card list** — native select ของเบราว์เซอร์ scale ได้เป็นพันตัวเลือกโดยไม่กระทบ perf หน้าเว็บ (ต่างจาก div-based grid) → **ตัดสินใจไม่แก้โค้ด** ของจริงไม่ได้เสี่ยงแบบที่ audit ตอนแรกกังวล
- [x] `GET /api/assets/all` (`scripts/api_videos.py:549`) — consumer: `MediaAssetsHub.jsx` มี 7 จุด render (1 split-view list + 6 grid-view ต่อประเภท) แต่มีแค่จุดเดียวโชว์พร้อมกันเสมอ (ผูกกับ `activeAssetTab`) → windowing เดียวใช้ร่วมกันได้ทั้งหมด (`visibleCurrentItems`, 40/page, reset เมื่อเปลี่ยนแท็บ/ค้นหา)
- [x] `GET /assets/duplicates/scan` (`scripts/api_asset_dedup.py:16`) — consumer: `SystemSettings.jsx` เป็น on-demand admin action (กด scan เอง ไม่ใช่ default-visible) อยู่ใน container ที่จำกัดความสูงอยู่แล้ว (`max-h-60`) — เสี่ยงต่ำกว่าอันอื่น แต่แก้ไว้ให้สอดคล้องกัน (30 กลุ่ม/page, reset ทุกครั้งที่ scan ใหม่)

### Gate (Phase 2 — เสร็จหมด)
- [x] `npm run build` ผ่าน, vitest 158 passed ทุกจุดที่แก้
- [ ] Browser verify: ยังไม่ได้ทำ (เหตุผลเดียวกับ Phase 1)

---

## Phase 3 (Low) — เช็คแล้ว ไม่ต้องแก้โค้ดสักจุด

- [x] `GET /api/posts`, `GET /api/posts/performance` (`scripts/api_phase1.py:169,211`) — ยืนยันแล้วว่า `getPosts` ไม่มีที่ไหนใน `frontend/src/` เรียกใช้เลย (grep ทั้ง repo เจอแค่ definition ใน `api.js`) → dead code จริง ข้ามได้
- [x] `GET /api/tiktok-stats/pending` — ยืนยันแล้วว่าเป็นคิวชั่วคราวจริง (`PerformanceAnalyticsTab.jsx`) เคลียร์ทันทีที่ attach/ignore ผ่าน UI ที่มีอยู่แล้ว ("แถวที่ยังไม่ได้จับคู่ (N)") ไม่สะสม
- [x] `GET /backup/list` (`scripts/api_backup.py:21`) — consumer: `SystemSettings.jsx` โตช้าจริง (backup เป็น manual/cron action ไม่ใช่ per-clip) และมี `max-h-60 overflow-y-auto` จำกัดความสูงอยู่แล้วเหมือน dedup scan → **ไม่ต้องแก้**
- [x] `GET /api/tasks/active` (`scripts/api_tasks.py:12`, `TaskManager.get_active_tasks`) — ยืนยันแล้วว่า `limit: int = 50` เป็นค่าจริงใน signature (`scripts/task_manager.py:530`) ปลอดภัยอยู่แล้ว 100%

**สรุป Phase 3:** ทั้ง 4 จุดเช็คแล้วไม่มีจุดไหนต้องแก้โค้ดจริง — เป็น dead code, self-clearing, หรือปลอดภัยอยู่แล้วโดยธรรมชาติ ปิด Phase 3 แบบไม่มี code change

**ไม่ต้องแตะ:** `GET /hooks/styles`, `GET /angles` (catalog คงที่ ไม่ใช่ user data ที่โต), `GET /render/batch/{batch_id}` (self-prune 50 อยู่แล้ว, ไม่มี "list all" endpoint ให้แก้)

---

## หมายเหตุการตัดสินใจ

- เลือก **limit/offset แบบกดปุ่ม "โหลดเพิ่ม"** ไม่ใช่ infinite-scroll อัตโนมัติ และไม่ใช่ virtualization library —
  เหตุผล: ไม่มี dependency ใหม่, พฤติกรรม predictable, ใช้ pattern เดียวกับ `/tokens/history` ที่มีอยู่แล้วในระบบ
- ลำดับ Phase อิงจาก "อัตราการโตของข้อมูลจริง" ไม่ใช่ความยากง่ายของโค้ด — `/api/raw-vault` มีความซับซ้อนเพิ่ม (fix อัลกอริทึม join ควบคู่ pagination) จึงอาจใช้เวลานานกว่าตัวอื่นใน Phase เดียวกัน
