# ผลตรวจละเอียด Mobile ↔ Desktop synchronization

ดำเนินการโดย: Codex (GPT-6) + 3 delegated agents (Codex GPT-6)
วันที่: 2026-10-04 · รอบ CODEX-MOBILE-SYNC-DEEP-AUDIT-20261004
สถานะ: ตรวจและทำแผนแล้ว ยังไม่ได้แก้ implementation หรือข้อมูลจริง
แผนรับช่วง: [MOBILE_DESKTOP_SYNC_HANDOFF_20261004.md](../Plans/MOBILE_DESKTOP_SYNC_HANDOFF_20261004.md)

## ข้อสรุปและขอบเขต

ยังมีปัญหาที่ต้องแก้ ไม่ใช่เพียงหน้ามือถือแสดงผลไม่ครบ: contract ของ export path/identity ทำให้ backend ผูกงานไม่สำเร็จแล้วรายงาน success; frontend สามารถใช้คลิปของสินค้าก่อนหน้า; lifecycle ปกหลังโพสต์และ refresh ข้ามอุปกรณ์ไม่ครบ
รายงานรวม 24 กลุ่มปัญหา โดยรวมอาการที่มีต้นเหตุร่วมกัน ไม่ใช่ 24 บั๊กที่รันครบ end-to-end ทุกตัว ระดับหลักฐานแต่ละกลุ่มอยู่ในตาราง

การแบ่งเอเจนต์: mobile_backend_audit ตรวจ backend/store/task/render/source; mobile_frontend_audit ตรวจ state/filming/restore/intake; desktop_integration_audit ตรวจ Tracker/cover/gallery/post/QC/refresh ส่วน root ตรวจซ้ำจุดสำคัญและทำ API/browser probes
ทุกเอเจนต์อ่าน current working tree ซึ่งมีงานเดิมหลายไฟล์ รายงานไม่ได้ตัดสินว่าใครเป็นผู้สร้างบั๊ก ไม่มี production code edits, commit, AI/TTS/FFmpeg render หรือการอ่าน/ซ่อม media/DB จริง

## หลักฐานที่รันจริง

| กลุ่มตรวจ | ผล | ความหมายและข้อจำกัด |
|---|---|---|
| Root API/store defect probes | 14 passed, 1 warning | ใช้ FastAPI mobile router จริง, ProductStore/ExportRegistry ชั่วคราว, synchronous worker, mock pipeline; assertions ตั้งใจยืนยันพฤติกรรมที่ผิด ไม่ใช่ acceptance หลังแก้ |
| Root browser defect probes | 5 passed | Chromium/React/Vite จริง, API intercept ทั้งหมด, viewport 360×800 และ390×844; ยืนยัน quick-angle missing id/stale memory, BGM payload, null-session restore, footage ข้ามสินค้า, URL เก่าชนะ saved workflow |
| Existing browser regression tests | 6 passed | tests/motion_capture/test_mobile_studio_browser.py; ครอบ happy flow/reload/share menu/errors/reconnect/filming return ภายใต้ mock API |
| Existing Node tests | 13 passed | mobileStudioFlow.test.js + workspaceData.test.js; helper/cache/polling ผ่าน แต่ไม่ได้ mount MobileQuickStudio |
| Frontend agent extracted-handler probes | 4 assertions ผ่าน | Execute handlers ที่ extract จาก source ด้วย Node VM: stale identity, undefined assemble angle, footage leak, ignored posted response; ไม่มี mounted React |
| Integration agent function probes | 6 assertions ผ่าน; cleanup_complete=true | AST compile functions จริง mark_posted/cover hydration/media discovery กับ fake stores/temp placeholder media; ไม่ใช่ HTTP/DB transaction end-to-end |

