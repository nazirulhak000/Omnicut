# HANDOFF: ทำงาน HyperFrames Studio ต่อบนเครื่องนี้

คัดลอกมาจากเครื่องเดิม (`D:\Winona\Programmer\Omnicut\03_Projects\_HyperFrames_Studio`) เมื่อ 2026-10-10
**AI/คนที่มาทำต่อ: อ่านไฟล์นี้ → `README.md` → `kit/STYLE.md` ก่อนเริ่มงานทุกครั้ง**

## 1. ตั้งค่าครั้งแรก (ทำครั้งเดียว)

**ขั้น 0: ติดตั้ง skill ตัดต่อ** (อยู่ที่ `E:\PGM\claude-skills\` ดู README ในนั้น):
```powershell
Copy-Item -Recurse -Force E:\PGM\claude-skills\* "$env:USERPROFILE\.claude\skills\" -Exclude README.md
```
แล้วปิดและเปิด Claude Code ใหม่

เปิด terminal ที่โฟลเดอร์นี้ (`E:\PGM\Omnicut\03_Projects\_HyperFrames_Studio`) แล้วรันตามลำดับ:

```bash
node -v          # ต้องมี Node.js 18+
ffmpeg -version  # ต้องมี ffmpeg ใน PATH
npm install      # ติดตั้ง @hyperframes/core + producer (ใช้กับ audio carve)
npx hyperframes@0.8.143 doctor
python -c "import faster_whisper"   # ถ้า error: pip install faster-whisper
```

- **Whisper model** `large-v3-turbo` จะโหลดอัตโนมัติครั้งแรก (~1.6 GB) จากนั้นแก้ `local_files_only=True` ใน `kit/new_clip.py` ได้ตามปกติ ถ้าโหลดไม่ได้ให้เปลี่ยนเป็น `local_files_only=False` ชั่วคราว
- **rembg / Gemini TTS** ใช้ `.venv` และ `.env` ของ Omnicut บนเครื่องนี้ (`E:\PGM\Omnicut\.venv`, `.env`) ตรวจว่า `.venv` มี `rembg` และ `.env` มี `GEMINI_API_KEY`
- **Audio carve script** อยู่ใน skill `hyperframes-audio` (`~/.claude/skills/hyperframes-audio/scripts/carve.mjs`) ได้มาจากขั้น 0
- โค้ด Omnicut บนเครื่องนี้ตามหลังเครื่องเดิม 2 commit (`git pull` ได้) แต่ Studio ไม่ได้อยู่ใน git (`03_Projects/` ถูก ignore) ต้องคัดลอกไฟล์เหมือนรอบนี้

## 2. เปิดดู / render

- ดับเบิลคลิก `open_studio.bat` → เลือกคลิปที่แผง Compositions
- Render: `npx hyperframes render -c compositions/<คลิป>.html -o ../../04_Exports/<YYYYMMDD>_<สินค้า>_<สไตล์>_v1.mp4`

## 3. สิ่งที่เจ้าของช่อง (Nz) ตั้งไว้ — memory จากเครื่องเดิม

- คลิปต้อง **"เหมือนคนตัด ไม่ใช่ AI ตัด"**: ห้ามการ์ด UI มืด / pill ฟ้า / พื้นดำโล่ง / ไอคอน SVG วาดเอง ใช้ของจริงแทน (ฉลากทางการ, ภาพจริงตัดพื้นหลัง, meme GIPHY ตรงมุก + meme SFX + meme pause), motion มีฟิสิกส์
- **สไตล์ที่อนุมัติ 4 แบบ** (รายละเอียดเต็มใน `kit/STYLE.md`):
  1. **Meme-PAS** (รีวิวสายมีม): คลิปอ้างอิง `hat01-meme-45s` ("ชอบมาก")
  2. **Tech Explainer** (สาย Vox): `ess02-explainer-40s`
  3. **VS Battle** (สายเกมต่อสู้): `ess02-vs-25s`
  4. **POV Chat Story** ⭐ ชอบที่สุด ไม่มีเสียงพากย์: `ess02-pov-chat-28s` (component `kit/line-chat.css`, คลังสถานการณ์อยู่ใน STYLE.md)
- **ไม่ผ่าน:** Velocity Hype (ฟุตเทจซ้ำ ไม่มีเรื่อง), Hands-only ASMR (slow-mo จาก 30fps กระตุก) ห้ามใช้จนกว่าจะแก้ต้นเหตุ
- สั่งงานด้วยชื่อสไตล์ เช่น "ตัด Hatari แบบ VS Battle" / "ทำ POV Chat Hatari เรื่องแม่บ่นค่าไฟ"
- ได้ feedback ใหม่ → เขียนลง `kit/STYLE.md` (หัวข้อ "บันทึก feedback") ทุกครั้ง ไม่ใช่แค่ในแชท
- ตรวจงานด้วยการ render draft แล้วดึงเฟรมทุก beat มาดู (`check` อย่างเดียวไม่พอ)

## 4. ไฟล์ที่ไม่ได้คัดลอก (สร้างใหม่ได้)

`node_modules/`, `.thumbnails/`, `.hyperframes/` (cache ของ Studio) และ MP4 ใน `04_Exports/` ของเครื่องเดิม (ถ้าต้องการให้คัดลอกเอง)

แหล่งเสียงพากย์/บทของแต่ละคลิปอยู่ที่ `03_Projects/HAT01-meme-50s_1`, `ESS02-แบตหมด-meme_1`, `ESS02-explainer_1`, `ESS02-vs-battle_1` (คัดลอกมาแล้ว)
