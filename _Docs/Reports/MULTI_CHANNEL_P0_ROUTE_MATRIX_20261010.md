# P0 Route Matrix — OmniCut multi-channel (2026-10-10)

- **ดำเนินการโดย:** Claude Code (Claude Opus 5.5) — agent P0-A (read-only inventory)
- **อ้างอิงแผน:** `_Docs/Plans/PLAN_MULTI_CHANNEL_20261010.md` §2, §3, §5.1, §9 (P0), §10 (AC02)
- **ไฟล์คู่:** `_Docs/Reports/MULTI_CHANNEL_P0_ROUTE_MATRIX_20261010.json` (1 แถวต่อ method+path)
- **ขอบเขต:** อ่านอย่างเดียว ไม่แก้โค้ด/เทส ไม่รัน server/migration/render

## 1. วิธีนับและผลนับ

นับจาก `scripts.api_server.app.routes` ด้วย `.venv` (import app แล้ววน routes):
- รวม **232** route objects = **228 `APIRoute`** (ทุกตัว method เดียว) + **4 Starlette built-in** (`/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc` — global, ไม่มีข้อมูลช่อง)
- ไม่มี WebSocket route, ไม่มี `app.mount`/StaticFiles, ไม่มี FastAPI app ที่สอง; router 30 ตัวถูก `include_router` ที่ `scripts/api_server.py:284-313`
- **แถวใน JSON = 228** ตรงกับ APIRoute 228 แถวพอดี (built-in 4 ตัวระบุไว้ในข้อ 1.1 ไม่ใส่ใน JSON)
- Middleware: `api_key_gate` (`scripts/api_server.py:206-272`) — เป็น auth ไม่ใช่ channel scope; GET/HEAD `/api/media/*` รับ `?api_key=` ได้ (สำคัญต่อการออกแบบ scope ของ media เพราะ `<video>/<img>` ส่ง header ไม่ได้)

### 1.1 Server/route นอก FastAPI app (ต้องรู้ไว้ แต่ไม่อยู่ใน 228)

| ที่มา | Route | Scope | หมายเหตุ |
|---|---|---|---|
| `scripts/interactive_sam2_daemon.py:99-236` (http.server, `127.0.0.1:8008`) | `GET /health`, `POST /set_frame`, `POST /predict`, `POST /shutdown`, `OPTIONS *` | internal | เรียกจาก `scripts/interactive_sam2_client.py`; `/set_frame` รับ `source` path ใดก็ได้ (`:134`) ไม่มี confinement — ต้องให้ caller (`/api/background-isolation/interactive-segment`) ตรวจก่อนส่ง |
| `frontend/vite.config.js:8-35` (Vite dev middleware) | `GET /api/media/02_Assets/Fonts/{filename}` | shared | เสิร์ฟฟอนต์ตรงจาก Vite ไม่ผ่าน FastAPI; ตรวจ basename + .ttf/.otf แล้ว |
| `03_Projects/_HyperFrames_Studio` (`npx hyperframes preview`, เปิดผ่าน `POST /api/hyperframes/open-studio`, พอร์ต 3002) | HyperFrames Studio dev server | channel (composition) | ไม่พบการเรียก `/api/*` ของ OmniCut จาก kit/index.html; ผูกกับ OmniCut ผ่านไฟล์ใน compositions/ และ api_hyperframes |
| Starlette built-in | `/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc` | global | — |
| `frontend/src/api.js:244` `uploadMultipleFiles` | `POST /api/upload-multiple` | — | **ไม่มี route นี้ใน backend** และไม่มี component เรียกใช้ (dead code) |

## 2. สรุปตาม scope / risk

- scope: channel **164**, shared **38**, global **26**
- risk: blocker **82**, major **88**, minor **58**
- วิธีจัดประเภท: อ่าน handler จริง **228** แถว; heuristic (provisional) **0** แถว

| Module | routes | channel | shared | global | blocker | test files (URL-level) |
|---|---|---|---|---|---|---|
| `scripts.api_analytics` | 6 | 2 | 0 | 4 | 2 | test_analytics_hub.py |
| `scripts.api_asset_dedup` | 2 | 2 | 0 | 0 | 1 | test_api_asset_dedup.py |
| `scripts.api_audio_beats` | 2 | 0 | 2 | 0 | 0 | test_api_audio_beats.py |
| `scripts.api_background_isolation` | 7 | 1 | 6 | 0 | 1 | motion_capture/test_cutout_preview_render_parity.py, motion_capture/test_cutout_video_preview.py, motion_capture/test_subject_points_browser.py, test_api_background_isolation.py, test_sam2_gpu_api_integration.py |
| `scripts.api_backup` | 5 | 0 | 0 | 5 | 0 | test_api_backup.py |
| `scripts.api_batch_render` | 3 | 3 | 0 | 0 | 2 | test_batch_render.py |
| `scripts.api_covers` | 9 | 7 | 1 | 1 | 4 | test_api_covers_ai.py, test_api_covers_scene.py |
| `scripts.api_editor` | 6 | 2 | 4 | 0 | 1 | test_backend_api_contracts.py, test_hook_templates_custom.py, test_phase1_smoke.py, test_word_layout.py |
| `scripts.api_exports` | 4 | 4 | 0 | 0 | 2 | test_analysis_fixes.py, test_backend_api_contracts.py, test_mobile_desktop_sync_regression.py, test_post_lifecycle.py, test_post_log_integrity.py |
| `scripts.api_gadget_media` | 7 | 6 | 1 | 0 | 1 | test_api_gadget_media.py |
| `scripts.api_gadget_media_projects` | 13 | 13 | 0 | 0 | 5 | test_api_gadget_media_projects.py |
| `scripts.api_hooks` | 4 | 2 | 2 | 0 | 0 | test_api_hooks.py |
| `scripts.api_hyperframes` | 6 | 3 | 2 | 1 | 2 | test_api_hyperframes.py |
| `scripts.api_mobile_studio` | 9 | 8 | 1 | 0 | 4 | motion_capture/test_mobile_studio_browser.py, test_mobile_desktop_sync_regression.py, test_mobile_quick_studio.py |
| `scripts.api_phase1` | 25 | 19 | 2 | 4 | 11 | motion_capture/test_editor_shell_browser.py, motion_capture/test_footage_coverage_notice_browser.py, motion_capture/test_render_cutout_click_browser.py, motion_capture/test_render_preflight_browser.py, motion_capture/test_subject_points_browser.py, motion_capture/test_timeline_ux2_browser.py, motion_capture/test_voice_cut_preview_browser.py, test_analysis_fixes.py, test_backend_api_contracts.py, test_bug3_tiktok_product_id_and_conflict_clear.py, test_final_compatibility_signoff.py, test_phase1_smoke.py, test_posted_protection.py, test_prod1_tiktok_product_id_creation.py, test_product_batch_angles.py, test_product_code.py, test_product_cover_persistence.py, test_product_metadata.py, test_project_archive.py, test_project_revision.py, test_quota_swallowing_sites.py, test_refactor_baseline_contracts.py, test_render_completion_publication.py, test_reroll_script.py, test_safe1_disk_guard_and_snapshots.py, test_security_scraper_ssrf.py, test_voice_edit_api.py |
| `scripts.api_posts` | 9 | 9 | 0 | 0 | 3 | test_analysis_fixes.py, test_backend_api_contracts.py |
| `scripts.api_producer` | 8 | 8 | 0 | 0 | 4 | test_producer_notes_api.py, test_producer_vision_api.py |
| `scripts.api_products` | 19 | 18 | 0 | 1 | 10 | test_backend_api_contracts.py, test_bug3_tiktok_product_id_and_conflict_clear.py, test_posted_protection.py, test_prod1_tiktok_product_id_creation.py, test_product_batch_angles.py, test_qc_reviewed.py, test_reroll_script.py |
| `scripts.api_proxy` | 2 | 0 | 1 | 1 | 0 | motion_capture/test_high_resolution_playback_browser.py, motion_capture/test_subject_points_browser.py, test_api_proxy.py |
| `scripts.api_recording` | 5 | 5 | 0 | 0 | 0 | motion_capture/test_mobile_studio_browser.py |
| `scripts.api_render` | 4 | 2 | 0 | 2 | 1 | test_analysis_fixes.py, test_api_auth.py, test_backend_api_contracts.py, test_posted_protection.py, test_refactor_baseline_contracts.py, test_render_completion_publication.py, test_restart_recovers_orphaned_render_angle.py, test_safe1_disk_guard_and_snapshots.py, test_security_boundary_agent.py |
| `scripts.api_schedule_queue` | 11 | 11 | 0 | 0 | 8 | test_post_log_integrity.py, test_schedule_queue.py |
| `scripts.api_shot_lists` | 8 | 8 | 0 | 0 | 1 | test_manual_shot_map.py, test_manual_shot_map_sync.py |
| `scripts.api_tasks` | 5 | 5 | 0 | 0 | 3 | test_backend_api_contracts.py, test_product_metadata.py, test_reroll_script.py |
| `scripts.api_tiktok_autopost` | 4 | 4 | 0 | 0 | 4 | test_api_tiktok_autopost.py |
| `scripts.api_tiktok_stats` | 10 | 10 | 0 | 0 | 3 | test_tiktok_stats_import.py |
| `scripts.api_tokens` | 5 | 0 | 0 | 5 | 0 | test_backend_api_contracts.py |
| `scripts.api_typesafe_studio` | 6 | 0 | 5 | 1 | 1 | test_typesafe_studio.py |
| `scripts.api_videos` | 17 | 11 | 5 | 1 | 7 | motion_capture/test_cutout_preview_render_parity.py, motion_capture/test_cutout_video_preview.py, motion_capture/test_editor_shell_browser.py, motion_capture/test_footage_coverage_notice_browser.py, motion_capture/test_high_resolution_playback_browser.py, motion_capture/test_mobile_studio_browser.py, motion_capture/test_render_cutout_click_browser.py, motion_capture/test_render_preflight_browser.py, motion_capture/test_subject_points_browser.py, motion_capture/test_timeline_ux2_browser.py, motion_capture/test_voice_cut_preview_browser.py, test_analysis_fixes.py, test_api_covers_ai.py, test_audit_p0_safety.py, test_backend_api_contracts.py, test_covers_pro.py, test_delete_file_guard.py, test_mobile_desktop_sync_regression.py, test_mobile_quick_studio.py, test_post_lifecycle.py, test_posted_protection.py, test_refactor_baseline_contracts.py, test_security_boundary_agent.py, test_security_product_id_path_write.py |
| `scripts.api_voice` | 7 | 1 | 6 | 0 | 1 | test_backend_api_contracts.py, test_quota_swallowing_sites.py, test_quota_unmetered_sites.py, test_typesafe_studio.py |

