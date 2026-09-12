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
- [ ] `GET /api/exports` (`scripts/api_exports.py:180`) — จุดที่คุยกันตอนแรก, consumer: `ExportGallery.jsx`
- [ ] `GET /api/products` (`scripts/api_phase1.py:441`) — คืน products พร้อม nested `angles[]`, consumer: `ContentTrackerHub.jsx`, `ProductToClip.jsx`, `RawVaultPanel.jsx` (dropdown)
- [ ] `GET /api/videos` (`scripts/api_videos.py:111`) — สแกน raw footage ทุกไฟล์ทุกครั้ง, consumer: `MediaAssetsHub.jsx`, `MediaPickerModal.jsx`
- [ ] `GET /api/raw-vault` (`scripts/api_videos.py:298`) — ⚠️ docstring เดิมเตือนเองว่า join logic เป็น O(products×files) แล้ว ที่สเกล SaaS จะช้าจาก **อัลกอริทึม** ไม่ใช่แค่ payload ใหญ่ — ต้องดู query pattern ควบคู่กับ pagination ไม่ใช่แค่ตัด limit ท้าย, consumer: `RawVaultPanel.jsx`
- [ ] Schedule-queue root (`scripts/api_schedule_queue.py:586`) — ไม่เคย prune ใน `schedule_store.py`, โตวันละแถวไม่มีลบ, consumer: `ScheduleAgenda.jsx`
- [ ] `GET /api/tiktok-stats/latest` (`scripts/api_tiktok_stats.py:120`) — ผูกกับ `PostLog` ที่ไม่เคย prune เช่นกัน, consumer: `PerformanceAnalyticsTab.jsx`

### Gate
- [ ] pytest ของแต่ละ endpoint ที่แก้ (มี test เดิมอยู่แล้วต้องอัปเดต ไม่ใช่เขียนใหม่ทั้งหมด)
- [ ] `npm run build`
- [ ] Browser verify: เปิดแต่ละหน้า กด "โหลดเพิ่ม" แล้วเห็นแถวใหม่มาจริง ไม่ซ้ำ ไม่หาย

---

## Phase 2 (Medium) — โตช้ากว่า แต่ยังเป็นความเสี่ยงในระยะยาว

- [ ] `GET /api/tiktok-stats/clip-candidates` (`scripts/api_tiktok_stats.py:146`) — โตตาม products+angles เหมือน Phase 1 ข้อ 2 (ผูกกันอยู่แล้ว อาจ fix พร้อมกันได้เลย)
- [ ] `GET /api/assets/all` (`scripts/api_videos.py:549`) — คลัง SFX/เพลง/ฟอนต์/สติกเกอร์/LUT/เอฟเฟกต์ โตช้ากว่าเพราะเพิ่มมือ แต่ไลบรารีสำเร็จรูปมีเป็นร้อยได้, consumer: `MediaAssetsHub.jsx` (6 จุด `.map`), `SystemAssets.jsx`
- [ ] `GET /assets/duplicates/scan` (`scripts/api_asset_dedup.py:16`) —ผลลัพธ์สเกลตามปริมาณ raw footage, consumer: `SystemSettings.jsx`

### Gate
- [ ] pytest + `npm run build` + browser verify (เหมือน Phase 1)

---

## Phase 3 (Low) — ยังไม่ต้องรีบ บันทึกไว้เฉยๆ

- [ ] `GET /api/posts`, `GET /api/posts/performance` (`scripts/api_phase1.py:169,211`) — **ไม่มี frontend เรียกใช้จริงตอนนี้** (`getPosts` เป็น dead code) — ข้ามได้จนกว่าจะมีคนเรียกใช้จริง
- [ ] `GET /api/tiktok-stats/pending` — เป็นคิวชั่วคราว เคลียร์ทันทีที่จับคู่เสร็จ ไม่สะสมยาว ไม่รีบ
- [ ] `GET /backup/list` (`scripts/api_backup.py:21`) — โตช้าตามความถี่ backup manual/cron ไม่รีบ
- [ ] `GET /api/tasks/active` (`scripts/api_tasks.py:12`) — ปลอดภัยแล้วด้วย hardcoded `limit=50` ฝั่ง `TaskManager` — แค่เสนอให้เปิดเป็น query param แทนการ hardcode เผื่ออนาคตอยากปรับ ไม่ใช่บั๊ก

**ไม่ต้องแตะ:** `GET /hooks/styles`, `GET /angles` (catalog คงที่ ไม่ใช่ user data ที่โต), `GET /render/batch/{batch_id}` (self-prune 50 อยู่แล้ว, ไม่มี "list all" endpoint ให้แก้)

---

## หมายเหตุการตัดสินใจ

- เลือก **limit/offset แบบกดปุ่ม "โหลดเพิ่ม"** ไม่ใช่ infinite-scroll อัตโนมัติ และไม่ใช่ virtualization library —
  เหตุผล: ไม่มี dependency ใหม่, พฤติกรรม predictable, ใช้ pattern เดียวกับ `/tokens/history` ที่มีอยู่แล้วในระบบ
- ลำดับ Phase อิงจาก "อัตราการโตของข้อมูลจริง" ไม่ใช่ความยากง่ายของโค้ด — `/api/raw-vault` มีความซับซ้อนเพิ่ม (fix อัลกอริทึม join ควบคู่ pagination) จึงอาจใช้เวลานานกว่าตัวอื่นใน Phase เดียวกัน
