# SaaS Readiness Plan

Audit ของ Capcut content studio — สถานะปัจจุบัน, จุดบัค/จุดเสี่ยง, และสิ่งที่ต้องแก้ก่อนเปิดให้คนอื่นใช้

สถานะวันนี้: **single-user local app** — data เป็นไฟล์ JSON ใน `_Docs/`, media อยู่ในโฟลเดอร์ `00_Inbox`…`06_Archive`, ไม่มี auth, รัน render ในโปรเซสเดียวกับ API

> ทุกข้อด้านล่าง **verify จากโค้ดจริงแล้ว** ไม่ใช่การเดา
> รอบแรก audit เอง (agent ชน session limit), รอบสองยิง agent สำเร็จ 3 ด้าน: frontend React, security (path traversal/SSRF), performance
> ยังเหลือพื้นที่ที่ยังไม่ได้ scan — ดูหัวข้อ "ยังไม่ได้ตรวจ" ท้ายเอกสาร

---

## สรุปผู้บริหาร

| ด้าน | สถานะ |
|---|---|
| Atomic write | ✅ ดีอยู่แล้ว (tmp + replace) |
| Command injection (`shell=True`) | ✅ ไม่พบ |
| Secret hardcode | ✅ ไม่พบ (ใช้ env, มีแค่ `.env.example` ใน git) |
| Repo hygiene | ✅ `.gitignore` ครอบคลุมดี |
| `pickle`/`eval`/`exec`/unsafe yaml | ✅ ไม่พบใน `scripts/` |
| `dangerouslySetInnerHTML` (XSS) | ✅ ไม่พบใน `frontend/src/` |
| Extension host_permissions | ✅ scope แคบดี (localhost + tiktok.com เท่านั้น) |
| **Arbitrary file write (path traversal)** | 🔴 exploit ได้จริง ไม่ต้อง login |
| **SSRF (cloud metadata)** | 🔴 ขโมย IAM credential ได้ตอนขึ้น cloud |
| **ไม่มี auth เลย** | 🔴 blocking สำหรับ SaaS |
| **CORS `*`** | 🔴 blocking |
| **Frontend fetch race** | 🔴 ข้อมูลที่เพิ่งเซฟ revert เอง |
| **ไม่มี quota enforcement** | 🔴 blocking (เผาเงิน AI ได้ไม่จำกัด) |
| **Lost update race (backend)** | 🔴 มีจริง ~20 จุด |
| **Absolute path ใน data** | 🟠 ย้ายเครื่องพัง |
| **Test เขียนทับ data จริง** | 🟠 รัน test ทีไรเลอะทุกที |

---

## P0 — บัคที่มีผลตอนนี้ (แก้ได้เลย ไม่ต้องรอ SaaS)

### 1. Lost update race ใน ProductStore 🔴
`scripts/product_store.py:34,40,50`

`_lock` ล็อกเฉพาะตอน `_save()` แต่ pattern จริงคือ:

```
products = cls._load()   # ← นอกล็อก
...mutate...
cls._save(products)      # ← ล็อกแค่ตรงนี้
```

มีประมาณ 20 จุดที่ทำแบบนี้ (`add`, `update`, `update_angle_status`, `update_angle_videos`, `add_video_to_product`, `delete`, …)

**Failure scenario:** สอง request เข้าพร้อมกัน — A อ่าน 10 products, B อ่าน 10 products, A เพิ่มตัวที่ 11 เซฟ, B เพิ่มตัวที่ 11 (คนละตัว) เซฟทับ → **ของ A หายเงียบ** ไม่มี error ไม่มี log

ตอนนี้เจอไม่บ่อยเพราะใช้คนเดียว แต่ background render job + UI poll ยิงพร้อมกันก็ชนได้แล้ว

**Fix:** ย้าย `_load()` เข้ามาในล็อกเดียวกับ `_save()` — ทำ `_mutate()` context manager ที่ครอบทั้ง read-modify-write ในล็อกเดียว แล้วให้ทุก method เรียกผ่านมัน
**Effort:** SMALL (ครึ่งวัน) — แก้จุดเดียวแล้ว refactor call site
**หมายเหตุ:** `threading.Lock` แก้ได้แค่ในโปรเซสเดียว พอขึ้น multi-worker/gunicorn ต้องเป็น DB transaction แทน (ดู P2)

### 2. Test เขียนทับ `_Docs/post_log.json` จริง 🟠
`tests/test_analysis_fixes.py`

ไม่ใช้ `tmp_path` — รัน pytest ทีไร append fixture ปลอม ("Test Serum Anti-Aging") ลง log จริง + สร้าง `products.json.bak*` เกลื่อน

เจอตอน commit รอบที่แล้ว ต้อง revert มือ

**Fix:** ใช้ `tmp_path` + `monkeypatch` ตาม `.agents/rules/testing_standard.md` rule 3 (repo มี rule นี้อยู่แล้ว ตัว test แค่ไม่ทำตาม)
**Effort:** SMALL
**ต้องเช็คเพิ่ม:** test ตัวอื่นที่มีปัญหาเดียวกัน — ยังไม่ได้ scan ครบ

### 3. `_Docs/post_log.json` ถูก track ใน git 🟠
Data ปนกับ code — ทุกครั้งที่โพสต์จริง git จะ dirty, และเป็นเหตุให้ข้อ 2 มองเห็นใน diff

`products.json` ไม่ถูก track (ถูกแล้ว) แต่ `post_log.json` ถูก track

**Fix:** `git rm --cached _Docs/post_log.json` + ใส่ `.gitignore` + commit ตัว seed/example แทนถ้าจำเป็น
**Effort:** SMALL

### 4. Absolute path ฝังใน data 🟠
`_Docs/products.json` เก็บ `"D:\\Winona\\Programmer\\Capcut\\01_Raw\\..."` เต็มๆ

**Failure:** ย้ายเครื่อง / เปลี่ยนชื่อโฟลเดอร์ / ขึ้น Docker → path ทั้งหมดเสีย
`scripts/config.py:5` คำนวณ `BASE_DIR` แบบ dynamic อยู่แล้ว แต่ data ที่เซฟไปแล้วเป็น absolute

**Fix:** เก็บเป็น path relative จาก `BASE_DIR` แล้ว resolve ตอนอ่าน + เขียน migration script แปลงของเก่า
**Effort:** MEDIUM (1–2 วัน — ต้องไล่ทุกจุดที่อ่าน/เขียน path)
**นี่คือ blocker ของ SaaS ด้วย** — object storage ทำไม่ได้ถ้ายังฝัง local path

---

## P0.5 — ช่องโหว่ที่ exploit ได้จริงวันนี้ 🔴🔴

