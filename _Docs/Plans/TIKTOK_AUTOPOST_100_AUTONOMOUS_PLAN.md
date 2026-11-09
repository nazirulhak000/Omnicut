# แผน: TikTok Auto-Post อัตโนมัติ 100% (ไม่ต้องมีคนกด)

- วันที่: 2026-11-09
- ดำเนินการโดย: Claude Code (Claude Opus 5.5)
- สถานะ: **แผนเท่านั้น — ยังไม่แตะโค้ด** รอผู้ใช้ตอบ "อนุมัติแผน"
- รอบใน TODO: `CLAUDE-PLAN-TIKTOK-AUTOPOST-100-AUTONOMOUS-20261109`

---

## 1. เป้าหมาย + นิยาม "100%"

เริ่มงานด้วยการกด 1 ครั้ง (หรือให้ scheduler เริ่มเอง) แล้วระบบทำครบทุกคลิปในคิวจนจบเอง:

prepare job → เปิด TikTok Studio `/upload` → อัปวิดีโอ → แคปชัน+แฮชแท็ก → แนบสินค้า Showcase → ปก 3:4 → ตั้งเวลา/โพสต์ → ยืนยันผลจริง → ack backend → คลิปถัดไป

**ผ่าน = ทั้ง 4 ข้อ**

| เกณฑ์ | ค่าเป้า |
| :--- | :--- |
| คลิปติดกันไม่มีคนแตะ | 10/10 คลิป (soak 1 คืน) |
| โพสต์ซ้ำ | 0 |
| สถานะใน OmniCut ตรงกับหน้า TikTok Studio Content | 100% |
| ถ้าเจอสิ่งที่ตัดสินใจเองไม่ได้ (captcha, login หลุด, บัญชีไม่ตรง) | หยุด + แจ้งเตือน ไม่เดา ไม่โพสต์มั่ว |

---

## 2. ผลตรวจโค้ดปัจจุบัน (ทำไมยังไม่ 100%)

โฟลว์ตอนนี้: loop อยู่ใน **sidepanel** (`tiktok_autopost_extension/sidepanel.js:2746` → `batch_orchestrator.js:282 executeSingleClipStages`) สั่ง service worker ทีละขั้นผ่าน message

### 2.1 Hard blocker (ยืนยันจากโค้ดแล้ว)

| # | ปัญหา | ที่ | ผล |
| :--- | :--- | :--- | :--- |
| B1 | `runWaitForUploadOnly()` ไม่ `return` อะไร → `sendResponse(undefined)` | `background.js:4658` · sidepanel เช็ก `if (!r) reject` ที่ `sidepanel.js:2934` | **ทุกคลิปพังที่ขั้น 2** "ไม่ได้รับคำตอบจาก Extension ขณะรออัปโหลดวิดีโอ" |
| B2 | orchestrator ส่ง `finalOutcome` เป็น string แต่ `reconcile` เช็ก `outcome?.markError` / `outcome?.outcome` | `batch_orchestrator.js:379` · `sidepanel.js:2983` | reconcile ไม่เคยรัน → สถานะไม่ sync |
| B3 | ตรวจ "กำลังอัป" ด้วย regex `NN%` ทั้ง `document.body` | `background.js:1454` | แคปชันมี `%` (เช่น "ลด 50%") → ค้าง timeout 60s คลิปพัง |
| B4 | ack ล้มครั้งเดียว `pendingReceipt` ค้าง, force release ไม่ล้าง | `background.js:546-590` | ทุกคลิปถัดไปโดน `posting_instance_busy` → ทั้ง batch ตาย |
| B5 | recovery 409 ส่ง `lease_token` แต่ `/pending` ตัด token ทิ้ง | `sidepanel.js:2837-2876` · `scripts/api_tiktok_autopost.py:448` | release ไม่สำเร็จ, job ค้าง |

### 2.2 ความเสี่ยงสูง (ทำให้ไม่นิ่ง / ซ้ำ / ต้องมีคน)

