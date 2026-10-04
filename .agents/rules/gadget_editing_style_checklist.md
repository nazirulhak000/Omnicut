# 🎬 กฎและเช็กลิสต์มาตรฐานการตัดต่อวิดีโอแกดเจ็ต (Gadget Editing Style Standard & Checklist)

> **เป้าหมาย:** สรุปกฎเหล็กและเช็กลิสต์ตรวจสอบทุกรอบการตัดต่อคลิปรีวิวแกดเจ็ต 9:16 (1080x1920) ความยาว 60 วินาที เพื่อให้คลิปสนุก คมชัดระดับโปร ตัวหนังสือสวยงาม ไม่ตกหล่น และไม่มีจุดผิดพลาด

---

## 📌 1. กฎเหล็ก 5 เสาหลัก (The 5 Core Pillars)

### 🔤 เสาหลักที่ 1: ซับไตเติล Mali-Bold & การจัดกลุ่มพยางค์ (Syllable Clustering)
1. **ฟอนต์ซับไตเติล**: บังคับใช้ **`Mali-Bold`** (ขนาด 88px, ขอบดำ Outline 5.2px, Shadow 0, MarginV 380) เท่านั้น
2. **ห้ามใช้ผลลัพธ์ดิบจาก Whisper เด็ดขาด (Strict Zero-Whisper Hallucination)**:
   - Whisper ถอดเสียงเพี้ยนและสะกดชื่อแบรนด์ผิดเสมอ (เช่น `Xiaomi MIX Flip` กลายเป็น "เสยมีมิกกษฟลิป")
   - ต้องนำ Timestamp จาก Whisper มา Map เข้ากับ **บทสคริปต์ทางการภาษาไทยและภาษาอังกฤษที่ถูกต้อง 100%**
3. **การรวมพยางค์ (Syllable Clustering)**:
   - ต้องผูก `พยัญชนะต้น + สระบน/ล่าง + วรรณยุกต์/การันต์` ไว้ในก้อนเดียวกันเสมอ เช่น `("นี่", ...)`, `("สมาร์ท", ...)`, `("โฟน ", ...)`, `("รุ่น", ...)`
   - ❌ **ห้ามวนลูปทีละตัวอักษร Unicode เดี่ยวๆ (No Char-by-Char Splitting)** เพราะจะทำให้สระลอยและวรรณยุกต์ฉีกขาด
   - ใส่เว้นวรรคท้ายคำเพื่อสร้างช่องไฟธรรมชาติ (Natural Spacing) ให้อ่านง่ายเป็นจังหวะ
4. **เทคนิค Progressive Ghost Reveal (ตัวอักษรค่อยๆ โผล่จากซ้ายไปขวา)**:
   - คำที่พูดไปแล้ว: สีขาวบริสุทธิ์ `{\c&HFFFFFF&}`
   - พยางค์ที่กำลังออกเสียง: สีเขียวนีออนสะท้อนแสง `{\c&H66FF00&}` ขยาย 114% `{\fscx114\fscy114}`
   - คำถัดไปที่ยังไม่พูด: ซ่อนโปร่งใส 100% `{\alpha&HFF&}` (จองพื้นที่แบบ Zero-Jitter Ghost Layout ตัวหนังสือไม่กระโดด)
   - เมื่อพูดจบทั้งวลี ให้คงข้อความสีขาวเต็มบรรทัดไว้จนจบช่วง (Settle Duration) เพื่อให้คนดูอ่านทัน
5. **จำกัดความยาว 1 บรรทัด (1-Line Micro-Burst)**:
   - แต่ละช่วงแสดง 2–4 คำ สั้นกระชับ ❌ **ห้ามขึ้น 2 บรรทัดเด็ดขาด** หากประโยคยาว ให้ตัดแบ่งเป็น 2 วลีย่อย

---

### 🏷️ เสาหลักที่ 2: กล่องสเปก Callout (Top White + Bottom Vibrant Orange)
1. **ข้อความบน (Category/Feature)**:
   - ฟอนต์: `Prompt-Bold` ขนาด 76px, สีขาวล้วน `&H00FFFFFF&`, ขอบดำ Outline 4.5px, Shadow 2.0px, MarginV 250
2. **ข้อความล่าง (Spec Metric/Highlight)**:
   - ฟอนต์: `Prompt-Black` ขนาด 94px, สีส้มนีออนสดใส `&H002266FF&` (`#FF6622`), ขอบดำ Outline 5.5px, Shadow 2.5px, MarginV 530
