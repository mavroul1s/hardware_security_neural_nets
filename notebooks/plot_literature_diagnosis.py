"""Render scientific figures for the completed CPU diagnosis."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/literature_diagnosis_2026-10-04"
read = lambda p:json.loads(p.read_text(encoding="utf-8"))
diagnosis = read(OUT / "diagnosis.json")
correlation = read(OUT / "second_order_correlation.json")
run = ROOT / "runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0"
folder = next(run.glob("evaluation_validation_*"))
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
with np.load(folder / "clean_curves.npz", allow_pickle=False) as cnn:
    axes[0].plot(cnn["trace_counts"], cnn["ge"], label="CNN checkpoint epoch4", color="gray")
    axes[1].plot(cnn["trace_counts"], cnn["sr"], label="CNN checkpoint epoch4", color="gray")
with np.load(OUT / "second_order_correlation_curves.npz", allow_pickle=False) as curves:
    for family, result in correlation["results"].items():
        n = np.arange(1, 2001)
        label = "Correlation pair " + " x ".join(map(str, result["pair"]))
        axes[0].plot(n, curves[family + "_ge"], label=label)
        axes[1].plot(n, curves[family + "_sr"], label=label)
axes[1].axhline(.9, linestyle="--", color="black", linewidth=.8, label="Sustained SR90% criterion")
axes[0].set(ylabel="Mean key rank (zero based)", ylim=(-5, 260))
axes[1].set(ylabel="Success rate", ylim=(-.04, 1.04))
for axis in axes:
    axis.set_xlabel("Profiling-validation traces")
    axis.grid(alpha=.2)
    axis.legend(fontsize=7)
fig.suptitle("Validation diagnosis: 20 common trace orders, different selection information")
fig.tight_layout()
fig.savefig(OUT / "correlation_recovery.png", dpi=170)
plt.close(fig)

targets = ["unmasked_hw", "output_mask_hw", "linear_mask_hw", "masked_sbox_rout_hw", "masked_sbox_r3_hw"]
labels = ["Unmasked\nSbox", "Output\nmask", "Linear\nmask", "Masked\nSbox/rout", "Masked\nSbox/r3"]
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
for axis, (name, entry) in zip(axes, diagnosis["checkpoints"].items()):
    snr = entry["splits"]["validation"]["hidden"]["dense2"]["targets"]
    positions = np.arange(len(targets))
    axis.bar(positions - .18, [snr[t]["observed_max_snr"] for t in targets], width=.36, label="Observed")
    axis.bar(positions + .18, [snr[t]["largest_shuffled_max_snr"] for t in targets], width=.36,
             color="gray", label="Largest of 8 shuffled controls")
    axis.set_xticks(positions, labels, fontsize=8)
    axis.set_yscale("log")
    axis.set_title(name.capitalize() + " checkpoint: epoch" + str(entry["epoch"]))
    axis.set_ylabel("Maximum weighted SNR over 10 hidden units")
    axis.grid(axis="y", alpha=.2)
    axis.legend(fontsize=7)
fig.suptitle("Held-out dense2 representation: HW grouping; controls are descriptive")
fig.tight_layout()
fig.savefig(OUT / "hidden_leakage.png", dpi=170)
plt.close(fig)

brief = {"cpu_diagnosis_seconds": diagnosis["diagnosis_seconds"],
    "correlation_diagnosis_seconds": correlation["seconds"], "full_gpu_trainings_total": 3,
    "no_new_kaggle_execution": True, "final_attack_set_read": False,
    "correlation_results": {k:{field:v for field,v in item.items() if field != "row_shuffled_product_controls"}
                            for k,item in correlation["results"].items()},
    "cnn": {name:{"epoch":entry["epoch"], "training_ce":entry["splits"]["training"]["metrics"]["cross_entropy"],
        "validation_ce":entry["splits"]["validation"]["metrics"]["cross_entropy"],
        "bn_counterfactual_validation_ce":entry["batchnorm"]["training_moments_counterfactual"]["validation"]["cross_entropy"],
        "validation_sr":entry["validation_key_recovery"]["sr_at_budget"]}
        for name,entry in diagnosis["checkpoints"].items()}}
(OUT / "summary.json").write_text(json.dumps(brief, indent=2), encoding="utf-8")
print(json.dumps(brief, indent=2))
