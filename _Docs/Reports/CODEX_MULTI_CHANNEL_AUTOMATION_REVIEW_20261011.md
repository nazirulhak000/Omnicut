# Multi-channel automation readiness — 2026-10-11
ดำเนินการโดย: Codex (GPT-6), delegated cutover_review

## ข้อสรุป
**ขอบเขตล่าสุด: ผู้ใช้เลือกกด extension ก่อน ยังไม่ทำ scheduler** จึงใช้ protocol/extension เดิมตรวจรับทีละงานจนถึงก่อนกด Post ได้ การไม่มี unattended dispatcher **ไม่ใช่ blocker ของ mode ที่เลือก**; งาน scheduler/orchestrator ด้านล่างเลื่อนไว้ภายหลัง สิ่งที่ยังบล็อกการรับรองใช้งานจริงคือ live account/selector evidence และ production migration preflight

ผู้ใช้ยืนยัน `main = @rizanntry`, ช่องที่สอง `@rizannntry`, legacy clips/campaigns ทั้งหมดเป็น main; existing ID ของช่องที่สองคือ `rizannntry` ห้ามสร้าง ID `second` ซ้ำ การเตรียมเปิดอัตโนมัติไม่ได้แปลว่าให้โพสต์ backlog ทั้งหมดทันที รายงานนี้อ่าน code/DB/JSON เท่านั้น ไม่หยุด service ไม่เปลี่ยน registry ไม่ apply migration และไม่โพสต์จริง

## Trace และสิ่งที่ต้องทำ
| เรื่อง | หลักฐานใน code | ผลต่อการเปิดใช้ |
|---|---|---|
| Registry พร้อมตาม metadata | `scripts/channel_store.py:598–640`: render readiness ตรวจ status/profile; posting readiness เพิ่ม verified binding/handle | ทั้งสองช่อง active, posting_enabled=true, binding status=verified ใน registry ณ inventory; ไม่ใช่หลักฐาน live session และไม่เริ่ม worker |
| UI enable switch | `frontend/src/components/SystemSettings.jsx:33–47`; `ExportGallery.jsx:536` อ่าน localStorage `omnicut_tiktok_autopost_enabled` | เป็น local browser switch สำหรับ UI ไม่ใช่ scheduler และไม่ครอบคลุม extension/production/render runtime |
| API startup | `scripts/api_server.py:87–130` recover เฉพาะ background isolation และ batch render | เปิด server อาจ resume rendering ที่ค้าง แต่ไม่ dispatch posting; อย่าใช้ startup เป็นการซ้อมที่ไร้ side effect |
| Schedule queue | `scripts/api_schedule_queue.py:1137`, `1152`, `1304` preview/commit auto-fill และ explicit POST `/{item_id}/prepare` | auto-fill จัดรายการในคิว; ไม่ใช่ due-time runner ที่ upload/publish เอง |
| Extension | `background.js:11–14`, `2115`; `sidepanel.js:740–761`, `818–819` | ทำเมื่อผู้ใช้กดปุ่ม; legacy `run-autopost` ถูกปฏิเสธ;ไม่มี alarms permission/automatic loop ใน manifest |
| Combined prepare | `background.js:2053–2090` | caption → product → optional schedule → cover แล้ว return; publish เป็น `runClickPostOnly` แยกที่ `1955` |
| Account และผลโพสต์ | `background.js:63–69`, `1713–1722`, `1747–1809`, `1955–2007` | ต้องอ่าน account ใหม่และ fence หลัง processing ก่อน click; unknown outcome เก็บ receipt และหยุด ไม่ retry publish อัตโนมัติ |
| Stats | `sidepanel.js:1116`, `1172`; `scripts/api_tiktok_stats.py:197–213` | sync ถูกเรียกจากปุ่ม; strict source account/binding ต้องตรงกัน; unknown compatibility ต้อง quarantine ไม่ถือว่า sync ตรงช่องแล้ว |

## Inventory คิวจริงแบบอ่านอย่างเดียว
อ่าน `_Docs/store.db` ด้วย SQLite `mode=ro`; จำนวนตรงกับ JSON mirrors ณ inspection

