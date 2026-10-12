# แผนระบบหลายช่อง TikTok ใน OmniCut — ฉบับทบทวน v3

- **ผู้จัดทำเดิม:** Claude Code (Claude Sonnet 5.5)
- **ทบทวนและออกแบบใหม่โดย:** Codex (GPT-6)
- **วันที่:** 2026-10-10; ตรวจ implementation ล่าสุด 2026-10-11
- **สถานะ:** P0–P8 มี implementation แล้ว; offline gates backend3686/frontend989/build/extension49ผ่าน; production owner migration9สำเร็จรวมcampaign1/21slots และAPIเปิดกลับแล้ว ยังรอ live account/selector และ cleanup exceptions ตามรายงาน
- **ขอบเขต:** แอปเดียวรองรับหลายช่อง แยกข้อมูล งานผลิต ตัวตนคลิป คิวโพสต์ และผลวิเคราะห์ครบวงจร
- **วิธีตรวจ:** ไล่ caller/store/worker/extension จริง พร้อม deterministic tests, Chromium UI และ FFmpeg parity ใน temporary roots; offline audit อ่านproductionอย่างเดียว ส่วน cutover follow-up ได้รับอนุญาตหยุดAPI/backup/apply9/validate/restartแล้ว ไม่โพสต์/commit; ดู [รายงาน audit](../Reports/CODEX_GEMINI_MULTI_CHANNEL_AUDIT_20261011.md) และ [ผล cutover](../Reports/CODEX_MULTI_CHANNEL_CUTOVER_READINESS_20261011.md)

## สถานะรับช่วงและลำดับปิดงาน

ดำเนินการโดย: Codex (GPT-6) + delegated Codex (GPT-6)

1. P3/P6: ownership guards, media carriers, lifecycle, nested discovery, consistent SQLite backup และ restore fingerprint แก้แล้ว; explicit Gadget migration เพิ่ม guard ให้ indexed artifact และ enclosing project owner ไม่ขัดกัน (dedicated25/related124/full3686 passed); cutover follow-up apply9สำเร็จรวมcampaignเก่าเป็นmain run20261011T135342-0a925b
2. P4: identity snapshot ของ Preview/render/Gadget/HyperFrames แก้และตรวจ actual Canvas/FFmpeg แล้ว; ไม่เปลี่ยน font/text geometry
3. P5: account guard, fresh confirmation, lease release, durable receipt repair และ transaction fence ต่อ export ใหม่แก้แล้ว; การตรวจบัญชีจริงและ selector ของ TikTok ยังเป็น cutover gate
4. P7: profile/selector/editor/mobile/autosave/cache และ invalid-link recovery แก้แล้ว; manual-draft coverage ของ Schedule/Producer/HyperFrames/Tracker/CoverStudio ตรวจ actual browser รวม save failure/pending/switch-back/reload guard แล้ว; frontend 989 passed/build ผ่าน ไม่อ้างทุก two-tab combination
5. P8: final full backend บนไฟล์คงที่ผ่าน 3686 ข้อ/skip13/warning62; frontend989, extension49, build และ actual parity gates ผ่านตามรายงาน AC01–AC17. ไม่อ้างทุก live/two-tab scenario และไม่บวก targeted gates ซ้ำเป็นยอด full
6. README/ARCHITECTURE/protocol และรายงานอัปเดตแล้ว; ปิดรอบ audit ใน TODO/HISTORY พร้อมผลจริง แต่คง cutover/legacy-owner/cleanup follow-ups. Automatic review ปฏิเสธ Temp cleanup เดิม จึงไม่อ้าง cleanup100%

## 1. เป้าหมายและขอบเขต

ผู้ใช้เลือกช่อง A แล้วเห็นและจัดการงานของ A ได้ตั้งแต่สินค้า → สคริปต์ → ถ่ายทำ → ตัดต่อ → เรนเดอร์ → ปก → จัดคิว → โพสต์ → สถิติ โดยการสลับไป B ไม่เปลี่ยนเจ้าของงานที่เริ่มไว้ และไม่มีคำสั่งใดแก้ข้อมูลของอีกช่องโดยไม่ตั้งใจ

ข้อมูลที่รับต่อจากแผนเดิม:
- ช่องหลัก `main`: ชื่อ `rizannTry`, handle `@rizanntry`, เนื้อหาไอที/แกดเจ็ต
- ช่องรอง: สินค้าทั่วไป; มีไฟล์รูปเตรียมไว้ แต่ชื่อ/handle/ข้อความลายน้ำยังไม่ยืนยัน
- เสียงพากย์ใช้ Fenrir + `commercial_premium` ร่วมกัน; โพสต์ด้วยบัญชี TikTok คนละบัญชี
- โครงสร้างรองรับ N ช่องตั้งแต่ต้น; จำนวนช่องจริงไม่จำเป็นต้องทราบก่อนพัฒนา foundation

ใช้แอปและ engine เดิมร่วมกัน เพิ่ม ownership และการตรวจ scope ที่ storage/service/API ไม่ต้องก๊อปโปรเจกต์ทั้งก้อนหรือแยก AI provider เพื่อแยกช่อง การแยก Chrome profile เป็นตัวช่วยใช้งานและต้องมีการตรวจบัญชีจริงร่วมด้วย

ขอบเขตนี้ไม่เพิ่มระบบผู้ใช้หลายคนหรือ tenant security เต็มรูปแบบ และไม่เปลี่ยนฟอนต์ ขนาด ขอบ ตำแหน่ง subtitle หรือ safe zone งาน multi-channel เปลี่ยนข้อมูลตัวตนช่องผ่าน contract เดิมเท่านั้น

## 2. ผลตรวจแผนเดิม: ต้องออกแบบเพิ่มก่อนลงมือ

ลำดับความสำคัญ: **Blocker** = อาจข้อมูลสูญหายหรือโพสต์ผิดบัญชี; **Major** = แยกช่องไม่ครบหรือย้อนหลังผิดความจริง

