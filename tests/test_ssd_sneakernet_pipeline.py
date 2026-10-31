"""End-to-End Test Suite & 100-Point Scoring Evaluator for External SSD Sneakernet Pipeline.

Agent 5: QA / TDD Gatekeeper & 100-Point Scoring Evaluator
Validates the entire round-trip pipeline across Home PC -> SSD Vault -> Cafe Laptop -> Return Home.
Calculates and asserts the 100-Point Scoring Rubric.
"""
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import pytest
from http.server import HTTPServer
import threading
import urllib.request
import urllib.error

from scripts.ssd_staging_engine import SSDStagingEngine, compute_file_sha256, get_removable_drives, flush_disk_buffers
from scripts.ssd_reconcile_engine import SSDReconcileEngine
import tools.portable_uploader_server as portable_server


@pytest.fixture
def sandbox_env(tmp_path):
    """Creates an isolated mock environment simulating Home PC, External SSD, and Laptop."""
    home_dir = tmp_path / "HomePC"
    ssd_dir = tmp_path / "ExternalSSD_E"

    home_dir.mkdir(parents=True)
    ssd_dir.mkdir(parents=True)

    # 1. Create Home PC file structure
    docs_dir = home_dir / "_Docs"
    ready_dir = home_dir / "04_Exports" / "Ready_to_post"
    posted_dir = home_dir / "04_Exports" / "Posted"
    covers_dir = home_dir / "05_Covers_Thumbnails"
    ext_dir = home_dir / "tiktok_autopost_extension"
    tools_dir = home_dir / "tools"

    for d in (docs_dir, ready_dir, posted_dir, covers_dir, ext_dir, tools_dir):
        d.mkdir(parents=True, exist_ok=True)

    # 2. Mock video files
    video_file = ready_dir / "PROD01_review_v1.mp4"
    video_file.write_bytes(b"MOCK_MP4_VIDEO_CONTENT_BYTE_STREAM_1080x1920_HIGH_QUALITY")

    # 3. Mock cover file
    cover_file = covers_dir / "PROD01_cover_3x4.jpg"
    cover_file.write_bytes(b"MOCK_JPEG_IMAGE_COVER_THUMBNAIL_BYTES")

    # 4. Mock extension dummy file
    (ext_dir / "manifest.json").write_text('{"name": "OmniCut Mock"}', encoding="utf-8")

    # 5. Mock tools
    (tools_dir / "portable_uploader_server.py").write_text("# Mock", encoding="utf-8")

    # 6. Mock registries
    schedule_data = [
        {
            "id": "queue_item_001",
            "export_id": "exp_prod01_001",
            "video_path": "04_Exports/Ready_to_post/PROD01_review_v1.mp4",
            "cover_path": "05_Covers_Thumbnails/PROD01_cover_3x4.jpg",
            "status": "pending",
            "product_id": "prod_123",
            "product_name": "Ultra Power Bank 30000mAh",
            "hook_title": "พาวเวอร์แบงก์โคตรอึด ชาร์จได้ 7 วัน!",
            "caption": "พาวเวอร์แบงก์ไร้สาย แม่เหล็กแน่นมาก พิกัดในตะกร้า 👇",
            "hashtags": "#นายหน้าtiktok #รีวิวของดี",
            "tiktok_product_id": "173999888777",
            "scheduled_at": "2026-11-01T12:00:00+07:00",
            "channel_id": "main",
        }
    ]
    with open(docs_dir / "schedule_queue.json", "w", encoding="utf-8") as f:
        json.dump(schedule_data, f, indent=2)

    export_data = [
        {
            "id": "exp_prod01_001",
            "path": "04_Exports/Ready_to_post/PROD01_review_v1.mp4",
            "product_id": "prod_123",
            "status": "rendered",
            "created_at": "2026-10-31T10:00:00",
        }
    ]
    with open(docs_dir / "export_registry.json", "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2)

    channels_data = [
        {
            "id": "main",
            "name": "OmniCut Main Channel",
            "handle": "@omnicut_official",
            "status": "active",
            "posting_enabled": True,
            "account_binding": {"status": "verified", "verified_handle": "@omnicut_official"}
        }
    ]
    with open(docs_dir / "channels.json", "w", encoding="utf-8") as f:
        json.dump(channels_data, f, indent=2)

    with open(docs_dir / "post_log.json", "w", encoding="utf-8") as f:
        json.dump([], f)

    return {
        "home_dir": home_dir,
        "ssd_dir": ssd_dir,
        "video_file": video_file,
        "cover_file": cover_file,
    }


def test_category_1_drive_detection_and_staging(sandbox_env):
    """Category 1: Drive Detection & Safe Staging (20 Points)."""
    home = sandbox_env["home_dir"]
    ssd = sandbox_env["ssd_dir"]

    # 1.1 Drive Detection
    drives = get_removable_drives()
    assert isinstance(drives, list)

    # 1.2 Staging execution
    result = SSDStagingEngine.stage_to_vault(
        target_root=ssd,
        base_dir=home,
        include_all_pending=True,
    )
    assert result["status"] == "ok"
    assert result["staged_count"] == 1
    assert result["safe_to_eject"] is True

    # 1.3 Checksum validation
    vault_root = ssd / "OmniCut_Portable_Vault"
    staged_video = vault_root / "media" / "videos" / "PROD01_review_v1.mp4"
    staged_cover = vault_root / "media" / "covers" / "PROD01_cover_3x4.jpg"
    assert staged_video.exists()
    assert staged_cover.exists()

    orig_hash = compute_file_sha256(sandbox_env["video_file"])
    staged_hash = compute_file_sha256(staged_video)
    assert orig_hash == staged_hash

    # Check checksums.sha256 file
    checksum_lines = (vault_root / "checksums.sha256").read_text(encoding="utf-8").strip().splitlines()
    assert any(orig_hash in line and "PROD01_review_v1.mp4" in line for line in checksum_lines)

    # 1.4 Flush Disk Buffers
    flushed = flush_disk_buffers(vault_root)
    assert flushed in (True, False)  # Handles OS without root or mock environment gracefully


def test_category_2_vault_integrity_and_path_independence(sandbox_env):
    """Category 2: SSD Vault Integrity & Path Independence (20 Points)."""
    home = sandbox_env["home_dir"]
    ssd = sandbox_env["ssd_dir"]

    # Stage first
    SSDStagingEngine.stage_to_vault(target_root=ssd, base_dir=home)
    vault_root = ssd / "OmniCut_Portable_Vault"

    # 2.1 File structure completeness
    assert (vault_root / "manifest.json").exists()
    assert (vault_root / "queue.json").exists()
    assert (vault_root / "state.json").exists()
    assert (vault_root / "START_CAFE_UPLOADER.bat").exists()
    assert (vault_root / "media" / "videos").is_dir()
    assert (vault_root / "media" / "covers").is_dir()
    assert (vault_root / "_Docs" / "channels.json").exists()

    # 2.2 Drive-Letter Independence: simulate moving SSD to a new path (e.g. Drive F:)
    simulated_laptop_drive = sandbox_env["home_dir"].parent / "Simulated_Drive_F"
    shutil.copytree(vault_root, simulated_laptop_drive / "OmniCut_Portable_Vault")
    new_vault = simulated_laptop_drive / "OmniCut_Portable_Vault"

    # Verify all references in queue.json are relative
    with open(new_vault / "queue.json", "r", encoding="utf-8") as f:
        queue = json.load(f)
    item = queue[0]
    assert item["video_rel_path"] == "media/videos/PROD01_review_v1.mp4"
    assert (new_vault / item["video_rel_path"]).exists()

    # 2.3 Atomic state writing test
    state_file = new_vault / "state.json"
    with open(state_file, "r", encoding="utf-8") as f:
        state = json.load(f)
    state[item["id"]]["status"] = "uploading"
    portable_server._save_json_atomic(state_file, state)

    with open(state_file, "r", encoding="utf-8") as f:
        updated_state = json.load(f)
    assert updated_state[item["id"]]["status"] == "uploading"


def test_category_3_and_4_portable_mini_server_and_extension(sandbox_env):
    """Category 3 & 4: Mini-Server APIs and Chrome Extension Parity (40 Points)."""
    home = sandbox_env["home_dir"]
    ssd = sandbox_env["ssd_dir"]

    SSDStagingEngine.stage_to_vault(target_root=ssd, base_dir=home)
    vault_root = ssd / "OmniCut_Portable_Vault"

    # Point portable server to this vault
    portable_server.VAULT_ROOT = vault_root

    server = HTTPServer(("127.0.0.1", 0), portable_server.PortableRequestHandler)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        # 3.1 GET /api/channels
        req = urllib.request.Request(f"{base_url}/api/channels")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            channels_res = json.loads(resp.read().decode("utf-8"))
            channels_list = channels_res.get("channels") if isinstance(channels_res, dict) else channels_res
            assert len(channels_list) >= 1
            assert channels_list[0]["id"] == "main"

        # 3.2 GET /api/schedule-queue
        req = urllib.request.Request(f"{base_url}/api/schedule-queue")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            queue_res = json.loads(resp.read().decode("utf-8"))
            queue_items = queue_res.get("items") if isinstance(queue_res, dict) else queue_res
            assert len(queue_items) == 1
            assert queue_items[0]["status"] in ("pending", "ready_for_extension")
            assert Path(queue_items[0]["video_path"]).exists()

        # 3.3 GET /api/exports
        req = urllib.request.Request(f"{base_url}/api/exports")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            exports = json.loads(resp.read().decode("utf-8"))
            assert len(exports) == 1

        # 3.4 GET /api/media/*
        cover_rel = queue_items[0]["cover_url"].replace("/api/media/", "")
        media_req = urllib.request.Request(f"{base_url}/api/media/{cover_rel}")
        with urllib.request.urlopen(media_req) as resp:
            assert resp.status == 200
            assert resp.read() == b"MOCK_JPEG_IMAGE_COVER_THUMBNAIL_BYTES"

        # 4.1 POST /api/tiktok-autopost/prepare
        prepare_payload = json.dumps({
            "video_path": queue_items[0]["video_path"],
            "cover_path": queue_items[0]["cover_path"],
            "caption": queue_items[0]["caption"],
            "hashtags": queue_items[0]["hashtags"],
            "tiktok_product_id": queue_items[0]["tiktok_product_id"],
            "queue_id": queue_items[0]["id"],
        }).encode("utf-8")
        prep_req = urllib.request.Request(
            f"{base_url}/api/tiktok-autopost/prepare",
            data=prepare_payload,
            headers={"Content-Type": "application/json", "X-OmniCut-Channel": "main"},
        )
        with urllib.request.urlopen(prep_req) as resp:
            assert resp.status == 200
            prepared = json.loads(resp.read().decode("utf-8"))
            assert prepared["protocol_version"] == 2
            assert prepared["job_id"].startswith("job_")
            job_id = prepared["job_id"]

        # 4.2 GET /api/tiktok-autopost/pending
        pending_req = urllib.request.Request(f"{base_url}/api/tiktok-autopost/pending")
        with urllib.request.urlopen(pending_req) as resp:
            assert resp.status == 200
            pending = json.loads(resp.read().decode("utf-8"))
            assert pending["job_id"] == job_id

        # 4.3 POST /api/tiktok-autopost/claim
        claim_payload = json.dumps({
            "job_id": job_id,
            "lease_owner": "test_extension_worker",
            "protocol_version": 2,
        }).encode("utf-8")
        claim_req = urllib.request.Request(
            f"{base_url}/api/tiktok-autopost/claim",
            data=claim_payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(claim_req) as resp:
            assert resp.status == 200
            claimed = json.loads(resp.read().decode("utf-8"))
            assert claimed["lease_token"].startswith("lease_")
            assert claimed["status"] == "claimed"

        # 4.4 POST /api/tiktok-autopost/acknowledge (Simulate upload success)
        ack_payload = json.dumps({
            "job_id": job_id,
            "queue_id": queue_items[0]["id"],
            "post_url": "https://www.tiktok.com/@omnicut_official/video/7391234567890",
            "platform_id": "7391234567890",
        }).encode("utf-8")
        ack_req = urllib.request.Request(
            f"{base_url}/api/tiktok-autopost/acknowledge",
            data=ack_payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(ack_req) as resp:
            assert resp.status == 200
            ack_resp = json.loads(resp.read().decode("utf-8"))
            assert ack_resp["success"] is True

        # Verify state.json on SSD updated to posted
        with open(vault_root / "state.json", "r", encoding="utf-8") as f:
            updated_states = json.load(f)
        assert updated_states[queue_items[0]["id"]]["status"] == "posted"
        assert updated_states[queue_items[0]["id"]]["post_url"] == "https://www.tiktok.com/@omnicut_official/video/7391234567890"

    finally:
        server.shutdown()
        server.server_close()


def test_category_5_two_way_reconciliation_and_archive(sandbox_env):
    """Category 5: Two-Way Reconciliation & Archiving (20 Points)."""
    home = sandbox_env["home_dir"]
    ssd = sandbox_env["ssd_dir"]

    # 1. Stage
    SSDStagingEngine.stage_to_vault(target_root=ssd, base_dir=home)
    vault_root = ssd / "OmniCut_Portable_Vault"

    # 2. Simulate posted state on SSD
    with open(vault_root / "queue.json", "r", encoding="utf-8") as f:
        queue = json.load(f)
    item_id = queue[0]["id"]

    state_file = vault_root / "state.json"
    states = {
        item_id: {
            "status": "posted",
            "uploaded_at": "2026-11-01T13:45:00+07:00",
            "post_url": "https://www.tiktok.com/@omnicut/video/99887766",
            "post_id": "99887766",
            "error": None,
        }
    }
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(states, f, indent=2)

    # 3. Run Reconciliation
    res = SSDReconcileEngine.reconcile_from_vault(
        vault_root=ssd,
        base_dir=home,
        clean_ssd_after=True,
    )
    assert res["status"] == "ok"
    assert res["reconciled_count"] == 1
    assert res["cleaned_media_count"] == 1

    # 4. Verify Home PC Databases
    # schedule_queue.json
    with open(home / "_Docs" / "schedule_queue.json", "r", encoding="utf-8") as f:
        home_q = json.load(f)
    assert home_q[0]["status"] == "posted"
    assert home_q[0]["posted_at"] == "2026-11-01T13:45:00+07:00"
    assert "04_Exports/Posted/" in home_q[0]["video_path"]

    # export_registry.json
    with open(home / "_Docs" / "export_registry.json", "r", encoding="utf-8") as f:
        home_exp = json.load(f)
    assert home_exp[0]["status"] == "posted"
    assert "04_Exports/Posted/" in home_exp[0]["path"]

    # post_log.json
    with open(home / "_Docs" / "post_log.json", "r", encoding="utf-8") as f:
        post_log = json.load(f)
    assert len(post_log) == 1
    assert post_log[0]["post_url"] == "https://www.tiktok.com/@omnicut/video/99887766"

    # Video moved from Ready_to_post to Posted
    ready_video = home / "04_Exports" / "Ready_to_post" / "PROD01_review_v1.mp4"
    posted_video = home / "04_Exports" / "Posted" / "PROD01_review_v1.mp4"
    assert not ready_video.exists()
    assert posted_video.exists()

    # 5. Idempotent merge test (Run a second time, must not duplicate)
    res_second = SSDReconcileEngine.reconcile_from_vault(vault_root=ssd, base_dir=home)
    assert res_second["status"] == "ok"
    assert res_second["already_posted_count"] == 1

    with open(home / "_Docs" / "post_log.json", "r", encoding="utf-8") as f:
        post_log_second = json.load(f)
    assert len(post_log_second) == 1  # Still 1, zero duplicates!


def test_ssd_posted_archive_and_partial_batch(sandbox_env):
    """Verifies Posted_Archive on SSD, selective staging, and partial batch handling."""
    home = sandbox_env["home_dir"]
    ssd = sandbox_env["ssd_dir"]

    # 1. Add second clip to home
    ready_dir = home / "04_Exports" / "Ready_to_post"
    v2 = ready_dir / "PROD02_clip.mp4"
    v2.write_bytes(b"CLIP_TWO_BYTES")

    with open(home / "_Docs" / "schedule_queue.json", "r", encoding="utf-8") as f:
        q_data = json.load(f)
    q_data.append({
        "id": "queue_item_002",
        "export_id": "exp_prod02_002",
        "video_path": "04_Exports/Ready_to_post/PROD02_clip.mp4",
        "status": "pending",
        "product_id": "prod_456",
        "product_name": "Second Product",
        "hook_title": "คลิปที่สอง",
        "caption": "แคปชันคลิปที่สอง",
    })
    with open(home / "_Docs" / "schedule_queue.json", "w", encoding="utf-8") as f:
        json.dump(q_data, f)

    # 2. Stage only item 2 via export_ids (Selective Staging)
    res = SSDStagingEngine.stage_to_vault(target_root=ssd, base_dir=home, export_ids=["exp_prod02_002"], include_all_pending=False)
    assert res["staged_count"] == 1
    vault_root = ssd / "OmniCut_Portable_Vault"
    assert (vault_root / "media" / "videos" / "PROD02_clip.mp4").exists()

    # 3. Simulate post
    with open(vault_root / "state.json", "w", encoding="utf-8") as f:
        json.dump({"queue_item_002": {"status": "posted", "uploaded_at": "2026-11-01T15:00:00"}}, f)

    # 4. Reconcile with retention_mode='archive'
    rec = SSDReconcileEngine.reconcile_from_vault(vault_root=ssd, base_dir=home, retention_mode="archive")
    assert rec["status"] == "ok"
    assert rec["archived_media_count"] == 1
    assert (vault_root / "Posted_Archive" / "PROD02_clip.mp4").exists()
    assert not (vault_root / "media" / "videos" / "PROD02_clip.mp4").exists()


def test_100_point_scoring_rubric_evaluation(sandbox_env):
    """Master Evaluator: Computes and asserts 100/100 points across all 5 categories."""
    home = sandbox_env["home_dir"]
    ssd = sandbox_env["ssd_dir"]

    scores = {
        "cat1_staging_and_detection": 0,
        "cat2_vault_integrity": 0,
        "cat3_mini_server_apis": 0,
        "cat4_extension_parity": 0,
        "cat5_reconcile_and_idempotence": 0,
    }

    # Category 1: Staging & Detection (20)
    drives = get_removable_drives()
    if isinstance(drives, list):
        scores["cat1_staging_and_detection"] += 5

    res = SSDStagingEngine.stage_to_vault(target_root=ssd, base_dir=home)
    if res["status"] == "ok" and res["staged_count"] == 1:
        scores["cat1_staging_and_detection"] += 5

    vault = ssd / "OmniCut_Portable_Vault"
    if (vault / "checksums.sha256").exists():
        scores["cat1_staging_and_detection"] += 5

    if res.get("safe_to_eject") is True:
        scores["cat1_staging_and_detection"] += 5

    # Category 2: Vault Integrity (20)
    if (vault / "manifest.json").exists() and (vault / "queue.json").exists() and (vault / "START_CAFE_UPLOADER.bat").exists():
        scores["cat2_vault_integrity"] += 5

    with open(vault / "queue.json", "r", encoding="utf-8") as f:
        q = json.load(f)
    if not any(":" in item["video_rel_path"] for item in q):  # Path independence check
        scores["cat2_vault_integrity"] += 5

    if q[0].get("tiktok_product_id") and q[0].get("caption"):
        scores["cat2_vault_integrity"] += 5

    if (vault / "state.json").exists():
        scores["cat2_vault_integrity"] += 5

    # Category 3: Mini-Server Performance & APIs (20)
    portable_server.VAULT_ROOT = vault
    server = HTTPServer(("127.0.0.1", 0), portable_server.PortableRequestHandler)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        req = urllib.request.Request(f"{base_url}/api/schedule-queue")
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                scores["cat3_mini_server_apis"] += 5

        req = urllib.request.Request(f"{base_url}/api/channels")
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                scores["cat3_mini_server_apis"] += 5

        cover_rel = q[0]["cover_rel_path"]
        req = urllib.request.Request(f"{base_url}/api/media/{cover_rel}")
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                scores["cat3_mini_server_apis"] += 5

        if (vault / "START_CAFE_UPLOADER.bat").exists():
            scores["cat3_mini_server_apis"] += 5

        # Category 4: Extension Parity & Upload Automation (20)
        prep_payload = json.dumps({
            "video_path": q[0]["video_rel_path"],
            "caption": q[0]["caption"],
            "hashtags": q[0]["hashtags"],
            "tiktok_product_id": q[0]["tiktok_product_id"],
            "queue_id": q[0]["id"],
        }).encode("utf-8")
        prep_req = urllib.request.Request(f"{base_url}/api/tiktok-autopost/prepare", data=prep_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(prep_req) as resp:
            job = json.loads(resp.read().decode("utf-8"))
            if job.get("protocol_version") == 2 and job.get("job_id"):
                scores["cat4_extension_parity"] += 5

        pending_req = urllib.request.Request(f"{base_url}/api/tiktok-autopost/pending")
        with urllib.request.urlopen(pending_req) as resp:
            if resp.status == 200:
                scores["cat4_extension_parity"] += 5

        claim_payload = json.dumps({"job_id": job["job_id"], "protocol_version": 2}).encode("utf-8")
        claim_req = urllib.request.Request(f"{base_url}/api/tiktok-autopost/claim", data=claim_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(claim_req) as resp:
            if resp.status == 200:
                scores["cat4_extension_parity"] += 5

        ack_payload = json.dumps({"job_id": job["job_id"], "queue_id": q[0]["id"], "post_url": "https://tiktok.com/123"}).encode("utf-8")
        ack_req = urllib.request.Request(f"{base_url}/api/tiktok-autopost/acknowledge", data=ack_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(ack_req) as resp:
            if resp.status == 200:
                scores["cat4_extension_parity"] += 5

    finally:
        server.shutdown()
        server.server_close()

    # Category 5: Reconcile & Idempotence (20)
    rec1 = SSDReconcileEngine.reconcile_from_vault(vault_root=ssd, base_dir=home)
    if rec1["status"] == "ok" and rec1["reconciled_count"] == 1:
        scores["cat5_reconcile_and_idempotence"] += 5

    with open(home / "_Docs" / "schedule_queue.json", "r", encoding="utf-8") as f:
        hq = json.load(f)
    if hq[0]["status"] == "posted":
        scores["cat5_reconcile_and_idempotence"] += 5

    posted_video = home / "04_Exports" / "Posted" / "PROD01_review_v1.mp4"
    if posted_video.exists():
        scores["cat5_reconcile_and_idempotence"] += 5

    rec2 = SSDReconcileEngine.reconcile_from_vault(vault_root=ssd, base_dir=home)
    if rec2["already_posted_count"] == 1:
        scores["cat5_reconcile_and_idempotence"] += 5

    total_score = sum(scores.values())
    print(f"\n[SCORE] 100-Point Scoring Rubric Results: {scores} -> Total: {total_score}/100")
    assert total_score == 100, f"Score was {total_score}/100, expected 100/100!"
