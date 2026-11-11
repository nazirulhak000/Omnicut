# รายละเอียดสไตล์การตัดต่อทั้งหมดของ OmniCut Pro Studio

> **จัดทำ:** 2026-11-11 · **ดำเนินการโดย:** Claude Code (Claude Sonnet 5.5)
> **ที่มาของตัวเลข:** อ่านจากโค้ดจริงใน `main`/working tree ณ วันที่ทำเอกสาร ตารางทุกตารางในส่วนที่ 2–7 สร้างจากโค้ดด้วยสคริปต์ (ไม่ได้พิมพ์ตัวเลขมือ) — ถ้าโค้ดเปลี่ยน เอกสารนี้จะล้าสมัย ให้ถือโค้ดเป็นหลัก
> **ขอบเขต:** สไตล์ของคลิปที่ pipeline ตัดต่อให้ (แนวตั้ง 9:16, 1080×1920, 30 FPS) ตั้งแต่จังหวะตัด, transition, กล้อง, Hook, ซับ, overlay, เสียง จนถึงปก
> **ที่ยังไม่ได้ตรวจลึก:** สไตล์คลิปละครคู่รัก (Couple Paper Chat / POV LINE chat) — สรุปเฉพาะกฎระดับ `AGENTS.md` ในส่วนที่ 12 ไม่ได้อ่านโค้ดของสไตล์นั้น

---

## สารบัญ

1. ภาพรวม: สไตล์ประกอบด้วยกี่ชั้น
2. Style Preset 10 แบบ (ตัวเลือกหลักของคลิป)
3. จังหวะตัด (cut rhythm) และ J-Cut
4. Transition
5. กล้อง (push / pan) และภาพนิ่ง (Ken Burns)
6. Hook ต้นคลิป (Hook line + Nameplate + Template 18 แบบ)
7. ซับไตเติล (โหมด, Ghost Reveal, สีตาม Hook, ฟอนต์, ตำแหน่ง)
8. Overlay อื่นๆ (callout, SpecBar, ลายน้ำ, สติกเกอร์)
9. เสียง (เสียงพากย์, น้ำเสียงโฆษณา, มิกซ์)
10. โครงเรื่องและความยาว
11. ปก (Cover)
12. สไตล์พิเศษอื่นๆ และกฎ compliance
13. ความขัดแย้งของเอกสารเก่า / ช่องว่างที่ยังไม่ปิด
14. แผนที่ไฟล์โค้ด

---

## 1. ภาพรวม: สไตล์ประกอบด้วยกี่ชั้น

คลิปหนึ่งคลิปมีสไตล์ซ้อนกัน 6 ชั้น แต่ละชั้นตั้งได้แยกกัน

| ชั้น | เลือกอะไรได้ | เก็บที่ไหน | ผูกกับ Style Preset ไหม |
|---|---|---|---|
| **A. Style Preset** | 10 แบบ (ส่วนที่ 2) | `style_preset` ใน manifest | — (เป็นตัวหลัก) |
| **B. Hook template** | 18 แบบ (8 legacy + 10 T1) | overlay `kind:"hook"` | preset เลือกให้อัตโนมัติ 1 ต่อ 1 แต่แก้แยกได้ |
| **C. ซับ** | โหมด ทีละคำ/ทั้งประโยค · สีตาม Hook เปิด/ปิด · ฟอนต์ 5 · สีซับ 5 · ตำแหน่ง 3 · ซับอังกฤษเปิด/ปิด | `style` ของโปรเจกต์ | โหมดไม่ผูก · สีผูกกับ Hook |
| **D. เสียง** | เสียงพากย์ 5 · น้ำเสียงโฆษณา 4 · อัตราพูด · BGM | manifest | ไม่ผูก |
| **E. โครงเรื่อง** | 5 รูปแบบ · ความยาวเป้าหมาย 5 ค่า | form สร้างคลิป | ไม่ผูก |
| **F. ปก** | Cover Studio (ส่วนที่ 11) | `05_Covers_Thumbnails/` | ไม่ผูก |

**หลักการร่วม:** preset ควบคุมเฉพาะ "จังหวะและการเคลื่อนไหว" (ตัด, transition, กล้อง) กับ "สี accent + Hook template" ส่วนฟอนต์/ขนาด/ตำแหน่งซับเป็น Golden Master ที่ preset ไม่แตะ (`font_text_visual_contract.md`)

**ค่า default:** `clean_tech_review` เป็น Golden Master และ One Click ใช้ตัวนี้เสมอ preset อื่นต้องให้ผู้ใช้เลือกเอง ค่าที่ไม่รู้จักหรือข้อมูลเก่า fallback กลับมาที่ตัวนี้

---

## 2. Style Preset 10 แบบ

ทุกแบบต้องรู้สึกต่างกันจริง — เทส `tests/test_style_distinctness.py` บังคับระยะห่างระหว่าง preset และลายนิ้วมือ transition ไม่ซ้ำ (ตัดสินใจโดยผู้ใช้ 2026-10-31, M5)

### 2.1 รายการและความตั้งใจ

| id | ชื่อ | ชื่อไทย | หมายเหตุ | คำอธิบายในระบบ |
|---|---|---|---|---|
| `viral_punch` | Viral Punch | ไวรัล กระชับ มีพลัง | แนะนำ | แกนของสาย Punch: ตัดเร็ว กล้องซูมและส่ายทุกช็อต Slide ถี่ เหมาะกับ Hook และคลิปขายสินค้า |
| `clean_tech_review` | Clean Tech Review | รีวิวเทคแบบคลีน | default | ภาพชัด จังหวะพอดี ใช้ motion เฉพาะช็อตที่ควรเด่น ตัดกระชับขึ้นช่วง Hook |
| `tech_product_showcase` | Tech Product Showcase | รีวิวสินค้าไอทีแบบภาพเด่น |  | โชว์สินค้าเต็มเฟรม กล้องส่ายกว้างสม่ำเสมอ เปิดรายละเอียดทีละจุด slide ต่อทิศทางกล้อง |
| `smooth_showcase` | Smooth Showcase | โชว์สินค้าไหลลื่น |  | กล้องนุ่ม ใช้ dissolve ล้วน เหมาะ Demo/Detail ที่ต้องดูต่อเนื่อง |
| `premium_minimal` | Premium Minimal | เรียบหรู จังหวะนิ่ง |  | ลดการเคลื่อนไหว ตัดช้าและนิ่ง fade เป็นระยะ คุมสีทอง |
| `flash_deal` | Flash Deal | โปรไฟลุก ดีลเด็ด |  | พลังมาจากการตัด ไม่ใช่การซูม: ช็อตสั้นสุด Hook แน่นสุด กล้องนิ่งกว่า |
| `pain_punch` | Pain Punch | ชี้ปัญหา กระตุกอารมณ์ |  | เปิดด้วยปัญหา ซูมเข้าหนักตอนขยี้จุดเจ็บ ตัดช้ากว่า Flash Deal ให้ประโยคปัญหาค้างให้ได้ยิน |
| `tech_compare` | Tech Comparison | เทียบสเปก วิเคราะห์ชัด |  | เน้นความน่าเชื่อถือ จังหวะสม่ำเสมอ สลับ wipe กับ slide ให้เห็นความต่าง |
| `smart_hack` | Smart Hack | ทริกลึก เคล็ดลับป้ายยา |  | ทีละขั้น ตัดคมแบบ hard cut กล้องสะกิดสั้นเข้าจังหวะทุกขั้น |
| `niche_focus` | Niche Focus | เจาะกลุ่ม เฉพาะสาย |  | push-in ลึก ค้างภาพนานให้อ่านฟังก์ชันทัน iris (circle) ทุก 4 รอยต่อ |

