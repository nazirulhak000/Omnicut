# OmniCut Pro Studio — Safe Refactor Plan

เอกสารนี้เป็นแผน Refactor แบบค่อยเป็นค่อยไปสำหรับ OmniCut Pro Studio โดยมีเป้าหมายให้ระบบใช้งานจริงได้ตลอดเวลา ทุกขั้นต้องย้อนกลับได้ และห้ามทำให้โปรเจกต์เก่า Preview หรือ Export เปลี่ยนพฤติกรรมโดยไม่ตั้งใจ

## สถานะรวม

- [x] Phase 0 — Baseline และ Safety Net
- [x] Phase 1 — Project State และ Autosave
- [ ] Phase 2 — Render Job และ Polling
- [ ] Phase 3 — แยก Editor Shell
- [ ] Phase 4 — แยก Timeline
- [ ] Phase 5 — แยก Inspector
- [ ] Phase 6 — แยก Backend API
- [ ] Phase 7 — แยก Pipeline Stages
- [ ] Phase 8 — แยก Subtitle/Overlay Engine
- [ ] Phase 9 — Multi-track และ Keyframe
- [ ] Phase 10 — Error Handling และ Recovery
- [ ] Final — Compatibility และ Production Sign-off

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

- [ ] แยก Render Job controller/hook
- [ ] ย้าย polling ออกจาก Editor Shell
- [ ] รวม interval cleanup ไว้จุดเดียว
- [ ] ผูก response กับ job ID และ project ID
- [ ] ป้องกัน job เก่าเปลี่ยน state โปรเจกต์ใหม่
- [ ] แยก Progress/ETA calculation
- [ ] แยก Success/Failure mapping
- [ ] เพิ่ม test unmount ระหว่าง polling
- [ ] เพิ่ม test refresh ระหว่าง Render
- [ ] เพิ่ม test backend restart ระหว่าง polling
- [ ] ลบ polling เดิมหลังเส้นทางใหม่ผ่าน

### Gate

- [ ] ไม่มี interval ค้างหลังออกจาก Editor
- [ ] ไม่มี polling ซ้ำหลังเข้าออกหลายครั้ง
- [ ] Refresh แล้วกลับมาติดตาม job เดิมได้
- [ ] Job เก่าไม่เขียนทับโปรเจกต์ใหม่
- [ ] Error แสดงต่อผู้ใช้และมี log อ้างอิงได้

### Notes

- วันที่ผ่าน Gate:
- หลักฐาน/ผลทดสอบ:
- ข้อยกเว้น:

---

## Phase 3 — แยก Editor Shell

เป้าหมาย: ให้ Editor Shell ทำหน้าที่ประกอบ UI และประสาน controller เท่านั้น

### Todo แบบ commit เล็ก

- [ ] แยก Desktop layout
- [ ] แยก Mobile layout
- [ ] แยก Preview workspace
- [ ] แยก Project header/status
- [ ] แยก panel resize state
- [ ] แยก Selection controller
- [ ] แยก Clip commands
- [ ] แยก Caption commands
- [ ] แยก Overlay commands
- [ ] วัด render count ก่อนและหลัง
- [ ] ลด props ที่ส่งต่อหลายชั้น
- [ ] ลบ implementation เดิมหลัง behavior tests ผ่าน

### Gate

- [ ] UI Desktop และ Mobile ทำงานเท่าเดิม
- [ ] Keyboard shortcuts เท่าเดิม
- [ ] Selection, Split, Duplicate และ Delete เท่าเดิม
- [ ] Autosave และ Render payload ไม่เปลี่ยน
- [ ] Editor Shell ไม่มี business logic ซ้ำกับ hooks ที่แยกแล้ว

### Notes

- วันที่ผ่าน Gate:
- หลักฐาน/ผลทดสอบ:
- ข้อยกเว้น:

---

## Phase 4 — แยก Timeline

เป้าหมาย: แยกการวาด Timeline ออกจาก interaction และ timeline math

### Todo แบบ commit เล็ก

