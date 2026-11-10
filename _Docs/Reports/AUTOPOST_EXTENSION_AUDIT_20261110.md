# รายงานตรวจ extension โพสต์อัตโนมัติ (เฟส A: ตรวจอย่างเดียว) — 2026-11-10

ผู้ตรวจ: Claude Code (Claude Sonnet 5.5) + agent ย่อยอ่านโค้ด 3 สาย (worker / แผงข้าง+orchestrator / backend+conductor) · ฐานตรวจ: extension v0.4.1, commit `e0a23d5` · พรอมต์: `_Docs/Plans/MASTER_AUTOPOST_EXTENSION_AUDIT_PROMPT.md`
**ยังไม่ได้แก้โค้ดใดๆ ในเฟสนี้** (ไม่มีการแก้ไฟล์ซอร์ส มีเพียงสคริปต์ probe ชั่วคราวใน `.tmp/` ซึ่งถูก gitignore) รอผู้ใช้พิมพ์ "อนุมัติ" ก่อนเริ่มเฟส B

## ระดับการยืนยัน (อ่านตารางตามนี้)
- **V** = ผมยืนยันเองในรอบนี้ (รันสคริปต์/ตรวจหน้า TikTok จริง/อ่านโค้ดจุดนั้นโดยตรง)
- **R** = agent ย่อยรันสคริปต์ทดสอบจริง (temp dir / Node ล้วน ไม่แตะข้อมูลจริง) ผมยังไม่ตรวจซ้ำ
- **T** = agent ไล่เส้นทางโค้ดอย่างเดียว ผมยังไม่ตรวจซ้ำ (อาจผิดได้ ควรยืนยันก่อนแก้)
ไม่มีข้อใดที่ยืนยัน "บนการโพสต์จริง" เพราะห้ามโพสต์จริงตามกฎของพรอมต์

## 1) สรุปผู้บริหาร
**ยังไม่ควรปล่อยให้รันไม่มีคนเฝ้า 30 คลิปด้วยปุ่มเดียว** ส่วนที่ทดสอบจริงแล้ว (ตั้งเวลา, แบบร่าง, ปก, โควตา) ทำงานได้ แต่พบช่องทางที่ทำให้ "โพสต์สดโดยไม่ตั้งใจ / ผลสำเร็จเท็จ / โพสต์ซ้ำ" ได้ 7 ข้อ (S0) ที่ต้องปิดก่อน ความเสี่ยงสูงสุด 5 ข้อ:
1. **คลิปที่ไม่มีเวลานัดถูกโพสต์สด** ในโหมด Schedule Only/Smart (V) ในแผงมีคลิป "ไม่มีเวลา" 36 คลิปที่ติ๊กหรือรัน "ทั้งหมด" ได้ ตัวกันไม่ขวาง worker ข้ามขั้นตั้งเวลาเงียบๆ แล้วกดโพสต์
2. **force release ยกเลิกงานที่กดไปแล้ว** ทำให้ export เตรียมใหม่ได้ = โพสต์ซ้ำ (V โค้ด + R รันจริงใน temp)
3. **reconcile สร้างข้อความ "โพสต์สำเร็จ" เอง** และรับหลักฐานแค่ URL มี `/content` (V) คลิปที่ไม่ได้โพสต์อาจถูกบันทึกว่าโพสต์แล้วและย้ายไฟล์ไป Posted
4. **ตัวกันราคา/placeholder อ่อนและอยู่แต่ในแผงข้าง** (V) regex พลาดวลีทั่วไป (ลดเหลือ, ฟรี, 199.-, `{ชื่อสินค้า}`) ส่วน worker และ backend ไม่มีตัวกันเลย
5. **ตัวตรวจบัญชีตอนกด "ไม่ทำงานจริง"** (V) selector อ่านบัญชีหลักหายไปจากหน้า TikTok หมด ตัวกันตอนกดผ่านเสมอเมื่ออ่านไม่เจอ ที่เหลือคือการอ่านสดก่อนกดไม่กี่วินาที (ยังกันได้ แต่บางกว่าที่เอกสารบอก)

สิ่งที่ผู้ใช้ต้องตัดสินใจ: ดูหัวข้อ 6

## 2) ตารางข้อค้นพบ (เรียงตามความรุนแรง; รหัสใหม่ F-xx รวมข้อซ้ำของ agent ไว้ในช่อง "อ้างอิง")
ความรุนแรง: S0 โพสต์ผิด/ซ้ำ/สด/ผลเท็จ/รั่ว · S1 รอบพังกลางคัน/ข้อมูลไม่ตรง · S2 ล้มเป็นบางครั้ง/ใช้ยาก · S3 เก็บกวาด

