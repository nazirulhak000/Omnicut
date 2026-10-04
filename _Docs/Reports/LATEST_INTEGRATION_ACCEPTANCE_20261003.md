# Latest integration acceptance — 2026-10-03

ดำเนินการโดย: Codex (GPT-6) + mobile_integration / cutout_integration / audio_integration (GPT-6)

สถานะ: กำลังทำ; ยังไม่ใช่ผล gate สุดท้าย
Round: `LATEST-INTEGRATION-ACCEPTANCE-20261003` ใน TODO.md

## ขอบเขตและ baseline

ผู้ใช้อนุมัติให้วางแผนและแยกเอเจนต์ตรวจรวมงานใหม่หลัง PC-MAX โดยแก้บั๊กที่พิสูจน์ได้ งานก่อนเริ่มมี 18 tracked และ 5 untracked จากรอบ Antigravity; รักษา diff เดิมและรวมการแก้ที่จำเป็น ไม่ reset/stash/commit/push

รายงาน `CAPCUT_EDITOR_GAP_20261003/00_SUMMARY.md` ส่วน 11 ระบุว่ารอบ Claude Wave1 แก้หลายช่องว่างแล้ว จึงใช้รายการอัปเดตแทนการทำ Top10 เดิมซ้ำ รอบนี้ไม่เปลี่ยนรูปลักษณ์ฟอนต์/ข้อความ และไม่ใช้ข้อมูล Raw/Assets/ผลงาน/registry จริงในการทดสอบ

## แบ่งงาน

| เจ้าของ | งาน |
|---|---|
| mobile_integration | สัญญา RecordingSession/shot list/pipeline, task status/result, failure/polling, filming return, API+browser |
| cutout_integration | scope จุดต่อ source/reference window, multi-frame seed, cache, metadata save/load และ picker |
| audio_integration | corrupt/atomic cache, fallback gain/mute/length, color-match กับ clip mute |
| root | render completion/revision, รวม gate, source stability และปิดเอกสาร |

## บั๊กที่พิสูจน์และผลเฉพาะจุด

### Render completion / save revision

`complete_job` เผยแพร่ status completed ก่อน `finalize_incremental_render` เขียน manifest จบ ผู้ใช้จึงอ่าน revision กลางทางหลัง polling หยุดได้

- Regression ก่อนแก้: 1 failed, 1 passed ใน `test_render_completion_publication.py` โดยหยุด finalizer ด้วย Event (ไม่อาศัย sleep)
- แก้ให้ประกอบ result ก่อน แล้วเผยแพร่ completed หลัง final write จบ; metadata failure ยังเป็นวิดีโอสำเร็จพร้อม log ตาม contract เดิม
- ตรวจ API status → project GET ครั้งเดียว → save revision ล่าสุดสำเร็จ; ไม่ลดความเข้มงวดของ 409 guard
- Targeted backend: 53 passed ใน 1.21s (`test_render_completion_publication`, project_revision, incremental_render_reuse, ownership และ audio_mix_degraded)
- Frontend save/revision: 33 passed ใน 76.27ms; consecutive-read guard เดิมยังอยู่สำหรับ backend เก่า/ผู้เขียนภายนอก

### Audio/cache

แคช JSON root ผิดรูปแบบทำ `.get` พัง, clip mute ทิ้ง opted-in color-match, และ voice-only fallback ทิ้ง gain/mute/duration ที่ตั้งไว้ แก้ consumed cache entries ให้ finite numeric timeline arrays/paired motion lengths และ cache เสียเป็น miss

- Targeted 150 passed / 5.58s; เพิ่ม regression 40 ข้อ (cache34, PCM2, pipeline4)
- PCM จริง: mute ศูนย์ทุก sample, gain0.25 RMS ภายใน3%, duration1.2s แทนก่อนแก้3s
- เปลี่ยนเฉพาะ beat_sync, motion_analyzer, sfx_manager, video_assembly_stage; รักษา color-match ที่เปิดไว้และไม่เปลี่ยน font/text render math
- Mobile ใช้ render slot เดียวกับ desktop แล้ว จึงไม่เพิ่ม shared mix-state refactor ที่ไม่จำเป็น

### Mobile

แก้สัญญา angle_id/script_lines/selected_videos/specs list, shot-list builder และ batch1 fallback, session/raw path/ownership, output mp4_video ที่มีจริงไม่ว่างและอยู่ Exports, callback(message,fraction), shared render slot/cancellation, polling ที่ไม่ซ้อน/ไม่ค้าง/กลับมางานเดิม และ filming return workflow

