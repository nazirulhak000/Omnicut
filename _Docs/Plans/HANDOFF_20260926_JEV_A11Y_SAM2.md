# 🤝 Handoff 2026-09-26 — จาก Cline สู่ Claude

**สำหรับ:** session ถัดไป (Claude / agent ตัวไหนก็ได้) · **ผู้ส่งต่อ:** Cline (Claude)
**สถานะ repo ตอนส่ง:** `HEAD = a2634e5` · branch `phase1-affiliate-studio` · working tree **มีงานของเอเจนต์อื่นค้าง** (ดูหัวข้อ 2)

> เอกสารนี้เป็น**แผนส่งต่อเท่านั้น** ไม่ซ้ำเนื้อหาที่มีอยู่แล้ว — ให้ไปอ่านไฟล์ต้นฉบับตาม path ที่อ้าง

---

## 0. อ่านก่อนเริ่ม (บังคับตาม `AGENTS.md`)

1. `AGENTS.md` — 19 กฎเหล็ก + ข้อ 19 คือกฎ Jev Decision Layer ที่เพิ่งเพิ่ม
2. `TODO.md` — รอบที่ยังเปิดอยู่ (อ่านเฉพาะบล็อกที่เกี่ยวกับงานตัวเอง)
3. `git status` — **มีงานของเอเจนต์อื่นค้าง ห้ามเขียนทับ**
4. `.agents/rules/work_loop.md` — ต้องเขียนแผนลง `TODO.md` ก่อนแตะโค้ด

---

## 1. สิ่งที่ทำเสร็จแล้ว (ไม่ต้องทำซ้ำ)

| # | งาน | หลักฐานอยู่ที่ | commit |
| :-- | :--- | :--- | :-- |
| 1 | **กฎ Jev + CLI** ให้ AI ทุกตัวตัดสินใจร่วมกันได้ | `.agents/rules/jev_decision_layer.md` · `tools/jev_advisor.py` · `tests/test_jev_advisor.py` (22 tests) | `211d5c1` + `6ff8c85` |
| 2 | **แก้ accessible name ใน Inspector** 4 จุด | `frontend/src/components/editor/inspector/OverlayScaleControl.jsx` (เพิ่ม prop `ariaLabel`) + 3 ไฟล์อื่น | `d937e45` |
| 3 | **ปิดรอบค้าง 2 รอบ** เข้า `HISTORY.md` | `FIX-CUTOUT-MASTER-SWITCH` · `JEV-DECISION-LAYER-RULE` | `d937e45` |
| 4 | **รัน full test suite** วัดตัวเลขจริง | `TODO.md` → `Round PROXY-CONSOLE-ERROR-REGRESSION-20260926` | `449d9e3` · `b1d7ad6` |
| 5 | **ปิด Q3 ด้วยการวัดจริง** (SAM 2.1 CPU) | `_Docs/Reports/SAM2_CPU_FEASIBILITY_20260926.md` + contact sheet | `a2634e5` |

**ตัวเลขสำคัญที่ได้ (อย่าวัดซ้ำ):**
- Full suite: **41 failed / 1909 passed / 8 skipped** (10m12s)
- SAM 2.1 tiny บน CPU: **11.47 s/เฟรม p50** · 60 เฟรม = 715.61s · peak RSS **929 MiB** (ไม่ OOM) · คุณภาพติดตาม**ผ่าน**

---

## 2. ⚠️ สถานะ working tree ตอนส่ง — ห้ามเขียนทับ

```
 M _Docs/post_log.json
 M frontend/src/components/SequencePlayer.jsx      ← เอเจนต์อื่นกำลังแก้
 M frontend/src/lib/clipProxy.js
 M frontend/src/lib/clipProxy.test.js
 M tiktok_autopost_extension/manifest.json
?? tiktok_autopost_extension/icons/
```

**เจ้าของ:** session อื่นกำลังทำ proxy playback + color matching + slow-motion
→ ถ้าจะแตะไฟล์เหล่านี้ ให้เขียนแผนและประสานก่อน

---

## 3. งานที่เปิดค้าง 3 เรื่อง (เรียงตามความสำคัญ)

### 🥇 เรื่องที่ 1 — 40 เทสพังจาก proxy (deterministic)

**อาการ:** `test_frame_pair` 18 · `test_clip_frame_pair` 16 · `test_overlay_frame_pair` 4 · `test_app_capture` 2 = **40 เทส**
ล้มทั้งหมดด้วย `AppCaptureUnavailable: browser runtime errors were captured`

**รากเหตุที่พิสูจน์แล้ว** (ดึงจาก `manifest.json` runtime diagnostics):
```
console_errors=1  page_errors=0  request_failures=0
CONSOLE: "Failed to load resource: the server responded with a status of 403 ()"
url:    /api/proxy/for-clip?source_path=...%2Fmotion_capture.html&build=true
```

กลไก: `SequencePlayer` เรียก `getClipProxy()` ทุกคลิป → เทส capture เปิด **Vite fixture ที่ไม่มี FastAPI backend** → ได้ 403 → **Chromium บันทึก console error เอง** (เป็นข้อความของ browser จึงกดทิ้งจาก JS ไม่ได้) → `app_capture.py:306` เช็ค `runtime["clean"]` → fail ทั้งกลุ่ม