อย่ารวมตัวเลขทั้งหมดเป็นจำนวน integration tests: ทั้งระดับการจำลองและจุดซ้ำต่างกัน ไม่มี full production suite/physical phone/real TikTok/real exported-frame verification ในรอบนี้
Browser probe รอบแรกผิดที่ locator ของ sr-only checkbox; รอบถัดมาผิดที่ API ของ test harness; ปรับ harness แล้วได้ 5/5 ไม่มีการแก้ UI และไม่นับความผิดของ harness เป็นบั๊กสินค้า
API probe ตอนเพิ่ม quick-add พบ ProductScraper ไม่มี method scrape; จึงแก้ probe ให้ใช้เส้นทางจริงที่ catch AttributeError และยืนยัน fallback/duplicate โดยไม่ยิง scraper จริง

คำสั่งหลักที่รัน:

```powershell
.venv/Scripts/python.exe -m pytest .tmp/mobile_sync/deep_audit_probe.py -q -p no:cacheprovider --basetemp=.tmp/mobile_sync/deep_probe_data4 --disable-warnings
.venv/Scripts/python.exe -m pytest .tmp/mobile_sync/browser_deep_probe.py -q -p no:cacheprovider --disable-warnings
.venv/Scripts/python.exe -m pytest tests/motion_capture/test_mobile_studio_browser.py -q -p no:cacheprovider --disable-warnings
# cwd frontend:
node --test src/lib/mobileStudioFlow.test.js src/lib/workspaceData.test.js
```

Probes ชั่วคราวและข้อมูลถูก cleanup หลังบันทึกผล; คำสั่งสองบรรทัดแรกเป็นคำสั่งของรอบตรวจ ไม่ใช่ไฟล์ถาวรที่จะรันต่อได้ ผู้รับช่วงต้องสร้าง behavioral regression tests ใน tests/lib ก่อนแก้ โดยใช้สถานการณ์ที่อธิบายด้านล่าง

## กลุ่มปัญหาและ trace ที่ยืนยัน

P0 = ผูกผลงานผิด/ใช้วัตถุดิบผิด/แสดงปกเสียที่กระทบส่งงาน; P1 = workflow/state/persistence ไม่ครบ; P2 = preflight/robustness ที่ยังขาด ระดับเป็นลำดับเสนอแก้ ไม่ใช่การประเมิน production incident ที่วัดจาก telemetry
ตำแหน่งบรรทัดอิง current tree ณ รอบตรวจ ค้นชื่อฟังก์ชันก่อนแก้ เพราะไฟล์มีงานอื่น

