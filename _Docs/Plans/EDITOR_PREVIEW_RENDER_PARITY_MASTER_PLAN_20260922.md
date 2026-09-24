# Editor Full-Function & Preview–Render Parity Master Plan

วันที่: 2026-09-22  
ดำเนินการโดย: Codex (GPT-5)  
สถานะ: Phase 4 overlay + clip visual + Timeline vertical slices และ Render recovery ผ่านแล้ว; Master ยัง active เพราะ UX และ performance ยังไม่ผ่านครบ

อัปเดต 2026-09-23 โดย Codex (GPT-5): coverage `PASS 13 / APPROXIMATION 6 / BLOCKED 0 / UNTESTED 1`; backend full รอบล่าสุด `1,776 passed, 7 skipped`, frontend `311 passed`, build/validator ผ่าน รายละเอียดและหลักฐานล่าสุดอยู่ใน `_Docs/Reports/EDITOR_FEATURE_COVERAGE_REPORT_20260922.md` ห้ามใช้ readiness เก่าด้านล่างเป็นสถานะปัจจุบัน

อัปเดตต่อ: EditorShell เพิ่มคลิป/ผ่าคลิป/เลือก fade ผ่าน UI + reorder/Undo/Redo → Save/Reload → Preview Canvas เทียบ FFmpeg ผ่าน `18/18` เฟรม; Timeline `PASS`; Render worker process-kill → restart → task/project recovery ผ่าน; UX ยัง `UNTESTED`

## สถานะการดำเนินงาน

### Phase 0 — Parity Harness: เสร็จแล้ว (2026-09-22)

- pytest เปิด Vite/React fixture เองบน loopback port แบบสุ่ม ไม่ต้องตั้ง `MOTION_CAPTURE_APP_URL`
- จับเฟรมจริงจาก `SequencePlayer` ด้วย explicit frame indices จึงไม่พึ่ง wall clock
- manifest บันทึก browser version, console errors, page errors และ request failures; runtime error ทำให้ test fail
- frame pair เขียน Canvas, FFmpeg/libass, absolute diff, heatmap และ foreground masks ใต้ `.tmp/`
- lifecycle test ยืนยันว่า Vite process/port ถูกปิด และ temporary artifacts ถูก cleanup
- strict gate `python -m tests.motion_capture.run_live_gate` ไม่ skip และคืน exit code `1` ตาม defect จริง
- หลักฐานปัจจุบัน: identity ตรง, runtime สะอาด, แต่ Motion Text ยัง `blocked` ด้วย mask IoU `0.1813699` และ bbox edge delta `22 px`

Phase 0 สำเร็จเพราะตรวจจับความต่างได้อย่าง deterministic ไม่ได้หมายความว่า Motion Text parity ผ่านแล้ว

### Phase 1 — State/Renderer Coverage Matrix: เสร็จแล้ว (2026-09-22)

- เพิ่ม matrix แบบ machine-readable ครบ 20 feature families และ canonical render clip fields 15 fields
- validator ตรวจ consumer chain `UI → state → persistence → render payload → Preview → Render` จาก source token จริง
- readiness ปัจจุบัน: `PASS 2`, `APPROXIMATION 5`, `BLOCKED 3`, `UNTESTED 10`
- แก้ defect Spotlight ที่ Save/Preview ได้แต่ render request ไม่ได้ส่ง `spotlight`
- เพิ่ม transport contract `serializeRenderFeatures()` สำหรับ sticker/effect/spotlight/background isolation
- พบ contract conflict ใหม่: track mute/solo ถูกระบุว่า playback-only ในกฎ แต่ Editor ส่ง `audio_mutes` เข้า Render จึงจัดเป็น `BLOCKED` จนกว่าจะตัดสิน policy
- รายละเอียด: `_Docs/Reports/EDITOR_FEATURE_COVERAGE_REPORT_20260922.md`

### Phase 2 — Background Cutout: เส้นทางใช้งานหลักเสร็จแล้ว (2026-09-22)

