"""Lightweight local HTTP daemon for interactive single-frame SAM 2 subject segmentation.

Runs inside tools/cutout_runtime/.venv on CUDA GPU.
Provides instant (~20-50ms) interactive prompt prediction for real-time subject lift
and shimmering outline preview (iPhone/CapCut style).
"""
from __future__ import annotations

import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from typing import Any

import cv2
import numpy as np
from PIL import Image
import torch

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from scripts.cutout_runtime import resolve_checkpoint, MODEL_CONFIGS
from scripts.interactive_sam2_assembly import predict_product_mask
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

# Global state
PREDICTOR: SAM2ImagePredictor | None = None
CURRENT_FRAME_KEY: str | None = None
CURRENT_FRAME_SIZE: tuple[int, int] = (1080, 1920)  # (w, h)
LAST_ACTIVITY: float = time.time()


def get_predictor(model_name: str = "sam2.1_hiera_tiny") -> SAM2ImagePredictor:
    global PREDICTOR
    if PREDICTOR is not None:
        return PREDICTOR
    checkpoint = resolve_checkpoint(model_name)
    config = MODEL_CONFIGS[model_name]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = build_sam2(config, str(checkpoint), device=device)
    PREDICTOR = SAM2ImagePredictor(model)
    return PREDICTOR


def extract_frame_rgb(source_path: Path, timestamp: float, width: int = 540, height: int = 960) -> np.ndarray:
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
        "-ss", str(max(0.0, timestamp)),
        "-i", str(source_path),
        "-frames:v", "1",
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    frame = np.frombuffer(proc.stdout, dtype=np.uint8).reshape((height, width, 3))
    return frame


def mask_to_contours(mask: np.ndarray, width: int, height: int, max_points: int = 120) -> list[list[list[float]]]:
    """Extract normalized [x, y] polygon contours from binary mask."""
    uint_mask = (mask > 0).astype(np.uint8) * 255
    contours, _ = cv2.findContours(uint_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
    result = []
    for c in contours:
        if cv2.contourArea(c) < 50:  # Filter out tiny noise specks
            continue
        # Approximate to reduce point count for smooth rendering
        epsilon = 0.003 * cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, epsilon, True)
        pts = [[round(float(p[0][0]) / width, 5), round(float(p[0][1]) / height, 5)] for p in approx]
        if len(pts) >= 3:
            result.append(pts)
    return result


class InteractiveSAM2Handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, data: dict[str, Any]):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        global LAST_ACTIVITY
        LAST_ACTIVITY = time.time()
        if self.path == "/health":
            cuda = torch.cuda.is_available()
            self._send_json(200, {
                "ok": True,
                "status": "ready",
                "device": torch.cuda.get_device_name(0) if cuda else "cpu",
                "cuda": cuda,
                "current_frame": CURRENT_FRAME_KEY,
            })
        else:
            self._send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        global CURRENT_FRAME_KEY, CURRENT_FRAME_SIZE, LAST_ACTIVITY
        LAST_ACTIVITY = time.time()
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            self._send_json(400, {"ok": False, "error": f"invalid json: {e}"})
            return

        if self.path == "/set_frame":
            try:
                source = Path(payload["source"])
                timestamp = float(payload.get("timestamp", 0.0))
                width = int(payload.get("width", 540))
                height = int(payload.get("height", 960))
                frame_key = f"{source.resolve()}:{timestamp:.3f}:{width}x{height}"

                if CURRENT_FRAME_KEY != frame_key:
                    t0 = time.perf_counter()
                    frame = extract_frame_rgb(source, timestamp, width, height)
                    predictor = get_predictor()
                    with torch.inference_mode():
                        predictor.set_image(frame)
                    CURRENT_FRAME_KEY = frame_key
                    CURRENT_FRAME_SIZE = (width, height)
                    load_ms = round((time.perf_counter() - t0) * 1000, 1)
                else:
                    load_ms = 0.0

                self._send_json(200, {
                    "ok": True,
                    "frame_key": CURRENT_FRAME_KEY,
                    "width": CURRENT_FRAME_SIZE[0],
                    "height": CURRENT_FRAME_SIZE[1],
                    "load_ms": load_ms,
                })
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})

        elif self.path == "/predict":
            try:
                predictor = get_predictor()
                if CURRENT_FRAME_KEY is None:
                    self._send_json(400, {"ok": False, "error": "no frame loaded; call /set_frame first"})
                    return
                points_data = payload.get("points", [])
                if not points_data:
                    self._send_json(200, {"ok": True, "contours": [], "bbox": None, "predict_ms": 0.0})
                    return

                w, h = CURRENT_FRAME_SIZE
                coords = []
                labels = []
                for p in points_data:
                    coords.append([float(p["x"]) * w, float(p["y"]) * h])
                    labels.append(int(p.get("label", 1)))

                t0 = time.perf_counter()
                with torch.inference_mode():
                    best_mask, best_score = predict_product_mask(predictor, coords, labels)

                predict_ms = round((time.perf_counter() - t0) * 1000, 1)

                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                closed_mask = cv2.morphologyEx((best_mask > 0).astype(np.uint8), cv2.MORPH_CLOSE, kernel)
                dilated_mask = cv2.dilate(closed_mask, kernel, iterations=1)
                contours = mask_to_contours(dilated_mask, w, h)

                y_indices, x_indices = np.where(dilated_mask > 0)
                if len(x_indices) > 0 and len(y_indices) > 0:
                    bbox = [
                        round(float(x_indices.min()) / w, 5),
                        round(float(y_indices.min()) / h, 5),
                        round(float(x_indices.max()) / w, 5),
                        round(float(y_indices.max()) / h, 5),
                    ]
                else:
                    bbox = None

                self._send_json(200, {
                    "ok": True,
                    "contours": contours,
                    "bbox": bbox,
                    "score": round(best_score, 4),
                    "predict_ms": predict_ms,
                })
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})

        elif self.path == "/shutdown":
            self._send_json(200, {"ok": True, "message": "shutting down"})
            threading.Thread(target=self.server.shutdown).start()

        else:
            self._send_json(404, {"ok": False, "error": "not found"})


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8008)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()

    # Pre-warm predictor
    print("[interactive_sam2] Pre-warming SAM2 predictor on GPU...")
    get_predictor()
    print(f"[interactive_sam2] Interactive SAM2 daemon listening on http://{args.host}:{args.port}")

    server = HTTPServer((args.host, args.port), InteractiveSAM2Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[interactive_sam2] Stopping interactive daemon...")
        server.server_close()


if __name__ == "__main__":
    main()
