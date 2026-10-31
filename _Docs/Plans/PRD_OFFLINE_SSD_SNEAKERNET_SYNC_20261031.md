# PRD: OmniCut Offline SSD Staging & Sneakernet Two-Way Sync (Home PC ↔ Cafe Laptop)

**Document ID:** `PRD-OMNICUT-SNEAKERNET-20261031`  
**Status:** `ready-for-agent`  
**Created Date:** 2026-10-31  
**Author:** Antigravity (Gemini 3.8 Flash)  
**Target Systems:** OmniCut Desktop (Home Workstation) ↔ External Portable SSD ↔ OmniCut Mobile/Cafe Uploader (Laptop)

---

## Problem Statement

Content creators producing high-volume short-form e-commerce and affiliate videos (such as Chinese video adaptations, gadget reviews, and couple comedy sitcoms) encounter a severe physical infrastructure bottleneck:
1. **Asymmetric Network Speeds at Home:** The home workstation possesses the heavy GPU and CPU hardware necessary to run batch AI generation, Whisper transcription, multi-bus audio mixing, Rembg background removal, and 1080x1920 60fps video rendering. However, home residential broadband upload bandwidth is severely limited (often congested or capped at low upload speeds), making the direct upload of dozens of high-bitrate video clips (each 80–200 MB, totaling 3–10 GB per batch) to social platforms (TikTok Studio, YouTube Shorts, Facebook Reels) unacceptably slow, taking hours and blocking workflow.
2. **High-Speed Network at Cafes/Co-working Spaces:** Commercial cafes and co-working spaces offer gigabit symmetrical fiber and high-bandwidth 5G, where dozens of clips can be uploaded in minutes. However, the user's portable laptop lacks the high-end GPU/CUDA power required to generate and render these videos on battery power.
3. **Lack of Synchronized Offline Transport (Sneakernet):** Currently, manually copying video files via USB drives leads to fragmented files, missing captions, lost TikTok product IDs, lost thumbnail associations, untracked upload statuses, and duplicate uploads upon returning home. 
4. **Risk of Data Corruption & Status Drift:** Without atomic manifest files and cryptographic verification, premature SSD ejection can cause corrupt uploads, and the home database remains unaware of which clips were successfully posted, scheduled, or failed at the cafe.

---

## Solution

The **OmniCut Offline SSD Staging & Sneakernet Two-Way Sync Engine** provides a seamless, robust, hardware-assisted transport pipeline connecting the Home Heavy-Render Workstation and the Mobile Cafe Upload Laptop via an External Portable SSD (Drive 1 / NVMe / USB 3.2):

1. **Station 1 (Home Workstation — Generation & Staging):**
   - Completes batch generation and rendering of videos, thumbnails, captions, hashtags, and showcase product mappings.
   - Provides a 1-click **"Export to SSD"** action that constructs an atomic, self-contained transport bundle inside `[SSD]/OmniCut_Vault/`.
   - Generates SHA-256 cryptographic checksums for every video and cover asset to guarantee integrity.
   - Generates a standalone `sync_manifest.json` and `queue.json` containing complete posting payloads (captions, hashtags, TikTok showcase product IDs, schedules).
   - Signals a clean "Safe to Unplug" verification when file transfers and disk flushes are complete.

2. **Station 2 (External SSD — Portable Vault & Staging Medium):**
   - Functions as an isolated, self-describing staging capsule.
   - Contains all required media binaries (`videos/`, `covers/`), metadata descriptors, and a lightweight, dependency-free portable upload runner (`OmniCut_Cafe_Uploader`).

3. **Station 3 (Cafe Laptop — High-Speed Batch Upload Hub):**
   - User plugs the SSD into the laptop at a cafe with high-speed internet.
   - Laptop launches the lightweight **Cafe Upload Dashboard** (runs locally or via web browser, requiring no heavy AI models, Python torch, or CUDA).
   - Instant SHA-256 integrity check validates that files are intact.
   - User executes automated batch uploading (via browser automation / `tiktok-autopost` or guided 1-click clipboard assistant).
   - Live transaction log updates `state.json` on the SSD atomically after each video is posted or scheduled, recording platform post URLs, platform video IDs, and timestamps.
   - Supports seamless pause/resume if cafe WiFi drops or laptop goes to sleep.

