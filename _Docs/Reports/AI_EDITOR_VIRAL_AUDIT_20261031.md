# AI Editor & Auto-Cut Viral Audit — 2026-10-31

ดำเนินการโดย: Claude Code (Claude Opus 5.5) + 4 read-only Explore sub-agents (Claude Opus 5.5)
พรอมพ์ต้นทาง: [PROMPT_AI_EDITOR_VIRAL_STYLE_AUDIT_20261031.md](../Plans/PROMPT_AI_EDITOR_VIRAL_STYLE_AUDIT_20261031.md)
แผนที่ตามมา: [PLAN_AI_EDITOR_VIRAL_STYLES_20261031.md](../Plans/PLAN_AI_EDITOR_VIRAL_STYLES_20261031.md)

ป้ายกำกับ: **[code]** = หลักฐานจากโค้ด (path:line) · **[best practice]** = แนวปฏิบัติวงการ short-form ไม่ใช่ข้อเท็จจริงที่วัดในช่องนี้ · **[สมมติฐาน]** = ยังไม่ได้ยืนยัน
ขอบเขต: audit อย่างเดียว ไม่แก้โค้ด ไม่เรนเดอร์ ไม่ยิง paid API
ข้อค้นพบหลัก 9 ข้อเปิดโค้ดยืนยันซ้ำด้วยมือแล้ว (ทำเครื่องหมาย ✔)

---

## 0. สรุปผู้บริหาร

ระบบตัดต่อ "ถูกต้องเชิงเทคนิค" (Preview=Render, J-cut, beat snap, loudnorm มีครบ) แต่ **ยังไม่ได้ออกแบบมาเพื่อ retention**
ช่องว่างใหญ่ 5 ข้อ:

1. **วินาทีแรกไม่มี hook จริงบนจอ** — banner เป็นป้ายชื่อ แบรนด์/รุ่น/หมวด ค้าง 5 วิ ข้อความ hook ที่ AI เขียน (`hook_title`) ถูกถอดออกจากจอ ✔ `scripts/subtitle_engine.py:888-890`, `scripts/pipeline_context.py:442`
2. **จังหวะเรียบเท่ากันทั้งคลิป** — ไม่มี pacing curve, preset ตั้งต้น `clean_tech_review` ใส่ transition ทุก 5 รอยตัด, กล้องขยับทุก 2 ช็อต, zoom delta แค่ 0.04–0.14 ✔ `scripts/style_motion_policy.py:58,64-67`
3. **ช็อตยาว/ค้างภาพได้นานเกิน** — prompt Gemini ขอช็อต 2–6 วิ ขัดกับ max 2.5 วิของ preset ✔ `scripts/gemini_vision_matcher.py:957`; freeze hold ได้ถึง 9.5 วิ `scripts/shot_source_window.py:77`
4. **สคริปต์ไม่มีโครง retention** — ไม่มี open loop / payoff / loop ending / จุดชวนคอมเมนต์ และยาว 35–45 วิเป็นค่าตั้งต้น `scripts/ai_bridge.py:243-244`
5. **Compliance พึ่ง prompt อย่างเดียว** — ไม่มี lint ราคาบน output สคริปต์หลัก และ TTS sanitizer **อ่านราคาออกเสียงเป็น "บาท"** ✔ `scripts/tts_sanitizer.py:329-331`; fallback hook มีคำเรื่องราคา ✔ `scripts/it_angles.py:23,83`

และ **ยังวัดผลไม่ได้**: ไม่เก็บ avg watch time / completion, ไม่เก็บ `hook_style` และความยาวคลิปกับ export จึงยังสรุปไม่ได้ว่าสไตล์ไหนปังจริง (`scripts/post_log.py:29`, `scripts/export_registry.py:439-449`)

### Viral Readiness Score (0–10, ประเมินจากโค้ด)

| ข้อ | หมวด | คะแนน | เหตุผลย่อ |
|---|---|---|---|
| A | 0–1 วิแรก (Hook) | 3 | VO เริ่ม ~t=0 แต่ภาพแรกเป็นป้ายชื่อ ไม่มีข้อความ hook ไม่มี scoring |
| B | 1–5 วิ (Retention gate) | 3 | ไม่มี open loop, ช็อตต้นคลิปยาวเท่าช่วงกลาง |
| C | กลางคลิป | 4 | มี J-cut/beat snap/กันช็อตซ้ำ แต่ไม่มี pattern-interrupt guard, freeze hold ยาว, matching ไม่มี confidence |
| D | ซับ/ข้อความ | 4 | ไฮไลต์มี แต่ burst 34 ตัวอักษร, ไม่ไฮไลต์ตัวเลขสเปก, SpecBar ขึ้นก่อนพูด |
| E | เสียง | 6 | loudnorm -14 LUFS ดี แต่ ducking ปิดใน web render, SFX ทุกบรรทัดไม่มีเพดาน |
| F | ตอนจบ | 2 | CTA กลาง ๆ, ค้างเฟรมสุดท้าย, ไม่มี loop/payoff |
| G | Engagement trigger | 1 | ไม่มีในพรอมพ์เลย |
| H | Compliance | 5 | กันจุดไข่ปลา/อีโมจิ/ทับศัพท์ได้ดี แต่ราคาและ claim เกินจริงหลุดได้ |

