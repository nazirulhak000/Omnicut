# System Health Audit — OmniCut Studio
**Date:** 2026-09-09 · **Branch:** phase1-affiliate-studio @ 4929d60
**Scope:** Database / Data Layer · Infrastructure · System Analysis
**Method:** 4 parallel read-only code audits + live runtime probing of the running dev stack. No code was modified.

Verification legend: **[V]** = personally verified by reading the code or probing the running system · **[A]** = reported by an audit agent, code cited but not independently re-checked.

---

## 1. Overall status

| Area | Status | One-line reason |
|---|---|---|
| **Database / Data Layer** | 🔴 **At risk** | SQLite engine config is excellent, but the JSON-mirror layer can destroy rows on a `git checkout`, and several stores do read-modify-write outside their transaction. |
| **Infrastructure** | 🔴 **At risk** | API runs with **no authentication** bound to `0.0.0.0`, and one upload endpoint accepts an unsanitized filename — together that is unauthenticated arbitrary file write. |
| **System / Data Flow** | 🟡 **Watch** | Save paths swallow errors silently, the serialize/deserialize pair is asymmetric (confirmed live data loss), and the sticker legacy-mirror bug class is still open on the render side. |

### What is already good (verified — do not re-audit)
- **SQLite is properly configured** [V] — `journal_mode=wal`, `busy_timeout=5000`, `synchronous=FULL`, `PRAGMA integrity_check` → **ok**, and `idx_*_updated_at` exists on all 5 tables. No corruption.
- **No command injection anywhere** [A] — zero `shell=True` / `os.system` in the repo; all subprocess calls use argv lists. Caption text is ASS-escaped (`subtitle_engine.py:716`).
- **Secrets are clean** [A] — `.env` is gitignored (`.gitignore:9`) and was never committed; no hardcoded credentials in `scripts/`, `frontend/src/`, `tools/`, or the extension.
- **CORS is not a wildcard** — allowlisted to `localhost/127.0.0.1:5173` (`api_server.py:87-91`).
- **`project.json` writes are atomic** — tmp + `os.replace`, with one `.bak` generation and automatic recovery on parse failure (`project_manifest.py:98-109, 170-182`).
- **Auth code itself is well built** [V] — `secrets.compare_digest` constant-time compare, CORS-aware middleware ordering, documented (`auth.py:68-75`, `api_server.py:100-129`). It is simply **not switched on**.
- **The `useEffect` "changed size between renders" warning is NOT a real bug** [A] — it is a Vite HMR artifact at `SequencePlayer.jsx:3292`: commit 4929d60 grew that effect's dep array from 7 to 8 slots (`segmentsByClipId`, a `Map`, was added), and the hot-replaced module is compared against the stale one. A cold reload logs zero warnings; an AST scan of all 115 source files found no conditional or spread dep array anywhere. **Fix = hard-reload after editing that file. No code change needed.**
- **Refactor 4929d60 left no half-migration** [A] — `TimelineIntervalItem`, `TrackLabel`, `OverlayInspectorHeader`, `OverlayScaleControl`, `OverlayTimingControls` are each used by all intended call sites with no inline twin left behind.

---

## 2. Findings — sorted by severity

### 🔴 CRITICAL