## 3. Route matrix ทั้งหมด

คอลัมน์: R=read W=write RW=read_write; F=รับ/คืน path หรือแตะไฟล์ (พื้นผิวรั่วข้ามช่อง AC02); Callers: D=desktop M=mobile E=extension C=cli I=internal/ไม่พบผู้เรียก

### `scripts.api_analytics`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/analytics/production` | `get_production_analytics`:110 | channel | filter ProductStore.get_all() by product.channel == request channel | R |  | D | major |
| GET | `/api/analytics/storage` | `get_storage_analytics`:269 | global | posted_archive_potential.items / heavy_products should be filtered to request channel or route restricted to admin | R | F | D | major |
| POST | `/api/analytics/storage/purge-safe-cache` | `purge_safe_cache`:522 | global | admin/global-only; must not be callable per channel | W | F | D | blocker |
| GET | `/api/analytics/storage/cutout-cache` | `get_cutout_cache_stats`:540 | global | — | R | F | D | minor |
| POST | `/api/analytics/storage/purge-cutout-cache` | `purge_cutout_cache`:551 | global | admin/global-only | W | F | D | blocker |
| GET | `/api/analytics/inventory` | `get_inventory_health`:566 | channel | filter products by product.channel == request channel | R | F | D | major |

### `scripts.api_asset_dedup`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/assets/duplicates/scan` | `scan_duplicates`:16 | channel | — | R | F | D | major |
| POST | `/api/assets/duplicates/clean` | `clean_duplicates`:26 | channel | duplicate_paths[] -> 01_Raw/<product folder> of request channel | W | F | D | blocker |

### `scripts.api_audio_beats`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/audio/beats` | `get_bgm_beats`:88 | shared | bgm_name | R | F | D | minor |
| GET | `/api/audio/silences` | `get_media_silences`:147 | shared | media_path -> owner channel (project/raw/export) | R | F | D | major |

### `scripts.api_background_isolation`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| POST | `/api/background-isolation/preflight` | `preflight_background_isolation`:442 | shared | source_path -> source clip -> owning project/raw folder .channel | R | F | D | minor |
| POST | `/api/background-isolation/process` | `process_background_isolation`:460 | channel | source_path -> source clip -> project/raw .channel; project_name -> project.channel; task_id -> task_registry.channel (task stamped with channel) | W | F | D | blocker |
| GET | `/api/background-isolation/sequences/{artifact_id}/manifest` | `get_background_isolation_manifest`:606 | shared | artifact_id -> source clip -> project.channel (only if cutouts become channel-private) | R | F | D | minor |
| GET | `/api/background-isolation/videos/{artifact_id}/cutout.webm` | `get_background_isolation_video`:646 | shared | artifact_id -> source clip -> project.channel (if channel-private) | R | F | D | minor |
| GET | `/api/background-isolation/videos/{artifact_id}/preview.webm` | `get_background_isolation_video_preview`:654 | shared | artifact_id -> source clip -> project.channel (if channel-private) | R | F | D | minor |
| GET | `/api/background-isolation/sequences/{artifact_id}/frames/{frame_index}` | `get_background_isolation_frame`:669 | shared | artifact_id -> source clip -> project.channel (if channel-private) | R | F | D | minor |
| POST | `/api/background-isolation/interactive-segment` | `interactive_segment_endpoint`:687 | shared | source_path -> source clip -> project/raw .channel | R | F | D | major |

### `scripts.api_backup`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| POST | `/api/backup/create` | `create_backup`:11 | global | — | W | F | D | minor |
| GET | `/api/backup/list` | `list_backups`:21 | global | — | R | F | D | minor |
| GET | `/api/backup/download/{filename}` | `download_backup`:31 | global | filename | R | F | D | major |
| GET | `/api/backup/verify/{filename}` | `verify_backup`:49 | global | filename | R | F | I | minor |
| DELETE | `/api/backup/{filename}` | `delete_backup`:63 | global | filename | W | F | D | major |

### `scripts.api_batch_render`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| POST | `/api/render/batch` | `start_batch_render`:32 | channel | product_id -> product.channel_id; angle_ids -> product_id (enforced: filtered from product.angles, batch_render.py:231-236); project_name/angle_project_names -> project folder owned by same product/channel | W | F | D | blocker |
| GET | `/api/render/batch/{batch_id}` | `get_batch_render_status`:64 | channel | batch_id -> batch.product_id -> product.channel_id | R |  | D | major |
| POST | `/api/render/batch/{batch_id}/cancel` | `cancel_batch_render`:73 | channel | batch_id -> batch.product_id -> product.channel_id | W |  | D | blocker |

