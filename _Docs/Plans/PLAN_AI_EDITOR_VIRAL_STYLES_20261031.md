# PLAN — AI Editor Viral Styles Roadmap (2026-10-31)

ดำเนินการโดย: Claude Code (Claude Opus 5.5)
อ้างอิงหลักฐาน: [AI_EDITOR_VIRAL_AUDIT_20261031.md](../Reports/AI_EDITOR_VIRAL_AUDIT_20261031.md) (เลขข้อ A–H, §3–5 ในแผนนี้ชี้ไปที่รายงาน)
สถานะ: **ร่าง รอผู้ใช้ตอบคำถาม §5 ก่อนเริ่มโค้ด**

---

## 1. หลักการ

1. **Compliance ก่อนไวรัล** — คลิปผิดกฎ = ยอดเป็นศูนย์ ทำ lint ก่อนทุกอย่าง
2. **วัดได้ก่อนแต่ง** — เก็บ `style_preset`/`hook_style`/`story_format`/ความยาว/watch time ตั้งแต่สัปดาห์แรก ไม่งั้นทุกข้อเสนอในแผนนี้เป็นสมมติฐานตลอดไป
3. **Deterministic ก่อน AI** — lint, pacing curve, เพดานความยาวช็อต เป็น Python ล้วน เทส offline ได้ ไม่เสียโทเคน
4. **Preview = Render** — ทุกเอฟเฟกต์ใหม่ต้องเข้าทั้ง ffmpeg และ `SequencePlayer.jsx` + `test_preview_render_parity.py`
5. **ไม่แตะฟอนต์/ข้อความโดยไม่อนุมัติ** — ข้อที่ติดป้าย 🔒 ต้องได้คำตอบผู้ใช้ก่อน (AGENTS ข้อ 10, font_text_visual_contract)
6. **นิยามสไตล์ใหม่ = Story Format × Motion Family** — แทนการเพิ่ม preset ที่ต่างแค่สี

---

## 2. Roadmap

ลำดับเรียงตาม (ผลต่อไวรัล × ความมั่นใจ) ÷ ความยาก · ป้าย 🔒 = ต้องอนุมัติ · ⚠ = ผลต่อ manifest/schema

### ระดับ 1 — Quick wins (≤ 1 วัน/ข้อ, ไม่แตะ schema)

#### Q1. Compliance lint: ราคา + claim เกินจริง (H)
- **ปัญหา:** ราคา/claim พึ่ง prompt อย่างเดียว; TTS อ่าน "199.-" เป็น "199 บาท"; fallback hook มี "ถูกกับแพง"/"ไม่กี่บาท"; template มี "ใช้จริงมา 3 เดือนเต็ม"/"สั่งกันถล่มทลาย" (รายงาน H)
- **แก้:** ย้าย/ขยาย price lint จาก `script_rules.py:39-49` ให้เป็นฟังก์ชันกลาง เรียกกับ output สคริปต์หลัก (`ai_bridge._validate`), hook (`hook_generator`), `on_screen`, callout; เจอ = regen 1 ครั้ง แล้ว fail พร้อมข้อความไทย; TTS sanitizer เลิกแปลงราคาเป็นคำอ่าน (เปลี่ยนเป็น flag ส่ง lint); ลบ/เขียนใหม่ fallback hook 2 ตัว; ลบ claim ปลอมใน template; ลบ `"price"` จาก `CALLOUT_TYPES`; ถอด 📊 (`subtitle_engine.py:1426`) และอีโมจิใน `hook_title`; ล้าง "บลูทูธ"/"ฟาสชาร์จ" ใน `translation_service.py:44-45`
- **ไฟล์:** `scripts/script_rules.py`, `ai_bridge.py`, `hook_generator.py`, `tts_sanitizer.py`, `it_angles.py`, `script_generator.py`, `product_callout_builder.py`, `subtitle_engine.py`, `subtitle/translation_service.py`
- **AC:** สคริปต์/hook/on_screen/callout ที่มี `\d+\s*(บาท|฿|\.-)`, "ราคา", "ลด", "ส่วนลด", "โปร", "ถูกกว่า" ไม่หลุดถึง TTS/ASS 100% · fixture claim 10 ประโยคถูกจับครบ · `on_screen` ไม่มี "…"
- **เทส:** `tests/test_compliance_lint.py` (offline, fixture) + เทสเดิมทั้งหมดผ่าน
- **Rollback:** lint เป็นฟังก์ชันเดียว ปิดด้วย flag ใน `config.py`