> เจอจาก agent audit รอบสอง — หนักกว่าที่ประเมินรอบแรก
> ข้อ 4a/4b **exploit ได้โดยไม่ต้อง login** และเพราะ CORS `*` + ไม่มี auth = **เว็บไหนก็ตามที่คุณเปิดค้างไว้ ยิงได้เลย** ขณะที่ app รันอยู่

### 4a. Arbitrary file write ผ่าน `product_id` 🔴 CRITICAL
`scripts/api_videos.py:149-151`

```python
if product_id:
    dest_dir = RAW_DIR / product_id      # ← ไม่ sanitize เลย
    dest_dir.mkdir(parents=True, exist_ok=True)
```

บรรทัดถัดมา `custom_name` และ `orig_filename` sanitize ครบ (alnum allowlist) แต่ `product_id` ไม่มีอะไรเลย

**Exploit 2 แบบ:**
- relative: `product_id = "..\..\..\..\Windows\Temp"` → เขียนลง `C:\Windows\Temp\`
- absolute: `product_id = "C:\Users\Public"` → **Python ทิ้ง base path ทันทีเมื่อ join กับ absolute path** → เขียนที่ไหนก็ได้ที่โปรเซสมีสิทธิ์

นี่คือ **remote unauthenticated arbitrary-file-write** — ร้ายแรงสุดในทั้งหมด

**Fix:** sanitize เหมือน `custom_name` หรือเช็ค `dest_dir.resolve().relative_to(RAW_DIR.resolve())` ก่อน `mkdir`
**Effort:** SMALL (แก้ 3 บรรทัด)

### 4b. SSRF ใน product scraper 🔴 CRITICAL
`scripts/product_scraper.py:50-51, 68-69, 89`

เช็คแค่ scheme (`http://`/`https://`) **ไม่มี IP allowlist/denylist เลย** และ `urllib` follow redirect อัตโนมัติ แล้วเอา `resp.geturl()` ไป fetch ซ้ำ **โดยไม่ validate host ใหม่**

**Exploit:**
- `http://169.254.169.254/latest/meta-data/iam/security-credentials/` → **ขโมย IAM credential ของ server** (พอขึ้น cloud)
- `http://127.0.0.1:8000/...` → ยิง API ตัวเองจากข้างใน
- `http://192.168.x.x/`, `http://10.x.x.x/` → scan เครือข่ายภายใน (ผลลัพธ์ title/price เด้งกลับมา = ใช้เป็น oracle ได้)
- redirect bypass: เว็บของ attacker 302 ไป internal target → follow ตามไปเลย

**Fix:** resolve hostname แล้ว block loopback/private/link-local (127.0.0.0/8, 169.254.0.0/16, RFC1918, ::1, fc00::/7) — เช็คทั้ง URL แรกและทุก redirect hop; ปิด auto-redirect แล้ว validate เอง; เพิ่ม domain allowlist (Shopee/TikTok เท่านั้น เพราะเป็น use case เดียวที่ต้องใช้)
**Effort:** SMALL–MEDIUM

### 4c. `startswith()` เช็ค path containment ผิดวิธี 🟠 HIGH
`api_covers.py:60`, `api_editor.py:45`, `api_videos.py:508, 545`

```python
if not (str(target).startswith(str(BASE_DIR)) or ...):
```

string prefix ไม่ใช่ path containment — `D:\...\Capcut_evil\secrets.txt` ผ่านการเช็คได้ เพราะขึ้นต้นด้วย `D:\...\Capcut`

น่าสนใจ: `api_videos.py:90, 287, 349` ใช้ `relative_to()` ถูกต้องอยู่แล้ว — แค่ไม่สม่ำเสมอ

**Fix:** เปลี่ยนทุกจุดเป็น `target.relative_to(BASE_DIR)` + catch `ValueError`
**Effort:** SMALL

### 4d. Arbitrary file read ผ่าน filmstrip/cover endpoint 🟠
`api_covers.py:54-64`, `api_editor.py:38-49, 123-139`

`GET /api/editor/filmstrip?path=...` รับ path จาก client, `unquote` แล้วเช็คแค่ว่าอยู่ใต้ `BASE_DIR` (กว้างมาก ไม่จำกัดเฉพาะโฟลเดอร์ media)

รวมกับ CORS `*` + ไม่มี auth → เว็บไหนก็ยิง `fetch('http://127.0.0.1:8000/api/editor/filmstrip?path=..%5C..%5C.env')` จาก browser เหยื่อได้

**Fix:** ตอนทำ multi-tenant ต้อง scope ทุก path เป็น `tenant_root / relative_path`, reject `..` และ absolute path ตรงๆ (อย่า rebase เงียบๆ)

### 4e. Extension `debugger` permission + เชื่อ local API ดื้อๆ 🟠 HIGH
`tiktok_autopost_extension/manifest.json`

`host_permissions` แคบดี (localhost:8000 + tiktok.com เท่านั้น) ✅ แต่ `permissions` มี **`debugger`** — สิทธิ์แรงสุดตัวหนึ่งของ Chrome (attach DevTools Protocol คุม DOM/network/JS ของ tab ได้เต็ม)

ปัญหาคือ extension เชื่อ response จาก local API ที่**ไม่มี auth** แล้วเอาไปสั่งงานผ่าน `chrome.debugger` บน TikTok session จริง → ถ้ามีอะไรยิง localhost:8000 ได้ (ซึ่ง = ทุกแท็บที่เปิดอยู่) ก็สั่ง extension โพสต์อะไรก็ได้

**Fix:** ใส่ shared secret ระหว่าง extension ↔ API, pin CORS เป็น origin ของ extension, treat API response เป็น untrusted input

### 4f. ffmpeg filter / ASS injection 🟡 MEDIUM
- `video_editor.py:815, 825, 878-879` — escape แค่ `\` กับ `:` **ไม่ escape `'`** ในชื่อ path ที่ยัดเข้า filter string. วันนี้ยังปลอดภัยเพราะ path มาจาก config ไม่ใช่ user แต่ **ถ้า `product_id` (ข้อ 4a ที่ไม่ sanitize) ไหลลงมาถึงตรงนี้เมื่อไหร่ = inject filtergraph ได้**
- `subtitle_engine.py:604-687` — ยัด caption/product name ลง ASS override tag โดยไม่ escape `{` `}` → ชื่อสินค้าที่มี `{\...}` ทำ subtitle เพี้ยนได้ (แค่ cosmetic ไม่ถึงรันโค้ด)

**ข่าวดี:** ไม่ได้ใช้ `drawtext` filter เลย (caption ไปทาง `.ass` file กับ PIL แทน) → เลี่ยงช่องโหว่คลาสสิกไปได้

---

## P1 — Security พื้นฐาน (ต้องทำก่อนให้คนนอกแตะ)

