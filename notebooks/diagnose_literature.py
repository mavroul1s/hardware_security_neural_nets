"""Fixed-weight CPU diagnosis of the completed literature CNN; profiling only."""
import copy
import hashlib
import json
from pathlib import Path
import time

import h5py
import numpy as np
import torch
from sca.aes import identity_labels
from sca.data import fit_normalizer, normalize, split_identifier
from sca.metrics import evaluate_key_recovery
from sca.models import build_model
from sca.train import code_identity, environment, write_json

from diagnose_masking import weighted_snr

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0"
OUTPUT = ROOT / "outputs/literature_diagnosis_2026-10-04"
EXPECTED = "84eff3cde04c0e9a1756a3d29c44ec82e115a1a08575132686a02520333e2b5c"


def log_probabilities(logits):
    return torch.log_softmax(torch.as_tensor(logits, dtype=torch.float64), dim=1).numpy()


def classification_metrics(lp, labels):
    lp, labels = np.asarray(lp), np.asarray(labels)
    if lp.ndim != 2 or labels.shape != (len(lp),) or not np.isfinite(lp).all():
        raise ValueError("Expected aligned finite log probabilities and labels")
    return {"cross_entropy": float(-lp[np.arange(len(labels)), labels].mean()),
            "accuracy": float((lp.argmax(axis=1) == labels).mean())}


def channel_moments(model, data, batch_size=128):
    """Population moments before the only BatchNorm, reduced over trace/time axes."""
    total = square = None
    count = 0
    with torch.no_grad():
        for start in range(0, len(data), batch_size):
            values = model[:3](torch.from_numpy(data[start:start + batch_size])).double()
            part, part_square = values.sum(dim=(0, 2)), values.square().sum(dim=(0, 2))
            total = part if total is None else total + part
            square = part_square if square is None else square + part_square
            count += values.shape[0] * values.shape[2]
    if count <= 1:
        raise ValueError("Expected at least two channel observations")
    mean = total / count
    variance = (square / count - mean.square()).clamp_min(0)
    return mean, variance, count


def training_moment_counterfactual(model, training):
    """Clone only; substitute train-derived BN buffers, with every weight frozen."""
    mean, variance, count = channel_moments(model, training)
    clone = copy.deepcopy(model)
    with torch.no_grad():
        clone[3].running_mean.copy_(mean.to(clone[3].running_mean.dtype))
        clone[3].running_var.copy_((variance * count / (count - 1)).to(clone[3].running_var.dtype))
    clone.eval()
    assert all(torch.equal(p, q) for p, q in zip(model.parameters(), clone.parameters()))
    return clone, mean, variance, count


def predict(model, data, batch_size=128):
    logits, hidden1, hidden2 = [], [], []
    with torch.no_grad():
        for start in range(0, len(data), batch_size):
            values = torch.from_numpy(data[start:start + batch_size])
            for index, layer in enumerate(model):
                values = layer(values)
                if index == 7:
                    hidden1.append(values.numpy())
                elif index == 9:
                    hidden2.append(values.numpy())
            logits.append(values.numpy())
    return np.concatenate(logits), {"dense1": np.concatenate(hidden1), "dense2": np.concatenate(hidden2)}


def shuffled_alignment(lp, labels, permutations):
    observed = classification_metrics(lp, labels)["cross_entropy"]
    controls = np.array([classification_metrics(lp, labels[order])["cross_entropy"] for order in permutations])
    return {"observed_ce": observed, "shuffled_ce": controls.tolist(),
        "shuffled_ce_mean": float(controls.mean()), "shuffled_ce_min": float(controls.min()),
        "shuffled_ce_max": float(controls.max()), "mean_alignment_gain": float(controls.mean() - observed)}


def hidden_diagnostics(features, targets, permutations):
    entries = {}
    for layer, values in features.items():
        std = values.std(axis=0, dtype=np.float64)
        covariance = np.cov(values.astype(np.float64), rowvar=False, ddof=0)
        eigenvalues = np.maximum(np.linalg.eigvalsh(covariance), 0)
        effective_rank = float(eigenvalues.sum() ** 2 / np.square(eigenvalues).sum()) if np.any(eigenvalues) else 0.
        item = {"units": values.shape[1], "constant_units": int((std < 1e-8).sum()),
            "per_unit_std": std.tolist(), "covariance_participation_ratio": effective_rank,
            "targets": {}}
        for target, labels in targets.items():
            snr = weighted_snr(values, labels)
            controls = np.stack([weighted_snr(values, labels[order]) for order in permutations[:8]])
            item["targets"][target] = {"observed_max_snr": float(snr.max()),
                "observed_mean_snr": float(snr.mean()), "largest_shuffled_max_snr": float(controls.max()),
                "shuffled_maxima": controls.max(axis=1).tolist()}
        entries[layer] = item
    return entries


