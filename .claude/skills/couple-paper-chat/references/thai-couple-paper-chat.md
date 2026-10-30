# 🎬 คู่มือมาตรฐานสไตล์และระบบเสียง: Couple Paper Chat (#5) & Brand-First CTA

คู่มืออ้างอิงฉบับสมบูรณ์สำหรับ HyperFrames Creative และ OmniCut Studio ในการสร้างคลิปไวรัล TikTok สไตล์ **ละครสั้นคู่รักสายใต้ (น้องนุ้ย & พี่บ่าว) บนกระดาษยับ**

---

## 📌 1. ภาพรวมสไตล์ (Approved Standard #5)
- **อัตราส่วน & สเปก**: แนวตั้ง 9:16 (`1080x1920`, 30 FPS, H.264)
- **ฉากหลัง**: วิดีโอกระดาษยับ Stop-motion จริง (`assets/shared/paper_bg.mp4`) เล่นความเร็วช้าลงครึ่งหนึ่ง (`data-playback-rate="0.5"`) ให้ฟีลลิ่ง Handmade เป็นธรรมชาติ
- **ความยาว & การ์ดรูป (Creative Freedom)**:
  - **ความยาวคลิป**: ยืดหยุ่นได้ตามความสนุกและจังหวะโบ๊ะบ๊ะของบท (ปกติ 40–65 วินาที) **ไม่ฟิกซ์เวลาตายตัว** โฟกัสความสนุกสนาน น่าติดตาม จังหวะตบมุกคู่รักคมๆ และป้ายยาอย่างเป็นธรรมชาติ
  - **การ์ดรูปภาพ**: ยืดหยุ่นตามเนื้อหา (2–5 รูปตามความเหมาะสมของเรื่องราวและจุดขายสินค้า)
- **โครงเรื่อง (Drama-to-Commerce Hook)**:
  1. *ฉากที่ 1 (วิกฤต/ปัญหา)*: น้องนุ้ยมีปัญหาเร่งด่วน บ่นด่าแซวพี่บ่าว
  2. *ฉากที่ 2 (ส่งของกู้ชีพ)*: พี่บ่าวส่งรูปสินค้าเข้ามาในแชทแก้ปัญหา
  3. *ฉากที่ 3 (พิสูจน์จุดขาย)*: สเปก 2-4 จุดเด่น โชว์การ์ดรูปสินค้าทีละมุม
  4. *ฉากที่ 4 (ผลลัพธ์ & ชี้เป้า)*: น้องนุ้ยขอสั่งซื้อ/ยึดของ พี่บ่าวปิดการขายชี้เป้าตะกร้าเหลือง

---

## 🎨 2. ช็อตปกและ CTA ตอนจบ (Brand & Model First Standard)
ออกแบบมาเป็นพิเศษเพื่อให้สามารถแคปเจอร์เป็น **ภาพปก TikTok 9:16 (Cover Thumbnail)** ได้ทันที โดดเด่น ชัดเจน ไม่รกตา

### 2.1 โครงสร้างเลย์เอาต์ (Visual Hierarchy) & กฎเหล็กห้ามล้นขอบ (Strict Zero-Overflow Guard)
1. **Header บรรทัดที่ 1 (เน้นแบรนด์และรุ่นอันดับแรก - ห้ามล้นขอบ 100%)**:
   - รหัส HTML: `<div class="t center" id="cta-1"><span class="hl">{แบรนด์} · {ชื่อรุ่น}</span></div>`
   - 🛑 **กฎเหล็กห้ามข้อความล้นขอบจอ (Strict Safe-Zone & Text Fitting Guard):**
     - ข้อความต้องอยู่ภายใน Safe Zone กว้างสูงสุด **960px** (เว้นขอบซ้าย-ขวาอย่างน้อย 60px)
     - ปรับขนาดฟอนต์ `Kanit Black` ตามความยาวตัวอักษร:
       - ชื่อสั้น (<= 16 ตัวอักษร เช่น `Essager · PD 30W`): ใช้ **`104px - 108px`**
       - ชื่อปานกลาง/ยาว (17–24 ตัวอักษร เช่น `HOYAUP · พัดลมแม่เหล็ก`): ปรับลงเป็น **`82px - 86px`**
       - ชื่อยาวมาก (> 24 ตัวอักษร): ปรับลงเป็น **`74px - 78px`**
     - แถบไฮไลต์สีเหลืองนีออน `#FFE600`, ขอบหมึกเข้ม `#1b1a17`, ตำแหน่ง `top: 230px`
     - **ผลลัพธ์:** ตัวหนังสือคมชัด ไม่ขาด ไม่ตกขอบจอ และอ่านง่ายบนฟีด TikTok ทันที
