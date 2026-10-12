# P0-B — Inventory ชั้นเก็บข้อมูลทั้งหมด และสิ่งที่ migration ต้องรองรับ (Multi-Channel)

- **ดำเนินการโดย:** Claude Code (Claude Opus 5.5) — agent P0-B
- **วันที่:** 2026-10-10
- **อ้างอิงแผน:** `_Docs/Plans/PLAN_MULTI_CHANNEL_20261010.md` §2, §3, §4, §8.1, §9 (แถว P0)
- **ไฟล์คู่ (machine-readable):** `_Docs/Reports/MULTI_CHANNEL_P0_STORE_INVENTORY_20261010.json`
- **วิธีตรวจ:** อ่านโค้ดใน `scripts/` และ `tools/` (grep `DocumentTable`, `_load(`, `_save(`, `_mutate(`, `json.load`, `.write_text`, `open(`, `sqlite3`) และนับข้อมูลจริงแบบอ่านอย่างเดียว — `store.db` กับ `batch_render_queue.db` ถูกคัดลอกด้วย SQLite backup API จาก URI `mode=ro` ลง scratchpad แล้ววิเคราะห์เฉพาะสำเนา, ไฟล์ JSON อ่านอย่างเดียว ไม่ได้อ่าน/บันทึก key, token หรือ cookie ใด ๆ
- **ไม่ได้แก้โค้ด ไม่รัน migration/server/render/pytest และไม่ใช้คำสั่ง git ที่เขียนข้อมูล**

## 1. สรุปสั้น

| หัวข้อ | ผล |
|---|---|
| จำนวน store ที่ inventory | 33 (sqlite-table 12, json-file 6, files 10, memory 5) |
| call site ที่เรียก `_load/_save/_mutate` ตรงจากนอกโมดูลเจ้าของ | **34** (+ `BatchQueueStore.load/mutate` แบบ full-snapshot 4 จุด, + ตัวเขียน JSON mirror ตรง 1 จุด, + ตัวเขียน `project.json` ตรง 4 จุด) |
| call site ในเทสที่แตะ internals ของ store | 31 จุดใน 12 ไฟล์ (เฉพาะจำนวน) |
| ข้อมูลที่มี `channel_id` แล้ว | 0 record ทุก store |
| หลักฐานเจ้าของเดิม | post ทั้ง 72 แถวมี `tiktok_url` ของ `@rizanntry` เท่านั้น; `kit/channels.js` มีแค่ `main` → ข้อมูลเดิมทั้งหมดถือเป็น `main` ได้ตามหลักฐาน ยกเว้นกลุ่ม orphan/unknown ใน §5 |

## 2. แกนกลาง: `scripts/db.py`

- `DocumentTable` = ตารางแบบ `id TEXT PRIMARY KEY, updated_at, data JSON` ต่อ record (`db.py:147-166`)
- `save()` = `BEGIN IMMEDIATE` → `DELETE FROM <table>` → INSERT ทุกแถว → เขียน JSON mirror ใหม่ทั้งไฟล์ (`db.py:346-367`) — **contract แทนที่ทั้งตาราง** ตามที่แผน §2 ระบุ
- `mutate()` (`_MutateCtx`, `db.py:449-530`) อ่าน snapshot เต็มใน transaction เดียว แล้ว flush เฉพาะแถวที่เปลี่ยน (DELETE/INSERT/UPDATE ราย id) — เป็นฐานที่เหมาะกับ scoped mutation แต่ถ้าโค้ดเรียกด้วย list ที่ถูกกรองแล้ว แถวที่หายจาก list จะถูก **DELETE** (`db.py:503-504`)
- **Auto-import JSON mirror:** ทุก `load()`/`mutate()` เรียก `_sync_from_json_if_newer` ถ้า token (mtime^size) ของไฟล์ mirror ไม่ตรงกับ `_json_mirror_state` จะ `DELETE` ทั้งตารางแล้ว INSERT จากไฟล์ (`db.py:319-324`) → การแก้ JSON mirror ตรง ๆ ไฟล์เดียว = เขียนทับ DB ทั้งตาราง
- WAL เปิดครั้งเดียวต่อไฟล์ (`db.py:110-122`), busy_timeout 5s + retry 3 ครั้ง, connection แคชต่อ (thread, db path) → **ทุกตารางใน `store.db` ใช้ connection เดียวกันใน thread เดียวกัน** การเรียก store อื่นจากใน `mutate()` เสี่ยง nested transaction
- `_json_mirror_state` ในฐานจริงมี 21 แถว โดย **14 แถวชี้ path ของเครื่องอื่น** (`D:\Winona\Programmer\Capcut\_Docs\*`, `D:\Winona\Programmer\Omnicut\_Docs\*`) = ฐานถูกย้ายข้ามเครื่องมา ไม่มีผลต่อการทำงาน แต่ tool migration ต้องไม่สับสน

