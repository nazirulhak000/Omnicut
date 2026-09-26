import cv2
import numpy as np

from scripts.cutout_temporal import TemporalAlphaRefiner


def fixture():
    rng = np.random.default_rng(481)
    rgb = rng.integers(0, 256, (96, 96, 3), dtype=np.uint8)
    alpha = np.zeros((96, 96), np.uint8)
    cv2.rectangle(alpha, (20, 16), (76, 80), 255, -1)
    cv2.circle(alpha, (48, 40), 10, 0, -1)  # real hole must survive
    alpha = cv2.GaussianBlur(alpha, (5, 5), .8)
    return rgb, alpha


def test_stationary_soft_edge_flicker_reduces_without_changing_solid_detail():
    rgb, truth = fixture()
    refiner = TemporalAlphaRefiner()
    rng = np.random.default_rng(42)
    edge = (truth > 20) & (truth < 235)
    before, after = [], []
    for index in range(60):
        noise = rng.integers(-14, 15, truth.shape)
        noisy = np.where(edge, np.clip(truth.astype(int) + noise, 0, 255), truth).astype(np.uint8)
        result = refiner.refine(rgb, noisy, pts=index / 30, fps=30)
        before.append(noisy.astype(float))
        after.append(result.astype(float))
        assert np.array_equal(result[~edge], truth[~edge])
    raw_mae = np.abs(np.diff(before, axis=0))[:, edge].mean()
    refined_mae = np.abs(np.diff(after, axis=0))[:, edge].mean()
    assert refined_mae < raw_mae * .7, (raw_mae, refined_mae)
    assert refiner.stats["blended_pixels"] > 0


def test_translation_keeps_holes_and_does_not_leave_ghosts():
    rgb, truth = fixture()
    refiner = TemporalAlphaRefiner()
    for i in range(12):
        transform = np.float32([[1, 0, i], [0, 1, 0]])
        image = cv2.warpAffine(rgb, transform, (96, 96))
        alpha = cv2.warpAffine(truth, transform, (96, 96))
        result = refiner.refine(image, alpha, pts=i / 30, fps=30)
        assert np.array_equal(result[alpha == 0], alpha[alpha == 0])
        assert np.array_equal(result[alpha == 255], alpha[alpha == 255])
        assert (np.abs(result.astype(float) - alpha)[(alpha > 0) & (alpha < 255)]).mean() < 4


def test_cut_empty_frame_discontinuity_and_prompt_revision_reset_history():
    rgb, alpha = fixture()
    refiner = TemporalAlphaRefiner()
    refiner.refine(rgb, alpha, pts=0, fps=30)
    empty = np.zeros_like(alpha)
    assert not refiner.refine(np.zeros_like(rgb), empty, pts=1 / 30, fps=30).any()
    changed = np.clip(alpha.astype(int) - 10, 0, 255).astype(np.uint8)
    assert np.array_equal(refiner.refine(rgb, changed, pts=5, fps=30), changed)
    assert np.array_equal(refiner.refine(rgb, alpha, pts=5 + 1 / 30, fps=30, revision="edit"), alpha)
    assert refiner.stats["resets"] == 4