### 5. ไม่มี authentication เลย 🔴
`scripts/api_server.py` — ไม่มี `Depends`, ไม่มี API key check, ไม่มีอะไรเลย

ทุก endpoint เปิดหมด รวมถึงตัวที่:
- ใช้เงิน (AI generate, TTS, vision matching)
- โพสต์ขึ้น TikTok จริง
- ลบไฟล์ / ลบ product
- สั่ง render

**Fix ขั้นต่ำ:** API key middleware ตัวเดียวก่อน แล้วค่อยเป็น proper user auth (JWT/session) ตอนทำ multi-tenant
**Effort:** SMALL (ขั้นต่ำ) / MEDIUM (proper)

### 6. CORS `allow_origins=["*"]` 🔴
`scripts/api_server.py:61-63`

เว็บไหนก็ได้ที่ผู้ใช้เปิดค้างไว้ ยิง API นี้ได้หมด — พอ + ไม่มี auth = ใครก็สั่งลบ/สั่งโพสต์ได้

**Fix:** จำกัดเป็น origin ของ frontend เท่านั้น, อ่านจาก env
**Effort:** SMALL

### 7. ไม่มี quota / cost enforcement 🔴
`scripts/token_tracker.py` — มีแต่ `get_history()` บันทึกอย่างเดียว **ไม่มี raise/limit/quota/budget check เลย**

**SaaS impact:** ผู้ใช้คนเดียวยิง generate รัวๆ = ค่า Gemini/TTS บานปลาย ไม่มีอะไรหยุด
**Fix:** เพิ่ม per-tenant budget check ก่อนเรียก AI ทุกครั้ง + hard stop เมื่อเกิน
**Effort:** MEDIUM

---

## P1.5 — Frontend race condition 🔴

> localhost เร็วมากเลยไม่เคยเห็น พอขึ้น SaaS (network latency จริง + server โหลด) จะโผล่บ่อย

### 7a. `fetchProductsData()` ไม่มี request-sequence guard 🔴 CRITICAL
`frontend/src/components/ContentTrackerHub.jsx:1051-1067`

```js
const fetchProductsData = useCallback(async () => {
  setLoading(true);
  try {
    const res = await getProducts();
    if (res.products) setProducts(res.products);   // ← ไม่เช็คว่า response นี้ยังใหม่อยู่ไหม
  } catch (err) { console.error(err); }
  finally { setLoading(false); }
}, []);
```

เป็นตัวโหลดข้อมูลหลักของทั้ง tracker board และถูกเรียกซ้ำจาก 3+ ที่ (`handleCoverSaved`, ปุ่ม refresh บรรทัด 2712, หลังแก้ status/product-id/product-code)

**Failure:** กด refresh แล้วรีบเซฟ cover ต่อ → request เก่า resolve ทีหลัง เขียนทับข้อมูลใหม่ → angle status / video url / cover ที่เพิ่งเซฟ **revert กลับบนจอ** จนกว่าจะ refresh อีกรอบ

**Fix:** ก็อป pattern จาก `hooks/useProjectLoader.js:7,17,22,25` — repo มี `requestSequence` ref ที่ทำถูกต้องอยู่แล้ว
**Effort:** SMALL

### 7b. Optimistic local merge ชนกับ refetch 🟠 HIGH
`ContentTrackerHub.jsx:1096-1131, 1152-1182`

`handleAngleStatusChange`, `handleSaveTiktokProductId`, `handleSaveProductCode` — ทุกตัว `await update...()` แล้ว patch `products` เอง ไม่ได้ประสานกับ `fetchProductsData()` ที่อาจวิ่งอยู่ → refresh ที่ resolve ทีหลังลบ patch ทิ้ง

**root cause เดียวกับ 7a** — แก้ 7a ครอบคลุมข้อนี้ด้วย

### 7c. เปิด link modal รัวๆ selection โดน reset 🟡
`ExportGallery.jsx:1092-1109` — เปิด modal video A แล้วปิด เปิด B ก่อน A resolve → default-selection ของ A ทับสิ่งที่ผู้ใช้เพิ่งเลือกใน B

### 7d. `todayDateStr` แช่ค้างข้ามเที่ยงคืน 🟡
`ContentTrackerHub.jsx:934-938` — `useMemo(() => ..., [])` คำนวณครั้งเดียว

เปิดแท็บค้างข้ามคืน (tool จัดคอนเทนต์ คนเปิดค้างแน่) → `isAnglePostedToday` ใช้วันที่เมื่อวานทั้งวัน filter "โพสต์วันนี้" ผิดหมดจนกว่าจะ reload

**Fix:** recompute ตอน `visibilitychange`/window focus หรือตั้ง interval

### ✅ Frontend ที่ทำถูกอยู่แล้ว
- `hooks/useProjectLoader.js` — `requestSequence` guard ถูกต้อง (ใช้เป็นต้นแบบแก้ 7a)
- `hooks/useProjectAutosave.js` — sequence queue + debounce + `beforeunload` flush ครบ
- `ExportGallery.jsx:1062-1073` — `cancelled` flag cleanup ถูก
- `SequencePlayer.jsx:2513-2582` — audio graph teardown ครบ ไม่ leak
- `App.jsx:12-18` — code splitting ด้วย `React.lazy` ครบ 7 route แล้ว
- ไม่มี N+1 fetch ใน `.map` (fetch เป็น bulk ถูกต้อง)

---

## P1.7 — Performance

### 8a. O(n²) ใน export gallery / raw vault 🟠 — **คุ้มสุด แก้ก่อน**
`scripts/api_exports.py:81-91, 117-121` — ทุกไฟล์ export วนทุก product × ทุก angle เทียบ string
`scripts/api_videos.py:201-250` — ทุก product วนทุก raw file

**Cost:** 500 export files × 500 products × 3 angles ≈ **750,000 comparison ต่อการเปิดหน้า gallery 1 ครั้ง**. ที่ SaaS scale (5,000×5,000) = 15M+ → หน่วงหลายวินาทีต่อคลิก

**Fix:** สร้าง dict `angle_video_url → (product, angle)` และ `product_id → product` ครั้งเดียวต่อ request (O(n)) แล้ว lookup O(1)
**Effort:** SMALL — **ทำก่อนเพื่อน คุ้มที่สุด**

### 8b. TTS + ffmpeg ยิงทีละบรรทัด 🟠
`scripts/voice_engine.py:232-298` — วนทีละบรรทัด: เรียก edge-tts (network) → fallback → spawn ffmpeg subprocess แยกต่อบรรทัด