คะแนนต่อ preset ดูข้อ 3

---

## 1. แผนที่ระบบ (Inventory & Data Flow)

ลำดับ stage จริง: source → script → voice → subtitles → mix → shot_matching → video_assembly `scripts/pipeline.py:267-292`

| Stage | ไฟล์หลัก | AI ตัดสิน | Rule ตายตัว | style_preset มีผล? | จุดอ่อน |
|---|---|---|---|---|---|
| script | `stages/script_stage.py`, `ai_bridge.py:202-250` | Gemini เขียน hook + บรรทัด + SFX ต่อบรรทัด | template fallback `script_stage.py:82` | **ไม่** (context ไม่มี style/ความยาวเป้า `script_stage.py:45-51`) | โครงสคริปต์ตายตัว 7–8 บรรทัด ไม่ผูก style/angle |
| voice | `stages/voice_stage.py`, `gemini_tts_engine.py` | Gemini TTS (ค่าเริ่มต้น `pipeline.py:111-112`) | cue จาก RMS pause >140ms `voice_stage.py:102-121` | ไม่ | Gemini TTS ไม่มี word timing → editorial pacing ปิด |
| subtitles | `stages/subtitle_stage.py`, `subtitle_engine.py` | — | pacing plan เมื่อมี `word_timings` เท่านั้น `subtitle_stage.py:141` | ใช่ `:125,164` | burst ยาว 34 ตัวอักษร |
| mix | `stages/audio_mix_stage.py`, `sfx_manager.py` | — | atempo BGM ±8%, loudnorm | ไม่ | SFX ไม่ผูก style |
| shot_matching | `stages/shot_matching_stage.py`, `gemini_vision_matcher.py` | Gemini Vision เลือก window + punch_zoom `:947-975` | timing/merge/snap ทั้งหมด | ใช่ (rhythm `:759`, transition `:1182`, camera `:1256`) | ไม่มี confidence, fallback เลือกตามตำแหน่ง |
| assembly | `stages/video_assembly_stage.py`, `video_editor.py` | — | เติม transition `:117-138` | ใช่ `:184` | ค้างเฟรมสุดท้าย `video_editor.py:2053-2058` |

Preview: `SequencePlayer.jsx` ไม่คำนวณ policy เอง เล่นตาม manifest → parity ขึ้นกับ manifest ไม่พบเอฟเฟกต์ที่มีใน ffmpeg แต่ไม่มีใน preview (`SequencePlayer.jsx:490-791`) — ข้อดี ต้องรักษาไว้

---

## 2. Viral Checklist ละเอียด

สถานะ: ✅ มีครบ · 🟡 บางส่วน · ❌ ไม่มี | ผล = ผลต่อไวรัล H/M/L | ยาก = S/M/L

### A. 0–1 วินาทีแรก

| ข้อ | สถานะ | หลักฐาน | ช่องว่าง | ผล | ยาก |
|---|---|---|---|---|---|
| เฟรมแรกเคลื่อนไหว/สินค้าเต็มเฟรม ไม่ fade จากดำ | 🟡 | ไม่มี fade-in ดำ `video_editor.py:846` (เป็น overlay alpha) | ไม่มีกฎเลือก "ช็อตแรกต้อง motion สูง/สินค้าเด่น"; motion snap ดันรอยตัดไปเฟรมนิ่ง `shot_matching_stage.py:1097-1112` | H | M |
| Text hook ขึ้น ≤0.3 วิ อ่านจบ <1.5 วิ | ❌ | banner = แบรนด์/รุ่น/หมวด `overlay_model.py:440-444`, `subtitle_engine.py:888-890` ✔ ค้าง 5 วิ `pipeline_context.py:442` | ข้อความ hook จริงไม่ขึ้นจอ | **H** | M |
| เสียงพูดเริ่มทันที | 🟡 | Edge ตัด silence ต้น ≤15ms `voice_engine.py:93-97`; Gemini TTS เหลือ 0.1–0.4 วิ `shot_matching_stage.py:769-780` | ตัด lead silence ของ Gemini ด้วย | M | S |
| Hook 3 ชั้นสอดคล้อง (ภาพ+ข้อความ+เสียง) | ❌ | ภาพ=ช็อตใดก็ได้, ข้อความ=ป้ายชื่อ, เสียง=hook line | ไม่มีกลไกผูก 3 ชั้น | H | M |
| Hook หลายแบบ / A/B | 🟡 | เจน 5 style `api_hooks.py:53-73`, `hook_generator.py:21-52`; modal ชื่อ "A/B Generator" แต่ใช้ได้ทีละอัน `HookVariationModal.jsx:68-95,108` | ไม่มี scoring, ไม่เรนเดอร์หลาย variant, ไม่ผูกผล | H | M |
| Opener ไม่เสียเวลา | ❌ | "ทุกคน! อย่าเพิ่งเลื่อนผ่านนะ" `script_generator.py:25,35`; "หยุดดูก่อน 10 วินาทีครับ" `hook_generator.py:131`; deal_promo ใส่ CTA วินาทีแรก `:147` | filler เปิดคลิป [best practice: เปิดด้วยผลลัพธ์/ภาพ/คำถามเฉพาะ ไม่ใช่คำขอให้หยุดดู] | H | S |