2. **Header บรรทัดที่ 2 (จุดขายและ Action)**:
   - รหัส HTML: `<div class="t center" id="cta-model">{จุดขายตัวจบ} · กดตะกร้าเหลือง</div>`
   - สไตล์: ฟอนต์ `Anuphan Bold` ขนาด **54px - 62px**, สีแดงสด `#d90429`, ตำแหน่ง `top: 385px`, ความกว้างสูงสุด 960px ไม่ชิดขอบ
3. **Hero Product (ภาพสินค้าเด่นตรงกลาง)**:
   - ใช้ภาพ **Transparent Clean Cutout PNG** (ขนาด 630x630px ไดคัทด้วย `rembg` เงาตกกระทบนุ่มลึก คมกริบ)
   - ❌ *ห้ามใช้ภาพสี่เหลี่ยมต้นฉบับที่มีขอบโปสเตอร์หรือกรอบสี่เหลี่ยมทึบเด็ดขาด*
4. **ป้ายสีและป้ายสเปก (Color & Spec Badges)**:
   - ป้ายสี: `[สีดำ]` `[สีขาว]` (พื้นขาว/ดำ ขอบหมึกดำ)
   - ป้ายสเปก: `[เซมิคอนดักเตอร์ 24W]` `[จอดิจิทัลบอกอุณหภูมิ]` `[เบาหวิว 83 กรัม]`
   - 🛑 **การจัดเรียงไม่ให้ล้นขอบ:** ป้ายสเปกต้องใส่ `flex-wrap: wrap; justify-content: center; max-width: 960px; gap: 10px;` ขนาดฟอนต์ **`26px - 28px`** ห้ามชิดหรือเลยขอบซ้ายขวาเด็ดขาด
   - ❌ **ห้ามใส่อีโมจิเด็ดขาด (Strict Zero-Emoji Guard):** ห้ามมี ⚡, ❄️, 🛡️, ⚪, 🔥, 🛒 เพื่อให้ดูเป็นมินิมอลพรีเมียม ไม่ดูเหมือน AI สแปม
5. **ลูกศรชี้ตะกร้าเหลือง (Minimal Curved Red Arrow)**:
   - เส้นลูกศร SVG สีแดงสด `#d90429` หนา 18px วาดเส้นโค้งกวาดลงมุมซ้ายล่างหาตำแหน่งปุ่มตะกร้าเหลือง TikTok
   - แอนิเมชัน GSAP Pulse ขยับเด้งเบาๆ (-18px, +18px)
   - ❌ **ถอดข้อความ "ซ้ายล่าง" ออก 100%**: ปล่อยพื้นที่ว่างให้ลูกศรทำหน้าที่ชี้นำสายตาอย่างสะอาดตา
6. **ตำแหน่งดึงภาพปก (Thumbnail Capture Seek)**:
   - คำนวณที่ `cta_start + 1.8s` (หรือ `cta_start + 2.0s`) ก่อนจบคลิป 0.5s เป็นจุดที่องค์ประกอบทุกชิ้นคลี่คลายสมบูรณ์แบบ

---

## 🎙️ 3. คู่มือการเจนเสียงพากย์ฉบับสมบูรณ์ (Master TTS & Audio Engineering Guide)