### S0
| รหัส | ข้อค้นพบ | หลักฐาน | ยืนยัน | อ้างอิง | วิธีแก้เสนอ |
|---|---|---|---|---|---|
| F-01 | **คลิปไม่มีเวลานัดถูกโพสต์สด** ในโหมดตั้งเวลา: worker ข้ามขั้น schedule เมื่อ job ไม่มี `schedule_date/time` แล้ว `click-post-only` กด Post; `/prepare` รับ schedule ว่างได้ (`Optional`); ตัวกัน `clipSkipReason` คืน `""` สำหรับคลิปไม่มีเวลา; ไม่มีการอ่านย้อนว่าหน้าอยู่โหมด Schedule ก่อนกด | `background.js:5148` (`if (job.schedule_date && job.schedule_time)` ไม่มี else) · `api_tiktok_autopost.py:192` · รันตัวกัน: คืน `""` | **V** | P-01, W-04 | (ก) แผงข้ามคลิปไม่มีเวลาเมื่อเป้าหมายเป็นตั้งเวลา (ข) worker ปฏิเสธ `click-post-only` เมื่อ job ไม่มีเวลา เว้นแต่ job ระบุ `intent` ชัด (ค) ก่อนกดอ่านย้อนว่าเลือก Schedule และวันเวลาตรง job (ง) `intent` ต้องผูกกับ `/attempt` |
| F-02 | **ติ๊กเลือกแล้วทุกคลิปถูกกัน → ระบบรันทั้งคิวแทน**: `selectedClipsInList()` กรองคลิปที่ถูกกันออก ทำให้ `usingPicked=false` แล้วใช้ `allClips` ทั้งหมด (ส่งผลร่วมกับ F-01) | `sidepanel.js:2882-2897`, `757-759` | **T** | P-02 | คำนวณเซ็ตที่ติ๊กดิบก่อน ถ้าไม่ว่างแต่ใช้ได้ศูนย์ ให้หยุดพร้อมข้อความ |
| F-03 | **force release ยกเลิก job ที่กดโพสต์/ตั้งเวลา/แบบร่างแล้ว** → เตรียม export เดิมซ้ำได้ → โพสต์ซ้ำ ปุ่มในแผงมีแค่ `confirm()` ที่ไม่เตือน | `posting_jobs.py:263-274` · `sidepanel.js:311-317` · agent รัน: force→cancelled แล้ว re-prepare→prepared | **V** (โค้ด) + **R** | W-09, B-01 | ตัด `force` สำหรับ job ที่มี `publish_attempted_at`/สถานะสุดท้าย ใช้ทางเฉพาะ (`release_draft` หรือ reconcile โดยมีหลักฐาน/ผู้ปฏิบัติการ) + เทส |
| F-04 | **reconcile สร้างหลักฐานเท็จ**: จับคู่แถวจากโทเค็นชื่อสินค้า/prefix caption และเงื่อนไข "ใหม่" ที่ผ่านทุกแถวที่มีเลข "0" แล้วส่ง `platform_success_notice` ด้วยข้อความค่าตายตัว "Post published successfully" พร้อม token จริง · แถวเก่าของสินค้าเดียวกันทำให้คลิปที่ไม่ได้โพสต์ถูกบันทึกว่าโพสต์แล้ว · reconcile ไม่รู้ intent (draft/schedule) → บันทึกเป็น `published` เสมอ | `background.js:975-998,1050-1068` | **V** | W-01, W-11 | ใช้ `rowMatchesClip` + วันเวลา/อ่าน badge ตรง ห้ามสร้าง `platform_success_notice` เอง ให้ผลเป็น `confirmation_unknown` ถ้าไม่มั่นใจ รับ intent จาก job |
| F-05 | **หลักฐาน URL อย่างเดียวรับเป็นสำเร็จ**: ถ้าไม่เห็น toast แต่ URL มี `/content` (รวม `?tab=draft`) worker คืน `published` ด้วย `content_page_reconciled`; backend รับ kind นี้โดยไม่ตรวจข้อความ/ผู้ปฏิบัติการ และข้ามการผูก token; `manual_user_confirmation`/`user_confirmed` รับโดยไม่ต้องระบุตัวผู้ยืนยัน | `background.js:4343-4365` · `posting_jobs.py:176-187` · agent รัน: published ด้วย `{kind}` อย่างเดียวผ่าน | **V** (โค้ด) + **R** | W-05, B-03 | URL → `confirmation_unknown` เท่านั้น ยกเว้น `tab=draft`; kind reconcile ต้องมี `platform_post_id`/notice; manual ต้องมี operator id |
| F-06 | **ตัวกันราคา/placeholder อ่อนและอยู่แต่ในแผง**: regex ไม่จับ ลดเหลือ 99 / แค่ 199.- / เพียง 99 บ. / ลด 50 เปอร์เซ็นต์ / ฟรี* / โปร* / half price / `{ชื่อสินค้า}` / `{ product_name }` / `{product-name}` · worker พิมพ์ `job.caption` โดยไม่ตรวจ · backend ไม่มีตัวกันเลย (grep ไม่พบ) · ไม่มีตัวกัน caption >4000 · agent รัน 47/70 วลีหลุด | `post_guard.js:10-12` · `background.js` ไม่มีการเรียก `clipSkipReason` · grep backend | **V** (รันเอง + grep) + **R** | W-12, P-12/13/14 | ย้ายตัวกันเป็นโมดูลกลางเรียกซ้ำใน worker (ก่อนพิมพ์/ก่อน attempt) และ backend `/prepare` · normalize ข้อความ (NFKC, ลบ zero-width, เลขไทย) · ตัดสินใจเรื่อง "ฟรี/โปร/ถูก" ร่วมกับเจ้าของช่อง · ตรวจความยาว/จำนวน hashtag |
| F-07 | **ปุ่ม Post มีทางสำรองกด "Save draft" ได้**: ถ้า `post_video_button` หาย/ถูก disable แต่ Save draft กดได้ โค้ดเลือกปุ่มสุดท้ายที่ตรง · และ "Post now"/"Schedule now" ถูกกดในโมดัลใดก็ได้โดยไม่ดู intent ของงาน (เงื่อนไข `isContinueDialog` ไม่บังคับ) | `background.js:4259-4281` (validButtons) · `dismissContinueToPostDialogIfPresent` (3387+) | **V** | W-02, W-03 | ตัดข้อความ draft ออกจาก fallback ของ Post · ส่ง intent ให้ dismisser รับเฉพาะปุ่มที่ตรง บังคับ `isContinueDialog` |
| F-08 | **เส้นทางมือถือข้ามกติกาสถานะ**: `/handoff` รับแถวสถานะ scheduled/draft/unknown ได้ และ `/confirm` ทำให้ job สถานะใดก็ได้เป็น published/scheduled โดยไม่ผ่าน `acknowledge` และกลืน exception | `api_mobile_posting.py:603-624, 663-708` | **T** (อ่านเงื่อนไข `status == posted` แล้วตรงกับที่รายงาน) | B-02 | ใช้การ์ดสถานะเดียวกับ PATCH, ผ่าน `acknowledge`, ไม่กลืน exception |

