"""SAM 2 GPU Video Isolation Worker.

Runs in tools/cutout_runtime/.venv using CUDA to stream video frames through
Meta's SAM 2.1 VideoPredictor into a VP9 transparent video artifact (cutout.webm).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil

os.environ["TQDM_DISABLE"] = "1"
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# Direct execution uses the isolated GPU venv, with scripts/ as sys.path[0].
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.cutout_runtime import MODEL_CONFIGS, cutout_frame_filter, frame_in_intervals, resolve_checkpoint, sam2_input_memory_bytes

import numpy as np
from PIL import Image
try:
    import torch
except ImportError:
    torch = None

VIDEO_NAME = "cutout.webm"
PREVIEW_NAME = "preview.webm"


def _verify_video(path: Path, *, width: int, height: int, frame_count: int) -> None:
    """Verify VP9 video decodes valid RGBA frames with transparency and opacity."""
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-c:v", "libvpx-vp9",
        "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgba", "pipe:1"
    ]
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          stdin=subprocess.DEVNULL) as proc:
        assert proc.stdout is not None
        bytes_per_frame = width * height * 4
        decoded = 0
        saw_transparency = saw_opaque = False
        while True:
            frame = proc.stdout.read(bytes_per_frame)
            if not frame:
                break
            if len(frame) != bytes_per_frame:
                proc.kill()
                raise RuntimeError("cutout video has truncated decoded frame")
            decoded += 1
            alpha = frame[3::4]
            saw_transparency |= min(alpha) < 32
            saw_opaque |= max(alpha) > 223
        stderr = proc.stderr.read(4096) if proc.stderr else b""
        if proc.wait() != 0 or decoded != frame_count or not saw_transparency or not saw_opaque:
            raise RuntimeError(f"cutout video verification failed: {decoded}/{frame_count} frames, {stderr.decode(errors='replace')[:300]}")


def build_alpha_preview(master: Path, *, width: int, height: int, frame_count: int,
                        fps: float, max_width: int = 540, max_height: int = 960) -> dict[str, Any] | None:
    """Derive scaled preview proxy (540x960) for Canvas 2D player."""
    scale = min(1.0, max_width / width, max_height / height)
    if scale >= 1.0:
        return None
    preview_width = max(2, int(width * scale) // 2 * 2)
    preview_height = max(2, int(height * scale) // 2 * 2)
    preview = master.with_name(PREVIEW_NAME)
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-c:v", "libvpx-vp9", "-i", str(master), "-an",
        "-vf", f"scale={preview_width}:{preview_height}:flags=lanczos",
        "-fps_mode", "passthrough", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
        "-auto-alt-ref", "0", "-deadline", "good", "-cpu-used", "5",
        "-g", str(max(1, round(fps / 2))), "-crf", "32", "-b:v", "0", str(preview)
    ]
    with tempfile.TemporaryFile() as log:
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=log, timeout=600)
        if result.returncode:
            log.seek(0)
            raise RuntimeError(f"สร้าง Cutout Preview ไม่สำเร็จ: {log.read(2048).decode(errors='replace')}")

    _verify_video(preview, width=preview_width, height=preview_height, frame_count=frame_count)
    with preview.open("rb") as handle:
        checksum = hashlib.sha256(handle.read()).hexdigest()
    return {
        "video_file": PREVIEW_NAME,
        "codec": "vp9-alpha",
        "width": preview_width,
        "height": preview_height,
        "frame_count": frame_count,
        "sha256": checksum,
        "size_bytes": preview.stat().st_size,
        "frame_mapping": "identity",
        "derived_from": VIDEO_NAME
    }


def process_video_sam2(
    source: Path,
    output_dir: Path,
    *,
    start: float = 0.0,
    duration: float | None = None,
    fps: float = 30.0,
    width: int = 1080,
    height: int = 1920,
    model: str = "sam2.1_hiera_tiny",
    checkpoint: Path | None = None,
    prompts: list[dict] | None = None,
    crf: int = 24,
    active_intervals: list[tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Run SAM 2 video predictor on GPU and stream to cutout.webm."""
    from sam2.build_sam import build_sam2_video_predictor

    model = model or "sam2.1_hiera_tiny"
    resolved_checkpoint = resolve_checkpoint(model, checkpoint)
    config_file = MODEL_CONFIGS[model]
    if torch is None or not torch.cuda.is_available():
        raise RuntimeError("SAM2 requires a CUDA GPU in the selected Cutout runtime")
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_frames_dir = Path(tempfile.mkdtemp(prefix="sam2_frames_", dir=output_dir))
    started_at = time.perf_counter()
    torch.cuda.reset_peak_memory_stats()
    isolated_frame_count = 0

    try:
        # Extract source frames as temporary JPEGs for SAM 2
        decode_cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
            "-ss", str(start),
        ]
        if duration is not None:
            decode_cmd.extend(["-t", str(duration)])
        decode_cmd.extend([
            "-i", str(source),
            "-vf", f"fps={fps},{cutout_frame_filter(width, height)}",
            "-q:v", "2",
            str(temp_frames_dir / "%05d.jpg")
        ])

        subprocess.run(decode_cmd, check=True)
        frame_paths = sorted(temp_frames_dir.glob("*.jpg"), key=lambda p: int(p.stem))
        total_frames = len(frame_paths)
        if total_frames == 0:
            shutil.rmtree(temp_frames_dir, ignore_errors=True)
            raise RuntimeError("No frames extracted from source video")
        # Also guard direct /process requests, which need not call preflight.
        import psutil
        required_memory_bytes = sam2_input_memory_bytes(total_frames)
        available_memory_bytes = psutil.virtual_memory().available
        if available_memory_bytes < required_memory_bytes:
            raise RuntimeError("RAM ว่างไม่พอสำหรับ SAM2 กรุณาตัดช่วง source ให้สั้นลง "
                               f"(ต้องการประมาณ {required_memory_bytes / 1024**3:.2f} GiB)")

        # Default prompt: Center point if none supplied
        if not prompts:
            prompts = [{
                "object_id": 1,
                "points": [[0.5, 0.5]],
                "labels": [1]
            }]

        # Initialize SAM 2 Predictor on CUDA
        predictor = build_sam2_video_predictor(
            config_file,
            str(resolved_checkpoint),
            device="cuda",
            apply_postprocessing=False
        )

        out_master = output_dir / VIDEO_NAME
        encode_cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{width}x{height}",
            "-r", str(fps), "-i", "pipe:0",
            "-an", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
            "-auto-alt-ref", "0", "-deadline", "good", "-cpu-used", "2",
            "-g", str(max(1, round(fps))), "-crf", str(crf), "-b:v", "0",
            str(out_master)
        ]

        with tempfile.TemporaryFile() as encode_log:
            encode_proc = subprocess.Popen(encode_cmd, stdin=subprocess.PIPE, stderr=encode_log)
            assert encode_proc.stdin is not None

            try:
                with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
                    # SAM2 eagerly loads 1024² RGB float32 frames. Keep them
                    # on host RAM so a long source window does not consume
                    # ~12 MiB/frame of the GPU's finite VRAM.
                    state = predictor.init_state(str(temp_frames_dir), offload_video_to_cpu=True, offload_state_to_cpu=False)
                    for p in prompts:
                        pts = np.array(p["points"], dtype=np.float32) * [width, height]
                        predictor.add_new_points_or_box(
                            state,
                            frame_idx=int(p.get("frame", 0)),
                            obj_id=p["object_id"],
                            points=pts,
                            labels=np.array(p["labels"], dtype=np.int32)
                        )

                    for index, object_ids, logits in predictor.propagate_in_video(state):
                        # Track the full window to preserve temporal memory;
                        # expose alpha only in the requested source intervals.
                        if frame_in_intervals(index, start, fps, active_intervals):
                            alpha = (logits > 0).any(dim=0).squeeze().cpu().numpy().astype(np.uint8) * 255
                            isolated_frame_count += 1
                        else:
                            alpha = np.zeros((height, width), dtype=np.uint8)
                        with Image.open(frame_paths[index]) as img:
                            rgba = img.convert("RGBA")
                            # Put alpha channel into image
                            rgba.putalpha(Image.fromarray(alpha))
                            encode_proc.stdin.write(rgba.tobytes())

                        progress_val = (index + 1) / total_frames
                        if (index + 1) % 5 == 0 or index == total_frames - 1:
                            print(f"PROGRESS:{progress_val:.3f}", flush=True)

                encode_proc.stdin.close()
                encode_proc.wait(timeout=300)
            finally:
                if not encode_proc.stdin.closed:
                    encode_proc.stdin.close()
                if encode_proc.poll() is None:
                    encode_proc.kill()
                    encode_proc.wait(timeout=10)
                shutil.rmtree(temp_frames_dir, ignore_errors=True)

            if encode_proc.returncode != 0:
                encode_log.seek(0)
                err = encode_log.read().decode(errors="replace")
                raise RuntimeError(f"FFmpeg VP9 encode failed (code {encode_proc.returncode}): {err}")

        # Verify master cutout
        _verify_video(out_master, width=width, height=height, frame_count=total_frames)

        with out_master.open("rb") as handle:
            master_checksum = hashlib.sha256(handle.read()).hexdigest()

        # Build scaled preview for UI
        preview_info = build_alpha_preview(out_master, width=width, height=height, frame_count=total_frames, fps=fps)

        manifest = {
            "schema_version": 2,
            "engine": "sam2",
            "model": model,
            "status": "ready",
            "width": width,
            "height": height,
            "fps": fps,
            "frame_count": total_frames,
            "video_file": VIDEO_NAME,
            "sha256": master_checksum,
            "size_bytes": out_master.stat().st_size,
            "preview": preview_info,
            "device": "cuda",
            "device_name": torch.cuda.get_device_name(0),
            "torch_version": torch.__version__,
            "prompts": prompts,
            "geometry": "fit-letterbox",
            "isolated_frame_count": isolated_frame_count,
            "tracking_full_window": True,
            "offload_video_to_cpu": True,
            "performance": {
                "total_seconds": round(time.perf_counter() - started_at, 3),
                "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated(),
                "peak_cuda_reserved_bytes": torch.cuda.max_memory_reserved(),
                "required_input_memory_bytes": required_memory_bytes,
            },
        }

        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest

    finally:
        shutil.rmtree(temp_frames_dir, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SAM 2 GPU Video Isolation Worker")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--model", type=str, default="sam2.1_hiera_tiny")
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--active-intervals", type=str, default=None,
                        help="source-time begin,end;begin,end, with end excluded")
    parser.add_argument("--prompts", type=str, default=None)
    parser.add_argument("--prompt-points-file", type=Path, default=None)
    parser.add_argument(
        "--prompt-points", type=str, default=None,
        help="x,y,label;x,y,label in normalized 0..1 coords (1=subject, 0=background)",
    )
    args = parser.parse_args()

    prompts_data = json.loads(args.prompts) if args.prompts else None
    prompt_points_text = (args.prompt_points_file.read_text(encoding="utf-8")
                          if args.prompt_points_file else args.prompt_points)
    if prompt_points_text:
        # A quote-free payload is used because JSON on argv loses its double
        # quotes before this process can parse it on Windows.
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from scripts.cutout_prompt import parse_prompt_points

        points = parse_prompt_points(prompt_points_text)
        if points:
            by_frame: dict[int, list[dict[str, Any]]] = {}
            for point in points:
                f_idx = int(point.get("frame", 0))
                by_frame.setdefault(f_idx, []).append(point)
            prompts_data = [
                {
                    "object_id": 1,
                    "frame": f_idx,
                    "points": [[p["x"], p["y"]] for p in pts],
                    "labels": [p["label"] for p in pts],
                }
                for f_idx, pts in sorted(by_frame.items())
            ]
    result = process_video_sam2(
        source=args.source,
        output_dir=args.output_dir,
        start=args.start,
        duration=args.duration,
        fps=args.fps,
        width=args.width,
        height=args.height,
        model=args.model,
        checkpoint=args.checkpoint,
        prompts=prompts_data,
        active_intervals=[tuple(map(float, pair.split(","))) for pair in args.active_intervals.split(";")]
            if args.active_intervals is not None else None,
    )
    print(f"RESULT:{json.dumps(result)}", flush=True)
