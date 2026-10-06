"""Correctness checks for variable-key isolation, wider traces and interior point selection."""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "notebooks"))
import paper_variable_campaign as experiment


def test_constant_key_guard_rejects_full_key_variation_even_if_target_byte_constant():
    keys = np.zeros((3, 16), dtype=np.uint8)
    keys[:, 2] = 37
    np.testing.assert_array_equal(experiment.constant_evaluation_key(keys), keys[0])
    keys[1, 10] = 1
    with pytest.raises(ValueError, match="Variable attack keys"):
        experiment.constant_evaluation_key(keys)
    with pytest.raises(ValueError):
        experiment.constant_evaluation_key(keys[:, 2])


def test_variable_training_labels_produce_real_centered_product_correlations():
    rng = np.random.default_rng(72)
    plaintext, keys = rng.integers(0, 256, size=(2, 120), dtype=np.uint8)
    labels = experiment.SBOX[plaintext ^ keys]
    target = experiment.HW[labels]
    training = rng.normal(size=(120, 17))
    scores = experiment.pair_correlations(training, target)
    for a, b in ((0, 16), (3, 11), (6, 8)):
        product = (training[:, a] - training[:, a].mean()) * (training[:, b] - training[:, b].mean())
        assert scores[a, b] == pytest.approx(np.corrcoef(product, target)[0, 1], abs=1e-14)
    # Candidate hypotheses depend only on plaintext; the evaluation key is absent.
    hypotheses = experiment.candidate_labels(plaintext)
    for candidate in (0, 37, 255):
        np.testing.assert_array_equal(hypotheses[:, candidate], experiment.SBOX[plaintext ^ candidate])


def test_interior_selection_excludes_border_maxima_and_preserves_diversity():
    scores = np.zeros((1400, 1400))
    for a, b, value in ((0, 1399, 1.), (10, 1389, .8), (40, 1359, -.7)):
        scores[a, b] = scores[b, a] = value
    pairs, count = experiment.interior_pairs(scores)
    assert pairs == {"pair1": [10, 1389], "pair2": [40, 1359]}
    assert count == 1330 * 1331 // 2
    center = np.zeros(1400)
    values = np.ones((2, 1400))
    for pair in pairs.values():
        np.testing.assert_array_equal(experiment.selected_product(values, center, pair, np.array([-10, 10])), [1, 1])


def test_1400_sample_alignment_matches_realized_shift_and_avoids_border_padding():
    rng = np.random.default_rng(73)
    reference = rng.normal(size=1400)
    true_offsets = np.arange(-10, 11, dtype=np.int16)
    original = np.broadcast_to(reference, (21, 1400))
    values = experiment.shifted(original, true_offsets)
    edge = experiment.shifted(original, true_offsets, "edge")
    template = {"mean": reference, "variance": np.ones(1400)}
    for method in ("gaussian_template", "ncc_template"):
        offsets, scores = experiment.estimate_offsets(values, template, method)
        np.testing.assert_array_equal(offsets, true_offsets)
        np.testing.assert_array_equal(scores, experiment.estimate_offsets(edge, template, method)[1])
    np.testing.assert_array_equal(experiment.sad_offsets(values, reference)[0], true_offsets)