### S1
| รหัส | ข้อค้นพบ | หลักฐาน | ยืนยัน | อ้างอิง | วิธีแก้เสนอ |
|---|---|---|---|---|---|
| F-09 | **ตรวจตัวตนตอนกดเป็น no-op ในหน้าปัจจุบัน**: selector อ่านบัญชีหลัก 5 ตัว + `a[href*="/@"]` + rehydration JSON มี 0 บนหน้าอัปโหลดจริง ทางเดียวที่ได้บัญชีคือกดรูปโปรไฟล์แล้วอ่านลิงก์ "Profile" (`@rizanntry` ใน ~150ms) · `studioIdentityAtClick` ไม่เปิดเมนู จึงไม่เห็น handle และใช้ `current = clean[0] \|\| target` ผ่านเสมอ · ชั้นกันที่เหลือคือการอ่านสดใน `/attempt` ก่อนกดไม่กี่วินาที | probe หน้าจริง (`acct.js`) · `background.js:4151` | **V** (หน้าจริง + โค้ด) | W-13 | เมื่อไม่เห็น handle ให้ throw หรืออ่านผ่านเมนูในขั้นกดเดียวกัน · เพิ่ม canary ของ selector บัญชี |
| F-10 | **สิทธิ์กดครั้งเดียวถูกใช้ทิ้งโดยไม่ได้กด**: `waitForUploadComplete` ผ่านเมื่อไม่มีปุ่ม Post เลย แล้ว `/attempt` ถูกบันทึกก่อน evaluate หาปุ่ม → throw → `confirmation_unknown` โดยไม่เคยกด (ทางแบบร่างแก้แล้ว ทางโพสต์ยังไม่แก้) | `background.js` `waitForUploadComplete` ส่วนปุ่ม submit · `runClickPostOnly` | **V** (โค้ด) | W-07 | ตรวจว่ามีปุ่ม Post ที่กดได้ก่อน `beginPublish` |
| F-11 | **ข้อผิดพลาดหลังกด นับเป็น "ล้ม" ไม่ใช่ "ไม่แน่ใจ" และไม่ reconcile**; TRIGGER_SUBMIT อยู่ใน `runWithRetry` ที่ retry เมื่อ "message port closed" (worker กันกดซ้ำได้ แต่ผลถูกบันทึกเป็น failed); กด Stop/Abort หลังกดแล้วข้าม verify/update backend → โพสต์สดแต่ไม่ถูกนับ | agent รัน: `submits=2 ok=1` / `failed=1 unknown=0 reconcile=0` / `ABORTED reconcile=0` | **R** | P-04, P-05, P-06 | ไม่ retry TRIGGER_SUBMIT; error ใน post-submit stage → `unknown` + reconcile; Stop/Pause ทำที่ขอบคลิปหลังจบ verify/update |
| F-12 | **Start ซ้ำ/หลายแผงเริ่มสองรอบได้**: `busy` ตั้งหลัง `await askConfirm()`/`openTikTokUploadTab()`; ปุ่ม OK ผูก listener ซ้อน; รอบที่สอง `park` job ของรอบแรก · ไม่มีล็อกรอบ · ปิด/รีโหลดแผงฆ่ารอบกลางคัน (ลูปอยู่ในหน่วยความจำของแผง) | `sidepanel.js:2875-2937,1113-1143` · grep ไม่พบ `beforeunload`/run lock | **T** | P-03, P-09 | flag `starting` แบบ synchronous, ล็อกรอบ + heartbeat ใน `chrome.storage.session`, เตือนเมื่อปิดแผง, กู้ job กำพร้าตอนเปิดแผง |
| F-13 | **backend รับ `published` ให้งานที่มีเวลานัดด้วย toast เปล่า "Video published"** (ตรวจแค่ทิศกลับ) → คลิปตั้งเวลาถูกบันทึกว่าโพสต์แล้วและย้ายไป Posted (extension แปลงเป็น scheduled ฝั่งตัวเอง แต่ backend ไม่กัน) | `posting_jobs.py:199-209` · agent รัน: scheduled job → published | **R** | B-04 | ปฏิเสธ `published` เมื่อ job มี schedule เว้นแต่หลักฐานมาจากการอ่าน Content ว่า "เผยแพร่แล้ว" |
| F-14 | **API ของ backend เปิดให้ DNS rebinding**: โหมดโลคัลไม่ตรวจ Host/Origin บน HTTP; ทดสอบ `Host: evil.example` ได้ 200 และ `auth_required:false` → เว็บใดๆ ที่ผู้ใช้เปิดอาจเรียก POST/PATCH/DELETE ได้ผ่าน rebinding (CORS preflight จาก origin แปลกถูก 400 อยู่แล้ว) | `curl` เอง: Host แปลก → 200 · `/api/health` `auth_required:false` · `api_auth.py:186-206` | **V** (พฤติกรรม) | B-07 | middleware allowlist Host (127.0.0.1/localhost) + บังคับ API key |
| F-15 | **ความสอดคล้อง job↔queue↔export**: ไม่มีที่เขียนสถานะคิว `confirmation_unknown` (แถวค้าง ready_for_extension ทั้งที่ job สุดท้ายแล้ว → รอบถัดไปหยิบซ้ำ ล้ม 2 ครั้ง breaker ทำงาน); PATCH planned/DELETE แถวที่ job ยังไม่จบได้ แล้ว effects คืน 404 ซ้ำจน receipt ค้าง; `/clear` กับ `/release` ทิ้งแถวคิวชี้ job ที่ตายแล้ว → prepare ใหม่ 409 | `api_tiktok_autopost.py:560-608` · `api_schedule_queue.py:1324,1349` · `conductor.js:124-135` | **R/T** | B-05, B-06, B-10, B-11 | สะท้อน unknown ลงคิว, บล็อก PATCH/DELETE เมื่อมี job ไม่สิ้นสุด, effects ไม่ถือว่าแถวหายเป็นความผิดร้ายแรง, รีเซ็ตแถวใน `/clear` |
| F-16 | **ลำดับงานผิดก่อนรั้วกัน**: `clickPostButton` เขียน token ใหม่/ตัด observer ก่อน `/attempt` → กดซ้ำบน job ที่ attempt แล้วทำลาย token เดิม ทำให้ reconcile ไม่ผ่าน · wrapper `findUploadTab()` กู้แท็บ Content→Upload ก่อน `click-post-only`/`save-draft-only` ทำลายหน้าที่ใช้เป็นหลักฐาน · job refresh ที่ล้มเหลวถูกกลืน แล้ว park อาจ force-release job ที่ attempt แล้ว | `background.js:4213-4225, 5571, 583/615` | **T** | W-06, W-08, W-10 | สร้าง token หลัง `/attempt`; ข้ามการกู้แท็บเมื่อ job attempt แล้ว; ถ้า GET ล้มให้ถือว่า attempt แล้วและไม่ release |
| F-17 | **quota/อื่นๆ ที่ทำลายงานระหว่างทาง**: นับโควตาแบบ `allowNavigate` พาแท็บอัปโหลดไป Content ทิ้งงานที่กรอกค้าง · คลิกพิกัดเก่าในขั้นบันทึกปก (automation.js:406-413) · `readStudioAccountOnce` เปิดเมนูแล้วไม่ปิด | `background.js:5462-5478` · `automation.js:406-413` | **T** | W-15, W-19, W-21 | ปฏิเสธเมื่อมี `activeJob`; ตรวจโมดัลก่อนคลิปพิกัด; ปิดเมนูหลังอ่าน |
| F-18 | **ชุดสถานะ/ผลสรุปไม่ซื่อสัตย์**: สถานะสุดท้ายไม่ดู unknown/ERROR/ABORTED (ขึ้นสีเขียว "เสร็จสิ้น"); ความล้มเหลวของ reconcile/reset/checkQuota ถูกกลืนเงียบ; stage 4-6 เป็น no-op แต่ log ว่าทำ; action ที่หายถูกนับสำเร็จ | `sidepanel.js:3304-3308, 3123-3169` · `batch_orchestrator.js:364-367` | **T** | P-07, P-08, P-20 | ใช้ `summary.state`/unknown/`circuitReason`, log ทุกความล้มเหลว, บังคับ action ที่จำเป็นตอนเริ่ม, ตัด/เปลี่ยนชื่อขั้น no-op |
| F-19 | **conductor**: หลัง timeout ต่อคลิป `runClip` ไม่ถูกยกเลิก ขั้นที่ค้างยังส่ง `click-post-only` ไปที่ worker ตัวใหม่ (agent รัน) · API fetch ไม่มี timeout · ไม่มี lock กันรันซ้อน (เสี่ยงชนแท็บเดียวกันพอร์ต 9333) · `process.exit(3)` ใน try ข้าม finally | `conductor.js:254-268` · `api.js:18` · `run.js:135-205` | **R** (8) / **T** | B-08, B-09 | token รุ่นต่อคลิปตรวจก่อนส่งทุกครั้งโดยเฉพาะก่อน click-post; `AbortSignal.timeout`; lock ไฟล์; ยกระดับ SIGINT ครั้งที่สอง |
| F-20 | **แผงเก่ายังโหลดอยู่**: `batch_runner.js` โหลดก่อน orchestrator และเป็น fallback เงียบถ้า orchestrator โหลดไม่ขึ้น (ไม่มี breaker/unknown/draft quota); ปุ่ม "เตรียมคลิปนี้" แบบแมนนวลไม่มีตัวกันเลย | `sidepanel.js:3173-3177` · `sidepanel.html:4911` · `sidepanel.js:1605-1700` | **T** | P-10, P-11 | ลบ `batch_runner.js`+เทส+script tag และทำให้ orchestrator หายเป็น hard stop; เรียก `clipSkipReason` ใน `prepareClip` |