#### Q2. อุดช่องช็อตยาวเกิน (H)
- **ปัญหา:** prompt Gemini ขอ 2–6 วิ ✔; topic coalesce / force-merge ไม่มีเพดาน; freeze hold ถึง 9.5 วิ (รายงาน C)
- **แก้:** ส่ง `max_shot` ของ preset เข้า prompt Gemini (`gemini_vision_matcher.py:957`) แทน 2.0–6.0; เพดาน merge = `max_shot × 1.25` ใน `_coalesce_ai_thought_groups` และ force-merge; freeze hold เกิน 1.0 วิ → แตกเป็นช็อตใหม่จาก window ถัดไป (fallback เดิมเป็นตัวสำรอง)
- **ไฟล์:** `gemini_vision_matcher.py`, `stages/shot_matching_stage.py`, `shot_source_window.py`
- **AC:** ในชุด fixture manifest ไม่มีคลิปยาวเกิน `max_shot × 1.25` ยกเว้นติดป้าย `hold_reason`; freeze hold ≤ 1.0 วิ
- **เทส:** `tests/test_shot_duration_caps.py` + `test_preview_render_parity.py`

#### Q3. ตัด filler opener + CTA วินาทีแรก (H)
- **แก้:** เขียน template ใหม่ใน `script_generator.py:25,35`, `hook_generator.py:131,147` ให้เปิดด้วยผลลัพธ์/ภาพ/คำถามเฉพาะสินค้า; เพิ่มกฎ prompt "ประโยคแรกห้ามเป็นคำขอให้หยุดดู"; lint ห้าม CTA ในบรรทัด 1
- **AC:** template ทุกตัวผ่าน lint "ไม่มี filler opener" (รายการวลีห้าม)
- **เทส:** รวมใน `test_compliance_lint.py`

#### Q4. Audio defaults: ducking + เพดาน SFX (M)
- **แก้:** `api_schemas.py:58` `bgm_ducking` → `True` ให้ตรง pipeline (`pipeline_context.py:456`); SFX ระยะห่างขั้นต่ำ 2.0 วิ, ห้าม boom ซ้อนที่ 0.0 (`sfx_manager.py:405-456`, `subtitle_engine.py:430-433`) — ต่อยอด Phase 4 ของ `PRO_EDITOR_STYLE_PLAN.md`
- **AC:** fixture timeline SFX ไม่มีคู่ที่ห่าง < 2.0 วิ (ยกเว้น transition whoosh ที่ผูกกับรอยตัด); web render มี sidechain ใน filter graph
- **เทส:** `tests/test_sfx_density.py`, เทส filter graph เดิม
- **หมายเหตุ:** ระดับ Voice 1.0 / SFX 0.28 / BGM 0.12 ไม่เปลี่ยน

#### Q5. บั๊ก preset / angle (M)
- **แก้:** `BatchRenderModal.jsx:400-403` เลิกส่ง `'commercial_premium'` (ใช้ id จริง) และให้ค่าที่ผู้ใช้เลือกชนะ angle default (`batch_render.py:636-638`); map angle key ของ `it_angles.py` → preset (หรือรวมเป็นชุดเดียว); ให้ `hookColor` = accent; ให้ `color_theme.py` อ่านจาก policy; แก้ label preset ให้ตรงกับที่ render ทำจริง (tech_compare/niche_focus/smart_hack/premium_minimal)
- **AC:** ทุก angle key ใน `it_angles.py` ได้ preset ที่ตั้งใจ (ไม่ตกไป default); เทสเช็ก catalog vs policy สีตรงกัน 10/10
- **เทส:** `tests/test_style_preset_consistency.py` + `npm test`

