"""Arithmetic, label-free alignment and isolation checks on synthetic fixtures."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "notebooks"))
spec = importlib.util.spec_from_file_location("paper_alignment", ROOT / "notebooks/paper_alignment.py")
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)


def test_non_circular_offsets_have_correct_sign_and_padding():
    x = np.array([[1., 2., 3., 4., 5.], [1., 2., 3., 4., 5.]])
    np.testing.assert_array_equal(experiment.shifted(x, np.array([2, -2])),
                                  [[0., 0., 1., 2., 3.], [3., 4., 5., 0., 0.]])
    with pytest.raises(ValueError):
        experiment.shifted(x, np.array([5, 0]))


def test_position_scaler_does_not_commute_and_transport_restores_raw_shift():
    x = np.arange(16, dtype=float).reshape(2, 8)
    minimum, scale = np.arange(8, dtype=float), np.arange(1, 9, dtype=float)
    offsets = np.array([1, -1])
    for padding in ("zero", "edge"):
        pipelines, transported = experiment.corruption_pipelines(x, minimum, scale, offsets, np.ones_like(x), padding)
        np.testing.assert_allclose(transported, pipelines["raw_shift"], atol=1e-14)
        assert not np.allclose(pipelines["raw_shift"][:, 1:-1], pipelines["feature_shift_surrogate"][:, 1:-1])


def test_scalar_affine_transform_commutes_interior_but_padding_requires_transport():
    x = np.arange(16, dtype=float).reshape(2, 8)
    pipelines, transported = experiment.corruption_pipelines(x, np.full(8, -3.), np.full(8, 2.),
                                                            np.array([1, -1]), np.zeros_like(x))
    np.testing.assert_array_equal(pipelines["raw_shift"][:, 1:-1], pipelines["feature_shift_surrogate"][:, 1:-1])
    assert not np.array_equal(pipelines["raw_shift"], pipelines["feature_shift_surrogate"])
    np.testing.assert_array_equal(transported, pipelines["raw_shift"])


@pytest.mark.parametrize("method", ["ncc_template", "gaussian_template"])
def test_trace_only_estimator_recovers_positive_and_negative_offsets_without_border_cues(method):
    rng = np.random.default_rng(7)
    reference = rng.normal(size=120)
    training = reference + rng.normal(scale=.02, size=(80, 120))
    template = experiment.fit_template(training)
    true_offsets = np.array([-5, -2, 0, 2, 5])
    x = np.broadcast_to(reference, (5, 120)).copy()
    zero, edge = experiment.shifted(x, true_offsets), experiment.shifted(x, true_offsets, "edge")
    estimated, scores = experiment.estimate_offsets(zero, template, method, max_shift=5)
    estimated_edge, scores_edge = experiment.estimate_offsets(edge, template, method, max_shift=5)
    np.testing.assert_array_equal(estimated, true_offsets)
    np.testing.assert_array_equal(estimated_edge, estimated)
    np.testing.assert_array_equal(scores_edge, scores)


@pytest.mark.parametrize("method", ["ncc_template", "gaussian_template"])
def test_constant_waveform_ties_choose_zero_offset(method):
    template = experiment.fit_template(np.ones((20, 80)))
    assert np.all(template["variance"] > 0)
    estimated, _ = experiment.estimate_offsets(np.ones((4, 80)), template, method, max_shift=5)
    np.testing.assert_array_equal(estimated, np.zeros(4))


def test_confirmation_rows_are_reproducible_disjoint_and_do_not_replace_training_budget():
    train, validation = np.arange(20), np.arange(20, 30)
    a = experiment.confirm_indices(train, validation, n_profiling=100, count=15)
    b = experiment.confirm_indices(train, validation, n_profiling=100, count=15)
    np.testing.assert_array_equal(a, b)
    assert not np.intersect1d(a, np.union1d(train, validation)).size
    assert len(a) == len(np.unique(a)) == 15 and np.all(a[:-1] < a[1:])
