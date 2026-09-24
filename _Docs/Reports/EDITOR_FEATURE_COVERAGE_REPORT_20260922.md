# Editor Feature Coverage Report

วันที่: 2026-09-23
ดำเนินการโดย: Codex (GPT-5)  
แหล่งข้อมูล: `EDITOR_FEATURE_COVERAGE_MATRIX_20260922.json`

## ผลรวม

| สถานะ | จำนวน | ความหมาย |
| --- | ---: | --- |
| PASS | 13 | consumer chain และ automated evidence ครบ ไม่มี blocker ที่ทราบ |
| APPROXIMATION | 6 | Preview มีข้อจำกัดที่ต้องเปิดเผยต่อผู้ใช้ |
| BLOCKED | 0 | ไม่มี contract conflict ที่ยังเปิดอยู่ |
| UNTESTED | 1 | มีเส้นทางโค้ดครบ แต่ยังขาด production-path behavioral gate |
| รวม | 20 | ครบทุก feature family ใน Master Plan |

`PASS + APPROXIMATION` ไม่ได้หมายความว่า Editor สมบูรณ์แล้ว โดยเฉพาะ `APPROXIMATION` ต้องมีข้อความแจ้งผู้ใช้ตาม policy ใน matrix ก่อน release

## Coverage ปัจจุบัน

| Feature | Readiness | หมายเหตุสำคัญ |
| --- | --- | --- |
| Project lifecycle | PASS | Save/autosave/reload และ queue มี regression |
| Timeline editing | PASS | EditorShell เพิ่มคลิป/ผ่าคลิป/เลือก fade ผ่าน UI จริง + reorder/Undo/Redo → Save/Reload → Canvas/Render ผ่าน 18 เฟรม; drag snap/delete มี browser gate แยก |
| Clip timing | PASS | live Canvas-vs-Render trim/speed/freeze หลายช่วงเวลา และ Save/Reload ผ่าน |
| Clip transform | PASS | live static/keyframed zoom/pan, rotation/mirror และ Save/Reload ผ่าน |
| Clip framing | PASS | live fill/blur และ blur หลัง rotation ผ่าน; UI มี fill/blur ไม่ได้มี fit แบบแยก |
| Clip color | APPROXIMATION | Canvas brightness multiplier ต่างจาก FFmpeg additive offset |
| Transitions | APPROXIMATION | dissolve PRNG และ bridge easing ไม่ pixel-identical |
| Captions | PASS | live Canvas-vs-libass matrix `4/4` ผ่าน Thai/English/ตัวเลข/1–3 บรรทัด; explicit newline และ Save/Reload มี regression |
| Motion Text | PASS | strict live frame-pair `16/16` ผ่าน IoU/bbox/centroid/NMAE; app capture `7/7`, save/reload และ preset contract มี regression |
| Stickers | PASS | live Canvas-vs-production pair ผ่านใน ROI ของ sticker, พร้อม timing/geometry Save/Reload regression |
| Effects | PASS | live Canvas-vs-production pair ผ่านสำหรับ effect assets จริง 2 แบบ พร้อม decode/loop และ Save/Reload regression |
| Spotlight | PASS | live ellipse + dim + feather Canvas-vs-production pair ผ่าน พร้อม z-order/timing และ Save/Reload regression |
| Background Isolation | APPROXIMATION | ใช้เฉพาะ Timeline window, block silent fallback, prefetch/cache/cancel พร้อม; temporal mask ยังขึ้นกับ footage/model |
| LUT | APPROXIMATION | browser ที่ไม่มี WebGL2 แสดงสีจริงไม่ได้ |
| Clip audio | APPROXIMATION | Preview playbackRate อาจเปลี่ยน pitch ต่างจาก atempo |
| Audio mix | APPROXIMATION | loudnorm/sidechaincompress ทำเหมือนใน browser ไม่ได้ |
| Track mute/solo | PASS | Preview/Save/Reload/Export ใช้ effective mute เดียวกัน; clip bus mute ไม่เขียนทับ slider |
| Export job control | PASS | job identity, stale guard และ polling มี regression |
| Reliability/recovery | PASS | disk-full, missing source, cancel, network retry, FFmpeg error cleanup และ kill โปรเซส render worker จริง → restart → task/project state recovery ผ่านใน fixture แยกข้อมูล |
| Editor UX controls | UNTESTED | Chromium Inspector/Timeline keyboard/focus บางส่วนผ่าน แต่ยังไม่ครบทุก Inspector/dialog/screen reader |

## Phase 4 Vertical Slice Evidence