### B. 1–5 วินาที

| ข้อ | สถานะ | หลักฐาน | ช่องว่าง | ผล | ยาก |
|---|---|---|---|---|---|
| Open loop / สัญญาผลตอบแทน | ❌ | โครง Hook→Pain→reveal→feature `ai_bridge.py:243` ไม่มีคำสั่ง open loop | เพิ่ม beat "สัญญา" ใน prompt + lint | H | S |
| Pacing curve (ต้นเร็วกว่า) | ❌ | min/max คงที่ทั้งคลิป `shot_matching_stage.py:759-762` | ไม่มี hook acceleration | H | M |

### C. กลางคลิป

| ข้อ | สถานะ | หลักฐาน | ช่องว่าง | ผล | ยาก |
|---|---|---|---|---|---|
| ช็อตเฉลี่ย 1.5–3 วิ | 🟡 | preset 1.5–3.0 `style_motion_policy.py`; แต่ merge 1.5×max `:872`, force-merge ไม่มีเพดาน `:900-927`, topic coalesce ไม่เช็กความยาว `:55-71`, Gemini prompt 2–6 วิ ✔ `gemini_vision_matcher.py:957` | ช็อตยาว 4–6 วิหลุดได้ | H | S |
| Pattern interrupt ทุก 2–4 วิ | ❌ | transition เฉพาะบน stride `style_motion_policy.py:326-327`; ไม่มี speed ramp `shot_matching_stage.py:1236` | ไม่มี guard "N วิไม่มีอะไรเปลี่ยน" | H | M |
| ไม่มีช็อตนิ่ง/ค้างนาน | ❌ | freeze hold ถึง 9.5 วิ `shot_source_window.py:77`; ไม่คัดฟุตเทจนิ่ง `:1137-1139` | ต้องมี freeze cap + reject still | H | M |
| Dead air กลางคลิป | 🟡 | ไม่ตัดอัตโนมัติ `silence_detect.py:3-7`; gap ระหว่างบรรทัดถูกบีบ 40–80ms `voice_engine.py:414` | ด้านเสียงแน่นดีแล้ว แต่ไม่มี "หายใจ" ตรง beat สำคัญ | L | S |
| Strict Topic Hold | 🟡 | hold ท้ายประโยค `shot_matching_stage.py:836-847` | ไม่มี confidence field `gemini_vision_matcher.py:961-975`; catalog เลือก top score แม้ไม่มี keyword ตรง `:573-577`; fallback เลือกตามตำแหน่ง `shot_matching_stage.py:305-331` | H | M |
| Beat sync + J-cut ทุก preset | 🟡 | J-cut ทุก preset `:50-52`; beat snap ทำเฉพาะตอนไม่มี pacing plan `:980` | path guided/storyboard อาจข้าม rhythm [สมมติฐาน] `:643-651` | M | S |
| Failure mode | ❌ | exception ใน shot planning → คลิปเดียวยาวทั้งเรื่อง ✔ `shot_matching_stage.py:1309-1317` | ต้อง fail loud แทนส่งคลิปนิ่งยาว | M | S |

### D. ข้อความ/ซับ

