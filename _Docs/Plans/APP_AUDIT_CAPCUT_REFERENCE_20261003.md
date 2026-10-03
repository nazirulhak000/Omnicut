# รายงาน Audit OmniCut + เทียบ CapCut (2026-10-03)

ดำเนินการโดย: Claude Code (Claude Sonnet 5.5) · ตามพรอมพ์ `PROMPT_APP_AUDIT_AND_CAPCUT_REFERENCE.md`
วิธีทำ: เอเจนต์ read-only 7 ตัวขนาน (pipeline, editor, cutout, schedule/autopost, tools+test, เทียบ CapCut, data-loss) แล้ว root รวมและสุ่มตรวจ evidence
**ไม่ได้แก้โค้ดใดๆ · ไม่ได้รัน test/GPU/render · ไม่ได้เปิด draft CapCut จริง**

## ข้อจำกัดของรายงาน (อ่านก่อน)
- evidence ทั้งหมดมาจากการอ่านโค้ดใน working tree ปัจจุบัน ซึ่งมี diff ที่ยังไม่ commit ของ Codex (SequencePlayer, EditorShell, AssetPanel, cutout) เลขบรรทัดอาจเลื่อนเมื่อ Codex ส่งงาน
- **ข้อมูล CapCut ไม่ได้ยืนยันจากตัวโปรแกรม**: ใน repo ไม่มีโค้ดที่อ่าน/เขียน `draft_content.json` (grep ใน `scripts/` เจอแค่ชื่อใน `storage_cleaner.py` ที่ล้างแคช) ตาราง 2 จึงอ้างจากเอกสารภายใน `CAPCUT_PREMIERE_TECH_INTEGRATION_PLAN.md` และ `_Docs/PROMPT_เทียบ_CapCut.md` ทุกแถว = "ยังไม่ได้ยืนยัน" ในฝั่ง CapCut ส่วนฝั่ง OmniCut ยืนยันจากโค้ด
- สถานะ ✔ = root เปิดอ่านซ้ำแล้วตรงกับที่เอเจนต์รายงาน · อื่นๆ = เชื่อตามเอเจนต์ที่อ้างบรรทัดที่เปิดจริง

## ตาราง 1: ปัญหาเดิมและฟีเจอร์ใหม่

เรียงตามความคุ้มค่า (ความเสี่ยงข้อมูล > ผลต่อ views > ต้นทุนแก้)

