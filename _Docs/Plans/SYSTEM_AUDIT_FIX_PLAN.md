# SEC-AUDIT-1 — System Audit Fix Plan (Parallel Streams)

วันที่: 2026-09-09
สถานะ: planning — รอ signal ว่า codex agent เสร็จ/แตะไฟล์ไหนบ้าง ก่อนยิง stream ขนาน
อ้างอิง: [SYSTEM_AUDIT_2026-09-09.md](SYSTEM_AUDIT_2026-09-09.md) (รายงานเต็ม 4-agent audit)
คำสั่ง: user อนุญาตแยก agent ขนานเมื่อ write scope ไม่ทับกัน (เหมือน PERF-UX-1)

## Objective

ปิดช่องโหว่ security (API เปิดโล่ง, path traversal), บั๊ก data-integrity ตระกูล dual-source-of-truth (sticker resurrection ที่แก้ไปแล้วเป็นแค่ประตูเดียว), และ transaction/concurrency hazard ในชั้น data store — โดยไม่ทำให้ระบบ render/editor พังระหว่างทาง

## Pre-flight (ทำก่อนยิง stream ไหนทั้งนั้น)

- [ ] เช็คว่า codex agent แตะไฟล์อะไรบ้าง (`git status`, `git diff`) กัน scope ชนกับ stream ด้านล่าง
- [ ] `git status` ต้องสะอาดหรือรู้ diff ค้างทั้งหมดก่อนแบ่งงาน — ห้าม reset/checkout ทับ diff ที่มีอยู่

## Phase 0 — Security config (ทำทันที, sequential, ไม่ใช่ code fix)

Write scope: `.env`, `frontend/.env` (สร้างใหม่ถ้ายังไม่มี), `.gitignore`

- [ ] C1 — ตั้ง `OMNICUT_API_KEY` (backend) + `VITE_API_KEY` (frontend `.env`) ด้วย `secrets.token_urlsafe(32)`
- [ ] H1 — เพิ่ม `_Docs/post_log.json`, `_Docs/schedule_queue.json`, `_Docs/schedule_templates.json` ลง `.gitignore` (ให้เหมือน `products.json`/`export_registry.json` ที่ ignore อยู่แล้ว)
- [ ] cleanup — ลบ `GEMINI_API_KEY_OLD` ออกจาก `.env` (revoke ที่ AI Studio ก่อน), เติม `#` ที่ `.env:4`, เพิ่ม `temp_ecc/` ลง `.gitignore`

ไม่ต้องใช้ agent แยก — แก้เองได้ใน 1 รอบ ไม่มี merge risk

---

## Phase 1 — Parallel streams (write scope ไม่ทับกัน)

| Stream | Write scope (ไฟล์) | ปิด finding | Risk |
|---|---|---|---|
| **A — Upload & path containment** | `scripts/api_videos.py`, `scripts/api_render.py`, `scripts/api_voice.py`, `scripts/api_covers.py` | C2, C6, MED(upload RAM read `:585`), MED(sticker badge path `api_render.py:53-57`), MED(`api_voice.py:297-308` media_path), MED(`api_covers.py:734-736` export_filename) | กลาง — endpoint หลายตัว แต่ fix เป็น pattern เดียวกันซ้ำ (`.name` strip + containment check ที่มีตัวอย่างถูกอยู่แล้วใน `api_videos.py:231` และ `api_videos.py:37`) |
| **B — Manifest lock & SSRF** | `scripts/api_phase1.py`, `scripts/project_manifest.py`, `scripts/render_jobs.py` | C4, H12, H6, MED(`project_manifest.py` dir_for containment), MED(`render_jobs.py:312-316` merge-under-lock), MED(`render_jobs.py:92` log cap, `:133` slot timeout) | สูง — `project_manifest.py` เป็นจุดกลางที่ render pipeline ก็เขียนด้วย ต้องมี regression test เซฟ/โหลด manifest ให้ครบ |
| **C — Render engine safety** | `scripts/video_editor.py`, `scripts/stages/shot_matching_stage.py` | C3, H13, H7, MED(readline loop `:1172`), MED(atexit/process kill `:1211-1238`) | สูง — แตะ ffmpeg subprocess โดยตรง ต้องรัน render จริงทดสอบ ไม่ใช่แค่ unit test |
| **D — Data store transactions** | `scripts/db.py`, `scripts/product_store.py`, `scripts/api_schedule_queue.py`, `scripts/api_tiktok_autopost.py`, `scripts/api_exports.py` | C7, C8, H8, H9, MED(N+1 `api_schedule_queue.py:595-603`), MED(cross-store atomicity `api_exports.py:703-708`), MED(`db.py` `get(id)` query perf) | สูง — transaction nesting เป็นบั๊กเดิมที่เคย fix บางส่วน (ac3a3ea) ต้องมี test ที่ nest จริงเหมือนที่ H8 บอกว่ายังไม่มี |
| **E — Background stores (locks)** | `scripts/asset_registry.py`, `scripts/hook_styles.py`, `scripts/token_tracker.py`, `scripts/task_manager.py` | H10, H11, MED(unlocked write pattern ซ้ำ 3 จุด), MED(truncating write fallback `task_manager.py:239`) | ต่ำ — pattern เดียวกันซ้ำๆ (เพิ่ม lock + unique tmp name), ไม่กระทบ render/editor โดยตรง |
| **G — Editor shell reliability** | `frontend/src/components/editor/EditorShell.jsx` | C5, H3, MED(trackMix เข้า undo history) | สูง — ไฟล์กลางของ editor ต้องเทส add/update/delete sticker + reroll flow ทั้งหมดใหม่ |
| **H — Editor data serialization** | `frontend/src/lib/editorProjectState.js`, `frontend/src/lib/overlayBoxGeometry.js` | H2, MED(cue scale/x/y/position หายตอน reload), MED(transition clip 0 หาย), MED(selection fallback ผิด sticker) | กลาง — ต้องเทส round-trip save→load ให้ field ไม่หาย โดยเฉพาะ `micro_cues` ที่ข้อมูลจริงเสียไปแล้ว 7 project ต้องคิดเรื่อง data recovery ด้วย ไม่ใช่แค่ fix โค้ด |
| **I — Save-failure visibility** | `frontend/src/hooks/useProjectAutosave.js`, `frontend/src/lib/projectSaveQueue.js`, `frontend/src/components/editor/EditorHeader.jsx` | H4, H5 | ต่ำ — เพิ่ม error surface + retry, ไม่เปลี่ยน happy-path behavior |
| **J — Mechanical cleanup** | `requirements.txt`, `start_app.bat`, `frontend/postcss.config.js`, `scripts/db.py` (docstring only), ลบ `temp_ecc/`, `scratch/`, `frontend/dist/` | venv, LOW(postcss double config), LOW(db.py docstring), disk cleanup | ต่ำ — ไม่แตะ logic เลย ทำเมื่อไหร่ก็ได้ |