**Cost:** script 8-12 บรรทัด = network call 8-12 ครั้ง + spawn ffmpeg 8-12 ครั้ง (แต่ละครั้ง startup ~100-300ms) ≈ **เสียเปล่า 3-6 วินาทีต่อวิดีโอ**

**Fix:** `asyncio.gather` / ThreadPoolExecutor สังเคราะห์พร้อมกัน แล้วค่อยต่อ audio ตามลำดับทีหลัง (ลำดับสำคัญแค่ตอน assemble ไม่ใช่ตอน synth)
**Effort:** SMALL–MEDIUM

### 8c. JSON full-rewrite ทุก operation 🔴 — **SaaS blocker ตัวจริง**
`scripts/product_store.py:40-55` + 14 call site

แก้ field เดียว = parse ทั้งไฟล์ + serialize ทั้งไฟล์ + เขียนทั้งไฟล์

**Cost:** วันนี้ 79KB ยังไหว. 1,000 products (~800KB) = ทุกครั้งที่กดเปลี่ยน status ต้อง parse+write 800KB. 10,000 products (~8MB) = 8MB ต่อคลิก

**Fix:** ต้องย้ายลง DB (ดูข้อ 9) — patch ชั่วคราวได้แค่ cache in-memory keyed by mtime
**Effort:** LARGE — เป็นโปรเจกต์แยก ไม่ใช่ quick fix

### 8d. Sync endpoint + threadpool ceiling 🟡
เกือบทุก endpoint เป็น `def` ไม่ใช่ `async def` — **ถูกต้องแล้ว** สำหรับงาน sync/subprocess (FastAPI รันใน threadpool ให้อัตโนมัติ ไม่ block event loop)

แต่ threadpool cap ~40 worker → 50 tenant ยิงพร้อมกัน = คิวยาว
**Fix:** ขยาย threadpool เป็น stopgap, ตัวจริงคือ task queue (ข้อ 11)

### 8e. ไม่มี list virtualization 🟡
ไม่มี `react-window`/`react-virtual` ในโปรเจกต์เลย. `ContentTrackerHub.jsx:2855, 2896-2919` render kanban ทั้งบอร์ด

**Cost:** 50 products × 5 angles = 250 card ≈ 3,750-7,500 DOM node. Power user 500 products = 30,000+ node → scroll กระตุก
**Fix:** virtualize kanban column — ทำตอนใกล้ launch SaaS พอ

### ✅ Performance ที่ทำถูกอยู่แล้ว
- `gemini_vision_matcher.py:40-361` — cache keyed by file hash + cue hash เช็คก่อนเรียก API **ถูกต้อง**
- render หลักเป็น ffmpeg pass เดียว ไม่ re-encode ซ้ำ
- `allAnglesList`, `phaseCounts`, `filteredAngles` (บรรทัด 1332-1369) memoize ถูกแล้ว
- code splitting ครบ

---

## P1.6 — Pipeline: บัคที่ทำวิดีโอเสียเงียบๆ 🔴

> ธีมเดียวกับ extension — **ล้มแล้วไม่บอก** ได้ไฟล์ที่ดูปกติแต่ผิด

### 11a. TTS ล้ม 1 บรรทัด → subtitle เพี้ยนทั้งคลิป 🔴 CRITICAL
`scripts/voice_engine.py:236-346`

```python
if not line_text:
    continue                      # ← ไม่มี else, ไม่ log
...
if proc_wav.exists():
    cues.append(...); current_time += seg_duration
                                  # ← ไฟล์ไม่มี = ข้ามเงียบ, current_time ไม่ขยับ
```

edge-tts error โดนกลืน (`stdout=DEVNULL, stderr=DEVNULL` ไม่เช็ค returncode), gTTS fallback ห่อ `except Exception: pass`

**Failure:** บรรทัดไหน sanitize แล้วเหลือว่าง (emoji ล้วน) หรือ TTS ล้มทั้ง 3 ทาง → บรรทัดนั้นหายทั้ง audio+caption **และทุกบรรทัดถัดไป timestamp เลื่อนถาวร** subtitle ไม่ตรงเสียงทั้งคลิป ไม่มี error ไม่มี log ไม่มีทางรู้

**Fix:** TTS ล้ม → ใส่ silence ความยาวเท่ากัน (timeline ไม่เพี้ยน) หรือ raise ให้ job log เห็น
**Effort:** SMALL

### 11b. Render timeout → ffmpeg ผีค้าง 🔴 CRITICAL
`scripts/video_editor.py:953-1017`

`proc.wait(timeout=300)` (บรรทัด 1003) raise `TimeoutExpired` **ไม่มีใคร catch** → process ffmpeg ไม่เคยถูก kill

path นี้ใช้ทุกครั้งที่ render จาก UI (เพราะ `VideoAssemblyStage` ส่ง `on_ffmpeg_progress` เสมอ)

**Failure:** render หนักเกิน 300 วิ → job ขึ้น failed แต่ **ffmpeg ยัง encode อยู่เบื้องหลัง** กิน CPU ต่อ ทั้งที่ `_RENDER_SLOT` ปล่อยไปแล้ว + ไฟล์ partial ค้างเต็มดิสก์

**Fix:** ห่อ try/finally kill process + unlink ไฟล์ partial
**Effort:** SMALL

### 11c. MP4 กำพร้าเมื่อ pipeline ล้มหลัง render 🟠 HIGH
`scripts/stages/video_assembly_stage.py:79-187` — render เสร็จบรรทัด 98 แต่ `ProjectManifest.save()` อยู่บรรทัด 186. ล้มระหว่างนั้น = ไฟล์ mp4 อยู่บนดิสก์แต่ไม่มี manifest ชี้ถึง

แต่ละครั้งได้ timestamp ใหม่ → retry หลายรอบ = ไฟล์ขยะสะสมเรื่อยๆ

### 11d. Thai ยาวเกินล้นเฟรม 🟠 HIGH
`scripts/subtitle_engine.py:130, 180-181` + `scripts/subtitle/word_layout.py:96-193`

`split_into_smart_clauses` เรียก `pythainlp.word_tokenize` **เฉพาะตอน `len(raw_parts) <= 1`** — ถ้าประโยคมีช่องว่างพอดี 1 ที่ (`"สายชาร์จแม่เหล็กแรงดูดสูงงานดีมาก จริงๆ"`) จะไม่ตัดคำเลย ท่อนยาว >34 ตัวผ่านไปดิบๆ

`layout_line()` ไม่มี pixel-width wrap เลย — ไม่มีตาข่ายรับ

**Failure:** caption ไทยยาวๆ ที่มีช่องว่าง 1 ที่ **ล้นออกนอกเฟรม 1080px ทั้งซ้ายขวา**
**Fix:** เปลี่ยน guard ให้ trigger เมื่อชิ้นไหนชิ้นหนึ่งยาวเกิน `max_line_len` ด้วย ไม่ใช่แค่ตอนไม่มีช่องว่างเลย

