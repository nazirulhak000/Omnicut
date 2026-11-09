# -*- coding: utf-8 -*-
"""Parallel HyperFrames renderer & NVENC/libx264 enhancer for Couple Paper Chat (#5)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import inspect
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from scripts import media_validation
from scripts.config import BASE_DIR

DEFAULT_MAX_WORKERS = 4  # Rule 24: Hardware-Aware Multi-Worker Default
MIN_VALID_MP4_BYTES = media_validation.MIN_VALID_MP4_BYTES
HF_RENDER_TIMEOUT_SEC = 1800  # one 60s clip renders in ~1 min; 30 min = genuinely hung


def is_valid_mp4(path: Union[Path, str]) -> bool:
    """Central integrity gate (ffprobe streams + 1080x1920 + 30fps + tail decode)."""
    return media_validation.is_valid_mp4(path)


def encode_with_nvenc_fallback(
    input_mp4: Union[Path, str],
    output_mp4: Union[Path, str],
    runner_fn: Optional[Callable[[List[str]], subprocess.CompletedProcess]] = None,
) -> Dict[str, Any]:
    """Encode/enhance video attempting `h264_nvenc` first and falling back to `libx264` at runtime.

    Writes ``<stem>.partial.mp4``, validates it with the central gate and its
    duration (within 0.1s of the source) and only then ``os.replace``-s it to
    ``output_mp4``. Raises RuntimeError (Thai) when neither encoder produces a
    valid file; ``output_mp4`` is never left half-written.
    """
    src = Path(input_mp4)
    dst = Path(output_mp4)
    dst.parent.mkdir(parents=True, exist_ok=True)
    partial = media_validation.partial_path_for(dst)
    src_duration = media_validation.probe_duration(src)
    timeout = media_validation.encode_timeout_for(src_duration)

    def _default_run(cmd: List[str]) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", check=False, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(cmd, returncode=-1, stdout="",
                                               stderr=f"timeout after {exc.timeout}s")

    run_cmd = runner_fn or _default_run

    vf_chain = "eq=brightness=-0.031:contrast=1.04:saturation=1.06,unsharp=5:5:0.75:5:5:0.0"
    codecs = {
        "h264_nvenc": ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "20"],
        "libx264": ["-c:v", "libx264", "-preset", "fast", "-crf", "19"],
    }
    errors: Dict[str, str] = {}
    for encoder in ("h264_nvenc", "libx264"):
        cmd = [
            "ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf_chain,
            *codecs[encoder], "-c:a", "copy", "-movflags", "+faststart", str(partial),
        ]
        try:
            with media_validation.nvenc_session(enabled=encoder == "h264_nvenc"):
                res = run_cmd(cmd)
            if res.returncode != 0:
                errors[encoder] = f"exit {res.returncode}: {(getattr(res, 'stderr', '') or '')[-300:]}"
                continue
            check = media_validation.validate_mp4(partial, use_cache=False)
            if not check.ok:
                errors[encoder] = check.reason
                continue
            out_duration = check.details.get("duration")
            if src_duration and out_duration and abs(out_duration - src_duration) > 0.1:
                errors[encoder] = f"ความยาวไม่ตรงต้นฉบับ ({out_duration:.2f}s vs {src_duration:.2f}s)"
                continue
            os.replace(partial, dst)
            return {"encoder": encoder, "fallback_used": encoder != "h264_nvenc", "output_path": dst}
        finally:
            media_validation.discard_partial(partial)

    raise RuntimeError(
        f"เข้ารหัสวิดีโอไม่สำเร็จทั้ง h264_nvenc และ libx264 ({src.name}): "
        f"nvenc={errors.get('h264_nvenc', '')} | x264={errors.get('libx264', '')}"
    )


def _invoke_render_fn(
    render_fn: Callable[..., Any],
    task: Dict[str, Any],
    output_mp4: Path,
) -> Path:
    sig = inspect.signature(render_fn)
    params = list(sig.parameters.values())
    accepts_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
    param_names = {p.name for p in params}

    kwargs = {
        **task,
        "task": task,
        "output_mp4": output_mp4,
        "output_path": output_mp4,
        "mp4_path": output_mp4,
    }
    if accepts_var_kw:
        res = render_fn(**kwargs)
    elif param_names and param_names.issubset(kwargs.keys()):
        res = render_fn(**{k: v for k, v in kwargs.items() if k in param_names})
    else:
        if len(params) == 1:
            res = render_fn(task)
        elif len(params) == 2:
            res = render_fn(task, output_mp4)
        else:
            res = render_fn(task.get("clip_id"), task.get("html_path"), output_mp4)

    # Whatever the render function produced lands under a .partial name first
    # and only reaches ``output_mp4`` after the central gate passes. A render
    # that produced nothing is a failure -- never fabricate a placeholder MP4.
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    partial = media_validation.partial_path_for(output_mp4)
    if isinstance(res, (bytes, bytearray)):
        partial.write_bytes(bytes(res))
    elif isinstance(res, (Path, str)) and Path(res).is_file() and Path(res).resolve() != output_mp4.resolve():
        partial.write_bytes(Path(res).read_bytes())
    elif output_mp4.is_file():
        return output_mp4  # render_fn wrote the target itself; the worker gate validates it
    else:
        raise RuntimeError(f"ฟังก์ชันเรนเดอร์ไม่ได้สร้างไฟล์วิดีโอ: {output_mp4.name}")
    media_validation.finalize_partial(partial, output_mp4)
    return output_mp4


def _default_hyperframes_render(task: Dict[str, Any], output_mp4: Path) -> Path:
    studio = BASE_DIR / "03_Projects" / "_HyperFrames_Studio"
    html_path = Path(task.get("html_path") or (studio / "compositions" / f"{task['clip_id']}.html"))
    # Unique raw path per render: two workers on the same clip id never share
    # (or delete) each other's intermediate file.
    tmp_raw = BASE_DIR / ".tmp" / f"raw_{task['clip_id']}_{uuid.uuid4().hex[:8]}.mp4"
    tmp_raw.parent.mkdir(parents=True, exist_ok=True)
    media_validation.require_disk_space(output_mp4.parent)

    try:
        npx_bin = "npx.cmd" if sys.platform == "win32" else "npx"
        cmd = [
            npx_bin,
            "--yes",
            "hyperframes@0.8.149",
            "render",
            ".",
            "-c",
            f"compositions/{html_path.name}",
            "--gpu",
            "--browser-gpu",
            "-o",
            str(tmp_raw),
        ]
        try:
            proc = subprocess.run(cmd, cwd=str(studio), capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", check=False, timeout=HF_RENDER_TIMEOUT_SEC)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"HyperFrames เรนเดอร์ {task['clip_id']} ค้างเกิน {HF_RENDER_TIMEOUT_SEC} วินาที — ยกเลิกคลิปนี้"
            ) from exc
        if proc.returncode != 0 or not is_valid_mp4(tmp_raw):
            raise RuntimeError(
                f"HyperFrames เรนเดอร์ {task['clip_id']} ไม่สำเร็จ (exit {proc.returncode}): {(proc.stderr or '')[-300:]}"
            )
        # Enhancer failure fails the clip: never ship the raw, unenhanced MP4.
        encode_with_nvenc_fallback(tmp_raw, output_mp4)
    finally:
        tmp_raw.unlink(missing_ok=True)
    return output_mp4


def render_clip_parallel(
    clip_tasks: Sequence[Dict[str, Any]],
    max_workers: int = DEFAULT_MAX_WORKERS,
    render_fn: Optional[Callable[..., Any]] = None,
    force: bool = False,
    date_str: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Render Couple Paper Chat clips in parallel with hardware-aware default `max_workers=4`.

    Features:
    - Instant Resume Gate: skips any task whose target `output_mp4` already passes `is_valid_mp4`.
    - Pins `date_str` once per batch so midnight rollover never produces duplicate exports.
    - Preserves task ordering in the returned results list.
    """
    if max_workers < 1:
        raise ValueError("max_workers must be >= 1")

    pinned_date = date_str or datetime.datetime.now().strftime("%Y%m%d")
    normalized_tasks: List[Dict[str, Any]] = []
    for idx, raw_t in enumerate(clip_tasks):
        t = dict(raw_t)
        cid = str(t.get("clip_id") or t.get("stem") or f"clip_{idx + 1:02d}")
        t["clip_id"] = cid
        if "output_mp4" in t and t["output_mp4"] is not None:
            out_mp4 = Path(t["output_mp4"])
        elif "mp4_path" in t and t["mp4_path"] is not None:
            out_mp4 = Path(t["mp4_path"])
        else:
            exports_dir = Path(t.get("exports_dir") or (BASE_DIR / "04_Exports" / "Ready_to_post"))
            out_mp4 = exports_dir / f"{pinned_date}_{cid}_v1.mp4"
        t["output_mp4"] = out_mp4
        t["date_str"] = pinned_date
        normalized_tasks.append(t)

    def _worker(task: Dict[str, Any]) -> Dict[str, Any]:
        t0 = time.time()
        cid = task["clip_id"]
        out_mp4: Path = task["output_mp4"]

        if not force and is_valid_mp4(out_mp4):
            return {
                "clip_id": cid,
                "output_mp4": out_mp4,
                "status": "resumed",
                "skipped": True,
                "elapsed_sec": round(time.time() - t0, 3),
                "date_str": pinned_date,
            }

        if render_fn is not None:
            _invoke_render_fn(render_fn, task, out_mp4)
        else:
            _default_hyperframes_render(task, out_mp4)

        if not is_valid_mp4(out_mp4):
            # An invalid file must not stay under the export name where the
            # resume gate, gallery or autopost could pick it up.
            media_validation.discard_partial(out_mp4)
            return {
                "clip_id": cid,
                "output_mp4": out_mp4,
                "status": "failed",
                "skipped": False,
                "error": f"ไฟล์ MP4 ไม่ผ่านการตรวจความสมบูรณ์ (ffprobe/สเปก/ถอดรหัสท้ายไฟล์): {out_mp4}",
                "elapsed_sec": round(time.time() - t0, 3),
                "date_str": pinned_date,
            }

        return {
            "clip_id": cid,
            "output_mp4": out_mp4,
            "status": "rendered",
            "skipped": False,
            "elapsed_sec": round(time.time() - t0, 3),
            "date_str": pinned_date,
        }

    results_by_index: Dict[int, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        fut_to_idx = {
            pool.submit(_worker, task): i for i, task in enumerate(normalized_tasks)
        }
        for fut in as_completed(fut_to_idx):
            i = fut_to_idx[fut]
            try:
                results_by_index[i] = fut.result()
            except Exception as exc:
                results_by_index[i] = {
                    "clip_id": normalized_tasks[i]["clip_id"],
                    "output_mp4": normalized_tasks[i]["output_mp4"],
                    "status": "failed",
                    "skipped": False,
                    "error": str(exc),
                    "date_str": pinned_date,
                }

    return [results_by_index[i] for i in range(len(normalized_tasks))]
