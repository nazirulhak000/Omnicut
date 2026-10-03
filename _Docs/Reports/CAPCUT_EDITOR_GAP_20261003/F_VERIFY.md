# F_VERIFY: ยืนยัน/ล้ม 3 ข้อสงสัยจากรายงาน Editor vs CapCut (2026-10-03)

ดำเนินการโดย: Claude Code sub-agent F (Claude Sonnet 5.5)
รอบ: EDITOR-CAPCUT-FIX-WAVE1-20261003 · เลน F (อ่านโค้ด + ทดลอง ไม่แก้ซอร์สทุกไฟล์)

## สรุปบรรทัดเดียว

| ข้อ | เรื่อง | Verdict | ระดับหลักฐาน | ขนาดแก้ |
|---|---|---|---|---|
| L3-02 | แก้ข้อความซับที่เปิด Ghost Reveal แล้ว preview ยังโชว์คำเก่า | **CONFIRMED** (ฝั่ง preview) / render **REFUTED** (render ถูกต้อง) | รันฟังก์ชันจริง (`drawCaption` ของ SequencePlayer.jsx + `SubtitleEngine.generate_ass`) | S (กัน) + M (ให้ Ghost Reveal กลับมา) |
| L7-04 | หลัง render แล้วแก้ต่อ/เรนเดอร์ซ้ำ ได้ 409 | **CONFIRMED** | ฝั่ง server รันจริง (router + ProjectManifest จริง) · ฝั่ง browser อ่านโค้ด (จับทุกจุดเรียก) | M |
| L2-10 | mirror + pan ทิศกลับระหว่าง preview กับ render | **CONFIRMED** (เฉพาะเส้นทาง cover-fit ธรรมดา และเส้นทาง keyframe) | เทียบเฟรมจริง (ffmpeg render จริง เทียบ preview จริง) | S |

**หมายเหตุความสดของหลักฐาน:** ระหว่างทำงาน เลนอื่นแก้ `SequencePlayer.jsx`, `EditorShell.jsx`, `useEditorCommands.js`, `video_editor.py` ไปแล้ว ผมรันการทดลองทั้ง 3 ข้อซ้ำบนซอร์สปัจจุบันหลังจากนั้น ผลเหมือนเดิมทุกตัวเลข และ diff ของเลนอื่นไม่ได้แตะโค้ดที่ตรวจ (ไม่มี `word_reveal`, `mirror`/`hflip`, `handleRenderComplete`, `rememberProjectRevision` ใน diff)

ไม่ได้กด UI และไม่ได้รัน dev server ทุกการทดลองรันใน `.tmp/` และ tmp dir แล้วลบทิ้งหมด

---

## L3-02 Ghost Reveal โชว์คำเก่าหลังแก้ข้อความ

**Verdict: CONFIRMED ที่ preview · render ไม่เป็นปัญหา**

### เส้นทางข้อมูลที่ตามจริง
1. พิมพ์ในกล่องข้อความ: `CaptionInspector.jsx` เรียก `onCaptionChange(uid, { text })`
2. `patchCaption` (`useEditorCommands.js`) ทำ `{ ...c, ...patch }` เท่านั้น ไม่แตะ `word_reveal` / `word_timings` (ไม่มีตัวไหนในโฟลเดอร์ `frontend/src` ลบหรือสร้างใหม่ นอกจากคอมเมนต์ใน `editorProjectState.js` ที่บอกว่า "ต้องรักษาไว้")
3. `manifestToEditorState` spread `...cue` ตอนโหลด จึง **ตั้งใจเก็บ** `word_reveal` ไว้ทุกครั้ง และ autosave ส่ง cue ทั้งก้อนกลับไปเก็บใน manifest (`api_phase1.py` เก็บ `cues` ตามที่ส่ง)
4. **preview:** `drawSingleCue` ตัวแปร `revealTrack = style.ghostReveal ? cue.word_reveal : null` แล้ว cue บรรทัดเดียวเรียก `ghostRevealSegments(revealTrack, t)` ตรงๆ **ไม่เทียบกับ `cue.text`** (ซับหลายบรรทัดมี guard `splitRevealByLines` ที่คืน null ถ้าคำไม่ตรง แต่บรรทัดเดียวไม่มี)
5. **render:** `generate_ass` เรียก `generate_micro_cues` ก่อน ซึ่งสร้าง `word_reveal` ใหม่จากข้อความ (`build_word_reveal(cue_text, ...)`) ทุกครั้ง และชั้น `generate_ass` เองยังมี guard `stored_matches` เทียบคำที่เก็บไว้กับข้อความที่จะวาด ถ้าไม่ตรงก็คำนวณใหม่

