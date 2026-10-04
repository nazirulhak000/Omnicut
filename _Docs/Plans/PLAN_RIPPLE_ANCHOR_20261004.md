# แผนออกแบบ: Ripple Delete แบบตัดเสียงพากย์ + เลื่อนซับ/overlay ให้ตรงกัน (Round EDITOR-CUT-QUALITY-R3 · เลน RD)

วันที่: 2026-10-04 · ดำเนินการโดย: Claude Code (Claude Opus 5.5) — เลน RD ออกแบบ อ่านโค้ดอย่างเดียว
สถานะ: แผน รอ review ก่อนเปิดเลน RI · ไม่มีการแก้โค้ด/เทสในเลนนี้
Jev (choice A/B/C ของข้อ 3): เลือก **B** confidence **0.76 (< 0.80 → escalate)** — เป็นคำแนะนำ ไม่ใช่การอนุมัติ ต้องให้ user ยืนยัน (ดูข้อ 8 ข้อ D1)

> เลขบรรทัดอ้างจาก working tree วันที่ 2026-10-04 ไฟล์ที่มี diff ค้างของ session อื่น (ดูข้อ 7.5) เลขอาจขยับ ให้ Grep ชื่อ symbol ก่อนแก้เสมอ

---

## 0. สรุปสั้น

- ปัญหา: ripple ตอนนี้แก้แค่ `clipList` แต่เสียงพากย์เป็นไฟล์เดียว และ render ยาวเท่าเสียง → ภาพสั้นลง ซับ/SFX/overlay ยังอยู่ที่เดิม ทุกอย่างหลังจุดตัดหลุดซิงก์กับภาพ
- คำแนะนำ (ต้องให้ user ยืนยัน): **แบบผสม (B)**
  1) ตัวไฟล์เสียงพากย์ **ไม่แตะเลย** เก็บรายการช่วงที่ตัด `voice_edit.cuts` (หน่วยเวลาของไฟล์เสียงต้นฉบับ) แล้วไปตัดตอนมิกซ์ (ffmpeg `atrim`+`concat`) และตอน preview (WebAudio)
  2) เวลาของซับ/คำ/overlay/sticker/effect/คลิป **เขียนใหม่ในสถานะของ editor** ด้วย `set()` ครั้งเดียว → Ctrl+Z ครั้งเดียวย้อนได้ทั้งหมด ส่วนที่อ่านเวลาอยู่แล้วไม่ต้องรู้จัก cut เลย
  3) ฟังก์ชันแปลงเวลาตัวเดียว มีคู่ JS/Python ให้ผลเท่ากัน และมีเทส parity ผ่าน node
- anchor `{clip_id, offset}` **ยังไม่จำเป็นสำหรับเฟสแรก** เพราะการตัดเป็นช่วงเวลาครอบทุกเลนอยู่แล้ว ไว้เฟส 2 ตอนทำย้ายลำดับคลิป/ripple เฉพาะภาพ (เหตุผลในข้อ 2.7)

---

## 1. โครงข้อมูลปัจจุบัน (ตรวจกับโค้ดแล้ว)

### 1.1 Manifest และการโหลด/บันทึกใน editor
- โหลด: `frontend/src/lib/editorProjectState.js:66` `manifestToEditorState()`
  - `clipList` จาก `manifest.clip_list` (:74) — **ไม่มีเวลาบนไทม์ไลน์เก็บไว้** ตำแหน่งคำนวณจากลำดับ+trim+speed+transition ด้วย `buildSegments()` (`timelineMath.js:172`) วางบนกริดเฟรม 1/30 (`planSequenceFrames` :215)
  - `id` ของคลิป **สร้างใหม่ทุกครั้งที่โหลด** (`EditorShell.jsx:791` `createClipId: () => newId()`) และ `serializeClips()` (:273) ตัด `id` ทิ้งตอนบันทึก (มีเทสยืนยัน `editorProjectState.test.js:39`) → ตอนนี้ **ไม่มี id คลิปที่คงที่ข้ามการโหลด** ซึ่งทำให้ anchor ต่อคลิปทำไม่ได้ถ้าไม่เพิ่มฟิลด์ใหม่
  - `cuesList` จาก `manifest.cues` หรือ `micro_cues` (:112) เป็น `{start,end,text,sfx,...}` เวลาแบบ absolute และเก็บฟิลด์อื่นไว้ทั้งหมดด้วย spread (:118) เช่น `word_reveal`, `word_timings`
  - `microCuesList` (:257) — **อยู่นอก history** (`EditorShell.jsx:528` `useState`) และ `editorStateToSavePayload` ส่ง `micro_cues` จาก `microCuesList` ถ้ามี (:367)
  - `stickers` (:176-214), `effects` (:216-240) เป็น `{id,start,end,normX,normY,...}` absolute
  - `overlays` (:258) ผ่าน `migrateToOverlays` เป็น `{start,end,sfx?,...}` absolute (ฝั่ง render อ่านที่ `scripts/subtitle/overlay_events.py:637-641`, hook `:265-266`)
  - `audioDuration` = `manifest.audio_duration || total_duration` (:265), `mixedAudioPath`/`voiceAudioPath` จาก `manifest.artifacts.*.path` (:268-269)
- บันทึก: `editorStateToSavePayload()` (`editorProjectState.js:363`) → `PATCH /api/projects/{name}/state` (`scripts/api_phase1.py:859` `update_project_state`) ผ่าน `ProjectManifest.save_merge` (rolling backup `.json.bak1-3` ใน `scripts/project_manifest.py:230-248`)
  - **Pydantic ทิ้งฟิลด์ที่ไม่ได้ประกาศเงียบ ๆ** (คอมเมนต์ `api_phase1.py:838-841`) → ฟิลด์ใหม่ (`voice_edit`) ต้องประกาศใน `UpdateProjectStateRequest` (:830) ไม่งั้นหายเงียบ
