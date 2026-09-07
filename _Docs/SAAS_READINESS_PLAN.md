# SaaS Readiness Plan

Audit ของ Capcut content studio — สถานะปัจจุบัน, จุดบัค/จุดเสี่ยง, และสิ่งที่ต้องแก้ก่อนเปิดให้คนอื่นใช้

สถานะวันนี้: **single-user local app** — data อยู่ใน SQLite (`_Docs/*.db`, JSON เดิมเหลือเป็น live mirror), media อยู่ในโฟลเดอร์ `00_Inbox`…`06_Archive` (path เก็บแบบ relative แล้ว), auth เป็น shared-secret ปิดอยู่โดย default, รัน render ในโปรเซสเดียวกับ API

> **Verified against commit `b4807a6`** (2026-09-07 — เอกสารก่อนหน้าค้างอยู่ที่ `d4fc3dc`)
> อ่าน `git log d4fc3dc..HEAD` แบบเต็มข้อความ + spot-check โค้ดจริงทุกข้อที่เอกสารเดิมบอกว่ายังเปิดอยู่
> ข้อ `renderJobModel` และ `keyframe_engine` ที่รอบก่อนเขียนว่า "กำลังแก้/ยังเปิด" **ปิดไปแล้ว** (`46135c7`, `cd2d778`) — ย้ายลงท้ายเอกสารแล้ว
> `tiktok_autopost_extension/` เป็นพื้นที่ของ dev อีกคนที่แก้อยู่ตลอด — เช็ค `git log` ก่อนเชื่อสถานะฝั่งนั้น

---

## ⚠️ เรื่องสำคัญที่ต้องรู้ก่อนอ่านต่อ

เอกสารรุ่นก่อน (commit `d4fc3dc`) มีปัญหาที่ทำให้มัน**หลอกคนอ่านโดยไม่ตั้งใจ**: commit `d4fc3dc` เอง **แก้บัคที่ P0/P0.5/P1.5/8a อธิบายไปพร้อมกัน** (path traversal, SSRF, frontend fetch race, O(n²) export scan) แต่ตัวเอกสารที่ commit เดียวกันนั้นเขียน กลับ**เติมส่วนใหม่ต่อท้าย (P1.6/P1.7/P1.8) โดยไม่ย้อนไปแก้ส่วนต้นให้บอกว่า "เสร็จแล้ว"** ผลคือใครเปิดอ่านโดยไม่ไล่ code จะเข้าใจผิดว่า arbitrary file write / SSRF ยัง exploit ได้อยู่ ทั้งที่แก้ไปตั้งแต่ `d4fc3dc` แล้ว

รอบนี้เขียนใหม่ทั้งหมดเพื่อไม่ให้เกิดซ้ำ — ทุกข้อที่ปิดแล้วจะถูก**ลบออกจาก body หลัก** เหลือไว้แค่สรุปสั้นๆ ใน "สิ่งที่แก้ไปแล้ว" ท้ายเอกสาร ไม่ใช่ maintain เป็น dead section

---

## สรุปผู้บริหาร

| ด้าน | สถานะ |
|---|---|
| Atomic write (local disk) | ✅ ดีอยู่แล้ว (tmp + replace) |
| Command injection (`shell=True`) | ✅ ไม่พบ |
| Secret hardcode | ✅ ไม่พบ |
| Path traversal (write + read) | ✅ ปิดแล้ว (`d4fc3dc`) — component-wise containment ทุกจุด |
| SSRF (product scraper) | ✅ ปิดแล้ว (`d4fc3dc`) — resolve + block private/loopback ทุก redirect hop + domain allowlist |
| Frontend fetch race (tracker board) | ✅ ปิดแล้ว (`d4fc3dc`, ขยายเพิ่ม `a8c7870`) |
| O(n²) export/raw-vault scan | ✅ ปิดแล้ว (`d4fc3dc`) |
| Lost-update race (JSON store) | ✅ ปิดแล้ว (`83a9f1e` — ย้ายลง SQLite + `BEGIN IMMEDIATE`) — **ยกเว้น 1 เมธอดที่ยังหลุด ดูข้อ 3** |
| Absolute path ฝังใน data | ✅ ปิดแล้ว (`cea03eb`) — ปลดล็อก object storage แล้ว |
| Silent-fail pipeline (TTS drop, timeout, ffprobe 15s) | ✅ ปิดแล้ว (`c12527b`) |
| Extension silent-success (post/link/schedule ไม่เช็คผล) | ✅ ปิดแล้ว (`c12527b`, live-verify รอบ POST-3.x) |
| Quota enforcement | ✅ ครบ 6 จุดจ่ายเงินจริงแล้ว (`c12527b`, `1b9ba1d`) |
| API key gate + CORS allowlist | 🟡 มีกลไกแล้วแต่ **ปิดอยู่โดย default** — ไม่ใช่ auth จริง |
| **ไม่มี auth/per-user identity เลย** | 🔴 blocking สำหรับ SaaS — ยังไม่เริ่ม |
| **Render in-process, `_RENDER_SLOT` ล็อกเดียวทั้งโปรเซส** | 🔴 blocking — ไม่มี job queue |
| `renderJobModel.js` key ด้วยชื่อ project | ✅ ปิดแล้ว (`46135c7`) — key เดียวทั้งแท็บ addressed ด้วย job uuid4 |
| **`ProductStore.reconcile_existing_projects()` ยังใช้ bare `_load()`/`_save()`** | 🟠 หลุดจาก transaction ที่ `83a9f1e` วางไว้ |
| **`token_tracker` cache ยังมีช่องโหว่ same-tick-same-size** | 🟡 ทฤษฎีล้วนๆ วันนี้ ไม่เคยเจอจริง |
| **SQLite เป็น document store** (`angles`/`videos` ไม่ normalize) | 🟠 ตั้งใจ — ต้องแลกกับงาน rewrite ใหญ่ก่อนแตะ |
| **Extension cover flow ผ่าน CDP path เอง — ยังไม่ verify จริง** | 🟠 Playwright ปฏิเสธ file send, รอทดสอบผ่าน extension จริง |
| `keyframe_engine.py` ไม่มีใครเรียก | ✅ ตรวจแล้ว (`cd2d778`) — **ไม่ลบ** เป็น Phase 9 scaffolding ที่มี easing/clamp เกินของ live + doc ยังอ้าง `ease_out`; ใส่ STATUS ใน docstring แทน |

