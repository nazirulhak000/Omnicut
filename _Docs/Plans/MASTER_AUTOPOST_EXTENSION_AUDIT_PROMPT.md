# 🔍🤖 MASTER PROMPT: Deep Audit & Stabilisation of the TikTok Autopost Extension
# พรอมต์แม่บทตรวจ extension โพสต์อัตโนมัติ (OmniCut TikTok Post Helper) ทุกมุม ทุกจุด — เป้าหมาย "เสถียรที่สุด"

> วิธีใช้: คัดลอกบล็อก ```markdown ด้านล่างทั้งก้อนไปวางให้ AI agent (Claude Code ฯลฯ) · สถานะข้อเท็จจริงอ้างอิง ณ 2026-11-10, extension v0.4.1, commit `8bf9ba4` / `e0a23d5`
> ผู้เขียน: Claude Code (Claude Sonnet 5.5) · เป็นพรอมต์ 2 เฟส: **เฟส A ตรวจอย่างเดียว (อ่าน/ทดสอบ ห้ามแก้โค้ด) → รายงาน → รอผู้ใช้พิมพ์ "อนุมัติ" → เฟส B แก้ตามลำดับความสำคัญพร้อมเทส**

```markdown
/scrutinize /diagnose /tdd /video-editing

คุณคือ Principal Reliability Engineer + Chrome MV3 Extension Architect + QA Lead ที่เคยทำระบบ browser automation ที่ต้องรันไม่มีคนเฝ้าบนเว็บของบุคคลที่สาม (TikTok Studio) และต้อง "ห้ามโพสต์ซ้ำ/ห้ามโพสต์ผิดบัญชี/ห้ามโพสต์สดโดยไม่ตั้งใจ" ตอบเป็นภาษาไทย กระชับ ตรงประเด็น (กฎข้อ 7 ของ AGENTS.md)

---

## 🎯 ภารกิจ (Objective)
ตรวจ **extension `tiktok_autopost_extension/` ทั้งชุด + จุดที่มันคุยด้วย** (backend `scripts/api_tiktok_autopost.py`, `scripts/posting_jobs.py`, `scripts/api_schedule_queue.py`, conductor `tools/autopost_conductor/`, หน้าแอปหลักที่แสดงคิว) ให้ครบทุกมุม แล้ว:
1. หา **บั๊ก ช่องโหว่ความปลอดภัย จุดที่จะพังเมื่อรันนาน/รันหลายคลิป/เจอสถานการณ์แปลก** ทุกจุดพร้อมหลักฐาน
2. หา **ฟีเจอร์/การป้องกันที่ควรเพิ่ม** เพื่อให้เสถียรที่สุด (จัดลำดับตามผลต่อความเสถียรและความปลอดภัย ไม่ใช่ตามความเท่)
3. เสนอแผนแก้ + ทดสอบ แล้ว **หยุดรออนุมัติ** (เฟส A) · ลงมือเฉพาะหลังผู้ใช้พิมพ์ "อนุมัติ" (เฟส B)

เป้าหมายสูงสุดที่วัดได้: คิว 30 คลิปรันครบด้วยปุ่มเดียวในแผงข้าง โดย (ก) ไม่มีโพสต์ซ้ำ/ผิดบัญชี/โพสต์สด/โพสต์ราคา (ข) ทุกความล้มเหลวมีข้อความที่บอกสาเหตุจริง ไม่ค้างเงียบ (ค) กู้คืนเองได้จากเน็ตหลุด/backend ล่ม/worker ถูก kill/Chrome ปิด (ง) ไม่ทิ้งขยะบน TikTok (แบบร่างค้าง, หน้า upload ค้าง)

---