- Schedule **156** รายการ ทั้งหมด main: posted **111**, planned **43**, ready_for_extension **2**
- planned dates **2026-10-11 09:00 → 2026-10-21 21:30 +07**; ready dates **2026-10-10 21:30** และ **2026-10-11 21:30 +07** จึงมีอย่างน้อยหนึ่งรายการค้างข้ามวัน ไม่สรุปว่า planned วันนี้ยังไม่ overdue เพราะขึ้นกับเวลาเปิดจริง
- Posting jobs **4** ทั้งหมด main: cancelled **1**, prepared **2**, claimed **1**; active 3 ยังไม่มี `publish_attempted_at`, effects_applied=false; prepared หนึ่งงานไม่ผูก queue อีกสอง active งานผูก queue
- Inventory นี้ไม่ยืนยันว่าไฟล์/เวลาที่เตรียมไว้ยังใช้ได้ หรือ lease ที่ claim ไว้หมดอายุแล้ว ต้องตรวจ snapshot ใหม่ก่อน release/reclaim; อย่าทิ้งงานเดิมหรือสร้าง post ซ้ำจากการดู count อย่างเดียว

**ใน mode กด extension:** เลือกและตรวจ channel/job/export/เวลา ทีละรายการ; ห้ามปล่อย backlog ทั้งหมดจากคำยืนยันว่า legacy เป็น main และตรวจ prepared/claimed เดิมก่อน release/reclaim ส่วน dispatcher ในอนาคต default exclude legacy backlog และใช้ allowlist ที่ตรวจแล้ว ไม่ bootstrap โดยส่ง 156 รายการเข้า publish; posted/cancelled ไม่กลับเข้า runner, unknown/publishing ต้อง reconciliation

## Live verification ที่ยังขาด
ผู้ใช้เปิด Chrome แล้ว แต่ parent ตรวจ CUA ได้ `browsers=[]`, `apps=[]` และ `createBrowserTab("chrome", ...)` ตอบ `Browser not available: chrome` จึงยังเข้าถึง logged-in session ไม่ได้ นี่เป็นข้อจำกัดการเชื่อมต่อเครื่องมือ ไม่ใช่หลักฐานว่า Chrome ไม่ได้เปิดหรือบัญชีไม่ถูกต้อง

1. เชื่อม Chrome profiles ที่ login บัญชีทั้งสอง และ extension/API key แบบไม่เปิดเผย key; ตรวจ channel selector และ account DOM ให้ชัดว่าเป็น logged-in account ไม่ใช่ caption/profile link ของวิดีโอ
2. ตรวจ native file upload/processing, caption, product radio/Next/confirm, schedule date/time/timezone, cover save กับ DOM ปัจจุบันบน session จริง (`background.js:370`, `836`, `1014`, `1146`, `1713`, `1747`; `automation.js` cover/upload logic) ไม่ใช้คอมเมนต์ UNVERIFIED เป็นหลักฐานว่าทำงานจริง
3. ซ้อมถึงก่อน Post และทำ account mismatch negative check; actual publication ต้องใช้ export/เวลา/account ที่ตรวจรับแล้วโดยแยกรายการชัดเจน
4. Post outcome ต้องเป็น fresh positive signal ผูก confirmation token; blank toast/navigation/form disappearance ไม่พอ ACK; server downtime/restart ต้อง resend receipt เดิมโดยไม่ click ใหม่ (`api_tiktok_autopost.py:508–569`, `posting_jobs.py:155–219`)

