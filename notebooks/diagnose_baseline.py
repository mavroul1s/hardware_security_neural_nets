"""Read-only profiling diagnostics for the completed baseline; no optimizer steps."""
import hashlib
import json
from pathlib import Path
import time

import h5py
import numpy as np
import torch
from sca.aes import identity_labels
from sca.data import fit_normalizer, load_profiling, make_splits, normalize, split_identifier
from sca.models import build_model

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/kaggle_control/baseline_v3_output/runs/minimal_v1/none_seed0"
OUTPUT = ROOT / "outputs/baseline_diagnosis_2026-10-03"
OUTPUT.mkdir(parents=True, exist_ok=True)
torch.set_num_threads(2)
started = time.perf_counter()
manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
with np.load(RUN / "splits.npz", allow_pickle=False) as archive:
    training, validation = archive["training"], archive["validation"]
expected = make_splits(50000, 10000, 5000, 2026)
assert np.array_equal(training, expected[0]) and np.array_equal(validation, expected[1])
assert not np.intersect1d(training, validation).size
assert split_identifier(training, validation) == manifest["split_id"]
dataset = ROOT / "data/ASCAD.h5"
assert hashlib.sha256(dataset.read_bytes()).hexdigest() == manifest["dataset_sha256"]
with h5py.File(dataset, "r") as handle:
    profiling = handle["Profiling_traces"]
    metadata, labels = profiling["metadata"][:], profiling["labels"][:]
    assert np.array_equal(labels, identity_labels(metadata["plaintext"], metadata["key"], 2))
    all_rows_label_check = len(labels)
xt, yt, xv, yv = load_profiling(dataset, training, validation)
stats = fit_normalizer(xt)
assert stats == manifest["normalizer"]
xt, xv = normalize(xt, stats), normalize(xv, stats)
assert np.isfinite(xt).all() and np.isfinite(xv).all()
counts = np.bincount(yt, minlength=256)
prior = counts / counts.sum()
assert np.all(counts > 0)
prior_train_ce = float(-np.log(prior[yt]).mean())
prior_validation_ce = float(-np.log(prior[yv]).mean())
report = {
    "scope": "CPU read-only diagnosis; profiling data only; no training and no attack-set reads",
    "dataset_sha256": manifest["dataset_sha256"], "labels_verified_profiling_rows": all_rows_label_check,
    "train_validation_overlap": 0, "split_id": manifest["split_id"], "normalizer_matches": True,
    "training_classes_present": int((counts > 0).sum()),
    "training_class_count_min": int(counts.min()), "training_class_count_max": int(counts.max()),
    "normalized_training_mean": float(xt.mean(dtype=np.float64)),
    "normalized_training_std": float(xt.std(dtype=np.float64)),
    "uniform_cross_entropy": float(np.log(256)),
    "training_prior_only_ce": prior_train_ce, "validation_prior_only_ce": prior_validation_ce,
    "checkpoints": {},
}


def predict(model, data):
    logits = []
    active = {"conv1_relu": np.zeros(8, dtype=np.int64),
              "conv2_relu": np.zeros(16, dtype=np.int64),
              "dense_relu": np.zeros(64, dtype=np.int64)}
    seen = {name: 0 for name in active}
    hooks = []
    def hook(name):
        def observe(_, __, value):
            axes = (0, 2) if value.ndim == 3 else (0,)
            active[name] += (value > 0).sum(dim=axes).cpu().numpy()
            seen[name] += value.shape[0] * (value.shape[2] if value.ndim == 3 else 1)
        return observe
    for index, name in ((2, "conv1_relu"), (5, "conv2_relu"), (9, "dense_relu")):
        hooks.append(model[index].register_forward_hook(hook(name)))
    with torch.no_grad():
        for start in range(0, len(data), 256):
            logits.append(model(torch.from_numpy(data[start:start + 256])).numpy())
    for item in hooks:
        item.remove()
    return np.concatenate(logits), {name: {
        "units_never_active": int((values == 0).sum()), "units": len(values),
        "mean_active_fraction": float((values / seen[name]).mean()),
        "unit_active_fractions": (values / seen[name]).tolist(),
    } for name, values in active.items()}


def metrics(logits, labels):
    values = torch.log_softmax(torch.from_numpy(logits).double(), dim=1).numpy()
    return {"cross_entropy": float(-values[np.arange(len(labels)), labels].mean()),
            "accuracy": float((logits.argmax(1) == labels).mean())}


for name in ("best", "last"):
    # These are our own verified checkpoints downloaded from the notebook we submitted.
    checkpoint = torch.load(RUN / (name + ".pt"), map_location="cpu", weights_only=False)
    model = build_model("cnn")
    model.load_state_dict(checkpoint["model"])
    model.eval()
    training_logits, training_activation = predict(model, xt)
    validation_logits, validation_activation = predict(model, xv)
    shuffled = np.random.default_rng(20261003).permutation(len(yv))
    input_variation = validation_logits.std(axis=0, dtype=np.float64)
    report["checkpoints"][name] = {
        "epoch": int(checkpoint["epoch"]), "steps": int(checkpoint["steps"]),
        "parameters": sum(p.numel() for p in model.parameters()),
        "training": metrics(training_logits, yt), "validation": metrics(validation_logits, yv),
        "validation_labels_shuffled_control": metrics(validation_logits, yv[shuffled]),
        "validation_input_logit_std_mean": float(input_variation.mean()),
        "validation_input_logit_std_max": float(input_variation.max()),
        "training_activation": training_activation, "validation_activation": validation_activation,
        "finite_parameters": all(torch.isfinite(p).all().item() for p in model.parameters()),
        "optimizer_steps_min": min(int(value["step"]) for value in checkpoint["optimizer"]["state"].values()),
        "optimizer_steps_max": max(int(value["step"]) for value in checkpoint["optimizer"]["state"].values()),
    }
report["diagnosis_seconds"] = time.perf_counter() - started
(OUTPUT / "diagnosis.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
brief = {key: value for key, value in report.items() if key != "checkpoints"}
brief["checkpoints"] = {name: {key: value for key, value in item.items()
    if key not in ("training_activation", "validation_activation")} for name, item in report["checkpoints"].items()}
brief["activation_never_active"] = {name: {layer: f"{data['units_never_active']}/{data['units']}"
    for layer, data in item["validation_activation"].items()} for name, item in report["checkpoints"].items()}
print(json.dumps(brief, indent=2))