| # | Location | Problem | Concrete failure scenario | Minimal fix |
|---|---|---|---|---|
| C1 | `.env` (missing `OMNICUT_API_KEY`) + `api_server.py:111,163` **[V]** | API is fully unauthenticated **and** hardcoded to `host="0.0.0.0"`. `is_auth_enforced()` returns false with no key set, so the gate passes every request through. | Probed live: `GET /api/products` → 200, `GET /api/projects` → 200, `GET /docs` → 200, no key. Anyone on the same Wi-Fi opens `http://<your-ip>:8000/docs` and drives everything — delete files, start renders, burn Gemini credits, queue TikTok posts. Not internet-reachable unless the router forwards port 8000. | Generate a key (`python -c "import secrets;print(secrets.token_urlsafe(32))"`), set `OMNICUT_API_KEY` in `.env` **and** `VITE_API_KEY` in `frontend/.env`. Zero code change. |
| C2 | `api_videos.py:583` **[V]** | `save_path = dest_dir / file.filename` — raw `UploadFile.filename`, no `.name`, no extension allowlist. | `POST /api/assets/upload` with `filename="../../scripts/config.py"` writes into `scripts/` → that code runs on the next backend restart = **RCE**. An absolute `C:/...` filename makes pathlib discard `dest_dir` entirely. Unauthenticated because of C1. The sibling endpoint at `:231` already does this correctly. | Copy `:231`'s pattern: `Path(file.filename or "").name` + suffix allowlist. |
| C3 | `video_editor.py:873,897-906` **[V]** | `if stickers and isinstance(stickers, list): … elif sticker_path …` — `[]` is falsy, so an empty sticker list falls through to the legacy `sticker_path` branch. `render_params.sticker_path` has **no clear path**: `serializeStyle` never emits it, so `PATCH /state` can neither write nor clear it. | Delete every sticker in the editor, then render → the deleted sticker is **burned into the exported MP4**. This is the exact bug class just fixed in the editor UI, still open on the render side. Currently **latent**: all 7 projects on disk read `sticker_path: ''`. | Change `:873` to `if isinstance(stickers, list):` — matches the already-correct guard at `overlay_model.py:408`. |
| C4 | `api_phase1.py:749-819` **[A]** | Manifest read-modify-write with `load()` **outside** `_SAVE_LOCK`; `render_params` is rebuilt wholesale from the stale read at `:754`. | Autosave PATCH reads the manifest → the pipeline writes `render_params` (`video_assembly_stage.py:222`) → the PATCH commits and reverts every `render_params` key the render just wrote. Because `pipeline_context.py:119-123` reads `render_params` first, the next reroll uses pre-render values. | Add `ProjectManifest.save_merge(name, mutator_fn)` that does the read + merge inside `_SAVE_LOCK`. |
| C5 | `EditorShell.jsx:1235` **[A]** | `await updateProjectState(...).catch(() => {})` immediately before `startReroll`, which does not resend cues/overlays. | Edit a caption → click เรนเดอร์ → the PATCH fails → backend re-reads the old manifest → the MP4 ships with the **previous** captions while the UI reports success. | Await it properly and abort the render if it rejects. |
| C6 | `api_videos.py:743-746`, `api_render.py:238-241` **[V]** | `except HTTPException: raise` / `except Exception: pass` around the "already posted → refuse" guard. The guard's own rejection survives, but any *other* error inside the try (ProductStore read, path resolve) skips the guard entirely. | A transient store read error makes the guard **fail open** → an already-posted export gets deleted or overwritten, and `{"success": true}` is returned. | Fail closed: on an unexpected exception, refuse rather than continue. |
| C7 | `api_videos.py:192-207,497-506` **[A]** | `ProductStore._load()` … `_save()` outside any transaction, and `_save` does `DELETE FROM products` + full reinsert (`db.py:275-280`). | Video rename / batch-delete concurrent with a finishing render's `update_angle_status` → the **entire products table** reverts to the stale list read at `:192`. Not one lost field — all of them. | Wrap both in `with ProductStore._mutate() as products:`. |
| C8 | `api_schedule_queue.py:662-684` → `api_tiktok_autopost.py:194,199` **[A]** | `prepare()` is called inside an open `BEGIN IMMEDIATE`, and `ExportRegistry` shares the same per-thread connection (`db.py:124-143`) → `sqlite3.OperationalError: cannot start a transaction within a transaction`, which `_retry_on_locked` (`db.py:103`) does not catch. | `POST /schedule-queue/{id}/prepare` on an unregistered export returns 500 and rolls back; the item is stuck in `planned` forever. | Resolve/ensure the export record *before* opening the queue transaction — the pattern already used at `product_store.py:404-417`. |

### 🟠 HIGH

