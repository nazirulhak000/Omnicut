# Prompt: รอบต่อจาก Audit — ปิดงานค้างให้เรียบร้อย (Phase 2)

ไฟล์นี้เป็น prompt สำหรับ AI coding agent ให้ชี้มาที่ไฟล์นี้แล้วสั่ง "ทำตามไฟล์นี้"
ต่อจาก `PROMPT_APP_AUDIT_AND_CAPCUT_REFERENCE.md` และรอบ `AUDIT-FIX-SAFETY-AUTOPOST-20261003` ใน TODO.md

---

## เป้าหมาย

ปิดของที่ยังค้างจาก audit (`_Docs/Plans/APP_AUDIT_CAPCUT_REFERENCE_20261003.md`) ให้ครบ ทดสอบผ่านทั้งชุด
แล้วปิดรอบย้ายเข้า HISTORY.md ได้ ไม่เพิ่มฟีเจอร์ใหม่นอกรายการนี้

## ขั้นเตรียม (บังคับ)

1. อ่านบล็อก `## Round AUDIT-FIX-SAFETY-AUTOPOST-20261003` ใน TODO.md (ใช้ grep หาบรรทัด แล้วอ่านเฉพาะบล็อกนั้น) โดยเฉพาะหัวข้อ "ค้าง" และ "เลื่อนไว้"
2. อ่าน Top 5 และภาคผนวกในรายงาน audit
3. รัน `git status` แล้วเช็กว่า Codex ยังถือไฟล์ไหนอยู่ (ดูตารางเจ้าของไฟล์ใน TODO.md) **ห้ามแก้ไฟล์ที่ Codex ยังไม่ส่งงาน**
   ถ้าไฟล์ที่ต้องแตะยังเป็นของ Codex ให้ข้ามข้อนั้น บันทึกว่า "รอ Codex" แล้วทำข้ออื่นต่อ
4. เปิดรอบใหม่ใน TODO.md ชื่อ `Round AUDIT-FOLLOWUP-PHASE2-<YYYYMMDD>` พร้อม `ดำเนินการโดย: <เอเจนต์> (<โมเดล>)` และตารางเจ้าของไฟล์

## กลุ่ม A: ทำได้เลย (ไม่ต้องรอใคร)

| # | งาน | ไฟล์ | เกณฑ์ผ่าน |
|---|---|---|---|
| A1 | แก้ regression จาก B5: Ctrl+Escape ต้องออก zen ได้เหมือนเดิม และเช็กว่า Alt+ปุ่มที่เคยใช้งานไม่หาย | `frontend/src/hooks/useEditorShortcuts.js` + test | test ใหม่ยืนยัน Ctrl+Escape ออก zen; Ctrl+S ยังไม่ split |
| A2 | `angle_performance`/`summary` ใช้ `mature_metrics` (>=48 ชม.) แทนตัวเลขดิบ แล้วอัปเดต test ที่คาดเลขเดิม | `scripts/api_analytics.py`, `scripts/post_log.py`, tests ที่เกี่ยวข้อง | โพสต์อายุ <48 ชม. ไม่ถูกนับในสรุป |
| A3 | แก้ `tools/jev_advisor.py --help` ล้มด้วย encoding error บน Windows | `tools/jev_advisor.py` | `--help` พิมพ์ภาษาไทยได้ใน PowerShell/Git Bash ไม่ crash |
| A4 | แก้ hardcoded absolute path ใน `tools/` ตามภาคผนวกของรายงาน ให้ใช้ `pathlib` หรือ `scripts/config.py` | ไฟล์ตามรายการภาคผนวก | grep หา `D:\\|d:/|C:\\Users` ใน `tools/*.py` ไม่เจอ (ยกเว้น comment) |
| A5 | ลิงก์ใน AGENTS.md/TODO.md ชี้ไป `file:///d:/Winona/Programmer/Capcut/...` ซึ่งไม่ใช่ที่อยู่โปรเจกต์ปัจจุบัน เปลี่ยนเป็นลิงก์ relative | `AGENTS.md`, หัวไฟล์ TODO.md (**ห้ามแก้เนื้อหารอบเก่าใน HISTORY.md**) | คลิกลิงก์แล้วเปิดไฟล์ได้จริง |

## กลุ่ม B: ทำหลัง Codex ส่งงาน (ไฟล์ทับกัน)