### 11e. เสียงคนจริง → caption ไม่ตรง 🟡 MEDIUM
`scripts/stages/voice_stage.py:54-65` — ใช้ `dur_per_line = total_duration / num_lines` หารเท่าๆ กัน ไม่ align กับเสียงจริง

ทั้งที่ path ของ Gemini TTS มี energy-based alignment อยู่แล้ว (บรรทัด 125-220 ไฟล์เดียวกัน) แค่ไม่ได้เอามาใช้กับเสียงคน
**Fix:** ใช้ RMS alignment ตัวเดิมกับ human voice path ด้วย

### 11f. ffprobe ล้ม → แอบใส่ 15 วินาที 🟡
`scripts/stages/voice_stage.py:52, 112`

```python
total_duration = float(probe_res.stdout.strip()) if probe_res.stdout.strip() else 15.0
```

ffprobe ล้ม/ไฟล์เสีย → กลายเป็น 15.0 เงียบๆ แล้วไหลไปเป็น `-t {total_duration}` ตอน ffmpeg → **ตัดเสียงจริงทิ้งที่ 15 วิ** หรือมีหางเปล่า ไม่มี log
**Fix:** stdout ว่าง = raise error ไม่ใช่ใส่เลขมั่ว

### 11g. Font หาย → เดาความกว้าง 🟢 LOW
`scripts/subtitle/font_metrics.py:130-137` — fallback `len(line) * font_size * 0.55` ใช้ไม่ได้กับไทย (สระ/วรรณยุกต์ advance width = 0)
**Fix:** log warning ตอนเข้า fallback จะได้จับได้ตอน test

### ยังไม่ได้ตรวจใน pipeline
`gemini_tts_engine.py`, `ai_bridge.py` (retry/failure handling), `translator.py`, `tts_sanitizer.py`, `motion_analyzer.py`, `image_motion_engine.py`, `overlay_model.py`, `sfx_manager.py` (audio-mix division math), `task_manager.py`, และ filter-graph construction ส่วนใหญ่ของ `video_editor.py` (บรรทัด 1-900)

---

## P1.8 — Chrome extension: silent-success bug 🔴

> ธีมเดียวกับบัคที่แก้ไปแล้วที่ `background.js:683` (เลือกสินค้าผิดแล้วบอกสำเร็จ) — **ยังมีอีกหลายจุด**
> plumbing แจ้ง error ทำถูกแล้ว (`sidepanel.js:230-243` โชว์ error ถูกต้อง) ปัญหาคือ step function พวกนี้**ไม่เคย throw** เลย return success เฉยๆ

### 12a. กดโพสต์แล้วไม่เคยเช็คว่าโพสต์สำเร็จ 🔴 CRITICAL
`background.js:1029-1069, 1176`

```js
await clickPostButton(send);
return { success: true, clicked:true, posted:false };   // ← ยอมรับเองว่าไม่รู้ว่าโพสต์ไหม
```

ไม่เช็คอะไรเลยหลังคลิก: ไม่ดู error toast ของ TikTok, ไม่ดู URL เปลี่ยน, ไม่ดูปุ่ม disable/spinner

ซ้ำร้าย `background.js:1025-1028` เขียนคอมเมนต์ไว้เองว่า selector ปุ่มโพสต์ (`.btn-post:not(.disabled)`) เป็น **"UNVERIFIED best-guess placeholder"** — selector ของ action สำคัญสุดยังไม่เคย verify กับ TikTok จริง

**Failure:** TikTok reject (caption สั้นไป / ไม่มี cover / ไม่ได้เลือกหมวด) โชว์ error banner แต่ extension ขึ้น "ขั้น 5 สำเร็จ 🎉" → ผู้ใช้เชื่อว่าโพสต์แล้ว ทั้งที่ไม่มีอะไรขึ้นเลย

**ผ่อนหนัก:** รันเฉพาะตอน opt-in auto-click, default คือหยุดให้กดเอง — แต่ถ้าเปิดใช้แล้วอันตรายเต็มๆ
**Fix:** poll หา URL เปลี่ยน / form หาย / error toast ภายใน timeout แล้วค่อย return success ไม่งั้น `{success:false, reason:'post_not_confirmed'}`

### 12b. แนบลิงก์สินค้าไม่เช็คว่าแนบติดจริง 🟠 HIGH
`background.js:867-927` — `confirmed = true` เพราะเจอปุ่มแล้วคลิก จบ ไม่เช็คว่า modal ปิด / chip สินค้าโผล่ในฟอร์ม

**Failure:** โพสต์ออกไปโดย**ไม่มีลิงก์สินค้า** ทั้งที่บอกสำเร็จ — กระทบรายได้ตรงๆ เพราะทั้งระบบคือ affiliate

### 12c. สลับโหมดตั้งเวลาไม่เช็คว่าสลับจริง 🟠 HIGH
`background.js:934-983` — คลิกแล้ว `return {success:true}` ทันที ไม่เช็คว่า date picker โผล่ / radio checked จริง

**Failure:** ผู้ใช้คิดว่าตั้งเวลาไว้แล้ว แต่**โพสต์ออกทันที**

### 12d. `dismissLeaveConfirmDialogIfPresent` เขียนไว้แต่ไม่มีใครเรียก 🟡
`background.js:995-1023` — grep ทั้ง repo แล้ว **ไม่มี call site เลย**

ฟังก์ชันนี้เขียนมาจัดการ dialog "ออกจากหน้านี้ไหม" ที่เด้งหลังกดโพสต์ (ตามคอมเมนต์ของโค้ดเอง) แต่ไม่เคยถูกต่อเข้า flow → dialog เด้งจริงเมื่อไหร่ flow ค้างเงียบ

**Fix:** เรียกจาก `clickPostButton` หลังคลิก (โค้ดพร้อมแล้ว แค่ยังไม่ได้ wire)

### 12e. ตรวจ caption แค่ 10 ตัวแรก 🟡
`background.js:238-246` — `cleanCaption.slice(0, 10)` เทียบ prefix เท่านั้น

**Failure:** caption ขาด/เพี้ยนท้ายข้อความ ผ่าน verify ได้ถ้า 10 ตัวแรกตรง (Draft.js drop text ได้ถ้า editor เสีย focus กลางคัน)
**Fix:** เทียบ full string