3. **ความคลีน**:
   - ❌ **ห้ามใส่เส้นคั่นสีเขียว และห้ามใส่สีเขียวในหัวข้อ Callout**
   - มีแอนิเมชัน Fade In/Out นุ่มนวล `{\fad(200,200)}`
4. **ลายน้ำ/เครดิต (Source Attribution)**:
   - ระบุแหล่งที่มาจริงที่ขอบล่างสุด (`MarginV: 36`): `Source : mi.com Official` (ฟอนต์ Prompt ขนาด 24px สีขาวจางขอบดำ)
   - ❌ **ห้ามใส่ป้ายปลอม เช่น TECH MX**

---

### ⏱️ เสาหลักที่ 3: กฎล็อกภาพค้างจบประโยค (Strict Topic Hold)
1. **ห้ามตัดภาพหนีก่อนเสียงพูดจบประโยค**:
   - ขณะพูดถึงฟีเจอร์ใด ภาพบนจอต้องเป็นฟีเจอร์นั้นตลอดทั้งประโยค
   - **ช่วงหน้าจอด้านใน (18.14s – 28.28s)**: ต้องแสดงภาพกางหน้าจอจริง / หน้าจอ OLED ดอกไม้ / สเปก 3,000 nits ตลอดทั้งช่วง ❌ **ห้ามตัดสลับกลับไปภาพเครื่องพับให้คนดูสับสน**
   - **ช่วงระบบระบายความร้อน 3D VC (42.40s – 48.64s)**: ต้องแช่ภาพชิ้นส่วน Exploded 3D Dual-VC Chamber ค้างตลอดทั้งประโยคระบายความร้อน
2. **Dynamic Multi-Cut & Ken Burns**:
   - สลับภาพทุก 1.5 – 3.0 วินาที เพื่อความกระชับ น่าติดตาม
   - ภาพนิ่งทุกภาพต้องใส่ Ken Burns (Slow Zoom 1.0 -> 1.10) ห้ามแช่ภาพนิ่งแข็งทื่อ
   - Ken Burns ของรูปนิ่ง (`scripts/image_motion_engine.py`, `_ENGINE_SCHEMA = 2`) ต้องได้ **จำนวนเฟรมพอดี `ceil(ความยาว × 30)`** (เดิม cue 2 วิ ได้ ~100 วิ) · ขยายภาพก่อน 4× ด้วย lanczos · รูปแนวนอนต้องไม่ถูกยืด (pad เป็น 3:4) · ชื่อไฟล์ segment `motion_seg_NNN_<hash>.mp4`
