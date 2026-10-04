"""Explicit local GPU acceptance test; the ordinary suite remains offline.

Run with OMNICUT_TEST_SAM2_GPU=1. Source, task registry, cache and decoded test
media are isolated and immediately removed, including on failed assertions.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile

from fastapi import FastAPI
from fastapi.testclient import TestClient
import numpy as np
from PIL import Image, ImageDraw
import pytest

import scripts.api_background_isolation as api
import scripts.task_manager as task_manager
from scripts.background_isolation_video_worker import video_artifact_id


pytestmark = pytest.mark.skipif(os.environ.get("OMNICUT_TEST_SAM2_GPU") != "1",
    reason="explicit local GPU acceptance: set OMNICUT_TEST_SAM2_GPU=1")


def _fixture_frame(index: int) -> tuple[Image.Image, Image.Image, Image.Image]:
    """Moving bottle left of a skin-coloured palm: centre is not the product."""
    image = Image.new("RGB", (720, 1280), "#223044")
    product_mask = Image.new("L", image.size)
    hand_mask = Image.new("L", image.size)
    draw = ImageDraw.Draw(image)
    hand = ImageDraw.Draw(hand_mask)
    dx = index * 2
    # Palm plus fingers touch the bottle while remaining a separate object.
    palm = (330 + dx, 550, 650 + dx, 1050)
    finger = (230 + dx, 510, 420 + dx, 610)
    draw.ellipse(palm, fill="#DBA889")
    draw.rounded_rectangle(finger, radius=38, fill="#DBA889")
    hand.ellipse(palm, fill=255)
    hand.rounded_rectangle(finger, radius=38, fill=255)
    body = (120 + dx, 300, 280 + dx, 650)
    cap = (150 + dx, 250, 250 + dx, 320)
    draw.rounded_rectangle(body, radius=35, fill="#147ACA", outline="#80C9FC", width=6)
    draw.rounded_rectangle(cap, radius=12, fill="#123563")
    draw.rounded_rectangle((145 + dx, 405, 255 + dx, 535), radius=14, fill="#F2F7FA")
    draw.line((140 + dx, 352, 140 + dx, 395), fill="#B1E4FF", width=7)
    product = ImageDraw.Draw(product_mask)
    product.rounded_rectangle(body, radius=35, fill=255)
    product.rounded_rectangle(cap, radius=12, fill=255)
    # The visible hand excludes pixels occluded by the product.
    hand_array = np.asarray(hand_mask).copy()
    hand_array[np.asarray(product_mask) > 0] = 0
    return image, product_mask, Image.fromarray(hand_array)


def _encode_source(path: Path, frames: list[Image.Image]) -> None:
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{frames[0].width}x{frames[0].height}", "-r", "30",
        "-i", "pipe:0", "-an", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(path),
    ], input=b"".join(frame.tobytes() for frame in frames), capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode(errors="replace")


def _decode_alpha(path: Path, frame_count: int, width: int, height: int) -> np.ndarray:
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-c:v", "libvpx-vp9",
        "-i", str(path), "-an", "-vf", "alphaextract", "-pix_fmt", "gray", "-f", "rawvideo", "pipe:1",
    ], capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert len(result.stdout) == frame_count * width * height
    return np.frombuffer(result.stdout, dtype=np.uint8).reshape(frame_count, height, width)


def _fit_mask(mask: Image.Image, width: int, height: int) -> np.ndarray:
    scale = min(width / mask.width, height / mask.height)
    resized = mask.resize((round(mask.width * scale), round(mask.height * scale)), Image.Resampling.NEAREST)
    canvas = Image.new("L", (width, height))
    canvas.paste(resized, ((width - resized.width) // 2, (height - resized.height) // 2))
    return np.asarray(canvas) > 0


@pytest.mark.parametrize("scoped", [False, True, "multi-seed"], ids=["full-window", "scoped-windows", "scoped-multiple-seeds"])
def test_picked_positive_negative_points_reach_actual_sam2_gpu_via_api(monkeypatch, tmp_path, scoped):
    with tempfile.TemporaryDirectory(prefix="sam2-api-gpu-", dir=tmp_path) as temporary:
        workspace = Path(temporary)
        projects = workspace / "isolated-project-store"
        projects.mkdir()
        monkeypatch.setattr(api, "PROJECTS_DIR", projects)
        monkeypatch.setattr(task_manager, "TASKS_FILE", projects / "task_registry.json")
        monkeypatch.setattr(api.TaskManager, "_tasks", {})
        # Only scheduler timing is synchronous; API normalization, registry,
        # worker subprocess, CUDA inference and media validation are actual.
        monkeypatch.setattr(api.TaskManager, "run_in_background", lambda fn: fn())
        app = FastAPI()
        app.include_router(api.router)
        client = TestClient(app)
        count, width, height = 12, 1080, 1920
        fixtures = [_fixture_frame(index) for index in range(count)]
        if scoped:
            # A square source catches the historical stretch-vs-letterbox
            # bug; the full-window case also checks a matching 9:16 source.
            fixtures = [(image.resize((720, 720), Image.Resampling.BICUBIC),
                         product.resize((720, 720), Image.Resampling.NEAREST),
                         hand.resize((720, 720), Image.Resampling.NEAREST))
                        for image, product, hand in fixtures]
        source = workspace / "off-centre-bottle-and-hand.mp4"
        _encode_source(source, [fixture[0] for fixture in fixtures])
        # Same JSON shape sent by EditorShell, including positive/negative
        # labels from subjectPointFromPickClick/normalizeSubjectPoints.
        points = [{"x": .27778, "y": .39453 if scoped else .3125, "label": 1},
                  {"x": .68, "y": .57031 if scoped else .625, "label": 0},
                  {"x": .9, "y": .1, "label": 0}]
        config = {"enabled": True, "engine": "sam2", "model": "sam2.1_hiera_tiny",
                  "mode": "cutout", "quality": "quality", "subject_points": points,
                  "auto_prompt": False}
        if scoped == "multi-seed":
            # Deterministic prompt discovery isolates real SAM2's reseeding
            # behavior from rembg accuracy/model installation. CUDA inference,
            # all three seed frames, alpha encoding and frame counts are real.
            config.pop("auto_prompt")
            config.update(prompt_reference_source=str(source), prompt_reference_start=0)
            def derive(_source, _staged, timestamp, *_args):
                return [{**point, "x": round(point["x"] + timestamp * 30 * 2 / 720, 5)}
                        for point in points]
            monkeypatch.setattr("scripts.background_isolation_video_worker._derive_points_for_timestamp", derive)
        payload = {"source_path": str(source), "config": config, "start": 0,
                   "duration": count / 30, "fps": 30, "timebase": "1/30",
                   "width": width, "height": height, "rotation": 0}
        intervals = [[2 / 30, 5 / 30], [8 / 30, 11 / 30]] if scoped else None
        if intervals is not None:
            payload["active_intervals"] = intervals
        preflight = client.post("/api/background-isolation/preflight", json=payload)
        assert preflight.status_code == 200
        assert preflight.json()["ok"] is True, preflight.json()
        assert preflight.json()["runtime"]["cuda"] is True
        response = client.post("/api/background-isolation/process", json=payload)
        assert response.status_code == 200, response.text
        assert response.json()["config"]["subject_points"] == points
        task = api.TaskManager.get_task(response.json()["task_id"])
        assert task["status"] == "completed", task
        completed = task["result"]
        assert completed["subject_points"] == points
        artifact_id = completed["artifact"]["id"]
        manifest_response = client.get(f"/api/background-isolation/sequences/{artifact_id}/manifest")
        assert manifest_response.status_code == 200
        manifest = manifest_response.json()
        assert manifest["width"] == width and manifest["height"] == height
        assert manifest["frame_count"] == count and manifest["engine"] == "sam2"
        assert manifest["sam2"]["device"] == "cuda"
        assert manifest["sam2"]["geometry"] == "fit-letterbox"
        assert manifest["sam2"]["offload_video_to_cpu"] is True
        assert manifest["sam2"]["prompts"][0]["labels"] == [1, 0, 0]
        assert manifest["sam2"]["prompts"][0]["points"] == [[p["x"], p["y"]] for p in points]
        if scoped == "multi-seed":
            assert [prompt["frame"] for prompt in manifest["sam2"]["prompts"]] == [0, 2, 8]
        master = projects / ".cache/background-isolation-videos" / artifact_id / "cutout.webm"
        preview = master.with_name("preview.webm")
        alpha = _decode_alpha(master, count, width, height)
        proxy_alpha = _decode_alpha(preview, count, 540, 960)
        metrics = []
        for index, (_, product, hand) in enumerate(fixtures):
            if scoped and index not in (2, 3, 4, 8, 9, 10):
                assert alpha[index].max() == 0, (index, "inactive master alpha")
                # The lossy VP9 proxy may round the zero alpha plane to 1/255;
                # master alpha is exact zero and proxy leakage is bounded.
                assert proxy_alpha[index].max() <= 1, (index, "inactive proxy alpha")
                metrics.append({"frame": index, "inactive_alpha_max": 0,
                                "inactive_proxy_alpha_max": int(proxy_alpha[index].max())})
                continue
            expected = _fit_mask(product, width, height)
            excluded = _fit_mask(hand, width, height)
            actual = alpha[index] > 127
            iou = float((actual & expected).sum() / (actual | expected).sum())
            hand_leak = float((actual & excluded).sum() / excluded.sum())
            assert iou >= .75, (index, iou)
            assert hand_leak <= .04, (index, hand_leak)
            assert alpha[index, round(points[0]["y"] * height), round((.27778 + index * 2 / 720) * width)] >= 240
            assert alpha[index, round(points[1]["y"] * height), round((.68 + index * 2 / 720) * width)] <= 16
            assert proxy_alpha[index, round(points[0]["y"] * 960), round((.27778 + index * 2 / 720) * 540)] >= 240
            metrics.append({"frame": index, "product_iou": round(iou, 4), "hand_leak": round(hand_leak, 4)})
        served = client.get(f"/api/background-isolation/videos/{artifact_id}/cutout.webm")
        assert served.status_code == 200 and served.content == master.read_bytes()
        assert client.get(f"/api/background-isolation/videos/{artifact_id}/preview.webm").status_code == 200
        stamp = master.stat().st_mtime_ns
        repeat = client.post("/api/background-isolation/process", json=payload)
        repeat_task = api.TaskManager.get_task(repeat.json()["task_id"])
        assert repeat_task["status"] == "completed", repeat_task
        assert repeat_task["result"]["artifact"]["id"] == artifact_id
        assert master.stat().st_mtime_ns == stamp
        changed = {**config, "subject_points": [{**points[0], "x": .32}, *points[1:]]}
        identity_arguments = dict(start=0, duration=count / 30, fps=30, timebase="1/30",
                                  width=width, height=height, rotation=0, active_intervals=intervals)
        assert video_artifact_id(manifest["source_fingerprint"], changed, **identity_arguments) != artifact_id
        no_negatives = {**config, "subject_points": points[:1]}
        assert video_artifact_id(manifest["source_fingerprint"], no_negatives, **identity_arguments) != artifact_id
        assert not list(projects.rglob("sam2_frames_*"))
        assert not list(projects.rglob(".prompt_frame.jpg"))
        if scoped:
            assert manifest["isolated_frame_count"] == 6
            assert manifest["sam2"]["tracking_full_window"] is True
        print("SAM2_GPU_ACCEPTANCE:" + json.dumps({"runtime": preflight.json()["runtime"],
            "frame_count": count, "resolution": [width, height], "alpha": metrics,
            "active_intervals": intervals,
            "source_resolution": list(fixtures[0][0].size),
            "performance": manifest["performance"], "gpu": manifest["sam2"]["performance"],
            "cache_reused": True, "point_change_invalidates": True, "negative_change_invalidates": True}))
    assert not workspace.exists(), "all source/cache/registry/media must be cleaned"
