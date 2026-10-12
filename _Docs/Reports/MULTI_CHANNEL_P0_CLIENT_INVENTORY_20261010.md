# P0-C — Inventory ฝั่ง Client สำหรับระบบหลายช่อง

- **ดำเนินการโดย:** Claude Code (Claude Opus 5.5) — agent P0-C
- **วันที่:** 2026-10-10
- **ขอบเขต:** อ่านอย่างเดียว ไม่ได้แก้โค้ด ไม่ได้รัน server/test/render
- **วิธีตรวจ:** ตรวจ frontend เองโดยใช้สคริปต์ parse `api.js` และ grep ส่วน extension, HyperFrames kit และ CLI ให้ sub-agent ที่อ่านอย่างเดียวช่วยตรวจ ผมยังไม่ได้เปิดยืนยันเลขบรรทัดของสามส่วนนี้ทุกจุด
- **ข้อมูลที่อ่านด้วยเครื่องได้:** `MULTI_CHANNEL_P0_CLIENT_INVENTORY_20261010.json` (ไฟล์เดียวกันนี้ มีรายการ call site ครบ 296 จุด)

## 1. สรุปตัวเลข

| หมวด | จำนวน |
|---|---|
| ฟังก์ชัน export ใน `frontend/src/api.js` (axios instance เดียวกัน) | 199 (ไม่มีผู้เรียก 23) |
| call site ที่ component/hook/lib เรียกฟังก์ชันจาก api.js | 296 ใน 44 ไฟล์ |
| จุดที่ใช้ fetch ตรงหรือเรียก axios default ตรง (ไม่ผ่านฟังก์ชันใน api.js) | 10 |
| ไฟล์ที่ใส่ URL `/api/...` ลงใน `<video>`/`<img>`/`<a>`/`@font-face` (browser ใส่ header เองไม่ได้) | 14 ไฟล์ ราว 60 จุด |
| storage key ฝั่ง browser (รวม cache ในหน่วยความจำ 2 ตัว) | 25 รายการ: ต้องแยกตามช่อง 13, global 12 |
| จุดที่ poll ซ้ำเป็นรอบ | 12 |
| flow ของ extension | 18 รายการ: network 10, message/scripting 8 |
| จุดใน HyperFrames kit และ bridge ที่ต้องแก้ | 15 + 4 จุดฝั่ง frontend |
| CLI ที่อ่าน/เขียน store | 17 ตัว ทุกตัวอ่าน/เขียน store ตรง ไม่ผ่าน API |

## 2. Frontend: ชั้นที่ใช้เรียก API

- `frontend/src/api.js:5` สร้าง axios instance (`baseURL: '/api'`) และมี response interceptor แค่ตัวเดียว (`:14`) **ยังไม่มี request interceptor** จึงเป็นจุดเดียวที่ควรใส่ `X-OmniCut-Channel` แต่ตามแผน §5.2 ต้อง "เก็บ scope ณ เวลาที่ส่ง" ไม่ใช่อ่านค่าช่องปัจจุบันตอนส่ง
- เรื่อง auth: Vite proxy ใส่ `X-API-Key` ให้ฝั่ง server (`frontend/vite.config.js`, `proxy.configure`) ตัว browser ไม่ได้ถือ secret เอง
- จุดที่ไม่ผ่าน wrapper (ต้องใส่ scope เอง):
  - `hooks/useProjectAutosave.js:317` ส่ง keepalive `PATCH /api/projects/{name}/state` ตอน pagehide/beforeunload โดยใช้ header จาก `lifecycleSaveHeaders()` (`:9`) **ต้องใช้ช่องที่ผูกกับ job ที่ค้างอยู่ ไม่ใช่ช่องปัจจุบัน**
  - `components/VoicePickerModal.jsx:60,90` เรียก voice presets/preview ซึ่งเป็น global
  - `components/MobileQuickStudio.jsx:513` fetch ไฟล์วิดีโอผลลัพธ์ไปใช้กับ share
  - `components/SequencePlayer.jsx:3454,3599` (axios default), `:4496` (voice), `:4727` (sfx); `lib/audioPeaks.js:25`; `lib/lut3d.js:260`
