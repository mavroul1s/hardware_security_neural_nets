"""Permutation, candidate-domain and holdout isolation correctness checks."""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "notebooks"))
import paper_selection_audit as audit


def test_cached_permutation_matrix_matches_direct_centered_products():
    rng = np.random.default_rng(26)
    x = rng.normal(size=(65, 12))
    x[:, 11] = 1.
    y = rng.integers(0, 9, size=65)
    centered, h, denominator = audit.moment_cache(x, y)
    for order in (np.arange(len(y)), rng.permutation(len(y))):
        matrix = audit.cached_correlations(centered, h[order], denominator)
        for a, b in ((0, 1), (3, 7), (8, 10)):
            direct = np.corrcoef(centered[:, a] * centered[:, b], y[order])[0, 1]
            assert matrix[a, b] == pytest.approx(direct, abs=1e-13)
        assert not matrix[:, 11].any()
    with pytest.raises(ValueError, match="Constant target"):
        audit.moment_cache(x, np.ones(len(x)))


def test_maximum_search_uses_all_eligible_pairs_and_frozen_row_major_ties():
    scores = np.zeros((160, 160))
    scores[0, 159] = 1.
    scores[10, 60] = -.8
    scores[11, 61] = .8
    scores[10, 59] = .99  # Separation49 is ineligible.
    value, pair, count = audit.eligible_maximum(scores, margin=10)
    assert value == .8 and pair == [10, 60] and count == 90 * 91 // 2
    assert audit.eligible_maximum(scores, margin=0)[1] == [0, 159]


def test_randomized_tail_is_nonzero_and_counts_conservative_numerical_ties():
    assert audit.monte_carlo_tail(np.zeros(99), 1.) == .01
    assert audit.monte_carlo_tail(np.ones(99), 1.) == 1.
    assert audit.monte_carlo_tail(np.array([0., 1. - 5e-13, 2.]), 1.) == .75
    with pytest.raises(ValueError):
        audit.monte_carlo_tail(np.array([np.nan]), 1.)


def test_fresh_confirmation_never_reuses_excluded_rows_and_is_deterministic():
    excluded = np.array([1, 3, 5, 7, 7])
    rows = audit.fresh_rows(100, excluded, count=30)
    assert len(rows) == len(np.unique(rows)) == 30
    assert not np.intersect1d(rows, excluded).size
    np.testing.assert_array_equal(rows, audit.fresh_rows(100, excluded, count=30))
    with pytest.raises(ValueError):
        audit.fresh_rows(5, np.arange(5), count=1)


def test_confirmation_product_uses_training_center_and_sign_is_fixed():
    training = np.array([[1., 2.], [3., 4.], [5., 8.]])
    confirmation = np.array([[20., 40.], [24., 42.], [27., 47.]])
    training_mean = training.mean(axis=0)
    product = np.prod(confirmation - training_mean, axis=1)
    confirmation_centered = np.prod(confirmation - confirmation.mean(axis=0), axis=1)
    assert not np.allclose(product, confirmation_centered)
    y = np.array([1., 2., 4.])
    r = audit.correlation(product, y)
    assert r == pytest.approx(np.corrcoef(product, y)[0, 1], abs=1e-14)
    # A negative historical training direction must remain negative-direction evidence.
    assert -r < 0
    assert audit.monte_carlo_tail(np.zeros(9), -r) == 1.
