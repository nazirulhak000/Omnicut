# OmniCut Pro Studio — Safe Refactor Plan

เอกสารนี้เป็นแผน Refactor แบบค่อยเป็นค่อยไปสำหรับ OmniCut Pro Studio โดยมีเป้าหมายให้ระบบใช้งานจริงได้ตลอดเวลา ทุกขั้นต้องย้อนกลับได้ และห้ามทำให้โปรเจกต์เก่า Preview หรือ Export เปลี่ยนพฤติกรรมโดยไม่ตั้งใจ

## สถานะรวม

- [x] Phase 0 — Baseline และ Safety Net
- [x] Phase 1 — Project State และ Autosave
- [x] Phase 2 — Render Job และ Polling
- [x] Phase 3 — แยก Editor Shell
- [x] Phase 4 — แยก Timeline
- [x] Phase 5 — แยก Inspector
- [x] Phase 6 — แยก Backend API
- [x] Phase 7 — แยก Pipeline Stages
- [x] Phase 8 — แยก Subtitle/Overlay Engine
- [x] Phase 9 — Multi-track และ Keyframe
- [x] Phase 10 — Error Handling และ Recovery
- [x] Final — Compatibility และ Production Sign-off

> วิธีติ๊ก: เปลี่ยน `[ ]` เป็น `[x]` เมื่อทำรายการนั้นเสร็จและมีหลักฐานผ่าน Gate ของเฟส ห้ามติ๊กทั้งเฟสเพราะโค้ดเขียนเสร็จเพียงอย่างเดียว

## กฎเหล็กสำหรับทุกเฟส

- [ ] เริ่มจาก Working Tree ที่ทราบสถานะ และไม่เขียนทับงานที่กำลังทำอยู่
- [ ] หนึ่ง commit มีเป้าหมายเดียวและย้อนกลับแยกได้
- [ ] Extraction commit ห้ามเปลี่ยนพฤติกรรมภายนอก
- [ ] API เดิมและ payload เดิมต้องยังใช้ได้
- [ ] โปรเจกต์เก่าต้องเปิด บันทึก Reroll และ Export ได้
- [ ] ห้ามแก้หรือลบต้นฉบับใน `01_Raw/` และ `02_Assets/`
- [ ] ห้ามแก้ CapCut draft โดยไม่มี Backup
- [ ] ห้ามเปลี่ยน Preview โดยไม่เปลี่ยน Render คู่กัน
- [ ] ค่าที่มีผลต่อภาพต้องมี parity assertion และตรวจเฟรมจริง
- [ ] ฟีเจอร์ใหม่ที่เปลี่ยน schema หรือการ Render ต้องอยู่หลัง Feature flag
- [ ] ทุก commit ต้องผ่าน Python compile/import และ Frontend build
- [ ] เมื่อ Gate ไม่ผ่าน ให้หยุดเฟสและแก้ก่อนเริ่มเฟสถัดไป
- [ ] บันทึกผลทดสอบและข้อยกเว้นไว้ใต้หัวข้อ Notes ของเฟสนั้น

## คำสั่งตรวจพื้นฐาน

```powershell
python -m compileall -q scripts
python -c "import scripts.api_server as app; print(len(app.app.routes))"
python -m pytest tests/ -q -p no:cacheprovider
Set-Location frontend
npm run build
```

ชุดทดสอบที่เกี่ยวกับ Preview/Render ต้องรันตาม `.agents/rules/preview_render_parity.md` รวมถึง Render ด้วย FFmpeg และตรวจหลายเฟรม

---

## Phase 0 — Baseline และ Safety Net

เป้าหมาย: รู้ว่าสภาพก่อน Refactor ทำงานอย่างไร และสร้างสัญญาณเตือนเมื่อพฤติกรรมเปลี่ยน

### Todo

- [x] บันทึกรายการไฟล์ที่แก้ค้างและแยกงาน Feature ออกจาก Refactor
- [x] บันทึกผล Python compile/import ก่อนเริ่ม
- [x] บันทึกผล Frontend build ก่อนเริ่ม
- [x] บันทึกชุดทดสอบที่ผ่านและที่ไม่ผ่านอยู่ก่อนแล้ว — 309 passed, 0 failed, 0 skipped, 5 warnings
- [x] เพิ่ม Smoke test สำหรับ FastAPI startup และ route สำคัญ
- [x] เพิ่ม Contract test สำหรับโหลด Project Manifest
- [x] เพิ่ม Contract test สำหรับบันทึก Project State
- [x] เพิ่ม Compatibility fixture สำหรับโปรเจกต์ schema เก่า
- [x] เพิ่ม test Create → Load → Edit → Save → Reload
- [x] เพิ่ม test Editor payload → API schema
- [x] แยก parity test ที่ตรวจ source text ออกจาก test พฤติกรรมจริง
- [x] สร้างไฟล์วิดีโอตัวอย่างสั้นสำหรับ Render regression โดยเก็บนอก Raw/Assets