### S2 / S3 (สรุปรวม — รายละเอียดอยู่ในรายงาน agent ที่แนบท้ายหัวข้อ 8)
- **S2**: ไม่มี timeout ที่ `chrome.debugger.sendCommand`/`tabs.*` และ worker หลับระหว่างขั้นเดี่ยวไม่มี keepalive (W-14) · attach ซ้ำคืน error ดิบ (W-14) · reconcile ตัด session ของขั้นอื่นด้วย `detach` (W-16) · แผงเขียนทั้งก้อน state ลง storage จากสำเนาเก่า (W-17) · ขั้นแต่ละขั้นไม่พก job id (W-18) · ไม่เช็ก slot ซ้ำตอนถึงคิวคลิป (P-16) · โควตาเก่า/ล้มเหลวถูกใช้ต่อ (P-17) · แบบร่างไม่เคยถูกตรวจซ้ำในแผง (P-18 — มี action แต่แผงไม่เรียก) · Pause/Stop ขัดจังหวะขั้นที่กำลังทำไม่ได้ และ `panelWorkerRequest` ไม่มี timeout (P-19) · `loadExports` เรียก detect-quota เงียบชน mutex ของ worker (P-22) · `rowMatchesClip` ตรวจวันที่ด้วยตัวเลขเปล่าตรงกับยอดวิวได้ (P-15) · `prepare` ไม่ตรวจเวลากับแถวคิว (B-13) · PATCH posted / mark-posted ไม่ต้องมีหลักฐาน (B-14) · `_Docs/posting_jobs.json` ถูก import กลับทับ SQLite (B-12) · ตัวกัน/ไม่มีตัวกันความยาว caption (P-14)
- **S3**: breaker ล้าง counter ซึ่งกัน/กัน (P-23) · start() ซ้ำตอน PAUSED (P-24) · `content_script.js` และ `popup.*` เป็นโค้ดตาย/กำพร้า (P-25, P-26) · ป้ายสถานะเก่า, เวอร์ชันฮาร์ดโค้ด, ค่าคงที่ซ้ำ 4 ที่ (P-27) · API key ใน URL สื่อ (P-28) · a11y/คอนทราสต์/ไอคอนในปุ่มขัด `ui_clean_standard` (P-29) · ไม่มีเทสแผงข้าง (P-30) · README คลาดเคลื่อน (B-16) · ข้อความ error ไม่บอกขั้น/สาเหตุ (W-20) · `/clear`/`/cover` ไม่มีรั้ง, ไม่มี body limit (B-17) · notice regex เข้มเกินสำหรับถ้อยคำจริงบางแบบ (B-15)