| # | หัวข้อ | ประเภท | ปัญหา/โอกาส | หลักฐาน (ไฟล์:บรรทัด) | ผลที่ได้ | แรง | ความเสี่ยง |
|---|---|---|---|---|---|---|---|
| 1 | ล้างแคช CapCut ลบ draft ผู้ใช้ได้ ✔ | แก้ | `execute_safe_purge` rmtree ทุกโฟลเดอร์ใน draft dir ที่ขึ้นต้น `.cloud_cache` **หรือ `cache_`** ไม่มี backup/confirm ฝั่ง server ขัด AGENTS ข้อ 3, 4 | `scripts/storage_cleaner.py:140,239-247`; `scripts/api_analytics.py:522-529` | draft ชื่อ `cache_xxx` ไม่หาย | S | ต่ำ |
| 2 | purge ลบไฟล์ใน 03_Projects ตามชื่อ "temp"/"preview" | แก้ | substring match + .jpg/.png/.wav/.mp3 จับ `template.png`, `cover_preview.jpg` ลบถาวร ไม่ผ่าน trash | `scripts/storage_cleaner.py:222-234`; test ครอบแค่ `tests/test_storage_cleaner.py:60` | ไฟล์งานไม่หายเงียบ | S | ต่ำ |
| 3 | `archive()` rmtree archive เดิมก่อน move ✔ | แก้ | ถ้า move พังกลางทาง (retry WinError 32) เสียทั้งสองฝั่ง | `scripts/project_manifest.py:442-447` | archive ไม่ทับกัน (ต่อท้าย timestamp) | S | ต่ำ |
| 4 | dedup `/clean` + delete-file/batch-delete ลบ 01_Raw/02_Assets ถาวรโดยไม่มี guard ฝั่ง server | แก้ | server ไม่เช็คว่ายังมีสำเนาเหลือ; `move_to_trash=False` unlink ถาวร; "trash" ใน delete-file ย้ายแล้ว unlink ทันที; confirm มีแค่ UI modal ขัด AGENTS ข้อ 1 | `scripts/asset_dedup.py:156-177`; `scripts/api_asset_dedup.py:11-37`; `scripts/api_videos.py:686-707,1103-1114,1244-1258`; UI `RawVaultPanel.jsx:294-327` | กันลบวัตถุดิบชุดสุดท้าย | M | ต่ำ |
| 5 | Autopost นับ "สำเร็จ" ผิด แล้วย้ายไฟล์เข้า Posted | แก้ | `waitForPostConfirmation` ถือสำเร็จเมื่อ evaluate throw / ไม่พบ editor 2 รอบ / tab หาย; ไม่มี `chrome.debugger.onDetach` → กด Cancel แบนเนอร์ debugger = "โพสต์แล้ว" → `mark_posted` ย้ายไฟล์+archive | `tiktok_autopost_extension/background.js:1419-1420,1428-1434,1458-1464,1677-1678`; `scripts/api_exports.py:810-823,861` | ไม่มีคลิปหายเงียบ | S | ต่ำ |
| 6 | `mark_posted` ไม่เขียน PostLog ✔ | แก้+ใหม่ | `PostLog.add_post` ถูกเรียกแค่ `api_posts.py:24` และ `api_phase1.py:194` (manual) row เกิดตอน sync stats แบบ fuzzy match → hook/style/hook_color/เวลาโพสต์หาย | `scripts/api_exports.py:751-865`; `scripts/post_log.py:70-107` | ปูทาง hook A/B ด้วยข้อมูลตรง | S | ต่ำ |
| 7 | Metrics ถูกทับ ไม่มี snapshot; best-time ไม่มี min-sample | แก้+ใหม่ | upsert `merged.update(metrics)`; sync ชม.ที่ 1 ถูกนับเป็นเลข 48 ชม.; เรียงชั่วโมงตาม score แม้ sample=1 ไม่แยกวัน | `scripts/post_log.py:229-232,450-451`; `scripts/api_schedule_queue.py:539-541,553-557,738-756` | best-time/hook ranking เชื่อได้ + กราฟโตตามเวลา | M | กลาง (schema ใหม่) |
| 8 | ไม่มี feedback loop views ↔ พารามิเตอร์ผลิต | ใหม่ | manifest เก็บ param ครบ แต่ post_log/analytics ไม่เก็บ hook_style/voice_preset/bgm → ไม่รู้สูตรไหนวิวดี | `scripts/stages/video_assembly_stage.py:258-303`; `scripts/api_tiktok_stats.py:1-9`; `scripts/api_hooks.py:1-7` (grep ไม่พบ param ใน post_log/api_analytics) | รายงาน "สูตรที่ชนะ" ปรับ default จากข้อมูลจริง | M | ต่ำ |
| 9 | Mirror JSON ที่ track ใน git อาจ re-import ทับ SQLite | แก้ | `post_log/schedule_queue/schedule_templates/tiktok_pending.json` อยู่ใน git, `store.db` ignore; `_sync_from_json_if_newer` DELETE+INSERT ทั้งตาราง → git pull/checkout ย้อนไฟล์ = แถวใหม่หาย | `.gitignore:74-77`; `scripts/db.py:219-283,409-412` | กันข้อมูลโพสต์/คิวหาย | S | ต่ำ (ต้องให้ user ยืนยัน `git rm --cached`) |
| 10 | Cutout: `sys` ไม่ได้ import ✔ | แก้ | `kill_process_tree` ใช้ `sys.platform` แต่ไฟล์ไม่มี `import sys` → cancel/error = NameError ทับ error จริง SAM2 process ค้างถือ VRAM | `scripts/background_isolation_video_worker.py:126` (imports :9-20), เรียก :360, :526 | cancel ได้จริง | S | ต่ำ |
| 11 | SAM2 ไม่มี quality gate, alpha binary, manifest ระบุ temporal ไม่ตรงจริง | แก้/ใหม่ | alpha=`(logits>0)` ขอบแข็ง track หลุดได้เฟรมว่างเงียบ; gate มีเฉพาะ rembg | `scripts/background_isolation_sam2_worker.py:213,61`; `scripts/background_isolation_worker.py:133-159`; `video_worker.py:426,490,500` | จับ track หลุด/ขอบนุ่ม | M | กลาง (ต้องวัดคลิปจริง) |
| 12 | Cutout: ไม่มี GPU lock | แก้ | pool 4 thread ไม่มี semaphore SAM2 สอง job พร้อมกัน = สอง process (RAM ≥1GiB+12MiB/เฟรม) | `scripts/task_manager.py:28,623-625`; `scripts/api_background_isolation.py:195-202`; `scripts/cutout_runtime.py:113-115` | กัน OOM | S | ต่ำ |
| 13 | Cutout: Python/JS contract ไม่ตรง | แก้ | default engine rembg(py) vs sam2(js); status `cancelled` py ไม่รับ; regex id `bgiso1-` vs artifact `bgseq1-`; EPSILON 1e-9 vs 1e-12 | `scripts/background_isolation.py:31,33,43,98-103`; `cutoutEngineModel.js:13,16`; `backgroundIsolationPreview.js:41` vs `background_isolation_compositor.py:419` | กัน 422/no-op เงียบ, preview=render | S | ต่ำ |
| 14 | Cutout: render ใช้สีจาก VP9 ที่ encode ซ้ำ | แก้/ใหม่ | subject ทับด้วย RGB จาก cutout.webm (crf 24/28, 4:2:0) → generation loss ควรใช้แค่ alpha + RGB จากต้นฉบับ | `scripts/video_editor.py:1459-1462`; encode `sam2_worker.py:185`, `video_worker.py:396` | ขอบ/สีตรงต้นฉบับ | M | กลาง (ต้องแก้ preview คู่) |
| 15 | Purge cache ล้าง cutout ทุกโปรเจกต์ | แก้ | ไม่มี LRU/กรองโปรเจกต์ → render ถัดไป fail "not ready" เสีย GPU time | `scripts/storage_cleaner.py:36-37,252,298-320`; `video_editor.py:1369-1372` | ไม่เสียงาน cutout | S | ต่ำ |
| 16 | Editor: Ctrl+S "ตัดคลิป" ด้วย ✔ | แก้ | handler เช็ค `mod` เฉพาะ z/y/b; Ctrl+S ตกเข้า `case 's'` (split) พร้อม save; Ctrl++/- แย่ง zoom browser | `frontend/src/hooks/useEditorShortcuts.js:42-57,75-78`; `EditorShell.jsx:1418-1421` | กันคลิปถูกตัดตอนกด save | S | ต่ำ |
| 17 | Editor: slider ท่วม undo stack | แก้ | `onClipChange={patchClip}` เรียก `set` ทุก onChange; ลาก 1 ครั้ง = หลายสิบ step stack 50 หลุดหมด; `onBeginDrag` ไม่ถึง Inspector | `useEditorHistory.js:6,31-35,55-60`; `ClipInspector.jsx:203-210`; `EditorShell.jsx:2442,2642,2794` | Ctrl+Z 1 gesture = 1 step | M | ต่ำ |
| 18 | Editor: `clipKey` ไม่มี speed/freeze_tail/volume/smooth_slowmo | แก้ | `segments` memo + `wireClipAudio` พึ่ง key นี้ (ปิด eslint) อาจ stale หลังเปลี่ยน speed (**ต้อง repro ก่อน**); key สร้างใหม่ทุก render ไม่ `useMemo` | `SequencePlayer.jsx:3608-3615,4104-4109,4538-4542`; `timelineMath.js:122-130` | preview ตรง render หลังเปลี่ยน speed | S | ต่ำ |
| 19 | Keyframe 2 ชุดสูตรไม่ตรง + ไม่มี UI | แก้+ใหม่ | live ใช้ linear/zoom min 1.0; `subjectFrameMapping` import `keyframeModel` (easing, zoom min 0.5); comment "ไม่มีใคร import" ล้าสมัย; ไม่มี UI เพิ่ม keyframe | `timelineMath.js:43-105`; `keyframeModel.js:18-60`; `subjectFrameMapping.js:1,15`; `video_editor.py:884-909` | รวมสูตรเดียว + Ken Burns ด้วยมือ | L | กลาง (แก้ JS+Py คู่) |
| 20 | Editor: autosave stringify ทั้ง payload + ปิดแท็บเสี่ยงหาย | แก้ | `getKey` stringify ทุกครั้งที่ payload เปลี่ยน; unload ใช้ `fetch keepalive` (limit ~64KB, `.catch` กลืน) ไม่มี local draft; save fail retry 2 ครั้งแล้วหยุด 409 ไม่มีทางเลือก | `useProjectAutosave.js:18-20,41-47,76-82,269-286`; `useProjectLoader.js:21-35` | กู้งานได้ / ลื่นขึ้น (ยังไม่วัด) | M | กลาง |
| 21 | Default เสียง/ฟอนต์ batch ไม่ตรง AGENTS | แก้ | AGENTS ข้อ 5 = Fenrir+commercial_premium; โค้ด Puck+commercial_hype; batch default `IBMPlex` (frontend ยังไม่ยืนยัน) | `scripts/api_render.py:177`; `pipeline_context.py:363`; `pipeline.py:112-113`; `voice_stage.py:444`; `api_batch_render.py:19-23`; `BatchRenderModal.jsx:94-98` | ตรงมาตรฐาน | S | **กลาง — ต้องถาม user (กระทบเสียงทุกคลิป)** |
| 22 | TTS atempo ไม่เช็ก returncode + wav เก่าถูกใช้เงียบๆ | แก้ | atempo พัง → ลบ raw แต่คืน path เดิม ถ้ามี `voiceover.wav` เก่า = เสียงไม่ตรงบท | `scripts/gemini_tts_engine.py:403-416`; `voice_stage.py:385`; `pipeline_context.py:603-609` | กันเสียงผิดบท | S | ต่ำ |
| 23 | ซับ: Gemini TTS ไม่มี word timing | ใหม่ | cue จาก RMS+สัดส่วนตัวอักษร; Ghost Reveal/pacing ใช้ proportional (Edge-TTS มี word timing) | `voice_stage.py:182-199,213-220`; `editorial_pacing.py:241,253-254`; `subtitle/word_reveal.py:161-163` | ซับตรงเสียงขึ้น | L | กลาง (เริ่มจาก RMS sub-block ไม่เพิ่ม dependency) |
| 24 | แปลอังกฤษไม่มี persistent cache + ทำทุกครั้ง | แก้ | `generate_micro_cues` แปลเสมอ ไม่รับ flag; cache in-memory | `subtitle_engine.py:494-506,622`; `translator.py:66,116-131` | เร็ว/ถูกขึ้น | S | ต่ำ |
| 25 | Hook-first cadence | ใหม่ | จังหวะตัดคงที่ 1.5–2.5s ตลอดคลิป ไม่เร่ง 3 วิแรก | `scripts/config.py:104-105`; `shot_matching_stage.py:561-598` | retention ต้นคลิป | M | กลาง (ต้องคง parity ผ่าน clip_list) |
| 26 | `hook_duration` auto ไม่ทำงาน | แก้ | sentinel เทียบ 3.0 แต่ default 5.0 → ใช้ 5.0 เสมอ; ข้อความ notify ยังเขียน "Kanit-Black 86pt" | `scripts/stages/subtitle_stage.py:83,101-104`; `pipeline_context.py:370` | hook ยาวตามข้อความ | S | กลาง (กระทบเวลา hook ถาม user ก่อน) |
| 27 | Transition ซ้ำ 2 ชุด / all-cut เลือกไม่ได้ / dead code | แก้ | `_every_boundary_is_a_cut` ซ้ำ 2 ที่; hard-cut ทั้งคลิปถูกเติม transition ทับ; `_parity_contract_reference` UnboundLocalError ถ้าถูกเรียก; เทส string-match ไฟล์ | `pipeline.py:84-92,306-348`; `video_assembly_stage.py:20,44-62`; `tests/test_preview_render_parity.py:569-587` | hard-cut ได้ + เทสวัดของจริง | S-M | กลาง |
| 28 | Source resolution เดาไฟล์เอง | แก้ | ไม่พบวิดีโอ → หยิบรูป 6 รูปแรกจาก Inbox ทำ slideshow (เสี่ยงผิดสินค้า ขัดข้อ 13) | `scripts/stages/source_resolution.py:38-45,56-60` | กันคลิปผิดสินค้า | S | ต่ำ |
| 29 | Cache JSON 3 ตัวเขียนไม่ atomic | แก้ | `.vision_cache.json` (02_Assets) อ่านพัง→`{}` แล้วเขียนทับ = cache ที่เสียค่า Gemini หาย; beat/motion cache เหมือนกัน | `scripts/gemini_vision_matcher.py:91-105,117,826`; `beat_sync.py:50`; `motion_analyzer.py:54` | ไม่เสียโควตา Vision ซ้ำ | S | ต่ำ |
| 30 | ลบสินค้า `force=true` ลบหลักฐานโพสต์ | แก้ | frontend ส่ง `force=true` เสมอ backend ข้าม guard posted ไม่มี snapshot | `ProductToClip.jsx:3085`; `scripts/product_store.py:1454-1468` | ประวัติโพสต์ไม่หาย | S | กลาง |
| 31 | `/api/products/{id}/videos` รับ path นอกโปรเจกต์ + batch-delete ลบ reference ข้ามสินค้าตามชื่อไฟล์ | แก้ | ไม่เช็ค containment; filter ด้วย `name` ชน `IMG_001.mov` | `scripts/api_products.py:492-508`; `scripts/api_videos.py:712-717` | กัน path ปน/reference หาย | S | กลาง |
| 32 | Queue ค้างสถานะ ไม่มี retry/resume | แก้+ใหม่ | server ไม่เคยตั้ง `failed`; `_pending` เก็บใน memory ช่องเดียว restart หาย; mirror queue กลืน exception → `ready_for_extension` ค้างลบไม่ได้ | `scripts/api_schedule_queue.py:29,1053,1082-1100`; `api_tiktok_autopost.py:34,236-262`; `api_exports.py:687-690` | ลดงานมือต่อคลิป | M | กลาง |
| 33 | Retention/watch-time ไม่ถูก scrape | ใหม่ | scrape ได้แค่ views/likes/comments/shares+duration ไม่มี avg watch time/completion (**DOM หน้า analytics ยังไม่ได้ยืนยัน**) | `tiktok_autopost_extension/stats_parser.js:17-20,115-119` | วัดว่าคนทิ้ง hook วินาทีไหน | L | กลาง |
| 34 | Caption/hashtag template ตายตัว ไม่มี feedback | ใหม่ | PostLog เก็บ hashtags+views อยู่แล้ว คำนวณ performance ต่อชุดได้ | `scripts/product_scraper.py:1068-1069,1192-1193`; `post_log.py:103` | ชุดที่วัดผลแล้ว | M | ต่ำ |
| 35 | Backup: ดึง `.cache` เข้า zip + list อ่านคีย์ผิด + ไม่มี restore จริง | แก้/ใหม่ | `os.walk` ไม่ prune `.cache`; list อ่าน `uncompressed_mb` แต่ manifest เขียน `total_uncompressed_bytes`; มีแต่ dry-run | `scripts/backup_engine.py:141-164,224`; `tools/backup_restore_dry_run.py:151-155` | backup เล็กลง, ปิดวง backup→restore | S (restore = M-L) | กลาง (restore) |
| 36 | tools hardcode path เก่า `d:\Winona\...` + รันตอน import + rmtree | แก้ | ขัดกฎข้อ 2 ไม่มี `__main__` guard/dry-run ไม่มี test (รายชื่อเต็มใน "ภาคผนวก") | `tools/clean_and_organize_tmp.py:7,22-25,43,63,76,104`; `tools/audit_video_resolutions.py:5-6,23` | ย้ายเครื่อง/รันปลอดภัย | S | ต่ำ |
| 37 | Test gap: router/hook ไม่มี test | ใหม่ | `api_posts`, `api_tokens`, `api_recording`, `recording_sessions`, `api_typesafe_studio`, `upload_storage`, `subtitle/badge_plate_renderer`; frontend lib `audioPeaks/angleToForm/hookStyles/lut3d/uiScale` + hooks `useEditorCommands/Selection/Shortcuts/ProjectLoader/TimelineDrag` (grep ไม่พบอ้างใน test) | ผล grep ของ A5 (`api_server.py:283-306` include router) | กัน regression | M | ต่ำ |
| 38 | `color_match.py` เสร็จแต่ไม่ต่อสาย ✔ | ใหม่ | ไม่มี import ใน `scripts/`; มีแค่ `tests/test_color_match.py` | `scripts/color_match.py:56-263` | auto color match ใช้ได้จริง | M | ต่ำ |
| 39 | Perf: list_exports / path lookup O(n) | แก้ | `sorted(key=os.path.getmtime)` stat ทุกไฟล์; `find_by_path` resolve ทั้ง registry | `scripts/api_exports.py:233-237`; `export_registry.py:119-123`; `sidepanel.js:347,362` | Gallery/sidepanel เร็วขึ้น (ยังไม่วัด) | M | ต่ำ |
| 40 | อื่นๆ เล็ก | แก้ | ปก 3:4 ไม่ย้ายไป Posted (`api_exports.py:639`); `DIAGNOSTIC_PASSIVE_WAIT` dead flag + selector Thai/EN hardcode (`background.js:36-47,1341-1348`); `tools/playwright_tiktok_assistant.py:18` ใช้ `--disable-blink-features=AutomationControlled` (เสี่ยง ToS ซ้ำบทบาท extension); comment อ้างแผนนอกโปรเจกต์ (`shot_matching_stage.py:432`, `source_resolution.py:149`) | ตามที่ระบุ | เก็บกวาด | S | ต่ำ |