## ⛔ กฎเหล็ก (STRICT DON'Ts) — ละเมิดข้อใดให้หยุดทันทีและรายงาน
1. ❌ **ห้ามกดโพสต์จริง/schedule จริงบนบัญชี TikTok** โดยไม่มีคำสั่งชัดเจนของผู้ใช้ในข้อความนั้น (การอนุมัติครั้งก่อนไม่ครอบคลุมครั้งนี้) ทดสอบหน้าจริงได้เฉพาะ: (ก) **Save draft** แล้วลบแบบร่างทิ้งทันทีและยืนยันว่า Drafts กลับเป็น 0 (ข) โหมดจำลองขั้นกดโพสต์ (`extension_e2e.js` ที่ stub `click-post-only`) (ค) dry-run ของ conductor (`--dry-run` ไม่กดโพสต์)
2. ❌ **ห้ามให้ caption/hashtags มีราคา ส่วนลด หรือการเดาราคา** (กฎของช่อง: ผิดกติกา TikTok) และห้ามให้ placeholder เช่น `{product_name}` หลุดไปโพสต์
3. ❌ **ห้ามลบ/เขียนทับ `01_Raw/`, `02_Assets/`** · ห้ามลบคลิป `04_Exports/` · ห้ามแตะคลิปที่ schedule/โพสต์แล้วบน TikTok (ลบได้เฉพาะของทดสอบที่คุณสร้างเอง และต้องแจ้ง)
4. ❌ **ห้ามอ่าน พิมพ์ หรือบันทึก API key / token / รหัสผ่าน** ลงรายงาน ล็อก คอมมิต หรือข้อความ (ตรวจว่า extension เองก็ไม่รั่วลง log/คลิปบอร์ด/ข้อความ error ด้วย)
5. ❌ **ห้ามสลับ/ใช้บัญชี GitHub, `gh`, หรือ credential อื่นโดยไม่ได้รับอนุญาตชัดเจน**
6. ❌ **ห้ามโพสต์พร้อมกันหลายคลิป** (ทีละคลิปเสมอ เสี่ยงบัญชีโดนจำกัด) · ห้ามลดการกันโพสต์ซ้ำเพื่อให้เทสผ่าน
7. ❌ **ห้ามอ้างว่า "ผ่าน/แก้แล้ว" ถ้าไม่ได้รันจริง** แยกชัดเจน 3 ระดับ: `ยืนยันบนหน้า TikTok จริง` / `ยืนยันด้วยเทสหน่วย-จำลอง` / `อ่านจากโค้ดเท่านั้น (ไม่ได้ทดสอบ)`
8. ❌ **ห้าม hardcode path ตายตัว** (ใช้ `pathlib`/`scripts/config.py`) · ห้ามติดตั้งแพ็กเกจนอก venv/`requirements.txt`
9. ❌ **ห้ามทิ้งขยะทดสอบ** (แบบร่างบน TikTok, job ค้างสถานะ claimed, รายการคิวชั่วคราว, ไฟล์ใน `04_Exports/`) ทำความสะอาด 100% ทุกครั้ง แล้วรายงานสถานะคิว/job/Drafts ก่อน-หลัง
10. ❌ ห้ามเปิดไฟล์ใหญ่ทั้งไฟล์ถ้าไม่จำเป็น (`background.js` ~5.6k บรรทัด, `sidepanel.js/html` ~3.4k/4.9k, `HISTORY.md`) อ่านเป็นช่วง ≤100 บรรทัดต่อครั้ง ใช้ Grep นำทาง (token-efficiency-guardian)

---

## 🧭 กติกาการทำงาน (ต้องทำก่อนเริ่ม)
1. อ่าน `TODO.md` (ส่วนรอบ `CLAUDE-PLAN-TIKTOK-AUTOPOST-100-AUTONOMOUS-20261109`) · `git status` (มี session อื่นแก้ค้าง: อย่าแตะ/อย่ารวมไฟล์ที่ไม่ใช่ของคุณ) · อ่านแผนเดิม `_Docs/Plans/TIKTOK_AUTOPOST_100_AUTONOMOUS_PLAN.md`, `TIKTOK_QUOTA_SCHEDULED_COUNT_PLAN.md`, `TIKTOK_DRAFT_MODE_PLAN.md`
2. **เขียนแผนรอบนี้ลง `TODO.md` ก่อนแตะโค้ด** (ระบุ `ดำเนินการโดย: <เอเจนต์> (<โมเดล>)`) · ปิดรอบแล้วย้ายเข้า `HISTORY.md`
3. เรียก Jev ตาม AGENTS ข้อ 19 ที่จุดบังคับ (ก่อนเริ่ม, ตอนมีทางเลือก 3–7 ทาง, ก่อน commit) confidence < 0.80 หรือ null = หยุดถามผู้ใช้ · คำตอบ Jev ไม่ใช่สิทธิ์อนุมัติ
4. ใช้ติดต่อ TikTok จริงเฉพาะ Chrome ที่โปรไฟล์ `tools/tiktok_browser_profile` พอร์ต 9333 (login แล้ว) · ทุกครั้งที่แก้โค้ด extension ให้ **ยกเลขเวอร์ชันใน `manifest.json`** (Chrome cache service worker ตาม id+version) และใช้สำเนาสดใน e2e (`.tmp/e2e_ext/`)
5. รัน `pytest` ชุดที่เกี่ยว + `node --test tiktok_autopost_extension/*.test.cjs tools/autopost_conductor/*.test.cjs` + `npm test` (frontend) ก่อนอ้างผล · เครื่องนี้ GPU/CPU แรง แต่ **งานโพสต์ห้ามขนาน**
6. commit แบบแยกเฉพาะไฟล์ของคุณ (temporary `GIT_INDEX_FILE` + `commit-tree` + `update-ref`) ห้ามรวมงาน session อื่น · ข้อความ commit ลงท้าย attribution ตามที่ระบบกำหนด · กิ่งเดียว `main` (กฎข้อ 25) · push ต้องรอผู้ใช้สั่ง (บัญชี `wni-nasirulhak` ไม่มีสิทธิ์เขียน ต้องได้รับอนุญาตก่อนสลับบัญชี)