## 3) สิ่งที่ตรวจแล้วดี (ไม่ต้องตรวจซ้ำ)
- **รั้งกันกดซ้ำฝั่ง job**: `/attempt` ระดับ atomic ใน SQLite (8 โปรเซสแย่ง job เดียว ชนะ 1 · re-prepare ของ export ที่ attempt แล้วถูกปฏิเสธ) — agent รัน
- **worker กันกดซ้ำ**: `guardPostingAction` ปฏิเสธเมื่อมี `pendingReceipt`/`publish_attempted_at`, บันทึกก่อนกด, mutex `actionRunning` กันหลายแผงพร้อมกัน, ไม่มีลูป retry รอบปุ่ม Post (อ่านโค้ด)
- **โหมดแบบร่าง**: ใช้ `save-draft-only` และ `data-e2e="save_draft_button"` ตรงเท่านั้น ตรวจปุ่มก่อน fence ปฏิเสธ job ที่มีเวลานัด; backend `drafts_page_confirmed` ยืนยัน published/scheduled ไม่ได้ (agent รัน)
- **XSS ในแผง**: ทุก `innerHTML` ที่รับข้อมูลภายนอกผ่าน `escapeHtml`; ไม่พบ eval/`new Function`; `content_script.js` ไม่ถูกหน้าเว็บสั่งได้
- **ความลับ**: ไม่พบ key/token ใน log; API key อยู่ใน header `X-API-Key` เท่านั้น (นอกจาก URL สื่อ P-28)
- **CORS**: preflight จาก `https://evil.example` ถูก 400; การป้องกัน path traversal ด้วย `_resolve_under`
- **ผลจริงที่ทดสอบแล้วก่อนหน้า**: schedule, Save draft, ปก 3:4, นับโควตาจากแถว, กู้แท็บหลังโพสต์, Smart schedule→draft ติดกัน
- selector ฟอร์ม (post/save draft/discard/caption/cover/upload status) **ยังอยู่ครบ** บนหน้าจริง ณ วันนี้ (canary: `.tmp/coverprobe/canary.js`)