- [ ] แยก Track geometry/layout model
- [ ] แยก Timeline ruler
- [ ] แยก Video lane
- [ ] แยก Overlay lanes
- [ ] แยก Audio lanes
- [ ] แยก Playhead
- [ ] แยก Context menu
- [ ] แยก Pointer drag controller
- [ ] แยก Keyboard controller
- [ ] รวม global listener cleanup
- [ ] เพิ่ม test Drag/Reorder
- [ ] เพิ่ม test Trim
- [ ] เพิ่ม test Split + Freeze
- [ ] เพิ่ม test Transition clamp
- [ ] เพิ่ม test Ripple behavior
- [ ] เพิ่ม test Snap behavior
- [ ] ลบ implementation เดิมหลังผ่าน

### Gate

- [ ] เวลารวมก่อนและหลัง Refactor เท่ากัน
- [ ] Preview time และ Render time เท่ากัน
- [ ] Drag/Trim/Split/Transition ผ่านทั้งหมด
- [ ] Undo/Redo ผ่านทุกคำสั่งที่ย้าย
- [ ] ไม่มี event ถูกเรียกซ้ำหลัง mount/unmount หลายรอบ

### Notes

- วันที่ผ่าน Gate:
- หลักฐาน/ผลทดสอบ:
- ข้อยกเว้น:

---

## Phase 5 — แยก Inspector

เป้าหมาย: ให้แต่ละชนิด selection มี panel และ validation ของตัวเอง

### Todo แบบ commit เล็ก

- [ ] แยก Clip Inspector
- [ ] แยก Caption Inspector
- [ ] แยก Overlay Inspector
- [ ] แยก Audio Inspector
- [ ] แยก Project Inspector
- [ ] สร้าง Slider control กลาง
- [ ] สร้าง Toggle control กลาง
- [ ] รวม numeric validation/clamping
- [ ] รวม patch/update helper
- [ ] เพิ่ม component tests สำหรับ control สำคัญ

### Gate

- [ ] ค่าเดิมแสดงเหมือนเดิม
- [ ] ทุก control แก้เฉพาะ field ที่ตั้งใจ
- [ ] Reset ไม่ลบ field อื่น
- [ ] Inspector ไม่ถือ state ซ้ำกับ Editor document
- [ ] Preview และ Render รับค่าเดียวกัน

### Notes

- วันที่ผ่าน Gate:
- หลักฐาน/ผลทดสอบ:
- ข้อยกเว้น:

---

## Phase 6 — แยก Backend API

เป้าหมาย: ให้ไฟล์สร้าง FastAPI app เหลือเฉพาะ configuration และ router mounting โดยรักษา API เดิม

### Todo แบบ commit เล็ก

- [ ] บันทึก route table ปัจจุบันเป็น contract fixture
- [ ] แยก Pydantic schemas
- [ ] แยก Video library routes
- [ ] แยก Upload routes
- [ ] แยก Export routes
- [ ] แยก Voice routes
- [ ] แยก Product routes
- [ ] แยก Task routes
- [ ] แยก Render routes
- [ ] แยก file metadata service
- [ ] แยก path validation service
- [ ] แยก background render worker
- [ ] ตรวจ route table ก่อน/หลัง
- [ ] ลบโค้ดเดิมหลัง router ใหม่ผ่าน contract tests

### Gate

- [ ] URL, method และ response shape เดิมครบ
- [ ] Payload เดิมไม่เกิด 422 เพิ่ม
- [ ] Error code และข้อความสำคัญไม่เปลี่ยนโดยไม่ตั้งใจ
- [ ] Backend เปิดด้วยคำสั่งเดิม
- [ ] Upload/stream/range request ผ่าน
- [ ] Render และ Task status ผ่าน

### Notes

- วันที่ผ่าน Gate:
- หลักฐาน/ผลทดสอบ:
- ข้อยกเว้น:

---

## Phase 7 — แยก Pipeline Stages

เป้าหมาย: แยก orchestration ออกจากรายละเอียดแต่ละขั้น และให้ Full Render/Reroll ใช้ stage เดียวกัน

### Todo แบบ commit เล็ก

