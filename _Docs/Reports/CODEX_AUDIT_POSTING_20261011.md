# Posting / Stats / Extension Audit — 2026-10-11

ดำเนินการโดย: Codex (GPT-6), delegated agent audit_posting

## Ownership และขอบเขต

Parent จองให้แก้ `posting_jobs.py`, `api_tiktok_autopost.py`, `api_tiktok_stats.py`, `api_exports.py` เฉพาะ outcome helper/mark_posted, `tiktok_pending.py`, extension background/sidepanel, posting/stats tests และ release route policy/count test เท่านั้น รอบและสารบัญอยู่ใน TODO ของ parent

ตรวจ actual prepare → claim → validate → attempt → ack/reconcile → file/registry/product/PostLog/queue effects; account DOM/tab guard, restart/lease และ stats matching เทียบ PLAN AC07–AC10

ทางเลือกที่เล็กที่สุด: รักษา durable protocol เดิม เพิ่ม guard ที่ boundary จริงและ repair signals แทนออกแบบคิวใหม่ ข้อมูล production `_Docs/channels.json`, `posting_jobs.json`, schedule/post log ไม่ถูกแก้ ไม่รัน TikTok/live account/production migration/commit

## Findings ที่แก้

1. **Blocker AC07: บัญชีเปลี่ยนระหว่าง backend await แล้วคลิกผิดบัญชี** — ก่อนแก้ `guardPostingAction` อ่าน DOM → รอ `/attempt`/storage → `clickPostButton` กด DOM แยกคำสั่งโดยไม่มี account check ในคำสั่งคลิก อ่านอย่างเดียวด้วย Node VM ได้ `accountCapturedBeforeAwait=@mainuser`, `clickedAs=@wronguser` แม้ callback guard จบแล้ว
   - แก้ `background.js:1713`, `:1747`: อ่าน normalized identity และ lease expiry ใน DOM expression เดียวกับ final click หลัง backend/storage await, unreadable/multiple/mismatch หยุด
   - ปิด unknown-account posting ทุกโหมดที่ `posting_jobs.py:28`, worker guard ไม่ใช้ main compatibility เพื่อข้าม AC07 อีก
   - Regression รัน DOM expression จริง เปลี่ยน account ระหว่าง callback แล้ว assert clicks=0

2. **Major AC09: success toast เก่าใช้ยืนยันงานใหม่ได้** — ก่อนแก้ `waitForPostConfirmation` พบ visible “Posted successfully” ก็ confirmed แม้ editor/tab ยังเป็น upload; Node VM ยืนยันผลนี้
   - แก้ `background.js:1726`, `:1609`: ติด MutationObserver ก่อน attempt, baseline notices เดิม, เก็บ click-specific token ใน storage/backend; รับเฉพาะ notice ใหม่/เปลี่ยนหลัง click ของ token นี้
   - Backend `PostingJobStore.acknowledge:154` เทียบ token เมื่อ attempt มี token; worker reconciliation ของงานเก่าที่ไม่มี original observation หยุด ไม่เดาผล
   - Regression DOM baseline stale → no confirmation; post-click mutation → confirmed; different token → no confirmation; backend different-attempt proof → reject

3. **Major AC09: PostLog/angle failure ถูกกลืน แต่ effects_applied ถูกตั้ง true** — `_record_posted_in_post_log` catch แล้ว return None; mark_posted คืน success พร้อม status_warning; protocol เดิมไม่อ่านสัญญาณดังกล่าว จึงไม่มี repair รอบถัดไป
   - แก้ `api_exports.py:1127` คืน post_log_incomplete warning และ `api_tiktok_autopost.py:508` ไม่ mark effects complete เมื่อ status/PostLog warning
   - Regression ใช้ mark_posted จริง: inject PostLog OSError หลัง file move → receipt published ยังคง durable + effects false + export posted; retry receipt เดิมหลังซ่อม → PostLog 1 row + effects true ไม่ upload/click ซ้ำ

