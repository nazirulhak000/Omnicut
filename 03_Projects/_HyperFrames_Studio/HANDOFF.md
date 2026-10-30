# HANDOFF: ทำงาน HyperFrames Studio ต่อบนเครื่องนี้ (อัปเดตล่าสุด 2026-10-12)

คัดลอกและซิงก์มาจากเครื่องหลัก (`D:\Winona\Programmer\Omnicut\03_Projects\_HyperFrames_Studio`) เมื่อ **2026-10-12**
**AI / คนที่มาทำต่อ: อ่านไฟล์นี้ → `kit/STYLE.md` → `.agents/rules/pov_couple_line_chat_standard.md` → `clips/ors01-pov1-240w/build.py` ก่อนเริ่มงานทุกครั้ง**

---

## ⭐ มาตรฐานหลักล่าสุด (ตั้งแต่ 2026-10-12 เป็นต้นไป): สไตล์ #5 "Couple Paper Chat"
เจ้าของช่อง (Nz) สั่งล็อกให้ใช้สไตล์ **Couple Paper Chat (แชทคู่รัก พี่บ่าว & น้องนุ้ย บนกระดาษยับ + พากย์ 2 เสียง + รูปสินค้าจาก TikTok Shop)** เป็นมาตรฐานหลักสำหรับทุกคลิปต่อจากนี้ เพื่อ**ไม่ต้องถ่ายคลิปสินค้าดิบเองอีกต่อไป** (ส่งแค่ลิงก์ TikTok Shop หรือรูปสินค้ามาก็ตัดได้เลย 100%)

### สเปกบังคับของ Couple Paper Chat (ห้ามเพี้ยนเด็ดขาด)
1. **พื้นหลังกระดาษยับ (`assets/shared/paper_bg.mp4`):**
   - เล่นช้าลงครึ่งความเร็ว **`0.5x`** (`playbackRate = 0.5` ใน `loadedmetadata` และ `timeupdate` loop)
   - ซ้อนทับด้วย `.warm-tint` และ `.vignette` (โทนอุ่นมีมิติ ไม่จืด)
2. **การพากย์เสียง TTS (ยิง API แค่ 2 รอบต่อคลิป — ประหยัดโควตาและโทนเสียงนิ่ง 100%):**
   - **ล็อกโมเดล `gemini-3.1-flash-tts-preview` ตัวเดียวเท่านั้น** ห้ามใส่ fallback ไปรุ่นอื่น
   - **อัดรวดเดียวต่อคน (1 Single-Take per Speaker):** รวมบทของคนนั้นทั้งหมดคั่นแต่ละเทิร์นด้วย `\n\n... ...\n\n` ยิงแค่ 2 ครั้งต่อคลิป (`take_F.wav` และ `take_M.wav`):
     - **ฝ่ายหญิง (`F` = น้องนุ้ย):** เสียง `Aoede`
       - `F_STYLE = "Cute, sassy, lively Southern Thai girlfriend named น้องนุ้ย (สาวใต้เสียงใส น่ารักแต่ดุ พูดจาเป็นธรรมชาติ)"`
       - FFmpeg Filter: `asetrate=24000*1.10,aresample=24000,atempo=1.20,highpass=f=110,loudnorm=I=-15:TP=-1.5:LRA=9`
     - **ฝ่ายชาย (`M` = พี่บ่าว):** เสียง `Puck`
       - `M_STYLE = "Playful, flustered, good-natured Southern Thai boyfriend named พี่บ่าว (พี่บ่าวคนซื่อ น้ำเสียงผู้ชายชัดเจน ตกใจฮาๆ)"` (**ห้ามใส่คำว่า `Calm` เด็ดขาด** เพราะจะทำให้เสียงพี่บ่าวขรึม/ทุ้มผิดคาแรกเตอร์)
       - FFmpeg Filter: `atempo=1.32,highpass=f=95,loudnorm=I=-15:TP=-1.5:LRA=9`
   - **การหั่นเทิร์น & ตรวจด้วย Whisper:**
     - หั่น `take_F.wav` และ `take_M.wav` ด้วย `split_by_longest_gaps()` (เลือก `n-1` ช่วงเงียบที่ยาวที่สุด + trim หัวท้าย)
     - **บังคับรัน `faster_whisper` (`large-v3-turbo`)** ใน `verify_turns_with_whisper()` เพื่อตรวจว่าเสียงแต่ละเทิร์น (`turn_00`..`turn_NN`) ตรงกับบทพูดจริง 100% ไม่เลื่อนเทิร์น แล้วบันทึกผลลง `whisper_turns.json`
