# Audit: การตัด / animation / สไตล์ตัดต่อ (2026-10-04)

ดำเนินการโดย: Claude Code (Claude Sonnet 5.5) + sub-agent อ่านโค้ด 3 ตัว (Explore)
ขอบเขต: logic ตัดอัตโนมัติ · animation/transition · UX ตัดมือบน timeline — **อ่านโค้ดอย่างเดียว ไม่ได้เรนเดอร์/กดใน browser**
ต่อจากรายงานเดิม `CAPCUT_EDITOR_GAP_20261003/` (ปุ่มหลอก/undo/คีย์ลัดที่แก้แล้ว ไม่รายงานซ้ำ)

สัญลักษณ์: ✅ = ผู้ประสานงานเปิดโค้ดยืนยันเอง · ⬜ = คำของ agent ยังไม่ได้ตรวจซ้ำ (เลนที่แก้ต้องตรวจก่อนแก้)

## A. Bug จริงในการตัดอัตโนมัติ (`scripts/stages/shot_matching_stage.py`)

| ID | สถานะ | ปัญหา | ตำแหน่ง |
|---|---|---|---|
| A1 | ✅ | `motion_times` มาจากวิเคราะห์ raw footage (`:524-528`) แต่ถูกเทียบกับ `boundary_times`/`v_start`/`v_end` ซึ่งเป็นเวลา timeline (`:683`, `:718-720`) · `raw_offset` คำนวณทีหลัง (`:747/:760`) ผลคือ motion snap และ emphasis zoom ดูผิดช่วงฟุตเทจ | `:524-528, 680-720` |
| A2 | ✅ | BGM ถูก `atempo` 0.92–1.08 (`sfx_manager.py:359-368`, `tempo_ratio` จาก chars/sec ของ cue) แต่ `beat_times` มาจากเพลงก่อนปรับ (`:504`) → beat grid เลื่อน (ratio 1.08 ที่ t=15s ≈ 1 วิ) | `shot_matching_stage.py:500-506, 691-700`; `sfx_manager.py:355-368` |
| A4 | ⬜ | AI shot ถูกแบ่งเป็น 2 กลุ่มใช้ `start_time` เดียวกัน (`end_time` ถูกมองข้าม) → ฟุตเทจเล่นซ้ำ; Gemini ขอ shot 2–6s แต่ MAX_SHOT 2.5s | `:29-73, 741-747`; `gemini_vision_matcher.py:912` |
| A5 | ⬜ | จุดตัดวางตามความยาว (MIN_SHOT 1.5s) ไม่ใช่จบประโยค → ตัดกลางประโยคได้ ขัด Strict Topic Hold; `sentence_end` (`:782`) แค่ปรับความยาว transition | `:583-598, 782` |
| A6 | ⬜ | ตัดเร็วกว่าที่ตั้งใจ: legacy path shot แรกเริ่มที่ `first_cue_start` (`:555`) แต่คลิปต่อกันจาก t=0 ไม่มี head pad และเสียงไม่ถูกเลื่อน ถ้า > 0.18s ภาพเปลี่ยนก่อนประโยค (ตรงข้าม J-cut) — **ต้องวัดด้วย ffprobe/เฟรมก่อนยืนยัน** | `:548-562` |
| A7 | ⬜ | pacing path ไม่มี J-lead (`:571`); whoosh วางที่ cue start −0.12s ไม่ใช่ขอบคลิปจริง (`sfx_manager.py:306-310`); style budget ถูกข้ามเมื่อทุก boundary เป็น cut (`video_assembly_stage.py:44-62`) | หลายที่ |

## B. Bug ฝั่ง render / preview / editor

