# 📖 คู่มือปฏิบัติงานมาตรฐาน: โฟลว์ผลิตคลิป AI รวมศูนย์แบบไร้รอยต่อ
# (Standard Operating Procedure: Unified AI Production Pipeline SOP)

> **เอกสารควบคุมฉบับหลัก (Master Reference):** รวบรวมขั้นตอน กฎการตั้งชื่อ รูปแบบ UUID รหัสอ้างอิง และลูปการทำงานตั้งแต่ต้นน้ำถึงปลายน้ำ (End-to-End) เพื่อให้ทั้ง User และ AI ทุกตัว (Antigravity, Codex, Claude Code) ทำงานสอดคล้องกัน 100% ไม่มีหลุดสเปก  
> **ดำเนินการโดย:** Antigravity (Gemini 3.8 Flash High)  
> **ปรับปรุงล่าสุด:** 2026-10-12  
> **ไฟล์แผนผัง Interactive:** [_Docs/AI_PIPELINE_FLOW.html](AI_PIPELINE_FLOW.html) (หรือ [UNIFIED_AI_PRODUCTION_PIPELINE_FLOW.html](UNIFIED_AI_PRODUCTION_PIPELINE_FLOW.html))

---

## 📌 1. ภาพรวมของลูปการผลิต (The 5-Stage Unified Loop)

OmniCut Pro Studio รวมศูนย์การผลิตคลิปจาก 5 หน้าจอเดิมให้กลายเป็นลูปเดียว โดยคงความถูกต้องของฐานข้อมูล สถานะใน Content Tracker และความสมบูรณ์ของไฟล์วิดีโอ 1080x1920 (9:16):

```
[Stage 1: Ingest & Voice]    URL/ข้อมูลสินค้า ➔ AI สกัดสเปก ➔ เจนสคริปต์ ➔ เจนเสียง TTS + Whisper Alignment
            ↓
[Stage 2: Tracker & Draft]   ลงทะเบียน ProductStore (products.json) ➔ ประกอบ HyperFrames Draft (index.html)
            ↓
[Stage 3: Preview & Render]  เปิด Studio Preview (http://localhost:3002) ➔ อนุมัติ ➔ 1-Click Render MP4
            ↓
[Stage 4: Packaging & Binding] ส่งเข้า 04_Exports/Ready_to_post/ ➔ ลงทะเบียน export_registry ➔ ผูกภาพปก Cover
            ↓
[Stage 5: Schedule & Publish]  เข้าคิว schedule_queue.json ➔ TikTok Extension โพสต์พร้อม Account Guard
```

---

## 🔑 2. กฎเหล็กพจนานุกรมรหัสและระบบการตั้งชื่อ (ID & Naming Conventions)

ทุกขั้นตอนที่สร้างไฟล์หรือเรคอร์ดใหม่ในฐานข้อมูล **ต้องใช้รูปแบบรหัสและชื่อไฟล์ตามกฎนี้เท่านั้น ห้ามสร้างรูปแบบอื่นโดยพลการ**:

### 2.1 รหัสระบุตัวตน (Identity & UUID Standards)

| ตัวแปร / ฟิลด์ | รูปแบบมาตรฐาน (Format) | ตัวอย่างจริง | ฟังก์ชันที่ใช้เจน |
| :--- | :--- | :--- | :--- |
| **`product_id`** | 32 ตัวอักษร Hex (ไม่มียัติภังค์) | `c6218d6bf94e43db825eef50cb25aa17` | `uuid.uuid4().hex` |
| **`product_code`** | ตัวอักษรพิมพ์ใหญ่ 3-5 ตัว + เลข 2 หลัก | `ORS01`, `ESS02`, `GOC01`, `HAT01` | `ProductStore._generate_product_code(name)` |
| **`angle_id`** | `ang_` + 8 ตัวอักษร Hex (+ `_bN` หากเป็นแบทช์ถัดไป) | `ang_e8f2a1b0`, `ang_3d4f8a12_b2` | `f"ang_{uuid.uuid4().hex[:8]}"` |
| **`export_id`** | `exp_` + 32 ตัวอักษร Hex | `exp_a1b2c3d4e5f678901234567890abcdef` | `f"exp_{uuid.uuid4().hex}"` |
| **`job_id`** | `job_` + 16 ตัวอักษร Hex | `job_582ab38e104f129a` | `f"job_{uuid.uuid4().hex[:16]}"` |
| **`channel_id`** | สตริงระบุชื่อช่อง (ค่าเริ่มต้น `main`) | `main`, `tech_gadget_th` | กำหนดจาก Context ช่องที่เลือก |

---

### 2.2 กฎการตั้งชื่อไฟล์และโฟลเดอร์ (File & Directory Naming Rules)