### 3.1 โมเดลและการยิง API (Dual TTS Engine: Gemini 3.8 Flash TTS)
- **โมเดลทางการ (Authoritative Dual TTS Engine)**: `gemini-3.8-flash-tts` (**Gemini 3.8 Flash TTS**)
- **โมเดลสำรอง (Fallback Engine)**: `gemini-2.5-flash-preview-tts` (กรณีระบบสำรอง)
- **กฎเหล็ก Single-Speaker 2 เทิร์น (Strict Single-Speaker Guard)**:
  - ❌ **ห้ามใช้ `multiSpeakerVoiceConfig`**: การยิงสคริปต์ยาว 10-16 เทิร์นในคอลเดียว จะทำให้โมเดลสลับเสียงชาย-หญิงกลางคลิป
  - ✅ **ต้องยิง Single-Speaker แยกคนละ 1 ครั้งรวดเดียว**:
    1. ครั้งที่ 1: เจนเฉพาะบทของฝ่ายหญิง (น้องนุ้ย) บันทึกเป็น `take_F.wav`
    2. ครั้งที่ 2: เจนเฉพาะบทของฝ่ายชาย (พี่บ่าว) บันทึกเป็น `take_M.wav`
  - คั่นระหว่างแต่ละท่อนด้วย `... ...` (เว้นวรรค 1.5 - 2.0 วินาที) เพื่อให้ตัดแบ่งเทิร์นตามช่วงเงียบได้แม่นยำ 100%

### 3.2 กฎเหล็กคุมโทนเสียงคงที่ 100% (Strict Monolithic Acting & Zero-Tone-Drift Guard)
โมเดล Multimodal TTS มักจะแอบเปลี่ยนโทนเมื่อเนื้อหาเปลี่ยน (เช่น พูดเรื่องสเปกจะเปลี่ยนเป็นเสียงสุขุม) จึงต้องคุมด้วย Prompt Guard:
- **ฝ่ายชาย (พี่บ่าว - Puck)**:
  - บุคลิก: หนุ่มบ้านๆ คนซื่อ ตกใจฮาๆ อารมณ์ดี กวนๆ
  - 🛑 **Strict No-Seriousness Guard**: ห้ามเปลี่ยนเป็นเสียงสุขุม เก๊กหล่อ หรือวิชาการเด็ดขาด แม้จะอ่านสเปกวัตต์ ชิป หรือราคา
  - ❌ ห้ามมีคำว่า `Calm`, `Serious`, `Professional`, `Formal` ใน Prompt
- **ฝ่ายหญิง (น้องนุ้ย - Aoede)**:
  - บุคลิก: สาวใต้เสียงใส น่ารักแต่ดุ แก่นเซี้ยว ขี้บ่นกวนๆ จังหวะฉะฉาน ชัดถ้อยชัดคำ
  - 🛑 **Strict Sassy & Vibrant Consistency**: ห้ามเปลี่ยนเป็นเสียงหวานนุ่มเรียบร้อย หรือเสียงโมโนโทนประชาสัมพันธ์
  - ❌ ห้ามมีคำว่า `Calm`, `Soft`, `Sweet`, `Formal`, `Monotone` ใน Prompt
- **Master Prompt Template**:
```text
[Voice style: {F_STYLE หรือ M_STYLE}
Pronunciation rule: Speak clear, lively, natural Thai with Southern Thai couple charm ("พี่บ่าว" and "น้องนุ้ย").
Strict Acting Rule: Keep the EXACT SAME voice, pitch, energy, pacing, and personality from the first word to the very last word.
DO NOT adapt or switch your acting tone to serious, calm, monotonous, or professional when reading product specs, features, or prices.
Speak with consistent comedy couple banter and lively energy throughout the entire take.
Between each section where you see '... ...' leave a clear 2 second silence.]
```

### 3.3 การประมวลผลเสียงด้วย FFmpeg (Audio Filters & Pitch/Speed Calibration)
- **น้องนุ้ย (Aoede)**:
  ```bash
  ffmpeg -i take_F_raw.wav -af "asetrate=24000*1.10,aresample=48000,atempo=1.20,highpass=f=140,equalizer=f=3500:t=q:w=1.2:g=3.0" take_F.wav
  ```
  - `asetrate*1.10`: ยกคีย์เสียงแหลมขึ้น 10% ให้เสียงใส อ่อนเยาว์
  - `atempo=1.20`: เร่งจังหวะการพูด 20% ให้กระฉับกระเฉง ฉะฉาน
  - `equalizer`: เสริมความคมชัดของเสียงพยัญชนะที่ 3.5 kHz
- **พี่บ่าว (Puck)**:
  ```bash
  ffmpeg -i take_M_raw.wav -af "atempo=1.32,highpass=f=95" take_M.wav
  ```
  - `atempo=1.32`: เร่งจังหวะพูด 32% โดยรักษา Pitch ทุ้มเดิมของเสียงผู้ชาย พูดรวดเร็ว กวนๆ ขี้ตกใจ
  - `highpass=f=95`: ตัดย่านหึ่งและเสียงลมต่ำกว่า 95 Hz