4. **Major AC08: claim แล้วทำต่อไม่ได้จะค้างจนเลือกช่องใหม่ไม่ได้** — cancel รับ prepared เท่านั้น; worker ไม่ให้เปลี่ยนช่องเมื่อ activeJob แม้ account mismatch/lease expiry/restart
   - เพิ่ม fenced `/release` (`api_tiktok_autopost.py:492`, `posting_jobs.py:211`): cancel เฉพาะ claimed ที่ยังไม่ attempted, ตรวจ original owner/token/revision, expired lease ยอม release เฉพาะเจ้าของเดิม, retry lost response idempotent
   - Queue reset เฉพาะ same posting_job_id; prepare ใหม่ได้หลัง explicit cancellation; attempted/confirmation_unknown ไม่คืน prepared
   - Worker clear local state หลัง server ยืนยัน cancelled เท่านั้น; UI ปุ่ม “ยกเลิกงานก่อนโพสต์” ใช้ secondary style/touch 44px
   - Regression stale owner/token/expired lease/lost reply/restart/foreign channel และ attempted-job rejection

5. **Major AC10: source account unknown ใน main compatibility ยัง merge metrics** — import เดิมผ่าน account warning แล้วเรียก PostLog.upsert โดยตรง ขัด PLAN §6 และ AC10 unknown account ไม่ merge
   - แก้ `api_tiktok_stats.py:192`: unknown main เก็บ quarantine pending เท่านั้น matched/updated/registered=0; strict/secondary unknown ยังคง reject; known source/account metadata เก็บกับ pending
   - Metadata account_unverified/source_account คงอยู่ผ่าน pending → ignored → restored; attach unknown ต้องซิงก์จากบัญชีที่ยืนยันได้ก่อน
   - Regression existing exact video id metrics10 ไม่เปลี่ยนเป็น999 เมื่อ account unknown; ignore/restore ยัง attach ไม่ได้; verified sync จึง update และเคลียร์ pending
   - Legacy matching tests ระบุ known source account จริงใน fixture เพื่อทดสอบ matching โดยไม่พึ่ง unsafe unknown path

6. **UI narrow header ทับ title/action ที่320px** — offline screenshot พบ brand ถูก flex-shrink จนชื่อซ้อนปุ่ม
   - Parent อนุญาต layout fix: `sidepanel.html` narrow header แยก brand/action rows + grid, min touch44; ไม่เปลี่ยน font family/size/weight
   - Playwright offline route mocks + fake Chrome session ตรวจ420×900/320×740: header boxes ไม่ทับ, buttons≥44px, release buttonไม่ล้น และ click ส่ง release-posting-job พร้อม cancellation success

## Verification และข้อจำกัด

- ก่อนแก้ baseline 61 focused Python +46 Node passed แสดงว่า tests เดิมไม่ครอบ boundary defects เหล่านี้
- หลังแก้: 147 passed (`test_channel_posting_protocol`, `test_tiktok_stats_import`, `test_channel_scope`, `test_channel_exports_posts`, `test_channel_schedule`); Node background 49 passed; syntax checks และ scoped git diff --check passed
- รายการ route channel179→180 จาก `/release`; explicit policy assertion เพิ่มแล้ว Test milestones เดิมอาศัย index ของ list ที่เรียงเวลา/ID ทำให้ flaky; เปลี่ยนเลือก product_name เป้าหมาย
- Offline UI images ตรวจแล้ว และลบออกจาก `.tmp` หลัง verification; tests ใช้ temp storage/conftest production write guard ไม่มี render/export จริง
- AC07–AC10 ถือว่าผ่าน paths ที่ตรวจ offline เท่านั้น ไม่อ้างว่าทดสอบบัญชีจริง/live TikTok selectors; DOM selector ที่เปลี่ยนจะ fail closed ต้อง validate readiness ก่อน live cutover
- Success proof ยังคงเป็น assertion ของ authenticated local extension พร้อม fencing/token มิใช่ server-side signed TikTok receipt; ไม่ถือ Jev/notice string เป็นหลักฐาน platform ภายนอก
- เมื่อ page reload/navigation ทำ original DOM observation หาย จะไม่เดาผลจาก generic toast ต้องตรวจผลเดิมผ่านกระบวนการที่ยืนยันได้; automatic republish ถูกระงับ
- Full backend/frontend/build gates parent เป็นเจ้าของผลสุดท้าย ไม่ใช้ targeted counts อ้าง complete P8 ทั้งโครงการ