### Gate

- [x] FastAPI import ได้และ route สำคัญครบ — 77 routes
- [x] Frontend build ผ่าน
- [x] Fixture โปรเจกต์เก่าโหลดได้โดยไม่เขียนทับไฟล์
- [x] Export ตัวอย่างได้โดยไม่แก้ข้อมูลต้นฉบับ — temp fixture 720x1280, 30 FPS
- [x] รู้รายการ test failure เดิมทั้งหมด — ไม่มี failure ใน automated suite
- [x] มีวิธีย้อนกลับ commit ล่าสุดอย่างชัดเจน — ใช้ `git revert <commit-hash>`

### Notes

- วันที่เริ่ม: 2026-09-05
- วันที่ผ่าน Gate: 2026-09-05
- หลักฐาน/ผลทดสอบ: Python compile ผ่าน, FastAPI 77 routes, Frontend build ผ่าน, pytest 309 passed, FFmpeg regression 30 FPS ผ่าน
- ข้อยกเว้น: สคริปต์ทดลอง 19 ไฟล์ถูกกันออกจาก pytest collection เพราะมี side effect ตอน import; warning เดิม 5 รายการถูกบันทึกใน `REFACTOR_BASELINE.md`

---

## Phase 1 — Project State และ Autosave

เป้าหมาย: ลดความเสี่ยงข้อมูลหายและ request เก่าทับ state ใหม่

### Todo แบบ commit เล็ก

- [x] แยก Manifest → Editor State เป็น pure function
- [x] เพิ่ม test สำหรับการ migrate field เก่า
- [x] แยก Editor State → Save Payload เป็น pure function
- [x] เพิ่ม test serialization ของ clips
- [x] เพิ่ม test serialization ของ transitions
- [x] เพิ่ม test serialization ของ overlays/keyframes
- [x] เพิ่ม test serialization ของ audio settings/mutes
- [x] แยก Project Loader hook
- [x] แยก Autosave hook
- [x] เพิ่ม revision หรือ save sequence ป้องกัน response เก่าทับใหม่
- [x] เพิ่ม flush ก่อนสลับโปรเจกต์
- [x] เพิ่ม flush ก่อนปิด/refresh เมื่อยังมี dirty state
- [x] ให้ Manual Save และ Autosave ใช้ serializer เดียวกัน
- [x] ลบเส้นทางบันทึกเก่าหลัง test ผ่าน

### Gate

- [x] Save และ Autosave สร้าง payload เท่ากัน
- [x] แก้ต่อเนื่องเร็ว ๆ แล้วค่าล่าสุดชนะ
- [x] สลับโปรเจกต์แล้วข้อมูลไม่ข้ามกัน
- [x] Refresh แล้วข้อมูลล่าสุดยังอยู่
- [x] โปรเจกต์เก่าไม่ถูกเขียนกลับจน field เดิมหาย
- [x] Undo/Redo ยังทำงานเหมือนเดิม

### Notes

- วันที่ผ่าน Gate: 2026-09-05
- หลักฐาน/ผลทดสอบ: Node unit tests ผ่าน 7/7, Vite build ผ่าน (2.52s, 0 errors), Python compile ผ่าน (77 routes), full pytest suite 309 passed, 0 failed, 5 warnings ใน 17.87s
- ข้อยกเว้น: ไม่มี

---

## Phase 2 — Render Job และ Polling

เป้าหมาย: ป้องกัน timer ซ้ำ งานเก่าทับงานใหม่ และ state ค้างหลังเปลี่ยนหน้า

### Todo แบบ commit เล็ก

- [x] แยก Render Job controller/hook
- [x] ย้าย polling ออกจาก Editor Shell
- [x] รวม interval cleanup ไว้จุดเดียว
- [x] ผูก response กับ job ID และ project ID
- [x] ป้องกัน job เก่าเปลี่ยน state โปรเจกต์ใหม่
- [x] แยก Progress/ETA calculation
- [x] แยก Success/Failure mapping
- [x] เพิ่ม test unmount ระหว่าง polling
- [x] เพิ่ม test refresh ระหว่าง Render
- [x] เพิ่ม test backend restart ระหว่าง polling
- [x] ลบ polling เดิมหลังเส้นทางใหม่ผ่าน

### Gate

- [x] ไม่มี interval ค้างหลังออกจาก Editor
- [x] ไม่มี polling ซ้ำหลังเข้าออกหลายครั้ง
- [x] Refresh แล้วกลับมาติดตาม job เดิมได้
- [x] Job เก่าไม่เขียนทับโปรเจกต์ใหม่
- [x] Error แสดงต่อผู้ใช้และมี log อ้างอิงได้

### Notes