### สิ่งที่รันจริง
- ดึง `drawCaption` + helper จริงออกจาก `SequencePlayer.jsx` (ตัดคอมโพเนนต์ JSX ออก) ไปรันใน node กับ canvas จำลองที่บันทึกทุก `fillText` แล้วป้อนข้อมูล cue ที่ "แก้ข้อความแล้วแต่ `word_reveal` ยังเป็นของเดิม" (สร้าง track เดิมด้วย `build_word_reveal` ของจริงจาก .venv)
- รัน `SubtitleEngine.generate_ass(..., ghost_reveal=True)` จริงกับ cue เดียวกัน

| กรณี (ข้อความใหม่ `ทดสอบลำโพงพกพาเสียงดี`, track เดิมของ `รีวิวหูฟังไร้สายรุ่นใหม่`) | preview วาดอะไร | render (ไฟล์ .ass) |
|---|---|---|
| t=0.5 วิ | `รีวิว` สีเขียว `#66FF00` | คำใหม่ `ทดสอบ` เขียว ที่เหลือซ่อน |
| t=2.0 วิ | `รีวิว หูฟัง` ขาว + `ไร้สาย` เขียว | คำใหม่ทั้งหมด ไม่มีคำเก่าเลยในไฟล์ |
| t=3.9 วิ | `รีวิว หูฟัง ไร้สาย` ขาว + `รุ่นใหม่` เขียว | เหมือนกัน |
| ล้าง `word_reveal` ออก (ทดลองเทียบ) | ซับคำใหม่ปกติ ไฮไลต์คีย์เวิร์ด | |

`contains_old_word=false`, `contains_new_word=true` ใน .ass ทั้งกรณีที่มี `word_timings` เก่าติดมา

### ผลข้างเคียงที่เจอจากการทดลองเดียวกัน (รากเหตุเดียวกัน)
- **แก้พิมพ์ผิด 1 ตัว** (`ใหม` → `ใหม่`): preview ยังวาด `ใหม` ตัวผิดในเอฟเฟกต์ reveal ทั้งที่ข้อความในกล่องถูกแล้ว (กรณี T5 โดยตรง)
- **แยกท่อน (split)**: `{...target, text}` ทำให้ทั้งสองครึ่งพก track ของประโยคเต็ม ท่อนหลัง (`ไร้สายรุ่นใหม่`) วาดทั้งประโยค `รีวิว หูฟัง ไร้สาย รุ่นใหม่`
- **ลาก/ย่อยาวซับ (เวลาเปลี่ยนแต่ข้อความเดิม):** `word_reveal.start/end` เป็นเวลาสัมบูรณ์ ย้ายซับไป +5 วิ แล้ว ณ `cue.start` ตัว track ถือว่า "settled" ไปแล้ว ผลคือขาวทั้งบรรทัดตั้งแต่เฟรมแรก ไม่มีเขียวไล่ตามคำเลย (Ghost Reveal หายใน preview) ส่วน render คำนวณเวลาใหม่จาก start/end ใหม่ จึงยัง reveal
- **`word_timings` เก่า** ที่ติดมากับ cue ยังถูก render ใช้จับเวลาคำใหม่ได้ ถ้าความยาวตัวอักษรอยู่ในช่วง 0.6-1.6 เท่า (คำถูกต้อง แต่ขอบเวลาตามของเก่า ในการทดลองคำแรกจบที่ 1.5 วิทั้งที่สัดส่วนควรเป็นอื่น) ผลกระทบเล็ก

### ผลกระทบ
สูงตามที่รายงานเดิมว่า ค่าเริ่มต้น Ghost Reveal เปิด ทุกครั้งที่แก้คำ/แยก/ลากซับ preview ไม่ตรง render ผิดกฎ Preview = Render แต่ **ไฟล์ที่ส่งออกถูกต้อง** จึงเป็นความเชื่อใจใน preview ไม่ใช่ข้อมูลเสีย

