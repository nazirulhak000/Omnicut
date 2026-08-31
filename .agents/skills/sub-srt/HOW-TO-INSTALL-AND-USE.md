# 🎬 sub-srt — How to Install & Use

Turn any audio/video clip into an **accurate** `.srt` subtitle file for CapCut,
Premiere, DaVinci, or Final Cut — subtitles that are **actually in sync**, because the
timing comes from real speech recognition (Whisper), never guessed. Great for
**Thai / Chinese / English** short-form video, including Thai + English mixed.

> ⚠️ This is a real tool that runs on your computer (not a chatbot prompt). It works
> **fully offline** — no upload, no per-minute fee, no watermark. You install it once.

---

## What's inside
- `sub-srt` / `generate_srt.py` — the tool
- `setup.sh` (Mac/Linux) · `setup.ps1` (Windows) — one-time installer
- `SKILL.md` — for Claude Code / Cursor users (auto-runs it)
- `README.md` — full documentation

---

## ✅ Install (one time)

**You need:** Python 3.9+ installed. Nothing else — no admin/sudo, no Homebrew.

**Mac / Linux** — open Terminal in this folder and run:
```bash
bash setup.sh
```

**Windows** — open PowerShell in this folder and run:
```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

The installer builds an isolated environment and picks the right engine for your
machine automatically (Apple Silicon → GPU; Windows/Intel/Linux → CPU or NVIDIA).
The **first** subtitle run downloads the model (~1.5 GB), then it's cached forever.

---

## ▶️ Use

**Mac / Linux:**
```bash
./sub-srt "clip.mp4" --lang th
```
**Windows:**
```powershell
.\.venv\Scripts\python.exe generate_srt.py "clip.mp4" --lang th
```

- Put a **video or audio** file in — audio is extracted automatically.
- Output lands next to your file as `clip-sub.srt`. Drag it onto your editor's
  subtitle track.
- `--lang th` = Thai (also `zh` Chinese, `en` English…). **Always pass `--lang`** for
  a clip that's mostly one language — it's much more accurate.

### Handy options
| Flag | What it does |
|------|--------------|
| `--mode bilingual` | *(default)* spoken line **+ English translation** stacked |
| `--mode mono` | single track, big karaoke-style captions |
| `--mode dual` | two separate files (original + English) |
| `--fast` | draft speed (lower accuracy) |
| `--words-per-line 4` | fewer words per box = bigger text |
| `--vtt` | also export a `.vtt` file |

---

## 🖥️ Using it inside Claude Code / Cursor
Drop this whole folder into your skills directory
(`~/.claude/skills/sub-srt/`), then just say **"make subtitles for this clip"** and
attach the file — it runs everything above for you and cleans up the caption text.

## 🔒 Uninstall
Delete this folder. (Model cache lives in `~/.cache/huggingface`.)

---
MIT — use it, share it, remix it.

<br>

# 🇹🇭 sub-srt — วิธีติดตั้งและวิธีใช้

เปลี่ยนไฟล์เสียง/วิดีโอให้เป็นไฟล์ซับ `.srt` ที่ **ตรงเป๊ะ** สำหรับ CapCut, Premiere,
DaVinci หรือ Final Cut — ซับ **ตรงกับเสียงจริง** เพราะเวลามาจากระบบถอดเสียงจริง (Whisper)
ไม่ใช่การเดา เหมาะกับคลิปสั้น **ไทย / จีน / อังกฤษ** รวมถึงไทยปนอังกฤษ

> ⚠️ อันนี้คือโปรแกรมที่รันบนเครื่องคุณจริง ๆ (ไม่ใช่พรอมต์แชท) ทำงาน **ออฟไลน์ทั้งหมด** —
> ไม่ต้องอัปโหลด ไม่มีค่าใช้จ่ายรายนาที ไม่มีลายน้ำ ติดตั้งครั้งเดียวจบ

---

## ในโฟลเดอร์มีอะไรบ้าง
- `sub-srt` / `generate_srt.py` — ตัวโปรแกรม
- `setup.sh` (Mac/Linux) · `setup.ps1` (Windows) — ตัวติดตั้งครั้งเดียว
- `SKILL.md` — สำหรับคนใช้ Claude Code / Cursor (สั่งให้รันอัตโนมัติ)
- `README.md` — คู่มือฉบับเต็ม

---

## ✅ ติดตั้ง (ครั้งเดียว)

**สิ่งที่ต้องมี:** ติดตั้ง Python 3.9+ ไว้ในเครื่อง แค่นั้น — ไม่ต้องใช้สิทธิ์ admin ไม่ต้อง Homebrew

**Mac / Linux** — เปิด Terminal ในโฟลเดอร์นี้ แล้วพิมพ์:
```bash
bash setup.sh
```

**Windows** — เปิด PowerShell ในโฟลเดอร์นี้ แล้วพิมพ์:
```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