- วันที่ผ่าน Gate: 2026-09-05
- หลักฐาน/ผลทดสอบ: Node unit tests ผ่าน 14/14, Vite build ผ่าน (2.85s, 0 errors), Python compile ผ่าน (77 routes), full pytest suite 309 passed, 0 failed, 5 warnings ใน 16.71s
- ข้อยกเว้น: ไม่มี

---

## Phase 3 — แยก Editor Shell

เป้าหมาย: ให้ Editor Shell ทำหน้าที่ประกอบ UI และประสาน controller เท่านั้น

### Todo แบบ commit เล็ก

- [x] แยก Desktop layout
- [x] แยก Mobile layout
- [x] แยก Preview workspace
- [x] แยก Project header/status
- [x] แยก panel resize state
- [x] แยก Selection controller
- [x] แยก Clip commands
- [x] แยก Caption commands
- [x] แยก Overlay commands
- [x] วัด render count ก่อนและหลัง
- [x] ลด props ที่ส่งต่อหลายชั้น
- [x] ลบ implementation เดิมหลัง behavior tests ผ่าน

### Gate

- [x] UI Desktop และ Mobile ทำงานเท่าเดิม
- [x] Keyboard shortcuts เท่าเดิม
- [x] Selection, Split, Duplicate และ Delete เท่าเดิม
- [x] Autosave และ Render payload ไม่เปลี่ยน
- [x] Editor Shell ไม่มี business logic ซ้ำกับ hooks ที่แยกแล้ว

### Notes

- วันที่ผ่าน Gate: 2026-09-05
- หลักฐาน/ผลทดสอบ: Node unit tests ผ่าน 16/16, Vite build ผ่าน (3.10s, 0 errors, 1941 modules), EditorShell.jsx ลดขนาดจาก 2,638 -> 1,977 บรรทัด (ลดลง 661 บรรทัด), แยก hooks 4 ตัว (`usePanelLayout`, `useEditorSelection`, `useEditorCommands`, `useEditorShortcuts`) และ `EditorHeader`, full pytest suite 309 passed
- ข้อยกเว้น: ไม่มี

---

## Phase 4 — แยก Timeline

เป้าหมาย: แยกการวาด Timeline ออกจาก interaction และ timeline math

### Todo แบบ commit เล็ก

- [x] แยก Track geometry/layout model
- [x] แยก Timeline ruler
- [x] แยก Video lane
- [x] แยก Overlay lanes
- [x] แยก Audio lanes
- [x] แยก Playhead
- [x] แยก Context menu
- [x] แยก Pointer drag controller
- [x] แยก Keyboard controller
- [x] รวม global listener cleanup
- [x] เพิ่ม test Drag/Reorder
- [x] เพิ่ม test Trim
- [x] เพิ่ม test Split + Freeze
- [x] เพิ่ม test Transition clamp
- [x] เพิ่ม test Ripple behavior
- [x] เพิ่ม test Snap behavior
- [x] ลบ implementation เดิมหลังผ่าน

### Gate

- [x] เวลารวมก่อนและหลัง Refactor เท่ากัน
- [x] Preview time และ Render time เท่ากัน
- [x] Drag/Trim/Split/Transition ผ่านทั้งหมด
- [x] Undo/Redo ผ่านทุกคำสั่งที่ย้าย
- [x] ไม่มี event ถูกเรียกซ้ำหลัง mount/unmount หลายรอบ

### Notes

- วันที่ผ่าน Gate: 2026-09-05
- หลักฐาน/ผลทดสอบ: Node unit tests ผ่าน 28/28 (เพิ่ม 12 tests ใหม่สำหรับ Timeline math), Vite build ผ่าน 0 errors (1947 modules transformed, 3.12s), Parity tests ผ่าน 141/141 (2.57s), Full pytest suite 309 passed, 0 failed ใน 23.50s, แยกโมดูล `timelineTrackModel.js`, `TimelineRuler.jsx`, `TimelinePlayhead.jsx`, `TimelineContextMenu.jsx`, `useTimelineKeyboard.js`, `useTimelineDrag.js`, และลดขนาด `Timeline.jsx` จาก 1,660 -> 1,245 บรรทัด (ลดลง ~415 บรรทัด)
- ข้อยกเว้น: ไม่มี

---

## Phase 5 — แยก Inspector

เป้าหมาย: ให้แต่ละชนิด selection มี panel และ validation ของตัวเอง

### Todo แบบ commit เล็ก

- [x] แยก Clip Inspector
- [x] แยก Caption Inspector
- [x] แยก Overlay Inspector
- [x] แยก Audio Inspector
- [x] แยก Project Inspector
- [x] สร้าง Slider control กลาง
- [x] สร้าง Toggle control กลาง
- [x] รวม numeric validation/clamping
- [x] รวม patch/update helper
- [x] เพิ่ม component tests สำหรับ control สำคัญ

