# 💬 มาตรฐานคลิปแนวละครสั้นคู่รักสายใต้ + แชท LINE ตัดแยกกล่องลงล่าง (POV Couple Sitcom & Stacked LINE Chat Standard)

เอกสารนี้กำหนดมาตรฐานการผลิตคลิปไวรัล TikTok สไตล์ **ละครสั้นคู่รักสายใต้ (`น้องนุ้ย` & `พี่บ่าว`) + กล่องแชท LINE เด้งซ้อนลงล่าง** สำหรับ HyperFrames Studio (`03_Projects/_HyperFrames_Studio`)

---

## 1. คาแรกเตอร์ประจำช่อง (Southern Thai Couple Persona)
- **ฝ่ายหญิง (`F`):** **`"น้องนุ้ย"`**
  - บุคลิก: สาวใต้เสียงใส น่ารักแต่ดุ พูดจังหวะกระชับ ชัดถ้อยชัดคำ
  - ตำแหน่งกล่องแชท: **ฝั่งซ้าย (Left-aligned)**
  - โปรไฟล์อวตาร: วงกลมสีชมพูไล่เฉด (`linear-gradient(135deg, #ff9eb5, #ff5277)`) ตัวอักษรย่อ **`"น"`**
  - ป้ายชื่อเหนือกล่อง: **`"น้องนุ้ย"`**
- **ฝ่ายชาย (`M`):** **`"พี่บ่าว"`**
  - บุคลิก: พ่อบ้านคนซื่อ อารมณ์ดี น้ำเสียงผู้ชายชัดเจน ตกใจฮาๆ
  - ตำแหน่งกล่องแชท: **ฝั่งขวา (Right-aligned)**
  - โปรไฟล์อวตาร: วงกลมสีฟ้าไล่เฉด (`linear-gradient(135deg, #60a5fa, #2563eb)`) ตัวอักษรย่อ **`"บ"`**
  - ป้ายชื่อเหนือกล่อง: **`"พี่บ่าว"`**

---

## 2. กฎเหล็กเรื่องเสียงพากย์ (Strict Single-Speaker TTS — ห้ามเสียงสลับกลางคลิปเด็ดขาด)
- ❌ **ห้ามใช้ `multiSpeakerVoiceConfig`** ในการเจนบทสนทนายาว 8–10 เทิร์น เพราะโมเดลมีโอกาสสลับเสียงชาย-หญิงกลางคลิป
- ✅ **ต้องแยกยิง Gemini TTS แบบ Single-Speaker 2 รอบแยกกันเสมอ:**
  1. **เสียง `น้องนุ้ย` (Female):** ใช้ `voiceName: "Aoede"` ล้วนทั้งคลิป พร้อมปรับ FFmpeg filter:
     `asetrate=24000*1.10,aresample=48000,atempo=1.20,highpass=f=140,equalizer=f=3500:t=q:w=1.2:g=3.0`
  2. **เสียง `พี่บ่าว` (Male):** ใช้ `voiceName: "Puck"` ล้วนทั้งคลิป พร้อมปรับ FFmpeg filter:
     `atempo=1.32,highpass=f=95`
- นำไฟล์เสียงทั้ง 2 แทร็กมาหั่นแยกตามเทิร์น (`split_into_n_segments`) แล้วเรียงสลับ (Interleave) เข้าด้วยกัน พร้อม Normalize ความดังที่ `-16 LUFS`

---