- **ผลการออกแบบที่สำคัญ:** browser ส่งคำขอ `/api/media/...` จาก `<video src>`, `<img src>`, `<a href>` และ `@font-face` เอง จึง **ใส่ header ไม่ได้** จุดเหล่านี้อยู่ที่ ContentTrackerHub (9 จุด), ExportGallery (8), ScheduleAgenda (3), AssetPanel (5), RawVaultPanel, MediaPickerModal, MediaAssetsHub, SystemAssets, `lib/mediaUrl.js`, filmstrip (`api.js:461`, `lib/timelineFilmstrip.js:68`) และ background-isolation `artifactBaseUrl` ใน SequencePlayer guard ของ media/filmstrip จึงต้องรับ scope ผ่าน query param หรือ cookie และตรวจ ownership ของ path ฝั่ง backend เหมือนที่ extension ใช้ `?api_key=` อยู่แล้ว
- ฟังก์ชันใน api.js ที่ไม่มีผู้เรียกเลย (23 ตัว เช่น `createProduct`, `getPosts`, `createPost`, `setPostMetrics`, `getAngles`, `uploadMultipleFiles`, `createGadgetMediaProjectFromSlot`) ดูรายชื่อทั้งหมดใน JSON → `frontend_fetch_sites.unused_exports`

## 3. หน้าจอ → route ที่ใช้

รายละเอียดครบอยู่ใน JSON → `frontend_pages_components` (44 ไฟล์) ตารางนี้สรุปเฉพาะหน้าที่แผน §5.2 กำหนดไว้

