"""Render frozen-pair sensitivity figures from saved validation results."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/correlation_robustness_2026-10-05"


def main():
    record = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    plan = record["plan"]
    lookup = {(r["condition"], r["family"], r["method"]):r for r in record["results"]}
    columns = [(family, method) for method in ("fixed", "oracle_known_shift") for family in ("rout", "r3")]
    conditions = [c["name"] for c in plan["conditions"]]
    matrix = np.array([[lookup[(name, family, method)]["sr_at_budget"] for family,method in columns] for name in conditions])
    labels = [f"{c['name']}  (noise={c['noise_std']:g}, shift=±{c['max_shift']})" for c in plan["conditions"]]
    fig, axis = plt.subplots(figsize=(10.8, 6.1))
    im = axis.imshow(matrix, cmap="YlGnBu", vmin=0, vmax=1, aspect="auto")
    axis.set_xticks(np.arange(4), ["Fixed pair\n181 × 521", "Fixed pair\n156 × 517",
                                  "Known-shift oracle\n181 × 521", "Known-shift oracle\n156 × 517"], fontsize=9)
    axis.set_yticks(np.arange(8), labels, fontsize=9)
    for row in range(8):
        for column in range(4):
            value = matrix[row, column]
            axis.text(column, row, f"{int(round(value * 20))}/20", ha="center", va="center",
                      color="white" if value >= .7 else "black", fontsize=11)
    axis.axvline(1.5, color="white", linewidth=2)
    fig.colorbar(im, ax=axis, label="SR at 2,000 validation traces", fraction=.035, pad=.025)
    axis.set_title("Second-order correlation: frozen points and training centers", fontsize=12, pad=15)
    fig.text(.5, .022, "20 common trace orders; one corruption realization. Oracle receives the injected shift.\n"
             "Feature-space corruption after train-only MinMax; profiling validation only.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .075, 1, 1))
    fig.savefig(OUT / "success_grid.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), sharex=True, sharey=True)
    shown = [("clean", "Clean", "#222222"), ("noise_matched", "Noise 0.1", "#2166ac"),
             ("shift_matched", "Shift ±5", "#1b9e77"), ("combined_matched", "Noise 0.1 + shift ±5", "#e08214"),
             ("combined_both_ood", "Noise 0.2 + shift ±10", "#b2182b")]
    with np.load(OUT / "audit_arrays.npz", allow_pickle=False) as arrays:
        for row, family in enumerate(("rout", "r3")):
            for column, method in enumerate(("fixed", "oracle_known_shift")):
                axis = axes[row, column]
                for name, label, color in shown:
                    axis.plot(np.arange(1, 2001), arrays[name + "__" + family + "__" + method + "__sr"],
                              label=label, color=color, linewidth=1.2, alpha=.9)
                axis.axhline(.9, color="gray", linestyle="--", linewidth=.8)
                pair = plan["pairs"][family]
                axis.set_title(f"Pair {pair[0]} × {pair[1]} — " + ("fixed positions" if method == "fixed" else "known-shift oracle"), fontsize=10)
                axis.grid(alpha=.2)
                axis.set_ylim(-.03, 1.03)
                axis.set_xlim(1, 2000)
                if column == 0:
                    axis.set_ylabel("Success rate")
                if row == 1:
                    axis.set_xlabel("Profiling-validation traces")
    handles, legend_labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="lower center", ncol=3, fontsize=8, frameon=False)
    fig.suptitle("Sensitivity diagnosis; oracle uses known synthetic offsets", fontsize=12)
    fig.tight_layout(rect=(0, .08, 1, .96))
    fig.savefig(OUT / "recovery_curves.png", dpi=180)
    plt.close(fig)
    fields = ["condition", "family", "method", "ge_at_budget", "sr_at_budget", "traces_to_sustained_sr90", "recovery_censored"]
    with (OUT / "metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(record["results"])
    print("Saved success_grid.png, recovery_curves.png and metrics.csv")


if __name__ == "__main__":
    main()