- **sidepanel ต้องเปิดค้าง** — state loop อยู่ใน panel; ปิด/รีโหลด = จบ ไม่มี resume (`sidepanel.js:2672`)
- **Service worker MV3** — state ใน memory หายเมื่อ worker restart; `waitForUpload` poll ได้ถึง 900s เกินลิมิต 5 นาทีต่อ request
- **chrome.debugger attach/detach ~8 ครั้ง/คลิป** + แถบ "is debugging this browser" ทุกครั้ง; กด Cancel หรือเปิด DevTools = ผลกลายเป็น unconfirmed
- **แท็บ `/content` ค้าง** ทำให้ข้ามการกดโพสต์เงียบๆ (`background.js:4466`)
- **Draft mode ไม่มีจริง** — `clickPostButton` กดปุ่ม "ตัวสุดท้าย" ที่ match Post/Schedule/Save draft (`background.js:4054`); backend ไม่รับ `draft_saved` (`scripts/posting_jobs.py:21`)
- **โพสต์ซ้ำได้**: `scheduled_on_platform` ไม่ mark export ถ้าไม่มี queue_id (`api_tiktok_autopost.py:578`); `confirmation_unknown` ถูก force-cancel แล้ว export กลับเป็นยังไม่โพสต์
- **False positive**: แค่หน้าไป `/content` ก็นับว่าสำเร็จ (`background.js:4128`); reconcile จับคู่ด้วย token เดียว / "แถวบนสุด" (`background.js:806-1000`)
- **ตั้งเวลา**: ปัด 5 นาที 23:58 → 00:00 วันเดิม (`background.js:2874`); ไม่เช็กกรอบ TikTok 15 นาที–10 วัน
- **Selector เปราะ** — match ข้อความไทย/อังกฤษตรงตัว, class `TUXTextInputCore`, `tiktok-timepicker-*`; หัวไฟล์ยังเขียน "UNVERIFIED" (`background.js:47`)
- **ฟังก์ชันที่มีแต่ไม่ถูกเรียก**: `dismissInterrupts`, `waitForSuccessToast`, `triggerSubmitWhenEnabled` ใน `content_script.js` (มีแต่เทสเรียก)
- **ทาง Python เดิมใช้ไม่ได้**: `tools/batch_tiktok_uploader.py` ฮาร์ดโค้ด `C:\Users\nazir\...`, tab id, ข้าม posting-job protocol, `submit_clip` คืน True เสมอ · `tools/run_batch_upload.py` ฮาร์ดโค้ดวัน/สินค้า

### 2.3 ของที่ใช้ต่อได้

- Backend protocol (`scripts/posting_jobs.py`, `api_tiktok_autopost.py`): lease / account guard / ack — มีเทส
- Extension Node tests 85/85 ผ่าน (แต่ mock ทั้งหมด ไม่มี e2e)
- โปรไฟล์ Chrome แยก `tools/tiktok_browser_profile/` login ไว้แล้ว (`tools/open_tiktok_browser.py`)
- Selector/ลำดับขั้นใน `background.js` = ความรู้ที่ผ่านหน้าจริงมาแล้ว ยกไปใช้ต่อได้

---

## 3. แนวทางที่เลือก: Hybrid 2 ชั้น

> Jev (กฎข้อ 19) ล่มตอนวางแผน (`JSONDecodeError`) → degrade ตามกฎ ทำงานต่อ · ต้องถาม Jev ใหม่ตอนเริ่ม Phase 1

| ทางเลือก | ข้อดี | ข้อเสีย | ตัดสิน |
| :--- | :--- | :--- | :--- |
| แพตช์ extension อย่างเดียว | เร็ว | ติดเพดาน MV3 (panel ต้องเปิด, worker ตาย, debugger infobar) ไม่มีทาง unattended จริง | ใช้เป็น Phase 1 |
| **Python Conductor คุม Chrome ผ่าน CDP (Playwright `connect_over_cdp`)** | รันนอกเบราว์เซอร์, ไม่มี infobar, resume ได้, จับภาพหลักฐานทุกขั้น, ตั้ง scheduler ได้ | งานใหม่ ~2–3 รอบ | **เป้าหลัก Phase 2** |
| คุมเมาส์/คีย์บอร์ดระดับ OS (pyautogui + OCR) | ไม่สน DOM | ช้า เปราะสุด จอต้องว่าง ล็อกจอไม่ได้ | ใช้เฉพาะ fallback กรณี native dialog เท่านั้น |