| ระดับ | ช่องว่างและผลกระทบ | หลักฐานจากโค้ดที่อ่าน | ข้อแก้ในแผนนี้ |
|---|---|---|---|
| Blocker | กรองข้อมูล A แล้ว `_save(A)` อาจลบ B เพราะ store แทนที่ทั้งตาราง | `scripts/db.py:345` ใช้ DELETE ทั้งตารางก่อน INSERT | scoped mutation บน snapshot เต็ม + test ว่า B ไม่เปลี่ยน |
| Blocker | สินค้า URL เดียวกันถูกนำไปแก้ record เดิมและอาจทับ angles ของอีกช่อง | `scripts/product_store.py:391` ตรวจ URL ทุกสินค้า | dedup ตาม (channel_id, URL); การคัดลอกข้ามช่องเป็น workflow ชัดเจน |
| Blocker | pending job กลางถูกแทนที่/เคลียร์ข้ามงานได้ ไม่มีเจ้าของช่องหรือ job identity | `scripts/api_tiktok_autopost.py:235`, `scripts/api_tiktok_autopost.py:292` | durable job, claim/lease, job-scoped clear/result, idempotency |
| Blocker | ปุ่มโพสต์ทำงานโดยไม่มีการตรวจบัญชีที่ตรงกับงาน | `tiktok_autopost_extension/background.js:1725` → `clickPostButton` | ตรวจบัญชีก่อน upload และก่อน publish/schedule ทุกเส้นทาง |
| Major | ข้อมูลไม่ได้อยู่ใน SQLite mirror ทั้งหมด | `scripts/gadget_media_repository.py:22`, `scripts/api_producer.py:34`, `scripts/task_manager.py:376` | migration ครอบ manifest/index, notes, task registry และ JSON store |
| Major | templates และเวลา occupied เป็นส่วนกลาง ทำให้เวลาเดียวกันต่างช่องชนกัน | `scripts/api_schedule_queue.py:252`, `scripts/api_schedule_queue.py:363`, `scripts/api_schedule_queue.py:444` | template key/slot/constraints แยก channel |
| Major | stats import ไม่มีข้อมูลบัญชี และ candidates รวมทุกช่อง | `scripts/api_tiktok_stats.py:41`, `scripts/api_tiktok_stats.py:179` | source account + channel scope ก่อน fuzzy match |
| Major | post idempotency fallback จับคู่ด้วย basename ซึ่งชนข้ามช่องได้ | `scripts/post_log.py:252` | channel + export identity; legacy fallback เฉพาะช่องและต้องไม่กำกวม |
| Major | เพิ่มโฟลเดอร์ย่อยอย่างเดียวแล้ว Gallery มองไม่เห็นและ Posted ยังรวมชื่อไฟล์ | `scripts/api_exports.py:234`, `scripts/api_exports.py:919` | ปรับ discovery, Posted, cover companions, registry และ repair พร้อมกัน |
| Major | HyperFrames API ไม่รับ/ส่ง channel และเดาสินค้าจากชื่อ composition | `scripts/api_hyperframes.py:49`, `scripts/api_hyperframes.py:310`, `scripts/api_hyperframes.py:389` | metadata ที่ชัดเจน + create/render/register ตรวจ ownership |
| Major | HyperFrames ลายน้ำอ่าน config สด; channel หายเพียงเตือน จึงไม่ใช่ render gate | `03_Projects/_HyperFrames_Studio/kit/kit.js:61` | identity snapshot + validation ก่อน render; unknown channel ต้องหยุด |
| Major | localStorage และ task cache ใช้ key กลาง สลับช่องแล้วอาจแสดง/บันทึกงานเก่า | `frontend/src/App.jsx:173`, `frontend/src/context/TaskContext.jsx:135`, `frontend/src/components/editor/EditorShell.jsx:224` | namespace cache, ป้องกัน response เก่า และ unsaved-change flow |

ไม่ใช้จำนวน record/ไฟล์จากแผนเดิมเป็น baseline เพราะยังไม่ได้วัดซ้ำในรอบนี้ ก่อน migration ต้องเก็บ inventory ใหม่แบบ read-only คำกล่าวว่า “ไม่มี channel/account เลย” ให้เปลี่ยนเป็น “ยังไม่มี channel ownership contract”; โค้ดมีคำเหล่านี้ในบริบทอื่นแล้ว

**ข้อสรุป:** คงทิศทางแอปเดียวของแผนเดิม แต่เปลี่ยนจากการเพิ่มฟิลด์และตัวกรองเป็นการบังคับ ownership ตลอดเส้นทาง

## 3. กติกาที่ระบบต้องรักษา

1. ทุก record ของงานช่องต้องมี `channel_id` ที่ลงทะเบียน และ record ลูกต้องตรงกับเจ้าของ parent; request/client ไม่สามารถเปลี่ยนเจ้าของด้วยการส่งค่าทับ
2. เมื่อเปิด multi-channel mode แล้ว request ที่ต้องมี scope แต่ไม่มี/ไม่รู้จักช่องต้องถูกปฏิเสธ ไม่ fallback ไป main เงียบ ๆ
3. legacy fallback ไป main ใช้ได้เฉพาะข้อมูลที่ตรวจและจัดอยู่ใน migration cohort แล้ว ไม่ใช้กับข้อมูลใหม่หรือไฟล์ที่ยังไม่ทราบเจ้าของ
4. resource ID ของช่อง B ที่ส่งมาใน scope A ต้องไม่อ่าน/แก้ได้ แม้ path อยู่ในโฟลเดอร์ที่อนุญาต; shared asset ต้องผ่านการอ้างอิงที่อนุญาตด้วย
5. mutation ของ A ต้องรักษา records และ revision ของ B; bulk requests ตรวจครบทุก item ก่อนเขียน ไม่สำเร็จบางส่วนโดยไม่มีรายงาน
6. render/job/export/post ตรึง `channel_id` ตอนสร้างงาน; Active Channel ของ UI ไม่เปลี่ยนงานที่กำลังทำ
7. ตัวตนช่องที่ใช้ผลิตเก็บ snapshot และ revision/hash; แก้ profile ไม่เปลี่ยน MP4 หรือประวัติของคลิปเดิม การเปลี่ยนตัวตนสร้าง project/render revision ใหม่
8. ก่อนทำงานใน TikTok ต้องรู้ว่าบัญชีจริงตรงกับ target; อ่านไม่ได้/ไม่ตรง/หมด lease ให้หยุด พร้อมสาเหตุภาษาไทย
9. เก็บข้อมูลบัญชีเป้าหมายและบัญชีที่ตรวจพบแยกกันใน audit; ไม่ถือค่าใน request หรือ profile binding เป็นหลักฐานว่าล็อกอินบัญชีนั้น
10. เวลาโพสต์เก็บ timezone ชัดเจน (`Asia/Bangkok` เป็นค่าเดิม); constraints แยกช่องแต่ใช้งาน extension แบบทีละ job ได้
11. ไม่สร้างสำเนา Raw/Assets เพียงเพื่อแยกช่อง; SHA-256 และข้อมูลรุ่นสินค้ากำกับการใช้ซ้ำ พร้อมสิทธิ์แหล่งที่มา
12. clip เสร็จ/posted ต้องเป็นสถานะจาก artifact/ผลโพสต์จริง; scheduled acceptance ไม่เท่ากับโพสต์เผยแพร่แล้ว

