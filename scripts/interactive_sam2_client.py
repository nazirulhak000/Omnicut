"""Client and lifecycle manager for the interactive SAM 2 daemon.

FastAPI calls this to ensure the interactive daemon is alive and to send single-frame
segmentation queries for real-time subject lift previews (<50ms).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from scripts.cutout_runtime import sam2_python

logger = logging.getLogger("omnicut.interactive_sam2")

DAEMON_PORT = 8008
DAEMON_HOST = "127.0.0.1"
DAEMON_URL = f"http://{DAEMON_HOST}:{DAEMON_PORT}"
_DAEMON_PROC: subprocess.Popen | None = None


def is_daemon_alive() -> bool:
    try:
        req = urllib.request.Request(f"{DAEMON_URL}/health", headers={"User-Agent": "OmniCut/1.0"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("ok") is True
    except Exception:
        return False


def ensure_daemon() -> bool:
    """Ensure the interactive SAM 2 daemon is running on GPU."""
    global _DAEMON_PROC
    if is_daemon_alive():
        return True

    interpreter = sam2_python()
    if not interpreter.is_file():
        logger.warning(f"SAM 2 interpreter not found at {interpreter}")
        return False

    script_path = Path(__file__).resolve().parent / "interactive_sam2_daemon.py"
    cmd = [
        str(interpreter),
        str(script_path),
        "--port", str(DAEMON_PORT),
        "--host", DAEMON_HOST,
    ]

    try:
        creationflags = 0
        if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            creationflags = subprocess.CREATE_NO_WINDOW
        _DAEMON_PROC = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )

        # Wait up to 10 seconds for daemon to become ready
        for _ in range(50):
            time.sleep(0.2)
            if is_daemon_alive():
                logger.info(f"Interactive SAM 2 daemon started on {DAEMON_URL}")
                return True
        logger.error("Timed out waiting for interactive SAM 2 daemon to start")
        return False
    except Exception as e:
        logger.error(f"Failed to start interactive SAM 2 daemon: {e}")
        return False


def post_daemon(endpoint: str, payload: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
    if not ensure_daemon():
        raise RuntimeError("Interactive SAM 2 daemon is unavailable")

    url = f"{DAEMON_URL}/{endpoint.lstrip('/')}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "OmniCut/1.0"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def segment_frame_interactive(
    source_path: str,
    timestamp: float,
    points: list[dict[str, Any]],
    width: int = 540,
    height: int = 960,
) -> dict[str, Any]:
    """Load frame (if changed) and predict segmentation contour in one high-level call."""
    # 1. Set frame
    frame_resp = post_daemon("set_frame", {
        "source": source_path,
        "timestamp": timestamp,
        "width": width,
        "height": height,
    })
    if not frame_resp.get("ok"):
        raise RuntimeError(frame_resp.get("error", "Failed to set frame"))

    # 2. Predict mask
    predict_resp = post_daemon("predict", {
        "points": points,
    })
    if not predict_resp.get("ok"):
        raise RuntimeError(predict_resp.get("error", "Failed to predict mask"))

    return {
        "ok": True,
        "contours": predict_resp.get("contours", []),
        "bbox": predict_resp.get("bbox"),
        "score": predict_resp.get("score"),
        "predict_ms": predict_resp.get("predict_ms", 0.0),
        "load_ms": frame_resp.get("load_ms", 0.0),
    }
