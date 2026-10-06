"""Frozen CPU signal-replication and label-permutation audit of existing point pairs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import h5py
import numpy as np
import torch
from sca.train import code_identity, environment, write_json
from paper_alignment import ROOT, RUN, EXPECTED_SOURCE, read, sha

OUT = ROOT / "outputs/paper_selection_audit_2026-10-06"
HW = np.array([value.bit_count() for value in range(256)])
CAMPAIGNS = {
    "fixed": {"dataset": "data/ASCAD.h5", "n": 50000, "width": 700, "margin": 0,
        "selection": "outputs/paper_maskfree_2026-10-05/selection.json", "scores": "training_correlations",
        "splits": "outputs/paper_alignment_controls_2026-10-05/splits.npz"},
    "variable": {"dataset": "data/ASCAD_variable.h5", "n": 200000, "width": 1400, "margin": 10,
        "selection": "outputs/paper_variable_campaign_2026-10-05/fit.json", "scores": "training_coefficients",
        "splits": "outputs/paper_variable_campaign_2026-10-05/splits.npz"}}


def utc():
    return datetime.now(timezone.utc).isoformat()


def moment_cache(training, target):
    """Reuse label-independent centered-product variances over fixed training rows."""
    x, y = np.asarray(training, dtype=float), np.asarray(target, dtype=float)
    if x.ndim != 2 or y.shape != (len(x),) or len(x) < 2 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Expected finite training traces and target")
    h = y - y.mean()
    if np.mean(h * h) <= 0:
        raise ValueError("Constant target")
    centered = x - x.mean(axis=0)
    product_mean = centered.T @ centered / len(x)
    square = centered * centered
    variance = np.maximum(square.T @ square / len(x) - product_mean ** 2, 0)
    return centered, h, np.sqrt(variance * np.mean(h * h))


def cached_correlations(centered, h, denominator):
    covariance = centered.T @ (centered * h[:, None]) / len(centered)
    return np.clip(np.divide(covariance, denominator, out=np.zeros_like(covariance), where=denominator > 0), -1, 1)


def eligible_maximum(correlations, margin=0, separation=50):
    """Full-search maximum; first row-major candidate wins ties, never a fixed-pair null."""
    matrix = np.asarray(correlations)
    width = matrix.shape[0]
    if matrix.ndim != 2 or matrix.shape != (width, width) or margin < 0 or width - 2 * margin <= separation:
        raise ValueError("Invalid candidate matrix or margin")
    a, b = np.triu_indices(width - 2 * margin, k=separation)
    a, b = a + margin, b + margin
    index = int(np.abs(matrix[a, b]).argmax())
    return float(abs(matrix[a[index], b[index]])), [int(a[index]), int(b[index])], len(a)


def correlation(product, target):
    a, b = np.asarray(product, dtype=float), np.asarray(target, dtype=float)
    a, b = a - a.mean(), b - b.mean()
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        return 0.
    return float(np.dot(a, b) / denominator)


def monte_carlo_tail(null, observed, tolerance=1e-12):
    """One-sided conservative +1 randomized-test tail, including numerical ties."""
    values = np.asarray(null, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all() or not np.isfinite(observed):
        raise ValueError("Expected finite null sample and statistic")
    return float((1 + np.count_nonzero(values >= observed - tolerance)) / (len(values) + 1))


def fresh_rows(total, excluded, count=5000, seed=20261010):
    remaining = np.setdiff1d(np.arange(total), np.unique(excluded))
    if len(remaining) < count:
        raise ValueError("Insufficient unused profiling rows")
    return np.sort(np.random.default_rng(seed).choice(remaining, count, replace=False))


def make_plan():
    if (OUT / "results.json").exists():
        raise FileExistsError("Completed audit is protected")
    assert code_identity()["source_sha256"] == EXPECTED_SOURCE
    OUT.mkdir(parents=True, exist_ok=True)
    watched, split_arrays, campaign_plans = [], {}, {}
    for campaign, config in CAMPAIGNS.items():
        with np.load(ROOT / config["splits"], allow_pickle=False) as f:
            training, validation = f["training"], f["validation"]
            excluded = np.concatenate([f[name] for name in f.files if name != "attack"])
        if campaign == "fixed":
            # The last control split includes all three previous confirmations.
            assert len(np.unique(excluded)) == 35000
        else:
            assert len(np.unique(excluded)) == 15000
        confirmation = fresh_rows(config["n"], excluded)
        for name, values in (("training", training), ("validation", validation), ("excluded", np.unique(excluded)), ("confirmation", confirmation)):
            split_arrays[campaign + "__" + name] = values
        selection = read(ROOT / config["selection"])
        campaign_plans[campaign] = {**config, "pairs": selection["pairs"],
            "training_scores": selection[config["scores"]], "candidate_pairs": selection["candidate_pairs"],
            "previously_used_profiling_rows": len(np.unique(excluded))}
        watched += [ROOT / config[name] for name in ("dataset", "selection", "splits")]
    watched += [RUN / name for name in ("best.pt", "last.pt", "manifest.json", "splits.npz")]
    watched += [ROOT / "notebooks/kaggle_baseline.ipynb", ROOT / "outputs/kaggle_resume_input_literature.zip",
        ROOT / "outputs/kaggle_project_literature.zip"]
    for name in ("paper_alignment_2026-10-05", "paper_alignment_coordinates_2026-10-05",
                 "paper_maskfree_2026-10-05", "paper_alignment_controls_2026-10-05", "paper_variable_campaign_2026-10-05"):
        watched += [ROOT / "outputs" / name / "plan.json", ROOT / "outputs" / name / "results.json"]
    plan = {"authorization": "User requested continuing the paper-oriented CPU point-selection diagnostics on 2026-10-06",
        "reason": "Test replication of frozen selected signal and compare training-selected scores with the full-search permutation maximum",
        "campaigns": campaign_plans, "training_rows_each": 10000, "new_confirmation_rows_each": 5000,
        "confirmation_seed": 20261010, "train_permutation_seed": 2026, "confirmation_permutation_seed": 2026,
        "paired_randomness": "Same permutation indices across equally sized campaigns; streams restarted by role, not independent training seeds",
        "training_permutations": 99, "confirmation_permutations": 999,
        "training_null": "Permute HW targets on original training10k; recompute maximum absolute correlation over every originally eligible pair on each permutation",
        "training_null_scope": "Global no-association exchangeable-label diagnostic; not proof of absence of leakage, causal overfitting, or strong FWER under partial alternatives",
        "confirmation_method": "Raw frozen-pair centered products using original training means; no alignment, new point selection, noise, masks, plaintexts or keys",
        "confirmation_statistic": "Correlation multiplied by sign of the historical training coefficient; direction fixed before fresh confirmation",
        "monte_carlo_p": "(1 + count(null >= observed - 1e-12))/(B + 1), never zero",
        "primary_criterion": "A frozen pair replicates signed signal iff signed fresh correlation>0 and min(4*p,1)<=0.05; four tests across two campaigns",
        "multiple_testing": "Bonferroni for four fixed-pair confirmation tests; random pairing/exchangeability required; no physical security claim",
        "train_null_used_to_tune": False, "confirmation_used_to_tune": False,
        "inference_limitations": "Conditional on fixed training split; Monte Carlo resolution .01/.001; no multiple training seeds or causal attribution from prior attack failures",
        "no_new_training_budget_or_model": True, "new_gpu_trainings": 0, "new_optimizer_updates": 0,
        "attack_payloads_or_key_metadata_read_in_this_audit": False,
        "source_sha256": EXPECTED_SOURCE, "script_sha256": sha(Path(__file__)),
        "input_hashes": {p.relative_to(ROOT).as_posix(): sha(p) for p in watched}}
    if (OUT / "plan.json").exists():
        old = read(OUT / "plan.json")
        assert {k: v for k, v in old.items() if k != "frozen_utc"} == plan
        plan = old
        with np.load(OUT / "splits.npz", allow_pickle=False) as f:
            for name, values in split_arrays.items():
                np.testing.assert_array_equal(values, f[name])
    else:
        plan["frozen_utc"] = utc()
        write_json(OUT / "plan.json", plan)
        np.savez_compressed(OUT / "splits.npz", **split_arrays)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    plan = make_plan()
    if args.prepare_only:
        print("Frozen diagnostic plan:", OUT / "plan.json", flush=True)
        return
    if (OUT / "calibration.json").exists() or (OUT / "confirmation_access.json").exists():
        raise FileExistsError("Protect existing partial audit; inspect it before any retry")
    torch.set_num_threads(2)
    started = time.perf_counter()
    arrays, calibrations, timings = {}, {}, {}
    with np.load(OUT / "splits.npz", allow_pickle=False) as f:
        splits = {name: f[name] for name in f.files}
    # Complete training-only null calibration on both campaigns before fresh payloads.
    for campaign, config in plan["campaigns"].items():
        calibration_started = time.perf_counter()
        with h5py.File(ROOT / config["dataset"], "r") as f:
            x = f["Profiling_traces/traces"][splits[campaign + "__training"]].astype(float)
            y = HW[f["Profiling_traces/labels"][splits[campaign + "__training"]]]
        centered, h, denominator = moment_cache(x, y)
        arrays[campaign + "__training_mean"] = x.mean(axis=0)
        observed_matrix = cached_correlations(centered, h, denominator)
        for family, pair in config["pairs"].items():
            np.testing.assert_allclose(observed_matrix[tuple(pair)], config["training_scores"][family], atol=1e-12, rtol=1e-12)
        observed_max, observed_pair, candidates = eligible_maximum(observed_matrix, config["margin"])
        assert candidates == config["candidate_pairs"] and observed_pair == config["pairs"]["pair1"]
        rng = np.random.default_rng(plan["train_permutation_seed"])
        permutations, maxima, null_pairs, null_selected = [], [], [], []
        for index in range(plan["training_permutations"]):
            order = rng.permutation(len(y))
            scores = cached_correlations(centered, h[order], denominator)
            maximum, pair, _ = eligible_maximum(scores, config["margin"])
            permutations.append(order)
            maxima.append(maximum)
            null_pairs.append(pair)
            null_selected.append([float(scores[tuple(p)]) for p in config["pairs"].values()])
            if (index + 1) % 20 == 0:
                print("Training null:", campaign, index + 1, "/", plan["training_permutations"], flush=True)
        arrays[campaign + "__train_permutations"] = np.asarray(permutations, dtype=np.int16)
        arrays[campaign + "__null_maxima"] = np.asarray(maxima)
        arrays[campaign + "__null_max_pairs"] = np.asarray(null_pairs, dtype=np.int16)
        arrays[campaign + "__null_frozen_pair_correlations"] = np.asarray(null_selected)
        calibrations[campaign] = {"candidate_pairs": candidates, "observed_maximum": observed_max,
            "null_maximum_median": float(np.median(maxima)), "null_maximum_range": [float(min(maxima)), float(max(maxima))],
            "max_null_tail": {family: monte_carlo_tail(maxima, abs(value)) for family, value in config["training_scores"].items()},
            "rng_final_state": rng.bit_generator.state}
        timings[campaign + "__calibration_seconds"] = time.perf_counter() - calibration_started
    calibration = {"campaigns": calibrations, "plan_sha256": sha(OUT / "plan.json"),
        "completed_utc": utc(), "confirmation_payloads_read": False, "not_a_new_selected_model": True}
    write_json(OUT / "calibration.json", calibration)
    write_json(OUT / "confirmation_access.json", {"started_utc": utc(), "calibration_sha256": sha(OUT / "calibration.json"),
        "frozen_pairs_unchanged": True, "attack_payloads_or_metadata_read": False})
    results = []
    for campaign, config in plan["campaigns"].items():
        confirmation_started = time.perf_counter()
        with h5py.File(ROOT / config["dataset"], "r") as f:
            x = f["Profiling_traces/traces"][splits[campaign + "__confirmation"]].astype(float)
            y = HW[f["Profiling_traces/labels"][splits[campaign + "__confirmation"]]]
        mean = arrays[campaign + "__training_mean"]
        products = np.column_stack([(x[:, pair[0]] - mean[pair[0]]) * (x[:, pair[1]] - mean[pair[1]])
                                     for pair in config["pairs"].values()])
        signs = np.sign(list(config["training_scores"].values()))
        assert np.all(signs != 0)
        a, h = products - products.mean(axis=0), y.astype(float) - y.mean()
        denominator = np.linalg.norm(a, axis=0) * np.linalg.norm(h)
        observed = np.divide(a.T @ h, denominator, out=np.zeros(2), where=denominator > 0)
        rng = np.random.default_rng(plan["confirmation_permutation_seed"])
        permutations = np.stack([rng.permutation(len(y)) for _ in range(plan["confirmation_permutations"])])
        null = np.divide(h[permutations] @ a, denominator[None, :], out=np.zeros((len(permutations), 2)),
                         where=denominator[None, :] > 0)
        arrays[campaign + "__confirmation_permutations"] = permutations.astype(np.int16)
        arrays[campaign + "__confirmation_products"] = products
        arrays[campaign + "__confirmation_null_correlations"] = null
        for index, (family, pair) in enumerate(config["pairs"].items()):
            p = monte_carlo_tail(signs[index] * null[:, index], signs[index] * observed[index])
            corrected = min(4 * p, 1.)
            results.append({"campaign": campaign, "family": family, "pair": pair,
                "training_correlation": config["training_scores"][family], "confirmation_correlation": float(observed[index]),
                "training_global_max_null_tail": calibrations[campaign]["max_null_tail"][family],
                "signed_confirmation_correlation": float(signs[index] * observed[index]),
                "confirmation_one_sided_p": p, "confirmation_bonferroni_p": corrected,
                "signed_signal_replicates": bool(signs[index] * observed[index] > 0 and corrected <= .05)})
        calibrations[campaign]["confirmation_rng_final_state"] = rng.bit_generator.state
        timings[campaign + "__confirmation_seconds"] = time.perf_counter() - confirmation_started
        print("Fresh profiling confirmation:", campaign, [r for r in results if r["campaign"] == campaign], flush=True)
    for relative, expected in plan["input_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    assert sha(Path(__file__)) == plan["script_sha256"] and code_identity()["source_sha256"] == EXPECTED_SOURCE
    np.savez_compressed(OUT / "arrays.npz", **arrays)
    record = {"results": results, "calibrations": calibrations, "timings": timings,
        "plan_sha256": sha(OUT / "plan.json"), "calibration_sha256": sha(OUT / "calibration.json"),
        "access_sha256": sha(OUT / "confirmation_access.json"), "seconds": time.perf_counter() - started,
        "environment": environment(torch.device("cpu")), "source_sha256": EXPECTED_SOURCE,
        "original_artifacts_preserved": True, "new_confirmation_rows_viewed": True,
        "attack_payloads_or_key_metadata_read_in_this_audit": False,
        "new_gpu_trainings": 0, "new_optimizer_updates": 0, "no_new_fitted_attack_model": True,
        "full_gpu_trainings_total": 3, "no_efficacy_or_paper_novelty_claim": True}
    write_json(OUT / "results.json", record)
    print(json.dumps({"seconds": record["seconds"], "results": results}, indent=2), flush=True)


if __name__ == "__main__":
    main()