- History: `useEditorHistory(EMPTY)` (`EditorShell.jsx:206`) state = `clipList, cuesList, overlays, stickers, effects, spotlight, backgroundIsolation, trackMix, style` (`EMPTY` :179) — `set()` ครั้งเดียว = undo ครั้งเดียว

### 1.2 เวลาของคำ (Ghost Reveal)
- cue มี `word_reveal: [{text,start,end}]` absolute สร้างที่ `scripts/subtitle/word_reveal.py:134` `build_word_reveal()` และอาจมี `word_timings` (edge-tts) absolute
- ASS ใช้ `word_reveal` ที่เก็บไว้ถ้าข้อความตรงกัน ไม่งั้นสร้างใหม่จาก `cue.start/end` (`scripts/subtitle_engine.py:1102-1111`)
- ฝั่ง editor มี `retimeReveal`/`reconcileCueReveal` ใน `frontend/src/lib/captionEdits.js` (:70-82) ใช้ตอนลาก cue

### 1.3 เสียงพากย์ / ความยาว
- `scripts/stages/voice_stage.py:302` `VoiceStage.run` สร้าง `voiceover.wav` ในโฟลเดอร์โปรเจกต์ (เสียงคนจริงถูก copy มาจากต้นทาง :375-387) และตั้ง `ctx.total_duration` = ความยาวเสียง (:526) ตอน reuse อ่าน `manifest["total_duration"]` (:371)
- render ตัดความยาวตามเสียง และถ้าภาพสั้นกว่าจะค้างเฟรมสุดท้าย `scripts/video_editor.py:2032-2044` (`tpad=stop_mode=clone`)

### 1.4 มิกซ์เสียง (render)
- `scripts/stages/audio_mix_stage.py:76-83` เรียก `SFXManager.mix_audio_track(voice_audio_path, cues=ctx.micro_cues, total_duration, overlays=ctx.effective_overlays, ...)` เฉพาะตอน `export_mp4` (:43-46)
- `scripts/sfx_manager.py:248` กราฟ: เสียงพากย์ `[0:a]volume=…,apad=pad_dur=1.0` (:297-302) (มี `asplit` เป็น sidechain key ตอน ducking) · boom ที่ 0 (:305-310) · SFX ต่อ cue ด้วย `adelay` จาก `cue.start` และ pre-roll 0.12 s สำหรับ whoosh (:315-332) · SFX ต่อ overlay (:336-355) · BGM `-stream_loop -1`, `atempo` จาก `bgm_tempo_ratio(cues)`, `atrim=0:total+0.5`, fade out 0.35 s (:357-395) · `amix duration=first` + loudnorm (:406-409) · `-t total+0.2` (:420)
- **SFX ไม่มีรายการแยก** มาจาก `cue.sfx` และ `overlay.sfx` → ถ้าเวลา cue/overlay ถูกเลื่อน SFX เลื่อนตามเองทั้ง render และ preview
- Reuse ตัดสินด้วย fingerprint: `scripts/pipeline_context.py:304-322` (mix ใช้ `voice_audio` fingerprint, `micro_cues`, `total_duration`, `overlays`, bgm…) · subtitles ใช้ `cues` (:273-302) → แก้ cues แล้ว subtitles รันใหม่และสร้าง `micro_cues` ใหม่จาก cues (`scripts/stages/subtitle_stage.py:145-168`)

### 1.5 Preview เสียง (`frontend/src/components/SequencePlayer.jsx`)
- `AUDIO_MIX` (:388) · stem: เสียงพากย์เล่นบน `<audio>` (`audioElRef`, render :5218-5222) ต่อเข้า WebAudio ด้วย `createMediaElementSource` (:4433) · BGM บน element ที่สอง loop + `playbackRate = bgmRate` (:4605-4613) · SFX เป็น `AudioBufferSourceNode` ตั้งเวลาล่วงหน้า (`pumpSfx` :4515)
- **เสียงพากย์เป็น master clock**: `tick()` อ่าน `t = audio.currentTime` (:4887-4895) และ seek `audio.currentTime = t` (:4588, :4908) → สมมติว่าเวลาไฟล์เสียง = เวลาไทม์ไลน์ 1:1 ซึ่ง **จะผิดทันทีที่มี cut**
- ducking ใน preview ใช้ช่วง cue แทนการ sidechain (:4555-4583) และ fade ท้ายจาก `totalDuration`
- รายการ SFX ของ preview สร้างที่ `EditorShell.jsx:2216-2280` จาก `cuesList[].start` + `overlays[].start` + boom ที่ 0

### 1.6 Ripple ที่มีอยู่ตอนนี้
- ลบคลิป: `useEditorCommands.js:189-194` กรอง `clipList` อย่างเดียว · Q/W trim: `:125-135`
- ตัดช่วงเงียบ: `frontend/src/lib/silenceRipple.js` (plan :68 / describe :192) ใช้กับ `clipList` อย่างเดียว และช่วงเงียบกลางคลิป **ตัดจากท้ายคลิป ไม่ใช่ตำแหน่งจริง** (:117-129) · ตรวจเงียบจาก `voiceover.wav` ผ่าน `GET /api/audio/silences` (`scripts/api_audio_beats.py:147-189`, อ่านอย่างเดียว) · dialog ยืนยัน `EditorShell.jsx:2400-2446`, handler `:1226-1263`
- Magnetic ripple ของซับ (`useTimelineDrag.js:177-183`, `applyCaptionMagneticRipple`) เลื่อนซับโดยไม่แตะเสียง → หลุดซิงก์แบบเดียวกัน (นอกขอบเขตรอบนี้ แต่ควรบันทึก)

### 1.7 Reroll
- `POST /api/reroll` (`api_phase1.py:1276`) part: `hook/subtitles/video/voice/bgm/script` (`REROLL_COST` :558) — `voice`/`script` สังเคราะห์เสียงใหม่ → cues ใหม่ + `total_duration` ใหม่
- editor สั่ง render ด้วย `part: audioDirty ? 'bgm' : 'subtitles'` (`EditorShell.jsx:2119`) แล้ว fingerprint ตัดสินว่า stage ไหนต้องรันจริง

