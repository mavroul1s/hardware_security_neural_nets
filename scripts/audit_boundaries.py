"""Training-only exploratory boundary diagnostics; masking makes SNR incomplete."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sca.data import make_splits, load_profiling, fit_normalizer, normalize
from sca.augment import shift_batch


def audit(dataset, output, n_train=10000, n_validation=5000, split_seed=2026):
    import h5py
    with h5py.File(dataset, "r") as f:
        n = len(f["Profiling_traces/traces"])
    train_indices, val_indices = make_splits(n, n_train, n_validation, split_seed)
    x, labels, _, _ = load_profiling(dataset, train_indices, val_indices)
    x = normalize(x, fit_normalizer(x))
    means, variances, counts = [], [], []
    for label in np.unique(labels):
        subset = x[labels == label].astype(np.float64)
        means.append(subset.mean(0))
        variances.append(subset.var(0))
        counts.append(len(subset))
    means, variances = np.array(means), np.array(variances)
    weights = np.array(counts) / sum(counts)
    grand_mean = np.average(means, axis=0, weights=weights)
    between = np.average((means - grand_mean)**2, axis=0, weights=weights)
    within = np.average(variances, axis=0, weights=weights)
    snr = between / np.maximum(within, 1e-12)
    report = {"dataset": str(dataset), "training_rows": n_train, "validation_rows": n_validation,
        "split_seed": split_seed, "classes_present": len(counts),
        "peak_identity_first_order_snr_sample": int(snr.argmax()),
        "caution": "Finite-sample upward bias; identity first-order SNR cannot certify masked multi-point leakage retention",
        "edge_diagnostics": {}}
    for shift in (2, 5, 10, 20):
        edge = np.r_[snr[:shift], snr[-shift:]]
        report["edge_diagnostics"][str(shift)] = {"discarded_fraction_max": shift / 700,
            "edge_max_snr": float(edge.max()), "overall_max_snr": float(snr.max())}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "boundary_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    fig, axes = plt.subplots(2, 1, figsize=(10, 6))
    axes[0].plot(snr, linewidth=0.8)
    axes[0].axvspan(0, 10, color="orange", alpha=0.3)
    axes[0].axvspan(690, 699, color="orange", alpha=0.3)
    axes[0].set_ylabel("Identity first-order SNR (exploratory)")
    axes[0].set_title("Training-only boundary audit; cannot certify retention of masked leakage")
    trace = torch.from_numpy(x[:1])
    for shift in (-10, 0, 10):
        axes[1].plot(shift_batch(trace, torch.tensor([shift]))[0], label=f"shift {shift}", alpha=0.75, linewidth=0.7)
    axes[1].set_xlabel("Sample index in 700-point window")
    axes[1].set_ylabel("Normalized amplitude")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(output / "boundary_audit.png", dpi=160)
    plt.close(fig)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset")
    parser.add_argument("--output", default="outputs/boundary_audit")
    args = parser.parse_args()
    audit(args.dataset, args.output)