---

## P0 — ยังเปิดอยู่วันนี้ (ผลกระทบจริง ไม่ต้องรอ SaaS)

### 1. ไม่มี authentication จริง 🔴
`scripts/api_server.py:92-128`

สิ่งที่มีวันนี้คือ **shared-secret gate** (`OMNICUT_API_KEY` + `X-API-Key` header, constant-time compare) ที่ `c12527b` เพิ่มเข้ามา — **permissive เมื่อไม่ตั้งค่า** (ค่า default) และไม่มีแนวคิด per-user เลย ทุกคนที่มี key เดียวกันเห็นข้อมูลเดียวกันหมด

`a8c7870` ต่อสาย frontend (`frontend/src/api.js:15,18`) ให้ส่ง header นี้แล้ว แต่ **extension (`tiktok_autopost_extension/`) ยังไม่ส่ง** — ถ้าตั้ง `OMNICUT_API_KEY` วันนี้ extension จะ 401 ทันที (ไฟล์นั้นเป็นของ dev อีกคน ไม่แตะ)

**นี่คือ shared secret ไม่ใช่ auth** — ไม่มี JWT, ไม่มี session, ไม่มี user table, ไม่มีทางแยกว่าใครยิง request ไหน

**Fix:** ระยะสั้นคือให้ extension ส่ง header (เล็ก, ทำได้ไว) ระยะยาวต้องเป็น JWT/session + `get_current_user()` จริงตอนทำ multi-tenant
**Effort:** SMALL (ต่อสาย extension) / LARGE (auth จริงต่อ user) — **นี่คือ effort ประเมินเดิมที่ผิด**: เอกสารเก่าบอก "MEDIUM (proper)" แต่หลังเห็นว่าทุก endpoint (108+ ตัว), ทุก store (`ProductStore`/`PostLog`/`TaskManager`/`ProjectManifest`), และ global state 6 ตัว (ดูข้อ 6) ต้องร้อย identity ผ่านหมด — ควรนับเป็นงานระดับสัปดาห์ ไม่ใช่วัน

### 2. Render เป็น in-process, ล็อกเดียวทั้งโปรเซส 🔴
`scripts/render_jobs.py:20,45` (`ACTIVE_JOBS`, `_RENDER_SLOT`)

`18735fd` เพิ่ม `owner_id` scoping ให้ `ACTIVE_JOBS`/`TaskManager._tasks` แล้ว (ป้องกัน enumerate job คนอื่น) — **แต่นี่ไม่ใช่ multi-tenancy** ตามที่ commit message บอกไว้เอง: ไม่มี `tenant_id`, ไม่มี auth ผูกกับ `owner_id`, ทุกคน default เป็น `"local"` เหมือนเดิม สิ่งที่ทำจริงคือเปลี่ยน API signature ให้พร้อมรับ parameter ตอนมี auth จริง

`_RENDER_SLOT` ยังเป็น `threading.Lock()` เดียวทั้งโปรเซส — เจตนา (เครื่องนี้ CPU-only, render ทีละงานพอ) แต่หมายความว่า **ไม่มี concurrency, ไม่มี priority, ไม่มี queue** งาน render ของ user คนที่สองรอคิวงานคนแรกเสมอ ไม่มีทาง fairness

`ACTIVE_JOBS` ยังอยู่ใน memory ล้วนๆ — restart แล้วหายหมด (คอมเมนต์ในโค้ดยอมรับเอง) ส่วน `task_manager.py` persist ลง `task_registry.json` แต่ restart แล้ว mark ทุกงานค้างเป็น failed ไม่ resume

**Fix:** ต้องเป็น job queue จริง (arq แนะนำกว่า Celery สำหรับทีมเล็ก — asyncio-native, ops น้อย) + `_RENDER_SLOT` กลายเป็น worker-pool sizing + per-tenant concurrency rule
**Effort:** LARGE — เป็นโปรเจกต์แยก ต้องคิดเรื่อง retry policy ด้วย (TTS network ล้ม = retry ได้, ffmpeg OOM = อย่า retry)

### 3. `ProductStore.reconcile_existing_projects()` หลุดจาก transaction 🟠
`scripts/product_store.py:596-793`

`83a9f1e` ย้าย `ProductStore`/`PostLog` ทั้งคู่ไปอยู่บน SQLite แล้วครอบทุก mutate ด้วย `_mutate()` context manager ที่เปิด `BEGIN IMMEDIATE` (ดู `scripts/db.py:197,230,335`) — แก้ lost-update race ของเดิมได้จริง

แต่ `reconcile_existing_projects()` (เรียกจาก `get_all()` ทุกครั้งที่ list สินค้า) ยังเขียนแบบเดิม: `products = cls._load()` ตรง entry (บรรทัด 601) แก้ list ใน memory ตลอดฟังก์ชัน แล้ว `cls._save(products)` ท้ายฟังก์ชัน (บรรทัด 793) — **ไม่ผ่าน `_mutate()` เลย** เป็นเมธอดเดียวที่เหลือหลุดจาก 12 จุดที่ใช้ `with cls._mutate()` ถูกต้อง

**Failure scenario:** สอง request เรียก `get_all()` พร้อมกัน (poll UI 2 แท็บ, หรือ background job + UI) — ทั้งคู่ `_load()` เห็น state เดียวกัน, mutate คนละ field, `_save()` ทับกัน → การ reconcile ของฝั่งหนึ่งหาย เงียบๆ เหมือนบัคเดิมที่ `83a9f1e` เพิ่งแก้ไป แต่หลุดเฉพาะ endpoint นี้