พิสูจน์ว่าเป็น deterministic แล้ว: รัน `test_app_capture.py` 2 รอบ → fail 2/2

**ทางเลือกแก้ 3 ทาง** (แนะนำข้อ 1):
1. **ไม่ยิง proxy เมื่อไม่มี backend / `source_path` เล่นไม่ได้** — แก้ที่ต้นเหตุ ปลอดภัยที่สุด
2. เพิ่ม `/api/proxy` 403 ใน allowlist ของ `app_capture.py` — เร็ว แต่ทำให้ parity gate จับปัญหาจริงไม่ได้
3. ให้ `motionCaptureFixture.jsx` ปิด proxy บังคับเส้นทาง master — จำกัดผลกระทบเฉพาะเทส

> รายละเอียดทั้งหมดอยู่ใน `TODO.md` → `Round PROXY-CONSOLE-ERROR-REGRESSION-20260926`

### 🥈 เรื่องที่ 2 — Q4: ออกแบบ offline worker สำหรับ SAM 2.1

**บริบท:** Q3 ปิดแล้ว — คุณภาพติดตาม**ผ่าน** แต่ **11.47 s/เฟรม** = คลิป 15 วินาที = **86 นาที**

**ข้อบังคับที่ต้องยึด:**
- ต้องเป็น **offline worker** ที่รายงาน progress ได้ (แบบ `background_isolation_video_worker.py`) — **ห้าม** คิดว่าทำ interactive ได้
- mask ที่ได้เป็น **binary segmentation ไม่ใช่ alpha matting** → ต้อง refine ต่อด้วย `scripts/cutout_temporal.py`
- รันด้วย venv แยกเท่านั้น: `tools/cutout_runtime/.venv` (torch 2.5.1+cpu, Python 3.12.13) — **ห้าม** ติดตั้งลง `.venv` หลัก (กฎข้อ 5)
- checkpoint มีอยู่แล้ว: `03_Projects/.cache/cutout-models/sam2.1_hiera_tiny.pt` — **ห้ามดาวน์โหลดซ้ำ** (กฎข้อ 13)
- harness พร้อมแล้ว: `tools/benchmark_cutout_tracker.py` — **ห้ามเขียนซ้ำ** (Zero-Duplicate)

**เสนอให้ทำก่อน:** วัดความเร็วใหม่หลังปรับ (threads 4→8, ลด `image_size`, หรือยิงทุก 3 เฟรมแล้ว interpolate) — ถ้าเหลือ 20–30 นาทีต่อคลิป การออกแบบ Q4 จะง่ายขึ้นมาก

### 🥉 เรื่องที่ 3 — เทสที่เหลือ 2 อัน (ไม่ใช่ regression)

| เทส | อาการ | สถานะการวินิจฉัย |
| :--- | :--- | :--- |
| `test_cutout_video_preview` | `{'seeks': 0, 'visible': 50}` · เกณฑ์คือ `visible >= 54` | ยืนยันเป็น **flake** (รัน 3 รอบ: fail, fail, ผ่าน) → ประเมินลด threshold เหลือ 48 |
| `test_export_registry_bulk` | `assert 'exp_...' is None` | **order-dependent** ผ่าน 3/3 เดี่ยว ๆ · สาเหตุน่าสงสัยคือ class-level cache `_path_index` + `_path_index_signature` ที่ใช้ร่วมทุกเทส (`scripts/export_registry.py:62-99`) → เพิ่ม `autouse` fixture reset |

---

## 4. กติกาที่ต้องรู้ก่อนแตะงาน

| กฎ | สาระสำคัญ |
| :--- | :--- |
| **ข้อ 10** | ต้องเขียนแผนลง `TODO.md` **ก่อน** แตะโค้ดบรรทัดแรก |
| **ข้อ 14** | ทุกบล็อกต้องมี `ดำเนินการโดย: <agent> (<model>)` |
| **ข้อ 15** | ไฟล์ทดสอบลบให้หมด 100% — ผลวัด/วิดีโอ/thumbnail ต้องไม่เหลือใน `04_Exports/` |
| **ข้อ 19** | ใช้ Jev ตัดสินใจร่วมกันทุกจุดสำคัญ — ดูหัวข้อ 5 |
| **ข้อ 1** | ห้ามลบ/เขียนทับ `01_Raw/` `02_Assets/` โดยไม่มีการยืนยัน |
| **ข้อ 9** | Preview = Render — แก้ทั้งสองฝั่งในคอมมิตเดียว |

**เครื่องมือ Jev (ใช้ก่อนตัดสินใจสำคัญ):**
```powershell
cd d:/Winona/Programmer/Capcut
& .venv\Scripts\python.exe tools\jev_advisor.py --check
& .venv\Scripts\python.exe tools\jev_advisor.py fanout --spec .tmp\jev_spec.json
# exit 0 = ทำต่อได้ · 1 = escalate (ถามผู้ใช้) · 2 = ใช้ไม่ได้
```
เกณฑ์: confidence `>= 0.80` ทำต่อ · ต่ำกว่านั้นหยุดถามผู้ใช้
**จำกัด:** Jev อ่านได้แค่ข้อความ ใช้ตรวจเฟรม/ซับจริง/ฟอนต์ไม่ได้

