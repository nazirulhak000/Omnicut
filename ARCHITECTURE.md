# OmniCut Pro Studio Architecture

เอกสารนี้อธิบายโครงสร้างสถาปัตยกรรมที่ใช้งานจริง ณ วันที่ 2026-09-24 (ปรับปรุงล่าสุด) หากสถานะงานหรือผลทดสอบต่างจากเอกสารนี้ ให้ยึด [TODO.md](TODO.md) และโค้ดปัจจุบันเป็นหลัก

## ภาพรวมระบบ

```mermaid
flowchart LR
    UI[React/Vite 10-Module UI] --> API[FastAPI 26 modular routers]
    API --> JOB[Task and render jobs]
    JOB --> PIPE[TikTokAutoCutterPipeline]
    PIPE --> STAGES[Modular pipeline stages]
    STAGES --> MEDIA[FFmpeg, TTS, AI providers]
    STAGES --> MANIFEST[03_Projects/project.json]
    MEDIA --> EXPORT[04_Exports/Ready_to_post]
    MANIFEST --> EDITOR[Editor load, autosave, reroll]
    API --> ANALYTICS[Analytics & Operations Hub]
    UI --> GADGET[Gadget Media Product Studio]
    GADGET --> GMAPI[Product Project API]
    GMAPI --> GMSTORE[03_Projects/GadgetMedia]
    GMAPI --> GMEXPORT[04_Exports/Ready_to_post/GadgetMedia]
```

ค่ามาตรฐานของไฟล์โพสต์จริงคือ 1080x1920 (9:16), H.264, AAC, 30 FPS และ `+faststart` ส่วน Draft ใช้ 720x1280 เพื่อทดสอบเร็วขึ้น

## เมนูและการนำทางฝั่ง Frontend (10 รายการ: Gadget Media + เมนู 0-8)

ระบบจัดหมวดหมู่การทำงานเป็น 10 รายการใน `frontend/src/components/Sidebar.jsx` — เมนูเสริม `gadget` (Gadget Media) อยู่บนสุด ตามด้วยเมนูตัวเลข id `producer` ถึง `guide`:

0. **0. ผู้ช่วยโปรดิวเซอร์ (`producer/ProducerHub.jsx` + `producer/QuickRefPage.jsx`):** ศูนย์บัญชาการรายวัน — Daily Mission, Spotlight Next Mission, Pacing Calculator, 1-Click Playbook Add, คลังไอเดียและเรฟ (Idea & Ref Vault พร้อม Visual Insights จาก Gemini Vision) และ Producer Notes ที่ปักหมุด/แก้ไขได้ (ซิงก์ผ่าน `scripts/api_producer.py`)
1. **1. สินค้า → คลิป (`ProductToClip.jsx`):** วิเคราะห์สินค้าด้วย AI (ลิงก์/สเปก/รูป) สร้าง Content Matrix 4-10 สคริปต์ พร้อมระบุ TikTok Product ID / ลิงก์ปักตะกร้า และสไตล์การตัดต่อ 10 แบบที่ผูกกับ Hook Style 1-to-1
2. **2. แทร็กเกอร์ 4 เฟส (`ContentTrackerHub.jsx`):** จัดการสเตจงาน 4 ขั้น (สคริปต์พร้อม, เลือกคลิป, กำลังตัดต่อ, ตัดต่อเสร็จ) พร้อม Shot List Modal และ Mobile Filming Page
3. **3. ตัดต่อ & สร้างคลิป (`editor/EditorShell.jsx`):** สตูดิโอตัดต่อไทม์ไลน์ Multi-track, SequencePlayer (Canvas 2D), Inspector ปรับแต่ง Overlay/Motion/Subtitles
4. **4. Export Gallery (`ExportGallery.jsx`):** คลังวิดีโอสำเร็จรูป, พรีวิว, Post Studio (สร้างปก 3:4/9:16, reveal file ใน Explorer, คัดลอกแคปชั่น, ส่งต่อ TikTok Auto-post, มาร์คว่าโพสต์แล้ว)
5. **5. Media Assets Hub (`MediaAssetsHub.jsx`):** ศูนย์รวมฟอนต์, BGM, SFX, สติกเกอร์/ป้ายกำกับ, และ Color LUTs
6. **6. สถิติ & วิเคราะห์รวม (`analytics/AnalyticsHub.jsx`):** แดชบอร์ดวิเคราะห์ 5 แท็บ (`analytics/tabs/`) — Production (Funnel 4 เฟส), Performance (ผลงาน TikTok + คลิปปัง), Tokens, Storage (รวม Safe Cache Cleaner) และ Inventory — ด้วย Pure SVG Glassmorphic Charts (AreaLine, Donut, Funnel, ProgressRing)
7. **7. ตั้งค่าระบบ (`SystemSettings.jsx`):** ตรวจสอบ System Health, AI Providers, เสียงพากย์ Edge-TTS/Gemini, และการเชื่อมต่อมือถือผ่าน QR Code
8. **8. คู่มือใช้งาน (`UserGuide.jsx`):** Interactive Knowledge Base สำหรับผู้ใช้ (Sticky TOC, เช็กลิสต์ติ๊กได้พร้อมความจำ localStorage, การ์ดเมนู 0-7, โฟลว์ 7 ขั้นกดเปิดเมนูได้, Quick Action ปุ่มลัดแก้ปัญหา, FAQ ค้นหาได้)