## 4. Data contract และ ownership

### 4.1 Channel registry

แหล่งกำหนด profile เดียว: `_Docs/channels.json` ผ่าน service ที่ validate, เขียน atomic และตรวจ expected revision ไม่ให้หลาย agent/UI ทับกัน; ไฟล์ที่ sync ไป kit เป็น derived output

ฟิลด์ขั้นต่ำ:
- `schema_version`, `revision`
- แต่ละช่อง: `id` (slug คงที่), `display_name`, `handle`, `watermark_text`, `avatar_asset_path`, `follow_title`, `timezone`, `status`
- `status`: `draft` / `active` / `archived`; ช่อง draft เปิดให้ตั้งค่าได้แต่ยังสร้าง final export หรือเตรียมโพสต์ไม่ได้
- `posting_enabled` เปิดได้เมื่อชื่อ/handle/ตัวตนและ account binding พร้อม; registry ไม่เก็บ cookie, API key หรือข้อมูลล็อกอิน
- AI/TTS/BGM ใช้ค่า global เดิม โดย reserve override ต่อช่องสำหรับอนาคต; ไม่ต้องเพิ่ม provider/key แยกช่องใน MVP
- normalize handle ด้วยกฎเดียวทั้ง Python/JS; ไม่เทียบ display name; handle ซ้ำระหว่างช่อง active ต้องถูกปฏิเสธ
- id เปลี่ยนไม่ได้; archive ไม่ลบประวัติ และหยุด job ใหม่/การ claim โดยเก็บผลเก่าให้อ่านได้

ไฟล์ใหม่ที่เสนอ: `scripts/channel_store.py`, `scripts/channel_scope.py`, `scripts/api_channels.py`, `tools/sync_channels.py` (ยังไม่มีในรอบนี้)

### 4.2 ตารางข้อมูลและวิธีแยก

| กลุ่ม | เจ้าของและ key | การแก้ไขที่ต้องทำ |
|---|---|---|
| Products + angles + batches | product มี channel; angles/batches สืบทอดและตรวจตรงกัน | get/add/update/delete/reconcile, URL dedup, code generation, import/export |
| ProjectManifest + editor document | channel + project identity + identity snapshot | load/save/autosave/reroll, revision, artifact fingerprint และ cache reuse |
| Render/Batch/Task/recording/shot lists | บันทึก channel ตอนสร้าง; ตรวจ parent ก่อนทุก action | worker, retry/cancel, upload/finalize, progress/result และ deep link |
| ExportRegistry + thumbnails/covers | channel + stable export_id; path เป็นข้อมูลตำแหน่ง | latest_for_angle/find_by_path/path_index/ensure/link/move/delete |
| Schedule queue/templates | channel + slot time; template id เช่น `main:default`, `main:week:2026-10-12` | default/override/copy/reset/auto-fill, daily rules, preview/commit revision |
| Posting jobs + PostLog | channel + job_id/export_id; platform account snapshot | lease, result, idempotency, repair, scheduled/published outcome |
| TikTok stats/pending/ignored/latest-sync | source channel/account + video_id | candidates/fuzzy/manual attach/ignore/restore scoped; เก็บ sync แยกช่อง |
| Analytics/producer missions/notes/refs | channel สำหรับข้อมูลเนื้อหา; global เฉพาะข้อมูลระบบ | Production/Performance/Inventory, notes/ideas และ feedback loop |
| Gadget Media | channel ใน campaign/slot/product project/model/index/master | API/repository/timeline/render/quality ใช้ engine ร่วมและคง workspace_scope |
| HyperFrames | channel + composition_id + linked product/angle + snapshot | metadata, list/create/render, voiceover lookup, export bridge |
| Media libraries/config/system health | ฟอนต์/เพลง/SFX/LUT/model/provider ใช้ร่วมกัน | asset attachment/rights/product model ตรวจ scope; ไม่ duplicate ไฟล์ |
| Backup/restore/storage maintenance | งานระบบ global ที่แสดงขอบเขตชัดเจน | รวม channel/config/manifests/index/job state; destructive actions คงกฎ confirmation |

producer note/ref ที่ผู้ใช้ตั้งใจใช้ร่วมต้องมี `scope=shared` ชัดเจน; ไม่เหมาว่าทุกรายการเป็น shared ส่วน Tokens/Storage/System Health เป็น global view ใน MVP ห้ามแสดงตัวเลข global เป็นผลของช่องที่เลือก หากเพิ่ม usage attribution ภายหลังให้บันทึก channel ตั้งแต่สร้าง task และยังมี global total

### 4.3 สินค้ารุ่นเดียวหลายช่อง

ค่าเสนอ: สร้าง product work item คนละ record/angles/status ต่อช่อง และอ้าง raw/spec/rights ด้วย asset identity เดิม เพิ่ม `canonical_product_key` หรือ `source_product_id` เพื่อระบุรุ่นเดียวกัน; รักษา product IDs และ codes ไม่ให้ชนใน global integrations