---

## 📸 ภาพรวมระบบ ณ ตอนนี้ (ข้อเท็จจริงที่ต้อง "ตรวจซ้ำ" ไม่ใช่เชื่อ)
- **ส่วนประกอบ**: service worker `background.js` (19 actions: claim-posting-job, upload-file-only, wait-for-upload-only, prepare-details, type-caption-only, attach-product-only, upload-cover-only, schedule-mode-only, click-post-only, **save-draft-only**, verify-post-content, **verify-draft-content**, retry-posting-receipt, release-posting-job, reconcile-posting-result, reset-upload-page, detect-tiktok-quota, broadcast-batch-signal, select-posting-channel) · แผงข้าง `sidepanel.html/js` (รายการคลิป, ติ๊กเลือก, 3 โหมด, โควตา, log) · `batch_orchestrator.js` (10 ขั้นต่อคลิป, breaker ล้ม 3/ไม่แน่ใจ 2) · `post_guard.js` (ตัวกัน) · `quota_detector.js` · `automation.js` (CDP helpers/ปก) · `content_script.js`, `popup.html/js`, `batch_runner.js` (ของเก่า — ตรวจว่ายังใช้ไหม/ควรลบหรือกันออก) · permissions: `debugger tabs storage sidePanel scripting windows`; host: `127.0.0.1:8000`, `localhost:8000`, `www.tiktok.com`
- **protocol v2**: prepare → claim(lease) → validate/attempt(fence, `publish_attempt` ครั้งเดียว) → ack/reconcile; ผลสุดท้าย `published` / `scheduled_on_platform` / `draft_saved` / `confirmation_unknown`; สถานะคิว `planned→ready_for_extension→(posted | scheduled_on_platform | draft_on_platform | confirmation_unknown)`
- **ทดสอบแล้วบนหน้าจริง**: schedule ผ่านแผงข้าง/conductor, Save draft, ปก 3:4, นับโควตา (list virtualized), กู้แท็บหลังโพสต์, ลบโพสต์/แบบร่าง
- **ยังไม่เคยทดสอบจริง**: โควตา schedule เต็ม 30/30 จริง · modal ลิขสิทธิ์ "Post now" · captcha/2FA/login หมดอายุกลางรอบ · สินค้าหมด/ลิงก์สินค้าผิด · ปิดแผงข้างกลางรอบ · kill Chrome หลังกดโพสต์ · Chrome ส่วนตัวของผู้ใช้ที่มี extension อื่น · DPI/zoom >150% · รัน 30 คลิปติดกัน/ข้ามคืน · เพดาน schedule จริงของ TikTok (โค้ดสมมติ 30) · `chrome.alarms`/MV3 worker หลับกลางรอบยาว
- **ที่เคยเจอจริง (ห้ามกลับไปพัง — ต้องมีเทสกัน)**: ปกถูกนับว่าล้มเพราะ TikTok เคลียร์ `input.files` · ปก 9:16 ถูกครอป (ต้อง 3:4) · หลังโพสต์จริงแท็บถูกพาไป Content ทำให้ทุกขั้นถัดไปหาแท็บไม่เจอ · รายการ Content เป็น virtualized (อ่านครั้งเดียวได้ ~8 แถว) · TikTok ไม่มี toast หลัง Save draft (พาไป `?tab=draft`) · toast "Video published" เหมือนกันทั้งโพสต์สดและ schedule · โฟกัสคีย์บอร์ดอยู่ที่แผงข้าง ทำให้พิมพ์ caption ไม่เข้า · modal เพิ่มสินค้าถูกตัดเมื่อจอแคบ · "Leave site?" (beforeunload) ค้าง · service worker เก่าถูก cache · `{product_name}` หลุดใน caption · การกดปุ่ม Post ใน draft mode เดิมจะโพสต์สด
- **สมมติฐาน/ค่าตั้งที่ยังไม่ยืนยัน**: เพดาน schedule = 30 · schedule ล่วงหน้า ≥15 นาที, ขั้น 5 นาที, ≤30 วัน · เวลา badge = GMT+7 ถ้าไม่ระบุ · แบบร่างหมดอายุ 60 วัน · lease 5 นาที

---

## 🔍 สถานีตรวจ 14 สถานี (Audit Traversal Matrix) — ทุกสถานีต้องมี: สิ่งที่ตรวจ · วิธีตรวจ · หลักฐาน · ระดับความมั่นใจ