| รายการ | โครงสร้างชื่อมาตรฐาน | ตัวอย่าง | โฟลเดอร์จัดเก็บ |
| :--- | :--- | :--- | :--- |
| **Composition Slug** | `{product_code_lower}-{format}-{slug}` | `ors01-pov2-fire`<br>`ess02-asmr-26s` | `03_Projects/_HyperFrames_Studio/compositions/{slug}.html` |
| **Clip Workspace** | ตรงกับ Composition Slug | `ors01-pov2-fire` | `03_Projects/_HyperFrames_Studio/clips/{slug}/` |
| **Voiced Audio** | `vo.wav` (48kHz Stereo) | `vo.wav` | `03_Projects/_HyperFrames_Studio/assets/clips/{slug}/vo.wav` |
| **Export MP4** | `YYYYMMDD_{PRODUCT_CODE}_{HOOK}_vN.mp4` | `20261012_OrsenS6_240W_battery_1pct_fire_v1.mp4` | `04_Exports/Ready_to_post/` |
| **Cover Thumbnail** | `YYYYMMDD_{PRODUCT_CODE}_{HOOK}_cover.webp` | `20261012_OrsenS6_240W_cover.webp` | `05_Covers_Thumbnails/` |

---

## 🛠️ 3. ขั้นตอนปฏิบัติงาน 5 สเตจอย่างละเอียด (Step-by-Step SOP)

### 🟢 Stage 1: Ingest & Voice Generation (สกัดข้อมูล + สคริปต์ + เสียงพากย์)
1. **ดึงข้อมูลสินค้า (Product Ingestion)**:
   - นำเข้า URL TikTok Shop หรือ Shopee ผ่าน `scripts/product_scraper.py`
   - สกัดชื่อสินค้า, ราคา, สเปกสำคัญ, รูปภาพทางการ High-Res (เซฟลง `03_Projects/_HyperFrames_Studio/assets/{product_code_lower}/img/`)
2. **สร้างมุมมองและสคริปต์ (Angles & Script Formulation)**:
   - สรุปปัญหาหลัก (Pain Point) และจุดขาย (Selling Point)
   - ยกร่างสคริปต์ความยาว 40–60 วินาที โดยจัดคำเป็น **Micro-Burst Clusters** (2–4 คำต่อช่วง)
   - ❌ **ห้ามใส่จุดไข่ปลา ("...", "…") ในบทพูดเด็ดขาด** (ป้องกันหลุดเข้าซับและเพี้ยนในการสังเคราะห์เสียง)
