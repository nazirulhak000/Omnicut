# 📱 รายงาน: Mobile Studio Flow v2 — P0 (กันตัน + ยกเลิกงาน)

> **วันที่:** 2026-10-04
> **ดำเนินการโดย:** Cline (Claude Sonnet 4.5)
> **แผนอ้างอิง:** [PLAN_MOBILE_STUDIO_FLOW_V2_20261004.md](../Plans/PLAN_MOBILE_STUDIO_FLOW_V2_20261004.md)
> **สถานะ:** P0 + P1 + P2 ครบทุกข้อ (P2-1/2/3/4) เสร็จ · เหลือทดสอบบนเครื่องจริง + ยังไม่ commit

## งานที่ทำ (P0)

| WP | สิ่งที่แก้ | ไฟล์ |
|---|---|---|
| P0-1 | Preflight ก่อนเรนเดอร์: `hasFootage = uploadedVideoPath \|\| selectedAngle.attached_raw \|\| sessionFootageReady` · ปุ่ม `disabled={!hasFootage}` + ข้อความบอกเหตุ + ปุ่ม "ตรวจสอบคลิปอีกครั้ง" · `refreshSessionFootage()` hydrate สถานะ session จากหน้ากล้อง (`getRecordingSession`) · guard ใน `handleStartAssemble` | `frontend/src/components/MobileQuickStudio.jsx` |
| P0-2 | endpoint `POST /api/mobile-studio/cancel/{task_id}` (TaskManager.cancel_task + render_jobs.request_cancel) · `cancelMobileTask()` · ปุ่ม "ยกเลิกการเรนเดอร์" + `ConfirmModal` (variant warning) | `scripts/api_mobile_studio.py`, `frontend/src/api.js`, `MobileQuickStudio.jsx` |
| P0-3 | ปุ่ม "ลองโหลดใหม่" ใน empty/error state Step 1 | `MobileQuickStudio.jsx` |
| P0-4 | แยก state `confirming` แทน global `loading` → กดยืนยันแล้วลิสต์ไม่ยุบ + สปินเนอร์ที่ปุ่ม | `MobileQuickStudio.jsx` |

## หลักฐานการตรวจสอบ

- `.venv` Python 3.13: `py_compile scripts/api_mobile_studio.py scripts/mobile_quick_studio.py` → **OK**
- route ใหม่ลงทะเบียนจริง: `/api/mobile-studio/cancel/{task_id}` (ตรวจจาก `router.routes`)
- `pytest tests/test_mobile_quick_studio.py -q -k "cancel or cancelled"` → **2 passed** (collect 26 tests)
- `pytest ... --collect-only` → **26 tests collected** ไม่มี import error
- `esbuild` transform `MobileQuickStudio.jsx` + `api.js` → **OK** (syntax ถูก)
- `oxlint MobileQuickStudio.jsx` → **0 errors**, 8 warnings (เป็น warning เชิง React-hooks ของโค้ดเดิม ไม่ใช่ error)

## P1 — สบายมือครบวง (ทำต่อในรอบเดียวกัน)

| WP | สิ่งที่แก้ | ไฟล์ |
|---|---|---|
| P1-1 | `resolveInitialMobileMode()` (URL > localStorage `omnicut.uiMode` > viewport) · `applyUiMode()` persist + ตั้ง `?mode=` · `useEffect` ฟัง resize/orientationchange (auto เฉพาะเมื่อยังไม่เลือกเอง) | `frontend/src/App.jsx` |
| P1-2 | เฮดเดอร์ `pt-[calc(env(safe-area-inset-top)+0.75rem)]` · แถบปุ่มล่าง Step 1/2 `bottom-[calc(env(safe-area-inset-bottom)+1rem)]` | `MobileQuickStudio.jsx` |
| P1-3 | ปุ่ม "มาร์คว่าโพสต์แล้ว" + `handleMarkPosted` (`markPosted(video_path, product, angle)`) + reset `postedDone` เมื่อเริ่มงานใหม่ | `MobileQuickStudio.jsx` |
| P1-4 | ลบอีโมจิซ้อนไอคอน 4 จุด (`+ เพิ่มสินค้า`, `⚡ ถ่ายด่วน…`, `➕ เขียนมุม…`, `⚡ …ไปหน้าถ่ายทำ`) | `MobileQuickStudio.jsx` |

## หลักฐานการตรวจสอบ (P1)

