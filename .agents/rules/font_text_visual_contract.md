# 🔒 กฎเหล็กฟอนต์ ข้อความ และซับไตเติล (Font & Text Visual Contract)

กฎนี้เป็น **Project-level Golden Master Contract** สำหรับทุก AI Agent และนักพัฒนาที่แตะระบบบทพูด
ข้อความ ซับไตเติล Hook, Preview หรือ Render ของ OmniCut Pro Studio

> **หลักสูงสุด:** งานที่ผู้ใช้ไม่ได้สั่งให้เปลี่ยนฟอนต์หรือข้อความ
> **ห้ามทำให้เนื้อหา รูปแบบ ขนาด ตำแหน่ง การตัดบรรทัด หรือภาพที่เรนเดอร์เปลี่ยนโดยเด็ดขาด**
> ถ้ารักษาสัญญานี้ไม่ได้ ให้หยุดงานและขออนุมัติผู้ใช้ก่อน ห้ามเลือกค่าใหม่เอง

---

## 1. ขอบเขตที่ถือว่าเป็น Font/Text Contract

การเปลี่ยนแปลงต่อไปนี้ถือว่ากระทบ contract แม้ไม่ได้แก้ข้อความโดยตรง:

- ข้อความไทย/อังกฤษ, Unicode, การคงชื่อแบรนด์และศัพท์เทคนิค, คำแปล และลำดับ cue
- font family, physical face/weight, font size, scale, bold, outline, shadow และสี
- line wrapping, Micro-Burst, จำนวนบรรทัด, line height, alignment, margin และ safe zone
- ASS style/override tags, Canvas `ctx.font`, text metrics, font fallback และ `fontsdir`
- ค่า default ใน UI, form migration, style preset, manifest serializer และ render payload
- dependency หรือ Python environment ที่ใช้คำนวณ font metrics
- การ reuse/versioning ของ `.ass` และ fingerprint ของ subtitle stage

ไฟล์ที่ต้องถือว่าอยู่ในขอบเขตนี้อย่างน้อย:

- `scripts/subtitle_engine.py`
- `scripts/subtitle/`
- `scripts/stages/subtitle_stage.py`
- `scripts/pipeline_context.py`
- `scripts/project_manifest.py`
- `frontend/src/components/SequencePlayer.jsx`
- editor form/default/serializer ที่ส่ง caption, font, style หรือ overlay
- `tests/test_preview_render_parity.py`
- `tests/test_preview_render_behavior.py`
- `tests/test_subtitle_artifact_contract.py`

---

## 2. Content Identity — ห้ามเปลี่ยนคำโดยผลข้างเคียง

1. งาน UI, style, render, performance, refactor, dependency หรือ infrastructure
   **ห้ามแก้ `cue.text`, `cue.translation`, บทพูด, ชื่อแบรนด์, รุ่นสินค้า หรือศัพท์เทคนิค**
2. เปลี่ยนข้อความได้เฉพาะเมื่อผู้ใช้แก้ข้อความเอง หรือสั่งงานที่มีเจตนาชัดเจน เช่น
   “แก้บท”, “เจนบทใหม่”, “แปลใหม่” หรือ “แก้ซับ”
3. การกด **บันทึก** เก็บ state/manifest เท่านั้น ห้ามสร้างคำใหม่ แปลใหม่ หรือเปลี่ยนความหมายเอง
4. การกด **Render** มีหน้าที่แปลง state ล่าสุดเป็น artifact ห้าม rewrite เนื้อหาเพื่อให้เข้ากับ style
5. การ escape อักขระและตัดบรรทัดเพื่อ ASS ทำได้เฉพาะสำเนาที่ใช้เรนเดอร์
   ห้ามเขียนค่าที่ escape/wrap แล้วกลับทับข้อความต้นฉบับใน manifest
