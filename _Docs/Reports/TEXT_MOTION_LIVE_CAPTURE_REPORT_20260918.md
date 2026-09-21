# Text Motion Live Capture Report — 2026-09-18

ดำเนินการโดย: Codex (GPT-5)

## ผลที่ยืนยันแล้ว

- เปิดแอปผ่าน Vite HTTPS และใช้ proxy `/api` ของแอปจริง
- โหลดโปรเจกต์จริงจาก `/api/projects` แล้วเปิด `EditorShell` ด้วย `capcut_active_tab=editor`
- จับภาพ Canvas ของ `SequencePlayer` จริงด้วย Playwright ผ่าน selector:

```css
div[class*="rounded-2xl"][class*="shadow-2xl"] canvas
```

- ผล capture จริง: Canvas ภายใน `540×960` และ CSS preview ประมาณ `316.94×565`
- ภาพถูกอ่านจาก `HTMLCanvasElement.toDataURL('image/png')`
- artifact ถูกเก็บชั่วคราวใน `.tmp/` และย้ายไป quarantine หลังตรวจเสร็จ ไม่แตะ `04_Exports/`

## Test-side seams ที่เพิ่ม

- `tests/motion_capture/app_capture.py`
  - รับ URL/selector
  - รองรับ HTTPS dev certificate
  - รองรับ `localStorage` ก่อน navigation
  - ใช้ `window.motionCapture.capture({ frameIndex })` ถ้าหน้า fixture มี deterministic seek hook
  - ปฏิเสธ output นอก `.tmp/`
- `frontend/motion_capture.html`
- `frontend/src/motionCaptureFixture.jsx`
  - mount `SequencePlayer` ตัวจริง ไม่ใช่การวาดแถบสีแทน renderer
  - ใช้ motion contract เดียวกับ catalog และคืน `frameIndex/timestampMs`
- `tests/motion_capture/test_app_capture.py`
  - live app test เป็น opt-in และ skip อย่างโปร่งใสเมื่อไม่ได้ตั้ง environment

## ข้อจำกัดที่ยังไม่เคลม

ยังไม่ประกาศ Canvas-vs-ASS pixel parity เพราะต้องทำให้ metadata ต่อไปนี้ตรงกันก่อน:

- ขนาด Canvas preview `540×960` กับ ASS frame
- ข้อความ/การขึ้นบรรทัด/ฟอนต์/ขนาด/ตำแหน่งเดียวกัน
- `frame_index` เดียวกันที่ `30 FPS` แทนการปัด timestamp แยก renderer
- phase timing ของ overlay เดียวกัน โดยเฉพาะ In/Hold/Out
- ROI ของ overlay แทนการคำนวณ error จากพื้นหลังทั้งภาพ

ดังนั้นผล live capture รอบนี้มีสถานะ `app_canvas` และ `pixel_parity_claim: false` ตามเจตนา

## Verification

```text
pytest -q tests/motion_capture/test_app_capture.py \
  tests/test_motion_capture_harness.py \
  tests/test_motion_capture_ass_fixture.py
13 passed, 2 skipped
```