เมนูเสริม **Gadget Media (`GadgetMediaHub.jsx` + `gadget-media/GadgetMediaStudio.jsx`)** อยู่บนสุดของ Sidebar แยกเป็น `Product Studio` สำหรับ workflow `1 สินค้า = 1 Product Video Project = 1 Approved Master` (เดิน 6 ขั้น `Brief → Sources → Evidence → Story → Cut → Review` ผ่าน `StageRail` + `ProductWorkspace` + `QualityInspector`) และ `Campaign และ Analytics` สำหรับวางแผน/ติดตามผล โดย Product Workspace มี Brief, Sources, Evidence, Story, Cut และ Review อยู่ในเมนูเดียว มีไทม์ไลน์ผ่าน `gadget-media/timeline/GadgetMediaTimelineHost.jsx` และไม่ส่งงานไป Global Editor (storage แยกที่ `*/GadgetMedia/`)

## Backend (FastAPI 26 Routers)

Entry point คือ `scripts/api_server.py` ทำหน้าที่สร้าง FastAPI app, ตรวจสอบ API Key security, ตั้ง CORS, และ mount router โดเมนต่างๆ รวม 208 routes (ตรวจสอบจริงผ่าน `len(app.routes)` = 208 โดยเป็น HTTP API route 204 รายการ ที่เหลือเป็น docs/openapi):

| ลำดับ | โมดูล Router | หน้าที่หลัก |
| :--- | :--- | :--- |
| 1 | `scripts/api_phase1.py` | Project lifecycle, AI script generator, partial reroll |
| 2 | `scripts/api_editor.py` | Timeline manifest load/save, filmstrip thumbnails |
| 3 | `scripts/api_tokens.py` | Token ledger, usage breakdown, daily aggregates |
| 4 | `scripts/api_voice.py` | Edge-TTS / Gemini TTS voice synthesize & audio preview |
| 5 | `scripts/api_videos.py` | Raw video library, upload multipart, file reveal |
| 6 | `scripts/api_covers.py` | Post Studio Cover generation (3:4, 9:16 jpg export) |
| 7 | `scripts/api_tiktok_autopost.py` | TikTok auto-post extension bridge & upload queue |
| 8 | `scripts/api_schedule_queue.py` | Schedule agenda & auto-queue slots |
| 9 | `scripts/api_products.py` | Product queue, scraping, TikTok Product ID extraction/resolution |
| 10 | `scripts/api_exports.py` | Export gallery scan, mark posted, media info probe |
| 11 | `scripts/api_tasks.py` | Background async tasks & progress tracking |
| 12 | `scripts/api_render.py` | Full video assembly, render jobs, queue runner |
| 13 | `scripts/api_posts.py` | Post log, publication tracker, performance metrics |
| 14 | `scripts/api_shot_lists.py` | Shot List builder & filming task assignment |
| 15 | `scripts/api_recording.py` | Mobile filming stream & upload ingest |
| 16 | `scripts/api_analytics.py` | Aggregated metrics 5 แท็บ สำหรับ Analytics Hub |
| 17 | `scripts/api_tiktok_stats.py` | ซิงก์สถิติ TikTok Studio, จับคู่โพสต์ manual และ milestone คลิปปัง |
| 18 | `scripts/api_backup.py` | One-click system backup & restore (รวม WAL snapshot) |
| 19 | `scripts/api_asset_dedup.py` | สแกนและล้างไฟล์สื่อซ้ำอย่างปลอดภัย |
| 20 | `scripts/api_hooks.py` | Hook Header และ Hook Variation / A-B generator |
| 21 | `scripts/api_batch_render.py` | เรนเดอร์หลายคลิปพร้อมกันผ่าน `BatchRenderManager` |
| 22 | `scripts/api_producer.py` | AI Producer Hub — notes, missions และ vision insights |
| 23 | `scripts/api_background_isolation.py` | ตัดพื้นหลัง/แยกตัวแบบ async พร้อมกู้งานค้างตอน startup |
| 24 | `scripts/api_gadget_media.py` | Campaign, Content Slot, rights readiness และ analytics ของ Gadget Media |
| 25 | `scripts/api_gadget_media_projects.py` | Product Library/Workspace, source probe, scoped timeline, Gemini TTS, quality gate, render และ Approved Master |
| 26 | `scripts/api_typesafe_studio.py` | TypeSafe System One (Jev) — Hook ranking/Retention Score และ Smart B-roll matcher |