### 1.8 สิ่งที่ตรวจไม่ได้ในรอบนี้
- ไม่ได้เปิดดูเสียงจริงใน Chrome · ไม่ได้ตรวจ sample rate ของไฟล์ Gemini TTS ทุกโปรเจกต์ (สมมติ 24 kHz; ข้อ 4.2 ออกแบบให้ไม่ขึ้นกับค่านี้) · ไม่ได้อ่าน `useEditorHistory` ทั้งไฟล์ (อาศัยคอมเมนต์ใน `useEditorCommands.js:69-79,191`) · ไม่ได้ตรวจเส้นทาง CapCut draft export ว่าอ่าน cue/voice อย่างไร (ต้องให้เลน RI ตรวจ ถ้ามี export ไป CapCut ต้องส่งเสียงที่ตัดแล้ว)

---

## 2. สเปก `rippleDeleteRange([t0, t1])`

### 2.1 อินพุต
- `t0 < t1` เป็น **เวลาโปรแกรม** (เวลาบนไทม์ไลน์ที่ผู้ใช้เห็น) snap เข้ากริด 1/30 s ด้วย `snapToFrame` (`timelineMath.js:539`) ช่วงต้องยาว ≥ 1 เฟรม
- ขอบเขต: `scope = 'all'` (ภาพ+เสียงพากย์+ซับ+ทุกเลน, ค่าเริ่มต้นใหม่) หรือ `'video'` (พฤติกรรมเดิม แก้คลิปอย่างเดียว)
- ให้ `d = t1 - t0` และฟังก์ชันแปลงเวลา (ตัดครั้งเดียว):
  ```
  shift(t) = t            ถ้า t <= t0
           = t0           ถ้า t0 < t < t1     (ยุบ)
           = t - d        ถ้า t >= t1
  ```

### 2.2 ผลต่อแต่ละอย่าง (scope = 'all')
| สิ่งของ | กติกา |
|---|---|
| `clipList` | คลิปอยู่ในช่วงทั้งก้อน → ลบ · คร่อมขอบซ้าย → ตัดหาง · คร่อมขอบขวา → ตัดหัว · ช่วงอยู่ **กลางคลิป** → แยกคลิปที่ t0 และ t1 ด้วย `splitClipAt` (:350, รองรับ keyframes) แล้วทิ้งชิ้นกลาง (ไม่ตัดจากท้ายแบบ `silenceRipple.js` เดิม เพราะภาพจะผิดตำแหน่ง) · แปลงเวลาโปรแกรมเป็นเวลาต้นทางด้วย `× speed` · ส่วน `freeze_tail` ถูกตัดก่อนเนื้อคลิป |
| ทรานซิชัน | ถ้า t0/t1 ตกในช่วงซ้อนของ xfade ให้ **ขยายช่วงออกไปถึงขอบช่วงซ้อน** (แสดงในหน้ายืนยัน) · ทรานซิชันที่อยู่ในช่วงหายไปกับคลิป · รอยต่อใหม่ที่เกิดจาก ripple = `cut` เสมอ · คลิปแรกของไทม์ไลน์ห้ามมีทรานซิชันเข้า (กติกาเดิม `silenceRipple.js:159-163`) |
| เสียงพากย์ | เพิ่ม `{id, start: u0, end: u1}` ลง `voice_edit.cuts` โดย `u = programToSource(t)` (ข้อ 3) ไฟล์ไม่ถูกแตะ |
| ความยาวรวม | `total = source_duration − Σ(cut)` ใช้ทั้ง `audioDuration` ฝั่ง editor และ `ctx.total_duration` ฝั่ง render |
| cues (`cuesList` และ `micro_cues`) | `e <= t0` คงเดิม · `s >= t1` เลื่อน −d · อยู่ในช่วงทั้งหมด → **ลบ** (เสียงของคำนั้นถูกตัดไปด้วย) · คร่อมขอบ → `start = shift(s)`, `end = shift(e)` · คร่อมทั้งช่วง (s < t0 และ e > t1) → `end = e − d` และติดธง `ripple_text_cut: true` ให้เตือนในหน้ายืนยันว่า "ข้อความยังอยู่ แต่เสียงบางคำถูกตัด" (ห้ามแก้ข้อความ เพราะซับต้องใช้บททางการ, AGENTS.md ข้อ 17) · ผลยาว < 0.10 s → ลบ |
| `word_reveal` / `word_timings` | map ทุกคำด้วย `shift()` คำที่อยู่ในช่วงจะยุบเหลือความยาว 0 ที่ t0 (ยังมีข้อความครบ) แล้ว `reconcileCueReveal` ตรวจซ้ำ · ถ้าไม่ผ่าน `reveal_is_usable` ให้ลบ `word_reveal` ทิ้ง (backend สร้างใหม่จาก start/end เองตาม `subtitle_engine.py:1106`) |
| overlays / stickers / effects | กติกาเดียวกับ cue (ใช้เวลา absolute) · `hidden` คงเดิม · hook overlay ที่เริ่มที่ 0 ถ้า t0 = 0 จะถูกเลื่อน/ตัดหัวตามกติกา · ไม่มีการลบข้อความใดๆ เมื่อถูกตัดบางส่วน |
| SFX | ตามเจ้าของ (cue/overlay) อัตโนมัติ · boom ที่ 0 คงเดิม · SFX ที่เจ้าของถูกลบก็หายไปด้วย (แสดงจำนวนในหน้ายืนยัน) |
| BGM | **เล่นต่อเนื่องไม่ตัด** (แนะนำ) วางบนเวลาโปรแกรมตั้งแต่ 0 ยาวเท่า total ใหม่ — เสียงเพลงไม่กระโดด · ผลข้างเคียง: คลิปหลังจุดตัดอาจไม่ตรง beat grid เดิม (ดู D2) · `bgm_tempo_ratio(cues)` จะเปลี่ยนเล็กน้อยเพราะช่วง cue หดลง เกิดเท่ากันทั้ง preview/render เพราะทั้งคู่อ่านจาก cues |
| beat grid (`getBgmBeats`) | ไม่เปลี่ยน (เพลงไม่ถูกตัด) |
| playhead / selection | playhead ไปที่ t0 · ล้าง selection |

