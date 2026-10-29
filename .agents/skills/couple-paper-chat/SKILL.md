---
name: couple-paper-chat
description: Production-ready video editing skill for OmniCut & HyperFrames. Builds Thai comedy couple sitcom clips (#5 Couple Paper Chat: น้องนุ้ย & พี่บ่าว) on stop-motion paper background (1080x1920 9:16) with Gemini 3.8 Flash TTS, Faster-Whisper, Brand-First CTA, and TikTok Pro sharpness.
---

# 🎬 สกิลการตัดต่อวิดีโอ: Couple Paper Chat (#5) & OmniCut Master Style

คู่มือและคำสั่งกำกับ AI สำหรับตัดต่อคลิปวิดีโอแนวตั้ง **9:16 (1080x1920, 30 FPS)** สไตล์ **ละครสั้นคู่รักสายใต้ (น้องนุ้ย & พี่บ่าว) บนกระดาษยับ** ผสมผสานความสนุก ดราม่าโบ๊ะบ๊ะ และการป้ายยาสินค้าอย่างแนบเนียน เป็นธรรมชาติเหมือนคนตัดจริง ไม่ใช่ AI ตัด

---

## 🛑 กฎเหล็กข้อห้ามเด็ดขาด (Strict Don'ts)

1. ❌ **ห้ามใส่ราคาในคลิปเด็ดขาด (Strict Zero-Price Guard)**:
   - ผิดกฎชุมชน TikTok และทำลายความน่าเชื่อถือ
   - ห้ามมีตัวเลขราคา, ราคาขีดฆ่า, "ลด X%", "ถูกมาก", "ไม่ถึงร้อย"
   - ให้ขายด้วย **ปัญหาเร่งด่วน ➔ หลักฐานและสเปกจริง ➔ ชี้เป้าตะกร้าเหลือง**
2. ❌ **ห้ามใส่จุดไข่ปลา ("...", "…") ในบทพูดเด็ดขาด**:
   - ทำให้โมเดล TTS สังเคราะห์จังหวะการหายใจเพี้ยน และหลุดเข้าไปแสดงในซับไตเติล (ให้ใช้การเว้นวรรคธรรมชาติ)
3. ❌ **ห้ามใส่อีโมจิในช็อต CTA ท้ายคลิปเด็ดขาด (Strict Zero-Emoji Guard)**:
   - ห้ามมี ⚡, ❄️, 🛡️, ⚪, 🔥, 🛒 ในป้ายสเปกหรือป้ายสี เพื่อให้ดูมินิมอลพรีเมียม
4. ❌ **ห้ามใส่ข้อความ "ซ้ายล่าง" ติดกับลูกศร**:
   - ใช้ลูกศรแดงโค้งเพียวๆ ชี้ลงมุมซ้ายล่าง ปล่อยพื้นที่ให้สะอาดตา
5. ❌ **ห้ามเปลี่ยนบุคลิกเสียงกลางคัน (Strict Monolithic Acting Guard)**:
   - ฝ่ายชาย (พี่บ่าว) ห้ามเปลี่ยนเป็นเสียงสุขุม/เก๊กหล่อ/ทางการเด็ดขาด แม้อ่านสเปกหรือชิป
   - ฝ่ายหญิง (น้องนุ้ย) ห้ามเปลี่ยนเป็นเสียงหวานนุ่มเรียบร้อย หรือโมโนโทน
6. ❌ **ห้ามมีพื้นหลังสีดำโล่ง**:
   - ทุกช็อตต้องมีวิดีโอกระดาษยับ (`assets/shared/paper_bg.mp4`) เล่นช้า 0.5x ตลอดทั้งคลิป

---

## 🎯 1. สเปกวิดีโอ & เลย์เอาต์หลัก (Composition Specs)

- **ความละเอียด:** `1080x1920` (9:16 Vertical Video)
- **เฟรมเรต:** `30 FPS`, ตัวแปลงสัญญาณ H.264 High Profile 4.2
- **ความยาวคลิป:** ยืดหยุ่นตามความสนุกของบท (ปกติ **40–60 วินาที**)
- **Safe Zone ด้านล่าง:** **420px** (ห้ามมีปุ่ม แชท หรือข้อความสำคัญ เพื่อไม่ให้ปุ่ม Like/Comment และแคปชันของ TikTok บัง)
- **ฉากหลัง:** วิดีโอกระดาษยับจริง `assets/shared/paper_bg.mp4` (`data-playback-rate="0.5"`) ให้ฟีลลิ่ง Handmade Stop-motion

---

## 🎭 2. คาแรกเตอร์ & บทสนทนาคู่รักสายใต้ (Characters & Voice Architecture)

| บทบาท | ฝ่ายหญิง: "น้องนุ้ย" (ฝั่งซ้าย) | ฝ่ายชาย: "พี่บ่าว" (ฝั่งขวา) |
| :--- | :--- | :--- |
| **อวตาร** | วงกลมสีชมพู ตัวอักษร `"น"` | วงกลมสีฟ้า ตัวอักษร `"บ"` |
| **กล่องแชท** | สีขาวบริสุทธิ์ `#ffffff`, ขอบหมึกมน | สีเขียว LINE `#8de07a`, ขอบหมึกมน |
| **บุคลิก** | สาวใต้เสียงใส น่ารักแต่ดุ แก่นเซี้ยว ขี้บ่นกวนๆ | หนุ่มใต้ซื่อๆ ตกใจฮาๆ อารมณ์ดี กวนประสาท |
| **โมเดล TTS** | `gemini-3.8-flash-tts` (เสียง `Aoede`) | `gemini-3.8-flash-tts` (เสียง `Puck`) |
| **FFmpeg DSP** | `asetrate=24000*1.10,aresample=48000,atempo=1.20,highpass=f=140,equalizer=f=3500:t=q:w=1.2:g=3.0` | `atempo=1.32,highpass=f=95` |

### กฎการเจนเสียงพากย์ (Strict Single-Speaker 2 Passes):
1. **ยิง Single-Speaker แยก 2 รอบรวดเดียว (ห้ามใช้ multiSpeaker):**
   - รอบที่ 1: เจนบทของน้องนุ้ยทั้งหมด บันทึกเป็น `take_F.wav`
   - รอบที่ 2: เจนบทของพี่บ่าวทั้งหมด บันทึกเป็น `take_M.wav`
   - คั่นระหว่างแต่ละท่อนด้วย `... ...` (เว้น 2.0 วินาที)
2. **System Prompt Guard กำกับโมเดล:**
   ```text
   [Voice style: {F_STYLE หรือ M_STYLE}
   Pronunciation rule: Speak clear, lively, natural Thai with Southern Thai couple charm ("พี่บ่าว" and "น้องนุ้ย").
   Strict Acting Rule: Keep the EXACT SAME voice, pitch, energy, pacing, and personality from the first word to the very last word.
   DO NOT adapt or switch your acting tone to serious, calm, monotonous, or professional when reading product specs, features, or prices.
   Speak with consistent comedy couple banter and lively energy throughout the entire take.
   Between each section where you see '... ...' leave a clear 2 second silence.]
   ```
3. **ตัดแบ่งเทิร์น & สแกนคำ:**
   - ตัดแบ่งเทิร์นตามช่วงเงียบด้วย `split_by_longest_gaps`
   - สแกน Timestamp คำพูดด้วย `faster_whisper` (โมเดล `large-v3-turbo`)
   - รวมสลับบทพูดเป็น `vo.wav`

---

## 🎨 3. เลย์เอาต์ปกและช็อต CTA ท้ายคลิป (Brand & Model First Standard)

ช็อต CTA ตอนท้ายจะถูกดึงเป็น **ภาพปกคลิป TikTok 9:16 (Cover Thumbnail)** โดยอัตโนมัติที่เวลา **`cta_start + 1.8s`**:

1. **Header บรรทัดที่ 1 (เด่นที่สุด - ชูแบรนด์และรุ่น):**
   - HTML: `<div class="t center" id="cta-1"><span class="hl">{แบรนด์} · {ชื่อรุ่น}</span></div>`
   - ฟอนต์: `Kanit Black` แถบไฮไลต์เหลืองนีออน `#FFE600`, ขอบหมึกเข้ม `#1b1a17`, `top: 230px`
   - ขนาดฟอนต์ตามความยาว (Strict Zero-Overflow):
     - สั้น (<= 16 ตัวอักษร เช่น `Essager · PD 30W`): **`104px - 108px`**
     - ปานกลาง (17–24 ตัวอักษร เช่น `HOYAUP · พัดลมแม่เหล็ก`): **`82px - 86px`**
     - ยาว (> 24 ตัวอักษร): **`74px - 78px`**
2. **Header บรรทัดที่ 2 (จุดขายตัวจบ):**
   - HTML: `<div class="t center" id="cta-model">{จุดขายตัวจบ} · กดตะกร้าเหลือง</div>`
   - ฟอนต์: `Anuphan Bold` ขนาด **54px - 62px**, สีแดงสด `#d90429`, `top: 385px`
3. **Hero Product (สินค้าตรงกลาง):**
   - ใช้ภาพไดคัทโปร่งใส **Clean Cutout PNG** ขนาด **630x630px** (ไดคัทด้วย `rembg` เงาตกกระทบนุ่มลึก คมกริบ)
   - ❌ *ห้ามใช้ภาพโปสเตอร์มีกรอบสี่เหลี่ยมทึบ*
4. **ป้ายสีและป้ายสเปก (Minimal Badges):**
   - การ์ดมินิมอล `[สีดำ]` `[สีขาว]` `[สเปก 1]` `[สเปก 2]`
   - ฟอนต์ `26px - 28px`, `flex-wrap: wrap; justify-content: center; max-width: 960px;`
   - ❌ *ห้ามใส่อีโมจิเด็ดขาด*
5. **ลูกศรชี้ตะกร้าเหลือง (Minimal Curved Red Arrow):**
   - เส้น SVG สีแดงสด `#d90429` หนา 18px โค้งกวาดลงมุมซ้ายล่างหาตำแหน่งปุ่มตะกร้า TikTok
   - แอนิเมชัน GSAP Pulse ขยับเด้งเบาๆ (-18px, +18px)
   - ❌ *ถอดข้อความ "ซ้ายล่าง" ออก 100%*

---

## 🔇 4. ระบบเสียง & การขจัดเสียงซ่า (Audio Sanitization & Mix)

1. **Zeroing Digital Noise ระหว่างเทิร์น:**
   - สแกน Silence Gaps ระหว่างเทิร์นใน `vo.wav` และเคลียร์ขยะเสียง Amplitude > 15,000 ด้วย Cosine Crossfade 5ms
2. **Smooth Cosine Tail Fade-out:**
   - ช่วง 120ms ท้ายคลิปของ `vo.wav` ใส่ Fade-out สู่ 0 เงียบสนิท ไร้เสียงช็อต
3. **มิกซ์ Balance เสียง:**
   - **Voice:** 1.0 (Normalize FFmpeg loudnorm -16 LUFS)
   - **BGM:** Lo-fi Upbeat 0.05 พร้อม Voiceover Ducking
   - **SFX:** whoosh 0.18, boom 0.15, cash_register 0.20, paper 0.40

---

## 🚀 5. การเรนเดอร์ & ความคมชัด TikTok Pro Sharpness

1. **เรนเดอร์ Headless MP4 ด้วย HyperFrames CLI:**
   ```bash
   npx --yes hyperframes@0.8.149 render . -c compositions/{slug}.html -o renders/{slug}.mp4
   ```
2. **ปรับแต่งความคมชัดพิเศษสำหรับ TikTok:**
   ```bash
   python scripts/tiktok_enhancer.py renders/{slug}.mp4 04_Exports/Ready_to_post/YYYYMMDD_{product_code}_{hook}_v1.mp4
   ```
   - Pre-sharpening: Unsharp Mask `5:5:0.8:5:5:0.3` (ต้านทานการบีบอัดของ TikTok)
   - Color Primaries: Saturation +4%, Contrast +4% (BT.709)
   - Keyframe Interval: บังคับ GOP 2s (`g=60` ที่ 30fps) ตรงตามข้อกำหนดของ TikTok CDN
3. **สกัดปกอัตโนมัติ (Auto CTA Cover):**
   - ดึงเฟรมที่เวลา `cta_start + 1.8s` บันทึกเป็น WebP ขนาด 540x960 ลง `05_Covers_Thumbnails/`
   - ผูกเข้ากับ `export_registry.json` และซิงค์ `products.json`

---

## 🛠️ 6. ขั้นตอนการสร้างคลิปในโปรเจกต์ OmniCut (Production Execution)

ในการตัดคลิปจริง ระบบ OmniCut มีเทมเพลตและสคริปต์อัตโนมัติรองรับอยู่แล้ว **ไม่ต้องเขียนโค้ด Audio Assembler หรือ TTS Engine ใหม่จากศูนย์**:

### ขั้นตอนที่ 1: กำหนดข้อมูลสินค้า (Product Input)
ผู้ใช้หรือ AI ต้องระบุข้อมูลพื้นฐาน:
- **แบรนด์และชื่อรุ่น** (เช่น `Orsen S6`, `Essager 100W`)
- **จุดขายเด่น 2-3 ข้อ** (เช่น ชิป E-MARK, สายถัก 48 เส้น, ชาร์จโน้ตบุ๊ก 240W)
- **รูปภาพสินค้า** ที่ไดคัทแล้วใน `03_Projects/_HyperFrames_Studio/assets/{slug}/img/`

### ขั้นตอนที่ 2: สร้างไฟล์สคริปต์ `clips/{slug}/build.py`
สร้างโฟลเดอร์ `03_Projects/_HyperFrames_Studio/clips/{slug}/` และสร้าง `build.py` โดยใส่เฉพาะบทสนทนา `TURNS` และหัวข้อ `HEADLINES` (ก๊อปปี้เทมเพลตจาก `clips/els6-couple-paper/build.py`):
```python
# กำหนดบทพูด น้องนุ้ย (F) และ พี่บ่าว (M)
TURNS = [
    ("F", [("พี่บ่าว!", "พี่บ่าว!"), ("โน้ตบุ๊กแบตเหลือ 3%!", "โน้ตบุ๊กน้องแบตเหลือสามเปอร์เซ็นต์!")], None),
    ("M", [("ใจเย็นน้องนุ้ย", "ใจเย็นครับน้องนุ้ย"), ("ใช้เส้นนี้เลย", "ใช้เส้นนี้เลย")], (1, "assets/els6/img/src/coil_240w.jpg", "photo")),
    # ...
    ("M", [("จัดให้ครับ", "จัดให้ครับ"), ("กดตะกร้าเหลือง", "ใครอยากได้ กดตะกร้าเหลือง")], None),
]
CTA_PHRASE = (len(TURNS) - 1, 1)
```

### ขั้นตอนที่ 3: รันคำสั่งอัตโนมัติ 3 สเต็ปบนเครื่อง Local
```bash
# 1. เจนเสียง Gemini TTS 2 รอบ + ถอดคำ Faster-Whisper + รวมเสียง vo.wav + สร้าง HTML คอมโพสิชัน
cd 03_Projects/_HyperFrames_Studio
python clips/{slug}/build.py

# 2. เรนเดอร์วิดีโอ 1080x1920 30fps
npx --yes hyperframes@0.8.149 render . -c compositions/{slug}.html -o renders/{slug}.mp4

# 3. เร่งความคมชัดระดับโปรสำหรับ TikTok (จากรากโปรเจกต์)
cd ../..
python scripts/tiktok_enhancer.py 03_Projects/_HyperFrames_Studio/renders/{slug}.mp4 04_Exports/Ready_to_post/YYYYMMDD_{product_code}_{hook}_v1.mp4
```