Jev อ่านเฉพาะสรุปจาก agent ไม่อ่าน code เอง: initial noul0.71 confidence=null; after-fix quality score2.94/4 confidence0.78 ใช้ user low-confidence override เดิม ไม่เป็นหลักฐานการผ่าน tests

Verdict: defects ที่มี reproduction ข้างต้นแก้และมี regression; ส่งเข้า full gates และยังต้องตรวจ selector readiness บัญชีจริงก่อนเปิด live posting

## Checkpoint เพิ่มเติม — confirmed outcome และ P7 profile UI

ดำเนินการโดย: Codex (GPT-6), delegated agent audit_posting; parent จองเพิ่ม `ChannelSettings.jsx`, `channelProfileForm.js/.test.js`, `test_channel_profile_browser.py` และบันทึกขอบเขตใน TODO

- **Major AC09 durable receipt repair ใช้ helper ของ manual posting ผิด boundary**: `_apply_outcome_effects` เดิมเรียก `mark_posted` ซึ่งปฏิเสธ export เก่าที่แพลตฟอร์มยืนยันแล้วเมื่อมี render ใหม่ และ legacy helper เลือก queue ด้วย export/basename ก่อน exact job check ท้าย path จึงอาจมาร์กคิวที่เปลี่ยนเจ้าของแล้ว ข้อค้นพบแรกจาก actual call-path; regression ยืนยัน manual latest-export guard ให้409 แต่ confirmed receipt ต้องซ่อมของเดิมได้
- แก้ `api_exports.py:991` เพิ่ม internal `apply_posted_outcome` รับเฉพาะ published job พร้อม receipt_hash/owner/export ตรงกัน; HTTP `mark_posted` คง latest-export guard เดิม `api_tiktok_autopost.py:528` ส่ง canonical job หลัง ownership/content hash/account/proof checks เดิม
- `api_exports.py:1057` preflight queue_id/export_id/posting_job_id/status ก่อน file effects; protocol ไม่ใช้ legacy matching queue helper; final queue transaction ยัง fenced ตาม job เดิม เมื่อคิวถูก rebind จะ409 ไม่มีการย้ายไฟล์/มาร์ก registry/คิวใหม่ และ durable receipt คง effects_applied=false ให้ตรวจผลเดิม
- เมื่อ confirmed export ถูก supersede ซ่อม file/registry/PostLog เดิมได้ แต่ไม่ย้าย cover ตาม angle ใหม่ ไม่ทับ angle ใหม่ และไม่ archive project ใหม่ (`api_exports.py:1063`, `:1128`, `:1176`); regression actual temp product/export versions ตรวจ newest bytes/status/angle export_id ไม่เปลี่ยน
- P7 UI เพิ่ม profile fields/readiness inline, draft create expected_registry_revision, PATCH/lifecycle expected_revision, archived read-only และ disabled noop บัญชีแสดงผลการตรวจจริงเท่านั้น ไม่สร้าง verified binding จาก form
- Dirty participant จับ snapshot channel ID/revision และ runtime-issued opaque token (ห้าม clone token เพราะ guard ตรวจ identity) บันทึก owner เดิมก่อนสลับ; baseline หลัง refresh ไม่เกิด false dirty และ draft create บังคับ posting_enabled=false
- Cross-review พบ discard ระหว่าง server mutation ยังทำให้สลับ B ก่อน A เสร็จได้ แก้ `ChannelSettings.jsx:103` ปฏิเสธ discard ขณะ busy พร้อมข้อความชัดเจน ทุก operation รวม lifecycle ใช้ busy guard; actual browser held PATCH ตรวจ main ยังเป็น owner และ dialog error ก่อนปล่อย response
- Actual App/Provider/API browser fixtures mock **ทุก** `/api` request; ตรวจ320/1440px save revision, busy discard reject, save/discard switch, registry revision create, activate/archive และ readonly/no horizontal overflow; เพิ่ม aria-label ให้ profile inputs เพื่อชื่อฟิลด์แยกจาก help text และ archived readiness copy ไม่กล่าวว่าพร้อมสร้างงาน
- Node profile5 + extension49 =54 passed; Vite build passed (font URLs runtime warnings เดิม) Browser2 passed และรันซ้ำ390px ผ่าน; screenshots320/390/1440 +390 busy ตรวจอ่านแล้ว ส่ง parent ตรวจและลบหลังรับภาพ ไม่มี live APIs/production writes
- Expanded final targeted Python/browser gate **164 passed/70.05s** (`test_channel_posting_protocol`, stats, scope, exports/posts, schedule, existing autopost, actual profile browser); full project gate/report ให้ parent สรุป ผล147เดิม superseded; scoped diff check clean และ oxlint0error/1warning (effect synchronize selected profile → local form baseline)
- Jev final summary-only score2.37/4 confidence0.37 ใช้ user override เดิม ไม่อ้าง confidence เป็น test evidence; screenshot parent พบ global Topbar clip narrow screen ซึ่ง parent เป็นเจ้าของแก้ ไม่แก้ซ้อนใน agentนี้

