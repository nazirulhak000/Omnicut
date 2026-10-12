# Runbook — ย้ายข้อมูลเดิมเข้าระบบหลายช่อง (multi-channel P2.3)

- **ดำเนินการโดย:** Claude Code (Claude Opus 5.5) — agent P2.3
- **วันที่:** 2026-10-10
- **อ้างอิง:** `_Docs/Plans/PLAN_MULTI_CHANNEL_20261010.md` §8, §10 (AC13, AC17), §11 · ADR `_Docs/Plans/ADR_MULTI_CHANNEL_20261010.md` §12 · P0 `_Docs/Reports/MULTI_CHANNEL_P0_STORE_INVENTORY_20261010.md`
- **โค้ด:** `scripts/channel_migration.py` (library) · `tools/migrate_channels.py` (CLI) · `scripts/maintenance_lock.py` (lock) · เทส `tests/test_channel_migration.py`
- **ผลซ้อมกับข้อมูลจริง (อ่านอย่างเดียว):** `_Docs/Reports/MULTI_CHANNEL_P2_MIGRATION_DRYRUN_20261010.md/.json`

> **ห้าม `--apply` กับข้อมูลจริงก่อน P8 cutover และก่อนเจ้าของตัดสินรายการในข้อ 6** — รอบนี้ทดสอบเฉพาะบน temp root และสำเนา

## 1. Tool ทำอะไร / ไม่ทำอะไร

เติม `channel_id` บนสุดของ record เดิมที่ยังไม่มี (legacy) ทีละ store เรียง parent → child:
products → export_registry → posts → schedule_queue → schedule_templates → shot_lists → recording_sessions → tiktok_pending/ignored → batch_render_queue → task_registry → project.json

| store | หลักฐานที่ใช้ | ไม่รู้ → unknown |
|---|---|---|
| products | legacy cohort = `main` เมื่อ registry มีแค่ `main` และ handle ในโพสต์ทุกแถวเป็นของ main (ถ้ามีช่องอื่นต้องระบุ `--legacy-owner`) | — |
| export_registry | `product_id` → สินค้า; ไม่มี → `project.json` ของ `project_name` (`render_params.product_id`) | product หาย, ไม่มี manifest |
| posts | `export_id`/`product_id`; ไม่มี → ชื่อไฟล์ตรงกับ export **เพียง 1 รายการ** | `clip.mp4` ฯลฯ (ห้ามเดา), ชื่อซ้ำหลาย export, ไม่พบ |
| schedule_queue | export/product (ชี้คนละช่อง = conflict) | ไม่มี parent |
| schedule_templates | เปลี่ยน id `default`/`week:<d>` → `<owner>:default`/`<owner>:week:<d>` + `channel_id` + `legacy_id` — **ปิดอยู่จนกว่าจะใส่ `--rename-templates`** | id แบบอื่น |
| shot_lists / recording_sessions / batch_render_queue / task_registry (`payload.product_id`) / project.json | ผ่าน product | product หาย / ไม่มี product |
| tiktok_pending/ignored | ไม่มีหลักฐานบัญชีต้นทาง | ทุกแถว (ตอนนี้ 0) |
| GadgetMedia campaigns/projects | **explicit assignment เท่านั้น** — P3 model เก็บ `channel_id` แล้ว; ไม่ derive จาก account_role/สินค้า/main cohort | ownerless legacy คง unknown; linked campaign/slot/project ต้องมีเจ้าของเดียวกัน |

