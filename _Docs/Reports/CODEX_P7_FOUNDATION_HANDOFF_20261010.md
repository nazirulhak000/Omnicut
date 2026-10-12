# Codex P7 foundation — checkpoints และส่งต่อ

ดำเนินการโดย: Codex (GPT-6) + 3 delegated agents (Codex GPT-6)
วันที่: 2026-10-10 · สถานะ: ปิดรอบ foundation ตามผู้ใช้อนุมัติแล้ว; P7/P8 ยังไม่จบทั้งเฟส

## File ownership

| ผู้รับผิดชอบ | ไฟล์ที่เขียนได้ |
|---|---|
| Parent Codex | frontend/src/lib/channelId.js, channelId.test.js; รายงานนี้และบล็อกรอบของตัวเองใน TODO/HISTORY |
| p7_state | frontend/src/lib/channelState.js, channelState.test.js |
| p7_request | frontend/src/lib/channelRequest.js, channelRequest.test.js |
| p7_review | อ่านอย่างเดียว ส่งข้อพบให้ parent |

ไฟล์ shared/backend ของ Claude และ channelHandle pair ไม่อยู่ในขอบเขต; ไม่มีการแก้ App/api/TaskContext/route policy/conftest หรือเปิด strict/migrate/post/render จริง

## Checkpoint 1 — ก่อนเริ่มงานขนาน

- TODO จองไฟล์ก่อนแตะโค้ดแล้ว; ใช้ ADR_MULTI_CHANNEL_20261010 เป็น source contract
- Parent Jev: scope_fit 0.97/1 confidence 0.94, verdict proceed (ตรวจจากสรุปข้อความ ไม่ได้อ่านไฟล์เอง)
- เอเจนต์ state Jev 3.29/4 confidence 0.42; request noul 0.69 confidence null; review noul 0.95 confidence null — paused ตาม confidence gate และส่งคำถามให้ผู้ใช้แล้ว
- Parent ทำ channelId helper และ behavioral tests ต่อได้ในขอบเขตผ่าน gate; ไม่ถือผลของ parent เป็นการอนุมัติแทน gate ของเอเจนต์
- Limit observation จาก local session events ณ 2026-10-10 19:39:23 Asia/Bangkok: primary 300 นาที used 18–19%, secondary 10080 นาที used 23%; ไม่พบ rate_limit_reached_type ค่าจริงเป็น snapshot ไม่รับประกันโควตาอนาคต
- ตรวจซ้ำก่อน full frontend gate และก่อนส่งมอบ; หาก metadata ไม่พร้อมให้บันทึก unknown ไม่เดาตัวเลข

## ส่งต่อหาก session ถูกตัด

1. อ่าน Round CODEX-P7-FOUNDATION-PARALLEL-20261010 ใน TODO, git status และรายงานนี้
2. ผู้ใช้ตอบอนุมัติ delegated Jev gate แล้ว: “ทำต่อในขอบเขตที่จองไว้ ใช้เทสและรีวิวตรวจ (แนะนำ)” Parent resume ทั้งสามเอเจนต์แล้ว
3. ตรวจไฟล์และผลเอเจนต์ล่าสุดก่อนทำซ้ำ; channelId pair เป็นของ parent และ state/request pairs เป็นของเอเจนต์ที่จอง
4. ห้ามนำ helpers ไปเชื่อม App/api จนเจ้าของ integration ทำตาม ADR และ AC06; build ผ่านไม่ได้แปลว่า P7 สำเร็จครบ

## API และผลทดสอบ

Checkpoint 2 — 2026-10-10 19:42 Asia/Bangkok:

- `channelId.js` ส่งออก `isValidChannelId(value)` และ `assertChannelId(value)`; ไม่ trim/lowercase ค่าที่ผู้ใช้ส่ง และ error มี code `channel_scope_invalid`
- Targeted Node tests: 2 passed/0 failed; syntax checks ผ่าน
- Full frontend tests: 919 passed/0 failed/0 skipped; Vite production build ผ่าน เป็น gate ณ checkpoint นี้ ต้องรันใหม่หลังเพิ่ม state/request modules
- Quota snapshot ล่าสุด 19:42:01: primary 300 นาที used 24%, secondary 10080 นาที used 24%; `rate_limit_reached_type=null` ยังไม่พบการชนลิมิต
- ทั้งสามเอเจนต์หยุดรอคำตอบ confidence gate; ยังไม่มี channelState/channelRequest modules และยังไม่เชื่อม production UI

Final gate: helpers 35 passed/0 failed (ID 2, state 15, request 18); frontend full tests 952 passed/0 failed/0 skipped; Vite production build ผ่าน; read-only reviewer trace contract และ fixes แล้วไม่พบ must-fix เหลืออยู่ ผลทดสอบใช้ storage fixtures/temp logs ไม่มี production wiring และไม่รัน Python full suite ของ backend ที่เจ้าของกำลังทำอยู่

Checkpoint 3 — 2026-10-10 19:53 Asia/Bangkok:

- ผู้ใช้อนุมัติ delegated gate แล้ว; ทั้งสามเอเจนต์ resume ใน ownership เดิม
- State/cache pair เขียนแล้ว own targeted tests 15 passed/0 failed; รอ independent review/final gate
- Reviewer พบ request registry recovery และ `params.channel` validation gaps; request agent กำลังแก้พร้อมเพิ่มเทส
- Quota snapshot 19:53:01: primary 300 นาที used สูงสุด 32%, weekly used 25%; ไม่พบ limit reached