---

## 4. แผนเป็นเฟส

### Phase 0 — Baseline + เครื่องมือสังเกต (ไม่โพสต์จริง)

- [x] (2026-11-09 baseline: ext 85/85, pytest 87/87) รัน `node --test tiktok_autopost_extension/*.test.cjs` + `pytest tests/test_api_tiktok_autopost.py tests/test_channel_posting_protocol.py tests/test_post_lifecycle.py tests/test_posted_protection.py -q` บันทึก baseline
- [ ] เพิ่ม **step log + screenshot ทุกขั้น** ลง `.tmp/autopost_runs/<run_id>/` (ชื่อไฟล์ `NN_<stage>.png` + `run.jsonl`)
- [ ] เพิ่มโหมด **`dry_run`** = ทำทุกขั้นจนถึงก่อนกดโพสต์แล้ว Discard — ใช้ทดสอบซ้ำได้ไม่เปลืองโควตา
- [ ] จับ DOM snapshot หน้า `/upload` จริง (ก่อน/หลังอัป, Showcase modal, cover modal, schedule picker, toast) เก็บ `.tmp/autopost_dom/` → ใช้ทำ fixture เทส selector

### Phase 1 — แก้ hard blocker ใน extension (ให้ใช้ได้ทันที, กดเริ่ม 1 ครั้งแล้วจบ batch)

- [x] B1: `runWaitForUploadOnly` คืน `{success:true}` / `{success:false, reason}` + เทส sidepanel↔worker wiring
- [x] B2: (helper `shouldReconcileAfterPost` ใน batch_orchestrator.js รับทั้ง string+object) ส่ง object ผลเต็ม (`{outcome, toastResult, markError}`) เข้า `reconcile`; แก้เงื่อนไขให้รันเมื่อ `confirmation_unknown`
- [x] B3: (ตัดข้อความใน contenteditable/textarea/input ออกก่อน match) ตรวจ % เฉพาะใน element progress ของอัปโหลด ตัด caption editor ออก
- [x] B4: (โหมด `park` ใหม่: retry receipt 3 ครั้ง, งานที่กดโพสต์แล้วพักไว้ใน `unresolvedJobs` ไม่ cancel = กันโพสต์ซ้ำ) force release ต้อง retry/ล้าง `pendingReceipt`; ack ล้ม → retry 3 ครั้ง → mark `needs_reconcile` แล้วไปคลิปถัดไป ห้ามล็อกทั้ง batch
- [x] B5: (ตัด raw `/release force` ออกจาก sidepanel, `/clear` เฉพาะ job `prepared`) ให้เจ้าของ instance ดึง `lease_token` ได้ (หรือ `/clear` รับ job `attempted` ที่ instance เดียวกัน)
- [x] `runClickPostOnly` ทางลัด reconcile เฉพาะงานที่กดโพสต์แล้วจริง (เดิม: แท็บ /content ค้างทำให้ข้ามการกด) ไม่ใช่ทุกแท็บ TikTok
- [ ] attach debugger **ครั้งเดียวต่อคลิป** (session เดียวตลอด stage) ลด infobar/detach
- [ ] เลือกปุ่มตาม mode ชัดเจน: `schedule` → ปุ่ม Schedule, `post` → Post, `draft` → Save draft + backend รับ `draft_saved`
- [ ] ต่อ `dismissInterrupts` (content_script) ก่อนทุก stage และหลังกดโพสต์
- [x] ตั้งเวลา: 23:58 ปัดลง 23:55 (ไม่ข้ามวัน) + ปฏิเสธเวลาที่ผ่านแล้ว/ใกล้เกิน 15 นาที · *เพดานสูงสุด (10 หรือ 30 วัน) ยังไม่ใส่ — รอยืนยันจากหน้า TikTok จริง*
- [ ] `scheduled_on_platform` → mark export เป็น scheduled กันวนกลับมาโพสต์ซ้ำ; `confirmation_unknown` → reconcile บนหน้า Content ก่อนเริ่มคลิปถัดไป ห้าม force-cancel
- [ ] คุมความแม่น reconcile: ต้อง match แคปชัน ≥ N token + เวลาโพสต์อยู่ในหน้าต่าง ±10 นาที ห้ามใช้ "แถวบนสุด"
- [ ] Gate: Node tests + pytest ข้างบนผ่าน 100% + dry_run 3 คลิปบนหน้าจริง