| ID / ลำดับ | ปัญหาและผลกระทบ | Trace / input ที่เปิดเผย | หลักฐาน |
|---|---|---|---|
| M01 / P0 | render completed ทั้งที่ผูก angle ไม่สำเร็จ | video_assembly_stage.py:365–373 คืน export_id → mobile_quick_studio.py:537,550 ส่ง media URL → product_store.py:575–579 reject filesystem path mismatch → mobile:554–557 กลืน error/complete task; complete_job ไปก่อนที่541 | API probes จริงพร้อม temp export_id และ injected store failure |
| M02 / P0 | quick-angle/quick-add DTO ไม่ตรง catalog; render angle_id หาย และจำมุมเก่า | mobile:64–78,233–249 คืน angle_id/hook_title/script_text; MobileQuickStudio.jsx:243,270,303 รับตรงแต่398อ่าน .id; rememberWorkflow:360อ่าน stateเก่าหลังsetState | Browser ส่ง request ไม่มี angle_id →422; saved identity เก่า; handler probe |
| M03 / P0 | footage จากงาน A ไปงาน B และ intake race | MobileQuickStudio.jsx:222–230,724,1179–1191 ไม่ reset uploadedVideoPath; upload314–328ไม่มี owner/version guard; render395ใช้ pathเก่า และ1037ไม่ block upload pending | Browser ยืนยัน payload product B + raw/upload-a.mp4; delayed/reordered race ยังเป็น code trace |
| M04 / P1 | ปก/identity/QC ของ angle ไม่ถูกส่งให้ mobile และไม่มีทางจัดการปกใน result | mobile:179–198 projectionไม่มี cover/project/export/QC;201ใช้ product thumbnail; MobileQuickStudio:651แสดงภาพสินค้า และ result1121+ไม่มี CoverStudio integration | API probeยืนยันcover fieldsถูกตัด แต่stored coverยังอยู่; UI trace |
| M05 / P0 | ปก9:16หลังpostedเป็น URLเก่า;3:4/9:16มี lifecycleต่างกัน | api_exports.py:634 companionsเฉพาะ_cover.jpg;902ย้ายไปPosted;920อัปเดตvideoไม่cover; api_phase1.py:263–305เชื่อstored path; media_service.py:68ค้นCOVERS_DIR; product_store.py:1881ข้ามposted | 4 function assertionsเรื่องvariant move/hydration/discovery; ไฟล์ถูกย้ายไม่ถูกลบ |
| M06 / P1 | lifecycleมือถือไม่ตรงstore:postedกลายrendered และไม่มีin_productionระหว่างงาน | mobile:175,188 override statusเมื่อมีvideo_url;468–523ไม่update in_production ต่างจากapi_render.py:152–158; readinessอิงpathไม่ตรวจexistence | API probesposted→rendered และpipelineเริ่มตอนangleยังdraft; missing-file availabilityยังtrace |
| M07 / P1 | Trackerที่เปิดบนคอมไม่revalidateผลจากอีกเครื่อง | ContentTrackerHub.jsx:1235–1265fetchเมื่อmount/action;986focus/visibilityอัปเดตวัน; App.jsx:263–298refresh shell/exportsไม่products; TaskContext.jsx:166refreshTriggerไม่มีconsumerในTracker | Code traceครบทั้งApp/context/coordinator; ยังไม่วัดจริงสองอุปกรณ์ |
| M08 / P1 | quick angleใช้draftนอกTracker phases; การไม่เลือกงานวันนี้เป็นอีกเหตุที่ดูเหมือนไม่มีงาน | mobile:71draft; product_store.py:836รักษาdraft; Tracker:36,1614phasesไม่draft;958pickedScriptIdsอยู่localStorage,3187scripted Kanbanfilterตามpicked | API probedraft; code tracefilter ต้องไม่เหมาว่าrenderedถูกpickedfilterด้วย |
| M09 / P1 | URL/storageไม่เปลี่ยนพร้อมworkflowใหม่; task recoveryขึ้นกับsession | MobileQuickStudio:157–158,177URLมาก่อนsaved;359เปลี่ยนstorageแต่ไม่URL;179–187ต้องมีrestoredSession; returnจากfilmingA→เลือกB→refreshกลับA | Browser staleURL/savedBและnull-session; normalcurrentUIสร้างsessionก่อนuploadจึงnull-sessionเป็นcompatibilitycase |
| M10 / P1 | posted response/partial warningถูกกลืน; preview/shareยังpathก่อนย้าย | api_exports:902ย้าย,927–931status_warning,958success+moved; MobileQuickStudio:529ไม่อ่านresponse; MobileQuickPostPage.jsx:80QRpathมาก่อนlivepathและ151ไม่ปรับ; Tracker1324/Gallery1325ไม่อ่านwarning | Handler probe ignored moved/warning + function probe successทั้งที่storefail; QRเป็นstatic trace |
| M11 / P1 | latecancelทำtask cancelled/job completed/angle rendered; finalizeไม่ร่วมcancel | mobile:541completejobก่อนpersist; api_mobile_studio.py:152cancelTaskก่อนrequestCancel; render_jobs.py:247ไม่cancelcompleted; task_manager.py:490ไม่completecancelled; finalize recording_sessions.py:252–275ไม่มีcancel hook | API latecancel barrierยืนยัน3stateแตก; finalize subprocessยังไม่รันจริง |
| M12 / P1 | double submit/retryไม่มีactive-attempt dedupe | mobile:463–483สร้างproject/taskใหม่ทุกcall; render_jobs.py:141–182serializeอย่างเดียว | API2callsได้2task/2project; simultaneousraceยังไม่ทดสอบ |
| M13 / P1 | postedยังเริ่มrenderเสียทรัพยากรและได้ผลใหม่ที่ไม่ผูกมุม | mobile415–523ไม่มีpostedguard; product_store:637–638ป้องกันdemoteจึงมุมเดิมยังsealed; desktopapi_render:108–137,307มีguard | APIprobepipelineถูกเรียก/new resultแต่angleยังoldposted; ไม่ใช่เขียนทับposted proof |
| M14 / P1 | คลิปหลายแหล่ง/manual shot mapที่คอมเตรียมถูกทิ้ง | mobile:41–43selected_videos[0];502–523ไม่ส่งmanual_shot_map/clip_list; pipeline_context.py:531defaultว่าง; shot_matching_stage.py:646–650อ่านctxmap; desktopapi_render:218–219forward | APIprobeใช้เฉพาะA; manualmapstatic trace; guided_take sidecarยังทำงานผ่านsource_resolution.py:145–148 |
| M15 / P1 | plan/sessionไม่ตรวจrevisionเมื่อdesktopแก้บท; filmingอ่านแผนล่าสุดแต่segment snapshotเก่า | mobile:376–377ตรวจแค่มีplan; shot_lists_store.py:143is_staleไม่ได้ใช้; recording_sessions.py:130–163reuse/snapshot; MobileFilmingPage.jsx:156–159fetchlatest; shot_matching_stage.py:413–419beatmismatch | Conditional code trace; ไม่รันTTS/footageจริงและยังไม่ยืนยันtopicmismatchเมื่อcountเท่ากัน |
| M16 / P1 | fallbackสำหรับangle_b2เขียนbatch1แล้วสร้างsessionไม่ได้ | mobile:385,391hardcode1; shot_lists_store:44–63extract2; recording_sessions:123–125หาplanไม่พบ | APIprobegeneratorraises→session400 |
| M17 / P1 | filmingไม่resume uploadedprefix; ถ่ายใหม่แล้วuploadedtakeเดิมถูกใช้; localtakesในRAMหายเมื่อreload | MobileFilmingPage:100,152–161ไม่restoreconfirmedClips;306indexจากlength;444–448skipuploaded;398–406bufferRAM | Code traceของpartialfailure/reload; ยังไม่มีcamera/resume browserprobe |
| M18 / P1 | camera readyก่อนsessionโหลดอาจmountrefไม่ทัน; shotlist errorถูกกลืน | MobileFilmingPage:283–289loadingreturnspinner;176–214cameraeffect[]/canvas[cameraReady]refnull;156catchnull;668recordbuttonไม่ตรวจcurrentBeat | Conditional race/code error trace; ไม่ถือว่าphysicalcamera reproแล้ว |
| M19 / P1 | BGMtoggleไม่เปลี่ยนrenderจริง | MobileQuickStudio:82,1025checkbox; api.js:566–572/schemaapi_mobile_studio:38ไม่มีoption; mobile:513–514hardcodeDEFAULT_BGM/.14 | Browserปิดtoggleแล้วrequestไม่มีBGMfields; backendtrace |
| M20 / P1 | quick-addลิงก์ใช้scraper methodที่ไม่มีและไม่เก็บshop identity/dedupe | mobile:337ProductScraper.scrapeแต่product_scraper.py:611มีscrape_url;catchfallback;347–352ไม่ส่งurl/tiktok_product_id/specs;product_store.py:391dedupeเฉพาะurl | APIprobemockresolverเท่านั้น:ลิงก์เดียวได้2product/namegeneric/urlempty;ไม่ยิงscraper |
| M21 / P1 | caption/hashtagsมือถือไม่ใช้ค่าที่คอมบันทึก | mobile:565hashtagsfixed; MobileQuickStudio:472hook+fixedhashtags; QR/Desktopใช้tiktok_caption/tiktok_hashtagsตามMobileQuickPostPage:76/Gallery:1335 | Statictrace; ยังไม่clipboard/TikTokdeviceprobe |
| M22 / P1 | typeงานมือถือไม่ได้ถูกรวมtasknavigation/restartrecovery | mobile:469type mobile_auto_assemble_render; TaskContext.jsx:298ไม่จัดเป็นrenderและ362เลือกEditorเมื่อมีproject; task_manager.py:53RENDER_TASK_TYPESไม่มีmobile | Statictrace; recoveryเป็นdependencyเมื่อเพิ่มin_production ไม่อ้างว่าrecoveryปัจจุบันทำงานแล้ว |
| M23 / P1 | mobileไม่เห็นQC และsharedAPI markPostedข้ามrejected/unreviewedได้ | mobilecatalogไม่มีqc;api_exports.py:882guardlatestexportไม่มีQC;Tracker/GallerymarkPostedไม่มีsharedgate | Functionprobeqc_note rejected/qc_reviewedfalseแต่postedสำเร็จ; policyต้องตกลง ไม่อ้างdesktop enforceอยู่แล้ว |
| M24 / P2 | preflightพื้นที่ว่างขาดในmobile heavywork | desktopapi_render.py:139–143diskcheck;mobile/pipeline pathไม่พบcheckเดียวกัน | Statictrace; ยังไม่diskfull behavioralfixture |