3. **สังเคราะห์เสียงพากย์ (Voice Synthesis & Alignment)**:
   - **กรณีคลิปคู่รัก (Couple Paper Chat #5)**: 
     - ยิงเสียงพากย์ Single-Speaker 2 ครั้งรวดเดียว (ห้ามใช้ `multiSpeakerVoiceConfig`):
       - ฝ่ายหญิง **น้องนุ้ย**: เสียง `Aoede` (สาวใต้เสียงใส น่ารักแต่ดุ แก่นเซี้ยว ขี้บ่นกวนๆ ฉะฉาน)
         - 🛑 **Strict Sassy & Vibrant Consistency**: ห้ามหวานนุ่มเรียบร้อย หรือโมโนโทนเด็ดขาด (ห้ามมีคำว่า `Calm`, `Soft`, `Sweet`, `Formal`, `Monotone`)
         - FFmpeg Filter: `asetrate=24000*1.10,aresample=48000,atempo=1.20,highpass=f=140,equalizer=f=3500:t=q:w=1.2:g=3.0`
       - ฝ่ายชาย **พี่บ่าว**: เสียง `Puck` (หนุ่มบ้านๆ ซื่อๆ ตกใจฮาๆ อารมณ์ดี กวนๆ)
         - 🛑 **Strict No-Seriousness Guard**: ห้ามสุขุม เก๊กหล่อ วิชาการเด็ดขาด แม้อ่านสเปกหรือราคา (ห้ามมีคำว่า `Calm`, `Serious`, `Professional`, `Formal`)
         - FFmpeg Filter: `atempo=1.32,highpass=f=95`
     - คั่นระหว่างเทิร์นด้วย `... ...` (เว้น 2 วินาที)
     - ตัดแบ่งเทิร์นตามช่วงเงียบ (`split_by_longest_gaps`)
     - ตรวจทานคำพูดด้วย `faster_whisper` (`large-v3-turbo`) 100% บันทึกลง `whisper_turns.json`
     - **Audio Sanitization**: สแกน Silence Gaps ขจัดขยะ Digital Glitch (Amplitude > 15,000) ของ Flash TTS ด้วย Cosine Crossfade 5ms และใส่ Smooth Cosine Tail Fade-out 120ms ท้ายคลิป `vo.wav` สู่ค่า 0 เงียบสนิท ไร้เสียงช็อต
     - รวมเสียงเป็นไฟล์มาสเตอร์ `vo.wav` พร้อม Normalize ด้วย `loudnorm=I=-16:TP=-1.5:LRA=9`
   - **กรณีคลิปรีวิวเดี่ยว (Gadget Master 60s)**:
     - เสียงพากย์ `Fenrir` สไตล์ `commercial_premium` (Volume 1.0, Edge-TTS +15%)
4. **การบริหารโควตา API (TTS Quota & Key Rotation Standard)**:
   - โมเดลเสียงพากย์ (Flash TTS) Free Tier มีเพดาน **50 Requests/วัน ต่อคีย์ (RPD)** และ **15 Requests/นาที (RPM)**
   - **วงจรรีเซ็ตโควตารายวัน:** ทุกวันเวลา **14:00 น. (บ่าย 2 โมงตรง เวลาไทย)**
   - **กลยุทธ์ยิงประหยัด:** ใช้ Single-Take (2 calls/คลิป) สำหรับผลิตคลิปจำนวนมาก
   - **กลยุทธ์เป๊ะ 100%:** ใช้ Turn-by-Turn (12–14 calls/คลิป) โดยต้องสลับหมุนเวียนคีย์ (Multi-Key Rotation อย่างน้อย 6–8 คีย์)

---

### 🟢 Stage 2: Content Tracker & HyperFrames Auto-Draft
1. **บันทึกลง Content Tracker (`_Docs/products.json` & `store.db`)**:
   - ตรวจสอบว่าสินค้ามีอยู่แล้วหรือไม่ (URL Check)
   - หากยังไม่มี: สร้างเรคอร์ดใหม่ด้วย `product_id` (`uuid4().hex`) และ `product_code`
   - เพิ่ม Angle เข้าสินค้าด้วย `angle_id` (`ang_{uuid4().hex[:8]}`) และตั้งสถานะเริ่มต้นเป็น `script_ready`
2. **สร้าง HyperFrames Composition**:
   - สร้างโฟลเดอร์ `03_Projects/_HyperFrames_Studio/clips/{clip_slug}/`
   - บันทึกโค้ดประกอบ `build.py` และคอมไพล์ไฟล์ `compositions/{clip_slug}.html`
   - **กฎการแสดงผลใน Composition**:
     - Resolution: `1080x1920` (9:16, 30 FPS)
     - Safe Zone ด้านล่าง: ขั้นต่ำ `420px` (ไม่ให้ปุ่ม TikTok ทับ)
     - **เลย์เอาต์ช็อต CTA ท้ายคลิป (Brand & Model First Standard)**:
       - Header 1 (บนสุด): `<span class="hl">{แบรนด์} · {ชื่อรุ่น}</span>` (`Kanit Black` 108px ไฮไลต์เหลือง `#FFE600`, ขอบหมึกเข้ม `#1b1a17`, `top: 230px`)
       - Header 2: `{จุดขายตัวจบ} · กดตะกร้าเหลือง` (`Anuphan Bold` 62px, สีแดง `#d90429`, `top: 385px`)
       - Hero Product: รูปไดคัทโปร่งใส Clean Cutout PNG 630x630px ขอบเนียน คมกริบ ❌ *ห้ามใช้ภาพโปสเตอร์มีกรอบสี่เหลี่ยมทึบ*
       - ป้ายสี & ป้ายสเปก: มินิมอลการ์ด ตัวหนังสือดำเข้ม `#111111` ❌ **ห้ามใส่อีโมจิเด็ดขาด (Strict Zero-Emoji Guard)**
       - ลูกศรชี้ตะกร้า: SVG แดงโค้งชี้ลงซ้ายล่าง ❌ **ถอดข้อความ "ซ้ายล่าง" ออก 100%**
   - อัปเดตสถานะใน `ProductStore` เป็น **`draft_ready`**

---

### 🟢 Stage 3: Preview & 1-Click Render Gate
1. **ตรวจสอบความถูกต้องใน Studio Preview**:
   - รัน Preview Server: `http://localhost:3002/#project/_HyperFrames_Studio/composition/{clip_slug}`
   - ให้ User ตรวจสอบจังหวะเสียง, แอนิเมชัน, ฟอนต์ และการตัดคำ
2. **เรนเดอร์ 1-Click (HyperFrames SDK Worker)**:
   - คำสั่งเรนเดอร์มาตรฐาน:
     ```bash
     npx --yes hyperframes@0.8.149 render . -c compositions/{clip_slug}.html -o renders/{clip_slug}.mp4
     ```
   - คัดลอกไฟล์ MP4 ไปยัง: `04_Exports/Ready_to_post/{YYYYMMDD}_{product_code}_{hook}_v1.mp4`
   - ตรวจสอบไฟล์วิดีโอ: H.264, 30 FPS, เสียงสเตอริโอ AAC 48kHz, ขนาดภาพ 1080x1920 พร้อม TikTok Pro Sharpness Enhancement
   - **มาตรฐานความสว่างผิวกระดาษ (Luminance Y Calibration)**: ควบคุมค่าความสว่างพื้นกระดาษให้อยู่ในช่วง **`Y = 220.0 – 225.0`** (วัดที่ Frame 0 ด้วย cv2/YCrCb) ไม่มืดหม่น (<210) และไม่สว่างจ้าเกินไป (>230) ตามมาตรฐานความสว่างสบายตา

---

### 🟢 Stage 4: Packaging & Durable Binding
1. **ลงทะเบียน Export Identity (`_Docs/export_registry.json`)**:
   - เรียก `ExportRegistry.ensure_many(...)` เพื่อสร้าง `export_id` (`exp_{uuid4().hex}`)
   - บันทึกความสัมพันธ์: `export_id` ➔ `product_id` ➔ `angle_id` ➔ `path`
2. **เลือกหรือสร้างภาพปก (Cover Studio Packaging)**:
   - สกัดภาพปกที่เวลา `cta_start + 1.8s` (ช่วงช็อต CTA ที่แสดงแบรนด์และชื่อรุ่นสมบูรณ์)
   - บันทึกภาพปกลง `05_Covers_Thumbnails/{YYYYMMDD}_{product_code}_{hook}_cover.webp` (ขนาด 540x960 9:16)
   - ผูกภาพปกเข้ากับ `export_id` ถาวรผ่าน `scripts/export_cover_bindings.py`
3. **อัปเดตสถานะใน Tracker**:
   - ปรับสถานะของ Angle เป็น **`rendered`**

---

### 🟢 Stage 5: Smart Schedule & Verified Publish
1. **จัดเวลาลงตารางคิวโพสต์ (`_Docs/schedule_queue.json`)**:
   - เพิ่มงานใหม่พร้อม `job_id` (`job_{uuid4().hex[:16]}`)
   - กำหนดเวลา Prime-Time (11:30, 18:00, หรือ 20:30 น.)
   - ใส่แคปชัน + 5 แฮชแท็กที่เตรียมไว้
2. **โพสต์ผ่าน TikTok Auto-Post Chrome Extension**:
   - ตรวจสอบ **Account Guard**: Username ของ TikTok ในเบราว์เซอร์จริงต้องตรงกับ `channel_id` (ป้องกันโพสต์ผิดช่อง 100%)
   - ดำเนินการอัปโหลดไฟล์วิดีโอ, แนบภาพปก, ใส่แคปชัน และปักตะกร้าสินค้า
   - รับ Post ID และ Receipt บันทึกลง `PostLog`
   - ปรับสถานะใน Content Tracker เป็น **`posted`** 100%

---

## 🧹 4. กฎการทำความสะอาดและจัดระเบียบดราฟต์ (Studio Cleanup Protocol)

1. **เมื่อเรนเดอร์ MP4 เสร็จแล้ว**:
   - ห้ามทิ้งไฟล์ Composition และคลิปให้รกแถบเมนูใน HyperFrames Studio
   - ย้ายไฟล์ Composition และโฟลเดอร์คลิปเข้า Archive:  
     📁 `06_Archive/HyperFrames_Studio/compositions/{clip_slug}.html`  
     📁 `06_Archive/HyperFrames_Studio/clips/{clip_slug}/`
2. **คำสั่งจัดการ Archive**:
   - ตรวจสอบรายการ: `python 03_Projects/_HyperFrames_Studio/manage_archive.py list`
   - ย้าย Composition เข้า Archive: `python 03_Projects/_HyperFrames_Studio/manage_archive.py archive {clip_slug}`
   - ย้ายโฟลเดอร์ Clip เข้า Archive: `python 03_Projects/_HyperFrames_Studio/manage_archive.py archive-clip {clip_slug}`
   - กู้คืน Composition กลับเข้า Studio: `python 03_Projects/_HyperFrames_Studio/manage_archive.py restore {clip_slug}`
   - กู้คืน Clip กลับเข้า Studio: `python 03_Projects/_HyperFrames_Studio/manage_archive.py restore-clip {clip_slug}`
3. **การล้างไฟล์ชั่วคราว (Test Cleanup 100%)**:
   - ลบไฟล์ทดสอบใน `.tmp/` ทันทีหลังทดสอบเสร็จ ห้ามมีไฟล์ค้างเด็ดขาด