### Phase 2 — Python Conductor (unattended จริง ไม่ต้องเปิด sidepanel)

โครง: `scripts/autopost_conductor/` (backend เรียกได้) + CLI `tools/run_autopost.py`

- [ ] **Browser**: เปิด Chrome จริงด้วยโปรไฟล์แยก `tools/tiktok_browser_profile` + `--remote-debugging-port=9333` (Chrome 136+ บังคับ user-data-dir ไม่ใช่ค่าเริ่มต้น — โปรไฟล์นี้เข้าเงื่อนไข) → Playwright `connect_over_cdp`; ไม่มี `--enable-automation`
- [ ] **Selector map กลาง** `tiktok_autopost_extension/tiktok_selectors.json` (ไทย+อังกฤษ, role/text/testid) ใช้ร่วมทั้ง extension และ conductor — แก้ที่เดียว
- [ ] **State machine + resume**: state ต่อคลิปเก็บใน JSON (atomic write + `threading.Lock` ตามกฎ 24) ล่มกลางทาง → เปิดใหม่แล้วตรวจหน้า Content ก่อนว่าโพสต์ไปแล้วหรือยัง (กันซ้ำ) ค่อยทำต่อ
- [ ] **ใช้ backend protocol เดิม** `prepare → pending(lease) → validate/begin → ack(evidence)` ผ่าน HTTP 127.0.0.1:8000 + auth key — ห้ามเขียน queue ตรงแบบ `batch_tiktok_uploader.py`
- [ ] **ขั้นต่อคลิป** (ยก logic จาก background.js): `set_input_files` วิดีโอ → รอ badge อัปเสร็จ → พิมพ์แคปชัน (คีย์บอร์ดจริง) → Showcase ค้น Product ID → เช็ก stock/radio disabled → ตั้งชื่อตะกร้า → ปก 3:4 (`set_input_files`) → ตั้งเวลา → กดปุ่มตาม mode (เมาส์จริง `page.mouse`)
- [ ] **ยืนยันผล 2 ชั้น**: (1) toast ใหม่หลังคลิก (2) เปิด `/tiktokstudio/content` หาแถวที่ match แคปชัน+เวลา → แนบ screenshot เป็น evidence ใน ack; ไม่เจอทั้งคู่ = `confirmation_unknown` + reconcile รอบหน้า
- [ ] **Interrupt handler แบบกฎ**: Discard ดราฟต์ค้าง / Post now (copyright check) / Leave site / ทัวร์ฟีเจอร์ใหม่ / cookie banner → กดอัตโนมัติ · **captcha, login หลุด, บัญชีไม่ตรง, 2FA** → หยุดทันที + แจ้งเตือน (PushNotification / ActivityCenter) ห้ามเดา
- [ ] **ทีละคลิป ต่อบัญชี** + cooldown 20–40s สุ่ม — *ข้อยกเว้นกฎ 24 (concurrency 4) เพราะ TikTok จับ spam/แบนบัญชี — ต้องให้ผู้ใช้ยืนยันข้อยกเว้นนี้*
- [ ] **Quota**: นับ scheduled ที่ค้างบน TikTok (สูงสุด 30) เกินแล้วเปลี่ยนเป็น draft หรือหยุดรอวันถัดไป
- [ ] **Scheduler**: Windows Task Scheduler (หรือ job ใน backend) รันช่วงเวลาที่กำหนด; เครื่องห้าม sleep ระหว่างรัน (`SetThreadExecutionState`)
- [ ] **UI**: ปุ่ม "เริ่มโพสต์อัตโนมัติ" ในแอป → backend spawn conductor; หน้าสถานะต่อคลิป + รูปหลักฐาน + ปุ่มหยุด
- [ ] **Fallback ระดับ OS** (เฉพาะเมื่อจำเป็น): `pywinauto` ปิด native file dialog / permission prompt ที่ CDP แตะไม่ได้
- [ ] เลิกใช้/ย้าย `tools/batch_tiktok_uploader.py`, `tools/run_batch_upload.py` ไป `06_Archive` หลัง conductor ผ่าน (ถามผู้ใช้ก่อน)
- [ ] Extension คงไว้เป็นทางสำรอง manual