| ข้อ | สถานะ | หลักฐาน | ช่องว่าง | ผล | ยาก |
|---|---|---|---|---|---|
| Burst 2–4 คำ | ❌ | `MICRO_BURST_MAX_CHARS = 34` ✔ `subtitle_engine.py:109` (คอมเมนต์ยอมรับว่าเกิน spec 16–24); log บอก "3-word" ผิด `subtitle_stage.py:85` | ขัด `subtitle_kinetic_rules.md` — **แต่การเปลี่ยนตัดบรรทัดต้องขออนุมัติตาม font contract** | H | M |
| ไฮไลต์คำถูกคำ | 🟡 | 1 คำต่อ burst, ลำดับ marker→keyword→dictionary `translation_service.py:264-313`; ไม่มี regex ตัวเลขสเปก มีแค่ 66W/100W/120Hz `:45-47` | ตัวเลขสเปก (mAh, W, ชม.) ควรได้ไฮไลต์ก่อนคำ hype | M | S |
| Callout ตรงจังหวะพูด | ❌ | SpecBar ขึ้นตั้งแต่ต้นประโยค `subtitle_engine.py:1410-1426`; callout ไม่มี beat → cue 0 `product_callout_builder.py:347-348` | ต้องผูกกับ word timing ของตัวเลข | M | M |

### E. เสียง

| ข้อ | สถานะ | หลักฐาน | ช่องว่าง | ผล | ยาก |
|---|---|---|---|---|---|
| Ducking | 🟡 | sidechain มี `sfx_manager.py:482-492`; pipeline default True `pipeline_context.py:456` แต่ API default False ✔ `api_schemas.py:58` | web render ไม่ duck | M | S |
| Loudness | ✅ | loudnorm I=-14 TP=-1 `sfx_manager.py:33-35,507-509` | single-pass (พอใช้) | L | — |
| SFX density | 🟡 | boom ที่ 0.0 เสมอ `sfx_manager.py:405-410` + SFX ทุกบรรทัด `subtitle_engine.py:430-433` + ทุก overlay `sfx_manager.py:437-456` | ไม่มีเพดาน/ระยะห่างขั้นต่ำ, อาจซ้อน boom 2 ตัวต้นคลิป [สมมติฐาน] | M | S |
| VO pace | 🟡 | Edge +15% `config.py:137`, Gemini atempo 1.15 `gemini_tts_engine.py:168` | ไม่มีเป้า คำ/วินาที | L | S |

### F. ตอนจบ

| ข้อ | สถานะ | หลักฐาน | ช่องว่าง | ผล | ยาก |
|---|---|---|---|---|---|
| Payoff ผูกกับ hook | ❌ | ไม่มีใน prompt `ai_bridge.py:243` | — | H | S |
| Loop กลับต้นคลิป | ❌ | BGM fade 0.35 วิ `sfx_manager.py:477-480`, ค้างเฟรมท้าย `video_editor.py:2054-2057` | [best practice: ประโยคท้ายต่อกับประโยคแรกได้ → rewatch] | H | M |
| ความยาวตาม angle | ❌ | ความยาว = ความยาว VO `voice_stage.py:476,624`; prompt 35–45 วิ หรือ 20–25 วิ ไม่มีตัวเลือกส่งเข้า `ai_bridge.py:243-244` | ไม่มี target 15/30/45 วิ | H | S |
| End card | ❌ (main) | มีเฉพาะ couple engine `couple_engine/compose.py:203` | — | L | M |

### G. Engagement trigger

| ข้อ | สถานะ | หลักฐาน | ช่องว่าง | ผล | ยาก |
|---|---|---|---|---|---|
| จุดชวนคอมเมนต์/แท็กเพื่อน | ❌ | grep "คอมเมนต์", "ดูจนจบ", loop ไม่เจอใน prompt | เพิ่ม beat คำถามปลายเปิดที่ไม่ผิดกฎ (ห้ามทายราคา) | M | S |

### H. Compliance

