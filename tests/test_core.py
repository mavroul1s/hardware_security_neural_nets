import json
from pathlib import Path

import h5py
import numpy as np
import pytest
import torch

from sca.aes import SBOX, candidate_labels, identity_labels
from sca.augment import augment_batch, shift_batch
from sca.data import (inspect_dataset, make_splits, load_profiling,
                      fit_normalizer, normalize, split_identifier)
from sca.metrics import rank_curve, evaluate_key_recovery
from sca.models import build_model
from sca.synthetic import create_fixture
from sca.train import train
from sca.evaluate import evaluate, evaluate_cached


def test_aes_known_values_and_candidate_mapping():
    assert SBOX[0] == 0x63 and SBOX[0x53] == 0xed and SBOX[0xff] == 0x16
    assert len(np.unique(SBOX)) == 256
    p = np.zeros((3, 16), dtype=np.uint8)
    k = p.copy()
    p[:, 2] = [0, 0x50, 0xff]
    k[:, 2] = [0, 3, 0]
    np.testing.assert_array_equal(identity_labels(p, k), [0x63, 0xed, 0x16])
    candidates = candidate_labels(np.array([0x50], dtype=np.uint8))
    assert candidates[0, 3] == 0xed
    with pytest.raises(ValueError):
        candidate_labels(np.array([-1]))


def test_rank_oracle_and_wrong_key():
    p = np.arange(20, dtype=np.uint8)
    key = 37
    lp = np.full((20, 256), -10000.0)
    lp[np.arange(20), SBOX[p ^ key]] = -0.01
    np.testing.assert_array_equal(rank_curve(lp, p, key), np.zeros(20))
    np.testing.assert_array_equal(rank_curve(lp, p, key + 1), np.full(20, 255))


def test_uniform_ties_never_claim_recovery_and_censoring():
    lp = np.full((10, 256), -np.log(256))
    summary, curves = evaluate_key_recovery(lp, np.arange(10, dtype=np.uint8), 42, budget=10, repetitions=3)
    assert summary["ge_at_budget"] == 255
    assert summary["sr_at_budget"] == 0
    assert summary["traces_to_sustained_success"] is None
    assert summary["recovery_censored"]
    assert curves["ranks"].shape == (3, 10)
    with pytest.raises(ValueError):
        evaluate_key_recovery(lp, np.arange(10, dtype=np.uint8), 42, budget=11)


def test_success_criterion_and_nonfinite_predictions():
    p = np.arange(12, dtype=np.uint8)
    lp = np.full((12, 256), -10.)
    lp[np.arange(12), SBOX[p ^ 5]] = -0.01
    summary, _ = evaluate_key_recovery(lp, p, 5, budget=8, repetitions=4)
    assert summary["sr_at_budget"] == 1 and summary["ge_at_budget"] == 0
    assert summary["traces_to_sustained_success"] == 1 and not summary["recovery_censored"]
    lp[0, 0] = np.nan
    with pytest.raises(ValueError):
        rank_curve(lp, p, 5)


def test_rank_randomization_is_reproducible():
    p = np.arange(20, dtype=np.uint8)
    lp = np.random.default_rng(5).normal(size=(20, 256))
    a = evaluate_key_recovery(lp, p, 33, budget=10, repetitions=5, seed=9)
    b = evaluate_key_recovery(lp, p, 33, budget=10, repetitions=5, seed=9)
    np.testing.assert_array_equal(a[1]["ranks"], b[1]["ranks"])


def test_splits_are_disjoint_nested_and_normalization_uses_training_only():
    train, val = make_splits(100, 30, 10, 42)
    more, val_more = make_splits(100, 60, 10, 42)
    assert not np.intersect1d(train, val).size
    assert set(train).issubset(set(more))
    np.testing.assert_array_equal(val, val_more)
    assert split_identifier(train, val) == split_identifier(train, val)
    stats = fit_normalizer(np.array([[1., 3.], [1., 3.]], dtype=np.float32))
    assert stats["mean"] == 2 and stats["std"] == 1
    assert normalize(np.full((2, 2), 1000, dtype=np.float32), stats).mean() == 998
    with pytest.raises(ValueError):
        make_splits(10, 8, 3, 42)


@pytest.mark.parametrize("shift,expected", [(2, [0, 0, 1, 2, 3]), (-2, [3, 4, 5, 0, 0]), (0, [1, 2, 3, 4, 5])])
def test_shifts_do_not_wrap(shift, expected):
    x = torch.tensor([[1., 2., 3., 4., 5.]])
    actual = shift_batch(x, torch.tensor([shift]))
    torch.testing.assert_close(actual, torch.tensor([expected], dtype=torch.float32))
    torch.testing.assert_close(x, torch.tensor([[1., 2., 3., 4., 5.]]))


def test_edge_padding_and_no_entire_trace_removal():
    x = torch.tensor([[1., 2., 3., 4., 5.]])
    torch.testing.assert_close(shift_batch(x, torch.tensor([2]), "edge"), torch.tensor([[1., 1., 1., 2., 3.]]))
    with pytest.raises(ValueError):
        shift_batch(x, torch.tensor([5]))