- angle/batch ภายในสินค้าไม่ได้ stamp (สืบทอดจากสินค้าตาม ADR §12.1)
- แถวที่มี `channel_id` อยู่แล้วไม่ถูกแตะ; ถ้าขัดกับ parent หรือไม่อยู่ใน registry = conflict (รายงาน ไม่แก้)
- Gadget follow-up · ดำเนินการโดย: Codex (GPT-6): ใช้ `--assign` ระบุ store `gadget_media_campaigns` + campaign_id หรือ `gadget_media_projects` + canonical project directory ID ทีละรายการ เจ้าของต้องมีใน registry และไม่ archived; ถ้ามี linked campaign/slot/project ต้อง assign ให้ครบและตรงช่อง หรือมี owner เดิมตรงกัน ห้ามเดาจาก account_role/brand/model/ProductStore และห้ามเขียน JSON production ตรงเพื่อหลบเครื่องมือ
- Gadget project รองรับเฉพาะ canonical `03_Projects/GadgetMedia/<project_id>/project.json` ที่ scoped repository เปิดได้; recursive inventory ตรวจพบ nested/duplicate IDs แต่ assignment จะถูกปฏิเสธ (ไม่มีการย้ายโฟลเดอร์อัตโนมัติ) ช่องรองที่อ้าง legacy generated export/cover ต้องมี verified export_registry/channel_artifacts owner ตรงกันก่อน; frozen channel identity หรือ materialized mirror ที่ขัดแย้งต้องแก้ด้วยแผนแยก ห้าม stamp ให้ดูเหมือนเสร็จทั้งที่เปิดไม่ได้
- Gadget apply แก้เฉพาะ `channel_id` ใน raw campaign/project และ product.json/project_index records ที่มีอยู่ เก็บ unknown fields, status, timestamps, approved master, metrics, styles, identity snapshots และ stage/artifact bytes; ไม่เรียก model save/materialize และไม่สร้าง optional mirrors ที่หาย Snapshot/journal เก็บ exact paths/hashes; resume ทน partial-file crash, rollback คืน missing/null owner เดิมและเก็บ edits/records ใหม่
- แผน production ที่ apply รอบ `20261011T004927-850bab` ยังไม่ได้ migrate legacy Gadget campaign `gadget-media-ebbb8c0304` (21 slots; zero Gadget project/actions) การรองรับในเครื่องมือใหม่นี้ **ไม่ได้หมายความว่า production assignment ถูกทำแล้ว** ต้องมี plan review/authorization ของรอบ production แยกก่อน apply
- unknown/conflict **คง legacy ไว้** (compat เห็นเป็น main, strict มองไม่เห็น) จนเจ้าของระบุ `--assign` รายแถว — ไม่มีการเหมารวมเป็น main
- ไม่แตะ: `00_Inbox/ 01_Raw/ 02_Assets/`, `04_Exports/`, `05_Covers_Thumbnails/`, CapCut drafts, ไฟล์อื่นในโฟลเดอร์โปรเจกต์, `_HyperFrames_Studio/`, `03_Projects/omnicut.db`, `_json_mirror_state` แถวของเครื่องอื่น; ไม่ย้าย/เปลี่ยนชื่อไฟล์ใด ๆ
- project.json แก้แบบ **แทรกบรรทัด `"channel_id": "main",` บรรทัดเดียว** (byte อื่นเหมือนเดิม, รักษา CRLF/BOM) เขียน temp+fsync+replace; ไม่สร้าง `.bak`; journal เก็บ sha256 ก่อน/หลัง (revision ของ editor จะเปลี่ยน → client ที่เปิดค้างได้ 409 ต้องโหลดใหม่)

## 2. ความปลอดภัยที่ฝังใน tool