## 3. ดีไซน์กล่องแชท LINE แบบตัดแยกกล่องลงล่างอัตโนมัติ (Stacked LINE Chat Bubbles)
- วางเฉพาะโซนล่างของจอ (`top: 1245px`, `left: 36px`, `right: 36px`) เด้งขึ้นมาทีละเทิร์น
- **ห้ามข้อความยาวล้นกล่องเด็ดขาด:**
  - กำหนดให้ `.cap-in` เป็น Flex Column (`display: flex; flex-direction: column; gap: 12px; background: transparent`)
  - ให้แต่ละ `<span class="w">` เป็น **กล่องแชท LINE แยกคนละใบซ้อนลงมาด้านล่าง (`ตัดออกมาลงล่างอีก 1 กล่อง`)**
  - ขนาดตัวอักษร `40px` (`white-space: nowrap`, `padding: 16px 28px`, `border-radius: 26px`)
  - กล่องของ **`น้องนุ้ย` (ซ้าย):** พื้นหลังสีขาว `#ffffff` มุมซ้ายบนแหลม (`border-radius: 6px 26px 26px 26px` ในกล่องใบแรก) มีเวลา `"18:05"` กำกับด้านขวา
  - กล่องของ **`พี่บ่าว` (ขวา):** พื้นหลังสีเขียว LINE `#8de07a` มุมขวาบนแหลม (`border-radius: 26px 6px 26px 26px` ในกล่องใบแรก) มีข้อความ `"อ่านแล้ว 18:05"` กำกับด้านซ้าย
  - จังหวะพูด: กล่องย่อยใบที่ 2 และ 3 จะซ่อนไว้ก่อน (`opacity: 0`) และเด้งขึ้นมา (`fromTo y: 18 -> 0, scale: 0.9 -> 1`) ในเสี้ยววินาทีที่เริ่มพูดวรรคนั้น พร้อมไฮไลต์ตัวหนังสือสีแดง `#d90429` และเปลี่ยนกลับเป็นสีดำ `#111111` เมื่อพูดวรรคถัดไป

---

## 4. การจัดวางองค์ประกอบภาพและเสียงประกอบ (Visual & Audio Polish)
1. **หัวข้อ Hook ด้านบนแบบตัวใหญ่ชัดเจน 2 บรรทัด (`scene-sub` & `scene-title` — ใหญ่สะใจ ไม่ล้นขอบจอ):**
   - ต้องแบ่งเป็น 2 บรรทัดด้วย `<br>` และตั้ง `white-space: normal !important` เพื่อให้ตัวหนังสือใหญ่เต็มตาแต่อยู่กึ่งกลางจอ ไม่กางยาวบรรทัดเดียวชนขอบซ้าย-ขวา
   - `scene-sub`: ขนาด `54px` (`top: 135px`, `left: 60px !important`, `right: 60px !important`)
   - `scene-title`: ขนาด `80px` (`top: 215px`, `left: 60px !important`, `right: 60px !important`, `line-height: 1.18`) **ห้ามล้นขอบจอ 1080px และห้ามใส่กล่องแคปซูลทึบ**
2. **ฟุตเทจสินค้าจริง 100% (No Meme Video Clutter):**
   - ห้ามใส่คลิปมีมคั่นกลางจอ ใช้ฟุตเทจสินค้าจริงคมชัดตลอดทั้งคลิป
3. **ช็อตสุดท้าย (Large Multi-Line Final CTA):**
   - แสดงหัวข้อ `"กดตะกร้าเหลือง"` ตัวใหญ่เด่นชัด (`font-size: 108px`, `top: 220px`) + ชื่อรุ่นสินค้าขนาดใหญ่ (`font-size: 72px`, `top: 360px`) + บรรทัดที่ 2 สีฟ้าไซแอน (`<span class="sub-line2">ของแท้ • ประกันศูนย์ไทย</span>` ขนาด `64px`) + ลูกศรโค้งชี้ลงซ้ายล่าง + คำว่า `"ซ้ายล่าง"` (`font-size: 98px`)
4. **ลายน้ำลิขสิทธิ์ (Bottom Clean Watermark):**
   - วางชิดขอบล่างตรงกลาง (`bottom: 26px`) พื้นหลังใส `background: transparent` **ห้ามใส่กล่องดำทึบหลังลายน้ำเด็ดขาด**