## ตาราง 2: เทียบ CapCut

ฝั่ง CapCut ทุกแถว **ยังไม่ได้ยืนยัน** (ไม่มีหลักฐานจากไฟล์ draft จริง/เว็บ — ดูข้อจำกัด) ฝั่ง OmniCut อ่านจากโค้ด

| ฟีเจอร์ CapCut | OmniCut มีหรือยัง | ช่องว่าง | วิธีทำในระบบเรา | แรง | ยืนยัน |
|---|---|---|---|---|---|
| Auto caption จากเสียง | ไม่มี STT ใน pipeline; ซับจากสคริปต์+TTS timing; Whisper มีแค่ `tools/inspect_whisper.py:4`; `requirements.txt` ไม่มี whisper | ใช้กับเสียงคนจริงไม่ได้ | STT optional (faster-whisper, degrade เงียบ) ใช้ align timing เท่านั้น **ห้ามใช้ผลดิบเป็นซับ** (กฎ 17) → `stages/subtitle_stage.py` | M | ยังไม่ได้ยืนยัน |
| Caption style/animation | มี Ghost Reveal + Micro-Burst: `subtitle/ghost_reveal_ass.py:72,129,199`, `word_reveal.py:134`, `motion_effects.py`, `CaptionInspector.jsx` | ไม่ต้องไล่ตาม — ล็อก font contract | **ห้ามแตะ** | - | ยังไม่ได้ยืนยัน |
| Caption translate | มี `translator.py:19,116`, `subtitle/translation_service.py` | แถว 24 (cache) | persistent cache | S | ยังไม่ได้ยืนยัน |
| Silence removal | มี `silence_detect.py:90,171`, `api_audio_beats.py:147,171`, `lib/silenceRipple.js:68`, ปุ่ม `Toolbar.jsx:176`; **ใช้ได้เฉพาะ editor ด้วยมือ ไม่ถูกเรียกใน VoiceStage** | ไม่มี bulk/auto | ปุ่ม "ตัดช่วงเงียบทุกคลิป" ใน `EditorShell.jsx`; หรือเรียกใน `voice_stage.py:100` (ต้องเลื่อน cues) | S / M | ยังไม่ได้ยืนยัน |
| Denoise เสียง | ไม่พบ `afftdn/arnndn/anlmdn` (grep); `voice_engine.py:351` มีแค่ EQ+loudnorm | ไม่มี | filter `afftdn` opt-in ใน `stages/audio_mix_stage.py` (ห้ามทำ Fenrir เพี้ยน) | S | ยังไม่ได้ยืนยัน |
| Beat sync | มี `beat_sync.py:34,55-169`, `api_audio_beats.py:88`, `lib/beatGrid.js:49,67`, snap `shot_matching_stage.py:691-700` | พอ | - | - | ยังไม่ได้ยืนยัน |
| Auto loudness / ducking | มี `loudnorm` `sfx_manager.py:116-128`, sidechain ducking `:351-370`, limiter `video_editor.py:2095` | ตรวจ parity ว่า SequencePlayer ทำ ducking ตรง ffmpeg (ยังไม่ยืนยัน) | เช็ค `SequencePlayer.jsx` | S | ยังไม่ได้ยืนยัน |
| Remove BG | มี rembg/SAM2/BiRefNet: `background_isolation*.py`, `birefnet_engine.py` (BiRefNet ใช้เฉพาะสติกเกอร์); UI `lib/cutoutEngineModel.js:13` | ปัญหาคุณภาพ/เสถียรภาพ ดูตาราง 1 แถว 10-15 | - | - | ยังไม่ได้ยืนยัน |
| Object tracking | มี SAM2 mask propagate `sam2_worker.py:209`; `cutout_temporal.py:13`; `motion_analyzer.py:27` | ไม่มี tracker ให้สติกเกอร์/ข้อความตามวัตถุ | ใช้ mask centroid จาก cutout เป็น keyframe ตำแหน่ง (`keyframe_engine.py`) | L | ยังไม่ได้ยืนยัน |
| Keyframe | backend `keyframe_engine.py:30-123`, `video_editor.py:884-966` (zoom/pan linear); frontend `keyframeModel.js:105` **ไม่มี UI** | UI ไม่มี; opacity/volume/easing ไม่ผ่าน render | แถบ keyframe ใน `ClipInspector.jsx` + diamond บน Timeline; รวมสูตร (ตาราง 1 แถว 19) | L | ยังไม่ได้ยืนยัน |
| Speed คงที่ | มี `ClipInspector.jsx:88-111`, `video_editor.py:1269-1320` (0.25–4x, minterpolate, freeze tail) | ครบ | - | - | ยังไม่ได้ยืนยัน |
| Speed ramp/curve | ไม่พบ (grep `speed_ramp/speedRamp/speed_curve`) | ไม่มี | speed keyframes + `setpts` piecewise + audio atempo + `clipDuration` (A/V sync เสี่ยง) | L | ยังไม่ได้ยืนยัน |
| Transition | 14 xfade `video_editor.py:363-369`, `timelineMath.js:9-24` | น้อยกว่า "~50" ที่เอกสารภายในอ้าง (ยังไม่ยืนยัน) | เพิ่ม xfade ทีละแบบพร้อม whitelist+เทส | S | ยังไม่ได้ยืนยัน |
| Effect/Overlay | `spotlight_effect.py:222`, `hyperframes_engine.py:21`, `EffectTrack.jsx`, `lib/motion/` | ไม่พบ glitch/blur ทั่วไป | preset ใน `motionPresets.js:148` + ffmpeg คู่ | M | ยังไม่ได้ยืนยัน |
| Mask ต่อคลิป | ไม่มี (มีแค่ cutout/subject points) | ไม่มี | ใหม่ ต้อง parity | L | ยังไม่ได้ยืนยัน |
| LUT / Auto color | LUT `video_editor.py:1750-1761`, `lib/lut3d.js`, 4 ไฟล์ `.cube`; eq มือ `ClipInspector.jsx:19-21`; **auto: `color_match.py` ไม่ต่อสาย ✔** | auto color match, temperature | เรียก `plan_color_match`/`apply_corrections` ใน `stages/video_assembly_stage.py` opt-in | M | ยังไม่ได้ยืนยัน |
| Auto-cut / beat cut | pipeline snap `pipeline.py:35`, `editorial_pacing.py:150,202`; editor แค่ snap ตอนลาก | ไม่มีปุ่ม auto split ตามบีตใน editor | ปุ่ม "ตัดตามบีต" ใช้ `beatSnapPoints` | M | ยังไม่ได้ยืนยัน |
| Template | `hook_styles.py:378`, `stylePresetCatalog.js` (10), `templates/hyperframes/` | ไม่มี template ทั้ง timeline เก็บ/แชร์ | บันทึก timeline JSON เป็น template (`editorProjectState.js`) | M | ยังไม่ได้ยืนยัน |
| Batch export | `batch_render.py:120`, `api_batch_render.py:32-73`, `BatchRenderModal.jsx` | รอบละ 1 สินค้า; ไม่มี export preset (res/bitrate) | multi-product queue + preset | M | ยังไม่ได้ยืนยัน |
| Preset style | `api_batch_render.py:23`, `stylePresetCatalog.js` | พอ | - | - | ยังไม่ได้ยืนยัน |
| Proxy/cache | `proxy_manager.py:191`, `api_proxy.py`, `lib/clipProxy.js:116` (preview-only ไม่ใช้ตอน render), `media_probe_cache.py` | ครบ | - | - | ยังไม่ได้ยืนยัน |
| Undo/redo/history | `useEditorHistory.js:5` (50 step, drag coalesce); ไม่คงอยู่ข้าม session; ไม่มี history panel | ตาราง 1 แถว 17 | coalesceKey | M | ยังไม่ได้ยืนยัน |
| Shortcut | `useEditorShortcuts.js` (Space, S, Ctrl+B, J/K/L, ←/→, +/-, F, N, M, Delete, Ctrl+Z/Y) | ไม่พบ I/O mark, ripple-delete key, copy/paste attr ข้ามคลิป (grep บางส่วน) | ตาราง 1 แถว 16 แล้วเพิ่มทีหลัง | S | ยังไม่ได้ยืนยัน |
| Reverse / Freeze / Chroma key / Stabilize | freeze tail มี (`video_editor.py:1273-1320`); reverse/chroma/vidstab/deshake **ไม่พบ** (grep) | ไม่มี | freeze=`tpad` (S); chroma=`chromakey`+despill+preview parity (S-M); reverse จำกัดความยาว (M) | S-M | ยังไม่ได้ยืนยัน |
| Auto-reframe / saliency | blur-bg ฉากแนวนอน `video_editor.py:786,1156`; saliency/scenedetect ไม่พบ | ไม่มี | `motion_analyzer.py` + crop expr (คง 1080x1920/30fps) | L | ยังไม่ได้ยืนยัน |
| Auto poster/cover | poster ล็อกเฟรมที่ 1s `video_editor.py:2334` | ไม่เลือกเฟรมดี | เลือกเฟรมจาก motion/face score | S | ยังไม่ได้ยืนยัน |