### 1) 🛡️ ความปลอดภัยของการโพสต์ (ห้ามพลาด 3 ข้อ: ซ้ำ / ผิดบัญชี / โพสต์สด)
- ไล่ **ทุกเส้นทางที่ปุ่ม Post อาจถูกกด** (`clickPostButton`, fallback ข้อความปุ่ม, `dismissContinueToPostDialogIfPresent` ที่กด "Post now", reconcile) แล้วพิสูจน์ว่าโหมดแบบร่าง/dry-run/ทดสอบไม่มีทางถึง · หาเส้นทางที่ `publish_attempt` ถูกบันทึกโดยไม่มีการกดจริง และกดจริงโดยไม่มี `publish_attempt`
- กันโพสต์ซ้ำ: idempotency key, lease/revision fence, `pendingReceipt` หลัง restart, `park` vs `cancel`, การ re-prepare export เดิม, ผล `confirmation_unknown` ต้องไม่ถูก retry อัตโนมัติ, การ reset หน้าหลังกดแล้ว
- กันผิดบัญชี: `readStudioAccount` (หลายบัญชี/อ่านไม่ได้/เมนูโหลดช้า), cache บัญชี ≤15 นาที (v0.4.1) ว่ามีช่องให้สลับบัญชีกลางทางแล้วหลุดไหม, `studioIdentityAtClick`, `target_handle`/`strict_mode`/multi-channel
- ตัวกันเนื้อหา: ราคา/ส่วนลด (regex ครอบ THB/บาท/% off/ภาษาอื่นไหม, emoji ตัวเลข, "ราคาถูก" ล่ะ), placeholder `{…}`, caption/hashtag ยาวเกิน (4000), hashtag ติด popup autocomplete, @mention ที่ไม่ตั้งใจ, ข้อความไทย/อีโมจิที่ตัดกลางตัวอักษร, ซับจีนฝังในคลิป (กฎข้อ 12) — มีตัวกันฝั่ง extension/backend ไหม

### 2) ⚙️ ความทนทานของ MV3 worker และ chrome.debugger
- อายุ service worker (idle ~30s / งานยาว >5 นาที), การ keep-alive ใน `startKeepAlive`, ผลเมื่อ worker ถูก kill กลางขั้น (ทดสอบ `--kill-worker-at`), สถานะที่ต้องอยู่รอดใน `chrome.storage` vs ที่หายไป
- วงจร attach/detach ต่อขั้น: "already attached", DevTools เปิด, `canceled_by_user` (แถบ debugging), หลาย extension ใช้ debugger พร้อมกัน, detach ไม่ครบ → แท็บค้าง, เวลาว่างระหว่างขั้นที่ banner กระพริบ
- Chrome cache สคริปต์ worker, การ reload/ติดตั้งซ้ำ, `manifest` version bump, การตรวจเวอร์ชัน extension ↔ backend (`/capabilities`) ว่าเข้ากันก่อนรัน
- timeout ทุก `await` ที่คุยกับหน้า (CDP, fetch backend 30s, `waitFor…`) — มีจุดไหนที่รอไม่จำกัด? งบเวลาต่อคลิป?

### 3) 🧱 เสถียรภาพของ DOM/selector ของ TikTok Studio
- รายการ selector ทั้งหมด (data-e2e, class, ข้อความไทย/อังกฤษ) จัดกลุ่มตามความเปราะ · UI ภาษาไทย vs อังกฤษ · A/B test ของ Studio · เปลี่ยน class hash · ข้อความปุ่มเปลี่ยน
- กลไกตรวจจับ "หน้าเปลี่ยน" ก่อนล้มแบบเงียบ: ทุกขั้นต้องล้มพร้อมข้อความ + (ควร) เก็บ DOM snapshot/ภาพหน้าจอ (conductor มี `.tmp/autopost_dom`, extension มีไหม?)
- สัญญาณสำเร็จ 3 แบบ (toast / Content row / Drafts row) ทนต่อ list ล่าช้า, หน้า virtualized, ภาษาไทย, เวลา timezone, caption ซ้ำกันสองคลิป
- เสนอ **canary/health check** ที่รันก่อนทุกรอบ: ตรวจว่า selector สำคัญยังอยู่ (upload input, Edit cover, Save draft, Post, product modal) โดยไม่แตะข้อมูลจริง

### 4) 📤 อัปโหลด/ประมวลผลวิดีโอ
- ไฟล์ใหญ่ (70MB+), เน็ตช้า/หลุดกลางอัปโหลด, `DOM.setFileInputFiles` ล้มเงียบ, อัปโหลดค้าง %/ขึ้น error ของ TikTok (ความยาว/ขนาด/ความละเอียดไม่รองรับ), ไฟล์ซ้ำ, path ภาษาไทย/ยาว, ไฟล์ถูกย้าย/ลบระหว่างรอบ (SHA snapshot `video_sha256`)
- `waitForUploadComplete`/`waitForUploadStatusBadge` ใช้ข้อความ/เปอร์เซ็นต์ — ทนภาษาอื่นไหม, % ใน caption ถูกตัดออกจากการตรวจจริงไหม (เคยเป็นบั๊ก B3)

