# HyperFrames Studio: ตัดคลิปรีวิวสินค้าทุกตัว

Studio กลางที่เดียวสำหรับทุกสินค้า ใช้ template กลาง (`kit/`) คุมแบรนด์ของช่อง ส่วนการตัดและ motion แยกเป็นของแต่ละคลิป

> **ก่อนออกแบบคลิปใหม่ อ่าน [`kit/STYLE.md`](kit/STYLE.md)** สไตล์การตัด "เหมือนคนตัด ไม่ใช่ AI" ที่สะสมจาก feedback

## เปิดดู / แก้

ดับเบิลคลิก **`open_studio.bat`** แล้วเลือกคลิปที่แผง **Compositions** ทางซ้าย ปิดหน้าต่างดำเพื่อหยุด Studio

คลิปที่ render เสร็จแล้วอยู่ที่ `04_Exports/`

## โครงสร้าง

```
kit/                     template กลาง: แก้ที่นี่ ทุกคลิปเปลี่ยนตาม
  kit.css                สีช่อง, ฟอนต์, scrim, ซับคาราโอเกะ, ลายน้ำ, แฟลช, .cam.murky
  kit.js                 HF.captions(tl), HF.flash(tl), HF.dash(el)
  fonts/                 Kanit Black, Anuphan Bold
  hf_timing.py           whisper → cue → ซับ + SFX → timing.js, index.html
  starter.html           โครงเริ่มต้นของคลิปใหม่
  new_product.py         เพิ่มสินค้า (grade footage + contact sheet + cutout)
  new_clip.py            เริ่มคลิปใหม่ (เสียงพากย์ + whisper + build.py + composition)
assets/
  shared/                bgm.wav, sfx/ (ใช้ทุกคลิป)
  <สินค้า>/              footage.mp4, contact_sheet.jpg, img/hero_*.png
  clips/<คลิป>/          vo.wav, timing.js (สร้างอัตโนมัติ)
clips/<คลิป>/            script.txt, whisper_words.json, build.py (clause + SFX ของคลิป)
compositions/<คลิป>.html การตัดช็อต + motion ของคลิปนั้น
```

ชื่อคลิปใช้รูปแบบ `<สินค้า>-<มุม>-<ความยาว>` เช่น `ess02-jaokum-22s`

## เพิ่มสินค้าใหม่

```bash
python kit/new_product.py hat01 "01_Raw/<โฟลเดอร์>/<ไฟล์>.mov" --hero-at 3.6
```

เปิดดู `assets/hat01/contact_sheet.jpg` (เลขบนภาพ = วินาที) เพื่อเลือกช่วงช็อต

## เพิ่มคลิปใหม่

```bash
python kit/new_clip.py hat01-review-30s --product hat01 --vo "03_Projects/HAT01-รีวิวสเปก_1/voiceover.wav" --script "<script.txt>"
```

1. เติม `CLAUSES` + `sfx` ใน `clips/<คลิป>/build.py` (ใช้คำที่ whisper สะกดตามที่สคริปต์พิมพ์ออกมา)
2. ออกแบบช็อตและ beat ใน `compositions/<คลิป>.html`
3. `python clips/<คลิป>/build.py`
4. `node %USERPROFILE%/.claude/skills/hyperframes-audio/scripts/carve.mjs --comp compositions/<คลิป>.html --bed bgm --voice vo --core .` เพื่อลด BGM ตอนมีเสียงพากย์
5. `npx hyperframes check`
6. `npx hyperframes render -c compositions/<คลิป>.html -o ../../04_Exports/<YYYYMMDD>_<สินค้า>_<hook>_v1.mp4`

## กฎ

- เวลาทุก cue มาจาก whisper ห้ามกะเอง
- path ของ asset อิงจาก root ของ studio (`assets/...`) ห้ามใช้ `../`
- ไฟล์ทดสอบ render ลง `.tmp/` เท่านั้น ห้ามลง `04_Exports/`
