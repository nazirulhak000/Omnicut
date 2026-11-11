# แผนเพิ่ม Style Preset ไวรัล 5 แบบ (10 → 15)

วันที่ 2026-11-11 · ดำเนินการโดย: Claude Code (Claude Fable 5.2) · สถานะ: **แผนเท่านั้น ยังไม่แตะโค้ด รอเจ้าของโปรเจกต์อนุมัติ**

เอกสารอ้างอิงสไตล์เดิม: [EDITING_STYLES_REFERENCE_20261111.md](../Reports/EDITING_STYLES_REFERENCE_20261111.md)

---

## 0. สรุปสั้น

- เสนอ preset ใหม่ 5 แบบ: `raw_ugc`, `beat_drop`, `swipe_stack`, `proof_test`, `glow_up`
- ทุกแบบใช้ **transition ที่ renderer และ preview วาดได้อยู่แล้ว** (`fadewhite`, `fadeblack`, `slideup`, `wipeup`, `wipedown`, `circleopen`) จึงไม่ต้องแก้ `video_editor.py` หรือ `SequencePlayer.jsx` งานโค้ดหลักคือเพิ่ม 4 กิ่งใน `apply_transition_budget`
- ตรวจด้วยตัววัดของ `tests/test_style_distinctness.py` แล้ว (รันจริงกับโค้ดปัจจุบัน): 15 preset = 105 คู่ ไม่มีคู่ไหนต่ำกว่า 0.90 คู่ที่ใกล้สุดของสไตล์ใหม่คือ `glow_up`/`niche_focus` = 1.040 ลายนิ้วมือ transition ไม่ซ้ำทั้ง 15 แบบ และเงื่อนไข "ที่สุด" ของ 10 ตัวเดิมยังจริงทุกข้อ
- 10 preset เดิมและ Golden Master ไม่ถูกแก้ค่าใดเลย สไตล์ใหม่เป็นตัวเลือกที่ผู้ใช้ต้องเลือกเอง ไม่ถูกผูกกับ angle อัตโนมัติ
- Jev (`choice`): เลือกแนวทาง "เพิ่มตระกูล transition เล็ก ๆ จาก type ที่ renderer รองรับแล้ว" conf 0.96 (เทียบกับ "ใช้ 5 ตระกูลเดิม" และ "สร้างเอฟเฟกต์ renderer ใหม่")

**ข้อจำกัดของหลักฐาน:** เหตุผลเชิงจิตวิทยาและเทรนด์ในเอกสารนี้เป็น**สมมติฐานการออกแบบ** จากรูปแบบคลิปที่พบทั่วไปบนแพลตฟอร์ม ไม่ได้มาจากข้อมูล watch-time ของช่องนี้ และไม่ได้ค้นข้อมูลเทรนด์สดจากเว็บ ต้องวัดผลจริงหลังปล่อย (หัวข้อ 9)

---

## 1. ช่องว่างที่ 10 สไตล์เดิมยังไม่ครอบคลุม

| ช่องว่าง | 10 ตัวเดิมที่ใกล้สุด | ทำไมยังไม่ใช่ |
|---|---|---|
| คลิปที่ดูเหมือนคนใช้จริงถ่ายเอง ไม่เหมือนโฆษณา | `smart_hack` | ยังมี slide และจังหวะเป็นระเบียบแบบงานตัดต่อ |
| ตัดตามบีทเพลง มีแฟลชขาว | `viral_punch` | ใช้ slide/circle ไม่มีแฟลช และ beat snap 0.12 |
| ลิสต์/นับถอยหลัง เลื่อนขึ้นเหมือนฟีด | `flash_deal` | slide ซ้าย-ขวา ไม่มีทิศแนวตั้ง |
| ทดสอบพิสูจน์ ลุ้นผล | `niche_focus` | ไม่มีจังหวะ "ตัดดำก่อนเฉลย" และกล้องไม่คืบช้าต่อเนื่อง |
| ก่อน-หลัง / เปลี่ยนโฉม | `tech_compare` | เทียบ A/B ซ้าย-ขวาสลับ ไม่ใช่เปิดม่านเผยผลลัพธ์ |

**แนวที่พิจารณาแล้วไม่เสนอ**

- ตัดถี่ระดับต่ำกว่า 1 วินาที (velocity edit): ขัดกับพื้น `min_shot` 1.5 วิ และ `hook_max_shot` ≥ 0.9 วิ ที่เทสกำหนดช่วงไว้ ต้องเปลี่ยนกฎก่อน
- ASMR ไม่มีเสียงพากย์: pipeline ผูกกับเสียงพากย์และมิกซ์ค่าเดียว (Voice 1.0 / SFX 0.28 / BGM 0.12) ต้องเป็นงานแยก
- สไตล์นับถอยหลังราคา/ส่วนลด: ห้ามแสดงราคาในคลิป TikTok

---

## 2. ตารางเทียบ 5 สไตล์ใหม่ (ค่าที่จะลงโค้ด)

หน่วยวินาที · เฟรมที่ 30 FPS ในวงเล็บ

