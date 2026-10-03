"""Check an untrained literature candidate, geometry and input conditioning on CPU."""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import torch

from sca.data import load_profiling, normalize
from sca.models import build_model
from candidate_literature_cnn import build_candidate, fit_feature_minmax, apply_feature_minmax

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/kaggle_control/leaky_v5_output/runs/minimal_v2_leaky/none_seed0"
OUTPUT = ROOT / "outputs/masking_diagnosis_2026-10-03"
OUTPUT.mkdir(parents=True, exist_ok=True)
torch.set_num_threads(2)
manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
with np.load(RUN / "splits.npz", allow_pickle=False) as splits:
    xt, yt, xv, yv = load_profiling(ROOT / "data/ASCAD.h5", splits["training"], splits["validation"])
stats = fit_feature_minmax(xt)
assert np.array_equal(stats["minimum"], xt.min(axis=0))
assert np.array_equal(stats["scale"], xt.max(axis=0) - xt.min(axis=0))
transformed_train, transformed_val = apply_feature_minmax(xt, stats), apply_feature_minmax(xv, stats)
assert np.isfinite(transformed_train).all() and np.isfinite(transformed_val).all()
global_train = normalize(xt, manifest["normalizer"])
condition = {"global_normalized_feature_mean_range": [float(global_train.mean(axis=0).min()), float(global_train.mean(axis=0).max())],
    "global_normalized_feature_std_range": [float(global_train.std(axis=0).min()), float(global_train.std(axis=0).max())],
    "candidate_training_minmax_range": [float(transformed_train.min()), float(transformed_train.max())],
    "candidate_validation_minmax_range": [float(transformed_val.min()), float(transformed_val.max())],
    "validation_values_outside_training_minmax_fraction": float(((transformed_val < 0) | (transformed_val > 1)).mean()),
    "normalization_fitted_only_on_training": True}
torch.manual_seed(0)
local = build_model("cnn_leaky")
torch.manual_seed(0)
candidate = build_candidate()
layers, receptive_field, jump, samples = [], 1, 1, 700
for layer in local:
    if isinstance(layer, torch.nn.Flatten):
        break
    if isinstance(layer, (torch.nn.Conv1d, torch.nn.AvgPool1d)):
        scalar = lambda value: value[0] if isinstance(value, tuple) else value
        kernel, stride, padding = scalar(layer.kernel_size), scalar(layer.stride), scalar(layer.padding)
        dilation = scalar(layer.dilation) if isinstance(layer, torch.nn.Conv1d) else 1
        receptive_field += (kernel - 1) * dilation * jump
        jump *= stride
        samples = (samples + 2 * padding - dilation * (kernel - 1) - 1) // stride + 1
        layers.append({"type": type(layer).__name__, "output_samples": samples,
                       "input_receptive_field": receptive_field, "input_stride": jump})
assert receptive_field == 34 and samples == 175 and local[8].in_features == 2800
candidate.eval()
with torch.no_grad():
    logits = candidate(torch.from_numpy(transformed_train[:128]))
assert logits.shape == (128, 256) and torch.isfinite(logits).all()
assert sum(parameter.numel() for parameter in candidate.parameters()) == 16952
candidate.zero_grad(set_to_none=True)
torch.nn.functional.cross_entropy(candidate(torch.from_numpy(transformed_train[:128])), torch.from_numpy(yt[:128])).backward()
assert all(parameter.grad is not None and torch.isfinite(parameter.grad).all() for parameter in candidate.parameters())
bootstrap_spec = importlib.util.spec_from_file_location("bootstrap", ROOT / "notebooks/kaggle_bootstrap.py")
bootstrap = importlib.util.module_from_spec(bootstrap_spec)
bootstrap_spec.loader.exec_module(bootstrap)
assert bootstrap.project_sha256(ROOT) == manifest["code"]["source_sha256"]
report = {"scope": "Untrained CPU prototype; forward/backward only; no optimizer step or attack read",
    "current_training_source_sha256_unchanged": manifest["code"]["source_sha256"],
    "current_cnn": {"parameters": 197424, "temporal_layers": layers,
        "dense_global_receptive_field": 700, "global_hidden_nonlinear_layers": 1},
    "candidate": {"parameters": 16952, "architecture": str(candidate),
        "global_hidden_nonlinear_layers": 2, "finite_forward_and_gradients": True,
        "performance_evidence": None, "kaggle_notebook_uses_candidate": False},
    "conditioning": condition,
    "source": "https://github.com/gabzai/Methodology-for-efficient-CNN-architectures-in-SCA/blob/master/ASCAD/N0%3D0/cnn_architecture.py"}
(OUTPUT / "architecture_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
proposal = {"status": "prepared_not_authorized_or_executed", "model": "literature_cnn_prototype",
    "proposed_baseline": {"training_rows": 10000, "validation_rows": 5000, "split_seed": 2026,
        "seed": 0, "epochs": 50, "batch_size": 128, "steps": 3950,
        "optimizer": "Adam", "learning_rate": 0.001, "scheduler": None,
        "normalization": "per_sample_position_minmax_fitted_on_training_only",
        "target": "unmasked Sbox byte2 identity256", "parameters": 16952},
    "differences_from_authors": ["10k training rather than45k", "training-only normalization fit",
        "constant Adam LR0.001 rather than OneCycle with max0.005", "batch128 rather than50",
        "PyTorch rather than Keras; running-variance and RNG conventions differ"],
    "minimal_followup_option": {"additional_baseline_trainings": 1, "conditional_combined_trainings": 1,
        "total_gpu_trainings_including_two_failures_at_most": 4, "single_augmentation_trainings": 0,
        "gate": "Clean validation SR@2000 >= 0.90 (18/20) using minimum-CE checkpoint; otherwise stop before combined",
        "notebooks": 1,
        "research_scope": "baseline versus combined robustness; cannot attribute benefit to combination versus each single"},
    "no_new_gpu_training_started": True}
(OUTPUT / "next_run_proposal.json").write_text(json.dumps(proposal, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
