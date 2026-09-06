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

## P2 — Multi-tenancy gap (งานใหญ่ ทำเป็นเฟส)

### 8. Data layer ต้องย้ายลง DB
JSON store ใช้กับหลายคนไม่ได้ — ทุก request อ่าน/เขียนไฟล์ทั้งก้อน (products.json 79K, post_log.json 132K วันนี้ และโตขึ้นเรื่อยๆ)

| ตอนนี้ | ควรเป็น |
|---|---|
| `_Docs/products.json` | ตาราง `products` (+ `tenant_id`) |
| `_Docs/post_log.json` | ตาราง `posts` |
| project manifest | ตาราง `projects` |
| token log | ตาราง `usage_events` |

ต้องร้อย `tenant_id` ผ่านทุก store method + ทุก API endpoint
**Effort:** LARGE (2–3 สัปดาห์)
**MVP version:** SQLite + SQLAlchemy ก่อน, ยังไม่ต้อง Postgres

### 9. Media ต้องย้ายขึ้น object storage
ตอนนี้ทุกอย่าง `open()` local path ตรงๆ รวมถึง ffmpeg ที่ต้องมีไฟล์จริงบนดิสก์

**Effort:** LARGE — ต้องมี layer ดาวน์โหลดมา temp ก่อน render แล้วอัปกลับ
**ขึ้นกับข้อ 4** (ต้องเลิกฝัง absolute path ก่อน)

### 10. Render ต้องแยกเป็น worker
ตอนนี้ render รันในโปรเซส API — CPU/GPU หนัก, คนเดียวยิง render ก็ทำให้ทั้งระบบอืด

**Fix:** job queue (Celery/RQ/arq) + worker แยก + per-tenant concurrency limit
**Effort:** LARGE
**RETHINK:** ถ้าจะให้คุ้ม ควรคิดเรื่อง worker autoscaling + isolation ตั้งแต่ออกแบบ

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