- Caption: live Canvas-vs-libass `4/4` และ Save/Reload ผ่าน
- Sticker: live Canvas-vs-production `1/1` ผ่าน strict ROI gate; source image decode, timing และ geometry ผ่าน
- Effect: live Canvas-vs-production `2/2` ผ่านจาก `.webm` จริง; video decode/loop, timing และ geometry ผ่าน
- Spotlight: live Canvas-vs-production `1/1` ผ่าน full-frame mask/feather gate; z-order/timing ผ่าน
- Motion/Caption regression: `test_frame_pair.py` `20 passed`; app capture + overlay `11 passed`
- Backend full รอบล่าสุด 2026-09-23: `1,776 passed, 7 skipped, 34 warnings`; targeted Chromium ที่เพิ่มหลัง collection ผ่าน
- Frontend ล่าสุด: `311 passed`; `npm run build` ผ่าน

## Phase 4 ต่อเนื่อง — Timeline, Clip และ Track Mix

- เพิ่ม live Production Canvas-vs-FFmpeg gate สำหรับ trim/speed/freeze, static/keyframed zoom/pan, rotation/mirror, fill/blur, cut boundary และ fade overlap; motion-capture run ผ่าน `54` รายการ (รายการ coverage assertion ที่รันระหว่างอัปเดต matrix ต้องรันยืนยันใหม่ และผ่านแล้ว)
- FFmpeg dynamic crop เดิมใช้ `iw/ih` ที่ผูกกับขนาดเริ่มต้นของ filtergraph ทำให้คีย์เฟรม zoom เลื่อนตำแหน่ง; เปลี่ยนไปใช้ขนาด scale ตาม zoom ของแต่ละเฟรม
- พื้นหลังเบลอฝั่ง Render เดิมใช้ `boxblur` ขอบและความเข้มไม่ตรง Canvas; เปลี่ยนเป็น padded Gaussian blur ที่วัด NMAE ลดจากประมาณ `0.0273` เป็น `0.0174` และ mask IoU จาก `0.7166` เป็น `1.0` ใน fixture ที่ใช้ปรับค่า
- Mute/Solo มีผลทั้ง Preview และ Export แล้ว; เมื่อเปลี่ยน mix ต้องสร้าง audio artifact ใหม่ และ clip bus mute ใช้ render-only copy จึงไม่เปลี่ยนค่าระดับเสียงที่บันทึกไว้
- การโหลด `.env` ของ Gemini TTS ไม่เขียนทับ process environment อีก จึงไม่เปิด API key gate ผิดพลาดระหว่าง import; Export ไม่เดินต่อถ้า save ล้ม และ baseline ของ render ปรับหลัง job สำเร็จ
- จำลอง ENOSPC ระหว่างเขียน manifest แล้วตรวจว่าฉบับล่าสุดยังอยู่และไฟล์ชั่วคราวถูกเก็บกวาด
- APPROXIMATION ทั้ง 6 หมวดมีข้อความอธิบายใน UI และ validator ตรวจ source evidence ของข้อความนั้นจริง
- เพิ่ม Chromium browser gates `5/5` สำหรับ ClipInspector, Timeline และ missing media: numeric edit, keyboard reorder, split/delete, drag-to-add, trim drag snap, Undo/Redo, Save/Reload, pressed/focus state และ error alert; ต่อผ่าน EditorShell จริงแล้วตามหลักฐาน `18/18` เฟรมด้านล่าง
- เพิ่ม worker fault gates สำหรับ disk probe/space, missing source และ cancel; frontend poll แยก 401/404 จาก transient network error; `check_disk_space()` เดิม probe ล้มแล้วอนุญาต Render ต่อ ตอนนี้ fail-closed ด้วย 507 และข้อความสาเหตุที่ชัด
- Performance probe ที่ Timeline 1/10/50/100 clips ผ่าน: Chromium fixture mount `464/452/434/553 ms`, selection `61/71/88/114 ms`, JS heap `27.6/27.6/29.4/33.1 MB` ตามลำดับบนเครื่องทดสอบรอบนี้
- เพิ่ม workload ที่เปิดไฟล์วิดีโอจริง (source เดียวซ้ำ 1/10/50/100 clips): Preview seek ไปคลิปท้าย `35/50/675/1998 ms`, decoded frames `49/30/30/31`, dropped frames `0/0/0/0`, heap ล่าสุด `29.4/29.4/35.1/35.1 MB`; FFmpeg Render `0.51/1.25/3.39/7.04 s` และ ffprobe duration `0.1/1/5/10 s` ตรงไทม์ไลน์ทั้งหมด ข้อมูลนี้วัดใน synthetic fixture ไม่ใช่คำรับรองกับ media/codec ที่หลากหลาย
- แก้ Inspector numeric trim ให้ไม่ย้อนหน้าต่าง source หรือเกินความยาวไฟล์; unit + Chromium gate ทดสอบกรอกค่าเกินจริงแล้ว clamp ตามสัญญา `MIN_CLIP_DURATION`
- Missing media ใน Preview ไม่ค้างเป็นภาพดำ/Loading แบบไร้คำอธิบายอีก: แสดงข้อความ `role=alert` พร้อมชื่อไฟล์และแนวทางแก้; Chromium error-media gate ผ่าน
- EditorShell จริง: กรณี 2 คลิปสลับลำดับด้วย keyboard แล้ว Undo/Redo/Undo ก่อนเปลี่ยน Trim เข้าเป็น 0.5s → Save ผ่าน API จำลอง → Reload → seek ในกรณีคลิปเดียวที่ 0.0/0.6/1.2s และกรณี fade overlap ที่ 0.0/0.35/0.5/0.7/1.2s → จับ Canvas/เทียบ FFmpeg จาก state ที่บันทึก ผ่าน `8/8` เฟรม; ใช้ source/ไฟล์ทดสอบใน temp เท่านั้น
- เส้นทาง manual Render เคยใช้ auto punch zoom `1.25` เมื่อ clip ไม่ระบุ `zoom` ทั้งที่ Preview ตีความเป็น `1.0`: repro ก่อนแก้ bbox ต่าง `24px` และ parity fail; หลังแก้ fallback เป็น `1.0` เมื่อไม่มี `shot_scales` ที่ระบุชัด ภาพผ่านทั้งสามช่วงเวลา โดย preset explicit และ 1-Click path คงเดิม
- Regression หลังแก้: `test_editor_shell_browser.py` + `test_clip_frame_pair.py` + `test_phase1_smoke.py` ผ่าน `168 passed, 5 warnings`; รอบยืนยันสุดท้าย EditorShell + coverage validator tests `8 passed`; `compileall`, coverage validator (`20` feature families) และ `git diff --check` ผ่าน ทั้งนี้ยังไม่ได้รัน full backend suite ซ้ำหลังแก้หนึ่งบรรทัดนี้
- Recovery gate เพิ่ม: จำลอง worker ได้ FFmpeg error แล้ว `render_jobs`/TaskManager เป็น `failed` ทั้งคู่; ล้างสถานะในหน่วยความจำให้เหมือน restart แล้ว `get_render_status()` ยังคืน `failed` จาก registry ชั่วคราว; ชุด failure/cleanup/task-manager ร่วมกันผ่าน `40/40` และทดสอบ nonzero-exit cleanup ของ FFmpeg มีอยู่ใน `test_render_timeout_cleanup.py`
- Timeline end-to-end ขยายเป็น `4` browser scenarios / `18` FFmpeg frame comparisons: กรณี trim 3, เลือก fade หลังเพิ่มคลิปผ่าน AssetPanel 5, fade บนจอ compact 1024×768 อีก 5, และผ่าคลิปก่อน/หลัง boundary 5; ทั้งหมด Save/Reload และใช้ state เดียวกัน Preview/Render ผ่าน รวม reorder/Undo/Redo ใน flow จริง
- แก้เมนู transition ที่ก่อนแก้เปิดขึ้นใน Timeline แต่ถูก Preview ครอบจนคลิกไม่ได้: ย้าย popover ไปแสดงที่ document layer พร้อมตำแหน่ง clamp ตาม viewport, จำกัดความสูง/scroll, `aria-expanded`/dialog, Escape และคืน focus ให้ปุ่ม; browser repro ล้มก่อนแก้และผ่านหลังแก้
- Gate ล่าสุดหลังเปลี่ยน UI: Chromium EditorShell/controls/coverage `15 passed`; frontend `311 passed`; Vite build ผ่าน; design detector ไม่พบข้อเตือน (`[]`)
- Recovery end-to-end ใหม่: โปรเซสลูกเข้าทาง `execute_render_job()` จริงแล้วถูก terminate ระหว่าง pipeline; หลัง TaskManager restart สถานะ job เป็น `failed`, มุมงานกลับ `scripted` และ `project_name` ถูกล้าง แม้มี partial `project.json` ค้าง; ก่อนแก้ assertion pointer ล้ม แก้ `TaskManager` ให้ล้างเหมือน failure handler ปกติ; targeted recovery `19 passed`
- UX ที่ตรวจเพิ่ม: Preview play/pause และ scrub slider มี accessible name, ปุ่มเปิด/ปิดเสียงคลิปและ volume slider มีชื่อสำหรับ screen reader; browser audit ของ visible controls ใน ClipInspector/Timeline fixture ผ่านหลังแก้ slider ที่ไม่มีชื่อ แต่ยังไม่ครบทุก Inspector/dialog จึงคง `UNTESTED`
- Gate รอบล่าสุด: Chromium controls/EditorShell/performance/coverage `28 passed`; frontend `311 passed`, production build ผ่าน; targeted backend render/recovery/reroll/schedule `66 passed` และ recovery fault tests `19 passed` ชุด backend ทั้งหมดที่เริ่มรันใหม่ถูกขัดจังหวะก่อนจบ จึงไม่อ้างว่า full suite รอบนี้ผ่าน (baseline ก่อนหน้า `1,776 passed, 7 skipped`)