| ฟิลด์ | `raw_ugc` | `beat_drop` | `swipe_stack` | `proof_test` | `glow_up` |
|---|---|---|---|---|---|
| ชื่อไทย | รีวิวดิบแบบคนใช้จริง | ตัดตามบีท แฟลชขาว | ลิสต์เลื่อนฟีด | พิสูจน์ให้ดู ลุ้นผล | ก่อน-หลัง เปิดม่าน |
| `transition_family` (ใหม่) | `hardcut` | `flash` | `vertical` | `chapter` | `reveal` |
| `min_shot` | 1.5 (45f) | 1.5 (45f) | 1.6 (48f) | 1.9 (57f) | 1.7 (51f) |
| `max_shot` | 2.3 (69f) | 2.1 (63f) | 2.2 (66f) | 3.0 (90f) | 2.7 (81f) |
| `hook_max_shot` | 1.0 | 1.0 | 1.1 | 1.1 | 1.2 |
| `max_static_sec` | 2.0 | 1.8 | 2.2 | 3.3 | 2.7 |
| `j_lead` | 0.17 | 0.17 | 0.18 | 0.22 | 0.20 |
| `beat_snap_tolerance` | 0.08 | 0.16 | 0.13 | 0.08 | 0.12 |
| `transition_stride` | 1 (ไม่มีผล) | 2 | 2 | 5 | 4 |
| `stylized_stride` | 0 | 0 | 6 | 0 | 8 |
| transition ที่เห็น | hard cut ล้วน | `fadewhite` ทุก 2 รอยต่อ | `slideup` ทุก 2 · `wipeup` ทุก 6 | `fadeblack` ทุก 5 | `wipedown` ทุก 4 · `circleopen` ทุก 8 |
| `max_transition_duration` | 0.15 | 0.18 | 0.22 | 0.40 | 0.36 |
| `transition_easing` | – | – (แฟลชไม่ ease) | `ease_out` | – (ไม่ ease) | `ease_in_out` |
| `camera_motion_stride` | 1 | 1 | 3 | 1 | 1 |
| `camera_zoom_delta` | 0.10 | 0.16 | 0.05 | 0.12 | 0.10 |
| `camera_pan_extent` (±) | 0.05 | 0.10 | 0.04 | 0.04 | 0.12 |
| `camera_min_duration` | 0.5 | 0.6 | 1.1 | 1.4 | 1.0 |
| `camera_easing` | `ease_out` | `ease_in` | `ease_out` | `linear` | `ease_in_out` |
| `accent_color` | `#FFB38A` | `#E845FF` | `#22E55E` | `#38BDF8` | `#7C7BFF` |
| `status_color` | `#25F4EE` | `#FFE600` | `#25F4EE` | `#FFE600` | `#25F4EE` |
| preset เดิมที่ใกล้สุด (ระยะ) | `flash_deal` 1.043 | `smart_hack` 1.132 | `flash_deal` 1.095 | `smooth_showcase` 1.181 | `niche_focus` 1.040 |

ทุกค่าอยู่ในช่วง `SPAN` ของเทส และ `beat_snap_tolerance ≤ j_lead` ทุกตัว (จุดตัดไม่ล้ำหน้าเสียงพากย์)

ลายนิ้วมือ 12 รอยต่อแรก:

```
raw_ugc      cut cut cut cut cut cut cut cut cut cut cut cut
beat_drop    cut FW  cut FW  cut FW  cut FW  cut FW  cut FW        (FW = fadewhite)
swipe_stack  cut SU  cut SU  cut WU  cut SU  cut SU  cut WU        (SU = slideup, WU = wipeup)
proof_test   cut cut cut cut FB  cut cut cut cut FB  cut cut       (FB = fadeblack)
glow_up      cut cut cut WD  cut cut cut CO  cut cut cut WD        (WD = wipedown, CO = circleopen)
```

`camera_easing` แบบ `linear` และ `ease_in` มีอยู่ใน `CAMERA_EASING_NAMES` แล้ว แต่ยังไม่มี preset เดิมตัวไหนใช้ จึงเป็นคันโยกความต่างที่ได้มาฟรี

---

## 3. รายละเอียดรายสไตล์

หมายเหตุร่วมทุกสไตล์

- **Hook template:** ใช้โครง T1 เดิมทุกประการ (Kanit, brand 170% UPPER สี accent, model 140% `#F7F7F7`, label 80% `#D0D0D0`, ขอบ 3px) ต่างเฉพาะสี brand และ motion เพื่อไม่แตะ font contract คำ motion ทุกคำมีใน `motion_contract.py` แล้ว
- **ซับ Ghost Reveal:** เมื่อเปิด "สีซับตาม Hook" คำที่กำลังพูดใช้สี accent ของสไตล์ (ทั้ง 5 สีผ่านเกณฑ์สีสดของ `reveal_color.py`: saturation ≥ 0.35, value ≥ 0.40, luminance ≥ 0.15) ขยาย 114% คำที่พูดแล้วขาว `#FFFFFF` ปิดซิงก์ = เขียว `#66FF00` สเปกฟอนต์/ตำแหน่งไม่เปลี่ยน
- **เสียง:** ค่ามาตรฐานของโปรเจกต์ยังเป็น Fenrir + `commercial_premium` + อัตราพูด `+15%` และมิกซ์ Voice 1.0 / SFX 0.28 / BGM 0.12 ค่าเดียวทุก path เสียง/โทนในแต่ละสไตล์ด้านล่างเป็น**ค่าแนะนำ** ไม่ผูกอัตโนมัติ (ดูข้อตัดสินใจ D2) ระดับ BGM ไม่เสนอให้ต่างจาก 0.12

### 3.1 `raw_ugc` — รีวิวดิบแบบคนใช้จริง

**1) แนวคิดและจิตวิทยา** คลิปที่ดูเหมือนเพื่อนเล่าให้ฟัง ไม่ใช่โฆษณา คนดูไม่ตั้งการ์ดตั้งแต่เฟรมแรกจึงไม่ปัดเพราะ "นี่โฆษณา" การตัดแบบ jump cut พร้อม punch-in เล็ก ๆ ทุกช็อตทำให้ภาพเปลี่ยนทุก 1.5–2.3 วิ โดยไม่มี transition ให้รู้สึกว่าถูกตัดต่อ ผลที่คาดต่ออัลกอริทึม: อัตราดูเกิน 3 วิ และดูจบดีขึ้นในกลุ่มที่เบื่อคลิปขายของ เหมาะกับ: ของใช้ประจำวันราคาเข้าถึงง่าย (สายชาร์จ, power bank, ที่วางมือถือ), มุม "ใช้มา 1 เดือน", `longterm_review`, `dont_cheap_out`