### 5) ✍️ Caption / ปก / สินค้า / ตั้งเวลา
- การพิมพ์ใน Draft.js (โฟกัส, IME, emoji, ขึ้นบรรทัดใหม่, autocomplete hashtag/mention) · การตรวจว่า TikTok รับข้อความครบ (เทียบ innerText) · ตำแหน่งแฮชแท็ก
- ปก: 3:4 vs 9:16, ไฟล์ปกหาย/ไม่ตรง export, `cover_sha256`, fallback ปกอัตโนมัติ (toggle ปิดคือค่าที่แนะนำ — ควรเป็นค่าเริ่มต้นไหม?), modal Edit cover ค้าง/Discard
- แนบสินค้า: modal ถูกตัดที่จอแคบ, สินค้าไม่พบ/หมด/ถูกลบ, ค้นหาเจอหลายตัว, เลือกผิดตัว (ตรวจ ID ตรงเป๊ะ?), ลิงก์ไม่ผูกร้านของบัญชี, สินค้าหลายร้าน
- ตั้งเวลา: time picker (5 นาที), วันที่ข้ามเดือน/ปี, timezone ของบัญชี vs เครื่อง, ช่วงต้อง ≥15 นาที (`scheduleWindowProblem`) ขณะที่รอบรันนานทำให้ slot เลยเวลาระหว่างทาง, ผลกับ DST

### 6) 🎛️ แผงข้าง (Side Panel) — UX ความเสถียร ความถูกต้องของสถานะ
- ปิด/เปิดแผงกลางรอบ, รีโหลดแผง, สลับแท็บ/หน้าต่าง, หลายแผงพร้อมกัน, กดเริ่มซ้ำ, กด pause/stop แล้วสถานะ worker/job เป็นอย่างไร (ค้าง claimed?) · การติ๊กเลือก (ไม่ถูกจำ, ถูกล้างหลังรีเฟรช) · "Cover Fallback" ค่าเริ่มต้น · ข้อความ error คัดลอกได้ · log หายเมื่อรีโหลด?
- ความถูกต้องของตัวเลขโควตา/ตัวจำกัด/ปุ่ม "เริ่ม (N จาก M)" ทุกคู่โหมด×จำนวน · สถานะการ์ด (`getExtensionStatus`) ตรงกับ backend · การ์ดที่ใช้ไม่ได้
- a11y (โฟกัสคีย์บอร์ด, ความเปรียบต่าง, ขนาดปุ่ม ≥44px), กฎ UI สะอาด (`ui_clean_standard.md`: ปุ่มขึ้นต้นกริยา ไม่มีสัญลักษณ์ซ้ำซ้อน), ธีมมืด/สว่าง, แผงแคบมาก
- ความซ้ำซ้อน/โค้ดตาย: `popup.html/js`, `content_script.js`, `batch_runner.js` (ซ้ำกับ orchestrator) — ยังถูกโหลด/ใช้หรือไม่, มี draft logic เก่าที่อันตรายหลงเหลือไหม

### 7) 🔁 Orchestrator / breaker / กู้คืน
- ทุกสถานะของ 10 ขั้นต่อคลิป × ล้ม/หยุด/พัก/ยกเลิก; retry ก่อนกดเท่านั้น (ห้ามหลังกด) — พิสูจน์ด้วยเทส · breaker (ล้ม 3, ไม่แน่ใจ 2) เหมาะสมไหม · `Resilient Auto-Skip` ซ่อนปัญหาเชิงระบบ (เช่น เข้าสู่ระบบหลุด) ให้ดูเป็น "ข้าม" ไหม
- jitter/พักระหว่างคลิป, โควตาแบบร่าง/ตั้งเวลาระหว่างรอบ (นับเพิ่มทีละคลิป, ตรวจซ้ำกลางรอบทุก N คลิปไหม), คลิปที่ slot ผ่านไประหว่างรอบ
- กู้คืนหลัง Chrome/เครื่องรีสตาร์ท: `pendingReceipt`, job ค้าง `claimed/publishing`, ปุ่ม/ขั้นตอนให้ผู้ใช้ไล่ผลเดิม (`reconcile`) และทางเคลียร์ job ค้างที่ปลอดภัย (ตอนนี้ต้องใช้สคริปต์ Python) → ควรมีปุ่มใน UI ไหม

### 8) 🌐 Backend & โปรโตคอล (`posting_jobs.py`, `api_tiktok_autopost.py`, `api_schedule_queue.py`)
- ทุก endpoint × auth/channel scope/ข้อมูลผิดรูป/ซ้ำ/race (สอง extension) · ตรวจ `ChannelError` ทุกทาง · ค่าสถานะที่หลุดมือ (เช่น job `draft_saved` กับคิว `planned`) · ความสอดคล้อง job↔คิว↔export (transaction แยกกัน: ถ้าล้มครึ่งทางเกิดอะไร) · `release_draft`/PATCH reset
- ผลกระทบข้ามระบบ: PostLog, ExportRegistry (ย้ายไป Posted เฉพาะ `published`), publication_effects/observations/hyperframes_publication (รับ draft_saved ได้ถูกไหม), mobile posting (`api_mobile_posting.py`)
- 401/403/500/timeout ตอนกลางรอบ, backend รีสตาร์ท (ตอนนี้ต้องรีสตาร์ทเพื่อโหลดโค้ดใหม่: ผลกับ job ที่กำลังรัน)

