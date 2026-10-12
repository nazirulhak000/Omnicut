# Legacy main ownership review — 2026-10-11
ดำเนินการโดย: Codex (GPT-6), agent legacy_cutover_inventory

ขอบเขต: ตรวจข้อมูลแบบอ่านอย่างเดียวผ่าน SQLite `mode=ro` และ JSON; ไม่ import production stores, ไม่ apply migration, ไม่เปลี่ยนสถานะ/identity/queue, ไม่ลบไฟล์หรือแถวใด

ผู้ใช้ยืนยัน main=`@rizanntry`, second=`@rizannntry` (existing channel ID `rizannntry`) และคลิป/แคมเปญเก่าเป็น main ทั้งหมด การยืนยันเจ้าของไม่ใช่หลักฐานว่า browser login ถูกบัญชีหรือคลิปโพสต์แล้ว

## ข้อเสนอที่เล็กที่สุด

ใช้ explicit assignments **9 แถว** เท่านั้น ไม่ assign unknown 295 แถวรวม เพราะจำนวนมากเป็นข้อมูลเทสหรือ operational orphan

| Store | Assign main | คงไว้ไม่เปลี่ยน | หลักฐาน/เหตุผล |
|---|---:|---:|---|
| export_registry | 1 | 39 | BCD01 alias อ้างไฟล์เดียวกับแถว main ที่มีอยู่; 38 TEST preset rows + test_sample_video 1 ไม่มีไฟล์แล้ว |
| posts | 7 | 0 | ทั้ง 7 มี URL `https://www.tiktok.com/@rizanntry/video/...` สอดคล้องกับ user confirmation |
| gadget_media_campaigns | 1 | 0 | `gadget-media-ebbb8c0304`, 21 slots; ผู้ใช้ยืนยัน main โดยตรง |
| shot_lists | 0 | 230 | parent products หาย; 229 ไม่มี shot_list, 1 เป็น `prod:angle:b1`; 227 มี script fixture, 225 มี pytest temp voice path |
| recording_sessions | 0 | 1 | `SsRzS7HuZI4er75E07Qdqg`, parent `prod`, pending fixture หมดอายุแล้ว; ไม่ปิด/ลบทิ้งในการตรวจนี้ |
| batch_render_queue | 0 | 1 | `f36a9253-a078-43e9-af8e-d68550146b58`, cancelled, parent `prod_api_test` ตรงกับ test fixture |
| task_registry | 0 | 15 | completed/failed orphan tasks; 2 API Angle Test, 4 Widget/x.test, ที่เหลือ mock/audio/render task ที่ไม่จำเป็นต่อ legacy content |
| schedule_templates | 0 | 1 deferred | `week:2026-09-07` รอ explicit namespace rename หลังยืนยัน reader รองรับ |

รวม **9 main candidates / 286 held unknown / 1 deferred template**; **758 already-owned** ไม่แตะ ไม่มี production channel_artifacts rows และไม่มี Gadget project manifests ใน inventory นี้

Exact IDs และ evidence รายแถวอยู่ใน [CODEX_LEGACY_MAIN_ASSIGNMENT_EVIDENCE_20261011.json](CODEX_LEGACY_MAIN_ASSIGNMENT_EVIDENCE_20261011.json), `main_assignment_candidates` เป็นข้อเสนอให้ parent review ไม่ใช่ applied assignment file

## ข้อควรระวังก่อน automatic cutover

- Export alias `exp_e9084d645ce54d82903f45211b1be8ff` และ canonical main `exp_3e37bf3212084b42ba155816fb4ff62e` อ้างไฟล์ BCD01 เดียวกัน ต้องไม่ enqueue/publish ทั้งคู่; การ stamp owner ไม่ใช่คำสั่งเปลี่ยน rendered/ready_to_post หรือสร้างงานใหม่
- Post 7 แถวคง posted history/metrics/URL เดิม ไม่เติม export link จาก `clip.mp4` ที่กำกวม และไม่สร้าง publication ใหม่
- Campaign 21 slots ไม่มี Gadget project manifests ให้ย้าย; owner migration ไม่ทำให้มีคลิปพร้อมโพสต์ขึ้นมาเอง
- Posting jobs ที่อ่านพบ: cancelled 1, prepared 2, claimed 1 (มี lease timestamp เดิม) ต้องตรวจสถานะ/lease/receipt โดย protocol ก่อนเปิด auto; ห้ามอนุมานว่า expired lease เท่ากับยังไม่โพสต์
- ไม่มี identity snapshot ใน proposed decision rows; ห้ามเติม/แก้ frozen identity ของ historical clips ด้วยการ migrate owner
- Hold 286 เป็นการกันออกจาก cutover รอบนี้ ไม่ใช่ลบหรือรับรองว่าทุกแถวเป็นขยะ และไม่ใช่การตีความว่าผู้ใช้ยืนยัน owner ไม่ได้

## หลักฐานและข้อจำกัด

Source precheck plan hash: `3f6f3426b5c80cacf06481758953ec0ab74dc53752e1d8cd7ded9c28f1de6762`; hashes/source IDs อยู่ใน evidence JSON ต้องสร้าง dry-run ใหม่ก่อน apply เพราะ API ยังทำงานและ source อาจเปลี่ยน

Trace: `scripts/channel_migration.py` TABLES/FILE_STORES และ plan_posts; `tests/test_api_batch_audio.py:38` ให้ fixture script/voice path, `tests/test_batch_render.py:190` ให้ `prod_api_test`, `tests/test_error_handling_recovery.py:120` ให้ `job_123`, `tests/test_phase1_smoke.py:1085` ให้ TEST preset

Jev startup CLI unavailable: API 400 `max_tokens_exceeded` เมื่อส่ง inventory ใหญ่; ใช้ degrade ตามกฎ รายงานสรุปขนาดเล็กหลังเขียนได้ quality **2.89/4, confidence 0.69** (ตรวจจากสรุป ไม่ได้อ่านไฟล์เอง); ทำต่อใน authorized scope ตาม user override ที่ให้ใช้ review/หลักฐานจริงแทนหยุดถามซ้ำ ไม่ถือผล Jev เป็นหลักฐาน รายงานนี้อิง raw read-only records และ user confirmation

Verdict: เตรียม exact 9 assignments และซ้อม temp mirror ได้; ยังไม่ apply/เปิด automatic posting จน stop-writers/backup/preflight/live-account/protocol checks ผ่าน