## 3. ตาราง store (ย่อ — รายละเอียดเต็มอยู่ใน JSON)

| Store | โมดูล / backing | id / natural key ที่ชนข้ามช่อง | scope | ข้อมูลจริง |
|---|---|---|---|---|
| `products` | `ProductStore` / `store.db::products` + `_Docs/products.json` | uuid; **URL dedup** `product_store.py:391-416`; `product_code` สแกนทุกสินค้า `:2046-2068`; `angle_id` ไม่ unique ข้ามสินค้า | channel | 27 สินค้า / 274 angles, hidden 7, URL ซ้ำ 0, code ซ้ำ 0 |
| `posts` | `PostLog` / `store.db::posts` + `post_log.json` | uuid; export_id; **basename fallback** `post_log.py:253`, `:371-383`; fuzzy ทุกโพสต์ `:341` | channel | 72 แถว (ทั้งหมด `source=tiktok_stats_auto`, ไม่มี `export_id`/`product_id` ทั้ง 72) |
| `export_registry` | `ExportRegistry` / `store.db::export_registry` + `export_registry.json` | `exp_<uuid>`; `path_key`; basename ในผู้ใช้ภายนอก | channel | 198 แถว (posted 116 / rendered 82) |
| `schedule_queue` | `ScheduleQueueStore` (thin) + logic ใน `api_schedule_queue.py` | uuid; **`scheduled_at` unique ทั้งระบบ** `:359,:444,:971,:1028`; `video_key='04_exports/<basename>'` `:308` | channel | 156 (posted 111, planned 44, ready_for_extension 1) |
| `schedule_templates` | `ScheduleTemplateStore` | **id = `default` / `week:<date>`** `:244,:261,:273,:951` | channel | 1 แถว `week:2026-09-07` |
| `shot_lists` | `ShotListsStore` | `<product_id>:<angle_id>[:bN]` | channel | 418 แถว (**218 แถว product ไม่มีอยู่**) |
| `recording_sessions` | `RecordingSessionStore` | token; resume key (product, angle) `:133-145` | channel | 12 (orphan 1) |
| `tiktok_pending` / `tiktok_ignored` | `TikTokPending`/`TikTokIgnored` | identity = video_id หรือ **title** `tiktok_pending.py:41-45`; `replace_from_sync` ล้างทั้งตาราง `:133` | channel (ตามบัญชีต้นทาง) | 0 / 0 (`tiktok_ignored.json` ยังไม่ถูกสร้าง) |
| `raw_video_scenes` | `video_semantic_indexer.py` (SQL ตรง ไม่ใช่ DocumentTable) ใน `store.db` | file_hash | shared | 0 |
| `batch_render_queue` | `BatchQueueStore` / **ไฟล์ DB แยก** `03_Projects/batch_render_queue.db` + `.json` | `batch_id`=`id` | channel | 61 batch / 217 items (orphan product 1) |
| `task_registry` | `TaskManager` / `03_Projects/task_registry.json` + memory | token หรือ id จากผู้เรียก; `owner_id='local'` (เป็นผู้ใช้ ไม่ใช่ช่อง) | channel + global view | 9 งาน (จบหมด), payload product หาย 4 |
| autopost `_pending` | `api_tiktok_autopost.py:34` memory singleton | ตัวเดียวทั้งระบบ แทนที่/ล้างข้ามงาน `:235`, `:293-297` | channel → ต้องเป็น durable job | volatile |
| render `ACTIVE_JOBS` | `render_jobs.py:38` memory | job_id | channel | volatile |
| Project manifest + editor document | `ProjectManifest` / `03_Projects/<name>/project.json` + `.bak/.bak1-3` | ชื่อโฟลเดอร์ (namespace กลาง) | channel | 65 manifest มี product_id+angle_id ครบและ resolve ได้; โฟลเดอร์ไม่มี manifest 5 |
| ไฟล์ export (+ `.webp`) | `04_Exports/Ready_to_post`, `Posted` | ย้าย Posted ด้วยชื่อไฟล์ `api_exports.py:919-923`; map stem/name `:271-281` | channel | Ready 57 / Posted 114, ไม่ลงทะเบียน 0 |
| Covers | `05_Covers_Thumbnails/*.jpg` (แบน) | `<export_stem>_cover.jpg` `api_covers.py:207,:1031`; หา cover ด้วยชื่อสินค้า `api_exports.py:225` | channel | 759 ไฟล์ (ai/studio/ref_cache 264), ลิงก์ใน angle หายไฟล์ 0 |
| Gadget Media projects | `GadgetMediaRepository` / `03_Projects/GadgetMedia/<id>/*.json` + index `_Docs/gadget_media/project_index.json` | project_id มี uuid | channel | 0 project, ยังไม่มี index |
| Gadget Media campaigns | `CampaignStore` / `_Docs/gadget_media_campaigns.json` (เขียนทั้งไฟล์ ไม่มี lock) | campaign_id / slot_id | channel | 1 campaign / 21 slots, `account_role=gadget_media` |
| Producer notes + refs | `api_producer.py` / `02_Assets/Refs/playbook_notes.json` + `ref_*.{png,jpeg}` | revision sha256 | channel หรือ `scope=shared` ชัดเจน | notes 0 (UI ใช้ starter defaults), ref media 31 |
| Producer missions | คำนวณฝั่ง client (`producerInsights.js`, `ProducerHub.jsx:351`) ไม่ persist; targets/playbook ใน localStorage | — | channel (client) | — |
| HyperFrames (read-only) | `03_Projects/_HyperFrames_Studio/` compositions/clips/assets/kit | composition = ชื่อไฟล์; product = prefix ของชื่อ `api_hyperframes.py:99`; VO glob `:288-292` | channel | 10 compositions (มี `data-channel=main` 4, ไม่มี 6 → default main), clips 8 |
| Token analytics | `token_tracker.py` / `03_Projects/.token_analytics.json` | — | global | 1 document |
| Asset registry / hook templates / typography | `02_Assets/*.json`, `02_Assets/Templates/*` | asset key | shared | มีอยู่ |
| Caches | beat/vision/tone/motion cache, proxies, `03_Projects/.cache`, covers `.cache`/`.filmstrips`, `frontend/public/voice_cache` | hash | shared/derived | สร้างใหม่ได้ |
| Config / identity | `.env` (อ่านอย่างเดียว), `WATERMARK_TEXT` hardcode ที่ `subtitle_engine.py:167` และ `SequencePlayer.jsx:357`, `kit/channels.js` | — | global → channel identity | ตัวตนช่องซ้ำ 3 ที่ |
| Raw/Inbox library | `00_Inbox`, `01_Raw` (+ `.guided_take.json`), `product.videos[]` | path + SHA-256 | shared | ห้ามคัดลอกต่อช่อง |
| Backups / trash | `06_Archive/Backups`, `06_Archive/.trash` | — | global | backup 0 ไฟล์, trash 9 รายการ |
| Browser storage | `capcut_active_product_context`, `capcut_active_angle_context`, `capcut_selected_angle_index`, `capcut_task_cache`, `omnicut_active_project`, `capcut_studio_form`, `capcut_script_lab`, `omnicut_today_picked_scripts`, `omnicut_producer_targets`, `omnicut_boss_playbook`, render job key, `omnicut.mobileWorkflow` (session) | key กลาง | channel (บริบทงาน) / global (UI prefs) | ฝั่ง client |
| Extension storage | `chrome.storage.local` (API key, productId/caption/hashtags) | — | per browser profile | ไม่ได้ตรวจค่า |
| Memory caches | `ExportRegistry._path_index`, reconcile debounce, `_PROJECT_DISK_INFO_CACHE`, `_STORAGE_CACHE`, cancel events | — | global | restart หลัง migrate |
| ไฟล์หลง | `03_Projects/omnicut.db` 0 byte ไม่มีโค้ดอ้างถึง | — | — | ห้ามลบเองโดยไม่ถาม |

