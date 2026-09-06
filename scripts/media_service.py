"""
Media and filesystem services for OmniCut Pro Studio.
Handles video file scanning, media inspection, metadata extraction,
and HTTP range-supported streaming for HTML5 audio/video playback.
"""

import time
import socket
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import Request, HTTPException, Response
from fastapi.responses import StreamingResponse

from scripts.config import BASE_DIR, COVERS_DIR

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".hevc", ".mkv"}

_ip_cache: Dict[str, Any] = {"ip": None, "ts": 0.0}
_IP_TTL = 5.0  # re-check every 5 s so Wi-Fi switches are reflected almost immediately


def get_local_ip(force: bool = False) -> str:
    """Returns the primary local IPv4 address. Re-checked every 5 s (or forced) so
    switching Wi-Fi networks is reflected dynamically without restarting the server."""
    now = time.monotonic()
    if force or _ip_cache["ip"] is None or (now - _ip_cache["ts"]) > _IP_TTL:
        ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.3)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            try:
                ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                pass
        _ip_cache["ip"] = ip
        _ip_cache["ts"] = now
    return _ip_cache["ip"]


def measure_wav_duration(wav_path: Path) -> float:
    """Seconds of audio in a WAV file, 0.0 if it cannot be read."""
    try:
        import wave
        with wave.open(str(wav_path), "rb") as wf:
            return round(wf.getnframes() / float(wf.getframerate()), 2)
    except Exception:
        return 0.0


def get_file_info(file_path: Path) -> Dict[str, Any]:
    stat = file_path.stat()
    rel_path = str(file_path.relative_to(BASE_DIR)).replace("\\", "/")
    webp_path = file_path.with_suffix(".webp")
    thumbnail_url = None
    if webp_path.exists():
        try:
            thumbnail_url = f"/api/media/{str(webp_path.relative_to(BASE_DIR)).replace('\\', '/')}"
        except Exception:
            thumbnail_url = None

    # Check for dedicated 9:16 cover image in 05_Covers_Thumbnails/
    cover_url = None
    cover_file = COVERS_DIR / f"{file_path.stem}_cover.jpg"
    if not cover_file.exists():
        cover_file = COVERS_DIR / f"{file_path.stem}_cover_3x4.jpg"
    if not cover_file.exists():
        cover_file = COVERS_DIR / f"{file_path.stem}.jpg"
    cover_path = None
    if cover_file.exists():
        try:
            cover_url = f"/api/media/{str(cover_file.relative_to(BASE_DIR)).replace('\\', '/')}"
            cover_path = str(cover_file.relative_to(BASE_DIR)).replace('\\', '/')
        except Exception:
            cover_url = None
            cover_path = None

    return {
        "name": file_path.name,
        "path": str(file_path),
        "rel_path": rel_path,
        "thumbnail_url": thumbnail_url,
        "cover_url": cover_url,
        "cover_path": cover_path,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified_time": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": stat.st_mtime
    }


def scan_video_files(*dirs: Path) -> List[Path]:
    """Fast single-pass filesystem scanner for video files across given directories."""
    found = []
    seen = set()
    for d in dirs:
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS:
                resolved = p.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    found.append(p)
    return found


def stream_media_file(file_path: Path, request: Request):
    """Range-supporting file streamer for smooth HTML5 video/audio playback."""
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    content_type = "video/mp4"
    ext = file_path.suffix.lower()
    if ext in [".mov"]:
        content_type = "video/quicktime"
    elif ext in [".mp3"]:
        content_type = "audio/mpeg"
    elif ext in [".wav"]:
        content_type = "audio/wav"
    elif ext in [".jpg", ".jpeg"]:
        content_type = "image/jpeg"
    elif ext in [".png"]:
        content_type = "image/png"
    elif ext in [".webp"]:
        content_type = "image/webp"
    elif ext in [".ttf"]:
        content_type = "font/ttf"
    elif ext in [".otf"]:
        content_type = "font/otf"

    STREAM_CHUNK_SIZE = 256 * 1024  # 256KB buffer
    INLINE_MAX_BYTES = 32 * 1024 * 1024

    if range_header:
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
        end = min(end, file_size - 1)
        chunk_size = (end - start) + 1

        if file_size <= INLINE_MAX_BYTES:
            with open(file_path, "rb") as f:
                f.seek(start)
                payload = f.read(chunk_size)
            return Response(
                content=payload,
                status_code=206,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(len(payload)),
                    "Content-Type": content_type,
                },
            )

        def iterfile():
            with open(file_path, "rb") as f:
                f.seek(start)
                bytes_left = chunk_size
                while bytes_left > 0:
                    read_len = min(STREAM_CHUNK_SIZE, bytes_left)
                    data = f.read(read_len)
                    if not data:
                        break
                    bytes_left -= len(data)
                    yield data

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Content-Type": content_type,
        }
        return StreamingResponse(iterfile(), status_code=206, headers=headers)
    else:
        if file_size <= INLINE_MAX_BYTES:
            return Response(
                content=file_path.read_bytes(),
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(file_size),
                    "Content-Type": content_type,
                },
            )

        def iterfile():
            with open(file_path, "rb") as f:
                while chunk := f.read(STREAM_CHUNK_SIZE):
                    yield chunk

        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": content_type,
        }
        return StreamingResponse(iterfile(), headers=headers)