### 3.4 การตัดแบ่งเทิร์นและการจัดเรียง (Turn Segmentation)
1. ใช้ฟังก์ชัน `split_by_longest_gaps` ค้นหาจุดที่มี Amplitude ต่ำสุดเป็นระยะเวลา > 0.4s เพื่อตัดแบ่งออกเป็น N เทิร์น
2. ตรวจทานความถูกต้องของคำพูดและบันทึกช่วงเวลาด้วย `faster_whisper` (โมเดล `large-v3-turbo`)
3. นำเทิร์นของน้องนุ้ยและพี่บ่าวมาประกอบสลับกัน (Interleave) ลงในแทร็ก `vo.wav`

### 3.5 การขจัดเสียงซ่าและเสียงช็อตท้ายคลิป (Audio Sanitization & Zero Tail Glitch)
1. **ขจัดขยะ White Noise ระหว่างเทิร์น**:
   - ปลายไฟล์ดิบของ Gemini Flash TTS มักมีขยะ Digital Glitch 100-150ms (Amplitude 19,000–32,768) ติดมาที่ท้ายประโยค
   - ต้องรัน `clean_all_inter_turn_audio_glitches.py` ตรวจจับ Silence Gaps ระหว่างเทิร์น และทำ Zeroing ขยะเสียงด้วย Cosine Crossfade 5ms ขจัดเสียงซ่า 100%
2. **Smooth Cosine Tail Fade-out**:
   - ในช่วง 120ms สุดท้ายของ `vo.wav` ต้องใส่ Fade-out สู่ค่า 0 ป้องกันอาการไฟช็อตและ DC Offset Pop
3. **การมิกซ์เสียงและ Headroom**:
   - ระดับเสียง SFX: `whoosh.mp3` = 0.18, `boom.wav` = 0.15, `cash_register.mp3` = 0.20, `paper.mp3` = 0.40
   - ระดับเสียง Voice: 1.0 (Normalize ด้วย FFmpeg loudnorm ที่ `-16 LUFS`)
   - BGM: Lo-fi Upbeat 0.05 พร้อม Voiceover Ducking/Carve

### 3.6 กลยุทธ์การยิงและบริหารโควตา API (TTS Request Strategy & Quota Management)

#### 1. ความแตกต่างของ 2 สถาปัตยกรรมการยิง (Execution Strategies):
- **กลยุทธ์ A: Single-Take 2 Passes (ประหยัดโควตาสูงสุด — 2 Requests/คลิป)**
  - *วิธีทำงาน:* ฝ่ายหญิงยิง 1 Request ยาวรวดเดียว (`take_F.wav`) และฝ่ายชายยิง 1 Request ยาวรวดเดียว (`take_M.wav`) คั่นแต่ละช่วงด้วย `... ...` (2.0s) แล้วหั่นด้วย `split_by_longest_gaps`
  - *ข้อดี:* ประหยัดโควตาที่สุด ผลิตคลิป 20 คลิปใช้เพียง **40 Requests** (คีย์เดียวก็เอาอยู่)
  - *ข้อควรระวัง:* ต้องระวังเรื่อง Preamble Hallucination (AI ด้นสดบทนำ) หรือ Silence Gap ไม่ขาดช่วง
- **กลยุทธ์ B: Isolated Turn-by-Turn (แม่นยำ 100% ไร้เสียงหลอน — 12-14 Requests/คลิป)**
  - *วิธีทำงาน:* ยิงเจนแยกทีละประโยคเดี่ยว 1 Turn = 1 Request ผูกกับหมายเลขเทิร์น 1:1 พร้อม Prompt Guard กำกับห้ามทักทายและตรวจทานด้วย Whisper
  - *ข้อดี:* ปราศจากเสียงพูดนอกบท 100%, ซับไตเติลตรงเป๊ะ 100%, ไม่มีเทิร์นเหลื่อม
  - *ข้อควรระวัง:* ใช้โควตาสูง 12–14 Requests ต่อ 1 คลิป (ทำ 20 คลิปต้องใช้ ~260–280 Requests) จึงต้องมี **Multi-Key Rotation (คีย์หมุนเวียนอย่างน้อย 6–8 บัญชี)**

