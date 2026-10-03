"""Final attack evaluation is explicit and separate from training."""
import csv
import json
import time
from pathlib import Path

import numpy as np
import torch
from .augment import augment_batch
from .data import inspect_dataset, load_attack, load_validation_evaluation, normalize
from .metrics import evaluate_key_recovery
from .models import build_model
from .train import select_device, write_json, environment, code_identity, sync


def evaluate(run_dir, evaluation_config, device="auto", output_dir=None, checkpoint_name="best.pt",
             split="attack", dataset_override=None):
    run_dir = Path(run_dir)
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    if dataset_override is not None:
        config["dataset"] = str(dataset_override)
    torch.set_num_threads(config["threads"])
    selected_device = select_device(device)
    checkpoint = torch.load(run_dir / checkpoint_name, map_location="cpu", weights_only=False)
    if split not in ("validation", "attack"):
        raise ValueError("Unknown evaluation split")
    inspection = inspect_dataset(config["dataset"], config["target_byte"], verify_attack=split == "attack")
    if inspection["sha256"] != checkpoint["dataset_sha256"]:
        raise ValueError("Evaluation dataset differs from the training dataset")
    if split == "attack":
        traces, plaintext, key = load_attack(config["dataset"], config["target_byte"])
    else:
        indices = np.load(run_dir / "splits.npz")["validation"]
        traces, plaintext, key = load_validation_evaluation(config["dataset"], indices, config["target_byte"])
    traces = normalize(traces, checkpoint["normalizer"])
    model = build_model(config["model"]).to(selected_device)
    model.load_state_dict(checkpoint["model"])
    model.eval()
    output = Path(output_dir) if output_dir else run_dir / f"evaluation_{split}"
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Evaluation output already exists: {output}")
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "evaluation_manifest.json", {"evaluation_config": evaluation_config,
        "training_manifest": json.loads((run_dir / "manifest.json").read_text(encoding="utf-8")),
        "checkpoint": checkpoint_name, "checkpoint_epoch": checkpoint["epoch"], "split": split,
        "environment": environment(selected_device), "code": code_identity(),
        "synthetic": inspection["synthetic"], "dataset_sha256": inspection["sha256"]})
    results = []
    for condition in evaluation_config["conditions"]:
        name = condition["name"]
        if not name.replace("_", "").isalnum():
            raise ValueError("Use alphanumeric condition names with underscores")
        generator = torch.Generator().manual_seed(evaluation_config["corruption_seed"])
        predictions = []
        sync(selected_device)
        started = time.perf_counter()
        with torch.no_grad():
            for start in range(0, len(traces), evaluation_config["batch_size"]):
                x = torch.from_numpy(traces[start:start + evaluation_config["batch_size"]])
                # Fixed CPU corruption RNG makes test conditions identical across training seeds/devices.
                x = augment_batch(x, **{k: v for k, v in condition.items() if k != "name"}, generator=generator)
                logits = model(x.to(selected_device))
                predictions.append(torch.log_softmax(logits.double(), dim=1).cpu().numpy())
        sync(selected_device)
        prediction_seconds = time.perf_counter() - started
        lp = np.concatenate(predictions)
        started = time.perf_counter()
        summary, curves = evaluate_key_recovery(lp, plaintext, key,
            budget=evaluation_config["budget"], repetitions=evaluation_config["repetitions"],
            seed=evaluation_config["attack_order_seed"], success_threshold=evaluation_config["success_threshold"])
        summary.update(condition=name, corruption=condition, prediction_seconds=prediction_seconds,
            ranking_seconds=time.perf_counter() - started, synthetic=inspection["synthetic"], split=split)
        np.savez_compressed(output / f"{name}_curves.npz", **curves)
        with open(output / f"{name}_curves.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["attack_traces", "guessing_entropy", "success_rate"])
            writer.writerows(zip(curves["trace_counts"], curves["ge"], curves["sr"]))
        results.append(summary)
        print(json.dumps(summary), flush=True)
    write_json(output / "results.json", results)
    plot_results(output, results, inspection["synthetic"])
    return results


def plot_results(output, results, synthetic):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for result in results:
        curves = np.load(output / f"{result['condition']}_curves.npz")
        axes[0].plot(curves["trace_counts"], curves["ge"], label=result["condition"])
        axes[1].plot(curves["trace_counts"], curves["sr"], label=result["condition"])
    axes[0].set_ylabel("Guessing entropy (rank 0 = best)")
    axes[1].set_ylabel("Success rate")
    axes[1].set_ylim(-0.02, 1.02)
    for axis in axes:
        axis.set_xlabel("Evaluation traces")
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
    split_label = "profiling validation (diagnostic)" if results[0]["split"] == "validation" else "attack set"
    fig.suptitle("SYNTHETIC correctness check" if synthetic else f"ASCAD fixed-key: {split_label}")
    fig.tight_layout()
    fig.savefig(output / "key_recovery.png", dpi=180)
    plt.close(fig)