**2) จังหวะตัด** 1.5–2.3 วิ · ช่วง Hook ≤ 1.0 วิ · ภาพนิ่งได้ไม่เกิน 2.0 วิ · J-lead 0.17 (สั้นสุดที่ยังอยู่ในหน้าต่าง 150–250 ms) · beat snap 0.08 (แทบไม่ตามเพลง จุดตัดตามคำพูด)

**3) Transition** ตระกูลใหม่ `hardcut`: ทุกรอยต่อเป็น hard cut 100% ไม่มี easing ค่า `max_transition_duration` 0.15 ใส่ไว้ให้อยู่ในช่วงของเทสเท่านั้น

**4) กล้อง** ขยับทุกช็อต · zoom 0.10 · pan ±0.05 · ช็อตสั้นกว่า 0.5 วิ อยู่นิ่ง (ในทางปฏิบัติคือขยับทุกช็อต) · `ease_out` ให้ punch-in เข้าเร็วแล้วหยุด เหมือนคนซูมด้วยมือ

**5) ภาพและ Hook** accent พีช `#FFB38A` / status `#25F4EE` · template `t2_ugc_peach` · motion เข้า `quick_fade` / วน `none` / ออก `fade` / `stagger: False` (ขึ้นพร้อมกันทั้ง 3 ชั้น ไม่ดูออกแบบ) · ซับ: คำที่พูดสีพีช

**6) เสียง** แนะนำ Puck (`gemini_puck_male_hype`) หรือ Kore (`gemini_kore_female_bright`) โทน `commercial_hype` พูดเหมือนเล่า · BGM เบาแบบ `bgm_aesthetic_pop.wav` · SFX น้อยที่สุด: `sfx_pop_bubble.wav` ที่ punch-in ของประโยค Hook และ `sfx_mouse_click.wav`/`sfx_keyboard_tap.wav` ตอนสาธิตการใช้ ไม่ใส่ whoosh

### 3.2 `beat_drop` — ตัดตามบีท แฟลชขาว

**1) แนวคิดและจิตวิทยา** ภาพกับเสียงตรงจังหวะกันทำให้สมองคาดเดาบีทถัดไปและรอดู แฟลชขาวสั้น ๆ บนบีทเป็นรางวัลของการรอ กล้องเร่งเข้าหาจุดตัด (`ease_in`) ทำให้ทุกช็อตมีแรงส่งไปช็อตถัดไป ผลที่คาด: ดูซ้ำ (loop) และดูจบสูงในคลิปสั้น 15–25 วิ เหมาะกับ: แกดเจ็ตที่หน้าตาเด่น/มีไฟ RGB (คีย์บอร์ด, เมาส์เกมมิ่ง, หูฟัง, ลำโพง), มุม `stop_scroll`

**2) จังหวะตัด** 1.5–2.1 วิ · Hook ≤ 1.0 วิ · ภาพนิ่ง ≤ 1.8 วิ (ต่ำสุดที่เทสอนุญาต) · J-lead 0.17 · beat snap 0.16 (แรงสุดในแคตตาล็อก และยังไม่เกิน J-lead)

**3) Transition** ตระกูลใหม่ `flash`: `fadewhite` ทุก 2 รอยต่อ ที่เหลือ hard cut · ยาวสุด 0.18 วิ · ไม่ ease (นโยบายเดิมไม่ ease `fadewhite` เพราะเรนเดอร์ช้าขึ้น 8–13 วิ ต่อรอยต่อ) · ความถี่แฟลชประมาณ 1 ครั้งต่อ 3–4 วิ ต่ำกว่าเกณฑ์เสี่ยงภาพกะพริบ (3 ครั้งต่อวินาที) มาก

**4) กล้อง** ทุกช็อต · zoom 0.16 (รองจาก `pain_punch` 0.20) · pan ±0.10 · ขั้นต่ำ 0.6 วิ · `ease_in` (เริ่มช้าแล้วเร่งจนถึงจุดตัด)

**5) ภาพและ Hook** accent ม่วงแดงนีออน `#E845FF` / status `#FFE600` · template `t2_beat_magenta` · เข้า `pop_zoom` / วน `pulse` / ออก `glitch` · ซับ: คำที่พูดสีม่วงแดง

**6) เสียง** แนะนำ Puck โทน `commercial_hype` · BGM บีทชัดแบบ `bgm_cyber_phonk.wav` หรือ `bgm_dj_quads_punch.mp3` (ต้องมีบีทให้ beat snap จับ) · SFX: `boom.wav` คู่กับแฟลชแรกหลัง Hook เท่านั้น แฟลชถัดไปปล่อยให้บีทเพลงทำงาน ไม่ใส่ SFX ทุกแฟลช (จะกลบเสียงพากย์)

### 3.3 `swipe_stack` — ลิสต์เลื่อนฟีด

**1) แนวคิดและจิตวิทยา** คลิปแบบ "3 เหตุผล" / "5 ข้อที่ต้องรู้" สร้างช่องว่างที่คนอยากปิด: เมื่อเห็นข้อ 1 จะอยากรู้ข้อสุดท้าย การเลื่อนขึ้นทุกครั้งที่เปลี่ยนข้อเลียนแบบท่าปัดฟีด ทำให้คนดูได้ความรู้สึก "ปัดแล้ว" โดยไม่ต้องออกจากคลิป กล้องนิ่งเกือบตลอดเพื่อให้อ่านหัวข้อทัน ผลที่คาด: ดูจบสูงและถูกบันทึก (save) เหมาะกับ: สินค้าที่มีจุดขายหลายข้อ, มุม `spec_explained`, `how_to_setup`, คลิป "ข้อควรรู้ก่อนซื้อ"

**2) จังหวะตัด** 1.6–2.2 วิ (ช่วงแคบ จังหวะสม่ำเสมอเหมือนนับข้อ) · Hook ≤ 1.1 วิ · ภาพนิ่ง ≤ 2.2 วิ · J-lead 0.18 · beat snap 0.13