| # | Location | Problem | Concrete failure scenario | Minimal fix |
|---|---|---|---|---|
| H1 | `.gitignore:71` + `db.py:202-253` **[V]** | `post_log.json`, `schedule_queue.json`, `schedule_templates.json` are **git-tracked** while `store.db` is **gitignored**. `_sync_from_json_if_newer` does `DELETE FROM <table>` + full re-import whenever the JSON mtime is newer than the recorded import. | Any `git checkout` / branch switch / `stash pop` that touches those files bumps the mtime → the next read **deletes every row** and re-imports the committed version. Quantified: `post_log.json` holds 163 records at HEAD but 94 records at commit `e7d19d1` (2026-09-04) — checking out that commit destroys **69 post records**. In sync today, so not yet realized. | Gitignore the three JSON mirrors, exactly as `products.json` and `export_registry.json` already are. |
| H2 | `editorProjectState.js:190,195` **[V]** | `editorStateToSavePayload` writes `micro_cues: cues` — literally the same array — and does not even accept `microCuesList` as a parameter, so the loaded value cannot be preserved. | Open a project and idle 500 ms → autosave flattens `micro_cues` into the coarse `cues` list. **Already happened: all 7 projects on disk have `cues` byte-identical to `micro_cues`.** Downstream, `audio_mix_stage.py:51` (SFX placement) and `shot_matching_stage.py:109` (vision cache key) then work off the wrong list → SFX move and the paid Gemini vision cache misses. | Accept and send `microCuesList`, or omit the key so the backend keeps its own. |
| H3 | `EditorShell.jsx:903-916` **[V]** | `handleUpdateSticker` patches `stickers[0]` when the target id is missing, and **fabricates a `sticker-1`** out of `prev.style.stickerBadge` when the list is empty. | Delete the last sticker, then any queued inspector/drag commit re-creates a sticker — the same silent-undo shape as the bug just fixed, through a different door. (Partly defanged by the recent fix, since `stickerBadge` is now cleared — but it still creates an empty phantom row.) | `if (!targetId || !currentList.some((s) => s.id === targetId)) return prev;` |
| H4 | `useProjectAutosave.js:103,211-216,232` **[A]** | Autosave, the `pagehide` keepalive, and the unmount flush all `.catch(() => {})`. A failed job is re-queued (`projectSaveQueue.js:37-40`) but nothing ever re-flushes it. | One transient 500 → the pill shows "มีการแก้ไข…", indistinguishable from a normal debounce. The user closes the tab and loses everything since the last good save. | Surface the error and schedule a retry flush. |
| H5 | `EditorHeader.jsx:185`, `EditorShell.jsx:1094` **[A]** | Manual save / Ctrl+S ignore the returned promise; there is no global `unhandledrejection` handler. | An explicit save fails with **no signal at all**. | `saveNow().catch(showToast)`. |
| H6 | `project_manifest.py:173-177` **[A]** | The `.bak` copy is wrapped in `except Exception: pass`. | Disk full → the backup is silently skipped, then the primary write tears → `load()`'s `.bak` recovery has nothing to recover from. Whole project lost. | Log it, and refuse to save if the backup failed. |
| H7 | `shot_matching_stage.py:419-441` **[A]** | A single `except` wraps the entire shot-planning block, falling back to one static clip. | Any Gemini or beat-analysis error produces a 25-second video of one frozen shot, reported as a successful render. | Narrow the except; mark the manifest degraded. |
| H8 | `product_store.py:1046,1150` **[A]** | `_reconcile_into` calls `ExportRegistry.latest_for_angle` / `find_by_path` inside the open products transaction — the nesting `db.py:76-84` documents as unfixed. | Any product listing after `export_registry.json` is touched out-of-band raises "cannot start a transaction within a transaction" → `GET /api/phase1/products` 500s. No test covers it (`tests/test_reconcile_transaction.py` has 4 tests, none nested). | Snapshot `ExportRegistry.all()` once before `_mutate()` and pass it in. |
| H9 | `db.py:219-253` **[A]** | The process-wide `_setup_lock`, shared by all 5 tables, is held across a blocking `BEGIN IMMEDIATE`; every store op takes it via `_conn()` (`:198`). | One thread busy-waiting 5 s on the write lock during a mirror re-import stalls **every** request touching any store — the remaining unfixed half of incident ac3a3ea, now 5 s instead of 100 s. | Do the JSON read + mtime check under the lock, then release before the import transaction. |
| H10 | `asset_registry.py:224-237` **[A]** | `_cache_is_fresh()` `rglob`+`stat`s ~1,950 files on **every** `load()`, and `sfx()/bgm()/fonts()/stickers()/luts()/effects()` each call `load()` separately. | ~11,700 stat syscalls per request that reads several categories; `resolve_sfx_path()` (`:282`) re-walks per SFX cue during a render. | Memoize the freshness check for a few seconds, or compare only the newest directory mtime. |
| H11 | `asset_registry.py:218-220,325-327` **[A]** | `rebuild()` and `set_starred()` are unlocked read-modify-write onto a **fixed** `.json.tmp` path. | Two threads both finding the cache stale write the same tmp file → corrupt `asset_registry.json`, or a Windows `PermissionError` on `replace()`. Two concurrent star toggles lose one. | Module lock + per-thread tmp name (as `db.py:329` already does). |
| H12 | `api_phase1.py:356,377` **[A]** | `POST /api/product/fetch` checks only the `http(s)://` prefix, then `urlopen(url)` and reflects 400 KB of the body back as `title`/`raw_text`. | SSRF with response reflection against `127.0.0.1`, `192.168.x.x`, `169.254.169.254`. `product_scraper.py:150-185` already has a full IP-allowlist + redirect-revalidating guard that this endpoint never calls. | Call `_validate_public_http_url(url, require_allowed_domain=False)` before `:377` and pass `_SafeRedirectHandler`. |
| H13 | `video_editor.py:391` **[A]** | The `ffprobe` call in `get_media_info` is the **only** subprocess with no `timeout=`. | A stalled source (unplugged USB, network share, malformed container) blocks forever **while holding `_RENDER_SLOT`** → all future renders permanently wedged. Also reachable from sync handlers, pinning request threads. | `timeout=60`. |
| H14 | `api_server.py:160` **[V]** | `FASTAPI_RELOAD` defaults to **`"true"`**; only `start_app.bat:20` turns it off. Compounded by `task_manager.py:498`, whose `initialize()` sweeps queued/processing → `failed` at import. | Start the server any other way and WatchFiles reloads on files the render itself writes → the live render is killed mid-encode, marked failed, and the angle demoted to `scripted`. | Flip the default to `"false"`. |