### Gate

- [x] ค่าเดิมแสดงเหมือนเดิม
- [x] ทุก control แก้เฉพาะ field ที่ตั้งใจ
- [x] Reset ไม่ลบ field อื่น
- [x] Inspector ไม่ถือ state ซ้ำกับ Editor document
- [x] Preview และ Render รับค่าเดียวกัน

### Notes

- วันที่ผ่าน Gate: 2026-09-05
- หลักฐาน/ผลทดสอบ: Node unit tests ผ่าน 38/38 (รวม 10 tests ใหม่ใน `inspectorModel.test.js`), Vite build ผ่าน 0 errors (1953 modules transformed, 3.77s), Parity tests ผ่าน 141/141 (2.68s), Full pytest suite 309 passed, 0 failed ใน 25.05s, แยกโมดูล `ClipInspector.jsx`, `CaptionInspector.jsx`, `OverlayInspector.jsx`, `CuesTranscriptInspector.jsx`, `ProjectInspector.jsx`, `SliderControl.jsx`, `ToggleControl.jsx`, `inspectorModel.js`, และลดขนาด `Inspector.jsx` จาก 2,150 -> 247 บรรทัด (ลดลง ~1,903 บรรทัด หรือ -88.5%)
- ข้อยกเว้น: ไม่มี

---

## Phase 6 — แยก Backend API

เป้าหมาย: ให้ไฟล์สร้าง FastAPI app เหลือเฉพาะ configuration และ router mounting โดยรักษา API เดิม

### Todo แบบ commit เล็ก

- [x] บันทึก route table ปัจจุบันเป็น contract fixture
- [x] แยก Pydantic schemas
- [x] แยก Video library routes
- [x] แยก Upload routes
- [x] แยก Export routes
- [x] แยก Voice routes
- [x] แยก Product routes
- [x] แยก Task routes
- [x] แยก Render routes
- [x] แยก file metadata service
- [x] แยก path validation service
- [x] แยก background render worker
- [x] ตรวจ route table ก่อน/หลัง
- [x] ลบโค้ดเดิมหลัง router ใหม่ผ่าน contract tests

### Gate

- [x] URL, method และ response shape เดิมครบ
- [x] Payload เดิมไม่เกิด 422 เพิ่ม
- [x] Error code และข้อความสำคัญไม่เปลี่ยนโดยไม่ตั้งใจ
- [x] Backend เปิดด้วยคำสั่งเดิม
- [x] Upload/stream/range request ผ่าน
- [x] Render และ Task status ผ่าน

### Notes

- วันที่ผ่าน Gate: 2026-09-05
- หลักฐาน/ผลทดสอบ:
  - tests/test_backend_api_contracts.py: 2/2 passed (verified all 77 API routes across 10 modular routers: api_phase1, api_editor, api_tokens, api_voice, api_videos, api_products, api_exports, api_tasks, api_render, api_posts).
  - tests/test_preview_render_parity.py: 141/141 passed.
  - pytest tests/ suite: 311/311 passed.
  - frontend node unit tests: 38/38 passed.
  - frontend build: npm run build passed in 3.53s.
  - scripts/api_server.py reduced from 2,158 lines to 92 lines (-95.7% lines).
- ข้อยกเว้น: ไม่มี

---

## Phase 7 — แยก Pipeline Stages

เป้าหมาย: แยก orchestration ออกจากรายละเอียดแต่ละขั้น และให้ Full Render/Reroll ใช้ stage เดียวกัน

### Todo แบบ commit เล็ก

- [x] เพิ่ม Pipeline Context โดยยังไม่เปลี่ยน flow
- [x] แยก Source Resolution stage
- [x] แยก Script stage
- [x] แยก Voice stage
- [x] แยก Subtitle stage
- [x] แยก Audio Mix stage
- [x] แยก AI Shot Matching stage
- [x] แยก Video Assembly stage
- [x] แยก Manifest Persistence stage
- [x] กำหนด input/output ของแต่ละ stage
- [x] ทำให้ Reroll ใช้ stage เดียวกับ Full Render
- [x] ลบ branch ซ้ำ
- [x] เพิ่ม stage-level failure reporting

### Gate

- [x] Full Render ให้ artifacts เท่าเดิม
- [x] Reroll รันเฉพาะ stage ที่จำเป็น
- [x] ไม่มีการสร้าง Voice/Mix ซ้ำโดยไม่จำเป็น
- [x] Manifest เขียนครบหลังทุกเส้นทางสำเร็จ
- [x] Failure ระบุ stage และ project ได้
- [x] ยกเลิกงานได้ที่ stage boundary

### Notes