ห้ามย้าย `channel_id` ของ product ที่มี project/export/queue/post แล้วด้วย PATCH ทั่วไป หากผู้ใช้อนุญาตสินค้าร่วม ให้ใช้ explicit clone สคริปต์ใหม่และไม่คัดลอก status, export หรือคิว พร้อมตรวจว่าไม่ใช้ final clip ซ้ำ นโยบายอนุญาตสินค้าร่วมยังรอยืนยัน (§11); ไม่เปิด workflow นี้โดยปริยาย

### 4.4 วิธีเขียน storage

`DocumentTable.save()` มี contract แทนที่ทั้งตาราง จึงไม่เปลี่ยน `_load()` ให้คืนเฉพาะช่องแล้วใช้ `_save()` เดิม สร้าง scoped service ที่:
- เปิด transaction/snapshot เต็มผ่าน `_mutate()`, หา record ด้วย id + channel, เปลี่ยนเฉพาะ record ที่ผ่าน guard
- แยก internal full-load ออกจาก scoped public reads; inventory ทุก call site ที่เข้าถึง `_load/_save` ตรง
- batch validation และการตรวจ expected revision อยู่ใน transaction เดียวกับ mutation
- ไม่ซ้อน `_mutate()` หลาย store ใน connection เดียว; ใช้ cross-store coordinator หรือ staged recovery ที่มี journal/idempotency
- แก้ scope ใน JSON blobs ได้โดยยังคง schema เดิมในระยะแรก; ประเมิน shadow column/index เมื่อวัด performance แล้ว ไม่ประกาศว่าการเพิ่มฟิลด์ไม่มีงาน storage อื่น
- หา records ของอีกช่องต้องให้ผล 404; ความขัดแย้งของ record ที่อ่านได้แล้วใช้ 409; missing/invalid scope ใช้ 422 พร้อมข้อความไทย

## 5. API และ frontend flow

### 5.1 API contract

ใช้ `X-OmniCut-Channel` เป็น request scope สำหรับ route ของงานช่อง โดย client wrapper รับ scope แบบ explicit; route ระบบ/shared ไม่บังคับช่อง `channel_id` ใน response/payload ที่อ้างงานต้องตรง header และ parent เสมอ header เป็น routing context ไม่ใช่ authentication

endpoint ตาม ID, upload multipart, media preview/download, thumbnail, task poll/cancel, bulk actions และ deep links ต้องผ่าน guard ด้วย ไม่ใช้เพียงตัวกรอง list สินค้า/คลิป ส่วน compatibility สำหรับ client เก่ารองรับเฉพาะ main ในช่วง single-channel mode ที่ยังไม่เปิดช่องรอง หลังเปิดโหมดหลายช่องให้ reject client ที่ไม่ส่ง scope พร้อมข้อความให้อัปเดต

สร้าง route matrix ใน P0: method/path → global/shared/channel → parents → reader/writer → caller (desktop/mobile/extension/CLI) → gate ครอบทุก router ที่อยู่จริง รวม api_hyperframes; ไม่ใช้จำนวน router ใน ARCHITECTURE ที่เก่าแล้วเป็นข้อยืนยันความครบ

### 5.2 ช่องที่ใช้งานอยู่

- `ChannelProvider` กลางใน App; user เลือกช่องก่อนสร้างสินค้า/project/job และเห็นชื่อช่องที่หัวหน้าและจุดสร้างงาน
- สลับช่อง: จัดการ unsaved editor changes ด้วยบันทึก/ละทิ้ง/ยกเลิก แล้ว abort requests, clear selections/modals, โหลดรายการของช่องใหม่
- request เก็บ scope ณ ตอนส่ง + channel generation; response ของ A ที่กลับหลังเปลี่ยนเป็น B ต้องไม่ทับ state ของ B
- namespace active product/angle/editor draft/project/task cache ต่อช่อง; cache เดิมย้ายเข้าช่อง main ครั้งเดียว
- multi-tab ใช้ active channel ต่อ tab (`sessionStorage`); remembered default ใช้ global preference ได้ แต่ไม่ส่ง event ไปเปลี่ยนอีก tab กลางงาน
- deep link มี channel + resource ID; backend ตรวจ resource ทุกครั้ง การเปิด resource ของอีกช่องไม่ทำให้เลือกช่องใหม่เงียบ ๆ
- task ของ A ยังทำต่อขณะดู B; activity/deep link ระบุเจ้าของและกลับไป A อย่างตั้งใจ
- ครอบ Producer, ProductToClip, Tracker, Global Editor, Creative Studio, Export/Post Studio, Schedule, Analytics, Gadget Media และ mobile/QR filming/posting
- หน้า global/shared ระบุขอบเขตให้ชัด; empty/loading/error state ไม่ค้างข้อมูลช่องเดิม
- ปุ่มใช้กริยาและไม่เพิ่มสัญลักษณ์ซ้ำ ตาม UI Clean Standard; การตรวจหน้าจริงต้องครอบ desktop/mobile และ keyboard

## 6. Posting protocol: ห้ามโพสต์ผิดบัญชีและห้ามโพสต์ซ้ำ

ใช้ durable posting job ผ่าน store เดิม แทน singleton `_pending`; MVP มีหลายงานรอได้ แต่ active lease ของการ automate มีเพียงหนึ่งงานต่อ extension instance ห้ามงานใหม่แทนที่งานที่ถูก claim แล้ว

ข้อมูล job ขั้นต่ำ: `job_id`, `channel_id`, `export_id`, `queue_id`, `target_handle`, `channel_revision`, `payload_hash`, `status`, `lease_owner`, `lease_expires_at`, `attempt`, timestamps และผล account/outcome

