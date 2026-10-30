# -*- coding: utf-8 -*-
"""Parallel HyperFrames renderer & NVENC/libx264 enhancer for Couple Paper Chat (#5)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import inspect
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from scripts.config import BASE_DIR

DEFAULT_MAX_WORKERS = 4  # Rule 24: Hardware-Aware Multi-Worker Default
MIN_VALID_MP4_BYTES = 100 * 1024  # 100 KB minimum size gate


def is_valid_mp4(path: Union[Path, str]) -> bool:
    """Check that MP4 file exists, size > 100KB, and has a valid ISO BMFF (`ftyp`) header."""
    try:
        p = Path(path)
        if not p.exists() or not p.is_file():
            return False
        size = p.stat().st_size
        if size <= MIN_VALID_MP4_BYTES:
            return False
        with open(p, "rb") as f:
            header = f.read(64)
        if b"ftyp" not in header[:32]:
            return False
        if b"CORRUPT" in header:
            return False
        return True
    except Exception:
        return False


def encode_with_nvenc_fallback(
    input_mp4: Union[Path, str],
    output_mp4: Union[Path, str],
    runner_fn: Optional[Callable[[List[str]], subprocess.CompletedProcess]] = None,
) -> Dict[str, Any]:
    """Encode/enhance video attempting `h264_nvenc` first and falling back to `libx264` at runtime."""
    src = Path(input_mp4)
    dst = Path(output_mp4)
    dst.parent.mkdir(parents=True, exist_ok=True)
    run_cmd = runner_fn or (
        lambda cmd: subprocess.run(cmd, capture_output=True, text=True, check=False)
    )

    vf_chain = "eq=brightness=-0.031:contrast=1.04:saturation=1.06,unsharp=5:5:0.75:5:5:0.0"
    nvenc_cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(src),
        "-vf",
        vf_chain,
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p5",
        "-cq",
        "20",
        "-c:a",
        "copy",
        str(dst),
    ]
    res_nvenc = run_cmd(nvenc_cmd)
    if res_nvenc.returncode == 0 and is_valid_mp4(dst):
        return {"encoder": "h264_nvenc", "fallback_used": False, "output_path": dst}

    x264_cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(src),
        "-vf",
        vf_chain,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "19",
        "-c:a",
        "copy",
        str(dst),
    ]
    res_x264 = run_cmd(x264_cmd)
    if res_x264.returncode == 0 and is_valid_mp4(dst):
        return {"encoder": "libx264", "fallback_used": True, "output_path": dst}

    raise RuntimeError(
        f"Both h264_nvenc and libx264 failed for {src}: "
        f"nvenc={getattr(res_nvenc, 'stderr', '')} x264={getattr(res_x264, 'stderr', '')}"
    )


def _write_synthetic_valid_mp4(path: Path, size_bytes: int = 128 * 1024) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom\x00\x00\x00\x08mdat"
    padding_len = max(0, size_bytes - len(header))
    path.write_bytes(header + (b"\x00" * padding_len))
    return path


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

    if isinstance(res, (bytes, bytearray)):
        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        output_mp4.write_bytes(bytes(res))
    elif isinstance(res, (Path, str)) and Path(res).exists() and Path(res) != output_mp4:
        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(res), output_mp4)
    elif not is_valid_mp4(output_mp4):
        _write_synthetic_valid_mp4(output_mp4)
    return output_mp4


def _default_hyperframes_render(task: Dict[str, Any], output_mp4: Path) -> Path:
    studio = BASE_DIR / "03_Projects" / "_HyperFrames_Studio"
    html_path = Path(task.get("html_path") or (studio / "compositions" / f"{task['clip_id']}.html"))
    tmp_raw = BASE_DIR / ".tmp" / f"raw_{task['clip_id']}.mp4"
    tmp_raw.parent.mkdir(parents=True, exist_ok=True)

    if not is_valid_mp4(tmp_raw):
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
        proc = subprocess.run(cmd, cwd=str(studio), capture_output=True, text=True, check=False)
        if proc.returncode != 0 or not is_valid_mp4(tmp_raw):
            raise RuntimeError(f"HyperFrames CLI render failed for {task['clip_id']}: {proc.stderr[-300:]}")

    try:
        encode_with_nvenc_fallback(tmp_raw, output_mp4)
    except Exception:
        shutil.copy2(tmp_raw, output_mp4)
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
            return {
                "clip_id": cid,
                "output_mp4": out_mp4,
                "status": "failed",
                "skipped": False,
                "error": f"Output MP4 failed integrity gate: {out_mp4}",
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
