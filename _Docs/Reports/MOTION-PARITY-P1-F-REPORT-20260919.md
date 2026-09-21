# P1-F Motion parity report — 2026-09-19

ดำเนินการโดย: Codex (GPT-5)

## ผลสรุป

สร้าง comparison seam แบบ opt-in สำเร็จใน `tests/motion_capture/` โดยใช้ `SequencePlayer` fixture จริง, seek hook ที่ 30 FPS และ ASS/FFmpeg fixture จาก motion contract เดิม

ผล pair จริงมี identity ตรงกันทั้งหมด แต่ structural pixel gate ยังไม่ผ่าน จึงตั้งสถานะเป็น `blocked` และคง `pixel_parity_claim: false`

## Pair ที่ตรวจสอบ

| ค่า | Canvas / live | ASS / FFmpeg | ผล |
|---|---|---|---|
| timestamp | `200ms` จาก `frameIndex=6` | `sample_ms=200` | ตรงกัน |
| preset | `hook.in.bounce` | `hook.in.bounce` | ตรงกัน |
| text | `Motion capture fixture` + `SequencePlayer Canvas` จาก fixture เดิม | logical text เดียวกัน | ตรงกัน |
| frame size | `540x960` | `540x960` | ตรงกัน |
| phase window | In ของ overlay 2 วินาที: `0–500ms` | ASS motion window `0–500ms` | ตรงกัน |

หลักฐานจากการรัน pair:

- live Canvas frame PNG: `b3c88af95a922a28eebb7d7a5723f5377605c4cec1e1434742d8289a2a3a1eea`
- Canvas frame หลัง composite พื้นหลังเดียวกับ ASS: `59dfa66bd594f43df82929c607ad95ac28d597ef15fe20932f3806f8f10d5c56`
- ASS PNG: `99b39d168d701ab1a100957eb81674ca3764b86882baebdda65d3c9e5d0119e2`
- ASS metadata JSON: `27b6cdd17fc6aa4f2d7e97bfffceda7c83e95c5e43271bfbb05ec5fd5c46262a`
- ASS file: `065233ea8bb45839f66237a01a4bebdaa27e820934daf63ca6727f14ce7b9234`

ไฟล์ PNG/ASS/JSON ข้างต้นสร้างใน temporary directory ใต้ `.tmp/` และล้างหลังการเปรียบเทียบแล้ว ไม่เหลือ artifact ถาวรจากรอบนี้

## Metrics

- exact pixel match: `false`
- mask IoU: `0.1813699217` (threshold `>= 0.90`) — ไม่ผ่าน
- bounding-box edge delta: `22px` (threshold `<= 6px`) — ไม่ผ่าน
- centroid delta: `2.0px` (threshold `<= 6px`) — ผ่าน
- normalized mean absolute error: `0.0192941176` (threshold `<= 0.22`) — ผ่าน
- `pixel_parity_claim`: `false`

## Blocker / gate

มี frame pair จริงและ metadata ตรงกัน แต่ภาพยังต่างจากโครงสร้างการวาดของ fixture: Canvas ใช้สอง tier, สี tier แยกกัน และ wrap `SequencePlayer Canvas` เป็นสองบรรทัดบน Canvas ขณะที่ ASS fixture ปัจจุบันเป็น event/text layout เดียวที่ยังไม่ได้ mirror tier color/accent/wrap ทั้งหมด จึงไม่ควรเลื่อน threshold หรืออ้าง parity จาก pair นี้

Opt-in gate จะ `skip` อย่างโปร่งใสเมื่อเจอผลนี้ โดยแสดงค่า `mask_iou` และ `bbox_edge_delta_px` ใน reason

## ไฟล์ที่แก้

- `tests/motion_capture/app_capture.py` — เก็บ `hook_metadata` จาก deterministic capture hook เพื่อยืนยัน preset/fps/frame identity
- `tests/motion_capture/ass_fixture.py` — รองรับ motion window, render text layout และ fixture style parameters โดยยังใช้ ASS adapter เดิม
- `tests/motion_capture/frame_pair.py` — orchestrator, identity gate, Canvas background normalization, comparison manifest และ cleanup ใต้ `.tmp/`
- `tests/motion_capture/test_frame_pair.py` — deterministic metric test และ opt-in live pair gate

ไม่ได้แก้ `TODO.md`, `HISTORY.md`, frontend production renderer, `scripts/subtitle/motion_effects.py`, `scripts/subtitle/overlay_events.py` หรือไฟล์ dirty worktree เดิม

## ผลทดสอบ

- `pytest tests/motion_capture -q` → `4 passed, 2 skipped`
- `pytest tests/motion_capture tests/motion_frame_matrix.py tests/test_preview_render_parity.py tests/test_keyframe_parity.py -q -rs` → `169 passed, 3 skipped`
- opt-in live pair → `4 passed, 2 skipped`; P1-F skip เป็น blocker จาก metrics ตามหลักฐานข้างต้น
- `git diff --check -- tests/motion_capture` → ผ่าน
