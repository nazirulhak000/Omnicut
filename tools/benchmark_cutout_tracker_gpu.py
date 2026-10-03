"""Run a local SAM 2 GPU feasibility probe on RTX 4060 in tools/cutout_runtime/.venv.

Measures real-time tracking speed (FPS), latency, VRAM consumption, and mask quality.
"""
from __future__ import annotations

import argparse
from collections import OrderedDict
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
from PIL import Image, ImageDraw
import psutil
import torch


def run(frames: Path, checkpoint: Path, prompts: list[dict], report: Path, contact: Path) -> dict:
    from sam2.build_sam import build_sam2_video_predictor
    import sam2.sam2_video_predictor as predictor_module

    paths = sorted([p for p in frames.glob("*.jpg") if p.stem.isdigit()], key=lambda path: int(path.stem))
    if not paths:
        raise ValueError("no JPEG frames found in " + str(frames))

    width, height = Image.open(paths[0]).size
    process = psutil.Process()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    
    start = time.perf_counter()
    device = "cuda"

    # Direct predictor initialization on CUDA
    predictor = build_sam2_video_predictor(
        "configs/sam2.1/sam2.1_hiera_t.yaml",
        str(checkpoint),
        device=device,
        apply_postprocessing=False
    )
    
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        state = predictor.init_state(str(frames), offload_video_to_cpu=False, offload_state_to_cpu=False)
        for prompt in prompts:
            points = np.array(prompt["points"], dtype=np.float32) * [width, height]
            predictor.add_new_points_or_box(
                state,
                frame_idx=int(prompt.get("frame", 0)),
                obj_id=prompt["object_id"],
                points=points,
                labels=np.array(prompt["labels"], dtype=np.int32)
            )
        
        initialized = time.perf_counter()
        startup_seconds = initialized - start

        selected = set(np.linspace(0, len(paths) - 1, min(6, len(paths)), dtype=int))
        sheet = Image.new("RGB", (width * 3, height * len(selected)), "#202020")
        row = 0
        coverage = []
        frame_seconds = []
        last = time.perf_counter()

        retention = max(32, predictor.num_maskmem * predictor.memory_temporal_stride_for_eval,
                        predictor.max_obj_ptrs_in_encoder)

        for index, object_ids, logits in predictor.propagate_in_video(state):
            # Combined mask from all tracked objects
            alpha = (logits > 0).any(dim=0).squeeze().cpu().numpy().astype(np.uint8) * 255
            coverage.append(float((alpha > 0).mean()))
            now = time.perf_counter()
            frame_seconds.append(now - last)
            last = now

            if index in selected:
                with Image.open(paths[index]) as image:
                    image = image.convert("RGB")
                    sheet.paste(image, (0, row * height))
                    for column, background in [(1, "white"), (2, "black")]:
                        composited = Image.new("RGB", (width, height), background)
                        composited.paste(image, mask=Image.fromarray(alpha))
                        sheet.paste(composited, (column * width, row * height))
                ImageDraw.Draw(sheet).text((4, row * height + 4), f"frame {index}", fill="red")
                row += 1

            for outputs in state["output_dict_per_obj"].values():
                old = [key for key in outputs["non_cond_frame_outputs"] if key < index - retention]
                for key in old:
                    del outputs["non_cond_frame_outputs"][key]

        total_track_seconds = time.perf_counter() - initialized
        total_seconds = time.perf_counter() - start
        contact.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(contact)

    with checkpoint.open("rb") as handle:
        checksum = hashlib.sha256(handle.read()).hexdigest()

    peak_vram_mib = torch.cuda.max_memory_allocated() / (1024 * 1024)
    peak_vram_reserved_mib = torch.cuda.max_memory_reserved() / (1024 * 1024)
    fps = len(coverage) / total_track_seconds if total_track_seconds > 0 else 0

    result = {
        "engine": "sam2.1_hiera_tiny",
        "device": "cuda",
        "device_name": torch.cuda.get_device_name(0),
        "checkpoint_sha256": checksum,
        "frames": len(coverage),
        "source_fps": 30,
        "startup_seconds": round(startup_seconds, 3),
        "total_seconds": round(total_seconds, 3),
        "track_only_seconds": round(total_track_seconds, 3),
        "fps": round(fps, 2),
        "speedup_vs_realtime": round(fps / 30.0, 2),
        "frame_seconds_p50": round(float(np.median(frame_seconds)), 4),
        "frame_seconds_p95": round(float(np.percentile(frame_seconds, 95)), 4),
        "peak_vram_allocated_mib": round(peak_vram_mib, 2),
        "peak_vram_reserved_mib": round(peak_vram_reserved_mib, 2),
        "coverage_min": round(min(coverage), 4),
        "coverage_max": round(max(coverage), 4),
        "prompts": prompts,
    }

    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--contact", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.frames, args.checkpoint, json.loads(args.prompts.read_text()),
                         args.report, args.contact)), flush=True)
