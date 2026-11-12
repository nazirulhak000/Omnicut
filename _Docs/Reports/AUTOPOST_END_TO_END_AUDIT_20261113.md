# Autopost End-to-End Audit — ผลิต → เรนเดอร์ → คิว → TikTok (2026-11-13)

ดำเนินการโดย: Claude Code (Claude Opus 5.5) · อ่านอย่างเดียว ไม่แก้โค้ด ไม่เขียน `_Docs/*.json` ไม่โพสต์จริง

## วิธีตรวจ

- อ่านโค้ด 3 ส่วนขนานกัน: extension (`tiktok_autopost_extension/`), backend คิว/โพสต์ (`api_tiktok_autopost.py`, `api_schedule_queue.py`, `posting_jobs.py`, `publication_observations.py`, ...), เส้นผลิต→เรนเดอร์ (`production_chain.py`, `api_phase1.py`, `auto_cover.py`, `auto_sharpen.py`)
- อ่าน `_Docs/schedule_queue.json`, `_Docs/post_log.json`, `_Docs/store.db` แบบอ่านอย่างเดียว เทียบกับโค้ด
- เทสต์: extension `node --test` **234/234 ผ่าน** · backend 11 ไฟล์ **233 ผ่าน 0 ล้ม** — ไม่มีเทสต์ไหนจับข้อที่เจอด้านล่าง
- ป้าย: **[ยืนยัน]** = ไล่โค้ด/ข้อมูลจริงแล้ว · **[สงสัย]** = ยังไม่ได้พิสูจน์

## 0. ข้อมูลจริงในคิวตอนนี้ (201 แถว: posted 157 · planned 28 · scheduled_on_platform 16)

| สิ่งที่เจอ | จำนวน | ต้นเหตุในโค้ด |
|---|---|---|
| คลิปเดียวกันมี 2 แถว (`TOS01-เทียบของเดิม` = posted + planned 13/11 12:30 · `TOS01-เจาะกลุ่ม` planned×2 · `HOY01-โปรไฟลุก` planned×2) | 3 คู่ | ข้อ A1, A2 |
| `scheduled_on_platform` เลยเวลา 1–3 วัน ไม่ขยับเป็น `posted` | 16 | ข้อ B2 |
| `planned` เลยเวลา (12/11) ไม่มีใครเตรียม | 5 | ข้อ B11 |
| `posted` แต่ `posted_at` ว่าง | 45 | ข้อ B9 |
| `updated_at` ไม่มี timezone | 60 | ข้อ C8 |
| `cover_path` กับ `cover_url` คนละไฟล์ | 15 | ข้อ C9 |
| แถว `HAT01-เตือนภัย_1` ชี้ไฟล์ mp4 ที่ไม่มีแล้ว | 1 | — |
| post_log แถวไม่มี `tiktok_url` | 52 | ข้อ B2 (ไม่มีทางผูก URL ย้อนหลัง) |
| job `77dc2ec7…` เป็น `published` แต่ไม่มี receipt/attempt | 1 | ตั้งค่านอก protocol |

> ⚠️ **ทำก่อนกด "เตรียมทั้งหมด"**: แถว `planned` ของ `TOS01-เทียบของเดิม` (13/11 12:30) เป็นคลิปที่โพสต์แล้ว — ถ้าเตรียมจะโพสต์ซ้ำ. ต้องให้เจ้าของยืนยันก่อนลบ/ยกเลิกแถวซ้ำทั้ง 3 คู่

## A. P0 — โพสต์ซ้ำ / ทำงานผิดคลิป