## Final race review — product mutation transaction

ดำเนินการโดย: Codex (GPT-6), delegated agent audit_posting; parent อนุมัติเพิ่ม `product_store.py` เฉพาะ update_angle_status CAS และ regression

- Parent cross-review พบ preflight superseded check ยังเกิดก่อน file move จึงไม่ atomic กับ angle mutation; deterministic regression แทรก register/new-render ก่อน update_angle_status จริง **ล้มก่อนแก้**: angle.export_id ของเวอร์ชันใหม่ถูกแทนด้วย export เดิม
- `product_store.py:873`, `:988` เพิ่ม optional require_latest_export สำหรับ receipt เท่านั้น: ภายใน scoped_mutate/BEGIN IMMEDIATE อ่าน export_registry ด้วย raw SELECT บน connection/store.db เดียวกัน ไม่มี nested transaction/import; ตรวจ angle.export_id และ newer registry file mtime ก่อนแก้ angle เมื่อ superseded คืน None โดยไม่เปลี่ยน product; api helperยังซ่อม receipt/export/PostLog เดิมได้
- ไม่ใช้ latest_for_angle ใน CAS หลัง mark registry เพราะ helperนั้น prefer Posted evidence จึงคืน old published export แม้ render ใหม่มี mtime สูงกว่า Regressionทั้ง new angle linked แล้วและ new registry commit ก่อน angle link ผ่าน
- Durable job มี frozen export แต่ไม่มี frozen project/angle cover owner: protocolจึงย้ายเฉพาะ companions ชื่อเดียวกับ export และไม่ autoarchive project จาก mutable angle pointer; HTTP manual postingคงพฤติกรรมเดิม การ archive งาน protocolต้องผ่านกระบวนการที่มี project ownership ชัดเจน
- Broader posting/product/export gate84 passed ก่อนเพิ่ม second race parameter; race2passed หลังเพิ่ม; Node profile6+extension49 =55passed; actualbrowser320/390/1440 =3passed11.03s หลัง parent Topbar fix พร้อม geometry assertion selector/icon/actions ไม่ทับและ actionทั้งกล่องอยู่ viewport (ไม่อาศัย page overflow อย่างเดียว)
- profileFailureรองรับ FastAPI422 validation detail array เป็น field/text ไม่ส่ง object child เข้า React; helper regression passed
- Read-only outsider review parent/runtime/transport/autosave/provider + workflow Gadget dirty save/discard guard ตาม actual path ไม่พบ concrete defects เพิ่ม ไม่แก้ cross-owned files
- Final expanded Python/browser gate **204 passed/61.22s** หลัง CASทั้ง2parameter, products/posting/stat/scope/exports/schedule/autopost/profile3widths; CAS raw SELECT ใช้ cached `_connection_for` (ไม่เรียก table setup/DDL ภายใน write) และ fail closed ถ้า connection ไม่อยู่ใน transaction หลังปรับ connection probe posting30passed/9.05s และ scoped diff check clean
- Parentตรวจ final3 + review3/busy1 แล้ว ACK; cleanup exact owned PNG7ไฟล์และassertทุกไฟล์ไม่มีเหลือ ไม่แตะภาพอื่น/production assets
- Final Jev after race noul0.31 confidence=null ใช้ override เดิม ไม่เป็นหลักฐานผ่าน; full gates/live cutover verdictยังเป็นของ parent

## CAS ambiguity follow-up — copied file metadata

ดำเนินการโดย: Codex (GPT-6), delegated agent audit_posting; parent อนุมัติ narrow guard ภายใน ProductStore mutation เดิม ไม่เปลี่ยน global registry schema/order