- เปลี่ยนจาก full-source เป็น disjoint Timeline windows และบันทึก `source_start/source_duration` ใน manifest
- cache/request identity รวม source fingerprint, window, rotation, model, quality, dimensions, fps และ timebase
- เพิ่ม preflight runtime/model/disk, estimate จำนวนช่วง/วินาที/เฟรม, progress, cancel และ retry
- conflict กับ `bg_blur`/`fit_mode=blur` ถูกแจ้งก่อนเริ่ม และ Render block เมื่อ artifact ไม่พร้อมแทน silent fallback
- Preview prefetch ล่วงหน้าแบบ bounded cache; Preview/Render ลบ window origin และเลือก frame index ด้วยสัญญาเดียวกัน
- live probe ใช้ `u2net` กับวิดีโอจริง: alpha `0..255`, Preview-vs-FFmpeg NMAE `0.0`, max delta `0`, source hash ไม่เปลี่ยน และ cleanup 100%
- ตัดสินใจไม่สร้าง Draft artifact คนละความละเอียด เพราะจะทำให้ Preview ใช้คนละ artifact กับ Render; window processing ลดต้นทุนโดยยังรักษา single-artifact parity
- temporal smoothing ไม่ถูกบังคับใช้ เพราะการ blend mask ข้ามเฟรมทำให้เกิด ghost edge กับวัตถุเคลื่อนที่ได้ ฟังก์ชันจึงอยู่สถานะ `APPROXIMATION` พร้อมข้อความให้ตรวจมือ/วัตถุโปร่งใส/motion blur ก่อน Render

readiness ปัจจุบันหลัง Phase 2: `PASS 2`, `APPROXIMATION 6`, `BLOCKED 2`, `UNTESTED 10`

## 1. เป้าหมาย

ทำให้ทุกฟังก์ชันในหน้าตัดต่อผ่านเส้นทางเดียวกันครบวงจร:

`คำสั่งผู้ใช้ → state กลาง → Preview → Save/Reload → Render → ไฟล์ส่งออก`

คำว่า “เสร็จ” หมายถึงผู้ใช้กดใช้งานได้จริง เห็นผลทันที บันทึกแล้วไม่หาย เรนเดอร์แล้วผลตรงกับ Preview มีข้อความผิดพลาดที่แก้ต่อได้ และมี regression test ป้องกันการพังซ้ำ

## 2. ข้อสรุปจากการตรวจรอบนี้

### 2.1 สิ่งที่มีหลักฐานว่าฐานระบบทำงาน

- ชุดทดสอบ backend ที่เกี่ยวกับ Preview/Render, keyframe, motion และ Background Isolation ผ่าน `309` รายการ ข้าม `2` รายการ
- ชุดทดสอบ frontend ที่เกี่ยวข้องผ่าน `80` รายการ
- มี motion contract, Canvas sampler, ASS adapter, render pipeline และ Background Isolation task lifecycle อยู่แล้ว
- มีการป้องกันบางกรณี เช่น Background Isolation ใช้ร่วมกับ `bg_blur` หรือ `fit_mode=blur` ไม่ได้ และ renderer จะ fail-close กลับไปใช้ภาพต้นฉบับ

### 2.2 สิ่งที่ยังห้ามสรุปว่า “สมบูรณ์”

- test ส่วนใหญ่พิสูจน์ schema, contract และคำสั่ง FFmpeg แต่ยังไม่พิสูจน์ภาพจริงจาก browser เทียบกับไฟล์ render ครบทุกฟังก์ชัน
- live visual tests ถูกข้าม เพราะยังไม่ได้เปิดแอปและกำหนด URL/selector สำหรับ capture จริง
- Motion Text เคยเทียบเฟรมจริงแล้วไม่ผ่าน: mask IoU `0.1814` จากเกณฑ์ `≥ 0.90` และขอบกล่องต่าง `22 px` จากเกณฑ์ `≤ 6 px`
- motion preset catalog ระบุ `renderer_bound: false` จึงยังไม่ควรถือว่าทุก preset มี Preview และ Render จากนิยามเดียวกัน
- Background Isolation fixture เดิมเป็น synthetic/สั้นมาก และยังไม่วัดคุณภาพขอบผม มือ สินค้าโปร่งใส หรืออาการ mask กระพริบข้ามเฟรม

