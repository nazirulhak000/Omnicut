# Workflow audit — Multi-channel P3/P4/AC14/AC15
ดำเนินการโดย: Codex (GPT-6), delegated workflow agent

สารบัญ: Findings, fixes, evidence, remaining limits — ดำเนินการโดย: Codex (GPT-6)

เป้าหมาย: ตรวจเส้นทาง backend จริงเทียบ PLAN_MULTI_CHANNEL_20261010/ADR และแก้ขอบเขตที่ parent จองให้ โดยใช้ engine/ownership helpers เดิมแทนเพิ่ม workflow อีกชุด

## Findings และสิ่งที่แก้

1. **AC15 lifecycle ของ implicit main ถูกข้าม** — `_guard_write` ใน `api_recording.py`, `api_shot_lists.py`, `api_mobile_studio.py`, `api_gadget_media.py`, `api_gadget_media_projects.py`, `api_producer.py` และ media job gates ใน `api_background_isolation.py`, `api_voice.py` ตรวจ status เฉพาะ explicit scope จึงเปิดทาง legacy client เขียนช่อง archived/เริ่มงานช่อง draft ได้ Middleware ตรวจ scope แต่ไม่ได้ตรวจ lifecycle ให้ handlers
   - แก้ให้ตรวจ active/writable ทุก ChannelScope รวม implicit main; ยังคง readiness compatibility ของ implicit main ตาม decision เดิม
   - Voice preview ที่ไม่มี header แต่สร้าง artifact ของ main ต้อง resolve implicit main ก่อน gate
   - Regression ยิง HTTP จริงตรวจ 409 และไม่มีการเปลี่ยน stores/job/engine ก่อน reject สำหรับ implicit main draft/archived; Producer archived ตรวจไม่แตะ store เลย

2. **AC11 avatar ที่ registry ยอมรับแต่ HyperFrames ใช้ไม่ได้** — `api_hyperframes.py:_freeze_composition` เดิมบังคับ avatar อยู่ใต้ Studio แม้ `channel_store.normalize_avatar_path` รองรับ path สัมพัทธ์ใดก็ได้ภายใน workspace เช่น `02_Assets/avatar.png`
   - แก้ copy bytes ที่ผ่าน snapshot hash ไป `Studio/assets/shared/channel-identities/<sha256>.<suffix>` โดยไม่เขียนทับ asset ต้นทาง; ใช้ filename ตาม hash เพื่อ deduplicate; cache bytes ผิด hash ต้อง reject
   - Snapshot fields เดิมยังเป็น provenance; เพิ่มเฉพาะ Studio-local browser URL ใน embedded identity
   - Regression ตรวจ source bytes คงเดิม, copy/hash ถูก, repeated freeze reuse, cache corruption reject และ actual HyperFrames browser gate บน fixture ภาพ PNG นอก Studio

3. **AC14 mobile หลาย selected videos ล้มก่อน render** — `mobile_quick_studio.py` ใส่ `multi_video_paths` เมื่อเลือก >=2 คลิป แต่ `TikTokAutoCutterPipeline.run` ไม่มี argument นี้ ทำให้ TypeError; mocks เดิมรับ **kwargs จึงซ่อนปัญหา
   - แก้ใช้ `manual_shot_map` ของ pipeline เดิม จับหนึ่ง official script line ต่อหนึ่ง speech beatและวนใช้คลิปที่เลือกโดยคงทั้ง beat; probe duration และ reject เมื่ออ่านไม่ได้
   - Custom raw/session ที่ผู้ใช้ระบุคง priority และไม่ถูก selected list แทรก
   - Regression bind kwargs กับ signature จริงและเรียก ShotMatchingStage จริง ตรวจ source สองไฟล์และ duration ต่อ beatก่อนตรวจ task completed