## ข้อแก้ความเข้าใจจากแผนก่อน

1. ปกไม่แสดงยังไม่เท่ากับถูกลบ: M04เป็นprojection/UIgap; M05เป็นrelocation/stalepath
2. ผลrealpipelineมีexport_idจึงถูกrejectก่อนเก็บURLผิด; mockไม่มีexport_idจึงเก็บURLผิดได้ M01ต้องทดสอบทั้งสองแบบ
3. null-sessionrestoreเป็นcontractgap แต่current UIปกติสร้างsessionก่อนถึงupload; ปัญหาcurrent flowที่reproduceคือstaleURLและstaleangleidentity
4. postedguardในProductStoreทำงาน; ปัญหาคือmobileยังrenderและแจ้งผลใหม่ที่ไม่ผูก ไม่ใช่demotepostedได้
5. guided_take sidecarยังทำงาน; สิ่งที่ถูกdropคือpreparedmultisource/manualmapอีกเส้นทาง
6. งานscriptedที่ไม่pickedวันนี้ไม่ได้หายจากstorage; filterกับdraftต้องแยก และrendered/postedไม่ได้ผ่านpickedfilterนี้
7. QCgateเป็นช่องว่างร่วมปัจจุบัน ไม่ใช่สิ่งที่desktopมีครบแล้ว