### 2.1.1 Preset ไวรัลเพิ่ม 5 แบบ (2026-11-11, รวมเป็น 15 แบบ)

ผู้ใช้เลือกเอง ไม่ผูกกับ angle อัตโนมัติ · เหตุผล ค่าเต็ม และเรื่องเสียงที่แนะนำ: `_Docs/Plans/VIRAL_STYLE_EXPANSION_PLAN_20261111.md`

| id | ชื่อไทย | ตระกูล transition | transition ที่เห็น | accent | Hook template |
|---|---|---|---|---|---|
| `raw_ugc` | รีวิวดิบแบบคนใช้จริง | hardcut | hard cut ล้วน | `#FFB38A` | `t2_ugc_peach` |
| `beat_drop` | ตัดตามบีท แฟลชขาว | flash | `fadewhite` ทุก 2 รอยต่อ | `#E845FF` | `t2_beat_magenta` |
| `swipe_stack` | ลิสต์เลื่อนฟีด | vertical | `slideup` ทุก 2 · `wipeup` ทุก 6 | `#22E55E` | `t2_swipe_green` |
| `proof_test` | พิสูจน์ให้ดู ลุ้นผล | chapter | `fadeblack` ทุก 5 | `#38BDF8` | `t2_proof_sky` |
| `glow_up` | ก่อน-หลัง เปิดม่าน | reveal | `wipedown` ทุก 4 · `circleopen` ทุก 8 | `#7C7BFF` | `t2_glow_indigo` |


### 2.2 สี accent และ Hook template ที่ผูก และ angle ที่ใช้เป็นค่าเริ่มต้น

`ANGLE_TO_DEFAULT_STYLE` (ต้องตรงกันระหว่าง `stylePresetCatalog.js` กับ `batch_render.py` — เทส `test_style_preset_consistency.py`) ตัวเลือก batch "auto" ใช้ preset ที่แนะนำของแต่ละ angle

| preset | accent | status | Hook template | angle ที่ใช้ preset นี้เป็นค่าเริ่มต้น |
|---|---|---|---|---|
| `viral_punch` | #FE2C55 | #25F4EE | `b1_viral_red` | stop_scroll · fake_vs_real |
| `clean_tech_review` | #FFE600 | #25F4EE | `b2_clean_yellow` | spec_review |
| `tech_product_showcase` | #FFCC33 | #25F4EE | `b2_tech_cyan` | unboxing · real_test |
| `smooth_showcase` | #25F4EE | #FFE600 | `b1_smooth_mint` | longterm_review |
| `premium_minimal` | #E6C24A | #D8C58A | `b2_premium_gold` | math_value · worth_upgrade |
| `flash_deal` | #FF7A00 | #25F4EE | `b1_deal_orange` | fomo_deal |
| `pain_punch` | #FF2E93 | #25F4EE | `b1_pain_pink` | pain_point · dont_cheap_out |
| `tech_compare` | #3B82F6 | #FFE600 | `b2_compare_blue` | comparison · spec_compare |
| `smart_hack` | #84CC16 | #25F4EE | `b1_hack_lime` | life_hack · how_to_setup |
| `niche_focus` | #A855F7 | #25F4EE | `b2_niche_purple` | niche_target · spec_explained |

---

## 3. จังหวะตัด (cut rhythm) และ J-Cut

ค่าอยู่ใน `scripts/style_motion_policy.py` (เดิมเป็นค่าคงที่ร่วม) ค่าเริ่มต้นร่วมจาก `scripts/config.py`: `MIN_SHOT_DURATION=1.5`, `MAX_SHOT_DURATION=2.5`, `J_CUT_OFFSET_SECONDS=0.18`, ค่า beat snap global `0.15`

| preset | min_shot (วิ) | max_shot (วิ) | ช็อตเปิด (hook_max_shot) | ภาพนิ่งนานสุด (max_static_sec) | J-lead (วิ) | beat snap (วิ) |
|---|---|---|---|---|---|---|
| `viral_punch` | 1.5 | 2.2 | 1.0 | 2.0 | 0.17 | 0.12 |
| `clean_tech_review` | 1.5 | 2.5 | 1.2 | 2.5 | 0.18 | 0.15 |
| `tech_product_showcase` | 1.7 | 2.6 | 1.2 | 2.0 | 0.18 | 0.1 |
| `smooth_showcase` | 1.8 | 2.8 | 1.5 | 3.0 | 0.21 | 0.1 |
| `premium_minimal` | 1.8 | 3.0 | 1.8 | 3.5 | 0.22 | 0.08 |
| `flash_deal` | 1.5 | 1.9 | 0.9 | 2.0 | 0.17 | 0.1 |
| `pain_punch` | 1.7 | 2.5 | 1.2 | 2.5 | 0.19 | 0.15 |
| `tech_compare` | 1.8 | 2.4 | 1.3 | 2.8 | 0.2 | 0.16 |
| `smart_hack` | 1.6 | 2.3 | 1.3 | 2.0 | 0.19 | 0.14 |
| `niche_focus` | 1.8 | 2.8 | 1.4 | 3.0 | 0.2 | 0.09 |