## 4) ฟีเจอร์ที่เสนอเพิ่ม (จัดตามผลต่อความเสถียร)
| ลำดับ | ฟีเจอร์ | แนะนำ | เหตุผล/ต้นทุน |
|---|---|---|---|
| 1 | **ตัวกันเนื้อหากลาง** (price/placeholder/ความยาว/hashtag) เรียกจาก panel+worker+backend+conductor | **ทำทันที** | ปิด F-06 ทุกเส้นทางเดียว ต้นทุนเล็ก ความเสี่ยงต่ำ |
| 2 | **Intent ต่อ job** (`schedule` / `draft` / `post_now`) ผูก `/attempt` + อ่านย้อนหน้าก่อนกด | **ทำทันที** | ปิด F-01/F-07 ชั้นเดียว ต้องแตะ backend + worker + แผง |
| 3 | **Preflight ปุ่มเดียว** (เวอร์ชัน extension↔backend, API key, login, บัญชีตรงช่อง, canary selector รวมบัญชี, ขนาดหน้า, โควตา) | ทำเร็ว | จับปัญหาก่อนเริ่มรอบ ลดล้มกลางทาง |
| 4 | **ประวัติการรันถาวร + หลักฐานตอนล้ม** (job_id ทุกบรรทัด, DOM/ภาพที่ลบข้อมูลส่วนตัว) | ทำเร็ว | ตอนนี้ log หายเมื่อปิดแผง วินิจฉัยยาก |
| 5 | **ล็อกรอบ + Resume + ปุ่มไล่ผลเดิม/เคลียร์ job ค้างที่ปลอดภัย** | ทำเร็ว | ตอนนี้ต้องใช้สคริปต์ Python เคลียร์ job (F-12/F-15) |
| 6 | **แจ้งเตือนเมื่อต้องใช้คน** (badge/notification) | ทำ | login หมด/captcha/บัญชีไม่ตรง/ไม่แน่ใจผลโพสต์ |
| 7 | ตั้งค่ากลางของค่าคงที่ (เพดาน, lead time, timeout, jitter) | ทำภายหลัง | ลดค่าซ้ำ 4 ที่ |
| 8 | ปุ่มจัดการแบบร่าง (เผยแพร่/ลบ+รีเซ็ตจากแผง) | ภายหลัง | สะดวก ไม่กระทบความปลอดภัย |
| 9 | จัดตารางใหม่อัตโนมัติเมื่อ slot เลย/โควตาเต็ม | ภายหลัง/แนะนำเท่านั้น | เสี่ยงเปลี่ยนเวลาโดยไม่ตั้งใจ |
| 10 | ตัดสินเส้นทางหลักของงานไม่มีคนเฝ้า: extension หรือ conductor | **ตัดสินใจก่อนลงทุนเพิ่ม** | ตอนนี้สองชุดมีตัวกัน/โควตาซ้ำและต่างกัน |
| — | อัปเดตตัวเอง/จัดการหลายช่องให้ชัด/Dry-run ในแผง | ประเมินหลัง R3 | ได้ประโยชน์ต่ำกว่าข้างบน |

