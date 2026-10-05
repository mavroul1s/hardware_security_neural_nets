"""Corruption RNG parity, oracle positioning and interior padding arithmetic."""
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest
import torch
from sca.augment import augment_batch, shift_batch

original_path = sys.path[:]
sys.path.insert(0, str(Path(__file__).parents[1] / "notebooks"))
spec = importlib.util.spec_from_file_location("robustness_audit", Path(__file__).parents[1] / "notebooks/audit_correlation_robustness.py")
audit = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(audit)
finally:
    sys.path[:] = original_path


@pytest.mark.parametrize("noise,shift,padding", [(0.,0,"zero"), (.1,0,"edge"), (0.,2,"zero"), (.2,2,"zero"), (.2,2,"edge")])
def test_recorded_offset_corruption_matches_production_rng_across_batches(noise, shift, padding):
    x = np.arange(55, dtype=np.float32).reshape(5, 11) / 55
    condition = {"noise_std":noise, "max_shift":shift, "padding":padding}
    actual, offsets = audit.corrupt_with_offsets(x, condition, seed=123, batch_size=2)
    generator = torch.Generator().manual_seed(123)
    expected = np.concatenate([augment_batch(torch.from_numpy(x[s:s+2]), **condition, generator=generator).numpy()
                               for s in range(0, len(x), 2)])
    assert np.array_equal(actual, expected)
    assert np.all(np.abs(offsets) <= shift)


def test_oracle_restores_both_points_for_positive_and_negative_non_circular_shifts():
    x = np.arange(30, dtype=np.float32).reshape(3, 10)
    shifts = np.array([-2, 0, 2])
    center = np.arange(10, dtype=np.float64) / 3
    pair = [3, 6]
    corrupted = shift_batch(torch.from_numpy(x), torch.from_numpy(shifts), "zero").numpy()
    expected = (x[:,3] - center[3]) * (x[:,6] - center[6])
    assert np.array_equal(audit.selected_product(corrupted, center, pair, shifts), expected)
    assert not np.array_equal(audit.selected_product(corrupted, center, pair), expected)
    with pytest.raises(ValueError, match="cropped"):
        audit.selected_product(corrupted, center, [0, 9], shifts)


def test_padding_changes_edges_but_not_safe_fixed_or_oracle_products_with_paired_noise():
    x = np.arange(50, dtype=np.float32).reshape(5, 10) + 1
    condition = {"noise_std":.1, "max_shift":2, "padding":"zero"}
    zero, offsets = audit.corrupt_with_offsets(x, condition, seed=6, batch_size=3)
    edge, edge_offsets = audit.corrupt_with_offsets(x, {**condition, "padding":"edge"}, seed=6, batch_size=3)
    assert np.array_equal(offsets, edge_offsets) and not np.array_equal(zero, edge)
    for shifts in (None, offsets):
        assert np.array_equal(audit.selected_product(zero, np.zeros(10), [3,6], shifts),
                              audit.selected_product(edge, np.zeros(10), [3,6], shifts))