#### Q6. เก็บข้อมูลสำหรับวัดผล ⚠ (H ระยะยาว)
- **แก้:** บันทึก `style_preset`, `hook_style`, `story_format` (ค่าเริ่ม `"classic"`), `duration_sec`, `hook_text`, `opener_type` ลง export registry + PostLog ตอน finalize (`export_registry.py:439-449`, `post_log.py:218,262`, `api_exports.py:978`); เพิ่มคอลัมน์ `avg_watch_time_sec`, `completion_rate` (optional) ใน TikTok stats import (`api_tiktok_stats.py:46-50`) ถ้าไฟล์ที่ผู้ใช้ import มีให้
- **AC:** export ใหม่มีครบ 6 field; import CSV ที่มี/ไม่มีคอลัมน์ watch time ผ่านทั้งคู่; record เก่าอ่านได้ (field optional)
- **เทส:** `tests/test_export_style_metadata.py` (temp storage, Lock), migration ไม่จำเป็นเพราะ optional
- **ใช้ `threading.Lock`** ตาม AGENTS ข้อ 24

#### Q7. เล็ก ๆ ที่ได้ผลเร็ว (M)
- ตัด lead silence ของ Gemini TTS ให้เหลือ ≤ 50ms เหมือน Edge (`voice_engine.py:93-97`, `gemini_tts_engine.py`)
- ไฮไลต์ตัวเลขสเปกด้วย regex (`\d+(\.\d+)?\s?(mAh|W|Hz|ชม\.|ชั่วโมง|GB|TB|นาที)`) ก่อน dictionary hype (`translation_service.py:264-313`) — **ไม่เปลี่ยนสี/ฟอนต์ เปลี่ยนแค่คำที่ถูกเลือก**
- Shot planning exception → fail พร้อม log ไทย แทนส่งคลิปเดียวยาวทั้งเรื่อง (`shot_matching_stage.py:1309-1317`)
- แก้ log "3-word bursts" ให้ตรงจริง (`subtitle_stage.py:85`)
- **AC/เทส:** เทสหน่วยต่อข้อ + parity

---

### ระดับ 2 — Mid (2–5 วัน)

#### M1. 🔒 Hook text บนจอ 0–1.8 วิ (H)
- **ปัญหา:** banner เป็นป้ายชื่อค้าง 5 วิ ข้อความ hook ไม่ขึ้นจอ (รายงาน A)
- **แก้ (ร่าง ต้องอนุมัติ):** ชั้น hook line (ข้อความ 1 บรรทัด ≤ 22 ตัวอักษร) ขึ้น 0.0–1.8 วิ ตำแหน่งบนจอใน safe zone แล้วค่อยส่งต่อให้ nameplate 3 ชั้นเดิม (เริ่ม 1.8 วิ ลดเวลาค้างจาก 5 → 3 วิ); ใช้ฟอนต์/สไตล์จาก hook template เดิม ไม่สร้าง family ใหม่
- **ไฟล์:** `subtitle_engine.py:888+`, `overlay_model.py`, `subtitle/overlay_events.py`, `SequencePlayer.jsx`, `pipeline_context.py:442`
- **AC:** เฟรม t=0.3 วิ มีข้อความ hook อ่านได้; t=2.0 วิ มี nameplate; snapshot เฟรมจริงตรวจด้วยตา (AGENTS ข้อ 22); ไม่มีข้อความชิดขอบขวา-ล่าง
- **เทส:** `test_preview_render_parity.py` + เรนเดอร์ใน `.tmp/` แล้ว snapshot แล้วลบ

#### M2. Pacing curve + interrupt guard (H)
- **แก้:** ใน `StyleMotionPolicy` เพิ่ม `hook_window_sec` (3.0), `hook_max_shot` (1.3), `max_static_sec` (2.5); `shot_matching_stage` ใช้ max ที่สั้นกว่าในช่วง hook; ช่วงใดเกิน `max_static_sec` โดยไม่มีรอยตัด/transition/camera → แทรก camera punch (scale +0.08, 0.15 วิ) อัตโนมัติ (ใช้ keyframe engine เดิม ไม่ใช่เอฟเฟกต์ใหม่ → preview เล่นตาม manifest)
- **ค่าต่อ family:** Punch 1.0/2.0 · Tech 1.3/2.5 · Smooth 1.5/3.0 · Premium 1.8/3.5 [สมมติฐาน จูนจากข้อมูล Q6]
- **AC:** fixture: 3 วิแรกไม่มีช็อต > `hook_max_shot`; ไม่มีช่วงนิ่ง > `max_static_sec`; manifest schema ไม่เปลี่ยน (keyframe เดิม)
- **เทส:** `tests/test_pacing_curve.py`, parity