### 2.3 scope = 'video' (โหมดเดิม)
แก้ `clipList` อย่างเดียว เหมือน `deleteSelected` ปัจจุบัน แต่ให้ใช้ split ตามตำแหน่งจริงด้วยฟังก์ชันเดียวกัน · ไม่แตะเสียง/ซับ → ภาพสั้นกว่าเสียง render จะค้างเฟรมท้าย (พฤติกรรมเดิม) และต้องแสดงคำเตือนเดิมใน `ProjectInspector`

### 2.4 Declick ที่รอยต่อเสียง
- **fade ออก 8 ms ที่ท้ายช่วงก่อนตัด + fade เข้า 8 ms ที่หัวช่วงหลังตัด** ความยาวรวมไม่เปลี่ยน (ไม่ใช้ `acrossfade` เพราะมันหดเวลาเท่าความยาว crossfade → map เวลาไม่ตรง)
- ทดลองแล้วใน `.tmp/rd/` (ลบแล้ว): `atrim`+`asetpts`+`afade`+`concat` ให้ความยาว **ตรงทุก sample** (24 kHz: 6.0 s ตัด 1.5 s ได้ 108000 samples = 4.500 s พอดี) ส่วน `aselect='not(between(t,..))'` **หาย 864 samples** (ตัดตาม audio frame) → ห้ามใช้ `aselect`
- ขอบ 1/30 s ตรงกับจำนวน sample เต็มทั้ง 24k (800), 44.1k (1470), 48k (1600) → cut ที่ snap กริดเฟรมแล้วตัดได้ตรง sample ทุก rate ที่ใช้อยู่ (ทดลองที่ 44.1 kHz cut 2.0333 s: `start/end` แบบวินาที และ `start_sample/end_sample` ได้ 199920 samples เท่ากัน)

### 2.5 กรณีขอบ
- ตัดแล้วไม่เหลือคลิป หรือ total < 1 s → ปฏิเสธพร้อมบอกเหตุผล (เหมือน `silenceRipple.js:146-156`)
- ช่วงเลยท้ายเสียง (t1 > total) → clamp ที่ total
- ช่วงซ้อนกับ cut เดิม: แปลงเป็นเวลาต้นทางก่อนแล้ว merge (`mergeSpans` :37) ไม่มี cut ซ้อนกันใน manifest
- ภาพยาวกว่าเสียง (ช่วงอยู่หลัง total เสียง): ตัดแค่ภาพ ไม่เพิ่ม cut เสียง

### 2.6 Undo / Redo
หนึ่งคำสั่ง = `set()` ครั้งเดียว ที่เปลี่ยน `clipList, cuesList, microCuesList, overlays, stickers, effects, voiceEdit` พร้อมกัน → Ctrl+Z ครั้งเดียวคืนทั้งหมด (ต้องย้าย `microCuesList` และ `voiceEdit` เข้า history state, ดูเลน RM)

### 2.7 ทำไม anchor `{clip_id, offset}` ไว้เฟส 2
- การตัดเป็นช่วงเวลาใช้กติกาเดียวกับทุกเลน → ซับ/overlay ที่ "อยู่บนคลิปที่ถูกลบ" อยู่ในช่วงนั้นพอดี จึงถูกลบ/ตัดเหมือนกัน ไม่ต้องรู้ว่าผูกกับคลิปไหน
- anchor จำเป็นจริงตอน **ย้ายลำดับคลิป** หรือ **ripple เฉพาะภาพ** ที่อยากให้สติกเกอร์ตามคลิปไป ซึ่งต้องมี id คลิปคงที่ก่อน (ตอนนี้ไม่มี ข้อ 1.1) → เฟส 2: เพิ่มฟิลด์ `uid` ถาวรบนคลิป (ไม่ใช่ `id` เพื่อไม่ชนเทสเดิม) + `anchor: {clip_uid, offset}` แบบ optional บน overlay/sticker/effect; คลิปที่ anchor ถูกลบ → ของที่ anchor ถูกลบด้วยในโหมด 'all' และ "ปลด anchor เป็นเวลา absolute ที่ตำแหน่งเดิม" ในโหมด 'video'

---

## 3. วิธีเก็บข้อมูล: เทียบ 3 แบบ

นิยาม: `u` = เวลาในไฟล์เสียงต้นฉบับ, `t` = เวลาโปรแกรม