4. **Gadget identity เดิมมีแค่ provenance ไม่ปรากฏใน output** — หลัง parent จองเพิ่มให้แก้ `gadget_media_renderer.py` เปลี่ยน scoped worker จาก EMPTY_ASS เป็น SubtitleEngine.generate_ass(cues=[], bilingual=False, snapshot จาก queued job) เพิ่มเฉพาะ watermark identity ที่ parent ขอ ไม่เพิ่ม captions/callouts/follow/avatar และไม่เปลี่ยน style preset/clip timings
   - main fixture ใช้ MAIN_SEED content เดิม; ช่องรองใช้ frozen profile; เปลี่ยน live profile หลัง queue แล้วยังได้ ASS/registry identity เดิม
   - งาน standalone unscopedคง EMPTY_ASS เดิม; scoped secondary ที่ snapshotหายต้อง reject แทน fallback main
   - Actual libass probeของ ASS ที่ส่งเข้า VideoEditor ตรวจภาพ 1080×1920 และ pixels เกิดเฉพาะ watermark columnเดิม
   - `_next_output` ตรวจไฟล์ที่มีอยู่จริงก่อนเลือก version เพื่อไม่เขียนทับ outputที่ยังไม่ลง artifact registry หลัง partial failure/retry; regressionตรวจ bytesเดิมไม่เปลี่ยน

5. **Gadget Preview และ manual draft ไม่เข้าระบบสลับช่อง** — TimelineHost เดิมไม่ส่ง channel/snapshot เข้า SequencePlayer; Brief/Source/Evidence/Story/Cut/Timeline ไม่ลงทะเบียน switch participant ทำให้สลับช่องทิ้ง draft ได้
   - Project ใหม่และจาก campaign slot เก็บ captured identity ใน presentation; patch presentation รักษา snapshot และ reject การปลอม/แก้ผ่าน field นี้; artifact render เก็บ snapshot ของ queued job และ GET/build/save timeline คืน snapshot จาก artifact ล่าสุดหรือ project เดิม ไม่อ่าน live profile
   - TimelineHost ส่ง snapshot/channel เข้า SequencePlayer และแสดงคำเตือนเมื่อไม่มี identity ที่บันทึกไว้; ช่องรองไม่มี snapshot ไม่ fallback main
   - เพิ่ม manual draft participant พร้อม saved baseline, failed-save remains dirty, discard และ dirty recheck สำหรับ edit ระหว่าง save; save-and-switch บันทึกเนื้อหาโดยไม่ advance production stage
   - เปลี่ยน key ที่ใช้ project.updated_at/timeline.updated_at ให้ไม่ remount ฟอร์มเมื่อ server ตอบ save; timeline ใหม่ sync ได้เฉพาะ draft ที่ clean จึงไม่ทิ้ง local edit ใหม่
   - เปลี่ยน copy Timeline เป็นภาษาใช้งานและปุ่ม save/split เป็น min-height 44px ไม่มี icon+text ซ้ำซ้อนตาม parent จอง ไม่เปลี่ยน caption/font/style/layout ของวิดีโอ
   - ProductLibrary creation form และ CampaignPlanner draft/sourceDraft ลงทะเบียนกลไกเดียวกัน; draft ไม่ครบคงช่องพร้อม error, discard ไม่ POST, Campaign creation ที่ค้างต้อง await promise เดิมก่อนสลับ ไม่สร้าง POST ซ้ำ
   - Campaign save ใช้ slot จาก PATCH acknowledgement อัปเดตเฉพาะ slot ที่จับไว้ และไม่ rehydrate draft ทุกครั้งที่ response กลับ; invalidates readiness เดิมก่อน refresh เพื่อไม่แสดงสถานะเก่าเมื่อ refresh ล้มเหลว
   - Gadget helpers เป็น re-export alias ของ neutral shared channelDraft/useChannelDraft ที่ recovery agent สร้างสำหรับ Schedule; ไม่มี generic implementation ซ้ำใน components