### Phase 3 — ทดสอบจริงแบบไต่ระดับ

1. [ ] `dry_run` 5 คลิป (ไม่กดโพสต์) — screenshot ทุกขั้นถูกต้อง
2. [ ] โพสต์จริง 1 คลิปแบบ **"เฉพาะฉัน" (Only me)** — ยืนยัน confirmation + ack; ลบโพสต์ทดสอบหลังตรวจ (ขออนุญาตผู้ใช้ก่อนลบ)
3. [ ] Schedule 3 คลิปจริง — ตรวจตรงหน้า Content
4. [ ] Soak 10 คลิปข้ามคืน — ผ่านเกณฑ์ข้อ 1
5. [ ] จำลองล่มกลางทาง (kill process หลังกดโพสต์) → resume ต้องไม่โพสต์ซ้ำ

### Phase 4 — กัน TikTok เปลี่ยนหน้า (selector drift)

- [ ] Health check รายวัน: เปิด `/upload` แบบ dry → เช็ก selector สำคัญครบไหม → รายงานเขียว/แดงในแอปก่อนเริ่ม batch
- [ ] เทส selector กับ DOM fixture จาก Phase 0 (offline, deterministic ตาม testing_standard)

---

## 5. ความเสี่ยงที่ต้องรู้

- TikTok ToS/anti-bot: อัตโนมัติเต็มตัวเสี่ยงบัญชีโดนจำกัด → ทีละคลิป, หน่วงสุ่ม, ใช้โปรไฟล์จริงที่ login มือ, ไม่ปลอม fingerprint
- แคปชันต้องไม่มีราคา/ส่วนลด (กฎช่อง) — เพิ่ม guard ตรวจแคปชันก่อนพิมพ์ (ช่วยตัดปัญหา `%` ด้วย)
- เครื่องต้องเปิด + login Windows + Chrome โปรไฟล์นี้ห้ามเปิดซ้อนด้วยมือระหว่างรัน

---

## 6. พรอมพ์พร้อมใช้ (copy ไปสั่ง AI ทีละเฟส)

### 6.1 พรอมพ์ตรวจเช็ก (Audit — ไม่แก้โค้ด)