## สิ่งที่ยังไม่ตรวจจริงและเกณฑ์หยุดอ้างความครบ

- กล้อง/MediaRecorder/iOS/Android/WebShare permission, RAM pressure, lockscreen/background, physicaldevice และTikTokจริง
- Real TTS/FFmpeg, rendered frames/font/subtitle parity, media quality; scopeนี้เป็นworkflowaudit
- สองเครื่องจริง/network latency/concurrent requests/database transaction/restart/crash during file move
- Production corrupted records/ไฟล์ปกของผู้ใช้จริง; ยังไม่ได้repair/migrate/deleteอะไร
- Full offline suite: บาง mobile tests ยังเรียกshotlist generatorจริง; install_pipelineคืนMP4ไม่มีexport_idทำให้P0หลุด ต้องแก้testisolation/realisticcontractก่อนรันfullsuite

## Jev และการตัดสินใจ

Rootเรียกtools/jev_advisor.py --checkผ่าน; ก่อนdeepauditได้risk0.61/4,confidence0.57จากสรุปscope ไม่ได้อ่านcodeเองและไม่ใช่หลักฐานcorrectness
คำขอผู้ใช้รอบนี้ระบุให้แยกเอเจนต์ตรวจและเขียนแผนทับโดยตรง จึงทำเฉพาะaudit/probe/เอกสารที่ร้องขอ ไม่มีimplementation decisionหรือการซ่อมข้อมูลจริงที่อ้างJevอนุมัติ
Verdict: fix-then-verify — แก้sharedcontractและpersistenceก่อนUIpolish แล้วใช้acceptanceของแผนใหม่พิสูจน์แต่ละflow