### ทางแก้ที่เสนอ (ยังไม่ลงมือ)
1. **S (ทำก่อน):** guard ใน `drawSingleCue` บรรทัดเดียวก่อน `ghostRevealSegments` ใช้ track ก็ต่อเมื่อ `strip(reveal.map(text).join('')) === strip(cue.text)` และ `|reveal[0].start - cue.start|` กับ `|reveal.at(-1).end - cue.end|` ไม่เกินประมาณ 0.05 วิ ไม่งั้นข้าม reveal (ตกไปไฮไลต์คีย์เวิร์ดตามเดิม) และล้าง `word_reveal`/`word_timings` ใน `patchCaption` เมื่อ patch มี `text`/`start`/`end` และใน `handleSplitCue*`, `handleMergeCue*`, `handleBatchFindAndReplace`
   - ข้อเสีย: ระหว่างที่ track ถูกทิ้ง preview ไม่ใช่ Ghost Reveal แต่ render ยังเป็น Ghost Reveal (ยังไม่ตรงทั้งหมด แต่ไม่โชว์ข้อความผิด)
2. **M (ทำให้ตรงจริง):** endpoint เล็กใน backend เรียก `build_word_reveal` (ใช้ pythainlp เหมือน render) ให้ frontend ขอ track ใหม่แบบ debounce หลังแก้ข้อความ/เวลา แล้วเก็บลง cue (ห้ามให้ browser แบ่งคำเองด้วย `Intl.Segmenter` เพราะ test `test_preview_reveals_on_the_same_word_boundaries_as_the_render` ห้ามไว้)
- ไฟล์ที่ต้องแก้: `frontend/src/components/SequencePlayer.jsx`, `frontend/src/hooks/useEditorCommands.js`, `tests/test_preview_render_parity.py` (เพิ่มเทสแบบ node ดึง `drawCaption` มารันเหมือนที่ผมทำ), ข้อ 2 เพิ่ม `scripts/api_phase1.py` (หรือไฟล์ router ที่เหมาะสม)
- ต้องทำตามกฎข้อ 9 ใน AGENTS.md: แก้ SequencePlayer ต้องมีเทส parity และดูเฟรม ffmpeg จริง

### สิ่งที่ยังไม่ได้ตรวจ
- ไม่ได้เห็นเฟรม canvas ใน browser จริง (ใช้ canvas จำลองที่บันทึก `fillText` จึงเห็นคำ/สีที่จะวาด ไม่เห็นตำแหน่งพิกเซล)
- ซับหลายบรรทัดที่ guard `splitRevealByLines` ทำงาน อ่านโค้ดเท่านั้น ไม่ได้รัน
- ไม่ได้ตรวจว่าเรนเดอร์ใหม่แล้ว manifest เขียน `cues` ทับ `word_reveal` เก่าหรือไม่

### ถ้าอยากยืนยันด้วยมือ (ไม่จำเป็น)
เปิดโปรเจกต์ที่ Ghost Reveal เปิด เลือกซับ 1 ท่อน แก้ 1 คำในกล่องข้อความ เล่น preview ที่ท่อนนั้น ถ้าเห็นคำเก่าเขียวไล่ตามเสียง = ตรงกับที่ทดลอง

---

## L7-04 revision ฝั่ง browser ค้างหลัง render → 409

**Verdict: CONFIRMED**

### ลำดับเหตุการณ์ (replay จริงด้วย `fastapi.testclient` + router `api_phase1` จริง + `ProjectManifest` จริง ใน tmp dir; ตัวอย่างค่า hash ย่อ)
| # | เหตุการณ์ | ผลที่ server ตอบ | revision ที่ browser จำ |
|---|---|---|---|
| 1 | เปิดโปรเจกต์ `GET /projects/{name}` (`applyLoadedProject` เรียก `rememberProjectRevision`) | R0 `374b8bc7` | R0 |
| 2 | แก้ zoom autosave `PATCH /state` ส่ง `base_revision=R0` | 200 | R1 `38a27599` (`updateProjectState` จำค่าจาก response) |
| 3 | กดเรนเดอร์: `await updateProjectState(...)` ส่ง base=R1 | 200 | R1 |
| 4 | `POST /reroll` แล้ว pipeline เขียน manifest: `ProjectManifest.save(**manifest_fields)` (`video_assembly_stage.py`) และ `render_jobs.finalize_incremental_render` เขียนอีกรอบ (`incremental_render`) (ผมเรียกของจริงทั้งสองจุดใน replay) | server เป็น R2 `778cccac` | **ยัง R1** |
| 5 | render เสร็จ `handleRenderComplete` / `useRenderJob.onResponse` ไม่ GET ไม่ remember | | **ยัง R1** |
| 6 | ผู้ใช้ปรับ slider ซูม (autosave) base=R1 | **409** | R1 |
| 7 | ผู้ใช้กดเรนเดอร์อีกรอบ (ไม่ได้แก้อะไร) `updateProjectState` base=R1 | **409** ข้อความ "โปรเจกต์ถูกแก้ไขจากอีกหน้าหรืองานเบื้องหลัง กรุณาเปิดโปรเจกต์ใหม่ก่อนบันทึก…" | R1 |
| 8 | ควบคุม: GET ใหม่ (reload) แล้วแก้ซูม | 200 | R3 |