**ความหมาย**
- `min_shot` / `max_shot` — ความยาวช็อตต่ำสุด/สูงสุดที่ตัวจัดช็อตอัตโนมัติใช้
- `hook_max_shot` — ใน 3 วินาทีแรก ช็อตต้องสั้นกว่านี้ (ตัดเร็วขึ้นช่วงที่คนตัดสินใจปัดคลิป)
- `max_static_sec` — ห้ามมีช่วงใดนิ่งนานกว่านี้โดยไม่มีการตัด, transition หรือกล้องขยับ
- `J-lead` — เสียงประโยคใหม่มาก่อนภาพกี่วินาที (J-Cut) มาตรฐานโปรเจกต์ 150–250 ms; ทุกสไตล์ตั้งไว้ 0.17–0.22 เพื่อให้หลังปัดเข้ากริดเฟรม (±17 ms) ยังอยู่ในช่วงนี้
- `beat snap` — ดึงจุดตัดเข้าหาบีทเพลงได้ไกลสุดเท่านี้ และต้อง ≤ J-lead เสมอ (จุดตัดขยับเร็วขึ้นได้ แต่ไม่เคยเลื่อนมาก่อนเสียงเริ่ม)

**ค่า pacing ตาม family** (ใช้เมื่อ preset ไม่กำหนด `hook_max_shot`/`max_static_sec` เอง)

| family | hook_max_shot | max_static_sec |
|---|---|---|
| energetic | 1.0 | 2.0 |
| adaptive | 1.3 | 2.5 |
| smooth | 1.5 | 3.0 |
| minimal | 1.8 | 3.5 |
| compare | 1.3 | 2.5 |

**กติกาที่ใช้ทุกสไตล์**
- **ค้างภาพจนจบประโยค (Strict Topic Hold):** ถ้าจบประโยคอยู่ในระยะ `max_shot` ให้รอจบประโยคก่อนตัด ภาพต้องตรงกับที่เสียงกำลังพูดทั้งประโยค
- **ลำดับ snap:** beat > motion > voice-valley > rhythm (voice-valley = ขยับ ±2 เฟรมไปช่วง 10 ms ที่เงียบที่สุดของเสียงพากย์ โดย lead ต้องอยู่ 0.10–0.30 วิ)
- **J-Cut วัดจากไฟล์จริง:** ทุกรอยต่อภาพเปลี่ยนหลังเสียงเริ่ม; จุดตัดแรก = 0.0; transition วางกึ่งกลางจุดตัด (`j_cut_rules.md` §6)
- **กริดเฟรมเต็ม:** จุดตัด/ความยาว/offset ทั้งหมดอยู่บนกริด 1/30 วิแบบสะสม (`boundary_k = round(cumsum_k × 30) / 30`) พรีวิวกับเรนเดอร์ใช้เฟรมรวมเท่ากัน

---

## 4. Transition

Transition ที่ระบบสร้างอัตโนมัติผ่าน `apply_transition_budget` ที่ "งบ" ต่อสไตล์: ช่องที่ไม่ใช่รอบของ stride = ตัดตรง (hard cut) รายการ transition ที่แก้เอง (manual) ไม่ผ่านฟังก์ชันนี้

| preset | family | transition ทุก N รอยต่อ | circle ทุก N | ยาวสุด (วิ) | easing |
|---|---|---|---|---|---|
| `viral_punch` | energetic (slide สลับซ้าย/ขวา + circle ตามรอบ) | ทุก 2 | ทุก 6 | 0.28 | ease_out |
| `clean_tech_review` | adaptive (ใช้ตัวเลือก transition ของระบบ แต่ลดให้เหลือน้อย) | ทุก 5 | ทุก 10 | 0.35 | ease_in_out |
| `tech_product_showcase` | energetic (slide สลับซ้าย/ขวา + circle ตามรอบ) | ทุก 3 | ไม่มี | 0.3 | ease_in_out |
| `smooth_showcase` | smooth (dissolve ล้วน) | ทุก 3 | ไม่มี | 0.35 | ease_in_out |
| `premium_minimal` | minimal (fade ล้วน) | ทุก 6 | ไม่มี | 0.3 | ease_in_out |
| `flash_deal` | energetic (slide สลับซ้าย/ขวา + circle ตามรอบ) | ทุก 2 | ไม่มี | 0.24 | ease_out |
| `pain_punch` | energetic (slide สลับซ้าย/ขวา + circle ตามรอบ) | ทุก 3 | ทุก 6 | 0.24 | ease_out |
| `tech_compare` | compare (wipe ↔ slide สลับกัน) | ทุก 3 | ไม่มี | 0.3 | ease_in_out |
| `smart_hack` | energetic (slide สลับซ้าย/ขวา + circle ตามรอบ) | ทุก 4 | ไม่มี | 0.2 | ease_out |
| `niche_focus` | energetic (slide สลับซ้าย/ขวา + circle ตามรอบ) | ทุก 4 | ทุก 4 | 0.32 | ease_in_out |

**กฎต่อ family**
- **adaptive** (`clean_tech_review`): ใช้ตัวเลือกของระบบ แต่ transition แบบ stylized จะถูกลดเป็น dissolve สั้น (≤0.25 วิ) ยกเว้นรอบ stylized stride
- **energetic:** slide สลับซ้าย/ขวาตามเลขช่อง; ถ้ารอบนั้นตรงกับ circle stride = `circleopen`
- **smooth:** dissolve ทั้งหมด
- **minimal:** fade ทั้งหมด
- **compare:** วนเป็นรอบแน่นอน (ไม่ขึ้นกับตัวเลือกของระบบ): wipeleft → slideleft → wiperight → slideleft …
- **slide ตามกล้อง:** `orient_slide_to_pan` หันทิศ slide ให้ต่อเนื่องกับการแพนของคลิปขาออก (แพนขวา → เนื้อหาวิ่งซ้าย → `slideleft`)

**Easing ของ transition** (ไม่แตะฟอนต์/ขนาด/ตำแหน่ง)
- `ease_in_out`: clean_tech_review, tech_product_showcase, smooth_showcase, premium_minimal, tech_compare, niche_focus
- `ease_out`: viral_punch, flash_deal, pain_punch, smart_hack
- ตั้งเฉพาะ fade / wipe / slide เท่านั้น — ❌ ห้ามตั้งบน `fadeblack`/`fadewhite` (เรนเดอร์ช้าลง +8–13 วิ ต่อ transition ที่ 1080×1920); `dissolve`/`circleopen`/`circleclose` คง linear

---

## 5. กล้อง (push / pan) และภาพนิ่ง

กล้องของคลิปที่ pipeline สร้าง = keyframe 2 จุด (เริ่ม→จบ) ต่อช็อต โดยซูมเดิมของช็อตเป็นจุดกึ่งกลางของการเคลื่อน ทิศแพนสลับทุกช็อตที่ขยับ ช็อตที่สั้นกว่า "ความยาวขั้นต่ำ" จะไม่ขยับ (เป็นช็อตพัก) keyframe ที่ผู้ใช้ทำเองไม่ถูกแตะ