### หมายเหตุ dependency ระหว่าง stream

- Stream A เรียก `ProductStore._mutate()` (context manager) ที่ Stream D อาจต้องสร้าง/แก้ให้รองรับ C7 — ถ้า Stream D ยังไม่เสร็จ ให้ Stream A fix แค่ C2 (filename) ก่อน แล้วค่อยกลับมา wrap C7 ทีหลัง (ไม่ block กัน เพราะคนละ finding ในไฟล์เดียวกัน)
- Stream G (H3 sticker phantom) กับ Stream H (selection fallback) แก้ปัญหาคนละมุมของ resurrection เดียวกัน — ควรรวม test case เดียวกันตอน integrate: "ลบ sticker ตัวสุดท้าย → ไม่มีทางกลับมาได้จากทุกทาง"
- Stream C (C3, sticker isinstance ที่ `video_editor.py:873`) คือฝั่ง render ของบั๊กเดียวกับ Stream G/H — ทั้งสามฝั่งต้อง merge พร้อมกันไม่งั้นปิดไม่ครบ

---

## Phase 2 — Deep fix (sequential, หลัง Phase 1 merge เสร็จ, ไม่ขนาน)

**Root cause consolidation**: style scalar หนึ่งค่าเก็บซ้ำ 6 ที่ (root/`style`/`render_params` × camelCase/snake_case) + `firstPresent()` ข้าม `null` ทำให้ "ล้างค่า" เป็นไปไม่ได้เชิงโครงสร้าง + `video_assembly_stage.py:172-212` เขียน `render_params` ใหม่ทั้งก้อนทุกครั้ง render (ลบ `effects`/`track_mix`/`hook_*`/`sticker_badge` ทิ้งทุกรอบ)

Write scope: `scripts/stages/video_assembly_stage.py`, `scripts/pipeline_context.py`, `frontend/src/lib/editorProjectState.js` (รอบสอง หลัง Stream H merge แล้ว)

- [ ] ตัดสินใจ single source of truth ต่อ field (ไม่ generate เอง — ต้องคุยกับ user ว่าจะยึด root หรือ `render_params` เป็นหลัก)
- [ ] แก้ `firstPresent` ให้แยก "ไม่มีค่า" กับ "ตั้งใจ clear เป็น null" ออกจากกัน
- [ ] แก้ `video_assembly_stage.py` ให้ merge เข้า `render_params` เดิมแทนการสร้างใหม่ทั้งก้อน
- [ ] เขียน migration/repair script สำหรับ 7 project ที่ `cues`/`micro_cues` ถูกทับไปแล้วจริง (H2) — ถ้ากู้คืนจาก git history เก่าได้ (มี `.bak` หรือ commit ก่อนหน้า)

ไม่ขนานกับ Phase 1 เพราะแตะไฟล์เดียวกับ Stream B/H และเป็นการเปลี่ยน data contract จริง ต้อง regression เต็มก่อน

---

## Integration order

1. Phase 0 (config) ก่อนเสมอ — ไม่ block ใคร
2. Phase 1 streams A–J ยิงขนานได้ทั้งหมด (write scope แยกกันแล้ว)
3. Merge ตามลำดับ: A/E/I/J (risk ต่ำ-กลาง, ไฟล์ไม่ทับใคร) → B/D (data layer, merge คู่กันเพราะ A พึ่ง D) → C/G/H (sticker resurrection 3 ฝั่ง merge พร้อมกัน + regression test เดียวกัน)
4. รัน full test suite (`pytest`, `npm test`, `npm run build`) หลังหยุด parallel writes
5. Phase 2 deep fix เริ่มได้หลัง Phase 1 merge เสร็จหมดเท่านั้น

## Safety gates

- ไม่ติ๊ก `[x]` เพราะแก้โค้ดเสร็จ ต้องมี command output จริง (pytest/npm test ผ่าน)
- Stream ที่แตะ render (C) ต้องรัน render จริง 1 คลิปขั้นต่ำ ไม่ใช่แค่ unit test
- Stream ที่แตะ save/load (H) ต้องเทส round-trip: save → reload → field ต้องเหมือนเดิมทุกตัว
- Stream G/H/C (sticker resurrection 3 ฝั่ง) ต้องมี regression เดียวกันครอบทั้ง 3 จุด ก่อนถือว่าปิด
- ทุก commit ต้องตรวจ `git diff --check` และ file ownership ตามตารางบนนี้ ห้ามข้าม scope ของ stream อื่น
