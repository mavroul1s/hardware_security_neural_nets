"""Arithmetic and state-isolation checks for the fixed-weight CPU diagnosis."""
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest
import torch
from torch import nn

original_path = sys.path[:]
sys.path.insert(0, str(Path(__file__).parents[1] / "notebooks"))
spec = importlib.util.spec_from_file_location("literature_diagnostics", Path(__file__).parents[1] / "notebooks/diagnose_literature.py")
diagnostic = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(diagnostic)
finally:
    sys.path[:] = original_path


def test_ce_and_shuffled_alignment_have_correct_direction():
    lp = np.log([[.9, .1], [.1, .9]])
    labels = np.array([0, 1])
    metrics = diagnostic.classification_metrics(lp, labels)
    assert metrics["cross_entropy"] == pytest.approx(-np.log(.9))
    assert metrics["accuracy"] == 1
    result = diagnostic.shuffled_alignment(lp, labels, [np.array([1, 0])])
    assert result["mean_alignment_gain"] == pytest.approx(np.log(9))
    with pytest.raises(ValueError):
        diagnostic.classification_metrics(lp, labels[:1])


def test_streamed_channel_moments_reduce_batch_and_time_not_channels():
    model = nn.Sequential(nn.Unflatten(1, (1, 4)), nn.Identity(), nn.Identity(), nn.BatchNorm1d(1))
    data = np.arange(12, dtype=np.float32).reshape(3, 4)
    mean, variance, count = diagnostic.channel_moments(model, data, batch_size=2)
    assert count == 12
    assert mean.item() == pytest.approx(5.5)
    assert variance.item() == pytest.approx(143 / 12)


def test_bn_counterfactual_keeps_original_buffers_and_all_weights():
    model = nn.Sequential(nn.Unflatten(1, (1, 4)), nn.Identity(), nn.Identity(), nn.BatchNorm1d(1))
    model.eval()
    original = {k:v.clone() for k,v in model.state_dict().items()}
    data = np.arange(12, dtype=np.float32).reshape(3, 4)
    clone, _, _, _ = diagnostic.training_moment_counterfactual(model, data)
    assert clone[3].running_mean.item() == pytest.approx(5.5)
    assert clone[3].running_var.item() == pytest.approx(13)
    assert all(torch.equal(v, model.state_dict()[k]) for k,v in original.items())
    assert all(torch.equal(p, q) for p,q in zip(model.parameters(), clone.parameters()))
    assert not clone.training


def test_prefix_correlation_matches_direct_centered_arithmetic_and_ties():
    correlation_spec = importlib.util.spec_from_file_location("correlation_diagnostic",
        Path(__file__).parents[1] / "notebooks/diagnose_second_order_correlation.py")
    correlation = importlib.util.module_from_spec(correlation_spec)
    correlation_spec.loader.exec_module(correlation)
    x = np.array([3., 1., 5., 2., 8.])
    hypotheses = np.stack([x, -x, np.ones(5), np.array([2., 4., 1., 7., 3.])], axis=1)
    result = correlation.prefix_correlations(x, hypotheses)
    assert np.array_equal(result[0], np.zeros(4))
    for stop in range(2, 6):
        for column in (0, 1, 3):
            assert result[stop - 1, column] == pytest.approx(np.corrcoef(x[:stop], hypotheses[:stop, column])[0, 1])
    assert np.array_equal(result[:, 2], np.zeros(5))
    assert correlation.conservative_absolute_ranks(result, 0).tolist() == [3, 2, 1, 1, 1]
