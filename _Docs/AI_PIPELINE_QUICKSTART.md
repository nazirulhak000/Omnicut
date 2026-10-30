# ⚡ OmniCut Pro Studio: AI Production Pipeline Quickstart
> **คู่มือสรุปย่อกระชับพิเศษสำหรับส่งต่อ AI (Claude Code, Cursor, Gemini, ChatGPT)**  
> คัดลอกเนื้อหาไฟล์นี้ทั้งไฟล์ส่งให้ AI อ่าน เพื่อเริ่มผลิตคลิปใหม่หรือทำต่องานในระบบได้ทันที 100% ถูกต้องตามกฎทุกข้อ
---

## ⚡ 0. คำสั่งสั่งงาน AI จบในคลิกเดียว (Master All-In-One Prompt)
> **คัดลอกข้อความในกล่องนี้ไปส่งสั่ง AI (Antigravity, Claude Code, Cursor) ผลิตคลิปได้รวดเดียวจบ 100%:**

```text
[คำสั่งปฏิบัติการ OmniCut AI Production Pipeline แบบ End-to-End รวดเดียวจบ]
ผลิตคลิปสำหรับสินค้า: [ใส่ชื่อสินค้า / สเปก / โฟลเดอร์ใน 01_Raw/]

🛑 กฎเหล็กก่อนเริ่มงาน (Mandatory Skill & Rule Compliance):
เปิดอ่านและยึดถือมาตรฐานจาก 2 เอกสารอ้างอิงนี้อย่างเคร่งครัดทุกขั้นตอน ห้ามหลุดสไตล์เด็ดขาด:
1. .agents/skills/hyperframes-creative/references/thai-couple-paper-chat.md
2. .agents/rules/pov_couple_line_chat_standard.md

ดำเนินการอัตโนมัติรวดเดียวจบตามขั้นตอนดังนี้:
1. [Script]: วางสคริปต์สไตล์คู่รักใต้ Drama-to-Commerce (40-50 วินาที, 12-16 เทิร์น, ห้ามมีจุดไข่ปลา "..." ในบทพูดเด็ดขาด)
2. [TTS Audio]: สังเคราะห์เสียง Gemini 3.8 Flash (gemini-3.8-flash-tts) แยก Single-Speaker 2 รอบ:
   - หญิง (น้องนุ้ย): เสียง Aoede สไตล์สาวใต้ใส แก่นเซี้ยว น่ารักแต่ดุ + FFmpeg: asetrate=24000*1.10,aresample=48000,atempo=1.20,highpass=f=140,equalizer=f=3500:t=q:w=1.2:g=3.0
   - ชาย (พี่บ่าว): เสียง Puck สไตล์หนุ่มบ้านๆ ซื่อๆ ตกใจฮาๆ (ห้ามใส่คำว่า Calm/Serious/Formal เด็ดขาด) + FFmpeg: atempo=1.32,highpass=f=95
   - บังคับ Monolithic Acting Guard คุมพลังเสียงคงที่ 100% จากคำแรกถึงคำสุดท้าย
3. [Whisper & Sanitization]: ถอดคำด้วย Faster-Whisper, คลีนขยะ Digital Glitch ระหว่างเทิร์นด้วย Cosine Crossfade 5ms, และใส่ Smooth Cosine Tail Fade-out 120ms ท้ายคลิป vo.wav เงียบสนิท
4. [Draft Build]: ลงทะเบียน _Docs/products.json และสร้างดราฟต์ HyperFrames สไตล์ Couple Paper Chat #5 พร้อมช็อต CTA แบบ Brand & Model First (หัวข้อแบรนด์-รุ่น 108px ไฮไลต์เหลือง + สินค้าไดคัท 630px ไร้อีโมจิ + ลูกศรแดงโค้ง)
5. [Render]: เรนเดอร์ไฟล์วิดีโอ MP4 1080x1920 30fps
6. [TikTok Pro Sharpness]: นำคลิปที่เรนเดอร์ได้มารันผ่าน python scripts/tiktok_enhancer.py [render.mp4] 04_Exports/Ready_to_post/[output_v1.mp4] เพื่อใส่ Unsharp Mask พรีเซ็ตพิเศษ ปรับแต่งสี BT.709 Primaries และฟิกซ์ Keyframe 2s ให้คลิปคมชัดที่สุดบน TikTok
7. [Auto CTA Cover]: สกัดภาพปก WebP 540x960 อัตโนมัติจากช็อต CTA ท้ายคลิปที่จุดเวลา cta_start + 1.8s เซฟลง 05_Covers_Thumbnails/
8. [Sync & Archive]: บันทึกลง _Docs/export_registry.json, อัปเดตสถานะใน _Docs/products.json เป็น "rendered" พร้อมใส่ video_url และ cover_url, จากนั้นเคลียร์คลัง Studio ด้วย manage_archive.py archive และ archive-clip ให้เรียบร้อย 100%
```