### 🟡 MEDIUM / 🟢 LOW (abridged — full detail in the agent transcripts)

| Location | Sev | Problem | Fix |
|---|---|---|---|
| `video_editor.py:1172` | MED | Blocking `proc.stdout.readline()` with no wall-clock deadline; the cancel check only runs between lines → a hung ffmpeg is both untimed-out and uncancellable, holding the render slot. | Deadline in the loop, then `kill()`. |
| `render_jobs.py:133` | MED | Bare `_RENDER_SLOT.acquire()`, no timeout or queue cap; every waiter pins an anyio thread. Since all handlers are sync `def`, enough queued renders starve the threadpool and the whole API stops responding — same class as ac3a3ea. | Refuse with 429 past N queued (`is_busy()` already exists). |
| `api_voice.py:297-308` | MED | `req.media_path` gets no containment check; writes `<stem>-sub.srt/.vtt` into any directory and returns the content. | Reuse the `_is_contained` guard from `api_videos.py:37`. |
| `api_render.py:53-57`, `api_phase1.py:1111-1115` | MED | `STICKERS_DIR / req.sticker_badge` with no `.name` or containment → arbitrary image read, composited into the video. | `.name`-strip or containment-check. |
| `project_manifest.py:69` | MED | `dir_for()` is unguarded; on Windows `%5C` survives the `[^/]+` route regex → `PATCH /api/projects/..%5C..%5Cx/state` traverses out of `03_Projects`. Scope-limited to overwriting an existing `project.json`. `delete()` **is** guarded. | Add the containment check to `dir_for`. |
| `api_covers.py:734-736` | MED | `export_filename` reaches `COVERS_DIR / ...` with only substring stripping → arbitrary JPEG write. Nuisance, not RCE. | `.name`-strip. |
| `task_manager.py:57,231,458` | MED | `_tasks` has no cap, TTL, or auto-prune; `_save_to_disk_locked` rewrites the whole dict every 2 s and `get_active_tasks` sorts it per poll. Write errors are swallowed at `:240`. | Prune completed tasks older than ~7 days in `initialize()`. |
| `video_editor.py:1211-1238` | MED | No `atexit`, signal handler, or job object; the `finally` only covers in-process exceptions. A hard kill leaves ffmpeg holding a write handle → next render hits `WinError 32` or a corrupt file. | `CREATE_NEW_PROCESS_GROUP` + an `atexit` PID sweep. |
| `requirements.txt:3-7` | MED | Dependencies installed into **global** site-packages, no venv — shared with unrelated projects. | `python -m venv .venv`; point `start_app.bat` at it. **Highest value per minute in this list.** |
| `api_videos.py:585` | MED | `content = await file.read()` loads the whole upload into RAM (`:248` streams in 1 MB chunks). A 2 GB upload = 2 GB RSS mid-render. | Copy the chunked loop from `:247-249`. |
| `db.py:256-264,275-280` | MED | Every read is `SELECT data FROM <table>` — full scan + JSON-parse of all rows; `idx_*_updated_at` is never queried; `ExportRegistry.get()` linear-scans in Python despite `id` being the PK. | Add `DocumentTable.get(id)` doing `SELECT data WHERE id=?`. |
| `api_schedule_queue.py:595-603` | MED | N+1: `find_by_path` per queue row, each calling `Path.resolve()` per registry row → ~1,200 syscalls per `GET /schedule-queue`. | Load the registry once, build a path→id dict. |
| `overlayBoxGeometry.js:80-81` | MED | `|| (list)[0]` fallback on selection miss → dragging after a delete silently moves the wrong sticker. | Return `null` when the id isn't found. |
| `editorProjectState.js:50-57,151` | MED | The loader drops cue `scale/x/y/position` (both are consumed downstream); `serializeTransitions` does `clipList.slice(1)`, discarding clip 0's `transition_in`. | Spread the cue; serialize clip 0. |
| `EditorShell.jsx:515` vs `:526` | MED | `trackMix` lives in `useState`, outside the undo history and outside `reset()`. | Move it into the history object. |
| `hook_styles.py:196-218`, `token_tracker.py:136-150`, `task_manager.py:239` | MED | More unlocked read-modify-write on fixed tmp paths; `token_tracker`'s lock is process-local so a second process loses events and `quota.check_budget` under-counts; `task_manager`'s fallback after 3 failed renames is a direct truncating write. | Locks + unique tmp names; drop the truncating fallback. |
| `api_exports.py:703-708` | MED | Mark-posted spans file move → queue → registry → product store with no cross-store atomicity. Crash mid-way: queue says `posted`, angle does not. | Reorder, or record a completion marker. |
| `.env:2` | LOW | `GEMINI_API_KEY_OLD` is a live-looking key with **no reader** in the codebase. Not committed. | Revoke in AI Studio, delete the line. |
| no `logging.basicConfig` anywhere | LOW | 236 bare `print()` across 44 files, zero handler setup, no log file. There is no `/health` (`GET /health` → 404 **[V]**), and `/api/status` hardcodes `"ffmpeg_ready": True` while doing a full recursive `rglob` of `01_Raw`+`00_Inbox` per call. | One `basicConfig(filename=...)`; make `ffmpeg_ready` a cached probe. |
| `render_jobs.py:92` | LOW | Per-job `logs` list is uncapped (~2.5 entries/s) and the status endpoint returns the whole job dict → O(n²) polling traffic. `task_manager.py:333` caps at 50; do the same. | `logs[-50:]` on append. |
| 6 cache writers (`gemini_vision_matcher.py:88`, `motion_analyzer.py:54`, `script_tone_analyzer.py:59`, `beat_sync.py:36`, `generate_voice_cache.py:146`, `stages/source_resolution.py:109`) | LOW | Direct truncating whole-file writes. An interrupted write corrupts the entire **paid** Gemini vision cache. | tmp + `os.replace`. |
| `project_manifest.py:169-177` | LOW | Single-generation `.bak`: if the primary is corrupt, `load()` recovers from `.bak`, then the next `save()` copies the corrupt primary **over** the good `.bak`. Two autosaves make it unrecoverable. | Skip the `.bak` copy when the primary failed to parse. |
| `tools/clean_products_data.py:154`, `tools/scrape_myinstants_titles.py:137` | LOW | Write `products.json` / `asset_metadata.json` directly, bypassing the stores → the next `_load()` re-imports and wipes newer SQLite rows. | Route through `ProductStore._mutate()`. |
| `temp_ecc/` (31 MB), `scratch/` (9 MB), `frontend/dist/` (13 MB) | LOW | Dead weight. `temp_ecc/` is a **nested `.git`** and is not in `.gitignore`. No cleanup path for `COVERS_DIR/.cache`. `frontend/dist/` is served by nothing (no `StaticFiles` mount anywhere) — a latent stale-bundle trap, not a live one. | Delete all three; gitignore `temp_ecc/`. |
| `.git` = 250 MB **[V]** | LOW | Audio assets committed to history — `02_Assets/Music/*.wav` at ~6 MB each, plus voiceover WAVs. Deleting them now does not reclaim the space. | Only fixable by history rewrite; not worth it unless the repo gets pushed. |
| `db.py:18-22`, `.env:4`, `frontend/postcss.config.js` | LOW | Docstring claims a `url` index that `_ensure_table` never creates. `.env:4` is a comment line missing its `#`. Tailwind v4 is wired twice (`@tailwindcss/vite` **and** `@tailwindcss/postcss` + redundant `autoprefixer`). | Fix the docstring, add the `#`, delete `postcss.config.js`. |