6. **Full-gate fixture failures ที่ยืนยันแล้ว** — HF 4 failures พึ่ง Studio/สินค้า production และ HTML fixture ไม่มี head; Voice 2 failures เปลี่ยนเฉพาะ api_voice.BASE_DIR ออกจาก config workspace ทำให้ artifact ownership reject ก่อน provider; alpha proxy fixture ใช้โฟลเดอร์ชื่อ projects ที่ไม่ใช่ canonical 03_Projects
   - HF tests สร้าง Studio และสินค้าเจ้าของ main ชั่วคราว มี head สำหรับ frozen metadata และ mock browser/network; invalid composition ID ตรวจ 422/code เดิมของ contract พร้อมย้าย validation ก่อน freeze/storage side effects
   - Voice fixture ใช้ isolated_storage เดียวกับ config โดยคง quota 429/no-fallback assertions; alpha proxy ใช้ canonical temporary workspace + with TestClient และคง actual FFprobe alpha/PTS, Range 206, render master/source assertions

## Evidence

- ก่อนแก้: channel_jobs + mobile_gadget + hyperframes + workflows = **45 passed, 9 warnings**; tests เดิมยังผ่านทั้งที่ lifecycle/HF avatar/mobile signature gaps มีอยู่
- หลังแก้ชุด lifecycle/mobile/HF: **64 passed, 31 warnings** (ก่อนเพิ่ม optional actual-browser test)
- หลังเพิ่ม optional browser test: lifecycle + mobile_gadget + hyperframes = **35 passed, 1 skipped, 9 warnings**; skip นี้เป็น local browser gate ที่รันแยกแล้ว
- Actual browser: `OMNICUT_RUN_HF_BROWSER=1` + pytest `test_channel_hyperframes.py -k actual_hyperframes_browser` = **1 passed, 10 deselected**; ใช้ `hyperframes@0.8.143 check --json --snapshots` จริง และ assert browser ไม่ถูก skip, `ok=true`
- `python -m compileall -q scripts` ผ่าน; `git diff --check` ผ่าน (มี CRLF working-copy notices เดิม)
- Broader related gate: channel_jobs/workflows/stats_producer + api_background_isolation/gadget_media/gadget_media_projects = **83 passed, 3 skipped** (9.96s)
- Gadget identity/legacy product studio/API gate หลังเพิ่ม watermark+collision guard = **15 passed** พร้อม actual FFmpeg libass frame probesสำหรับ main/second
- Gadget API + lifecycle gate หลัง persist project/artifact snapshot = **24 passed, 9 warnings**; draft immutability/preview snapshot HTTP regression ใหม่ผ่านแยก
- Full-gate triage related set (channel_mobile_gadget + api_hyperframes + quota_swallowing_sites) = **40 passed, 11 warnings** (31.27s)
- Manual Gadget editing Node runtime regressions = **6 passed**; frontend production build ผ่าน
- Actual App/Provider/Gadget/Canvas browser gate + canonical alpha-proxy regression = **6 passed, 10 deselected** (11.87s); desktop/mobile save failure→retry→switch และ discard ตรวจ owner ของ PATCH จริง; main/second ตรวจ actual Canvas fillText/strokeText ใช้ frozen identity แม้ live profile เปลี่ยน, missing secondary แสดง warning และไม่วาด main; abort external Google fonts และอ่าน packaged local fonts เท่านั้น
- Final Gadget browser gate หลัง creation/Campaign/shared helper = **9 passed** (16.51s); เพิ่ม invalid creation/discard, Campaign draft/source failed save→retry/discard และ held creation POST ที่ตรวจว่าช่องยังเป็น main จน request เดิม settle และไม่มี POST ซ้ำ
- Expanded owned backend gate (lifecycle/mobile/HF/Gadget/legacy Product Studio/API/quota) = **101 passed, 1 skipped, 33 warnings** (100.53s); optional actual HF browser skip เคยผ่านแยกตาม evidence ด้านบน
- Alpha proxy teardown เคยติด SQLite handle หลัง shared conftest เปลี่ยนเป็น TemporaryDirectory; recovery agent เพิ่ม gc หลังปิด worker/current-thread handles และ owned test ใช้ TestClient context manager แล้ว final gate cleanup ผ่าน ไม่มี ignore cleanup error
- Warnings เป็น datetime.utcnow deprecation ที่ shot_lists_store/recording_sessions ซึ่งไม่ได้แก้ในชุดนี้
- Tests ใช้ conftest temporary storage + monkeypatch/offline engines; browser fixtureใช้ TemporaryDirectory และ cleanup ทั้ง HTML/image/cache/snapshotทันที; ไม่ render MP4/ลง production registry/แก้ Raw/Assets ของจริง