| กลไก | รายละเอียด |
|---|---|
| dry-run เป็นค่าเริ่มต้น | เปิด SQLite แบบ `mode=ro` (ไม่มี `-wal` → `immutable=1` จึงไม่สร้างไฟล์ใด ๆ); ไม่เขียนอะไรนอกจากไฟล์รายงานที่สั่ง `--report` |
| `--expect-plan` | apply ต้องได้ plan_hash ตรงกับ dry-run ที่ตรวจแล้ว (ข้อมูล/การตัดสินใจเปลี่ยน = ปฏิเสธ) |
| preflight (blocker) | integrity_check ทั้ง 2 DB, mirror ที่กำลังจะถูก auto-import ต้องเท่ากับ DB, registry มี `main`, ไม่มี lock/รอบค้าง, ไม่มี task/batch ที่ยังวิ่ง, พื้นที่ดิสก์ ≥ 2× snapshot + 64MB, API server `127.0.0.1:8000` ต้องปิด (ตรวจเมื่อ root = โปรเจกต์จริง) |
| preflight (warning) | recording session ที่เปิดอยู่, คิว `ready_for_extension` (ปิด extension ก่อน), unknown/conflict |
| maintenance lock | `_Docs/.maintenance.lock` (owner/pid/host/reason/run_id/started_at/token) — ระหว่างนั้น DocumentTable ทุกตัวปฏิเสธการเขียน (`MaintenanceModeError`, 0 แถว), ข้าม JSON auto-import, API ตอบ 503 `maintenance_mode` กับ non-GET, `TaskManager.create_task` / batch create/dispatch/recovery ไม่เริ่มงานใหม่; อ่านได้ปกติ; tool เขียนผ่าน token ของตัวเอง |
| snapshot ก่อน apply | `06_Archive/Migrations/multi_channel_v1/<run_id>/snapshot/` — `store.db` + `batch_render_queue.db` ผ่าน SQLite online-backup API (WAL-consistent) + JSON mirrors, `channels.json`, `task_registry.json`, `gadget_media_campaigns.json`, `_Docs/gadget_media/`, `03_Projects/GadgetMedia/**/*.json`, project.json ทุกไฟล์ + `manifest.json` (sha256 ต่อไฟล์ + count/ids/rows digest ต่อตาราง) |
| เขียนผ่าน store layer | หนึ่ง transaction ต่อ store ผ่าน `DocumentTable.mutate()` → DB, JSON mirror และ `_json_mirror_state` ไปด้วยกัน; ไม่แก้ mirror ตรง; ก่อนทุกขั้นตรวจว่า mirror จะไม่ถูก import ทับ DB |
| journal | `<run_id>/journal.jsonl` (fsync ทุกบรรทัด): start/done ต่อขั้น + ทุกแถว `before_hash`/`after_hash`/`added` + manifest ต่อไฟล์; `plan.json`, `state.json`, `../current.json` |
| validation | id/จำนวนครบ, เปลี่ยนเฉพาะฟิลด์ที่วางแผน (เทียบกับ snapshot), child ตรง parent, mirror == DB ทีละ id, integrity_check, post-apply fingerprint |
| idempotent | apply รอบสอง = `noop` 0 writes (ไฟล์ byte เดิม ไม่สร้าง lock/snapshot) |
| fail closed | ล้มก่อนเขียนข้อมูล → ปลด lock (`failed_clean`); ล้มหลังเริ่มเขียน → **คง lock** (`needs_attention`) จนกว่าจะ `--resume`/`--rollback`; process ตาย → lock ค้าง (stale) ยังบล็อก writer |
| จำกัดที่เขียน | ทุกไฟล์ต้องอยู่ใต้ `--root` (ยกเว้น path รายงาน/ซ้อม restore ที่สั่งเอง) — มีเทส audit hook |

## 3. ใครตัดสินอะไร

| เรื่อง | ผู้ตัดสิน |
|---|---|
| รายการ unknown/conflict ใน dry-run (ยืนยันเจ้าของ, หรือสั่งลบขยะเทสผ่านเครื่องมือของ store แยกต่างหาก) | **เจ้าของช่อง** → เขียนไฟล์ `--assign` |
| เปิด `--rename-templates` | เมื่อโค้ดคิว/เทมเพลต (P2.2/P5) อ่าน id แบบ `<channel>:…` แล้วเท่านั้น (ถ้าเปลี่ยนก่อน UI จะหา template เดิมไม่เจอ) |
| `--legacy-owner` (เมื่อ registry มีช่องอื่นก่อน migrate) | เจ้าของช่อง |
| วันเวลา apply / หยุดระบบ | เจ้าของ + ผู้ดูแล cutover (P8) |
| rollback vs restore snapshot | ผู้ดูแล cutover ตามข้อ 8 |

ไฟล์ `--assign` (รายแถวเท่านั้น):

```json
{"schema": "omnicut.channel_assign.v1",
 "assignments": [
   {"store": "posts", "id": "<post id>", "channel_id": "main", "note": "ตรวจบน TikTok แล้ว"},
   {"store": "manifests", "id": "<ชื่อโฟลเดอร์โปรเจกต์>", "channel_id": "main"}
 ]}
```
store ที่ใช้ได้: `products export_registry posts schedule_queue schedule_templates shot_lists recording_sessions tiktok_pending tiktok_ignored batch_render_queue task_registry manifests` · ช่องต้องอยู่ใน registry และไม่ archived · ห้ามขัดกับหลักฐาน/parent · id ที่ไม่มีจริง = error ทั้งไฟล์

## 4. ขั้นตอน (PowerShell ที่รากโปรเจกต์)

