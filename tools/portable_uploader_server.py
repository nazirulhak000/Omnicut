#!/usr/bin/env python3
"""Portable Uploader Server for OmniCut Pro Studio.

Agent 2: Portable Mini-Server Architect
Zero-dependency, standalone HTTP server running on standard library (Python 3.8+).
Runs directly from External SSD on any laptop, serving only the endpoints needed
by `tiktok_autopost_extension` (Chrome Extension).
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import sys
import threading
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs, unquote

VAULT_ROOT = Path(__file__).resolve().parent.parent

_LOCK = threading.Lock()
_CURRENT_JOB = None


def _load_json(file_path: Path, default=None):
    if not file_path.exists():
        return default if default is not None else []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []


def _save_json_atomic(file_path: Path, data):
    tmp_path = file_path.with_suffix(f".tmp_{uuid.uuid4().hex[:6]}")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp_path.replace(file_path)


class PortableRequestHandler(BaseHTTPRequestHandler):
    """Zero-dependency HTTP Handler emulating OmniCut API for TikTok Chrome Extension."""

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE, PATCH")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Max-Age", "86400")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def _send_json(self, status_code: int, data: any):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _read_body_json(self):
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            return {}
        body_bytes = self.rfile.read(content_len)
        try:
            return json.loads(body_bytes.decode("utf-8"))
        except Exception:
            return {}

    def log_message(self, format, *args):
        # Keep terminal output concise and helpful
        sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]} {args[1]} -> {args[2]}\n")

    def do_GET(self):
        global _CURRENT_JOB
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. Channels (Required by Extension sidepanel initializeChannelSelector)
        if path == "/api/channels":
            channels_file = VAULT_ROOT / "_Docs" / "channels.json"
            channels_doc = _load_json(channels_file, default=None)
            
            if isinstance(channels_doc, dict) and "channels" in channels_doc:
                for ch in channels_doc["channels"]:
                    if "display_name" not in ch and "name" in ch:
                        ch["display_name"] = ch["name"]
                self._send_json(200, channels_doc)
                return
            elif isinstance(channels_doc, list) and channels_doc:
                for ch in channels_doc:
                    if "display_name" not in ch and "name" in ch:
                        ch["display_name"] = ch["name"]
                self._send_json(200, {
                    "channels": channels_doc,
                    "revision": 1,
                    "schema_version": 1,
                    "default_channel_id": "main",
                })
                return
            else:
                self._send_json(200, {
                    "channels": [{
                        "id": "main",
                        "display_name": "Main Channel",
                        "name": "Main Channel",
                        "handle": "@default",
                        "status": "active",
                        "posting_enabled": True,
                        "account_binding": {"status": "verified", "verified_handle": "@default"}
                    }],
                    "revision": 1,
                    "schema_version": 1,
                    "default_channel_id": "main",
                })
                return

        # 2. Schedule Queue (Returns {"items": [...]})
        if path == "/api/schedule-queue":
            queue_file = VAULT_ROOT / "queue.json"
            state_file = VAULT_ROOT / "state.json"
            queue_items = _load_json(queue_file, default=[])
            states = _load_json(state_file, default={})

            formatted_queue = []
            for item in queue_items:
                item_id = item["id"]
                item_state = states.get(item_id, {})
                raw_status = item_state.get("status", item.get("status", "pending"))
                
                # Active queue statuses expected by sidepanel.js:
                # ['planned', 'ready_for_extension', 'awaiting_post', 'failed']
                if raw_status in ("pending", "staged", "queued"):
                    current_status = "ready_for_extension"
                elif raw_status in ("posted", "published"):
                    current_status = "posted"
                else:
                    current_status = raw_status

                video_abs = str(VAULT_ROOT / item["video_rel_path"])
                cover_rel = item.get("cover_rel_path")
                cover_abs = str(VAULT_ROOT / cover_rel) if cover_rel else None
                cover_url = f"/api/media/{cover_rel}" if cover_rel else None

                formatted_queue.append({
                    "id": item_id,
                    "export_id": item.get("export_id") or item_id,
                    "status": current_status,
                    "video_path": video_abs,
                    "cover_path": cover_abs,
                    "cover_url": cover_url,
                    "caption": item.get("caption", ""),
                    "hashtags": item.get("hashtags", ""),
                    "tiktok_product_id": item.get("tiktok_product_id"),
                    "product_name": item.get("product_name"),
                    "channel_id": item.get("channel_id", "main"),
                    "scheduled_at": item.get("scheduled_at"),
                    "created_at": item.get("scheduled_at", datetime.now(timezone.utc).isoformat()),
                })
            self._send_json(200, {"items": formatted_queue, "total": len(formatted_queue)})
            return

        # 3. Exports (Returns array with angle_status: 'rendered', is_latest: True)
        if path == "/api/exports":
            queue_file = VAULT_ROOT / "queue.json"
            state_file = VAULT_ROOT / "state.json"
            queue_items = _load_json(queue_file, default=[])
            states = _load_json(state_file, default={})

            formatted_exports = []
            for item in queue_items:
                item_id = item["id"]
                item_state = states.get(item_id, {})
                raw_status = item_state.get("status", item.get("status", "pending"))
                is_posted = raw_status in ("posted", "published")
                video_abs = str(VAULT_ROOT / item["video_rel_path"])
                cover_rel = item.get("cover_rel_path")
                cover_abs = str(VAULT_ROOT / cover_rel) if cover_rel else None

                formatted_exports.append({
                    "id": item.get("export_id") or item_id,
                    "queue_id": item_id,
                    "path": video_abs,
                    "rel_path": item["video_rel_path"],
                    "cover_path": cover_abs,
                    "status": raw_status,
                    "angle_status": "rendered",
                    "is_latest": True,
                    "is_posted": is_posted,
                    "tiktok_caption": item.get("caption", ""),
                    "tiktok_hashtags": item.get("hashtags", ""),
                    "tiktok_product_id": item.get("tiktok_product_id"),
                    "product_name": item.get("product_name"),
                    "channel_id": item.get("channel_id", "main"),
                })
            self._send_json(200, formatted_exports)
            return

        # 4. TikTok Capabilities
        if path == "/api/tiktok-autopost/capabilities":
            self._send_json(200, {
                "protocol_version": 2,
                "durable_jobs": True,
                "job_scoped_ack": True,
                "account_guard": True,
            })
            return

        # 5. TikTok Pending Job
        if path == "/api/tiktok-autopost/pending":
            with _LOCK:
                if _CURRENT_JOB and _CURRENT_JOB.get("status") in ("prepared", "claimed"):
                    res = {k: v for k, v in _CURRENT_JOB.items() if k != "lease_token"}
                    self._send_json(200, res)
                    return
            self._send_json(404, {"detail": "ยังไม่มีคลิปที่เตรียมไว้ -- เลือกคลิปในแถบข้างก่อน"})
            return

        # 6. TikTok Job status
        if path.startswith("/api/tiktok-autopost/jobs/"):
            job_id = unquote(path.replace("/api/tiktok-autopost/jobs/", ""))
            with _LOCK:
                if _CURRENT_JOB and _CURRENT_JOB.get("job_id") == job_id:
                    res = {k: v for k, v in _CURRENT_JOB.items() if k != "lease_token"}
                    self._send_json(200, res)
                    return
            self._send_json(404, {"detail": f"Job {job_id} not found"})
            return

        # 7. Media Streaming (/api/media/*)
        if path.startswith("/api/media/"):
            rel_media_path = unquote(path.replace("/api/media/", "")).lstrip("/")
            file_path = VAULT_ROOT / rel_media_path

            if not file_path.exists() or not file_path.is_file():
                self._send_json(404, {"detail": "Media file not found"})
                return

            mime_type, _ = mimetypes.guess_type(str(file_path))
            mime_type = mime_type or "application/octet-stream"

            file_size = file_path.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self._send_cors_headers()
            self.end_headers()

            with open(file_path, "rb") as f:
                while chunk := f.read(256 * 1024):
                    self.wfile.write(chunk)
            return

        # Default 404
        self._send_json(404, {"detail": "Endpoint not found"})

    def do_POST(self):
        global _CURRENT_JOB
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body_json()

        # 1. Prepare Job
        if path == "/api/tiktok-autopost/prepare":
            channel_id = self.headers.get("X-OmniCut-Channel", "main")
            raw_video = body.get("video_path", "")
            raw_cover = body.get("cover_path")

            video_file = Path(raw_video)
            if not video_file.is_absolute():
                video_file = VAULT_ROOT / raw_video

            cover_file = None
            if raw_cover:
                cover_file = Path(raw_cover)
                if not cover_file.is_absolute():
                    cover_file = VAULT_ROOT / raw_cover

            job_id = "job_" + uuid.uuid4().hex[:12]
            with _LOCK:
                _CURRENT_JOB = {
                    "job_id": job_id,
                    "channel_id": channel_id,
                    "protocol_version": 2,
                    "revision": 1,
                    "status": "prepared",
                    "video_path": str(video_file),
                    "cover_path": str(cover_file) if cover_file else None,
                    "caption": body.get("caption", ""),
                    "hashtags": body.get("hashtags", ""),
                    "tiktok_product_id": body.get("tiktok_product_id"),
                    "queue_id": body.get("queue_id"),
                    "lease_token": None,
                }
            self._send_json(200, _CURRENT_JOB)
            return

        # 2. Claim Job
        if path == "/api/tiktok-autopost/claim":
            job_id = body.get("job_id")
            lease_owner = body.get("lease_owner", "extension")
            with _LOCK:
                if not _CURRENT_JOB or _CURRENT_JOB.get("job_id") != job_id:
                    self._send_json(404, {"detail": "Job not found"})
                    return
                lease_token = "lease_" + uuid.uuid4().hex[:8]
                _CURRENT_JOB["lease_token"] = lease_token
                _CURRENT_JOB["lease_owner"] = lease_owner
                _CURRENT_JOB["status"] = "claimed"
                response = dict(_CURRENT_JOB)
            self._send_json(200, response)
            return

        # 3. Clear Job
        if path == "/api/tiktok-autopost/clear":
            with _LOCK:
                _CURRENT_JOB = None
            self._send_json(200, {"success": True})
            return

        # 4. Acknowledge / Reconcile Outcome (Called by background.js retryPostingReceipt / savePostingReceipt)
        if path in (
            "/api/tiktok-autopost/ack",
            "/api/tiktok-autopost/reconcile",
            "/api/tiktok-autopost/acknowledge",
            "/api/tiktok-stats/import",
        ):
            channel_id = self.headers.get("X-OmniCut-Channel", "main")
            job_id = body.get("job_id") or (_CURRENT_JOB.get("job_id") if _CURRENT_JOB else None)
            queue_id = body.get("queue_id") or (_CURRENT_JOB.get("queue_id") if _CURRENT_JOB else None)
            proof = body.get("proof") or {}
            post_url = body.get("post_url") or body.get("video_url") or proof.get("notice")
            platform_id = body.get("platform_id") or body.get("item_id") or proof.get("platform_post_id")
            outcome = body.get("outcome", "published")

            # Update state.json and queue.json on SSD
            queue_file = VAULT_ROOT / "queue.json"
            state_file = VAULT_ROOT / "state.json"

            states = _load_json(state_file, default={})
            queue_items = _load_json(queue_file, default=[])

            target_id = queue_id
            if not target_id and _CURRENT_JOB and _CURRENT_JOB.get("queue_id"):
                target_id = _CURRENT_JOB["queue_id"]
            if not target_id and queue_items:
                target_id = queue_items[0]["id"]

            if target_id:
                states[target_id] = {
                    "status": "posted",
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    "post_url": post_url,
                    "post_id": platform_id,
                    "error": None,
                }
                _save_json_atomic(state_file, states)

                for q in queue_items:
                    if q["id"] == target_id:
                        q["status"] = "posted"
                        q["posted_at"] = states[target_id]["uploaded_at"]
                _save_json_atomic(queue_file, queue_items)

            with _LOCK:
                if _CURRENT_JOB and (_CURRENT_JOB.get("job_id") == job_id or not job_id):
                    _CURRENT_JOB["status"] = "published"

            self._send_json(200, {
                "success": True,
                "outcome": outcome,
                "job_id": job_id,
                "channel_id": channel_id,
                "status": "published",
                "queue_id": target_id,
            })
            return

        self._send_json(404, {"detail": "Endpoint not found"})


def run_server(host: str = "127.0.0.1", port: int = 8000):
    server_address = (host, port)
    try:
        httpd = HTTPServer(server_address, PortableRequestHandler)
    except OSError as e:
        print(f"\n❌ ไม่สามารถเปิดพอร์ต {port} ได้ ({e})")
        print("💡 สาเหตุที่พบบ่อย:")
        print("   1. มี OmniCut Pro Studio (run_studio_pc.py) รันอยู่ที่เครื่องหลักแล้ว")
        print("   2. หากรันที่เครื่องหลัก ให้ปิดหน้าต่าง terminal ของ OmniCut ก่อน หรือใช้ Extension โพสต์ตรงกับเครื่องหลักได้เลย")
        print("   3. สคริปต์นี้ออกแบบมาให้รันบน 'เครื่องโน้ตบุ๊กที่คาเฟ่' ผ่าน START_CAFE_UPLOADER.bat\n")
        sys.exit(1)

    print(f"=====================================================")
    print(f"🚀 OmniCut Portable Uploader Server (Port {port})")
    print(f"📁 Serving Vault: {VAULT_ROOT}")
    print(f"🔗 Chrome Extension Target: http://{host}:{port}")
    print(f"=====================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OmniCut Portable Uploader Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    args = parser.parse_args()
    run_server(args.host, args.port)