**3) Transition** ตระกูลใหม่ `vertical`: `slideup` ทุก 2 รอยต่อ · ทุกรอยต่อที่ 6 เป็น `wipeup` (ขึ้นหัวข้อใหม่) · ยาวสุด 0.22 วิ · `ease_out` · ค่าเรนเดอร์: slide แบบ ease เพิ่มประมาณ 0.9 วิ ต่อรอยต่อ (ตัวเลขจากคอมเมนต์ในโค้ด) คลิป 60 วิ มีประมาณ 12–15 รอยต่อที่เป็น slide

**4) กล้อง** ขยับทุก 3 ช็อต (เท่า `premium_minimal`) · zoom 0.05 · pan ±0.04 · ขั้นต่ำ 1.1 วิ · `ease_out` — การเคลื่อนไหวหลักมาจากการเลื่อน ไม่ใช่กล้อง

**5) ภาพและ Hook** accent เขียว `#22E55E` / status `#25F4EE` · template `t2_swipe_green` · เข้า `slide_up` / วน `none` / ออก `slide` (เข้า-ออกทิศเดียวกับ transition) · ซับ: คำที่พูดสีเขียว

**6) เสียง** แนะนำ Fenrir (ค่ามาตรฐาน) โทน `commercial_expert` นับข้อชัดเจน · BGM `tiktok_upbeat_bgm.wav` · SFX: `sfx_key_swipe_card_wav.mp3` เบา ๆ ที่ `wipeup` (ขึ้นหัวข้อ) และ `ding.wav` ที่ข้อสุดท้าย

### 3.4 `proof_test` — พิสูจน์ให้ดู ลุ้นผล

**1) แนวคิดและจิตวิทยา** ตั้งคำถามใน 1 วิ แรก ("ตกจากโต๊ะแล้วพังไหม") แล้วให้คนดูรอคำตอบ กล้องคืบเข้าช้า ๆ ด้วยความเร็วคงที่ (`linear`) สร้างความตึงแบบสารคดี และตัดผ่านดำหนึ่งจังหวะก่อนเฉลยผลในแต่ละช่วง ช็อตยาวพอให้เห็นการทดสอบจริงทั้งการกระทำ (ตรงกับกฎ Strict Topic Hold) ผลที่คาด: เวลาดูเฉลี่ยสูง และคอมเมนต์ถกผล เหมาะกับ: ของที่ทดสอบได้ด้วยตา (ความทน, กันน้ำ, ความเร็วชาร์จ, แรงแม่เหล็ก), มุม `real_test`, `fake_vs_real` · ข้อความต้องผ่าน `compliance_lint.py` ห้ามอ้างผลเกินจริง

**2) จังหวะตัด** 1.9–3.0 วิ (ยาวสุดเท่าที่กฎอนุญาต) · Hook ≤ 1.1 วิ (ช่วงตั้งคำถามตัดเร็ว ตัดกับตัวคลิปที่ช้า) · ภาพนิ่ง ≤ 3.3 วิ · J-lead 0.22 · beat snap 0.08

**3) Transition** ตระกูลใหม่ `chapter`: `fadeblack` ทุก 5 รอยต่อ (ประมาณทุก 10–13 วิ = จบหนึ่งการทดสอบ) ที่เหลือ hard cut · ยาวสุด 0.40 วิ · ไม่ ease

**4) กล้อง** ทุกช็อตที่ยาว ≥ 1.4 วิ · zoom 0.12 · pan ±0.04 (แทบไม่ส่าย) · `linear`

**5) ภาพและ Hook** accent ฟ้า `#38BDF8` / status `#FFE600` · template `t2_proof_sky` · เข้า `fade` / วน `pulse` (จังหวะเหมือนชีพจร) / ออก `fade` · ซับ: คำที่พูดสีฟ้า

**6) เสียง** แนะนำ Charon (`gemini_charon_male_pro`) โทน `commercial_expert` พูดช้าลงเล็กน้อยได้ (เช่น `+8%`) · BGM ตึงแต่ไม่ง่วงแบบ `bgm_arp_generative_sound_by_glorb.mp3` · SFX: `sfx_beep_adr_countdown.mp3` ก่อนเฉลย, `sfx_gasp_chimes_success_2_wav.mp3` เมื่อผ่าน, `sfx_buzzer_sounds_wrong_answer_error.mp3` เมื่อของเทียบไม่ผ่าน

### 3.5 `glow_up` — ก่อน-หลัง เปิดม่าน

**1) แนวคิดและจิตวิทยา** โชว์สภาพ "ก่อน" ที่รกหรือมีปัญหาใน 1.2 วิ แรก แล้วเปิดม่านลงมาเผย "หลัง" คนดูอยู่ต่อเพราะอยากเห็นผลลัพธ์สุดท้าย และวงกลมเปิดทุกรอยต่อที่ 8 เป็นจังหวะโชว์ภาพรวมที่เสร็จแล้ว ผลที่คาด: ดูจบสูง แชร์และบันทึกในกลุ่มจัดโต๊ะ/จัดบ้าน เหมาะกับ: อุปกรณ์จัดโต๊ะทำงาน, ที่เก็บสาย, ไฟ, ขาตั้งจอ, เคส/ฟิล์ม, มุม `worth_upgrade`

**2) จังหวะตัด** 1.7–2.7 วิ · Hook ≤ 1.2 วิ · ภาพนิ่ง ≤ 2.7 วิ · J-lead 0.20 · beat snap 0.12

**3) Transition** ตระกูลใหม่ `reveal`: `wipedown` ทุก 4 รอยต่อ · ทุกรอยต่อที่ 8 เป็น `circleopen` · ยาวสุด 0.36 วิ · `ease_in_out` (circle ไม่ ease ตามนโยบายเดิม)