| ข้อ | สถานะ | หลักฐาน | ช่องว่าง | ผล | ยาก |
|---|---|---|---|---|---|
| ห้ามราคา/ส่วนลด | ❌ เสี่ยง | prompt ห้าม `ai_bridge.py:241` และถอด price key `:163,269-270` แต่ `_validate` เช็กแค่โครง `:343-364`; TTS แปลง "199.-"→"199 บาท" ✔ `tts_sanitizer.py:329-331`, เขียนเป็น "ราคาพิเศษ" `:283`; fallback hook "ถูกกับแพง"/"ไม่กี่บาท" ✔ `it_angles.py:23,83`; `CALLOUT_TYPES` มี "price" `product_callout_builder.py:21`; lint ราคามีแค่ couple `script_rules.py:39-49,179-188` | ต้องมี deterministic price lint ทุก output (สคริปต์, hook, on_screen, callout, TTS) | **H** | S |
| Claim เกินจริง | ❌ | prompt อย่างเดียว `ai_bridge.py:240`; offline hook แต่งเอง "ใช้จริงมา 3 เดือนเต็ม" `hook_generator.py:135,139`, "สั่งกันถล่มทลาย" `script_generator.py:47` | ถอด claim ปลอมจาก template + lint | H | S |
| จุดไข่ปลา | 🟡 | strip ใน hook/script/caption/TTS แต่ไม่ strip `on_screen` | เพิ่ม on_screen | L | S |
| ทับศัพท์แบรนด์ | 🟡 | rule + reverse map `tts_sanitizer.py:153-178`; แต่ dictionary ไฮไลต์มี "บลูทูธ"/"ฟาสชาร์จ" `translation_service.py:44-45` | ทำความสะอาด dictionary | L | S |
| อีโมจิ | 🟡 | strip ใน caption/TTS; แต่ SpecBar เติม "📊" `subtitle_engine.py:1426`, `hook_title` อนุญาต 1 อีโมจิ `hook_generator.py:195` | ถอด | L | S |
| ซับต่างชาติฝังในฟุตเทจ | — | ไม่ได้ตรวจในรอบนี้ (ต้องดูภาพจริง ไม่ใช่โค้ด) | ควรมี vision check ตอน intake | M | M |

---

## 3. วิเคราะห์ Style Preset 10 แบบ

ค่าจาก `scripts/style_motion_policy.py:54-257`, catalog `frontend/src/lib/stylePresetCatalog.js:13-187`

| preset | transition ทุก N | กล้องทุก N | zoom Δ | ช็อต (วิ) | family | ความต่างจริง | ข้อเสนอ |
|---|---|---|---|---|---|---|---|
| viral_punch | 2 | 1 | .12 | 1.5–2.2 | energetic | ฐานของกลุ่ม punch | **คง** — เป็นแกน "Punch" |
| flash_deal | 2 | 1 | .12 | 1.5–2.0 | energetic | motion เหมือน viral_punch ทุกค่า ต่างแค่ max_shot + สี | **รวม motion เข้า viral_punch**; ชื่อ/angle "fomo_deal" เสี่ยงพาสคริปต์ไปพูดเรื่องราคา → เปลี่ยนเป็น urgency แบบไม่พูดราคา |
| pain_punch | 2 | 1 | .14 | 1.5–2.3 | energetic | ต่างแค่ stylized stride + zoom นิด | **รวม motion เข้า viral_punch** คงไว้เป็น "hook/script variant" |
| clean_tech_review (default) | 5 | 2 | .08 | 1.5–2.5 | adaptive | เรียบสุดในกลุ่ม tech | **คงแต่จูน** — เป็น default ที่ช้าเกินสำหรับไวรัล |
| tech_compare | 3 | 2 | .08 | 1.7–2.7 | adaptive | กล้องเหมือน clean_tech_review; label สัญญา "Wipe ซ้ายขวา" แต่ wipe มาจาก tone=="major" เท่านั้น `pipeline.py:66` | **จูน** ให้มี split/compare layout จริง หรือรวม |
| tech_product_showcase | 3 | 1 | .10 | 1.6–2.6 | energetic | ใกล้ niche_focus มาก | **รวมกับ niche_focus** |
| niche_focus | 4 | 2 | .10 | 1.6–2.6 | energetic | label สัญญา "Zoom" แต่ energetic ให้แค่ slide/circle | รวม |
| smooth_showcase | 3 | 1 | .05 | 1.8–2.8 | smooth | dissolve ทุก 3 รอยตัด | **คง** เป็นแกน "Smooth" |
| smart_hack | 3 | 1 | .06 | 1.6–2.4 | smooth | เหมือน smooth_showcase; `ease_out` ไม่มีผลเพราะ dissolve ไม่ใช้ easing `:274-284,330-331`; label "Slide นุ่มนวล" ไม่ตรง render `stylePresetCatalog.js:143` | **รวม** หรือทำให้ต่างจริง (ใส่ speed ramp/step reveal) |
| premium_minimal | 6 | 3 | .04 | 1.8–3.0 | minimal | label "Fade เฉพาะ Section" แต่จริงคือ fade ทุก 6 รอยตัด `:141,333` | **คง** เป็นแกน "Premium" |

**สรุป:** motion ที่ผู้ชมแยกออกจริงมีแค่ **4 แกน** (Punch / Tech / Smooth / Premium). อีก 6 แบบต่างกันแค่สีและตัวเลขเล็กน้อย

**ข้อจำกัดเชิงโครงสร้าง:** preset คุมแค่ transition, กล้อง, จังหวะตัด, สี accent และ hook template **ไม่คุม** สคริปต์, ความยาว, ซับ, ฟอนต์ (Kanit ทุกตัว), BGM, LUT หรือความถี่ SFX (`it_angles.py:117,135,150-161`; grep SFX ไม่เจอ `style_preset`). ผลคือ "สไตล์" เป็นแค่ผิวหน้า ไม่ใช่วิธีเล่าเรื่อง

