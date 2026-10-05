"""Check saved correlation endpoints with a separate centered-dot-product formula."""
import json
from pathlib import Path

import h5py
import numpy as np
from sca.aes import candidate_labels
from sca.train import write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/literature_diagnosis_2026-10-04"
RUN = ROOT / "runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0"
record = json.loads((OUT / "second_order_correlation.json").read_text(encoding="utf-8"))
with np.load(RUN / "splits.npz", allow_pickle=False) as splits:
    training, validation = splits["training"], splits["validation"]
with h5py.File(ROOT / "data/ASCAD.h5", "r") as handle:
    group = handle["Profiling_traces"]
    center = group["traces"][training].mean(axis=0, dtype=np.float64)
    x = group["traces"][validation].astype(np.float64)
    metadata = group["metadata"][validation]
    plaintext = metadata["plaintext"][:, 2]
    key = int(np.unique(metadata["key"][:, 2]).item())
hw = np.array([v.bit_count() for v in range(256)])
hypotheses = hw[candidate_labels(plaintext)].astype(np.float64)
rng = np.random.default_rng(8001)
orders = [rng.permutation(len(x))[:2000] for _ in range(20)]
verified = {}
with np.load(OUT / "second_order_correlation_curves.npz", allow_pickle=False) as curves:
    for family, result in record["results"].items():
        i, j = result["pair"]
        product = (x[:, i] - center[i]) * (x[:, j] - center[j])
        ranks = curves[family + "_ranks"]
        assert ranks.shape == (20, 2000) and np.all((ranks >= 0) & (ranks <= 255))
        assert np.array_equal(curves[family + "_sr"], (ranks == 0).mean(axis=0))
        assert np.array_equal(curves[family + "_ge"], ranks.mean(axis=0))
        for index, order in enumerate(orders):
            a = product[order] - product[order].mean()
            b = hypotheses[order] - hypotheses[order].mean(axis=0)
            scores = np.abs((a[:, None] * b).sum(axis=0) / np.sqrt((a*a).sum() * (b*b).sum(axis=0)))
            rank = int((scores >= scores[key] - 1e-12).sum() - 1)
            assert rank == ranks[index, -1]
        assert result["ge_at_budget"] == float(ranks[:, -1].mean())
        assert result["sr_at_budget"] == float((ranks[:, -1] == 0).mean())
        reached = np.flatnonzero(np.logical_and.accumulate((curves[family + "_sr"] >= .9)[::-1])[::-1])
        assert result["traces_to_sustained_sr90"] == (int(reached[0] + 1) if len(reached) else None)
        verified[family] = {"independent_endpoint_checks": 20, "ranks_and_ge_sr_verified": True,
                            "sustained_success_recomputed": True}
write_json(OUT / "correlation_verification.json", {"method": "Separate centered-dot-product Pearson formula",
    "validation_only": True, "families": verified})
print(json.dumps(verified, indent=2))