### `scripts.api_covers`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/covers/badges` | `get_badges_endpoint`:1108 | shared | — | R | F | D | minor |
| POST | `/api/covers/highlights` | `get_highlights_endpoint`:1114 | channel | video_path -> owning export/raw/project -> channel | RW | F | D | blocker |
| POST | `/api/covers/raw-sources` | `get_raw_sources_endpoint`:1122 | channel | video_path -> owning export -> channel; matched projects (03_Projects/*) -> channel; matched 01_Raw files -> product -> channel | R | F | D | major |
| POST | `/api/covers/product-ref-images` | `get_product_ref_images_endpoint`:1130 | channel | product_id -> product.channel; product_name/video_path -> fuzzy-matched product -> channel | R | F | D | major |
| POST | `/api/covers/generate-hooks` | `generate_hooks_endpoint`:1141 | global | — | R |  | D | minor |
| POST | `/api/covers/render-pro` | `render_pro_cover_endpoint`:1152 | channel | video_path -> export -> channel; raw_video_path -> raw clip -> product -> channel; custom_image_path / layer asset paths -> owning file (product image / cover / shared asset); export_filename -> target cover -> export -> | RW | F | D | blocker |
| POST | `/api/covers/generate` | `generate_cover_endpoint`:1197 | channel | video_path -> export/raw -> channel; output cover -> export -> channel | RW | F | D | blocker |
| POST | `/api/covers/grab-frame` | `grab_frame_endpoint`:1215 | channel | video_path -> export/raw -> channel | RW | F | D | major |
| POST | `/api/covers/ai-generate-image` | `ai_generate_cover_image_endpoint`:1346 | channel | source_image_path -> owning product image / file -> channel | RW | F | D | blocker |

### `scripts.api_editor`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/editor/filmstrip` | `get_filmstrip`:149 | channel | path -> 01_Raw / 03_Projects file of request channel (or shared 02_Assets) | RW | F | D | blocker |
| GET | `/api/editor/media-info` | `get_media_info_route`:170 | channel | path -> 01_Raw / 03_Projects file of request channel (or shared 02_Assets) | R | F | D | major |
| POST | `/api/editor/overlay/layout` | `get_overlay_layout`:183 | shared | font_name | R |  | D | minor |
| GET | `/api/editor/hook-templates` | `list_hook_templates`:210 | shared | — | R |  | D | minor |
| POST | `/api/editor/hook-templates` | `create_or_update_hook_template`:223 | shared | id | W |  | D | minor |
| DELETE | `/api/editor/hook-templates/{template_id}` | `remove_custom_hook_template`:234 | shared | template_id | W |  | D | minor |

### `scripts.api_exports`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/exports` | `list_exports`:228 | channel | each export file -> export_registry.channel; matched product/angle -> channel (if products become channel-owned) | RW | F | CDE | major |
| POST | `/api/exports/link-angle` | `link_export_to_angle`:592 | channel | export_id -> export_registry.channel; video_path -> export_registry.channel; product_id/angle_id -> channel (or shared product + channel-owned angle) | W | F | D | blocker |
| POST | `/api/exports/mark-posted` | `mark_posted`:875 | channel | export_id/file_path -> export_registry.channel; product_id/angle_id -> channel; matched queue row -> queue.channel; post_log row -> channel | W | F | DEM | blocker |
| GET | `/api/exports/media-info` | `get_export_media_info`:1011 | channel | path -> export_registry.channel (or per-channel export dir) | R | F | D | minor |

### `scripts.api_gadget_media`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/gadget-media/campaigns` | `list_campaigns`:57 | channel | campaign -> channel | R | F | D | major |
| POST | `/api/gadget-media/campaigns` | `create_campaign`:66 | channel | campaign_id unique globally vs per channel | W | F | D | major |
| GET | `/api/gadget-media/campaigns/{campaign_id}` | `get_campaign`:80 | channel | campaign_id -> campaign.channel | R | F | I | major |
| GET | `/api/gadget-media/campaigns/{campaign_id}/readiness` | `get_campaign_readiness`:85 | channel | campaign_id -> campaign.channel | R | F | D | major |
| GET | `/api/gadget-media/campaigns/{campaign_id}/analytics` | `get_campaign_analytics`:91 | channel | campaign_id -> campaign.channel | R | F | I | major |
| GET | `/api/gadget-media/preset-sources` | `get_preset_sources`:97 | shared | — | R | F | D | minor |
| PATCH | `/api/gadget-media/campaigns/{campaign_id}/slots/{slot_id}` | `update_slot`:108 | channel | campaign_id -> channel; slot_id -> campaign_id; product_project_id -> project.channel == campaign.channel | W | F | D | blocker |

### `scripts.api_gadget_media_projects`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/gadget-media/projects` | `list_projects`:157 | channel | project -> channel | R | F | D | major |
| POST | `/api/gadget-media/projects` | `create_project`:163 | channel | project_id unique global | W | F | D | major |
| GET | `/api/gadget-media/projects/{project_id}` | `get_project`:183 | channel | project_id -> project.channel | R | F | D | major |
| PATCH | `/api/gadget-media/projects/{project_id}` | `patch_project`:188 | channel | project_id -> project.channel; campaign_links[].campaign_id -> same channel; source_assets[].local_path -> project/raw owner | W | F | D | blocker |
| POST | `/api/gadget-media/projects/{project_id}/sources/probe` | `probe_project_source`:197 | channel | project_id -> channel; local_path -> project/raw owner | RW | F | D | blocker |
| POST | `/api/gadget-media/projects/{project_id}/timeline/build` | `build_project_timeline`:226 | channel | project_id -> channel | W | F | D | major |
| GET | `/api/gadget-media/projects/{project_id}/timeline` | `get_project_timeline`:237 | channel | project_id -> channel | R | F | D | major |
| PUT | `/api/gadget-media/projects/{project_id}/timeline` | `save_project_timeline`:246 | channel | project_id -> channel; clips[].source_path -> project/raw owner | W | F | D | blocker |
| POST | `/api/gadget-media/projects/{project_id}/quality/validate` | `validate_project_quality`:257 | channel | project_id -> channel | RW | F | D | major |
| POST | `/api/gadget-media/projects/{project_id}/audio/generate` | `generate_project_narration`:273 | channel | project_id -> channel; job_id -> render_jobs.channel | W | F | D | major |
| POST | `/api/gadget-media/projects/{project_id}/renders` | `start_project_render`:304 | channel | project_id -> channel; job_id -> channel; timeline clip sources -> project/raw owner | W | F | D | blocker |
| POST | `/api/gadget-media/projects/{project_id}/renders/{artifact_id}/approve` | `approve_project_render`:331 | channel | project_id -> channel; artifact_id -> project_id | W | F | D | major |
| POST | `/api/gadget-media/campaigns/{campaign_id}/slots/{slot_id}/project` | `create_project_from_slot`:340 | channel | campaign_id -> channel; slot_id -> campaign_id; slot.product_project_id -> same channel; new project inherits campaign channel | W | F | I | blocker |

### `scripts.api_hooks`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/hooks/styles` | `get_hook_styles`:45 | shared | — | R |  | I | minor |
| POST | `/api/hooks/generate` | `generate_hooks`:51 | shared | — | R |  | D | minor |
| POST | `/api/hooks/apply-angle` | `apply_hook_to_angle`:74 | channel | product_id -> product.channel_id; angle_id -> product_id (checked, batch ignored) | RW |  | D | major |
| POST | `/api/hooks/apply-project` | `apply_hook_to_project`:125 | channel | project_name -> project manifest.channel_id (or -> product.channel_id via manifest product_id) | RW | F | I | major |

### `scripts.api_hyperframes`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/hyperframes/status` | `get_hyperframes_status`:137 | global | — | R | F | D | minor |
| GET | `/api/hyperframes/styles` | `get_approved_styles`:194 | shared | — | R |  | D | minor |
| GET | `/api/hyperframes/compositions` | `list_compositions`:245 | channel | composition -> channel (no record exists; channel only lives in data-channel attr inside HTML) | R | F | D | major |
| POST | `/api/hyperframes/create-clip` | `create_clip`:257 | channel | product -> product.channel; vo_path -> project/raw owner; clip_id -> global uniqueness across channels (single compositions dir) | W | F | D | blocker |
| POST | `/api/hyperframes/render` | `render_composition`:329 | channel | composition_id -> composition.channel; product_id/angle_id -> product.channel (must equal composition channel); export record -> channel | W | F | D | blocker |
| POST | `/api/hyperframes/open-studio` | `open_studio`:419 | shared | port | W |  | D | major |

### `scripts.api_mobile_studio`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/mobile-studio/catalog` | `get_mobile_catalog`:46 | channel | product -> channel; session -> product | R | F | M | major |
| POST | `/api/mobile-studio/session` | `get_or_create_session`:87 | channel | product_id -> channel; angle_id -> product_id | W | F | M | major |
| POST | `/api/mobile-studio/assemble` | `assemble_and_render`:101 | channel | product_id -> channel; angle_id -> product_id; session_id -> product_id/angle_id; custom_raw_video -> product raw dir / channel; task -> channel; export record -> channel | W | F | M | blocker |
| GET | `/api/mobile-studio/task/{task_id}` | `get_mobile_task`:122 | channel | task_id -> task.channel | R | F | M | major |
| POST | `/api/mobile-studio/cancel/{task_id}` | `cancel_mobile_task`:140 | channel | task_id -> task.channel | W |  | M | blocker |
| POST | `/api/mobile-studio/quick-angle` | `create_quick_angle`:160 | channel | product_id -> channel | W | F | M | major |
| POST | `/api/mobile-studio/upload-video` | `upload_mobile_video`:176 | channel | product_id -> channel; angle_id -> product_id | W | F | M | blocker |
| POST | `/api/mobile-studio/products/quick-add` | `quick_add_product`:198 | channel | new product -> request channel; URL dedupe -> same channel | W | F | M | blocker |
| POST | `/api/mobile-studio/preview-voice` | `preview_mobile_voice`:210 | shared | text, voice | W | F | M | minor |

### `scripts.api_phase1`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| POST | `/api/ai/prompt` | `ai_prompt`:91 | global | — | R |  | I | minor |
| POST | `/api/ai/parse` | `ai_parse`:124 | global | — | R |  | D | minor |
| GET | `/api/ai/status` | `ai_status`:133 | global | — | R |  | I | minor |
| GET | `/api/angles` | `get_angles`:154 | shared | — | R |  | I | minor |
| GET | `/api/hook-motion-presets` | `get_hook_motion_presets`:164 | shared | — | R |  | D | minor |
| GET | `/api/posts` | `get_posts`:184 | channel | — | R |  | C | major |
| POST | `/api/posts` | `create_post`:194 | channel | clip_file -> export (export_registry) of request channel; product_name -> product of request channel | W | F | C | major |
| POST | `/api/posts/{post_id}/metrics` | `set_metrics`:216 | channel | post_id -> post.channel_id | W |  | I | blocker |
| GET | `/api/posts/performance` | `get_performance`:226 | channel | — | R |  | C | major |
| POST | `/api/product/fetch` | `fetch_product`:378 | global | url | R |  | I | minor |
| GET | `/api/products` | `list_products`:464 | channel | status | RW | F | CDM | major |
| POST | `/api/products` | `create_product`:473 | channel | — | W |  | C | major |
| PATCH | `/api/products/{product_id}` | `update_product`:482 | channel | product_id -> product.channel_id; angles[].project_name -> project manifest of same product/channel; angles[].selected_videos -> 01_Raw files of same product | W | F | D | blocker |
| DELETE | `/api/products/{product_id}` | `delete_product`:500 | channel | product_id -> product.channel_id | W |  | D | blocker |
| GET | `/api/projects` | `list_projects`:576 | channel | — | R | F | CD | major |
| GET | `/api/projects/{project_name}/origin` | `project_origin`:599 | channel | project_name -> product/angle (manifest render_params.product_id/angle_id) -> channel | R | F | D | major |
| DELETE | `/api/projects/{project_name}` | `delete_project`:628 | channel | project_name -> product/angle (manifest) -> channel | W | F | D | blocker |
| POST | `/api/projects/{project_name}/archive` | `archive_project`:710 | channel | project_name -> product/angle (manifest) -> channel | W | F | I | blocker |
| GET | `/api/projects/{project_name}` | `get_project`:732 | channel | project_name -> product/angle (manifest) -> channel | R | F | D | blocker |
| GET | `/api/projects/{project_name}/snapshots` | `list_project_snapshots`:762 | channel | project_name -> product/angle (manifest) -> channel | R | F | I | major |
| POST | `/api/projects/{project_name}/snapshots/{snapshot_id}/restore` | `restore_project_snapshot`:772 | channel | project_name -> product/angle (manifest) -> channel | W | F | I | blocker |
| PATCH | `/api/projects/{project_name}/cues` | `update_project_cues`:790 | channel | project_name -> product/angle (manifest) -> channel | W | F | D | blocker |
| PATCH | `/api/projects/{project_name}/clips` | `update_project_clips`:824 | channel | project_name -> product/angle (manifest) -> channel; clip_list[].source_path -> 01_Raw files of the same product/channel | W | F | D | blocker |
| PATCH | `/api/projects/{project_name}/state` | `update_project_state`:945 | channel | project_name -> product/angle (manifest) -> channel; clip_list/sticker/voice paths -> files of same channel or shared assets | W | F | D | blocker |
| POST | `/api/reroll` | `trigger_reroll`:1369 | channel | project_name -> product/angle (manifest render_params) -> channel; sticker_path/sticker_badge -> 02_Assets/Stickers (shared); bgm/lut/font -> shared 02_Assets; clip_list sources -> 01_Raw of same product | W | F | D | blocker |

### `scripts.api_posts`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/post-log` | `get_post_log`:13 | channel | — | R |  | I | major |
| POST | `/api/post-log` | `add_post_log`:20 | channel | clip_file -> export of request channel; product_name -> product of request channel | W | F | I | major |
| POST | `/api/post-log/{post_id}/metrics` | `update_post_log_metrics`:41 | channel | post_id -> post.channel_id | W |  | I | blocker |
| PATCH | `/api/post-log/{post_id}/metrics` | `update_post_log_metrics`:41 | channel | post_id -> post.channel_id | W |  | I | blocker |
| PATCH | `/api/posts/{post_id}/metrics` | `update_post_log_metrics`:41 | channel | post_id -> post.channel_id | W |  | I | blocker |
| GET | `/api/post-log/pending` | `get_pending_metrics`:53 | channel | — | R |  | I | major |
| GET | `/api/post-log/performance` | `get_angle_performance`:60 | channel | — | R |  | I | major |
| GET | `/api/post-log/summary` | `get_post_log_summary`:66 | channel | — | R |  | I | major |
| GET | `/api/posts/summary` | `get_post_log_summary`:66 | channel | — | R |  | C | major |

### `scripts.api_producer`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| POST | `/api/producer/upload-ref-media` | `upload_ref_media`:165 | channel | new ref file must be stamped with request channel (no index exists today; file name is the only identity) | W | F | D | major |
| GET | `/api/producer/ref-media/{filename}` | `get_ref_media`:222 | channel | filename -> ref media owner channel (needs index or per-channel dir) | R | F | I | major |
| GET | `/api/producer/notes` | `get_notes`:233 | channel | filter notes by note.channel_id == request channel (or explicit shared flag) | R | F | D | major |
| POST | `/api/producer/notes` | `save_notes`:239 | channel | every note id in payload -> notes.channel must equal request channel; replace must be limited to request channel's slice | W | F | I | blocker |
| POST | `/api/producer/notes/add` | `add_note`:258 | channel | if client id collides with existing note -> existing note.channel must equal request channel, else reject; stamp channel_id server-side | W | F | D | blocker |
| DELETE | `/api/producer/notes/{note_id}` | `delete_note`:281 | channel | note_id -> notes.channel == request channel | W | F | D | blocker |
| PUT | `/api/producer/notes/{note_id}` | `update_note`:290 | channel | note_id -> notes.channel == request channel; images[] ref filenames -> ref media owner channel | RW | F | D | blocker |
| POST | `/api/producer/ai-idea-to-angle` | `ai_idea_to_angle`:545 | channel | product_id -> products.channel == request channel; ref_images local names -> ref media owner channel | R | F | D | major |

### `scripts.api_products`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| POST | `/api/products/resolve-tiktok-id` | `resolve_tiktok_id_endpoint`:255 | global | url_or_id | R |  | D | minor |
| POST | `/api/products/{product_id}/preview-source` | `preview_product_source`:262 | channel | product_id -> product.channel_id == request channel | R |  | D | major |
| POST | `/api/products/{product_id}/preview-image-metadata` | `preview_product_image_metadata`:380 | channel | product_id -> product.channel_id | R | F | I | major |
| POST | `/api/products/{product_id}/preview-image-metadata-async` | `preview_product_image_metadata_async`:412 | channel | product_id -> product.channel_id; task -> channel (task registry entry must carry channel_id) | RW | F | D | major |
| POST | `/api/products/{product_id}/refresh-source` | `refresh_product_source`:428 | channel | product_id -> product.channel_id | RW |  | D | major |
| POST | `/api/products/{product_id}/videos` | `attach_video_to_product`:492 | channel | product_id -> product.channel_id; video_path -> must be inside the channel's raw folder (01_Raw/<channel>/...) | RW | F | I | blocker |
| DELETE | `/api/products/{product_id}/videos` | `remove_video_from_product`:511 | channel | product_id -> product.channel_id; video_path -> must be linked to this product and inside channel raw folder | W | F | D | blocker |
| DELETE | `/api/products/{product_id}/angles/{angle_id}` | `delete_product_angle`:533 | channel | product_id -> product.channel_id; angle_id(+batch) -> product_id (checked) | W |  | D | blocker |
| PATCH | `/api/products/{product_id}/angles/{angle_id}` | `update_product_angle_status`:545 | channel | product_id -> product.channel_id; angle_id(+batch) -> product_id (checked); export_id -> export.channel_id and export.product_id/angle_id; video_url -> channel exports folder; project_name -> project.channel_id | RW |  | D | blocker |
| PATCH | `/api/products/{product_id}/angles/{angle_id}/cover` | `update_product_angle_cover`:597 | channel | product_id -> product.channel_id; angle_id(+batch) -> product_id (checked); cover_path -> channel's covers folder | RW | F | D | major |
| POST | `/api/products/{product_id}/angles/{angle_id}/videos` | `update_angle_videos_endpoint`:624 | channel | product_id -> product.channel_id; angle_id(+batch) -> product_id (checked); selected_videos[] -> channel raw folder / product.videos | RW |  | D | blocker |
| POST | `/api/products/{product_id}/default-videos` | `set_default_videos_endpoint`:643 | channel | product_id -> product.channel_id; selected_videos[] -> channel raw folder | RW |  | D | blocker |
| GET | `/api/products/{product_id}/scene-catalogs` | `get_scene_catalogs`:656 | channel | product_id -> product.channel_id; video_path -> must be one of product's linked videos | R | F | D | blocker |
| POST | `/api/products/{product_id}/index-scenes` | `index_scenes_endpoint`:732 | channel | product_id -> product.channel_id; video_path -> must be one of product's linked videos; task -> channel | RW | F | D | blocker |
| POST | `/api/products/scrape-and-plan` | `scrape_and_plan`:863 | channel | new product -> request channel_id; url -> dedup must be scoped to channel; image_paths[] -> channel inbox/upload folder | RW | F | D | blocker |
| POST | `/api/products/scrape-and-plan-async` | `scrape_and_plan_async`:1090 | channel | new product -> request channel_id (must be captured at request time and passed to worker); url dedup -> channel; task -> channel | RW | F | CD | blocker |
| POST | `/api/products/{product_id}/angles/{angle_id}/reroll-script` | `reroll_angle_script`:1234 | channel | product_id -> product.channel_id; angle_id(+batch) -> product_id (checked); task -> channel | RW |  | D | major |
| POST | `/api/products/{product_id}/generate-batch` | `generate_product_batch`:1380 | channel | product_id -> product.channel_id; task -> channel | RW |  | D | major |
| POST | `/api/products/{product_id}/angles` | `add_product_angle`:1420 | channel | product_id -> product.channel_id; if cloned: source angle -> same channel | RW |  | D | major |

### `scripts.api_proxy`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/proxy/for-clip` | `proxy_for_clip`:120 | shared | source_path -> owner channel | RW | F | D | major |
| GET | `/api/proxy/status` | `proxy_cache_status`:163 | global | — | R | F | I | minor |

### `scripts.api_recording`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| POST | `/api/recording-sessions` | `create_recording_session`:32 | channel | product_id -> product.channel_id; angle_id -> product_id (NOT checked); session -> product/angle (store channel_id on session) | RW |  | D | major |
| GET | `/api/recording-sessions/{session_id}` | `get_recording_session`:45 | channel | session_id -> product_id -> product.channel_id (phone page may not send channel header; token is a capability) | R |  | M | major |
| POST | `/api/recording-sessions/{session_id}/segments` | `upload_recording_segment`:53 | channel | session_id -> product_id -> product.channel_id | W | F | M | major |
| DELETE | `/api/recording-sessions/{session_id}/segments/{beat_index}` | `delete_recording_segment`:85 | channel | session_id -> product_id -> product.channel_id | W | F | I | minor |
| POST | `/api/recording-sessions/{session_id}/finalize` | `finalize_recording_session`:113 | channel | session_id -> product_id -> product.channel_id; session.angle_id -> product_id; output -> channel raw folder | W | F | M | major |

### `scripts.api_render`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/render/disk-check` | `get_render_disk_check`:61 | global | — | R |  | I | minor |
| POST | `/api/render` | `trigger_render`:304 | channel | product_id -> products.channel == request channel; angle_id -> product.angles (same product); project_name -> project.channel (existing folder) or new project stamped with channel; raw_video_path / clip_list[].source_pat | W | F | CD | blocker |
| GET | `/api/render/status/{job_id}` | `get_render_status`:384 | channel | job_id -> render job.owner/channel (render_jobs.get_job owner_id param exists); job_id -> task registry .channel (fallback) | R |  | D | major |
| GET | `/api/status` | `get_system_status`:413 | global | refresh_ip (query) | R | F | CD | minor |

### `scripts.api_schedule_queue`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/schedule-queue/template` | `get_schedule_template`:915 | channel | template id ('default' / 'week:<date>') -> channel | R |  | D | major |
| PUT | `/api/schedule-queue/template` | `save_schedule_template`:922 | channel | template id -> channel | W |  | D | blocker |
| POST | `/api/schedule-queue/template/copy` | `copy_schedule_template`:932 | channel | source template -> channel; target template -> channel (must be same channel) | RW |  | D | blocker |
| DELETE | `/api/schedule-queue/template/{week_start}` | `reset_schedule_template`:945 | channel | week override -> channel | W |  | D | blocker |
| POST | `/api/schedule-queue/auto-fill/preview` | `preview_auto_fill`:955 | channel | clips[].export_id/video_path -> export_registry.channel; template -> channel; occupied slots -> queue.channel; post_log history -> channel | R | F | D | major |
| POST | `/api/schedule-queue/auto-fill` | `commit_auto_fill`:960 | channel | items[].export_id/video_path -> export_registry.channel; new rows -> request channel | W | F | D | blocker |
| GET | `/api/schedule-queue` | `list_queue`:985 | channel | rows -> queue.channel | R |  | DE | major |
| POST | `/api/schedule-queue` | `create_queue`:1020 | channel | export_id/video_path -> export_registry.channel; product_id/angle_id -> channel; new row -> request channel | W | F | D | blocker |
| PATCH | `/api/schedule-queue/{item_id}` | `patch_queue`:1034 | channel | item_id -> queue.channel | W |  | D | blocker |
| DELETE | `/api/schedule-queue/{item_id}` | `remove_queue`:1059 | channel | item_id -> queue.channel | W |  | D | blocker |
| POST | `/api/schedule-queue/{item_id}/prepare` | `prepare_queue_item`:1073 | channel | item_id -> queue.channel; row.export_id/video_path -> export_registry.channel; pending autopost job -> channel | W | F | D | blocker |

### `scripts.api_shot_lists`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| POST | `/api/products/{product_id}/angles/{angle_id}/shot-list` | `create_shot_list`:61 | channel | product_id -> product.channel_id; angle_id(+batch) -> product_id (checked in builder); task -> channel | RW | F | D | major |
| GET | `/api/products/{product_id}/angles/{angle_id}/shot-list` | `get_shot_list`:99 | channel | product_id -> product.channel_id; angle_id -> product_id | R |  | DM | major |
| GET | `/api/products/{product_id}/shot-list-status` | `get_shot_list_status`:143 | channel | product_id -> product.channel_id | R |  | D | major |
| POST | `/api/products/{product_id}/batch-generate-audio` | `batch_generate_audio`:348 | channel | product_id -> product.channel_id; task -> channel | RW | F | D | major |
| PATCH | `/api/products/{product_id}/angles/{angle_id}/manual-shot-map` | `save_manual_shot_map`:394 | channel | product_id -> product.channel_id; angle_id(+batch) -> product_id (checked in store); shot_map[].video_path -> product/angle linked videos in channel raw folder | RW |  | D | blocker |
| GET | `/api/products/{product_id}/angles/{angle_id}/manual-shot-map` | `get_manual_shot_map`:448 | channel | product_id -> product.channel_id; angle_id -> product_id (checked) | R | F | D | major |
| POST | `/api/products/{product_id}/angles/{source_angle_id}/sync-manual-shot-map` | `sync_manual_shot_map`:649 | channel | product_id -> product.channel_id; source_angle_id -> product_id (checked); target_angle_ids[] -> product_id (implicitly, only matches this product) | RW |  | D | major |
| GET | `/api/products/{product_id}/filming-recipe` | `get_universal_filming_recipe`:749 | channel | product_id -> product.channel_id | R |  | D | minor |

### `scripts.api_tasks`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/tasks/active` | `get_active_tasks`:13 | channel | — | R |  | CD | major |
| GET | `/api/tasks/{task_id}` | `get_task_by_id`:20 | channel | task_id -> task.owner_id/channel_id | R |  | DM | major |
| POST | `/api/tasks/{task_id}/cancel` | `cancel_task`:29 | channel | task_id -> task.owner_id/channel_id; task_id == render job_id -> same channel | W |  | D | blocker |
| DELETE | `/api/tasks/{task_id}` | `delete_task`:51 | channel | task_id -> task.owner_id/channel_id | W |  | D | blocker |
| POST | `/api/tasks/clear-completed` | `clear_completed_tasks`:60 | channel | — | W |  | D | blocker |

### `scripts.api_tiktok_autopost`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| POST | `/api/tiktok-autopost/prepare` | `prepare`:187 | channel | export_id/video_path -> export_registry.channel; cover_path -> channel; queue_id -> queue.channel; pending job -> channel | W | F | DE | blocker |
| POST | `/api/tiktok-autopost/cover` | `update_cover`:266 | channel | pending job -> channel; cover_path -> channel | W | F | E | blocker |
| GET | `/api/tiktok-autopost/pending` | `get_pending`:281 | channel | pending job -> channel; extension request must identify channel/account | RW | F | DE | blocker |
| POST | `/api/tiktok-autopost/clear` | `clear_pending`:292 | channel | pending job -> channel | W |  | E | blocker |

### `scripts.api_tiktok_stats`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| POST | `/api/tiktok-stats/import` | `import_stats`:170 | channel | payload -> source account/channel; matched post -> post_log.channel; candidates -> queue/products of same channel | W |  | E | blocker |
| GET | `/api/tiktok-stats/latest` | `latest_stats`:192 | channel | posts -> post_log.channel | R |  | D | major |
| GET | `/api/tiktok-stats/pending` | `list_pending`:215 | channel | pending rows -> source channel | R |  | D | major |
| GET | `/api/tiktok-stats/clip-candidates` | `list_clip_candidates`:226 | channel | queue rows -> channel; product angles -> channel (if channel-owned) | R |  | D | major |
| POST | `/api/tiktok-stats/attach` | `attach_pending`:232 | channel | pending_id -> channel; post_id -> post_log.channel (must equal pending's channel); candidate -> channel | W |  | D | blocker |
| POST | `/api/tiktok-stats/pending/ignore` | `ignore_pending`:254 | channel | pending_id -> channel | W |  | D | major |
| POST | `/api/tiktok-stats/pending/ignore-all` | `ignore_all_pending`:269 | channel | all pending rows -> request channel only | W |  | D | blocker |
| GET | `/api/tiktok-stats/ignored` | `list_ignored`:280 | channel | ignored rows -> channel | R |  | D | minor |
| POST | `/api/tiktok-stats/ignored/restore` | `restore_ignored`:287 | channel | ignored_id -> channel | W |  | D | minor |
| GET | `/api/tiktok-stats/milestones` | `get_viral_milestones`:302 | channel | posts -> post_log.channel | R |  | D | major |

### `scripts.api_tokens`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/tokens/summary` | `get_token_summary`:13 | global | — | R |  | CD | minor |
| GET | `/api/tokens/history` | `get_token_history`:22 | global | before, task, q | R |  | D | minor |
| GET | `/api/tokens/alerts` | `get_token_alerts`:37 | global | — | R |  | I | minor |
| POST | `/api/tokens/alerts/clear` | `clear_token_alerts`:46 | global | — | W |  | D | minor |
| POST | `/api/tokens/reset` | `reset_token_analytics`:56 | global | — | W |  | D | minor |

### `scripts.api_typesafe_studio`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/typesafe-studio/status` | `get_typesafe_status`:57 | global | — | R |  | D | minor |
| POST | `/api/typesafe-studio/match-broll` | `api_match_broll`:75 | shared | candidate_clips | R |  | I | minor |
| POST | `/api/typesafe-studio/match-sequence` | `api_match_sequence`:87 | shared | candidate_clips | R |  | I | minor |
| POST | `/api/typesafe-studio/match-raw-folder` | `api_match_raw_folder`:104 | shared | raw_folder -> product raw dir of request channel | R | F | D | blocker |
| POST | `/api/typesafe-studio/generate-hooks` | `api_generate_hooks`:118 | shared | product_name | R |  | D | minor |
| POST | `/api/typesafe-studio/evaluate-hook` | `api_evaluate_hook`:131 | shared | hook_text | R |  | I | minor |

### `scripts.api_videos`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/videos` | `list_raw_videos`:313 | channel | product_id -> product.channel; each listed raw file -> owning product (RAW_DIR/<pid>/ folder or product.videos[]) -> channel; unassigned inbox/raw files have no owner | R | F | CD | major |
| POST | `/api/videos/rename` | `rename_video_file`:362 | channel | video_path -> owning product (RAW_DIR/<pid> or product.videos[]) -> channel; product_id -> product.channel; video_path -> export_registry record -> channel | W | F | D | blocker |
| POST | `/api/upload` | `upload_file`:440 | channel | product_id -> product.channel; target_dir (inbox/raw) -> channel-less shared root today | W | F | CD | blocker |
| GET | `/api/raw-vault` | `get_raw_vault`:507 | channel | each product -> product.channel; each raw file -> owning product -> channel | R | F | D | major |
| POST | `/api/raw-vault/reassign` | `reassign_raw_video`:630 | channel | video_path -> owning product -> channel; source_product_id -> product.channel; target_product_id -> product.channel (must equal request channel) | W | F | D | blocker |
| POST | `/api/raw-vault/batch-delete` | `batch_delete_raw_videos`:723 | channel | each video_path -> owning product -> channel | W | F | D | blocker |
| GET | `/api/raw-vault/scene-catalogs` | `get_raw_vault_scene_catalogs`:759 | channel | video_path -> owning product -> channel | R | F | D | major |
| POST | `/api/raw-vault/index-scenes` | `index_raw_vault_scenes`:802 | channel | each video_path -> owning product -> channel; task -> channel | RW | F | D | major |
| GET | `/api/sfx` | `list_sfx`:913 | shared | — | R | F | C | minor |
| GET | `/api/assets/all` | `list_all_assets`:919 | shared | — | R | F | D | minor |
| POST | `/api/assets/rescan` | `rescan_assets`:944 | shared | — | W | F | I | minor |
| POST | `/api/assets/star` | `star_asset`:956 | shared | id -> shared asset (no channel) | W | F | D | minor |
| POST | `/api/assets/upload` | `upload_asset`:973 | shared | asset_type -> fixed 02_Assets subdir (Branding may need channel owner) | W | F | D | minor |
| POST | `/api/open-folder` | `open_folder`:1031 | global | target -> fixed key map (exports,inbox,raw,assets,sfx,music,fonts,stickers,luts,capcut,root) | R | F | CD | minor |
| POST | `/api/reveal-file` | `reveal_file`:1069 | channel | file_path -> owning export (export_registry) or cover -> product.channel | R | F | D | blocker |
| POST | `/api/delete-file` | `delete_file`:1105 | channel | file_path -> owning export/project/raw folder/asset -> channel; export_id -> export.channel; product_id -> product.channel; angle_id -> product_id | W | F | CD | blocker |
| GET | `/api/media/{file_path:path}` | `stream_media`:1308 | channel | file_path under 01_Raw/00_Inbox -> owning product -> channel; 04_Exports -> export_registry -> channel; 03_Projects/<project> -> project -> channel; 05_Covers_Thumbnails -> cover -> export/product -> channel; 02_Assets - | R | F | DE | blocker |

### `scripts.api_voice`

| Method | Path | Handler:line | Scope | Res. params → parents | A | F | Callers | Risk |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/voice/presets` | `get_voice_presets`:66 | shared | — | R | F | D | minor |
| GET | `/api/voice/cache-status` | `get_voice_cache_status`:97 | shared | — | R | F | I | minor |
| POST | `/api/voice/generate-cache` | `trigger_voice_cache_generation`:109 | shared | admin/global action - should not be per-channel | W | F | I | minor |
| POST | `/api/voice/preview` | `preview_voice`:126 | shared | text, voice_gender/preset, ad_tone, speed | W | F | CD | major |
| POST | `/api/script/generate` | `generate_script`:177 | shared | product_name, key_features, pain_point, price_deal, template_key | R |  | C | minor |
| POST | `/api/script/ai-generate` | `generate_ai_scripts`:190 | shared | quota/budget -> optionally per-channel budget | R |  | CD | minor |
| POST | `/api/sub-srt/transcribe` | `run_sub_srt_transcription`:366 | channel | media_path -> owning project/raw folder .channel | RW | F | D | blocker |

## 4. Routes ที่ไม่สอดคล้องกันอยู่แล้ว / เสี่ยง (file:line)

ทุกข้อด้านล่างมาจากการอ่าน handler (ยกเว้นที่ระบุ) — ปัจจุบัน **ไม่มี route ใดตรวจ channel/ownership เลย** guard ที่มีคือ confinement ระดับโฟลเดอร์เท่านั้น

### 4.1 Top 10 risk routes (blocker)

| # | Route | ปัญหา | หลักฐาน |
|---|---|---|---|
| 1 | `POST /api/tiktok-autopost/prepare`, `GET /pending`, `POST /clear`, `POST /cover` | job เดียวใน memory (`_pending`) ไม่มี channel/account/job_id; prepare เขียนทับ, clear/cover ทำกับ job ใดก็ได้ → โพสต์ผิดบัญชี | `scripts/api_tiktok_autopost.py:235-249`, `:274-277`, `:286-289`, `:296-297` |
| 2 | `GET /api/media/{file_path:path}` | สตรีมไฟล์ทุกช่องจาก 00_Inbox…06_Archive + CapCut drafts; เป็น GET ที่ `<video>/<img>` ใช้ จึงแนบ `X-OmniCut-Channel` ไม่ได้ → ต้องออกแบบ signed URL/channel prefix; `_allowed_media_path` ถูก reuse โดย audio/silences และ proxy/for-clip | `scripts/api_videos.py:1275-1278`, `:1293`, `:1308-1334`; `scripts/api_audio_beats.py:21`; `scripts/api_proxy.py:26` |
| 3 | `POST /api/delete-file` | ลบด้วย path จาก client ใน 6 roots รวม 02_Assets; companion `.srt/.vtt/.webp` ถูก unlink ถาวร; rollback อิง product_id/angle_id ที่ไม่ตรวจ | `scripts/api_videos.py:1132-1139`, `:1212-1217`, `:1249` |
| 4 | `POST /api/render` | `raw_video_path`/`human_voice_audio` รับ absolute path; fallback ค้นชื่อไฟล์ทั่ว 01_Raw/00_Inbox; `project_name` ไม่ sanitize (มี `../`) → เขียน project/export/registry ทับช่องอื่น; job/task ไม่มี owner | `scripts/api_render.py:77-87`, `:154`, `:226`, `:234`, `:367-371`; `scripts/stages/source_resolution.py:25-40`, `:100-101`; `scripts/api_schemas.py:27` |
| 5 | `POST /api/hyperframes/render` | `composition_id`, `output_filename` ไม่ validate → เขียน/ทับ .mp4 นอก Ready_to_post; register export ไม่มี channel และเดา product จากชื่อ composition | `scripts/api_hyperframes.py:332-349`, `:358`, `:379-393` |
| 6 | `POST /api/exports/mark-posted` | fallback จับ queue row ด้วย `video_key`/ชื่อไฟล์ (ข้ามช่อง) แล้ว set posted; Posted เป็นโฟลเดอร์แบน `POSTED_DIR / src.name` ชื่อชน/ลบไฟล์ซ้ำ | `scripts/api_exports.py:705-714`, `:840`, `:919`; `scripts/api_schedule_queue.py:308` |
| 7 | `PUT/POST copy/DELETE /api/schedule-queue/template*`, `PATCH/DELETE /api/schedule-queue/{item_id}`, `POST /{item_id}/prepare` | template id global (`default`/`week:X`) ทับทุกช่อง; item หาโดย id ไม่มี owner; occupied/uniqueness คิดรวมทุกช่อง | `scripts/api_schedule_queue.py:252-273`, `:927`, `:937-951`, `:967-971`, `:1024-1028`, `:1037`, `:1062-1069`, `:1091-1097` |
| 8 | `POST /api/tiktok-stats/import`, `/attach`, `/pending/ignore-all` | ไม่มี account; `replace_from_sync` ล้าง pending ทั้งตาราง; fuzzy match title ข้ามทุกโพสต์; attach ทับ metrics ของ post ใดก็ได้ | `scripts/api_tiktok_stats.py:41-43`, `:179`; `scripts/tiktok_pending.py:133`, `:186-191`; `scripts/post_log.py:253`, `:341`, `:371-383`, `:452-498` |
| 9 | `PATCH /api/products/{product_id}/angles/{angle_id}` + `scrape-and-plan(-async)` + `refresh-source` | set `video_url` วนรีเซ็ต angle ของทุก product ที่ใช้ URL เดียวกัน; URL dedup ข้าม product ทับ angles/ข้อมูล | `scripts/product_store.py:575-582`, `:676-694`, `:391-416`; `scripts/api_products.py:126-129`, `:449-472`, `:932`, `:1038` |
| 10 | `POST /api/covers/ai-generate-image` (+ `render-pro`, `generate`) | fallback `Path(src)` ข้าม `_resolve_media` → ไฟล์ใดบนดิสก์ถูกส่งออกเป็น reference ให้ CLI ภายนอก; SSRF จาก URL; ผลลัพธ์เลือก "jpg ล่าสุด" ในโฟลเดอร์กลาง; cover เขียนทับ `<stem>_cover.jpg` แบน | `scripts/api_covers.py:1305-1340`, `:1365-1383`, `:1031-1048`, `:207`, `:83-93` |

### 4.2 Blocker/major อื่นที่ต้องเก็บใน P2–P6

- **`PATCH /api/products/{product_id}` แทนที่ `angles` ทั้งชุดจาก client** (รวม posted, `selected_videos` ที่ batch render ใช้โดยไม่ confine) — `scripts/product_store.py:499`, `scripts/api_phase1.py:351`, `scripts/batch_render.py:455-457`
- **Project by name** — `DELETE /api/projects/{name}` `shutil.rmtree` (`scripts/project_manifest.py:410`) และ `scope=product` ลบ product ด้วย (`scripts/api_phase1.py:680`); archive ย้ายเข้า `06_Archive/Projects` กลาง (`project_manifest.py:452`); snapshot restore / `cues` / `clips` / `state` เขียนทับ manifest ใดก็ได้; `/state` คัดลอกทุก key ของ `req.style` เข้า manifest+render_params (`scripts/api_phase1.py:992-996`); clip_list path ไม่ตรวจแล้ว reroll render ต่อ (`:836-844`, `:983-985`, `:1128-1129`); sticker fallback `BASE_DIR / badge` (`:1406-1407`)
- **Batch render** — `project_name`/`angle_project_names` ชน project ช่องอื่น, fallback mp4 แรกใน RAW/INBOX — `scripts/batch_render.py:442-445`, `:468-488`; cancel by id `:339`
- **Tasks** — cancel/delete by id และ `clear-completed` ล้างทุกช่อง `scripts/api_tasks.py:43-47`, `:54`, `:63` ทั้งที่ `task_manager.py:421-429` รองรับ `owner_id`; reroll สร้าง task ไม่มี owner `scripts/api_phase1.py:1415`
- **Asset dedup clean** ลบ raw ของช่องหนึ่งเพราะอีกช่องมีสำเนา — `scripts/asset_dedup.py:223-231`, `:267-279`
- **Post metrics 4 entry points คนละ error code** — `scripts/api_phase1.py:221` (400) vs `scripts/api_posts.py:49` (404); เขียนทับด้วย post_id ใดก็ได้ `scripts/post_log.py:283-304`
- **`GET /api/products` write-on-read** — `reconcile_existing_projects()` scan 03_Projects/04_Exports ทั้งหมด match by name `scripts/product_store.py:2019`; cover lookup by stem `scripts/api_phase1.py:276-290`
- **`GET /api/editor/filmstrip`** เสิร์ฟเฟรมของไฟล์ใดใต้ BASE_DIR — `scripts/api_editor.py:56-67`
- **Raw footage path routes** — `POST /api/videos/rename` (match basename ข้าม product เมื่อไม่ส่ง product_id), `/api/raw-vault/reassign`, `/api/raw-vault/batch-delete`, `POST /api/upload` (เขียนเข้า `01_Raw/<product_id>` ใดก็ได้): `scripts/api_videos.py:370-426`, `:452`, `:497`, `:637-661`, `:731-746`; confinement คือ `_resolve_allowed_video_path` `:53-105` และ `_safe_product_dir` `:126-142`
- **Product video paths ไม่ confine** — `POST /api/products/{id}/videos` `scripts/api_products.py:495-507`; scene-catalogs/index-scenes `:666-667`, `:740-745`; manual-shot-map `scripts/api_shot_lists.py:420-431`; `DELETE /api/products/{id}/videos` ย้ายไฟล์ก่อนตรวจ `scripts/api_products.py:518-529`
- **remove_angle lost update + ลบ product เมื่อ angle สุดท้ายหมด** — `scripts/product_store.py:1357`, `:1390-1394`; `add_product_angle` รับ object จาก client เกือบทั้งก้อน `:833-848`
- **Producer notes ไม่มี owner และ replace ทั้งไฟล์** — `scripts/api_producer.py:244-254`, `:270-276`, `:285`, `:311-314`; 409 คืน notes ทั้งหมด `:245-251`, `:297-303`
- **Purge cache ทุกช่องไม่มี confirmation** — `scripts/storage_cleaner.py:248-253`, `:275`, `:339` (via `/api/analytics/storage/purge-*`)
- **`POST /api/sub-srt/transcribe` เขียน .srt ข้าง media ใดก็ได้ในโปรเจกต์ (รวม 01_Raw/02_Assets)** — `scripts/api_voice.py:380-397`
- **Background isolation** — `project_name` join path ไม่ตรวจ `scripts/api_background_isolation.py:323`; allowed roots มี `''` = ทั้ง workspace `:54`; dedup คืน task ของคนอื่น `:472-478`
- **Task/job ไม่มี channel** — `TaskManager.create_task` ไม่บันทึก channel; `GET /api/render/status/{job_id}` ไม่ส่ง `owner_id` (`scripts/api_render.py:387`, `:397`) ทั้งที่ `render_jobs.py:106-135` รองรับ; `POST /api/mobile-studio/cancel/{task_id}` ยกเลิก task ใดก็ได้ `scripts/api_mobile_studio.py:154-156`
- **HyperFrames create-clip** — `vo_path` absolute ถูก copy, fallback glob `03_Projects/*{PRODUCT}*` เลือก VO ช่องอื่น, ไม่ส่ง `--channel` → ทุกคลิป `data-channel="main"`: `scripts/api_hyperframes.py:271-307`
- **Gadget Media source paths** — probe confine แค่ BASE_DIR `scripts/api_gadget_media_projects.py:117-120`; PATCH source_assets/PUT timeline ไม่ตรวจ `:52`, `scripts/gadget_media_timeline_adapter.py:89-108`; slot `product_project_id` ตั้งค่าอะไรก็ได้ `scripts/gadget_media_campaign.py:431`
- **TypeSafe match-raw-folder list โฟลเดอร์ใดก็ได้** — `scripts/typesafe_bridge.py:426-457`
- **Mobile upload/assemble** — `scripts/mobile_quick_studio.py:95-101`, `:314-326`, quick-add URL dedup ข้ามทุก product `:374-377`
- **`POST /api/exports/link-angle` ลงทะเบียน path ใดก็ได้ใต้ BASE_DIR เป็น export** — `scripts/api_exports.py:600-607`; `scripts/export_registry.py:46-53`; `GET /api/exports` เขียน registry (`ensure_many`) `scripts/api_exports.py:441`
- **Shared output files** — `/api/voice/preview` และ mobile preview-voice เขียน `test_voice.wav` ไฟล์เดียว `scripts/api_voice.py:129`

### 4.3 ความไม่สอดคล้องที่ไม่ใช่เรื่องช่องแต่เจอระหว่างทาง

- `POST /api/hooks/apply-angle` และ `/api/hooks/apply-project` น่าจะ 500 ทุกครั้ง (ส่ง dict แบบ positional) — `scripts/api_hooks.py:114`, `:149`, `:130-135` (ยังไม่ได้รันยืนยัน)
- `frontend/src/api.js:244` เรียก `POST /api/upload-multiple` ที่ไม่มีใน backend (dead code)
- `pov_chat` ที่ไม่มี VO fail เสมอ เพราะ `kit/new_clip.py:51` บังคับ `--vo`
- `scripts/interactive_sam2_daemon.py:134` `/set_frame` รับ path ใดก็ได้ (internal, loopback)
- `resolve-tiktok-id` เปิด URL ใดก็ได้ฝั่ง server `scripts/api_products.py:45-51`; covers ai-generate-image fetch URL `scripts/api_covers.py:1365-1373` (SSRF)

## 5. Callers

ที่มา: map `api.js` export → route แล้ว grep การใช้ใน `frontend/src` (ไม่รวม `*.test.*`); mobile = `MobileQuickStudio.jsx`, `MobileQuickPostPage.jsx`, `MobileFilmingPage.jsx`; extension = `tiktok_autopost_extension/{background,sidepanel,popup}.js` (ยิงตรง `http://127.0.0.1:8000`, ไม่ผ่าน Vite proxy); cli = `tools/system_health_check.py:281-303` (ตรวจแค่ว่า route มีอยู่ ไม่ได้ยิง HTTP); HyperFrames Studio ไม่เรียก OmniCut API

- **Extension (9 routes, ต้องรองรับ scope ใน P5):** `GET /api/tiktok-autopost/pending` (background.js:44, popup.js:37), `POST /clear` (:81), `POST /cover` (:92), `POST /api/exports/mark-posted` (background.js:63, sidepanel.js:871), `GET /api/exports` (sidepanel.js:384), `GET /api/schedule-queue` (sidepanel.js:411), `POST /api/tiktok-autopost/prepare` (sidepanel.js:542), `POST /api/tiktok-stats/import` (sidepanel.js:1008), `GET /api/media/...` (sidepanel.js:137, :426-427)
- **Mobile (QR/quick):** `/api/mobile-studio/*` ทั้ง 9, `GET /api/recording-sessions/{id}`, `POST .../segments`, `POST .../finalize`, `GET /api/tasks/{task_id}`, `GET .../shot-list`, `GET /api/products`, `POST /api/exports/mark-posted`, `/api/media/...`
- รายชื่อ component ต่อ route อยู่ใน JSON ฟิลด์ `caller_files`; route ที่ callers = `internal` คือไม่พบผู้เรียกใน frontend/extension (อาจเรียกจาก test หรือเลิกใช้แล้ว เช่น `/api/post-log*`, `/api/projects/{name}/snapshots*`, `/api/product/fetch`)

## 6. Test coverage ที่ต้องรักษาให้เขียว

ตารางในข้อ 2 แสดงไฟล์ test ที่ยิง URL ของแต่ละโมดูล (จับด้วย string match ใน `tests/`) ไฟล์ที่เทสระดับ handler โดยตรงเพิ่มเติม: `test_task_manager.py` (tasks), `test_api_batch_audio.py` (shot_lists batch audio), `test_security_path_containment.py` (editor/videos/covers), `test_delete_file_guard.py`, `test_security_boundary_agent.py`, `test_security_product_id_path_write.py`, `test_api_auth.py`, `test_backend_api_contracts.py`, `test_gemini_voice_defaults.py` (batch_render)

Route ที่**ไม่พบ test ยิง URL เลย (36)**: `GET /api/editor/media-info`, `GET /api/tokens/alerts`, `POST /api/tokens/alerts/clear`, `GET /api/raw-vault/scene-catalogs`, `POST /api/raw-vault/index-scenes`, `POST /api/assets/star`, `POST /api/reveal-file`, `GET /api/covers/badges`, `POST /api/covers/{highlights,raw-sources,generate-hooks,generate,grab-frame}`, `POST /api/schedule-queue/{item_id}/prepare`, `POST /api/products/resolve-tiktok-id`, `GET /api/products/{id}/scene-catalogs`, `POST /api/products/{id}/index-scenes`, `GET /api/exports/media-info`, shot-list POST/GET, `GET /api/products/{id}/shot-list-status`, `POST /api/products/{id}/batch-generate-audio`, `/api/recording-sessions` ทั้ง 4 write routes, `POST /api/producer/upload-ref-media`, `GET /api/gadget-media/campaigns/{id}`, gadget-media project `sources/probe`, `timeline` GET/PUT, `quality/validate`, `renders`, `renders/{artifact_id}/approve`, `campaigns/{id}/slots/{slot_id}/project`, `POST /api/background-isolation/interactive-segment` — เฟสถัดไปต้องเพิ่มเทส scope ก่อนแก้

## 7. สิ่งที่ยังจัดประเภทไม่ได้ / ต้องตัดสินใจ

1. Backup download/list/verify/delete เป็น global แต่ zip มี `store.db` + projects ของทุกช่อง (`scripts/api_backup.py:42-46`) — ต้องมี admin gate ชัดเจน; `/api/editor/overlay/layout` ยังไม่ยืนยันว่ารับ font path หรือไม่
2. Producer notes/ref media: ต่อช่องหรือ shared playbook (แผน §4.2 บอกต้องมี `scope=shared` ชัดเจน) — จัดเป็น channel ชั่วคราว
3. Cutout cache, proxy cache, asset star flag, `02_Assets/Branding` upload: shared หรือแยกช่อง
4. Recording session token ใช้จาก QR โดยไม่มี header — ควร derive channel จาก `session.product_id`
5. `/api/media/*` และ URL ที่ `<video>/<img>` ใช้ ต้องเลือกกลไก scope (signed URL / path prefix / cookie) เพราะแนบ header ไม่ได้
6. Extension ยังไม่ส่ง header ใด ๆ นอกจาก `X-API-Key` (`tiktok_autopost_extension/auth_key.js:44-51`)