**บั๊ก/ความไม่สอดคล้องที่เจอ**
- `BatchRenderModal.jsx:400-403` ส่ง `'commercial_premium'` ซึ่งไม่ใช่ preset id ✔ → fallback เป็น clean_tech_review แบบเงียบ ๆ (`style_motion_policy.py:303-304`) และ angle default ทับค่าที่ผู้ใช้เลือก (`batch_render.py:636-638`)
- `it_angles.py` ใช้ angle key ชุดอื่น (spec_compare, fake_vs_real, …) ตรงกับ `ANGLE_TO_DEFAULT_STYLE` แค่ `pain_point` → ที่เหลือตกไป default (`it_angles.py:14-98` vs `stylePresetCatalog.js:176-187`)
- `hookColor` ≠ accent ใน tech_product_showcase/smooth_showcase (`stylePresetCatalog.js:55,60,70,75`), `color_theme.py:21-80` ไม่ตรงกับ policy; schedule diversity ฝั่ง frontend กับ backend เลยคำนวณไม่ตรงกัน
- เปลี่ยน preset หลังเจนแล้วได้แค่สี/hook template เพราะ transition/กล้อง/จังหวะ bake ลง clip metadata ไปแล้ว (`video_assembly_stage.py:153-159`)

---

## 4. สไตล์การตัดใหม่ (เสนอ 4 แบบ)

หลักคิด: ก่อนเพิ่ม ให้ **รวม 10 → 4 motion family** ก่อน แล้วเปลี่ยนนิยาม "สไตล์" เป็น **Story Format × Motion Family** (Story Format คุมสคริปต์/ความยาว/beat; Motion Family คุมการตัด) แทนการเพิ่ม preset อีก 10 ตัวที่ต่างกันแค่สี
4 แบบด้านล่างคือ **Story Format** ใหม่ ส่วน Seamless Loop เป็น **modifier** ที่ใช้ร่วมกับทุก format

> ทุก beat sheet ใช้ได้กับ 1080x1920 / 30fps / safe zone ล่างตาม font contract; ไม่พูดราคา; ตัวเลขทั้งหมดเป็น [best practice]/[สมมติฐาน] จนกว่าจะมีข้อมูลช่องจริง