**4) กล้อง** ทุกช็อตที่ยาว ≥ 1.0 วิ · zoom 0.10 · pan ±0.12 (กวาดดูผลลัพธ์) · `ease_in_out`

**5) ภาพและ Hook** accent ม่วงคราม `#7C7BFF` / status `#25F4EE` · template `t2_glow_indigo` · เข้า `pop` / วน `lightsweep` / ออก `zoom` · ซับ: คำที่พูดสีม่วงคราม

**6) เสียง** แนะนำ Aoede (`gemini_aoede_female_pro`) โทน `commercial_aesthetic` · BGM `bgm_aesthetic_pop.wav` · SFX: `sfx_magic_sparkle.wav` ที่ `circleopen`, `sfx_camera_shutter.wav` ที่ช็อตผลลัพธ์สุดท้าย

---

## 4. แผนที่ไฟล์ที่ต้องเพิ่ม/แก้

| # | ไฟล์ | งาน |
|---|---|---|
| 1 | `scripts/style_motion_policy.py` | เพิ่ม 4 ตระกูลใน `FAMILY_PACING` · เพิ่ม 5 รายการใน `STYLE_MOTION_POLICIES` · เพิ่ม 4 กิ่งใน `apply_transition_budget` |
| 2 | `scripts/hook_styles.py` + `frontend/src/lib/hookStyles.js` | เพิ่ม template `t2_*` 5 ตัว (สองฝั่งต้องตรงกันทุกฟิลด์ — `test_preview_render_parity.py`) |
| 3 | `scripts/overlay_model.py` (`STYLE_PRESET_TO_TEMPLATE`) + `frontend/src/lib/overlayModel.js` | ผูก preset → template 5 คู่ |
| 4 | `frontend/src/lib/stylePresetCatalog.js` | เพิ่ม 5 รายการใน `STYLE_PRESETS` (ไม่แตะ `ANGLE_TO_DEFAULT_STYLE`) |
| 5 | `frontend/src/components/editor/Toolbar.jsx` | เพิ่ม `<option>` ของ template ใหม่ 5 ตัว (รายการเดิมเขียนตายตัว) |
| 6 | `tests/test_style_distinctness.py` | 10 → 15, 45 → 105 คู่ (บรรทัด 124, 126, 148, 375) + เทสเจตนาของสไตล์ใหม่ |
| 7 | `tests/test_style_preset_consistency.py` | บรรทัด 89 (`== 10`) · `_TYPE_KEYWORD` เพิ่ม `fadewhite`/`fadeblack`/`slideup`/`wipeup`/`wipedown` · กรณี `hardcut` ที่ไม่มี transition เลย (ตอนนี้เทสมี `assert emitted`) |
| 8 | `tests/test_style_motion_policy.py` | รายการชื่อ preset (บรรทัด ~89, 347, 441) และตัวนับ (97, 389) |
| 9 | `tests/test_style_real_render.py` | เพิ่ม `EXPECTED_KINDS` ของ 4 สไตล์ที่มี transition |
| 10 | `frontend/src/lib/stylePresetCatalog.test.js` | รายการ id และข้อความ transition |
| 11 | `_Docs/GADGET_VIDEO_PRODUCTION_SOP.md`, `.agents/rules/gadget_editing_style_checklist.md`, `_Docs/Reports/EDITING_STYLES_REFERENCE_20261111.md`, `ARCHITECTURE.md` | อัปเดตรายการสไตล์ (กฎข้อ 18) |

**ไม่ต้องแก้:** `scripts/video_editor.py`, `frontend/src/components/SequencePlayer.jsx`, `scripts/subtitle_engine.py`, `scripts/config.py`, `scripts/batch_render.py`

ยังไม่ได้ตรวจ: `BatchRenderModal.jsx` และฟอร์มสร้างคลิปดึงรายการจาก `STYLE_PRESET_CATALOG` อัตโนมัติหรือเขียนรายการเอง — ต้องเปิดดูตอนลงมือ

---

## 5. โค้ดพร้อมแปะ

### 5.1 Python — `scripts/style_motion_policy.py`

```python
# FAMILY_PACING: (hook_max_shot, max_static_sec) defaults for the new families.
    "hardcut": (1.0, 2.0),   # raw_ugc: jump cuts only
    "flash": (1.0, 1.8),     # beat_drop: white flash on the beat
    "vertical": (1.1, 2.2),  # swipe_stack: feed-style upward slide
    "chapter": (1.1, 3.3),   # proof_test: dip to black before each result
    "reveal": (1.2, 2.7),    # glow_up: curtain wipe, iris on the payoff
```