## 4. Call site ที่เข้าถึง store ตรง (แผน §4.4 บังคับ)

**ProductStore (13):** `scripts/api_videos.py:420` (_mutate), `:530` (_load), `:741` (_mutate), `:1152` (_load), `:1224` (_load); `scripts/api_render.py:124`, `:334` (_load); `scripts/api_phase1.py:1178` (_load); `scripts/backfill_product_codes.py:11` (_load), `:24` (_save); `scripts/migrate_paths_to_relative.py:171` (_load), `:194` (_save); `scripts/migrate_json_to_sqlite.py:92` (_load)

**PostLog (1):** `scripts/migrate_json_to_sqlite.py:93`

**ExportRegistry (2):** `scripts/api_exports.py:294` (_load), `scripts/migrate_compound_angle_ids.py:120` (_mutate)

**ScheduleQueueStore (12):** `scripts/api_schedule_queue.py:444, 670, 989, 1090` (_load), `:966, 1023, 1036, 1061, 1113` (_mutate); `scripts/api_tiktok_stats.py:79` (_load); `scripts/api_tiktok_autopost.py:253` (_mutate); `scripts/api_exports.py:693` (_mutate)

**ScheduleTemplateStore (4):** `scripts/api_schedule_queue.py:254` (_load), `:925, 938, 950` (_mutate)