---

## 3. Dual source of truth — the structural root cause

The sticker bug just fixed was not a one-off. The persisted schema stores the same fact in multiple places, and **`firstPresent` (`editorProjectState.js:6-8`) skips `null`** — so a deliberately cleared value at the root can never shadow a stale non-null copy in `render_params` or `style`. Every one of the ~16 style fields inherits this. **[V]**

| Entity | The two representations | Delete/clear keeps both in sync? | Consequence |
|---|---|---|---|
| Sticker → `sticker_path` | `stickers[]` vs `render_params.sticker_path` | **NO** — `serializeStyle` never emits it; only a reroll's `sticker_badge:''` clears it | **C3** — deleted sticker burned into the MP4 |
| Sticker → geometry | `stickers[i].{scale,normX,normY,start,end}` vs `style.sticker_*` (+ root + `render_params` + camel twins) | **NO** — all three delete paths clear only `stickerBadge`; the 5 timing/position mirrors persist forever | Supplies the coordinates for the C3 phantom |
| Sticker → badge | `stickers[]` vs `style.stickerBadge` | **YES** — the known fix. But 3 independent handlers each re-implement the clear; nothing enforces it | Fragile, not broken |
| Cues | `cues` vs `micro_cues` | Sync by **clobbering** | **H2** — already flattened on all 7 projects |
| BGM | root/`style.bgm_name` vs `render_params.bgm_name` | **NO** — "no BGM" is `null`, which `firstPresent` skips | **Clearing BGM is not expressible.** Latent (no project currently holds `null`) |
| Style scalars | `manifest[k]` / `manifest.style[k]` / `render_params[k]`, each in camel **and** snake — up to **6 copies of one fact** | Priority is **inverted**: frontend reads root-first, the reuse engine (`pipeline_context.py:119-123`) reads `render_params`-first | Live divergence found: `GOC01-โปรไฟลุก_1` has root `sticker_start_time=1.4` vs `render_params=None` |
| `render_params` key set | `video_assembly_stage.py:172-212` builds it as a **fresh literal** and `ProjectManifest.save` does `manifest.update()` = wholesale replace **[V]** | n/a | **Every render deletes `render_params.effects`, `.track_mix`, `.hook_*`, `.sticker_badge`.** `effects` is the feature just added in ef8cfc4 |
| Text overlays | `overlays[]` vs `text_overlays[]` | Guarded (`isinstance(existing, list)` / `Array.isArray`) — `[]` is authoritative | Safe |
| Hook tiers | `overlays[]` vs `hook_brand/_model/...` | Scalars are never written by any frontend caller | Banner is guarded, but `subtitle_engine.py:696` reads scalars absent from all 7 projects → **brand/model caption highlighting is silently dead** |
| `trackMix` | `useState` vs undo history | Never in `reset()` | Ctrl+Z cannot undo a mute/solo |