## 3. สาเหตุหลักที่ BG Cutout รู้สึกว่าใช้งานไม่ได้จริง

เรียงตามความน่าจะเป็นและผลกระทบ:

| ระดับ | ช่องว่าง | หลักฐาน/ผลกระทบ |
| --- | --- | --- |
| P0 | ประมวลผลทั้ง source ตั้งแต่ต้นถึงจบที่ `1080x1920`, `30 fps` | คลิป 60 วินาทีอาจกลายเป็น 1,800 เฟรม full-HD ที่ต้องรัน rembg ทีละเฟรม ทำให้ช้ามากและดูเหมือนค้าง |
| P0 | เมื่อ artifact หาย/ผิดพลาด Preview และ Render fallback เป็นภาพต้นฉบับ | ผู้ใช้เห็น “ไม่มีอะไรเกิดขึ้น” แทนที่จะทราบว่างานล้มเหลวหรือยังไม่พร้อม |
| P0 | ใช้ร่วมกับ Background Blur หรือ `fit_mode=blur` ไม่ได้ | ระบบปิด cutout แบบ fail-close แต่ UI ยังไม่อธิบาย conflict ให้ชัดก่อนเริ่มงาน |
| P1 | Preview โหลด PNG mask/foreground รายเฟรมผ่าน HTTP | เสี่ยงเฟรมกระพริบ สะดุด หรือภาพต้นฉบับโผล่ระหว่าง cache miss |
| P1 | ยังไม่มี trimmed-range/proxy workflow | ผู้ใช้ใช้เพียงช่วงสั้นใน Timeline แต่ระบบอาจประมวลผล source เต็มไฟล์ |
| P1 | ยังไม่พิสูจน์ temporal consistency | mask ที่ดีทีละเฟรมอาจสั่นบริเวณนิ้ว ผม ขอบสินค้า และ motion blur |
| P2 | ไม่มี quality/performance profile ที่ผู้ใช้เลือกได้ | ไม่ทราบเวลารอ ขนาด disk หรือ trade-off ก่อนกด |

## 4. สาเหตุหลักที่ Motion Text ยังไม่เรียบร้อย

| ระดับ | ช่องว่าง | ผลกระทบ |
| --- | --- | --- |
| P0 | Canvas และ ASS/FFmpeg ยังจัด layout แยกกัน | wrap, baseline, tier สี และขนาดตัวอักษร drift ได้ |
| P0 | preset catalog ยังไม่ถูก bind กับ renderer ครบ | การ์ด hover อาจขยับ แต่ไม่ได้พิสูจน์ว่า Timeline และ Render ขยับแบบเดียวกัน |
| P0 | live frame comparison ยังเป็น opt-in และถูก skip | CI สีเขียวได้ทั้งที่ภาพจริงต่างกัน |
| P1 | ยังไม่ตรวจทุก phase ของ animation | การตรวจเฟรมเดียวอาจพลาด in/hold/out, loop boundary และ seek กลาง motion |
| P1 | Thai shaping/สระ/วรรณยุกต์/emoji fallback ยังไม่มี golden fixture ครบ | ตัวหนังสืออาจซ้อน ฉีก หรือเปลี่ยน metrics ระหว่าง browser กับ libass |
| P1 | effect บางชนิดมีนิยามเชิงภาพ แต่ไม่มี degradation rule | ถ้า ASS ทำไม่ได้เท่า Canvas ระบบยังไม่บอกว่าจะลดรูปแบบอย่างไร |

## 5. กติกา Preview–Render Parity

### 5.1 ระดับความเท่ากัน

1. **Exact contract** — ต้องตรงกัน: เวลาเริ่ม/จบ, layer order, visibility, trim, speed, keyframe value, content, font family/weight, wrap, alignment, สี, opacity และตำแหน่ง
2. **Bounded visual parity** — ยอม anti-alias ต่างกันได้ แต่ต้องผ่าน metric: text/mask IoU `≥ 0.90`, centroid delta `≤ 6 px`, bbox edge delta `≤ 6 px`, normalized pixel errorตาม baseline ที่อนุมัติ
3. **Documented approximation** — อนุญาตเฉพาะข้อจำกัดของ browser เช่น loudnorm, sidechain ducking, pitch จาก playbackRate, transition noise pattern หรือ LUT เมื่อ WebGL2 ใช้ไม่ได้ ต้องมีป้าย “Preview โดยประมาณ” และ Render เป็นแหล่งผลลัพธ์สุดท้าย