Sticker comparison ใช้ ROI เฉพาะบริเวณ sticker เพื่อไม่ให้ source-video codec noise นอก overlay ถูกนับเป็น defect ของ overlay; Effect และ Spotlight ใช้ full-frame comparison

## Defect ที่แก้แล้ว

`SpotlightV1` เคยถูก Preview และ Save ได้ แต่ `EditorShell` ไม่ส่ง `spotlight` ใน request ตอน Render ทั้งที่ backend และ `video_editor.py` รองรับอยู่แล้ว รอบนี้เพิ่ม `serializeRenderFeatures()` เป็น transport contract กลางสำหรับ stickers, effects, spotlight และ background isolation พร้อม regression test

รอบนี้พบและแก้ Preview/Render drift ของ Sticker และ Effect: geometry ฝั่ง Render เคยคำนวณบน draft profile dimensions ทั้งที่ FFmpeg กำลัง composite บน working raster `1080x1920` ทำให้ขนาดและตำแหน่งไม่ตรง Canvas แก้ให้ overlay geometry ใช้ working raster เดียวกันก่อน final downscale และเพิ่ม live frame-pair fixture ที่รอ asset decode/seek จริงแบบ deterministic

Background Isolation เคยประมวลผลตั้งแต่ source time `0` ถึง EOF แม้ Timeline ใช้เพียงไม่กี่วินาที และ Preview/Render fallback เป็นภาพเดิมแบบเงียบ รอบ Phase 2 เปลี่ยนเป็น window artifact ที่บันทึก `source_start/source_duration`, แยก cache key ต่อช่วง, preflight runtime/model/disk, progress/cancel/retry, bounded prefetch และ block Render เมื่อ artifact ไม่พร้อมหรือชนกับพื้นหลังเบลอ หลักฐาน live probe ด้วย `u2net` ให้ alpha `0..255`, composite NMAE `0.0`, max delta `0` และ source hash ไม่เปลี่ยน