---

## 4. Data flow (condensed)

**Render pipeline** — `pipeline.py:234-259`, 7 stages, state almost entirely in-memory on `PipelineContext`:
`SourceResolution` → `Script` → `Voice` (`voiceover.wav`) → `Subtitle` (`subtitles.ass`) → `AudioMix` (`mixed_audio.wav`) → `ShotMatching` (`image_motion_footage.mp4`) → `VideoAssembly` (`exports/*.mp4`, ExportRegistry, **and the only write of `project.json`**).

> **Crash safety: none.** No checkpoint, no resume, no cleanup. Dying at stage 4 leaves wav/ass/partial-mp4 on disk with **no manifest**, so `resume_from` fails at `ProjectManifest.require()` and a retry claims a *new* folder, orphaning the partial one. `pipeline.py:336` has a `resume_from` parameter that nothing ever calls.

**Editor round trip** — React state → `editorStateToSavePayload` → 500 ms debounce → `projectSaveQueue` → `PATCH /projects/{n}/state` → `ProjectManifest.save` → `manifestToEditorState` → `reset()`.
The pair is **not symmetric**. Confirmed round-trip losses: `micro_cues` (H2), cue `scale/x/y/position`, clip 0's `transition_in`.

---

## 5. Quick wins vs deep fixes