#### 2. ข้อจำกัดของ Free Tier Quota & วงจรการรีเซ็ต (Reset Timing):
- **โควตารายวัน (RPD - Requests Per Day):**
  - โมเดลเสียงพากย์ (Multimodal / Flash TTS Preview) บน Free Tier มีเพดานจำกัดอยู่ที่ประมาณ **50 Requests/วัน ต่อ 1 API Key** (ต่างจากโมเดล Text ทั่วไปที่ได้ 1,500 RPD)
  - **เวลารีเซ็ต:** รีเซ็ตทุกวันตอน **00:00 เที่ยงคืนเวลาแปซิฟิก (Pacific Time - PT)** ➔ **14:00 น. (บ่าย 2 โมงตรง เวลาไทย)**
- **โควตารายนาที (RPM - Requests Per Minute):**
  - จำกัดอยู่ที่ **15 RPM** (ไม่ควรยิงถี่เกิน 15 ครั้งใน 1 นาที)
  - **เวลารีเซ็ต:** เป็น Rolling Window คลายตัวและกลับมาพร้อมใช้งานภายใน **1–2 นาที**
- **การแยกแยะ 429 vs 503:**
  - `429 RESOURCE_EXHAUSTED`: โควตาของคีย์นั้นหมดจริง (รอรีเซ็ต 14:00 น. หรือสลับไปใช้คีย์อื่น)
  - `503 UNAVAILABLE ("high demand")`: เซิร์ฟเวอร์ของ Google โหลดแน่นชั่วคราวทั่วโลก ไม่ใช่คีย์หมด ให้รอ 5–15 วินาทีแล้วลองใหม่ ห้ามทิ้งคีย์นั้น

---

## ☀️ 4. มาตรฐานความสว่างผิวกระดาษและวิดีโอ (Paper Luminance Standard: Y = 220–225)

### 4.1 ระดับความสว่างมาตรฐาน (Scientific Luminance Metric)
- **ค่าความสว่างเป้าหมาย (Frame 0 Luminance Y)**: **`220.0 – 225.0`**
- **ค่าสีมุมขอบกระดาษ (RGB Corner Pixel)**: `[233, 230, 224]` ถึง `[236, 233, 227]` (สีครีมกระดาษนวลตา สดใสเป็นธรรมชาติ)
- **ทำไมต้อง 220–225**:
  - $Y < 210$: มืดทึบ หม่นหมอง กล่องแชทสีขาวดูเทา ไม่ดึงดูดสายตาบนฟีด
  - $Y > 230$: สว่างจ้าเกินไป แสบตา สีขาวของกล่องแชทกลืนหายไปกับพื้นกระดาษ ขาดคอนทราสต์
  - $Y \in [220, 225]$: จุดสมดุลสูงสุด (Golden Balance) — ตัวหนังสือดำคมกริบ กล่องข้อความขาว/เขียวอ่านง่าย ผิวกระดาษมีเท็กซ์เจอร์ชัดเจน

### 4.2 กฎการตั้งค่าและการประมวลผล (Encoding & Enhancement Pipeline)
1. **ใน Composition HTML**:
   - พื้นหลัง `#paper`: ใช้วิดีโอ `assets/shared/paper_bg.mp4` ปกติ (ไม่ใส่ฟิลเตอร์เร่งจนขาวจ้า)
   - ❌ **ห้ามใส่ `<div id="paper-tint">` (Vignette มืด 22%) เด็ดขาด**
2. **ใน TikTok Pro Sharpness Engine (`scripts/tiktok_enhancer.py`)**:
   - พารามิเตอร์ `eq` ผ่าน FFmpeg ปรับเทียบให้ Frame 0 Y ลงล็อกที่ 220–225
3. **การตรวจสอบด้วยคอมพิวเตอร์ (Verification Command)**:
   ```python
   import cv2, numpy as np
   cap = cv2.VideoCapture("output.mp4")
   ret, f0 = cap.read()
   y0 = np.mean(cv2.cvtColor(f0, cv2.COLOR_BGR2YCrCb)[:, :, 0])
   assert 220.0 <= y0 <= 225.5, f"Luminance Y {y0:.2f} out of target range [220, 225]"
   ```