เส้นทางบังคับ:
1. Prepare: ตรวจ channel/product/angle/project/export/cover/queue/account config ครบก่อนเขียน; duplicate prepare ใช้ idempotency key ไม่สร้างงานซ้ำ
2. Claim: extension ที่ bind ช่อง/profile รับเฉพาะงานที่ตรง scope; claim atomic พร้อม lease token และเก็บ job snapshot ไม่ fetch “งานล่าสุด” ใหม่ทุกขั้น
3. ก่อน upload/แก้ฟอร์ม: อ่านบัญชีจริงจากหน้า Studio ใน tab ที่ล็อกไว้ เทียบ normalized handle; ไม่มีข้อมูล/ไม่ตรงให้ block ก่อน side effect
4. ก่อน final publish/schedule: ตรวจบัญชีซ้ำ + tab/job/lease/payload revision; ครอบ action ย่อยทุกปุ่มและเส้นทาง `prepare-details` ไม่ให้ bypass
5. ส่ง result ด้วย job_id + lease token + expected revision; clear/cancel รับ job_id เท่านั้น ไม่ล้างคิวกลาง
6. ผลสำเร็จต้องมี outcome ของ platform ที่ตรวจได้; เส้นทาง navigation ทั่วไปหรือ debugger detach อย่างเดียวไม่เพียงพอ
7. schedule accepted → `scheduled_on_platform`; published ที่ยืนยันแล้ว → `published`; timeout/ผลกำกวม → `confirmation_unknown` และระงับ retry ที่คลิกโพสต์ซ้ำ
8. ถ้า platform สำเร็จแต่ backend offline ให้เก็บ receipt ใน extension storage แล้ว retry เฉพาะการบันทึกผล; backend idempotent และไม่ upload/publish ใหม่
9. เมื่อ browser/backend restart ให้ recovery job/lease อย่างชัดเจน; งานที่เลยขั้น publish attempt ต้อง reconcile ผลก่อนอนุญาตให้ retry
10. สถานะ queue/job จะแยกจาก production status เดิมและต้อง migrate/UI mapping ก่อนเปิดใช้; ไม่ mark Posted/ย้ายไฟล์จริงเพราะเพียงตั้งเวลาบน platform

ใช้ profile binding ผ่าน settings ของ extension (ไม่เดา profile จาก Chrome API); API secret เดิมยังเป็น authentication แต่ไม่ใช้เป็นตัวตน TikTok เก็บ audit event prepare/claim/account_check/attempt/outcome/repair โดยตัดข้อมูลลับ

stats sync ต้องส่ง source account จาก tab ที่ scrape จริงด้วย; server เทียบ binding และกรอง candidates ตามช่องก่อนจับคู่ ชื่อคลิปเหมือนกันสองช่องต้องไม่ merge; result กำกวมหรือบัญชีไม่ทราบให้ pending ที่ต้องตรวจเอง

ก่อนเปิดช่องรอง ต้องอัปเดต backend/extension protocol ทั้งคู่; client เก่าห้าม claim/clear โดยไม่มี job/scope ผ่าน capability/version handshake

## 7. Render, HyperFrames และไฟล์

### 7.1 ตัวตนคลิปและ Preview = Render

`ChannelIdentitySnapshot` มี channel_id/revision/display_name/handle/watermark/follow/avatar identity/hash เก็บใน project/composition และ export provenance worker รับ snapshot เดิมตลอดงาน และรวม identity fingerprint ใน incremental artifact/cache invalidation

Global Editor ส่ง snapshot ผ่าน RenderRequest → PipelineContext → SubtitleStage/engine + ProjectManifest; Preview อ่าน snapshot เดียวกัน แก้ `SequencePlayer.jsx` คู่ `subtitle_engine.py` และ label ใน `editor/NewClipPanel.jsx` โดยรักษา Font/Text Golden Master และ gadget style preset เดิมตาม contract ที่ใช้อยู่

ข้อความช่องยาวต้อง validate ก่อนบันทึก/render ให้พอดีพื้นที่เดิม ไม่แก้ font/size/wrapping/position เพื่อให้ข้อความใหม่พอดีโดยพลการ; escaping ไทย/ASS/HTML และรูป profile หายต้องมี gate

### 7.2 HyperFrames bridge

ตรวจพบฐานเดิม: `kit/channels.js` ลงทะเบียน main, `03_Projects/_HyperFrames_Studio/kit/new_clip.py:53` มี `--channel`, `03_Projects/_HyperFrames_Studio/kit/kit.js:61` มี `HF.applyChannel()`, และไฟล์รูปช่องรองมีอยู่ การตรวจรอบนี้เป็น source review ไม่ได้ยืนยันการสลับช่องหรือเฟรมเรนเดอร์จริงตามที่แผนเดิมกล่าว

งานที่ยังต้องทำ:
- CreateClipRequest/RenderCompositionRequest/list metadata รับ channel และ link IDs ชัดเจน; ไม่เดา owner จาก product shortcode หรือชื่อไฟล์
- create ส่ง `--channel` ที่ validate แล้ว; VO lookup จำกัด project ของช่อง ห้ามหยิบ voiceover แรกที่ชื่อสินค้าตรงจาก global glob
- composition เก็บ identity snapshot แบบ frozen; generated `channels.js` ใช้เป็นค่าเริ่มต้นของงานใหม่ ไม่เป็นแหล่งสดที่ทำให้คลิปเก่าเปลี่ยนตัวตน
- create/render ตรวจ composition metadata กับ parent/export scope; unknown/missing channel config ต้อง reject ไม่ใช่แค่ console warning
- render output/register ต้องส่ง channel, IDs และ snapshot hash; is_test ลง .tmp และไม่ register; กัน overwrite และ path traversal
- sync canonical config ไป kit แบบ validate/atomic + dry-run/diff; ห้ามมีแหล่งแก้ profile สองที่; avatar ใช้ file/hash เดิม ไม่คัดลอกซ้ำเมื่อไม่เปลี่ยน
- kit อยู่ใต้ project ที่ถูก gitignore: เก็บตัว sync/template/contract ที่ทำซ้ำได้ใน tools/tests และรวม kit/config/snapshots ใน backup/restore; commit เฉพาะไฟล์ tracked ไม่พึ่งการแก้ local kit อย่างเดียว

### 7.3 Path strategy

ใช้ path resolver กลางจาก `scripts/config.py` และ `Path` ตรวจ containment + channel ownership; ไม่เปลี่ยนค่า EXPORTS_DIR global ตาม Active Channel ระหว่าง request

ข้อเสนอ MVP: legacy main คงที่อยู่เดิม; งานใหม่ของช่องรองใช้:
- `03_Projects/<channel_id>/<project_id>/`
- `04_Exports/Ready_to_post/<channel_id>/<filename>.mp4`
- `04_Exports/Posted/<channel_id>/<filename>.mp4`
- `05_Covers_Thumbnails/<channel_id>/<project_id>/`