| เกณฑ์ | A: Non-destructive ทั้งหมด (ทุกเวลาเก็บเป็น u + `ripple_cuts`) | **B: ผสม (แนะนำ)** เวลาของทุกอย่างเป็น t ใน editor state + `voice_edit.cuts` เป็น u ใช้กับเสียงพากย์อย่างเดียว | C: Destructive (เขียน wav ใหม่ทุกครั้ง + เก็บไฟล์เก่าไว้ undo) |
|---|---|---|---|
| Undo/redo | ง่าย (history ของ JS) | ง่าย (`set()` ครั้งเดียว) | ยาก: undo ต้องสลับ artifact path และไฟล์ต้องมีอยู่จริง redo หลังแก้อย่างอื่นซับซ้อน |
| จุดที่ต้องแก้ | ทุกที่ที่อ่าน/เขียนเวลา (Timeline ลาก, Inspector, captionEdits, SequencePlayer วาดซับ/overlay, subtitle_engine, overlay_events, video_editor stickers/effects, sfx_manager) ~15 จุด ส่วนใหญ่อยู่ในไฟล์ที่มี diff ค้าง | 2 จุดเสียง (กราฟมิกซ์, preview เสียงพากย์) + ความยาว + โหลด/บันทึก | backend endpoint เขียนไฟล์ + editor ต้องรอเครือข่ายก่อนจะ preview ได้ |
| ของใหม่ที่เพิ่มหลัง cut | สับสนว่าเก็บเป็น u หรือ t | เป็น t ตามปกติ | เป็น t ตามปกติ |
| Save/load | ฟิลด์ใหม่ 1 ตัว | ฟิลด์ใหม่ 1 ตัว (`voice_edit`) | path artifact ใหม่ + ฟิลด์ประวัติ |
| Reroll เสียงใหม่ | cut ทั้งหมดใช้ไม่ได้ + เวลาทุกอย่างอยู่ใน u ของไฟล์เก่า | ล้าง `voice_edit` (เวลา t ของ overlay ยังอยู่ เหมือนพฤติกรรมทุกวันนี้ตอนพากย์ใหม่) | ล้างไฟล์ที่ตัด |
| Parity test | ต้องเทสทุก reader | เทส map 1 ฟังก์ชัน + เทสเสียงจริง 1 ชุด | เทสไฟล์ที่เขียน |
| ย้ายโปรเจกต์เก่า | ไม่มี cut = map เป็น identity | เหมือนกัน (ไม่มี `voice_edit` = เหมือนเดิมทุกไบต์) | เหมือนกัน |
| เสี่ยงข้อมูลหาย | ต่ำ | **ต่ำสุด**: wav ไม่ถูกเขียน, manifest มี backup อยู่แล้ว | กลาง: เขียนไฟล์บ่อย ถ้าเขียนทับ `voiceover.wav` = ผิดกฎห้ามทับเสียง |
| ประสิทธิภาพ | map ทุกเฟรม | ไม่มีงานเพิ่มต่อเฟรม; มิกซ์เพิ่ม `atrim` K ช่วง | ffmpeg ทุกครั้งที่ตัด |

**คำแนะนำ: B** เพราะ (1) ไฟล์เสียงไม่ถูกเขียนเลย ตรงกฎ "ห้ามลบไฟล์เสียงเดิมของ user" ใน TODO R3 (2) undo เป็นเรื่องของ JS state ล้วน (3) โค้ดที่อ่านเวลาอยู่แล้ว (ASS, overlay, sticker, SFX, ducking) ไม่ต้องแก้ ลดการชนกับ diff ค้างของ session อื่น (4) เทส parity มีจุดเดียว
ข้อเสียของ B ที่ต้องยอมรับ: ข้อมูลเวลาเดิมของซับก่อนตัดหายจาก manifest หลังบันทึก (กู้ได้จาก undo ในเซสชันเดียวกัน หรือ `.json.bak1-3`) — ถ้า user ต้องการ "กู้คืนช่วงที่ตัด" ข้ามเซสชัน ต้องเพิ่มใน `voice_edit.cuts[].removed` เก็บ snapshot ของสิ่งที่ถูกลบ (แนะนำทำ: เล็ก และทำให้ปุ่ม "คืนช่วงนี้" เป็นไปได้ภายหลัง)

### 3.1 สคีมาที่เสนอ
```json
"voice_edit": {
  "schema_version": 1,
  "source": {"path": "<artifacts.voice_audio.path>", "size": 123456, "mtime_ns": 0, "duration": 31.2},
  "cuts": [{"id": "cut-1a2b", "start": 4.0, "end": 4.6, "reason": "manual|silence"}]
}
```
- `cuts` เรียง ไม่ซ้อน ขอบอยู่บนกริด 1/30 ในหน่วย u
- `source` คือตัวกันความปลอดภัย: ถ้า fingerprint ไฟล์เสียงไม่ตรง (พากย์ใหม่แล้ว) **ห้ามใช้ cut** ทั้ง backend และ preview ตั้ง `voice_edit_stale = true` และแสดงแถบเตือน
- `total_duration` ใน manifest = ค่าหลังตัด (ผู้อ่านเดิมทุกตัวถูกต้องทันที) และ `source.duration` เก็บความยาวไฟล์จริง

---

## 4. Parity: preview = render

### 4.1 ฟังก์ชันแปลงเวลา (คู่ JS/Python)
- JS: `frontend/src/lib/voiceCutMap.js` (ใหม่) · Python: `scripts/voice_cut_map.py` (ใหม่) — ฟังก์ชันเดียวกันชื่อเดียวกัน:
  - `normalizeCuts(cuts, sourceDuration)` → snap กริด, merge, clamp
  - `keepRanges(cuts, sourceDuration)` → `[{srcStart, srcEnd, progStart}]`
  - `sourceToProgram(u, cuts)` (ยุบ u ที่อยู่ใน cut ไปที่ขอบ) · `programToSource(t, cuts)` (t ที่ขอบ → u ฝั่งหลังตัด)
  - `effectiveDuration(cuts, sourceDuration)`
  - `shiftTime(t, t0, t1)` + `rippleItems(items, t0, t1, opts)` สำหรับ cue/overlay/sticker/effect (ฝั่ง JS ใช้จริง ฝั่ง Python มีไว้ให้เทส parity และใช้กับ API ภายหลัง)
- ห้ามใช้ `round()` ต่างแบบ: ใช้ `Math.floor(x*30+0.5)` ให้ตรงกับ `sequenceFrameIndex` (`timelineMath.js:201`)

### 4.2 Render ตัดเสียงพากย์
- ใน `sfx_manager.mix_audio_track` เพิ่มพารามิเตอร์ `voice_cuts=None`; ถ้ามี cut แทนที่ต้นกราฟ `[0:a]volume=…` ด้วย
  ```
  [0:a]asplit=K[v0]..[vK-1];
  [v0]atrim=start=S0:end=E0,asetpts=PTS-STARTPTS,afade=t=out:st=E0-S0-0.008:d=0.008[k0];
  [v1]atrim=start=S1:end=E1,asetpts=PTS-STARTPTS,afade=t=in:d=0.008,afade=t=out:...[k1]; ...
  [k0]..[kK-1]concat=n=K:v=0:a=1,volume=…,apad=pad_dur=1.0[voice_padded]   (หรือ asplit=2 ต่อเมื่อ ducking)
  ```
  ช่วงแรกไม่ fade in ช่วงท้ายไม่ fade out · ไม่มี cut = สตริงกราฟเดิมทุกไบต์ (ต้องมีเทสยืนยัน)