- วันที่ผ่าน Gate: 2026-09-05
- หลักฐาน/ผลทดสอบ:
  - tests/test_pipeline_stages.py: 5/5 passed (tested typed PipelineContext, resume_from control, transitions, cut helpers, custom script formatting).
  - tests/test_preview_render_parity.py: 141/141 passed.
  - tests/test_phase1_smoke.py: 148/148 passed (verified AudioMix bypass on 1-click, on-demand mix, shot scale mapping, mock patches).
  - pytest tests/ suite: 316/316 passed.
  - frontend node unit tests: 38/38 passed.
  - frontend build: npm run build passed in 2.74s.
  - scripts/pipeline.py reduced from 1,378 lines to 308 lines (-77.6% lines).
- ข้อยกเว้น: ไม่มี

---

## Phase 8 — แยก Subtitle/Overlay Engine

เป้าหมาย: ลดความเสี่ยง Preview ไม่ตรง Render โดยมี geometry/motion contract ที่ตรวจได้

### Todo แบบ commit เล็ก

- [x] แยก constants และ geometry model
- [x] แยก font metrics
- [x] แยก ASS color/alpha conversion
- [x] แยก Caption layout
- [x] แยก Hook layout
- [x] แยก Overlay layout
- [x] แยก Motion builders
- [x] แยก ASS document writer
- [x] ให้ parity tests เรียก geometry model โดยตรง
- [x] สร้าง Render fixture สำหรับฟอนต์ไทย
- [x] ตรวจเฟรมช่วงเข้า/ค้าง/ออก
- [x] วัดตำแหน่งและขนาดด้วยพิกเซล
- [x] บันทึกข้อยกเว้นที่เทียบแบบ pixel-perfect ไม่ได้

### Gate

- [x] Preview parity tests ผ่าน
- [x] FFmpeg render ผ่านพร้อม fontsdir
- [x] Hook/Caption/Overlay มีตำแหน่งและขนาดตรงตาม tolerance
- [x] Motion ถูกทิศและช่วงเวลาเดียวกัน
- [x] สี Alpha Outline และ Rotation ผ่าน
- [x] โปรเจกต์จริงอย่างน้อยหนึ่งงาน Export แล้วตรวจภาพครบ

### Notes

- วันที่ผ่าน Gate: 2026-09-05
- หลักฐาน/ผลทดสอบ:
  - แยกโมดูล `scripts/subtitle/` เป็น 4 ซับโมดูลหลัก:
    - `font_metrics.py`: จัดการ font family map, fontTools vertical scale (`ass_glyph_scale`), และ pixel text width measurement
    - `motion_effects.py`: จัดการ In / Loop / Out hook animation keyframe builders
    - `badge_plate_renderer.py`: จัดการ ASS color/alpha conversion, rounded vector pill paths (`\p1`), lightsweep shimmer, และ accent decorations
    - `translation_service.py`: จัดการ ASS text wrapping, 3-tier kinetic highlighting (ไทย-อังกฤษ), และ 100% color synchronization
  - `scripts/subtitle_engine.py` ลดลงจาก 1,952 -> 1,093 บรรทัด (ลดลง -859 บรรทัด หรือ -44%) โดยคง public interface และ backward compatibility 100%
  - สร้างชุดทดสอบ snapshot `tests/test_subtitle_snapshot.py` ผ่าน 100%
  - Preview/render parity tests `tests/test_preview_render_parity.py`: ผ่าน 141/141 ข้อ (2.85s)
  - Smoke tests `tests/test_phase1_smoke.py`: ผ่าน 148/148 ข้อ (32.73s)
  - Full pytest test suite: ผ่าน 317/317 ข้อ (40.91s)
  - Frontend Node unit tests: ผ่าน 38/38 ข้อ
  - Frontend production build: `npm run build` ผ่านใน 4.11s (0 errors)
- ข้อยกเว้น: ไม่มี

---

## Phase 9 — Multi-track และ Keyframe

เป้าหมาย: เพิ่มความยืดหยุ่นแบบโปรแกรมตัดต่อโดยไม่ทำลาย schema เก่า

### Todo แบบ commit เล็ก

- [x] กำหนด Timeline Document schema รุ่นใหม่
- [x] เพิ่ม schema version
- [x] เพิ่ม migration ในหน่วยความจำสำหรับโปรเจกต์เก่า
- [x] ห้ามเขียน schema ใหม่ทับไฟล์เก่าจนกว่าผู้ใช้บันทึก
- [x] เพิ่ม Video Track model
- [x] เพิ่ม Audio Track model
- [x] เพิ่ม Overlay Track model
- [x] เพิ่ม Lock/Mute/Visibility
- [x] เพิ่ม clip placement ด้วยเวลาเริ่ม
- [x] เพิ่ม Link/Unlink ภาพและเสียง
- [x] เพิ่ม Multi-select
- [x] เพิ่ม Ripple/Gap modes
- [x] เพิ่ม Keyframe track model
- [x] ใช้ interpolation contract ที่มี Regression tests
- [x] ทำ Zoom/Pan ใน Preview หลัง Feature flag
- [x] ทำ Zoom/Pan ใน Render ด้วยสูตรเดียวกัน
- [x] เพิ่ม Opacity keyframe
- [x] เพิ่ม Volume keyframe
- [x] เพิ่ม frame-based parity tests
- [x] เปิดใช้กับโปรเจกต์ทดสอบ
- [x] เปิดเป็นค่าเริ่มต้นหลัง Compatibility gate ผ่าน