## Minimum unattended design — deferred ไม่อยู่ในรอบนี้
ผู้ใช้เลือก button-per-job extension; รายการต่อไปนี้เป็นแนวทางอนาคต **ไม่ต้องทำเพื่อปิด mode ปัจจุบัน** และยังไม่ implement
- ใช้ queue+durable job protocol เดิม: per-channel enablement แยก **produce/render**, **dispatch upload**, **publish**, **stats**; initial modes disabled/dry-run พร้อม allowlist และ stop control
- Due dispatcher ใช้ timezone + schedule window; late/expired slots ไป review ไม่ burst catch-up; ตรวจ product/export/QC/cover/media digests/frozen identity ทุกครั้งก่อน prepare/claim
- Runner ผูก channel กับ profile/extension instance และหนึ่ง active job ต่อ instance; persist step checkpoint และ lease heartbeat; resume เฉพาะก่อน publish ที่ปลอดภัย คง expected revision/payload hash/lease/account fencing เดิม
- Account อ่านใหม่ก่อนทุกผลกระทบและทันทีหน้า click; expired leaseหรือ handle/profile mismatch หยุด; publish attempt persist ก่อน click; confirmation_unknown เป็น terminal automation จน reconcile ห้ามนำกลับเข้า retry queue
- Dry-run/clock tests ก่อนจริง: due/late/future, empty queue, two profiles, duplicate runner, session logout, worker restart, storage/backend outage, click สำเร็จแต่ ACK ล้ม, source account เปลี่ยนระหว่าง upload. ไม่มี live publication ในการตรวจนี้

## Skips และ warnings ของ final gate
- อ่าน `.tmp/codex-gemini-audit-backend-final3.log` โดยตรง: **3686 passed / 13 skipped / 62 warnings / 1622.61s** ไม่มี failure; log ไม่ได้เก็บ `-rs` จึงไม่สามารถรับรองรายการเหตุผลทั้ง 13 รายข้อจาก log นี้ และไม่ควรเดาจาก test names
- Warning จำแนกครบ **62**: `shot_lists_store.py:62` datetime.utcnow **24**, `recording_sessions.py:58` datetime.utcnow **15**, Pillow Image.getdata ใน `test_preview_render_behavior.py` **23**. เป็น deprecation ไม่ใช่ failure; runtime 39 ข้อควรแก้เมื่อปรับ version/timezone โดย regression timestamp contract, Pillow 23 เป็น test-only
- Source มี optional GPU SAM2 (`test_background_isolation_sam2.py:120`), opt-in HF browser (`test_channel_hyperframes.py:104`), platform symlink privilege และ asset-dependent parity skips; ไม่อ้างว่าทั้งหมดตรงกับ 13 ข้อที่ final run skip. HF opt-in เคยผ่านแยกตาม `_Docs/Reports/CODEX_AUDIT_WORKFLOWS_20261011.md:49–59`. หากใช้งาน SAM2 GPU หรือ symlink จริง ต้องตรวจเครื่องนั้นเฉพาะ capability; skipped optional checks ไม่ใช่หลักฐาน TikTok live readiness

## Jev และข้อจำกัด
เรียก CLI `tools/jev_advisor.py` (ไม่ได้ทำ one-off script) ก่อน review: noul **0.45**, confidence **null**, verdict escalate; หลังเขียนรายงานคะแนน **3.5/4**, confidence **0.56** จากสรุปใน prompt (ไม่ได้อ่าน report/code เอง) user override ให้ใช้ tests/review แทนการถามซ้ำในขอบเขตนี้ยังใช้ได้ ไม่ถือ Jev เป็นหลักฐาน การตรวจนี้ไม่ได้รัน full suite ซ้ำหรือเปิด browser/credentials และไม่แก้ production data

## Cutover checkpoint จาก parent
Parent รายงาน backup snapshot/restore rehearsal **82 ไฟล์ผ่าน** และ archive ZIP manifest SHA **82 ไฟล์ verified**; explicit assignments **9** รายการเตรียมแล้วแต่ยังไม่ apply; migration preflight เหลือ API server ที่ยังทำงานอยู่ต้องหยุดก่อน apply ข้อความนี้เป็น evidence ที่ parent ส่งมา ไม่ใช่การรันซ้ำจากเอเจนต์ review

Verdict: **เตรียม mode กด extension ได้; live acceptance ยังรอการเชื่อม Chrome และตรวจ account/selector** — scheduler deferred ไม่บล็อก mode นี้; migration ยังไม่ apply และ existing enabled metadata ไม่แทน live proof