### 9) 📊 โควตา & การนับ
- นับ schedule จากแถว Content (ป้ายเวลาอนาคต): ทนต่อ list lag, virtualization, แถว pinned, โพสต์ที่ตั้งเวลา "ในอดีตแต่ยังไม่เผยแพร่", timezone, ภาษาอื่น, ปีไม่แสดง, >400 แถว · นับแบบร่างจากแท็บ "Drafts N"
- เพดาน 30 ของ schedule: **หาหลักฐานจริงจาก TikTok** (ข้อความบนหน้า/เอกสาร/พฤติกรรมเมื่อเต็ม) แทนการสมมติ · จะรู้ได้อย่างไรเมื่อ TikTok ปฏิเสธเพราะเต็ม (ข้อความ error) และ extension ควรตอบสนองยังไง
- ตัวเลขที่แสดงใน 3 ที่ (แผงข้าง, orchestrator, conductor) ต้องมาจากแหล่งเดียวกันและไม่ขัดกัน

### 10) 🧪 ชุดทดสอบ & ช่องว่างการทดสอบ
- รัน/อ่านเทสทั้งหมด: ตรวจว่าเทสทดสอบ "พฤติกรรม" ไม่ใช่แค่ "ไม่ error" (fake ที่คืนค่า `true` ให้ทุก evaluate จะทำให้เทสผ่านโดยไม่ได้ทดสอบ — เคยเจอ) · จุดที่ไม่มีเทสเลย (โค้ด DOM ของ `sidepanel.js` ~3.4k บรรทัด) · e2e (`extension_e2e.js`) ที่ stub ขั้นกดโพสต์: ขาดอะไร
- เสนอเทส/e2e เพิ่ม: เน็ตหลุดกลางขั้น, worker ถูก kill ทุกขั้น, ปิดแผงกลางรอบ, caption มีอีโมจิ/ยาว, สินค้าหาย, โควตาเต็ม, สองคลิปมี caption เดียวกัน, ชนกับโพสต์เดิมใน Content, Chrome ภาษาไทย vs อังกฤษ, จอแคบ/zoom
- วินัยชุดทดสอบ (`testing_standard.md`): deterministic/offline, ห้ามแตะข้อมูลจริง, ล้างขยะ 100%

### 11) 🔭 Observability & การวินิจฉัย
- ข้อความ error ทุกจุดบอก **ขั้น + สาเหตุ + ขนาดจอ/โฟกัส/URL ปัจจุบัน** หรือไม่ · log ในแผงคัดลอกได้แต่หายเมื่อปิด → ควรมี **ประวัติการรัน** (ไฟล์/`chrome.storage`/endpoint backend) ที่ค้นย้อนหลังได้ · รหัสอ้างอิงต่อคลิป (job_id) ใน log ทุกบรรทัด · ภาพหน้าจอ/DOM ตอนล้ม (ไม่รั่วข้อมูลส่วนตัว)
- การแจ้งเตือนเมื่อต้องการคน: login หมดอายุ, captcha, บัญชีไม่ตรง, ไม่แน่ใจผลโพสต์ — ตอนนี้ conductor เขียน `.tmp/autopost_ALERT.txt`; extension ควรมี `chrome.notifications`/badge หรือไม่

### 12) 🔐 ความปลอดภัยของ extension เอง (supply-chain / ข้อมูล)
- permissions จำเป็นขั้นต่ำไหม (`debugger`, `scripting`, `windows`), host_permissions กว้างเกินไหม, `externally_connectable`/message listeners ที่เว็บอื่นเรียกได้ไหม, `content_script.js` รับข้อความจากหน้าเว็บไหม (page → extension injection), การ `eval`/สร้างโค้ดจากข้อความของสินค้า/caption (XSS ในแผงข้าง: `innerHTML` กับ `escapeHtml` ครบทุกจุดไหม)
- การเก็บ API key (`auth_key.js`, storage), การส่ง key ไป backend (header), key ในล็อก, CORS/localhost เท่านั้น, ใครก็ตามบนเครื่อง/เว็บอื่นเรียก `127.0.0.1:8000` ได้ไหม (CSRF/DNS rebinding)
- ข้อมูลที่ extension อ่านจากหน้า TikTok (บัญชี, รายการโพสต์) ถูกเก็บ/ส่งที่ไหนบ้าง

