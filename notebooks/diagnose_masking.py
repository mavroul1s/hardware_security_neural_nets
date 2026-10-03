"""Read-only ASCAD profiling leakage audit; no training or attack-set access."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import h5py
import numpy as np


def weighted_snr(traces, labels):
    """Population Var(E[X|Y]) / E(Var(X|Y)), weighted by observed class counts."""
    values = np.asarray(traces, dtype=np.float64)
    labels = np.asarray(labels)
    if values.ndim != 2 or labels.ndim != 1 or len(values) != len(labels) or not len(labels):
        raise ValueError("Expected nonempty aligned traces and labels")
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite trace values")
    order = np.argsort(labels, kind="stable")
    _, starts, counts = np.unique(labels[order], return_index=True, return_counts=True)
    ordered = values[order]
    means = np.add.reduceat(ordered, starts, axis=0) / counts[:, None]
    second = np.add.reduceat(ordered * ordered, starts, axis=0) / counts[:, None]
    weights = counts / len(labels)
    global_mean = np.sum(weights[:, None] * means, axis=0)
    between = np.sum(weights[:, None] * (means - global_mean) ** 2, axis=0)
    within = np.sum(weights[:, None] * np.maximum(second - means ** 2, 0), axis=0)
    result = np.divide(between, within, out=np.zeros_like(between), where=within > 0)
    result[(within == 0) & (between > 0)] = np.inf
    return result


def select_separated_points(curve, count=5, separation=8):
    points = []
    for index in np.argsort(-np.asarray(curve), kind="stable"):
        if all(abs(int(index) - point) >= separation for point in points):
            points.append(int(index))
        if len(points) == count:
            return points
    raise ValueError("Too few separated points")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("outputs/masking_diagnosis_2026-10-03"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    run = root / "runs/kaggle_control/leaky_v5_output/runs/minimal_v2_leaky/none_seed0"
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    dataset = root / "data/ASCAD.h5"
    before = {name: hashlib.sha256((run / name).read_bytes()).hexdigest() for name in ("best.pt", "last.pt")}
    assert hashlib.sha256(dataset.read_bytes()).hexdigest() == manifest["dataset_sha256"]
    started = time.perf_counter()
    with np.load(run / "splits.npz", allow_pickle=False) as archive:
        indices = {"training": archive["training"], "validation": archive["validation"]}
    assert not np.intersect1d(indices["training"], indices["validation"]).size
    # Only these profiling groups are read. The held-out attack group is never opened.
    splits = {}
    with h5py.File(dataset, "r") as handle:
        group = handle["Profiling_traces"]
        for split, rows in indices.items():
            metadata = group["metadata"][rows]
            traces = group["traces"][rows].astype(np.float64)
            labels = group["labels"][rows]
            from sca.aes import identity_labels
            assert np.array_equal(labels, identity_labels(metadata["plaintext"], metadata["key"], 2))
            # ASCADv1 metadata: masks[0] is r[3] (one-based notation), masks[15] is rout.
            targets = {"unmasked_sbox": labels, "output_mask": metadata["masks"][:, 15],
                       "linear_mask": metadata["masks"][:, 0],
                       "masked_sbox_rout": labels ^ metadata["masks"][:, 15],
                       "masked_sbox_r3": labels ^ metadata["masks"][:, 0]}
            splits[split] = {"traces": traces, "targets": targets}
    hw = np.array([int(value).bit_count() for value in range(256)])
    controls = 8
    rng = np.random.default_rng(20261004)
    permutations = {split: [rng.permutation(len(data["traces"])) for _ in range(controls)]
                    for split, data in splits.items()}
    curves, report = {}, {"scope": "CPU profiling diagnostics; no trained model, optimizer step or attack read",
        "dataset_sha256": manifest["dataset_sha256"], "split_id": manifest["split_id"],
        "training_rows": len(indices["training"]), "validation_rows": len(indices["validation"]),
        "mask_mapping_source": "https://eprint.iacr.org/2018/053.pdf section 2.6.1",
        "mask_metadata_indices": {"r3": 0, "rin": 14, "rout": 15},
        "shuffled_controls": controls, "control_seed": 20261004,
        "controls_interpretation": "Descriptive finite-sample background; not a confidence interval or formal p-value",
        "first_order": {}, "selected_products": {},
        "cnn_receptive_field": {"conv1": 11, "pool1": 12, "conv2": 32, "pool2": 34,
            "pool2_stride": 4, "pool2_samples": 175, "first_dense_global_samples": 700,
            "global_nonlinear_hidden_layers": 1,
            "interpretation": "The convolutions are local; the flattened dense layer can combine all input regions."}}
    for split, data in splits.items():
        entries = report["first_order"][split] = {}
        for target, values in data["targets"].items():
            for encoding in ("id", "hw"):
                labels = values if encoding == "id" else hw[values]
                key = target + "_" + encoding
                curve = weighted_snr(data["traces"], labels)
                shuffled = np.stack([weighted_snr(data["traces"], labels[order]) for order in permutations[split]])
                assert np.isfinite(curve).all() and np.isfinite(shuffled).all()
                curves[split + "_" + key] = curve
                curves[split + "_" + key + "_control_mean"] = shuffled.mean(axis=0)
                entries[key] = {"peak_sample": int(curve.argmax()), "peak_snr": float(curve.max()),
                    "mean_snr": float(curve.mean()), "classes_present": int(len(np.unique(labels))),
                    "shuffled_maxima": shuffled.max(axis=1).tolist(),
                    "largest_shuffled_maximum": float(shuffled.max())}
        print("Completed first-order audit:", split, flush=True)

    # All centers, PoIs and product selection are fitted on the 10k training rows only.
    # Metadata is used to locate shares for diagnosis, never fed to the CNN or key-rank evaluator.
    train_mean = splits["training"]["traces"].mean(axis=0)
    for family, mask, share in (("rout", "output_mask", "masked_sbox_rout"),
                                ("r3", "linear_mask", "masked_sbox_r3")):
        mask_points = select_separated_points(curves["training_" + mask + "_id"])
        share_points = select_separated_points(curves["training_" + share + "_id"])
        pairs = [(i, j) for i in mask_points for j in share_points if i != j]
        products, product_snr = {}, {}
        for split, data in splits.items():
            x = data["traces"] - train_mean
            products[split] = np.stack([x[:, i] * x[:, j] for i, j in pairs], axis=1)
            labels = hw[data["targets"]["unmasked_sbox"]]
            product_snr[split] = weighted_snr(products[split], labels)
        chosen = int(product_snr["training"].argmax())
        item = {"mask_points_selected_on_training": mask_points,
                "share_points_selected_on_training": share_points,
                "candidate_pairs": pairs, "product_selection_target": "HW(unmasked Sbox)",
                "selected_pair": pairs[chosen], "separation_samples": abs(pairs[chosen][0] - pairs[chosen][1]),
                "training_only_centering_and_selection": True}
        for split, data in splits.items():
            labels = hw[data["targets"]["unmasked_sbox"]]
            control_snr = np.stack([weighted_snr(products[split], labels[order]) for order in permutations[split]])
            item[split] = {"selected_product_snr": float(product_snr[split][chosen]),
                "all_product_snr": product_snr[split].tolist(),
                "selected_product_control_snr": control_snr[:, chosen].tolist(),
                "largest_control_snr_across_all_candidate_pairs": float(control_snr.max())}
            curves[split + "_" + family + "_product_snr"] = product_snr[split]
        report["selected_products"][family] = item
    after = {name: hashlib.sha256((run / name).read_bytes()).hexdigest() for name in before}
    assert after == before
    report["checkpoint_hashes_unchanged"] = after
    report["seconds"] = time.perf_counter() - started
    (output / "diagnosis.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    np.savez_compressed(output / "snr_curves.npz", **curves)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
    names = list(splits["training"]["targets"])
    for row, split in enumerate(("training", "validation")):
        for col, encoding in enumerate(("id", "hw")):
            axis = axes[row, col]
            for target in names:
                key = split + "_" + target + "_" + encoding
                axis.plot(curves[key], label=target.replace("_", " "), linewidth=1)
            axis.plot(curves[split + "_unmasked_sbox_" + encoding + "_control_mean"],
                      color="gray", linestyle="--", linewidth=1, label="shuffled target: mean of 8")
            axis.set_title(split.capitalize() + ": " + encoding.upper() + " grouping")
            axis.set_ylabel("Weighted SNR")
            axis.set_xlabel("Trace sample (zero based)")
            axis.grid(alpha=0.2)
    axes[0, 0].legend(fontsize=7, ncol=2)
    fig.suptitle("ASCAD share leakage audit: fixed 10k/5k profiling split; no training")
    fig.tight_layout()
    fig.savefig(output / "share_snr.png", dpi=170)
    plt.close(fig)
    brief = {"first_order_hw": {split: {name: value for name, value in entries.items() if name.endswith("_hw")}
                                for split, entries in report["first_order"].items()},
             "selected_products": report["selected_products"], "seconds": report["seconds"]}
    print(json.dumps(brief, indent=2))


if __name__ == "__main__":
    main()