## Remaining limits ที่ต้องไม่อ้างว่าผ่านครบ

- Gadget outputเดิมไม่มี watermark; รอบนี้เพิ่ม watermark จาก frozen snapshotตาม parent สั่ง ภาพ probeยืนยันเฉพาะregionดังกล่าว ไม่มี Gadget follow/avatar overlays ใหม่; Gadget Canvas content/owner ยืนยันด้วย actual browser แล้ว แต่ไม่อ้างพิสูจน์ caption/callout/audio parity ทั้ง renderer
- Actual HF gate รอบนี้ตรวจ frozen avatar URL/runtime/asset ใน browserจริงบน static temporary fixture; ไม่ใช่ actual MP4 ของ production composition และไม่พิสูจน์ timing/font/main-vs-secondary parityทุก template
- Existing pipeline ASS identityใช้ watermark content; follow/avatar layout ไม่ปรากฏใน renderer เดิม ไม่เพิ่ม layout เองใน audit นี้
- Global/frontend identity transport, SequencePlayer watermark parity และ full AC01–AC17/full backend/frontend/build gates เป็นงาน parent; รายงานนี้ไม่แทน final acceptance
- No live posting, migration apply/rollback, account login, commit หรือ production render ถูกเรียก

## Frontend second-opinion (read-only, parent owns fixes)

- `useProjectAutosave` เดิมไม่ advance saved baseline จึง dirty หลัง save success; แจ้ง parent และอ่าน final call path พบ parent อัปเดต baseline เมื่อ request สำเร็จโดยตรวจ baseline generation แล้ว
- Transport เดิมตรวจ stale epochเฉพาะsendที่สำเร็จ; parent แก้ rejected sendให้ reject stale responseก่อน caller consume แล้ว และ scoped Node gate ด้านล่างรวม regression late failed response
- อ่าน path พบ HyperFramesHub newClipId/scriptText/selection และ ProducerHub idea/target modal/note edits/AI proposal เสีย draft เมื่อ channel workspace remount; parent อนุมัติจองสอง Hub รวม optional captured token ของ producer note/upload API และ bound-storage arguments ของ producerInsights แล้ว
- NewClipPanel และ MobileQuickStudio เก็บ form/workflow ใน storage ของ captured channel จึงไม่จัดเป็น draft loss ปกติจากการสลับช่อง (ยังไม่ยืนยันกรณี browser storage ใช้งานไม่ได้)

## Manual forms final checkpoint — Codex (GPT-6)

ดำเนินการโดย: Codex (GPT-6). Reservation ที่ parent อนุมัติ: `frontend/src/components/hyperframes/HyperFramesHub.jsx`, `frontend/src/components/producer/ProducerHub.jsx`, optional producer note/upload token ใน `frontend/src/api.js`, optional bound storage ใน `frontend/src/lib/producerInsights.js`; browser regression อยู่ไฟล์เดิมที่จอง `tests/motion_capture/test_channel_gadget_browser.py`.

