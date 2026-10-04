"""Offline product/part segmentation contracts; no model or real assets."""
import numpy as np
import pytest

from scripts.interactive_sam2_assembly import predict_product_mask


def rectangle(start, end):
    mask = np.zeros((100, 100), dtype=bool)
    mask[start:end, start:end] = True
    return mask


class Predictor:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = []

    def predict(self, **kwargs):
        self.calls.append(kwargs)
        masks, scores = next(self.responses)
        return np.array(masks), np.array(scores), None


def test_one_click_expands_fan_part_to_case():
    part, product = rectangle(35, 65), rectangle(30, 70)
    predictor = Predictor(([part], [0.96]), ([part, product], [0.97, 0.93]))
    mask, score = predict_product_mask(predictor, [[50, 50]], [1])
    assert np.array_equal(mask, product)
    assert score == 0.93
    assert len(predictor.calls) == 2
    assert predictor.calls[1]["box"].tolist() == [29, 29, 70, 70]


def test_joint_case_and_center_proposal_can_replace_ring():
    ring, product = rectangle(30, 70), rectangle(30, 70)
    ring[40:60, 40:60] = False
    predictor = Predictor(([ring], [0.95]), ([product], [0.94]))
    mask, _ = predict_product_mask(predictor, [[35, 35]], [1])
    assert mask[50, 50]
    assert np.array_equal(mask, product)


def test_box_casing_assembles_only_enclosed_seed_region():
    hub = rectangle(47, 53)
    hint = rectangle(30, 70)
    shell = hint.copy()
    shell[35:65, 35:65] = False
    shell[31:33, 31:33] = False  # Separate unselected hole must stay open.
    predictor = Predictor(([hub, hint], [0.96, 0.1]), ([shell], [0.90]))
    mask, _ = predict_product_mask(predictor, [[50, 50]], [1])
    assert mask[50, 50]
    assert mask[40, 40]
    assert not mask[31, 31]
    assert mask.sum() == hint.sum() - 4


def test_open_casing_does_not_fill_exterior_background():
    hub, hint = rectangle(47, 53), rectangle(30, 70)
    shell = hint.copy()
    shell[35:65, 35:65] = False
    shell[30:40, 49:52] = False
    predictor = Predictor(([hub, hint], [0.96, 0.1]), ([shell], [0.90]))
    mask, _ = predict_product_mask(predictor, [[50, 50]], [1])
    assert np.array_equal(mask, hub)


@pytest.mark.parametrize('bad', ['full_frame', 'outside_box', 'low_quality', 'lost_seed', 'missed_click'])
def test_bad_expansion_keeps_original_product(bad):
    seed = rectangle(35, 65)
    candidate = rectangle(30, 70)
    score = 0.94
    if bad == 'full_frame':
        candidate[:] = True
    elif bad == 'outside_box':
        candidate = rectangle(25, 75)
    elif bad == 'low_quality':
        score = 0.60
    elif bad == 'lost_seed':
        candidate[35:48, 35:65] = False
    else:
        candidate[50, 50] = False
    predictor = Predictor(([seed], [0.96]), ([candidate], [score]))
    mask, result_score = predict_product_mask(predictor, [[50, 50]], [1])
    assert np.array_equal(mask, seed)
    assert result_score == 0.96


def test_large_low_quality_background_does_not_win_initial_selection():
    part = rectangle(35, 65)
    background = rectangle(10, 90)
    predictor = Predictor(([part, background], [0.96, 0.70]), ([part], [0.96]))
    mask, _ = predict_product_mask(predictor, [[50, 50]], [1])
    assert np.array_equal(mask, part)


def test_large_proposal_guides_box_but_requires_new_credible_mask():
    hub, noisy_product, product = rectangle(47, 53), rectangle(30, 70), rectangle(28, 72)
    predictor = Predictor(([hub, noisy_product], [0.96, 0.10]), ([product], [0.94]))
    mask, _ = predict_product_mask(predictor, [[50, 50]], [1])
    assert np.array_equal(mask, product)
    assert predictor.calls[1]['box'].tolist() == [22, 22, 77, 77]


def test_negative_point_and_real_hole_are_preserved_without_box_or_fill():
    product = rectangle(30, 70)
    product[45:55, 45:55] = False
    predictor = Predictor(([product], [0.94]))
    mask, _ = predict_product_mask(predictor, [[35, 35], [50, 50]], [1, 0])
    assert np.array_equal(mask, product)
    assert len(predictor.calls) == 1
    assert not predictor.calls[0]['multimask_output']


def test_product_plus_hand_stays_on_joint_prompt_path():
    product = rectangle(30, 60)
    product[55:80, 55:70] = True
    predictor = Predictor(([product], [0.94]))
    mask, _ = predict_product_mask(predictor, [[40, 40], [65, 70]], [1, 1])
    assert np.array_equal(mask, product)
    assert len(predictor.calls) == 1


@pytest.mark.parametrize('kind', ['empty', 'full_frame', 'nan', 'negative_violation'])
def test_no_credible_mask_returns_empty_without_refinement(kind):
    candidate = rectangle(30, 70)
    labels, score = [1], 0.95
    if kind == 'empty':
        candidate[:] = False
    elif kind == 'full_frame':
        candidate[:] = True
    elif kind == 'nan':
        score = float('nan')
    else:
        labels = [0]
    predictor = Predictor(([candidate], [score]))
    mask, result_score = predict_product_mask(predictor, [[50, 50]], labels)
    assert not mask.any()
    assert result_score == 0
    assert len(predictor.calls) == 1


def test_edge_click_expansion_is_clipped_to_frame():
    seed = np.zeros((100, 100), dtype=bool)
    seed[:30, :30] = True
    predictor = Predictor(([seed], [0.95]), ([seed], [0.95]))
    mask, _ = predict_product_mask(predictor, [[0, 0]], [1])
    assert np.array_equal(mask, seed)
    assert predictor.calls[1]['box'].tolist() == [0, 0, 35, 35]