## 5) แผนแก้ (เฟส B) — รอบละ ≤1 วัน เรียงตามความเสี่ยง
> ทุกรอบ: เขียนเทสที่ล้มก่อน → แก้ → เทสผ่าน → ทดสอบจริงตามกติกา (เฉพาะ Save draft/จำลอง/dry-run) → ยกเวอร์ชัน manifest → ล้างขยะ → อัปเดตเอกสาร → commit แยกไฟล์ของเรา

| รอบ | เนื้อหา | ไฟล์หลัก | เทสเพิ่ม | ต้องยกเวอร์ชัน/รีสตาร์ท |
|---|---|---|---|---|
| R1 หยุดโพสต์สด/ซ้ำ/เท็จ (F-01,02,03,04,05,07) | intent ต่อ job; ปฏิเสธโพสต์เมื่อไม่มีเวลา; ตัด `force` ของ job ที่ attempt; ตัดข้อความ draft จาก Post fallback; dismisser รับตาม intent; reconcile ไม่สร้าง notice, URL→unknown; เซ็ตติ๊กดิบ | `background.js`, `sidepanel.js`, `posting_jobs.py`, `api_tiktok_autopost.py` | unscheduled→refuse, force-release refused, fabricated-notice impossible, draft fallback, all-picks-blocked | extension + รีสตาร์ท backend |
| R2 ตัวกันเนื้อหา + ตัวตน (F-06,09,10,13,14,16) | โมดูลตัวกันกลาง (worker+backend+panel+conductor); normalize; Host allowlist+API key; ตัวตนตอนกด; ต้องมีปุ่ม Post ก่อน attempt; token หลัง attempt; `published` เมื่อมี schedule ต้องมีหลักฐาน | `post_guard.js`(+ฝั่ง Python), `background.js`, `api_server/api_auth` | ชุดวลีราคา 70+ ตัวอย่าง, placeholder, 4000 ตัวอักษร, Host แปลก, ไม่มีปุ่ม Post | extension + backend |
| R3 orchestrator/แผง (F-11,12,18,20) | post-submit error→unknown+reconcile; ไม่ retry TRIGGER_SUBMIT; Stop ที่ขอบคลิป; flag starting + run lock + beforeunload; สถานะสุดท้ายซื่อสัตย์; ลบ runner/popup/content_script เก่า; `prepareClip` มีตัวกัน; แผงเรียก verify-draft | `batch_orchestrator.js`, `sidepanel.js/html`, ลบไฟล์เก่า | abort after click, double start, port-closed no retry, final status, legacy removal | extension |
| R4 ความสอดคล้อง/กู้คืน (F-08,15,16,17,19) | mirror unknown ลงคิว; บล็อก PATCH/DELETE เมื่อ job ไม่จบ; effects ทนแถวหาย; `/clear`/`/release` รีเซ็ตแถว; mobile routes ใช้การ์ดเดียวกัน; conductor generation token/timeout/lock/startup reconcile | `api_*`, `posting_jobs.py`, `conductor.js`, `run.js`, `api.js` | ครอบคลุมช่อง B-02/05/06/08/10 | backend |
| R5 สังเกตการณ์ + ฟีเจอร์ (ข้อ 3-6 ของตารางฟีเจอร์) | preflight, ประวัติการรัน, หลักฐานตอนล้ม, แจ้งเตือน, ค่ากลาง, README, เทสแผงด้วยการแยกโมดูล | ใหม่ + แผง | เทสแผงข้างขั้นต้น | extension |