**ตาราง `_TABLE` ที่ import ข้ามโมดูล (2):** `scripts/migrate_compound_angle_ids.py:22/139` (`shot_lists_store._TABLE.mutate`), `scripts/mobile_quick_studio.py:130` (`recording_sessions._TABLE.load`)

**Full-snapshot public API:** `scripts/batch_render.py:131` (mutate), `:141, :149, :193` (load)

**เขียนไฟล์ข้าม store:** `tools/clean_products_data.py:146,154` อ่าน/เขียน `_Docs/products.json` ตรง → auto-import จะ DELETE+INSERT ทั้งตาราง `products`; `tools/clean_products_data.py:161,173`, `scripts/rename_projects_with_product_code.py:101-103`, `tools/reprepare_cutout_video.py:125-129` เขียน `project.json` ตรงไม่ผ่าน `ProjectManifest`

ข้อสังเกต: ScheduleQueueStore ไม่มี API ระดับ record เลย ทุก caller ทำงานบน snapshot เต็ม จึงเป็นกลุ่มที่ต้องสร้าง scoped service ก่อนเป็นอันดับแรก

## 5. Natural key ที่ชนข้ามช่อง

1. **URL สินค้า** — `product_store.py:391-416` add() เจอ URL ซ้ำจะทับ angles/status ของ record เดิมไม่ว่าช่องไหน
2. **product_code** — `product_store.py:2046-2068` สแกนทุกสินค้า (ถ้าคง global ไม่ชน)
3. **angle_id / label** — ในข้อมูลจริงมี angle_id 20 ค่าใช้ซ้ำข้ามสินค้า ต้องใช้คู่ `(product_id, angle_id, batch)` เสมอ (`shot_lists_store.py:94`, `recording_sessions.py:133`)
4. **ชื่อไฟล์ export** — `api_exports.py:121,140,271-281,919-923`, `api_schedule_queue.py:308`, `api_covers.py:207,1031-1032`
5. **เวลา slot คิว** — `api_schedule_queue.py:359,444,971,1028`
6. **template id** — `api_schedule_queue.py:244,261,273,951`
7. **task id/cache** — id สุ่มไม่ชน แต่ list และ cache กลาง (`task_manager.py:392`, `TaskContext.jsx:39/135`)
8. **post idempotency basename** — `post_log.py:253`, `:371-383`, fuzzy `:341`
9. **pending/ignored title fallback + ล้างทั้งตาราง** — `tiktok_pending.py:41-45`, `:133`
10. **stats candidates รวมทุกช่อง** — `api_tiktok_stats.py:62-167`
11. **HyperFrames เดาเจ้าของจาก prefix ชื่อ** — `api_hyperframes.py:99`, `:288-292`, `:389`
12. **cover จากชื่อสินค้า** — `api_exports.py:225`
13. **ชื่อโฟลเดอร์โปรเจกต์** — `project_manifest.py:77-94`, `product_store.py:1437-1442`