ห้ามใช้คำว่า parity หากยังไม่มีภาพ/เสียงจากทั้งสองฝั่งมาเทียบกัน

### 5.2 Definition of Done ต่อหนึ่งฟังก์ชัน

- UI แก้ค่าได้จริง มี min/max/default และ validation
- state กลางมี schema/version/migration ชัดเจน
- Preview อ่านค่าจาก state กลาง ไม่ใช้ค่าซ้ำที่ hardcode
- Save แล้ว Reload ค่าและภาพไม่เปลี่ยน
- Render อ่าน field เดียวกันและไม่ silently ignore
- Undo/Redo ทำงาน และไม่ทำลาย selection/timeline
- ทดสอบที่เฟรมก่อนเริ่ม, เริ่ม, 25%, 50%, 75%, ก่อนจบ, จบ และหลังจบ
- ทดสอบ clip boundary, overlap, seek ย้อน, pause/resume และ render ซ้ำสองครั้งได้ผล deterministic
- failure/cancel/retry มีสถานะและข้อความที่ผู้ใช้แก้ต่อได้
- artifact ทดสอบอยู่ใน `.tmp/` และ cleanup 100%

## 6. Feature Inventory และ Gate ที่ต้องปิด

| หมวด | ฟังก์ชัน | สิ่งที่ต้องพิสูจน์ |
| --- | --- | --- |
| Project | create/open/save/autosave/reload/schema migration | state round-trip เท่ากัน, ไม่เปิดผิดโปรเจกต์, recovery หลัง crash |
| Timeline | add/delete/reorder/split/trim/duplicate/snap/multi-track | เวลาและลำดับตรง Render, undo/redo ครบ, boundary ไม่เกิดช่องดำ |
| Clip timing | trim start/end, speed, freeze tail | source-time mapping ตรงทุก boundary และเสียง sync |
| Transform | zoom, pan, rotation, mirror, keyframes | geometry matrix และ easing ตรง Preview/Render |
| Framing | fit/fill/blur background/aspect ratio | crop และ safe area ตรง, conflict แจ้งชัด |
| Color | brightness/contrast/saturation/LUT | สีเทียบด้วย fixture และ histogram; LUT แจ้งเมื่อ Preview ใช้ไม่ได้ |
| Transition | cut/fade/dissolve/black/white และ preset อื่น | duration, overlap, easing, first/last frame และ audio transition |
| Caption | Thai/English/bilingual/style/highlight/outline/wrap | shaping, baseline, line-break, safe zone และ timing ตรง |
| Motion Text | hook/text overlay/34 presets/in-hold-out/loop | renderer binding ครบและผ่าน multi-frame comparison |
| Sticker | position/scale/rotation/opacity/timing | alpha/layer order/keyframe ตรง |
| Effect | effect preset/intensity/timing | ไม่มี UI-only effect; มี render adapter และ visual threshold |
| Spotlight | subject/region/timing/layer | mask geometry, feather, color และ z-order ตรง |
| BG Cutout | prepare/progress/cancel/retry/cache/preview/render | ใช้งานจริงกับคลิปคนและสินค้า, ไม่มี silent fallback, mask ไม่กระพริบ |
| Audio | clip volume/BGM/SFX/voice/mute/solo/fade/ducking | timing/gain/channel mapping ตรง; approximation มีป้าย |
| Export | preset/resolution/fps/progress/cancel/retry/output | render จาก saved snapshot เดียวกัน, error ไม่ทิ้งไฟล์ปลอม |
| Reliability | missing media/network loss/restart/concurrent edit | recover ได้, ไม่ทำ state เสีย, แจ้งเหตุผลชัดเจน |
| UX | disabled state/progress/error/accessibility/keyboard | ปุ่มกดได้จริง, focus/shortcut ไม่ชน, ไม่มีสถานะหลอก |