def test_noise_units_order_and_reproducibility():
    x = torch.ones(2000, 50)
    actual = augment_batch(x, noise_std=0.2, max_shift=3, generator=torch.Generator().manual_seed(7))
    generator = torch.Generator().manual_seed(7)
    shifts = torch.randint(-3, 4, (2000,), generator=generator)
    expected = shift_batch(x, shifts) + 0.2 * torch.randn(x.shape, generator=generator)
    torch.testing.assert_close(actual, expected)
    noise = actual - shift_batch(x, shifts)
    assert abs(float(noise.mean())) < 0.003 and abs(float(noise.std()) - 0.2) < 0.003


def test_schema_and_bad_label_detection(tmp_path):
    path = tmp_path / "fixture.h5"
    create_fixture(path, n_profiling=32, n_attack=16)
    report = inspect_dataset(path)
    assert report["synthetic"] and not report["official_checksum_match"]
    t, v = make_splits(32, 16, 8, 0)
    loaded = load_profiling(path, t, v)
    assert loaded[0].shape == (16, 700) and len(loaded) == 4
    with pytest.raises(ValueError):
        load_profiling(path, t, t)
    with h5py.File(path, "r+") as f:
        f["Profiling_traces/labels"][0] = (int(f["Profiling_traces/labels"][0]) + 1) % 256
    with pytest.raises(ValueError, match="labels mismatch"):
        inspect_dataset(path)


@pytest.mark.parametrize("name", ["cnn", "mlp"])
def test_model_shape(name):
    assert build_model(name)(torch.zeros(4, 700)).shape == (4, 256)


def test_checkpoint_continuation_matches_uninterrupted_training_and_evaluation(tmp_path, monkeypatch):
    dataset = tmp_path / "fixture.h5"
    create_fixture(dataset, n_profiling=64, n_attack=16)
    base = {"dataset": str(dataset), "model": "cnn", "target_byte": 2, "seed": 1,
        "split_seed": 2026, "n_train": 32, "n_validation": 16, "epochs": 2,
        "batch_size": 16, "learning_rate": 0.001, "threads": 2, "device": "cpu",
        "augmentation": {"noise_std": 0.1, "max_shift": 2, "padding": "zero"}}
    full_dir, resumed_dir = tmp_path / "full", tmp_path / "resumed"
    full = train({**base, "run_dir": str(full_dir)})
    train({**base, "run_dir": str(resumed_dir), "epochs": 1})
    continued = train({**base, "run_dir": str(resumed_dir)}, resume=True)
    a = torch.load(full_dir / "last.pt", weights_only=False)
    b = torch.load(resumed_dir / "last.pt", weights_only=False)
    for name in a["model"]:
        torch.testing.assert_close(a["model"][name], b["model"][name], rtol=0, atol=0)
    for parameter_id, state in a["optimizer"]["state"].items():
        for key, value in state.items():
            torch.testing.assert_close(value, b["optimizer"]["state"][parameter_id][key], rtol=0, atol=0)
    assert full["optimization_steps"] == continued["optimization_steps"] == 4
    assert (full_dir / "code_snapshot.zip").exists()
    assert a["history"][1]["train_loss"] == b["history"][1]["train_loss"]
    original_checkpoint = (resumed_dir / "last.pt").read_bytes()
    original_history = (resumed_dir / "history.json").read_bytes()
    reused = train({**base, "run_dir": str(resumed_dir)}, resume=True, reuse_completed=True)
    assert reused == continued
    assert (resumed_dir / "last.pt").read_bytes() == original_checkpoint
    assert (resumed_dir / "history.json").read_bytes() == original_history
    earlier_stage = train({**base, "run_dir": str(resumed_dir), "epochs": 1},
                          resume=True, reuse_completed=True)
    assert earlier_stage["epochs"] == 2 and earlier_stage["optimization_steps"] == 4
    with pytest.raises(ValueError, match="mismatch"):
        train({**base, "run_dir": str(resumed_dir), "seed": 2}, resume=True, reuse_completed=True)
    assert not json.loads((full_dir / "inspection.json").read_text())["groups"]["Attack_traces"]["labels_verified"]
    evaluation = {"budget": 8, "repetitions": 3, "success_threshold": 0.9,
        "attack_order_seed": 8001, "corruption_seed": 9001, "batch_size": 8,
        "conditions": [{"name": "clean", "noise_std": 0., "max_shift": 0, "padding": "zero"}]}
    results = evaluate(full_dir, evaluation, device="cpu")
    assert results[0]["synthetic"]
    assert (full_dir / "evaluation_attack/key_recovery.png").exists()
    validation_results = evaluate(full_dir, evaluation, device="cpu", split="validation")
    assert validation_results[0]["split"] == "validation"
    assert validation_results[0]["attack_pool_size"] == 16
    cached = evaluate_cached(full_dir, evaluation, device="cpu", split="validation")
    def unexpected_evaluation(*args, **kwargs):
        raise RuntimeError("Evaluation recomputed")
    with monkeypatch.context() as context:
        context.setattr("sca.evaluate.evaluate", unexpected_evaluation)
        assert evaluate_cached(full_dir, evaluation, device="cpu", split="validation") == cached
        with pytest.raises(RuntimeError, match="recomputed"):
            evaluate_cached(full_dir, {**evaluation, "repetitions": 4}, device="cpu", split="validation")
    with pytest.raises(ValueError, match="mismatch"):
        train({**base, "run_dir": str(resumed_dir), "epochs": 3, "seed": 2}, resume=True)