### 13) 🖥️ สภาพแวดล้อมจริงของผู้ใช้
- Chrome ส่วนตัวมี extension อื่น (Gemini, ตัวช่วยพิมพ์, ad-block) ชนกัน? · ภาษา UI TikTok ไทย · DPI/zoom/ไม่เต็มจอ/แผงข้างกว้าง ทำให้ viewport ~700px · คอมหลับ/ล็อกจอ/สลับผู้ใช้ Windows ระหว่างรอบ · แท็บ TikTok ถูกปิด/สลับ/มีหลายหน้าต่าง Chrome · profile ที่ login หลายบัญชี TikTok · เวลาเครื่องผิดเขตเวลา
- ขั้นตอนติดตั้ง/อัปเดต/ถอดสำหรับผู้ใช้ที่ไม่ใช่นักพัฒนา (reload extension, ใส่ API key, เลือกช่อง) ชัดเจนและมีการตรวจสุขภาพ (preflight) ที่บอกว่า "พร้อม/ไม่พร้อม เพราะอะไร" ก่อนกดเริ่ม

### 14) 🧰 คุณภาพโค้ด & ความยั่งยืน
- `background.js` ใหญ่ 5.6k บรรทัดและมีบรรทัดว่างซ้อนในหลายช่วง (การแก้ไขอัตโนมัติพลาดง่าย) → ข้อเสนอแบ่งโมดูลที่ **ไม่เปลี่ยนพฤติกรรม** (มีเทสกำกับ) · โค้ดตาย/ซ้ำ (`batch_runner.js`, `popup.*`) · ค่าคงที่กระจัดกระจาย (30, 15 นาที, timeout) รวมไว้ที่เดียว · เวอร์ชันที่ซ้ำกัน 4 ที่ (manifest, sidepanel.html, เทส) ให้มีแหล่งเดียว
- เอกสาร: README ของ extension (ติดตั้ง/ใช้/แก้ปัญหา), `ARCHITECTURE.md`, แผนภาพโฟลว์โพสต์ (สกิล `/flow-html` ถ้าเหมาะ)

---

## 🧩 ฟีเจอร์ที่ต้อง "ประเมิน" ว่าควรเพิ่มไหม (ให้เหตุผล ผลต่อความเสถียร ต้นทุน ความเสี่ยง) — อย่าทำเอง ก่อนอนุมัติ
1. **Preflight ก่อนกดเริ่ม**: เวอร์ชัน extension↔backend, API key, login, บัญชีตรงช่อง, ขนาดหน้าจอ, canary selector, โควตา (ปุ่มเดียวบอก "พร้อม/ไม่พร้อม")
2. **ประวัติการรันถาวร** + หน้าดูย้อนหลัง/ส่งออก (ใครรัน อะไรสำเร็จ/ล้ม/ไม่แน่ใจ)
3. **จำสถานะแผง**: การติ๊กเลือก, โหมด, ตัวจำกัด · **กู้รอบที่ค้าง** (Resume) หลังรีสตาร์ท พร้อมปุ่มไล่ผลเดิม (`reconcile`) และปุ่มเคลียร์ job ค้างที่ปลอดภัย
4. **แจ้งเตือนเมื่อต้องใช้คน** (badge/notification/เสียง) + **หยุดสะอาด** (stop แล้วปล่อย job, ไม่ทิ้งหน้าค้าง)
5. **เก็บหลักฐานตอนล้ม** (ภาพ/DOM ที่ลบข้อมูลส่วนตัว)
6. **Dry-run ในแผง** (กรอกทุกอย่างแต่ไม่กด) และ **ตัวอย่างก่อนโพสต์** (ดู caption/ปก/สินค้า/เวลา ที่จะส่งจริง) พร้อมขั้นยืนยันสำหรับรอบแรกของวัน
7. **ตัวกันเพิ่ม**: ราคาหลายรูปแบบ/ภาษา, caption ซ้ำกับคลิปที่โพสต์ไปแล้ว, hashtag เกินจำนวน/ต้องห้าม, คลิปความยาว/ขนาดไม่รองรับ, ซับต่างชาติฝัง, เวลา slot ชนกัน
8. **จัดตารางใหม่อัตโนมัติ** เมื่อ slot เลยเวลา / โควตาเต็ม (แนะนำ ไม่ทำเอง)
9. **ปุ่มจัดการแบบร่าง**: เผยแพร่จากแบบร่าง / ลบแบบร่างและรีเซ็ตคิวจากแผง / ล้างแบบร่างที่หมดอายุ
10. **ตั้งค่ากลาง**: เพดานโควตา, lead time, งบเวลา, jitter, จำนวนลองซ้ำ ปรับได้ใน Settings พร้อมค่าปลอดภัยเริ่มต้น
11. **จัดการหลายช่อง/หลายบัญชี** ให้ชัด (สลับช่อง, ป้ายบัญชีที่ผูก, กันสลับกลางรอบ)
12. **การอัปเดตตัวเอง/แจ้งเวอร์ชันเก่า** (เตือนเมื่อ worker เก่ากว่า backend)
13. **conductor ↔ extension**: ใช้ตัวกัน/โควตาชุดเดียวกัน, ตัวรันตามเวลา (Task Scheduler) — ตัดสินว่าจะให้ extension หรือ conductor เป็นเส้นทางหลักของงานไม่มีคนเฝ้า