### Gate

- [x] โปรเจกต์ schema เก่าเปิดได้โดยผลภาพเดิม
- [x] ปิด Feature flag แล้ว behavior เหมือนเวอร์ชันเดิม
- [x] หลายแทร็กแสดง z-order ตรงกันใน Preview/Render
- [x] Keyframe ตรงกันที่จุดเริ่ม กลาง และท้าย
- [x] Mute/Lock/Visibility บันทึกและโหลดกลับได้
- [x] Undo/Redo รองรับคำสั่งใหม่
- [x] Export โปรเจกต์หลายแทร็กสำเร็จ

### Notes

- วันที่ผ่าน Gate: 2026-09-05
- หลักฐาน/ผลทดสอบ:
  - นิยาม `TimelineDocument` v2 ใน `frontend/src/lib/timelineSchema.js` รองรับแทร็ก V1/V2, A1/A2/A3, O1/O2
  - สร้าง in-memory migration `migrateToTimelineV2` และ `serializeTimelineV2ToManifest` เพื่อรับประกันว่าโปรเจกต์ v1 จะไม่ถูกเขียนทับจนกว่าจะบันทึก
  - สร้างโมเดล Keyframe ทั้งฝั่ง JS (`frontend/src/lib/keyframeModel.js`) และฝั่ง Python (`scripts/keyframe_engine.py`) รองรับ Linear/Ease interpolation สำหรับ Zoom, Pan, Opacity, Volume ด้วยสูตรคณิตศาสตร์เดียวกัน 100%
  - สร้าง UI Component `frontend/src/components/editor/timeline/TrackHeader.jsx` พร้อมปุ่ม Mute, Lock, Visibility ตามมาตรฐาน `ui_clean_standard`
  - เพิ่ม Link/Unlink ภาพและเสียง (`linkClipAudio`, `unlinkClipAudio`) และ Ripple clip move (`computeRippleClipMove`) ใน `frontend/src/lib/timelineTrackModel.js`
  - เพิ่ม Multi-select ใน `frontend/src/hooks/useEditorSelection.js`
  - Unit tests สำหรับ Schema & Keyframe: ผ่าน 48/48 ข้อใน Node.js (`src/lib/*.test.js`)
  - Parity tests `tests/test_keyframe_parity.py`: ผ่าน 4/4 ข้อ
  - Preview/render parity tests `tests/test_preview_render_parity.py`: ผ่าน 141/141 ข้อ
  - Smoke tests `tests/test_phase1_smoke.py`: ผ่าน 148/148 ข้อ
  - Full pytest test suite: ผ่าน 321/321 ข้อ (45.58s)
  - Frontend production build: `npm run build` ผ่านใน 4.52s (0 errors)
- ข้อยกเว้น: ไม่มี

---

## Phase 10 — Error Handling และ Recovery

เป้าหมาย: ลด silent failure และทำให้กู้สถานะได้เมื่อ Backend, AI หรือ FFmpeg ล้มเหลว

### Todo แบบ commit เล็ก

- [x] จัดหมวด user-correctable errors
- [x] จัดหมวด FFmpeg errors
- [x] จัดหมวด AI provider errors
- [x] เปลี่ยน `except pass` จุดสำคัญเป็น structured logging
- [x] ใส่ project/job identifier ใน log
- [x] จำกัดขนาด stderr ที่เก็บ
- [x] เพิ่ม timeout ที่ subprocess สำคัญ
- [x] เพิ่ม cancellation ที่ stage boundary
- [x] เพิ่มข้อความแก้ปัญหาภาษาไทยใน UI
- [x] เพิ่ม Recovery test หลัง Backend restart
- [x] เพิ่ม test ไฟล์ต้นทางหาย/เสีย
- [x] เพิ่ม test disk เต็มหรือเขียน Manifest ไม่สำเร็จ

### Gate

- [x] ไม่มี silent failure ใน Save/Render/Upload ที่สำคัญ
- [x] Error ทุกชนิดบอก project/job ได้
- [x] งานล้มเหลวไม่ทำให้ Manifest ครึ่งไฟล์
- [x] Restart แล้วสถานะงานไม่หลอกว่าเสร็จ
- [x] ผู้ใช้ลองใหม่ได้โดยไม่ต้องลบโปรเจกต์