- `audio_mix_stage.py` ส่ง `voice_cuts` จาก `ctx` · `pipeline_context.py` เพิ่ม `voice_edit` ใน payload ของ stage `mix` (:309-321) และใน snapshot (:729) ให้ fingerprint เปลี่ยนเมื่อ cut เปลี่ยน
- `voice_stage.py` ทาง reuse (:365-373): ถ้า `voice_edit` ใช้ได้ → `ctx.total_duration = effectiveDuration(...)`, `ctx.voice_cuts = cuts`; ทางสร้างเสียงใหม่ทุกทาง → ล้าง `voice_edit` และบันทึกเหตุผล
- ถ้ากราฟยาวขึ้นมาก (cut เงียบหลายสิบจุด) ให้ใช้กลไก `-filter_complex_script` ของเลน F

### 4.3 Preview ตัดเสียงพากย์
- เมื่อ `voiceEdit.cuts` ว่าง: ใช้เส้นทาง `<audio>` เดิม (ไม่เสี่ยง)
- เมื่อมี cut: decode เสียงพากย์เป็น `AudioBuffer` ครั้งเดียว (ไฟล์ 30-60 s ~ 3-10 MB) แล้วตั้งเวลา `AudioBufferSourceNode` ต่อ keep range: `src.start(ctxWhen + (progStart - t), srcStart + max(0, t - progStart), remaining)` พร้อม `GainNode` ramp 8 ms ที่ขอบ (เท่ากับ render) ต่อเข้า bus `voice` เดิม
- master clock ตอนมี cut: `t = clock.startT + (ctx.currentTime - clock.ctxStart)` (นาฬิกาเดียวกับที่ใช้ตั้งเวลาเสียง) แทน `audio.currentTime`; seek/stop = หยุด node ทั้งหมดแล้วตั้งใหม่ (เหมือน `flushSfx`)
- โมดูลใหม่ `frontend/src/lib/voiceCutScheduler.js` (pure: คืนรายการ `{when, offset, duration, fadeIn, fadeOut}`) เพื่อเทสด้วย node ได้โดยไม่ต้องมีเบราว์เซอร์; `SequencePlayer.jsx` แค่เรียกใช้
- `cueStemsTo`, ducking, BGM ยังใช้ t เดิม ไม่ต้องแก้

### 4.4 แผนเทส
1. `frontend/src/lib/voiceCutMap.test.js` + `rippleRange.test.js` (node --test): ทุกกรณีในตาราง 2.2 + กรณีขอบ 2.5 + undo payload
2. `tests/test_voice_cut_map.py`: unit ฝั่ง Python
3. `tests/test_voice_cut_map_parity.py`: ใช้ node รัน JS แบบเดียวกับ `tests/test_preview_render_parity.py:751-770` สุ่ม 500 ชุด (seed คงที่) เทียบผล map/keepRanges/effectiveDuration แบบเท่ากันทุกค่า
4. `tests/test_voice_cut_mix_render.py` (render จริง, `tmp_path`): ใช้ helper แบบใน `tests/test_real_render_cut_alignment.py` (`_write_voice` :72 สร้าง burst 1 kHz ที่เวลากำหนด, `_decoded_audio` :111, `_onsets` :117) — สร้างเสียง burst ที่ u = 1.0/3.0/5.0, ตัด [2.0, 2.5] → onset ที่ได้ต้องเป็น 1.0/2.5/4.5 ±5 ms, ความยาว = เดิม − 0.5 s ±1 เฟรม, ไม่มี click (ค่า peak ของ derivative รอบรอยต่อ < เกณฑ์) และตรวจว่าไม่มี cut แล้วกราฟเหมือนเดิมทุกไบต์
5. render end-to-end สั้น ๆ (ภาพ index-coded + เสียง burst + cue ที่เลื่อนแล้ว): onset ของเสียงตรงกับขอบคลิปหลังตัดภายในหน้าต่าง J-cut เดิม
6. Browser (Playwright fixture `frontend/editor_shell_audit.html`): ตัดช่วง → เล่น → อ่านเวลาเริ่มของ voice source node ที่ตั้งไว้เทียบกับ keepRanges
7. ลบไฟล์ทดสอบ 100% (`tmp_path`/`.tmp/` เท่านั้น ห้ามเขียน `03_Projects`/`04_Exports`)

---

## 5. ปุ่ม "ตัดช่วงเงียบ" (L4-01) ใช้กลไกเดียวกัน
- เดิม: `getMediaSilences(voiceAudioPath)` → `planSilenceRipple(clipList, spans)` แก้คลิปอย่างเดียว ตัดจากท้ายคลิป → หลุดซิงก์ (`L4.md:90-95`)
- ใหม่:
  1. backend `/api/audio/silences` ไม่ต้องแก้ (คืนช่วงเงียบในหน่วย u ของไฟล์ต้นฉบับ ซึ่งตรงกับ `voice_edit.cuts` พอดี)
  2. ฝั่ง editor ตัดช่วงที่ซ้อนกับ cut เดิมออก แล้วแปลงเป็นเวลาโปรแกรมด้วย `sourceToProgram`
  3. ใช้ `planRippleRanges(state, ranges)` (เหมือน `rippleDeleteRange` แต่หลายช่วง ทำจากช่วงหลังสุดไปหน้าสุด เพื่อให้เวลาของช่วงก่อนหน้าไม่ขยับ) ได้ plan เดียว
  4. หน้ายืนยันเดิม (`EditorShell.jsx:2400`) แสดงสรุปใหม่ (ข้อ 6) กด "ตัดเลย" = `set()` ครั้งเดียว