หมายเหตุ: `_Docs/PROMPT_เทียบ_CapCut.md` ตาราง "ยังไม่มี" ล้าสมัย (auto-ducking, LUT, waveform, keyframe backend, beat มีแล้ว) ควรอัปเดต

## Top 5 ที่ควรทำก่อน (ลำดับทำ)

1. **ชุดปิดช่องข้อมูลหาย** (ตาราง 1 แถว 1, 2, 3, 4, 29) — ขัดกฎเหล็กข้อ 1/3/4 ตรงๆ ทั้งหมดแก้ S ต้นทุนต่ำสุด ความเสียหายถ้าพลาดสูงสุด และไม่ชนงาน Codex (ไฟล์ backend ล้วน)
   - แตะ: `scripts/storage_cleaner.py`, `scripts/api_analytics.py`, `scripts/project_manifest.py`, `scripts/asset_dedup.py`, `scripts/api_asset_dedup.py`, `scripts/api_videos.py`, `scripts/gemini_vision_matcher.py`, `frontend/src/api.js` (ส่ง confirm)
   - test เพิ่ม: `tests/test_storage_cleaner.py` (`cache_myclip/draft_content.json` และ `template.png` ต้องรอด, ไม่มี confirm = 400), `tests/test_project_archive.py` (archive ชื่อซ้ำเหลือทั้งสอง), `tests/test_asset_dedup.py` + `tests/test_api_asset_dedup.py` (ส่ง original+dup พร้อมกันต้องเหลือ 1), `tests/test_delete_file_guard.py` ใหม่ (ไม่มี token → 403, `Posted/` ยังกัน)