| preset | ขยับทุก | ซูมรวม (delta) | แพนสุด (±) | ช็อตสั้นสุดที่ขยับ (วิ) | easing |
|---|---|---|---|---|---|
| `viral_punch` | ทุกช็อต | 0.12 | 0.18 | 0.65 | ease_in_out |
| `clean_tech_review` | ทุก 2 ช็อต | 0.08 | 0.14 | 0.8 | ease_in_out |
| `tech_product_showcase` | ทุกช็อต | 0.06 | 0.24 | 0.9 | ease_in_out |
| `smooth_showcase` | ทุกช็อต | 0.05 | 0.08 | 1.0 | ease_in_out |
| `premium_minimal` | ทุก 3 ช็อต | 0.04 | 0.06 | 1.2 | ease_in_out |
| `flash_deal` | ทุก 2 ช็อต | 0.06 | 0.10 | 0.9 | ease_out |
| `pain_punch` | ทุกช็อต | 0.20 | 0.06 | 0.7 | ease_out |
| `tech_compare` | ทุก 2 ช็อต | 0.06 | 0.22 | 0.9 | ease_in_out |
| `smart_hack` | ทุกช็อต | 0.07 | 0.12 | 0.7 | ease_out |
| `niche_focus` | ทุก 2 ช็อต | 0.16 | 0.04 | 1.0 | ease_in_out |

- ซูมจำกัด 1.0–3.0×
- easing ที่รองรับ: `linear`, `ease_in`, `ease_out`, `ease_in_out` (default ของกล้อง = `ease_in_out`; preset แนว punch ใช้ `ease_out` ให้ซูมกระแทกแล้วชะลอ)
- **ภาพนิ่ง (รูปสินค้า):** ต้องมี Ken Burns (slow zoom 1.0 → 1.10) ห้ามแช่ภาพแข็ง; เฟรมที่ได้ต้องพอดี `ceil(ความยาว × 30)`; ขยายภาพ 4× ด้วย lanczos ก่อน; รูปแนวนอนต้องไม่ถูกยืด (pad เป็น 3:4); ไฟล์ segment `motion_seg_NNN_<hash>.mp4` (`scripts/image_motion_engine.py`)
- **เลย์เอาต์ภาพ:** สินค้ากึ่งกลาง คมชัด 100% ไม่ครอป + ขอบบน/ล่างเบลอแบบ Gaussian

---

## 6. Hook ต้นคลิป

### 6.1 ไทม์ไลน์ 2 ชั้นตั้งแต่ M1

| ช่วงเวลา | สิ่งที่ขึ้นจอ | ที่มา |
|---|---|---|
| **0.0 – 1.8 วิ** | **Hook line** ประโยคเดียวที่ AI เขียน (`hook_title`) เช่น "เบื่อไหม" | `scripts/hook_line.py` |
| **1.8 – 4.8 วิ** | **Nameplate** แบรนด์ / รุ่น / label 3 ชั้น | overlay `kind:"hook"` (ค้าง 3 วิ เป็น `HOOK_NAMEPLATE_DEFAULT_SEC`) |

- เหตุผล: 2 วินาทีแรกคือจังหวะตัดสินใจปัดคลิป ควรเจอเหตุผลให้ดูต่อ ไม่ใช่ชื่อสินค้า (เดิม nameplate ขึ้นตั้งแต่วินาทีแรกค้าง 5 วิ)
- **Hook line:** ไม่เกิน 22 ตัวอักษร (ขั้นต่ำ 4); ตัดที่ขอบคำไทย ไม่ให้จบด้วยคำค้าง (เช่น "ที่" — มีรายการคำค้างในโค้ด `_DANGLING_WORDS`) และต้องผ่าน compliance lint; กว้างสุด 860px; ไม่ย่อเล็กกว่า 70% ของ tier ใหญ่สุดของ template (ถ้าไม่พอดี = ไม่แสดง); วางที่ y ≈ 225px (ตำแหน่งเดียวกับ tier แรกของ nameplate); ใช้ฟอนต์/สีของ template เดียวกัน; เข้าแบบ `snap` 70 ms ไม่มีเฟดออก ตัดตรงเข้า nameplate
- **เงื่อนไข:** เกิดเฉพาะ "การสร้างซับครั้งแรก" ของโปรเจกต์; ถ้าผู้ใช้แก้/ลบ overlay แล้ว รอบถัดไประบบไม่แตะ; คลิปสั้นกว่า 2.8 วิ หรือไม่มีประโยคที่ผ่านเกณฑ์ = ไม่ใส่
- **Nameplate:** ถ้าไม่มีข้อความ brand/model/label ระบบเดาแบรนด์/รุ่นจากชื่อสินค้า (`guess_brand_model`) ขนาดฐานตามค่า `HOOK_FS_RATIO` (0.065) เริ่มที่ y = 180/1920 วางบนสุดกึ่งกลาง; มี scrim (แถบมืดไล่ระดับ) หลังข้อความ

### 6.2 โครงสร้าง 3 ชั้น (tier)

ทุก template มี `brand` / `model` / `label` — ตั้งได้ต่อชั้น: ขนาด (% ของฐาน), สี, สีขอบ, ความหนาขอบ, ตัวพิมพ์ใหญ่, ป้าย pill (พื้นหลังสี) · สีที่เป็น "accent" = ใช้สี accent ของ preset ณ ตอนเรนเดอร์ · ผู้ใช้สร้าง template เองได้ เก็บที่ `02_Assets/Templates/custom_hook_templates.json`

### 6.3 Template legacy 8 แบบ (default = `tech`)

| id | ฟอนต์ | brand | model | label | motion เข้า / วน / ออก |
|---|---|---|---|---|---|
| `tech` | Chakra Petch | 130% #FFFFFF ขอบ 6px UPPER | 100% accent ขอบ 6px | 58% #E0E0E0 ขอบ 6px | bounce / pulse / fade / accent=underline |
| `cute` | Itim | 118% #FFFFFF ขอบ 10px | 100% #FFFFFF ขอบ 10px | 62% #FFFFFF ขอบ 0px pill #E86BC7 | bounce_soft / wave / fade |
| `bold_pop` | Kanit | 122% #E038D8 ขอบ 14px | 110% #FFE04C ขอบ 12px | 78% #4CE0FF ขอบ 10px | pop / shake / zoom / accent=badge |
| `plain` | Prompt | 130% #FFFFFF ขอบ 0px | 82% accent ขอบ 0px | 58% #C8C8C8 ขอบ 0px | fade / none / fade |
| `clean` | Anuphan | 126% #FFFFFF ขอบ 3px UPPER | 100% #FFFFFF ขอบ 3px | 60% #D0D0D0 ขอบ 3px | slide_up / lightsweep / fade |
| `flash_sale` | Kanit | 128% #FFFFFF ขอบ 10px UPPER | 112% #FFE04C ขอบ 8px | 68% #FFFFFF ขอบ 0px pill #FE2C55 | pop / flicker / slide / accent=badge |
| `neon_cyber` | Chakra Petch | 130% #FFFFFF ขอบ 8px UPPER | 105% #25F4EE ขอบ 8px | 64% #FFE04C ขอบ 4px | pop_zoom / wave / glitch / accent=underline |
| `minimal_luxury` | Prompt | 124% #FFFFFF ขอบ 4px UPPER | 96% #E6C24A ขอบ 4px | 60% #C8C8C8 ขอบ 2px | quick_fade / lightsweep / fade / accent=underline |