- Cross-review parent พบ mtime-only CAS ไม่พอ; regression actual confirmed ack แทรก new registry row กับมุมยังไม่ผูก export, `created_at` เท่ากันระดับวินาที และ file mtime100/50 เทียบเดิม100 **ล้มก่อนแก้2กรณี**: มุมกลายเป็นpostedพร้อมชี้ exportเก่า
- `product_store.py:1010` เปรียบเทียบ immutable registry created_at ภายใน SQLite write transaction เดิม เพิ่มจาก mtime; registrationใหม่กว่า independentจากเวลาไฟล์ต้องไม่แก้ mutable angle; competing rows เวลาเท่ากัน/เวลาไม่ครบหรือเทียบ timezone ไม่ได้จะ abstain ไม่เดาลำดับจาก UUID/rowid และไม่ใช้ Posted priority
- Regression20กรณี: mtimeใหม่กว่า/เท่ากัน/เก่ากว่า × initial angle bound/unbound × new angle linked/unlinked พร้อมsame/newer/missingcreated_at; confirmed oldexport/receipt/PostLogยังซ่อมสำเร็จ effects_applied=true แต่ currentangle/renderใหม่ไม่ถูกทับ
- Latest combined posting/ProductStore/exports gate **103passed31.24s** (supersedes84/99ในขอบเขตนี้); scoped diffcheck clean; ไม่มีproduction assets/writes/liveposting ภาพทดสอบชุดก่อนcleanupครบแล้ว
- ข้อจำกัดตามจริง: registryไม่มีmonotonicregistrationsequenceและcreated_atเป็นseconds ดังนั้น ambiguous tie/missingtimestamp ไม่อ้างว่าเลือกactive/latestได้และคง mutableangleเดิมไว้ แม้ publishedreceipt/export/PostLogเดิม appliedแล้ว ต้องเลือกมุม/exportที่เป็นเจ้าของงานชัดเจนผ่านworkflow ไม่republishเพื่อซ่อม local status
- Targeted20 cases rerun **20passed9.64s** หลังเพิ่มassert oldexportposted/PostLogexactly1; Jev follow-up noul0.63 confidence=null ใช้ useroverrideเดิม ไม่ถือเป็นtestevidence; backendownedfilesfreezeแล้ว Fullprojectgateparentเป็นเจ้าของ

## Tracker / Mobile QuickPost outsider review

ดำเนินการโดย: Codex (GPT-6), delegated agent audit_posting; parent จองเพิ่ม `test_channel_tracker_browser.py`, `MobileQuickPostPage.jsx`, `test_channel_quick_post_browser.py` และ narrow Tracker success guard พร้อมหยุดแก้ไฟล์ซ้อน

- Trace Tracker actual owner-bound channelLocalStorage → trackerDrafts → failedDraftWrites switch participant → Provider save/discard; QR actual anchor href ใช้channel/parent/export/video ของsecond; actualbrowserยืนยัน main/second ที่ export ID เหมือนกันไม่ปน caption/QC draft
- ทดสอบ QC server503 เก็บ modal/noteไว้ และ switch second→main เปิด noteเดิมได้; บล็อกlocalStorage.setItemเฉพาะ tracker.manualDrafts แล้ว save-switchต้องคงmainพร้อมalert, explicitdiscardจึงสลับsecondและเห็นdraftsecondเดิม
- **Concrete failureพบเพิ่ม:** Tracker `handleQcPass` await status helperที่คืนfalseเมื่อ503 แต่ยังแสดงQCผ่านและปิดpreview; browserก่อนแก้พบmodalหายหลังserverfail แก้ `ContentTrackerHub.jsx:1564` ตรวจsavedก่อน success/close; regressionต้องเห็นerror+previewเดิมและไม่มีQC success
- **QuickPost false local success:** branchไม่มีparent/fileยังsetIsPosted(true)โดยไม่เรียกserver และ branchไม่มีparentเมื่อserverrejectไม่มีcatch; แก้ `MobileQuickPostPage.jsx:93`, `:174` require exactexport+validownerfileทั้งdisabled/handler พร้อมcatchรวมทุกbranch ไม่มีmutation/successเมื่อinputไม่ครบหรือ503; inlineerrorอธิบายmissingexport/file
- Angleปัจจุบันที่postedคนละexport ไม่ถือว่าQRexportเดิมโพสต์แล้ว (`MobileQuickPostPage.jsx:65`); browserกรณีnewer_angle_postedยังส่งexactQRexportและเก็บสถานะunpostedเมื่อserverปฏิเสธ
- Initial parentnativeQuickPosttests2 + newcases5 + Tracker1 =8 actualbrowser **passed11.65s** หลังinlinealert; Node trackerDraft1+profile6+background49 =56passed และVitebuildpassed; scopedgitdiffcheckclean ทุกรายการAPI/networkmock, ไม่เปิดTikTok/ดาวน์โหลดไฟล์จริง/สร้างภาพใหม่
- BackendCAS/datafilesคงfreeze ไม่มีแก้backendในช่วงreviewนี้ ข้อจำกัดreceipt/live readinessเดิมคงอยู่ ManualQuickPostต้องให้ผู้ใช้ยืนยันการโพสต์จริงและserverยอมรับidentity จึงบันทึกlocalposted ไม่เป็นserver-signedTikTokproof
- Jev reviewsummary noul0.60 confidence=null ใช้existinguseroverride ไม่เป็นtestevidence; Tracker/QuickPostownedfilesfreezeแล้ว