### 12f. Selector กระจัดกระจาย + เปราะ 🟡
- ไม่มี selector map กลาง — `background.js` hand-roll แยกทุกฟังก์ชัน, `isVisible` เขียนซ้ำ ~6 รอบ (แก้ที่เดียวไม่ propagate)
- `[id="2"]` (`background.js:353, 383`) — positional id ของ Showcase tab
- `[class*="itemTitle--active"]`, `[class*="--checked"]` — substring ของ class ที่ TikTok generate
- `TARGETS = ['ตั้งเวลา', 'กำหนดเวลาโพสต์', ..., 'Schedule']` (`:947`) — match ด้วยข้อความ UI, เปลี่ยนภาษาแตกทันที (เคยโดนมาแล้วกับ "Uploading..." vs "กำลังอัปโหลด" ที่ `:263-271`)
- product row match ด้วย `text.includes(query.slice(-6))` (`:674-681`) — 6 ตัวท้ายชนกันได้

**คุ้มที่จะรวมเป็น `selectors.js` ไฟล์เดียว** — ดู git history ที่ commit "fix selectors" ซ้ำๆ นับครั้งไม่ถ้วน จะคุ้มตั้งแต่ TikTok เปลี่ยน UI ครั้งหน้า

### 12g. `sleep()` แข็งแทนการรอ element 🟡
`background.js:519 (1500ms), 544 (1800ms), 553, 651 (2500ms), 811, 864, 929` + `automation.js:96, 140, 166`

เครื่องช้า/เน็ตช้า = รอไม่พอ (race), เครื่องเร็ว = รอเกินเปล่าๆ. retry loop มี cap ดีแล้ว แต่ไม่มี backoff

### 12h. Service worker ตายกลางคัน sidepanel ค้าง 🟡
`background.js:1237-1238` — `actionRunning` เป็น global ของ service worker ไม่ persist

MV3 Chrome kill service worker ตอน idle ~30s ได้ ถ้าตายระหว่าง `sleep` ยาวๆ ใน `attachProductLink` → promise chain หาย, `sendResponse` ไม่เคยถูกเรียก → **ปุ่มใน sidepanel ค้าง disable ถาวร ไม่มี error โชว์**

### 12i. Dead code 🟢
- `DIAGNOSTIC_PASSIVE_WAIT` (`:47`) — declare แล้วไม่ใช้ที่ไหนเลย (คอมเมนต์บอกว่าเป็น A/B test หา tab crash — สรุปแล้วหรือยังไม่รู้)
- `popup.js` (126 บรรทัด) — manifest ไม่ได้ reference แล้ว (ย้ายไป sidepanel) แต่ไฟล์ยังอยู่

### ✅ Extension ที่ทำถูกแล้ว
- `host_permissions` แคบ (localhost:8000 + tiktok.com) ไม่มี `<all_urls>`
- error plumbing ถูกต้อง — throw แล้วเด้งถึง UI จริง
- retry loop มี cap ทุกตัว ไม่มี infinite loop
- `actionRunning` กันยิงซ้อนได้ (พอสำหรับ single user)
- `automation.js` มี `page()`/`buttonQuery()` helper — pattern ดี ควรขยายไปใช้ทั่ว

---

## P2 — Multi-tenancy gap (งานใหญ่ ทำเป็นเฟส)

### 13. Cross-tenant data leak — เสี่ยงสุดในหมวดนี้ 🔴

> พวกนี้ leak **เงียบ** (ไม่ crash ไม่ error) เลยอันตรายกว่าข้ออื่น — verify จากโค้ดแล้วทุกข้อ

| ที่ | ปัญหา | ผลถ้าไม่แก้ |
|---|---|---|
| `task_manager.py:41` `_tasks` | class-level dict **ไม่มี tenant key เลย** — `get_active_tasks()` คืนทุกอย่างในโปรเซส | tenant A เห็น render job title/payload ของ tenant B ทันทีที่แชร์โปรเซส |
| `render_jobs.py:20` `ACTIVE_JOBS` | dict เปล่าๆ key ด้วย `job_id` อย่างเดียว | เดา job_id ได้ = อ่าน progress/result ของคนอื่น |
| `token_tracker.py:42-44` `_cache`/`_cache_mtime` | class attribute เก็บ JSON ทั้งก้อนในหน่วยความจำ ใช้ร่วมกันทุก request | อ่าน usage ของ tenant อื่นถ้าสลับไฟล์ต่อ tenant โดยไม่ล้าง cache |
| `product_store.py:34` `_lock` | Lock เดียวทุก tenant | ไม่ leak แต่ tenant A เขียน = tenant B รอ (ไม่แฟร์) |
| `render_jobs.py:27` `_RENDER_SLOT` | **1 slot ทั้งโปรเซส** (จงใจ เพราะเครื่องนี้ CPU-only 13.7GB) | tenant B รอคิว tenant A ไม่มี priority/fairness เลย |
| `ai_bridge.py` `get_api_keys()` | key list เป็น global | ทำ bring-your-own-key ไม่ได้ |

**หมายเหตุ:** `asset_registry.py` **ไม่ต้องใส่ tenant_id** — SFX/BGM/font เป็น asset กลางใช้ร่วมกัน (อย่าเสียเวลาแก้)

### 14. ID generation ชนกันได้ตั้งแต่วันนี้ 🟠
`product_store.py:106` + `post_log.py:69`

```python
"id": f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(products) + 1}"
```

เพิ่ม 2 รายการในวินาทีเดียวกันตอน list ยาวเท่ากัน = **id ซ้ำ**. ต้องแก้ก่อนย้าย DB เพราะ primary key ต้องการ uniqueness จริง ไม่ใช่ "คงไม่ชนหรอกเพราะใช้คนเดียว"

**Fix:** `uuid.uuid4().hex` (MVP) หรือ ULID (ถ้าอยากให้ sort ตามเวลาได้ — โค้ดหลายที่ sort ด้วย `updated_at` อยู่แล้ว)
**Effort:** SMALL

### 15. Schema mapping (จาก record จริง)

**`products`** — `id` (เปลี่ยนเป็น UUID), `tenant_id` FK NOT NULL indexed, `name`, `url`, `platform` (free-form อยู่ ควรทำ enum), `status` (มี `STATUSES` enum ในโค้ดแล้ว), `product_code` → ต้อง `UNIQUE (tenant_id, product_code)` **และ `_generate_product_code()` ต้อง scan เฉพาะ tenant ตัวเอง** (ตอนนี้ scan ทั้งไฟล์), `specs`/`pain_points`/`selling_points` เก็บเป็น jsonb พอ. unique `(tenant_id, url)` แทน logic de-dupe ปัจจุบัน (ซึ่งเป็น scan-then-insert = race อีกตัว)

