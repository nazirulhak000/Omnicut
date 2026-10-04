"""Manual CUDA/FFmpeg probe using a synthetic product; artifacts are temporary.

Run with the isolated cutout interpreter. No real project/assets are read.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.interactive_sam2_daemon import get_predictor
from scripts.interactive_sam2_assembly import predict_product_mask
from scripts.interactive_sam2_client import segment_frame_interactive


class RecordingPredictor:
    def __init__(self, predictor):
        self.predictor = predictor
        self.calls = []

    def predict(self, **kwargs):
        result = self.predictor.predict(**kwargs)
        self.calls.append({'box': kwargs.get('box', np.array([])).tolist(),
                           'scores': result[1].tolist(),
                           'center_included': [bool(mask[200, 180]) for mask in result[0]],
                           'areas': [int((mask > 0).sum()) for mask in result[0]]})
        return result


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    temporary_root = ROOT / '.tmp'
    temporary_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cutout_t6_', dir=temporary_root) as directory:
        output = Path(directory)
        image = np.full((480, 360, 3), (36, 28, 24), dtype=np.uint8)
        cv2.rectangle(image, (90, 100), (270, 310), (190, 190, 195), -1)
        cv2.rectangle(image, (100, 110), (260, 300), (45, 45, 45), -1)
        cv2.circle(image, (180, 200), 70, (230, 120, 30), 9)
        for angle in range(0, 360, 60):
            cv2.ellipse(image, (180, 200), (52, 16), angle, 0, 360, (115, 115, 120), -1)
        cv2.circle(image, (180, 200), 16, (180, 180, 185), -1)
        cv2.imwrite(str(output / 'source.png'), image)
        predictor = get_predictor()
        coords, labels = np.array([[180, 200]], np.float32), np.array([1], np.int32)
        with torch.inference_mode():
            predictor.set_image(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            masks, scores, _ = predictor.predict(point_coords=coords, point_labels=labels,
                                                  multimask_output=True)
            areas = np.array([(mask > 0).sum() for mask in masks])
            valid = np.flatnonzero(areas < image.shape[0] * image.shape[1] * .85)
            previous = masks[max(valid, key=lambda index: areas[index]) if len(valid) else scores.argmax()] > 0
            predict_product_mask(predictor, coords, labels)  # Warm up both decoder paths.
            torch.cuda.synchronize()
            start = time.perf_counter()
            recorder = RecordingPredictor(predictor)
            current, score = predict_product_mask(recorder, coords, labels)
            torch.cuda.synchronize()
            elapsed = (time.perf_counter() - start) * 1000
        assert current.any(), 'GPU probe returned an empty mask'
        assert current[200, 180], 'GPU probe lost the selected point'
        expected = np.zeros(current.shape, dtype=bool)
        expected[100:311, 90:271] = True
        before_iou = float((previous & expected).sum() / (previous | expected).sum())
        after_iou = float((current & expected).sum() / (current | expected).sum())
        assert after_iou > .99, 'Synthetic housing was not assembled completely'
        panels = []
        for mask in [previous, current]:
            panel = image.copy()
            tint = np.full_like(panel, (0, 240, 120))
            panel[mask] = cv2.addWeighted(panel, .5, tint, .5, 0)[mask]
            panels.append(panel)
        cv2.imwrite(str(output / 'comparison.png'), np.hstack(panels))
        commands = [
            ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-loop', '1',
             '-i', str(output / 'comparison.png'), '-t', '0.2', '-r', '30', '-c:v', 'libx264',
             '-pix_fmt', 'yuv420p', str(output / 'probe.mp4')],
            ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-i',
             str(output / 'probe.mp4'), '-frames:v', '1', str(output / 'frame.png')],
        ]
        for command in commands:
            try:
                subprocess.run(command, check=True, capture_output=True, timeout=30)
            except subprocess.CalledProcessError as exc:
                raise RuntimeError('ตรวจเฟรม FFmpeg ไม่สำเร็จ: ' + exc.stderr.decode(errors='replace')[-500:]) from exc
        http_result = segment_frame_interactive(str(output / 'source.png'), 0,
                                                [{'x': .5, 'y': 200 / 480, 'label': 1}],
                                                width=360, height=480)
        assert http_result['ok'] and http_result['contours'] and http_result['bbox']
        warm_http_result = segment_frame_interactive(str(output / 'source.png'), 0,
                                                     [{'x': .5, 'y': 200 / 480, 'label': 1}],
                                                     width=360, height=480)
        print(json.dumps({'cuda': torch.cuda.is_available(), 'initial_scores': scores.tolist(),
                          'initial_areas': areas.tolist(), 'calls': recorder.calls, 'before_area': int(previous.sum()),
                          'after_area': int(current.sum()), 'score': score, 'warm_predict_ms': round(elapsed, 1),
                          'before_iou': round(before_iou, 6), 'after_iou': round(after_iou, 6),
                          'frame': str(output / 'frame.png'), 'synthetic_only': True,
                          'http_bbox': http_result['bbox'], 'http_predict_ms': http_result['predict_ms'],
                          'http_warm_predict_ms': warm_http_result['predict_ms']}))
        # Keep the frame alive only until the reviewer has inspected it.
        input('Inspect frame, then press Enter to clean all probe artifacts: ')
    print('Probe artifacts cleaned: 100%')


if __name__ == '__main__':
    main()