3. **เลย์เอาต์การ์ดแชทบนกระดาษ + รูปสินค้าจริงในบับเบิล:**
   - หัวคลิป `.paper-header` (`top: 110px`): ป้ายหมวดสีแดง `#d90429` + พาดหัว `Kanit 82px` + เส้นใต้สีแดง
   - เธรดแชท `.chat-stage` (`top: 380px`, `bottom: 390px`): แสดงบับเบิลบนหน้าจอพร้อมกันสูงสุด **`maxV = 3` กล่อง** เมื่อมีข้อความใหม่จะเลื่อนขึ้น (`gsap.to(..., { y: -shift, ease: "power2.out" })`)
   - จังหวะโชว์จุดเด่นสินค้า ให้แนบรูปสินค้าจริงจาก TikTok Shop (`<img class="b-photo">`) เข้าไปในบับเบิลแชท พร้อม SFX (`msg_recv.mp3`, `msg_send.mp3`, `pop.wav`, `ding.wav`, `cash.wav`, `whoosh.mp3`)
   - ท้ายคลิปมีป้ายปักหมุดตะกร้าเหลือง `#cta-note` มุมซ้ายล่าง (`bottom: 130px; left: 54px; transform: rotate(-2deg)`)
4. **กฎเหล็กเรื่อง Preview (ห้าม Render MP4 เองโดยพลการ):**
   - เมื่อรัน `build.py` และตรวจ `npx hyperframes lint` (`0 error(s)`) เสร็จแล้ว **ห้ามรัน `npx hyperframes render` เอง** ให้เปิดหน้า **HyperFrames Studio Preview** (`npx hyperframes preview --background`) แล้วส่งลิงก์ให้ตรวจก่อนเสมอ

### ไฟล์ต้นแบบอ้างอิงของ Couple Paper Chat
- **สคริปต์ Builder ต้นแบบ (สมบูรณ์ที่สุด):**
  - `clips/ors01-pov1-240w/build.py` → สร้าง `compositions/ors01-pov1-240w.html` (`46.76s`, 13 เทิร์น, ตรวจ Whisper ครบใน `clips/ors01-pov1-240w/whisper_turns.json`)
  - `clips/els6-couple-paper/build.py` → สร้าง `compositions/els6-couple-paper.html` (`36.18s`, 13 เทิร์น)
- **ไฟล์ MP4 ตัวอย่างที่เรนเดอร์ไว้เทียบ:**
  - `../../04_Exports/20261012_orsen-s6-240w_couple-paper_v2.mp4`

---

## 🛠️ 1. ตั้งค่าครั้งแรกบนคอมอีกเครื่อง (ทำครั้งเดียว)

เปิด terminal ที่โฟลเดอร์ `03_Projects/_HyperFrames_Studio` แล้วรัน:

```powershell
node -v          # ต้องมี Node.js 18+
ffmpeg -version  # ต้องมี ffmpeg ใน PATH
npm install      # ติดตั้ง @hyperframes/core + producer
npx hyperframes preview --background
npx hyperframes preview --status
python -c "import faster_whisper"   # ถ้ายังไม่มี: pip install faster-whisper
```

- ตรวจสอบว่าไฟล์ `.env` ที่รากโปรเจกต์ (`Omnicut/.env`) มี `GEMINI_API_KEY=...` สำหรับยิง Gemini TTS (`gemini-3.1-flash-tts-preview`)

---

## 📚 2. รายชื่อคลิปทั้งหมดใน `_HyperFrames_Studio` (22 Compositions)

1. **Couple Paper Chat (มาตรฐานหลักล่าสุด — ไม่ใช้ฟุตเทจถ่ายเอง):**
   - `compositions/ors01-pov1-240w.html` (`46.76s` — Orsen S6 240W บทใหม่ เสียง Puck สไตล์พี่บ่าวคนซื่อ `atempo=1.32`)
   - `compositions/els6-couple-paper.html` (`36.18s` — Orsen S6 240W บทแบต 4%)
2. **POV Couple Sitcom บนฟุตเทจ/ภาพสินค้า (12 คลิป):**
   - Orsen S6 (30s): `els6-pov-chat-30s.html`
   - GoChek Ultra S24 (~30s 6 คลิป): `goc01-pov-32s.html`, `goc01-pov1-anc.html`, `goc01-pov2-wall.html`, `goc01-pov3-bat.html`, `goc01-pov4-dual.html`, `goc01-pov5-plug.html` (Builder: `clips/rebuild_all_pov_clean.py`)
   - Essager 30W (~60s 5 คลิป): `ess02-pov1-fast60.html`, `ess02-pov2-safe60.html`, `ess02-pov3-mini60.html`, `ess02-pov4-worth60.html`, `ess02-pov5-cool60.html` (Builder: `clips/build_ess02_pov60_all.py`)
3. **สไตล์อื่นๆ ในแคตตาล็อก (`kit/STYLE.md`):**
   - Meme-PAS: `hat01-meme-45s.html`, `ess02-battery-36s.html`, `ess02-review-30s.html`, `ess02-jaokum-22s.html`
   - Tech Explainer: `ess02-explainer-40s.html`, `goc01-spec-42s.html`
   - VS Battle: `ess02-vs-25s.html`
   - Silent POV Chat: `ess02-pov-chat-28s.html`
   - ทดลอง (ไม่ผ่าน): `ess02-hype-25s.html`, `ess02-asmr-26s.html`