### 6.4 Template T1 10 แบบ (ผูกกับ preset)

ทุกแบบฟอนต์ Kanit, ขอบ 3px, brand ตัวใหญ่สุดสี accent, model ขาว `#F7F7F7` 140%, label เทา `#D0D0D0` 80%, เข้าแบบ slide_up + stagger, ออกแบบ fade — ต่างกันที่สี brand และ animation วน

| id | ฟอนต์ | brand | model | label | motion เข้า / วน / ออก |
|---|---|---|---|---|---|
| `b1_viral_red` | Kanit | 170% #FE2C55 ขอบ 3px UPPER | 140% #F7F7F7 ขอบ 3px | 80% #D0D0D0 ขอบ 3px | slide_up / flicker / fade |
| `b2_clean_yellow` | Kanit | 170% #FFE600 ขอบ 3px UPPER | 140% #F7F7F7 ขอบ 3px | 80% #D0D0D0 ขอบ 3px | slide_up / shake / fade |
| `b2_tech_cyan` | Kanit | 170% #25F4EE ขอบ 3px UPPER | 140% #F7F7F7 ขอบ 3px | 80% #D0D0D0 ขอบ 3px | slide_up / wave / fade |
| `b1_smooth_mint` | Kanit | 170% #00F2AA ขอบ 3px UPPER | 140% #F7F7F7 ขอบ 3px | 80% #D0D0D0 ขอบ 3px | slide_up / lightsweep / fade |
| `b2_premium_gold` | Kanit | 170% #E6C24A ขอบ 3px UPPER | 140% #F7F7F7 ขอบ 3px | 80% #D0D0D0 ขอบ 3px | slide_up / wave / fade |
| `b1_deal_orange` | Kanit | 170% #FF7A00 ขอบ 3px UPPER | 140% #F7F7F7 ขอบ 3px | 80% #D0D0D0 ขอบ 3px | slide_up / flicker / fade |
| `b1_pain_pink` | Kanit | 170% #FF2E93 ขอบ 3px UPPER | 140% #F7F7F7 ขอบ 3px | 80% #D0D0D0 ขอบ 3px | slide_up / shake / fade |
| `b2_compare_blue` | Kanit | 170% #3B82F6 ขอบ 3px UPPER | 140% #F7F7F7 ขอบ 3px | 80% #D0D0D0 ขอบ 3px | slide_up / wave / fade |
| `b1_hack_lime` | Kanit | 170% #84CC16 ขอบ 3px UPPER | 140% #F7F7F7 ขอบ 3px | 80% #D0D0D0 ขอบ 3px | slide_up / lightsweep / fade |
| `b2_niche_purple` | Kanit | 170% #A855F7 ขอบ 3px UPPER | 140% #F7F7F7 ขอบ 3px | 80% #D0D0D0 ขอบ 3px | slide_up / wave / fade |

**คำศัพท์ motion ของ Hook:** เข้า = `bounce`, `bounce_soft`, `pop`, `pop_zoom`, `fade`, `quick_fade`, `slide_up` · วน = `pulse`, `wave`, `shake`, `flicker`, `lightsweep`, `none` · ออก = `fade`, `zoom`, `slide`, `glitch` · accent = `underline`, `badge`, `none` (ค่า timing เช่น bounce/pop accel 0.6, out accel 2.2, shake step 100 ms, glitch step 33 ms อยู่ใน `motion_contract.py` / `motionPresets.js` ผูกด้วยเทส)

---

## 7. ซับไตเติล

### 7.1 สเปก Golden Master (ห้าม drift — `font_text_visual_contract.md`)

| รายการ | ค่า |
|---|---|
| ฟอนต์ default ของ pipeline | IBM Plex Sans Thai SemiBold |
| ขนาด em (วิดีโอ 1080×1920, scale 1.0) | 50 px (= 1080 × 0.0463) · ASS Fontsize 82 · Mali ใช้ 106 |
| ซับอังกฤษ | 68% ของไทย สี `#EAEAEA` |
| ระยะบรรทัด | 1.0 × ASS Fontsize |
| ตำแหน่ง bottom | MarginV 420 (เรนเดอร์จริง 410 เพื่อชดเชยหมึกฟอนต์) กัน UI ของ TikTok |
| ขอบ | `max(1.8, 0.04 × fs)` ≈ 2.0 px |
| alignment | ASS 2 (ล่างกึ่งกลาง) |
| ความยาว | บรรทัดเดียว 2–4 คำ (Micro-Burst ≤ 24 ตัวอักษรต่อท่อน ราว 0.5–1.4 วิ) ❌ ห้ามขึ้น 2 บรรทัด |
| บทที่ใช้ | บทสคริปต์ทางการ 100% — ❌ ห้ามใช้ข้อความดิบจาก Whisper (Whisper ให้แค่ timing) |
| การตัดคำไทย | Syllable Clustering: พยัญชนะ+สระ+วรรณยุกต์ไม่ฉีก ❌ ห้ามวนทีละตัวอักษร |
| emoji | ถูกตัดออกจากซับ |

**ตำแหน่ง 3 แบบ** (ASS alignment, margin): bottom = (2, 410) · middle = (5, 0) · top = (8, 180) · วางเองได้ (x,y ต่อ cue)

**ฟอนต์ที่เลือกได้ 5:** Kanit · IBM Plex Sans Thai (default pipeline) · Prompt · Noto Sans Thai · Mali

**สีซับ 5 ชุด (Caption Inspector):** ขาวคลาสสิก `#FFFFFF` · เหลือง TikTok `#FFE600` · แดงเตือนภัย `#FE2C55` · ฟ้านีออน Glow `#25F4EE` · ส้มพรีเมียม `#FF7A00`

### 7.2 สองโหมดการขึ้นของซับ (เลือกได้ใน editor และในฟอร์มสร้างคลิป)