6. ถ้าแก้เฉพาะฟอนต์ สี ตำแหน่ง หรือ motion เนื้อหาไทยและอังกฤษก่อน/หลังต้องเท่ากัน
   แบบ Unicode หลัง normalization ที่ระบบกำหนด
7. ห้ามแปลงชื่อแบรนด์ รุ่น หรือศัพท์อังกฤษเป็นคำทับศัพท์ไทย ตามกฎใน `AGENTS.md`

---

## 3. Golden Master Typography — ค่าเริ่มต้นห้าม drift

สำหรับวิดีโอ `1080x1920`, `caption_scale = 1.0` และ IBM Plex Sans Thai:

| รายการ | Golden Master |
|---|---|
| Caption em intent | `1080 × 0.0463 = 50px` |
| Canvas preview | `540 × 0.0463 = 25px` |
| IBM line-box scale | `1000 / (1116 + 534) = 0.6060606` |
| ASS `TikTokWhite`/`TikTokSoftShadow` Fontsize | `round(50 / 0.6060606) = 82` |
| English subtitle scale | `68%` ของภาษาไทย |
| Caption line advance | `1.0 × ASS Fontsize` |
| Bottom caption margin | `420px` ที่ความสูง `1920px` |
| Caption alignment เริ่มต้น | ASS alignment `2` (bottom centre) |
| Caption physical face | `IBM Plex Sans Thai SemiBold` |
| Caption outline intent | `max(1.8, 50 × 0.040) = 2.0px` |
| Hook em intent | `1080 × 0.065 = 70px` ก่อนคูณ scale ของฟอนต์ Hook |

กฎบังคับ:

- ห้ามเปลี่ยน ratio `0.0463`, English `68%`, line factor `1.0`, margin `420`, physical face,
  caption-scale default หรือ font-metric formula ในงานที่ไม่ได้รับคำสั่งให้เปลี่ยน typography
- ห้ามใช้เลข `50` จาก ASS เป็นหลักฐานว่าขนาดถูกต้อง เพราะ libass ใช้ line box ไม่ใช่ em box
- `ass_glyph_scale()` ต้องอ่าน metric จากไฟล์ฟอนต์จริง และต้องให้ผลเหมือนกันใน project `.venv`
  ห้าม fallback เป็น `1.0` แบบเงียบเมื่อ dependency หาย
- font fallback ใดที่ทำให้ physical face หรือ metrics เปลี่ยน ต้อง fail ชัดเจนหรือแจ้งผู้ใช้
  ห้าม render ต่อด้วยภาพคนละแบบโดยไม่บอก

---

## 4. Save, Render และเวอร์ชัน `.ass`

- **Save:** บันทึกข้อความและค่าตั้งในโปรเจกต์ ยังไม่จำเป็นต้องสร้าง `.ass` ใหม่
- **Render:** รัน subtitle stage เมื่อ input/fingerprint/contract เปลี่ยน แล้วสร้าง `.ass` เวอร์ชันใหม่
- Render ที่ไม่มี input หรือ contract เปลี่ยนสามารถ reuse `.ass` ล่าสุดที่ผ่าน validation ได้
- `subtitles.ass` เป็น artifact แบบ legacy; `subtitles_v1.ass`, `subtitles_v2.ass` คือ artifact
  ที่สร้างตามลำดับการรัน subtitle stage ไม่ใช่ทุกครั้งที่กด Save
- `project.json` เป็นแหล่งจริงว่ารอบปัจจุบันใช้งาน `.ass` ไฟล์ใด ห้ามเดาจากเลขไฟล์สูงสุดอย่างเดียว
- เมื่อเปลี่ยน output contract ที่ทำให้ภาพเก่าไม่ถูกต้อง ต้อง bump
  `SUBTITLE_RENDER_CONTRACT_VERSION` และทำให้ artifact เก่าถูก regenerate
- ห้ามลบ `.ass` เก่าหรือแก้ด้วยมือเป็นวิธีแก้หลัก เพราะจะทำลาย forensic/recovery evidence

---