HyperFrames และ Gadget Media รักษา engine/workspace namespace เดิมใน MVP และแยกด้วย metadata + globally unique IDs; ถ้าจะซ้อน channel folder ใน namespace เหล่านี้ ต้องแก้ resolvers/discovery/index/backup ในเฟสเดียวกัน

ก่อนใช้ nested paths ต้องแก้ project discovery, Gallery, cover lookup/companions, serve/reveal, posted collision, registry path normalization, linking/reconcile, trash/delete และ backup/restore พร้อมกัน ตั้งชื่อ export ตาม convention เดิมได้ใน MVP เพราะ ownership อยู่ใน metadata/path ไม่ต้องบังคับรหัส it/gen หรือแก้ AGENTS.md เพื่อเริ่ม foundation

ไฟล์ unregistered ไม่เดา owner จาก basename/ชื่อสินค้าเพียงอย่างเดียว: ตรวจ registry → project/composition manifest → parent link; ขัดกันหรือไม่พบให้ “ต้องระบุช่อง” และห้ามเข้าคิว/โพสต์ จนผู้ใช้ assign owner ผ่าน workflow ที่ตรวจได้

## 8. Migration และ rollback

### 8.1 ก่อนย้ายข้อมูล

1. Inventory แบบ read-only: stores/DB/JSON/manifests/GadgetMedia index/HyperFrames metadata/jobs/cover links; บันทึกจำนวน, IDs, paths, references, hash และ orphan/conflict ลง `_Docs/Reports/`
2. สร้าง dry-run migration plan ระบุ record ที่ขาด channel และเหตุผลการกำหนด owner; ข้อมูลเก่าที่ชัดว่าเป็น main ให้ main แต่ unknown/conflict ต้องรายงานและรอตรวจ
3. เปิด maintenance/read-only mode หยุดผู้เขียนทุกตัว (API, worker, reconcile, extension และ CLI), drain/cancel งานอย่างชัดเจน; ไม่ migrate กลาง render/post
4. backup ผ่าน SQLite backup API ที่ใช้ WAL-consistent snapshot ตาม `scripts/backup_engine.py:37`; เก็บ JSON mirrors, channel registry, manifests/index, kit config/snapshots, task/job state พร้อม checksums; ห้าม copy store.db อย่างเดียว
5. ทดสอบ restore สำเนาลง temp root และตรวจจำนวน/ID/hash ก่อน apply ของจริง

### 8.2 วิธี apply

- tool ที่เสนอ `tools/migrate_channels.py`: default dry-run; มี explicit apply/resume/report และ migration version/journal (ยังไม่สร้างในรอบนี้)
- DB/JSON mirror ใช้ store/coordinator ที่ทำให้ข้อมูลสองฝั่งสอดคล้องกัน; ห้ามแก้ JSON เดี่ยวแล้วปล่อย auto-import ทับ DB
- backfill parents ก่อน children; channel ที่มีอยู่แล้วต้องรักษาไว้; แปลง template keys และ stats/job source account อย่างมี mapping
- manifests/GadgetMedia files เปลี่ยนแบบ atomic พร้อม original revision/hash; ไม่แตะ Raw/Assets, CapCut draft หรือเนื้อหา MP4 เก่า
- cross-store/filesystem ไม่ได้ atomic ทั้งก้อน: ใช้ journal ต่อขั้น, maintenance lock และ roll-forward/rollback ที่รันซ้ำได้; migration ครั้งที่สองต้อง 0 unintended changes
- validation: counts/IDs เดิมไม่หาย, ownership ของทุก parent-child ตรง, paths/links ยังเปิดได้, mirrored data ตรงกัน, unknown = รายการที่ระบุไว้ชัดเจน
- ใหม่ทุก record ต้องมี channel; legacy read fallback ถูกปิดหลัง validation และเปิด strict multi-channel mode

### 8.3 Release และ rollback

ปล่อยเป็นสองขั้น: (1) foundation/backfill และ client ใหม่ใน single-channel mode (2) เปิด strict isolation พร้อมช่องรองหลัง gates ผ่าน; อย่าเปิดช่องรองก่อน guard/extension/parity/migration พร้อม

หากพบ scope leak/identity mismatch ให้หยุดเขียน/โพสต์ทันทีและ rollback release ไม่ย้อน backup ทั้งฐานแบบเงียบ ๆ หากมีข้อมูลใหม่หลัง cutover ต้องใช้ journal และ replay/reverse migration ที่รักษาข้อมูลนั้นไว้; export/post ที่เกิดจริงคงประวัติและไม่ replay publish

channel ที่ archive/เปลี่ยน handle ระหว่างมี job ต้อง block claim/attempt ใหม่จน revalidate; งานที่ส่งถึง platform แล้วเก็บ target account เดิมไว้ audit และ reconcile ห้าม rebind ไปช่องอื่น

## 9. ลำดับพัฒนาใหม่และผลส่งมอบ

ทุกเฟสเปิดรอบ TODO ก่อนแก้โค้ด, ปิดเฉพาะเมื่อ gate ผ่าน และ commit เฉพาะงานตัวเอง; งาน agent อื่นใน working tree ไม่ใช่ scope ของเฟสนี้