2. **Autopost เชื่อถือได้ + ปิด feedback loop** (แถว 5, 6, 7, 8) — ตัวเดียวที่ตอบโจทย์ "เพิ่มยอดดู" และตอนนี้ข้อมูลหายตั้งแต่ต้นทาง ทำตามลำดับ: แก้ false-success → เขียน PostLog ตอน `mark_posted` พร้อม hook/style/voice/bgm → snapshot metrics → รายงานสูตรที่ชนะ
   - แตะ: `tiktok_autopost_extension/background.js`, `scripts/api_exports.py`, `scripts/post_log.py`, `scripts/api_schedule_queue.py`, `scripts/api_analytics.py`
   - test เพิ่ม: `background.test.cjs` (detach/editor-gone แต่ URL เดิม → ไม่ mark), `tests/test_schedule_queue.py`, `tests/test_tiktok_stats_import.py`, `tests/test_export_versioning.py` (mark-posted สร้าง PostLog 1 แถวพอดี; sync 2 ครั้ง = 2 snapshot; analytics ไม่นับ <48 ชม.)
   - ข้อ 9 (mirror JSON ใน git) ต้องให้ user ยืนยันก่อน `git rm --cached`
3. **Editor quick wins** (แถว 16, 17, 18) — Ctrl+S ตัดคลิป, undo ท่วม, `clipKey` ครบ
   - แตะ: `hooks/useEditorShortcuts.js`, `hooks/useEditorHistory.js` (+ `coalesceKey`), `EditorShell.jsx`, `SequencePlayer.jsx:3608` — **สองไฟล์หลังมี diff ค้างของ Codex ให้รอ Codex ส่งงานก่อน** ส่วน shortcuts/history แก้ได้เลย
   - test เพิ่ม: `hooks/useEditorShortcuts.test.js` ใหม่ (Ctrl+S ไม่ split), `lib/editorHistory.test.js` (slider 20 ครั้ง = 1 undo), `tests/test_preview_render_parity.py` + test เทียบ `buildSegments` หลังเปลี่ยน speed