4. **Station 4 (Return Home — Two-Way Reconciliation & Archiving):**
   - User returns home and plugs the SSD back into the Home Workstation.
   - OmniCut detects the SSD and offers a 1-click **"Reconcile & Merge from SSD"**.
   - Ingests `state.json` receipts, updates canonical databases (`_Docs/post_log.json`, `_Docs/schedule_queue.json`, `_Docs/export_registry.json`, `_Docs/store.db`), and transitions clip statuses to `posted`.
   - Automatically moves posted videos on the Home PC to `04_Exports/Posted/` and archives or wipes the staging vault on the SSD to prepare for the next production batch.
   - 100% Zero-Duplicate and Zero-Status-Drift guarantee.

---

## User Stories

1. As a video creator, I want to render all Chinese video adaptation clips on my powerful home desktop, so that rendering completes rapidly without overheating a laptop.
2. As a video creator, I want OmniCut to detect my connected external SSD automatically, so that I don't have to navigate Windows drive letters manually.
3. As a video creator, I want to click a single "Stage to External SSD" button in the OmniCut desktop UI, so that all queued ready-to-post clips are packaged without manual file copying.
4. As a video creator, I want the export bundle to include both 9:16 and 3:4 thumbnail covers alongside the video files, so that I have the exact cover files ready during mobile uploading.
5. As a video creator, I want the SSD export process to generate SHA-256 checksums for each file, so that I can detect if any file was corrupted during USB transfer.
6. As a video creator, I want the home system to flush all operating system disk write buffers before alerting me, so that I can safely unplug the external SSD without corrupting data.
7. As a video creator, I want the staging bundle to bundle all post captions, hashtags, scheduled posting times, and TikTok affiliate product IDs, so that I don't need to retype or look up metadata at the cafe.
8. As a video creator, I want the SSD to contain a lightweight portable upload runner, so that my laptop does not require a full OmniCut installation with heavy AI dependencies.
9. As a mobile worker, I want to plug the SSD into my laptop at a cafe and immediately view my upload queue, so that I can start uploading within seconds of opening my laptop.
10. As a mobile worker, I want the laptop uploader to verify the SHA-256 checksum of each video before attempting to upload, so that corrupted videos are rejected before wasting bandwidth.
11. As a mobile worker, I want a 1-click "Batch Upload to TikTok" feature on my laptop, so that all scheduled clips are uploaded and scheduled automatically using the cafe's gigabit internet.
12. As a mobile worker, I want the uploader to auto-fill the caption, hashtags, and TikTok showcase product anchor, so that human error and typos are completely eliminated.
13. As a mobile worker, I want the laptop uploader to update the SSD's `state.json` file immediately after each individual clip finishes uploading, so that no progress is lost if the laptop battery runs out or cafe WiFi disconnects.
14. As a mobile worker, I want the uploader to record the remote post URL, platform video ID, and actual upload timestamp into the SSD receipt, so that I have proof of publication.
15. As a mobile worker, I want the uploader to show upload speed (MB/s) and estimated time remaining for the batch, so that I know exactly when I can pack up and leave the cafe.
16. As a mobile worker, I want the ability to retry failed uploads with a single click, so that transient network glitches at the cafe do not break the whole batch.
17. As a mobile worker, I want a fallback "Manual Quick-Copy" panel on the laptop showing copyable captions, hashtags, product links, and video download buttons, so that I can manually post via mobile browser if automated login triggers a captcha.
18. As a video creator, I want to plug the SSD back into my home computer upon returning, so that the home system recognizes that an upload batch was completed.
19. As a video creator, I want a 1-click "Reconcile SSD" button on the home PC, so that post logs, schedule queues, and export registries on the home PC are synchronized with the cafe upload results.
20. As a video creator, I want the home reconciliation process to move posted videos from `04_Exports/Ready_to_post/` to `04_Exports/Posted/`, so that my local work directory remains clean and uncluttered.
21. As a video creator, I want the home reconciliation process to mark the scheduled items as `posted` in `schedule_queue.json`, so that the system never schedules or posts the same video twice.
22. As a video creator, I want an option to clean up or archive the video files on the external SSD after successful reconciliation, so that the SSD does not run out of storage space over time.
23. As a video creator, I want a visual sync report showing how many videos were exported, uploaded, scheduled, or failed, so that I have complete transparency across my two machines.
24. As a video creator, I want multi-channel support in the SSD bundle, so that clips intended for different TikTok/YouTube accounts are clearly separated and uploaded to the appropriate account profile.
25. As a video creator, I want an offline preview player in the laptop runner, so that I can double-check video and audio quality on my laptop before starting the upload.