## 7. แผนดำเนินงานแบบเป็นลำดับ

### Phase 0 — สร้าง Parity Harness กลาง (P0)

- สร้าง fixture project ขนาดเล็กที่มีทุก layer แต่ใช้ media สังเคราะห์ deterministic
- เปิดแอปจริงด้วย Playwright จับ Canvas ที่ timestamp กำหนด
- render project เดียวกันผ่าน production API/FFmpeg แล้ว extract เฟรมเวลาเดียวกัน
- ทำ comparator กลาง: alpha mask, bbox, centroid, SSIM/NMAE, pixel heatmap และ JSON report
- บังคับ live test ไม่ให้ skip ใน parity release gate
- บันทึก environment: browser, DPR, font hash, FFmpeg/libass version และ renderer mode

**Gate:** จงใจทำให้ transform หรือสีต่าง 10% แล้ว test ต้องแดง จากนั้นคืนค่าแล้วต้องเขียว

### Phase 1 — ทำ State/Renderer Coverage Matrix (P0)

- ไล่ทุก control จาก Inspector/Asset Panel/Timeline ว่าเขียน field ใด
- map field ไป Preview consumer, persistence serializer และ Render consumer
- fail CI เมื่อ field ที่ renderable ไม่มี consumer ครบสามจุด
- ทำ single canonical defaults เพื่อไม่ให้ frontend/backend default คนละค่า

**Gate:** ไม่มี control สถานะ `unknown`, `UI-only` หรือ `render ignored` โดยไม่ติดป้ายชัดเจน

### Phase 2 — ทำ BG Cutout ให้ใช้งานได้จริง (P0)

1. เพิ่ม preflight ตรวจ rembg/onnxruntime/model/disk/RAM และแสดงข้อความแก้ไขได้
2. เปลี่ยนงานจาก full source เป็นเฉพาะ source-time window ที่ถูกใช้ใน Timeline พร้อม padding เล็กน้อย
3. เพิ่ม `Draft` proxy mode และ `Final` full-quality mode; แสดงจำนวนเฟรม/เวลาประมาณ/พื้นที่ก่อนเริ่ม
4. แสดง conflict กับ `bg_blur`/`fit_mode=blur` ที่ UI และให้ผู้ใช้เลือกว่าจะปิดอะไร
5. ห้าม silent fallback: Preview ใส่ badge และ Render ต้อง warning/error ตาม policy
6. ทำ frame prefetch, bounded cache และ cancellation ที่หยุด worker จริง
7. เพิ่ม temporal smoothing/consistency และวัด edge flicker
8. invalidation ต้องอิง source hash + trim window + rotation + model + dimensions + fps
9. ทดสอบ real fixtures อย่างน้อย: คน/ผม, มือถือสินค้า, วัตถุขอบโปร่งใส, motion blur, low contrast

**Gate:** คลิป 10 วินาทีเริ่มเห็น preview ได้ตาม performance budget ที่กำหนด, cancel/retry/reload ได้, Render เทียบ mask กับ Preview ผ่านทุก sample frame และไม่มี original-frame flash

### Phase 3 — Motion Text ให้มีนิยามเดียว (P0) — เสร็จแล้ว 2026-09-23

1. กำหนด canonical motion schema: transform, opacity, blur, color, clipping, per-line/per-token phase และ easing
2. ให้ Canvas sampler และ ASS/FFmpeg adapter อ่าน schema เดียว ห้ามนิยามสูตรซ้ำ
3. ทำ preset registry ระบุ capability: `preview_bound`, `render_bound`, `seek_safe`, `loop_safe`, `degradation`
4. preset ที่ยัง bind ไม่ครบต้อง disable ใน production UI หรือขึ้น “Preview only” ห้ามแสดงว่าใช้งานได้สมบูรณ์
5. แยก text layout ออกจาก motion; freeze line-break/baseline/font metrics ก่อนใส่ animation
6. เพิ่ม golden fixtures ภาษาไทย สระ/วรรณยุกต์ ตัวเลข อังกฤษ emoji และข้อความ 1/2/3 บรรทัด
7. ตรวจ in/hold/out และ loop ที่ 0/10/25/50/75/90/100% รวม seek ตรงกลางและย้อนเวลา
8. แก้ fixture ปัจจุบันที่ IoU `0.1814` ให้ผ่าน `≥ 0.90` ก่อนประกาศ parity