## 6) สิ่งที่ยังตรวจไม่ได้ / ต้องการจากผู้ใช้
1. **อนุญาตโพสต์ทดสอบจริง 1 คลิป** (บัญชีจริง) เพื่อพิสูจน์ F-01 แบบ end-to-end หลังแก้, modal "Post now", และพฤติกรรมเมื่อ TikTok ปฏิเสธเพราะเต็ม — ตอนนี้ยืนยันได้แค่จากโค้ด/จำลอง
2. **ตัดสินเรื่อง "ฟรี / โปร / ถูก / ส่งฟรี"** ว่าจะนับเป็นถ้อยคำราคาที่ห้ามหรือไม่ (มีผลกับ caption ที่มีอยู่ในคลัง)
3. **เส้นทางมือถือ (`api_mobile_posting`) ยังใช้อยู่ไหม** — ถ้าไม่ใช้ ปิดไปเลยง่ายกว่าแก้
4. **ตัดสินเส้นทางหลักของงานไม่มีคนเฝ้า** (extension หรือ conductor) ก่อนลงทุนเพิ่มสองชุด
5. ขอ log จาก Chrome ส่วนตัวของผู้ใช้ตอนเจออาการแปลก (ใช้ปุ่มคัดลอก log) เพราะผมทดสอบได้เฉพาะ Chrome ทดสอบพอร์ต 9333
6. **ยืนยันเพดาน schedule จริงของ TikTok** (โค้ดสมมติ 30; ยังไม่เคยเต็มจริง)
7. ยอมรับให้ผมรีสตาร์ท backend ตอน R1–R2 (ผลต่อ job ที่รันอยู่ ต้องไม่มีรอบวิ่ง)

## 7) สถานะหลังทดสอบ (ก่อน/หลัง)
| รายการ | ก่อนเฟส A | หลังเฟส A |
|---|---|---|
| คิว | โพสต์แล้ว 155 · schedule แล้ว 15 · planned 1 (LOOP) | **เท่าเดิม** |
| job ค้าง (claimed/publishing) | 0 | **0** |
| แบบร่างบน TikTok | 0 (เคลียร์หลังรอบก่อน) | **ไม่ได้อ่านซ้ำตอนจบ** (เฟส A ไม่ได้สร้างแบบร่าง; probe การอัปโหลดไม่บันทึกอะไร) |
| ไฟล์ใน `04_Exports/` | ไม่เปลี่ยน | ไม่เปลี่ยน (ไม่มีการสร้างไฟล์ทดสอบ) |
| ไฟล์ที่ผมสร้าง | — | `.tmp/coverprobe/{canary,acct}.js` (ชั่วคราว, gitignore) · รายงานนี้ |
| โค้ดซอร์ส | commit `e0a23d5` | **ไม่ถูกแก้** |

## 8) วิธีที่ใช้ และข้อจำกัดของรายงานนี้
- baseline: node 171 ข้อ + pytest 118 ข้อ ผ่านหมดที่ `e0a23d5`
- หน้า TikTok จริง (ไม่โพสต์/ไม่บันทึก): canary ตรวจ selector 18 ตัว; probe แหล่ง handle บัญชี 4 แหล่ง; ตรวจ Host header ของ backend (GET เท่านั้น)
- agent 3 สาย: อ่านโค้ด + รัน Node/pytest/Python ใน temp dir เท่านั้น ผมตรวจยืนยันซ้ำเฉพาะข้อ S0 สำคัญ (ตามคอลัมน์ "ยืนยัน") ส่วนที่เหลือเป็นผลของ agent: อาจผิด/ไม่ครบ
- **ไม่ได้เรียก Jev** ตามกฎข้อ 19 ในเฟสนี้ (ครั้งก่อนล่มด้วย JSON/ได้ confidence null; เลือกไม่หน่วงงาน) — ควรเรียกก่อนเริ่มเฟส B
- ไม่ได้ทดสอบ: ปิดแผงกลางรอบบนหน้าจริง, kill Chrome หลังกด, DPI/zoom >150%, 30 คลิปติดกัน/ข้ามคืน, MV3 worker หลับกลางรอบยาว, Chrome ส่วนตัวที่มี extension อื่น (ยกไปไว้ในข้อ 6)
- รายงานเต็มของ agent (ตารางละเอียด W-01..W-21, P-01..P-30, B-01..B-17 พร้อมบรรทัดอ้างอิง) อยู่ในประวัติ session นี้ ผมสรุปรวมไว้ที่นี่โดยใช้รหัสอ้างอิงเดิมในคอลัมน์ "อ้างอิง" ถ้าจะเก็บฉบับเต็มเป็นไฟล์ แจ้งได้

ตรวจเสร็จ — **รออนุมัติแผนแก้** (เฟส B ยังไม่เริ่ม)