การเปลี่ยน route, method, request หรือ response ต้องตรวจสอบความเข้ากันได้กับ `frontend/src/api.js` เสมอ

## Pipeline การเรนเดอร์

`scripts/pipeline.py` เป็น orchestrator ภายนอก ส่วน state ระหว่าง stage อยู่ใน `scripts/pipeline_context.py`

Cutout รุ่นใหม่ใช้ `scripts/background_isolation_video_worker.py` ถอดเฉพาะช่วงต้นฉบับผ่าน FFmpeg pipe แล้วส่งผล rembg เข้า `cutout.webm` (VP9 alpha) พร้อม manifest รุ่น 2 ใน `03_Projects/.cache/background-isolation-videos/`. `api_background_isolation.py` ให้ข้อมูล manifest และวิดีโอแบบ Range; `SequencePlayer.jsx` วาดเฟรมวิดีโอโปร่งใสบน Canvas หลัง `requestVideoFrameCallback`; `video_editor.py` ถอดด้วย `libvpx-vp9` เพื่อรักษา alpha ระหว่าง Render. Artifact PNG รุ่นเดิมยังอ่านได้เฉพาะโปรเจกต์เก่า.

ลำดับหลัก (8 Stages):

1. `SourceResolutionStage` ตรวจและเตรียมวิดีโอ/รูปต้นทางจาก `01_Raw/`
2. `ScriptStage` สร้างหรือใช้สคริปต์ที่กำหนด พร้อมระบบทำความสะอาดคำห้าม/วรรณยุกต์
3. `VoiceStage` สร้างเสียงพากย์ (ค่าเริ่มต้น Gemini Flash TTS + preset Fenrir ชายสตรองพรีเมียม, เลือก Edge-TTS +15% ได้เอง) และ timing alignment
4. `SubtitleStage` สร้าง cues, overlays, kinetic highlight และไฟล์ ASS
5. `AudioMixStage` รวม Voice, BGM, SFX และ clip audio ตามระดับสัดส่วนมาตรฐาน
6. `ShotMatchingStage` จับคู่ภาพกับบทด้วย AI เมื่อเปิดใช้
7. `VideoAssemblyStage` ประกอบและ export ผ่าน FFmpeg 1080x1920 30FPS H.264
8. `ProjectManifest` บันทึก state และ artifact paths แบบ atomic/versioned (`03_Projects/project.json`)

Reroll ใช้ stage เดียวกับ Full Render ผ่าน `resume_from` จึงต้องรักษา `ProjectManifest.should_run()` และ artifact reuse contract ห้ามสร้าง branch ประมวลผลสำรองอีกชุด

## Editor State & Save Queue

`frontend/src/components/editor/EditorShell.jsx` เป็น composition shell งาน state และคำสั่งสำคัญแยกออกเป็นโมดูลเฉพาะทาง:

| หน้าที่ | โมดูล |
| :--- | :--- |
| Manifest → Editor state / Save payload | `frontend/src/lib/editorProjectState.js` |
| Autosave, flush, page unload | `frontend/src/hooks/useProjectAutosave.js` |
| Latest-save-wins queue | `frontend/src/lib/projectSaveQueue.js` |
| Project loading and stale response guard | `frontend/src/hooks/useProjectLoader.js` |
| Render polling/resume/cleanup | `frontend/src/hooks/useRenderJob.js` |
| Undo/redo | `frontend/src/hooks/useEditorHistory.js` |
| Clip/caption/overlay commands | `frontend/src/hooks/useEditorCommands.js` |
| Selection and shortcuts | `useEditorSelection.js`, `useEditorShortcuts.js` |

Manual Save และ Autosave ต้องเรียก serializer เดียวกัน ห้ามประกอบ payload ซ้ำใน component การสลับโปรเจกต์ต้อง flush pending save ก่อน และ response เก่าต้องไม่เปลี่ยน state ของโปรเจกต์ใหม่

## Timeline และ Keyframes

`frontend/src/lib/timelineSchema.js` กำหนด Timeline Document v2 พร้อม in-memory migration จาก manifest รุ่นเก่า โดยยังไม่เขียนทับไฟล์เก่าจนผู้ใช้บันทึก