- [ ] เพิ่ม Pipeline Context โดยยังไม่เปลี่ยน flow
- [ ] แยก Source Resolution stage
- [ ] แยก Script stage
- [ ] แยก Voice stage
- [ ] แยก Subtitle stage
- [ ] แยก Audio Mix stage
- [ ] แยก AI Shot Matching stage
- [ ] แยก Video Assembly stage
- [ ] แยก Manifest Persistence stage
- [ ] กำหนด input/output ของแต่ละ stage
- [ ] ทำให้ Reroll ใช้ stage เดียวกับ Full Render
- [ ] ลบ branch ซ้ำ
- [ ] เพิ่ม stage-level failure reporting

### Gate

- [ ] Full Render ให้ artifacts เท่าเดิม
- [ ] Reroll รันเฉพาะ stage ที่จำเป็น
- [ ] ไม่มีการสร้าง Voice/Mix ซ้ำโดยไม่จำเป็น
- [ ] Manifest เขียนครบหลังทุกเส้นทางสำเร็จ
- [ ] Failure ระบุ stage และ project ได้
- [ ] ยกเลิกงานได้ที่ stage boundary

### Notes

- วันที่ผ่าน Gate:
- หลักฐาน/ผลทดสอบ:
- ข้อยกเว้น:

---

## Phase 8 — แยก Subtitle/Overlay Engine

เป้าหมาย: ลดความเสี่ยง Preview ไม่ตรง Render โดยมี geometry/motion contract ที่ตรวจได้

### Todo แบบ commit เล็ก

- [ ] แยก constants และ geometry model
- [ ] แยก font metrics
- [ ] แยก ASS color/alpha conversion
- [ ] แยก Caption layout
- [ ] แยก Hook layout
- [ ] แยก Overlay layout
- [ ] แยก Motion builders
- [ ] แยก ASS document writer
- [ ] ให้ parity tests เรียก geometry model โดยตรง
- [ ] สร้าง Render fixture สำหรับฟอนต์ไทย
- [ ] ตรวจเฟรมช่วงเข้า/ค้าง/ออก
- [ ] วัดตำแหน่งและขนาดด้วยพิกเซล
- [ ] บันทึกข้อยกเว้นที่เทียบแบบ pixel-perfect ไม่ได้

### Gate

- [ ] Preview parity tests ผ่าน
- [ ] FFmpeg render ผ่านพร้อม fontsdir
- [ ] Hook/Caption/Overlay มีตำแหน่งและขนาดตรงตาม tolerance
- [ ] Motion ถูกทิศและช่วงเวลาเดียวกัน
- [ ] สี Alpha Outline และ Rotation ผ่าน
- [ ] โปรเจกต์จริงอย่างน้อยหนึ่งงาน Export แล้วตรวจภาพครบ

### Notes

- วันที่ผ่าน Gate:
- หลักฐาน/ผลทดสอบ:
- ข้อยกเว้น:

---

## Phase 9 — Multi-track และ Keyframe

เป้าหมาย: เพิ่มความยืดหยุ่นแบบโปรแกรมตัดต่อโดยไม่ทำลาย schema เก่า

### Todo แบบ commit เล็ก

- [ ] กำหนด Timeline Document schema รุ่นใหม่
- [ ] เพิ่ม schema version
- [ ] เพิ่ม migration ในหน่วยความจำสำหรับโปรเจกต์เก่า
- [ ] ห้ามเขียน schema ใหม่ทับไฟล์เก่าจนกว่าผู้ใช้บันทึก
- [ ] เพิ่ม Video Track model
- [ ] เพิ่ม Audio Track model
- [ ] เพิ่ม Overlay Track model
- [ ] เพิ่ม Lock/Mute/Visibility
- [ ] เพิ่ม clip placement ด้วยเวลาเริ่ม
- [ ] เพิ่ม Link/Unlink ภาพและเสียง
- [ ] เพิ่ม Multi-select
- [ ] เพิ่ม Ripple/Gap modes
- [ ] เพิ่ม Keyframe track model
- [ ] ใช้ interpolation contract ที่มี Regression tests
- [ ] ทำ Zoom/Pan ใน Preview หลัง Feature flag
- [ ] ทำ Zoom/Pan ใน Render ด้วยสูตรเดียวกัน
- [ ] เพิ่ม Opacity keyframe
- [ ] เพิ่ม Volume keyframe
- [ ] เพิ่ม frame-based parity tests
- [ ] เปิดใช้กับโปรเจกต์ทดสอบ
- [ ] เปิดเป็นค่าเริ่มต้นหลัง Compatibility gate ผ่าน