5. **ระดับเสียง BGM & SFX ตามสถานการณ์:**
   - BGM (`bgm_lofi.wav`): เปิดคลอเบาๆ ที่ `data-volume="0.04"` พร้อม `data-carve="0.25"` ไม่ให้ตีกับเสียงพูด (หากคลิปยาวเกิน 60 วินาที ให้ต่อ `<audio id="bgm2">` อัตโนมัติ)
   - SFX แชทเด้ง: ฝ่ายหญิงใช้ `msg_recv.mp3`, ฝ่ายชายใช้ `msg_send.mp3`
   - SFX จังหวะสำคัญ: โชว์สเปกใช้ `ding.wav`, จังหวะตบมุก/ยึดของใช้ `punch.mp3`, จังหวะชี้ตะกร้าใช้ `cash_register.mp3`

---

## 5. สคริปต์ต้นแบบ (Master Reference Builders)
- **กรณีไม่มีคลิปดิบ / ไม่ต้องถ่ายสินค้าเอง (Couple Paper Chat — มาตรฐานหลักสำหรับป้ายยาจากลิงก์ TikTok Shop):**
  - สคริปต์ต้นแบบ: `03_Projects/_HyperFrames_Studio/clips/ors01-pov1-240w/build.py` และ `03_Projects/_HyperFrames_Studio/clips/els6-couple-paper/build.py`
  - พื้นหลัง: วิดีโอกระดาษยับ stop-motion `assets/shared/paper_bg.mp4` เล่นความเร็วครึ่งเดียว (`data-playback-rate="0.5"`, ห้ามใส่โค้ดเขย่า/สั่นจอซ้ำ)
  - การอัดเสียง (ยิงแค่ 2 รอบต่อคลิป ประหยัดโควตาและโทนเสียงนิ่ง 100%):
    - ล็อกโมเดล `TTS_MODEL = "gemini-3.1-flash-tts-preview"` ตัวเดียว ห้าม fallback
    - อัดรวดเดียวต่อคน (`tts/take_F.wav` สำหรับ `Aoede` และ `tts/take_M.wav` สำหรับ `Puck`) โดยใช้คำสั่งสไตล์ชุดมาตรฐาน:
      - `F_STYLE = "Cute, bright, energetic young Southern Thai girlfriend named น้องนุ้ย (สาวใต้เสียงใส น่ารักแต่ดุ พูดจังหวะกระชับชัดเจน)"` (`asetrate*1.10, atempo=1.20`)
      - `M_STYLE = "Playful, flustered, good-natured Southern Thai boyfriend named พี่บ่าว (พี่บ่าวคนซื่อ น้ำเสียงผู้ชายชัดเจน ตกใจฮาๆ)"` (`atempo=1.32` — **ห้ามใส่คำว่า `Calm` เด็ดขาด** เพราะทำให้โทนเสียง `Puck` เปลี่ยนเป็นเนิบสุขุม)
    - หั่นแยกเทิร์นตรงช่วงเงียบที่ยาวที่สุด `n-1` จุด (`split_by_longest_gaps`) แล้วรัน `verify_turns_with_whisper()` ด้วย `faster_whisper` (`large-v3-turbo`) ตรวจว่าทุกท่อนตรงเทิร์น 100%
  - โครงสร้างภาพในแชท: แชท ➔ รูปสินค้าทางการกรอบขาว (`540px` + เสียง `paper.mp3`) เด้งเข้ามาในเธรดแชทใต้วรรคที่พูดถึง ➔ แชทเลื่อนขึ้นอัตโนมัติ ➔ ปิดด้วยหน้า CTA กดตะกร้าเหลืองซ้ายล่าง (เปิดหน้า Studio Preview ให้ตรวจก่อนเสมอ ห้ามเรนเดอร์ MP4 จนกว่า User จะสั่ง)
- **กรณีมีคลิปฟุตเทจสินค้าจริง:**
  - สคริปต์ต้นแบบ 30 วินาที (GoChek S24): `03_Projects/_HyperFrames_Studio/clips/rebuild_all_pov_clean.py`
  - สคริปต์ต้นแบบ 60 วินาที (Essager 30W): `03_Projects/_HyperFrames_Studio/clips/build_ess02_pov60_all.py`