```powershell
# 0) ตรวจสถานะ
& .venv\Scripts\python.exe tools\migrate_channels.py --status

# 1) หยุดผู้เขียนทุกตัว: ปิด API server (start_app.bat / uvicorn), ปิด Chrome extension TikTok autopost,
#    รอ/ยกเลิก render, batch, task ให้จบ; ปิด mobile recording; ไม่รัน tools/clean_products_data.py ฯลฯ

# 2) dry-run + รายงาน (อ่านอย่างเดียว)
& .venv\Scripts\python.exe tools\migrate_channels.py --report _Docs\Reports\MULTI_CHANNEL_MIGRATION_DRYRUN_<วันที่>
#    ตรวจ: preflight blockers = 0, ตาราง unknown/conflict, ชุดที่จะเขียน, plan_hash

# 3) เจ้าของตัดสินรายการ → (ถ้ามี) เขียน assign.json แล้ว dry-run ซ้ำด้วย --assign assign.json จนรายงานถูกต้อง

# 4) ซ้อม backup/restore ลงโฟลเดอร์ว่างนอกโปรเจกต์ (อ่าน root อย่างเดียว)
& .venv\Scripts\python.exe tools\migrate_channels.py --rehearse-restore D:\OmniCut_restore_rehearsal_<วันที่>
#    ต้องได้ "ok": true (sha256 ทุกไฟล์, integrity_check, count/ids/rows ต่อตาราง, เปิดผ่าน DocumentTable ได้)

# 5) backup ทั้งระบบตามปกติด้วย (หน้า Backup) — apply ทำ snapshot ของตัวเองอีกชั้น

# 6) apply ด้วย plan_hash ที่ตรวจแล้ว (ต้องใช้ตัวเลือกเดียวกับ dry-run ทุกตัว เช่น --assign/--rename-templates)
& .venv\Scripts\python.exe tools\migrate_channels.py --apply --expect-plan <plan_hash> [--assign assign.json]

# 7) ยืนยัน: dry-run อีกรอบต้อง "แถวที่จะเขียน: 0" ; --status = applied ; ไม่มี _Docs\.maintenance.lock
# 8) เปิด API server ใหม่ (cache ในหน่วยความจำ เช่น path_index/task registry ต้องโหลดใหม่)
```

Exit code: 0 สำเร็จ · 1 ผิดพลาด · 2 ถูกบล็อก/ข้อมูลเข้าไม่ถูกต้อง · 3 ข้อมูลเปลี่ยนระหว่างทาง/ตรวจผลไม่ผ่าน

## 5. อะไรบล็อก apply

- preflight blocker ใด ๆ (ข้อ 2) — แก้ต้นเหตุแล้ว dry-run ใหม่
- plan_hash ไม่ตรง (ข้อมูลเปลี่ยนหลังตรวจรายงาน หรือใช้ตัวเลือกไม่ตรงกัน)
- ไฟล์ `--assign` ผิด (store/id/ช่อง/ขัดหลักฐาน)
- **unknown/conflict ไม่บล็อก** apply — แถวเหล่านั้นถูกข้ามและคง legacy แต่ **นโยบายโครงการ (แผน §11)** คือเจ้าของต้องตรวจรายการก่อน apply จริง และก่อนเปิด strict mode (P8) ต้องเหลือ unknown เท่าที่เจ้าของยอมรับว่ามองไม่เห็นใน strict
- ข้อมูลเปลี่ยนระหว่าง apply (`DriftError`, exit 3) — store นั้น rollback ทั้ง transaction; ถ้ามี store ก่อนหน้าเขียนแล้ว lock ยังคงอยู่ → `--resume` หรือ `--rollback`

## 6. Resume (process ตาย/ไฟดับ/ล้มกลางทาง)

```powershell
& .venv\Scripts\python.exe tools\migrate_channels.py --status
& .venv\Scripts\python.exe tools\migrate_channels.py --resume
```
ทำต่อจาก `plan.json` เดิม (ไม่คำนวณแผนใหม่), ใช้ token เดิมรับ lock คืน, ข้ามขั้นที่ done, ขั้นที่ start ค้างรันซ้ำแบบ idempotent (แถวที่ทำแล้วตรวจ hash แล้วข้าม), ซ่อม JSON mirror ที่ค้างจากการตายระหว่าง commit กับเขียน mirror แล้ว validate ใหม่ — เทสครอบ crash 20 จุด

## 7. Rollback

