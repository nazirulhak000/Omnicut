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
3. ❌ **ห้ามใส่อีโมจิในช็อต CTA ท้ายคลิปและปกคลิปเด็ดขาด (Strict Zero-Emoji Guard)**:
   - ห้ามมี ⚡, ❄️, 🛡️, ⚪, 🔥, 🛒 ในป้ายสเปก, ป้ายสี หรือการ์ดพาเลตต์ เพื่อให้ดูพรีเมียมระดับ Agency ป้องกันความรู้สึกว่าเป็นคลิปสแปม AI
4. ❌ **ห้ามใส่ลูกศรสีแดงชี้พาดผ่านตัวสินค้าเด็ดขาด (Strict Zero-Arrow Guard)**:
   - ถอดเส้นลูกศรแดงออก 100% ไม่ให้บดบังตัวสินค้า โดยใช้ Header Hook (`พลังลมตัวจบ · กดตะกร้าเหลือง`) และเสียงพากย์ชี้นำตะกร้าเหลืองแทน
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

## 🎨 3. มาตรฐานปกและช็อต CTA ท้ายคลิป (Master Cover & CTA Outro Frame — Style 3B Golden Formula)

ช็อต CTA ตอนท้ายจะทำหน้าที่แบบ Dual-Purpose: เป็นทั้ง **ฉากจบ CTA Outro (2-3 วินาทีสุดท้าย)** และถูกสกัดเป็น **ภาพปกคลิป TikTok 9:16 (Cover Thumbnail)** โดยอัตโนมัติที่เวลา **`cta_start + 1.8s`**:

1. **Header บรรทัดที่ 1 (ชูแบรนด์และรุ่นเด่นชัด):**
   - HTML: `<div class="t center" id="cta-1"><span class="hl">{แบรนด์} · {ชื่อรุ่น}</span></div>`
   - ฟอนต์: `Kanit Black` แถบไฮไลต์เหลืองนีออน `#FFE600`, ขอบหมึกเข้ม `#1b1a17`, `top: 170px` (Safe-zone 960px)
   - ขนาดฟอนต์: 80px - 108px ตามความยาวชื่อสินค้า
2. **Header บรรทัดที่ 2 (Sub-headline / Action):**
   - HTML: `<div class="t center" id="cta-model">{Sub-headline}</div>`
   - ฟอนต์: `Anuphan Bold` ขนาด **50px - 62px**, สีแดงสด `#d90429`
   - *สำหรับปกคลิป (Cover):* ใช้ Hook กระตุ้นความสนใจ เช่น `ดีไซน์มินิมอล · คุ้มสุดงบหลักร้อย`
   - *สำหรับฉากจบ (CTA Outro):* ใช้คำปิดการขาย เช่น `พลังลมตัวจบ · พิกัดตะกร้าเหลือง`
3. **Hero Stage (สินค้าตรงกลาง + เงาสัมผัส Realistic Contact Shadow):**
   - ใช้ภาพไดคัทโปร่งใส **Clean Cutout PNG** (ไดคัทด้วย `rembg` คมกริบ ไร้ขอบเหลี่ยม)
   - มีเงาสัมผัสวงรี `radial-gradient` ใต้ฐานสินค้าทุกตัวบนกระดาษยับ ป้องกันสินค้าดูลอย
4. **Bottom Tier (Specs & Actions เหนือ TikTok Safe Zone >280px):**
   - **4 Spec Badges:** กล่องสเปก 4 ชิ้น ฟอนต์ `Anuphan Bold` 26px - 28px พื้นขาว ขอบดำ 3px เงาแข็ง `3px 5px 0 #1b1a17`
   - ❌ **ห้ามใส่อีโมจิเด็ดขาด (Strict Zero-Emoji Guard):** ห้ามมี 🎨, ✨, 🔥, ⚡, 🛒 ในป้ายหรือการ์ดใดๆ
   - ❌ **ห้ามใส่ลูกศรแดงพาดผ่านตัวสินค้า (Strict Zero-Arrow Guard):** ถอดลูกศรแดงออก 100% เพื่อให้ภาพสินค้าสะอาดตาพรีเมียม
5. **กลยุทธ์สินค้า 3 กลุ่ม (Adaptive Product Strategy):**
   - **สินค้าหลากสี:** สูตร 3B (Trio Hero 3 ตัวหน้าขนาดใหญ่ + การ์ดสวอชสีกลม 6 สีสไตล์ Pantone ด้านล่าง เช่น `6 โทนสีพาสเทล`)
   - **สินค้าชิ้นเดียว/สีเดียว:** ขยายสินค้าใหญ่ 650–700px เอียง 3D Perspective 15°–20° + ขนาบข้างด้วย Floating Feature Badges 2 ฝั่งเพื่อไม่ให้ข้างๆ โล่ง
   - **สินค้าแบบเซ็ต:** ตัวเครื่องหลักเป็น Hero ใหญ่ตรงกลาง + อุปกรณ์เสริมเรียงขนาบข้างแบบ Knolling เป็นระเบียบ

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