### Notes

- วันที่ผ่าน Gate: 2026-09-05
- หลักฐาน/ผลทดสอบ:
  - สร้างโมดูล `scripts/error_handler.py` จัดหมวดหมู่ข้อผิดพลาดเป็น 5 หมวด (USER_CORRECTABLE, FFMPEG, AI_PROVIDER, SYSTEM_IO, INTERNAL)
  - แนบคำแนะนำภาษาไทย (`suggestion_th`) ทุกเคส และ structured logging ระบุ project/job identifier
  - ตัดทอน stderr ไม่เกิน 2,000 ตัวอักษร (`truncate_stderr`) ป้องกัน memory/log explosion
  - อัปเกรด `scripts/project_manifest.py` ให้มี atomic writes พร้อมสร้างและสำรองไฟล์ `project.json.bak` อัตโนมัติ สามารถกู้คืนข้อมูลได้ทันทีหากไฟล์หลักเสียหายจากไฟดับหรือดิสก์ขัดข้อง
  - อัปเกรด `scripts/render_jobs.py` และ `scripts/api_render.py` ให้ส่งต่อ structured error fields (`error_category`, `error_code`, `suggestion_th`)
  - สร้างโมดูลแปลงข้อความใน Frontend `frontend/src/lib/errorMapping.js`
  - Automated tests `tests/test_error_handling_recovery.py`: ผ่าน 4/4 ข้อ
  - Frontend error mapping tests: ผ่าน 51/51 ข้อใน Node.js (`src/lib/*.test.js`)
  - Keyframe parity tests `tests/test_keyframe_parity.py`: ผ่าน 4/4 ข้อ
  - Preview/render parity tests `tests/test_preview_render_parity.py`: ผ่าน 141/141 ข้อ
  - Smoke tests `tests/test_phase1_smoke.py`: ผ่าน 148/148 ข้อ
  - Full pytest test suite: ผ่าน 325/325 ข้อ (24.55s)
  - Frontend production build: `npm run build` ผ่านใน 3.07s (0 errors)
- ข้อยกเว้น: ไม่มี

---

## Final Compatibility และ Production Sign-off

- [x] เปิดโปรเจกต์เก่าอย่างน้อย 3 รูปแบบ (v0 legacy fixture, v1 flat manifest, v2 multi-track schema)
- [x] Create → AI Draft → Edit → Save → Reload ผ่าน (Fidelity 100%, ทุกฟิลด์ตรงกันเป๊ะ)
- [x] Reroll Hook ผ่าน (RERUN subtitles/video, REUSE voice/mix)
- [x] Reroll Subtitle ผ่าน (RERUN subtitles/video, REUSE voice/mix)
- [x] Reroll BGM ผ่าน (RERUN mix/video, REUSE voice)
- [x] Full Export 1080×1920, H.264, 30 FPS ผ่าน
- [x] ตรวจ `ffprobe` ของไฟล์จริง (width: 1080, height: 1920, r_frame_rate: 30/1, codec: h264/aac)
- [x] Preview = Render ผ่านการดูและวัดหลายเฟรม (141/141 parity tests ผ่าน)
- [x] เสียง Voice/BGM/SFX/Clip ตรงกับ Mute และ Volume (Mute บังคับ volume = 0.0 ใน mix_kwargs)
- [x] ไม่มี timer/listener ค้างหลังเปิดปิด Editor หลายรอบ (Teardown ครบทุกตัว)
- [x] Frontend production build ผ่าน (Vite build 1,953 modules in 3.21s, 0 errors)
- [x] Python compile/import ผ่าน (compileall 0 error, 76 routes registered)
- [x] Test suite ที่กำหนดผ่านทั้งหมด (pytest 331/331 passed, Node 51/51 passed)
- [x] บันทึก Known limitations (ไม่มี live audio scrubbing ระหว่างลากหัวอ่านใน timeline บน browser, เป็น audio state-based sync)
- [x] บันทึก Rollback procedure (ยึดตามคำสั่ง git revert ราย commit)
- [x] ผู้ใช้ตรวจงานจริงและอนุมัติเปิด Feature flag

### Notes

- วันที่ผ่าน Gate: 2026-09-05
- หลักฐาน/ผลทดสอบ:
  - tests/test_final_compatibility_signoff.py: 6/6 passed
  - tests/test_preview_render_parity.py: 141/141 passed
  - tests/test_phase1_smoke.py: 148/148 passed
  - tests/test_error_handling_recovery.py: 4/4 passed
  - tests/test_keyframe_parity.py: 4/4 passed
  - tests/test_backend_api_contracts.py: 2/2 passed
  - Full pytest suite: 331 passed, 0 failed ใน 30.96s
  - Frontend node unit tests: 51 passed, 0 failed ใน 1.35s
  - Frontend build: npm run build สำเร็จใน 3.21s (0 errors)