| | **ทีละคำ** (default) | **ทั้งประโยค** |
|---|---|---|
| ชื่อในโค้ด | `ghost_reveal = true` — Progressive Ghost Reveal | `ghost_reveal = false` |
| พฤติกรรม | คำข้างหน้าโปร่งใส (จองที่ไว้ ไม่ให้บรรทัดกระโดด) · คำที่กำลังพูด = สีเน้น + ขยาย 114% · คำที่พูดแล้ว = ขาว | ทั้งท่อนขึ้นพร้อมกัน (fade เข้า 70 ms) |
| ไฮไลต์ keyword | ไม่ใช้ (Ghost Reveal แทน) — แต่ดู 7.4 | ใช้: เหลือง `#FFE600` (ปัญหา/ราคา/ตัวเลข) · ฟ้า `#00E5FF` (จุดเด่น/สเปก/คำจากชื่อสินค้า) · แดง `#FF3B30` (คำเตือน) |
| หลังพูดจบทั้งท่อน | คงข้อความขาวเต็มบรรทัดค้างไว้ (settle 0.2 วิ) จนจบ cue | — |
| คำสั้นสุดที่ได้เวลา | 0.06 วิ (`MIN_WORD_DUR`) | — |

**ขอบเขต:** ทั้งสองค่าเป็น "ระดับทั้งโปรเจกต์" — กดครั้งเดียวมีผลทุกท่อน (ไม่ใช่รายกล่อง) · การเปลี่ยนมีผลกับคลิป export ตอนเรนเดอร์ใหม่ · Preview เด้งทีละคำได้เฉพาะ cue ที่มีข้อมูลเวลารายคำ (`word_reveal`) — โปรเจกต์ที่สร้างก่อนฟีเจอร์นี้ไม่มี ต้องสร้างซับใหม่

### 7.3 สีของคำที่กำลังพูด: ตาม Hook (default เปิด)

- เปิด "สีซับตาม Hook" (`reveal_color_sync`, default true) → สีของคำที่กำลังพูดคือ **สีสดตัวแรกของ Hook overlay** (ไล่ brand → model → label; ถือว่า "สีสด" เมื่อ saturation ≥ 0.35 และ value ≥ 0.40) ผู้ใช้แก้สี Hook ใน editor ซับเปลี่ยนตาม
- สีที่มืดเกิน (luminance < 0.15) ถูกยกเข้าหาขาว 30% ให้อ่านออก
- Hook ไม่มีสีสด (ขาว/เทาล้วน) หรือปิดซิงก์ → ใช้เขียวนีออน `#66FF00` (ค่า SOP เดิม) · คำที่พูดแล้ว = `#FFFFFF` เสมอ
- ตัวอย่าง: viral_punch → แดง `#FE2C55` · clean_tech_review → เหลือง `#FFE600` · pain_punch → ชมพู `#FF2E93`
- กติกาเลือกสีเขียนไว้ 2 ที่ให้ตรงกัน: `scripts/subtitle/reveal_color.py` (render) กับ `frontend/src/lib/revealColor.js` (preview) ล็อกด้วย `tests/fixtures/reveal_color_parity_cases.json`
- ⚠ `#66FF00` เป็นค่าใน `AGENTS.md` ข้อ 17 (D2) — เปลี่ยน default เป็น "ตาม Hook" แล้วโดยผู้ใช้ยืนยัน 2026-11-10

### 7.4 keyword ไทย/อังกฤษ ตามสี Hook (โหมดทีละคำ + เปิดซิงก์)

เมื่อเปิดซิงก์ในโหมดทีละคำ keyword ที่ถูกไฮไลต์ทั้งบรรทัดไทยและบรรทัดอังกฤษ (ซ้อนใต้) จะใช้สี Hook เดียวกันหมด แทนสีประเภทคำ (เหลือง/ฟ้า/แดง) — เพื่อไม่ให้มีสีฟ้า/เหลืองตกค้างชนกับสี reveal · โหมดทั้งประโยค หรือปิดซิงก์ = สีตามประเภทคำเหมือนเดิม · คำ keyword ของโปรเจกต์มาจากคำใน brand/model/label ของ Hook (ยาว ≥ 3 ตัวอักษร) + พจนานุกรมคำไทย/อังกฤษของระบบ

### 7.5 ซับอังกฤษซ้อนใต้ (ซับสองภาษา)

เปิด/ปิดได้ (default เปิด; ปิดแล้วคำแปลไม่ถูกลบ แค่ไม่แสดง) · ขนาด 68% ของไทย สี `#EAEAEA` · คำแปลที่เป็นหน้า error ถูกทิ้งไม่ฝังลงซับ · ชื่อแบรนด์/รุ่น/ศัพท์เทคนิคคงเป็นอังกฤษ ❌ ห้ามทับศัพท์เป็นไทย

---

## 8. Overlay อื่นๆ

| รายการ | สเปก | หมายเหตุ |
|---|---|---|
| **Product callout** | ชั้นเดียว (ปิด auto ตอนนี้) | ที่ pipeline ใช้จริง |
| **SpecBar** (`on_screen` ของ cue) | กล่องสีเหลือง `#FFE600` ตัวอักษรดำ ชิดขวา (MarginR 140, MarginV 380) | ขอบกล่อง ≤ x 950 กัน UI ขวา |
| **Callout 2 ชั้น** (Prompt-Bold 76px ขาว MarginV 250 + Prompt-Black 94px `#FF6622` MarginV 530) | — | **legacy ของ tools one-off — ยังไม่มีใน pipeline** (D3) ❌ ห้ามมีเส้นขีดเขียว |
| **ลายน้ำ** | ข้อความแดงจาง ~37% opaque ขวาตอนล่าง (x 94.5%, y 72%) ขนาด 3.8% | เปิด/ปิดได้ใน editor; ข้อความมาจากช่อง |
| **Source Attribution** | MarginV 36 ระบุแหล่งที่มาจริงเท่านั้น | ❌ ห้ามใส่โลโก้/ป้ายปลอม (เช่น TECH MX) |
| **สติกเกอร์** | Universal Badges 6 แบบ พื้นขาว + ขอบ die-cut | เข้า: fade-in 7 เฟรม (0.233 วิ) + scale 0.88→1.0 ease_out · ออก: fade-out 6 เฟรม (0.2 วิ) · ❌ ห้ามสติกเกอร์ระบุข้อความเฉพาะสินค้า |
| **Safe zone** | ห้ามข้อความ/สติกเกอร์ชิดขอบขวา-ล่าง กันปุ่ม TikTok | ซับล่าง 420px, Hook บน 180px |

---

## 9. เสียง