```python
    "raw_ugc": StyleMotionPolicy(
        key="raw_ugc",
        # Looks shot by a real user: every join is a hard cut and every shot
        # gets a small, fast punch-in. transition_stride is unused by the
        # "hardcut" family; 1 keeps it inside the sane range.
        transition_stride=1,
        stylized_stride=0,
        max_transition_duration=0.15,
        transition_family="hardcut",
        camera_motion_stride=1,
        camera_zoom_delta=0.10,
        camera_pan_extent=0.05,
        camera_min_duration=0.5,
        min_shot=1.5,
        max_shot=2.3,
        j_lead=0.17,
        beat_snap_tolerance=0.08,
        transition_easing="ease_out",
        hook_max_shot=1.0,
        max_static_sec=2.0,
        camera_easing="ease_out",
        accent_color="#FFB38A",
        status_color="#25F4EE",
        neutral_color="#FFFFFF",
    ),
    "beat_drop": StyleMotionPolicy(
        key="beat_drop",
        # Music-led: the firmest beat lock of any preset, a short white flash
        # on every second boundary, and a push that accelerates into the cut.
        transition_stride=2,
        stylized_stride=0,
        max_transition_duration=0.18,
        transition_family="flash",
        camera_motion_stride=1,
        camera_zoom_delta=0.16,
        camera_pan_extent=0.10,
        camera_min_duration=0.6,
        min_shot=1.5,
        max_shot=2.1,
        j_lead=0.17,
        beat_snap_tolerance=0.16,
        transition_easing="ease_out",
        hook_max_shot=1.0,
        max_static_sec=1.8,
        camera_easing="ease_in",
        accent_color="#E845FF",
        status_color="#FFE600",
        neutral_color="#FFFFFF",
    ),
    "swipe_stack": StyleMotionPolicy(
        key="swipe_stack",
        # Listicle: the picture scrolls up like the feed (slideup every second
        # boundary, a wipeup on every sixth for a new item) while the camera
        # stays almost still so each item can be read.
        transition_stride=2,
        stylized_stride=6,
        max_transition_duration=0.22,
        transition_family="vertical",
        camera_motion_stride=3,
        camera_zoom_delta=0.05,
        camera_pan_extent=0.04,
        camera_min_duration=1.1,
        min_shot=1.6,
        max_shot=2.2,
        j_lead=0.18,
        beat_snap_tolerance=0.13,
        transition_easing="ease_out",
        hook_max_shot=1.1,
        max_static_sec=2.2,
        camera_easing="ease_out",
        accent_color="#22E55E",
        status_color="#25F4EE",
        neutral_color="#FFFFFF",
    ),
    "proof_test": StyleMotionPolicy(
        key="proof_test",
        # Test-and-reveal: long holds on the action, a constant-speed creep
        # in, and a dip to black every fifth boundary before the next result.
        transition_stride=5,
        stylized_stride=0,
        max_transition_duration=0.40,
        transition_family="chapter",
        camera_motion_stride=1,
        camera_zoom_delta=0.12,
        camera_pan_extent=0.04,
        camera_min_duration=1.4,
        min_shot=1.9,
        max_shot=3.0,
        j_lead=0.22,
        beat_snap_tolerance=0.08,
        hook_max_shot=1.1,
        max_static_sec=3.3,
        camera_easing="linear",
        accent_color="#38BDF8",
        status_color="#FFE600",
        neutral_color="#FFFFFF",
    ),
    "glow_up": StyleMotionPolicy(
        key="glow_up",
        # Before/after: a curtain wipe down every fourth boundary and an iris
        # on every eighth for the finished result, with a sweeping pan.
        transition_stride=4,
        stylized_stride=8,
        max_transition_duration=0.36,
        transition_family="reveal",
        camera_motion_stride=1,
        camera_zoom_delta=0.10,
        camera_pan_extent=0.12,
        camera_min_duration=1.0,
        min_shot=1.7,
        max_shot=2.7,
        j_lead=0.20,
        beat_snap_tolerance=0.12,
        hook_max_shot=1.2,
        max_static_sec=2.7,
        accent_color="#7C7BFF",
        status_color="#25F4EE",
        neutral_color="#FFFFFF",
    ),
```

`apply_transition_budget` — สองจุด:

```python
    # (a) directly after the `profile.key == "legacy"` check, before the stride test
    if profile.transition_family == "hardcut":
        return {"type": "cut", "duration": 0.0}

    # (b) new branches beside the existing `compare` / `energetic` ones.
    # All four depend on the boundary number only, like `compare`, so the
    # render and the preview that plays its manifest get the same plan.
    elif profile.transition_family == "flash":
        candidate["type"] = "fadewhite"
    elif profile.transition_family == "chapter":
        candidate["type"] = "fadeblack"
    elif profile.transition_family in ("vertical", "reveal"):
        stylized = profile.stylized_stride > 0 and boundary_index % profile.stylized_stride == 0
        if profile.transition_family == "vertical":
            candidate["type"] = "wipeup" if stylized else "slideup"
        else:
            candidate["type"] = "circleopen" if stylized else "wipedown"
```

โค้ดท้ายฟังก์ชันเดิมจะจำกัด duration ด้วย `max_transition_duration` และใส่ easing ให้เฉพาะ slide/wipe เอง (`fadewhite`, `fadeblack`, `circleopen` ไม่ถูก ease)

### 5.2 Python — `scripts/hook_styles.py` (และกระจกใน `hookStyles.js`)

```python
    "t2_ugc_peach": {
        "label_th": "T1 (พีช+นิ่ง)",
        "font": "Kanit",
        "tiers": {
            "brand": {"size_pct": 170, "color": "#FFB38A", "outline_color": "#0A0A0A",
                      "outline_px": 3.0, "upper": True, "pill": None},
            "model": {"size_pct": 140, "color": "#F7F7F7", "outline_color": "#0A0A0A",
                      "outline_px": 3.0, "upper": False, "pill": None},
            "label": {"size_pct": 80, "color": "#D0D0D0", "outline_color": "#101010",
                      "outline_px": 3.0, "upper": False, "pill": None},
        },
        "motion": {"in": "quick_fade", "loop": "none", "out": "fade", "accent": "none", "stagger": False},
    },
```

อีก 4 ตัวใช้ `tiers` เหมือนกัน เปลี่ยนเฉพาะสี brand และ `motion`:

| id | `label_th` | สี brand | in / loop / out | stagger |
|---|---|---|---|---|
| `t2_beat_magenta` | T1 (ม่วงแดง+เต้น) | `#E845FF` | `pop_zoom` / `pulse` / `glitch` | True |
| `t2_swipe_green` | T1 (เขียว+เลื่อน) | `#22E55E` | `slide_up` / `none` / `slide` | True |
| `t2_proof_sky` | T1 (ฟ้า+ชีพจร) | `#38BDF8` | `fade` / `pulse` / `fade` | True |
| `t2_glow_indigo` | T1 (ม่วงคราม+กวาดแสง) | `#7C7BFF` | `pop` / `lightsweep` / `zoom` | True |

`STYLE_PRESET_TO_TEMPLATE` (Python) และ map เดียวกันใน `overlayModel.js`:

```python
    "raw_ugc": "t2_ugc_peach",
    "beat_drop": "t2_beat_magenta",
    "swipe_stack": "t2_swipe_green",
    "proof_test": "t2_proof_sky",
    "glow_up": "t2_glow_indigo",
```

### 5.3 JavaScript — `frontend/src/lib/stylePresetCatalog.js`

ข้อความ `transitions` ต้องมีคำหลักของทุก type ที่ policy ปล่อยออกมา และห้ามมีคำหลักของ type ที่ไม่ปล่อย (เทส `test_transition_label_names_the_transition_the_policy_renders`) คำหลักใหม่ที่เสนอ: `fadewhite` → `Flash`, `fadeblack` → `Dip`, `slideup` → `Slide`, `wipeup`/`wipedown` → `Wipe` — ข้อความของ `proof_test` จึงห้ามมีคำว่า `Fade`

```js
  {
    id: 'raw_ugc',
    label: 'Raw UGC',
    labelTh: 'รีวิวดิบแบบคนใช้จริง',
    description: 'ตัดตรงทุกรอยต่อ ซูมเข้าเล็กน้อยทุกช็อต ดูเหมือนคนใช้จริงถ่ายเอง',
    motion: 'Punch-in สั้นทุกช็อต',
    transitions: 'Hard cut ทุกรอยต่อ',
    audio: 'Voice นำหน้า SFX น้อยที่สุด',
    accent: '#FFB38A',
    status: '#25F4EE',
    neutral: '#FFFFFF',
    hookTemplate: 't2_ugc_peach',
    hookBadge: 'T1 · STILL',
    hookColor: '#FFB38A',
  },
  {
    id: 'beat_drop',
    label: 'Beat Drop',
    labelTh: 'ตัดตามบีท แฟลชขาว',
    description: 'จุดตัดล็อกกับบีทเพลง แฟลชขาวสั้นสลับรอยต่อ กล้องเร่งเข้าหาจุดตัด',
    motion: 'Push เร่งเข้าทุกช็อต',
    transitions: 'Flash ขาวทุก 2 รอยต่อ ที่เหลือ Hard cut',
    audio: 'เพลงบีทชัด Voice นำหน้า',
    accent: '#E845FF',
    status: '#FFE600',
    neutral: '#FFFFFF',
    hookTemplate: 't2_beat_magenta',
    hookBadge: 'T1 · PULSE',
    hookColor: '#E845FF',
  },
  {
    id: 'swipe_stack',
    label: 'Swipe Stack',
    labelTh: 'ลิสต์เลื่อนฟีด',
    description: 'เล่าเป็นข้อ ภาพเลื่อนขึ้นเหมือนปัดฟีด กล้องนิ่งให้อ่านหัวข้อทัน',
    motion: 'กล้องนิ่งเป็นหลัก ขยับทุก 3 ช็อต',
    transitions: 'Slide ขึ้นทุก 2 รอยต่อ · Wipe ขึ้นทุก 6 รอยต่อ ที่เหลือ Hard cut',
    audio: 'Voice นำหน้า เสียงปัดเบาเมื่อขึ้นหัวข้อ',
    accent: '#22E55E',
    status: '#25F4EE',
    neutral: '#FFFFFF',
    hookTemplate: 't2_swipe_green',
    hookBadge: 'T1 · SLIDE',
    hookColor: '#22E55E',
  },
  {
    id: 'proof_test',
    label: 'Proof Test',
    labelTh: 'พิสูจน์ให้ดู ลุ้นผล',
    description: 'ช็อตยาวเห็นการทดสอบจริง กล้องคืบเข้าช้าสม่ำเสมอ ตัดผ่านดำก่อนเฉลยผล',
    motion: 'Push ช้าความเร็วคงที่ทุกช็อต',
    transitions: 'Dip ผ่านดำทุก 5 รอยต่อ ที่เหลือ Hard cut',
    audio: 'Voice นำหน้า เสียงนับก่อนเฉลย',
    accent: '#38BDF8',
    status: '#FFE600',
    neutral: '#FFFFFF',
    hookTemplate: 't2_proof_sky',
    hookBadge: 'T1 · PULSE',
    hookColor: '#38BDF8',
  },
  {
    id: 'glow_up',
    label: 'Glow Up',
    labelTh: 'ก่อน-หลัง เปิดม่าน',
    description: 'เปิดด้วยสภาพก่อน แล้วปาดลงเผยผลลัพธ์ วงกลมเปิดที่ภาพรวมหลังเสร็จ',
    motion: 'Push + Pan กวาดทุกช็อต',
    transitions: 'Wipe ลงทุก 4 รอยต่อ · Circle ทุก 8 รอยต่อ ที่เหลือ Hard cut',
    audio: 'Voice นำหน้า เสียงประกายเมื่อเผยผล',
    accent: '#7C7BFF',
    status: '#25F4EE',
    neutral: '#FFFFFF',
    hookTemplate: 't2_glow_indigo',
    hookBadge: 'T1 · SWEEP',
    hookColor: '#7C7BFF',
  },
```

---

## 6. ลำดับการทำ (กิ่ง `feat/viral-style-expansion`)

1. **P1 policy + เทส:** แก้ไฟล์ #1 และเทส #6–#8 ให้ผ่าน เพิ่มเทสเจตนา: `raw_ugc` ปล่อยเฉพาะ `cut`, `beat_drop` มี `beat_snap_tolerance` สูงสุดของแคตตาล็อกและ `camera_easing == "ease_in"`, `proof_test` ใช้ `linear` และมี `fadeblack` ห่างกัน 5 พอดี, `swipe_stack` ไม่มี slide ซ้าย-ขวา, `glow_up` สลับ `wipedown`/`circleopen`
2. **P2 Hook template:** ไฟล์ #2, #3, #5 + parity test
3. **P3 แคตตาล็อก UI:** ไฟล์ #4, #10 ตรวจฟอร์มสร้างคลิป/Batch ว่าเห็นสไตล์ใหม่
4. **P4 เรนเดอร์จริง:** ไฟล์ #9 แล้วเรนเดอร์ทดสอบ 5 สไตล์ลง `.tmp/` ดึงเฟรมที่รอยต่อมาดูด้วยตา ลบไฟล์ทดสอบทั้งหมดเมื่อเสร็จ
5. **P5 เอกสาร:** ไฟล์ #11 แล้ว merge เข้า `main` และลบกิ่ง