## CoverStudio captured scope / manual form final review

ดำเนินการโดย: Codex (GPT-6), delegated agent audit_posting; parent จองเพิ่ม CoverStudioModal, captured-token wrappers ใน api.js และ new offline browser test; backend owned filesคง freeze

- Read-only actual path: Gallery/Tracker render CoverStudioModal; hookText/subText/aiPrompt และ source/crop/overlay อยู่ local React state ไม่มี switch participant/persistence เดิม; ปิด modalด้วย X/ยกเลิกไม่มีการแจ้งทิ้งร่าง แล้วเลือกช่องทำให้ main.jsx:10 App key remountทิ้งข้อมูล ไม่มี before-fix browser assertionที่ยืนยัน failureนี้: ข้อนี้เป็น source trace ตรงและหลังแก้ใช้actualbrowserยืนยันพฤติกรรม ไม่อ้าง failed fixture setupเป็น product failure
- CoverStudioModal:123–162 ใช้ neutral createChannelDraftParticipant กับ explicit switch participant: save-switchแจ้ง `บันทึกปกก่อนสลับช่อง หรือเลือกทิ้งการแก้ไข` ไม่เรียก render/AI; discardขณะงานกำลังบันทึก/สร้างปฏิเสธพร้อมข้อความ จึงไม่ข้าม ownerระหว่างงาน; ปิด modalที่dirtyต้องยืนยันทิ้งร่าง ปฏิเสธแล้วข้อความยังอยู่
- CoverStudioModal:509–557 จับdraft+preview signatureก่อนawaitrender และmarkSaved snapshotนั้นเมื่อcanonical cover renderสำเร็จ การแก้ข้อความเพิ่มระหว่างรอยังคงdirty; renderProCoverและTracker updateAngleCover followupใช้opaque capturedowner tokenเดียวกัน (api.js:179/:333, Tracker:1351/:1364) พร้อม current-owner check ไม่สร้างtokenใหม่หลังawait
- Actual delayed render caseพบ success previewถูกล้างหลัง Gallery refresh ส่งvideoItem objectใหม่ effectเดิมขึ้นกับobjectidentity; narrowแก้ dependencyเป็นvideoPath/productName/angleTitle/product_id/timeline fields (CoverStudio:228) จึงไม่รีเซ็ตsource/cropหรือsavedpreviewเมื่อข้อมูลเจ้าของคลิปเหมือนเดิม หลังแก้delayedsave/neweredit+successpreview+dirtyconfirmationผ่าน
- Native URLs: server candidate thumb_urlที่ไม่มีqueryไม่ใช่ runtime failureด้วยตัวมันเอง เพราะ channelTransport.channelMediaDataเติมcarrierแบบrecursiveก่อนcomponentรับ; ไม่อ้างเป็นdefectที่พิสูจน์แล้ว เพิ่มtoMediaUrlพร้อม capturedownerที่native image9sitesเป็นdefensive normalizationของlegacy/raw paths และactualbrowsercandidateยืนยันsecondcarrier Shared/data/blob/external semanticsตามhelperเดิม
- New `test_channel_cover_studio_browser.py`3กรณี: unsaved, render503, delayed successful renderพร้อมneweredit; real modal close-click/confirm-dismissรักษาข้อความ, programmatic channel selector+switch button handlersตรวจguardขณะmodal overlay, busyclose disabled/discardreject, actualsecond header+secondvideo payload, explicitdiscardจึงswitchmain และswitchไม่มีextra render/AI ทุกรายการnetwork/API mock
- Final scoped actual browser gate Cover3+Tracker1+QuickPost7 **11passed18.79s**; neutral draft/profile/Tracker Node **12passed**; Vitebuildpassedหลังsourceสุดท้ายและscoped diffcheckclean ไม่มีnew screenshots/media/download/productionwrites
- Limitationตามจริง: CoverStudio modalบัง channel selector และswitchdialogz100อยู่หลังcoverz10000 ดังนั้นswitch handler guardทดสอบผ่านprogrammatic selection/buttonclick ไม่อ้างว่าเป็นpointer-accessible journey; real usercloseใช้explicitdiscardconfirmation ป้องกันsilentloss ร่างCoverไม่ได้persistข้ามreloadหรือbrowserclose, save-switchต้องให้ผู้ใช้บันทึกปกด้วยปุ่มเองก่อน ไม่autoAI/render ไม่มีcosmeticiteration
- Jev reviewsummary noul0.61 confidence=null ใช้existinguseroverride ไม่เป็นtestproof; Cover/Tracker/API/newtestsourcefreezeแล้ว parentเป็นเจ้าของfullgateและfinalverdict