### 9.1 มิกซ์ (`scripts/config.py` ค่าเดียวทุก path)

| ช่อง | ค่า |
|---|---|
| เสียงพากย์ (Voice) | 1.0 |
| SFX | 0.28 (≈ −11 dB — ได้ยินแต่ไม่ตกใจ) |
| BGM | 0.12 (≈ −18 dB — เป็นฐานใต้เสียงพากย์) |
| BGM มาตรฐาน | `02_Assets/Music/tiktok_upbeat_bgm.wav` เพลงไอทีสนุก คึกคัก ❌ ห้าม Lo-Fi ชวนง่วง; ท้ายคลิป fade out นุ่ม |
| อัตราพูด default | `+15%` (TikTok fast-paced) |

มี ducking ของ BGM ใต้เสียงพากย์ และ 4-bus mixing (voice / sfx / bgm / master) ตามเทส `test_audio_bus_levels.py` — รายละเอียดคอนฟิก ducking ไม่ได้ตรวจในเอกสารนี้

### 9.2 เสียงพากย์ AI (Gemini Flash TTS)

default = `gemini_fenrir_male_strong` (Fenrir)

| preset | เสียง | เพศ | คำอธิบาย |
|---|---|---|---|
| `gemini_puck_male_hype` | Puck | male | Puck — ชายพลังสูง TikTok |
| `gemini_charon_male_pro` | Charon | male | Charon — ชายทุ้มลึก น่าเชื่อถือ |
| `gemini_kore_female_bright` | Kore | female | Kore — หญิงสดใส ป้ายยาเก่ง |
| `gemini_aoede_female_pro` | Aoede | female | Aoede — หญิงพรีเมียม นุ่มนวล |
| `gemini_fenrir_male_strong` | Fenrir | male | Fenrir — ชายสตรอง คมเข้ม |

### 9.3 น้ำเสียงโฆษณา (ad tone)

default = `commercial_premium` · มีผลกับการเขียนบทและสไตล์การพูด; ถ้าไม่ได้ระบุ `style` ระบบอาจเลือก Hook template จาก ad tone ได้ (ลำดับ: template ที่ระบุ → จาก style preset → จาก ad tone → `tech`)

| id | ความหมาย |
|---|---|
| `commercial_premium` | โฆษณาพรีเมียม |
| `commercial_hype` | ป้ายยาไวรัล |
| `commercial_aesthetic` | มินิมอล ดูแพง |
| `commercial_expert` | ผู้เชี่ยวชาญ |

---

## 10. โครงเรื่องและความยาว (ฟอร์มสร้างคลิป)

**รูปแบบการเล่า (`story_format`)**

| id | ชื่อ | โครง |
|---|---|---|
| `classic` (default) | คลาสสิก | Hook → จุดเด่น → CTA ตามสูตรเดิม |
| `countdown` | นับถอยหลัง 3 เหตุผล | ข้อ 3 → 2 → 1 เก็บข้อเด็ดไว้ท้าย |
| `problem_reveal` | ปัญหา → ทางแก้ | เปิดด้วยปัญหา แล้วเฉลยตัวช่วย |
| `myth_buster` | เข้าใจผิดมาตลอด | แก้ความเชื่อผิดด้วยสเปกจริง |
| `loop` | วนต่อเนื่อง | ประโยคท้ายต่อกลับประโยคแรก |

**ความยาวเป้าหมาย (`target_duration`):** อัตโนมัติ (ยาวตามบท, default) · 15 วิ (สั้นมาก) · 25 วิ (กระชับ) · 35 วิ (มาตรฐาน) · 45 วิ (เล่าครบ)

---

## 11. ปก (Cover)

### 11.1 เลือกเฟรมปกอัตโนมัติ (ใหม่ 2026-11-10)

- **ปกแนะนำ = เฟรมที่คมที่สุดในช่วงที่ nameplate ขึ้นจริง** (ให้เห็นแบรนด์/รุ่น/สินค้าพร้อมกัน) — `scripts/cover_frame_picker.py`
- ช่วงเวลาอ่านจาก overlay Hook ของโปรเจกต์ (หาโปรเจกต์จาก `artifacts.mp4_video` ตรงตัว): หน้าต่าง = [เริ่ม + 0.6 วิ, จบ − 0.3 วิ] โปรเจกต์เก่าที่ nameplate 0–5 วิ ได้ 0.6–4.7 วิ; โปรเจกต์ใหม่ (nameplate 1.8–4.8) ได้ 2.4–4.5 วิ
- คะแนน = ความคม (Laplacian variance) ของ "แถบกลางเฟรม" (x 8–92%, y 28–68% — ตัดแถบ Hook ด้านบนกับซับด้านล่างออก); เฟรมที่ติดรอยต่อ (เฟรมข้างๆ ต่างกันมาก) ลดเหลือ 30%; ถอดรหัสครั้งเดียว 8 fps (~0.65 วิ/คลิป)
- ใช้กับ: ตัวเลือกแรกของ `/covers/highlights` (ป้าย "ปกแนะนำ (Hook + สินค้า)"), `GET /covers/recommended-frame`, ค่า default ของ `at_seconds` ใน `/covers/generate` และ `/covers/render-pro`, และสไลเดอร์ใน Export Gallery (ถ้ายังไม่ได้ลาก)
- mp4 ที่ export ฝัง nameplate ไว้แล้ว → ถ้าเฟรมอยู่ในช่วง nameplate ระบบ **ไม่ประทับ brand/model/label ซ้ำ**
- **ข้อจำกัด:** ใช้ความคมของภาพล้วน ไม่ได้ตรวจว่า "เห็นสินค้าจริง" (ข้อมูล shot ใน manifest ไม่บอก); ปก render-pro ยังใช้ประโยค Hook (`hook_text`) ไม่ใช่แบรนด์/รุ่น; เฟรมจาก export มีซับและลายน้ำติดมา (ใช้ raw footage ใน Cover Studio ถ้าต้องการเฟรมสะอาด)

### 11.2 Cover Studio

- ขนาด 9:16 (1080×1920) และ 3:4 (1080×1440) · ปกที่คิวโพสต์ใช้คือ `_cover_3x4.jpg` (ปก 9:16 จะถูก TikTok ครอป)
- เทมเพลตข้อความ: `neon` · `yellow_bar` · `modern_box` · `minimal_bold` · ตำแหน่ง hook บน/กลาง/ล่าง · badge 3D มุมซ้าย/ขวาบน · pan/zoom 1.0–3.0×
- ภาพพื้น: เฟรมจากวิดีโอ, raw footage ไร้ซับ, หรือภาพที่อัปโหลด