4. **Cutout เสถียร** (แถว 10, 12, 11) — `import sys` (1 บรรทัด), GPU semaphore, SAM2 quality gate/manifest ตรงจริง
   - แตะ: `scripts/background_isolation_video_worker.py`, `scripts/api_background_isolation.py`, `scripts/background_isolation_sam2_worker.py` — **อยู่ในไฟล์ที่ Codex แก้ค้าง (S0/S1) ต้องประสานก่อน**
   - test เพิ่ม: `kill_process_tree` กับ process จริงที่ยังรัน (ไม่ NameError, process ตาย), `tests/test_background_isolation_sam2.py` (คลิปสังเคราะห์ subject หายกลางคลิป → manifest รายงานเฟรมว่าง), สอง request SAM2 พร้อมกันรันต่อคิว (runner จำลอง ไม่แตะ GPU)
5. **ต่อโค้ดที่เสร็จแล้ว + ช่องว่าง CapCut ที่ถูกสุด** (แถว 38 + silence/beat bulk + denoise) — `color_match.py` มี test อยู่แล้วแค่ไม่ต่อสาย; ปุ่ม bulk silence-cut/beat-cut ใช้ `silence_detect.py`/`beat_sync.py` ที่มี; denoise `afftdn` opt-in — ทั้งหมด opt-in ไม่กระทบสเปกเดิม
   - แตะ: `scripts/stages/video_assembly_stage.py`, `scripts/stages/audio_mix_stage.py`, `EditorShell.jsx`/`Toolbar.jsx` (รอ Codex)
   - test เพิ่ม: `tests/test_color_match.py` (integration เมื่อ opt-in), filter chain `afftdn` ใน `tests/test_audio_mix_stage*`, parity ถ้ากระทบ preview