## 5. Environment Parity — เทสด้วยตัวเดียวกับเซิร์ฟเวอร์จริง

1. คำสั่งตรวจ Python ต้องใช้ `.venv\Scripts\python.exe` ของโปรเจกต์เสมอ
   ห้ามรับรองผลจาก system Python ถ้า backend รันด้วย `.venv`
2. dependency ที่มีผลต่อภาพต้องประกาศใน `requirements.txt` และ `pip check` ต้องผ่าน
3. ห้ามจับ exception กว้างแล้วคืนค่า default ที่ทำให้ภาพเปลี่ยนโดยไม่มี error
4. ก่อนปิดงาน visual ต้องยืนยัน process backend ถูก restart หลัง patch และใช้ executable จาก `.venv`
5. probe, test และ live render ต้องรายงาน interpreter/environment ที่ใช้เมื่อผลขึ้นกับ dependency

บทเรียน `FONT-SIZE-REGRESSION-2`: system Python มี `fontTools` จึงสร้าง Fontsize `82`
แต่ backend `.venv` ไม่มี package และ fallback เป็น scale `1.0` จึงสร้าง Fontsize `50`
ทั้งที่ source code ชุดเดียวกัน กฎนี้มีไว้ห้าม environment mismatch แบบนั้นเกิดซ้ำ

---

## 6. Gate บังคับเมื่อมีการเปลี่ยน Font/Text Contract

ห้ามสรุปว่าเสร็จจากการอ่าน source หรือเห็นตัวเลขใน ASS เท่านั้น ต้องผ่านทั้งหมด:

1. เขียน regression test ก่อนแก้ที่ seam ซึ่งทำให้บั๊กเกิดจริง
2. รันด้วย project `.venv`:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests/test_subtitle_artifact_contract.py tests/test_preview_render_parity.py tests/test_preview_render_behavior.py -q -p no:cacheprovider --tb=short
   ```

3. Render จริงด้วย FFmpeg + libass โดยส่ง `fontsdir=02_Assets/Fonts`
4. Motion ต้องดึงอย่างน้อย 3 เฟรม: ช่วงเข้า ช่วงค้าง และช่วงออก
5. เรื่องขนาด/ตำแหน่งต้องวัด pixel bands หรือ bounding box เทียบ Golden Master
   ห้ามใช้คำว่า “ดูใกล้เคียง” เป็น gate
6. ตรวจข้อความไทย/อังกฤษใน manifest ก่อนและหลังว่าไม่ถูกเปลี่ยนโดยงาน visual
7. รัน full backend, frontend test/build, `compileall`, `pip check` และ `git diff --check`
8. ถ้าแก้ renderer contract ต้องทดสอบว่า `.ass` รุ่นก่อนถูก invalidate และรุ่นใหม่ถูก reuse ได้

---

## 7. Stop Condition — เมื่อใดต้องหยุดถามผู้ใช้

ต้องหยุดงานและขออนุมัติผู้ใช้ก่อน หากเกิดข้อใดข้อหนึ่ง:

- งานที่สั่งไม่ได้เกี่ยวกับฟอนต์/ข้อความ แต่จำเป็นต้องเปลี่ยนค่าตามตาราง Golden Master
- Preview กับ Render ไม่สามารถรักษาขนาด ตำแหน่ง สี หรือเนื้อหาให้ตรงกันได้
- จำเป็นต้องเปลี่ยน font family/face, ขนาด, English ratio, line wrapping, safe zone หรือค่า default
- dependency/font fallback ทำให้ไม่สามารถพิสูจน์ physical face และ metrics ที่ใช้จริง
- regression test หรือ FFmpeg pixel gate ไม่ผ่าน แม้ภาพด้วยตาจะดูดี

ห้ามลด assertion, เปลี่ยน baseline, ปิดเทส หรือเพิ่ม tolerance เพื่อให้ผ่านโดยไม่ได้รับอนุมัติจากผู้ใช้