| # | งาน | ไฟล์ | เกณฑ์ผ่าน |
|---|---|---|---|
| B1 | ต่อ `coalesceKey` เข้า `EditorShell.jsx` ให้ slider/drag เป็น undo ก้อนเดียว | `EditorShell.jsx` | ลาก slider 20 ครั้ง = undo 1 ครั้ง |
| B2 | `clipKey` ใน `SequencePlayer.jsx` ให้ครบทุก field ที่กระทบภาพ (เช่น speed) | `SequencePlayer.jsx`, `subtitle_engine.py` ถ้าจำเป็น | `tests/test_preview_render_parity.py` ผ่าน + render ffmpeg เทียบเฟรมจริงตาม preview_render_parity.md |
| B3 | Cutout เสถียร (Top 5 ขั้น 4): `import sys` ที่ขาด, GPU semaphore, SAM2 quality gate ให้ manifest ตรงความจริง | `background_isolation_video_worker.py`, `api_background_isolation.py`, `background_isolation_sam2_worker.py` | test ตามที่รายงานระบุ (kill process tree, subject หายกลางคลิป, 2 request เข้าคิว) ไม่แตะ GPU จริง |
| B4 | Top 5 ขั้น 5: ต่อสาย `color_match.py`, denoise `afftdn`, ปุ่ม bulk ตัดช่วงเงียบ/ตัดตามบีต — **ทั้งหมดต้อง opt-in ปิดไว้เป็นค่าเริ่มต้น** | `stages/video_assembly_stage.py`, `stages/audio_mix_stage.py`, `EditorShell.jsx`/`Toolbar.jsx` | ค่าเริ่มต้นได้ผลลัพธ์เหมือนเดิม; เปิด opt-in แล้ว test ผ่าน; parity ถ้ากระทบ preview |

## กลุ่ม C: ต้องให้ผู้ใช้ตัดสินใจก่อน (ห้ามตัดสินใจเอง)

ถามผู้ใช้ทีละข้อ จดคำตอบลง TODO.md แล้วค่อยทำ:

1. **เสียงเริ่มต้น Puck หรือ Fenrir** — AGENTS.md ข้อ 5 กำหนด Fenrir + `commercial_premium` แต่โค้ด fallback เป็น Puck (`scripts/gemini_tts_engine.py:128`) และ `ad_tone` default เป็น `commercial_hype` (`scripts/api_render.py:178`, `pipeline_context.py:364`, `pipeline.py:113`) จะแก้ให้ตรงกฎไหม (กระทบเสียงทุกคลิปใหม่)
2. **delete-file เส้นทางหลัก** (`api_videos.py` ที่ยังใช้ `target.unlink()`) จะเปลี่ยนเป็นย้ายไป `06_Archive/.trash` ทุกกรณีไหม
3. **`git rm --cached` mirror JSON 4 ไฟล์** ให้ออกจาก git (ไฟล์ในเครื่องยังอยู่) ทำไหม
4. **ทดสอบ autopost กับ TikTok จริง 1 คลิป** — ผู้ใช้ต้องเป็นคนกดโพสต์เอง เพื่อยืนยันว่า URL ออกจาก `/tiktokstudio/upload` จริง ถ้าไม่ออก extension จะรายงานว่าโพสต์ไม่สำเร็จทั้งที่สำเร็จ

## ข้อห้าม

- ห้ามแตะฟอนต์/ซับ/safe zone (font_text_visual_contract.md) เว้นแต่ B2 ที่ต้องแก้คู่ตาม preview_render_parity.md
- ห้ามเขียนลง 01_Raw/, 02_Assets/, 04_Exports/ จริง; test ใช้ `tmp_path` เท่านั้น; cleanup 100%
- ห้าม `git add/commit/stash/checkout/reset` เว้นแต่ผู้ใช้สั่ง
- ห้าม hardcode absolute path
- เรียก `tools/jev_advisor.py` ตามจุดบังคับใน AGENTS.md ข้อ 19 (หลังแก้ A3 แล้วควรใช้ได้) ถ้า confidence < 0.80 ให้หยุดถามผู้ใช้

## ปิดรอบ

1. รันครบ: `pytest tests/` + `npm test` + `npm run build` (ใน `frontend/`) บันทึกผลจริง ถ้า fail ระบุสาเหตุและเจ้าของไฟล์
2. `git diff --check` เฉพาะไฟล์ของรอบ
3. ถ้ากลุ่ม A, B, C ปิดครบ ย้ายบล็อก `AUDIT-FIX-SAFETY-AUTOPOST-20261003` และรอบนี้ไป HISTORY.md เหลือชื่อรอบบรรทัดเดียวใน TODO.md
   ถ้ายังไม่ครบ อย่าย้าย ระบุว่าค้างอะไร รออะไร
4. สรุปในแชตไม่เกิน 15 บรรทัด: ทำอะไรเสร็จ, test ผลเท่าไร, อะไรรอ Codex, อะไรรอผู้ใช้