## Cover / neutral draft F5 guard checkpoint

ดำเนินการโดย: Codex (GPT-6), delegated agent audit_posting; parentบันทึกTODOreservationและอนุมัติ narrow `useChannelDraft.js`+CoverStudio beforeunload หลังชุดbrowserก่อนหน้า84965จบ7passed ไม่มีHMRแก้ระหว่างgate

- User/parentชี้AC06 F5 limitation จึงทำactualbrowser regressionก่อนแก้: dirty Cover reloadไม่เกิดnative beforeunload dialogและหน้าreloadไปแล้ว (`test_channel_cover_studio_browser.py` unsaved case **failed timeout8s**, ไม่ใช่setupfailure) ยืนยันการสูญร่างเงียบ ๆ ที่reportก่อนหน้ายังเป็นเพียงsource trace
- Neutral `hooks/useChannelDraft.js`เพิ่มsynchronous beforeunload guardตรวจparticipantผ่านref.current.isDirty() ซึ่งรวมpendingoperation; Coverใช้customparticipantจึงเพิ่มguardของตนตรวจisOpen+busyRef/draft.isDirtyด้วย ไม่เรียกasyncsave/AI/render/networkระหว่างunload ทำเพียงpreventDefaultและreturnValueพร้อมcleanup listener
- Actualbrowser4cases **passed12.77s**: dirty/failure/newereditเรียกnative beforeunload confirmationจริง dismissแล้วcurrentowner/formยังเดิมและไม่มีextra writes; explicitdiscardหลังswitchreloadได้; canonical successfulrenderโดยไม่มีnewereditreloadได้โดยไม่ถูกบล็อก NoBlob/FileJSON persistenceหรือcosmeticchanges
- Bounded final Cover4+Gallery1+Workspace3 actualbrowser **8passed24.20s** หลังguardsourceครบ ไม่มีnewfailure; ไม่ขยายreview/testscopeต่อ
- Vitebuildpassedหลังguardsourceสุดท้าย; scopeddiffcheckclean; ข้อจำกัดไม่persistร่างข้ามbrowserkillยังจริง แต่reload/navigationที่browserรองรับbeforeunloadไม่ทิ้งร่างโดยไม่มีnativeconfirmationแล้ว จึงsupersede reload-silent-loss limitationข้างบน ไม่อ้างว่าnativeconfirmationเป็นstorage durability
- Jev before/after noul0.76 confidence=null ใช้existinguseroverride ไม่เป็นevidence; backendproduction/data/mediaคงเดิม source/testfreezeหลังcheckpointนี้ Parentเป็นเจ้าของfinalfullgates