```text
อ่าน AGENTS.md, TODO.md, _Docs/Plans/TIKTOK_AUTOPOST_100_AUTONOMOUS_PLAN.md ก่อน
งาน: ตรวจระบบ TikTok autopost ว่ายังมีจุดไหนที่ทำให้โพสต์อัตโนมัติไม่จบ 100% (ห้ามแก้โค้ด)
1. ไล่โฟลว์จริง sidepanel.js (ปุ่มเริ่ม batch) → batch_orchestrator.js executeSingleClipStages → background.js message handlers → scripts/api_tiktok_autopost.py + scripts/posting_jobs.py
2. ยืนยันทีละข้อว่า blocker B1–B5 และความเสี่ยงหัวข้อ 2.2 ในแผนยังอยู่ไหม (อ้าง file:line)
3. หาจุดใหม่ที่แผนยังไม่ครอบคลุม: ทุกที่ที่ต้องมีคนกด/ยืนยัน, ทุก throw ที่หยุด batch, ทุก timeout, ทุก selector ที่ match ข้อความตรงตัว
4. รัน node --test tiktok_autopost_extension/*.test.cjs และ pytest เทส posting ที่ระบุใน Phase 0 รายงานผล
5. ถ้าเปิด Chrome ได้: ใช้ dry_run (ห้ามกดโพสต์จริง) ไล่ 1 คลิปบนหน้า TikTok Studio /upload จริง เก็บ screenshot ทุกขั้นลง .tmp/autopost_runs/
สรุปเป็นตาราง: จุด | file:line | อาการ | ร้ายแรง (block/เสี่ยง/เล็ก) | วิธีแก้ 1 บรรทัด
อัปเดตหัวข้อ 2 ของแผนถ้าเจอของใหม่ บันทึกรอบลง TODO.md ระบุ "ดำเนินการโดย: <เอเจนต์> (<โมเดล>)"
```

### 6.2 พรอมพ์ Phase 1 (แก้ extension)

```text
อ่าน AGENTS.md + _Docs/Plans/TIKTOK_AUTOPOST_100_AUTONOMOUS_PLAN.md หัวข้อ 2 และ Phase 1
แตกกิ่ง fix/tiktok-autopost-blockers (กฎ 25) เขียนบล็อกรอบลง TODO.md ก่อนแตะโค้ด
แก้ทีละข้อใน checklist Phase 1 ตามลำดับ B1 → B5 ก่อน แล้วค่อยข้ออื่น
ทุกข้อ: เขียนเทสที่ fail ก่อน (background.test.cjs / batch_orchestrator.test.cjs / pytest) แล้วค่อยแก้ให้ผ่าน
เพิ่มเทส wiring จริง sidepanel action → worker handler → response shape (ตัวที่ทำให้ B1 หลุดมาได้)
ห้ามโพสต์จริงระหว่างพัฒนา ใช้ dry_run เท่านั้น
Gate: node --test tiktok_autopost_extension/*.test.cjs + pytest posting tests ผ่าน 100% + dry_run 3 คลิปบนหน้าจริงพร้อม screenshot
ติ๊ก checklist ในแผน + TODO.md ตามจริง ห้ามติ๊กเพราะ "เขียนโค้ดจบ"
```

### 6.3 พรอมพ์ Phase 2 (Python Conductor)

```text
อ่าน AGENTS.md + _Docs/Plans/TIKTOK_AUTOPOST_100_AUTONOMOUS_PLAN.md Phase 2 ทั้งหมด
สร้าง scripts/autopost_conductor/ + tools/run_autopost.py ตามแผน:
- เปิด Chrome โปรไฟล์ tools/tiktok_browser_profile พร้อม --remote-debugging-port แล้ว Playwright connect_over_cdp
- ยก selector/ลำดับขั้นจาก tiktok_autopost_extension/background.js ไปไว้ที่ tiktok_selectors.json ใช้ร่วม
- ใช้ posting-job protocol ของ backend เท่านั้น (prepare/pending/validate/ack) ห้ามเขียน schedule store ตรง
- state machine + resume + ตรวจหน้า Content ก่อนทำต่อ กันโพสต์ซ้ำ
- ยืนยันผล 2 ชั้น (toast + หน้า Content) แนบ screenshot เป็น evidence
- captcha/login หลุด/บัญชีไม่ตรง = หยุด + แจ้งเตือน ห้ามเดา
- ทีละคลิปต่อบัญชี + cooldown สุ่ม 20–40s
- มีโหมด --dry-run (ไม่กดโพสต์)
เทส offline ด้วย DOM fixture จาก .tmp/autopost_dom/ + mock backend; ห้ามแตะข้อมูลจริงในเทส
Gate: pytest ใหม่ผ่าน 100%, dry_run 5 คลิปจริงพร้อมรูปหลักฐาน แล้วหยุดถามผู้ใช้ก่อนโพสต์จริงคลิปแรก
```