ผลรวมจากสคริปต์: `{"after_render_autosave": 409, "after_render_rerender": 409, "control_after_reload": 200}` (รัน 2 รอบ ก่อนและหลังเลนอื่นแก้ซอร์ส ได้ผลเดียวกัน) เทสเดิม `test_external_cutout_migration_invalidates_editor_revision` ยืนยันว่า "การเขียน manifest จากข้างนอกทำให้ revision เปลี่ยน" เป็นพฤติกรรมตั้งใจ ปัญหาคือ browser ไม่ถูกบอก

### หลักฐานฝั่ง browser (อ่านโค้ด ไม่ได้กดจริง)
- `rememberProjectRevision` ถูกเรียกแค่ 2 จุดทั้งโปรเจกต์: `EditorShell.applyLoadedProject` (ตอนโหลด) และ `api.js` `updateProjectState` (จาก response ของ PATCH) `getProject` ใน `api.js` ไม่เรียก (ตั้งใจ ตามคอมเมนต์ใน `projectRevision.js`)
- `handleRenderComplete` ใน `EditorShell.jsx` ทำแค่รีเซ็ต baseline ของ audio/caption + `updateAngleStatus('rendered')` ไม่ reload โปรเจกต์
- ทางที่อาจทำให้ reload เองได้ คือ effect "Load project handed down" ที่ depend `productContext`: ผมไล่แล้ว `workspaceData.invalidateTrackerData()` เป็นแค่ล้างแคช ไม่เปลี่ยน object `activeProductContext` ใน `App.jsx` จึงไม่ trigger (ข้อนี้เป็นการอนุมานจากโค้ด ควรให้คนกดยืนยันหนึ่งรอบ)
- เมื่อโดน 409: `useProjectAutosave.runFlush` ตั้งสถานะ `'error'` และ **ไม่ retry** (EditorHeader แสดง "บันทึกไม่สำเร็จ — ลองอีกครั้ง") ปุ่มลองซ้ำก็ 409 ซ้ำจนกว่าจะโหลดโปรเจกต์ใหม่
- **ความเสี่ยงข้อมูลหาย:** งานที่แก้หลัง render ทุกอย่างไม่ถูกบันทึกจนกว่าจะ reload และการบันทึกตอนปิดแท็บ (`saveBeforeUnload` ใช้ `withProjectRevision` เดียวกัน) ก็โดน 409 แบบเงียบ (`.catch(() => {})`) ปิดแท็บ = งานหลัง render หาย

### ข้อควรรู้สำหรับออกแบบทางแก้
`project_revision` แฮชทั้ง manifest (ยกเว้น `_editor_revision`) รวม `updated_at`, `artifacts`, `render_performance`, `incremental_render` ดังนั้นการเขียนใดๆ ของ pipeline เปลี่ยน revision เสมอ และ pipeline เขียน `clip_list` (`actual_clip_list`) และ `render_params` ทับด้วย ถ้าให้ browser ยอมรับ revision ใหม่เฉยๆ โดยไม่ดูเนื้อหา การบันทึกครั้งต่อไปจะเขียนทับค่าที่ pipeline ปรับ (ขัดเจตนา guard)