**Gate:** preset ที่เปิดให้ผู้ใช้ทุกตัวผ่าน live Canvas-vs-render frame pair; ไม่มี `renderer_bound: false` ใน preset production

ผลตรวจจริง: live frame-pair `16/16` ผ่าน mask IoU/bbox/centroid/NMAE, app capture `7/7`, Save/Reload และ preset contract ผ่าน regression; backend เต็ม `1,731 passed, 7 skipped`, frontend `302 passed`, build ผ่าน จึงเลื่อนงานที่ยังขาด live vertical slice ไป Phase 4 ตาม coverage matrix

### Phase 4 — ตรวจ Editor ทุกฟังก์ชันแบบ Vertical Slice (P1)

ทำทีละหมวด ไม่ทำ Preview ทั้งหมดก่อนแล้วค่อยตาม Render:

1. Clip timing + timeline boundaries
2. Transform/keyframe/framing
3. Caption/text/sticker/effect/spotlight และ z-order
4. Color/LUT
5. Transition
6. Audio
7. Save/reload/undo/redo/recovery

**Progress 2026-09-23 — overlay vertical slice ปิดแล้ว:** Caption, Sticker, Effect และ Spotlight ผ่าน live Canvas-vs-production evidence พร้อม Save/Reload regression แล้ว โดยผล coverage matrix ปัจจุบันคือ `PASS 7`, `APPROXIMATION 6`, `BLOCKED 1`, `UNTESTED 6` รายละเอียดอยู่ที่ `_Docs/Reports/EDITOR_FEATURE_COVERAGE_REPORT_20260922.md` และรอบงานถูกย้ายเข้า `HISTORY.md`

**ยังไม่ปิด:** timeline boundary/overlap, clip trim/speed/freeze, transform/keyframes, framing/blur, reliability/recovery และ Editor UX/accessibility; color, transitions, Background Isolation, LUT, audio และ mute/solo ยังคงต้องจัดการตามสถานะใน matrix
8. Export/cancel/retry/error

ต่อหนึ่ง slice ต้องปิด UI → state → Preview → save/reload → Render → comparison ในรอบเดียว

### Phase 5 — Performance, Failure และ Release Gate (P1)

- profile หน้า Editor ที่ timeline 1, 10, 50 และ 100 clips
- ตรวจ dropped frames, memory growth, cache eviction และ seek latency
- จำลอง source หาย, API ล่ม, disk เต็ม, worker ตาย, render cancel และ app restart
- ทำ parity dashboard แสดงจำนวน feature: Passed / Approximation / Blocked / Untested
- ห้าม release หาก P0 มี `Untested`, visual live tests ถูก skip หรือ artifact cleanup ไม่ครบ

## 8. Test Matrix ขั้นต่ำต่อฟังก์ชัน

| มิติ | กรณีทดสอบขั้นต่ำ |
| --- | --- |
| เวลา | ก่อนเริ่ม, start, กลาง, ก่อนจบ, end, หลังจบ, clip overlap |
| การควบคุม | mouse, keyboard, direct numeric input, undo, redo |
| persistence | save, reload, migrate project เก่า, crash recovery |
| playback | play, pause, seek ไปหน้า, seek ย้อน, loop |
| media | 24/30/60 fps, VFR, ไม่มี audio, stereo/mono, rotation metadata |
| text | Thai marks, EN, digits, emoji fallback, long word, multi-line |
| render | draft/final, 1080x1920@30, rerender deterministic |
| failure | network fail, worker fail, invalid field, missing artifact, cancel/retry |

## 9. รูปแบบรายงานที่ต้องได้จากแต่ละรอบ

```text
Feature:
User action:
Canonical fields:
Preview consumer:
Persistence path:
Render consumer:
Fixture/timestamps:
Observed Preview:
Observed Render:
Metrics and thresholds:
Failure UX:
Save/Reload result:
Undo/Redo result:
Status: PASS | APPROXIMATION | FAIL | UNTESTED
Evidence paths:
Regression tests:
Cleanup result:
```