- `npm run build` → **ผ่าน** (`✓ built in 692ms`, 2071 modules, chunk `MobileQuickStudio-CmP7KMgn.js`)
- `esbuild` transform `App.jsx` + `MobileQuickStudio.jsx` → **OK**
- `oxlint App.jsx MobileQuickStudio.jsx` → **0 errors**
- `node --test src/lib/mobileStudioFlow.test.js` → **6 passed / 0 failed**
- cleanup `.tmp` 100%

## หมายเหตุ (งานอื่น — ไม่ได้แก้)

`frontend/src/lib/editorShortcutKeys.js` (งาน KEYFRAME ของอีก agent) เคย syntax พังกลางทางแล้วถูกเจ้าของซ่อม → build กลับมาเขียว แต่เทสต์ `src/lib/editorShortcutKeys.test.js:212` ("SHORTCUT_GROUPS: every probed row…") ยัง **ตก 1 ตัว** ซึ่งเป็นของงานนั้น ไม่ใช่ Mobile Studio

## ค้าง

- ทดสอบบนเครื่องจริง: Android Chrome (Wake-Lock จอไม่ดับ + ติดตั้ง PWA) / iOS Safari ไม่พัง — ผู้ใช้ทำเอง
- commit (ยังไม่สั่ง)
- ~~P2-4 แบ่งหน้าแคตตาล็อก~~ — เสร็จแล้ว ดูหัวข้อ "P2-4" ด้านล่าง

---

## P2 — Polish (ทำต่อ 2026-10-04 · Cline (Claude Sonnet 4.5))

**Jev (ครบรอบก่อนเริ่ม):** `verdict=proceed`, `confidence=0.87`, เลือก `core` → ทำ P2-1/2/3 รอบนี้ · P2-4 (แบ่งหน้าแคตตาล็อก) เลื่อนไปรอบถัดไป

| WP | สิ่งที่แก้ | ไฟล์ |
|---|---|---|
| P2-1 | PWA manifest (`display: standalone`, `orientation: portrait`, `theme/background #07090E`, `start_url "/"` scope `/`) + ไอคอน 4 ขนาด (apple-touch 180 / 192 / 512 / 512-maskable) + แท็ก `<link rel=manifest>` `<link rel=apple-touch-icon>` `<meta name=theme-color>` `mobile-web-app-capable` `apple-mobile-web-app-*` `description` | `frontend/public/manifest.webmanifest` (ใหม่), `frontend/public/{apple-touch-icon,pwa-192,pwa-512,pwa-512-maskable}.png` (ใหม่), `frontend/index.html` |
| P2-2 | `_find_duplicate_raw()` — เทียบ size ก่อนแล้วค่อยยืนยัน SHA-256 (ไม่เปิดอ่านทุกไฟล์) → ไฟล์ซ้ำใช้ไฟล์เดิมไม่เขียนซ้ำ · `upload_mobile_video` คืน `sha256` + `deduplicated` · `file_info["sha256"]` ติดไปกับรายการสินค้า | `scripts/mobile_quick_studio.py` |
| P2-3 | `useWakeLock(active)` — ขอกลับอัตโนมัติเมื่อ tab กลับมา visible, release ตอน unmount/ยกเลิก, บราวเซอร์ไม่รองรับ (iOS Safari) เป็น no-op · เปิดใช้ตอนเรนเดอร์ Step 3 และตอนเปิดหน้ากล้อง Guided Take | `frontend/src/hooks/useWakeLock.js` (ใหม่), `MobileQuickStudio.jsx`, `MobileFilmingPage.jsx` |
| test | `test_upload_mobile_video_dedupes_identical_bytes` — bytes เดิม 2 ครั้ง = ไฟล์เดียว + `deduplicated` / bytes ต่าง = ไฟล์ใหม่ + นับไฟล์จริงใน `raw_dir/prod` | `tests/test_mobile_quick_studio.py` |

### หลักฐานการตรวจสอบ (P2)

- `.venv` `py_compile scripts/mobile_quick_studio.py scripts/api_mobile_studio.py tests/test_mobile_quick_studio.py` → **exit 0**
- `pytest tests/test_mobile_quick_studio.py -q` → **27 passed** (รวมเคส dedupe ใหม่)
- `npm run build` → **ผ่าน** (`✓ built in 494ms`)
- `npx oxlint src/hooks/useWakeLock.js src/components/MobileQuickStudio.jsx src/components/MobileFilmingPage.jsx` → **0 errors** (warnings เป็นของเดิม), `useWakeLock.js` **0 warnings**
- `node --test src/lib/mobileStudioFlow.test.js` → **6 passed / 0 failed**
- `manifest.webmanifest` parse เป็น JSON ผ่าน + ถูก copy ลง `dist/` ครบ (ไอคอน 4 ไฟล์ + manifest)
- `01_Raw/prod` ไม่มีไฟล์ทดสอบหลุดเข้า (fixture ชี้ไป `tmp_path/raw_dir`)

