import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "notebooks"))
from paper_window_regression import (FEATURES, window_columns, noise_product_covariance,
    fit_weights, extract_features, orient_weight, bootstrap_difference)
from paper_alignment import shifted


def test_product_noise_covariance_exact_conditional_monte_carlo():
    rng = np.random.default_rng(62)
    a, b = rng.normal(size=(400, 2)), rng.normal(size=(400, 3))
    a -= a.mean(axis=0); b -= b.mean(axis=0)
    sigma = .7
    q = (a[:, :, None] * b[:, None, :]).reshape(400, 6)
    expected = np.cov(q, rowvar=False, bias=True) + noise_product_covariance(a, b, sigma)
    # Repeat every fixed training row equally; only added noise is random.
    aa, bb = np.repeat(a, 1000, axis=0), np.repeat(b, 1000, axis=0)
    p = ((aa + sigma * rng.normal(size=aa.shape))[:, :, None] *
         (bb + sigma * rng.normal(size=bb.shape))[:, None, :]).reshape(len(aa), 6)
    np.testing.assert_allclose(np.cov(p, rowvar=False, bias=True), expected, atol=.02, rtol=.02)
    np.testing.assert_array_equal(noise_product_covariance(a, b, 0), np.zeros((6, 6)))


def test_noise_objective_equals_expected_squared_loss():
    rng = np.random.default_rng(64)
    a, b = rng.normal(size=(700, 2)), rng.normal(size=(700, 2))
    a -= a.mean(0); b -= b.mean(0)
    p = (a[:, :, None] * b[:, None, :]).reshape(len(a), 4)
    y, w, sigma = rng.normal(size=len(a)), rng.normal(size=4), .5
    expected = np.mean((p @ w - y) ** 2) + w @ noise_product_covariance(a, b, sigma) @ w
    aa, bb, yy = np.repeat(a, 600, 0), np.repeat(b, 600, 0), np.repeat(y, 600)
    noisy = ((aa + sigma * rng.normal(size=aa.shape))[:, :, None] *
             (bb + sigma * rng.normal(size=bb.shape))[:, None, :]).reshape(len(aa), 4)
    assert np.mean((noisy @ w - yy) ** 2) == pytest.approx(expected, rel=.015)


def test_window_feature_point_box_and_diagonal_reference():
    rng = np.random.default_rng(9); x = rng.normal(size=(200, 80))
    y = (x[:, 15] - x[:, 15].mean()) * (x[:, 55] - x[:, 55].mean())
    weights, stats, moments = fit_weights(x, y, [15, 55], radius=2, sigma=.4)
    extracted = extract_features(x, x.mean(0), [15, 55], 2, np.zeros(len(x), dtype=int), weights)
    a = x[:, 13:18] - x.mean(0)[13:18]; b = x[:, 53:58] - x.mean(0)[53:58]
    candidates = [a[:, 2] * b[:, 2], a.mean(1) * b.mean(1), np.mean(a * b, axis=1)]
    for j, raw in enumerate(candidates):
        # Weight normalization and training orientation can change scale/sign only.
        assert abs(np.corrcoef(raw, extracted[:, j])[0, 1]) == pytest.approx(1.)
    assert stats["training_correlations"]["point"] == pytest.approx(1.)
    assert np.linalg.eigvalsh(moments["noise_covariance"]).min() > 0


def test_alignment_reads_original_training_centers_and_never_border_padding():
    rng = np.random.default_rng(2); x = rng.normal(size=(30, 80)); y = x[:, 15] * x[:, 55]
    w, _, _ = fit_weights(x, y, [15, 55], radius=2)
    delta = np.resize(np.arange(-5, 6), len(x))
    ref = extract_features(x, x.mean(0), [15, 55], 2, np.zeros(len(x), dtype=int), w)
    for padding in ("zero", "edge"):
        actual = extract_features(shifted(x, delta, padding), x.mean(0), [15, 55], 2, delta, w)
        np.testing.assert_allclose(actual, ref, atol=1e-12)


def test_zero_noise_ridge_identity_and_rank1_covariance_solution():
    rng = np.random.default_rng(99); x = rng.normal(size=(300, 80)); y = x[:, 15] * x[:, 55]
    w, _, moments = fit_weights(x, y, [15, 55], radius=2, sigma=0)
    np.testing.assert_array_equal(w["ridge_noise"], w["ridge_clean"])
    c = moments["target_covariance"].reshape(5, 5)
    assert np.linalg.matrix_rank(w["covariance_rank1"].reshape(5, 5), tol=1e-10) == 1
    assert np.sum(c * w["covariance_rank1"].reshape(5, 5)) == pytest.approx(np.linalg.svd(c, compute_uv=False)[0])


def test_ridge_follows_normal_equations_with_scaled_noise_increment():
    rng = np.random.default_rng(100); x = rng.normal(size=(300, 80)); y = x[:, 15] * x[:, 55]
    w, _, m = fit_weights(x, y, [15, 55], radius=2, sigma=.8)
    for name, increment in (("ridge_clean", 0), ("ridge_noise", m["noise_covariance"])):
        matrix = m["product_covariance"] + increment + .01 * np.diag(m["product_scale"] ** 2)
        residual_direction = matrix @ w[name]
        assert abs(np.corrcoef(residual_direction, m["target_covariance"])[0, 1]) == pytest.approx(1.)


def test_paired_bootstrap_identical_feature_difference_zero():
    rng = np.random.default_rng(101); a, y = rng.normal(size=(2, 200))
    draws, state = bootstrap_difference(a, a, y, count=65)
    np.testing.assert_array_equal(draws, np.zeros(65))
    other, other_state = bootstrap_difference(a, a, y, count=65)
    np.testing.assert_array_equal(other, draws); assert state == other_state


def test_invalid_windows_offsets_and_degenerate_fit():
    for pair in ([0, 50], [10, 12], [10, 79]):
        with pytest.raises(ValueError): window_columns(pair, 2, 80)
    with pytest.raises(ValueError): noise_product_covariance(np.zeros((3, 2)), np.zeros((4, 2)), .5)
    with pytest.raises(ValueError): fit_weights(np.ones((5, 80)), np.ones(5), [15, 55])
    with pytest.raises(ValueError): orient_weight(np.zeros(4), np.ones((5, 4)), np.arange(5))
    with pytest.raises(ValueError): extract_features(np.ones((5, 80)), np.ones(80), [15, 55], 2, np.ones(5) * 2, {})