**`angles`** — ตอนนี้ซ้อนใน `products[].angles[]` **ต้องแยกเป็นตารางเอง**. `angle_id` เป็น taxonomy คงที่ ~7-8 ตัว (`pain_point`, `unboxing`, `fomo_deal`, …) แต่เก็บเป็น free text. ใส่ `tenant_id` ซ้ำในตารางลูกด้วย (status board poll บ่อย ไม่อยาก join). **ตัดทิ้งได้:** `script_text` (= `"\n".join(script_lines)`) และ `selected_video` (= `selected_videos[0]`) — คำนวณตอนอ่านแทน

**`videos`** — ซ้อนอยู่เหมือนกัน ต้องแยก. หมายเหตุ: `rel_path` **ไม่ได้ relative จริง** — ในข้อมูลจริงเป็น absolute path เหมือน `path` เป๊ะ (ชื่อฟิลด์หลอก). `selected_videos` ควรเป็น join table `angle_video_links(angle_id, video_id, position)` ไม่ใช่ array ของ path

**`posts`** — **ไม่มี `product_id` เลย** ทุกวันนี้ join กลับหา product ได้แค่ด้วยชื่อ (fuzzy) → ต้องเพิ่ม FK แล้ว backfill โดย match `clip_file` กับ `angle.video_url` (ใช้ logic เดียวกับ `rollback_by_video_or_project()` ที่มีอยู่แล้ว). `metrics` ควร flatten เป็น column จริง (`views`, `likes`, `orders`, …) เพราะ `angle_performance()` ทำ SUM/AVG — SQL ทำได้ native

**`projects`** — `project_name` เป็น PK วันนี้ (ชื่อโฟลเดอร์) → ต้องเป็น `(tenant_id, project_name)` หรือ UUID. `render_params.product_id/angle_id` ที่ฝังใน JSON ควรเลื่อนขึ้นมาเป็น column จริง (โค้ดใช้เป็น join key อยู่แล้ว)

**`usage_events`** — map ตรงๆ ได้เลย. **`totals` อย่า migrate** — เป็น aggregate ที่ manual sync ทุก write (drift แน่) ใช้ `SUM() GROUP BY` ตอนอ่านแทน

### 16. ขนาดงาน threading tenant_id
- `ProductStore` **ทั้ง 20 method** (ทุกตัวเรียก `_load()` ที่อ่านไฟล์ global)
- `PostLog` 7 method, `TaskManager` 9 method, `ProjectManifest` — แก้ `dir_for`/`path_for` 2 ตัวพอ ที่เหลือไหลตาม
- **API endpoint 108 ตัว** ต้องใส่ `Depends(get_current_tenant)` — งาน mechanical แต่เยอะ

รวม ~45 call site + 108 endpoint. ส่วนที่ต้องคิดจริงๆ คือ global state 6 ตัวในข้อ 13 ไม่ใช่การส่ง parameter

### 17. Media / object storage
ทุกจุดที่ `open()` local path: `media_service.py` (`stream_media_file` line 150/165/186/195, `get_file_info`, `scan_video_files`), ffmpeg ทุก call, `ProjectManifest.save()`

**ข้อจำกัดจริง:** ffmpeg **อ่าน S3/GCS URL ตรงๆ ไม่ได้** ต้องมีไฟล์บนดิสก์ (หรือ HTTP URL ที่ seek ได้ ซึ่งไม่น่าเชื่อถือสำหรับงาน edit)

**Layer ที่ต้องมี:** `MediaStore` abstraction 2 backend — local (วันนี้ passthrough) กับ object-store (download → `<tmp>/<tenant>/<job>/` ก่อน render, upload กลับหลังเสร็จ, ลบ scratch). ffmpeg/PIL ตรงกลาง**ไม่ต้องแก้เลย** แค่ห่อขอบเข้า-ออก

**สำคัญ:** `tmp.write_text()` + `tmp.replace()` ที่ใช้อยู่เป็น **atomic ของ local filesystem เท่านั้น** — object store ไม่มี rename atomic ต้องออกแบบใหม่

**คำแนะนำ:** local disk พอสำหรับ MVP SaaS. ย้ายขึ้น object storage เมื่อ (ก) worker หลายเครื่อง (ข) storage เกินดิสก์เดียว (ค) ต้องการ CDN. **ต้องแก้ absolute path (ข้อ 4) ก่อน** — object store ไม่มีคอนเซปต์ "CWD ของแอป" ให้ resolve relative path

### 18. Rendering — วันนี้มี 2 ระบบซ้อนกัน
1. `render_jobs.py` — `ACTIVE_JOBS` in-memory + `_RENDER_SLOT` lock เดียว, **หายหมดตอน restart** (คอมเมนต์ยอมรับเอง)
2. `task_manager.py` — persist ลง `task_registry.json`, มี `TaskStatus` enum + `ThreadPoolExecutor(max_workers=4)`, **restart แล้ว mark ทุกงานค้างเป็น failed** ไม่ resume

ทั้งคู่ in-process, UI poll REST endpoint อ่าน Python dict ตรงๆ (ไม่มี websocket/SSE)

**ควรเช็คเพิ่ม:** สองระบบนี้ใช้กับ job คนละชนิดจริงหรือทับซ้อนกันโดยไม่ตั้งใจ

**Target:** **arq** เหมาะกว่า Celery สำหรับทีมเล็ก (asyncio-native, ops น้อย, mental model ใกล้ `run_in_background()` เดิม). ย้ายไป Celery ต่อเมื่อ arq ไม่พอ

`_RENDER_SLOT` → กลายเป็น **worker pool sizing** + per-tenant concurrency rule ตอน dequeue (เช่น free = 1 render, paid = 3)

**ข่าวดี:** UI ไม่ต้องแก้ — poll endpoint เดิมได้ แค่เปลี่ยนจากอ่าน dict เป็นอ่าน Redis/DB. อย่าเอา SSE/WebSocket มาผูกกับงานนี้ (แยกเรื่องกัน)

**Retry:** วันนี้**ไม่มี auto-retry เลย**. ควรแยก — TTS network ล้ม = retry ได้, ffmpeg OOM = อย่า retry (ล้มซ้ำเปล่าๆ) ส่ง error ให้ tenant เห็น. `error_handler.py` (`classify_exception`/`AppError`) ที่มีอยู่ย้ายไปใช้ใน worker ได้เลย

### 19. Quota enforcement — จุดที่ต้อง hook
มี `record_event()` แค่ 3 ที่ **และทั้งหมดเรียกหลังจ่ายเงินไปแล้ว**:
- `ai_bridge.py:385` (Antigravity CLI) + `:419` (Google AI Studio) — ห่อ `try/except: pass` กลืน error
- `gemini_tts_engine.py:257`
- `gemini_vision_matcher.py:344`

**ต้องเพิ่ม pre-flight check ก่อนยิง network** ที่ 3 จุดนี้ + ตาราง `tenant_budgets` (`tokens_used`, `tokens_limit`, `cost_thb_used`, `cost_thb_limit`) — debit ต้องอยู่ transaction เดียวกับ insert usage log ไม่งั้น drift