#### M3. Script retention structure + ความยาวเป้า (H)
- **แก้:** `script_stage.py:45-51` ส่ง `target_duration` (15/25/35 วิ) และ `story_format` เข้า `ai_bridge`; prompt บังคับ beat: hook → open loop (≤ วิ 3) → เนื้อหา → payoff ผูกกับ hook → คำถามปลายเปิด (ห้ามทายราคา) → CTA; ตัวตรวจโครงหลังเจน (deterministic: มีบรรทัด open loop, บรรทัดท้ายไม่ใช่ filler, จำนวนตัวอักษรตามเป้า ±15%)
- **AC:** 20 สคริปต์จาก fixture product ผ่านตัวตรวจโครง ≥ 90% โดยไม่ regen เกิน 1 ครั้ง; ความยาว VO อยู่ในเป้า ±15%
- **เทส:** ตัวตรวจโครงเทส offline; การเจนจริงทดสอบด้วยมือ (ยิง API = เสียเงิน ต้องขอผู้ใช้)

#### M4. Viral Lint + Retention heatmap (H)
- **แก้:** `scripts/viral_lint.py` (ใหม่, pure) รับ manifest → รายการ issue: hook ช้า, ช็อตยาว, ช่วงนิ่ง, dead air > 0.4 วิ, SFX ถี่, ไม่มี open loop/payoff, ความยาวเกินเป้า, compliance (เรียก Q1) — แต่ละข้อมี severity + เวลา; API คืนผล; `RenderPreflightNotice.jsx` แสดงเป็น warning (ไม่ block ยกเว้น compliance); Timeline วาดแถบสีตามช่วงที่มี issue
- **AC:** lint ทำงาน < 50ms ต่อ manifest; fixture ที่ฝังปัญหา 8 แบบถูกจับครบ; compliance block การ render
- **เทส:** `tests/test_viral_lint.py` + `npm test` ส่วน UI; UI ใช้ `/impeccable` ตาม AGENTS 5.1

#### M5. รวม preset 10 → 4 Motion Family ⚠ 🔒 (M)
- **แก้:** ใน `style_motion_policy.py` เหลือ 4 family (punch / tech / smooth / premium); preset id เก่า 10 ตัวเป็น **alias** → family + palette เดิม (manifest เก่าเปิดได้, สีเดิมคงอยู่); catalog UI แสดง 4 family × palette
- **AC:** manifest เก่าทุกตัวโหลดได้และ render ได้ค่า motion เท่าเดิมตาม alias map; UI เลือกได้ 4 แบบ + สี
- **เทส:** `test_style_preset_consistency.py`, parity, `npm test`
- **ทางเลือก:** ถ้าผู้ใช้ไม่อยากรวม → ทำให้แต่ละตัวต่างจริงแทน (แพงกว่า)

#### M6. Shot matching confidence + ปฏิเสธฟุตเทจนิ่ง (H)
- **แก้:** เพิ่ม `confidence` ใน response schema ของ Gemini (`gemini_vision_matcher.py:961-975`); catalog path ต้องมี keyword ตรงอย่างน้อย 1 ไม่งั้นติดป้าย low; low → ใช้ช็อตสินค้าทางการ (hero) แทนการเดาตามตำแหน่ง; motion snap เลิกดันรอยตัดเข้าเฟรมนิ่ง (`shot_matching_stage.py:1097-1112`) และ reject window ที่ motion score ต่ำกว่าเกณฑ์ในช่วง hook
- **AC:** fixture: ไม่มีช็อต low-confidence ในช่วง hook; ช็อตแรกมี motion score ≥ เกณฑ์
- **เทส:** `tests/test_shot_confidence.py` (mock Gemini)

#### M7. Batch render 4 workers + resume gate (M, ผิดกฎข้อ 24 อยู่)
- **แก้:** `batch_render.py` dispatcher ใช้ `ThreadPoolExecutor(max_workers=4)`; `is_valid_mp4` (ffprobe, > 1MB, decode ได้) ข้ามคลิปที่เสร็จแล้ว; Lock รอบ registry
- **AC:** batch 8 item ใช้เวลา ≤ 40% ของแบบ sequential (fixture จำลอง); restart กลางทางไม่เรนเดอร์ซ้ำ
- **เทส:** `tests/test_batch_concurrency.py` (fake render function, temp storage)

