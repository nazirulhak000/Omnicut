"""Compare rembg alpha modes on the SAME decoded frames; never edits a project."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw
from scripts.background_isolation_worker import BackgroundIsolationWorker
from scripts.cutout_temporal import TemporalAlphaRefiner


def run(folder: Path, report: Path, contact: Path):
    paths = sorted(folder.glob("*.jpg"), key=lambda path: int(path.stem))
    segmenter, session = BackgroundIsolationWorker()._get_session("u2net")
    refiner = TemporalAlphaRefiner()
    previous = {}
    previous_gray = None
    results = {mode: {"edge_error_sum": 0., "valid_pixels": 0, "edge_pixels": 0,
                      "spatial_iou_sum": 0., "empty_frames": 0} for mode in ("off", "legacy", "motion")}
    width, height = Image.open(paths[0]).size
    sheet = Image.new("RGB", (width * 4, height * 6), "white")
    selected = set(np.linspace(0, len(paths) - 1, 6, dtype=int))
    row = 0
    started = time.perf_counter()
    for index, path in enumerate(paths):
        with Image.open(path) as image:
            rgb = image.convert("RGB")
        raw = segmenter.remove(rgb, session=session).convert("RGBA").getchannel("A")
        legacy = raw.copy()
        if "legacy" in previous:
            before = Image.fromarray(previous["legacy"])
            stable = ImageChops.difference(before, raw).point(lambda value: 255 if value < 24 else 0)
            legacy.paste(Image.blend(before, raw, .65), mask=stable)
        masks = {"off": np.asarray(raw), "legacy": np.asarray(legacy),
                 "motion": refiner.refine(np.asarray(rgb), np.asarray(raw), pts=index / 30, fps=30)}
        gray = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2GRAY)
        if previous_gray is not None:
            backward = cv2.calcOpticalFlowFarneback(gray, previous_gray, None, .5, 3, 21, 3, 5, 1.2, 0)
            forward = cv2.calcOpticalFlowFarneback(previous_gray, gray, None, .5, 3, 21, 3, 5, 1.2, 0)
            yy, xx = np.mgrid[:height, :width].astype(np.float32)
            bx, by = xx + backward[..., 0], yy + backward[..., 1]
            cycle = np.linalg.norm(backward + cv2.remap(forward, bx, by, cv2.INTER_LINEAR), axis=2)
            photo = np.abs(cv2.remap(previous_gray, bx, by, cv2.INTER_LINEAR).astype(float) - gray)
            valid = (cycle < 1) & (photo < 20) & (bx >= 0) & (by >= 0) & (bx < width - 1) & (by < height - 1)
            binary = (masks["off"] > 127).astype(np.uint8)
            kernel = np.ones((5, 5), np.uint8)
            edge = cv2.dilate(binary, kernel) != cv2.erode(binary, kernel)
            for mode, mask in masks.items():
                warped = cv2.remap(previous[mode], bx, by, cv2.INTER_LINEAR)
                result = results[mode]
                result["edge_error_sum"] += float(np.abs(mask.astype(float) - warped)[edge & valid].sum()) / 255
                result["valid_pixels"] += int((edge & valid).sum())
                result["edge_pixels"] += int(edge.sum())
        for mode, mask in masks.items():
            raw_binary, binary = masks["off"] > 127, mask > 127
            union = (raw_binary | binary).sum()
            results[mode]["spatial_iou_sum"] += float((raw_binary & binary).sum() / max(1, union))
            results[mode]["empty_frames"] += int(not binary.any())
        if index in selected:
            sheet.paste(rgb, (0, row * height))
            for column, (mode, mask) in enumerate(masks.items(), start=1):
                composite = Image.new("RGB", rgb.size, "#0b1220")
                composite.paste(rgb, mask=Image.fromarray(mask))
                sheet.paste(composite, (column * width, row * height))
                ImageDraw.Draw(sheet).text((column * width + 3, row * height + 4), f"{mode}: {index}", fill="white")
            row += 1
        previous, previous_gray = masks, gray
        if index % 10 == 0:
            print(json.dumps({"frame": index}), flush=True)
    summary = {"frames": len(paths), "fps": 30, "width": width, "height": height,
               "seconds": time.perf_counter() - started, "model": "u2net",
               "note": "Spatial IoU compares to raw rembg, NOT annotated ground truth. No subject correctness claim.",
               "methods": {}}
    for mode, result in results.items():
        summary["methods"][mode] = {
            "motion_compensated_boundary_mae": result["edge_error_sum"] / max(1, result["valid_pixels"]),
            "valid_boundary_coverage": result["valid_pixels"] / max(1, result["edge_pixels"]),
            "mean_iou_vs_raw_rembg": result["spatial_iou_sum"] / len(paths),
            "empty_frames": result["empty_frames"],
        }
    report.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    sheet.save(contact)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--contact", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.frames, args.report, args.contact)), flush=True)