### 6.4 พรอมพ์ Phase 3 (ทดสอบจริง)

```text
ทำ Phase 3 ในแผน _Docs/Plans/TIKTOK_AUTOPOST_100_AUTONOMOUS_PLAN.md ทีละขั้น หยุดถามผู้ใช้ก่อนขึ้นขั้นถัดไปทุกครั้ง
ขั้น 2 ต้องตั้ง visibility "เฉพาะฉัน" และขออนุญาตก่อนลบโพสต์ทดสอบ
รายงานผลแต่ละขั้น: จำนวนคลิป, สำเร็จ/ล้ม, ซ้ำ, สถานะ OmniCut vs หน้า Content, ลิงก์รูปหลักฐานใน .tmp/autopost_runs/
ลบไฟล์ทดสอบและถอดรายการทดสอบออกจาก registry ทันทีหลังจบ (กฎ 11/15)
```


---

## 7. สถานะการทำงานจริง (อัปเดต 2026-11-09 — Claude Code / Claude Sonnet 5.5)

**ปรับแผน Phase 2:** ไม่เขียน selector ใหม่เป็น Python/Playwright — ใช้ **Node host** (`tools/autopost_conductor/`) โหลด `background.js` เดิมที่ผ่านหน้าจริงมาแล้ว รันผ่าน CDP ตรง (chrome shim) ได้ครบเรื่อง headless/ไม่มี infobar/resume โดยไม่ต้องย้าย selector ซ้ำ

| รายการ | สถานะ |
| :--- | :--- |
| Phase 1: B1–B5, /content ค้าง, ปัดเวลา, กันเวลาผ่านแล้ว | ทำแล้ว (commit 2c3132a) |
| Phase 1: `scheduled_on_platform` วนซ้ำ | แก้ฝั่ง conductor: ข้าม export ที่มี job อยู่แล้ว (เดิมของ backend กันโพสต์ซ้ำถูกต้องอยู่แล้ว ไม่แก้) |
| Phase 1: draft mode / debugger session เดียว / dismissInterrupts ใน extension | **ตัดออก** — conductor แทนที่ทางนี้ (ไม่ใช้ batch/draft; worker ตัวเดิมมี dismiss dialog ของตัวเองในแต่ละขั้น) |
| Phase 0: step log + screenshot + `dry_run` + DOM dump | ทำใน conductor (`--dry-run`) |
| Phase 2: conductor (sequential, resume, park, stop+ALERT, keep-awake, price-caption guard) | ทำแล้ว · เทส offline 15 ข้อ |
| Phase 2: Task Scheduler | มี `install_task.ps1` (preview เป็นค่าเริ่มต้น ยังไม่ register) |
| Phase 2: ปุ่ม Start ในแอป / auto-detect quota 30 | **ยังไม่ทำ** — ต้องแตะ route policy + frontend ที่ agent อื่นแก้ค้างอยู่ |
| Phase 4: health check | `--health` เขียน `.tmp/autopost_health.json` + task รายวัน (ยังไม่ register) |
| Phase 3: health + dry-run บนหน้าจริง | **ผ่าน** (ผู้ใช้ login แล้ว): `--health` ok · `--dry-run --limit 1` ผ่านครบ upload → รอ 100% → แคปชัน → ตะกร้า → ตั้งเวลา → ปก(auto) แล้วคืนงาน คิวไม่ค้าง (planned 42) · พบ+แก้ 6 จุดจากหน้าจริง: `Headers` ไม่มีใน vm · อ่านบัญชีแข่งกับเมนูโปรไฟล์ · เลือก dialog ผิดอัน (Add link) · native beforeunload บล็อก reset · readiness ตอนหน้าค้างฟอร์ม · Discard-this-edit หลังปิด Cover |
| Phase 3: โพสต์จริง / ตั้งเวลาจริง / รันข้ามคืน | **ยังไม่ทำ** — (1) คิวทุกคลิปเลยเวลาแล้ว ต้อง re-plan ในแอป (2) ปกเองใช้ไม่ได้ ต้องให้ผู้ใช้ตัดสิน `--cover-fallback` (3) สัญญาไว้ว่าจะถามก่อนโพสต์จริงคลิปแรก |