Checkpoint 4 — final handoff:

- แก้ข้อพบ request ครบ: registry ก่อน validate context, URL+params scope, baseURL origin/root, mutable native carriers และ serialization hooks ที่เปลี่ยน owner ภายหลัง
- Parent final gate 35 helper tests และ 952 frontend tests ผ่าน; reviewer verdict ship isolated foundation
- Quota snapshot 2026-10-10 19:57:20 Asia/Bangkok: primary 300 นาที reset รอบใหม่แล้ว used 1%, weekly used 26%; ไม่พบ limit reached
- Completed artifacts: channelId/channelState/channelRequest พร้อม test pairs และรายงานนี้; ขั้นถัดไปคือเจ้าของ P7 ทำ integration ตามรายการด้านล่าง
- Jev completion ตรวจจากสรุปข้อความ ไม่ได้อ่านไฟล์เอง: handoff_quality 3.11/4 confidence 0.57 escalate; improvement 3.78/4 confidence 0.82 proceed ส่งคำถามผู้ใช้ก่อนย้ายบันทึกเข้า HISTORY; โค้ด/tests/review เสร็จแล้ว รอเฉพาะ closeout gate
- Closeout: ผู้ใช้ตอบ “ปิดรอบ foundation ตามผลเทสและรีวิว (แนะนำ)” แล้ว ย้ายบล็อกเข้า HISTORY และเหลือชื่อรอบบรรทัดเดียวใน TODO; quota snapshot ล่าสุด 19:57:58 primary used 3%, weekly used 27%, ไม่พบ limit reached; cleanup temporary logs/JSON เฉพาะของรอบนี้ ไม่มี commit

## งาน integration ที่ส่งต่อให้เจ้าของ P7

1. ต่อ ChannelProvider โดยเก็บ active channel ต่อ tab; ทุก request/autosave จับ channel และ generation ตอนเริ่ม ไม่อ่าน active channel ใหม่เมื่อ response กลับ
2. ก่อนเปลี่ยนช่องให้ผู้ใช้เลือก save/discard/cancel หาก editor มีงานค้าง; เปลี่ยน generation หลังยืนยันจริง แล้ว abort requests/reset selections/modals และโหลดข้อมูลใหม่
3. ต่อ wrapper ตาม route policy: channel/global/shared ต้องระบุชัด; URL สื่อใช้ query ได้เฉพาะ allowlist; registry recovery ต้องอ่านรายการช่องได้แม้ช่องเดิมถูกลบ
4. ย้ายเฉพาะ cache ของข้อมูลช่องตาม client inventory; shared font/audio caches คง global; ย้าย legacy เข้า main ผ่าน helper แล้วทดสอบ reload/interruption/storage denied
5. ตรวจ desktop/mobile และสอง tabs จริง รวม autosave scope, request echo, late response และ A→B→A; helpers และ Node tests ยังไม่ครอบคลุม wiring เหล่านี้

State/cache API: `channelCacheKey`, `readChannelCache`, `writeChannelCache` รับ channel ID ชัดเจนและ storage injection; `migrateLegacyMain` ย้ายทีละ legacy key เข้า main พร้อม journal/read-back; `readActiveChannel`/`writeActiveChannel` รับ sessionStorage; `createChannelRequestGuard` มี `activate/capture/isCurrent`; `decideChannelSwitch` คืน `stay/switch/confirm/save_before_switch` โดยไม่เปลี่ยน state เอง

ข้อจำกัด state: storage exceptions ส่งต่อให้ caller ต้องจัด UI fallback; `save_before_switch` ต้องรอ save ของช่องเดิมสำเร็จก่อนเปลี่ยน; migration journal กู้การขัดจังหวะได้แต่ไม่ใช่ cross-tab transaction/lock จึงต้อง serialize migration ตอน integration

Request API: `createChannelRequestContext({channelId, compat})`, `prepareChannelRequest(context, options, {scope, origin})`, `scopedMediaUrl(url, context, {origin})`, `assertChannelResponseScope(context, headers)`; `CHANNEL_HEADER` คือ `X-OmniCut-Channel` ต้อง capture context ณ dispatch และใช้ร่วมกับ state guard ก่อนรับ response

ข้อจำกัด request: helper ไม่ส่ง network request และไม่ใช่ authorization; caller ต้องระบุ route scope จาก policy และ trusted origin เอง URL ต้องรวม `/api` และ baseURL ใช้ origin root เท่านั้นไม่ใช่ `/api` prefix; รองรับ plain JSON/string payload และ immutable Blob ส่วน FormData/URLSearchParams, Date/custom objects, functions/serialization hooks/accessors/cycles และ custom adapters/serializers/transforms คืน `channel_request_unsupported` จึงต้องทำ upload/axios adapter ให้ตรวจ wire form ณ dispatch ก่อน integration; scoped native headers ถูกแปลงเป็น plain headers ส่วน unscoped compat รองรับ plain headers; ไม่มีการเปลี่ยน axios defaults/global interceptors

ข้อสังเกตส่งต่อ backend owner: `scripts/channel_store.py` ใช้ Python regex `.match()` กับ `$` ซึ่งอาจยอมรับ newline ท้าย slug; frontend helper ปฏิเสธ newline ตาม full-string contract ให้เจ้าของ backend ตรวจเพิ่ม (รอบนี้ไม่แก้ backend)