---

## 7. เช็กลิสต์ทดสอบ

**Golden Master ไม่ขยับ**

- [ ] `git diff` ของ 10 รายการเดิมใน `STYLE_MOTION_POLICIES` ว่างเปล่า
- [ ] ลายนิ้วมือ 24 รอยต่อของ 10 ตัวเดิมเท่าเดิม (เทียบก่อน-หลังแก้ `apply_transition_budget`)
- [ ] `test_clean_default_keeps_its_body_and_tightens_only_the_hook` และเทส "ที่สุด" ของตัวเดิม (`flash_deal` ช็อต/Hook สั้นสุด, `pain_punch` zoom มากสุด, `tech_product_showcase` pan กว้างสุด, `premium_minimal` stride มากสุดและ zoom น้อยสุด, `tech_compare` ช่วงช็อตแคบอันดับสอง) ผ่านโดยไม่แก้เงื่อนไข
- [ ] `DEFAULT_STYLE_PRESET`, `DEFAULT_ONE_CLICK_STYLE_PRESET`, `ANGLE_TO_DEFAULT_STYLE` ไม่เปลี่ยน
- [ ] `tests/test_preview_render_parity.py` ผ่าน และไม่มี diff ใน `subtitle_engine.py` / `SequencePlayer.jsx`

**Distinctness**

- [ ] 105 คู่ ≥ 0.90 (ค่าที่วัดไว้: ต่ำสุดของทั้งแคตตาล็อกยังเป็นคู่เดิม `pain_punch`/`smart_hack` 0.967)
- [ ] recipe (ตระกูล, stride, camera stride, ช่วงช็อต) ไม่ซ้ำ 15 แบบ
- [ ] ลายนิ้วมือ transition ไม่ซ้ำ 15 แบบ
- [ ] ทุกค่าอยู่ใน `SPAN` · `beat_snap_tolerance ≤ j_lead` · `0.17 ≤ j_lead ≤ 0.22`
- [ ] `test_planner_output_differs_between_presets` ได้ 15 แผนที่ต่างกัน (ข้อนี้ยังไม่ได้รันล่วงหน้า เพราะต้องมี policy ในโค้ดก่อน)

**Parity และของจริง**

- [ ] Hook template ใหม่ตรงกันทุกฟิลด์ระหว่าง `hook_styles.py` กับ `hookStyles.js`
- [ ] สี `hookColor` ในแคตตาล็อก = สี brand ที่ template เรนเดอร์จริง
- [ ] ข้อความ `transitions` ในแคตตาล็อกตรงกับ type ที่ policy ปล่อย
- [ ] เรนเดอร์จริง: นับ `fadewhite`/`fadeblack`/`slideup`/`wipedown` ใน manifest ตรงกับแผน, ความยาววิดีโอ/เสียงตรง, ดูเฟรมรอยต่อด้วยตา
- [ ] J-cut ของทุกสไตล์ใหม่อยู่ในช่วง 150–250 ms หลังปัดเข้ากริด 1/30 วิ
- [ ] ซับสีตาม Hook แสดงสี accent ใหม่ทั้ง 5 และอ่านออกบนฟุตเทจสว่าง/มืด

**คำสั่ง**

```
.venv\Scripts\python -m pytest tests/test_style_distinctness.py tests/test_style_motion_policy.py tests/test_style_preset_consistency.py tests/test_preview_render_parity.py -q
.venv\Scripts\python -m pytest tests/test_style_real_render.py -q
cd frontend && npm test && npm run build
```

---

## 8. ข้อที่เจ้าของโปรเจกต์ต้องตัดสินใจ

| # | คำถาม | ข้อเสนอ |
|---|---|---|
| D1 | รับทั้ง 5 สไตล์ ชื่อ และสีตามนี้หรือไม่ | รับทั้ง 5 |
| D2 | เสียงพากย์/โทนต่อสไตล์: ผูกอัตโนมัติ หรือเป็นแค่คำแนะนำ | เป็นคำแนะนำ ค่ามาตรฐานยังเป็น Fenrir + `commercial_premium` (กฎข้อ 5) |
| D3 | เปลี่ยน angle เริ่มต้นหรือไม่ เช่น `real_test` → `proof_test` | ยังไม่เปลี่ยน รอผลวัดจริงก่อน เพราะจะเปลี่ยนผลของ Batch ที่ใช้ "auto" |
| D4 | ชื่อ prefix ของ template (`t2_`) | ใช้ `t2_` (ไม่ทราบความหมายของ `b1_`/`b2_` เดิม จึงไม่ใช้ต่อ) |
| D5 | BGM ต่อสไตล์ | ยังไม่ได้ตรวจว่ามีกลไกเลือก BGM ตาม preset หรือไม่ ถ้าไม่มี = ผู้ใช้เลือกเองตามคำแนะนำ |

---

## 9. การวัดผลหลังปล่อย

เหตุผลเชิงไวรัลทั้งหมดต้องพิสูจน์ด้วยข้อมูลจริง: ปล่อยสินค้าเดียวกัน บทเดียวกัน 2 สไตล์ (ใหม่เทียบกับตัวเดิมที่ใกล้สุดในตารางหัวข้อ 2) อย่างน้อย 5 คู่ต่อสไตล์ แล้วเทียบอัตราดูเกิน 3 วิ, เวลาดูเฉลี่ย, อัตราดูจบ สไตล์ที่ไม่ดีกว่าตัวเทียบให้ปรับค่าหรือถอดออก