**Fix:** ห่อทั้งฟังก์ชันด้วย `with cls._mutate() as products:` เหมือนเมธอดอื่น (ต้องปรับ logic เพราะตอนนี้มี early-return `if not products: return False` และหลาย `if changed: cls._save()` — ต้อง restructure ให้เข้ากับ pattern yield-then-commit)
**Effort:** SMALL–MEDIUM (ฟังก์ชันยาว ~200 บรรทัด logic ซับซ้อนกว่าเมธอดอื่นที่ย้ายไปแล้ว ต้อง test ครอบคลุม edge case เดิมทั้งหมด)

---

## P1 — ต้องทำก่อนให้คนนอกแตะ (ไม่ blocking วันนี้แต่ blocking SaaS)

### 4. Quota enforcement ครบจุดแล้ว แต่ยังไม่มี hard budget table จริง 🟡
`scripts/quota.py` + เรียกจาก `ai_bridge.py:461`, `api_voice.py:199`, `gemini_tts_engine.py:136`, `gemini_vision_matcher.py:240`, `product_scraper.py:351`, `script_tone_analyzer.py:89`

**เปลี่ยนจากเอกสารเก่ามาก:** ตอน `d4fc3dc` ยังไม่มี quota check เลย (`token_tracker.py` มีแต่ `get_history()`) วันนี้ `check_budget()` เรียกก่อนทุกจุดที่จ่ายเงินจริงแล้วครบ 6 จุด — cache hit ของ vision matcher ไม่โดนหักด้วย (check วางหลัง cache lookup ตามที่ตั้งใจ)

`c12527b` แยกเคส "โควตาหมด" ออกจาก "provider ล่ม" ให้ถูกต้อง (ก่อนหน้านั้น broad except กลืนทั้งคู่ไปเป็น fallback เดียวกัน ผู้ใช้แยกไม่ออกว่าโดนตัดโควตาหรือ Gemini ล่ม) `1b9ba1d` ปิดช่องที่เหลือ 3 จุดที่เคย bypass ได้เพราะสร้าง `genai.Client` ตรงๆ

**ที่ยังไม่มี:** ตาราง `tenant_budgets` จริง (`tokens_used`/`tokens_limit`/`cost_thb_limit`) — วันนี้ budget check เทียบกับ threshold คงที่ใน `quota.py` ไม่ใช่ per-user configurable, และยังไม่มี "reserve ประมาณการก่อนยิง แล้ว reconcile ทีหลัง" (สองคำขอผ่าน check พร้อมกันก่อนใครจะ debit ยังมี race อยู่ในทางทฤษฎี — เบากว่าของเดิมมากเพราะทับซ้อนกันได้แค่ในหน้าต่างเวลาสั้นมาก แต่ไม่ได้ปิดสนิท)
**Fix:** เพิ่มตาราง budget ต่อ tenant/user จริงตอนทำ multi-tenant
**Effort:** MEDIUM (โครง check_budget วางไว้ดีแล้ว งานที่เหลือคือ schema + debit-in-transaction)

### 5. `token_tracker` cache ยังมี same-tick-same-size gap ทางทฤษฎี 🟡
`scripts/token_tracker.py:83-106` (`_disk_stamp`)

`22559a1` เปลี่ยนจาก plain `st_mtime` (float วินาที) เป็น `(st_mtime_ns, st_size)` แก้ปัญหาที่ Windows/FAT filesystem มี mtime resolution หยาบจนสองการเขียนในวินาทีเดียวกันอ่าน mtime เท่ากัน — **ของเดิมพังบ่อยกว่านี้มาก** เพราะ float-seconds ชนกันง่าย

ที่เหลือคือ edge case ที่ commit เองก็ยอมรับตรงๆ ในคอมเมนต์: ถ้าสองโปรเซสเขียนแล้วบังเอิญได้ `st_mtime_ns` เดียวกัน **และ** ขนาดไฟล์เท่ากันพอดี (เช่น field หนึ่งยาวขึ้น อีก field สั้นลงพอดีกัน) cache จะไม่ invalidate แล้วอ่านค่าเก่า สำหรับ `check_budget()` หมายถึง under-count งบประมาณ

**ความเสี่ยงจริงวันนี้:** ต่ำมาก — ต้องมีสองโปรเซสเขียน token analytics พร้อมกันในนาโนวินาทีเดียวกัน "และ" ขนาดบังเอิญเท่ากันเป๊ะ ยังไม่เคยพบเจอจริง เก็บไว้เป็นความรู้ว่ามีช่องโหว่ทางทฤษฎีอยู่ ไม่ต้องรีบแก้ก่อน job queue จริง (ข้อ 2) ซึ่งจะเปลี่ยนโมเดล concurrency ทั้งหมดอยู่ดี
**Fix ถ้าจะแก้:** เนื้อหา hash (เช่น จำนวน events + last event id) แทนการอิง stat() ล้วนๆ, หรือรอย้ายเป็น DB-backed counter ตอนทำ tenant budget (ข้อ 6) เพราะจะพันกันอยู่แล้ว

