"""Run a local SAM 2 CPU feasibility probe in tools/cutout_runtime/.venv.

Consumes an explicitly supplied temporary JPEG directory. No project edits,
network requests, or production exports. Report and contact sheet paths are
chosen by the caller; source images and model checkpoints are read-only.
"""
from __future__ import annotations

import argparse
from collections import OrderedDict
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image, ImageDraw
import psutil
import torch


def run(frames: Path, checkpoint: Path, prompts: list[dict], report: Path, contact: Path) -> dict:
    from sam2.build_sam import build_sam2_video_predictor
    import sam2.sam2_video_predictor as predictor_module

    torch.set_num_threads(4)
    paths = sorted(frames.glob("*.jpg"), key=lambda path: int(path.stem))
    if not paths:
        raise ValueError("no JPEG frames")
    width, height = Image.open(paths[0]).size
    process = psutil.Process()
    peak = process.memory_info().rss
    start = time.perf_counter()

    class LazyFrames:
        """Same normalization as upstream, with a four-frame tensor cache."""
        def __init__(self, size):
            self.size = size
            self.cache = OrderedDict()
            self.mean = torch.tensor([.485, .456, .406])[:, None, None]
            self.std = torch.tensor([.229, .224, .225])[:, None, None]

        def __len__(self):
            return len(paths)

        def __getitem__(self, index):
            if index not in self.cache:
                with Image.open(paths[index]) as image:
                    pixels = np.array(image.convert("RGB").resize((self.size, self.size)), dtype=np.float32) / 255
                tensor = torch.from_numpy(pixels).permute(2, 0, 1)
                self.cache[index] = (tensor - self.mean) / self.std
                while len(self.cache) > 4:
                    self.cache.popitem(last=False)
            self.cache.move_to_end(index)
            return self.cache[index]

    original_loader = predictor_module.load_video_frames
    predictor_module.load_video_frames = lambda **kwargs: (LazyFrames(kwargs["image_size"]), height, width)
    try:
        predictor = build_sam2_video_predictor("configs/sam2.1/sam2.1_hiera_t.yaml", str(checkpoint),
                                               device="cpu", apply_postprocessing=False)
        with torch.inference_mode():
            state = predictor.init_state(str(frames), offload_video_to_cpu=True, offload_state_to_cpu=True)
            for prompt in prompts:
                points = np.array(prompt["points"], dtype=np.float32) * [width, height]
                predictor.add_new_points_or_box(state, frame_idx=int(prompt.get("frame", 0)),
                    obj_id=prompt["object_id"], points=points, labels=np.array(prompt["labels"], dtype=np.int32))
            initialized = time.perf_counter()
            selected = set(np.linspace(0, len(paths) - 1, min(6, len(paths)), dtype=int))
            sheet = Image.new("RGB", (width * 3, height * len(selected)), "#202020")
            row = 0
            coverage, frame_seconds = [], []
            last = time.perf_counter()
            retention = max(32, predictor.num_maskmem * predictor.memory_temporal_stride_for_eval,
                            predictor.max_obj_ptrs_in_encoder)
            for index, object_ids, logits in predictor.propagate_in_video(state):
                alpha = (logits > 0).any(dim=0).squeeze().cpu().numpy().astype(np.uint8) * 255
                coverage.append(float((alpha > 0).mean()))
                now = time.perf_counter()
                frame_seconds.append(now - last)
                last = now
                peak = max(peak, process.memory_info().rss)
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
                # No chunk reset: keep the memory/obj-pointer span required by
                # this pinned model and all user conditioning frames.
                for outputs in state["output_dict_per_obj"].values():
                    old = [key for key in outputs["non_cond_frame_outputs"] if key < index - retention]
                    for key in old:
                        del outputs["non_cond_frame_outputs"][key]
                if index % 10 == 0:
                    print(json.dumps({"frame": index, "rss_mib": round(peak / 2**20)}), flush=True)
            sheet.save(contact)
        with checkpoint.open("rb") as handle:
            checksum = hashlib.file_digest(handle, "sha256").hexdigest()
        result = {"engine": "sam2.1_hiera_tiny", "device": "cpu", "threads": 4,
                  "code_commit": "2b90b9f5ceec907a1c18123530e92e794ad901a4",
                  "checkpoint_sha256": checksum, "frames": len(coverage), "source_fps": 30,
                  "startup_seconds": initialized - start, "total_seconds": time.perf_counter() - start,
                  "frame_seconds_p50": float(np.median(frame_seconds)),
                  "frame_seconds_p95": float(np.percentile(frame_seconds, 95)),
                  "peak_sampled_rss_mib": peak / 2**20, "coverage_min": min(coverage),
                  "coverage_max": max(coverage), "prompts": prompts,
                  "quality_gate": "requires human subject review; binary segmentation is not alpha matting"}
        report.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    finally:
        predictor_module.load_video_frames = original_loader


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