```powershell
& .venv\Scripts\python.exe tools\migrate_channels.py --rollback
```
ย้อนตาม journal: ถอดเฉพาะฟิลด์ที่ migration เพิ่ม (`channel_id`, และ `legacy_id` + คืน id template) — แถวที่ไม่ถูกแก้หลัง cutover กลับเป็นเดิมทุก byte (mirror/project.json/task_registry ทดสอบแล้ว byte-identical), แถว/ไฟล์ที่ถูกแก้หลัง cutover **เก็บการแก้ใหม่ไว้** และถอดแค่ฟิลด์ของ migration, แถวที่สร้างหลัง cutover ไม่ถูกแตะ, แถวที่ channel_id ถูกเปลี่ยนเป็นค่าอื่นจะถูกข้ามและรายงาน

`--restore-snapshot` (คืนทั้งชุดจาก snapshot) ใช้ได้ **เฉพาะ** รอบที่ applied และข้อมูลปัจจุบันยังเท่ากับ post-apply fingerprint (ไม่มีงานใหม่) — ไม่งั้นปฏิเสธและให้ใช้ `--rollback`; คืน DB ด้วย backup API (ไม่ copy ทับไฟล์ WAL)

`--release-stale-lock` ปลด lock ที่ process เจ้าของตายแล้วเท่านั้น และปฏิเสธถ้าเป็น lock ของรอบที่ค้าง (ต้อง resume/rollback)

## 8. Contract สำหรับเฟสถัดไป (ไม่แก้ ADR — P2.2 เป็นผู้เพิ่ม §13)

- หลัง apply: legacy rows ที่เหลือ = รายการ unknown ในรายงานเท่านั้น; ทุก writer ต้อง **คงฟิลด์ `channel_id`** ตอนเขียน record เดิม (P3 ต้องตรวจ writer ที่สร้าง dict ใหม่ทั้งก้อน เช่น shot_lists upsert, `BatchRenderManager._persist_batch` ของ batch ในหน่วยความจำที่โหลดก่อน migrate, `CampaignStore`/`GadgetMediaRepository` dataclass)
- template id ใหม่ `<channel>:default` / `<channel>:week:<YYYY-MM-DD>` + `legacy_id`; โค้ดอ่านต้องรองรับก่อนเปิด `--rename-templates`
- `scripts/maintenance_lock.py`: `assert_writable(root)`, `refuse_new_job(root)`, `is_blocked(root)`, `bypass(token)`, `install_maintenance_gate(app)`; lock root ของ DB = `db_path.parent.parent`
- ProductStore `reconcile_existing_projects()` ที่ถูกเรียกจาก GET จะได้ 503 ถ้ามีอะไรต้อง reconcile ระหว่าง maintenance (อ่านอย่างเดียวไม่มีปัญหา) — แนะนำให้ P3 ข้าม reconcile เมื่อ `maintenance_lock.is_blocked()`
- `TaskManager` ถือ task ในหน่วยความจำและเขียนทั้งไฟล์ทับ → **ต้องปิด server ก่อน apply** (preflight ตรวจพอร์ต 8000); ไม่งั้น `channel_id` ใน `task_registry.json` อาจถูกเขียนทับ

## 9. ช่องว่างของ `scripts/backup_engine.py` (P6 รับไปแก้ — รอบนี้ไม่แก้)

- `03_Projects/batch_render_queue.db` ถูก zip แบบไฟล์ดิบ (ไม่ใช่ backup API) + `-wal/-shm` แยก → ไม่ WAL-consistent (ใช้ `channel_migration.sqlite_online_backup()` ได้)
- ไม่เก็บโฟลเดอร์ย่อยของ `_Docs` (`_Docs/gadget_media/`), dotfiles ใน `03_Projects` (`.run_started.json`), `02_Assets/Refs/playbook_notes.json` + ref media, `02_Assets/asset_registry.json`/`asset_metadata.json`/`Templates/*`, `06_Archive/Migrations/` (journal/snapshot ของ migration)
- `backup_manifest.json` ไม่มี sha256/จำนวนแถวต่อตาราง และ **ไม่มี restore routine** — ใช้ `create_snapshot()` / `restore_snapshot()` / `verify_restore()` / `rehearse_restore()` ใน `scripts/channel_migration.py` เป็นต้นแบบ