### 11.3 มาตรฐานภาพปก / ฉาก CTA (Style 3B Golden Formula — `AGENTS.md` ข้อ 23)

- ❌ ห้ามอีโมจิ (Zero-Emoji) · ❌ ห้ามลูกศรแดงพาดสินค้า (Zero-Arrow)
- โครง 3 ชั้น: Top Hook 20% · Hero Stage + Contact Shadow 55% · Spec Badges + Options 25%
- ปรับตามกลุ่มสินค้า: **หลากสี** = สูตร 3B (พัดลม: Trio Hero + การ์ดสวอชสี 6 สี / สายชาร์จ: Quad Heads Lineup) · **ชิ้นเดียวขนาดเล็ก** = Macro Hero 730–780px + Contact Shadow 560–640px + 4 Floating Badges · **เซ็ต** = Hero กลาง + Knolling อุปกรณ์เสริม

---

## 12. สไตล์พิเศษอื่นๆ และกฎ compliance

### 12.1 คลิปละครสั้นคู่รักสายใต้ (สรุปจาก `AGENTS.md` ข้อ 20 — ยังไม่ได้อ่านโค้ด)

- สกิล `/couple` หรือ `/couple-paper-chat` · ตัวละคร น้องนุ้ย (หญิง, อวตารชมพู "น", กล่องแชทขาว `#ffffff`, เสียง Aoede) และ พี่บ่าว (ชาย, อวตารฟ้า "บ", กล่องแชทเขียว LINE `#8de07a`, เสียง Puck)
- คุมโทนเสียงคงที่ทั้งคลิป (ห้ามเปลี่ยนเป็นสุขุม/ทางการแม้ตอนอ่านสเปก)
- กรณีไม่มีคลิปดิบ: พื้นกระดาษยับ ความเร็วครึ่งเดียว, ยิง TTS 2 รอบต่อคลิป, ตัดเทิร์นตามช่วงเงียบ, ตรวจด้วย faster-whisper, เปิด Studio Preview ตรวจก่อนเรนเดอร์
- กรณีมีฟุตเทจ: กล่องแชท LINE ซ้อนล่างบนฟุตเทจจริง

### 12.2 กฎ compliance ที่บังคับกับข้อความในคลิป (`scripts/compliance_lint.py`)

`NO_PRICE` (ห้ามราคา/ส่วนลด/เดาราคา — ผิดกฎ TikTok) · `NO_EXAGGERATED_CLAIM` · `NO_FILLER_OPENER` · `NO_CTA_FIRST_LINE` · `NO_ELLIPSIS` (ห้าม "..." / "…" ในบทพูด) · `NO_EMOJI` · โครงสร้าง: ต้องมี open loop, ห้ามจบแบบ filler, ต้องมีคำถามชวนคอมเมนต์, ความยาวต้องใกล้เป้า

---

## 13. ความขัดแย้งของเอกสารเก่า / ช่องว่างที่ยังไม่ปิด

**เอกสารที่ล้าสมัย (ถือ `AGENTS.md` ข้อ 17 + `font_text_visual_contract.md` + โค้ดเป็นหลัก)**
- `gadget_editing_style_checklist.md` แถว Pre-Flight ข้อ 1 (Mali-Bold 88px / MarginV 380), ข้อ 4 (สีเขียว `#66FF00` ล้วน), ข้อ 6 (Callout 2 ชั้น) — ส่วนหัวของไฟล์เองระบุว่าค่าเหล่านี้เป็นของ tools one-off ไม่ใช่สเปก pipeline
- `subtitle_kinetic_rules.md` ยังระบุฟอนต์ 78–84px, ขอบ 5.5px, Pop 125%→100% และไฮไลต์ keyword 3 สี เป็นสเปกหลัก — ปัจจุบันไฮไลต์ keyword ใช้เฉพาะโหมด "ทั้งประโยค" หรือเมื่อปิดซิงก์
- `AGENTS.md` ข้อ 3 (ไฮไลต์ `#FFE600`) ขัดกับข้อ 17 (Ghost Reveal แทนไฮไลต์) — ข้อ 17 ใหม่กว่า

**ช่องว่าง**
- ฟอร์มสร้างคลิปเลือกโหมดซับ/สีตาม Hook ได้แล้ว แต่ **ยังไม่มี UI เลือก Hook template, สี Hook หรือ animation T1 ในฟอร์ม** (ตั้งผ่าน preset หรือแก้ใน editor)
- โปรเจกต์เก่าที่ไม่มี `word_reveal` ไม่เด้งทีละคำใน Preview
- Hook line (ประโยค AI) ยังไม่มีสวิตช์ปิดใน UI — ใส่อัตโนมัติรอบแรก
- ปกยังไม่มีการเลือก "เห็นสินค้า" ด้วยวิธีตรวจจับวัตถุ/Vision
- ยังไม่ได้ทดสอบทั้งชุด pytest (~4,200 ข้อ) จนจบ

---

## 14. แผนที่ไฟล์โค้ด

| เรื่อง | ไฟล์ |
|---|---|
| นโยบาย motion ของ preset (ตัด/transition/กล้อง/สี) | `scripts/style_motion_policy.py` |
| แคตตาล็อก preset ฝั่ง UI + angle→preset | `frontend/src/lib/stylePresetCatalog.js` |
| Hook template (legacy + T1) | `scripts/hook_styles.py` · `frontend/src/lib/hookStyles.js` |
| Hook line / nameplate | `scripts/hook_line.py` · `scripts/overlay_model.py` |
| ซับ: engine ASS | `scripts/subtitle_engine.py` · `scripts/subtitle/` |
| Ghost Reveal | `scripts/subtitle/ghost_reveal_ass.py` · `scripts/subtitle/word_reveal.py` |
| สีตาม Hook | `scripts/subtitle/reveal_color.py` · `frontend/src/lib/revealColor.js` |
| ซับ: preview | `frontend/src/components/SequencePlayer.jsx` |
| ซับ: ปุ่มตั้งค่า | `frontend/src/components/editor/inspector/CaptionInspector.jsx` · `frontend/src/components/editor/NewClipPanel.jsx` |
| ปก | `scripts/api_covers.py` · `scripts/cover_frame_picker.py` · `frontend/src/components/CoverStudioModal.jsx` · `ExportGallery.jsx` |
| เสียง/ค่าคงที่ | `scripts/config.py` · `scripts/generate_voice_cache.py` |
| compliance | `scripts/compliance_lint.py` |
| กฎ/SOP | `AGENTS.md` · `.agents/rules/font_text_visual_contract.md` · `.agents/rules/gadget_editing_style_checklist.md` · `_Docs/GADGET_VIDEO_PRODUCTION_SOP.md` |