### ทางแก้ที่เสนอ (ยังไม่ลงมือ) ขนาด M
1. ใน `handleRenderComplete` (และเคส cancel/fail ที่ pipeline อาจเขียนบางส่วน): ถ้า editor "สะอาด" (`saveStatus === 'saved'` ไม่มีงานค้างในคิว) ให้ `getProject` แล้วเทียบ `editorStateToSavePayload(mapProject(manifest))` กับ payload ปัจจุบัน ถ้าเท่ากัน (pipeline ไม่ได้เปลี่ยนฟิลด์ที่ editor เป็นเจ้าของ) เรียก `rememberProjectRevision` ได้เลย ถ้าต่างให้ `loadProject` ใหม่ (รับว่า undo history รีเซ็ต)
2. ถ้า editor "สกปรก" (แก้ต่อระหว่าง render): ห้าม advance revision เงียบๆ ให้ขึ้นแถบ "เรนเดอร์เสร็จและโปรเจกต์ถูกปรับ กดโหลดใหม่ (งานที่แก้ค้างจะ…)" พร้อมปุ่ม
3. เพิ่มปุ่ม "โหลดโปรเจกต์ใหม่" ตอนเจอ 409 (แทนข้อความให้ไปเปิดเอง) และอย่าให้ `saveBeforeUnload` กลืน 409 เงียบ
- ไฟล์: `frontend/src/components/editor/EditorShell.jsx` (`handleRenderComplete`, ปุ่ม/แถบ 409), `frontend/src/lib/projectRevision.js` (ฟังก์ชัน pure ตัดสินใจ) + เทส node ใน `frontend/src/lib/*.test.js`, `tests/test_project_revision.py` (เพิ่มเทส replay ลำดับข้างบน) ไม่ต้องแก้ backend
- ความเสี่ยงสูง (guard กันข้อมูลหาย) EditorShell ถูกเลนอื่นแก้อยู่ ต้องประสานก่อน

### สิ่งที่ไม่ได้ตรวจ
- ไม่ได้รัน pipeline เต็มรอบ replay เรียก `ProjectManifest.save` และ `finalize_incremental_render` จริง แต่ใส่ฟิลด์ที่ `video_assembly_stage.py` เขียนเป็นตัวอย่าง (ไฟล์นั้นกำลังถูก session อื่นแก้ จึงอ่านอย่างเดียว)
- พฤติกรรม React จริงใน browser (ชิปสถานะแสดงจริงไหม) ยังเป็นการอ่านโค้ด

### ถ้าอยากยืนยันด้วยมือ (1 รอบ ราว 3 นาที)
เปิดโปรเจกต์ → เรนเดอร์แบบทดลอง 720p ให้เสร็จ → ปรับ slider ซูม 1 ค่า โดยไม่โหลดโปรเจกต์ใหม่ → ดูชิปหัว editor ว่าเป็น "บันทึกไม่สำเร็จ — ลองอีกครั้ง" ไหม → กด "เรนเดอร์" อีกรอบ ดูว่ามีข้อความ "โปรเจกต์ถูกแก้ไขจากอีกหน้า…" ไหม ทำสองอย่างทั้งเปิดจากหน้าสินค้า (มี productContext) และเปิดโปรเจกต์ตรงๆ

---

## L2-10 mirror + pan ทิศไม่ตรงกันระหว่าง preview กับ render

**Verdict: CONFIRMED** (เมื่อ mirror เปิด + zoom > 1 + pan_x ≠ 0)

### สูตรที่เทียบ
- **render** (`video_editor.py`): `mirror_filter = "hflip,"` ถูกใส่ **ก่อน** scale/crop (คอมเมนต์ในโค้ดบอกชัดว่า "applied before the scale/crop chain") จึง crop หน้าต่างตาม `pan_x` บนภาพที่กลับซ้ายขวาแล้ว (ทั้งเส้นทาง `framing_filters` ที่ปิด one-pass เมื่อมี mirror และเส้นทาง `dynamic_camera_filter` ของ keyframe)
- **preview** (`drawVideoFrame` ใน `SequencePlayer.jsx`): คำนวณ source rect ด้วย `sx += (roomX/2)*(1+panX)` บนภาพ **ที่ยังไม่กลับ** แล้วค่อย `ctx.scale(-1,1)` ตอนวาด (crop ก่อน แล้วกลับ)
- เส้นทาง bg_blur ของ preview แยกต่างหาก ใช้ transform ที่ pan ทีหลัง mirror (ตรงกับ render อยู่แล้ว)