### 4.1 Countdown "3 เหตุผล" (Listicle)
- **เป้า metric:** completion (คนรอดูข้อ 1) [best practice]
- **Beat sheet (~25 วิ):** 0–1.5 วิ ข้อความ "3 เหตุผลที่ {สินค้า} {ผลลัพธ์}" + ช็อตสินค้า motion สูง · 1.5–3 วิ "ข้อ 1 ดีสุด เก็บไว้ท้าย" (open loop) · 3–9 / 9–15 / 15–22 วิ ข้อ 3→2→1 แต่ละข้อมีตัวเลขใหญ่ (#3 #2 #1) + punch zoom + SFX ตอนเปลี่ยนข้อ · 22–25 วิ payoff + CTA ตะกร้า
- **Policy:** Punch family, ช็อต 1.2–2.0 วิ, transition ทุกครั้งที่เปลี่ยนข้อ, ซับ burst สั้น, SFX เฉพาะตอนเปลี่ยนข้อ (ไม่ใช่ทุกบรรทัด)
- **Hook:** curiosity · **เหมาะ:** สินค้าฟีเจอร์ชัด 3 อย่างขึ้นไป · **ไม่เหมาะ:** สินค้าฟีเจอร์เดียว
- **วัตถุดิบ:** อย่างน้อย 3 ช็อตต่อฟีเจอร์ · fallback: รูปสินค้าทางการ + Ken Burns (`image_motion_engine.py`)
- **ใช้ engine เดิมได้ ~70%:** ต้องเพิ่ม prompt template, overlay ตัวเลขลำดับ (เพิ่มใน `overlay_model` + SequencePlayer คู่กันเพื่อ parity), beat → transition mapping
- **ความเสี่ยง:** overlay ใหม่ต้องผ่าน `test_preview_render_parity.py`

### 4.2 Problem → Solution Reveal (Before/After)
- **เป้า metric:** hook rate + share [best practice]
- **Beat sheet (~20 วิ):** 0–2 วิ ภาพปัญหา + ข้อความปัญหา (เช่น "แบตหมดกลางทาง") · 2–4 วิ ขยี้ปัญหา 1 ประโยค · 4–5 วิ **reveal**: speed ramp ช้า→เร็ว + whoosh + สินค้าเต็มจอ · 5–16 วิ วิธีแก้ 2–3 ฉาก · 16–20 วิ ผลลัพธ์ (After) + CTA
- **Policy:** ช็อตช่วงปัญหายาว 2–2.5 วิ (ให้รู้สึก) → หลัง reveal 1.2–1.8 วิ (pacing curve แบบกลับด้าน), speed ramp 1 จุด
- **Hook:** pain_point · **เหมาะ:** ของใช้แก้ปัญหาชัด (powerbank, ที่ชาร์จ, จัดระเบียบ) · **ไม่เหมาะ:** ของแฟชั่น/ของสะสม
- **วัตถุดิบ:** ต้องมีช็อต "ปัญหา" — ถ้าไม่มี ใช้ข้อความบนพื้นมืด/เบลอแทน (ห้ามใช้ฟุตเทจที่มีซับต่างชาติ)
- **ใช้ engine เดิมได้ ~50%:** ต้องเพิ่ม speed ramp primitive (ยังไม่มี `shot_matching_stage.py:1236`) ทั้งใน ffmpeg (setpts) และ SequencePlayer

### 4.3 Myth-buster "เข้าใจผิดมาตลอด"
- **เป้า metric:** comment + rewatch [best practice]
- **Beat sheet (~20 วิ):** 0–1.5 วิ "หลายคนคิดว่า {ความเชื่อ}" + ป้าย "จริงไหม?" · 1.5–3 วิ "ผิด" (ภาพ+SFX หยุด) · 3–15 วิ อธิบายด้วยสเปก/เดโมจริง · 15–18 วิ สรุป · 18–20 วิ คำถามปลายเปิด "เคยเข้าใจแบบนี้ไหม" + CTA
- **Policy:** Tech family, transition ตอนพลิกประเด็น, ไฮไลต์ตัวเลขสเปก
- **Hook:** warning/curiosity · **เหมาะ:** สินค้าที่มีความเชื่อผิด ๆ (mAh vs ชาร์จจริง, W สูงไม่ได้แปลว่าเร็ว) · **ข้อห้าม:** ห้ามอ้างข้อเท็จจริงที่ไม่มีสเปกยืนยัน ต้องผ่าน claim lint
- **ใช้ engine เดิมได้ ~80%:** ส่วนใหญ่เป็นงาน prompt + lint

### 4.4 Seamless Loop (modifier ใช้กับทุก format)
- **เป้า metric:** rewatch / avg watch time >100% [best practice]
- **กลไก:** ประโยคสุดท้ายจบด้วยวลีที่ต่อกับประโยคแรกได้ (เช่น ท้าย "…เพราะแบบนี้ไง" → ต้น "ทำไมคนถึงเลิกพกสายชาร์จ"); ช็อตท้ายใช้ framing ใกล้ช็อตแรก; BGM ไม่ fade-out แต่ตัดที่ beat; ไม่ค้างเฟรมท้าย
- **ใช้ engine เดิมได้ ~60%:** ต้องแก้ prompt, BGM tail ใน `sfx_manager.py:477-480`, freeze tail `video_editor.py:2054-2057`
- **ข้อจำกัด:** CTA ตะกร้ายังต้องมี → วาง CTA ก่อนประโยค loop

### พักไว้ (ยังไม่เสนอ)
- **ASMR Unboxing / Silent Text-Story** — ต้องใช้ฟุตเทจถ่ายเอง/เสียงจริงคุณภาพสูง ซึ่ง pipeline ปัจจุบันพึ่ง VO + B-roll; ทำหลังมีข้อมูลช่องว่า format VO ไม่พอ
- **Speed-ramp Reveal เป็น preset เดี่ยว** — ทำเป็น primitive ใน 4.2 แทน

---

## 5. ความสามารถ AI Editor ที่ควรเพิ่ม

| ไอเดีย | มีแล้ว? | หลักฐาน | คุ้ม? | ทำตรงไหน |
|---|---|---|---|---|
| Pre-render Viral Lint (dead air, ช็อตยาว, hook ช้า, ไม่มี interrupt เกิน N วิ, ราคาในข้อความ) | 🟡 มี preflight แต่เช็กแค่ความถูกต้องเชิงเทคนิค | `frontend/src/lib/renderPreflight.js:16-115` | **สูง** — deterministic ถูก ทำครั้งเดียวใช้ทุกคลิป | backend `scripts/viral_lint.py` (ใหม่) + แสดงใน `RenderPreflightNotice.jsx` |
| Retention heatmap บน Timeline | ❌ | — | กลาง — ใช้ผล lint มาวาดได้ | `editor/timeline/` |
| Auto pattern interrupt (zoom punch/SFX ตรงคำสเปก) | ❌ | zoom cycle ตายตัว `shot_matching_stage.py:753` | สูง | shot_matching + subtitle keyword |
| Hook A/B batch render | ❌ | 1 item ต่อ angle `batch_render.py:296-309,611-613` | สูง แต่ต้องมี data loop ก่อนถึงจะวัดผลได้ | batch_render + export registry |
| อธิบาย "ทำไม AI ตัดตรงนี้" | ❌ | มีแค่เหตุผลตอน silence cut `EditorShell.jsx:529-537` | กลาง — ช่วยผู้ใช้แก้เร็ว | manifest เพิ่ม `cut_reason` → Inspector |
| One-click style swap เก็บ edit มือ | 🟡 | เก็บ hook template ที่ custom `EditorShell.jsx:2029-2041` แต่ transition/กล้อง bake ไปแล้ว | กลาง | ต้อง re-plan เฉพาะคลิปที่ไม่ได้แก้มือ |
| สลับช็อตเดียว (reroll per shot) | ❌ | reroll ทั้งโปรเจกต์ `api_phase1.py:524-526` | สูงสำหรับ UX | API + TimelineContextMenu |
| CoPilot สั่งแก้ด้วยภาษาพูด | ❌ | CoPilot เป็นแชท brief ใช้ keyword `copilot_engine.py:441-486`, ไม่มี route แก้ timeline | ต่ำ-กลาง (ทำทีหลัง lint/format) | — |
| Feedback loop สไตล์ ↔ ผลจริง | ❌ | ไม่มี watch time/completion `post_log.py:29`; ไม่เก็บ `hook_style`; registry ไม่มี style/duration `export_registry.py:439-449`; grep recommend/by_style ไม่เจอ | **สูงที่สุดระยะยาว** — ไม่มีอันนี้ ทุกข้อเสนอเป็นแค่สมมติฐาน | post_log + export registry + Performance tab |

**ผิดกฎ AGENTS ข้อ 24 ที่เจอระหว่างทาง:** `batch_render.py` ไม่มี `ThreadPoolExecutor`/`max_workers` ✔ — dispatcher เดียววิ่งทีละ item (`batch_render.py:4-6,165-202`) ทั้งที่กฎบังคับ 4 workers

---

## 6. แผนเดิมที่ทับซ้อน (ไม่เสนอซ้ำ)

- `PRO_EDITOR_STYLE_PLAN.md`: Phase 2A–3B เสร็จแล้ว (pacing, 4 preset แรก, camera keyframe parity); **Phase 4 (ducking/SFX policy/loudness), 5 (template gallery), 6 (golden master) ยังไม่ทำ** → แผนใหม่ต่อยอด Phase 4 แทนการเขียนใหม่
- `TEMPLATE_MOTION_PLAN.md`: Round 3–7 ปิดแล้ว (per-word layout/animation) ไม่ทับซ้อน
- `PLAN_SPEED_TRANSITION_TEXT_STYLE_20261004.md`: checkbox ยังไม่ติ๊ก แต่โค้ดมีแล้ว (`ClipInspector.jsx:287,698`, `OverlayInspector.jsx:89-91`) → เอกสารล้าสมัย [สมมติฐาน] ควรปิดรอบ

---

## 7. Jev decision layer

- `tools/jev_advisor.py --check` → ok, key present
- `choice` คำถาม "แก้ข้อไหนก่อน ผลไวรัล/แรงสูงสุดโดย compliance ห้ามพัง" ตัวเลือก compliance/hook/pacing/subs/script/data → **เลือก `hook` confidence 0.74 → verdict escalate**
- ต่ำกว่าเกณฑ์ 0.80 → ส่งให้ผู้ใช้ตัดสิน (อยู่ในคำถามของแผน) ผล Jev ไม่ใช่หลักฐานหรือการอนุมัติ

---

## 8. สิ่งที่ยังไม่ได้ตรวจในรอบนี้

- ไม่ได้เรนเดอร์คลิปจริงเพื่อดูเฟรม (รอบ audit อย่างเดียว) — ตัวเลข pacing ทั้งหมดมาจากโค้ด ไม่ใช่การวัดคลิปที่ส่งออกจริง
- ไม่ได้ตรวจ path guided-take / storyboard ว่าข้าม rhythm logic จริงไหม
- ไม่ได้ตรวจ couple engine / HyperFrames ในเชิง retention (คนละ pipeline)
- ไม่ได้ดึงสถิติ TikTok จริงมาดูว่า preset/angle ไหนทำผลได้ดี (ข้อมูล watch time ไม่มีให้ดึง)