- `timelineMath.js` จัดการเวลา, trim, split, transition, magnetic snap และ ripple math
- `useEditorShortcuts.js` ควบคุมคีย์ลัดด่วน (Spacebar, S ตัดคลิป, N สลับ Snap, M สลับโหมด Cutout Mask, J/K/L, Ctrl+Z/Y, Ctrl+S)
- `SequencePlayer.jsx` เรนเดอร์ Canvas 2D พร้อม Smart Center Crosshair Guides (`🎯 กึ่งกลางจอ 50%`) และ Cutout Mask Inspection 3 โหมด (ปกติ / หมากรุก / ขาวดำ)
- `timelineTrackModel.js` จัดการ track layout และ audio/video/overlay track state
- `keyframeModel.js` และ `scripts/keyframe_engine.py` ต้องรักษาสูตร interpolation ให้ตรงกัน
- `Timeline.jsx` ประกอบ ruler, lanes, playhead และ context menu จาก component ย่อยใน `editor/timeline/`

## Preview และ Render Parity (กฎเหล็ก)

ภาพเดียวกันมีสอง implementation คู่ขนานที่ต้องให้ภาพตรงกัน 100%:

- **Preview:** Canvas 2D ใน `frontend/src/components/SequencePlayer.jsx`
- **Render:** ASS/libass ใน `scripts/subtitle_engine.py` และโมดูลใต้ `scripts/subtitle/`

Overlay model มี mirrored pair คือ `frontend/src/lib/overlayModel.js` และ `scripts/overlay_model.py` การแก้ geometry, font, color, alpha, outline, motion, wrapping หรือ timing ต้องแก้ทั้งคู่และทำตาม [.agents/rules/preview_render_parity.md](.agents/rules/preview_render_parity.md)

Subtitle modules ปัจจุบัน:

- `subtitle/font_metrics.py` วัด glyph advance และ font mapping
- `subtitle/translation_service.py` แปลและ wrap ข้อความ
- `subtitle/motion_effects.py` สร้าง ASS motion/keyframes
- `subtitle/overlay_events.py` สร้าง event สำหรับ hook/text overlays
- `subtitle/badge_plate_renderer.py` สร้าง plate/badge drawing
- `subtitle/word_layout.py` คำนวณ per-word coordinate layout

## ข้อมูลบนดิสก์

- `00_Inbox/` ไฟล์ดิบ ไอเดีย สคริปต์ย่อ และไฟล์วิดีโอที่ sync จากมือถือ
- `01_Raw/` วัตถุดิบต้นฉบับแยกตามโฟลเดอร์ ห้ามลบหรือเขียนทับโดยไม่ได้รับอนุญาต
- `02_Assets/` Media Assets ส่วนกลาง (Fonts, Music, SFX, Stickers, LUTs)
- `03_Projects/<project>/project.json` คือ manifest หลัก ใช้ atomic temp-file replace
- `04_Exports/Ready_to_post/` เก็บไฟล์ export จริง และ `04_Exports/Posted/` เก็บไฟล์ที่โพสต์แล้ว
- `05_Covers_Thumbnails/` เก็บปกคลิป 3:4 และ 9:16 ที่สร้างจาก Cover Studio
- `06_Archive/` พื้นที่จัดเก็บไฟล์เก่าสำรอง
- `_Docs/post_log.json` และ `_Docs/products.json` เป็น runtime data ของระบบ
- Gadget Media แยก ownership เป็น `01_Raw/GadgetMedia/`, `03_Projects/GadgetMedia/`, `04_Exports/Ready_to_post/GadgetMedia/`, `05_Covers_Thumbnails/GadgetMedia/` และ `_Docs/gadget_media/`
- `scripts/gadget_media_timeline_adapter.py` แปลง Story/EDL เป็น Timeline Document v2 ที่มี `workspace_scope=gadget_media`; ใช้ math/preview/render engine ร่วม แต่ไม่ใช้ manifest หรือ status ของ Global Editor

## สถานะการทดสอบปัจจุบัน (Verification Gates) — วัดจริง 2026-09-24

- **Python Scripts Compilation:** ผ่าน 100% (`python -m compileall -q scripts`)
- **FastAPI Endpoints:** 208 routes รวม 26 modular domain routers
- **Python Pytest Suite:** 1,807 tests collected (`pytest tests/` มี testpaths = tests ไม่กวาดชน tools/)
- **Frontend Suite:** 312 tests passed, 0 failures (`npm test` → `node --test src/lib/*.test.js`)
- **Vite Production Build:** ผ่านเรียบร้อย 2,026 modules transformed