| เฟส | งานและไฟล์หลัก | ต้องจบหลัง | ผลส่งมอบ / gate |
|---|---|---|---|
| P0 — Contracts & inventory | channel ownership/route matrix, migration inventory, ADR ในแผนนี้ | — | ทุก reader/writer/caller มี scope classification; unknown owner มีรายงาน |
| P1 — Registry & scope foundation | channel_store/scope/api_channels, config/path helpers, sync tool | P0 | profile validation, archive, explicit scope, unknown/missing rejection; shared/global ยังใช้ได้ |
| P2 — Stores & migration tool | db/store services, Products/Export/Post/Schedule, dry-run/apply/rollback | P1 | A mutation รักษา B, duplicate URL/filename/slot ไม่ merge ข้ามช่อง, migration/restore temp ผ่าน |
| P3 — Production workflows | phase1/editor/render/batch/tasks, recording/shot lists, Producer/Gadget Media/analytics/stats | P2 | ID access/upload/cancel/bulk/reconcile มี guard; parent ownership ตรง; workers คงช่อง |
| P4 — Identity & HyperFrames | pipeline/manifest/subtitle/SequencePlayer/NewClipPanel, api_hyperframes/kit contract | P3 | frozen identity และ fingerprints; Preview/Render parity; create→render→register ตรงช่อง |
| P5 — Posting protocol | durable jobs, queue templates, autopost routes, background/sidepanel/stats bridge | P3 + P4 | account guard ทุก action; lease/restart/result repair; old client ถูกกัน; scheduled/posted จริง |
| P6 — Paths & lifecycle | new-channel folders, Gallery/Posted/covers/reveal/delete/discovery/backup | P2 + P4 + P5 | nested + legacy เปิดได้, filename collision กันได้, recovery ไม่ orphan |
| P7 — Frontend & mobile integration | ChannelProvider/api wrapper/App/editor/Hub/Post/Schedule/Analytics/mobile | P3–P6 | scope ครบ, switching/unsaved/multi-tab/late response/cache ถูก; UI จริง desktop/mobile |
| P8 — Rehearsal & cutover | temp full-flow, read-only inventory ใหม่, backup/maintenance/backfill/feature flag | P0–P7 + §11 | replay migration/rollback ผ่าน, source account พร้อม, เปิดช่องรองอย่างมีบันทึก |

P0–P7 พัฒนาและตรวจด้วย fixtures หลายช่องแล้ว; P8 การเปิดใช้จริงต้องตรวจบัญชี/selector และ readiness ตามผล audit แยกสถานะ implementation ออกจาก acceptance/cutover

## 10. Acceptance matrix และคำสั่ง Gate

ทุก test deterministic/offline ใช้ tmp_path/monkeypatch ไม่มีการอ่าน/เขียนข้อมูลจริงหรือโพสต์ TikTok จริง; fixture account/DOM ไม่ใช่หลักฐานว่า selector ใช้ได้กับบัญชีจริง ต้องมีขั้น read-only/manual readiness ภายหลัง

| ID | สถานการณ์ขั้นต่ำ | ผลที่ต้องได้ |
|---|---|---|
| AC01 | A/B มี product URL, angle label, basename เหมือนกัน | ไม่ทับ/merge/status drift; latest/export/post อยู่ช่องที่ถูก |
| AC02 | อ่าน/แก้/ลบ/reveal/download ID หรือ path ของ B ด้วย A | reject และ B byte/revision ไม่เปลี่ยน; shared asset ผ่านเฉพาะ reference ที่อนุญาต |
| AC03 | batch ของ A แอบมี item B; scoped mutation; concurrent writers | reject ก่อนเขียน batch; ทุก record อีกช่องคงเดิม ไม่มี lost update |
| AC04 | A/B จองเวลาเดียวกัน, template copy/reset, auto-fill preview เก่า | ต่างช่องทำได้; ช่องเดียวชนตามกฎ; preview stale ไม่ commit เงียบ |
| AC05 | render A แล้วสลับ UI ไป B หรือแก้ชื่อ/handle A กลางงาน | output/registry/task เป็น A ใช้ snapshot เดิม; new revision เปลี่ยน cache ถูก |
| AC06 | late response A, F5, cache เก่า, editor unsaved, เปิดสอง tab | B ไม่ถูกทับ; migration cache เข้าช่อง main เท่านั้น; autosave scope ถูก |
| AC07 | account ถูก/ผิด/อ่านไม่ได้/เปลี่ยนก่อนคลิก final/หลาย upload tabs | ไม่มี upload หรือ publish ในบัญชีผิด; tab/job ตรวจตรงกันทุก action |
| AC08 | pending สองช่อง, stale clear/result, lease expired, restart/prepare ซ้ำ | job ไม่ถูกแทนที่/ล้างข้ามงาน; claim atomic; idempotent |
| AC09 | platform success แต่ callback fail; timeout กำกวม; schedule accepted | repair เฉพาะบันทึกผล; unknown ไม่ publish ซ้ำ; schedule ไม่ mark published |
| AC10 | stats ชื่อเดียวต่างบัญชี; pending attach/ignore/restore; analytics | candidates/metrics ไม่ข้ามช่อง; unknown account ไม่ merge |
| AC11 | unknown HyperFrames channel, VO อีกช่อง, identity/profile เปลี่ยน | create/render/register reject ผิด scope; คลิปเก่าคง snapshot |
| AC12 | legacy flat/nested files, Posted/covers/thumbnail, collision/delete | Gallery เปิดได้; companions เป็นเจ้าของถูก; ไม่ overwrite/ลบอีกช่อง |
| AC13 | migration รอบสอง, JSON import, crash ครึ่งทาง, rollback หลังมีงานใหม่ | IDs/counts preserved, mirror ตรง, resume/recovery ไม่สูญข้อมูลใหม่ |
| AC14 | GadgetMedia campaign/project/index/master + mobile recording/task | channel กับ workspace_scope อยู่ครบ; ไม่มีเส้นทาง global editor ที่ข้าม guard |
| AC15 | channel draft/archived/handle ซ้ำ/ข้อความยาว/รูปหาย | validation ชัด; final render/post ถูก block ตาม readiness; typography เดิม |
| AC16 | Preview/Render ของ main และ fixture ช่องรอง | identity ตรงกัน; probe font/layout/motion เดิม; output 1080×1920 30 FPS |
| AC17 | test cleanup และ backup/restore สำเนา | temp media/project/thumbnail/job หมด, production registry ไม่ถูกแตะ; restore เปิดได้ |

ไฟล์เทสเหล่านี้มีแล้ว: `tests/test_channel_scope.py`, `tests/test_channel_migration.py`, `tests/test_channel_workflows.py`, `tests/test_channel_posting_protocol.py`, `frontend/src/lib/channelState.test.js`; audit เพิ่ม behavioral cases ใน schedule/export/post/stats/hyperframes/backup/parity/extension และ actual Chromium สำหรับ workspace/profile/Gadget/Schedule/Tracker/QuickPost. ตรวจผลล่าสุดในรายงาน ไม่ใช้ชื่อไฟล์เป็นข้อพิสูจน์ว่า AC ครบ