| ID | สถานะ | ปัญหา | ตำแหน่ง |
|---|---|---|---|
| B1 | ✅ (โค้ด) / agent วัดด้วย ffmpeg 8.1.1 | Ken Burns รูปนิ่ง: `-loop 1 -t dur` คู่ `zoompan d=frames` → agent วัดได้ 3001 เฟรม (~100 วิ) แทน 2 วิ; ผลปลายทางยังไม่ได้ trace; input 960x1280 ไม่ pre-upscale (zoompan jitter) และ zoom linear | `scripts/image_motion_engine.py:143-181` |
| B2 | ✅ (handler มีจริง) | `hooks/useKeyboardShortcuts.js` ระดับ App จับ Space → toggle `<video>` ตัวแรกที่ width/height > 0 (รวม decode video 1px ใน `SequencePlayer.jsx:5235`) ซ้อนกับ handler ของ editor; Ctrl+S ซ้อนกับ `handleManualSave` (`EditorShell.jsx:1614`) — ผล runtime ยังไม่ได้ทดสอบ | `frontend/src/hooks/useKeyboardShortcuts.js:53-71` |
| B3 | ⬜ | `motion_ass_adapter.py:75-83` map ease_out → accel 0.5 (t^0.5) ขณะที่ `rendererAdapter.js:147` และ `motion_contract.py:165` ใช้ t(2−t); ease_in_out/sine_in_out/spring ถูกส่งเป็น linear เงียบๆ (opt-in path) | `scripts/motion_ass_adapter.py:75-83` |
| B4 | ✅ | `splitClipAt` คัดลอก `keyframes` ไปทั้งสองครึ่งโดยไม่แบ่งเวลา (keyframe เป็นเวลา local ของคลิป) → ครึ่งขวาเริ่ม ramp ซูมใหม่ ภาพกระโดดที่รอยตัด (L1-14 ที่ยังเปิด) | `frontend/src/lib/timelineMath.js:248-261` |
| B5 | ⬜ | ไม่มีการปัดเวลาเป็นกริด 1/30: cut ปัด ms (`shot_matching_stage.py:562,690`), clip duration/xfade offset ไม่ปัด (`video_editor.py:1653-1654`, `timelineMath.js:142`) → drift สะสมต่อ boundary; shake step 90ms / glitch 40ms ใกล้ 1 เฟรม | หลายที่ |

## C. ยกระดับ (ฟีเจอร์ — ยังไม่ทำ)

1. **Easing:** camera keyframe ทั้ง preview (`timelineMath.js:43-62`) และ render (`video_editor.py:884-903`) ไม่ใช้ `easing`; `keyframe_engine.py`/`keyframeModel.js` เป็นโค้ดที่ไม่ถูกเรียก; transition progress linear (`timelineMath.js:210`); bounce default เป็น linear segments (`motion_effects.py:79-94`)
2. **Cut rhythm ต่อสไตล์:** `style_motion_policy.py:33-185` ปรับแค่ transition+camera; MIN/MAX_SHOT (`config.py:104-105`), J-lead, snap tolerance เป็นค่าคงที่ร่วม
3. **ตัดตรงคำ:** cue ไม่ word-accurate (RMS block + แบ่งตามจำนวนตัวอักษร `voice_stage.py:83-225`); `editorial_pacing.py` ใช้ได้เฉพาะเมื่อมี `word_timings` ซึ่งมีแค่ edge-tts (`voice_engine.py:402`) → ทางเบา: snap จุดตัดไป RMS ต่ำสุด ±80ms ของเสียงพากย์
4. **Transition ตามทิศ pan:** ตอนนี้สลับ slideleft/right ตามลำดับ (`style_motion_policy.py:233-235`)
5. **Timeline มือ:** ไม่มี rolling/slip/slide/overwrite, ripple แค่ `clipList` (cue/overlay/voice ไม่ขยับ, `useEditorCommands.js:131`), ไม่มี multi-select, ไม่มี Q/W trim-to-playhead, ไม่แสดงเฟรมขอบตอน trim, scrub ไม่ snap, filmstrip memo ไม่ถูกใช้ (`EditorShell.jsx:1091`), zoom 5 ระดับ (frame tick โผล่ที่ 200px/s เท่านั้น), MIN_CLIP_DURATION 0.2s
6. **ไว้ทีหลัง (L):** cut-on-action ด้วย optical flow, speed ramp, motion blur, eased xfade (`transition=custom:expr=`), J/L-cut บน timeline, ซับ pop 125%→100% ตาม `subtitle_kinetic_rules.md` §1.2 (ปัจจุบัน alpha fade 70ms — ตั้งใจเพราะวรรณยุกต์)

## D. ที่ทำงานถูกอยู่แล้ว (ไม่ต้องแตะ)
Split snap เฟรม · trim handle snap + undo 1 ก้าว · snapping ต่อ playhead/ขอบคลิป/cue/beat · transition 14 แบบ geometry ตรง ffmpeg · ซับ/overlay motion preview↔render ใช้สูตรเดียวกัน · timecode mm:ss:ff · `coalesceKey` ของ slider ต่อสายแล้ว