### Gate

- [ ] โปรเจกต์ schema เก่าเปิดได้โดยผลภาพเดิม
- [ ] ปิด Feature flag แล้ว behavior เหมือนเวอร์ชันเดิม
- [ ] หลายแทร็กแสดง z-order ตรงกันใน Preview/Render
- [ ] Keyframe ตรงกันที่จุดเริ่ม กลาง และท้าย
- [ ] Mute/Lock/Visibility บันทึกและโหลดกลับได้
- [ ] Undo/Redo รองรับคำสั่งใหม่
- [ ] Export โปรเจกต์หลายแทร็กสำเร็จ

### Notes

- วันที่ผ่าน Gate:
- หลักฐาน/ผลทดสอบ:
- ข้อยกเว้น:

---

## Phase 10 — Error Handling และ Recovery

เป้าหมาย: ลด silent failure และทำให้กู้สถานะได้เมื่อ Backend, AI หรือ FFmpeg ล้มเหลว

### Todo แบบ commit เล็ก

- [ ] จัดหมวด user-correctable errors
- [ ] จัดหมวด FFmpeg errors
- [ ] จัดหมวด AI provider errors
- [ ] เปลี่ยน `except pass` จุดสำคัญเป็น structured logging
- [ ] ใส่ project/job identifier ใน log
- [ ] จำกัดขนาด stderr ที่เก็บ
- [ ] เพิ่ม timeout ที่ subprocess สำคัญ
- [ ] เพิ่ม cancellation ที่ stage boundary
- [ ] เพิ่มข้อความแก้ปัญหาภาษาไทยใน UI
- [ ] เพิ่ม Recovery test หลัง Backend restart
- [ ] เพิ่ม test ไฟล์ต้นทางหาย/เสีย
- [ ] เพิ่ม test disk เต็มหรือเขียน Manifest ไม่สำเร็จ

### Gate

- [ ] ไม่มี silent failure ใน Save/Render/Upload ที่สำคัญ
- [ ] Error ทุกชนิดบอก project/job ได้
- [ ] งานล้มเหลวไม่ทำให้ Manifest ครึ่งไฟล์
- [ ] Restart แล้วสถานะงานไม่หลอกว่าเสร็จ
- [ ] ผู้ใช้ลองใหม่ได้โดยไม่ต้องลบโปรเจกต์

### Notes

- วันที่ผ่าน Gate:
- หลักฐาน/ผลทดสอบ:
- ข้อยกเว้น:

---

## Final Compatibility และ Production Sign-off

- [ ] เปิดโปรเจกต์เก่าอย่างน้อย 3 รูปแบบ
- [ ] Create → AI Draft → Edit → Save → Reload ผ่าน
- [ ] Reroll Hook ผ่าน
- [ ] Reroll Subtitle ผ่าน
- [ ] Reroll BGM ผ่าน
- [ ] Full Export 1080×1920, H.264, 30 FPS ผ่าน
- [ ] ตรวจ `ffprobe` ของไฟล์จริง
- [ ] Preview = Render ผ่านการดูและวัดหลายเฟรม
- [ ] เสียง Voice/BGM/SFX/Clip ตรงกับ Mute และ Volume
- [ ] ไม่มี timer/listener ค้างหลังเปิดปิด Editor หลายรอบ
- [ ] Frontend production build ผ่าน
- [ ] Python compile/import ผ่าน
- [ ] Test suite ที่กำหนดผ่านทั้งหมด
- [ ] บันทึก Known limitations
- [ ] บันทึก Rollback procedure
- [ ] ผู้ใช้ตรวจงานจริงและอนุมัติเปิด Feature flag

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