| # | ปัญหา | ที่ | สถานการณ์ | วิธีแก้ |
|---|---|---|---|---|
| A1 | tool one-off รีเซ็ต export `posted` → `rendered` + เขียนคิวทั้งก้อนด้วย `_save` ข้ามด่านกันซ้ำ **[ยืนยัน]** | `tools/batch_schedule_non_couple_exports.py:141-149`, `tools/reschedule_all_old_non_couple_clips.py:161-169`, `tools/reschedule_47_unposted_clips.py:203` | ปลด guard หลักที่ `prepare()` ใช้ปฏิเสธคลิปที่โพสต์แล้ว (`api_tiktok_autopost.py:285`) → คู่ซ้ำในคิวตอนนี้ | เลิกใช้ หรือให้ผ่าน `create_queue`/auto-fill service · ห้ามรีเซ็ต `posted` โดยไม่ดู posting job |
| A2 | effect หลังโพสต์สร้างแถวคิวใหม่ ทั้งที่ export มีแถว `planned` อยู่แล้ว **[ยืนยัน]** | `api_tiktok_autopost.py:729-743` (หาแถวเดิมเฉพาะ `scheduled_on_platform`/`draft_on_platform`) | เตรียมจากหน้า exports (ไม่มี `queue_id`) → 2 แถว → โพสต์ซ้ำภายหลัง | ใช้/ปฏิเสธแถว active ที่ `export_id` เดียวกัน · panel ส่ง `queue_id` ที่มีอยู่ |
| A3 | panel ได้ 409 `already_prepared` แล้ว `/clear` งานที่ `/pending` คืน โดยไม่เช็ก `export_id` **[ยืนยัน]** | `sidepanel.js:1887-1899`, `:3321-3335` (conductor เช็กแล้วที่ `conductor.js:147`) | ยกเลิกงานของคลิปอื่น + รีเซ็ตแถวคิวคลิปอื่น | เช็ก `export_id` ตรงก่อน clear · backend supersede งาน `prepared` ที่ยังไม่ claim ของ export เดียวกันเอง |
| A4 | receipt ที่รอส่งถูกล้างเมื่องานอ่านได้ `cancelled` · panel เขียน state ทับทั้งก้อนจากสำเนาเก่า **[ยืนยันโค้ด / trigger สงสัย]** | `sidepanel.js:372-398`, `background.js:634-646` | โพสต์จริงแล้วแต่ receipt หาย → export กลับมาเตรียมได้ → ซ้ำ | ห้ามล้าง pending receipt ตอน cancelled · เปลี่ยน state ผ่าน worker เท่านั้น |
| A5 | publish-from-draft จับดราฟต์จาก caption 20 ตัวอักษรในแถวที่ render อยู่เท่านั้น ไม่เช็ก EP **[ยืนยันโค้ด]** | `background.js:5533-5579` | ดราฟต์สินค้าเดียวกัน hook ขึ้นต้นเหมือนกัน → เผยแพร่ผิดคลิป บันทึกเป็นงานนี้ | ใช้ `collectDraftRows` + `OmniDraftEvidence.matches` (มี EP) · ต้องเจอ 1 แถวพอดีทั้งรายการ · เช็ก EP ในหน้าแก้ไข |

## B. P1 — flow ค้าง / ต้องแก้มือ