## 10. Prompt สำหรับสั่ง Agent ตรวจแบบละเอียด

คัดลอกข้อความด้านล่างไปใช้ได้โดยตรง:

```text
คุณเป็น Senior Video Editor Systems Engineer และ QA Lead ของ OmniCut Pro Studio

ภารกิจ: ตรวจและทำให้หน้าตัดต่อทุกฟังก์ชันใช้งานได้จริงแบบ end-to-end และพิสูจน์ว่า Preview กับ Render ตรงกัน ห้ามสรุปจากการมีโค้ด, unit test, schema หรือคำสั่ง FFmpeg เพียงอย่างเดียว ต้องใช้หลักฐานจาก UI จริง, Canvas จริง และไฟล์ Render จริง

กติกาก่อนเริ่ม:
1. อ่าน AGENTS.md, TODO.md เฉพาะรอบ active, .agents/rules/work_loop.md, testing_standard.md, preview_render_parity.md และ font_text_visual_contract.md
2. รัน git status บันทึกไฟล์ค้างของผู้อื่น ห้ามเขียนทับ
3. เขียนรอบงานลง TODO.md ก่อนแก้ไฟล์ใด ระบุผู้ดำเนินการและโมเดล
4. ใช้ fixture deterministic/offline เก็บผลชั่วคราวใน .tmp เท่านั้น ห้ามแตะ 01_Raw, 02_Assets หรือ 04_Exports
5. งานนี้ต้องตรวจ Production path จริง ห้ามสร้าง demo implementation แยกเพื่อให้ test ผ่าน

นิยามความสำเร็จต่อฟังก์ชัน:
- ปุ่ม/slider/input เปลี่ยน canonical state ได้จริง
- Preview ตอบสนองทันทีและ seek-safe
- Save/Reload แล้ว state และภาพไม่เปลี่ยน
- Undo/Redo ทำงาน
- Render อ่าน field เดียวกัน ไม่มี silent ignore/fallback
- เทียบ start/middle/end และ animation phase หลายจุดด้วย metric ที่กำหนด
- error/cancel/retry แสดงสถานะตามจริงและ recover ได้
- มี regression test และ cleanup 100%

ขั้นตอนตรวจ:
A. ทำ Feature Inventory จาก Inspector, Asset Panel, Timeline, keyboard shortcuts, Settings และ Export dialog
B. สำหรับทุก control สร้างตาราง: UI component → state field/default/range → serializer/migration → Preview consumer → Render consumer → existing tests → gap → owner
C. ทำ parity harness เปิดแอปจริง จับ Canvas ตาม timestamp แล้ว render project snapshot เดียวกันผ่าน production API/FFmpeg จากนั้น extract frame เวลาเดียวกัน
D. เทียบ exact contract: timing, visibility, layer order, content, font, wrap, alignment, color, opacity, geometry
E. เทียบ visual metric: mask/text IoU ≥0.90, bbox edge delta ≤6 px, centroid delta ≤6 px และ pixel/SSIM threshold ที่บันทึกไว้
F. ถ้า browser ทำให้เหมือน render ไม่ได้ เช่น loudnorm/ducking/pitch/transition noise/LUT fallback ให้จัดเป็น APPROXIMATION พร้อมป้ายใน UI ห้ามเรียก PASS
G. ตรวจ play/pause/seek forward/seek backward/loop, clip boundary/overlap, save/reload, undo/redo, rerender และ project migration
H. จำลอง missing media, API/worker fail, network fail, disk full, cancel, retry และ restart

จุดตรวจ BG Cutout แบบบังคับ:
- ตรวจ dependency/model/disk/RAM preflight
- ตรวจว่า process เฉพาะ source-time window ที่ใช้ ไม่ใช่ทั้ง source โดยไม่จำเป็น
- แสดง frame count, progress, ETA, cancel และ retry จริง
- ตรวจ conflict กับ bg_blur และ fit_mode=blur ที่ UI
- ห้าม silent fallback เป็น original; ต้องมี badge/error/warning ที่เห็นได้
- ตรวจ cache key/invalidation ด้วย source hash, trim, rotation, model, fps, dimensions
- ตรวจ prefetch ไม่ให้ original frame flash
- ใช้คลิปคน/ผม, มือจับสินค้า, ขอบโปร่งใส, motion blur และ low contrast
- วัด alpha IoU, edge jitter, temporal flicker, dropped frames, เวลาและ disk usage
- เทียบ Preview mask กับ Render mask ทุก sample frame

จุดตรวจ Motion Text แบบบังคับ:
- ตรวจทุก production preset ว่า preview_bound และ render_bound เป็น true
- Canvas และ ASS/FFmpeg ต้องอ่าน canonical motion schema เดียวกัน
- freeze text layout: font hash, weight, baseline, wrap, line-height, Thai shaping, emoji fallback
- ตรวจ phase 0/10/25/50/75/90/100%, in/hold/out, loop boundary และ seek ย้อน
- ตรวจ opacity/translate/scale/rotate/blur/color/clipping/per-line/per-token
- เทียบข้อความไทยที่มีสระ/วรรณยุกต์, อังกฤษ, ตัวเลข, emoji และ 1–3 บรรทัด
- preset ที่ renderer ยังไม่รองรับต้อง disable หรือขึ้น Preview only ห้ามปล่อยเป็นฟังก์ชันสมบูรณ์

หมวดที่ต้องตรวจครบ:
Project lifecycle; timeline add/delete/reorder/split/trim/duplicate/snap; trim/speed/freeze; zoom/pan/rotation/mirror/keyframes; fit/fill/background blur; brightness/contrast/saturation/LUT; transitions; captions Thai/English/bilingual; hook/text overlays/motion presets; stickers; effects; spotlight; BG Cutout; clip audio/BGM/SFX/voice/mute/solo/fade/ducking; export/progress/cancel/retry; missing media/recovery; keyboard/accessibility/performance.

ผลลัพธ์ที่ต้องส่ง:
1. Coverage Matrix ทุกฟังก์ชัน: PASS | APPROXIMATION | FAIL | UNTESTED
2. Ranked findings P0/P1/P2 พร้อมหลักฐาน file:line, reproduction และ root cause ห้ามเดา
3. ภาพ Preview/Render/diff และ JSON metrics ของทุก visual feature
4. แผนแก้เป็น vertical slices โดยแต่ละ slice ปิด UI→state→Preview→save/reload→Render→test
5. regression tests และคำสั่งที่รัน พร้อม pass/fail/skip; skip ใน release gate ถือว่าไม่ผ่าน
6. รายงาน cleanup ว่าไม่มีไฟล์ทดสอบตกค้าง
7. อัปเดต TODO/HISTORY ตาม work loop และระบุ agent+model

ข้อห้าม:
- ห้ามบอกว่าใช้งานได้เพราะ unit test ผ่านอย่างเดียว
- ห้ามใช้ screenshot จาก gallery hover แทน Timeline Preview
- ห้ามลด threshold หรืออัปเดต golden โดยไม่อธิบายความแตกต่างที่ผู้ใช้มองเห็น
- ห้ามมี silent fallback, swallowed exception หรือ UI สถานะหลอก
- ห้ามแก้ Preview โดยไม่แก้ Render adapter และ regression test คู่กัน
- ห้ามเพิ่มฟีเจอร์ใหม่ก่อนปิด P0 parity/reliability ของฟีเจอร์เดิม
```

## 11. ลำดับที่แนะนำให้ทำต่อ

1. Parity Harness จริงใน browser + production render
2. BG Cutout usable path และ error visibility
3. Motion Text canonical renderer binding
4. Transform/Keyframe/Caption/Overlay parity
5. Transition/Color/LUT/Audio approximation policy
6. Full reliability/performance/release gate

นี่เป็นงานหลายรอบ ควรแตกเป็น vertical slice เล็กที่ตรวจจบจริงทีละหมวด ไม่ควรแก้ทั้ง Editor พร้อมกัน เพราะจะหาต้นเหตุและ regression ยาก