3. **จังหวะตัดตามสไตล์ (Cut Rhythm per Style)** — ค่า `min_shot`/`max_shot`/`j_lead`/`beat_snap_tolerance` อยู่ใน `scripts/style_motion_policy.py` ไม่ใช่ค่าคงที่ร่วมอีกต่อไป (ตารางครบทุกสไตล์ใน [_Docs/GADGET_VIDEO_PRODUCTION_SOP.md](file:///d:/Winona/Programmer/Capcut/_Docs/GADGET_VIDEO_PRODUCTION_SOP.md) Phase 5):
   - **ค้างภาพจนจบประโยค**: ถ้าจบประโยคอยู่ในระยะ `max_shot` ให้รอจบประโยคก่อนตัด (Sentence-aware grouping) — ไม่ขัดกับ Strict Topic Hold
   - **ลำดับ snap**: beat > motion > voice-valley > rhythm · voice-valley = ขยับ ±2 เฟรมไปช่วง 10 ms ที่เงียบที่สุดของเสียงพากย์ โดย lead ต้องอยู่ 0.10–0.30 s
   - **Transition แบบ slide** หันทิศตามการแพนของคลิปขาออก (pan ขวา → เนื้อหาวิ่งไปซ้าย → `slideleft`)
4. **J-Cut วัดจากไฟล์จริง**: ทุกรอยต่อภาพต้องเปลี่ยน**หลัง**เสียงเริ่มเสมอ (lead เป็นบวก ≈ 167 ms ที่ค่าเริ่มต้น; มาตรฐาน 150–250 ms) · จุดตัดแรก = `0.0` ไม่ใช่ `first_cue_start` · transition วางกึ่งกลางจุดตัด · รายละเอียดใน [.agents/rules/j_cut_rules.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/j_cut_rules.md) §6
5. **กริดเฟรมเต็ม**: จุดตัด/ความยาวคลิป/offset ของ transition ทั้งหมดอยู่บนกริด 1/30 s แบบสะสม (`boundary_k = round(cumsum_k × 30) / 30`) เฟรมรวม = `round(total × 30)` ทั้งพรีวิวและเรนเดอร์ — สาย 12 คลิปต้องไม่เลื่อนสะสม
6. **Easing เริ่มต้น (เปลี่ยนเฉพาะเส้นโค้งการเคลื่อนไหว ไม่แตะฟอนต์/ขนาด/ตำแหน่ง)**:
   - กล้อง: push/pan ที่ pipeline สร้างและ preset ซูมช้าใน Inspector ใช้ `ease_in_out` (keyframe ที่ไม่มี `easing` = linear เหมือนเดิม)
   - Transition: ตั้ง easing เฉพาะ fade/wipe/slide — `ease_in_out` สำหรับ smooth_showcase, premium_minimal, clean_tech_review, tech_product_showcase, niche_focus, tech_compare · `ease_out` สำหรับ viral_punch, flash_deal, pain_punch, smart_hack · ❌ ห้ามตั้งบน `fadeblack`/`fadewhite` (เรนเดอร์ช้าลง +8–13 วิ ต่อ transition ที่ 1080x1920) · `dissolve`/`circleopen`/`circleclose` คง linear
   - ข้อความ/Hook: bounce/pop/in-zoom accel 0.6, out fade/zoom accel 2.2, shake step 100 ms, glitch step 33 ms (ค่าอยู่ใน `motion_contract.py` / `motionPresets.js` ผูกด้วยเทส)
7. **สติกเกอร์/effect เข้า-ออกนุ่มนวล**: เข้า = fade-in 7 เฟรม (0.233 s) + (เฉพาะสติกเกอร์) scale 0.88→1.0 ease_out · ออก = fade-out 6 เฟรม (0.2 s) · fade ไม่เกิน 40% ของเวลาที่เห็น · เฟรมนิ่งต้องเหมือนเดิมทุกบิต · พรีวิว (`stickerAnimation.js`) = render (`video_editor.py overlay_anim_*`)

---

### 🎵 เสาหลักที่ 4: ระบบเสียงและดนตรี (Upbeat IT Channel Mix)
1. **เสียงบรรยาย (TTS Voice)**:
   - Gemini Flash TTS เสียง `Fenrir` (ชายสตรอง คมเข้ม) สไตล์ `commercial_premium`
   - ระดับเสียง: **`Volume: 1.0`** (คมชัด ไม่แตก)
2. **เพลงประกอบ (BGM)**:
   - บังคับใช้เพลงสไตล์ไอที สนุกสนาน คึกคัก มีจังหวะบีทกระแทกกระทั้น เช่น **`02_Assets/Music/tiktok_upbeat_bgm.wav`**
   - ❌ **ห้ามใช้เพลง Lo-Fi ชวนง่วง**
   - ระดับเสียง: **`Volume: 0.14`** (เสียงดังพอดี เสริมความมันส์ ไม่กลบเสียงพากย์)
   - ช่วงท้ายคลิป (58.5s – 60.0s): Fade out ดนตรีนุ่มนวล

---

### 🖼️ เสาหลักที่ 5: สเปกภาพ 9:16 และความสะอาดของไฟล์
1. สเปกวิดีโอ: `1080x1920`, `30.00 FPS`, ความยาว `60.00 วินาทีเต็ม`
2. เลย์เอาต์: ตัวสินค้ากึ่งกลาง คมชัด 100% (Uncropped) + ขอบบนล่างเบลอแบบ Gaussian Blur
3. ความสะอาดของโปรเจกต์: วิดีโอทดสอบทั้งหมดต้องอยู่ใน `.tmp/` ห้ามทิ้งไฟล์ลง `04_Exports/` เด็ดขาด

---

## ✅ 2. เช็กลิสต์ตรวจสอบก่อนส่งมอบงาน (Pre-Flight QA Checklist)

ก่อนรายงานผลให้ผู้ใช้ ต้องผ่านการตรวจเช็กทุกข้อดังนี้:

| จุดตรวจ | สิ่งที่ต้องยืนยัน | ผ่าน (Y/N) |
| :--- | :--- | :---: |
| **1. ฟอนต์ซับ** | เป็น `Mali-Bold` ขนาด 88px ขอบดำ 5.2px และ MarginV 380 | [ ] |
| **2. การตัดคำ** | สระบน/ล่าง วรรณยุกต์ติดกับพยัญชนะต้น ไม่มีการฉีกขาด | [ ] |
| **3. สะกดคำ** | ชื่อแบรนด์และสเปกถูกต้องเป๊ะ (Xiaomi MIX Flip, Snapdragon, Leica) | [ ] |
| **4. แอนิเมชันซับ** | ค่อยๆ โผล่ทีละพยางค์ (Ghost Reveal) เด้งสีเขียวนีออน `#66FF00` 114% | [ ] |
| **5. บรรทัดเดียว** | ซับไตเติลทุกช่วงสั้นกระชับ แสดงบรรทัดเดียว ไม่มีการตกบรรทัด | [ ] |
| **6. กล่อง Callout** | ข้อความบนสีขาว (`Prompt-Bold`) + ข้อความล่างสีส้มไฟนีออน (`Prompt-Black`) | [ ] |
| **7. Strict Topic Hold** | ภาพตรงกับสิ่งที่พูดตลอดประโยค ไม่ตัดภาพหนีก่อนพูดจบ | [ ] |
| **8. เพลง BGM** | ใช้เพลงสนุกสนานแนวไอที (`tiktok_upbeat_bgm.wav`) ระดับเสียง 0.14 | [ ] |
| **9. วิดีโอสเปก** | 1080x1920, 30 FPS, ความยาว 60.00s เป๊ะ | [ ] |
| **10. สกัดคีย์เฟรม** | สกัดภาพตรวจสอบจุดสำคัญอย่างน้อย 5 จุดบันทึกลง Artifact | [ ] |
| **11. ลิงก์เปิดไฟล์** | จัดทำ Markdown Link แบบ `file:///` คลิกเปิดได้ทันที | [ ] |
| **12. ข้อความหลังสินค้า (ถ้ามี)** | Hook/Text Overlay เลือกชั้นหน้า/หลังตรงตามเจตนา เตรียม Cutout เฉพาะช่วง และตรวจเฟรมเข้า/ออกใน Preview กับ Render | [ ] |
| **13. J-Cut วัดจริง** | ภาพเปลี่ยนหลังเสียงเริ่มทุกรอยต่อ (lead บวก ≈ 167 ms ที่ค่าเริ่มต้น, มาตรฐาน 150–250 ms) ไม่มี reverse J-cut และไม่มีเฟรมท้ายถูกค้าง | [ ] |
| **14. กริดเฟรม** | จุดตัดทุกจุดอยู่บนกริด 1/30 s, เฟรมรวม = `round(ความยาว × 30)`, สายคลิปยาวไม่เลื่อนสะสม | [ ] |
| **15. จังหวะตัดต่อสไตล์** | ความยาว shot อยู่ในช่วง `min_shot`–`max_shot` ของสไตล์ที่เลือก (ตาราง SOP Phase 5) และตัดหลังจบประโยคเมื่อถึงภายใน `max_shot` | [ ] |
| **16. Easing** | กล้อง push/pan = `ease_in_out`, transition fade/wipe/slide ตามนโยบายสไตล์ (ไม่มีบน fadeblack/fadewhite), Ken Burns รูปนิ่งได้เฟรมเท่า `ceil(dur × 30)` ไม่ถูกยืด | [ ] |
| **17. สติกเกอร์/effect** | เข้า fade-in 7 เฟรม (+ scale 0.88→1.0 เฉพาะสติกเกอร์) ออก fade-out 6 เฟรม ดูเฟรมเข้า/นิ่ง/ออกใน Preview กับ Render ตรงกัน | [ ] |

---

## 🛠️ โค้ดแม่แบบอ้างอิง (Golden Master Reference Script)
* **โฟลเดอร์ผลงานมาสเตอร์ Product-Centric**: [.tmp/Products/Xiaomi_MIX_Flip/03_Export/](file:///d:/Winona/Programmer/Capcut/.tmp/Products/Xiaomi_MIX_Flip/03_Export/)
* **ไฟล์วิดีโอตัวจบมาสเตอร์**: [Xiaomi_MIX_Flip_60s_Master.mp4](file:///d:/Winona/Programmer/Capcut/.tmp/Products/Xiaomi_MIX_Flip/03_Export/Xiaomi_MIX_Flip_60s_Master.mp4)
* **สคริปต์คอมโพสิตและสร้างซับไตเติล**: [tools/build_60s_mali_burst_ass.py](file:///d:/Winona/Programmer/Capcut/tools/build_60s_mali_burst_ass.py)
* **ไฟล์ซับไตเติลมาตรฐาน**: [.tmp/Products/Xiaomi_MIX_Flip/02_Workspace/subtitles/subtitles_60s_mali_burst.ass](file:///d:/Winona/Programmer/Capcut/.tmp/Products/Xiaomi_MIX_Flip/02_Workspace/subtitles/subtitles_60s_mali_burst.ass)