## 6. ข้อมูลจริง: orphan / ไม่ทราบเจ้าของ

- **ความสอดคล้อง DB↔mirror:** 8 mirror ที่มีอยู่ id ตรงกับตารางทุกตัว (0 แตกต่าง), `integrity_check` = ok
- **export_registry:** ไม่มี product_id 26 แถว (rendered ใน Ready_to_post ทุกแถวมี project_name), product_id ไม่มีในสินค้า 1 แถว, ไฟล์หายจากดิสก์ 27 แถว (rendered, ไม่มีคิวอ้างถึง)
- **posts:** 72/72 ไม่มี export_id และ product_id; จับคู่ basename กับ export ได้ 1:1 จำนวน 65, ชื่อกลาง `clip.mp4` 7 แถวโยงไม่ได้; กลุ่ม basename ซ้ำ 4 กลุ่ม; Posted mp4 ที่ไม่มีแถว post 55 ไฟล์
- **shot_lists:** 218/418 อ้างสินค้าที่ไม่มีอยู่ (แต่ละแถวคนละ product_id — น่าจะเป็นขยะเทสหลุดเข้าฐานจริง) → ต้องทำรายการให้ผู้ใช้ยืนยันก่อนลบ ห้ามลบเอง
- **recording_sessions** orphan 1, **batch_render_queue** orphan 1, **task_registry** payload product หาย 4
- **โฟลเดอร์โปรเจกต์ไม่มี manifest 5:** `BLU01-FOMO_โปรไฟลุก_1`, `ESS02-explainer_1`, `ESS02-vs-battle_1`, `ESS02-แบตหมด-meme_1`, `HAT01-meme-50s_1` (มีแค่ VO/script ใช้เป็นแหล่ง VO ของ HyperFrames) → เจ้าของรู้ได้จาก prefix รหัสสินค้าเท่านั้น ซึ่งแผน §7.3 ไม่อนุญาตให้เดา จึงเป็น “ต้องระบุช่อง”
- angle ที่ `project_name` ชี้โฟลเดอร์ที่ลบแล้ว 105 (ทุกตัวสถานะ posted — ปกติ ไม่ใช่ orphan ที่ต้องแก้)
- **ไม่มีแถวที่หลักฐานเจ้าของขัดกัน** — กลุ่ม unknown = รายการ orphan ข้างต้น + covers แบนที่ไม่มีใครอ้าง + producer ref 31 ไฟล์ + campaign 1 (role `gadget_media`)

## 7. Backup coverage (`scripts/backup_engine.py`)

**ครอบคลุมแล้ว:** `_Docs/*.json` ระดับบนสุด (copy ไฟล์ตรง), `_Docs/store.db` ผ่าน backup API `mode=ro` + integrity_check (`backup_engine.py:37-70`), ทุกไฟล์ใน `03_Projects/**` ที่ชื่อไม่ขึ้นต้นด้วย `.` (ยกเว้น `.token_analytics*`) และไม่ใช่ `.tmp/.lock` — รวม `project.json`/`.bak*`, `task_registry.json`, `batch_render_queue.json`, GadgetMedia, `_HyperFrames_Studio` ทั้งหมด (รวม `node_modules`, `kit/channels.js`), `_RecordingSegments`, `_ShotLists`, `.cache`

**ยังไม่ครอบคลุม/มีปัญหา:**
- `03_Projects/batch_render_queue.db` ถูก zip แบบไฟล์ดิบ (ไม่ใช่ backup API) พร้อม `-wal/-shm` แยก → **ไม่ WAL-consistent**
- โฟลเดอร์ย่อยของ `_Docs` (`_Docs/gadget_media/project_index.json`) ไม่ถูกเก็บ
- ไฟล์ที่ชื่อขึ้นต้นด้วย `.` ใน 03_Projects (เช่น `.run_started.json`) ถูกข้าม
- `02_Assets/Refs/playbook_notes.json` + ref media, `02_Assets/asset_registry.json`/`asset_metadata.json`/`Templates/*`, `frontend/public/voice_cache`, `.env`, browser/extension storage, memory `_pending`/`ACTIVE_JOBS`
- **ไม่มี restore routine** (`api_backup.py` มีแค่ create/list/download/verify/delete; `tools/backup_restore_dry_run.py` แค่ตรวจ)