**ไม่ใส่ใน Top 5 แต่ควรรู้:** แถว 21 (default เสียง Puck vs Fenrir) กระทบเสียงทุกคลิป ต้องให้ user ตัดสินใจ ไม่ใช่ agent; แถว 19/23/33 (keyframe UI, Gemini word timing, retention scrape) ผลสูงแต่แรง L

## ภาคผนวก: hardcoded absolute path ที่ต้องแก้ (ขัดกฎข้อ 2)
`tools/`: `download_bgm_pack.py:14`, `download_chillhop_pack.py:14`, `download_instant_hook_pack.py:13`, `download_new_thai_fonts.py:4`, `reorganize_product_folders.py:24`, `clean_and_organize_tmp.py:7`, `audit_video_resolutions.py:5`, `build_60s_mali_burst_ass.py:18`, `download_gsm_photos.py:10`, `fetch_70mai_assets.py:5`, `fetch_mix_flip_pack.py:12`, `scrape_official_mi_assets.py:9`, `render_60s_{dynamic,clean_pro,cinematic,pro}_master.py`, `render_mali_master.py:11`, `render_snap_style_hands_on.py:21`, `render_{font_comparison,new_distinct_fonts,individual_font_cards,ui_font_comparison}.py:5-7`
ข้อมูลใน repo ที่ฝัน path: `02_Assets/.vision_cache.json`, `02_Assets/Music/bgm_*.json`, `02_Assets/asset_registry.json:6+`
`scripts/` runtime: ไม่พบ (มีแค่ comment/docstring) · `frontend/src`: ไม่พบ

## ที่ตรวจแล้วปลอดภัย
`/api/delete-file` กันคลิป posted/`Posted/` และ fail-closed (`api_videos.py:1116-1162`) · `_safe_product_dir` กัน traversal (`:126-142`) · `mark_posted` ไม่เขียนทับหลักฐาน (`api_exports.py:700-736`) · store หลัก (ProductStore/ExportRegistry) ใช้ SQLite + mirror แบบ atomic (`db.py:409-414`) · backup delete ผ่าน `resolve_safe_path` (`backup_engine.py:275-282`) · upload `upload_storage.py:21-36` ไม่ทับไฟล์เดิม · ไม่พบโค้ดที่เขียน `draft_content.json`

## ภาคผนวก: ไฟล์ที่ต้องแตะ + test ที่ต้องเพิ่ม ต่อแถวของตาราง 1

พรอมพ์ขอให้ระบุต่อข้อ ("→ Top5-N" = รายละเอียดอยู่ในหัวข้อ Top 5) ชื่อ test ที่ขึ้นต้นด้วย `tests/` ตรวจแล้วว่ามีไฟล์อยู่จริง ส่วนที่ระบุ "ใหม่" ต้องสร้าง