### หมายเหตุ

- ~~**P2-4 (แบ่งหน้าแคตตาล็อก) ยังไม่ทำ**~~ → **ทำแล้ว** ดูหัวข้อ "P2-4 — แบ่งหน้าแคตตาล็อก" ด้านล่าง
- Wake-Lock ทดสอบใน node ไม่ได้ (ต้องมี DOM/navigator) → ยืนยันบนเครื่องจริง: Android Chrome จอไม่ดับระหว่างถ่าย/เรนเดอร์, iOS Safari ไม่พัง (API ไม่รองรับ)
- ยังไม่ commit

---

## P2-4 — แบ่งหน้าแคตตาล็อก (ทำต่อ 2026-10-04 · Cline (Claude Sonnet 4.5))

**Jev (ก่อนเริ่ม):** `verdict=proceed`, `confidence=0.98`, `choice=go`

| WP | สิ่งที่แก้ | ไฟล์ |
|---|---|---|
| P2-4a | `GET /api/mobile-studio/catalog?page=&page_size=` — `page ≥ 1`, `page_size` 1–100 (FastAPI `Query`) · คืน `page`/`page_size`/`total_pages`/`has_more` เพิ่มจากของเดิม · ไม่ส่งพาราม = ของเดิมทั้งหมด (back-compat) | `scripts/api_mobile_studio.py` |
| P2-4b | `fetchMobileCatalog(params)` ส่ง query ได้ (ไม่ส่ง = ของเดิม) · helper `MOBILE_CATALOG_PAGE_SIZE = 20`, `catalogPageParams(page)`, `mergeCatalogPage(existing, incoming)` (ตัด id ซ้ำ ไม่ mutate ลิสต์เดิม) | `frontend/src/api.js`, `frontend/src/lib/mobileStudioFlow.js` |
| P2-4c | Step 1: โหลดหน้าแรก 20 รายการ + ปุ่ม "โหลดเพิ่ม (X จาก Y)" · `loadMoreCatalog` กันยิงทับด้วย `catalogVersionRef` + merge กันซ้ำ · กู้สถานะ URL/sessionStorage ถ้าสินค้าไม่อยู่ในหน้าแรก → ดึงทั้งคลังครั้งเดียว (ไม่เสียการ restore `?product=`) | `frontend/src/components/MobileQuickStudio.jsx` |
| test | `test_catalog_pagination_slices_and_reports_next_page` (slice / has_more / total_pages / ไม่ส่งพาราม / พารามผิดขอบ 422) · `mobileStudioFlow.test.js` เพิ่่มเคส `catalogPageParams` + `mergeCatalogPage` | `tests/test_mobile_quick_studio.py`, `frontend/src/lib/mobileStudioFlow.test.js` |

### หลักฐานการตรวจสอบ (P2-4)

- `.venv` `py_compile scripts/api_mobile_studio.py tests/test_mobile_quick_studio.py` → **exit 0**
- `pytest tests/test_mobile_quick_studio.py -q` → **28 passed** (รวมเคส pagination ใหม่)
- `npm run build` → **ผ่าน** (`✓ built in 533ms`)
- `npx oxlint src/components/MobileQuickStudio.jsx src/api.js src/lib/mobileStudioFlow.js src/lib/mobileStudioFlow.test.js` → **0 errors** (8 warnings เป็นของโค้ดเดิม)
- `node --test src/lib/mobileStudioFlow.test.js` → **7 passed / 0 failed**
- ไม่มีไฟล์ทดสอบหลุดเข้า `01_Raw`

### หมายเหตุ

- `page_size` ฝั่งเซิร์ฟเวอร์จำกัด ≤ 100; client ใช้ 20 ต่อหน้า — ถ้าคลัง ≤ 20 ชิ้น behavior เดิมเป๊ะ (ไม่เห็นปุ่มโหลดเพิ่ม)
- ปุ่ม "โหลดเพิ่ม" และ Wake-Lock ต้องยืนยันบนเครื่องจริง (Android Chrome / iOS Safari)