ตัวติดตั้งจะสร้างสภาพแวดล้อมแยกให้ และเลือกเอนจินที่เหมาะกับเครื่องคุณอัตโนมัติ
(Apple Silicon → ใช้ GPU; Windows/Intel/Linux → CPU หรือการ์ด NVIDIA)
การรัน **ครั้งแรก** จะดาวน์โหลดโมเดล (~1.5 GB) หลังจากนั้นจะเก็บไว้ใช้ตลอด

---

## ▶️ วิธีใช้

**Mac / Linux:**
```bash
./sub-srt "clip.mp4" --lang th
```
**Windows:**
```powershell
.\.venv\Scripts\python.exe generate_srt.py "clip.mp4" --lang th
```

- ใส่ไฟล์ **วิดีโอหรือเสียง** เข้าไป — ระบบดึงเสียงออกให้เอง
- ไฟล์ผลลัพธ์ `clip-sub.srt` จะอยู่ข้าง ๆ ไฟล์ต้นฉบับ ลากไปวางในแทร็กซับของโปรแกรมตัดต่อได้เลย
- `--lang th` = ภาษาไทย (หรือ `zh` จีน, `en` อังกฤษ…) **ควรใส่ `--lang` เสมอ** ถ้าคลิป
  เป็นภาษาเดียวเป็นหลัก จะแม่นกว่ามาก

### ออปชันที่ใช้บ่อย
| แฟลก | ทำอะไร |
|------|--------|
| `--mode bilingual` | *(ค่าเริ่มต้น)* บรรทัดที่พูด **+ คำแปลอังกฤษ** ซ้อนกัน |
| `--mode mono` | แทร็กเดียว ตัวใหญ่สไตล์คาราโอเกะ |
| `--mode dual` | แยกเป็นสองไฟล์ (ต้นฉบับ + อังกฤษ) |
| `--fast` | โหมดร่าง เร็วขึ้น (แม่นน้อยลง) |
| `--words-per-line 4` | คำต่อกล่องน้อยลง = ตัวอักษรใหญ่ขึ้น |
| `--vtt` | ส่งออกไฟล์ `.vtt` เพิ่มด้วย |

---

## 🖥️ ใช้ผ่าน Claude Code / Cursor
วางทั้งโฟลเดอร์นี้ไว้ในโฟลเดอร์ skills (`~/.claude/skills/sub-srt/`) แล้วพิมพ์ว่า
**"ทำซับให้คลิปนี้"** พร้อมแนบไฟล์ — มันจะรันทุกอย่างข้างบนให้ และเกลาข้อความซับให้ด้วย

## 🔒 ถอนการติดตั้ง
ลบโฟลเดอร์นี้ทิ้ง (แคชโมเดลอยู่ที่ `~/.cache/huggingface`)

---
MIT — ใช้ได้ แชร์ได้ ดัดแปลงได้