#### M8. 🔒 ซับ Micro-burst 2–4 คำ (H)
- **ปัญหา:** `MICRO_BURST_MAX_CHARS = 34` ขัด `subtitle_kinetic_rules.md` (2–4 คำ) แต่การเปลี่ยนการตัดบรรทัด = กระทบข้อความตาม font contract
- **แก้ (ถ้าอนุมัติ):** ลดเป็น 16–24 ตาม spec, ใช้ syllable clustering เดิม, ไม่เปลี่ยนฟอนต์/ขนาด/outline/ตำแหน่ง
- **AC:** burst ≤ 24 ตัวอักษร; สระ/วรรณยุกต์ไม่ฉีก; golden master เดิมผ่าน; snapshot เฟรมจริง
- **เทส:** เทสซับเดิม + `test_preview_render_parity.py`

#### M9. Word timing สำหรับ Gemini TTS (enabler)
- **ปัญหา:** Gemini TTS (ค่าเริ่มต้น) ไม่มี word timing → editorial pacing ปิด, callout ผูกตัวเลขไม่ได้ (รายงาน C, D)
- **แก้:** align VO กับสคริปต์ด้วย faster-whisper (`device="cuda", compute_type="float16"` ตาม AGENTS ข้อ 21) → `word_timings`; ให้ SpecBar/callout เริ่มตอนพูดตัวเลข
- **AC:** word timing ครบ ≥ 95% ของคำใน fixture; SpecBar เริ่มภายใน ±150ms จากคำตัวเลข
- **เทส:** fixture เสียงสั้นใน `tests/fixtures` (ไม่ใช้ 01_Raw)

---

### ระดับ 3 — Big bets (ต้องออกแบบเพิ่ม / เปลี่ยน manifest)

#### B1. Story Format layer ⚠
- 3 format ใหม่: **Countdown 3 เหตุผล**, **Problem → Solution Reveal**, **Myth-buster** + format เดิม `classic` (รายงาน §4)
- `story_format` เป็น field ระดับโปรเจกต์ → คุม prompt สคริปต์ (M3), pacing (M2), overlay ลำดับ (Countdown), SFX policy
- **ต้องมาก่อน:** Q1, Q6, M2, M3
- **AC:** แต่ละ format เจนคลิปตัวอย่างจากสินค้าจริง 1 ตัว ผ่าน Viral Lint, snapshot ตรวจด้วยตา, ลบไฟล์ทดสอบ 100%

#### B2. Seamless Loop modifier
- prompt บรรทัดท้ายต่อกับบรรทัดแรก; BGM ตัดที่ beat แทน fade (`sfx_manager.py:477-480`); เลิกค้างเฟรมท้าย (`video_editor.py:2054-2057`) → ช็อตท้าย framing ใกล้ช็อตแรก
- **AC:** ไม่มี freeze tail; รอยต่อ loop เมื่อเล่นวนไม่มีเสียงขาด > 100ms

#### B3. Speed ramp primitive
- ffmpeg `setpts` แบบช่วง + SequencePlayer `playbackRate` ตาม keyframe; ใช้ใน Problem→Solution (จุด reveal)
- **AC:** parity เฟรมต่อเฟรม ±1 เฟรมที่ 30fps; เสียง VO ไม่ถูกเร่ง

#### B4. Hook A/B batch
- 1 สคริปต์ → 2–3 hook variant → เรนเดอร์ขนาน (M7) → บันทึก variant id (Q6) → หน้า Performance เทียบ
- **ต้องมาก่อน:** Q6, M7, M1

#### B5. Style recommendation จากข้อมูลจริง
- เมื่อมีโพสต์ ≥ 10 คลิปต่อ format/family (mature ≥ 48 ชม. ตาม `post_log.mature_metrics`) → แนะนำ format/family ต่อหมวดสินค้า พร้อม confidence; ต่ำกว่าเกณฑ์ = ไม่แนะนำ
- **AC:** ไม่แนะนำเมื่อข้อมูลไม่พอ; แสดงจำนวนตัวอย่างทุกครั้ง

