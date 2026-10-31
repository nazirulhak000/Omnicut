# PROMPT — AI Editor & Auto-Cut Viral Style Audit (วางแผนอย่างเดียว ห้ามแก้โค้ด)

> วิธีใช้: คัดลอกทั้งบล็อกด้านล่างไปวางให้ AI agent (Claude Code / Codex / Antigravity) ที่เปิดอยู่ในรากโปรเจกต์ OmniCut

---

```text
บทบาท: คุณคือ Senior Video Editor สาย TikTok Shop + Retention Strategist + Software Architect
ที่ต้อง audit ระบบ "AI Editor / AI ตัดคลิปอัตโนมัติ" ของ OmniCut Pro Studio แล้วเขียนแผนปรับปรุง
เป้าหมายเดียว: คลิปที่ระบบเจนออกมา "มีโอกาสไวรัลสูงขึ้น" (hook rate, average watch time, completion rate,
rewatch, share/comment, add-to-cart) โดยไม่ผิดกฎโปรเจกต์และกฎ TikTok

=== ขอบเขต ===
- งานรอบนี้ = AUDIT + PLAN เท่านั้น ห้ามแก้โค้ด ห้ามเรนเดอร์ลง 04_Exports ห้ามยิง paid API
- ถ้าต้องเรนเดอร์ตัวอย่างเพื่อดูเฟรมจริง ให้ใช้ .tmp/ แล้วลบทิ้ง 100% หลังดู
- ทุกข้อสรุปต้องมีหลักฐาน `path:line` จากโค้ดจริง ถ้าไม่มีหลักฐานให้ติดป้าย [สมมติฐาน]
- ความรู้เรื่อง "อะไรทำให้ไวรัล" ให้ติดป้าย [best practice] หรือ [สมมติฐาน] ห้ามอ้างเป็นข้อเท็จจริงลอย ๆ

=== ขั้น 0: อ่านก่อนเริ่ม (บังคับ) ===
1. AGENTS.md, TODO.md (ส่วนบน), ARCHITECTURE.md, .agents/rules/work_loop.md
2. กฎที่เกี่ยวกับการตัด: .agents/rules/{gadget_editing_style_checklist, subtitle_kinetic_rules,
   j_cut_rules, preview_render_parity, font_text_visual_contract, pov_couple_line_chat_standard}.md
3. _Docs/GADGET_VIDEO_PRODUCTION_SOP.md และแผนเดิมที่ทับซ้อน: _Docs/Plans/PRO_EDITOR_STYLE_PLAN.md,
   TEMPLATE_MOTION_PLAN.md, PROMPT_EDITOR_VS_CAPCUT_DEEP_AUDIT.md (ห้ามเสนอซ้ำของที่แผนเดิมมีแล้ว ให้อ้างถึงแทน)
4. เขียนบล็อกรอบงานลง TODO.md ก่อนเริ่ม พร้อม "ดำเนินการโดย: <เอเจนต์> (<โมเดล>)"
5. ประหยัดโทเคน: อ่านไฟล์ใหญ่ทีละไม่เกิน 100 บรรทัด ใช้ grep หา symbol ก่อนเปิด ห้ามเปิด HISTORY.md ทั้งไฟล์

=== ขั้น 1: แผนที่ระบบตัดต่อปัจจุบัน (Inventory) ===
ไล่ data flow จริงตั้งแต่ สินค้า → สคริปต์ → เสียง → เลือกช็อต → ประกอบ → ซับ → มิกซ์ → export
ไฟล์ตั้งต้น (ตรวจว่ายังมีจริงก่อนอ้าง):
- สคริปต์/hook: scripts/script_generator.py, script_rules.py, script_tone_analyzer.py,
  hook_generator.py (HOOK_STYLES), hook_styles.py, hook_motion_presets.py, it_angles.py
- จังหวะ/สไตล์: scripts/style_motion_policy.py (10 policy), editorial_pacing.py, beat_sync.py,
  silence_detect.py, voice_cut_map.py, keyframe_engine.py, image_motion_engine.py, spotlight_effect.py
- เลือกช็อต/เข้าใจภาพ: scripts/stages/shot_matching_stage.py, gemini_vision_matcher.py,
  video_semantic_indexer.py, motion_analyzer.py, shot_source_window.py, color_match.py
- ประกอบ/ซับ/เสียง: scripts/stages/{script,voice,video_assembly,subtitle,audio_mix}_stage.py,
  subtitle_engine.py, sfx_manager.py, pipeline.py, tiktok_enhancer.py
- สไตล์คู่รัก/HyperFrames: scripts/couple_engine/, couple_script_generator.py, hyperframes_*.py
- Frontend: frontend/src/lib/stylePresetCatalog.js (10 preset), components/ProductToClip.jsx,
  components/editor/{EditorShell,StylePresetPicker,Timeline,Inspector}.jsx, SequencePlayer.jsx,
  HookVariationModal.jsx, AICoPilotChat.jsx, analytics/tabs/ (Performance)

ส่งออกเป็นตาราง: ขั้น | ไฟล์หลัก | AI ตัดสินอะไร | อะไรเป็น rule ตายตัว | style preset ไปมีผลตรงไหน | จุดอ่อน

=== ขั้น 2: Viral Checklist ละเอียด (ให้คะแนนทีละข้อ) ===
แต่ละข้อรายงาน: สถานะ (มีครบ/บางส่วน/ไม่มี) | หลักฐาน path:line | ช่องว่าง | ผลต่อไวรัล (H/M/L) | ความยาก (S/M/L)

A. 0–1 วินาทีแรก (Hook / Scroll-stop)
 - เฟรมแรกมีการเคลื่อนไหว/สินค้าเต็มเฟรม ไม่ใช่ fade-in จากดำ หรือโลโก้
 - Text hook ขึ้นภายใน 0.3 วิ อ่านจบ < 1.5 วิ อยู่ใน safe zone
 - เสียงพูดเริ่มทันที ไม่มี dead air ต้นคลิป (วัดจาก silence_detect)
 - Hook ทั้ง 3 ชั้นสอดคล้องกัน: ภาพ + ข้อความ + เสียงพูด
 - ระบบเจน hook หลายแบบให้เลือก/ทำ A/B ได้ไหม (HookVariationModal) และเลือกตามอะไร
B. 1–5 วินาที (Retention gate)
 - Open loop / สัญญาว่าจะได้อะไรถ้าดูต่อ
 - ช็อตแรก ๆ สั้นกว่าช่วงกลางคลิป (pacing curve) หรือยาวเท่ากันหมด
C. กลางคลิป (Retention curve)
 - ความยาวช็อตเฉลี่ย/สูงสุดต่อ preset (MIN/MAX_SHOT_DURATION) เทียบกับ 1.5–3 วิ
 - Pattern interrupt ทุก 2–4 วิ: zoom punch, speed ramp, angle change, SFX, text pop
 - ไม่มีช็อตนิ่ง/ภาพซ้ำนานเกิน threshold, ไม่มี dead air กลางคลิป
 - Strict Topic Hold: ภาพตรงกับที่พูดทั้งประโยค (shot matching confidence ต่ำทำอะไร)
 - Beat sync กับ BGM และ J-cut 150–250ms ทำงานจริงทุก preset หรือเปล่า
D. ข้อความ/ซับ
 - Kinetic sub burst 2–4 คำ, keyword highlight ถูกคำ (ฟีเจอร์/ตัวเลขสเปก ไม่ใช่คำเชื่อม)
 - Callout สเปกขึ้นตรงจังหวะพูดสเปก
E. เสียง
 - VO pace (คำ/วินาที), SFX density ไม่ล้น, BGM ducking, loudness เท่ามาตรฐาน TikTok
F. ตอนจบ
 - Payoff ชัด, CTA ไม่ยืด, ปลายคลิปต่อกับต้นคลิปเป็น loop ได้ (rewatch)
 - ความยาวรวมเหมาะกับ angle (15 / 30 / 45–60 วิ) ระบบเลือกเองหรือ fix
G. Engagement trigger
 - มีจุดชวนคอมเมนต์/ถกเถียง/แท็กเพื่อน ที่ไม่ผิดกฎ
H. Compliance (ถ้าผิด = ไวรัลไม่ได้)
 - ห้ามแสดงราคา/ส่วนลด/ให้ทายราคาในคลิปเด็ดขาด
 - ห้ามคลิปที่มีซับจีน/ซับต่างชาติฝัง, ห้ามอ้างสรรพคุณเกินจริง
 - ห้าม "..." ในบทพูด, ห้ามทับศัพท์แบรนด์เป็นไทย, ห้ามอีโมจิในปก/CTA

สรุปท้ายขั้น: Viral Readiness Score รายข้อ A–H (0–10) + ต่อ preset 10 แบบ

=== ขั้น 3: วิเคราะห์ Style Preset ที่มี ===
Preset ปัจจุบัน: viral_punch, clean_tech_review, tech_product_showcase, smooth_showcase,
premium_minimal, flash_deal, pain_punch, tech_compare, smart_hack, niche_focus
และ hook styles ใน hook_generator.HOOK_STYLES
สำหรับแต่ละ preset:
 - ค่า policy จริง (transition stride, camera zoom/pan, shot duration, transition family)
 - ต่างจาก preset อื่นจริงไหม — ผู้ชมแยกออกไหม หรือแค่ค่าต่างกันนิดเดียว (หาตัวซ้ำซ้อน → เสนอรวม/ตัด)
 - ผูกกับ hook/angle อย่างไร (getRecommendedStyleForAngle) และเหมาะกับสินค้าแบบไหน
 - Preview (SequencePlayer) กับ Render (ffmpeg) ตรงกันทุกเอฟเฟกต์ของ preset นี้หรือไม่
ผล: ตาราง preset × (ความต่าง, จุดแข็ง, จุดอ่อน, ข้อเสนอ: คงไว้/จูน/รวม/ตัด)

=== ขั้น 4: เสนอสไตล์การตัดใหม่ (สูงสุด 3–5 แบบ) ===
ก่อนเสนอใหม่ ต้องตอบก่อนว่า "จูน preset เดิมแทนได้ไหม" ถ้าได้ ให้จูนแทน
ไอเดียตั้งต้น (เลือก/ตัด/เพิ่มเองได้ ต้องมีเหตุผล):
 - Seamless Loop (จบต่อต้นคลิปเนียน เพิ่ม rewatch)
 - Countdown "3 เหตุผลที่..." (listicle, open loop ข้อสุดท้าย)
 - Before/After split หรือ Problem → Solution reveal
 - Myth-buster / "เข้าใจผิดมาตลอด"
 - ASMR Unboxing / Satisfying (เสียงจริง + ซับน้อย)
 - Speed-ramp Reveal (ช้า→เร็ว ตรงจุดเผยฟีเจอร์)
 - Silent Text-Story (ไม่มี VO ใช้ข้อความเล่าเรื่อง)
แต่ละสไตล์ใหม่ต้องมี:
 1. เป้า metric ที่จะดัน (เช่น completion, rewatch, comment)
 2. Beat sheet ตามวินาที (0–1, 1–3, 3–X, ending) ระบุภาพ/ข้อความ/เสียง/SFX แต่ละช่วง
 3. ค่า StyleMotionPolicy ที่เสนอ + กฎซับ + กฎเสียง + hook style ที่ผูก
 4. สินค้า/angle ที่เหมาะ และที่ห้ามใช้
 5. วัตถุดิบที่ต้องมี (ฟุตเทจแบบไหน กี่ช็อต) — ถ้าวัตถุดิบไม่พอ ระบบ fallback อย่างไร
 6. ทำได้ด้วย engine เดิมกี่ % ต้องเพิ่มอะไร (ไฟล์ไหน) + ความเสี่ยงต่อ Preview=Render / font contract
 7. ตัวอย่าง storyboard 1 คลิปจากสินค้าที่มีจริงในระบบ

=== ขั้น 5: ความสามารถ AI Editor ที่ควรเพิ่ม ===
ประเมินทีละไอเดีย (มีแล้ว?/คุ้มไหม/ทำตรงไหน):
 - Pre-render Viral Lint: สแกน manifest ก่อนเรนเดอร์ เตือน dead air, ช็อตนิ่งยาว, hook ช้า,
   ข้อความล้น safe zone, ไม่มี pattern interrupt เกิน N วิ (deterministic ก่อน AI)
 - Retention heatmap บน Timeline (คาดจุดคนปัดทิ้ง จาก heuristic)
 - Auto pattern interrupt: zoom punch/SFX อัตโนมัติตรง keyword สเปก
 - Hook A/B batch: เจนหลาย hook ต่อสคริปต์เดียว เรนเดอร์ขนาน (ThreadPoolExecutor 4 workers)
 - "ทำไม AI ตัดตรงนี้" — อธิบายเหตุผลการตัด/เลือกช็อตใน Inspector ให้ผู้ใช้แก้ได้
 - One-click style swap พร้อม preview ทันทีโดยไม่เสีย edit ที่ทำเอง
 - AI CoPilot สั่งแก้ด้วยภาษาพูด ("ทำ hook ให้แรงขึ้น", "ตัดให้กระชับเหลือ 30 วิ")
 - Feedback loop: ผูก style_preset + hook_style + ความยาว กับผลจริงจาก TikTok stats
   (views, avg watch time, completion) → แนะนำ style ตามข้อมูลจริงของช่อง
   ตรวจว่าตอนนี้เก็บ field อะไรไว้แล้วบ้าง ขาดอะไร
ใช้ tools/jev_advisor.py ช่วยจัดลำดับเมื่อทางเลือก 3–7 อัน ตาม jev_decision_layer.md
(confidence < 0.80 = หยุดถามผู้ใช้)

=== ขั้น 6: Roadmap ===
จัดเป็น 3 ระดับ:
 - Quick wins (≤ 1 วัน/ข้อ, ไม่แตะ schema)
 - Mid (2–5 วัน)
 - Big bets (ต้องออกแบบเพิ่ม/เปลี่ยน manifest)
ทุกข้อต้องมี: ปัญหา → วิธีแก้ → ไฟล์ที่แตะ → ผลต่อ metric ที่คาด → Acceptance Criteria วัดได้ →
แผนเทส (pytest offline/temp storage, test_preview_render_parity.py ถ้าแตะ preview/subtitle,
snapshot เฟรมจริงใน .tmp) → ความเสี่ยงและวิธี rollback
เรียงตาม (ผลต่อไวรัล × ความมั่นใจ) / ความยาก

=== กฎเหล็กที่ห้ามละเมิดในข้อเสนอ ===
- 1080x1920, 30 FPS, ข้อความไม่ชิดขอบขวา-ล่าง, safe zone ล่างตาม font_text_visual_contract
- ห้ามเปลี่ยนฟอนต์/ขนาด/outline/ตำแหน่งซับโดยไม่ระบุว่าเป็นข้อเสนอที่ต้องให้ผู้ใช้อนุมัติ
- Preview = Render: เอฟเฟกต์ใหม่ต้องทำได้ทั้ง SequencePlayer.jsx และ ffmpeg
- ไม่มีราคา/ส่วนลดในคลิป, ไม่มีซับต่างชาติฝัง, ไม่มีโลโก้แปลกปลอม, สติกเกอร์เฉพาะ Universal Badges 6 แบบ
- งาน batch ต้อง concurrent 4 workers + resume gate, GPU (cuda/NVENC) เป็นค่าเริ่มต้น
- ห้ามเสนอ copy คลิป/สไตล์ของครีเอเตอร์รายใดรายหนึ่งตรง ๆ ให้สรุปเป็นหลักการ

=== ผลลัพธ์ที่ต้องส่ง ===
1. _Docs/Reports/AI_EDITOR_VIRAL_AUDIT_<YYYYMMDD>.md — ขั้น 1–5 ครบ พร้อมหลักฐาน path:line
2. _Docs/Plans/PLAN_AI_EDITOR_VIRAL_STYLES_<YYYYMMDD>.md — Roadmap ขั้น 6
3. สรุปในแชทไม่เกิน 15 บรรทัด: Top 5 สิ่งที่ควรทำก่อน + เหตุผล
4. รายการ "คำถามที่ต้องให้ผู้ใช้ตัดสิน" (เช่น ยอมเปลี่ยนสไตล์ซับไหม, ตัด preset ไหนได้, ความยาวคลิปเป้าหมาย)
5. อัปเดต TODO.md (ระบุเอเจนต์+โมเดล) — ห้ามแก้โค้ดในรอบนี้

=== Self-check ก่อนส่ง ===
[ ] ทุก claim เรื่องโค้ดมี path:line และเปิดดูแล้วจริง
[ ] แยก [best practice] / [สมมติฐาน] / [หลักฐานจากโค้ด] ชัด
[ ] ไม่เสนอซ้ำกับแผนเดิมใน _Docs/Plans โดยไม่อ้างถึง
[ ] ทุกข้อเสนอผ่านกฎเหล็กข้างบน
[ ] ทุก roadmap item มี Acceptance Criteria + แผนเทส
[ ] ไม่มีไฟล์ทดสอบค้างใน 04_Exports / 03_Projects / .tmp
```