| หน้าจอ | ไฟล์ | route หลัก | ต้องแยกตามช่อง |
|---|---|---|---|
| Shell/App | `App.jsx` | status, videos, exports, products, schedule-queue, PATCH angle | ใช่ |
| Producer | `producer/ProducerHub.jsx`, `QuickRefPage.jsx` | producer/notes*, upload-ref-media, ai-idea-to-angle, products, exports, schedule template, tiktok-stats/latest | ใช่ (notes/refs ต้องตัดสินว่า shared หรือแยกช่อง) |
| ProductToClip | `ProductToClip.jsx` (25 ฟังก์ชัน) | products/*, angles/*, shot-list, scene catalogs, upload, render/batch, tasks | ใช่ |
| Tracker | `ContentTrackerHub.jsx` | products, schedule-queue, shot-list, mark-posted, tiktok-autopost/prepare, tasks | ใช่ |
| Schedule | `ScheduleAgenda.jsx` (render อยู่ใน Tracker) | schedule-queue (CRUD, template, auto-fill, prepare) | ใช่ |
| Global Editor | `editor/EditorShell.jsx` (25), `NewClipPanel.jsx`, `ProjectSelector.jsx`, `EditorHeader.jsx`, `hooks/useRenderJob.js` | projects/*, render, reroll, render/status, background-isolation, angle status/cover | ใช่ (assets, hook templates และ hook-motion-presets เป็นของใช้ร่วม) |
| Export/Post Studio | `ExportGallery.jsx`, `CoverStudioModal.jsx` | exports, link-angle, mark-posted, delete-file, covers/*, tiktok-autopost/prepare, reveal-file | ใช่ |
| Analytics | `analytics/tabs/*` | analytics/production, analytics/inventory, tiktok-stats/* | Production/Inventory/Performance แยกช่อง; Storage/Tokens เป็น global |
| Gadget Media | `GadgetMediaHub.jsx`, `gadget-media/*` | gadget-media campaigns/projects/* | ใช่ (`preset-sources` เป็น global) |
| HyperFrames hub | `hyperframes/HyperFramesHub.jsx` | hyperframes/compositions, create-clip, render, status, styles, open-studio | ใช่ (create/render/list) |
| Mobile Studio | `MobileQuickStudio.jsx` | mobile-studio/* (catalog, session, assemble, task, upload, quick-add), mark-posted, recording-sessions | ใช่ |
| Mobile Filming (QR) | `MobileFilmingPage.jsx` | recording-sessions/*, shot-list, tasks | ใช่ |
| Mobile Quick Post (QR) | `MobileQuickPostPage.jsx` | products, mark-posted | ใช่ (ดูข้อ 6: อาจไม่ได้ render เลย) |
| Activity/Tasks | `context/TaskContext.jsx`, `ActivityCenter.jsx`, `BatchRenderModal.jsx` | tasks/active, cancel, delete, clear-completed, tiktok-stats/milestones, render/status | ใช่ (`clear-completed` ตอนนี้ล้างทุกช่อง) |
| Global/system | `SystemSettings.jsx`, `TokenDashboard.jsx`, `SystemAssets.jsx`, `MediaAssetsHub.jsx`, `SubSrtTool.jsx` | backup, tokens, assets, typesafe status, sub-srt | ไม่ต้อง (หน้าจอต้องบอกขอบเขตให้ชัด) |

## 4. Storage ฝั่ง browser

| key | ไฟล์:บรรทัด | รูปค่า | แยกช่อง | วิธีย้าย |
|---|---|---|---|---|
| `capcut_active_product_context` | App.jsx:175,224 | object สินค้าเต็มตัว | ✔ | ย้ายเข้า namespace main ครั้งเดียว แล้วใช้ revalidate ที่ App.jsx:308 |
| `capcut_selected_angle_index` | App.jsx:186,228 | int | ✔ | ย้ายพร้อม product context |
| `capcut_active_angle_context` | App.jsx:192,230 | `{productId,angleId,batch}` | ✔ | ย้ายเข้า main |
| `capcut_task_cache` | TaskContext.jsx:39,135 | task 20 รายการล่าสุด | ✔ | แยก namespace หรือเลิก cache |
| `omnicut_active_project` (+ URL `?project=`) | EditorShell.jsx:224,849,1063,1130 | ชื่อโปรเจกต์ | ✔ | ย้ายเข้า main และให้ URL มี channel |
| `omnicut_active_render_job` | lib/renderJobModel.js:5,138,164 | `{jobId, projectKey}` | ✔ | เพิ่ม `channel_id` (ActivityCenter.jsx:992 ฟัง event `storage` ข้ามแท็บอยู่) |
| `capcut_studio_form` | lib/studioDefaults.js:49,67; NewClipPanel.jsx:150 | ฟอร์มสร้างคลิป | ✔ | ย้ายเข้า main |
| `capcut_script_lab` | ScriptLab.jsx:83,113 | ข้อมูลสินค้า + scripts | ✔ | ย้ายเข้า main |
| `omnicut_today_picked_scripts` | ContentTrackerHub.jsx:960,969 | array id | ✔ | ย้ายเข้า main |
| `omnicut_producer_targets` | lib/producerInsights.js:13 | `{dailyCuts,weeklyCuts,dailyPosts}` | ✔ (รอตัดสินใจ) | copy ไป main |
| `omnicut_boss_playbook` | lib/producerInsights.js:14 | array notes | ✔ (รอตัดสินใจ shared หรือแยก) | ค่าเริ่มต้นเป็น main |
| `omnicut.mobileWorkflow` (sessionStorage) | lib/mobileStudioFlow.js:1; MobileQuickStudio.jsx:155,377 | `{productId,angleId,sessionId…}` | ✔ | เพิ่ม `channel_id` |
| `projectRevision` Map (หน่วยความจำ) | lib/projectRevision.js:3 | ชื่อโปรเจกต์ → sha256 | ✔ | ใช้ key เป็นช่อง+โปรเจกต์ |
| workspaceData cache (หน่วยความจำ) | lib/workspaceData.js:6 | status/rawVideos/exports/products/scheduleQueue | ✔ | ใช้ key ตามช่อง หรือ invalidate ทั้งหมดตอนสลับ |
| `omnicut_tiktok_autopost_enabled` | SystemSettings.jsx:35,44; ExportGallery.jsx:510 | 'true'/'false' | ✘ | เก็บไว้เป็นสวิตช์ UI global; gate จริงคือ `posting_enabled` ต่อช่อง |
| UI prefs: `capcut_active_tab`, `capcut_ui_font`, `omnicut.uiMode`, `capcut_ui_scale`, `capcut_tracker_view_mode`, `omnicut_export_gallery_view_mode`, `omnicut_assets_view_mode`, `omnicut_guide_checklist_v1`, `omnicut.previewQuality`, panel layout 6 keys (`hooks/usePanelLayout.js`) | หลายไฟล์ | ค่าเดี่ยว | ✘ | คงเป็น global |

ไม่พบการใช้ IndexedDB, Cache API หรือ BroadcastChannel ส่วน cache ในหน่วยความจำของ audioPeaks/lut3d/voice buffer ใช้ URL ของ asset ร่วมเป็น key จึงไม่ต้องแยกช่อง

## 5. จุดที่ response ที่มาช้าอาจทับ state หลังสลับช่อง (§5.2)

1. `App.jsx:264` `refreshData` เรียก `setStatus`, `setVideos`, `setExportsList` หลัง await โดยไม่เช็ก generation
2. `lib/workspaceData.js` มี generation ต่อ key แล้ว แต่ key ไม่มีช่อง และ cache อายุ 2 วินาทีอาจคืนรายการของช่อง A ให้ช่อง B
3. `context/TaskContext.jsx:141-247` poll ทุก 1.5/6 วินาทีแล้ว `setTasks` ทั้งก้อน มีปัญหาย่อยสามข้อ:
   - `refreshTrigger` (`:166`) ยิงเมื่องานของช่องไหนก็ได้เสร็จ ทำให้ ProductToClip โหลดใหม่ (ProductToClip.jsx:2573)
   - `jumpToTaskResult` (`:277`) พาไปหน้าผลลัพธ์โดยไม่ระบุช่อง และ set product ของงานลงช่องปัจจุบัน
   - `clearCompletedTasksApi` (`:270`) ล้างงานของทุกช่อง
4. `hooks/useProjectAutosave.js` งาน save ที่ค้างในคิวหรือ keepalive ของโปรเจกต์ A จะถูกส่งออกไปพร้อม header ของ B ถ้า wrapper อ่านค่าช่องปัจจุบันตอนส่ง ช่วงที่เสี่ยงคือตอน flush ขณะสลับโปรเจกต์หรือช่อง (`:338`)
5. `EditorShell.jsx:1100-1140` เรียก `getProjects`/`getAllAssets` ตอน mount โดยไม่มี guard ส่วนการโหลดโปรเจกต์ผ่าน `useProjectLoader` มี sequence guard แล้ว (ใช้เป็นแบบอย่างได้)
6. `ProductToClip.jsx:2565` `onFocus → loadHistory()` ไม่มี stale guard (ทั้งไฟล์ไม่มี cancelled/abort)
7. ไฟล์ที่ไม่มี guard เลย ได้แก่ `ContentTrackerHub.jsx` (มี poll ทุก 12 วินาทีที่ `:1278` และ revalidate ตอน focus/visibility), `producer/ProducerHub.jsx`, `producer/QuickRefPage.jsx` (poll notes ทุก 20 วินาทีที่ `:138`), `analytics/tabs/*`, `HyperFramesHub.jsx`, `RawVaultPanel.jsx`, `MediaPickerModal.jsx`, `NewClipPanel.jsx`
8. จุด poll ที่ต้องผูกกับช่องของงานไม่ใช่ช่องที่กำลังดู: `ActivityCenter.jsx:974` (ทุก 1 วินาที อ่าน job จาก localStorage กลาง), `BatchRenderModal.jsx:109`, `gadget-media/ProductWorkspace.jsx:153,176`, `hooks/useRenderJob.js:201`, `EditorShell.jsx:408` (มี cancelled guard แล้ว) และ `mobileStudioFlow.pollMobileTask` (มี stop guard แล้ว)
9. ในโค้ดทั้งหมดยังไม่มีการใช้ `AbortController` เลย

## 6. Deep link, URL param และ QR

- `App.jsx:44` `mode`/`quick`; `:71` `view=quick-ref`/`quick_ref=1`; `:82` `film=1&session=&return=&product=&angle=`
- `EditorShell.jsx:221` `?project=`; `MobileQuickStudio.jsx:381` `product/angle/mobile_session`
- QR ที่สร้าง URL ได้แก่ `ExportGallery.jsx:37` (`buildQuickPostUrl`), `ContentTrackerHub.jsx:2247`, `ShotListModal.jsx:76` (filming), `lib/mobileStudioFlow.js:8` (`filmingUrl`), `Sidebar.jsx:40` และ `Header.jsx:34` (mobile_url)
- **มือถือที่สแกน QR จะเปิด browser ใหม่ที่ sessionStorage ว่าง** URL ทุกตัวจึงต้องพกค่าช่องไปด้วย และ backend ต้องตรวจว่า resource เป็นของช่องนั้นจริง
- **ข้อสังเกตที่ยังไม่ยืนยัน:** `App.jsx:58-65` คำนวณ `isQuickPostMode` แต่ไม่ได้ใช้ และ `MobileQuickPostPage` ถูก lazy-import ที่ `:23` แต่ไม่มีที่ไหน render ลิงก์ `?quick_post=1` จึงน่าจะไม่ถูกใช้งานจริง (เปิดแล้วตกไปที่ MobileQuickStudio หรือ desktop) ควรตรวจในเบราว์เซอร์จริง

## 7. ตัวตนช่องที่ hardcode อยู่

- `SequencePlayer.jsx:357` `WATERMARK_TEXT` (rizanntry) เป็นคู่ของ `scripts/subtitle_engine.py:167` ต้องแก้คู่กันตามกฎ Preview = Render
- label `@rizanntry`: `editor/NewClipPanel.jsx:735`, `editor/EditorHeader.jsx:275`, `UserGuide.jsx:64`
- hashtag ค่าเริ่มต้น `#รีวิวของดี #พิกัดในตะกร้า`: `ExportGallery.jsx:1336`
- `ExportGallery.jsx:1349` และ `ContentTrackerHub.jsx:1131` เปิด `tiktokstudio/upload` ใน Chrome profile ไหนก็ได้ที่กำลังเปิดอยู่ ไม่มีการตรวจบัญชี

## 8. TikTok autopost extension

- **Manifest:** MV3 v0.2.0 permission คือ debugger/tabs/storage/sidePanel/scripting/windows ไม่มี content_scripts และไม่มี externally_connectable `popup.js`/`popup.html` ไม่ได้ผูกกับ manifest (dead code และ `popup.js:37` เรียก `/pending` โดยไม่มี key)
- **Backend URL และ auth:**
  - backend hardcode ไว้ที่ `http://127.0.0.1:8000` (`background.js:31`, `sidepanel.js:1`)
  - auth ใช้ `X-API-Key` ผ่าน `authedFetch` (`auth_key.js:47`) เก็บ key ใน `chrome.storage.local['omnicutApiKey']` และ media ใช้ `?api_key=`
  - **ไม่มี capability/version handshake** มีแค่ `manifest.version` ที่แสดงบนหน้าจอ (`sidepanel.js:925`)
- **Network flows** (รายละเอียดใน JSON → `extension_message_flows`):
  - `/api/tiktok-autopost/pending`: GET อ่าน job, ทุก action ดึงใหม่เองที่ `background.js:1618,1648,1726,1813`
  - `/api/tiktok-autopost/clear`: ล้าง job
  - `/api/tiktok-autopost/cover`: อัปเดตปก
  - `/api/tiktok-autopost/prepare`: เตรียม job จาก side panel ที่ `sidepanel.js:542`
  - `/api/exports/mark-posted`: มาร์คอัตโนมัติ (`background.js:61`) และกดเอง (`sidepanel.js:871`)
  - `GET /api/exports` และ `GET /api/schedule-queue`: ไม่แยกช่อง
  - `/api/media`: โหลดภาพ/วิดีโอ preview
  - `POST /api/tiktok-stats/import`: ส่ง `{rows}` โดยไม่มีบัญชี
- **Message flows:**
  - มี `chrome.runtime.onMessage` ตัวเดียวที่ `background.js:1863` แมป action ไว้ที่ `:1853-1861`: `upload-file-only`, `type-caption-only`, `attach-product-only`, `schedule-mode-only`, `click-post-only`, `upload-cover-only`, `prepare-details`
  - lock อยู่ในหน่วยความจำของ service worker (`actionRunning :1851`)
  - automation ทำผ่าน `chrome.debugger` (CDP) ส่วน stats ใช้ `scripting.executeScript` (`sidepanel.js:931,999`)
- **Side effect** ทุกอันยังไม่มีการตรวจบัญชี:
  - upload: `runUploadFileOnly :1617`
  - caption: `:1768` ใช้ข้อความจาก panel ไม่ใช่จาก job
  - ผูกสินค้า: `:1664` จับคู่ด้วย 6 ตัวท้ายของรหัส (`:759-766`)
  - ตั้งเวลา: `:1692`
  - ปก: `:1642`
  - prepare-details: `:1811` (ไม่กดโพสต์)
  - **กดโพสต์:** `runClickPostOnly :1725` → `clickPostButton :1538` ถ้าหาปุ่มหลักไม่เจอจะ fallback ไปกดปุ่ม "โพสต์/Post/Schedule" ตัวสุดท้าย (`:1557-1569`) และ `isPostSuccessUrl :1389` ถือว่าสำเร็จเมื่อ URL เป็น tiktok หน้าใดก็ได้ที่ไม่ใช่ upload
  - `findUploadTab :135-173` ตรวจแค่ URL
- **การอ่านบัญชีจริง:** ตอนนี้ **ไม่มีเลย** ไม่มี selector สำหรับ avatar/handle และไม่ได้อ่าน page data ร่องรอยเดียวคือ `video_url` ในแถว stats ที่มี `/@handle/` (`stats_parser.js:106,159`) ซึ่งยังไม่ได้ parse ออกมา P3 ต้องหา selector ของ Studio ใหม่จากหน้าจริง
- **Tests ของ extension:**
  - ไฟล์: `background.test.cjs` (~31 test), `clip_state.test.cjs` (4), `stats_parser.test.cjs` (11) และ backend `tests/test_api_tiktok_autopost.py`, `tests/test_tiktok_stats_import.py`
  - วิธีรัน: `node --test ...` ในโฟลเดอร์ extension ซึ่ง **ไม่อยู่ใน `npm test`**
  - test ที่ต้องอัปเดตเมื่อเปลี่ยน protocol: "prepare never publishes" (`:57`) และ "confirmed post marks exact pending export" (`:417`)

## 9. HyperFrames kit และ bridge

- `kit/channels.js:5-19` มีแค่ `main` (@rizanntry) ส่วน `second` ถูก comment ไว้ ไฟล์ `assets/shared/img/channel_second.jpg` มีอยู่จริง (133,762 bytes)
- `kit/kit.js:61-77` `HF.applyChannel` ถ้าช่องไม่รู้จักจะแค่ `console.warn` (`:67-69`) จึงยังไม่เป็น render gate
- `kit/new_clip.py:53` รับ `--channel` แต่ไม่ validate และบังคับ `--vo` (`:51`)
- composition 4 จาก 10 ตัวใช้ `data-channel` อีก 6 ตัว hardcode ลายน้ำไว้ (ess02 asmr/battery/hype/jaokum/review, goc01-spec) และ `clips/ess02-hype-25s/template.tpl:84` ก็ hardcode ด้วย
- `scripts/api_hyperframes.py`:
  - request model `:49-62` ไม่มี channel
  - metadata เดาสินค้าจากชื่อไฟล์ (`:99`)
  - หา VO ด้วย glob ข้ามช่อง (`:286-292`)
  - เรียก subprocess `new_clip.py` โดยไม่ส่ง `--channel` (`:307-313`)
  - registry ไม่มี channel และ product_id เป็นรหัสสั้น (`:384-396`)
- **Bug ที่พบระหว่างทาง:**
  - `:347` ต่อ `"Ready_to_post"` ซ้ำกับ `EXPORTS_DIR` (`config.py:81`) ทำให้ได้โฟลเดอร์ซ้อน
  - `:294` ยอมให้ pov_chat ไม่มี VO แต่ `new_clip.py` บังคับ `--vo`
- Frontend: `HyperFramesHub.jsx:462` (create ไม่ส่ง channel), `:487` (render ส่ง `product_id: comp.product.toUpperCase()`), `:444` (port 3002) และ `:548,:773` (ลิงก์ hardcode) ส่วน `api.js:610` ใช้ port ค่าเริ่มต้น 3100

## 10. CLI ที่ใช้ store ตรงโดยไม่ผ่าน API

ไม่มี CLI ตัวไหนเรียก HTTP API ทุกตัวเข้า store ตรง จึงหลบ guard ฝั่ง API ทั้งหมด

- **ต้องรองรับช่อง:**
  - `scripts/pipeline.py` เขียน ExportRegistry และฝังลายน้ำ
  - `tools/playwright_tiktok_assistant.py` ใช้ profile `tools/tiktok_browser_profile` ตัวเดียว ต้องแยก profile ต่อบัญชี
  - `scripts/migrate_json_to_sqlite.py` ต้องกำหนดช่องเริ่มต้นให้แถว legacy
  - `scripts/migrate_compound_angle_ids.py`
- **อาจต้องรองรับ:**
  - `scripts/backfill_product_codes.py` ถ้ารหัสสินค้าแยกตามช่อง
  - `tools/system_health_check.py` ควรแสดงยอดแยกตามช่อง
  - CLI สรุปผล `post_log.py`, `product_store.py`, `project_manifest.py`
- **เสี่ยงเมื่อมีฟิลด์ channel:**
  - `tools/clean_products_data.py` เขียน `_Docs/products.json` ดิบโดยไม่ผ่าน store
  - `tools/repair_swollen_projects.py` เขียน project.json ดิบและไม่มี dry-run
- รายละเอียดทั้งหมดอยู่ใน JSON → `cli_tools`

## 11. Tests ที่เฟสถัดไปต้องรักษาให้ผ่าน

- `cd frontend && npm test` คือ `node --test src/lib/*.test.js` (101 ไฟล์ **ไม่รวม** `src/lib/motion/*.test.js`)
- test ที่เกี่ยวกับ storage และ cache:
  - `workspaceData.test.js`
  - `renderJobModel.test.js`, `renderJobPolling.test.js`, `renderJobController.test.js`
  - `projectRevision.test.js`, `projectAutosave.test.js`, `projectSaveQueue.test.js`
  - `editorEntry.test.js`, `postRenderRevision.test.js`, `notificationReliability.test.js`
  - `mobileStudioFlow.test.js`, `producerInsights.test.js`, `scheduleQueue.test.js`, `exportGalleryDeleteSyncContract.test.js`
- test ของ extension ดูข้อ 8

## 12. ความเสี่ยงสูงสุด

**เมื่อสลับช่อง**
1. Autosave/keepalive ส่งงานของโปรเจกต์ A ไปพร้อม header ของช่อง B
2. TaskContext เป็นตัวกลางตัวเดียว: แจ้งเตือนหรือ refresh ข้ามช่อง, jump ไปหน้าผลลัพธ์โดยไม่มีช่อง, clear-completed ล้างทุกช่อง
3. `capcut_active_product_context`, `omnicut_active_project` และ render job ใน localStorage อยู่ใน key กลางที่แชร์กันทุกแท็บ
4. URL ของ media ใส่ header ไม่ได้ ต้องออกแบบ guard ด้วย query param หรือ cookie
5. QR บนมือถือไม่มีข้อมูลช่อง
6. ไม่มี AbortController และหลายหน้าไม่มี stale guard

**เมื่อโพสต์ผิดบัญชีหรือโพสต์ซ้ำ**
1. ไม่มีการตรวจบัญชีก่อน side effect ใดเลย และยังไม่มี selector สำหรับอ่านบัญชี
2. `_pending` เป็น singleton ที่ `/prepare` เขียนทับได้ แต่ละขั้นจึงอาจดึง job คนละตัว
3. ปุ่มโพสต์ใช้ fallback และนับ "URL อะไรก็ได้" เป็นผลสำเร็จ ทำให้ mark posted ผิดหรือพาไปโพสต์ซ้ำ
4. ถ้า mark ไม่สำเร็จ ระบบไม่ clear pending และปุ่ม mark เองก็ไม่เรียก `/clear`
5. stats import ไม่มีบัญชีและจับคู่กับรายการของทุกช่อง (`register_missing=True`)
6. ไม่มี handshake ทำให้ client เก่ายัง claim/clear ได้

## 13. สิ่งที่ยังไม่ได้ข้อสรุป

- ลิงก์ quick_post ใช้งานได้จริงหรือไม่ (ข้อ 6) ต้องตรวจในเบราว์เซอร์
- selector ใน TikTok Studio สำหรับอ่าน handle จริง ซึ่งยังไม่มีในโค้ดและต้องสำรวจจากหน้าจริง
- `omnicut_boss_playbook`, producer targets และ producer notes จะใช้ร่วมหรือแยกตามช่อง ต้องให้เจ้าของตัดสินใจ
- เลขบรรทัดของ extension, kit และ CLI ได้มาจาก sub-agent และยังไม่ได้ตรวจซ้ำทุกจุด