| แถว | ไฟล์ที่ต้องแตะ | test ที่ต้องเพิ่ม |
|---|---|---|
| 1, 2, 3, 4, 29 | → Top5-1 | → Top5-1 |
| 5, 6, 7, 8 | → Top5-2 | → Top5-2 |
| 9 | `.gitignore`, `scripts/db.py` (snapshot รายวัน) — ต้องให้ user ยืนยัน `git rm --cached` | `tests/` ใหม่สำหรับ DocumentTable: mirror เก่ากว่า/ย้อนกลับต้องไม่ทำให้แถวใหม่ใน SQLite หาย |
| 10, 11, 12 | → Top5-4 | → Top5-4 |
| 13 | `scripts/background_isolation.py`, `cutout_runtime.py`, `frontend/src/lib/cutoutEngineModel.js`, `backgroundIsolationConfig.js` | `tests/test_background_isolation.py` + `frontend/src/lib/cutoutEngineModel.test.js`: default engine, status `cancelled`, regex id `bgseq1-`, EPSILON ตรงกันสองฝั่ง |
| 14 | `scripts/video_editor.py:1459-1462`, `frontend/src/lib/backgroundIsolationPreview.js` (แก้คู่) | `tests/test_background_isolation_render_integration.py` + `tests/test_preview_render_parity.py` (สีขอบ subject ตรงต้นฉบับ) |
| 15 | `scripts/storage_cleaner.py:298-320` | `tests/test_storage_cleaner.py`: purge ไม่ลบ cutout ของโปรเจกต์ที่ยังใช้ |
| 16, 17, 18 | → Top5-3 | → Top5-3 |
| 19 | `frontend/src/lib/timelineMath.js`, `keyframeModel.js`, `subjectFrameMapping.js`, `scripts/keyframe_engine.py`, `scripts/video_editor.py:884-909`, `ClipInspector.jsx` (UI) | `keyframeModel.test.js` + `timelineMath.test.js` (สูตรเดียวกัน) + `tests/test_preview_render_parity.py` |
| 20 | `frontend/src/hooks/useProjectAutosave.js`, `useProjectLoader.js`, `EditorHeader.jsx` | `frontend/src/lib/projectSaveQueue.test.js` (ถ้ามี) หรือ hook test ใหม่: retry/409/ข้อความผิดตอน flush ล้ม |
| 21 | `scripts/api_render.py:177`, `pipeline_context.py:363`, `pipeline.py:112-113`, `voice_stage.py:444`, `api_batch_render.py:19-23`, `BatchRenderModal.jsx:94-98` — **รอ user ตัดสินใจ** | `tests/test_batch_render.py` + `tests/test_voice_stage_engine_guard.py`: default ตรง AGENTS ข้อ 5 |
| 22 | `scripts/gemini_tts_engine.py:403-416`, `voice_stage.py:385` | `tests/test_gemini_tts_engine.py`: mock subprocess returncode≠0 ต้อง raise และไม่ใช้ wav เก่า |
| 23 | `scripts/stages/voice_stage.py`, `scripts/subtitle/word_reveal.py` | `tests/test_voice_stage_alignment_and_duration.py` (cue มี word_timings เรียง ไม่ทับ ไม่เกิน duration) + `tests/test_preview_render_parity.py` — ห้ามเปลี่ยน font contract |
| 24 | `scripts/subtitle_engine.py:494-506`, `scripts/translator.py` | `tests/test_translator_script.py` + `tests/test_bilingual_subtitles.py`: bilingual=False ไม่เรียก translate_batch, cache hit ไม่เรียกเครือข่าย |
| 25 | `scripts/config.py:104-105`, `scripts/stages/shot_matching_stage.py:561-598` | test ใหม่ cadence 3 วิแรก + `tests/test_preview_render_parity.py` (ผ่าน clip_list) — **เปลี่ยนจังหวะตัด ถาม user ก่อน** |
| 26 | `scripts/stages/subtitle_stage.py:83,101-104`, `pipeline_context.py:370` | test ใหม่ `hook_duration` auto — **กระทบเวลา hook ถาม user ก่อน** |
| 27 | `scripts/pipeline.py:84-92,306-348`, `scripts/stages/video_assembly_stage.py:20,44-62` | `tests/test_preview_render_parity.py:569-587` เปลี่ยนจาก string-match เป็นเรียก stage จริง + เคส hard-cut ทั้งคลิป |
| 28 | `scripts/stages/source_resolution.py:38-60` | test ใหม่: ไม่มีวิดีโอ → error ชัด ไม่หยิบรูป Inbox ผิดสินค้า |
| 30 | `scripts/product_store.py:1454-1468`, `ProductToClip.jsx:3085` | test ใหม่ `product_store` delete: posted + force → มี snapshot |
| 31 | `scripts/api_products.py:492-508`, `scripts/api_videos.py:712-717` | test ใหม่: path นอกโปรเจกต์ถูกปฏิเสธ; batch-delete ไม่ลบ reference ของสินค้าอื่นที่ชื่อไฟล์ซ้ำ |
| 32 | `scripts/api_schedule_queue.py:29,1053,1082-1100`, `api_tiktok_autopost.py:34,236-262`, `api_exports.py:687-690` | `tests/test_schedule_queue.py`: failed/retry, restart แล้ว pending ไม่หาย |
| 33 | `tiktok_autopost_extension/stats_parser.js` (ต้องยืนยัน DOM หน้า analytics ก่อน) | `tiktok_autopost_extension/stats_parser.test.cjs` + fixture HTML |
| 34 | `scripts/product_scraper.py:1068-1069,1192-1193`, `scripts/post_log.py` | `tests/test_tiktok_stats_import.py` หรือ test ใหม่ hashtag performance |
| 35 | `scripts/backup_engine.py:141-164,224`; restore จริง = ไฟล์ใหม่ | `tests/test_backup_engine.py`: `.cache` ไม่อยู่ใน zip, list คืน `uncompressed_mb`; restore ต้อง backup ไฟล์เดิมก่อนทับ |
| 36 | รายการ tools ในภาคผนวก path → ใช้ `scripts/config.py` + `__main__` guard + `--dry-run` | test ใหม่ import tool แล้วไม่มี side effect |
| 37 | `scripts/api_posts.py`, `api_tokens.py`, `api_recording.py`, `recording_sessions.py`, `api_typesafe_studio.py`, `upload_storage.py` | contract test ใหม่ต่อ router (TestClient + tmp_path); frontend `*.test.js` ใหม่สำหรับ `audioPeaks/angleToForm/hookStyles/lut3d/uiScale` |
| 38 | `scripts/stages/video_assembly_stage.py` | `tests/test_color_match.py` + integration opt-in เปิด/ปิด |
| 39 | `scripts/api_exports.py:233-237`, `export_registry.py:119-123` (ใช้ `path_index()`) | `tests/test_export_versioning.py`: ผลลัพธ์เดิม, จำนวน stat ลดลง |
| 40 | `scripts/api_exports.py:639`, `background.js:36-47`, `tools/playwright_tiktok_assistant.py:18`, comment ที่อ้างแผนนอกโปรเจกต์ | `tests/test_export_versioning.py` (ปก 3:4 ย้ายไป Posted) + `background.test.cjs` |

## ผลตรวจครบตามพรอมพ์ (self-check)
- ขั้นเตรียม 4 ข้อ: ทำแล้ว (TODO ≤100 บรรทัด, `git status`, ARCHITECTURE, แผนลง TODO พร้อมชื่อเอเจนต์+โมเดล)
- ขอบเขต 7 หมวด: ครบ (pipeline, editor, cutout, schedule/export, extension, tools/audit, test)
- หลักฐานต่อข้อ: ครบ; ข้อที่ไม่ได้เปิดอ่านระบุ "ยังไม่ได้ยืนยัน"
- CapCut: ไม่พบสำเนา `draft_content.json` ใน repo (glob แล้ว) ไม่ได้ค้นเว็บ จึงไม่มีแหล่งอ้างอิงภายนอก ทุกแถวฝั่ง CapCut = ยังไม่ได้ยืนยัน
- ข้อห้าม: ไม่แก้โค้ด/font/ซับ, ไม่สร้างไฟล์ใน 04_Exports, ไม่ติดตั้งอะไร, ไม่แตะ draft CapCut, ไม่ใช้ Jev (ไม่มีทางเลือก 3–7 ก่อน audit)
