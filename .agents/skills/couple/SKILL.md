---
name: couple
description: >-
  Production-grade workflow skill for Thai comedy couple sitcom clips (#5 Couple Paper Chat: น้องนุ้ย & พี่บ่าว) on stop-motion paper background (1080x1920 9:16). Trigger with /couple, /couple-chat, or "ทำสไตล์ couple" whenever generating scripts, audio, compositions, or rendering Southern couple review clips. Enforces 100% Golden Master parity (ors01), Zero-Emoji, Zero-Arrow, Single-Take TTS, and mandatory visual inspection gates.
---

# 🎬 สกิลการตัดต่อวิดีโอ: ละครสั้นคู่รักสายใต้บนกระดาษยับ (/couple)
### OmniCut & HyperFrames Master Couple Paper Chat (#5) Standard

> ### 🛑 กฎเหล็กข้อบังคับสูงสุด (NON-NEGOTIABLE CORE CONTRACT)
> เมื่อผู้ใช้สั่ง **/couple** หรือระบุให้ทำคลิปสไตล์ **Couple Paper Chat (น้องนุ้ย & พี่บ่าว)**:
> 1. **ห้ามเขียนโครงสร้าง HTML/CSS ใหม่จากหัวเด็ดขาด (No Improvisation)**: โครงสร้าง DOM และ CSS ทั้งหมดต้องโคลนจาก **Golden Master ([ors01-pov-s01.html](file:///D:/Programmer/All%20Project/Omnicut/06_Archive/HyperFrames_Studio/compositions/ors01-pov-s01.html))** และ [batch_produce_orsen_20.py](file:///D:/Programmer/All%20Project/Omnicut/tools/batch_produce_orsen_20.py) 100% เท่านั้น
> 2. **ห้ามก๊อปปี้ต่อจากสคริปต์ที่เคยดัดแปลง (No Drift Inheritance)**: ห้ามอ้างอิงหรือคัดลอก CSS/DOM จาก `batch_produce_goojodoq_20.py` เด็ดขาด
> 3. **ต้องผ่าน Visual Inspection Gate ก่อนเรนเดอร์หมู่เสมอ**: ต้องสกัดภาพนิ่ง 2 เฟรม (Frame แชท + Frame CTA) มาตรวจสอบขนาด, ฟอนต์, ระยะเว้น, อวตาร, และความโปร่งใสของพื้นหลัง ก่อนเริ่มเรนเดอร์ 20 คลิปเสมอ

---

## ⛔ 1. ข้อห้ามเด็ดขาด (STRICT DON'Ts)

1. ❌ **ห้ามใส่อีโมจิในช็อต CTA ท้ายคลิป และปกคลิปเด็ดขาด (Rule 21 & Strict Zero-Emoji Guard)**:
   - ห้ามมี `⚡`, `🔋`, `🪶`, `📱`, `🎨`, `✨`, `🔥`, `🛒`, `⚪` ในป้ายสเปก, ป้ายสี หรือการ์ดพาเลตต์ เพื่อรักษาความพรีเมียมระดับ Creative Agency ป้องกันความรู้สึกว่าเป็นคลิปขยะ/สแปม AI
2. ❌ **ห้ามใส่ลูกศรสีแดงชี้พาดผ่านสินค้าเด็ดขาด (Rule 22 & Strict Zero-Arrow Guard)**:
   - ถอดเส้นลูกศรแดง/SVG ออก 100% ไม่ให้บดบังตัวสินค้า โดยใช้ Header Hook (`พลังลมตัวจบ · กดตะกร้าเหลือง`) และเสียงพากย์ชี้นำตะกร้าเหลืองแทน
3. ❌ **ห้ามใส่ราคาในคลิปเด็ดขาด (Strict Zero-Price Guard)**:
   - ห้ามมีตัวเลขราคา, ราคาขีดฆ่า, "ลด X%", "ถูกมาก", "ไม่ถึงร้อย" ป้องกันการทำลายความน่าเชื่อถือและป้องกันการผิดกฎ TikTok
4. ❌ **ห้ามใส่จุดไข่ปลา ("...", "…") ในบทพูดสคริปต์เด็ดขาด (Rule 7)**:
   - ให้ใช้การเว้นวรรคธรรมชาติ ป้องกันเสียง TTS สะดุดหรือจุดไข่ปลาหลุดเข้าซับไตเติล
5. ❌ **ห้ามเปลี่ยนพื้นหลังกระดาษยับเป็นสีทึบในช็อต CTA ท้ายคลิป**:
   - `#b-cta` ต้องเป็น `background: transparent` เพื่อให้วิดีโอกระดาษยับจริง `assets/shared/paper_bg.mp4` เล่นต่อเนื่องไร้รอยต่อตลอดทั้ง 60 วินาที
6. ❌ **ห้ามเปลี่ยนบุคลิกเสียงกลางคัน (Rule 20 & Strict Monolithic Acting Guard)**:
   - พี่บ่าว: ห้ามเปลี่ยนเป็นเสียงสุขุม/เก๊กหล่อ/ทางการเด็ดขาด แม้อ่านสเปกหรือชิป
   - น้องนุ้ย: ห้ามเปลี่ยนเป็นเสียงหวานนุ่มเรียบร้อย หรือเสียงโมโนโทน
7. ❌ **ห้ามใช้ `transform: translateX(-50%)` บน Element ในฉาก CTA ที่เล่น GSAP Scale**:
   - เพราะ GSAP `fromTo({ scale })` จะล้าง inline transform ทิ้ง ทำให้ Element วิ่งหลุดจากกึ่งกลางไปทางขวาทันที ให้ใช้ `left: 50%; margin-left: -(width/2)px;` เสมอ
8. ❌ **ห้ามปล่อยให้หัวข้อ CTA (`#cta-1`) ล้นขอบจอ**:
   - หากความยาวชื่อสินค้า > 18 ตัวอักษร ให้ลดขนาดฟอนต์จาก 86px ลงเหลือ 68–72px ทันที ห้ามล้นขอบขวาเด็ดขาด
9. ❌ **ห้ามปล่อยให้มีเดดแอร์ (Silence Dead Air > 0.35s) ในเสียงพากย์เด็ดขาด**:
   - ต้องตัด Lead & Tail Silence ของทุกประโยคทิ้งให้หมด ก่อนประกอบเป็น `vo.wav`

---

## 📐 2. โครงสร้าง Layout และ CSS ตาม Golden Master (ors01 Parity)

| ส่วนประกอบ | ค่ามาตรฐานที่ถูกต้อง (Golden Master: `ors01`) | ข้อผิดพลาดที่ห้ามทำ (Anti-Pattern) |
| :--- | :--- | :--- |
| **Root Element** | `<div id="root" data-composition-id="...">` | ❌ ห้ามใช้ `<div id="stage">` |
| **Chat Container** | `<div id="chatwin"><div id="thread">` | ❌ ห้ามใช้ `#chat-thread` หรือ `#chat-canvas` |
| **Chat Window Bounds** | `top: 470px; height: 1170px; left: 0; right: 0; overflow: hidden;` | ❌ ห้ามย้ายตำแหน่งหรือแก้ความสูง |
| **Row Alignment** | `position: absolute; left: 40px; right: 40px;` | ❌ ห้ามใช้ `left: 80px; right: 80px;` หรือ Flex margin |
| **Speaker Avatar (`.ava`)** | `width: 80px; height: 80px; font-size: 40px; line-height: 72px;` อวตารตั้งค่า `position: absolute; top: 0;` (F อยู่ `left: 0;`, M อยู่ `right: 0;`) | ❌ ห้ามขยายเป็น 88px, ห้ามใช้ flex-flow, ห้ามตั้ง `bottom: 0` |
| **Row Padding** | ฝั่งหญิง: `padding-left: 96px;` / ฝั่งชาย: `padding-right: 96px;` | ❌ ห้ามใช้ค่าอื่น เพราะจะทำให้อวตารชนบับเบิล |
| **Speaker Name (`.nm`)** | `font-size: 32px; color: #55514a; padding: 0 104px;` (วางตรงหัวมุมบับเบิลพอดี) | ❌ ห้ามลดเหลือ 26px, ห้ามตั้ง `left: 80px` เหนือหัวอวตาร |
| **Speech Bubble (`.msg`)** | `font-size: 44px; line-height: 1.25; border-radius: 34px; border: 4px solid var(--ink); box-shadow: 4px 6px 0 var(--ink);` | ❌ ห้ามลด radius เหลือ 28px, **ห้ามใส่หางแชทแหลม 6px เด็ดขาด** |
| **Photo Frame (`.photo`)** | สี่เหลี่ยมจัตุรัสคลีน: `padding: 10px; border-radius: 18px;` รูปด้านใน `520x520px; border-radius: 10px; object-fit: cover;` | ❌ ห้ามใช้ทรงโพลารอยด์คางหนา (`padding: 14px 14px 28px 14px;`) |
| **CTA Outro Container** | `position: absolute; inset: 0; background: transparent;` | ❌ **ห้ามใส่ `background: #fdfbf7` หรือสีทึบเด็ดขาด** |
| **CTA Headline Grid** | `#cta-1` (`top: 165px; left: 0; right: 0; width: 100%; text-align: center;` ฟอนต์ Kanit Black: >30 ตัวอักษรใช้ `52-54px`, 25-29 ตัวใช้ `58-60px`, <25 ตัวใช้ `64-66px`) + `#cta-model` (`top: 275px; left: 0; right: 0; width: 100%; text-align: center; font-size: 44px;`) + `#cta-stage` (`top: 370px; height: 880px;`) + `.floating-badge` (`font-size: 24px; padding: 7px 16px; left/right: 65-70px;`) ป้องกันข้อความ/ป้ายสเปกล้นขอบจอ 100% (Safe Margin >= 65px ทุกด้าน) | ❌ ห้ามใช้ Flexbox ไหล, ห้ามตั้ง `left: 40px; right: 40px;` โดยไม่คุมขนาดฟอนต์, ห้ามฟอนต์ใหญ่เกิน 66px กับชื่อยาวเกิน 25 ตัว |
| **CTA Hero Centering** | `left: 50%; margin-left: -(width/2)px;` จัดกึ่งกลางด้วย margin เพื่อความปลอดภัยกับ GSAP | ❌ ห้ามใช้ `transform: translateX(-50%)` ที่จะถูก GSAP ล้าง |
| **BGM Standard Track** | `assets/shared/bgm_lofi.wav` ระดับเสียง `data-volume="0.05"` (`fade-in="0.6" fade-out="1.5"`) | ❌ ห้ามใช้เพลงอื่น หรือเปิดเสียงดังเกิน 0.08 จนกลบเสียงพากย์ |

---

## 🎙️ 3. มาตรฐานการพากย์เสียง (Gemini Flash TTS + Snappy Conversational Pacing)

1. **ยิง Single-Speaker แยก 2 ครั้งรวดเดียว (Strict 2 Passes):**
   - **Take 1 (น้องนุ้ย):** โมเดล `gemini-3.8-flash-tts`, เสียง `Aoede` (สาวใต้เสียงใส น่ารักแต่ดุ แก่นเซี้ยว ขี้บ่นกวนๆ)
     - DSP: `asetrate=24000*1.10,aresample=48000,atempo=1.20,highpass=f=140,equalizer=f=3500:t=q:w=1.2:g=3.0`
   - **Take 2 (พี่บ่าว):** โมเดล `gemini-3.8-flash-tts`, เสียง `Puck` (หนุ่มใต้ซื่อๆ ตกใจฮาๆ อารมณ์ดี กวนประสาท)
     - DSP: `atempo=1.32,highpass=f=95`
2. **คั่นประโยคด้วยช่วงเงียบ 2.0 วินาที (`... ...`)** และตัดแบ่งด้วย `split_by_longest_gaps`
3. **ตัด Dead Air เสียงพูด (Strict Lead & Tail Silence Trimming):**
   - ต้องตัด Lead Silence และ Tail Silence ของทุกไฟล์ก้อนเสียง Turn ออกให้หมด (ตัดขอบคลื่นเสียงที่แอมพลิจูด < 300) เหลือ buffer ปลอดภัยเพียง 30–50ms
   - ช่องว่างระหว่างคนพูดโต้ตอบ (Turn Gap) ต้องควบคุมให้กระชับแน่นที่ **0.18s – 0.25s** (กรณีสลับคนพูด) และ **0.10s – 0.14s** (กรณีคนเดิมพูดต่อ) ห้ามมีช่องว่างเดดแอร์เกิน 0.35s เด็ดขาด
4. **ตัดเสียงรบกวน (Audio Sanitization):**
   - ล้างรหัสสัญญาณรบกวน (White noise / glitch) ในช่องว่างระหว่างเทิร์น
   - ทำ Smooth Cosine Tail Fade-out 120ms ช่วงท้ายไฟล์ `vo.wav` เงียบสนิท 100%

---

## 🖼️ 4. Visual Inspection Gate (ขั้นตอนตรวจภาพก่อนเรนเดอร์หมู่)

ก่อนจะสั่งรัน Multi-Worker Batch Render (Concurrency = 4) กับคลิปหมู่:
1. **เรนเดอร์ภาพนิ่ง 2 เฟรมของคลิปแรกของ "ทุกสินค้า" (ห้ามตรวจแค่สินค้าเดียว):**
   - **Frame A (แชทกลางคลิป):** ตรวจสอบว่าอวตาร 80px, ชื่อคนพูดลอยตรงกับบับเบิล, บับเบิลมน 34px ไร้หางแหลม, รูปสินค้าไม่เป็นโพลารอยด์
   - **Frame B (ช็อต CTA ท้ายคลิป ที่เวลา `cta_t + 1.8s`):** ตรวจสอบว่าสินค้าอยู่กึ่งกลางจอ 1080px เป๊ะ, หัวข้อไม่ล้นขอบจอ, กระดาษยับขยับต่อเนื่อง, ไร้อีโมจิ, ไร้ลูกศรแดง, พิกัด 3-Tier สวยงาม
2. หากภาพถูกต้อง 100% ทุกสินค้า จึงจะเริ่มคำสั่งเรนเดอร์วิดีโอ MP4 ต่อไป

---

## ⚡ 5. มาตรฐานการเรนเดอร์ไฮบริด CPU + GPU คู่ขนาน (Mandatory CPU + GPU Hybrid Rendering Standard)

เพื่อให้การเรนเดอร์คลิปวิดีโอ 1080x1920 รวดเร็วและไม่ทำให้ซีพียูโอเวอร์โหลดจนค้าง ต้องบังคับใช้ฮาร์ดแวร์คู่ขนาน CPU + GPU (RTX 4060) เสมอ:
1. **HyperFrames DOM & Frame Capture (Chromium):**
   - ต้องแนบแฟล็ก `--gpu` และ `--browser-gpu` ในคำสั่ง `hyperframes render` ทุกครั้ง เพื่อบังคับให้ Chromium ใช้ฮาร์ดแวร์ GPU ในการทำ Layer Compositing, Drop-shadows, และ Canvas Rasterization
2. **TikTok Pro Video Enhancer (FFmpeg):**
   - ต้องตรวจจับและใช้ **NVIDIA NVENC Hardware Encoder (`h264_nvenc`)** เสมอ:
     `-c:v h264_nvenc -preset p4 -rc vbr -cq 19 -b:v 0 -profile:v high -level 4.2 -pix_fmt yuv420p`
   - โยกภาระการคำนวณเวกเตอร์บีบอัดวิดีโอ 1080x1920 จาก CPU ไปยังการ์ดจอ RTX 4060 (ลดเวลาแปลงไฟล์จาก 30 วิ เหลือ 2-3 วิ)
3. **การแบ่งบทบาท:**
   - **CPU:** ประมวลผล DOM Logic, GSAP Timeline, Audio Synchronization, Multi-Worker Orchestration
   - **GPU (RTX 4060):** รับงานหนักด้าน Video Transcoding, Unsharp Mask Shader, Color Calibration, Layer Rasterization