---

## Implementation Decisions

### 1. Architectural Boundaries & Domain Separation
- **Home Station Role (The Factory):** Only the home workstation performs video synthesis, CapCut project manipulations, TTS voice synthesis, audio mixing, and FFmpeg encoding. It is the canonical source of truth for raw projects and initial schedule queues.
- **Laptop Station Role (The Postman):** The laptop performs strictly lightweight I/O, integrity checking, metadata display, and network upload execution. It never attempts to re-render, re-encode, or regenerate video assets.
- **External SSD Role (The Vault & Transport Courier):** The external SSD carries the self-contained sync payload. It acts as an offline message broker using file-system based transactions.

### 2. Vault File System Layout on External SSD
The root of the external SSD will host a dedicated staging directory `OmniCut_Vault/` with the following canonical structure:
- `OmniCut_Vault/`
  - `manifest.json`: Vault metadata, batch ID, export timestamp, origin machine signature, total count, target channels.
  - `queue.json`: Complete publishing records (array of items with `item_id`, `export_id`, `product_id`, `title`, `caption`, `hashtags`, `tiktok_product_id`, `scheduled_at`, `video_filename`, `cover_filename`).
  - `state.json`: Dynamic state tracker (map of `item_id` to status: `pending` | `uploading` | `posted` | `failed`, error details, publish receipts).
  - `checksums.sha256`: Standard SHA-256 hash file mapping relative file paths to hashes.
  - `media/videos/`: All rendered MP4 video files ready for posting.
  - `media/covers/`: All 3:4 and 9:16 cover images.
  - `uploader/`: Lightweight standalone web frontend or Python/Node runner executable for the laptop.

### 3. Home Desktop Staging Service
- Add an SSD Staging Service to the backend that:
  - Enumerates removable drives via OS-level volume detection.
  - Reads `_Docs/schedule_queue.json` and `_Docs/export_registry.json` filtering for `status == "pending"` or user-selected batch.
  - Performs atomic copy of video files and covers into `OmniCut_Vault/media/`.
  - Computes SHA-256 hashes during stream copy to avoid double disk reads.
  - Writes `manifest.json`, `queue.json`, and an initialized `state.json`.
  - Executes explicit OS flush (`FlushFileBuffers` on Windows) to guarantee physical persistence.

### 4. Laptop Cafe Uploader Architecture
- Provide a zero-dependency portable runner:
  - Can be run as a lightweight Python script (`python uploader.py` using standard library + requests/playwright) or a self-contained single-file portable GUI / web app.
  - Directly opens local browser at `http://localhost:port` or native window.
  - Reads `queue.json` and `state.json` from the SSD.
  - Integrates with the existing `tiktok-autopost` automation module and Chrome CDP session on the laptop.
  - Implements an atomic write pattern for `state.json` (writes to `state.json.tmp` then atomic rename) after every individual clip upload.