---

## 🎯 1. ภาพรวมระบบ & สเปกวิดีโอ (System Specs)
- **อัตราส่วน:** แนวตั้ง 9:16 (`1080x1920`, 30 FPS, H.264)
- **สไตล์หลัก (#5):** `Couple Paper Chat` — ละครสั้นคู่รักสายใต้ (**น้องนุ้ย & พี่บ่าว**) โบ๊ะบ๊ะดราม่าป้ายยา บนพื้นหลังกระดาษยับ `assets/shared/paper_bg.mp4` เล่นช้าครึ่งสปีด (`data-playback-rate="0.5"`)
- **Safe Zone ด้านล่าง:** `420px` ห้ามมีปุ่ม แชท หรือข้อความสำคัญ (ป้องกันปุ่มและแคปชัน TikTok บัง)
- **สแต็กเทคโนโลยี:** HyperFrames Studio (`03_Projects/_HyperFrames_Studio/`), Python 3.12 (`.venv`), FFmpeg, Gemini Flash TTS, Faster-Whisper, SQLite/JSON Tracker

---

## 🔄 2. ลูปการทำงาน 5 สเตจ (The 5-Stage Execution Loop)

```
[Stage 1: สคริปต์ & เสียง] ➔ [Stage 2: Tracker & Draft] ➔ [Stage 3: พรีวิว & เรนเดอร์] ➔ [Stage 4: ปก & Archive] ➔ [Stage 5: คิวโพสต์]
```

### 🟢 Stage 1: สกัดสเปก ➔ สคริปต์ Micro-Burst ➔ เจนเสียงคู่รักสายใต้
1. **สคริปต์ Drama-to-Commerce (40–50 วินาที, 12–16 เทิร์น):**
   - เรียบเรียงเป็นคำสั้นกระชับแบบ Micro-burst (2–4 คำต่อช่วง)
   - ❌ **ห้ามใส่จุดไข่ปลา ("...", "…") ในบทพูดเด็ดขาด** (ให้ใช้เว้นวรรคธรรมชาติ)
2. **เจนเสียง Gemini 3.8 Flash TTS (`gemini-3.8-flash-tts`, สำรอง `gemini-2.5-flash-preview-tts`) แยก Single-Speaker 2 ครั้งรวดเดียว (ห้ามใช้ multiSpeaker):**
   - **ครั้งที่ 1 (น้องนุ้ย):** เจนบทฝ่ายหญิง ใช้เสียง `Aoede` บันทึกเป็น `take_F.wav`
   - **ครั้งที่ 2 (พี่บ่าว):** เจนบทฝ่ายชาย ใช้เสียง `Puck` บันทึกเป็น `take_M.wav`
   - คั่นระหว่างแต่ละท่อนด้วย `... ...` (เว้น 2 วินาที) เพื่อตัดแบ่งเทิร์นตามช่วงเงียบ
3. **กำกับโทนเสียงคงที่ 100% (Strict Monolithic Acting & Zero-Tone-Drift Guard):**
   - **พี่บ่าว (Puck):** หนุ่มใต้ซื่อๆ ตกใจฮาๆ อารมณ์ดี กวนๆ 🛑 **ห้ามเปลี่ยนเป็นเสียงสุขุม เก๊กหล่อ วิชาการเด็ดขาด** แม้จะอ่านสเปกวัตต์ ชิป หรือราคา (ห้ามมีคำว่า `Calm`, `Serious`, `Professional`, `Formal` ใน Prompt)
   - **น้องนุ้ย (Aoede):** สาวใต้เสียงใส น่ารักแต่ดุ แก่นเซี้ยว ขี้บ่นกวนๆ ฉะฉาน 🛑 **ห้ามเปลี่ยนเป็นเสียงหวานนุ่มเรียบร้อย หรือโมโนโทนเด็ดขาด** (ห้ามมีคำว่า `Calm`, `Soft`, `Sweet`, `Formal`, `Monotone` ใน Prompt)
4. **ประมวลผลเสียงด้วย FFmpeg Audio Filters:**
   ```bash
   # น้องนุ้ย (ยกคีย์แหลม 10% + เร่งสปีด 20% + เสริม EQ 3.5kHz)
   ffmpeg -i take_F_raw.wav -af "asetrate=24000*1.10,aresample=48000,atempo=1.20,highpass=f=140,equalizer=f=3500:t=q:w=1.2:g=3.0" take_F.wav

   # พี่บ่าว (เร่งสปีด 32% คีย์ทุ้มเดิม + ตัดย่านลมต่ำกว่า 95Hz)
   ffmpeg -i take_M_raw.wav -af "atempo=1.32,highpass=f=95" take_M.wav
   ```
5. **ตัดแบ่งเทิร์น & สแกนคำ:**
   - ตัดแบ่งเทิร์นตามช่วงเงียบด้วย `split_by_longest_gaps` และสแกนถอดคำจริงด้วย `faster_whisper` (`large-v3-turbo`)
   - รวมเป็นแทร็กหลัก `vo.wav`
6. **คลีนเสียงซ่า & เสียงช็อต 100% (Audio Sanitization):**
   - สแกน Silence Gaps ระหว่างเทิร์นใน `vo.wav` และ Zeroing ขยะ Digital Glitch (Amplitude > 15,000) ของ Flash TTS ด้วย Cosine Crossfade 5ms
   - ใส่ Smooth Cosine Tail Fade-out 120ms ช่วงท้ายคลิป `vo.wav` สู่ค่า 0 เงียบสนิท ไร้เสียงช็อต

---

### 🔵 Stage 2: ลงทะเบียน Content Tracker & ประกอบ HyperFrames Draft
1. **บันทึกลง `_Docs/products.json`:**
   - สร้าง `product_id` (`uuid4().hex` 32 หลัก) และ `product_code` (เช่น `ESS02`, `HOY01`)
   - สร้าง `angle_id` (`f"ang_{uuid4().hex[:8]}"`) ตั้งสถานะ `draft_ready`
2. **สร้างดราฟต์ใน `03_Projects/_HyperFrames_Studio/`:**
   - โค้ดคอมไพล์: `clips/{slug}/build.py` ➔ คอมไพล์เป็น `compositions/{slug}.html`
   - แบ็กกราวด์: วิดีโอกระดาษยับ `assets/shared/paper_bg.mp4` (`data-playback-rate="0.5"`)
   - กล่องแชท: ซ้าย = น้องนุ้ย (อวตารชมพู `"น"`, แชทขาว `#ffffff`), ขวา = พี่บ่าว (อวตารฟ้า `"บ"`, แชทเขียว LINE `#8de07a`)
3. **เลย์เอาต์ช็อต CTA ท้ายคลิป (Brand & Model First Standard):**
   - **Header บรรทัด 1 (เด่นที่สุด):** `<span class="hl">{แบรนด์} · {ชื่อรุ่น}</span>` (ฟอนต์ `Kanit Black` 108px ไฮไลต์เหลือง `#FFE600`, ขอบหมึกเข้ม `#1b1a17`, `top: 230px`)
   - **Header บรรทัด 2:** `{จุดขายตัวจบ} · กดตะกร้าเหลือง` (ฟอนต์ `Anuphan Bold` 62px, สีแดงสด `#d90429`, `top: 385px`)
   - **Hero Product:** รูปไดคัทโปร่งใส Clean Cutout PNG ขนาด 630x630px ขอบเนียน คมกริบ ❌ *ห้ามใช้ภาพโปสเตอร์มีกรอบสี่เหลี่ยมทึบ*
   - **ป้ายสี & ป้ายสเปก:** มินิมอลการ์ด ตัวหนังสือดำเข้ม ❌ **ห้ามใส่อีโมจิเด็ดขาด (Strict Zero-Emoji Guard)** (ห้ามมี ⚡, ❄️, 🛡️, ⚪)
   - **ลูกศรชี้ตะกร้า:** เส้น SVG แดงสดโค้งหนา 18px ชี้ลงมุมซ้ายล่าง ❌ **ถอดข้อความ "ซ้ายล่าง" ออก 100%** ให้ภาพสะอาดตา

---

### 🟣 Stage 3: พรีวิวสดบนเว็บ & สั่งเรนเดอร์ MP4 พร้อม TikTok Sharpness Enhancement
1. **เปิดดูพรีวิว:**
   - เข้าเว็บ: `http://localhost:3002/#project/_HyperFrames_Studio/composition/{slug}`
   - ตรวจการเด้งการ์ดสินค้า, จังหวะซับ, ข้อความ และเลย์เอาต์ CTA
2. **เรนเดอร์ 2 จังหวะ (HyperFrames CLI v0.8.149 ➔ TikTok Pro Sharpness):**
   ```bash
   # 1. เรนเดอร์ Headless MP4 1080x1920 30fps
   npx --yes hyperframes@0.8.149 render . -c compositions/{slug}.html -o renders/{slug}.mp4

   # 2. ปรับแต่งความคมชัดระดับโปรสำหรับ TikTok (Unsharp Mask + BT.709 Primaries + 2s Keyframe)
   python scripts/tiktok_enhancer.py renders/{slug}.mp4 04_Exports/Ready_to_post/YYYYMMDD_{product_code}_{hook}_v1.mp4
   ```

---

### 🟠 Stage 4: สกัดภาพปก WebP อัตโนมัติ (Auto CTA Cover) ➔ ลงทะเบียน Export ➔ เคลียร์คลัง Studio
1. **สกัดภาพปก TikTok 9:16 อัตโนมัติ (Cover Thumbnail):**
   - ดึงเฟรมจากช็อต CTA ท้ายคลิปที่เวลา `cta_start + 1.8s` (หรือ `duration - 0.5s`) ซึ่งแสดงแบรนด์และรุ่นเด่นชัดเจน
   - บันทึกเป็น WebP ขนาด 540x960: `05_Covers_Thumbnails/YYYYMMDD_{product_code}_{hook}_cover.webp`
2. **ลงทะเบียน Export Identity ใน `_Docs/export_registry.json`:**
   - สร้างรหัส `export_id` (`exp_{uuid4().hex}`) ผูกโยง `export_id` ➔ `product_id` ➔ `angle_id` ➔ ไฟล์ MP4 และปก WebP
   - อัปเดตสถานะมุมมองใน `_Docs/products.json` เป็น **`rendered`** พร้อมระบุ `video_url` และ `cover_url`
3. **เคลียร์พื้นที่หน้า Studio ให้คลีน 100% (Studio Archiving):**
   ```bash
   # ย้าย composition html และ โฟลเดอร์ clip เข้า 06_Archive/HyperFrames_Studio/
   python 03_Projects/_HyperFrames_Studio/manage_archive.py archive {slug}
   python 03_Projects/_HyperFrames_Studio/manage_archive.py archive-clip {slug}
   ```

---

### 🟢 Stage 5: จัดคิวโพสต์ & โพสต์ผ่าน TikTok Extension
1. **เพิ่มงานลง `_Docs/schedule_queue.json`:**
   - สร้างรหัส `job_id` (`job_{uuid4().hex[:16]}`) กำหนดเวลาช่วง Prime-Time (11:30, 18:00, หรือ 20:30 น.)
2. **Account Guard Check:**
   - ส่วนขยาย TikTok Extension จะตรวจสอบว่าบัญชีที่ล็อกอินตรงกับ `channel_id` 100% ก่อนเริ่มอัปโหลด ป้องกันโพสต์ผิดช่อง
   - เมื่อโพสต์สำเร็จ ปรับสถานะใน Content Tracker เป็น **`posted`** 100%

---

## 📋 3. สรุปพจนานุกรมรหัสและชื่อไฟล์ (ID & Naming Standards)

| รายการ | รูปแบบมาตรฐาน (Format) | ตัวอย่างจริง |
| :--- | :--- | :--- |
| **`product_id`** | 32 ตัวอักษร Hex (ไม่มียัติภังค์) | `c6218d6bf94e43db825eef50cb25aa17` |
| **`product_code`** | ตัวอักษรพิมพ์ใหญ่ 3-5 ตัว + เลข 2 หลัก | `ESS02`, `ORS01`, `HOY01` |
| **`angle_id`** | `ang_` + 8 ตัวอักษร Hex | `ang_e8f2a1b0` |
| **`export_id`** | `exp_` + 32 ตัวอักษร Hex | `exp_a1b2c3d4e5f678901234567890abcdef` |
| **`job_id`** | `job_` + 16 ตัวอักษร Hex | `job_582ab38e104f129a` |
| **Export MP4** | `YYYYMMDD_{PRODUCT}_{HOOK}_vN.mp4` | `20261013_ess02-pov-s01_v1.mp4` |
| **Cover WebP** | `YYYYMMDD_{PRODUCT}_{HOOK}_cover.webp` | `20261013_ess02-pov-s01_cover.webp` |

---

## ⛔ 4. กฎเหล็กข้อห้ามเด็ดขาด (Strict Don'ts)

1. ❌ **ห้ามใส่จุดไข่ปลา ("...", "…") ในบทพูดเด็ดขาด** (เสียงเพี้ยนและหลุดเข้าซับ)
2. ❌ **ห้ามใช้คลิปที่มีซับจีนหรือภาษาต่างชาติฝังในเนื้อวิดีโอ (Hardcoded Subtitles)**
3. ❌ **ห้ามใส่อีโมจิในการ์ด CTA ตอนท้ายเด็ดขาด** (ห้ามมี ⚡, ❄️, 🛡️, ⚪)
4. ❌ **ห้ามใส่ข้อความ "ซ้ายล่าง" ติดกับลูกศร** (ใช้ลูกศรแดงโค้งเพียวๆ มินิมอล)
5. ❌ **ห้ามโมเดล TTS สลับบุคลิกเสียงกลางคัน** (ชายห้ามสุขุมวิชาการ หญิงห้ามหวานนุ่มโมโนโทน)
6. ❌ **ห้ามปล่อยให้มีเสียงซ่า Digital Noise ค้างระหว่างเทิร์น หรือเสียงช็อตท้ายคลิป vo.wav**
7. ❌ **ห้ามทิ้งดราฟต์ที่เรนเดอร์แล้วค้างใน Studio** (ต้องสั่ง archive ย้ายเข้า `06_Archive/` ทุกครั้ง)
8. ❌ **ห้ามลบ/เขียนทับวัตถุดิบใน `01_Raw/` และ `02_Assets/` โดยไม่ยืนยันจาก User**