| # | ปัญหา | ที่ | ผล | วิธีแก้ |
|---|---|---|---|---|
| B1 | **ปกอัตโนมัติทำให้เข้าคิวไม่ได้ (409 `export_cover_selection_conflict`)** **[ยืนยันโค้ด]** | `api_schedule_queue.py:570-575` เลือกปก 3:4 ก่อน · `ScheduleAgenda.jsx:81,120` ส่ง `clip.cover_path` = 9:16 (`auto_cover.py:144-168`) | ทุกคลิปที่เรนเดอร์ใหม่มีปก auto (23/24 binding) → บันทึก auto-fill ล้มทั้งก้อน · preview ไม่เตือน | ยอมรับปกที่ตรง format ใดก็ได้ใน binding (หรือไม่สน `payload.cover_path` เมื่อมี binding) · preview ตรวจด่านเดียวกันแล้วข้ามรายการเสีย |
| B2 | `scheduled_on_platform` ไม่มีทางกลายเป็น `posted` **[ยืนยันข้อมูลจริง]** | `publication_observations.py:89-92` ต้องมี `platform_post_id` แต่ toast ตั้งเวลาไม่มี video id | 16 แถวค้าง · post_log ไม่มี URL · analytics ขาด | หลัง `scheduled_at` + grace ให้ extension reconcile จากหน้า Content (ได้ video id) หรือรับ observation ที่มี URL จับคู่ด้วย EP/caption |
| B3 | GET `/api/schedule-queue` ตอบ 500 ทั้งช่อง ถ้ามีแถว `scheduled_at=None` **[ยืนยัน]** | `sort_records` `api_schedule_queue.py:463` (`.get(...,"")` ได้ None), filter `:1284-1286` · แถว None มาจาก draft intent ไม่มี `queue_id` (`api_tiktok_autopost.py:701-703`) | หน้าคิวทั้งหน้าใช้ไม่ได้ | `item.get("scheduled_at") or ""` · guard None ใน filter |
| B4 | รูปแบบเวลาไม่ตรงกัน `…T10:15:00+07:00` vs `…T10:15+07:00` **[ยืนยัน, 1 แถวจริง]** | `api_tiktok_autopost.py:717` vs `scheduled_iso` | เช็กช่องเวลาซ้ำแบบเทียบ string พลาด → จองช่องซ้ำ | ใช้ `scheduled_iso(parse_scheduled_at(...))` ทุกจุด + normalize ข้อมูลเดิม |
| B5 | lease หมดแล้วเตรียมใหม่ → งานใหม่ค้าง `prepared` มองไม่เห็นแต่บล็อกคลิป **[ยืนยันจาก trace]** | `posting_jobs.py:127-134`, `api_tiktok_autopost.py:446-449` | ทางออกคือ PATCH มือ | ยกเลิกงานหมดอายุพร้อมรีเซ็ตแถวคิว · `_mark_ready` ยอมแถวที่ชี้งาน cancelled · effect ล้มให้ cancel งานใหม่ |
| B6 | receipt ที่ backend ปฏิเสธ (4xx อื่น) ค้างใน storage ถาวร → worker ล้มทุกคลิป **[ยืนยัน]** | `background.js:464-508, 514-519, 565-578` | ต้องแก้ storage มือ | 4xx → GET `/jobs/{id}` ถ้า final ทิ้ง receipt บันทึกใน `unresolvedJobs` + ปุ่ม "ทิ้ง receipt หลังตรวจ backend" |
| B7 | reconcile สำเร็จแบบ scheduled แล้วยังส่ง receipt `confirmation_unknown` ซ้ำ **[ยืนยันโค้ด]** | `background.js:4697-4721` (return เฉพาะ `published`) | ลดสถานะงานที่ยืนยันแล้ว หรือเข้า B6 | return เมื่อ reconcile ยืนยันแล้วทุกแบบ |
| B8 | ไม่เช็กวัน/เวลาที่ตั้งซ้ำตอนกด (cover editor re-render ฟอร์มได้) **[ยืนยันโค้ด]** | `background.js:4305-4338, 5116-5131` | TikTok โพสต์ผิดเวลา backend จดเวลาที่วางแผน | `assertPublishReady` เรียก `waitForScheduleValues` ไม่ตรง = ไม่กด |
| B9 | แถวคิว `posted` ไม่ได้ตั้ง `posted_at` **[ยืนยัน]** | `api_tiktok_autopost.py:681-691` | 45 แถว · ข้อจำกัดรายวัน/สถิติเพี้ยน | ตั้ง `posted_at = now_iso()` + backfill จาก receipt ของ job |
| B10 | ลิงก์สินค้านับว่าแนบแล้วแค่ modal ปิด **[ยืนยันโค้ด]** | `background.js:2699-2707` | คลิป affiliate โพสต์โดยไม่มีตะกร้า แต่รายงานสำเร็จ | ต้องเห็น chip สินค้าชื่อตรง + เช็กซ้ำใน `assertPublishReady` |
| B11 | ไม่บังคับเพดาน TikTok 10 วัน · reschedule ขอ 14 วัน backend รับถึง 60 · `/prepare` ไม่เช็กว่าเวลาอยู่ในอนาคต **[ยืนยัน]** | `sidepanel.js:3820`, `api_schedule_queue.py:227`, `post_guard.js`, `background.js:2938` | อัปโหลดเสร็จแล้วค่อยล้มที่เลือกวัน · อัปโหลดซ้ำ | `MAX_LEAD_MS` 10 วันใน `limits.js` + backend `le=10` + `/prepare` ต้อง `slot > now+15 นาที` |
| B12 | นับโพสต์ตั้งเวลาไม่ครบ (lazy-load) แต่ใช้เป็นค่าจริง **[ยืนยันโค้ด]** | `quota_detector.js:303-341`, `background.js:5405-5439` | ตั้งเวลาเกิน cap → unknown จน breaker ตัด | `complete=false` = ไม่รู้ |
| B13 | ปุ่ม "ยืนยันโพสต์แล้ว" ไม่มีด่าน และ backend `/reconcile` รับ `manual_user_confirmation` จากงาน `claimed` ที่ไม่เคยกดโพสต์ → งานเป็น final, ไฟล์ย้ายไป `Posted/`, เขียน PostLog · ล้าง `activeJob` แม้ได้ unknown **[ยืนยันทั้งสองฝั่ง]** | `background.js:843-892`, `sidepanel.js:2541-2547`, `posting_jobs.py:281-294` | คลิปที่ไม่ได้โพสต์ถูกจดว่าโพสต์แล้ว (โพสต์หาย) | backend ปฏิเสธ reconcile จาก `claimed` ที่ไม่มี `publish_attempted_at` · extension คง `activeJob` ถ้ายังไม่ final |
| B15 | GET `/pending` คืนงานเก่าสุดเสมอ ไม่สน lease/owner และไม่ข้ามงานที่ claim ไม่ได้แล้ว (hash เปลี่ยน) → บล็อกคิวทั้งช่อง **[สงสัย]** | `posting_jobs.py:97-101` | งานเดียวเสียค้างหัวแถว | ข้ามงานที่ hash/binding ไม่ตรง หรือ auto-cancel |
| B14 | หน้าเว็บไม่ส่ง `preview_revision` ตอนบันทึก auto-fill **[ยืนยัน]** | `ScheduleAgenda.jsx:998` | โหมด `OMNICUT_MULTI_CHANNEL_STRICT` = 422 ทุกครั้ง · โหมดปกติข้ามด่าน preview เก่า | ส่ง `autofillPreview.preview_revision` |

