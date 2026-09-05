# Refactor Baseline

Baseline นี้บันทึกสภาพระบบก่อนเริ่มแยกโมดูล ใช้เป็นจุดเปรียบเทียบสำหรับทุก Phase ใน `REFACTOR_PLAN.md`

## Environment

- Date: 2026-09-05
- Python: 3.14.2
- Node.js: 24.13.0
- npm: 11.6.2
- FFmpeg: 2025-12-10 build

## Current health

- Python compile: PASS (`python -m compileall -q scripts`)
- FastAPI import: PASS
- Registered FastAPI routes: 77
- Frontend production build: PASS
- Full pytest suite: PASS — 309 passed, 0 failed, 0 skipped, 5 warnings in 54.68s
- Short FFmpeg render regression: PASS — draft 720x1280, 30 FPS, generated entirely under pytest temp storage

## Working tree warning

ก่อนเริ่ม Refactor มีไฟล์ tracked ที่แก้ค้าง 19 ไฟล์ และมีไฟล์ใหม่หลายไฟล์ การเปลี่ยนแปลงเหล่านี้ต้องถือเป็นงานที่ใช้งานอยู่ ห้าม reset, checkout, clean หรือรวมเข้า Refactor commit โดยไม่ตรวจแยกก่อน

กลุ่มงานที่พบ:

- Frontend product flow และ content tracker
- Editor shell, timeline, inspector, asset panel และ preview player
- Timeline math และ overlay model
- Backend API, pipeline, audio mix, subtitle และ video renderer
- Preview/render parity tests และ keyframe interpolation tests
- Runtime data ใน `_Docs/post_log.json`

## Existing safety coverage

พบ tests ที่ครอบคลุมบางส่วนแล้ว:

- Manifest round-trip และ merge save
- Versioned artifact paths
- Project state และ hook fields
- Project path escape protection
- Render slot serialization/release
- Legacy single-source render path
- Filmstrip cache/path protection
- Reroll validation และ on-demand audio mix
- Preview/render parity หลายส่วน
- Saved projects on disk compatibility
- Keyframe interpolation contract

## Safety coverage added in Phase 0

- FastAPI critical-route inventory for Editor, project state, reroll, render status, and assets
- Legacy manifest fixture that loads without rewriting its bytes
- Representative Editor payload validated against `UpdateProjectStateRequest`
- Create → Load → Edit → Save → Reload round trip through the API
- Short synthetic FFmpeg render checked with FFprobe at 30 FPS
- Separate files for source-level parity probes and black-box render behavior
- Pytest collection guard for 19 historical manual scripts

## Remaining coverage gaps for later phases

- Frontend Autosave request ordering/concurrency
- Flush dirty state ก่อนสลับโปรเจกต์หรือปิดหน้า
- Component mount/unmount แล้ว timer/listener ไม่ค้าง
- Render polling หลัง refresh/backend restart
- Pixel-level Preview = Render comparison across entrance, hold, and exit frames

## Baseline acceptance

Baseline จะสมบูรณ์เมื่อ:

- [x] บันทึก environment versions
- [x] Python compile ผ่าน
- [x] FastAPI import ผ่าน
- [x] บันทึก route count
- [x] Frontend production build ผ่าน
- [x] บันทึก Working Tree ก่อน Refactor
- [x] ตรวจ existing test coverage
- [x] ระบุ coverage gaps
- [x] Full pytest suite จบและบันทึกจำนวน pass/fail/skip
- [x] แยก failure เดิมออกจาก regression ใหม่
- [x] มี short render fixture ที่ไม่แตะ Raw/Assets

## Full test result

ผลจากคำสั่ง:

```powershell
python -m pytest tests/ -q -p no:cacheprovider --tb=short
```

- Result: `309 passed, 5 warnings in 54.68s`
- Existing automated failures: ไม่มี
- Warning 1 รายการมาจากการเลิกใช้ `httpx` ผ่าน Starlette TestClient
- Warning 4 รายการมาจาก fallback/deprecation ของ audioread และ librosa

การรันครั้งแรกค้างระหว่าง collection เพราะมีสคริปต์ทดลอง 19 ไฟล์อยู่ใต้ `tests/` และใช้ชื่อ `test_*.py` บางไฟล์เรียก Gemini หรือ FFmpeg ตั้งแต่ import จึงเพิ่ม `tests/conftest.py` เพื่อกันเฉพาะรายชื่อสคริปต์เหล่านั้นออกจาก automated suite โดยไม่ได้แก้หรือลบตัวสคริปต์

## Rollback rule

บันทึก hash ของ refactor commit ทุกก้อนใน `REFACTOR_PLAN.md` และย้อนเฉพาะก้อนด้วย `git revert <commit-hash>` ห้ามใช้ `git reset`, `git checkout` หรือ `git clean` ขณะ Working Tree ยังมีงานอื่นค้างอยู่