### 6. Global state ที่ leak ข้าม tenant ได้ถ้าแชร์โปรเซส 🔴
| ที่ | ปัญหา | ผลถ้าไม่แก้ |
|---|---|---|
| `task_manager.py` `_tasks` | มี `owner_id` แล้ว (`18735fd`) แต่ default เดียวกันหมดเพราะไม่มี auth ผูก | รอ auth จริงก่อนถึงจะแยก tenant ได้จริง |
| `render_jobs.py` `ACTIVE_JOBS` | มี `owner_id` แล้วเหมือนกัน (`18735fd`) — เหตุผลเดียวกับข้างบน | เหมือนกัน |
| `token_tracker.py` `_cache`/`_cache_stamp` | class attribute เก็บ JSON ทั้งก้อนในหน่วยความจำ ใช้ร่วมกันทุก request | ยังไม่มี per-tenant analytics file แยก — ต้องออกแบบตอนทำ budget table (ข้อ 6) |
| `product_store.py` `_lock` (เหลือใน `_mutate` wrapper) | SQLite transaction แทน Python lock แล้ว (`83a9f1e`) ไม่ leak ข้าม request แต่ยังไม่มี tenant_id แยกแถว | ไม่ leak แต่ทุก tenant อยู่ตาราง(แถว)เดียวกันหมด — ต้องเพิ่ม column |
| `render_jobs.py` `_RENDER_SLOT` | 1 slot ทั้งโปรเซส (เจตนา — เครื่องนี้ CPU-only) | tenant B รอคิว tenant A เสมอ ไม่มี priority — ดูข้อ 2 |
| `ai_bridge.py` `get_api_keys()` | key list เป็น global | ทำ bring-your-own-key ไม่ได้ |

**หมายเหตุ:** `asset_registry.py` ไม่ต้องใส่ tenant_id — SFX/BGM/font เป็น asset กลางใช้ร่วมกัน (อย่าเสียเวลาแก้)

**เทียบกับเอกสารเก่า:** สองแถวแรก (`task_manager`/`render_jobs`) เอกสารเก่าบอกว่า "leak เงียบ" แบบไม่มีการป้องกันเลย วันนี้มี `owner_id` scoping แล้วจาก `18735fd` — **ลดความเสี่ยงลงจริง** (enumerate job คนอื่นไม่ได้แล้วถ้ารู้แค่ job_id) แต่ยังไม่ใช่ทางแก้เต็มเพราะรอ auth จริงมาผูก `owner_id`

---

## P2 — งานที่ต้องคิดก่อนแตะ (ไม่ใช่บัค แต่ต้องมีคนตัดสินใจ)

### 7. SQLite เป็น document store ไม่ใช่ normalized schema 🟠
`scripts/db.py` + `scripts/product_store.py`

`83a9f1e` ย้าย `ProductStore`/`PostLog` ลง SQLite แล้ว **แต่เก็บเป็น one-row-per-id, ทั้ง record เป็น JSON blob** — `angles`/`videos` ยังซ้อนอยู่ใน JSON ของแถว `products` ไม่ได้แยกเป็นตารางลูก

เหตุผลที่ commit ให้ไว้ (`83a9f1e`) ยังคงถูกต้องวันนี้: **หลายจุดเรียกผ่าน `_load()`/`_save()` ตรงๆ แล้วแก้ nested `angles`/`videos` in-place** (ไม่ใช่ผ่าน public method) — ถ้า normalize ตอนนี้ต้อง rewrite ทุก call site พร้อมกัน ไม่ใช่แค่ schema migration เฉยๆ

**สิ่งที่ต้องมีก่อนจะ normalize ได้จริง:**
1. Audit ทุกจุดที่แตะ `product["angles"]`/`product["videos"]` โดยตรง (ไม่ผ่าน helper method) — จะได้ list ของ call site ที่ต้อง rewrite พร้อมกัน
2. ตัดสินใจ schema ที่ข้อ 11 ของเอกสารนี้ร่างไว้ (`angles` ตาราง, `angle_video_links` join table แทน array)
3. เขียน migration ที่ backfill พร้อม verify id ทุกตัว (มี pattern ให้ทำตามแล้วจาก `scripts/migrate_json_to_sqlite.py`)

**Effort:** LARGE — ห้ามประเมินเป็น "แค่ ALTER TABLE" เพราะตัวบล็อกจริงคือ call site ที่แก้ nested structure ตรงๆ ไม่ใช่ schema เอง

### 8. Media ยังอยู่ local disk — แต่ object storage ทำได้แล้ววันนี้ ✅ (เปลี่ยนจากเดิม)
`cea03eb` ลบ blocker เดิมออกแล้ว: path ทั้งหมด (`angle.video_url`, `angle.selected_videos`, `product.videos[].rel_path`) เก็บเป็น BASE_DIR-relative จริงแล้ว (ก่อนหน้านี้ `rel_path` เก็บ absolute path เหมือน `path` เป๊ะ — ชื่อฟิลด์หลอก ตอนนี้แก้แล้ว) มี `scripts/migrate_paths_to_relative.py` แปลงของเก่า (round-trip verify ก่อนเขียนทับ)

**ยังต้องมีก่อนย้ายจริง:** `MediaStore` abstraction 2 backend (local passthrough / object-store ที่ download มา scratch dir ก่อน render แล้ว upload กลับ) — **ffmpeg อ่าน S3/GCS URL ตรงๆ ไม่ได้** ต้องมีไฟล์บนดิสก์เสมอ

**สำคัญ:** `tmp.write_text()` + `tmp.replace()` เป็น atomic เฉพาะ local filesystem — object store ไม่มี rename atomic ต้องออกแบบใหม่ตอนถึงจุดนั้น

**คำแนะนำ:** local disk พอสำหรับ MVP SaaS ย้ายขึ้น object storage เมื่อ (ก) worker หลายเครื่อง (ข) storage เกินดิสก์เดียว (ค) ต้องการ CDN — blocker เดิม (absolute path) หายไปแล้ว เหลือแค่เป็นงานที่ทำได้เมื่อจำเป็น ไม่ใช่ prerequisite
**Effort:** MEDIUM (wrapper layer เท่านั้น — ffmpeg/PIL ตรงกลางไม่ต้องแก้)

### 9. Schema mapping ถ้าจะ normalize (จาก record จริง)
**`products`** — `tenant_id` FK NOT NULL indexed (ยังไม่มี), `platform` ควรเป็น enum (วันนี้ free-form), `product_code` ต้อง `UNIQUE (tenant_id, product_code)` และ `_generate_product_code()` ต้อง scan เฉพาะ tenant ตัวเอง (วันนี้ scan ทั้งตาราง)