- API22 + browser6 + shot-list8 = 36 passed, 18 warnings, 19.07s
- Node flow6 passed / 51.56ms; build429ms เป็น snapshot ของ agent ก่อน gate รวม
- Browser ใช้ production React UI กับ isolated API/share mocks: success/share/reload, failed/cancelled/missingfile, offline reconnect และ film navigation roundtrip
- backend pipeline/TTS เป็น offline stub กับ source/output ใน temp; ไม่ทดสอบกล้องมือถือจริง, native share chooser หรือ live TTS/TikTok posting
- แก้ shot-list fixture ให้ monkeypatch PROJECTS_DIR ก่อนสร้าง dummy; พบไฟล์เดิม `03_Projects/_ShotLists/prod_gemini_1_ang_1/voiceover.wav` ตรวจ byte เท่ากับ `RIFFdummywav` และทั้งโฟลเดอร์มีไฟล์นี้อย่างเดียว จึงลบเฉพาะ dummy และโฟลเดอร์ว่างแล้ว ไม่ล้าง project/cache เป็นกลุ่ม

### Cutout

บันทึก prompt_reference_source/start จาก picker ผ่าน config/API/cache; เปลี่ยน reference แทนจุดเดิม, clear ล้าง metadata, source คนละไฟล์แม้ basename เท่ากันไม่ใช้จุดซ้ำ, failed auto ไม่ย้อนใช้ explicit เก่า, seed frame0 และแต่ละ interval พร้อมรักษาจุดเกิน32 จุด/long CLI และ malformed frame/reference fail closed

- Preview และ Python compositor invalidate ready artifact เมื่อแก้/ล้าง points/reference; serialize save/load/render metadata ผ่าน actual editor helpers
- Legacy clip_list/render_params.clip_list/clips รองรับทั้งหมด; SAM2 cache version เปลี่ยนเป็น prompt-scope-v2 ในรอบแรกและ prompt-scope-v3 หลัง external ปรับ legacy guard เพื่อไม่ใช้ artifact จาก semantics เก่า ส่วน rembg cache contract เดิมยังอยู่
- Offline Python128 passed,4 skipped /1.96s; Node76 passed /84.89ms
- Browser picker/save/reload6 passed /42.22s
- RTX4060 จริง3 passed /18.84s รวม sparse seeds0/2/8, ครบ12 encoded frames,6 active frames และ inactive alpha0
- Parity + FFmpeg behavior229 passed,23 known Pillow warnings /24.67s
- GPU multi-seed ใช้ point finder stub เพื่อแยกพิสูจน์ SAM2/CUDA/encoder/alpha จริง ไม่ใช่หลักฐาน rembg auto-point accuracy กับสินค้าจริง
- โปรเจกต์เก่าที่ไม่มี reference metadata ไม่สามารถกู้ historical pickerframe; fallback อ้างคลิปแรกทั้ง timeline อาจต้องเลือกจุดใหม่

## Gate สุดท้าย

### รอบตรวจรวมครั้งแรก (diagnostic)

ระหว่างรันมีงาน Antigravity marker/negative mode เข้ามา source watch770 ไฟล์พบ SequencePlayer, AssetPanel, EditorShell และ picker browser test เปลี่ยน จึงไม่ใช้ผลนี้เป็น final signoff

- 2408 passed,5 failed,12 skipped,50 warnings /779.02s; failures5 ข้อเป็น assertion เดิมที่คาดว่า marker ยังเห็นเมื่อ picker ปิด ทั้งที่พฤติกรรมใหม่ต้องซ่อน
- ปรับเฉพาะ acceptance assertions: hidden เมื่อ off/reload/play และ mapped marker เห็นเมื่อ paused picker reentry; points/reference save/load ยังตรวจครบและเพิ่ม actual PATCH ใน native Master case
- หลังปรับ browser6 passed /51.46s, negative gesture/state Node24 passed /152.59ms
- รอบแรก compileall ผ่าน, API220 routes, Node597 passed, build620ms; standalone diff check ผ่าน แต่ยังต้อง rerun gate บน source ล่าสุดที่นิ่ง
- Warning50 มาจาก utcnow ของ existing store/session code ที่เทสใหม่เรียกถึง, librosa/audioread fallback และ Pillow getdata deprecation; ไม่ถือเป็น failures และไม่ใช่บั๊กภาพที่ข้ามการตรวจ

### รอบสุดท้าย

รอบถัดมา: 2412 passed,1 failed,12 skipped,50 warnings /732.66s; circleopen ที่ actual t1.9712 ได้ MAE0.09078168 เทียบเกณฑ์เดิม0.08 ส่วน nontransition frameได้0.04924894 กำลังตรวจ frame-time alignment และ decoder readiness ก่อนเลือกแก้ ไม่เพิ่ม tolerance

Source watch770 ยังพบ EditorShell เปลี่ยนจากงานภายนอกอีกครั้ง; API220 routes, Node597 passed, build434ms, compileall ผ่าน ผลนี้จึงยังไม่เป็น final signoff และได้ประสาน user ให้หยุด source ระหว่างด่านสุดท้าย

ยืนยันสาเหตุ circleopen ด้วย FFmpeg lossless frame-counter ผ่าน pipe: output-side `-ss 1.9712` เลือก frame60 (2.0000s) แต่ frame ที่ใกล้ live timeที่สุดคือ59 (1.966667s) ส่วนวงกลมมี geometry mean error0.18046 เมื่อเทียบ frame60 และ0.03194 เมื่อเทียบ59 จึงแก้เฉพาะ test reference ให้ใช้ exact nearest output frame index แทน decimal seeking; เพิ่ม frame delta<=1/60s และ diagnostic decoder seeking โดยไม่เพิ่ม MAE threshold0.08 หรือเปลี่ยน production rendering

