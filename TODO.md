# 📋 OmniCut Pro Studio — Todo กลาง

สมุดบันทึกรอบงานที่ **ยังไม่เสร็จ** ของโปรเจกต์นี้ — ทุกงานต้องผ่านไฟล์นี้ก่อนแตะโค้ด

| ไฟล์ | ใช้ทำอะไร |
| :--- | :--- |
| **TODO.md** (ไฟล์นี้) | งานที่ยังไม่เสร็จ + Backlog — เขียนแผนลงที่นี่ก่อนลงมือ |
| [HISTORY.md](file:///d:/Winona/Programmer/Capcut/HISTORY.md) | รอบที่ปิดแล้ว ย้ายบล็อกเต็มไปเก็บไว้ที่นั่น ห้ามแก้ย้อนหลัง |
| [TEMPLATE_MOTION_PLAN.md](file:///d:/Winona/Programmer/Capcut/TEMPLATE_MOTION_PLAN.md) | แผนยาวของงาน motion ข้อความ (Round 3–7) — เหตุผลและตัวเลขที่วัดมา |
| [.agents/rules/work_loop.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/work_loop.md) | กติกาว่าหนึ่งรอบทำยังไง ติ๊กยังไง ปิดรอบยังไง |

---

## สถานะรวม

- [ ] Round POST-3 — ซ่อมขั้นหลังอัปโหลดและแนบปกจาก Cover Studio (2026-09-06)
- [x] Round POST-3.14 — เปิด Cover Studio ผ่านพอร์ทัล, ใช้ชื่อโปรเจคเป็นชื่อปก, และย้ายชื่อโปรเจค Logitech ให้เป็น LOG01 (2026-09-07)
- [x] Round POST-3.15 — ให้ `/api/exports` เลือกปกตามชื่อโปรเจคก่อน fallback เดิม (2026-09-07)
- [ ] Round POST-3.16 — ปกแสดง 3:4 และแก้ Extension แนบปกข้อ 5 ให้เปิด dialog/อัปโหลดได้จริง (2026-09-07)
- [ ] Round POST-3.17 — ซ่อม path ปกที่หายก่อนข้อ 5 และยืนยันการส่งต่อไป TikTok (2026-09-07)
- [ ] Round POST-3.18 — make CDP cover upload notify TikTok React (2026-09-07)
- [x] Round POST-3.19 - restore generated cover in TikTok post modal (2026-09-07)

- [x] Round DOC-1 — ตรวจโค้ดและอัปเดตเอกสาร/กฎให้ตรงกับระบบปัจจุบัน
- [x] Round BUG-1 — แก้ปุ่มสร้างคลิปใหม่กดไม่ได้ (executeRender ใน useRenderJob)
- [x] Round 4 — per-word layout (static, พิสูจน์ว่าเหมือนเดิมเป๊ะ)
- [x] Round 5 — per-word animation (คำทยอยเข้าทีละคำ)
- [x] Round 6 — ช่องใหม่ที่ mirror ได้เป๊ะ
- [x] Round 7 — template v2 + แกลเลอรีที่ขยับได้
- [x] Round BUG-2 — แก้ข้อความและ Hook Header ซ้อนทับกันเป็นก้อนใน SequencePlayer
- [ ] Round POST-1 — Desktop Post Studio (ปก + ลากไฟล์ + แคปชั่น + ปิดวงจร Posted)
- [ ] Round POST-2 — TikTok auto-post extension (กลับมาทำตามคำสั่ง User: ขั้น 2–5 และส่งปก)
- [x] Round BUG-3 — ซ่อม angle ชนกัน (คลิปผิดสคริปต์) ใน Content Tracker Hub + ปุ่มปักตะกร้า TikTok
- [x] Round PROD-1 — เพิ่มช่องระบุ TikTok Product ID ตอนสร้างสคริปต์ใหม่ + Fallback ค้นหาด้วยชื่อสินค้า + Click-to-Edit Cart ID
- [x] Round TRK-1 — เพิ่มปุ่มส่งคลิปไป TikTok Studio พร้อม Modal ตรวจสอบ/ปักตะกร้า ในหน้า Tracker (ContentTrackerHub)
- [x] Round TRK-2 — ตารางจัดคิวโพสต์ประจำวัน (Daily Run Sheet) & จัดกลุ่มย่อการ์ด (Product Grouping / Quick Pills)
- [x] Round TRK-3 — บอร์ดหลักคลีนไร้ความรก (Today-Only Posted, คลังสคริปต์หยิบทำวันนี้ & การ์ดตัดต่อเสร็จแนวนอนกะทัดรัด)
- [x] Round COV-1 — สตูดิโอสร้างปกคลิปด่วน 9:16 & 3:4 (Auto Highlight Crop, Interactive Pan & Zoom Subtitle-Free, Dual Export)

**ปิดไปแล้ว** (บล็อกเต็มอยู่ใน [HISTORY.md](file:///d:/Winona/Programmer/Capcut/HISTORY.md)):
Round 1 รวม overlay เป็นโมเดลเดียว · Round 2 วางกฎรอบงาน · Round 3 ซ่อมฐาน+easing · Round DOC-1 อัปเดตเอกสาร · Round BUG-1 ซ่อมปุ่มสร้างคลิป executeRender · Round 4 per-word layout static · Round 5 per-word animation (word_stagger_ms) · Round 6 ช่องใหม่ที่ mirror ได้เป๊ะ (loop/out/skew) · Round 7 template v2 + แกลเลอรีที่ขยับได้ (8 templates + motion presets + inspector animated gallery) · Round BUG-2 ซ่อมข้อความ/Hook Header ซ้อนทับกันใน SequencePlayer · Round BUG-3 ซ่อม angle ชนกัน + ปุ่มปักตะกร้า TikTok ใน Content Tracker Hub · Round PROD-1 เพิ่มช่อง TikTok Product ID + Fallback ค้นหาด้วยชื่อ + Click-to-Edit Cart ID ย้อนหลัง · Round TRK-1 เพิ่มปุ่มส่ง TikTok Studio + Modal ตรวจสอบ/ปักตะกร้า ในหน้า Tracker · Round TRK-2 ตารางจัดคิวโพสต์ประจำวัน (Daily Run Sheet) & จัดกลุ่มย่อการ์ด (Product Grouping / Quick Pills) · Round TRK-3 บอร์ดหลักคลีนไร้ความรก (Today-Only Posted, คลังสคริปต์หยิบทำวันนี้ & การ์ดตัดต่อเสร็จแนวนอนกะทัดรัด)

> คู่ขนาน: [REFACTOR_PLAN.md](file:///d:/Winona/Programmer/Capcut/REFACTOR_PLAN.md) Phase 0–10 + Final เสร็จครบแล้ว (ทำโดย Codex) ไฟล์นั้นปิดงานแล้ว เก็บไว้อ้างอิง

---

## คำสั่งตรวจพื้นฐาน

```powershell
python -m compileall -q scripts
python -c "import scripts.api_server as app; print(len(app.app.routes))"
python -m pytest tests/ -q -p no:cacheprovider
Set-Location frontend
npm run build
npm test
```

งานที่มีผลต่อภาพในวิดีโอ ต้องรัน ffmpeg ดึงเฟรมจริงมาดูด้วย ตาม
[.agents/rules/preview_render_parity.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/preview_render_parity.md)

---



## Round POST-3.16 — แก้การแนบปกข้อ 5 และแสดงภาพปก 3:4

วันที่: 2026-09-07 · สั่งโดย: user · สถานะ: กำลังทำ

**ขอบเขต:** แก้เฉพาะขั้นตอนแนบปกของ Extension (HTML btn6/chk6 และ automation uploadCover) กับการแสดงปกใน TikTok modal; ล็อกขั้นตอน 1–4 ไม่แตะ

### Todo

- [x] ปรับ TikTok modal ให้ใช้ภาพปก 3:4 เมื่อมีไฟล์ 3:4 และส่ง path เดียวกันไปขั้นตอนปก
- [x] ทำให้ Extension ตรวจ/กด “แก้ไขหน้าปก” ได้จาก DOM จริง พร้อม fallback click ที่ไม่เปิด native file picker ก่อนเวลา
- [x] ทำให้ตัวค้นหา dialog, file input และปุ่มบันทึกครอบคลุมโครงสร้าง TikTok ปัจจุบัน โดยไม่เปลี่ยนขั้นตอน 1–4
- [x] เพิ่ม regression tests สำหรับ mapping ปก 3:4, export variant และ selector contract ของข้อ 5

### Gate

- [x] `node --check tiktok_autopost_extension/automation.js` และ `node --check tiktok_autopost_extension/background.js`
- [x] `node --test tiktok_autopost_extension/background.test.cjs`
- [x] `npm test` และ `npm run build` ใน `frontend/`
- [x] `python -m compileall -q scripts` และ `python -m pytest tests/test_api_tiktok_autopost.py -q -p no:cacheprovider --tb=short`
- [ ] ทดสอบหน้าเว็บจริง: เปิด TikTok modal → Cover Studio, บันทึก both, ตรวจ preview 3:4 และตรวจว่าข้อ 5 พบ dialog/file input (ไม่กด Post)

### Notes

- งานค้างใน working tree ก่อนเริ่ม: `scripts/db.py`, `scripts/product_store.py`, `tests/test_reconcile_transaction.py` จากงานอื่น; ห้ามแตะหรือ stage รวม
- Full regression: `pytest tests/` ผ่าน 864 tests และไม่มีไฟล์ขั้นตอน 1–4 ถูกแก้ในรอบนี้
- Live page navigation เคยยืนยันการเปิด Cover Studio ได้ แต่ยังไม่มี TikTok tab ที่เชื่อมผ่าน CDP สำหรับกด Extension ข้อ 5 จริง จึงยังไม่ติ๊ก gate live นี้จนกว่าจะทดสอบบน Chrome session ของผู้ใช้


## Round POST-3.17 — ซ่อม path ปกที่หายก่อนข้อ 5

วันที่: 2026-09-07 · สั่งโดย: user · สถานะ: กำลังทำ

**หลักฐานอาการ:** งาน pending จริงมี `cover_path: null` ทั้งที่มีไฟล์ `05_Covers_Thumbnails/Logitech Wave Keys_cover_3x4.jpg`; Side Panel จึงหยุดที่ guard ของข้อ 5 ก่อนส่งคำสั่งเปิด Cover Studio

**ขอบเขต:** แก้เฉพาะการ resolve/ส่งต่อ path ปกและผลลัพธ์ของขั้นตอนแนบปก ไม่แตะ runtime ของขั้นตอน 1–4 และไม่แตะปุ่มโพสต์

### Todo

- [x] เพิ่มการค้นหาปกจากชื่อโปรเจค/ชื่อสินค้าและเลือก 3:4 เป็นค่าเริ่มต้นเมื่อ `prepare` ไม่มี `cover_path`
- [x] ทำให้ `pending` ซ่อม `cover_path` ที่หายได้ก่อน Extension ทำข้อ 5
- [x] ส่ง `cover_path` ที่ backend ยืนยันกลับไปยัง Side Panel
- [x] เพิ่ม regression tests สำหรับ pending ที่ไม่มี path แต่มีปกชื่อสินค้า
- [x] คง guard/selector ของข้อ 1–4 และปุ่มโพสต์เดิม

### Gate

- [x] `python -m pytest tests/test_api_tiktok_autopost.py -q -p no:cacheprovider --tb=short` — 11 passed
- [x] `node --check tiktok_autopost_extension/sidepanel.js` และ `node --test tiktok_autopost_extension/background.test.cjs` — 8 passed
- [x] `python -m compileall -q scripts`
- [ ] ตรวจหน้า TikTok จริง: กดข้อ 5 แล้วพบ dialog, ใส่ปก, บันทึกปก โดยไม่กดโพสต์

### Notes

- หลักฐาน live ก่อนแก้: `/api/tiktok-autopost/pending` คืน `cover_path: null`; helper ใหม่ resolve ได้เป็น `05_Covers_Thumbnails/Logitech Wave Keys_cover_3x4.jpg` จาก `product_id=20260904233315_1`
- ตรวจ DOM TikTok จริงแล้วพบปุ่ม `แก้ไขหน้าปก` 1 จุด, `cover-editor-container` 1 จุด และ `input[type=file]` แบบซ่อน 1 จุด; การอัปโหลดไฟล์ผ่าน browser controller ถูกระบบควบคุมไฟล์บล็อก จึงยังไม่ติ๊ก live gate
- Full regression หลังแก้: `866 passed, 6 warnings`; ขั้นตอน 1–4 และปุ่มโพสต์ไม่ได้ถูกแก้


??????: 2026-09-07 ? ???????: user ? ?????: ???????

**??????????????:** ???? Cover Studio ???????; DOM ?????? `cover-editor-container` ??? `label.ImageUpload__uploadArea` ??????? `input[type=file]` ??????? ?????????????????? extension ??????????? TikTok ??????????????

**??????:** ??????????? 5 (`automation.js`/`background.js` ??? regression tests) ??????? runtime ?????? 1?4 ??????????????? Post

### Todo

- [ ] ??????????????????? CDP: ??? input ? ?? node ? ??????? ? ???? `files.length`
- [ ] ??? `input`/`change` event ???? `DOM.setFileInputFiles` ???????? React/TikTok ???????
- [ ] ???? error ????????????????????? TikTok ????????????????????? preview
- [ ] ????? regression contract test ?????? event dispatch ??????????????
- [ ] ??????????? Chrome: ???? preview ????????????????? ???????? ??? ???????? Post

### Gate

- [ ] `node --check tiktok_autopost_extension/automation.js`
- [ ] `node --test tiktok_autopost_extension/background.test.cjs`
- [ ] ????? flow ??????? 5 ?? TikTok Studio

### Notes

- browser controller ??? Codex ????????? `fileChooser.setFiles`; ???????????????????????????????? extension debugger ?????????
- ???? `frontend/src/components/ContentTrackerHub.jsx` ?????????????????????? ??????????? stage ????????

## Round POST-3.18 — make CDP cover upload notify TikTok React

Date: 2026-09-07; Requested by: user; Status: in progress

**Evidence before fix:** Cover Studio opens. The live DOM contains `cover-editor-container` and `label.ImageUpload__uploadArea` wrapping a hidden `input[type=file]`, but the extension does not make TikTok show the selected cover.

**Scope:** Only step 5 (`automation.js`/`background.js` and regression tests). Do not touch steps 1-4 or the Post action.

### Todo

- [x] Record each CDP boundary: locate input with DOM.getDocument/querySelectorAll -> set file -> verify files.length
- [x] Dispatch `input`/`change` after `DOM.setFileInputFiles` so TikTok React receives the file
- [x] Report actionable errors when TikTok rejects the file or preview does not appear
- [x] Add a regression contract test for event dispatch and file verification
- [ ] Run the real Chrome step 5 flow: preview the program cover and click Save without clicking Post

### Persistence follow-up

- [x] Persist generated cover paths on the selected product angle so a refresh can restore the cover.
- [x] Return cover path and media URL variants from the products API after reload.
- [x] Add deterministic backend regression coverage for cover persistence and refresh.
- [ ] Verify step 5 with the extension after the persisted cover is restored.

### Upload acceptance follow-up

- [x] Use the exact input object from the scoped Cover Studio query for CDP assignment and React notification.
- [x] Verify the post-assignment notification targets the same input object instead of a fresh global selector.
- [x] Add a regression test for TikTok replacing or resetting the hidden input, with one controlled retry.
- [ ] Re-run the real extension step 5 flow and confirm preview plus Save.

### Gate

- [x] `node --check tiktok_autopost_extension/automation.js`
- [x] `node --test tiktok_autopost_extension/background.test.cjs`
- [ ] Real step 5 flow in TikTok Studio

### Notes

- `node --test tiktok_autopost_extension/background.test.cjs`: 12 passed; the new exact-object and input-replacement regressions pass.
- The Codex browser controller blocks `fileChooser.setFiles`; real file injection must be exercised by the extension debugger.
- The follow-up now sends `DOM.setFileInputFiles` with the scoped Runtime `objectId`, dispatches events on that same object, and retries once if TikTok replaces the hidden input.
- `frontend/src/components/ContentTrackerHub.jsx` and `frontend/src/components/ProductToClip.jsx` contain unrelated working-tree changes; do not touch or stage them.

- [x] Round POST-3.21 - multi-day TikTok publishing queue (2026-09-07)

## Round POST-3.20 - edit generated cover inside OmniCut

Date: 2026-09-07; Requested by: user; Status: in progress

**Goal:** Let the user edit or regenerate the saved 3:4 TikTok cover directly in OmniCut Cover Studio, then keep the selected cover visible in the TikTok preparation modal after refresh.

**Scope:** Inspect the current TikTok modal -> Cover Studio handoff, saved cover hydration, and edit affordance. Keep steps 1-4 and the working extension upload flow unchanged.

### Todo

- [x] Reproduce the current modal state where a saved cover is not shown or the edit action is unclear.
- [x] Define the edit path: open Cover Studio with the existing cover context, allow frame/crop/text changes, and persist the resulting 3:4 path.
- [x] Add deterministic regression coverage for path-only saved covers and restoring the selected 3:4 variant after refresh.
- [x] Improve the cover card behavior so the action clearly says edit when a saved cover exists and create when it does not.
- [x] Merge matching `/api/exports` cover metadata when the live `/api/products` response omits saved cover fields.
- [x] Add a large 3:4 cover preview in the TikTok modal, with a direct path back to Cover Studio for editing.
- [x] Run frontend/backend tests and build.
- [ ] Verify the remaining live edit -> save -> refresh flow in the browser.

### Gate

- [x] `npm test` - 74 passed
- [x] `npm run build` - passed
- [x] backend suite - 869 passed, 6 existing warnings
- [ ] browser verification of edit -> save -> refresh -> modal

### Notes

- Implementation commit: `f2dbfed` (`fix: restore saved cover metadata in TikTok modal`).
- The live `/api/products` response currently returns null cover fields for this product while `/api/exports` contains the matching saved 3:4 cover. The client now merges that export metadata by project name/video reference and preserves any explicit angle cover.
- Browser check: clicking the saved 3:4 thumbnail opens a large preview, and `เปลี่ยนภาพปก` closes it and opens Cover Studio with the current cover loaded.
- Existing uncommitted changes belong to another workstream: `frontend/src/components/editor/EditorShell.jsx`, `frontend/src/components/editor/Timeline.jsx`, `frontend/src/components/editor/TimelineClip.jsx`, `frontend/src/lib/timelineMath.js`, `frontend/src/lib/timelineMath.test.js`, and the untracked screenshots `alt-drag-left.png`, `alt-drag-mid.png`, `clip-selected.png`, `timeline-loaded.png`; do not modify, delete, or stage them.
- Steps 1-4 and the extension upload implementation are frozen by the user.
## งานค้าง (Backlog)

### Round POST-3 — แผนก่อนลงมือ (2026-09-06 / อัปเดตแก้ขั้น 3)

#### POST-3.1 — แก้จากหลักฐานหน้าจอ TikTok จริง (2026-09-07)

- [x] Radio สินค้า: ลดการคลิกซ้ำเหลือครั้งเดียวต่อ fallback และยืนยัน `checked/aria-checked` ก่อนเดินหน้า
- [x] Dialog ตั้งชื่อตะกร้า: รอ input `TUXTextInputCore-input` และปุ่ม `เพิ่ม` แล้วตรวจ modal ปิด/ชิปสินค้าหลังเพิ่ม
- [x] ตั้งเวลา: รับค่า date/time จาก Side Panel และยืนยันค่าที่แสดงจริงก่อนรายงานสำเร็จ
- [x] ปก: รองรับ `label.ImageUpload__uploadArea` และ file input ที่อยู่ใน/ข้าง label ผ่าน `DOM.setFileInputFiles`
- [x] เพิ่ม regression test สำหรับ radio toggle, cart-name dialog, schedule payload และ cover selector

หลักฐาน: ภาพวันที่ 2026-09-07 แสดง `input.TUXRadioStandalone-input` ที่ยังไม่ถูกเลือก,
dialog ชื่อสินค้าใช้ `input.TUXTextInputCore-input` และปกใช้ `label.ImageUpload__uploadArea`
role=`button`; การทดสอบ live ยังไม่ปิดจนกว่าผู้ใช้จะ reload extension และยืนยันผลจริง

ผล gate: `node --check` ผ่านทุกไฟล์, `node --test tiktok_autopost_extension/background.test.cjs` = 7 passed,
`python -m pytest tests/test_api_tiktok_autopost.py -q -p no:cacheprovider` = 4 passed, 1 known warning.
ยังไม่ได้ทดสอบ TikTok จริงหลังแพตช์รอบนี้

#### POST-3.2 — แก้ตามผลทดสอบ Playwright จริง (2026-09-07)

- [x] ปรับการเลือกสินค้าให้คลิก wrapper ของ `TUXRadioStandalone` เมื่อ native input ไม่เปลี่ยน `checked` และต้องคลิกเพียงครั้งเดียว
- [x] ปรับตัวเลือกเวลาให้ใช้รายการชั่วโมง/นาทีของ TikTok (`.tiktok-timepicker-option-text`) และตัวเลือกวันที่ `.day.valid` แทนการหา text แบบ ISO ตรง ๆ
- [x] เอา fallback click ซ้ำของปุ่ม “ถัดไป” ออก เพื่อไม่ให้ dialog ถูกเปิด/ปิดซ้ำ
- [ ] ยืนยัน flow หน้าปกด้วย `div.edit-container` → `label.ImageUpload__uploadArea` → file input → บันทึก โดยไม่กดเผยแพร่
- [x] รัน node tests, backend test และตรวจ syntax หลังแก้

หลักฐาน Playwright รอบนี้: พบ input วันเวลาเป็น `readonly` (`09:35`, `2026-09-07`); เปิด picker สำเร็จและเลือกเวลา `10:10` กับวันที่ `2026-09-08` ได้จริงด้วยรายการ DOM ของ TikTok; เลือกสินค้า ID `1737230577125983588` ผ่าน wrapper แล้ว `checked=true`, เปิด dialog ตั้งชื่อและกด `เพิ่ม` สำเร็จจนเห็นชิป `Logitech Wave Keys`; คลิก `div.edit-container` เปิด Cover Studio และพบ `label.ImageUpload__uploadArea` 1 จุด แต่การส่งไฟล์ผ่าน Chrome Playwright ถูกระบบเบราว์เซอร์ปฏิเสธ (`fileChooser.setFiles: Not allowed`) จึงยังไม่ติ๊ก gate แนบไฟล์จนกว่าจะทดสอบผ่าน extension/CDP จริง

#### POST-3.3 — แก้ root ของ modal ซ้อน (2026-09-07)

- [x] ให้การค้นหาแถวสินค้าและปุ่ม “ถัดไป” เลือก `.product-selector-container`/dialog ล่าสุด แทน dialog เก่าที่ค้างอยู่ใน DOM
- [x] คงการคลิก wrapper radio เพียงครั้งเดียวและตรวจ `checked` หลังคลิก
- [x] ลดการสลับแท็บ Showcase เหลือ logical click เดียว ตัด synthetic pointer sequence ที่ซ้ำบน tab และ container
- [x] รัน syntax check, node regression และ backend test หลังแก้

หลักฐาน: ใน DOM จริงของ TikTok พบ dialog “เพิ่มลิงก์” เก่ายังคงอยู่พร้อม dialog “เพิ่มลิงก์สินค้า”; root เดิมจึงมีโอกาสค้นหาแถวผิด dialog แพตช์นี้บังคับ scope ไปที่ product selector ล่าสุด

#### POST-3.4 — แก้ข้อ 4/5 จากผลใช้งานหลังคอมมิต (2026-09-07)

- [ ] ทำให้ schedule เลือกค่าใหม่แล้วกดปุ่มยืนยันของ TikTok (`ตั้งเวลา`) ก่อนตรวจค่าที่แสดง และคืน error ถ้าปุ่มยืนยันไม่ทำงาน
- [ ] ทำให้ข้อแนบปกเปิด Cover Studio ได้แม้ปุ่มเป็น `div.edit-container` และเลือกไฟล์ input ที่อยู่ใน modal ล่าสุดเท่านั้น
- [ ] แสดงผลลัพธ์แต่ละขั้นใน Side Panel ให้ผู้ใช้รู้ว่าค่า schedule/cover ถูกส่งจริงหรือหยุดที่จุดใด
- [ ] รัน node regression, backend test และ syntax check

- [x] แก้ไขขั้น 3: สลับแท็บ "นำเสนอสินค้า" (Showcase Tab)
  - รองรับกรณีหน้าต่าง `< เพิ่มลิงก์สินค้า` เปิดค้างอยู่แล้ว ไม่ต้องกดย้อน "+ เพิ่ม" ซ้ำ
  - ค้นหาแท็บทั่วทั้ง document ไม่จำกัดที่ `document.querySelector('[role="dialog"]')` ตัวแรก
  - ทริกเกอร์อีเวนต์เมาส์เต็มรูปแบบ (pointerdown, mousedown, pointerup, mouseup, click) ทั้งบนแท็บและคอนเทนเนอร์ `[role="tab"]` พร้อม CDP native click `buttons: 1`
  - ตรวจจับสถานะแอคทีฟของแท็บอย่างแม่นยำด้วย `aria-selected`, คลาสแอคทีฟ, ช่องค้นหาที่แสดงผลจริง และ negative-check ป้องกันค้างที่ "ไม่มีสินค้าในร้านของคุณ"
- [x] แก้ไขขั้น 3: ค้นหาและเลือกสินค้าด้วย Product ID
  - กรอก Product ID, dispatch input/change, คลิกปุ่มแว่นขยาย และกด Enter
  - ค้นหาแถวสินค้าในผลลัพธ์: รองรับทั้งกรณีแถวมีรหัสสินค้า หรือแถวผลลัพธ์จากการค้นหารหัสเฉพาะ
  - คลิกเลือก Radio/Checkbox ของสินค้ารายการแรกในผลการค้นหา และยืนยันสถานะ checked
  - คลิก "ถัดไป" และคลิก "เพิ่ม" เพื่อจบขั้นตอนแนบสินค้า
- [x] ตรวจขั้น 2–5 ด้วย behavioral regression; แยกผลจำลองออกจากผลบน TikTok จริง
- [x] ส่ง cover_path จากรายการคลิปไป prepare และเพิ่มปุ่มแนบปกพร้อมภาพตัวอย่าง (แก้ cover upload ผ่าน CDP ไม่เปิด native Windows file dialog)
- [x] ซ่อมการเลือก Radio สินค้า และคลิกปุ่ม "ถัดไป" ใน .product-selector-container
- [ ] ป้องกันคำสั่งซ้อนกัน; ทำต่ออัตโนมัติแบบหยุดทันทีเมื่อขั้นก่อนหน้าไม่ผ่าน และให้ผู้ใช้กดโพสต์เองตามข้อกำหนดเดิม
- [x] ตรวจ syntax JavaScript, Node tests และ pytest ที่เกี่ยวข้อง
- [ ] ทดสอบ TikTok จริง: caption, สินค้าตรง ID, ปก, schedule

Notes: ปรับปรุงโค้ด Extension ให้ตรงกับ Element จริงจาก DevTools และพฤติกรรม TikTok Studio:
1. ใส่คำอธิบายก่อน แล้วเคาะเว้นวรรค 2 บรรทัด ตามด้วยแฮชแท็ก
2. สลับไปแท็บ "นำเสนอสินค้า" (Showcase) ให้สำเร็จก่อนค้นหา ป้องกันพิมพ์ในแท็บ "ร้านของฉัน"
3. เลือกสินค้าด้วย radio element: เลิกเซ็ต input.checked=true ล่วงหน้าเพื่อไม่ให้ขัด React SyntheticEvent พร้อมเรียก React fiber props, DOM clicks และ CDP native clicks ทั้งที่ปุ่มและแถวสินค้า
4. กดปุ่ม "ถัดไป" ด้านล่างขวาของตารางรายการสินค้า (.product-selector-container) พร้อม fallback native CDP click
5. หน้ารายการสุดท้าย: สั่งคลุมดำชื่อสินค้า และกดปุ่ม "เพิ่ม" (Add button สีแดง) จบขั้นตอนปักตะกร้า
6. แก้ปัญหาแนบภาพปก: ยกเลิกการคลิกที่ label uploadArea (ที่เคยเรียก Windows Explorer dialog) เปลี่ยนมาใช้ CDP DOM.setFileInputFiles ตรงที่ input[type=file] รอ preview แล้วกดบันทึก
ผ่านการทดสอบ `node --test tiktok_autopost_extension/background.test.cjs` (6/6 passed) และ `pytest` (149 passed)

รายการที่รู้แล้วว่าต้องทำ แต่ยังไม่ได้จัดเข้ารอบไหน
เจอของใหม่ระหว่างทาง → เขียนลงตรงนี้ทันที ห้ามทำเงียบๆ

### ยังไม่ได้ทดสอบ

- [ ] **กด generate เต็ม loop 1 รอบ** — Round 1 ยืนยันแล้วเฉพาะ ASS writer, เฟรม ffmpeg,
      save→reload, และ editor เปิดโปรเจกต์เก่า แต่ **ยังไม่เคยรัน `/api/render` ครบวงจร**
      (ต้องใช้วิดีโอดิบ + TTS key + เวลาหลายนาที)

### บั๊กที่เจอแล้วแต่ยังไม่ได้แก้

- [x] **วรรณยุกต์ไทยชั้นสองยุบ — แก้แล้ว (2026-09-07, ใช้ `/diagnose`)**: `เพิ่ง`→`เพีง`, `สิ่ง`→`สีง`
      - **ข้อสันนิษฐานเดิมผิด:** ไม่ใช่ libass mark positioning และไม่ใช่ครบทั้ง 6 ฟอนต์ตามที่บันทึกไว้ก่อนหน้า
      - **root cause จริง (พิสูจน์ด้วย differential render):** สร้าง harness render คำเดียวกันสองทาง — (a) ผ่าน
        libass/ffmpeg (production path) (b) ผ่าน PIL ImageFont (คนละ text shaper คนละ engine ไม่ผ่าน libass เลย)
        ผลออกมา**ยุบเหมือนกันเป๊ะทั้งคู่** → พิสูจน์ว่าไม่ใช่ libass แต่เป็นตัวไฟล์ฟอนต์เอง (ขาด GPOS mark-to-mark
        anchor สำหรับ mark ไทยซ้อนสองชั้น เช่น สระอิ + ไม้เอก)
      - เช็คครบทั้ง 6 ฟอนต์จริง (ไม่ใช่แค่เชื่อบันทึกเดิม): **Kanit/Prompt/Mitr/Itim พัง** ·
        **IBM Plex Sans Thai/Chakra Petch/Anuphan ถูก** (Noto Sans Thai ก็ถูกด้วย, ทดสอบเพิ่มนอก 6 ตัวเดิม)
      - ทดสอบ workaround ทาง text-level (ZWJ/ZWNJ คั่นระหว่าง mark, สลับลำดับ mark) — **ไม่ช่วยเลย** ยืนยันว่า
        เป็นปัญหาที่ font file เท่านั้น แก้จาก input text ไม่ได้จริง
      - **แก้แล้ว:** เอา Kanit/Prompt ออกจาก dropdown เลือกฟอนต์ใน `NewClipPanel.jsx:55-60` (เหลือ IBM Plex
        Sans Thai + Noto Sans Thai เท่านั้น) — ไม่แตะฟอนต์ที่ preset อื่น (`kanit_viral`/`prompt_modern`/
        `mitr_minimal`/`capsule_pill` ใน `typography_presets.json` ยังอยู่เผื่อใช้ทางอื่น แค่ไม่โผล่ใน dropdown นี้)
      - **เจอบั๊กเพิ่มระหว่างทาง (ไม่เกี่ยวกับ tone mark):** ตัวเลือก "Noto Sans Thai" ใน dropdown เดียวกันนี้
        ส่ง `font_name="NotoSansThai"` ซึ่ง**ไม่เคย match key ไหนใน `_load_font_family_map()` เลย** — fallback
        ไปที่ `DEFAULT_FONT_FAMILY` (IBM Plex) แบบเงียบๆ ไม่มี error คนเลือก Noto จะได้ IBM Plex แทนโดยไม่รู้ตัว
        แก้แล้วเพิ่ม alias `"NotoSansThai": "Noto Sans Thai"` ใน `_LEGACY_FONT_ALIASES`
        ([font_metrics.py:18-25](scripts/subtitle/font_metrics.py#L18))
      - เทสใหม่ `tests/test_font_family_mapping.py` (3 เคส) ยืนยัน mapping ทั้งสองจุด — ผ่านหมด,
        `pytest tests/ -q` 492 passed, `npx vite build` ผ่าน

### ปรับปรุงที่ยังไม่จำเป็นเร่งด่วน

- [ ] `frontend/src/lib/overlayModel.js` มี export ที่ยังไม่มีใครเรียก (`baseFsRatio`, `ASS_ALIGNMENT`,
      `overlayToLegacy*`) — เก็บไว้เพราะเทสใช้ แต่ควรทบทวนว่าจะคงไว้หรือตัด

---

## รอบงาน

รอบที่ยังไม่ปิด เรียงจากที่ทำอยู่ไปข้างหน้า

## Round POST-1 — Desktop Post Studio (ปก + ลากไฟล์ + แคปชั่น + ปิดวงจร Posted)

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: กำลังทำ

**เป้าหมาย:** จบงานโพสต์บนคอมได้ในหน้าเดียว — ปกสวยพร้อมอัป ไฟล์ลากได้ทันที แคปชั่นก็อปปุ่มเดียว
แล้วมาร์คโพสต์เสร็จไฟล์ย้ายออกเอง

> repo มี flow โพสต์บนมือถือครบ 5 ขั้นอยู่แล้ว (`MobileQuickPostPage.jsx`) แต่ฝั่งเดสก์ท็อปไม่มีเลย
> รอบนี้คือสร้างฝาแฝดฝั่งเดสก์ท็อป ไม่ใช่ฟีเจอร์ใหม่จากศูนย์

### ข้อจำกัดที่บังคับรูปทรงดีไซน์

- เว็บแอปในเบราว์เซอร์ **ยัดไฟล์เข้า drop zone ของ TikTok ไม่ได้** → ลดแรงเสียดทาน ไม่ใช่ยิงอัตโนมัติ
- **clipboard ถือได้ทีละอย่าง** → ไฟล์ใช้ `explorer /select` (ไม่กิน clipboard) เหลือ clipboard ให้แคปชั่น
- ย้ายไฟล์ไป `Posted/` แล้ว **คลิปจะหายจากแกลเลอรี** (`api_exports.py:26` glob แค่ `EXPORTS_DIR`) → ต้องแก้คู่กันในรอบเดียว

### POST-1.1 Cover Studio — ปก jpg ที่อัปได้จริง

- [x] สร้าง `scripts/api_covers.py` แยกไฟล์ใหม่ (ไม่แตะ `api_editor.py`/`api_schemas.py` ที่ Round 5 กำลังแก้)
      — `POST /api/covers/generate` ดึงเฟรม jpg 1080×1920 ด้วย ffmpeg input-seek + วาด 3-tier ด้วย Pillow
- [x] ไม่ reuse `drawOneOverlay` (ฟังก์ชันอิงเวลา) — ใช้ `resolve_hook_style` (pure python, มีอยู่แล้ว)
      + `AssetRegistry.fonts()` หา path ฟอนต์ + `PIL.ImageDraw.text(stroke_width=...)` วาดเอง เพราะปกคือภาพนิ่ง
- [x] เขียนผลลง `05_Covers_Thumbnails/` (โฟลเดอร์ที่ README/AGENTS อ้างถึงมาตลอดแต่ยังว่าง) — ทดสอบจริงแล้ว
- [x] UI เลื่อนเลือกเฟรม + ปุ่มสร้างปกใน ExportGallery — สร้างเป็นส่วน "ปกโพสต์ (Cover)" ใน `ExportActiveWorkbench`
      ([:672+](frontend/src/components/ExportGallery.jsx#L672)): range input scrub (seek `<video>` จริงตามค่า) +
      preview thumbnail + ช่องแบรนด์/รุ่น/ป้าย (ไม่บังคับ ซ่อนอยู่) + ปุ่มสร้าง — ต่อกับ `POST /api/covers/generate` แล้ว

### POST-1.2 ลากไฟล์ให้ง่ายที่สุด

- [x] `POST /api/reveal-file` ([api_videos.py](scripts/api_videos.py)) — `explorer /select,<path>` ทดสอบจริงแล้ว
      เปิด Explorer พร้อมไฟล์ถูกเลือกไว้, ปฏิเสธ path นอก `04_Exports`/`05_Covers_Thumbnails` ด้วย 403
- [x] **ซ่อมช่องโหว่แล้ว:** `open_folder` unknown key เดิมตกไป `Path(req.target)` ไม่เช็ค containment
      → ปฏิเสธด้วย 400 แทน (ยืนยันแล้วว่า caller จริงทั้ง 4 จุดส่งแค่ literal key `'exports'`)

### POST-1.3 Post Studio panel

- [x] แผงเดียวจบใน ExportGallery: ปก (สร้าง+พรีวิว) → เปิดไฟล์ใน Explorer (`onRevealFile`) →
      คัดลอกแคปชั่น (มีอยู่แล้ว) → เปิด TikTok Studio (`tiktok.com/tiktokstudio/upload` แท็บใหม่) →
      มาร์คว่าโพสต์แล้ว (`onMarkPosted`, ขึ้น chip "โพสต์แล้ว" แทนปุ่มเมื่อ `video.is_posted`)
      — handler จริงอยู่ที่ `ExportGallery.jsx` เรียก `generateCover`/`revealFile`/`markPosted` จาก `api.js`
      ยืนยัน backend ผ่าน `TestClient` จริง (ไม่ใช่แค่อ่านโค้ด): สร้างปก 1080×1920 จริงจากคลิป export จริง
      (read-only ต่อไฟล์ต้นทาง) + mark-posted ย้ายไฟล์ scratch จริงไป `Posted/` + บล็อกย้ายซ้ำถูกต้อง (403/404)
      + `npx vite build` ผ่าน + `pytest` 355 passed ไม่ตก
- [x] **ลบ fallback แคปชั่นหลอกแล้ว** ทั้ง 2 จุด ([:656-687](frontend/src/components/ExportGallery.jsx#L656), [:1637-1668](frontend/src/components/ExportGallery.jsx#L1637))
      — ไม่มี `tiktok_caption` → ขึ้นเตือนสีเหลือง + ปุ่ม "ผูกกับสินค้าก่อน" (เรียก `onOpenLinkModal`/`handleOpenLinkModal` ที่มีอยู่แล้ว)
      แทนที่จะแอบใส่ข้อความปลอมให้คัดลอกไปโพสต์โดยไม่รู้ตัว
- [x] ป้ายสเปก probe จากไฟล์จริงแทน string ตายตัว — `GET /api/exports/media-info` ([api_exports.py](scripts/api_exports.py))
      ใช้ `VideoEditor.get_media_info()` ที่มีอยู่แล้ว ([video_editor.py:359](scripts/video_editor.py#L359), เพิ่ม `codec_name`
      เข้า return dict — additive, เช็คแล้วทุก caller เดิม (`api_editor.py`, `shot_matching_stage.py`) ใช้ `.get()` ไม่พัง)
      ดึงแบบ on-demand ต่อคลิปที่กำลังดูเท่านั้น (ไม่ยัดเข้า `list_exports()` เพราะจะ ffprobe ทุกไฟล์ทุกครั้ง refresh)
      ทั้ง `ExportActiveWorkbench` และ modal เปลี่ยนมาใช้ `formatCodecSpec`/`formatResolutionSpec` แล้ว
      ยืนยันจริงด้วย `TestClient` กับคลิป export จริง → คืน `{width:1080, height:1920, fps:30, codec_name:'h264'}` ตรงของจริง
      + path traversal โดนบล็อก 403 + ไฟล์ไม่มีคืน 404 + `pytest` 356 passed + `npx vite build` ผ่าน

### POST-1.4 ปิดวงจร Posted

- [x] `POST /api/exports/mark-posted` ([api_exports.py](scripts/api_exports.py)) — ย้าย mp4 + webp + cover jpg
      ไป `04_Exports/Posted/` พร้อมกันทั้ง 3 ไฟล์ ทดสอบจริงด้วย scratch fixture แล้ว (ไม่แตะไฟล์จริงของ user)
- [x] `list_exports()` scan ทั้ง `Ready_to_post/` และ `Posted/` + ติด `is_posted` flag ต่อไฟล์
      ทดสอบแล้ว: หลังย้าย ไฟล์ยังหาเจอในแกลเลอรีพร้อม `is_posted=true` + `thumbnail_url` ตามไปถูกที่
- [x] ย้ายไฟล์ซ้ำ (จาก `Posted/` อีกที) ถูกบล็อก 403 ถูกต้อง
- [x] **เจอบั๊กจริงระหว่างเทส ไม่ใช่แค่ตามที่คาด:** `reconcile_existing_projects()`
      ([product_store.py:499](scripts/product_store.py#L499)) รักษา `posted`/`mobile_ready`
      **เฉพาะตอนหา mp4 เจอเท่านั้น** — ถ้าหาไม่เจอ (เพราะย้ายไป `Posted/` แล้ว และ
      `artifacts.mp4_video.path` ในแมนิเฟสต์ยังชี้ไปที่เก่า) จะ**รีเซ็ตกลับเป็น `in_production`
      และล้าง `video_url` เป็น `None` แบบไม่มีข้อยกเว้น** — เป็น regression จริงที่ POST-1.4 จะสร้างถ้าไม่แก้
      ซ่อมแล้ว 2 จุด: (1) ขยาย mp4 fallback scan ให้เช็ค `Posted/` ด้วย ไม่ใช่แค่ `Ready_to_post/`
      (2) เพิ่ม branch ไม่ downgrade สถานะ `posted`/`mobile_ready` ตอนหา mp4 ไม่เจอเลย
- [x] เขียนเทสยืนยันจริง `tests/test_reconcile_preserves_posted.py` (4 เคส, ใช้ `tmp_path`+`monkeypatch`
      ตาม `.agents/rules/testing_standard.md` ไม่แตะ `_Docs/products.json` จริง) — **4 passed**
      (เจอบั๊กในเทสตัวเองก่อนด้วย — `store_path` ไม่ตรงกับที่ `_seed()` เขียน ทำให้ 2 เคสแรก "ผ่าน" แบบไม่ได้รันจริง
      แก้แล้วรันใหม่ยืนยันว่าทดสอบ logic จริง ไม่ใช่ vacuous pass)

### POST-1.5 ซ่อมของเสียที่เจอระหว่างสำรวจ

- [x] `setToastMessage` ไม่มีอยู่จริง → เปลี่ยนเป็น `hideToast` (ของจริงจาก `useToast()`) — ยืนยันด้วย `npm run build` ผ่าน
- [x] QR ในแกลเลอรีซ่อมแล้วทั้ง 2 จุด — เขียน `buildQuickPostUrl()` ตัวเดียวใช้ร่วม ส่ง `pid`/`aid`/`hook`/`tiktok_caption`/`tiktok_hashtags`
      ครบตามรูปแบบของ `ContentTrackerHub.jsx:1289` แทนที่จะเป็นสำเนาพิการคนละแบบ
- [x] `mobileBaseUrl` อ่าน `status.mobile_url` ก่อนแล้ว (`App.jsx` ส่ง `status` prop เข้า `ExportGallery` เพิ่ม) เหมือน `ContentTrackerHub.jsx:618`

### Gate

- [x] `pytest tests/ -q` → **355 passed** · `npx vite build` ผ่าน (`npm test`/`oxlint` ยังไม่รัน — ไม่มี npm test script แยกในโปรเจกต์นี้)
- [ ] ปก jpg ที่ออกมา **อัปขึ้น TikTok ได้จริง** (ทดสอบด้วยมือ 1 คลิป) — รอพี่ทดสอบเอง
- [ ] กด reveal แล้ว Explorer เปิดพร้อมไฟล์ถูกเลือก (ล่าสุด curl ผ่านตอน backend ยังไม่ถูก restart — ดู Notes เรื่อง backend ค้าง ต้อง restart ก่อนคลิกจริงในเบราว์เซอร์ได้)
- [x] มาร์คโพสต์ → ไฟล์ย้ายไป `Posted/` → ยืนยันด้วย `TestClient` จริงกับไฟล์ scratch (ไม่แตะของจริง) — ย้ายสำเร็จ + ย้ายซ้ำโดนบล็อก 404
- [x] เทส: reconcile รันแล้วสถานะ `posted` ไม่ถูกรีเซ็ตทั้งที่ไฟล์ไม่ได้อยู่ `Ready_to_post` แล้ว — `test_reconcile_preserves_posted.py` 4 passed (ดู POST-1.4)
- [x] คลิปที่ไม่มี angle link → ขึ้นเตือน ไม่ใช่ก็อปแคปชั่นปลอม — ดู POST-1.5, ยืนยันด้วย build ผ่าน + อ่านโค้ด conditional

### ⚠️ งานขนาน — ตรวจแล้วเมื่อ 2026-09-05 (กฎ work_loop ข้อ 6)

อีก session กำลังทำ **Round 5 (per-word animation)** อยู่ ตรวจ `git status` + mtime แล้วพบ:

| POST-1 | ไฟล์ | ชนกับ Round 5 |
| :--- | :--- | :--- |
| 1.1 ปกใส่ข้อความ | `SequencePlayer.jsx` · `overlayModel.js` | 🔴 ชนหนัก — `drawOneOverlay` + `anim.word_stagger_ms` คือหัวใจ Round 5 |
| 1.1 ดึงเฟรม | `scripts/api_editor.py` | 🔴 ชน — แก้อยู่ตอนนี้ |
| 1.2 schema | `scripts/api_schemas.py` | 🟡 เบา (เพิ่มคลาสใหม่) |
| 1.3 api client | `frontend/src/api.js` | 🟡 เบา (เพิ่ม export) |
| 1.1 แปลง jpg · 1.2 reveal · 1.3 แผง · 1.4 Posted · 1.5 บั๊ก | `video_editor.py` `api_videos.py` `ExportGallery.jsx` `api_exports.py` `product_store.py` | ✅ ไม่ชน |

**ลำดับที่ตกลง:** ทำชุดที่ไม่ชนก่อน (1.2 · 1.3 · 1.4 · 1.5 · แปลงปก jpg) — ครอบความเจ็บหลักได้ ~80%
ส่วนปกแบบเลือกเฟรม+ใส่ข้อความ รอ Round 5 ปิดก่อน

**แก้ดีไซน์ให้ชนหายไปเลย:** เดิมคิดจะ reuse `drawOneOverlay` วาดข้อความบนปก — **ผิดฝาผิดตัว**
มันเป็นฟังก์ชันอิงเวลา (animation, `tRel`, in/loop/out) แต่ปกคือภาพนิ่งเฟรมเดียว
ให้ใช้ `TextLookPreview.jsx` (DOM ภาพนิ่ง Round 5 ไม่แตะ) หรือวาดฝั่ง server จาก `TextLook` ตัวเดียวกันแทน

### Notes

- ตัดทิ้ง: ลากจากในแอปตรงเข้า TikTok (Chrome `DownloadURL` ลงได้แค่ Explorer/desktop ไม่เข้า drop zone เว็บอื่น) · ก็อปไฟล์ลง clipboard (แย่ง clipboard จากแคปชั่น)
- ~~ตัดทิ้ง: browser automation~~ (ทบทวนแล้ว 2026-09-05 — ดู Round POST-2: พี่ยอมรับความเสี่ยงหลังเทียบทางเลือก ออกแบบให้เสี่ยงน้อยสุดในบรรดาทางที่ทำได้จริง)
- ตัดทิ้งถาวร: TikTok Content Posting API (ก่อนผ่าน audit โพสต์ได้แค่ draft/private)
- **PostLog ยังไม่ทำในรอบนี้** — `scripts/post_log.py` + API + client wrapper (`api.js:159-162`) สร้างเสร็จแล้วแต่ caller เป็นศูนย์ ถ้าอยากได้วงจรวัดผลค่อยเปิดรอบใหม่
- **เจอกลางทางตอนจะเทสจริงผ่านเบราว์เซอร์:** backend ที่รันอยู่ที่ port 8000 เป็นโปรเซสค้าง (63 routes ไม่มี
  `/api/covers/generate`/`/api/reveal-file`/`/api/exports/mark-posted` เลยสักตัว) — `start_app.bat` ตั้ง
  `FASTAPI_RELOAD=false` ไว้โดยตั้งใจ (เพื่อ render นิ่ง) โค้ดใหม่เลยไม่โดนโหลด ต้อง restart เอง
  **ฆ่าโปรเซส (taskkill) โดน sandbox classifier บล็อก** — ต้องให้พี่รัน `start_app.bat` เอง (มัน kill+relaunch ให้ในตัว)
  ก่อนถึงจะกด reveal/สร้างปก/มาร์คโพสต์ **ผ่านเบราว์เซอร์จริง** ได้ ระหว่างนี้ยืนยัน logic ทุกเส้นทางผ่าน
  `fastapi.testclient.TestClient(app)` แทน (import โค้ดปัจจุบันตรงๆ ไม่ผ่านโปรเซสค้าง) — เทียบเท่ากันในแง่ความถูกต้องของ backend logic

---

## Round POST-2 — TikTok auto-post extension (เสี่ยง)

วันที่: 2026-09-05 · สั่งโดย: user · สถานะ: กำลังทำ — ⚠️ **แครชยังเป็นปริศนา ไม่ใช่ปิดถาวรแล้ว** (POST-2.12
ด่วนสรุปผิด ดู POST-2.13) ตอนนี้มี checklist ทีละขั้นให้พี่ไล่ทดสอบเองว่าขั้นไหนทำให้พัง

**เป้าหมาย:** กดปุ่มเดียวในแอป ให้ extension เติมไฟล์+ปก+แคปชั่นลงหน้าอัปโหลด TikTok ในเบราว์เซอร์ที่ login อยู่แล้ว
ไม่ต้องลาก ไม่ต้องพิมพ์เอง — **สถานะจริงตอนนี้:** แครชเกิดแบบไม่ 100% แน่นอน (flaky) แม้แต่ขั้น "อัปโหลดไฟล์อย่างเดียว"
เอง — บางรอบพังบางรอบผ่าน สาเหตุแท้จริงยังไม่ชัด ต้องไล่ทดสอบทีละขั้นด้วย checklist ใหม่ก่อน — รายละเอียด เหตุผล
และหลักฐานความเสี่ยงทั้งหมดอยู่ที่
[TIKTOK_AUTOPOST_PLAN.md](file:///d:/Winona/Programmer/Capcut/TIKTOK_AUTOPOST_PLAN.md)

> ⚠️ พี่ยืนยันรับความเสี่ยงผิด ToS/บัญชีโดนจำกัดแล้ว (2026-09-05) หลังเทียบทางเลือกทั้งหมด
> ดีไซน์เลือกใช้เบราว์เซอร์จริงที่ login อยู่แล้ว ไม่เปิดแยก ไม่ปลอมลายนิ้วมือ กดครั้งเดียวต่อโพสต์ — เสี่ยงน้อยสุดในบรรดาทางที่ทำได้จริง

### Todo

- [ ] **ทดสอบ 4 ข้อใน `TIKTOK_AUTOPOST_PLAN.md` §3 ก่อน (ต้อง login บัญชีจริง — พี่ทำเอง ผมทำแทนไม่ได้)**
      สำคัญสุด: TikTok Studio อัปปกเองได้ไหม (ถ้าได้ = ไม่ต้องพึ่ง Cover Studio ของ POST-1 สำหรับเส้นทางนี้)
      — **บล็อกจริง:** ทุก selector ใน `background.js` เป็นค่าเดา (จากเอกสาร community ใน plan) ยังไม่เคยรันกับ
      หน้า TikTok Studio จริงสักครั้ง รอผลข้อนี้ก่อนถึงจะรู้ว่าต้องแก้ selector ตรงไหน
- [x] สร้าง Chrome extension (Manifest V3) — `tiktok_autopost_extension/` (manifest.json, background.js,
      popup.html/js) — background service worker ถือ `chrome.debugger` session, ยืนยัน syntax ผ่านแล้ว
      (`node --check` ทั้ง 2 ไฟล์ js + `json.load` manifest) — **ยังไม่เคย attach กับแท็บ TikTok Studio จริง**
      เพราะต้องมี browser ที่ล็อกอินไว้แล้วซึ่งผมไม่มี ดู Todo ข้อแรก
- [x] `DOM.setFileInputFiles` ใส่ mp4 (+ cover jpg แบบ best-effort ถ้ามี input ที่ 2) — เขียนไว้ใน
      `findFileInputNodeId`/`setFileInput` ของ `background.js` — selector `input[type="file"]` **ยังไม่ยืนยัน**
      ว่าตรงกับของจริง (ทำเครื่องหมาย UNVERIFIED ไว้ในโค้ดทุกจุดที่เดา)
- [x] `Input.insertText` ใส่แคปชั่นใน contenteditable — `typeCaption()` focus ก่อนแล้วค่อย insertText ผ่าน
      CDP Input domain (ไม่ใช้ `.textContent =` ตรงๆ เพราะ framework ของ TikTok จะไม่เห็น event)
- [x] endpoint ฝั่งแอป: `POST /api/tiktok-autopost/prepare` ([api_tiktok_autopost.py](scripts/api_tiktok_autopost.py))
      ยืนยันจริงด้วย `TestClient`: prepare→pending→clear lifecycle ผ่าน, path traversal โดนบล็อก 403,
      pending ก่อน prepare คืน 404 ถูกต้อง — **หมายเหตุดีไซน์:** ไม่ต่อตรงกับ `mark-posted` อัตโนมัติ (ตามที่ระบุไว้เดิม)
      เพราะ extension ไม่รู้ว่า TikTok โพสต์สำเร็จจริงหรือยัง (ไม่มีวิธีตรวจจาก DOM ที่มั่นใจได้) — พี่กด "มาร์คว่าโพสต์แล้ว"
      เองในแอปหลังเห็นว่าโพสต์ขึ้นจริงบน TikTok ปลอดภัยกว่า
- [x] toggle เปิด/ปิดฟีเจอร์นี้ใน `SystemSettings.jsx` (แท็บ Engine) — **ปิดเป็นค่าเริ่มต้น** (`localStorage`
      key `omnicut_tiktok_autopost_enabled`, อ่านค่าเริ่มต้น `false`) ยืนยันด้วย `npx vite build` ผ่าน
- [x] แถบ "กำลัง debug" ต้องเห็นชัดทุกครั้ง ห้ามพยายามซ่อน — **ไม่ต้องเขียนโค้ดเพิ่ม** Chrome บังคับแสดงเองทันทีที่
      `chrome.debugger.attach()` ถูกเรียก ซ่อนไม่ได้จาก extension ฝั่งเราอยู่แล้วโดยดีไซน์ของเบราว์เซอร์เอง
- [ ] **POST-2.1 ปรับแต่งแคปชันและปักตะกร้าอัตโนมัติ (User ร้องขอ 2026-09-06)**:
      - แก้ ReferenceError: `waitForCaptionEditor is not defined` ที่ทำให้สคริปต์หยุดทำงานก่อนล้างชื่อไฟล์/พิมพ์แคปชัน/ปักตะกร้า
      - ล้างชื่อไฟล์ต้นทางที่ TikTok เติมให้อัตโนมัติ (`document.execCommand('selectAll')` + `'delete'`) แล้วพิมพ์แคปชันจริง + แฮชแท็กโดยใช้ `Input.insertText` คู่กับ Enter (`Input.dispatchKeyEvent`) พร้อมเลื่อนเคอร์เซอร์ไปจุดเริ่มต้น (`collapse(true)`) และรีเซ็ต `scrollTop = 0` ทุกคอนเทนเนอร์เพื่อให้แคปชันด้านบนไม่หลุดเฟรม
      - แนบลิงก์สินค้า (ปักตะกร้า): คลิก `+ เพิ่ม` -> ในหน้าต่างประเภทลิงก์กด `ถัดไป` -> สลับแท็บ `นำเสนอสินค้า` -> ค้นหาด้วย TikTok Product ID (`1737088044189583209`) -> ติ๊กเลือกวิทยุ -> กด `ถัดไป` -> กด `เพิ่ม`
      - รองรับการตั้งเวลาโพสต์ (Schedule): ค้นหาปุ่มเลือก `ตั้งเวลา` (ตามหน้าตาจริงของภาษาไทยใน TikTok Studio) เพื่อให้ผู้ใช้กำหนดวันเวลาปล่อยคลิปได้ตามแผน
      - บันทึก TikTok Product ID (`1737088044189583209`) ลงใน `_Docs/products.json` และส่งผ่าน `api_exports.py` อัตโนมัติ
- [x] **POST-2.2 แก้ปัญหาสลับแท็บนำเสนอสินค้าไม่ได้ และแก้คำอธิบายหาย/ขึ้นแต่แฮชแท็ก (User ร้องขอ 2026-09-06)**:
      - [x] **แก้สลับแท็บ "นำเสนอสินค้า"**: ปรับปรุง selector ใน `attachProductLink` (ฟังก์ชัน `switchToShowcaseTab`) กรอง element ที่มีข้อความ "ร้านของฉัน" ออกทั้งหมดเพื่อไม่ให้โดน parent container หลอก, ค้นหา leaf element ที่มีข้อความ "นำเสนอสินค้า" / "Showcase", คลิกด้วยทั้ง DOM mouse events (`pointerdown`/`mousedown`/`mouseup`/`click`) และ native CDP `Input.dispatchMouseEvent` ที่พิกัด bounding rect พร้อมตรวจจับว่าแท็บเปลี่ยนจริง (เช่น ช่องค้นหาสินค้าปรากฏ) มี retry loop สูงสุด 5 ครั้ง
      - [x] **แก้ปัญหาคำอธิบายไม่มา / มาแต่แฮชแท็ก / แฮชแท็กกลืนคำอธิบาย**:
        - ใน `background.js` ฟังก์ชัน `typeCaption`: ลบการส่ง `type: 'char', text: '\r'` ซึ่งเป็น Carriage Return ที่ทำให้เคอร์เซอร์เด้งกลับไปที่จุดเริ่มต้น (ทำให้พิมพ์แฮชแท็กนำหน้าคำอธิบายและเชื่อมติดกัน)
        - ใช้ `document.execCommand('insertText', false, text)` ในการแทรกข้อความแบบรวดเดียวพร้อมเว้นวรรคและขึ้นบรรทัดใหม่อย่างเป็นธรรมชาติ โดยวางโครงสร้างเป็น: คำอธิบายคลิป (บรรทัดบน) -> เว้นวรรค 2 บรรทัด (`\n\n`) -> แฮชแท็ก (บรรทัดล่าง)
        - เพิ่ม fallback ให้ `scripts/api_exports.py` และ `ExportGallery.jsx` ให้ดึงคำอธิบายจาก `hook_title` หรือชื่อคลิปอัตโนมัติหาก `tiktok_caption` ว่าง
      - [x] **ปรับปรุง Popup Extension UI**:
        - เพิ่มช่องแสดงและแก้ไข "คำอธิบายคลิป (Caption)" และ "แฮชแท็ก (Hashtags)" ให้ผู้ใช้เห็นบน Popup ก่อนกดส่งคำสั่ง สามารถแก้ไขหรือตรวจทานได้ทันที
        - รองรับการดึงคำอธิบายและแฮชแท็กจาก backend `/api/tiktok-autopost/pending` มาแสดงในฟอร์ม Popup อัตโนมัติ
        - เพิ่มปุ่ม "📝 เติมเฉพาะคำอธิบายและแฮชแท็ก" (กรณีผู้ใช้ต้องการเติมแค่ข้อความ ไม่ปักตะกร้าซ้ำ)
      - [x] ผ่าน Gate: `node --check` ทุกไฟล์ js ผ่าน, `npm run build` ผ่าน, `pytest tests/ -q` 357 passed
- [x] **POST-2.3 ซ่อมบั๊กคลิกโดนเมนู Sidebar 'โพสต์' และเพิ่มระบบรออัปโหลดครบ 100% (User ส่งคลิปวิดีโอยืนยัน 2026-09-06)**:
      - [x] **ต้นตอจากคลิป test cap.mp4**: วิดีโอยังอัปโหลดอยู่ที่ 29.36% แต่ extension รันต่อจนถึง `clickPostButton` ซึ่งหาปุ่ม `โพสต์` ที่ไม่ disabled — ปุ่มโพสต์จริงของฟอร์มถูก disable อยู่ จึงไปจับโดนปุ่มเมนูนำทาง `div[role="button"]` บน Sidebar ด้านซ้ายที่มีชื่อว่า `โพสต์` (เพื่อนำทางไปหน้ารายการโพสต์ `โพสต์ 24`) ทำให้เบราว์เซอร์พยายามเปลี่ยนหน้า และ TikTok เด้งหน้าต่างเตือน *"คุณแน่ใจหรือไม่ว่าต้องการออก? ความคืบหน้าและการเปลี่ยนแปลงของคุณจะไม่ได้รับการบันทึก"*
      - [x] **แก้ `clickPostButton`**:
        - กรองข้ามองค์ประกอบทั้งหมดที่อยู่ใน `aside, nav, header, [class*="sidebar"], [class*="menu"]` โดยเด็ดขาด
        - ค้นหาเฉพาะแท็ก `<button>` ของฟอร์มเท่านั้น (ห้ามใช้ `div[role="button"]` ของเมนูนำทาง)
        - เรียก `waitForUploadComplete` ก่อนกดเสมอ เพื่อให้มั่นใจว่าปุ่มของ TikTok ปลดล็อกและพร้อมกดจริง
      - [x] **ปรับปรุง `waitForUploadComplete` ตรวจจับหลายสัญญาณ (Multi-Signal)**:
        - ตรวจจับเปอร์เซ็นต์ที่ยังวิ่งไม่ถึง 100% (เช่น `29.36%`)
        - ตรวจจับคำว่า `Uploading...` บนหน้าจอมือถือพรีวิว
        - ตรวจจับข้อความขนาดไฟล์ (เช่น `7.76MB/26.43MB` หรือ `เหลือ X วินาที`)
        - ตรวจจับสถานะปุ่ม `โพสต์` / `กำหนดเวลา` ว่ายัง disabled อยู่หรือไม่
      - [x] **ตัดโค้ดหยอดปกใส่ `nodeIds[1]` (ซึ่งตรงกับปุ่ม "แทนที่วิดีโอ") ออก 100%** ป้องกันการ trigger ให้ TikTok คิดว่าจะเปลี่ยนคลิปใหม่
      - [x] ผ่าน Gate: `node --check` ทั้งสองไฟล์ผ่าน, `pytest tests/ -q` 367 passed
- [x] **POST-2.4 เพิ่มการ์ดกันสำหรับ dialog "แน่ใจหรือไม่ว่าต้องการออก" (ดูคลิป test cap.mp4 ซ้ำอีกรอบ 2026-09-06)**:
      - **หมายเหตุสำคัญ:** คลิปที่พี่ส่งมาดูรอบนี้เป็นคลิปเดียวกับที่ POST-2.3 ใช้วินิจฉัยบั๊ก "กดโดนเมนู Sidebar
        'โพสต์'" ไปแล้ว — โค้ดตอนนี้มี fix ของ POST-2.3 อยู่แล้ว (กรอง `isNav()` + รอ `waitForUploadComplete` ก่อนกด)
        ยังไม่มีคลิปทดสอบใหม่หลัง fix นั้นเข้ามายืนยันว่า dialog นี้หายไปจริงหรือยัง — เพิ่มตัวนี้เป็น**เกราะเสริม**
        เผื่อ dialog ยังโผล่แม้กดปุ่มถูกต้องแล้ว (SPA บาง framework มี "leave guard" ทำงานแม้ navigate หลังสำเร็จจริง)
      - เพิ่ม `dismissLeaveConfirmDialogIfPresent(send)` ใน `background.js` — poll หา heading ที่มีข้อความ
        "แน่ใจหรือไม่ว่าต้องการออก" / "Are you sure you want to leave" นาน 8 วิ ถ้าเจอกดปุ่ม "ออก"/"Leave" ให้
        ถ้าไม่เจอเลยคืน `false` เฉยๆ **ไม่ throw** เพราะไม่ยืนยันว่า dialog นี้โผล่ทุกครั้งหรือบางครั้ง
      - เรียกต่อจาก `clickPostButton(send)` ใน `runAutopost()` เฉพาะตอน `autoClickPost` เท่านั้น — ผลลัพธ์ใส่ใน
        response เป็น `leaveDialogDismissed` ให้ popup โชว์คำเตือนถ้าเจอ dialog ค้างแต่กดไม่ผ่าน (ให้พี่กดเอง)
      - ผ่าน Gate: `node --check` ทั้ง `background.js`/`popup.js` ผ่าน — **ยังไม่ได้ทดสอบกับ TikTok Studio จริงรอบใหม่**
        รอพี่ทดสอบคลิปใหม่แล้วส่งคลิปมาดูอีกรอบ ว่า dialog ยังโผล่ไหมหลัง POST-2.3 fix
- [x] **POST-2.5 เจอ root cause จริงของแท็บแครช (ดูคลิป test cap2.mp4, 2026-09-06)**:
      - เช็ค checkbox fix (POST-2.4-ก่อนหน้า) แล้ว: **ทำงานถูก** — auto-post ไม่ติ๊ก ระบบเติมข้อมูล+ปักตะกร้าสำเร็จ
        ไม่ได้กด Post ให้เองแล้ว ตรงตามที่พี่ขอ
      - **ปัญหาใหม่ที่เจอในคลิปเดียวกัน:** แท็บ Chrome เองแครช (หน้า "เกิดข้อผิดพลาด" native ของ Chrome ไม่ใช่ error
        จากโค้ดเรา) เปิด console เจอ `NotFoundError: Failed to execute 'removeChild' on 'Node': The node to be
        removed is not a child of this node` จาก `lib-react.cad72241.js` (React internals ของ TikTok เอง)
      - **ต้นตอที่เจอจริง (ตรวจโค้ดละเอียด):** 3 จุดใน `background.js` ยิง click event ซ้ำซ้อนใส่ element เดียวกัน
        มากเกินจำเป็น — `attachProductLink`'s `trigger()` ยิง `.click()` แล้วต่อด้วย `dispatchEvent` อีก 3 ตัว
        (mousedown/mouseup/click) = handler ทำงาน 2 รอบต่อ 1 คลิกที่ตั้งใจ, ปุ่มค้นหาใน step 4 ก็ double-click
        เหมือนกัน, ที่หนักสุดคือ `switchToShowcaseTab`'s `triggerEvents()` ยิง **5 synthetic events + .click()**
        ใส่ **3 element พร้อมกัน** (target + parentElement + tabParent) แล้วยังมี CDP native mouse click ต่อท้าย
        อีกแบบไม่มีเงื่อนไข ทุก retry (สูงสุด 5 รอบ) = สูงสุดราวๆ 30+ click event ยิงใส่ DOM หยิบมือเดียวในไม่กี่วินาที
        — ปริมาณ event ขนาดนี้ทำให้ React ของ TikTok ตามการเปลี่ยนแปลง DOM ตัวเองไม่ทัน จน fiber tree หลุด sync จริง
        (สอดคล้องกับ error `removeChild` ที่เจอ)
      - **แก้แล้ว:** ตัดทุกจุดเหลือ **1 คลิกต่อ 1 ความตั้งใจ**:
        - `attachProductLink`'s `trigger()` เหลือแค่ `.click()`
        - search icon (step 4) เหลือแค่ `.click()` ครั้งเดียว
        - `switchToShowcaseTab` เขียนใหม่ทั้งฟังก์ชัน: แยก `isActive()` เช็คสถานะออกมาเป็นฟังก์ชันย่อย, แต่ละ
          attempt ยิง `.click()` ทาง JS ครั้งเดียวบน element เป้าหมายตัวเดียว (ไม่แตะ parent/tabParent อีกแล้ว) →
          รอ 700ms ให้ React render จริงก่อนเช็คซ้ำ → **ถ้ายังไม่ติด** ค่อยลอง CDP native mouse click เป็นทางเลือกสำรอง
          (ไม่ใช่ยิงคู่กันทุกครั้งเหมือนเดิม) → รอ 700ms เช็คอีกที ถึงจะ retry รอบถัดไป
      - `node --check background.js` ผ่าน, `pytest tests/ -q` 372 passed (ไม่กระทบฝั่ง python)
      - **ยังไม่ได้ทดสอบกับ TikTok Studio จริงรอบใหม่หลัง fix นี้** — รอพี่ทดสอบแล้วส่งคลิปมาดูอีกรอบ ว่าแท็บยังแครชไหม
      - **แนวทางสำรองถ้ายังแครชอีก** (ยังไม่ทำ เพราะยังไม่มีหลักฐานว่าจำเป็น): reload แท็บ TikTok Studio ให้ fresh
        ก่อนเริ่มทุกรอบ `runAutopost()` (ไม่ใช้กับ `runAttachProductOnly` เพราะ flow นั้นสมมติว่าอัปโหลดมือไว้แล้ว)
- [x] **POST-2.6 ยังแครชอยู่หลัง POST-2.5 (screenshot 2026-09-06, ไม่มี leave-dialog ขึ้นรอบนี้)**:
      - หน้าตาแครชเหมือนเดิมทุกอย่าง แต่รอบนี้ **ไม่ขึ้น dialog "แน่ใจจะออก" ก่อนแครช** — บ่งชี้ว่าจุดแครชขยับมา
        **เร็วขึ้น** ในลำดับงาน (แครชก่อนจะไปถึงจุดที่เคยขึ้น dialog) สอดคล้องกับที่ POST-2.5 แก้จังหวะ retry ใน
        `switchToShowcaseTab` — ยังไม่มีคลิป/console log ใหม่ยืนยันว่าแครชเกิดตอนขั้นไหนแน่ๆ
      - **เพิ่มการป้องกันอีกชั้น (ยังไม่ยืนยันว่าเป็น root cause แท้จริง เพราะไม่มีหลักฐานใหม่):** สังเกตว่า
        `attachProductLink`/`switchToShowcaseTab` ค้นหา element ด้วย `document.querySelectorAll(...)` แบบกวาด
        ทั้งหน้าเว็บซ้ำๆ หลายจุด (บางจุดใน loop retry สูงสุด 5 รอบ) บนหน้า React ที่หนักอยู่แล้ว (TikTok Studio มี
        internal error/warning เพียบอยู่ก่อนแล้วจาก AR/effects engine ของเขาเอง เช่น "VideoFrame was garbage
        collected without being closed") — จำกัดขอบเขตการค้นหาให้แคบลงเหลือแค่ `[role="dialog"]` (fallback เป็น
        `document` ถ้าไม่เจอ dialog เลย ไม่แย่ไปกว่าเดิม) ในทุกจุดของ `attachProductLink` (step 2/4/5/6/7) และ
        `switchToShowcaseTab` — ลดจำนวนรอบสแกน DOM ทั้งหน้าเว็บซ้ำๆ ลงไปมาก โดยเฉพาะจุดที่อยู่ใน retry loop
      - `node --check` ผ่าน, `pytest` 372 passed
      - **ยังไม่ยืนยันว่าหายแครชจริง** — ต้องขอคลิปใหม่ + เปิด DevTools Console (กด F12 → แท็บ Console → ติ๊ก
        "Preserve log") **ก่อน**เริ่มกดปุ่มในแอป เพื่อจับ error ตัวจริงที่เกิดขึ้น**ก่อน**แท็บแครชจริงๆ (ตอนนี้เห็นแค่
        error ที่ค้างอยู่ใน log หลังแครชไปแล้ว ไม่ชัดว่าตัวไหนคือตัวกระตุ้นจริง)
      - **ข้อสังเกตเพิ่ม:** TikTok Studio หน้านี้เองมี error/warning หลักร้อย-พันสะสมอยู่แล้วจาก engine internal ของเขา
        (ไม่เกี่ยวกับเรา) — เป็นไปได้ว่า tab renderer process ใกล้ชนเพดานหน่วยความจำอยู่แล้วจากฝั่ง TikTok เอง
        พี่ลอง**ปิด Chrome ทั้งโปรแกรมแล้วเปิดใหม่** (ไม่ใช่แค่ reload แท็บ) ก่อนทดสอบรอบหน้า อาจช่วยได้ถ้าเป็นเรื่อง
        หน่วยความจำสะสมจริง
- [x] **POST-2.7 ทำ isolation test แยกตัวแปรสำเร็จ + เจอ root cause จริงแล้ว (2026-09-06)**:
      - **ผลทดสอบเด็ดขาด:** พี่อัปโหลดไฟล์เดิม (`test cap3.mp4`) ด้วยมือล้วนๆ **ไม่เปิด/ไม่แตะ extension เลย** →
        **ไม่แครช** — confirmed 100% ว่า crash เกิดจาก **automation ของเราเอง** ไม่ใช่บั๊กฝั่ง TikTok/ไฟล์วิดีโอ
        (ก่อนหน้านี้ผมอ่าน console log ผิด คิดว่าเป็น TikTok's own effect engine crash เอง — isolation test นี้
        พิสูจน์ว่าคิดผิด ต้องขอบคุณพี่ที่ทดสอบให้ชัวร์)
      - **เจอ signal สำคัญจากพี่โดยตรง:** ปุ่ม "แก้ไขหน้าปก" ("ปก" section) **คลิกได้ก็ต่อเมื่ออัปโหลดเสร็จ 100% จริง**
        เท่านั้น — ตรงกับ console log ที่เห็นตอนแครช (`clip-forge-effect-sd...`, `Worker: Setting canvas`,
        `EffectWebSDK setOffscreenCanvas`) ซึ่งคือ TikTok เองกำลังสร้างปก/thumbnail ด้วย AR effects engine —
        **สรุปได้ว่า:** `waitForUploadComplete()` เดิมใช้ text-pattern เดา 4 แบบ (%, "Uploading...", MB/MB,
        ปุ่ม submit disabled) ซึ่ง**ผ่านครบทั้ง 4 ได้ทั้งที่ pipeline สร้างปกของ TikTok ยังไม่เสร็จจริง** (ไม่มีเลขเปอร์เซ็นต์
        โชว์ค้าง, ปุ่ม submit อาจ enable ไปแล้วก่อนปกเสร็จ) แล้ว `attachProductLink` เริ่มคลิก/ค้นหา element
        ระหว่างที่ worker สร้างปกของ TikTok ยังทำงานอยู่พอดี — เป็นการชนกันจริงระหว่าง automation กับ internal worker
        ของ TikTok เอง (ไม่ใช่แค่ปัญหาคลิกซ้ำที่แก้ใน POST-2.5/2.6 ซึ่งช่วยได้แต่ไม่พอ)
      - **แก้แล้ว:** เพิ่มเช็คที่ 5 ใน `waitForUploadComplete()` ([background.js:248+](tiktok_autopost_extension/background.js#L248))
        — หาปุ่ม "แก้ไขหน้าปก"/"Edit cover" ถ้า**ไม่เจอปุ่มเลย** หรือ**เจอแต่ disabled** ให้ถือว่ายัง `isUploading: true`
        ต่อไป (ใช้ signal ที่พี่ยืนยันจริงจากบัญชีจริง แทนการเดา text pattern อย่างเดียว) — เช็คนี้เป็นเงื่อนไข**เพิ่ม**
        ต่อจาก 4 เช็คเดิม ไม่ได้แทนที่ ต้องผ่านครบทั้ง 5 ถึงจะถือว่าอัปโหลดเสร็จจริง
      - `node --check` ผ่าน, `pytest tests/ -q` 372 passed
      - **ยังไม่ได้ทดสอบกับ extension จริงหลัง fix นี้** — รอพี่ reload extension แล้วลองรอบใหม่ (เปิด Preserve log
        ต่อไว้เผื่อยังไม่หาย จะได้เห็น error ตัวจริงถ้าเกิดอีก)
      - **⚠️ แก้ไขต่อใน POST-2.8: สมมติฐานเช็คปุ่ม "แก้ไขหน้าปก" ผิด** — ดูรายละเอียดด้านล่าง

- [x] **POST-2.8 พี่ทดสอบมือเจาะจง — เช็คปุ่มที่ใส่ไปใน POST-2.7 ใช้ไม่ได้จริง แต่เจอบั๊กจริงอีกตัวแทน (2026-09-06)**:
      - **พี่ทดสอบเอง:** กด "แก้ไขหน้าปก" ที่ 0% อัปโหลด (`0B/21.37MB`) → **กดได้ทันที** เปิด modal ปกติ (แค่ข้างในโหลด
        สปินเนอร์รอจนคลิปอัปเสร็จค่อยโชว์ผลจริง) — สรุป: **ปุ่มนี้ไม่เคย disabled ระหว่างอัปโหลดเลย** สมมติฐานของ
        POST-2.7 (เช็คปุ่ม disabled) **ผิด** เช็คนั้นไม่เคยบล็อกอะไรจริง (เจอปุ่มไม่ disabled ตลอด ผ่านฟรีทุกครั้ง)
      - **ลบเช็คที่ 5 ของ POST-2.7 ออกแล้ว** (ทิ้ง comment อธิบายไว้ในโค้ดว่าทำไมถึงลบ กันคนมาใส่ซ้ำโดยไม่มีหลักฐานใหม่)
      - **เจอบั๊กจริงอีกตัวจากรูปเดียวกัน:** เช็คข้อ 2 เดิม (`allText.includes('Uploading...')`) **เช็คแต่คำอังกฤษ**
        แต่หน้าจริงเป็นภาษาไทยโชว์ **"กำลังอัปโหลด..."** ใต้รูปปกตอน 0% (เห็นชัดในสกรีนช็อตที่พี่ส่ง) — เช็คนี้จึง
        **ไม่เคยทำงานจริงเลยบนเซสชันภาษาไทย** ตั้งแต่แรก เพิ่มคำไทยเข้าไปด้วยแล้ว
      - `node --check` ผ่าน, `pytest tests/ -q` 372 passed
      - **สถานะตอนนี้:** เหลือ fix ที่ยืนยันแล้วว่ามีผลจริง 2 อย่าง — (1) ลดคลิกซ้ำซ้อน (POST-2.5/2.6, ยืนยันจาก
        isolation test ว่า "automation คือสาเหตุ" แต่ยังไม่รู้ว่าพอไหม) (2) เช็คคำไทย "กำลังอัปโหลด" ที่เพิ่งเพิ่ม
        (ยังไม่เคยเทสจริง) — ยังไม่มีหลักฐานเจาะจงว่า"จุดไหนกันแน่"ในลำดับงานที่ทำให้แครช รอผลทดสอบรอบใหม่กับ extension
        จริง (ไม่ใช่เทสมือ) พร้อม Preserve log เพื่อจับ error ตัวจริงตอนแครชให้ได้สักที

- [x] **POST-2.9 ทดสอบจริงกับ extension (test cap4.mp4) — แครช "ก่อน" จะเริ่มปักตะกร้าด้วยซ้ำ (2026-09-06)**:
      - **จุดเปลี่ยนสำคัญ:** คลิปนี้แครชตอน status **ยังค้างที่ "กำลังทำงาน...รอวิดีโอครบ 100%"** — คือแครชเกิดขึ้น
        **ระหว่าง `waitForUploadComplete()` กำลัง poll อยู่** ก่อนจะไปถึง `attachProductLink` เลยด้วยซ้ำ — คลิกซ้ำ/
        ค้นหา element ที่แก้ใน POST-2.5/2.6 **ไม่เกี่ยวกับจุดแครชนี้เลย** เพราะยังไม่ทันได้รันถึงตรงนั้น
      - Console ตอนแครชโชว์ log ของ TikTok เอง (`AMGAmazer`, `AMGUniformBuiltinName`, `AMGWebAudioEngine` —
        effects engine กำลัง initialize, มี `worker nums = 0`/`worker count = 0` หลายจุด น่าสงสัยเหมือนกัน)
      - **สมมติฐานใหม่ (ยังไม่ยืนยัน):** แค่ `chrome.debugger` attach ค้างอยู่ระหว่างที่ TikTok init effects engine
        เอง อาจไม่เสถียรอยู่แล้ว **ไม่ว่าจะส่งคำสั่งอะไรไปหรือเปล่า** ก็ได้ (ต่างจากที่คิดไว้ก่อนหน้าว่าการคลิก/ค้นหา
        คือตัวกระตุ้น) — พี่เสนอไอเดียตรวจแยกตัวแปร: "ลองเอาตัวปกออกดูไหม" (ดูรายละเอียดว่าทำไมไม่ตรงกับที่พี่คิดด้านล่าง)
      - **ตรวจแล้ว: โค้ดเราไม่ได้อัปโหลดปกเองเลย** (ส่วนที่เคยหยอดปกใส่ `nodeIds[1]` ถูกตัดออกไปแล้วใน POST-2.3) —
        "ปก" ที่เห็นเป็น pipeline อัตโนมัติของ TikTok เอง (`clip-forge-effect-sdk`) ที่ทำงานทันทีที่มีไฟล์วิดีโอถูกตั้งค่า
        ไม่ว่าจะตั้งด้วยมือหรือด้วยสคริปต์ — เลยไม่มี "ตัวอัปปก" ของเราให้เอาออกได้ตามที่พี่เสนอ
      - **แปลงเป็นการทดสอบที่ทำได้จริงแทน:** เพิ่ม diagnostic flag `DIAGNOSTIC_PASSIVE_WAIT`
        ([background.js:21+](tiktok_autopost_extension/background.js#L21)) — ชั่วคราวเท่านั้น ลบทิ้งเมื่อได้คำตอบ —
        แทนที่ `waitForUploadComplete()` (ซึ่ง poll ด้วย `Runtime.evaluate` ทุก ~1.5-2 วิ) ด้วย `sleep(35000)` เฉยๆ
        (ไม่ส่งคำสั่ง CDP อะไรเลย แต่ debugger ยังติดอยู่กับแท็บ) เพื่อแยกให้ชัดว่า:
        - **ถ้าแครชระหว่าง 35 วิที่นิ่งสนิทนี้** → ยืนยันว่าแค่ attach เฉยๆ ก็ไม่เสถียรแล้ว (แก้โค้ด polling ไม่ช่วย
          ต้องคิดสถาปัตยกรรมใหม่ เช่น detach ระหว่างรอ แล้วค่อย attach ใหม่ตอนจะทำจริง)
        - **ถ้าไม่แครชช่วงนี้ (แครชทีหลังตอน attachProductLink เริ่มทำงาน)** → ยืนยันว่าการยิง `Runtime.evaluate`
          ถี่ๆ ระหว่าง TikTok init effects engine ต่างหากที่เป็นตัวกระตุ้น
      - `node --check` ผ่าน, `pytest tests/ -q` 372 passed
      - **รอผลทดสอบจริง** — พี่ reload extension แล้วลองอีกรอบ (35 วินาทีนี้จะไม่มีอะไรเกิดขึ้นบนหน้าจอเลย ปกติ)
        สังเกตว่าแครชเกิดตอนไหน (ระหว่าง sleep เงียบๆ หรือหลังจากนั้น)

- [x] **POST-2.10 ผลทดสอบ DIAGNOSTIC_PASSIVE_WAIT: แครชเหมือนเดิม — พักรอบนี้ไว้ก่อนตามที่พี่บอกเหนื่อย (2026-09-06)**:
      - **ผลชี้ขาด:** แครชเหมือนเดิมแม้ตอน sleep เฉยๆ 35 วิ ไม่ส่งคำสั่ง CDP อะไรเลย → **ยืนยัน hypothesis (b):**
        แค่ `chrome.debugger` attach ค้างอยู่ระหว่างที่ TikTok init effects engine ของเขาเอง **ก็ไม่เสถียรอยู่แล้ว**
        ไม่เกี่ยวกับโค้ดที่เรา poll/คลิก/ค้นหาเลย — แก้ที่ polling behavior (POST-2.5 ถึง 2.9 ทั้งหมด) จึง**ไม่มีทาง
        แก้ได้จริง**ด้วยการปรับโค้ดฝั่งเราแบบที่ทำมา ต้องเปลี่ยนสถาปัตยกรรมใหญ่ (attach แค่ตอนจะสั่งจริงๆ แล้ว detach
        ทันที ไม่ถืออ้างอิงยาว) ถึงจะมีโอกาสเลี่ยงได้ — **ยังไม่ได้ทำ** เพราะพี่ขอพักรอบนี้ก่อน (บอกว่าเหนื่อยแล้ว)
      - **สังเกตเพิ่มจากพี่ที่ยังไม่ได้ตรวจ (บันทึกไว้เผื่อกลับมาทำต่อ):** "รอบแรกที่ทำมันยังอัพคลิปได้อยู่ ตอนแรกที่มัน
        ใส่แค่แฮชแท็กมันยังอัพคลิปได้เลย" — บ่งชี้ว่า `typeCaption()` (พิมพ์แคปชันเต็ม+ขึ้นบรรทัดใหม่ทีละบรรทัดผ่าน
        `Input.insertText`+`Input.dispatchKeyEvent`) อาจเป็นตัวแปรที่ทำให้ต่างจากตอนใส่แค่แฮชแท็กสั้นๆ — ยังไม่ได้
        แยกทดสอบเจาะจงจุดนี้ เป็นเบาะแสที่น่าตามต่อรอบหน้า
      - **มติ:** พักรอบ POST-2 นี้ไว้เหมือนเดิม (ก็พักอยู่แล้วในสถานะรวม) ใช้ flow ที่ยืนยันว่าปลอดภัยจริงแทน:
        **อัปโหลดคลิปด้วยมือ รอจนปกจริงขึ้นครบ (ไม่มีสปินเนอร์ค้าง) แล้วค่อยกด "ปักตะกร้าสินค้าอย่างเดียว"** — เส้นทางนี้
        ไม่ผ่าน `waitForUploadComplete()`/`DIAGNOSTIC_PASSIVE_WAIT` เลย ไม่เคยเจอแครชในทุกรอบเทสที่ผ่านมา
      - **DIAGNOSTIC_PASSIVE_WAIT ยังอยู่ในโค้ด** (ตั้งใจปล่อยไว้ เผื่อพี่กลับมาทดสอบต่อ) — ถ้าจะกลับมาแก้จริงจัง
        ต้องออกแบบใหม่ทั้งการ attach/detach ไม่ใช่แค่ปรับ polling ต่อ
      - `node --check` ผ่าน, `pytest tests/ -q` 372 passed (ไม่มีอะไรเปลี่ยนฝั่ง python)

- [x] **POST-2.11 สร้างเส้นทางขั้นต่ำ "อัปโหลดไฟล์อย่างเดียว" ตรงตาม root cause ของ POST-2.10 (2026-09-06)**:
      - พี่ขอกลับไปเริ่มจากจุดง่ายสุด (ให้อัปคลิปได้เฉยๆ ก่อน) — ไฟล์ `tiktok_autopost_extension/` ไม่เคย commit
        เข้า git เลย (`??` untracked ตลอด) เลย **rollback ด้วย git ทำไม่ได้จริง** ไม่มีเวอร์ชันแรกให้ย้อน แทนที่ด้วย
        การสร้างฟังก์ชันขั้นต่ำใหม่ที่ตรงกับสิ่งที่ต้องการเป๊ะ (อัปคลิปอย่างเดียว) และตรงกับ root cause ที่เพิ่งพิสูจน์
        ใน POST-2.10 พอดี (attach ค้างนานคือปัญหา ไม่ใช่คำสั่งที่ส่ง)
      - เพิ่ม `runUploadFileOnly()` ([background.js:737+](tiktok_autopost_extension/background.js#L737)) —
        attach → หา `<input type=file>` → `DOM.setFileInputFiles` → **detach ทันที** ไม่รอ ไม่ poll ไม่พิมพ์อะไรต่อ
        เวลาที่ debugger ติดอยู่กับแท็บเหลือไม่ถึงวินาที ไม่มีทางไปทับซ้อนกับตอน TikTok เริ่ม init effects engine เลย
      - เพิ่มปุ่ม "⬆️ อัปโหลดไฟล์อย่างเดียว (แนะนำ)" ในหน้า popup ไว้บนสุด (เหนือปุ่มเดิมที่ mark ไว้ว่า "ยังไม่เสถียร")
        ใช้คู่กับปุ่ม "เติมเฉพาะคำอธิบาย"/"ปักตะกร้าสินค้าอย่างเดียว" ที่มีอยู่แล้ว (ทั้งคู่ attach สั้นๆ แยกกันเหมือนกัน
        ไม่เคยแครชในทุกรอบเทสที่ผ่านมา) — รวมกัน 3 ปุ่มนี้คือ full flow แบบแยกทีละ attach สั้นๆ แทนการถือยาวทีเดียว
      - ตอบคำถามเรื่องเข้า Chrome เอง (ถามซ้ำรอบนี้): **ยังทำไม่ได้เหมือนเดิม** — Playwright ที่มีเปิด browser
        แยกของตัวเอง ไม่มี session ล็อกอินจริง เข้าไปดู element จริงของ TikTok Studio ไม่ได้
      - `node --check` ผ่านทั้ง `background.js`/`popup.js`, `pytest tests/ -q` 373 passed
      - **ยังไม่ได้ทดสอบจริง** — รอพี่ reload extension แล้วลองปุ่มใหม่ก่อน ถ้าอัปได้โดยไม่แครชแล้วค่อยลอง 2 ปุ่ม
        แยกที่เหลือทีละปุ่ม

- [x] **POST-2.12 ปิดเคส "อัปคลิปอัตโนมัติเต็มรูปแบบ" — เจอ root cause ตัวจริงที่แก้จากโค้ดเราไม่ได้ (2026-09-06)**
      **⚠️ กลับคำ — ดู POST-2.13: รอบถัดมากดปุ่มเดียวกันแล้วอัปผ่านไม่แครช สรุปด้านล่างนี้ผิด/ด่วนสรุปเกินไป**:
      - **ผลทดสอบปุ่ม "อัปโหลดไฟล์อย่างเดียว" (attach ไม่ถึงวินาที แล้ว detach ทันที):** พี่ยืนยันว่า **แครชที่
        "จังหวะเดิมเป๊ะ"** เท่ากับทุกรอบก่อนหน้า — นี่คือหลักฐานชี้ขาดตัวสุดท้าย: ตอนแครชเกิดขึ้นจริง **debugger ของเรา
        detach ไปนานแล้ว** (attach อยู่ไม่ถึง 1 วิ) แปลว่า hypothesis (b) ของ POST-2.10 ("attach ค้างคือปัญหา")
        **ก็ยังไม่ใช่ตัวจริงอีก** — ตัวกระตุ้นจริงคือ**การเรียก `DOM.setFileInputFiles` เอง** (วิธี CDP ตั้งค่าไฟล์ให้
        input) ที่ทำให้ TikTok's cover/effects pipeline (`clip-forge-effect-sdk`) รับไฟล์ไปแบบที่ต่างจากการเลือกไฟล์
        จริงด้วยมือมากพอ จนไป "ระเบิดเวลา" พังเองในภายหลังไม่กี่วินาที **ไม่ว่า debugger จะยังติดอยู่ตอนนั้นหรือไม่เลย**
      - **สรุปครบวงจร (ไล่ hypothesis ทั้งหมดที่ผ่านมา):**
        1. ~~คลิกซ้ำซ้อน~~ (POST-2.5/2.6) — ช่วยได้บ้างแต่ไม่ใช่ตัวหลัก (แครชได้แม้ไม่คลิกอะไรเลย)
        2. ~~scope การค้นหา DOM กว้างไป~~ (POST-2.6) — เช่นกัน ไม่ใช่ตัวหลัก
        3. ~~ปุ่ม "แก้ไขหน้าปก" disabled~~ (POST-2.7) — พิสูจน์แล้วว่าไม่เคย disabled เลย ผิดสมมติฐาน
        4. ~~attach ค้างระหว่าง TikTok init effects engine~~ (POST-2.10) — พิสูจน์แล้วว่าแครชได้แม้ detach ไปแล้ว
        5. **`DOM.setFileInputFiles` เอง (ตัวจริง)** — เป็นกลไกเดียวที่เหลืออยู่ในทุกรอบเทสที่แครช และไม่มีในรอบที่
           อัปมือแล้วไม่แครชสักครั้ง (ตัวแปรเดียวที่ต่างกันจริงระหว่าง "อัปมือ" กับ "อัปผ่าน extension" ทุกแบบ)
      - **นี่คือข้อจำกัดของ TikTok Studio เอง ไม่ใช่บั๊กที่แก้จากฝั่งเราได้** — ไม่มีวิธีอื่นให้เบราว์เซอร์ตั้งไฟล์ให้
        `<input type=file>` แบบเป็นโปรแกรมได้เลยนอกจาก `DOM.setFileInputFiles` (ดู TIKTOK_AUTOPOST_PLAN.md) ถ้ากลไก
        นี้เองที่ TikTok รับไม่ได้ ก็ไม่มีทางเลือกอื่นให้ auto-upload จริงๆ ได้อีกแล้วในทางเทคนิค
      - **มติสุดท้าย:** ปิดการพัฒนาฟีเจอร์ "อัปคลิปอัตโนมัติ" ไว้ตรงนี้ถาวร (ไม่ใช่แค่พักแล้วจะกลับมาแก้ต่อเหมือน
        POST-2.10) — ปุ่ม "อัปโหลดไฟล์อย่างเดียว"/"เติมข้อมูลคลิป + ปักตะกร้า" (แบบเต็ม) ให้คงไว้ในโค้ดแบบ opt-in
        (ปิดเป็นค่าเริ่มต้นอยู่แล้ว) แต่ไม่แก้ต่อ ไม่ไล่ debug ต่อ — **ใช้งานจริงทางเดียวจากนี้:** อัปคลิปด้วยมือเสมอ
        (เหมือนทำงานปกติที่พี่คุ้นเคยอยู่แล้ว) แล้วใช้ 2 ปุ่มที่พิสูจน์แล้วว่าปลอดภัย 100% ตลอดการทดสอบ: "เติมเฉพาะ
        คำอธิบายและแฮชแท็ก" + "ปักตะกร้าสินค้าอย่างเดียว" — ทั้งคู่ไม่แตะ `<input type=file>` เลยแม้แต่ครั้งเดียว
      - ไม่มีการแก้โค้ดเพิ่มในข้อนี้ (เป็นการปิดเคสด้วยข้อสรุป ไม่ใช่การแก้บั๊ก)

- [x] **POST-2.13 กลับคำ POST-2.12: กดปุ่มเดียวกันซ้ำ ครั้งนี้อัปผ่านไม่แครช — สร้าง checklist ทีละขั้นแทนเดา (2026-09-06)**:
      - **หลักฐานที่ทำให้ POST-2.12 ผิด:** พี่กด "อัปโหลดไฟล์อย่างเดียว" ซ้ำ (โค้ดเดิมเป๊ะ ไม่ได้แก้อะไรระหว่างนั้น)
        รอบนี้ **อัปผ่าน ไม่แครช** ทั้งที่รอบก่อนหน้า "จังหวะเดิมเป๊ะ" แครชซ้ำ — สรุปว่าแครชนี้**ไม่ deterministic
        100%** (flaky) แม้แต่ปุ่มเดียวกัน โค้ดเดียวกัน — ข้อสรุป "`DOM.setFileInputFiles` คือ root cause ถาวร แก้ไม่ได้"
        ใน POST-2.12 **ด่วนสรุปเกินไปจากหลักฐานแค่ 1 รอบ** ต้องขอโทษที่รีบปิดเคส
      - เช็ค backend ด้วย: ไม่เกี่ยวกับ backend ค้าง — `curl /openapi.json` เจอ `/api/tiktok-autopost/pending` ครบ
        อยู่แล้ว (backend stale ไม่ทำให้ tab ของ Chrome แครชได้ คนละ process กันคนละชั้นกันเลย)
      - **พี่ขอเปลี่ยนวิธี:** "ค่อยๆทำทีละฟังก์ชั่น และให้มีการติ๊ก แล้วผมจะดูเอง ว่าขั้นตอนไหนการเพิ่มอะไรที่ทำให้ crash"
        — เลิกเดา hypothesis ฝั่งผม เปลี่ยนเป็นเครื่องมือให้พี่ไล่ทดสอบเองทีละสเต็ปแทน
      - **สร้าง popup ใหม่เป็น checklist 5 ขั้น** แยก attach/act/detach คนละรอบต่อขั้น (ไม่ share session ข้ามขั้น):
        1. อัปโหลดไฟล์ (`upload-file-only`, มีอยู่แล้ว)
        2. พิมพ์คำอธิบาย/แฮชแท็ก (`type-caption-only`, มีอยู่แล้ว)
        3. ปักตะกร้าสินค้า (`attach-product-only` — ตัดการทำ scheduleMode ในตัวออก แยกเป็นขั้น 4 ต่างหาก)
        4. สลับเป็น "กำหนดเวลา" — ฟังก์ชันใหม่ `runScheduleModeOnly()` ([background.js:795+](tiktok_autopost_extension/background.js#L795))
        5. กด Post/กำหนดเวลา — ฟังก์ชันใหม่ `runClickPostOnly()` ([background.js:812+](tiktok_autopost_extension/background.js#L812))
      - แต่ละขั้นมีปุ่ม "ทำ" + checkbox แยก (ติ๊กเองอัตโนมัติเมื่อขั้นนั้นสำเร็จ, ไม่ติ๊ก = พังหรือหาไม่เจอ) — เขียนใหม่
        ทั้ง `popup.html`/`popup.js` เป็น checklist (เก็บช่องคำอธิบาย/แฮชแท็ก/ID สินค้าไว้เหมือนเดิม ย้ายมารวมกล่องเดียว)
      - ปุ่ม "เติมข้อมูลคลิป + ปักตะกร้า" (full auto flow เดิม) **เอาออกจาก UI แล้ว** (เก็บฟังก์ชัน `runAutopost` ไว้ใน
        โค้ดเผื่อใช้ทีหลัง แต่ไม่มีปุ่มเรียกแล้ว เพื่อไม่ให้สับสนกับ checklist ใหม่)
      - **ยังตอบไม่ได้เรื่องเข้า Chrome เอง** (พี่ถามซ้ำ) — Playwright ที่มีเปิด browser แยก ไม่มี session ล็อกอินจริง
      - `node --check` ผ่านทั้ง 2 ไฟล์ js, `python` เช็ค popup.html เบื้องต้นผ่าน (tag ครบคู่, id ครบ 5 ขั้น),
        `pytest tests/ -q` 373 passed
      - **ยังไม่ได้ทดสอบจริงกับ checklist ใหม่** — รอพี่ reload extension แล้วไล่กดทีละขั้น สังเกตว่าขั้นไหนพัง
        (เนื่องจากแครชดูจะ flaky ไม่ 100% แนะนำให้ลองซ้ำแต่ละขั้น 2-3 รอบ ไม่ใช่แค่รอบเดียว ก่อนสรุปว่าขั้นนั้นปลอดภัย)

- [x] **POST-2.14 checklist เจอตัวการจริงแล้ว — ขั้น 2 (พิมพ์คำอธิบาย) ทำให้แครช พร้อม console log ตัวจริงครั้งแรก (2026-09-06)**:
      - **หลักฐานชี้ขาดจาก console (มี "Keep log" เปิดค้างไว้ จับได้ตัวจริงเป็นครั้งแรก):** เจอ
        `NotFoundError: Failed to execute 'removeChild' on 'Node'` (React internals, `lib-react.cad72241.js`)
        **ต่อด้วยบรรทัด `pageCrash form unmount` จาก `Form.9fab7078.js` ทันที** — เป็น log ที่ TikTok เขียนเองสำหรับ
        เคสนี้โดยเฉพาะ (แปลว่าฟอร์มอัปโหลดของเขา unmount ตอน crash พอดี ไม่ใช่แค่ React เพี้ยนลอยๆ)
      - **จุดที่กดแล้วพังชัดเจน:** ขั้น 2 (พิมพ์คำอธิบาย/แฮชแท็ก) — error ขึ้น**ทันทีก่อนขึ้นอะไรเลย** (ไม่ใช่พิมพ์ติดแล้ว
        โดนเขียนทับทีหลังแบบที่สงสัยไว้ก่อนหน้า)
      - **ต้นตอที่เจอจริงจากอ่านโค้ด `typeCaption()`:** เดิมทำ **2 คำสั่งแยกคนละรอบ CDP call** —
        (1) `selectAll` + `delete` (ลบให้ว่าง) แล้ว **รอ 250ms** ก่อน (2) `insertText` เป็นอีก `Runtime.evaluate` แยก
        ต่างหาก — ระหว่างช่องว่าง 250ms ที่ field ว่างเปล่าจริงๆ นั้น TikTok's React มีโอกาสรีเรนเดอร์/แก้ DOM ตรงนั้น
        พอ `insertText` รอบหลังยิงเข้าไปเจอ node ที่ TikTok แก้ไปแล้ว โครงสร้างไม่ตรงกับที่ React คาดไว้ →
        `removeChild` พัง — ตรงกับที่สังเกตไว้ก่อนหน้าว่า "ใส่แค่แฮชแท็กสั้นๆ ยังผ่าน" (เนื้อหาสั้น โอกาสชนจังหวะน้อยกว่า)
      - **แก้แล้ว:** รวม `selectAll` + `insertText` เป็น **คำสั่งเดียวใน `Runtime.evaluate` เดียว**
        ([background.js:155+](tiktok_autopost_extension/background.js#L155)) — เลือกทั้งหมดแล้ว `execCommand
        ('insertText', ...)` ทับเลยทันทีในการเรียกเดียวกัน (`insertText` บน selection ที่เลือกไว้แทนที่เป็น
        native edit operation เดียว ไม่ต้องลบแยกอีกต่อไป) **ไม่มีช่องว่างให้ TikTok แทรกกลางคันได้เลย**
      - `node --check` ผ่าน, `pytest tests/ -q` 373 passed
      - **ยังไม่ได้ทดสอบจริงหลัง fix นี้** — รอพี่ reload extension แล้วลองขั้น 2 ซ้ำ 2-3 รอบตามที่แนะนำไว้
      - **⚠️ ผลจริง:** ลองซ้ำแล้ว **error signature เดียวกันเป๊ะ** ไม่เปลี่ยนแม้แต่นิดเดียว ทั้งที่แก้จริง (ครั้งที่ 3
        ที่ทฤษฎีต่างกันจริงทั้ง 3 รอบ) รวมกับที่เคยเจอ "ปุ่มเดียวกันโค้ดเดียวกัน บางรอบพังบางรอบผ่าน" (POST-2.13) —
        สรุปร่วมกับพี่ว่า **นี่น่าจะเป็น race condition ในโค้ด TikTok เอง** (form/autosave ภายใน) ที่ถูก sensitize ให้
        เกิดถี่ขึ้นเวลามี `chrome.debugger` ติดอยู่กับแท็บ ไม่ว่าเราจะสั่งอะไรตรงนั้นก็ตาม — ไม่ใช่บั๊กที่แก้จากโค้ดเรา
        ได้จริงแบบ deterministic อีกต่อไป (ต่างจาก POST-2.12 ที่ปิดเคสแบบไม่มีหลักฐานพอ อันนี้มีหลักฐาน 3 รอบสนับสนุน)
      - **พี่ตัดสินใจ:** พักการไล่ debug ส่วนอัตโนมัติเต็มรูปแบบไว้ตรงนี้จริงๆ (ไม่ปิดถาวร เผื่อ TikTok แก้ฝั่งเขาเอง
        ในอนาคต) หันไปทำฟีเจอร์ใหม่ที่ทำได้จริงแทน — ดู POST-2.15

- [x] **POST-2.15 เพิ่ม Chrome Side Panel แสดงรายการคลิป "ตัดต่อเสร็จ" จาก OmniCut โดยตรง (2026-09-06)**:
      - **คำขอ:** "ทำ extension ให้โผล่มาจาก sidebar แล้วแสดงรายละเอียดคลิปที่มีสถานะตัดต่อเสร็จทั้งหมด" — ฟีเจอร์ใหม่
        ที่ไม่เกี่ยวกับปัญหาแครชเลย ใช้ Chrome Side Panel API (Manifest V3) แยกจาก popup เดิม
      - เพิ่ม `"sidePanel"` permission + `"side_panel": {"default_path": "sidepanel.html"}` ใน `manifest.json`
      - สร้าง `sidepanel.html`/`sidepanel.js` ใหม่ — fetch `GET /api/exports` จาก backend เดียวกับที่แอปใช้เอง
        (`http://127.0.0.1:8000`, host_permissions มีอยู่แล้ว) กรองเฉพาะ `angle_status === 'rendered' &&
        is_latest !== false` (ตรงกับความหมาย "ตัดต่อเสร็จ" ของ `PIPELINE_PHASES` ใน `ContentTrackerHub.jsx` เป๊ะ —
        ไม่รวมคลิปที่ไปถึง mobile_ready/posted แล้ว หรือคลิปที่ยังไม่ได้ผูกกับสคริปต์เลย)
      - ยืนยันรูปทรง response จริงด้วย curl (8 exports จริง, มี 1 รายการ `angle_status='rendered', is_latest=true`
        ตรงเงื่อนไขพอดี — Logitech Wave Keys ที่เพิ่งซ่อมจาก Round BUG-3) + เช็ค thumbnail URL จริงคืน 200
      - แต่ละการ์ดโชว์ thumbnail (`.webp` เดิม) + ชื่อสินค้า + hook title + ขนาดไฟล์ + ปุ่ม "เตรียมคลิปนี้" ที่ยิง
        `POST /api/tiktok-autopost/prepare` ตรง (endpoint เดียวกับที่ popup ใช้อยู่แล้ว) แล้วบอกให้ไปกดต่อใน popup
      - เพิ่มปุ่ม "📋 เปิดรายการคลิปที่ตัดต่อเสร็จ (แถบข้าง)" ใน `popup.html` เรียก `chrome.sidePanel.open({windowId})`
        (ต้องเรียกจาก user gesture โดยตรงตาม Chrome API ถึงจะเปิดได้ — เก็บ `default_popup` เดิมไว้ไม่แตะ
        เพื่อไม่ให้ checklist หายไปเวลาคลิกไอคอน extension)
      - `node --check` ผ่านทั้ง 3 ไฟล์ js, manifest.json valid JSON, HTML tag เช็คคร่าวๆ ผ่าน, `pytest tests/ -q`
        373 passed (ไม่กระทบฝั่ง python เลย ฟีเจอร์นี้อยู่ใน extension ล้วนๆ)
      - **ยังไม่ได้ทดสอบจริง** — รอพี่ reload extension แล้วกดปุ่มเปิดแถบข้างจาก popup ดู
      - **⚠️ พี่ลองแล้ว: กดปุ่มไม่มีอะไรเกิดขึ้นเลย (ไม่มี error, ไม่มีแถบข้าง)** — เจอบั๊กจริงจากอ่านโค้ดตัวเอง:
        `chrome.sidePanel.open()` ต้องถูกเรียก**ในจังหวะ user gesture โดยตรง** (synchronous เท่านั้น) แต่โค้ดเดิม
        เรียก `chrome.windows.getCurrent()` (async) ก่อน แล้วค่อยเรียก `open()` **ข้างใน callback ของมัน** —
        เสีย user gesture ไปแล้วตอนนั้น ทำให้ `open()` throw แบบ **synchronous ทันที ก่อนจะถึง `.catch()` เลย** —
        เป็น uncaught exception ที่พี่มองไม่เห็นเลย (comment ในโค้ดเดิมพูดถูกว่าต้องเรียก sync แต่ implement ผิดเอง)
      - **แก้แล้ว:** ย้ายการดึง `windowId` ไปทำ**ตอน popup โหลด** (cache ไว้ล่วงหน้าตั้งแต่แรก ไม่ใช่ตอนกด) พอกดปุ่ม
        เรียก `chrome.sidePanel.open({windowId: currentWindowId})` **แบบ sync ทันที ไม่มีช่องว่าง async คั่นกลาง
        เลย** ([popup.js:11+](tiktok_autopost_extension/popup.js#L11)) + เพิ่ม try/catch ครอบกันการ throw
        แบบ synchronous ไว้ด้วย เผื่อพังกรณีอื่นจะได้เห็น error จริงแทนที่จะเงียบ
      - `node --check` ผ่าน, `pytest tests/ -q` 373 passed
      - **ยังไม่ได้ทดสอบจริงหลัง fix นี้** — รอพี่ reload extension แล้วลองกดปุ่มอีกที

- [x] **POST-2.16 รวม popup เดิม + side panel เป็น UI เดียว ตาม /grill-me (6 คำถามตอบครบ) (2026-09-06)**:
      - **คำขอ:** "อยากให้กด extension แล้วเปิดแถบข้างเลย ไม่ใช่กดปุ่ม แล้วออกแบบให้สวยงามด้วย" — grill-me สรุป:
        (1) รวม checklist เดิมเข้า side panel เป็น 2 แท็บ ลบ popup ทิ้งเลย (2) แท็บสวิตช์บนสุด (3) มี confirm
        dialog ก่อนเปลี่ยนคลิป active ถ้า checklist ทำค้างอยู่ (4) เพิ่มปุ่ม mark-posted **ในตัว extension เลย**
        (พี่ขอเองนอกเหนือจาก 2 ตัวเลือกที่เสนอไป — ไม่ต้องสลับไปกดในแอป OmniCut) (5) กล่อง mark-posted แยกท้ายสุด
        (6) รีเฟรชรายการคลิปแบบ manual เท่านั้น (ปุ่มเดิม ไม่ auto-poll)
      - **ลบ:** `popup.html`, `popup.js` ทั้งคู่ (`rm`) — เช็คด้วย `grep` แล้วว่าไม่มีโค้ด/manifest ที่อ้างถึงอีก
        (เจอแค่ log เก่าใน TODO.md/HISTORY.md ซึ่งเป็นบันทึกอดีต ไม่กระทบ)
      - **`manifest.json`:** เอา `"default_popup": "popup.html"` ออกจาก `"action"` (เหลือแค่ `default_title`)
      - **`background.js`:** เพิ่ม `chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })` ต้นไฟล์
        — ทำให้กดไอคอน extension เปิดแถบข้างตรงทันที ไม่ต้องผ่านปุ่มกลางทางอีก
      - **`sidepanel.html`** เขียนใหม่ทั้งไฟล์: เพิ่ม tab switcher (`#tabBtnList`/`#tabBtnChecklist`), แท็บ 2
        ("ขั้นตอนโพสต์") ย้าย caption/hashtags/productId inputs + checklist 5 ขั้นเดิมมาจาก popup.html ทุกอย่าง,
        เพิ่ม `#activeClipBanner` (โชว์คลิปที่กำลังทำอยู่), เพิ่มกล่อง `.mark-posted-card` (สีเขียว แยกจากปุ่ม
        automation โทนอันตราย) พร้อม `#markPostedBtn`, เพิ่ม `#confirmOverlay` modal สำหรับ confirm เปลี่ยนคลิป
      - **`sidepanel.js`** เขียนใหม่ทั้งไฟล์ เพิ่มจากของเดิม (list-only): tab-switch logic, `activeClip` state,
        `handlePrepareClick()` เช็ค `anyStepChecked()` ก่อน — ถ้ามีขั้นติ๊กค้างอยู่และกดคลิปอื่น จะเปิด confirm
        dialog ก่อนเสมอ (`askConfirm()` คืน Promise ผูกกับปุ่ม ok/cancel), `prepareClip()` ยิง `/prepare` เหมือน
        เดิมแล้วเติม caption/hashtags/productId ลง input พร้อมสลับไปแท็บ checklist อัตโนมัติ + reset ช่องติ๊กทั้ง 5
      - ปุ่ม checklist 5 ขั้น ย้าย `wireStep()` มาจาก popup.js เดิมเกือบคำต่อคำ ผูก action เดิมทุกตัว
        (`upload-file-only`/`type-caption-only`/`attach-product-only`/`schedule-mode-only`/`click-post-only`)
        — ไม่แตะ `background.js` ส่วนนี้เลย ยังใช้ message contract เดิมทั้งหมด
      - **ใหม่:** `markPostedBtn` handler ยิง `POST /api/exports/mark-posted` ตรง ({file_path, product_id,
        angle_id} จาก `activeClip`) — endpoint นี้มีอยู่แล้วใน `scripts/api_exports.py` (ไม่ได้แก้ backend เลย)
        สำเร็จแล้ว reset `activeClip`/checklist กลับที่ว่าง + เรียก `loadExports()` ใหม่ให้คลิปหายจากรายการ
      - เช็ค element id ตรงกันทุกตัวระหว่าง HTML กับ `getElementById` ใน JS ด้วย script python เทียบ set — ตรงกัน
        ครบ (มี false positive 2 ตัวจาก regex จับ template literal `chk${n}`/`btn${n}` ผิด ไม่ใช่ id จริง)
      - `node --check` ผ่านทั้ง `sidepanel.js`/`background.js`, manifest.json valid JSON
      - **ยังไม่ได้รัน `pytest` รอบนี้ และ**ยังไม่ได้ทดสอบจริง** — รอพี่ reload extension ที่ `chrome://extensions`
        แล้วทดสอบ: (1) คลิกไอคอนต้องเปิดแถบข้างตรงเลย ไม่มี popup แทรกอีก (2) แท็บ "รายการคลิป" เห็นคลิปเดิม
        (3) กด "เตรียมคลิปนี้" ต้องสลับไปแท็บ checklist พร้อมข้อมูลเติมให้ (4) ลองกด "เตรียมคลิปนี้" คลิปอื่นตอน
        checklist ทำค้าง ต้องขึ้น confirm dialog ก่อน (5) ปุ่ม "มาร์คว่าโพสต์แล้ว" ทดสอบกับคลิปจริงได้ตามที่พี่สะดวก
        (เป็นข้อมูลจริงของพี่ ปุ่มนี้ไม่แตะ TikTok เลย แค่ย้ายไฟล์ในเครื่อง — ตัดสินใจเองได้ว่าจะลองกับคลิปไหน)

- [x] **POST-2.17 ปรับ UI side panel ให้สวยขึ้น ผ่าน `/impeccable polish` + craft-floor (2026-09-06)**:
      - **คำขอ:** "ปรับหน้า UI ให้สวยๆหน่อย สวยที่สุด ใช้งานง่าย สบายตา" พร้อมสกรีนช็อตของ POST-2.16 (แบนมาก —
        สี cyan เดียวทั้งจอ ไม่มี depth ไม่มี hierarchy, tab ดูเป็นปุ่มลอยไม่ใช่ segmented control)
      - รัน `context.mjs` — ไม่มี `PRODUCT.md`/`DESIGN.md` ในโปรเจกต์ (scoped fix ไปได้เลยไม่ต้อง block) จัดเป็น
        **Operate mode** (task-completion tool ไม่ใช่ marketing surface) ตาม `polish.md`
      - เขียน `sidepanel.html` ใหม่ทั้ง `<style>`: เพิ่ม design tokens (`--bg/--surface/--surface-raised` 3 ระดับ
        elevation, `--text-primary/secondary/tertiary` 3 ระดับ, accent/success/danger แยกชัดเป็น semantic role
        ไม่ใช้ cyan ทุกที่แบบเดิม), shadow scale จริง (sm/md/lg มี offset+blur ตาม craft-floor "Depth" rule),
        radius scale, easing curve เดียว (`cubic-bezier(0.16,1,0.3,1)`)
      - ปุ่มแยก role ชัด: `.btn-primary` (cyan, action หลัก) / `.btn-ghost` (neutral, secondary) / `.btn-step`
        (checklist) / `.btn-success` (mark-posted, เขียวแยกจาก automation ตามที่ตั้งใจไว้ตั้งแต่ POST-2.16)
        ทุกปุ่มมี hover (translateY -1px + สี) + active (scale/brightness) + disabled state
      - Tab switcher ทำเป็น segmented control จริง (พื้นหลังเดียว active state เป็นแท่งทึบสีตัดกัน แทนปุ่มลอย
        แยกกันแบบเดิม) + hover state บนแท็บที่ไม่ active
      - Checklist step แต่ละแถวเพิ่ม `.step-num` (เลขในวงกลม เปลี่ยนเป็นเขียวเมื่อ `input:checked` ด้วย
        `:has()` selector) แทนแค่ checkbox ลอยเดี่ยวๆ — step 5 (กด Post จริง) มี `.danger` class เน้นสีต่างจาก
        step อื่นเพราะเป็นขั้นที่กดแล้วย้อนไม่ได้
      - Card คลิป: เพิ่ม hover elevation (translateY -1px + shadow เข้ม), ชื่อสินค้าเป็น uppercase label
        แยก hierarchy จาก hook title, meta แยก dot separator
      - Empty/error state: จาก text สั้นๆ เป็นกล่อง dashed border (`.empty`) / กล่อง danger wash (`.error`)
        ให้เห็นชัดว่าเป็น state ไม่ใช่ข้อความหลุด
      - Confirm modal: เพิ่ม `backdrop-filter: blur(3px)` บน overlay + scale-in animation บนกล่อง (แทนโผล่มาทันที)
      - เพิ่ม `@media (prefers-reduced-motion: reduce)` ปิด animation ทั้งหมดตาม craft-floor "Motion" rule
      - `sidepanel.js`: ปุ่ม "เตรียมคลิปนี้" ที่สร้างด้วย `createElement` เพิ่ม `btn.className = 'btn-primary'`
        (เดิมไม่มี class เลย), `setStatus()` เปลี่ยน default จาก `kind || ''` เป็น `kind || 'info'` ให้ทุกข้อความ
        สถานะได้กล่องสไตล์เดียวกันแทนที่จะเป็น text ลอยไม่มี padding เวลาไม่ส่ง kind มา
      - **เจอจาก detector จริง (`detect.mjs`):** รอบแรกมี `--shadow-glow-accent`/`--shadow-glow-success` เป็น
        zero-offset colored halo บน `.btn-primary`/`.btn-success` — ตรง antipattern "dark-glow" (ท่า AI-slop
        ที่ detector เช็คเฉพาะ) แก้เป็น `--shadow-cta` (neutral elevation shadow มี offset+blur จริง ไม่มีสี)
        ตัวเดียวใช้ร่วมกัน 3 จุด + เอา glow ออกจากจุดสีเขียวๆ บนจุดไฟหน้า h1 ด้วย — รันซ้ำแล้ว detector คืน `[]`
      - เช็ค element id ตรงกันหมดระหว่าง HTML/JS (script python เทียบ set, false positive 2 ตัวจาก regex
        จับ template literal `chk${n}`/`btn${n}` ผิดเหมือนรอบก่อน ไม่ใช่ id จริง), เช็ค tag เปิด-ปิดสมดุลหมด
      - `node --check sidepanel.js` ผ่าน, `pytest tests/ -q` 381 passed (ไม่กระทบฝั่ง python เลย)
      - **ยังไม่ได้ทดสอบจริงในเครื่องพี่** — รอ reload extension ที่ `chrome://extensions` แล้วดูหน้าตาจริง
        ทั้ง 2 แท็บ + ลอง hover/click ปุ่มต่างๆ ว่า transition ลื่นไหม

- [x] **POST-2.18 เพิ่มปุ่มคัดลอก caption+hashtags รวม + ทำ checkbox ติ๊กเองได้ (2026-09-06)**:
      - **คำขอ:** (1) "คำอธิบายกับแฮชแท็กอยากอยู่ช่องเดียวกัน หรือไม่ก็มีปุ่มคัดลอกทั้งสองอันพร้อมกัน" (2) "ตอนนี้
        ยังกดทำแล้วรันต่อไม่ได้ อยากติ๊กหัวข้อเพื่อทำ checklist เองได้ไหม"
      - ถามพี่ก่อน 2 คำถาม: (1) แยกช่องเดิม+ปุ่มคัดลอกรวม vs รวมเป็นช่องเดียว → พี่เลือก**แยกช่องเดิม+ปุ่มคัดลอก**
        (ไม่เสี่ยงพังการแยก parse hashtag ที่ `background.js` พึ่งอยู่) (2) ติ๊กเองแล้วต้องเกิดอะไร → พี่เลือก
        **แค่ mark progress ด้วยมือ** ปุ่ม "ทำ" ยังทำงานเดิมทุกอย่าง (auto-tick เมื่อ CDP สำเร็จจริง)
      - **ปุ่มคัดลอกรวม:** เพิ่ม `#copyAllBtn` ใต้ 2 textarea ใน `sidepanel.html` — `sidepanel.js` ต่อ
        `caption + '\n\n' + hashtags` (ตัด field ที่ว่างออกด้วย `.filter(Boolean)`) แล้ว
        `navigator.clipboard.writeText()` (ใช้ได้ตรงในหน้า extension เอง ไม่ต้องเพิ่ม permission ใน
        manifest.json) สำเร็จแล้วเปลี่ยนปุ่มเป็น "✅ คัดลอกแล้ว" สีเขียวชั่วคราว 1.5 วิ แล้วคืนข้อความเดิม
      - **checkbox ติ๊กเองได้:** เดิม checkbox ถูกซ่อนด้วย `pointer-events: none` แสดงแค่ `.step-num` (เลขวงกลม)
        เป็น `<span>` อ่านอย่างเดียว — เปลี่ยน `.step-num` จาก `<span>` เป็น `<label for="chkN">` ทั้ง 5 ขั้น
        ([sidepanel.html](tiktok_autopost_extension/sidepanel.html)) ให้คลิกที่เลขวงกลม = toggle checkbox
        ผ่านกลไก HTML label association มาตรฐาน (ไม่ต้องเขียน JS toggle เพิ่มเอง) + เพิ่ม `cursor: pointer` +
        hover/active state ให้เห็นว่ากดได้ ปุ่ม "ทำ" ยังคงอยู่คู่กันเหมือนเดิม ไม่ได้ตัดออก
      - **ไม่ต้องแก้ `sidepanel.js` เรื่อง checkbox เลย** — เช็คโค้ดแล้ว `anyStepChecked()`/`resetChecklist()`/
        `wireStep()` อ่าน-เขียนผ่าน `.checked` เฉยๆ ไม่สนว่าใครเป็นคนติ๊ก (ปุ่ม "ทำ" หรือพี่เอง) ผลพลอยได้ที่ถูกต้อง
        พอดี: ติ๊กเองก็ trigger confirm-dialog ตอนเปลี่ยนคลิปเหมือนกดปุ่ม "ทำ" จริง (สมเหตุสมผล เพราะแปลว่าพี่
        ทำขั้นนั้นไปแล้วจริงๆ ไม่ว่าจะทำเองนอกระบบหรือให้ extension ทำให้)
      - แก้ `step-note` ท้าย checklist ให้อธิบาย 2 วิธี (กดปุ่ม "ทำ" ให้อัตโนมัติ / กดเลขวงกลมเองถ้าทำเองแล้ว)
      - `node --check sidepanel.js` ผ่าน, detector (`detect.mjs`) คืน `[]` (ไม่มี antipattern ใหม่), id ตรงกัน
        ทุกตัว, tag เปิด-ปิดสมดุล (รวม `<label>` 5 คู่ใหม่), `pytest tests/ -q` 381 passed
      - **ยังไม่ได้ทดสอบจริง** — รอ reload extension แล้วลอง (1) กดปุ่มคัดลอกรวม วางใน caption box ของ TikTok
        ดูว่าได้ครบทั้ง 2 ส่วน (2) ลองกดเลขวงกลมของขั้นที่ยังไม่ทำ ดูว่าติ๊ก/เปลี่ยนสีเขียวได้ทันที

- [x] **POST-2.19 แก้บั๊กจริง: ขั้น 3 ปักตะกร้าค้างที่แท็บ "ร้านของฉัน" ไม่สลับไป "นำเสนอสินค้า" (2026-09-06)**:
      - **หลักฐาน:** พี่ส่งสกรีนช็อต — modal "เพิ่มลิงก์สินค้า" ค้างอยู่แท็บ "ร้านของฉัน" (empty state
        "ไม่มีสินค้าในร้านของคุณ") ไม่เคยสลับไปแท็บ "นำเสนอสินค้า" เลย ทั้งที่ ID/พิมพ์ค้นหาถูกส่งเข้าไปแล้ว
        (พี่บรรยาย: "ปักตระกร้า มันทำได้ถึงแค่ร้านค้า ไม่เปิดแทบนำสเนอสินค้า แล้วใส่เลขไอดีติ้กเลือกบันทึกให้")
      - **root cause จากอ่านโค้ด `switchToShowcaseTab()`'s `isActive()`
        ([background.js:322-335](tiktok_autopost_extension/background.js#L322) เดิม):** เช็คแค่
        `searchInput.offsetWidth > 0 || offsetHeight > 0 || getClientRects().length > 0` — ทั้ง 3 เงื่อนไขนี้
        คืนค่า non-zero ได้แม้ element อยู่ใน ancestor ที่ `display: none` (React ของ TikTok เก็บ tab panel
        ที่ไม่ active ไว้ใน DOM ต่อ ไม่ได้ unmount) แปลว่าถ้ามี search input เก่าค้างจาก render รอบก่อนที่ไหน
        สักที่ในหน้า `isActive()` จะ**คืน `true` เท็จตั้งแต่การเช็คครั้งแรก** (บรรทัด `if (await isActive())
        return true`) ทำให้ฟังก์ชันไม่เคยพยายามคลิกแท็บที่ถูกต้องเลย แล้วปล่อยผ่านไปเป็น "switched=true" ทั้งที่
        ยังอยู่ "ร้านของฉัน" จริงๆ
      - **แก้ 2 จุด:**
        1. `isActive()` เปลี่ยนเป็นเช็ค `checkVisibility()` จริง (fallback `getBoundingClientRect` +
           `getComputedStyle` ถ้า browser เก่าไม่รองรับ) **บวกเช็ค negative signal ตรงๆ**: ถ้าเจอข้อความ
           "ไม่มีสินค้าในร้านของคุณ" ที่ไหนในหน้า ถือว่ายังไม่ active แน่นอน ไม่ว่า search input จะดูเหมือน
           visible แค่ไหนก็ตาม ([background.js:321-360](tiktok_autopost_extension/background.js#L321))
        2. `attachProductLink()` เดิมเจอ `switched === false` แค่ `console.warn` แล้ว**เดินหน้าต่อ** พิมพ์ ID
           ลง search box ที่ไม่มีอยู่จริง (เพราะ "ร้านของฉัน" ไม่มี search) — เปลี่ยนเป็น **หยุดทันทีและ return
           error ชัดเจน** `'สลับไปแท็บ "นำเสนอสินค้า" ไม่สำเร็จ (ยังค้างอยู่ที่ "ร้านของฉัน") -- ลองกดขั้นนี้ซ้ำ'`
           ([background.js:508-514](tiktok_autopost_extension/background.js#L508)) แทนที่จะปล่อยให้พังต่อแบบ
           เงียบๆ แล้วไปโผล่ error ที่ไม่เกี่ยวกันในขั้นถัดไป (หาสินค้าไม่เจอ/กดปุ่มไม่ได้)
      - `node --check` ผ่าน, `pytest tests/ -q` 381 passed (ไม่กระทบฝั่ง python)
      - **ยังไม่ได้ทดสอบจริง** — รอพี่ reload extension แล้วลองกดขั้น 3 (ปักตะกร้าสินค้า) ใหม่ ดูว่าสลับไปแท็บ
        "นำเสนอสินค้า" ได้จริงไหม ถ้ายังพังอีก ตอนนี้จะได้ error message ที่ชี้ตรงจุดแทนที่จะเงียบเหมือนก่อน
      - **✅ ผลจริง (พี่ทดสอบแล้ว):** POST-2.19 แก้ตรงจุด — ขั้น 3 เดินผ่านไปจนถึงหน้า "เพิ่มลิงก์สินค้า" มีชื่อ
        สินค้า "LOGITECH WAVE KEYS (สีขาว/สีดำ" ขึ้นรอกด "เพิ่ม" ได้จริงแล้ว (พี่ส่งสกรีนช็อตยืนยัน)

- [x] **POST-2.20 แก้บั๊ก: ขั้น 4 "สลับเป็นกำหนดเวลา" กดโดน dropdown "ตำแหน่งที่ตั้ง" แทน (2026-09-06)**:
      - **หลักฐาน:** พี่ส่งสกรีนช็อต — กดขั้น 4 แล้ว dropdown "ตำแหน่งที่ตั้ง" (Location) เปิดขึ้นมาแทน ไม่ใช่ตัวเลือก
        "กำหนดเวลา" ("สลับเป็นกำหนดเวลา มันไปกดเลือกตำแหน่งแทน")
      - **root cause จากอ่านโค้ด `switchToScheduleMode()`
        ([background.js:667-685](tiktok_autopost_extension/background.js#L667) เดิม):** ค้นหา element ด้วย
        `t.includes('กำหนดเวลา')` แบบ **ไม่จำกัดว่าต้องเป็น leaf** — ถ้า TikTok วาง "กำหนดเวลาโพสต์" กับฟิลด์
        "ตำแหน่งที่ตั้ง" ไว้ใน section เดียวกัน `<div>` ครอบใหญ่ที่สุด (parent) ก็จะ match ก่อนเพราะ
        `innerText` ของมันรวมข้อความลูกทุกตัวไว้อยู่แล้ว (includes เจอแน่นอน) โค้ดเดิมหยิบ div ใหญ่นั้นมาแล้ว
        `.querySelector('input')` หา **input ตัวแรกที่เจอใน DOM order ภายใน container นั้น** ซึ่งถ้า input
        ของฟิลด์ location มาก่อน input ของ schedule radio ใน DOM ก็จะกดโดน location แทนทันที
      - **แก้:** เขียนใหม่ 3 จุด
        1. เปลี่ยนจาก `includes()` เป็น **exact match** (`TARGETS.includes(t)`) และเพิ่มเงื่อนไข **ห้ามมี child
           element ที่มีข้อความตรงกันซ้ำ** (`isLeafMatch`) — ป้องกัน parent div ที่ห่อ label จริงไว้ข้างในชนะ
        2. ถ้า match หลายตัว เรียงเอา bounding-box **เล็กสุดก่อน** (element เฉพาะเจาะจงที่สุด) เหมือน pattern
           ที่ใช้กับ `switchToShowcaseTab` ไปแล้วใน POST-2.5/2.6
        3. หา input ที่จะคลิกด้วย `getAttribute('for')` → `getElementById` (ผูก label-for ตรงมาตรฐาน) ก่อน
           แล้วค่อย fallback ไป `:scope > input` (ลูกตรงๆ ชั้นเดียว ไม่ query ลึกเข้าไปในลูกหลาน) แทนที่จะ
           `querySelector('input')` แบบเดิมที่มองเข้าไปได้ลึกทั้ง subtree
        4. เปลี่ยน return type จาก `undefined` เป็น `{success: boolean}` จริง — `runScheduleModeOnly()`
           ([background.js:866](tiktok_autopost_extension/background.js#L866)) เช็คค่านี้แล้ว **return
           error ชัดเจน** ถ้าหาตัวเลือกไม่เจอ แทนที่จะ report สำเร็จเสมอแบบเดิม (`return { success: true }`
           ไม่สนใจผลจริงเลย)
      - `node --check` ผ่าน, `pytest tests/ -q` 381 passed (ไม่กระทบฝั่ง python)
      - **ยังไม่ได้ทดสอบจริง** — รอพี่ reload extension แล้วลองกดขั้น 4 ใหม่ ดูว่าคลิกโดน "กำหนดเวลา" ตรงๆ
        แทนที่จะไปโดน location dropdown

- [ ] **POST-2.21 เพิ่มขั้นตอนอัปโหลดภาพปก (Cover Upload) ใน Extension Side Panel — ปิดจุดเจ็บไม่ต้องเปิดโฟลเดอร์ลากไฟล์เอง (2026-09-06)**:
      - **คำขอ:** "มันค่อนข้างยุ่งยากที่จะเปิด folder แล้วมาเลือก ผมมี extension แล้วจะให้นายทำต่อจากอีก เอเจนน่ะ"
      - **วิเคราะห์:** ปัจจุบันระบบทำปก 9:16 (COV-1) เซฟไฟล์ไว้ใน `05_Covers_Thumbnails/{stem}_cover.jpg` คมชัดแล้ว แต่ขั้นตอนโพสต์ใน TikTok Studio พี่ยังต้องเปิดโฟลเดอร์ใน Windows Explorer แล้วลากไฟล์รูปปกไปหยอดเองในหน้าแก้ไขหน้าปก
      - **แผนงานรอบนี้:**
        1. **Backend (`media_service.py` & `api_exports.py`):** คืนค่า `cover_path` ใน `GET /api/exports` เพื่อให้ extension รู้จักตำแหน่งไฟล์รูปปกจริงในเครื่อง
        2. **Extension (`sidepanel.js` & `sidepanel.html`):**
           - ส่ง `cover_path` ไปยัง `POST /api/tiktok-autopost/prepare` เมื่อกด "เตรียมคลิปนี้"
           - เพิ่มพรีวิวรูปปก 9:16 ใน Side Panel ใต้ชื่อคลิป เพื่อให้เห็นภาพปกทันทีก่อนอัปโหลด
           - เพิ่มขั้นตอนใน Checklist: "อัปโหลดภาพปก" (ปุ่มกดทำ + checkbox ติ๊กมือ/ออโต้)
        3. **Extension Background Worker (`background.js`):**
           - เพิ่ม handler `upload-cover-only`: attach debugger สั้นๆ -> คลิกเปิด modal "แก้ไขหน้าปก" ของ TikTok Studio -> หา `<input type="file">` ของรูปภาพ -> เรียก `DOM.setFileInputFiles` ใส่ไฟล์ปกจาก `05_Covers_Thumbnails/` -> รอภาพโหลด -> คลิกปุ่ม "บันทึก" ใน modal -> detach ทันที (ไม่แช่ session ป้องกัน tab crash)
      - **Gate:** `node --check` ทุกไฟล์ js ผ่าน, `pytest tests/ -q` ผ่าน, ตรวจสอบ element id และ HTML tags ถูกต้องครบถ้วน

### Gate

- [ ] ทดสอบมือกับคลิปทดลองก่อน อย่างน้อย 3-5 คลิป สังเกตอาการบัญชีก่อนใช้จริง — รอพี่ทำ (ต้องผ่าน Todo ข้อแรกก่อน)
- [x] ปุ่ม manual (POST-1) ยังอยู่คู่กันเสมอ ปิด auto-post ได้โดยไม่กระทบ flow อื่น — ปุ่ม "เปิด TikTok Studio"/
      "มาร์คว่าโพสต์แล้ว" ของ POST-1.3 ไม่แตะเลย ปุ่มใหม่ (`autopostEnabled &&`) ซ่อนเองถ้า toggle ปิดอยู่
- [x] ไม่มี schedule/headless — ทำงานเฉพาะตอนพี่กดเท่านั้น — ยืนยันจากโค้ด: `runAutopost()` ถูกเรียกจาก
      `chrome.runtime.onMessage` เท่านั้น (มาจากคลิกปุ่มใน popup) ไม่มี `setInterval`/`chrome.alarms` ที่ไหนเลย

### Notes

- เจอ 2 เรื่องที่ต้องแยกกันชัด: (1) ความเสี่ยงจากวิธีอัตโนมัติ ต่างจากบอทสแปม/ปั่นยอดที่โดนแบนจริง
  (2) นโยบายเปิดเผยเนื้อหา AI ของ TikTok ที่มีผลกับคลิปพี่**ไม่ว่าจะโพสต์วิธีไหน** — คนละเรื่องกัน ไม่ได้แก้ในรอบนี้
- ตัดทิ้ง: เปิด Chromium แยกแบบ library สำเร็จรูป (`tiktok-uploader` ฯลฯ) เพราะต้องพึ่ง stealth plugin ปลอมลายนิ้วมือ
  — เสี่ยงกว่าดีไซน์ที่เลือกซึ่งใช้ session จริงของพี่เอง
- **2026-09-06 (พี่ทดสอบซ้ำ, เจอเหมือนเดิม):** ระหว่างปักตะกร้ายังไม่เสร็จ extension กด Post ไปแล้ว — พี่ขอ
  ให้**หยุดกด Post อัตโนมัติไปเลย เดี๋ยวกดเอง** (ให้ extension ใส่ข้อมูล/ปักตะกร้าอย่างเดียวพอ)
  **แก้แล้ว:** `popup.js` เลิก restore ค่า `autoClickPost` จาก `chrome.storage.local` — checkbox "กด Post/
  กำหนดเวลา อัตโนมัติทันที" **เปิด popup มาต้อง unchecked เสมอ** ทุกครั้ง (ค่าเดิมที่เคยติ๊กไว้จากเทสรอบก่อน
  เคยค้างอยู่แบบไม่รู้ตัว — เป็นสาเหตุที่มันกด Post ซ้ำอีกทั้งที่พี่ไม่ได้ตั้งใจจะให้กดรอบนี้) ต้องติ๊กเองใหม่ทุกครั้งถ้าจะใช้
  **ยังไม่ได้แก้เชิงลึก:** ข้อสันนิษฐานของพี่ที่ว่า attach ยังไม่โหลดเสร็จ — โค้ดปัจจุบัน `attachProductLink` ใช้
  `sleep()` คงที่คั่นระหว่างขั้นตอน (1.5-2.5 วิ) ไม่ได้ poll จนกว่า modal จะปิด/สินค้าจะแนบจริง ถ้าเน็ตช้ากว่านั้น
  อาจ return "success" ทั้งที่ modal ยังไม่ปิดจริง — ตอนนี้ปิดความเสี่ยงด้วยข้อบนแทน (ไม่กด Post อัตโนมัติ)

---

## Round TRK-3 — บอร์ดหลักคลีนไร้ความรก (Today-Only Posted, คลังสคริปต์หยิบทำวันนี้ & การ์ดตัดต่อเสร็จแนวนอนกะทัดรัด) — ย้ายบล็อกเต็มไป [HISTORY.md](file:///d:/Winona/Programmer/Capcut/HISTORY.md) แล้ว
 
---

## Round COV-1 — สตูดิโอสร้างปกคลิปด่วน 9:16 (Auto Highlight Crop, AI Hook & 4 TikTok Templates)

- **เป้าหมาย:** สตูดิโอสร้างภาพปกคลิปแนวตั้ง 9:16 (1080x1920) สำหรับโพสต์ลง TikTok Studio เพื่อเพิ่มยอดคลิก (CTR) ดึงภาพช็อตเด่น + AI ช่วยคิดข้อความ Hook ปกสั้นทรงพลัง + 4 แม่แบบสำเร็จรูปสไตล์ TikTok พร้อมปรับตำแหน่งข้อความ 3 โซน (บน/กลาง/ล่าง) และแปะป้าย 3D
- **ผลลัพธ์จาก Grill-Me:**
  1. ภาพพื้นหลัง: เลือกช็อตเด่นจาก 4-6 Candidate frames + Scrubber วิดีโอ หรือ อัปโหลดรูปสินค้าความละเอียดสูง
  2. ข้อความ Hook: AI เจน 4 สไตล์สั้นกระชับ (Curiosity, Value, Problem/Solution, Review/Rating) + แก้ไขคำได้อิสระ
  3. สไตล์แม่แบบ: 4 ธีม TikTok ยอดนิยม (Neon `#FFE600` ขอบดำ, Yellow Bar แถบเหลืองอักษรดำ, Modern Box กล่องกระจกเงา, Minimal Bold ขาวขอบดำหนา)
  4. ตำแหน่ง Hook: เลือกได้ 3 โซน (บน ~25% default, กลาง ~50%, ล่างเหนือบาร์ ~70%)
  5. ตรา 3D Badge: เลือกแปะมุมซ้ายบน / มุมขวาบน / ไม่ใส่
  6. เอาต์พุต: บันทึกลง `05_Covers_Thumbnails/{video_stem}_cover.jpg` ขนาด 1080x1920 พร้อมอัปเดต `cover_url` ให้ Tracker นำไปใช้ทันที
- **กฎเหล็กที่ต้องรักษา:**
  - เคารพ `ui_clean_standard.md` (ไม่มีสัญลักษณ์ซ้ำซ้อน ไม่มีเครื่องหมายบวกหรืออีโมจินำหน้าข้อความปุ่ม)
  - ไม่ใช้ hardcoded absolute path (ใช้ `BASE_DIR` จาก `scripts/config.py`)

### งานย่อย

- [x] **COV-1.1 Backend: Candidate Highlight Extraction & Image Scrubber API**
      - เพิ่ม `POST /api/covers/highlights` ใน `scripts/api_covers.py` สกัด 4-6 เฟรมสำคัญจากคลิป mp4 ส่งเป็น thumbnail base64 หรือ image URL
      - ปรับ `POST /api/covers/preview-frame` รองรับการระบุวินาทีละเอียด (timestamp) สำหรับ live scrubbing
- [x] **COV-1.2 Backend: AI Cover Hook Generator & 4 Pro Templates Render Engine**
      - เพิ่ม `POST /api/covers/generate-hooks` เจน 4 สไตล์ Hook สั้นกระชับ 2-4 คำ
      - ปรับปรุง `POST /api/covers/render-pro` เรนเดอร์ไฟล์ JPG 1080x1920 ด้วย Pillow/FFmpeg รองรับ 4 templates, 3 โซนตำแหน่ง Hook, vertical pan offset, และป้าย 3D badge overlay
- [x] **COV-1.3 Frontend: CoverStudioModal.jsx คอมโพเนนต์สตูดิโอ 9:16**
      - จอพรีวิว 9:16 พร้อม Safe Zone Overlay Guide (ขอบล่าง 420px และไอคอน TikTok ด้านขวา)
      - ส่วนเลือกรูป (4 ช็อตเด่น + Scrubber ละเอียด + อัปโหลดรูป)
      - ส่วนข้อความ Hook (AI Pills 4 สไตล์ + ช่องพิมพ์แก้คำ + ปุ่มเลือก 3 โซนตำแหน่ง)
      - ส่วนสไตล์แม่แบบ (4 การ์ดแม่แบบ + ตัวเลือกป้าย 3D badge)
- [x] **COV-1.4 Frontend Integration: ContentTrackerHub & ExportGallery**
      - เพิ่มปุ่ม `[สร้างปก]` บนการ์ด "ตัดต่อเสร็จ" และในแถวตาราง Daily Run Sheet
      - ผูก Event เมื่อบันทึกเสร็จ อัปเดตข้อมูลปกให้การ์ดแสดงรูปปกจริงทันที
- [x] **COV-1.5 TikTok Clean Capture, 3:4 Profile Ratio, Overlay Toggles & Dual Export (User ร้องขอ 2026-09-06)**:
      - **Backend (`scripts/api_covers.py`)**:
        - รองรับ `aspect_ratio`: `"9:16"` (1080x1920), `"3:4"` (1080x1440), หรือ `"both"`
        - รองรับสวิตช์ `enable_hook_text` และ `enable_badge` (ปิดแล้วได้ภาพคลีน 100%)
        - รองรับการค้นหา Raw Footage จาก `01_Raw/` หรือ `03_Projects/{project_name}/project.json`
        - คำนวณ Crop 3:4 อัตโนมัติร่วมกับ `pan_y_pct`
        - บันทึกทั้งไฟล์ `_cover.jpg` (9:16) และ `_cover_3x4.jpg` (3:4) เมื่อเลือก `"both"`
      - **Frontend (`CoverStudioModal.jsx`)**:
        - ติ๊กออก Hook และ Badge เป็น Default (`enableHookText = false`, `enableBadge = false`) ตามคำขอ
        - รองรับ **ลากเลื่อน (Drag to Pan) บนหน้าจอพรีวิวโดยตรง** ด้วยเมาส์/ทัช
        - รองรับ **ซูมเข้า-ออก (Zoom In/Out 1.0x - 2.5x)** ด้วย Scroll Wheel และ Slider ซูมขยายเพื่อดันซับไตเติลหลุดขอบเฟรม 100%
        - ซิงก์ค่า `zoom_scale` และ `pan_y_pct` ไปยัง Backend `render_pro_cover` ให้เรนเดอร์ภาพตรงเป๊ะกับพรีวิว
- [x] **COV-1.6 Gate & Tests Verification**
      - รัน `python -m compileall -q scripts` → ผ่านฉลุย ไร้ syntax error
      - รัน `python -m pytest tests/ -q -p no:cacheprovider` → **381 passed** (ครอบคลุม `test_covers_pro.py` 8 เคสครบทุก template + 3:4 profile + dual export + zoom/pan)
      - รัน `npm run build` ใน `frontend/` → ผ่าน 100% ไม่มี type/lint error (สร้าง bundle เรียบร้อยใน 4.16s)
      - ทดสอบ endpoint ด้วย python script / pytest → ยืนยัน parity ครบ
      - ตรวจสอบความถูกต้องด้วย `browser_subagent` → บันทึกวิดีโอ `cover_studio_zoom_drag_demo_1788705513755.webp` ยืนยันการลากเลื่อนพรีวิว, ปรับซูม 1.5x ดันซับหลุดเฟรม, และบันทึกสำเร็จจริงทั้ง 9:16 และ 3:4




#### POST-3.4 implementation update (2026-09-07)

- [x] ส่ง `cover_path` ล่าสุดจาก Side Panel ไปอัปเดต pending job ก่อนเปิด Cover Studio
- [x] จำกัดการค้นหา cover modal และ file input ให้อยู่ใน modal ล่าสุด ลดโอกาสเลือก DOM เก่าค้าง
- [x] รองรับรายการชั่วโมง/นาทีที่แสดงแบบมีหรือไม่มีเลขศูนย์นำหน้า และยืนยันค่าที่แสดงหลังเลือก
- [x] รัน syntax check, Node regression และ backend tests: Node 7 passed, backend 5 passed
- [ ] ทดสอบกับแท็บ TikTok ที่ล็อกอินจริงเพื่อยืนยันวันเวลาและการอัปโหลดปก (ต้องทำหลัง reload extension)


#### POST-3.5 — แก้ regression ขั้น 3 หลังทดสอบจริง (2026-09-07)

- [x] จำกัดช่องค้นหา Product ID และไอคอนค้นหาให้อยู่ใน dialog ของ Product Selector ล่าสุด
- [x] เพิ่ม regression assertion ป้องกันการย้อนกลับไปใช้ `document.querySelector` ช่องแรกทั้งหน้า
- [x] รัน syntax check, Node regression และ backend tests
- [ ] ยืนยันกับ TikTok Studio จริงหลัง Reload extension
#### POST-3.6 — แก้เฉพาะข้อ 4–5 โดยล็อกข้อ 1–3 (2026-09-07)

- [x] ตรวจและแก้ schedule picker ให้เลือกวัน/เวลาใน TikTok จริง พร้อมยืนยันค่าที่แสดง
- [ ] ตรวจและแก้ Cover Studio ให้เปิด modal ล่าสุดและแนบไฟล์ปกผ่าน CDP
- [x] ห้ามแก้ฟังก์ชันค้นหา/เลือกสินค้าในข้อ 1–3
- [x] รัน syntax, Node regression และ backend tests
- [ ] ทดสอบกับแท็บ TikTok Studio ที่ล็อกอินจริงหลัง reload extension
#### POST-3.6 implementation update (2026-09-07)

- [x] จำกัดการเลือก schedule ให้คลิกเฉพาะ `input[type="radio"][value="schedule"]` ป้องกันชนปุ่มโพสต์ข้อความเดียวกัน
- [x] ปรับเวลาให้เป็นช่วงละ 5 นาทีของ TikTok (เช่น 16:08 → 16:10) และรายงานค่าที่ปรับกลับไปที่ Side Panel
- [x] ปรับ UI ช่องวันที่/เวลา แยกป้ายกำกับและเพิ่ม `step="300"` ให้เลือกเวลาได้ตรงกับ TikTok
- [x] คงการแก้ Cover Studio และการส่ง cover path ล่าสุดจากรอบก่อน
- [x] ไม่แก้โค้ดค้นหา/เลือกสินค้าในรอบนี้
- [x] รัน syntax check และ Node regression: 8 passed
- [x] ผู้ใช้ยืนยันว่าขั้น 4 เปลี่ยนวันและเวลาใน TikTok ได้จริง และไม่โพสต์อัตโนมัติ
- [ ] ทดสอบการแนบปกกับแท็บ TikTok จริงหลัง Reload extension

#### POST-3.7 — แก้เฉพาะ flow แนบปก (2026-09-07)

- [x] ตรวจจุดเปิด Cover Studio และขอบเขต modal จาก DOM จริง
- [x] ทำให้ CDP file upload และการกดบันทึกเลือกองค์ประกอบใน modal ล่าสุดเท่านั้น
- [x] ห้ามแก้โค้ดข้อ 1–4 และห้ามแตะปุ่มโพสต์
- [x] เพิ่ม regression test สำหรับ flow แนบปก
- [x] รัน syntax และ Node regression
- [ ] ทดสอบแนบปกกับแท็บ TikTok จริงหลัง Reload extension
#### POST-3.7 implementation update (2026-09-07)

- [x] ตรวจพบ root จริงของ Cover Studio (`CoverEditor__root`) ที่ไม่มี `role="dialog"`
- [x] จำกัดการค้นหา input และปุ่มบันทึกไว้ใน Cover Studio ล่าสุด
- [x] เปิด `Runtime` ก่อนใช้ CDP file upload และยืนยันว่า modal ปิดหลังบันทึก
- [x] เพิ่ม regression contract สำหรับ Cover Studio และรัน Node regression: 8 passed
- [ ] ทดสอบแนบปกจริงหลัง Reload extension

#### POST-3.8 — ปรับตัวเลือกเวลาและสถานะขั้นตอน (2026-09-07)

- [x] เปลี่ยนช่องเวลาเป็นตัวเลือกทีละ 5 นาที และคุมเวลาขั้นต่ำ 15 นาทีตาม TikTok
- [x] ทำให้แถวขั้นตอนแสดงสถานะสำเร็จหลังตอบกลับสำเร็จอย่างแน่นอน
- [x] ห้ามเปลี่ยน flow ปักตะกร้าและการโพสต์
- [x] รัน syntax และ Node regression: 8 passed

#### POST-3.9 — ตรวจยืนยันกับ TikTok จริง: เวลาและ Cover upload (2026-09-07)

- [x] ตรวจ DOM จริง: schedule radio เป็น `value="schedule"` และ picker มีชั่วโมง 00–23 กับนาที 00–55 ทีละ 5 นาที
- [x] ยืนยันด้วยการเลือกตรงบน TikTok ว่า `11:15` เปลี่ยนเป็น `12:20` ได้
- [ ] ตรวจว่าการกดขั้น 4 จาก extension ส่งค่าฝั่ง Side Panel ไปถึง TikTok ในรอบเดียวกัน
- [ ] ตรวจข้อผิดพลาดข้อ 5 แยกเป็นเปิด modal, เลือกไฟล์ CDP, และบันทึกปก
- [ ] ทดสอบผ่าน extension ที่ Reload แล้ว โดยไม่กดโพสต์จริง

#### POST-3.10 - Keep open TikTok pickers stable and expose cover-step failures (2026-09-07)

- [x] Detect an already-open date/time picker and avoid clicking its input again.
- [x] Add regression contracts for picker targeting and preserve steps 1-3 and the publish button.
- [x] Keep Cover Studio targeting scoped to the latest `CoverEditor__root` and `ImageUpload__uploadArea`.
- [x] Run syntax checks and Node regression: 8 passed.
- [ ] Verify local cover-file transmission through a reloaded extension; browser controller blocks local file injection.

Notes: Live TikTok inspection found the schedule input at `11:25` while Side Panel showed `12:00`; the edit-cover control opened `CoverEditor__root` successfully.

#### POST-3.11 - Scroll TikTok time options before selecting (2026-09-07)

- [x] Find hour/minute options across the full TikTok picker and call `scrollIntoView({block:'center'})` before clicking.
- [x] Add a regression contract for values outside the current viewport such as `:00` and `:05`.
- [x] Run `node --check background.js` and Node regression: 8 passed.
- [x] Confirm from `test tt.mp4` that TikTok stayed at `10:40` while Side Panel requested `10:00`.
- [ ] Verify with the reloaded extension on the real tab without publishing.

Notes: Only `tiktok_autopost_extension/background.js` and its regression contract changed in this round. Steps 1-3, Cover step, and publishing remain untouched. Other files were already modified by parallel work and were not staged.

#### POST-3.12 - Find Cover Studio save button outside the editor root (2026-09-07)

- [ ] Include TikTok `cover-editor-container` in the save-button scope; the visible Save button is a sibling container outside `CoverEditor__root`.
- [ ] Add a regression contract for the real Cover Studio DOM classes.
- [ ] Run syntax check and Node regression without changing schedule, steps 1-3, or publishing.
- [ ] Verify modal -> local cover file -> Save through the reloaded extension when direct file injection is available.


#### POST-3.12 implementation update (2026-09-07)

- [x] Include `cover-editor-container` in Cover Studio save-button discovery.
- [x] Prefer the outer container because TikTok renders Save beside `CoverEditor__root`.
- [x] Add a regression contract for the real DOM class.
- [x] Run syntax checks and Node regression: 8 passed.
- [ ] Verify local file injection and Save through the reloaded extension; direct browser control still blocks local file transmission.

Notes: Schedule code and steps 1-3 remain frozen.

#### POST-3.13 - Persist completed schedule styling and resolve product-named covers (2026-09-07)

- [ ] Add the `completed` row class whenever `prepare-details` marks a step checkbox, including schedule step 4.
- [ ] Let `/api/exports` resolve a saved product-named cover such as `Logitech Wave Keys_cover.jpg` when the export stem has no exact cover file.
- [ ] Add regression coverage for the completion class and product-cover fallback.
- [ ] Run focused frontend/backend tests and build checks without changing schedule behavior or steps 1-3.
- [ ] Verify the extension receives `cover_path` and can start Cover Studio after reloading.


#### POST-3.13 implementation update (2026-09-07)

- [x] Add `.completed` styling when `prepare-details` marks any checklist checkbox, including schedule step 4.
- [x] Resolve product-named covers such as `Logitech Wave Keys_cover.jpg` when an export-stem cover is absent.
- [x] Add deterministic fallback test and run focused checks: backend 6 passed, extension 8 passed, Python compileall passed.
- [ ] Verify the reloaded extension receives the fallback `cover_path` and completes Cover Studio upload.

Notes: Schedule selection logic itself remains frozen; only checklist styling and cover metadata resolution changed.
