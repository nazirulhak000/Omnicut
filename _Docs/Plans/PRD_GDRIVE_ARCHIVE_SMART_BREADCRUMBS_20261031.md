# PRD: Google Drive Smart Archiving & Local Breadcrumb Retention (OmniCut Pro Studio)

**Document ID:** `PRD_GDRIVE_ARCHIVE_SMART_BREADCRUMBS_20261031`  
**Author / Lead:** Antigravity (Gemini 2.5 Pro)  
**Status:** Approved & In-Progress  
**Target Environment:** Windows 11 Desktop (FastAPI + React/Vite + Google Drive for Desktop)

---

## 1. Executive Summary & Problem Statement

### 1.1 The Problem
In OmniCut Pro Studio, full 9:16 vertical video production generates large assets for each product angle:
- Heavy rendered 1080x1920 MP4 video files (`04_Exports/Posted/`) accumulate to several gigabytes (currently 3.87 GB across 116 posted clips).
- Downloaded B-roll and clean design films (`01_Raw/`) consume 3.42 GB.
- CapCut project folders, timeline cache, and audio stems (`03_Projects/`) consume 1.38 GB.
Over months of continuous production, keeping dozens or hundreds of completed, already-posted video files locally on the high-speed NVMe system drive (`D:\`) exhausts disk capacity.

### 1.2 The User's Requirement
1. **Archive to Google Drive:** Once a product or clip is posted, its heavy, non-essential assets should be safely backed up to Google Drive.
2. **Preserve Lightweight Breadcrumbs in App:** In the local OmniCut interface, keep lightweight markers (cover image thumbnails in `05_Covers_Thumbnails/`, metadata in `_Docs/post_log.json`, `_Docs/export_registry.json`, and clear badges indicating "โพสต์แล้ว (Posted)" and "☁️ Google Drive").
3. **Zero Blank Cards & Zero Data Loss:** The user should still see the visual cover art, metrics, product title, and date in the gallery without blank cards.
4. **1-Click Convenience:** 100% GUI via clickable buttons. Provide a button to "Open in Google Drive" directly in Windows Explorer, and a 1-click "Restore" button if the user ever needs the heavy video back locally.

---

## 2. Infrastructure Discovery & Seamless Integration

During system probing, the local filesystem confirmed:
- **Google Drive for Desktop is already installed and mounted at drive `G:\`!**
- Dedicated directories already exist at:
  - `G:\My Drive\Omnicut_Exports\01_Ready_to_post\`
  - `G:\My Drive\Omnicut_Exports\02_Posted_Archive\`

This eliminates the need for OAuth 2.0 web login flows, API rate limits, or expiring tokens. OmniCut can copy files directly to `G:\` with native filesystem speeds, and Google Drive for Desktop automatically synchronizes them to Google's cloud servers in the background.

---

## 3. Architecture & Functional Specification

### 3.1 Data Classification: What Moves vs What Stays

| Asset Type | Source Path | Action upon Archive | Local Storage Impact |
| :--- | :--- | :--- | :--- |
| **Rendered Video** | `04_Exports/Posted/*.mp4` | Copy to `G:\My Drive\Omnicut_Exports\02_Posted_Archive\[Product]\Videos\`, verify SHA-256, delete local | **Reclaims 100% of video space (3.87+ GB)** |
| **Cover Thumbnail** | `05_Covers_Thumbnails/*.jpg` | **STAYS LOCALLY** (Also backed up to Drive) | Preserved locally (~150 KB per clip) for instant UI display |
| **Post Log & Proof** | `_Docs/post_log.json` | **STAYS LOCALLY** (Updated with `cloud_archived: true`, `cloud_path: ...`) | Preserved locally for stats, metrics, and tracking |
| **Export Registry** | `_Docs/export_registry.json` | **STAYS LOCALLY** (Updated with `cloud_status: "archived_gdrive"`) | Preserved locally for canonical history |
| **Raw Materials** *(Optional)* | `01_Raw/[Product]/` | Copy to `G:\...\[Product]\Sources\Raw\`, verify, purge local | Reclaims 3.42 GB |
| **Project Drafts** *(Optional)*| `03_Projects/[Product]/`| Copy to `G:\...\[Product]\Sources\Projects\`, verify, purge local | Reclaims 1.38 GB |

### 3.2 Double SHA-256 Verification Gate (Zero Data Loss)
A local file is NEVER unlinked or deleted unless:
1. Destination file exists on `G:\My Drive\Omnicut_Exports\02_Posted_Archive\...`
2. Destination file size matches source file size exactly.
3. Destination SHA-256 hash matches source SHA-256 hash bit-for-bit.
4. `archive_manifest.json` is written to the destination directory.

### 3.3 Reversibility & 1-Click Restoration
Every archived clip maintains a link to its Google Drive archive path.
- Clicking **"เปิดโฟลเดอร์ใน Drive"** executes `explorer.exe /select,"G:\..."` to reveal the file in Windows Explorer.
- Clicking **"ดึงคลิปกลับมา (Restore)"** copies the video back from Google Drive to `04_Exports/Posted/`, immediately making it locally playable again.

---

## 4. Component Roadmap & Implementation Seams

1. **Backend Engine:** `scripts/gdrive_archive_engine.py`
   - Detects Google Drive Desktop root (`G:\My Drive\Omnicut_Exports\02_Posted_Archive` or custom).
   - Scans posted clips eligible for archiving.
   - Calculates space savings (MB / GB).
   - Stages files to Google Drive, performs SHA-256 checks, safely prunes local video.
   - Restores files on demand.

2. **Backend API Router:** `scripts/api_gdrive_archive.py`
   - `GET /api/archive/status`: returns total space reclaimable, drive health, and list of products with posted clips.
   - `POST /api/archive/execute`: executes archiving with progress tracking and safety verification.
   - `POST /api/archive/restore`: restores an archived clip back to local storage.
   - Registered in `scripts/api_server.py`.

3. **Frontend UI Modal:** `frontend/src/components/CloudArchiveModal.jsx`
   - Cyberpunk / Dark Glassmorphism Studio UI.
   - Reclaimable storage counter, drive detection status indicator.
   - Product list with thumbnail preview, clip count, and individual selection checkboxes.
   - Radio buttons for backup scope:
     - 🟢 **(Recommended) เฉพาะคลิปวิดีโอที่โพสต์แล้ว (Video Only)** — Safe, immediate 3.8+ GB reclaim.
     - 🔵 **สำรองครบทั้งโปรเจกต์ (Full Product Archive)** — Video + Raw + Drafts.
   - 1-Click execution button with progress bar and success summary.

4. **Frontend Integration:**
   - Add button `<Button icon={Cloud}>Google Drive Archive</Button>` in `frontend/src/components/ExportGallery.jsx`.
   - Update export cards to display `☁️ Google Drive` badge, "เปิดใน Drive", and "ดึงกลับ" buttons when `item.cloud_status === 'archived_gdrive'`.

5. **Automated Testing & Verification:**
   - `tests/test_gdrive_archive_pipeline.py`: Comprehensive sandbox tests for staging, hash verification, local pruning, cover retention, and full restoration.
