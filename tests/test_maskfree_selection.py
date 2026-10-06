"""Correctness checks for training-label-only second-order pair selection."""
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "notebooks"))
spec = importlib.util.spec_from_file_location("paper_maskfree_selection", ROOT / "notebooks/paper_maskfree_selection.py")
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)


def test_matrix_product_correlations_match_independent_pearson_for_every_pair():
    rng = np.random.default_rng(31)
    x = rng.normal(size=(120, 12))
    labels = rng.integers(0, 9, size=len(x))
    observed = experiment.pair_correlations(x, labels)
    centered = x - x.mean(axis=0)
    expected = np.array([[np.corrcoef(centered[:, i] * centered[:, j], labels)[0, 1]
                          for j in range(x.shape[1])] for i in range(x.shape[1])])
    np.testing.assert_allclose(observed, expected, atol=1e-13, rtol=1e-12)


def test_pair_selection_respects_signed_scores_separation_and_point_diversity():
    scores = np.zeros((80, 80))
    scores[0, 1] = 1.  # Ineligible near-diagonal decoy.
    scores[5, 60] = -.9
    scores[6, 61] = .8  # Too close to the selected first pair.
    scores[25, 79] = .7
    pairs, count = experiment.select_pairs(scores, separation=40, diversity=15)
    assert pairs == {"pair1": [5, 60], "pair2": [25, 79]}
    assert count == 820


def test_constant_targets_and_invalid_selection_inputs_are_rejected():
    with pytest.raises(ValueError, match="Constant target"):
        experiment.pair_correlations(np.ones((10, 80)), np.ones(10))
    with pytest.raises(ValueError):
        experiment.pair_correlations(np.ones((10, 80)), np.ones(9))
    with pytest.raises(ValueError):
        experiment.select_pairs(np.zeros((4, 5)))
