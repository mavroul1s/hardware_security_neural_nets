"""Independent SAD, reference-selection and correspondence-control correctness checks."""
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "notebooks"))
spec = importlib.util.spec_from_file_location("paper_alignment_controls", ROOT / "notebooks/paper_alignment_controls.py")
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)


def test_sad_matches_independent_scalar_scores_including_both_boundary_offsets():
    rng = np.random.default_rng(35)
    reference = rng.normal(size=700)
    true = np.arange(-10, 11, dtype=np.int16)
    traces = experiment.shifted(np.broadcast_to(reference, (21, 700)), true)
    observed, scores = experiment.sad_offsets(traces, reference)
    assert np.array_equal(observed, true)
    candidates = sorted(range(-10, 11), key=lambda value: (abs(value), value))
    expected = np.array([[sum(abs(float(row[column + offset]) - float(reference[column])) for column in range(20, 680))
                          for offset in candidates] for row in traces])
    np.testing.assert_allclose(scores, expected, atol=1e-12, rtol=1e-14)
    edge = experiment.shifted(np.broadcast_to(reference, (21, 700)), true, "edge")
    np.testing.assert_array_equal(experiment.sad_offsets(edge, reference)[1], scores)


def test_sad_ties_use_zero_first_and_nonfinite_or_invalid_inputs_are_rejected():
    offsets, _ = experiment.sad_offsets(np.ones((3, 700)), np.ones(700))
    assert not offsets.any()
    for traces, reference in ((np.ones((3, 700)), np.ones(699)),
                              (np.full((3, 700), np.nan), np.ones(700))):
        with pytest.raises(ValueError):
            experiment.sad_offsets(traces, reference)


def test_representative_reference_uses_only_fixed_training_window_and_first_tie():
    training = np.zeros((4, 700))
    training[0, :20] = 1000.  # Out-of-window values cannot change the reference choice.
    training[2, 20:680] = 2.
    training[3, 20:680] = 4.
    index, reference, distances = experiment.representative_reference(training)
    assert index == 2
    assert np.array_equal(reference, training[2])
    np.testing.assert_array_equal(distances, [2.25, 2.25, .25, 6.25])
    tied = np.zeros((3, 700))
    assert experiment.representative_reference(tied)[0] == 0


def test_wrong_correspondence_control_preserves_histogram_without_reading_true_offsets():
    offsets = np.array([-10, -2, 0, 3, 10], dtype=np.int16)
    rolled = experiment.roll_offsets(offsets)
    np.testing.assert_array_equal(rolled, [10, -10, -2, 0, 3])
    np.testing.assert_array_equal(np.sort(rolled), np.sort(offsets))
    np.testing.assert_array_equal(offsets, [-10, -2, 0, 3, 10])
    assert not np.shares_memory(offsets, rolled)
    with pytest.raises(ValueError):
        experiment.roll_offsets(np.array([1.5, 2.5]))
