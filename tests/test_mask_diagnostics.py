"""Independent arithmetic checks for the read-only leakage diagnostic."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location("mask_diagnostics", Path(__file__).parents[1] / "notebooks/diagnose_masking.py")
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


def test_weighted_snr_matches_hand_calculation_for_unequal_class_sizes():
    # Class0: mean1, variance1, weight1/3. Class1: mean5, variance5, weight2/3.
    # Between32/9, within11/3; SNR32/33. An unweighted class average is different.
    x = np.array([0., 2., 2., 4., 6., 8.])[:, None]
    labels = np.array([0, 0, 1, 1, 1, 1])
    assert diagnostic.weighted_snr(x, labels)[0] == pytest.approx(32 / 33)
    assert diagnostic.weighted_snr(4 * x + 17, labels)[0] == pytest.approx(32 / 33)
    assert diagnostic.weighted_snr(np.ones_like(x), labels)[0] == 0
    with pytest.raises(ValueError):
        diagnostic.weighted_snr(x, labels[:-1])


def test_selected_points_are_separated_and_reproducible():
    values = np.array([0., 10., 8., 6., 9., 7., 0., 5., 4.])
    assert diagnostic.select_separated_points(values, count=3, separation=3) == [1, 4, 7]
    with pytest.raises(ValueError):
        diagnostic.select_separated_points(values, count=4, separation=3)
