"""API Router for on-demand editing proxies.

The timeline plays 540p stand-ins so scrubbing a 4K master stays responsive,
while Render keeps reading the master (scripts/video_editor.py refuses a proxy
outright). This router is the seam between the two.

The contract that makes proxies safe to use is "never block, never lie":

- Asking for a proxy that does not exist yet starts the encode in the
  background and answers immediately with the master. The editor stays usable
  during the encode instead of waiting on ffmpeg.
- The response always names the master too, so the caller can fall back at any
  time, and timing questions (trim, in/out, speed) are answered from the
  master's own duration. A proxy is re-encoded and can differ by a frame, so
  it is pixels for the eye and never a clock.
"""
from __future__ import annotations

import threading
import urllib.parse
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException

from scripts.api_videos import _allowed_media_path
from scripts.config import BASE_DIR, CAPCUT_DRAFT_DIR
from scripts.proxy_manager import (
    ProxyError,
    ensure_proxy,
    get_proxy,
    proxy_path_for,
    scan_proxy_cache,
)

router = APIRouter(prefix="/api/proxy", tags=["editing-proxy"])

# Masters currently being encoded, so a timeline that asks for the same clip
# on every mount does not queue a second ffmpeg for work already in flight.
# Guarded by its own lock because BackgroundTasks may run concurrently.
_IN_FLIGHT: set[str] = set()
_IN_FLIGHT_LOCK = threading.Lock()


def _claim(key: str) -> bool:
    """Take ownership of encoding `key`, or report someone else already has."""
    with _IN_FLIGHT_LOCK:
        if key in _IN_FLIGHT:
            return False
        _IN_FLIGHT.add(key)
        return True


def _release(key: str) -> None:
    with _IN_FLIGHT_LOCK:
        _IN_FLIGHT.discard(key)


def _is_building(key: str) -> bool:
    with _IN_FLIGHT_LOCK:
        return key in _IN_FLIGHT


def _resolve_master(source_path: str) -> Path:
    """
    Resolve a caller-supplied clip path to a real master file.

    Reuses `_allowed_media_path` from api_videos.py rather than writing a
    second containment rule: the set of files a proxy may be built from must
    be exactly the set the media endpoint already serves. Containment is
    re-checked after resolve() so a symlink cannot widen it.
    """
    decoded = urllib.parse.unquote(source_path or "").strip()
    if not decoded:
        raise HTTPException(status_code=400, detail="ต้องระบุไฟล์ต้นฉบับ (source_path)")

    base = BASE_DIR.resolve()
    drafts = CAPCUT_DRAFT_DIR.resolve()
    target = Path(decoded)
    if not target.is_absolute():
        target = base / decoded

    if not _allowed_media_path(target, base, drafts):
        raise HTTPException(status_code=403, detail="ไม่อนุญาตให้เข้าถึงไฟล์นี้")
    try:
        target = target.resolve()
    except (OSError, RuntimeError, ValueError):
        raise HTTPException(status_code=403, detail="ไม่อนุญาตให้เข้าถึงไฟล์นี้") from None
    if not _allowed_media_path(target, base, drafts):
        raise HTTPException(status_code=403, detail="ไม่อนุญาตให้เข้าถึงไฟล์นี้")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์ต้นฉบับ")
    return target


def _relative_media_path(path: Path) -> str:
    """Path as the /api/media endpoint addresses it, or absolute if outside."""
    try:
        return str(path.resolve().relative_to(BASE_DIR.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _build_proxy_task(master_str: str, key: str) -> None:
    """
    Background encode. Swallows failure by design: the master always plays, so
    a proxy that cannot be built degrades performance, not correctness. The
    error is logged rather than raised because nothing is waiting to catch it.
    """
    try:
        ensure_proxy(Path(master_str))
    except ProxyError as exc:
        print(f"   ⚠️ สร้าง Proxy ไม่สำเร็จ ({exc}) — ไทม์ไลน์จะเล่นไฟล์ต้นฉบับแทน")
    except Exception as exc:  # noqa: BLE001 - a background task must not die loudly
        print(f"   ⚠️ สร้าง Proxy ไม่สำเร็จ ({exc}) — ไทม์ไลน์จะเล่นไฟล์ต้นฉบับแทน")
    finally:
        _release(key)


@router.get("/for-clip")
def proxy_for_clip(
    source_path: str,
    background_tasks: BackgroundTasks,
    build: bool = True,
) -> Dict[str, Any]:
    """
    The playback URL for one clip, plus whether it is the proxy or the master.

    `status` is one of:
      - `ready`    — a proxy exists; `url` points at it
      - `building` — an encode is running; `url` is the master for now
      - `master`   — no proxy and none requested (`build=false`)

    The caller re-requests to find out when a `building` proxy became `ready`.
    Polling is deliberate: an encode is short, and a push channel for something
    this minor would be more moving parts than the feature is worth.
    """
    master = _resolve_master(source_path)
    key = str(proxy_path_for(master))

    existing = get_proxy(master)
    master_url = "/api/media/" + urllib.parse.quote(_relative_media_path(master), safe="/")

    if existing:
        return {
            "status": "ready",
            "url": "/api/media/" + urllib.parse.quote(_relative_media_path(existing), safe="/"),
            "master_url": master_url,
            "is_proxy": True,
        }

    if build and not _is_building(key) and _claim(key):
        background_tasks.add_task(_build_proxy_task, str(master), key)

    return {
        "status": "building" if (build and _is_building(key)) else "master",
        "url": master_url,
        "master_url": master_url,
        "is_proxy": False,
    }


@router.get("/status")
def proxy_cache_status() -> Dict[str, Any]:
    """Size and file count of the proxy cache, for the storage panel."""
    summary = scan_proxy_cache()
    return {
        "status": "ok",
        "bytes": summary["bytes"],
        "mb": round(summary["bytes"] / (1024 * 1024), 2),
        "count": summary["count"],
        "path": summary["path"],
        "building": len(_IN_FLIGHT),
    }