### ทดลองด้วยเฟรมจริง
ต้นฉบับสังเคราะห์ 1080x1920 แบ่ง 3 สี ซ้าย=แดง (R) กลาง=เขียว (G) ขวา=น้ำเงิน (B) zoom=2.0, pan_y=0
- ฝั่ง render: เรียก `VideoEditor.assemble_tiktok_video` จริง (clip_list 1 คลิป, CPU encoder, preset draft) แล้วดึงเฟรมที่ 1.0 วิ ย่อเป็น 540x960
- ฝั่ง preview: ดึง `drawVideoFrame` จริงไปรันใน node ด้วย `resolveClipTransforms` จริงจาก `timelineMath.js` บน canvas จำลองที่ rasterize `drawImage` ด้วยเมทริกซ์ affine เต็ม (translate/scale/rotate) บนต้นฉบับชุดเดียวกัน
- อ่านสีตามแกน x ที่แถวกลางภาพ (ตัวเลข = ช่วงพิกเซล x ของภาพกว้าง 540)

| mirror | pan_x | render (ของที่ส่งออก) | preview (ที่เห็นในจอ) | ตรงกัน? |
|---|---|---|---|---|
| ปิด | -1 | R[0-359] G[360-539] | R[0-359] G[360-539] | ตรง |
| ปิด | 0 | R[0-89] G[90-449] B[450-539] | เหมือนกัน | ตรง |
| ปิด | +1 | G[0-179] B[180-539] | เหมือนกัน | ตรง |
| เปิด | 0 | B[0-89] G[90-449] R[450-539] | เหมือนกัน | ตรง |
| เปิด | -1 | **B[0-359] G[360-539]** | **G[0-179] R[180-539]** | **สลับกัน** |
| เปิด | +1 | **G[0-179] R[180-539]** | **B[0-359] G[360-539]** | **สลับกัน** |

- ความสัมพันธ์: `render(mirror, pan=p) == preview(mirror, pan=-p)` ครบทุกกรณี (ใช้ยืนยันทางแก้ด้านล่าง)
- เส้นทาง keyframe (pipeline ใส่ keyframe ให้คลิปจึงเจอบ่อยกว่าที่คิด): keyframe pan_x=+1, zoom=2, mirror เปิด → render `G[0-179] R[180-539]` แต่ preview `B[0-359] G[360-539]` (สลับเหมือนกัน) ส่วน mirror ปิดตรงกัน
- เส้นทาง bg_blur (ต้นฉบับแนวนอน 1920x1080, zoom 2, pan +1): mirror เปิดและปิด ตรงทั้งคู่ ไม่ต้องแก้
- ไม่กระทบ: mirror ปิด, zoom = 1, pan_x = 0, pan_y (กลับแค่แนวนอน)

### ผลกระทบ
ต่ำ-กลางตามที่รายงานเดิมว่า (ต้อง mirror + zoom + pan_x พร้อมกัน) แต่เป็นความผิด parity จริง ตำแหน่งที่ผู้ใช้เลื่อนดูใน preview ไม่ใช่ที่ออกในไฟล์ (ฝั่งตรงข้ามของภาพ) ผลต่อไปที่ติดมา: จุด SAM2 ที่คลิกบน preview (`subjectFrameMapping.js` `previewPointToSource`/`sourcePointToPreview`) ใช้สูตร crop-แล้ว-กลับ แบบเดียวกัน จึงสอดคล้องกับ preview ไม่ใช่ render

### ทางแก้ที่เสนอ (ยังไม่ลงมือ) ขนาด S
- **แก้ฝั่ง preview แนะนำ** (ไม่แตะ render ซึ่งเป็น golden master และของที่ส่งออกไปแล้ว; ความหมายของ render คือ "pan ในพื้นที่หน้าจอ ทิศเดียวกันไม่ว่า mirror หรือไม่" เหมือน CapCut): ในเส้นทางที่ไม่ใช่ bg_blur ให้ใช้ `panX = mirror ? -camera.pan_x : camera.pan_x` ตอนคำนวณ source rect
  - ที่ต้องแก้ให้คู่กัน: `drawVideoFrame` และ `drawIsolatedFrame` (cutout ใช้สูตรเดียวกันและต้องตรงกัน ตามคอมเมนต์ในไฟล์) ใน `SequencePlayer.jsx` และ `geometry()` ใน `frontend/src/lib/subjectFrameMapping.js` (กิ่งที่ไม่ใช่ blur)
  - **ข้อควรระวัง:** กรณี rotation 90/180/270 ร่วมกับ mirror ผมไม่ได้ทดสอบ (render ทำ rotate แล้วค่อย hflip) ต้องทดสอบด้วยวิธีเดียวกันก่อนใช้สูตรนี้กับกรณีหมุน
