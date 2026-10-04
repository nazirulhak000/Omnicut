"""Bounded whole-object refinement for a cached SAM2 image predictor.

SAM2's point proposals can describe a part or its enclosing object. Prefer a
credible enclosing proposal, then ask once with an expanded box. Assemble only
an enclosed interior containing the positive seed; other holes stay unchanged.
This module deliberately has no torch/SAM2 imports for offline contract tests.
"""
from __future__ import annotations

import cv2
import numpy as np


def _candidates(masks, scores, coords, labels, *, minimum_score=0.65):
    """Discard empty, low quality, frame-sized, or prompt-violating masks."""
    masks = np.asarray(masks) > 0
    height, width = masks.shape[-2:]
    pixels = np.floor(coords).astype(int)
    pixels[:, 0] = np.clip(pixels[:, 0], 0, width - 1)
    pixels[:, 1] = np.clip(pixels[:, 1], 0, height - 1)
    candidates = []
    for mask, score in zip(masks, scores):
        area = int(mask.sum())
        if not np.isfinite(score) or score < minimum_score or not 0 < area < width * height * 0.85:
            continue
        if not np.all(mask[pixels[:, 1], pixels[:, 0]] == (labels == 1)):
            continue
        candidates.append((mask, float(score)))
    if candidates and minimum_score > 0:
        highest_score = max(score for _, score in candidates)
        candidates = [(mask, score) for mask, score in candidates if score >= highest_score - 0.15]
    return candidates


def predict_product_mask(predictor, coords, labels):
    """Return a mask and its score; at most two decoder calls for one click.

Keep multi-point correction on SAM2's normal joint-prompt path. A rejected
box refinement falls back to the original proposal, never to a full-frame mask.
"""
    coords = np.asarray(coords, dtype=np.float32)
    labels = np.asarray(labels, dtype=np.int32)
    single_positive = len(coords) == 1 and labels[0] == 1
    masks, scores, _ = predictor.predict(
        point_coords=coords, point_labels=labels, multimask_output=single_positive,
    )
    candidates = _candidates(masks, scores, coords, labels)
    if not candidates:
        return np.zeros(np.asarray(masks).shape[-2:], dtype=bool), 0.0
    seed, seed_score = max(candidates, key=lambda item: int(item[0].sum()))
    if not single_positive:
        return seed, seed_score

    # Low-quality enclosing proposals are hints, never accepted masks. They let
    # a high-confidence hub/label seed reach the product's housing in one call.
    hints = [(mask, score) for mask, score in _candidates(masks, scores, coords, labels, minimum_score=0)
             if int((mask & seed).sum()) >= seed.sum() * 0.95]
    extent = max(hints, key=lambda item: int(item[0].sum()))[0] if hints else seed
    ys, xs = np.where(extent)
    height, width = seed.shape
    # Twenty percent per side lets a part proposal include its surrounding case.
    pad_x = max(4.0, (xs.max() - xs.min() + 1) * 0.20)
    pad_y = max(4.0, (ys.max() - ys.min() + 1) * 0.20)
    box = np.array([max(0, xs.min() - pad_x), max(0, ys.min() - pad_y),
                    min(width - 1, xs.max() + pad_x), min(height - 1, ys.max() + pad_y)],
                   dtype=np.float32)
    # Repeating a hub click here can keep SAM2 locked onto the hub even with a
    # box. A box-only proposal asks for the enclosing object; validate the
    # user's original point and seed against the resulting mask below.
    masks, scores, _ = predictor.predict(box=box, multimask_output=False)
    assembled = []
    for proposal in masks:
        mask = np.asarray(proposal) > 0
        # A box can select the casing while excluding its center. Only restore
        # the enclosed background component containing the confident seed.
        # Exterior background (including open gaps) is never flood-filled.
        _, regions = cv2.connectedComponents((~mask).astype(np.uint8), connectivity=8)
        px = int(np.clip(coords[0, 0], 0, width - 1))
        py = int(np.clip(coords[0, 1], 0, height - 1))
        region = int(regions[py, px])
        boundary = np.concatenate((regions[0], regions[-1], regions[:, 0], regions[:, -1]))
        if region and region not in boundary:
            interior = regions == region
            if int((interior & seed).sum()) >= seed.sum() * 0.95:
                mask = mask | interior
        assembled.append(mask)
    seed_area = int(seed.sum())
    refinements = []
    for mask, score in _candidates(assembled, scores, coords, labels):
        area = int(mask.sum())
        if area < seed_area or score < seed_score - 0.15:
            continue
        if int((mask & seed).sum()) < seed_area * 0.95:
            continue
        my, mx = np.where(mask)
        if mx.min() < box[0] or mx.max() > box[2] or my.min() < box[1] or my.max() > box[3]:
            continue
        refinements.append((mask, score))
    return max(refinements, key=lambda item: int(item[0].sum())) if refinements else (seed, seed_score)