## Gate ที่เพิ่ม

คำสั่งตรวจ:

```powershell
.\.venv\Scripts\python.exe -m tools.editor_feature_coverage
.\.venv\Scripts\python.exe -m pytest tests/test_editor_feature_coverage.py -q -p no:cacheprovider
```

Validator จะ fail เมื่อ:

- canonical clip field ไม่มี feature owner หรือถูก claim ซ้ำ
- rendered feature ขาด UI/state/persistence/render payload/Preview/Render consumer
- source path หรือ token หลักฐานไม่อยู่จริง
- `PASS` ยังมี blocker
- `APPROXIMATION` ไม่มีเหตุผลหรือ UI disclosure policy
- `BLOCKED/UNTESTED` ไม่อธิบายช่องว่าง

## ลำดับถัดไป

Phase 2 ปิดช่องว่างเชิงการใช้งานของ Background Isolation แล้ว แต่ยังขาด real-footage edge/temporal matrix ตาม Master Plan และคง `APPROXIMATION`; Phase 3 ปิด Motion Text parity; Phase 4 ปิด Caption/Sticker/Effect/Spotlight, clip timing/transform/framing, track mute/solo และ Timeline end-to-end แล้ว recovery fault matrix ปิดด้วย process-kill/restart test Performance synthetic media 1/10/50/100 clips ผ่านแล้ว งานที่ยังห้ามเรียกว่าเสร็จคือ Editor UX/accessibility browser matrix, approximation ทั้ง 6 หมวด และการยืนยันกับ footage จริงที่หลากหลาย