- **ทางเลือกที่ไม่แนะนำ:** ย้าย `hflip` ไปหลัง crop ใน `video_editor.py` (M) เปลี่ยนผลของ export ที่มี mirror+pan อยู่แล้ว และกระทบ `framing_filters` one-pass
- เทส: เพิ่มใน `tests/test_preview_render_parity.py` เทสแบบที่ผมทำ (node ดึง `drawVideoFrame` + render จริงของคลิป L/M/R แล้วเทียบช่วงสี) ครอบ mirror×pan_x และเส้นทาง keyframe ตามกฎข้อ 9 ต้องดูเฟรมจริงด้วย ffmpeg
- ไฟล์: `frontend/src/components/SequencePlayer.jsx`, `frontend/src/lib/subjectFrameMapping.js` (+ `.test.js`), `tests/test_preview_render_parity.py`

### สิ่งที่ไม่ได้ตรวจ
- rotation + mirror, การเปลี่ยนคลิปแบบ transition ระหว่างคลิปที่ mirror
- เบราว์เซอร์จริง (ใช้ rasterizer ในโหนดที่ทำเมทริกซ์ถูกต้องและแสดงผลตรงกับ render ในกรณีไม่ mirror ซึ่งเป็นตัวยืนยันว่าเครื่องมือเที่ยงตรง จึงไม่คาดว่า browser จะต่าง)

### ถ้าอยากยืนยันด้วยมือ (ไม่จำเป็น)
ตั้งคลิป mirror เปิด ซูม 2.0 เลื่อน pan_x ไปขวาสุด ดู preview แล้วส่งออกคลิปทดลองสั้นๆ เทียบเฟรมเดียวกัน ถ้าเห็นคนละฝั่งของภาพ = ตรงกับตาราง

---

## ลำดับที่แนะนำ (ผู้ใช้ตัดสินใจ)
1. L2-10: S ทำได้ทันที ผลตรวจชัดสุด ความเสี่ยงต่ำ (preview อย่างเดียว) ต้องรอเจ้าของ `SequencePlayer.jsx`
2. L3-02 ข้อ 1 (guard + ล้าง track): S ลดการโชว์ข้อความผิดทันที ข้อ 2 (ขอ track ใหม่จาก backend) M ทำทีหลัง
3. L7-04: M ความเสี่ยงสูง ต้องออกแบบกับเจ้าของ `EditorShell.jsx` แต่ผลกระทบหนักสุดในแง่งานหาย (แก้หลัง render ไม่ถูกบันทึกจนกว่าจะ reload) ควรเริ่มจากแค่ข้อ 3 (ปุ่มโหลดใหม่ + ไม่กลืน 409 ตอนปิดแท็บ) เป็นก้าวแรกที่เสี่ยงต่ำ

## ไฟล์ที่อ่านเป็นหลักฐาน (ค้นด้วยชื่อฟังก์ชัน)
`frontend/src/components/SequencePlayer.jsx` (`drawSingleCue`, `ghostRevealSegments`, `splitRevealByLines`, `drawVideoFrame`, `drawIsolatedFrame`), `frontend/src/hooks/useEditorCommands.js` (`patchCaption`, `handleSplitCue*`, `handleMergeCue*`), `frontend/src/lib/editorProjectState.js`, `frontend/src/lib/projectRevision.js`, `frontend/src/api.js` (`updateProjectState`), `frontend/src/hooks/useProjectAutosave.js`, `frontend/src/hooks/useRenderJob.js`, `frontend/src/components/editor/EditorShell.jsx` (`handleRenderComplete`, `applyLoadedProject`), `frontend/src/lib/subjectFrameMapping.js`, `scripts/subtitle_engine.py` (`generate_micro_cues`, `generate_ass`), `scripts/subtitle/word_reveal.py`, `scripts/api_phase1.py` (`get_project`, `update_project_state`, `trigger_reroll`), `scripts/project_manifest.py` (`project_revision`), `scripts/render_jobs.py` (`finalize_incremental_render`), `scripts/stages/video_assembly_stage.py` (อ่านอย่างเดียว), `scripts/video_editor.py` (`frame_geometry`, `framing_filters`, `dynamic_camera_filter`, `assemble_tiktok_video`)