หลังแก้ targeted4 passed/48.81s: cut MAE0.042622–0.049569, circle0.042654–0.055270, dissolve YUV420-normalized0.040717–0.052894; independent monochrome dissolve mask MAE0.0000072338 เดิม; ทุก source sample seeking=false และ cleanupครบ

รอบต่อไป runner เพิ่ม source-change flag/hook ก่อน test เพื่อหยุดผ่าน pytest.exit พร้อม normal fixture teardown หาก source ถูกแก้ระหว่างรัน ไม่ force-kill processes และไม่ข้าม assertions/gates; source quiet จึงรัน full suite จบได้

### Source guard ที่พิสูจน์แล้ว

หลังผู้ใช้แจ้งอีกฝั่งเสร็จ เริ่ม gate ใหม่บน770ไฟล์ แต่ตรวจพบ `MobileQuickStudio.jsx` และ `background_isolation_video_worker.py` เปลี่ยนทันที จึงหยุดด้วย pytest.exit ผ่าน fixture teardown ปกติ: 11 passed/9.21s, exit3 (wrapper9.84s) และ OS temp ถูกเก็บกวาดแล้ว ผลนี้เป็นหลักฐานของ guard เท่านั้น ยังไม่ใช่ full gate; ประสานให้พัก source และตรวจ diff ล่าสุดแบบ read-only

## Jev advisory

### งานที่เพิ่มหลัง gate เริ่ม

ตรวจ Mobile Pro Flow ล่าสุดพบ quick-create คืน angle_id แต่ UI อ่าน id, upload ของสินค้าเดิมติดค้างเมื่อเปลี่ยนสินค้า/มุม, BGM toggle ไม่มีผลกับ payload/pipeline และ fallback shot plan สร้างเวลาเดาเมื่อ TTS ล้มเหลว จึงเพิ่ม T5.4/T5.5 เพื่อแก้ regression และตรวจ upload validation/dedup/path ใน storage จำลองก่อน full gate ใหม่ ส่วน SAM2 points-only/no-reference/nonzero-start ถูก external เปลี่ยน semantics จึงต้องเปลี่ยน cache version พร้อม test ไม่ใช้ artifact เก่าข้าม semantics; รักษา guard ใหม่ไว้

SAM2 แก้ cache เป็น prompt-scope-v3 เฉพาะ engine นี้; behavioral no-reference/nonzero auto-on ใช้จุดใหม่, auto-off คืน center fallback, actual reference คืน manualpoints; targeted93 passed/3 skipped/3.42s, source SHA คงที่ระหว่างเทสและ rembg ID เดิม โปรเจกต์ legacy ไม่มี reference ที่เริ่ม nonzero อาจต้องเลือกจุดใหม่เพื่อคืน manual intent; ไม่อ้างว่าสามารถกู้ reference เก่าได้

- เลือกตรวจ integration ก่อนเพิ่มฟีเจอร์: choice A, confidence 1.00
- เลือกตรวจ browser/FFmpeg fixture ใน temp แทนดู source อย่างเดียวหรือใช้ข้อมูลจริง: choice real_temp, confidence 1.00
- agent noul หลายครั้งได้ probability แต่ confidence null; ไม่ถือเป็น confidence ผ่าน gate และไม่อ้างเป็นหลักฐาน ผู้ใช้อนุมัติขอบเขต bounded fixes ไว้แล้ว ผลพิสูจน์มาจาก behavioral tests
- Jev อ่านเฉพาะสรุปข้อความที่ส่งให้ ไม่ได้อ่านไฟล์เองและไม่ได้เห็นเฟรม/เสียง
- Mobile completion quality3.11/4 confidence0.85; Audio quality3.31/4 confidence0.70 และ improved noul0.94 confidence null; Cutout quality3.10/4 confidence0.75 และ next=full_gate confidence1.00 ตัวเลข quality/advice ไม่ใช่ผล acceptance

## ส่งต่องานถัดไป

หลังปิด integration นี้ ลำดับเสนอที่ยังต้องตรวจช่องว่างกับโค้ดล่าสุด: (1) ตัดช่วงเงียบให้ voice/captions/SFX เลื่อนตามภาพ (2) rebuild Ghost Reveal timing หลังแก้คำ (3) UX กู้คืน/แจ้ง conflict งานบันทึก (4) copy/apply settings ระยะที่ยังขาด งานเหล่านี้ไม่ถูกนับว่าเสร็จในรอบนี้

Mobile cached filming plan หลังเปลี่ยนบทพูดเป็นงานตรวจแยก: fresh/cached plan lookup และ reuse ได้รับการทดสอบแล้ว แต่ไม่ได้ออกแบบ migration ของ session ที่ถ่ายไว้ภายใต้บทเก่า ห้ามตีความว่า workflow นี้แก้ historical plan invalidation ครบแล้ว