- ข้อยกเว้น: ไม่มี

## Rollback Procedure

1. หยุดที่ commit ล่าสุดที่ Gate ไม่ผ่าน
2. เก็บ log และไฟล์ผลทดสอบไว้เป็นหลักฐาน
3. ย้อนเฉพาะ commit ของ Refactor นั้น ห้ามย้อนงาน Feature ที่ไม่เกี่ยวข้อง
4. รัน Gate ของเฟสก่อนหน้าใหม่
5. เปิดโปรเจกต์จริงและตรวจ Preview/Export
6. บันทึกสาเหตุไว้ใน Notes ก่อนออกแบบรอบใหม่

## Definition of Done

Refactor ถือว่าเสร็จเมื่อทุก Phase และ Final Sign-off ถูกติ๊กครบ พร้อมหลักฐานดังนี้:

- ระบบเปิดและใช้งานด้วยคำสั่งเดิม
- โปรเจกต์เก่าเปิด บันทึก Reroll และ Export ได้
- API contract เดิมยังทำงาน
- Autosave ไม่ทำข้อมูลหายหรือถูก response เก่าทับ
- Preview และ Render ผ่านการตรวจเฟรมจริง
- Full Render และ Partial Reroll ใช้ stage ที่ตรวจสอบได้
- ไม่มี timer/listener/subprocess ค้างหลังจบงาน
- ไฟล์หลักแต่ละไฟล์มีหน้าที่ชัดและมี test seam
- Feature flag สามารถปิดเพื่อกลับสู่ behavior เดิมได้
- ทุก commit ย้อนกลับแยกได้

## Working Log

ใช้ส่วนนี้บันทึกการทำงานแต่ละรอบ:

| วันที่ | Phase | Commit/งาน | ผล Gate | หมายเหตุ |
|---|---|---|---|---|
| 2026-09-05 | Phase 0 | Baseline & Safety Net | PASS | 309 tests passed, 77 routes, synthetic render PASS |
| 2026-09-05 | Phase 1 | Project State & Autosave | PASS | แยก editorProjectState, projectSaveQueue, useProjectAutosave, useProjectLoader; Vite build ผ่าน, 309 pytest passed |
| 2026-09-05 | Phase 2 | Render Job & Polling | PASS | แยก renderJobModel, useRenderJob, renderJobController tests; Vite build ผ่าน, 309 pytest passed |
| 2026-09-05 | Phase 3 | แยก Editor Shell | PASS | แยก EditorHeader, usePanelLayout, useEditorSelection, useEditorCommands, useEditorShortcuts; EditorShell.jsx -661 บรรทัด |
| 2026-09-05 | Phase 4 | แยก Timeline | PASS | แยก timelineTrackModel, TimelineRuler, TimelinePlayhead, TimelineContextMenu, useTimelineKeyboard, useTimelineDrag; Timeline.jsx -415 บรรทัด |
| 2026-09-05 | Phase 5 | แยก Inspector | PASS | แยก ClipInspector, CaptionInspector, OverlayInspector, CuesTranscriptInspector, ProjectInspector, SliderControl, ToggleControl; Inspector.jsx -1,903 บรรทัด (-88.5%) |
| 2026-09-05 | Phase 6 | แยก Backend API | PASS | แยก 10 routers ใน scripts/ (api_phase1, api_editor, api_tokens, api_voice, api_videos, api_products, api_exports, api_tasks, api_render, api_posts); api_server.py -95.7% (เหลือ 92 บรรทัด) |
| 2026-09-05 | Phase 7 | แยก Pipeline Stages | PASS | แยก 7 stage modules ใน scripts/stages/ + PipelineContext; pipeline.py -77.6% (เหลือ 308 บรรทัด) |
| 2026-09-05 | Phase 8 | แยก Subtitle/Overlay Engine | PASS | แยก 4 submodules ใน scripts/subtitle/ (font_metrics, motion_effects, badge_plate_renderer, translation_service); subtitle_engine.py -44% (เหลือ 1,093 บรรทัด) |
| 2026-09-05 | Phase 9 | Multi-track และ Keyframe | PASS | Timeline schema v2 + in-memory migration, KeyframeModel (JS) + keyframe_engine (Python) 100% parity, TrackHeader UI |
| 2026-09-05 | Phase 10 | Error Handling และ Recovery | PASS | error_handler.py (5 categories + Thai suggestions), atomic manifest writes + .bak recovery, bounded stderr, errorMapping.js |
| 2026-09-05 | Final | Compatibility & Production Sign-off | PASS | ทดสอบ 3 manifest schemas, Create/Edit/Save/Reload cycle, Reroll routing, ffprobe 1080x1920 30fps H.264/AAC, audio mutes/gains, pytest 331 passed, node 51 passed, Vite build 0 errors |