- `silenceRipple.js` เหลือแค่ `mergeSpans`/`describePlan` ส่วน `planSilenceRipple` กลายเป็น wrapper ของ `planRippleRanges` (เก็บชื่อเดิมไว้ให้เทสเดิมแก้น้อยที่สุด เทสที่ยืนยันพฤติกรรม "ตัดจากท้าย" ต้องแก้เป็นตำแหน่งจริง)
- เพิ่มตัวปรับ threshold/ความยาวขั้นต่ำ ไว้ทีหลัง (นอกรอบ)

---

## 6. UI/UX (ตาม `.agents/rules/ui_clean_standard.md`: ปุ่มขึ้นต้นด้วยกริยา ไม่มีสัญลักษณ์ซ้ำกับไอคอน)

- **Toolbar**: ปุ่มสลับขอบเขตการลบ (ไอคอน `Link2`/`Unlink`) ป้าย "ลบพร้อมเสียงและซับ" ↔ "ลบเฉพาะภาพ" · ค่าเริ่มต้น = ลบพร้อมเสียงและซับ เมื่อโปรเจกต์มีเสียงพากย์; ถ้าไม่มีเสียงพากย์ปุ่มซ่อน
- **ตัดช่วง**: ลาก In/Out บน ruler หรือกด `I` / `O` ที่ playhead แล้วกด `Shift+Delete` = ตัดช่วงแบบ ripple · `Delete` บนคลิปที่เลือก = ripple ช่วงของคลิปนั้นตามโหมดปุ่มสลับ
- **หน้ายืนยัน** (ใช้ dialog เดิม):
  - หัว: "ตัดช่วง 0:04.00–0:04.60 ออก?"
  - รอง: "ภาพ เสียงพากย์ ซับ และข้อความหลังจุดนี้จะเลื่อนมาชิดกัน"
  - สรุป: "เสียงพากย์สั้นลง 0.60 วินาที (31.20 → 30.60) · ลบซับ 1 บรรทัด · ปรับเวลาซับ 12 บรรทัด · ลบ SFX 1 เสียง · ตัดคลิป 1 คลิป"
  - เตือน (ถ้ามี): "ซับ 1 บรรทัดยังแสดงข้อความเต็ม แต่เสียงบางคำถูกตัด" / "ขยายช่วงให้พ้นทรานซิชัน 0.40 วินาที"
  - ปุ่ม: "ยกเลิก" / "ตัดช่วงนี้" · บรรทัดเล็ก "กด Ctrl+Z ย้อนกลับได้ทันที"
- **ตัวบอกจุดตัด**: เส้นแนวตั้งบางสีส้มบนเลนเสียงพากย์ที่ตำแหน่ง `sourceToProgram(cut.start)` hover แสดง "ตัด 0.60 วิ" · คลิกขวา → "คืนช่วงที่ตัด" (เฟส 2 ต้องมี `removed` snapshot)
- **เตือนหลังพากย์ใหม่**: "สร้างเสียงพากย์ใหม่แล้ว จุดตัดเสียงเดิม 3 จุดถูกล้าง" (สถานะตามจริง ไม่เงียบ)
- **Undo**: Ctrl+Z ครั้งเดียวคืนภาพ+เสียง+ซับ+overlay พร้อมกัน; Ctrl+Shift+Z ทำซ้ำ
- ปุ่ม "ตัดช่วงเงียบ" ใช้หน้ายืนยันเดียวกัน หัวเรื่อง "ตัดช่วงเงียบ 5 ช่วงออก?"

---

## 7. เลนลงมือ (เจ้าของไฟล์ไม่ซ้อนกัน)

ลำดับ: **RB → RM → (RP ∥ RU)** · RB เริ่มได้ทันทีหลังเลน F ปิด (ชน `sfx_manager.py`)

### 7.1 RB — backend: map + ตัดเสียงในมิกซ์ + manifest · แรง **M** · โมเดล Sonnet
- ไฟล์: `scripts/voice_cut_map.py` (ใหม่), `scripts/sfx_manager.py` (เฉพาะต้นกราฟเสียงพากย์ + signature), `scripts/stages/audio_mix_stage.py`, `scripts/stages/voice_stage.py`, `scripts/pipeline_context.py` (payload mix + snapshot + field `voice_cuts`), `scripts/api_phase1.py` (`UpdateProjectStateRequest.voice_edit` + validate: เรียง/ไม่ซ้อน/อยู่ในความยาว/source ตรง)
- เทส: `tests/test_voice_cut_map.py`, `tests/test_voice_cut_mix_render.py`, เทสว่ากราฟไม่เปลี่ยนเมื่อไม่มี cut, เทส reroll voice ล้าง `voice_edit`, เทส Pydantic เก็บฟิลด์
- หยุดเมื่อ: กราฟเดิมเปลี่ยนแม้ไม่มี cut · onset คลาด > 5 ms · ต้องแตะ `video_editor.py` (ไม่ควรต้อง)

### 7.2 RM — frontend model + คำสั่ง · แรง **L** · โมเดล Opus (กติกาเยอะ ต้องแม่น)
- ไฟล์: `frontend/src/lib/voiceCutMap.js` (+test, ใหม่), `frontend/src/lib/rippleRange.js` (+test, ใหม่: `planRippleRanges`, `describeRipplePlan`), `frontend/src/lib/silenceRipple.js` (+test), `frontend/src/lib/editorProjectState.js` (โหลด/บันทึก `voiceEdit`, เพิ่ม `microCuesList` ในผลโหลดเหมือนเดิม), `frontend/src/hooks/useEditorCommands.js` (`rippleDeleteRange`, `deleteSelected` ตามโหมด)
- เทส: node unit ทุกกรณี 2.2/2.5, parity `tests/test_voice_cut_map_parity.py`, round-trip save/load, undo หนึ่งขั้น
- หยุดเมื่อ: ต้องเปลี่ยนรูปแบบ cue ที่ backend อ่าน · ต้องแก้ `captionEdits.js` เกิน helper ที่มี