- HyperFrames เก็บ clip ID/style/product/angle/scenario/script เป็น draft ใน cache ของ captured channel ผ่าน neutral `useChannelDraft`; Save-and-switch เก็บ draft ในเครื่อง ไม่สร้างคลิปหรือ render เพิ่ม; failed create ไม่ล้างบท, pending create fence การสลับช่อง
- Producer เก็บ idea/URL/images/tag/product, target modal, note edit และ AI proposal ใน draft ของ captured channel; failed POST ไม่แสดงโน้ตสำเร็จหรือล้างฟอร์ม; image upload และ add/edit/confirm angle pending fence การสลับช่อง
- Producer cache callbacks ผูก storage ตั้งแต่ mount; note/upload wrappers ส่ง captured tokenจริงผ่าน transport `channelToken`. Edit ส่ง `base_revision` ที่จับตอนเปิด modal; pin/delete ACK advance revision ก่อนแก้ถัดไป; 409 เก็บข้อความไว้; Save-and-switch เก็บ draftโดยไม่ retry server mutation เงียบ ๆ
- Server ACK ไม่ล้างข้อความใหม่ที่พิมพ์ระหว่าง pending POST; storage save error ใน switch dialog เก็บ owner/form ไว้จน retry; discard ไม่มี server POST เพิ่ม
- Actual offline browser combinedล่าสุด **15 passed / 25.46s** (Gadget9เดิม + manual forms6 รวม AI proposal/pin→edit409 revision2); เพิ่ม held-upload แล้ว scoped pending note/upload **2 passed / 4.01s**, รวม unique browser cases16. Upload first Save-and-switch waits then runtime rechecks dirty/stays main พร้อม retry alert; retry เก็บ final URL+newer textแล้วswitch/returnmainได้ ไม่พบ draft loss จึงถอน speculative completion-cache change. Browser fixtures mock deterministic API rows, abort Google fonts,ไม่มี live provider/posting; revision regressionตรวจ HTTP request bodyจริงจาก UI ไม่ใช่ source-only test
- Scoped Node gate producerInsights/channelDraft/gadgetChannelEditing/channelTransport **40 passed**, production build **passed / 585ms** (`.tmp/codex-workflows-manual-final-build.log`). Backend owned gateก่อนหน้า **101 passed,1 skipped** และ optional actual HyperFrames browserผ่านแยกตามรายละเอียดข้างต้น
- Source/tests/backend freeze แจ้ง parent แล้ว; full backend/frontend final acceptance เป็น gate ของ parent ยังไม่อ้างว่าทั้งแผนผ่านจากผล scoped นี้

## Jev

- Jev ตรวจจากสรุป scope (ไม่ได้อ่านไฟล์เอง): risk **1.33/4**, confidence **0.54**, verdict escalate; ใช้ user override เดิมให้เดินต่อด้วย review/tests
- Initial inline JSON/PowerShell BOM calls failed ก่อนแก้ UTF-8 no-BOM จนได้ผลข้างต้น; scratch state ถูกลบทันที
- Jev ไม่ถูกใช้ยืนยันภาพ/ฟอนต์หรือเป็นสิทธิ์อนุมัติ
- Jev after-fix/reportตรวจจากสรุป: quality **2.14/4**, confidence **0.25**; improved noul **0.84**, confidence **null**; ใช้ user override เดิมและ testsต่อ
- Jevก่อน Gadget FFmpeg frame probe: risk **0.76/4**, confidence **0.70**, verdict escalate; ใช้ user overrideเดิม
- Jevก่อน actual Gadget browser/temporary FFmpeg fixture: risk **0.94/4**, confidence **0.75**, verdict escalate; ใช้ user overrideเดิมเพื่อเดินต่อด้วย offline tests; scratch JSON ลบทันที
- Jev final manual draft/report checkpoint: risk **2.08/4**, confidence **0.70**, verdict escalate; ใช้ user overrideเดิมและ meaningful scoped gates; scratch JSON ลบทันที ไม่มีการอ้างคะแนนเป็นหลักฐานว่า ACผ่าน
