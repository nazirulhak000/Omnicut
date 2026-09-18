# Text Motion P1-D Readiness Audit — 2026-09-18

ดำเนินการโดย: Codex (GPT-5)

## Scope

Read-mostly continuation audit เท่านั้น ไม่แก้ production renderer, ไม่ลบไฟล์ใน `04_Exports/` และไม่ commit

## Result

### 1. Contract และ catalog

- Frontend และ Python catalog มี parity surface 34 preset ตาม tests ที่มีอยู่
- `renderer_bound: false` ยังเป็นค่าที่ conservative และไม่ควรตีความว่าไม่มีการเชื่อม renderer เลย
- ปัจจุบันมีการเชื่อมแบบ opt-in แล้ว:
  - Canvas: `SequencePlayer.jsx` เรียก `sampleCanvasMotion()` เมื่อมี `motionContract`/`motionContractId` หรือ metadata ที่ชัดเจน
  - ASS: `overlay_events.py` เรียก `build_ass_motion_segments()` เมื่อมี contract ที่ explicit
  - contract ไม่ครบ/ไม่รู้จักยัง fallback ไป legacy
- ข้อสรุป: catalog ยังไม่ควรถูก promote เป็น renderer-bound ทั้งหมด เพราะยังไม่มี pixel parity gate และบาง track ยังมีข้อจำกัดใน ASS เช่น `reveal`/`position` ที่ต้องใช้ geometry context

### 2. Tests ที่รันรอบนี้

```text
Python motion targeted: 35 passed, 1 skipped
Node motion + scheduling targeted: 34 passed
git diff --check (motion scope): passed
```

Skip เดียวคือ browser Canvas capture เทียบ ASS/FFmpeg แบบ pixel จริง ซึ่งยังไม่มี harness

### 3. TODO/HISTORY consistency

พบเอกสารที่ต้อง reconcile ก่อนปิดรอบ:

- `TODO.md` มี P1-A ซ้ำ 2 รายการใน continuation plan
- `TODO.md` มี `Subtask MOTION-ASS-ADAPTER-20260918 — closed` แต่ checklist Todo/Gate ภายในยังเป็น `[ ]` ทั้งที่ `HISTORY.md` บันทึกว่างาน adapter ผ่าน 6 tests แล้ว
- active round ระบุ backend opt-in integration complete แล้ว แต่ยังมี P1-C active และ P1-D closeout ที่ยังไม่ปิด
- `HISTORY.md` มีบันทึกย่อยของ ASS adapter แล้ว แต่ยังไม่มี closeout entry ของรอบ `TEXT-MOTION-SYSTEM-FOUNDATION-20260918`

สถานะนี้เป็น documentation blocker ไม่ใช่ production blocker

### 4. Export cleanup

พบไฟล์ต้องสงสัยในโฟลเดอร์งานจริง:

- `04_Exports/Ready_to_post/demo_20260918_164441.mp4` — 565,081 bytes
- `04_Exports/Ready_to_post/demo_20260918_164441.webp` — 0 bytes
- MP4 มี entry ใน `_Docs/export_registry.json` ด้วย `status: rendered`, `project_name: demo`, `product_id: null`, `angle_id: null`

จึงยังสรุปว่าไม่มี test/demo artifact หลุดใน `04_Exports/` ไม่ได้ และยังไม่ควรปิด Definition of Done ข้อนี้จนกว่าจะยืนยันว่าเป็นผลงานจริงหรือจัดการด้วย cleanup ที่ได้รับอนุญาต

## Blockers

1. ยังไม่มี real Canvas-vs-ASS pixel frame diff
2. Documentation state ใน `TODO.md`/`HISTORY.md` ยังไม่ตรงกัน
3. `demo_*` export ต้องมีการตัดสินใจด้าน data cleanup ก่อนปิดรอบ

## Follow-up 2026-09-18

- Playwright Chromium capture seam is now available under `tests/motion_capture/`.
- It captured 34 presets x 5 frames deterministically and writes only to `.tmp/`.
- ASS/libass fixtures and structural metrics are available, but the Canvas side is still a contract fixture rather than the live `SequencePlayer` DOM.
- The identified demo test artifacts were moved out of `04_Exports/Ready_to_post` and their registry entries were removed. They remain quarantined under `.tmp/cleanup_20260918` because permanent deletion was blocked by execution safety policy.
- The four full-pytest failures were independently classified as unrelated pre-existing failures.

## Next actions

1. ขอ owner ยืนยันการเก็บ/ย้าย/ลบ `demo_*` และอัปเดต registry ให้สอดคล้อง โดยทำเป็น cleanup รอบแยก
2. แก้เฉพาะเอกสารให้เหลือ continuation plan เดียว, mark checklist adapter เป็น completed และเพิ่ม closeout evidence ของรอบหลัก
3. ทำ browser capture harness ใน `.tmp/` พร้อม ASS/FFmpeg fixture และ threshold ที่ระบุข้อจำกัด font/rasterizer/alpha
4. คง `renderer_bound: false` จนกว่า pixel gate จะผ่าน; หลังจากนั้นค่อยเปลี่ยน metadata เป็นราย preset ที่ตรวจจริง