### 5. Return Home Reconciliation Engine
- Add a Sync Reconciliation Service to the home backend that:
  - Detects the connected SSD containing an active or completed `OmniCut_Vault/`.
  - Compares `state.json` against `_Docs/schedule_queue.json`, `_Docs/post_log.json`, and `_Docs/export_registry.json`.
  - For every item with `status == "posted"`:
    - Appends record to `_Docs/post_log.json` with remote post URL and timestamp.
    - Updates corresponding entry in `_Docs/schedule_queue.json` to `posted`.
    - Updates `_Docs/export_registry.json` and moves local file from `04_Exports/Ready_to_post/` to `04_Exports/Posted/`.
    - Updates `_Docs/store.db` angle/product records to maintain consistency.
  - Offers a safe cleanup action: moves vault files to `06_Archive/SSD_Batches/` or clears SSD `OmniCut_Vault/` upon confirmation.

### 6. Failure Recovery & Concurrency Guarantees
- **Disconnected SSD Mid-Transfer (Home):** Incomplete batches are marked invalid via a missing `SYNC_COMPLETED` sentinel flag in `manifest.json`.
- **Disconnected SSD Mid-Upload (Cafe):** Since `state.json` is updated atomically per video, reconnecting the SSD instantly resumes from the first unposted clip without duplicate uploads.
- **Offline Mode:** If cafe WiFi is down, the user can still review clips and adjust captions locally on the SSD.

---

## Testing Decisions

### What Makes a Good Test
- Tests must be deterministic, offline, and operate on sandboxed temporary directories (`tmp_path`).
- Tests must verify external behavior and invariants (file presence, valid JSON structure, correct status transitions, SHA-256 match) rather than internal implementation details.
- No test may touch actual production directories `04_Exports/` or external hardware.

### Modules to Test
1. **SSD Staging Module:**
   - Test packaging an export queue into a mock external drive directory.
   - Verify that all referenced video and thumbnail files are copied accurately.
   - Verify that generated SHA-256 checksums match the source files.
   - Verify that the `manifest.json` and `queue.json` contain all necessary metadata.
2. **Laptop State & Upload Engine:**
   - Test loading the staging vault on a secondary mock device.
   - Test checksum verification detecting corrupted or modified video files.
   - Test simulated upload loop with mock success/failure responses.
   - Verify atomic persistence of `state.json` after each item.
3. **Reconciliation & Merge Engine:**
   - Test merging updated `state.json` back into mock home registries (`export_registry.json`, `schedule_queue.json`, `post_log.json`).
   - Test idempotency: running reconciliation multiple times produces identical, non-duplicate results.
   - Verify file relocation from `Ready_to_post/` to `Posted/` upon reconciliation.

### Prior Art in Codebase
- `scripts/backup_engine.py` (Atomic zip creation, snapshot locks, and safe path containment).
- `scripts/api_mobile_posting.py` (Schedule queue management, channel scoping, and posting job stores).
- `tests/test_mobile_sync_defects.py` (Cross-device data contract revalidation and state synchronization).

---

## Out of Scope

- Automated synchronization over cloud relays (e.g. Google Drive / AWS S3) for the video files, since the user explicitly requested an offline physical SSD solution due to slow home internet.
- Running heavy video rendering, AI transcription, or Rembg cutout on the laptop.
- Automatic hardware ejection without user confirmation.
- Directly flashing or re-partitioning external storage drives.

---

## Further Notes

- **Recommended External SSD Setup:** A portable USB 3.2 Gen 2 NVMe SSD (such as Samsung T7 / SanDisk Extreme / Crucial X9) delivers 800–1050 MB/s transfer speeds. Copying 30 clips (3 GB) takes less than 5 seconds.
- **Drive Letter Flexibility:** The system must locate the vault by folder signature (`OmniCut_Vault/manifest.json`) rather than hardcoded Windows drive letters (e.g., `D:`, `E:`, `F:`), ensuring flawless operation even if Windows assigns different drive letters between home and cafe.
- **Cafe Laptop Prerequisites:** The laptop only requires Chrome/Edge browser for uploading and a lightweight Python or Node runtime (or a bundled standalone executable).
