"""Plot saved masking diagnostic results; no data fitting or checkpoint changes."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs/masking_diagnosis_2026-10-03"
report = json.loads((OUTPUT / "diagnosis.json").read_text(encoding="utf-8"))
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
with np.load(OUTPUT / "snr_curves.npz", allow_pickle=False) as curves:
    for split, color in (("training", "tab:blue"), ("validation", "tab:orange")):
        axes[0].plot(curves[split + "_unmasked_sbox_hw"], color=color, linewidth=1, label=split)
        maximum = report["first_order"][split]["unmasked_sbox_hw"]["largest_shuffled_maximum"]
        axes[0].axhline(maximum, color=color, linestyle="--", linewidth=1, label=split + " shuffled max")
axes[0].set_title("Single-sample SNR for HW(unmasked Sbox)")
axes[0].set_xlabel("Trace sample (zero based)")
axes[0].set_ylabel("Weighted SNR")
axes[0].legend(fontsize=7)
axis = axes[1]
positions = np.arange(2)
width = 0.2
for number, (split, color) in enumerate((("training", "tab:blue"), ("validation", "tab:orange"))):
    values = [report["selected_products"][family][split]["selected_product_snr"] for family in ("rout", "r3")]
    background = [report["selected_products"][family][split]["largest_control_snr_across_all_candidate_pairs"] for family in ("rout", "r3")]
    axis.bar(positions + (number - 0.5) * width, values, width, color=color, label=split + " selected product")
    axis.scatter(positions + (number - 0.5) * width, background, facecolors="white", edgecolors=color,
                 marker="o", linewidths=1.5, zorder=4, label=split + " shuffled max")
axis.set_xticks(positions, ["samples 181 × 521", "samples 156 × 517"])
axis.set_title("Centered products: HW(unmasked Sbox)")
axis.set_ylabel("Weighted SNR")
axis.legend(fontsize=7)
for axis in axes:
    axis.grid(axis="y", alpha=0.2)
fig.suptitle("Both point pairs and centering selected on training only; 8 shuffled controls")
fig.tight_layout()
fig.savefig(OUTPUT / "second_order_evidence.png", dpi=180)
plt.close(fig)