---

## ✅ วิธีพิสูจน์ (ต้องใช้ ไม่ใช่แค่อ่านโค้ด)
- รันเทสทั้งหมด + บันทึกตัวเลขก่อน/หลัง · เทียบกับ HEAD
- หน้า TikTok จริง (เฉพาะที่อนุญาตตามกฎข้อ 1): ใช้ `tools/autopost_conductor/extension_e2e.js` (`--pick=N`, `--quota-probe`, `--draft-probe`, `--dropdown-probe`, `--smart-overflow`, `--narrow=W`, `--content-after-post`, `--kill-worker-at=S`) และ `run.js --health | --dry-run | --mode draft`
- ฉีดความผิดพลาดจริง: `--net slow|blip|offline`, `--viewport`, kill worker/Chrome/backend, ปิดแท็บ, เปลี่ยนบัญชี, ใส่ caption อันตราย (ราคา, `{x}`, ยาวมาก, อีโมจิ) — ดูว่าระบบหยุด/กู้ตามที่ควร
- หลังทุกการทดสอบ: ตรวจและรายงาน (ก) Drafts บน TikTok (ข) job ค้าง `claimed/publishing` (ค) สถานะคิว (ง) ไฟล์ใน `04_Exports/` และ `_Docs/export_registry.json`

---

## 📑 รูปแบบรายงาน (เขียนลง `_Docs/Reports/AUTOPOST_EXTENSION_AUDIT_<วันที่>.md` ห้ามวางเกลื่อนที่ราก)
1. **สรุปผู้บริหาร** (≤15 บรรทัด): พร้อมใช้ไหม, ความเสี่ยงสูงสุด 5 ข้อ, สิ่งที่ผู้ใช้ต้องตัดสินใจ
2. **ตารางข้อค้นพบ** เรียงตามความรุนแรง: `รหัส | สถานี | ความรุนแรง (S0 โพสต์ผิด/ซ้ำ/สด/รั่ว · S1 รอบพังกลางคัน/ข้อมูลผิด · S2 ใช้ยาก/ล้มเป็นบางครั้ง · S3 เก็บกวาด) | อาการ | หลักฐาน (ไฟล์:บรรทัด / ผลรัน / ภาพ) | ระดับยืนยัน (หน้าจริง/เทสจำลอง/อ่านโค้ด) | ผลกระทบ | วิธีแก้เสนอ | ขนาดงาน (S/M/L) | ความเสี่ยงของการแก้`
3. **สิ่งที่ตรวจแล้วดี** (สั้น) เพื่อกันตรวจซ้ำ
4. **ฟีเจอร์เสนอเพิ่ม** (จากหัวข้อประเมิน) พร้อมคำแนะนำ ทำ/ไม่ทำ/ภายหลัง และเหตุผล
5. **แผนแก้เรียงลำดับ** แบ่งรอบละ ≤1 วัน, ทุกรอบมี: ไฟล์ที่แตะ, เทสที่เพิ่ม, วิธีพิสูจน์, ความเสี่ยง/การย้อนกลับ, ต้องยกเวอร์ชัน extension หรือรีสตาร์ท backend หรือไม่
6. **สิ่งที่ยังตรวจไม่ได้และต้องการจากผู้ใช้** (เช่น ขออนุญาตโพสต์ทดสอบจริง 1 คลิป, ขอ log จาก Chrome ส่วนตัว, ขอยืนยันเพดานโควตา)
7. **สถานะหลังทดสอบ**: ตารางก่อน/หลังของ Drafts, job ค้าง, คิว (ต้องกลับเท่าเดิม)

จบเฟส A ด้วยข้อความ: "ตรวจเสร็จ — รออนุมัติแผนแก้" แล้วหยุด **ห้ามเริ่มแก้เอง**

---

## 🛠️ เฟส B (หลังผู้ใช้พิมพ์ "อนุมัติ" เท่านั้น)
- ทำทีละรอบตามแผน: เขียนเทสที่ล้มก่อน (tdd) → แก้ → เทสผ่าน → ทดสอบจริงตามกฎข้อ 1 → ยกเวอร์ชัน → ล้างขยะ → อัปเดต `TODO.md`/`ARCHITECTURE.md`/README → commit แยกเฉพาะไฟล์ของคุณ
- ทุกรอบรายงานตัวเลขเทสก่อน/หลัง และระดับการยืนยัน 3 ระดับ (กฎข้อ 7) · ปิดรอบ: ย้ายบล็อกไป `HISTORY.md` เหลือชื่อรอบบรรทัดเดียวใน `TODO.md`
- เจอของที่นอกแผนหรือเสี่ยง S0 ระหว่างทาง: หยุด รายงาน รอคำตัดสิน
```