### Quick wins — safe, minutes each, no design decision needed
1. **Set `OMNICUT_API_KEY` + `VITE_API_KEY`** (C1) — closes the whole unauthenticated surface, including C2's reachability. Config only.
2. **`Path(file.filename or "").name` + suffix allowlist** at `api_videos.py:583` (C2) — copy the sibling at `:231`.
3. **`if isinstance(stickers, list):`** at `video_editor.py:873` (C3) — one word.
4. **Gitignore the 3 JSON mirrors** (H1) — removes a silent data-destruction vector.
5. **`timeout=60`** on the `ffprobe` call at `video_editor.py:391` (H13).
6. **Default `FASTAPI_RELOAD` to `"false"`** at `api_server.py:160` (H14).
7. **Guard `handleUpdateSticker`** at `EditorShell.jsx:903` (H3) — one early return.
8. **Create a venv** and point `start_app.bat` at it.
9. **`logs[-50:]`** at `render_jobs.py:92`; **revoke and delete `GEMINI_API_KEY_OLD`**; **add the missing `#`** at `.env:4`.
10. **Delete `temp_ecc/`, `scratch/`, `frontend/dist/`** and gitignore `temp_ecc/`.

### Deep fixes — need a plan and tests first
1. **`ProjectManifest.save_merge()` under `_SAVE_LOCK`** (C4, and `render_jobs.py:312`) — touches every manifest writer.
2. **Transaction discipline across stores** (C7, C8, H8, H9) — the nested-transaction problem `db.py:76-84` already documents. Needs a rule about who may open a transaction and a test that actually nests.
3. **Collapse the 6-way style duplication** (§3) — decide one authoritative location, make `firstPresent` distinguish "absent" from "explicitly null", and stop `video_assembly_stage.py:172` from replacing `render_params` wholesale. This is the single change that retires the whole bug class, including the sticker one.
4. **Make save failures visible** (C5, H4, H5, H6) — a real error surface plus retry, instead of `.catch(() => {})`.
5. **`micro_cues` ownership** (H2) — decide whether the editor may write it at all. Note the existing damage is already on disk in all 7 projects.
6. **Render crash recovery** — wire up the `resume_from` that already exists, and reap orphaned ffmpeg.

---

## 6. Note on the audit itself

Findings marked **[A]** cite specific `file:line` locations but were produced by audit agents and not independently re-verified line by line. Everything marked **[V]** was checked directly against the code or the running system. Before acting on an **[A]** finding, read the cited line — the citation is a pointer, not a guarantee.

No code was modified during this audit.