**`angles`** — ต้องแยกเป็นตารางเอง (วันนี้ซ้อนใน `products` JSON) `angle_id` เป็น taxonomy คงที่ ~7-8 ตัวแต่เก็บเป็น free text ตัดทิ้งได้: `script_text` (= join ของ `script_lines`) และ `selected_video` (= `selected_videos[0]`) คำนวณตอนอ่านแทน

**`videos`** — ต้องแยก. `selected_videos` ควรเป็น join table `angle_video_links(angle_id, video_id, position)` ไม่ใช่ array ของ path (path เก็บ relative แล้วตั้งแต่ `cea03eb` — เหลือแค่ schema)

**`posts`** — ไม่มี `product_id` FK เลย วันนี้ join กลับหา product ได้แค่ด้วยชื่อ (fuzzy) ต้องเพิ่ม FK แล้ว backfill โดย match `clip_file` กับ `angle.video_url`

**`usage_events`** — map ตรงๆ ได้ **`totals` เปลี่ยนสถานะแล้ว**: เดิมเป็น manual-sync aggregate ที่ drift ได้ วันนี้ `22559a1` ทำให้ reconstructable แล้ว (`totals == trimmed_aggregate + sum(events)`, ยืนยันด้วย test) — ยังแนะนำให้ใช้ `SUM() GROUP BY` ตอนอ่านถ้าย้ายลง DB จริง เพราะ SQL ทำ aggregate ได้ native โดยไม่ต้องพึ่ง invariant ที่ต้องรักษาด้วยมือ

### 10. Rendering — สองระบบซ้อนกันเหมือนเดิม (ยังไม่รวม)
1. `render_jobs.py` — `ACTIVE_JOBS` in-memory + `_RENDER_SLOT` ล็อกเดียว, หายหมดตอน restart, มี `owner_id` แล้ว
2. `task_manager.py` — persist ลง `task_registry.json`, `ThreadPoolExecutor(max_workers=4)`, restart แล้ว mark ทุกงานค้างเป็น failed ไม่ resume, มี `owner_id` แล้ว, terminal-state guard แล้ว (`18735fd` — `complete_task()`/`fail_task()` ไม่ทับ state ที่จบแล้วอีก)

**ยังต้องเช็ค:** สองระบบนี้ใช้กับ job คนละชนิดจริงหรือทับซ้อนกันโดยไม่ตั้งใจ — ยังไม่มีใครตอบคำถามนี้

**Target เดิมยังใช้ได้:** arq เหมาะกว่า Celery สำหรับทีมเล็ก, `_RENDER_SLOT` → worker pool sizing + per-tenant concurrency

---

## สิ่งที่ต้องมนุษย์ตัดสินใจ (ไม่ใช่บัค)

### 11. `ad_tone` ที่ไม่รู้จักตกไปใช้ prompt `commercial_premium` เงียบๆ
`scripts/gemini_tts_engine.py:161`, `scripts/overlay_model.py:174`

พฤติกรรมนี้ยืนยันแล้วว่า**ยังอยู่เหมือนเดิม** (`a2a9eff` เขียน test cover พฤติกรรมนี้ตามที่เป็นอยู่ ไม่ได้เปลี่ยน) คำถามที่ต้องตอบ: อยาก fallback เงียบๆ แบบนี้ต่อไป (ยืดหยุ่นกับ tone ใหม่ที่ยังไม่ list) หรืออยาก raise/warn เมื่อเจอ `ad_tone` ที่ไม่รู้จัก (จับ typo/data เพี้ยนได้เร็วกว่า)

### 12. Vision matcher คืน cache เก่าข้าม cue set ได้เมื่อ parse response ไม่ออก
`scripts/gemini_vision_matcher.py:260,366,417` — เมื่อ parse response จาก Gemini ไม่สำเร็จ โค้ด fallback ไปหา cache entry ตัวไหนก็ได้ที่ **share แค่ file hash เดียวกัน** (`if k.startswith(file_hash) and v`) ไม่ตรวจว่า cue set เดียวกันไหม (`match_cache_key` เต็มคือ `file_hash + cue_hash`)

ยืนยันแล้วว่ายังอยู่เหมือนเดิม (`a2a9eff` cover พฤติกรรมนี้ตามที่เป็น ไม่เปลี่ยน) **ความเสี่ยงจริง:** แก้สคริปต์ (เปลี่ยน cue) แล้ว render ใหม่ แต่ vision response ครั้งใหม่ parse ไม่ออก (เช่น Gemini ตอบ format แปลก) → ได้ scene matching ของสคริปต์ **เก่า** มาใช้แบบเงียบๆ ไม่มี error

คำถามที่ต้องตอบ: อยากให้ fallback ไปหา cache แบบกว้างๆ (ดีกว่าไม่มีอะไรเลยตอน API ล่ม) หรืออยากให้ fallback แคบลงเหลือแค่ cue_hash เดียวกัน (ปลอดภัยกว่าแต่ parse fail = ไม่มี match เลย)

---

## ✅ สิ่งที่ทำถูกอยู่แล้ว (อย่าเสียเวลาแก้)

**Backend/data**
- Atomic write (tmp + replace) — ใช้ได้กับ local filesystem
- `gemini_vision_matcher.py` cache keyed by file hash + cue hash เช็คก่อนเรียก API ถูกต้อง (bug ที่เคยทำให้ cache ไม่เคยถูกเขียนแก้แล้วที่ `ece95f1`)
- SQLite transaction (`BEGIN IMMEDIATE`) ที่ `db.py` — ปิด lost-update race ได้จริงยกเว้น 1 จุด (ข้อ 3)
- Render หลักเป็น ffmpeg pass เดียว ไม่ re-encode ซ้ำ
- `asset_registry.py` ไม่ต้องมี tenant_id — asset กลางใช้ร่วมกันถูกแล้ว