**ที่ multi-channel ต้องเพิ่ม:** `_Docs/channels.json` (top-level จะติดอัตโนมัติ แต่ต้องตรวจ schema/revision ตอน restore), kit config + identity snapshot ใน manifest/composition, manifest ใต้ `03_Projects/<channel_id>/` (walk ครอบอยู่แล้ว), index GadgetMedia ใต้ `_Docs/gadget_media/`, ตาราง posting job/lease (ถ้าอยู่ใน `store.db` ครอบแล้ว ถ้าเป็น JSON ต้องเพิ่ม), migration journal/version, เปลี่ยน `batch_render_queue.db` ให้ใช้ backup API, และให้ `backup_manifest.json` บันทึกจำนวนแถว/sha256/schema version ต่อ store เพื่อใช้ตรวจ restore ตามแผน §8.1 ข้อ 4–5

## 8. ความเสี่ยงหลัก (เรียงตามระดับ)

1. **Blocker** — `save()`/auto-import แทนที่ทั้งตาราง (`db.py:346-367`, `:319-324`): scoped `_load→filter→_save` หรือแก้ mirror ตรง (`tools/clean_products_data.py:154`) จะลบข้อมูลช่องอื่น
2. **Blocker** — URL dedup ทับสินค้าช่องอื่น (`product_store.py:391-416`)
3. **Blocker** — `TikTokPending.replace_from_sync` ล้างทุกแถว (`tiktok_pending.py:133`)
4. **Major** — nested write บน connection เดียวกันของ `store.db`: `product_store.py:485` (ShotListsStore.delete ใน products `_mutate`), `tiktok_pending.py:129` (โหลด ignored ใน pending `_mutate`) → ต้องมี cross-store coordinator ตาม §4.4
5. **Major** — call site ตรง 34 จุด (คิวกำหนดการ 12 จุด) ต้องแยก internal-full vs scoped ก่อน P2
6. **Major** — HyperFrames render ลง `04_Exports/Ready_to_post/Ready_to_post` (`api_hyperframes.py:347`, เพราะ `EXPORTS_DIR` เป็น Ready_to_post อยู่แล้ว) และลงทะเบียน `product_id` ปลอมจาก prefix (`:389`) — วันนี้ยังไม่มีไฟล์/แถวแบบนี้
7. **Major** — legacy posts ไม่มี export_id/product_id ทั้งหมด ต้อง backfill ด้วย basename (7 แถวโยงไม่ได้)
8. **Major** — shot_lists orphan 52% ในฐานจริง
9. **Major** — backup ไม่ครอบ `batch_render_queue.db` อย่างถูกต้อง, ไม่ครอบ `_Docs/gadget_media/` และ producer notes, ไม่มี restore
10. **Minor** — `CampaignStore.save` เขียนทั้งไฟล์ไม่มี lock (`gadget_media_campaign.py:401-419`), ตัวตนช่องซ้ำ 3 ที่, `_json_mirror_state` มี path เครื่องอื่น 14 แถว

## 9. สิ่งที่ยังระบุไม่ได้

- ค่าใน browser localStorage และ `chrome.storage` บนเครื่องผู้ใช้ (ฝั่ง client ไม่ได้ตรวจ)
- มีข้อมูลช่องรองนอก repo หรือไม่ (เช่น Chrome profile ที่สอง) — ใน repo เห็นแค่ `@rizanntry`
- เจ้าของ campaign Gadget Media 1 รายการ (`account_role=gadget_media`) และนโยบาย producer ref media (shared หรือรายช่อง) — รอ §11
- export_registry 26 แถวที่ไม่มี product_id จะ resolve ผ่าน `project.json` ได้กี่แถว (27 ไฟล์หายจากดิสก์) — ให้ dry-run ใน P2 ตัดสิน
