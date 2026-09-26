"""Bounded-memory, motion-compensated alpha refinement (opt-in).

Flow is estimated on RGB, never on a mask: a stable but incorrect mask must not
make the motion estimate appear accurate. Disocclusions and hard cuts use the
current segmentation unchanged. No morphology is applied to the output alpha.
"""
from __future__ import annotations

import cv2
import numpy as np


class TemporalAlphaRefiner:
    def __init__(self, *, max_flow_side: int = 320, history_weight: float = 0.55):
        self.max_flow_side = max_flow_side
        self.history_weight = history_weight
        self.previous_gray = self.previous_alpha = None
        self.previous_pts = None
        self.revision = None
        self.stats = {"frames": 0, "resets": 0, "blended_pixels": 0, "edge_pixels": 0}

    def refine(self, rgb: np.ndarray, alpha: np.ndarray, *, pts: float,
               fps: float, revision: str = "default") -> np.ndarray:
        if rgb.shape[:2] != alpha.shape or rgb.ndim != 3 or rgb.shape[2] != 3:
            raise ValueError("RGB and alpha dimensions must agree")
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        height, width = alpha.shape
        scale = min(1.0, self.max_flow_side / max(height, width))
        small = cv2.resize(gray, (max(8, round(width * scale)), max(8, round(height * scale))), interpolation=cv2.INTER_AREA)
        current = alpha.astype(np.float32) / 255.0
        reset = (self.previous_gray is None or self.previous_gray.shape != small.shape
                 or self.previous_alpha.shape != alpha.shape or self.revision != revision
                 or self.previous_pts is None or abs(pts - self.previous_pts - 1 / fps) > 0.5 / fps)
        if not reset:
            difference = np.abs(small.astype(np.float32) - self.previous_gray.astype(np.float32))
            # Hard-cut detection precedes flow. Large appearance changes must
            # not drag the old subject into a new scene.
            hist_old = cv2.calcHist([self.previous_gray], [0], None, [32], [0, 256])
            hist_new = cv2.calcHist([small], [0], None, [32], [0, 256])
            distance = cv2.compareHist(hist_old, hist_new, cv2.HISTCMP_BHATTACHARYYA)
            reset = float(difference.mean()) > 45 or distance > 0.65
        self.stats["frames"] += 1
        output = current
        if reset:
            self.stats["resets"] += 1
        else:
            forward = cv2.calcOpticalFlowFarneback(self.previous_gray, small, None, .5, 3, 21, 3, 5, 1.2, 0)
            backward = cv2.calcOpticalFlowFarneback(small, self.previous_gray, None, .5, 3, 21, 3, 5, 1.2, 0)
            sh, sw = small.shape
            sy, sx = np.mgrid[:sh, :sw].astype(np.float32)
            bx, by = sx + backward[..., 0], sy + backward[..., 1]
            forward_at_previous = cv2.remap(forward, bx, by, cv2.INTER_LINEAR)
            cycle_error = np.linalg.norm(backward + forward_at_previous, axis=2)
            warped_gray = cv2.remap(self.previous_gray, bx, by, cv2.INTER_LINEAR)
            photo_error = np.abs(warped_gray.astype(np.float32) - small.astype(np.float32))
            reliable = ((cycle_error < 1) & (photo_error < 20)
                        & (bx >= 0) & (by >= 0) & (bx < sw - 1) & (by < sh - 1))
            flow = cv2.resize(backward, (width, height), interpolation=cv2.INTER_LINEAR)
            flow[..., 0] *= width / sw
            flow[..., 1] *= height / sh
            yy, xx = np.mgrid[:height, :width].astype(np.float32)
            history = cv2.remap(self.previous_alpha, xx + flow[..., 0], yy + flow[..., 1], cv2.INTER_LINEAR)
            valid = cv2.resize(reliable.astype(np.uint8), (width, height), interpolation=cv2.INTER_NEAREST).astype(bool)
            edge = (current > .02) & (current < .98)
            # Never invent alpha in an empty pixel or erode solid fine detail.
            blend = valid & edge & (history > .02) & (history < .98) & (np.abs(current - history) < .2)
            output = np.where(blend, current * (1 - self.history_weight) + history * self.history_weight, current)
            self.stats["edge_pixels"] += int(edge.sum())
            self.stats["blended_pixels"] += int(blend.sum())
        self.previous_gray = small
        self.previous_alpha = output
        self.previous_pts = pts
        self.revision = revision
        return np.rint(output * 255).clip(0, 255).astype(np.uint8)