### 7.1 สถานะล่าสุดหลังโพสต์จริง + จำลองความล้มเหลว (2026-11-09 ดึก — Claude Code / Claude Opus 5.5)

**โพสต์จริงผ่านทั้งสาย 3 คลิป** (ตั้งเวลา 10 พ.ย. 07:00 / 14:00 / 16:20): upload → caption → ตะกร้า → schedule → โพสต์ → ack backend → ตรวจหน้า Content = `scheduled` + `verified: true`

พบและแก้จากของจริง: toast ของ TikTok บัญชีนี้คือ **"Video published"** (ไม่มี successfully แม้ตั้งเวลา) → backend regex เข้มไป ack ถูกปฏิเสธ 422 job ค้าง `publishing` · worker จัด outcome เป็น `published` ทั้งที่ตั้งเวลา · หน้า Content อัปเดตช้ากว่า toast (ต้องรีโหลดซ้ำ) · 19/41 คลิปในคิวชี้ export ที่ไม่มีแล้ว

| สถานการณ์ | ผลจริง |
| :--- | :--- |
| หน้าต่าง 1024×700, 820×900 | modal เลือกสินค้าของ TikTok ถูกตัด → ล้ม · **แก้**: ขยายหน้าต่างอัตโนมัติ หรือจำลอง viewport 1440×900 · ผ่านทั้งสองทาง |
| 1366×768 / 1920×1080 | ผ่าน (1366 สะดุด 1 ครั้งแล้วผ่านเมื่อรันซ้ำ → เพิ่ม retry 1 ครั้งก่อนกดโพสต์) |
| เน็ตช้า (200KB/s) | ผ่าน |
| เน็ตหลุด 30 วิกลางอัปโหลด | พลาดขั้นรอ → retry จากหน้าสะอาด → ผ่าน |
| เน็ตล่มถาวร | คลิปล้มสะอาดตามเวลาที่กำหนด ไม่ค้าง |
| backend ล่มกลางคลิป | คลิปล้มสะอาด ไม่ค้าง · backend กลับมา → รันต่อได้ คิวคืน `planned` เอง ไม่โพสต์ซ้ำ |
| Chrome ถูกปิดกลางคลิป / ระหว่างคลิป | คลิปล้มสะอาด · เปิด Chrome ใหม่เอง login ยังอยู่ · 2/2 คลิปผ่านหลังกู้ |
| แท็บ TikTok ค้าง (renderer ไม่ตอบ) | เจอจริง: ทุกคำสั่งค้างเงียบ → **แก้**: timeout ทุกคำสั่ง CDP + ปิดแท็บค้างเปิดใหม่เอง |
| โปรเซสไม่ยอมจบเอง (ค้างจน timeout 1500s) | เจอจริงตอนจำลองเน็ต → **แก้**: ปล่อย session และ exit เองเสมอ (ยืนยัน exit=0) |
| worker ถูกแทนแล้ว worker เก่ายังตอบ "busy" | เจอจริง → **แก้**: shim เก็บ listener ตัวล่าสุดตัวเดียว |

**ยังไม่ได้ทดสอบสด:** ป๊อปอัป "Post now" ตรวจลิขสิทธิ์ (ไม่เคยโผล่ในการรันจริง มีแต่เทส mock) · captcha/2FA/login หมดอายุ · สินค้าหมด/Unavailable · ฆ่ากระบวนการ *หลัง* กดโพสต์ (ทดสอบ resume ไม่โพสต์ซ้ำ — มีเทส mock ไม่มีของจริง เพราะต้องโพสต์จริงอีก) · รันข้ามคืน 10 คลิป · ปกเอง (บัญชีนี้ไม่มีให้อัปโหลด ใช้ปกอัตโนมัติ) · ซูม/DPI เกิน 150% บนเครื่องจริง