def key_summary(lp, plaintext, key):
    summary, curves = evaluate_key_recovery(lp, plaintext, key, budget=2000, repetitions=20, seed=8001)
    return summary, curves


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(2)
    started = time.perf_counter()
    before_source = code_identity()["source_sha256"]
    assert before_source == EXPECTED
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    hashes_before = {n:hashlib.sha256((RUN / n).read_bytes()).hexdigest() for n in ("best.pt", "last.pt")}
    with np.load(RUN / "splits.npz", allow_pickle=False) as bundle:
        indices = {"training": bundle["training"], "validation": bundle["validation"]}
    assert split_identifier(**{"train":indices["training"], "validation":indices["validation"]}) == manifest["split_id"]
    dataset = ROOT / "data/ASCAD.h5"
    assert hashlib.sha256(dataset.read_bytes()).hexdigest() == manifest["dataset_sha256"]
    data = {}
    hw = np.array([i.bit_count() for i in range(256)])
    with h5py.File(dataset, "r") as handle:
        group = handle["Profiling_traces"]
        for split, rows in indices.items():
            metadata = group["metadata"][rows]
            labels = group["labels"][rows]
            assert np.array_equal(labels, identity_labels(metadata["plaintext"], metadata["key"], 2))
            keys = np.unique(metadata["key"][:, 2])
            assert len(keys) == 1
            data[split] = {"raw": group["traces"][rows].astype(np.float32), "labels": labels,
                "plaintext": metadata["plaintext"][:, 2], "key": int(keys[0]),
                "targets": {"unmasked_id": labels, "unmasked_hw": hw[labels],
                    "output_mask_hw": hw[metadata["masks"][:, 15]],
                    "masked_sbox_rout_hw": hw[labels ^ metadata["masks"][:, 15]],
                    "linear_mask_hw": hw[metadata["masks"][:, 0]],
                    "masked_sbox_r3_hw": hw[labels ^ metadata["masks"][:, 0]]}}
    stats = fit_normalizer(data["training"]["raw"], "feature_minmax_training_only")
    assert stats == manifest["normalizer"]
    rng = np.random.default_rng(20261004)
    permutations = {s:[rng.permutation(len(d["labels"])) for _ in range(32)] for s,d in data.items()}
    for item in data.values():
        item["normalized"] = normalize(item["raw"], stats)
    counts = np.bincount(data["training"]["labels"], minlength=256)
    assert np.all(counts > 0)
    prior = counts / counts.sum()
    prior_lp = np.log(prior)
    report = {"scope": "CPU fixed-weight diagnosis; profiling only; zero optimizer updates; no Kaggle actions",
        "split_id": manifest["split_id"], "dataset_sha256": manifest["dataset_sha256"],
        "source_sha256": EXPECTED, "environment": environment(torch.device("cpu")),
        "control_seed": 20261004, "classification_shuffles": 32, "hidden_snr_shuffles": 8,
        "control_interpretation": "Descriptive shuffled background; not independent training repeats, confidence intervals or formal p-values",
        "training_class_count_min": int(counts.min()), "training_class_count_max": int(counts.max()),
        "data_distribution": {}, "prior_only": {}, "checkpoints": {},
        "bn_counterfactual": "Training-only population moments replace buffers on an in-memory clone; no weight update or saved variant; diagnostic only",
        "full_gpu_trainings_total": 3, "notebook_count": 1, "final_attack_set_read": False}
    curves_to_save = {}
    for split, item in data.items():
        x = item["normalized"]
        report["data_distribution"][split] = {"rows": len(x), "normalized_min": float(x.min()),
            "normalized_max": float(x.max()), "fraction_outside_training_range": float(((x < 0) | (x > 1)).mean()),
            "feature_mean": x.mean(axis=0, dtype=np.float64).tolist(), "feature_std": x.std(axis=0, dtype=np.float64).tolist()}
        report["prior_only"][split] = classification_metrics(np.broadcast_to(prior_lp, (len(x), 256)), item["labels"])
    validation = data["validation"]
    prior_summary, prior_curves = key_summary(np.broadcast_to(prior_lp, (len(validation["labels"]), 256)),
                                             validation["plaintext"], validation["key"])
    report["prior_only"]["validation_key_recovery"] = prior_summary
    curves_to_save["prior_ranks"] = prior_curves["ranks"]
    for name in ("best", "last"):
        checkpoint = torch.load(RUN / (name + ".pt"), map_location="cpu", weights_only=False)
        assert checkpoint["normalizer"] == stats and checkpoint["code"]["source_sha256"] == EXPECTED
        model = build_model("cnn_literature")
        model.load_state_dict(checkpoint["model"])
        model.eval()
        original = {k:v.clone() for k,v in model.state_dict().items()}
        entry = {"epoch": checkpoint["epoch"], "steps": checkpoint["steps"], "splits": {}}
        train_logits, _ = predict(model, data["training"]["normalized"])
        train_marginal = np.exp(log_probabilities(train_logits)).mean(axis=0)
        for split, item in data.items():
            logits, hidden = predict(model, item["normalized"])
            lp = log_probabilities(logits)
            constant = np.broadcast_to(np.log(train_marginal), lp.shape)
            entry["splits"][split] = {"metrics": classification_metrics(lp, item["labels"]),
                "alignment": shuffled_alignment(lp, item["labels"], permutations[split]),
                "constant_train_prediction_marginal": classification_metrics(constant, item["labels"]),
                "input_logit_std_mean": float(logits.std(axis=0, dtype=np.float64).mean()),
                "hidden": hidden_diagnostics(hidden, item["targets"], permutations[split])}
            if split == "validation":
                summary, curves = key_summary(lp, item["plaintext"], item["key"])
                entry["validation_key_recovery"] = summary
                curves_to_save[name + "_ranks"] = curves["ranks"]
                controls = []
                for order in permutations[split][:8]:
                    control, _ = key_summary(lp[order], item["plaintext"], item["key"])
                    controls.append({"ge_at_budget":control["ge_at_budget"], "sr_at_budget":control["sr_at_budget"]})
                entry["row_shuffled_prediction_key_controls"] = controls
                if name == "best":
                    folders = list(RUN.glob("evaluation_validation_*"))
                    assert len(folders) == 1
                    with np.load(folders[0] / "clean_curves.npz", allow_pickle=False) as stored:
                        entry["cpu_vs_stored_gpu_rank_agreement_fraction"] = float((curves["ranks"] == stored["ranks"]).mean())
        print("Completed fixed-checkpoint diagnosis:", name, flush=True)
        clone, mean, variance, count = training_moment_counterfactual(model, data["training"]["normalized"])
        entry["batchnorm"] = {"observations": count, "num_batches_tracked": int(model[3].num_batches_tracked),
            "running_mean": model[3].running_mean.tolist(), "training_population_mean": mean.tolist(),
            "running_variance": model[3].running_var.tolist(), "training_population_variance": variance.tolist(),
            "standardized_mean_error": ((model[3].running_mean.double() - mean) / (variance + model[3].eps).sqrt()).tolist(),
            "variance_plus_eps_ratio": ((model[3].running_var.double() + model[3].eps) / (variance + model[3].eps)).tolist(),
            "training_moments_counterfactual": {}}
        for split, item in data.items():
            logits, _ = predict(clone, item["normalized"])
            lp = log_probabilities(logits)
            probe = classification_metrics(lp, item["labels"])
            if split == "validation":
                probe["key_recovery"], _ = key_summary(lp, item["plaintext"], item["key"])
            entry["batchnorm"]["training_moments_counterfactual"][split] = probe
        assert all(torch.equal(v, model.state_dict()[k]) for k,v in original.items())
        entry["original_model_state_unchanged"] = True
        entry["optimizer_step_min"] = min(int(v["step"]) for v in checkpoint["optimizer"]["state"].values())
        entry["optimizer_step_max"] = max(int(v["step"]) for v in checkpoint["optimizer"]["state"].values())
        report["checkpoints"][name] = entry
    hashes_after = {n:hashlib.sha256((RUN / n).read_bytes()).hexdigest() for n in hashes_before}
    assert hashes_after == hashes_before and code_identity()["source_sha256"] == before_source
    report["checkpoint_hashes_unchanged"] = hashes_after
    report["diagnosis_seconds"] = time.perf_counter() - started
    write_json(OUTPUT / "diagnosis.json", report)
    np.savez_compressed(OUTPUT / "rank_controls.npz", **curves_to_save)
    print(json.dumps({"seconds": report["diagnosis_seconds"], "prior":report["prior_only"],
        "checkpoints": {n:{"epoch":e["epoch"], "training":e["splits"]["training"]["metrics"],
            "validation":e["splits"]["validation"]["metrics"],
            "validation_alignment":e["splits"]["validation"]["alignment"],
            "validation_key":e["validation_key_recovery"], "bn":e["batchnorm"]}
            for n,e in report["checkpoints"].items()}}, indent=2))


if __name__ == "__main__":
    main()