### 7.3 RP — preview เสียง · แรง **M** · โมเดล Opus (นาฬิกา master + WebAudio)
- ไฟล์: `frontend/src/lib/voiceCutScheduler.js` (+test, ใหม่), `frontend/src/components/SequencePlayer.jsx` (เฉพาะส่วน stem audio :4330-4680 และ `tick` :4887-4921)
- เทส: scheduler unit (node), browser fixture วัดเวลาเริ่ม source node, ฟังจริงใน Chrome (ต้องให้ user ยืนยัน)
- หยุดเมื่อ: เส้นทางไม่มี cut เปลี่ยนพฤติกรรม · drift > 1 เฟรมหลังเล่น 30 s

### 7.4 RU — UI · แรง **M** · โมเดล Sonnet
- ไฟล์: `frontend/src/components/editor/EditorShell.jsx` (ย้าย `microCuesList` เข้า `EMPTY`/history, `voiceEdit` ใน `EMPTY`, dialog, `audioDirty` รวม `voiceEdit` เพื่อสั่ง part `bgm`, ส่ง `voiceEdit` ให้ SequencePlayer/Timeline), `frontend/src/components/editor/Toolbar.jsx` (ปุ่มสลับ), `frontend/src/components/editor/Timeline.jsx` (เส้นจุดตัด, In/Out), `frontend/src/lib/editorShortcutKeys.js` (+test: `Shift+Delete`, `I`, `O` — ตรวจว่าไม่ชนปุ่มเดิม)
- เทส: shortcut unit, browser fixture กดจริง, `npm run build`
- หยุดเมื่อ: ปุ่มลัดชนของเดิม · ต้องแก้ฟอนต์/ข้อความซับ (ห้าม, AGENTS.md ข้อ 10)

### 7.5 ไฟล์ที่มี diff ค้างของ session อื่น (ใช้ Edit เฉพาะ hunk ห้าม stage ทั้งไฟล์)
จาก `git status` 2026-10-04: `frontend/src/components/SequencePlayer.jsx`, `editor/EditorShell.jsx`, `editor/Timeline.jsx`, `editor/Toolbar.jsx`, `editor/Inspector.jsx`, `editor/TimelineClip.jsx`, `hooks/useEditorCommands.js`, `hooks/useEditorShortcuts.js`, `hooks/useTimelineDrag.js`, `lib/editorProjectState.js`, `lib/editorShortcutKeys.js` (+test), `lib/timelineMath.js` (+test), `scripts/sfx_manager.py` (+เลน F รอบนี้), `scripts/video_editor.py` (เลน F), `scripts/subtitle_engine.py`, `scripts/stages/video_assembly_stage.py`, `tests/test_preview_render_parity.py`
ไฟล์ที่ **สะอาด** (เลน RB แก้ได้สบาย): `scripts/api_phase1.py`, `scripts/stages/voice_stage.py`, `scripts/stages/audio_mix_stage.py`, `scripts/pipeline_context.py`, `scripts/project_manifest.py`, `frontend/src/lib/silenceRipple.js`

### 7.6 Gate รวม
`pytest tests/ --ignore=tests/motion_capture` + `npm test` + `npm run build` + render จริง 1 คลิปใน `.tmp/` ฟังรอยต่อ + ดูเฟรม + `git status` ไม่มีขยะทดสอบ

---

## 8. เรื่องที่ต้องให้ user ตัดสินใจ

**D1 — วิธีเก็บข้อมูล (Jev 0.76 → ต้องถาม)**
- แนะนำ **B ผสม**: ไฟล์เสียงไม่ถูกแตะ undo ครบ แก้โค้ดน้อยสุด / ผล: เวลาเดิมก่อนตัดหายหลังบันทึก (กู้จาก Ctrl+Z ในเซสชัน หรือ backup manifest)
- A: ทุกอย่างกู้ได้ข้ามเซสชัน แต่ต้องแก้ ~15 จุด ในไฟล์ที่มีงานค้างของคนอื่น ความเสี่ยง preview≠render สูง ใช้เวลานานกว่า ~2 เท่า
- C: ได้ไฟล์เสียงที่ตัดแล้วจริงไว้ใช้ที่อื่น (เช่นส่ง CapCut) แต่ undo ซับซ้อน มีไฟล์ wav ค้างหลายไฟล์ และเสี่ยงผิดกฎห้ามเขียนทับเสียง

**D2 — เพลง BGM ตอนตัด**
- แนะนำ **เพลงเล่นต่อเนื่อง** (ไม่กระโดด) / ผล: คลิปหลังจุดตัดอาจไม่ตรง beat เดิม (ตัด 0.6 s ที่ 120 BPM = เพี้ยน 1.2 beat)
- ตัดเพลงตามด้วย: beat ตรงกับภาพเดิม แต่ได้ยินเพลงสะดุดทุกจุดตัด (ไม่เหมาะกับตัดช่วงเงียบหลายจุด)
- ปัดความยาวที่ตัดให้เป็นจำนวน beat เต็ม: beat ตรง เพลงไม่สะดุด แต่ตัดได้ไม่ตรงที่ผู้ใช้เลือก (เหลือช่องเงียบ/ตัดเกิน) — เหมาะเป็นตัวเลือกเสริมทีหลัง

**D3 — ค่าเริ่มต้นของปุ่ม Delete บนคลิป**
- แนะนำ **ลบพร้อมเสียงและซับ** เมื่อโปรเจกต์มีเสียงพากย์ / ผล: กด Delete แล้วเสียงพากย์ช่วงนั้นหายด้วย (มีหน้ายืนยันทุกครั้ง)
- คงเดิม "ลบเฉพาะภาพ": ไม่เปลี่ยนนิสัยเดิม แต่ปัญหาภาพหลุดซิงก์ยังเกิดเหมือนเดิมถ้าลืมสลับ