#### B6. Editor UX: reroll ทีละช็อต + "ทำไมตัดตรงนี้"
- manifest เพิ่ม `cut_reason` (topic change / beat / interrupt guard / hook window) → Inspector; context menu "สลับช็อตนี้" เลือก window อันดับ 2–3 จาก matcher
- **AC:** สลับช็อตเดียวไม่กระทบคลิปอื่น/ซับ/เสียง

---

## 3. ลำดับ Sprint ที่เสนอ

| Sprint | งาน | เหตุผล |
|---|---|---|
| S1 | Q1, Q2, Q3, Q5, Q6 | ปิดความเสี่ยงกฎ + เริ่มเก็บข้อมูล + อุดช็อตยาว — ไม่ต้องรออนุมัติฟอนต์ |
| S2 | Q4, Q7, M2, M6, M7 | จังหวะ + matching + ความเร็ว batch |
| S3 | M1🔒, M3, M4, M9 | hook บนจอ + โครงสคริปต์ + lint |
| S4 | M5🔒, M8🔒, B1, B2 | format ใหม่ + loop |
| S5 | B3, B4, B5, B6 | ต้องมีข้อมูลจาก S1 สะสม ≥ 2–3 สัปดาห์ |

ทุก sprint: เขียนรอบลง `TODO.md` ก่อน → เทส `pytest tests/` + `npm test` + build → ปิดรอบย้าย `HISTORY.md` → ไม่มีไฟล์ทดสอบค้าง

---

## 4. Top 5 ควรทำก่อน

1. **Q1 Compliance lint** — ถูก ทำครั้งเดียว ป้องกันคลิปโดนลดการมองเห็น/แบน ตอนนี้ราคาหลุดได้จริงทาง TTS
2. **Q6 เก็บ style/hook/ความยาว/watch time** — ไม่มีข้อมูล = ไม่รู้ว่าแก้แล้วดีขึ้นจริงไหม ยิ่งเริ่มเร็ว ข้อมูลยิ่งสะสม
3. **M1 Hook text 0–1.8 วิ** — ช่องว่างใหญ่สุดของ hook rate (ภาพแรกตอนนี้เป็นป้ายชื่อ) — ติดอนุมัติ
4. **Q2 + M2 อุดช็อตยาว + pacing curve** — retention กลางคลิป แก้ใน Python ล้วน parity ปลอดภัย
5. **M3 โครงสคริปต์ retention + ความยาวเป้า** — open loop/payoff/loop ending เป็นงาน prompt + ตัวตรวจ ต้นทุนต่ำ ผลสูง [best practice]

---

## 5. คำถามที่ผู้ใช้ต้องตัดสิน

1. **ลำดับแรก:** Jev เลือก "hook" (confidence 0.74 < 0.80 → ต้องถาม) ส่วนแผนนี้เสนอ compliance + data ก่อน แล้วค่อย hook — เอาแบบไหน
2. **M1 🔒** อนุญาตเพิ่มชั้น hook text 0–1.8 วิ และลดเวลา nameplate จาก 5 → 3 วิ ไหม
3. **M8 🔒** อนุญาตลด burst ซับจาก 34 → 16–24 ตัวอักษร (ตาม spec เดิม) ไหม
4. **M5 🔒** รวม preset 10 → 4 motion family (id เก่าเป็น alias สีเดิม) หรือเก็บ 10 ตัวแล้วทำให้ต่างจริง
5. **ความยาวคลิปเป้าหมาย** ตั้งต้นเป็นเท่าไร (15 / 25 / 35 วิ) หรือให้ผูกตาม angle
6. **Watch time:** ตอนนี้ import สถิติ TikTok จากไหน (CSV จาก TikTok Studio?) มีคอลัมน์ avg watch time / completion ไหม
7. **Flash Deal / fomo_deal angle** — เปลี่ยนเป็น urgency แบบไม่พูดราคา (เช่น "ของเข้าล็อตเล็ก") หรือถอดทิ้ง
8. **Story Format ใหม่** — เริ่ม format ไหนก่อน: Countdown / Problem→Solution / Myth-buster