## C. P2 — ความทนทาน / ความเร็ว / UX

| # | ปัญหา | ที่ |
|---|---|---|
| C1 | angle ขึ้น `rendered` ก่อน sharpen + ปกเสร็จ (ช่วงไม่กี่วิ–40 วิ) → เข้าคิวได้โดยไม่มีปก / hash เปลี่ยนเป็น `posting_export_changed` **[สงสัย]** | `api_phase1.py:1544` ก่อน `:1563-1568`, `batch_render.py:943-961` |
| C2 | sharpen รันนอก `render_slot` → libx264 fallback ไม่ถูกจำกัด ชน RAM (AGENTS #24) | `api_phase1.py:1470` |
| C3 | `os.replace` ตอน sharpen ล้มบน Windows ถ้าไฟล์เปิดอยู่ แล้วกลืน error → โพสต์คลิปไม่คม **[สงสัย]** | `tiktok_enhancer.py:207`, `auto_sharpen.py:73` |
| C4 | restart server กลาง chain ไม่ resume · batch draft ยังวิ่ง chain ตาย → กดซ้ำทำดราฟต์ซ้ำ **[สงสัย]** | `task_manager.py:147-167` |
| C5 | chain สำเร็จบางส่วนแสดง "เสร็จ" (`ok = made > 0`) · คลิปเดียวอ่านไม่ได้หยุดทั้ง chain | `production_chain.py:602, 260` |
| C6 | ไม่มีขั้นอัตโนมัติจากเรนเดอร์เสร็จ → คิว (ขั้น 6–9 ทำมือทั้งหมด) | `production_chain.py` (ตั้งใจ ตาม docstring) |
| C7 | เช็กอัปโหลดล้มไม่ได้ รอ badge สำเร็จ 15 นาที · ข้อความ "-50%" อ่านเป็นกำลังอัปโหลด | `background.js:1474-1593` |
| C8 | `datetime.now().isoformat()` ไม่มี tz | `api_tiktok_autopost.py:455, 543, 690, 724, 769` |
| C9 | `cover_url` เก็บตามที่ client ส่ง ไม่ derive จาก `cover_path` → มือถือโชว์ปกคนละรูปกับที่โพสต์ | `api_schedule_queue.py:568-603`, `api_mobile_posting.py:154` |
| C10 | Gallery โชว์ `scheduled_on_platform` ทับ `posted` ของ registry | `api_exports.py:640-651` |
| C11 | quota check เงียบแย่ step lock ของ batch → "มีขั้นตอนกำลังทำอยู่" นับ unknown | `sidepanel.js:3466, 1485`, `background.js:5803` |
| C12 | message ค้าง 900 วิ เกิน SW 5 นาที · `debugger.attach` ไม่จัดการ "already attached" · `cdp()` ไม่มี timeout | `automation.js:166`, `background.js:1186, 4582…` |
| C13 | heartbeat run lock ใน panel ถูก throttle ตอนซ่อนหน้าต่าง (TTL 45 วิ) | `sidepanel.js:3113-3142`, `run_lock.js` |
| C14 | banner error เก่าอ่านเป็น "TikTok ปฏิเสธ" (ไม่เช็ก `fresh`) | `background.js:3854` |
| C15 | timezone เครื่องไม่ใช่ Bangkok → slot เพี้ยน · ปัดเวลา 5 นาทีเงียบ ๆ แล้ว verify ไม่ตรง | `background.js:2909, 2940` |
| C16 | reconcile/verify ขับแท็บ TikTok ใดก็ได้ของผู้ใช้ | `background.js:899-935, 5266` |
| C17 | `tools/portable_uploader_server.py`: `/api/media` path traversal + CORS `*` ไม่มี auth · `/ack` mark posted ทุก outcome | `:240-259, 332-388` |
| C18 | mobile handoff กลืน exception + สถานะ `awaiting_post` ที่ state machine ไม่รู้จัก (ผู้ใช้บอกไม่ใช้ route นี้) | `api_mobile_posting.py:420-443` |
| C19 | ช่อง main ใช้ปกของช่องอื่นได้ · `update_cover` แทนปกที่ freeze ไว้ได้ | `api_tiktok_autopost.py:378, 486` |
| C20 | ความเร็ว: SHA-256 ไฟล์วิดีโอเต็มทุก claim/validate/attempt · `posting_jobs.json` 965 KB (cancelled 149 งานไม่เคยลบ) เขียนทั้งก้อน ~4 ครั้ง/โพสต์ | `api_tiktok_autopost.py:578-595`, `posting_jobs.py` |
| C21 | อื่น ๆ: lookup ไม่สน lot (`batch`) — ยังไม่เกิดกับข้อมูลจริง · ชื่อไฟล์ export ไม่ตาม `YYYYMMDD_ชื่อ_hook_vN` · sharpen = encode รอบสอง เสียคุณภาพ | `api_phase1.py:1370,1566`, `video_assembly_stage.py:300-308` |

## D. ที่ตรวจแล้วโอเค

- store เป็น SQLite (WAL, `BEGIN IMMEDIATE`) + JSON mirror แบบ temp+replace · uvicorn worker เดียว → ไม่มี race ระหว่างเรนเดอร์ขนาน
- เรนเดอร์เขียนไฟล์ partial → ด่านตรวจไฟล์ → `os.replace` · mp4 เสียไม่ถูกตั้ง `rendered`
- posting job เช็ก hash วิดีโอ/ปกก่อนทุกขั้น → ไฟล์เปลี่ยน = ล้มแบบปลอดภัย ไม่โพสต์ผิดคลิป
- ข้อเก่าที่แก้แล้ว: CODEX_AUDIT_POSTING_20261011 ทั้งหมด, แผน F1–F7, extension audit F-01/02/03/04/07/10/11/12/17/18/20, EpisodeRegistry counter

## E. ลำดับแก้ที่แนะนำ

| รอบ | งาน | เหตุผล |
|---|---|---|
| 0 (ข้อมูล, รอเจ้าของยืนยัน) | จัดการคู่ซ้ำ 3 คู่ · แถว HAT01 ไฟล์หาย · backfill `posted_at` · ตัดสิน 16 แถว scheduled ที่เลยเวลา | กันโพสต์ซ้ำวันนี้ |
| 1 ปลดล็อกคิว + กันซ้ำ | B1, B3, B4, B9, B14, A1, A2, A3 + เทสต์ | backend/frontend ล้วน แก้เล็ก ผลใหญ่ |
| 2 ความถูกต้อง extension | A4, A5, B5, B6, B7, B8, B10, B11, B12, B13, B15 | ต้อง reload extension + ทดสอบบัญชีจริง |
| 3 ปิดวงจร | B2 (scheduled → posted), C1, C4, C6 (auto-fill หลัง chain จบ), C5 | ทำให้ไหลเองจริง |
| 4 ทนทาน/ความเร็ว | C2, C3, C7, C11–C16, C20 | |

## F. Endpoint ที่ extension ใช้ (สรุป)

`/api/tiktok-autopost`: GET `capabilities`, `pending`, `jobs/{id}` · POST `prepare`, `clear`, `claim`, `validate`, `attempt`, `release`, `ack`, `reconcile`, `cover` · panel: GET `/api/exports`, `/api/schedule-queue`, `/api/channels` · PATCH `/api/schedule-queue/{id}` · POST `resolve-draft`, `reschedule-overdue/preview`, `reschedule-overdue`, `/api/tiktok-stats/import` · GET `/api/media/...?api_key=`

## G. ผลการแก้ (รอบ CLAUDE-AUTOPOST-E2E-FIXES-20261113)

ดำเนินการโดย: Claude Code (Claude Opus 5.5) · เจ้าของสั่ง "จัดการแล้วเริ่มได้เลย ละเอียดทุกจุด" (2026-11-13)

| กลุ่ม | ทำแล้ว |
|---|---|
| ข้อมูลจริง (สำรอง `06_Archive/store_backup_20261113_autopost/`) | ลบแถวซ้ำ 3 · export TOS01-เทียบของเดิม → posted · เติม `posted_at` 45 · tz ของ `updated_at`/`extension_prepared_at` · `cover_url` จาก `cover_path` 16 · เวลาแบบมีวินาที 1 |
| A1–A5 | tool 3 ตัวปิดใช้ + `store_io` คืนสถานะ posted เสมอ · effect ใช้แถวเดิมของ export · `/prepare` แทนที่งาน prepared ที่ยังไม่มีใครรับ + panel clear เฉพาะ export ตรงกัน · ไม่ทิ้ง receipt ตอน cancelled · publish-from-draft ต้องตรง EP + แถวเดียว |
| B1–B15 | ปก auto เข้าคิวได้ · sort/filter ทน `scheduled_at=None` · เวลาแบบนาที · lease หมด/prepare ล้มไม่ทิ้งงานค้าง · receipt ที่ถูกปฏิเสธไม่ล็อก worker · reconcile ยืนยันแล้ว return · เช็กวัน/เวลาก่อนกด · `posted_at` · ต้องเห็นสินค้าจริง · หน้าต่าง 15 นาที–10 วัน ทีละ 5 นาที (backend/extension/frontend) · นับโพสต์ตั้งเวลาไม่ครบ = ไม่รู้ · reconcile ต้องเคยกดโพสต์ · `preview_revision` · `/pending` ข้ามงานที่ไฟล์เปลี่ยน · B2 endpoint `linkage-due` + `content-linkage` + ปุ่ม "ตรวจคลิปที่ถึงเวลาแล้ว" |
| C1–C21 | rendered หลัง sharpen+ปก · sharpen ใน render slot · retry `os.replace` + `tiktok_sharpen_error` · chain ข้ามมุมที่มี batch ค้าง · "เสร็จบางส่วน" · ค้นมุมตามล็อต · ตรวจอัปโหลดล้ม · tz · `cover_url` derive · Gallery posted ชนะ · busy/quota/SW/CDP timeout/heartbeat · banner ต้องสด · tz +07:00 ไม่ปัดเวลา · แท็บ Studio ของตัวเอง · portable server path/lease/outcome · mobile handoff · ปกข้ามช่อง · hash cache |
| ไม่ทำ (เหตุผล) | C6 คิวอัตโนมัติหลัง chain (เจ้าของเลือกจุดตรวจ) · เปลี่ยนชื่อไฟล์ export / รวม sharpen เข้า render (กระทบ Preview=Render) · ลบงาน cancelled ออกจากไฟล์ (ต้องเจ้าของยืนยัน) · สแกนฉากหยุดทั้ง chain (กฎเจ้าของ แค่บอกชื่อคลิป) |
| เพิ่มตามเจ้าของ | caption ติดราคา: `scripts/caption_price_fix.py` (AI task `caption_fix` → ตรวจด้วย `content_guard` → ไม่ผ่านใช้ประโยคกลาง, cache) · แก้อัตโนมัติตอนเข้าคิว + แจ้งจำนวน · ปุ่ม "แก้ caption ที่ติดราคา (N)" ดูก่อน/หลัง → บันทึก (แก้มุมต้นทางที่ยังไม่โพสต์ด้วย) |

ผลทดสอบ: pytest เต็มชุด 5562 ผ่าน / 3 ล้ม (2 = route `master-shot-list` ของรอบ PHONE-ONE-TAKE ที่ยังไม่ commit, 1 = `test_couple_engine` ล้มบน HEAD สะอาดอยู่เดิม) · ชุดหลังเพิ่ม caption 226/226 + คิว 51/51 · `tests/motion_capture` 181 ผ่าน (แก้ข้อความคาดหวัง 1 ข้อ) + เทสต์ใหม่ caption fix · extension node 258/258 · conductor 39/39 · extension โหลดจริง: p0 36/36, real 27/27, panel 0 fail · frontend 1321/1321 + build

ยังไม่ได้ทำ: ทดสอบกับบัญชี TikTok จริง (open-browser-use ไม่ได้เชื่อม Chrome ที่ล็อกอิน) → เจ้าของ reload extension 0.11.0 → กด "ตรวจคลิปที่ถึงเวลาแล้ว" (17 งาน) → ตั้งเวลาโพสต์จริง 1 คลิป เพื่อยืนยัน selector บนหน้า TikTok จริง (วัน/เวลา, ป้ายสินค้า, สถานะอัปโหลด, ลิงก์ `/video/` ในหน้า Content)