**หมายเหตุ:** quota check ต้องอยู่**นอก** cache check ของ `gemini_vision_matcher` — cache hit ไม่เสียเงิน ไม่ควรโดนกิน quota

**ปัญหาที่ต้องออกแบบ:** ยังไม่รู้ token จริงจนกว่าจะเรียกเสร็จ → ต้อง reserve ประมาณการก่อน แล้ว reconcile ทีหลัง (กัน race ที่ 2 request ผ่าน check พร้อมกันก่อนใครจะ debit)
**Effort:** MEDIUM

### 20. ลำดับ migration (แต่ละ step ship แยกได้ ไม่พังของเดิม)

| Step | งาน | Effort |
|---|---|---|
| 1 | แก้ id generation เป็น UUID/ULID (ข้อ 14) | SMALL |
| 2 | **SQLite หลัง store class เดิม** — signature เหมือนเดิมเป๊ะ ยังไม่มี tenant_id | MEDIUM |
| 3 | เพิ่ม column `tenant_id` + backfill เป็น tenant เดียว (ยังไม่ต่อ auth) | SMALL–MEDIUM |
| 4 | Auth จริง + `get_current_tenant()` + CORS ล็อก | MEDIUM |
| 5 | ร้อย `tenant_id` ผ่าน store จริง + แก้ global state 6 ตัว (ข้อ 13) | LARGE 1-2 สัปดาห์ |
| 6 | Relative path (ข้อ 4) + `MediaStore` wrapper | MEDIUM→LARGE |
| 7 | Job queue (arq) | LARGE / RETHINK |
| 8 | Quota enforcement (ข้อ 19) | MEDIUM |

Step 5 คือจุดที่**พลาด call site เดียว = data leak จริง** ต้อง test หนักสุด (ทดสอบด้วย tenant จริง 2 ตัว ยิงทุก endpoint ว่า A เห็น B ไม่ได้)

Step 6 ส่วน relative path จริงๆ **ควรทำก่อน step 3 ด้วยซ้ำ** — มีประโยชน์ไม่ว่าจะทำ SaaS หรือไม่

Step 8 ทำขนานกับ 6/7 ได้ ขึ้นกับ step 5 อย่างเดียว — และควรเสร็จ**ก่อน** step 7 เพราะ "กันเผาเงิน" ทำง่ายกว่า "สร้าง queue infra"

### 🎯 step ที่คุ้มที่สุด: **Step 2 (SQLite หลัง store class เดิม)**

ทำก่อนแตะ tenancy/auth/media เลย เพราะ:
1. **ปลอดภัย** — signature เดิมทั้งหมด แอป single-user วันนี้ไม่รู้สึกอะไร
2. **แก้บัคที่มีอยู่จริงไปในตัว 2 ตัว** — lost update race (ข้อ 1) กับ JSON full-rewrite (ข้อ 8c) เพราะ transaction จริงแทน lock ที่ไม่ครอบ `_load()` — นี่คือเงินที่เสียอยู่**วันนี้** ไม่ใช่ความเสี่ยงอนาคต
3. **ทุก step ที่เหลือต้องรอมัน** — เพิ่ม `tenant_id` column, unique per tenant, quota debit แบบ transaction ทำบน JSON + lock ครึ่งใบไม่ได้
4. **ไม่ผูกมัดการตัดสินใจอื่น** — SQLite vs Postgres, arq vs Celery, S3 vs local ยังเปิดหมดหลังทำ step นี้

---

## ลำดับการทำ (แนะนำ)

**เฟส 0 — อุดช่องโหว่ที่ exploit ได้วันนี้ (ครึ่งวัน) ⚠️ ทำก่อนเลย**
1. Sanitize `product_id` (ข้อ 4a) — แก้ 3 บรรทัด กัน arbitrary file write
2. SSRF guard ใน scraper (ข้อ 4b)
3. `startswith` → `relative_to` ทุกจุด (ข้อ 4c)

> ทำ 3 ข้อนี้ก่อนแม้จะยังไม่ทำ SaaS — เพราะ CORS `*` + ไม่มี auth = เว็บไหนที่เปิดค้างไว้ก็ยิงได้ ขณะ app รันอยู่

**เฟส 1 — บัคที่มีผลวันนี้ (2–3 วัน)**
4. Frontend fetch race (ข้อ 7a) — ก็อป pattern จาก `useProjectLoader.js`
5. Lost update race backend (ข้อ 1)
6. O(n²) export/raw vault (ข้อ 8a) — คุ้มสุดในหมวด performance
7. Test isolation (ข้อ 2) + `post_log.json` ออกจาก git (ข้อ 3)

**เฟส 2 — security ขั้นต่ำ (1–2 วัน)**
8. API key + CORS จำกัด (ข้อ 5, 6) + shared secret ให้ extension (ข้อ 4e)
9. Quota enforcement (ข้อ 7)

**เฟส 3 — ปลด blocker ของ SaaS (1 สัปดาห์)**
10. เลิกฝัง absolute path (ข้อ 4) ← ปลดล็อกข้อ 9
11. TTS/ffmpeg parallel (ข้อ 8b) — ลด render latency 3-6 วิ/คลิป

**เฟส 4 — multi-tenant จริง (3–6 สัปดาห์)**
12. DB migration (ข้อ 8, 8c)
13. Object storage (ข้อ 9) + per-tenant path scoping (ข้อ 4d)
14. Render worker (ข้อ 10) + virtualization (ข้อ 8e)

---

## ยังไม่ได้ตรวจ

audit ครอบคลุมแล้ว: backend API ผิวๆ, data layer, security (path traversal/SSRF/injection), frontend React, performance

ยังไม่มีข้อมูล:

- **Pipeline correctness** — AI/TTS failure recovery (render ค้างครึ่งทางไหม), subtitle timing drift, beat sync, Thai unicode edge case (repo มี test artifact เรื่อง Thai font เกลื่อน = เคยเจ็บมาก่อน)
- **Chrome extension เชิงลึก** — selector เปราะแค่ไหน, silent-success bug ตัวอื่น (แก้ไปแล้ว 1 ตัวที่ `background.js:683`), จะเกิดอะไรถ้าปิดแท็บกลางคัน
- **Test coverage gap** — module ไหนไม่มี test เลย, test ตัวไหนอีกที่เขียนทับ data จริงแบบ `test_analysis_fixes.py`
- **Frontend ที่เหลือ** — `Timeline.jsx`, `context/`, `api.js`
- **Data layer → DB migration plan เชิงลึก** — mapping ตาราง, จุดที่ต้องร้อย `tenant_id`
