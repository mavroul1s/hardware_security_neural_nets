"""Coordinate consistency controls for shifted feature-normalized observations."""
import importlib.util
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "notebooks"))
spec = importlib.util.spec_from_file_location("paper_alignment_coordinates", ROOT / "notebooks/paper_alignment_coordinates.py")
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)
from paper_alignment import corruption_pipelines, fit_template
from audit_correlation_robustness import selected_product


def test_coordinate_consistent_oracle_preserves_centered_product_under_both_pipeline_orders():
    rng = np.random.default_rng(42)
    training = rng.normal(size=(50, 80)) * np.arange(1, 81) + np.arange(80) ** 2
    x = training[:7]
    minimum = training.min(axis=0)
    scale = training.max(axis=0) - minimum
    shifts = np.arange(-3, 4)
    pair = [25, 55]
    pipelines, _ = corruption_pipelines(x, minimum, scale, shifts, np.zeros_like(x))
    raw_mean = training.mean(axis=0)
    expected = (x[:, pair[0]] - raw_mean[pair[0]]) * (x[:, pair[1]] - raw_mean[pair[1]])
    for pipeline in pipelines:
        values, template = experiment.coordinate_domain(pipelines[pipeline], training, minimum, scale, pipeline)
        actual = selected_product(values, template["mean"], pair, shifts)
        factor = scale[pair[0]] * scale[pair[1]] if pipeline == "feature_shift_surrogate" else 1.
        np.testing.assert_allclose(actual * factor, expected, atol=1e-9, rtol=1e-12)


def test_wrong_raw_center_on_feature_shifted_data_is_not_an_oracle_upper_bound():
    training = np.arange(320, dtype=float).reshape(4, 80) * np.arange(1, 81)
    minimum, scale = training.min(axis=0), np.maximum(training.max(axis=0) - training.min(axis=0), 1.)
    x, shifts = training[:2], np.array([2, -2])
    pipelines, _ = corruption_pipelines(x, minimum, scale, shifts, np.zeros_like(x))
    wrong = selected_product(pipelines["feature_shift_surrogate"], fit_template(training)["mean"], [25, 55], shifts)
    values, template = experiment.coordinate_domain(pipelines["feature_shift_surrogate"], training, minimum, scale, "feature_shift_surrogate")
    correct = selected_product(values, template["mean"], [25, 55], shifts) * scale[25] * scale[55]
    assert not np.allclose(wrong, correct)