คำสั่งรันตอนพัฒนาใช้ชุดที่เกี่ยวข้องกับแต่ละเฟส; ก่อนปิดรอบ implementation ให้รัน full gate ตาม [testing_standard.md](../../.agents/rules/testing_standard.md):

```powershell
& .venv/Scripts/python.exe -m compileall -q scripts tools
& .venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider --tb=short
node --test tiktok_autopost_extension/background.test.cjs
npm --prefix frontend test
npm --prefix frontend run build
git diff --check
```

งานภาพเพิ่ม `tests/test_preview_render_parity.py` และ `tests/test_preview_render_behavior.py`, ใช้ probe ด้วย .venv และ FFmpeg ดึงเฟรมเข้า/ค้าง/ออกสำหรับทั้งสองช่อง; HyperFrames ใช้ CLI check/preview/render ตาม skill ของ project และยืนยัน metadata/output จริง ผลเทสจาก mocks ไม่แทนการดูเฟรม

ทุก render/probe ของ gate ลง .tmp หรือ temp root และไม่ register เข้า production; cleanup เฉพาะ artifacts ของรอบเอง ตรวจ registry และ temp roots หลังจบ รายงาน pass/fail/skip จริง ไม่ยกตัวเลข suite เก่ามาอ้าง

## 11. ข้อมูลรอเจ้าของช่องและการตัดสินใจ

| รายการ | ค่าเสนอในแผน / ผลต่อการเริ่มงาน |
|---|---|
| ชื่อ/handle/ลายน้ำ/รูปของช่องรอง | registry จริงมี rizannntry / rizannnTry / @rizannntry แล้วตามการอ่านอย่างเดียว; ตรวจ completeness/revision ของ profile และ snapshot ก่อน final clip |
| จำนวนช่องรอง | schema รองรับ N; ไม่ block foundation |
| อนุญาตสินค้ารุ่นเดียวทำหลายช่องหรือไม่ | ค่าเริ่มต้นยังไม่เปิด clone; ถ้าอนุญาตใช้คนละสคริปต์/record และ reuse raw แบบมีสิทธิ์ |
| ตารางเวลาแต่ละช่อง | แยก template เสมอ; ตั้งต้นด้วยชุดเวลาเดียวกันได้เมื่อยืนยัน; ไม่ใช้ template record ร่วม |
| รหัสช่องในชื่อไฟล์ | optional หลัง MVP; คง naming rule เดิมก่อน ไม่บังคับแก้ AGENTS.md |
| profile/บัญชี TikTok ที่ bind ต่อช่อง | ผู้ใช้ยืนยัน main=@rizanntry, second=@rizannntry (existing ID rizannntry); registryตรงแล้ว ยังต้องเชื่อมChromeเพื่อตรวจบัญชีจริง/selector |
| legacy main cohort และ unknown ownership | ผู้ใช้ยืนยันคลิป/campaignเก่าเป็นmain; reviewed explicit9assignments applyสำเร็จ/postdryrun0writes/0conflicts; คง286test/orphan records+template1ไว้ก่อน ไม่ bulk stamp หรือลบ |
| รูปแบบเริ่มใช้งาน | ผู้ใช้เลือกกดผ่านextensionก่อน; ไม่เพิ่มunattendedschedulerในรอบนี้ ไม่ปล่อยbacklog/โพสต์จริงจากคำสั่งเตรียมระบบ |

ไม่จำเป็นต้องให้ผู้ใช้ตอบทุกข้อก่อนทำ P0–P7 แต่ข้อที่กระทบการเปิดใช้จริงต้องมีคำตอบใน cutover checklist ห้ามใช้ค่า placeholder ใน final clip

## 12. Definition of Done และข้อจำกัดของรอบนี้

- [ ] route/store/caller inventory ครบ และไม่มี channel route ที่ bypass guard
- [ ] ownership/identity snapshot ครบทุก flow รวม legacy + Global Editor + Gadget Media + HyperFrames + mobile
- [ ] AC01–AC17 ผ่าน พร้อม full gates และ actual frame verification ตามชนิดงาน
- [x] migration/restore/recovery แบบ temp rehearsal ผ่าน; production apply9มี maintenance/backup/report/snapshot-only-owner validation และAPIrestart/scoped GETผ่าน (ดูผล cutover)
- [ ] profile/account binding พร้อม; unknown account และ ambiguous outcome หยุดอย่างปลอดภัย
- [ ] UI จริงทุกหน้าสลับช่อง/empty/error/unsaved/deep link/multi-tab ผ่าน
- [x] ARCHITECTURE/README/คู่มือผู้ใช้/extension protocol อัปเดตตามพฤติกรรมจริง; รอบนี้ไม่เปลี่ยน caption font/layout/style ที่ต้องแก้ SOP/Checklist
- [ ] ไม่มี demo/probe/thumbnail/project/job ทดสอบค้างในคลังจริง; บันทึก TODO/HISTORY พร้อมเอเจนต์และโมเดล

**ผลตรวจ implementation:** Gemini ส่ง implementation จำนวนมากแล้ว แต่ audit พบ scope/cache/autosave/Preview/posting/recovery/manual-draft omissions และแก้พร้อม regression ตามรายงาน v3. Final offline gates ผ่านแล้วและปิดรอบ audit พร้อมข้อจำกัด; cutover follow-up กำหนดowner9แถวรวมlegacy Gadget campaign1/21เป็นmainแล้ว และตรวจsnapshot/APIscopeผ่าน แต่ metadata ไม่พิสูจน์บัญชี TikTok จริง. DoD ที่รวม live cutover/UIทุกกรณี/cleanup100% ยังไม่ติ๊กทั้งหมด; ดู follow-up ใน TODO และรายงาน

**Jev:** ตรวจร่วมจากสรุปข้อความที่ส่งให้เท่านั้น ไม่ได้อ่านไฟล์หรือเห็นเฟรมเอง; คะแนนและ confidence ของรอบนี้บันทึกใน TODO/HISTORY และรายงานให้ผู้ใช้ทราบ ไม่ใช้แทนหลักฐานจากโค้ด/เทส