---

## 5. แนะนำ skill ที่ควรเรียกใช้

| skill | ใช้ทำอะไร | เมื่อไหร่ |
| :--- | :--- | :--- |
| `video-editing` | กฎภาพ/เสียง FFmpeg ของโปรเจกต์ | ก่อนแตะ ffmpeg/ASS/subtitle |
| `typesafe-ai` | เอกสาร TypeSafe/Jev เต็มรูปแบบ | ถ้าจะใช้ Jev ลึกกว่า primitive 3 ตัว |
| `token-efficiency-guardian` | กันเปิด `HISTORY.md` ทั้งไฟล์ (~150k token) | **บังคับ** — อ่านแค่สารบัญ ≤100 บรรทัด |
| `git-guardrails-claude-code` | กัน commit/push พลาดตอนมีเอเจนต์อื่นทำขนาน | ก่อน `git add` / `commit` ทุกครั้ง |
| `qa` | วาง test plan + เกณฑ์ release | ก่อนปิดรอบ |
| `impeccable` / `design-an-interface` | UI/UX เมื่อต้องแก้ Inspector | ถ้างานไปแตะ UI |

---

## 6. คำสั่งที่ต้องรู้

```powershell
# เทสเต็ม (10 นาที — รันแบบ background แล้ว poll ไม่ใช่รอหน้าจอ)
Start-Process -FilePath ".venv\Scripts\python.exe" `
  -ArgumentList "-m","pytest","tests/","-q","-p","no:cacheprovider","--tb=line","-rf" `
  -RedirectStandardOutput ".tmp\pytest.log" -NoNewWindow -PassThru

# เฉพาะไฟล์
.venv\Scripts\python.exe -m pytest tests/motion_capture/test_editor_controls_browser.py -q

# frontend
cd frontend; npm test ; npm run build

# SAM 2.1 (venv แยกเท่านั้น)
tools\cutout_runtime\.venv\Scripts\python.exe tools\benchmark_cutout_tracker.py `
  --frames .tmp\cutout_tracker_probe `
  --checkpoint 03_Projects\.cache\cutout-models\sam2.1_hiera_tiny.pt `
  --prompts .tmp\cutout_tracker_probe\prompts.json `
  --report .tmp\cutout_tracker_probe\report.json `
  --contact .tmp\cutout_tracker_probe\contact_sheet.png
```

> ⚠️ **PowerShell มีกับดัก 2 จุดที่เจอแล้ว:**
> 1. `git commit -m "..."` หลายบรรทัดพัง → **เขียน message ลง `.tmp/` แล้วใช้ `git commit -F` เสมอ**
> 2. `Set-Content -NoNewline` ทำให้ `HISTORY.md` 9,632 บรรทัดกลายเป็นบรรทัดเดียว → **ห้ามใช้**

---

## 7. สิ่งที่ต้องระวัง

1. **มี AI หลายตัวทำขนานกัน** — เคยมีไฟล์ถูกกวาดไปรวมกับ commit ของเอเจนต์อื่น (`211d5c1`) → ตรวจ `git log --stat` ก่อนตัดสินว่าใครทำอะไร
2. **`git commit -m` หลายบรรทัดพังใน PowerShell** — ใช้ไฟล์ `-F` เสมอ
3. **ห้ามลบ `.tmp/cutout_playback_pytest` / `.tmp/cutout_quality_pytest`** — เป็นของเอเจนต์อื่น
4. **console ภาษาไทยบิดเบือน** — ถ้าตัวเลขแปลก ให้เขียนลงไฟล์แล้วอ่านด้วย tool อ่านไฟล์ อย่าเชื่อ console
5. **Jev คืน `noul.confidence = null` เสมอ** → บังคับ escalate ทุกครั้งตามกฎ ไม่ใช่บั๊ก

---

## 8. ข้อเสนอลำดับ 3 ขั้นตอนถัดไป

| ขั้น | งาน | เวลาโดยประมาณ | ผลลัพธ์ |
| :-- | :--- | :-- | :-- |
| 1 | แก้ 40 เทส (ข้อ 1: ไม่ยิง proxy เมื่อไม่มี backend) | ~30 นาที | gate ของ 2 รอบ Cutout ปลด |
| 2 | วัดความเร็ว SAM 2.1 ใหม่ (threads 8 / image_size เล็กลง) | ~20–40 นาที | ตัวเลขตัดสินว่า Q4 ออกแบบยังไง |
| 3 | แก้ 2 เทสที่เหลือ (threshold + autouse fixture) | ~15 นาที | full suite เขียว |

> ข้อ 1 ควรทำก่อน เพราะเป็นของเจ้าของ proxy และเป็น blocker ของ gate
> แต่ตอนส่ง เอเจนต์อื่นกำลังแก้ `SequencePlayer.jsx` อยู่ → **ต้องประสานก่อนแตะไฟล์เดียวกัน**