**Frontend**
- `hooks/useProjectLoader.js` — `requestSequence` guard เป็นต้นแบบที่ถูกต้อง (ตอนนี้ `ContentTrackerHub.jsx`, `api.js`'s task poll, link modal ก็ตามแบบนี้แล้วหลัง `d4fc3dc`/`a8c7870`)
- `hooks/useProjectAutosave.js` — sequence queue + debounce + `beforeunload` flush ครบ
- `TaskContext` value memoized แล้ว (`3be4403` — แก้ re-render ที่กระจายไปทุก consumer ตอน poll ทุก 1.5s)
- Code splitting ด้วย `React.lazy` ครบ 7 route
- ไม่มี N+1 fetch ใน `.map`

**Pipeline**
- ffmpeg filter graph ไม่ใช้ `drawtext` (caption ไปทาง `.ass` + PIL) เลี่ยงช่องโหว่คลาสสิกไปได้
- TTS/timeout/ffprobe silent-fail ทั้งชุดแก้แล้ว (ดู "สิ่งที่แก้ไปแล้ว" ด้านล่าง)

**Chrome extension**
- `host_permissions` แคบ (localhost:8000 + tiktok.com เท่านั้น) ไม่มี `<all_urls>`
- Error plumbing ถูกต้อง — throw แล้วเด้งถึง UI จริง (`sidepanel.js:230-243`)
- `automation.js` มี `page()`/`buttonQuery()` helper — pattern ดี แต่ยังไม่ถูกขยายไปใช้ทั่ว (ดูข้อ 13)
- Post/link-attach/schedule-toggle ตอนนี้ poll ยืนยันผลจริงก่อน report success แล้ว (`c12527b` + live-verify รอบ POST-3.1-3.4)

---

## ยังเปิดอยู่: Chrome extension (พื้นที่ของ dev อีกคน — ไม่แตะโค้ด แต่บันทึกไว้)

### 13. Selector ยังกระจัดกระจาย ไม่มีไฟล์กลาง 🟡
ไม่มี `selectors.js` หรือไฟล์รวม selector ใดๆ — `background.js` ยัง hand-roll แยกทุกฟังก์ชัน (68 จุดที่เรียก `querySelector`/`getElementById` ใน `background.js` ไฟล์เดียว) ประวัติ commit ช่วงนี้เห็นชัดว่าเป็นปัญหาจริง: `03c47cf`, `279b8ee`, `33210f2`, `bfeb7e6`, `f8be9b7`, `7c5cf50`, `78eda05`, `32c6972`, `ae9cced` — **9 commit แก้ selector/targeting ใน 28 commit ล่าสุด** เกือบหนึ่งในสาม

การรวมเป็นไฟล์เดียวจะคุ้มมากขึ้นเรื่อยๆ ทุกครั้งที่ TikTok เปลี่ยน UI — แต่ไม่ใช่ของที่แก้ได้ในเอกสารนี้ (directory เป็นของ dev อีกคน)

### 14. Cover flow ผ่าน CDP path ของ extension เอง — ยังไม่ verify จริง 🟠
`b24091d` บันทึกไว้ชัดเจน: Playwright session จริงเปิด Cover Studio ได้ พบ `label.ImageUpload__uploadArea` แต่ **การส่งไฟล์ผ่าน Playwright ถูกปฏิเสธ** (`fileChooser.setFiles: Not allowed`) — เป็นข้อจำกัดของ browser sandbox ไม่ใช่บัคของ extension เอง

extension มีทางของตัวเอง (upload ผ่าน CDP โดยตรง ไม่ใช้ OS file dialog — ตาม commit `a968d9f` ก่อนหน้า `d4fc3dc`) แต่**เส้นทางนั้นยังไม่เคย verify กับ TikTok จริงหลังแพตช์รอบล่าสุด** (`008aadd`, `ae9cced` แก้ cover upload/diagnostics เพิ่มอีก แต่ TODO.md เองยังทำเครื่องหมาย task นี้ค้างอยู่ที่ POST-3.4: "ทำให้ข้อแนบปกเปิด Cover Studio ได้... ยืนยัน flow หน้าปก... โดยไม่กดเผยแพร่" — ยังไม่ติ๊ก)

**นี่คือ gate ที่เปิดอยู่จริง ไม่ใช่แค่เอกสารเก่า** — ต้องรอทดสอบผ่านตัว extension ในเบราว์เซอร์จริง (ไม่ใช่ Playwright) ก่อนเชื่อว่าใช้ได้

---

## ลำดับการทำ (แนะนำใหม่ — เรียงตาม leverage วันนี้)

**เฟส 0 — เก็บของที่ทำค้าง (เล็ก, ทำได้ทันที)**
1. ต่อสาย `X-API-Key` เข้า extension (ข้อ 1) — ก่อน `OMNICUT_API_KEY` จะถูกเปิดใช้จริงเมื่อไหร่ก็ได้แล้วมันจะพังทันที
2. ห่อ `reconcile_existing_projects()` ด้วย `_mutate()` (ข้อ 3) — เป็นรูโหว่เดียวที่เหลือของ pattern ที่ `83a9f1e` เพิ่งปิดไปทั้งระบบ

**เฟส 1 — Auth จริง (จุดที่ block ทุกอย่างต่อจากนี้)**
5. ออกแบบ user/session model — JWT หรือ session cookie, ตาราง `users`
6. ผูก `owner_id` (มีโครงจาก `18735fd` แล้ว) เข้ากับ user จริงแทน `"local"` คงที่
7. CORS allowlist + API key gate ที่มีอยู่แล้ววันนี้ (`c12527b`) ใช้เป็นฐานได้เลย ไม่ต้องเขียนใหม่

**เฟส 2 — Multi-tenant data (ใหญ่ ต้องแยกเป็นสัปดาห์)**
8. เพิ่ม `tenant_id` column ทุกตาราง SQLite ที่มีแล้ว (`83a9f1e` วางฐานไว้ให้)
9. ร้อย `tenant_id` ผ่าน endpoint ทั้งหมด (108+ ตัว) — งาน mechanical แต่เยอะ ต้อง test ด้วย 2 tenant จริงยิงทุก endpoint
10. Budget table ต่อ tenant (ข้อ 6) — โครง `check_budget()` พร้อมแล้ว เหลือแค่ schema

**เฟส 3 — Scale infrastructure (ทำเมื่อ user จริงเริ่มชนขีดจำกัด ไม่ใช่ preemptive)**
11. Job queue จริง (arq) แทน `_RENDER_SLOT` เดี่ยว (ข้อ 2)
12. Object storage (ข้อ 10) — ทำได้แล้ววันนี้ แต่รอจนกว่าดิสก์เดียวไม่พอจริง
13. Normalize SQLite schema (ข้อ 9, 11) — รอจนกว่า record count เริ่มกระทบ perf จริง (JSON blob ต่อแถวยังไหวถึงหลักพัน record)

**เฟส 4 — ตัดสินใจที่รอมนุษย์ (ทำเมื่อไหร่ก็ได้ ไม่ block อะไร)**
14. `ad_tone` fallback เงียบๆ (ข้อ 11) — ตอบแล้วค่อยแก้โค้ด
15. Vision cache stale-match scope (ข้อ 12) — ตอบแล้วค่อยแก้โค้ด

---

## สิ่งที่แก้ไปแล้ว (ตั้งแต่ `d4fc3dc`) — เก็บไว้เป็นความรู้ ไม่ใช่ของค้าง

รวม 28 commit ระหว่าง `d4fc3dc..ae9cced` เก็บเฉพาะที่เป็น failure mode ที่ codebase นี้เคยผลิตจริง คุ้มจำไว้กันเกิดซ้ำ:

- **Path traversal (write + read)** — `product_id`/path จาก client ไม่ sanitize, `startswith()` string-prefix เช็ค containment ผิดวิธี (`D:\...\Capcut_evil\` ผ่านเช็คได้เพราะขึ้นต้นด้วย `D:\...\Capcut`) → เปลี่ยนเป็น component-wise / `relative_to()` ทุกจุด (`d4fc3dc`)
- **SSRF ใน product scraper** — เช็คแค่ scheme, follow redirect โดยไม่ validate host ใหม่ → เพิ่ม resolve+block private/loopback/link-local ทุก redirect hop + domain allowlist (`d4fc3dc`)
- **Lost-update race ใน JSON store** — `_load()` อยู่นอกล็อก, `_save()` อยู่ในล็อก → สอง request เขียนพร้อมกันข้อมูลหายเงียบ → ย้ายทั้งคู่ (`ProductStore`/`PostLog`) ไป SQLite + `BEGIN IMMEDIATE` transaction ครอบ read-modify-write เป็นก้อนเดียว (`83a9f1e`)
- **Absolute path ฝังใน data** — ย้ายเครื่อง/rename โฟลเดอร์/ขึ้น container พัง → normalize เป็น BASE_DIR-relative ทุกจุด + migration script (`cea03eb`)
- **TTS ล้ม 1 บรรทัดเงียบๆ → subtitle เพี้ยนทั้งคลิปถาวร** — ไม่มี else, ไม่ log → ใส่ silence ความยาวเท่ากันแทนแล้ว log warning (`c12527b`)
- **Render timeout → ffmpeg ผีค้าง** — `TimeoutExpired` ไม่มีใคร catch → ห่อ try/finally kill process + unlink partial (`c12527b`)
- **ffprobe ล้ม → แอบใส่ 15 วินาทีเงียบๆ** → เปลี่ยนเป็น raise error (`c12527b`)
- **Thai caption ล้นเฟรม** — tokenize เฉพาะตอนไม่มีช่องว่างเลย → trigger เมื่อชิ้นไหนยาวเกิน limit ด้วย (`c12527b`)
- **Font ที่ทำสระ/วรรณยุกต์ไทยยุบ** — Kanit/Prompt ไม่มี GPOS mark-anchor → ถอดออกจาก picker, map "Noto Sans Thai" ให้ตรง family จริง (ก่อนหน้านี้ silently fallback เป็น IBM Plex) (`b26dcfc`)
- **Vision cache ไม่เคยถูกเขียน** — `NameError` บน `match_cache_key` ที่ scope ผิดฟังก์ชัน ถูก broad except กลืน → ทุก render จ่าย Gemini ซ้ำทั้งที่ควร cache hit → แก้ scope + จำแนก retry ตาม error type จริง (429 backoff+retry same key, auth error rotate, quota error ไม่ retry) (`ece95f1`)
- **Extension silent-success** — post/link-attach/schedule-toggle report สำเร็จโดยไม่เช็คผลจริงเลย, caption verify แค่ 10 ตัวอักษรแรก → เพิ่ม poll ยืนยันหลักฐานจริงก่อน report + เทียบ full string (`c12527b`, ตามด้วย live-verify หลายรอบ POST-3.1-3.4)
- **Quota check ไม่ครบทุกจุดจ่ายเงิน** — มี 3 จุดสร้าง `genai.Client` ตรงๆ ข้าม `check_budget()` ได้ → ปิดครบ (`1b9ba1d`)
- **ASS injection ผ่านชื่อสินค้า** — `{\...}` ที่ scrape มาจาก listing ไม่ escape → escape braces/backslash ก่อนแทรก (`1c0e07b`)
- **Sticker overlay input index คำนวณผิด** — สมมติ 2 slot ต่อ input แต่ clip_list render ให้ 6 → 3 คลิปขอ stream 10 ของ 5 ที่มี (`1c0e07b`)
- **`[v_concat]` label ไม่ถูก define ตอน render คลิปเดียวพร้อม transition** → fallback ไป plain concat path (`3be4403`)
- **`generate_motion_video_from_images()` NameError** — refactor ก่อนหน้าลบ local variable ที่ยังใช้อยู่ → เพิ่มกลับ (`e6ad5d3`)
- **`totals` ใน token_tracker drift ไม่มีทาง reconstruct** — events trim ที่ 1000 แต่ totals สะสมตลอดชีพ → เพิ่ม `trimmed_aggregate` ให้ invariant ตรวจสอบได้จริง + cache invalidate ด้วย mtime_ns+size แทน mtime เฉยๆ (`22559a1`)
- **Frontend fetch race บนตาราง tracker** — `fetchProductsData()` ไม่มี sequence guard, optimistic update ชนกับ refetch → ตาม pattern `useProjectLoader.js` (`d4fc3dc`, ขยายเพิ่มที่ task poll และ link modal ใน `a8c7870`)
- **O(n²) scan ใน export gallery/raw vault** → สร้าง lookup dict ครั้งเดียวต่อ request (`d4fc3dc`)
- **Test เขียนทับ data จริง** — `test_analysis_fixes.py`, `test_export_versioning.py` ไม่ใช้ `tmp_path` → isolate แล้ว (`d4fc3dc`, เพิ่มอีกใน `1c0e07b` ที่พบ 4 test สร้าง real project dir ใต้ `03_Projects`)
- **Task/job id เดาได้ + ไม่มี owner scoping** — `f"task_{ms_timestamp}_{6 hex}"` walkable, `_tasks`/`ACTIVE_JOBS` ไม่มี owner key เลย → `secrets.token_urlsafe(16)` + `owner_id` scoping ทุก lookup/mutation (`18735fd`)
- **`complete_task()`/`fail_task()` ไม่มี terminal guard** — task ที่ fail แล้วโดน complete ทับสถานะได้ (ค้าง error ไว้พร้อม status COMPLETED) → เพิ่ม guard (`18735fd`)
- **`renderJobModel.js` key ด้วยชื่อ project ที่แสดงผล** — label ต่างกันระหว่าง save/read (EditorShell กับ NewClipPanel คำนวณคนละที่) ทำให้หา job ที่กำลังรันไม่เจอ UI บอกว่าไม่มี render, และ fallback `'วิดีโอ'` ทำให้ render ที่ไม่มีชื่อสองงานทับ key กัน → เปลี่ยนเป็น key เดียวทั้งแท็บถือ `{jobId, projectKey}` addressed ด้วย uuid4 ของ job (`46135c7`)
- **`import.meta.env` ล้มตอนรัน lib test** — interceptor `X-API-Key` อ่าน `import.meta.env.VITE_API_KEY` ตรงๆ แต่ `node --test` ไม่ผ่าน Vite → throw ล้มไป 2 suite → optional chaining (`46135c7`)
- **Render ที่ล้มกลางทางตามรอยโฟลเดอร์ไม่ได้** — ชื่อโปรเจกต์ที่ stage 1 ตั้งเองอยู่แค่ใน `ctx` จน `run()` return, `api_render` ใช้ `req_data.project_name` ที่เป็น `None` พอดี, `fail_job` fallback อ่าน `job["result"]` ที่มีค่าแค่ตอนสำเร็จ (dead logic) → stamp ชื่อบน exception + เขียน `.run_started.json` เป็น breadcrumb (ตั้งใจไม่ใช่ `project.json` เพราะ `require()` ถือว่ามี manifest = render เสร็จ จะทำให้ reroll วิ่งบน artifact ที่ไม่มี) (`566c3de`)
- **Test diagnostics เขียนไฟล์ลง repo root ทุกครั้งที่รัน** — 8 ไฟล์ใน `tests/` ไม่มี test function แต่ pytest import ตอน collect ทำให้ module body รัน → ใส่ `__main__` guard + ลบ artifact 14 ไฟล์ที่ค้าง (`cd2d778`)
- **`keyframe_engine.py` + `keyframeModel.js` เป็น Phase 9 scaffolding ที่ไม่มีใครเรียก** — ตรวจแล้ว**ไม่ลบ** เพราะมี easing/clamping/tier resolution ที่ของ live ไม่มี และ `TEMPLATE_MOTION_PLAN.md` ยังอ้าง `ease_out` เป็น naming guard → ใส่ STATUS ใน docstring ชี้ไปที่ของจริง (`video_editor.interpolate_keyframes`, `timelineMath.interpolateKeyframes`, easing ใน `SequencePlayer.jsx`) (`cd2d778`)

---

## ยังไม่ได้ตรวจ (เหมือนเดิม ยังไม่มีข้อมูลเพิ่ม)

- **Test coverage gap ที่เหลือ** — `a2a9eff` เพิ่ม test ให้ 5 module ที่ไม่เคยมี (overlay/hook-style/Gemini engine paths) แต่ยังไม่ได้ scan ทั้ง `tests/` หาโมดูลอื่นที่ไม่มี test เลย
- **Frontend ที่เหลือ** — `Timeline.jsx`, `context/` ที่เหลือ (นอกจาก `TaskContext` ที่เพิ่งแก้), `api.js` ส่วนที่ไม่เกี่ยวกับ auth header
- **Chrome extension เชิงลึกกว่านี้** — ปิดแท็บกลางคัน, service worker ตายกลาง flow (MV3 kill ตอน idle) ยังไม่ verify ว่าแก้ครบหรือยัง แม้จะมี fix รอบใหญ่หลายรอบแล้ว
- **`overlay_model.py`, `sfx_manager.py` audio-mix division math** — ยังไม่ได้ audit เชิงลึก
- **`video_editor.py` filter-graph construction บรรทัด 1-900 ส่วนใหญ่** — ยังไม่ได้ scan ทั้งไฟล์ มีแค่จุดที่บัคเฉพาะพา (timeout handling, sticker index) ถูกแก้ไปแล้ว
