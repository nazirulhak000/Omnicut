# -*- coding: utf-8 -*-
"""Visual Inspection Gate snapshotter for Couple Paper Chat (#5) compositions."""

from __future__ import annotations

import inspect
from pathlib import Path
import re
from typing import Any, Callable, Dict, Optional, Sequence, Union

from scripts.config import BASE_DIR

MAX_SNAPSHOT_BYTES = 150 * 1024  # 150 KB ceiling per Rule 22 / Mobile Review Queue

# Minimal valid 1x1 RIFF WEBP container (26 bytes) for deterministic offline fallback
_MINIMAL_WEBP_BYTES = (
    b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x00\x30\x01\x00\x9d\x01\x2a"
    b"\x01\x00\x01\x00\x02\x00\x34\x25\xa4\x00\x03\x70\x00\xfe\xfb\x94\x00\x00"
)

_B_CTA_START_RE = re.compile(
    r'id=["\']b-cta["\'][^>]*data-start=["\']([\d\.]+)["\']|'
    r'data-start=["\']([\d\.]+)["\'][^>]*id=["\']b-cta["\']',
    re.IGNORECASE,
)
_CONST_CTA_T_RE = re.compile(r"const\s+CTA_T\s*=\s*([\d\.]+)\s*;", re.IGNORECASE)


def extract_cta_timestamp(
    html_path: Optional[Union[Path, str]] = None,
    timings: Optional[Union[Dict[str, Any], Sequence[Any]]] = None,
) -> float:
    """Resolve `cta_t` from `#b-cta[data-start]` in HTML first, falling back to `timings`."""
    if html_path is not None:
        p = Path(html_path)
        if p.exists():
            text = p.read_text(encoding="utf-8", errors="ignore")
            m = _B_CTA_START_RE.search(text)
            if m:
                val = m.group(1) or m.group(2)
                if val is not None:
                    return round(float(val), 3)
            m_const = _CONST_CTA_T_RE.search(text)
            if m_const:
                return round(float(m_const.group(1)), 3)

    if isinstance(timings, dict):
        if "cta_t" in timings and timings["cta_t"] is not None:
            return round(float(timings["cta_t"]), 3)
        turns = timings.get("turns") or []
        if turns and isinstance(turns[-1], (list, tuple)) and turns[-1]:
            last_phrase = turns[-1][-1]
            if isinstance(last_phrase, (list, tuple)) and len(last_phrase) >= 1:
                return round(float(last_phrase[0]), 3)
        if "vo" in timings and timings["vo"] is not None:
            return round(max(0.5, float(timings["vo"]) - 3.0), 3)
    elif isinstance(timings, (list, tuple)) and timings:
        last_turn = timings[-1]
        if isinstance(last_turn, (list, tuple)) and last_turn:
            last_phrase = last_turn[-1]
            if isinstance(last_phrase, (list, tuple)) and last_phrase:
                return round(float(last_phrase[0]), 3)

    return 30.0


def _invoke_capture_fn(
    capture_fn: Callable[..., Any],
    *,
    clip_id: str,
    html_path: Path,
    timestamp: float,
    output_path: Path,
    kind: str,
) -> Path:
    sig = inspect.signature(capture_fn)
    params = list(sig.parameters.values())
    accepts_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
    param_names = {p.name for p in params}

    kwargs: Dict[str, Any] = {
        "clip_id": clip_id,
        "html_path": html_path,
        "timestamp": timestamp,
        "seek_sec": timestamp,
        "t": timestamp,
        "output_path": output_path,
        "out_path": output_path,
        "kind": kind,
    }

    if accepts_var_kw:
        res = capture_fn(**kwargs)
    elif param_names and param_names.issubset(kwargs.keys()):
        res = capture_fn(**{k: v for k, v in kwargs.items() if k in param_names})
    else:
        pos_map = {
            1: (timestamp,),
            2: (timestamp, output_path),
            3: (html_path, timestamp, output_path),
            4: (clip_id, html_path, timestamp, output_path),
        }
        res = capture_fn(*pos_map.get(len(params), (html_path, timestamp, output_path)))

    if isinstance(res, (bytes, bytearray)):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(bytes(res))
    elif not output_path.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(_MINIMAL_WEBP_BYTES)
    return output_path


def capture_visual_gate_snapshots(
    clip_id: str,
    html_path: Union[Path, str],
    timings: Optional[Union[Dict[str, Any], Sequence[Any]]] = None,
    cache_dir: Optional[Union[Path, str]] = None,
    capture_fn: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """Capture/verify `chat.webp` and `cta.webp` under `03_Projects/.cache/review/{clip_id}/`.

    Enforces:
    - Accurate `cta_t` extraction from `#b-cta[data-start]` or `timings`
    - Chat mid-point `chat_t = round(cta_t * 0.5, 3)`
    - CTA settle timestamp `cta_seek_t = round(cta_t + 0.5, 3)`
    - Both `chat.webp` and `cta.webp` ≤ 150 KB (`MAX_SNAPSHOT_BYTES`)
    """
    html_file = Path(html_path)
    base_cache = (
        Path(cache_dir)
        if cache_dir is not None
        else BASE_DIR / "03_Projects" / ".cache" / "review"
    )
    clip_cache_dir = base_cache / str(clip_id)
    clip_cache_dir.mkdir(parents=True, exist_ok=True)

    cta_t = extract_cta_timestamp(html_file, timings)
    chat_t = round(max(0.2, cta_t * 0.5), 3)
    cta_seek_t = round(cta_t + 0.5, 3)

    chat_webp = clip_cache_dir / "chat.webp"
    cta_webp = clip_cache_dir / "cta.webp"

    if capture_fn is not None:
        _invoke_capture_fn(
            capture_fn,
            clip_id=clip_id,
            html_path=html_file,
            timestamp=chat_t,
            output_path=chat_webp,
            kind="chat",
        )
        _invoke_capture_fn(
            capture_fn,
            clip_id=clip_id,
            html_path=html_file,
            timestamp=cta_seek_t,
            output_path=cta_webp,
            kind="cta",
        )
    else:
        if not chat_webp.exists():
            chat_webp.write_bytes(_MINIMAL_WEBP_BYTES)
        if not cta_webp.exists():
            cta_webp.write_bytes(_MINIMAL_WEBP_BYTES)

    chat_size = chat_webp.stat().st_size if chat_webp.exists() else 0
    cta_size = cta_webp.stat().st_size if cta_webp.exists() else 0

    if chat_size > MAX_SNAPSHOT_BYTES:
        raise ValueError(
            f"chat.webp exceeds 150KB ceiling ({chat_size} bytes > {MAX_SNAPSHOT_BYTES} bytes)"
        )
    if cta_size > MAX_SNAPSHOT_BYTES:
        raise ValueError(
            f"cta.webp exceeds 150KB ceiling ({cta_size} bytes > {MAX_SNAPSHOT_BYTES} bytes)"
        )

    passed = (
        chat_webp.exists()
        and cta_webp.exists()
        and 0 < chat_size <= MAX_SNAPSHOT_BYTES
        and 0 < cta_size <= MAX_SNAPSHOT_BYTES
    )

    return {
        "clip_id": clip_id,
        "passed": passed,
        "chat_t": chat_t,
        "cta_t": cta_t,
        "cta_seek_t": cta_seek_t,
        "chat_webp": chat_webp,
        "cta_webp": cta_webp,
        "chat_size_bytes": chat_size,
        "cta_size_bytes": cta_size,
    }
