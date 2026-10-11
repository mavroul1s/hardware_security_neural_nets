"""Prospective objective-matched window selection using unchanged training draws."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import h5py
import numpy as np
import torch
from sca.train import code_identity, environment, write_json
from paper_alignment import ROOT, RUN, EXPECTED_SOURCE, read, sha, shifted
from paper_maskfree_selection import pair_correlations, select_pairs
from paper_selection_audit import fresh_rows, correlation
from paper_training_alignment import FEATURES, fit_simple_features, extract_simple, offsets_batched

OUT = ROOT / "outputs/paper_window_selection_2026-10-09"
OLD = ROOT / "outputs/paper_selection_stability_2026-10-06"
ALIGN = ROOT / "outputs/paper_training_alignment_2026-10-06"
HW = np.array([v.bit_count() for v in range(256)])
SELECTORS = ["point_selector", "box_selector"]


def utc():
    return datetime.now(timezone.utc).isoformat()


def window_means(x, radius=5):
    """Valid means only: output column zero represents original center radius."""
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or radius < 0 or 2 * radius + 1 > x.shape[1] or not np.isfinite(x).all():
        raise ValueError("Expected finite traces and a valid radius")
    return np.lib.stride_tricks.sliding_window_view(x, 2 * radius + 1, axis=1).mean(-1)


def select_box_pairs(x, y, margin=25, radius=5, separation=50, diversity=20):
    """Absolute Pearson of products of two centered window means, same centers."""
    if margin < radius or x.shape[1] <= 2 * margin + separation + 2 * diversity:
        raise ValueError("Invalid common eligible domain")
    means = window_means(x, radius)
    matrix = pair_correlations(means[:, margin-radius:x.shape[1]-margin-radius], y)
    pairs, count = select_pairs(matrix, separation, diversity)
    return {k: [p + margin for p in v] for k, v in pairs.items()}, count, matrix


def oob_indices(draw, n):
    draw = np.asarray(draw)
    if draw.ndim != 1 or not np.issubdtype(draw.dtype, np.integer) or np.any((draw < 0) | (draw >= n)):
        raise ValueError("Invalid paired draw indices")
    return np.setdiff1d(np.arange(n), draw)


def summarize_pair(a, b):
    """Finite paired perturbation diagnostic, without independent-draw inference."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.shape != (20,) or b.shape != a.shape or not np.isfinite([a, b]).all():
        raise ValueError("Expected all twenty paired coefficients")
    return {"baseline_median": float(np.median(b)), "window_median": float(np.median(a)),
            "median_paired_difference": float(np.median(a-b)),
            "window_positive_draws": int(np.count_nonzero(a > 0)),
            "baseline_positive_draws": int(np.count_nonzero(b > 0)),
            "window_minimum": float(a.min()), "window_maximum": float(a.max())}


def exclusion_provenance():
    """Replay all variable profiling split unions; attack indices are never merged."""
    paths = ["paper_variable_campaign_2026-10-05", "paper_selection_audit_2026-10-06",
             "paper_window_regression_2026-10-06", "paper_precision_replication_2026-10-06",
             "paper_training_alignment_2026-10-06", "paper_selection_stability_2026-10-06"]
    prior = np.array([], dtype=np.int64)
    records = []
    for i, name in enumerate(paths):
        path = ROOT / "outputs" / name / "splits.npz"
        with np.load(path, allow_pickle=False) as f:
            if i == 0:
                rows = [f["training"], f["validation"]]
            elif i in (1, 2):
                np.testing.assert_array_equal(f["variable__excluded"], prior)
                keys = [k for k in f.files if k.startswith("variable__") and "attack" not in k]
                rows = [f[k] for k in keys]
            else:
                np.testing.assert_array_equal(f["excluded"], prior)
                rows = [f[k] for k in f.files]
            prior = np.unique(np.concatenate(rows))
        records.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "union_rows": len(prior)})
    assert [r["union_rows"] for r in records] == [15000, 20000, 30000, 70000, 110000, 150000]
    return prior, records


def make_plan():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "results.json").exists():
        raise FileExistsError("Completed phase is protected")
    excluded, provenance = exclusion_provenance()
    with np.load(OLD / "splits.npz", allow_pickle=False) as f:
        training = f["training"]
        np.testing.assert_array_equal(excluded, np.unique(np.concatenate([f[k] for k in f.files])))
    primary = fresh_rows(200000, excluded, count=10000, seed=20261020)
    replication = fresh_rows(200000, np.union1d(excluded, primary), count=10000, seed=20261021)
    watched = [OLD / n for n in ("plan.json", "splits.npz", "fit.json", "fit.npz", "verification.json", "results.json")]
    watched += [ALIGN / n for n in ("fit.json", "fit.npz", "plan.json", "verification.json")]
    watched += [RUN / n for n in ("best.pt", "last.pt", "manifest.json", "splits.npz")]
    watched += [ROOT / n for n in ("data/ASCAD_variable.h5", "notebooks/kaggle_baseline.ipynb",
        "outputs/kaggle_project_literature.zip", "outputs/kaggle_resume_input_literature.zip",
        "literature/SELECTION_OBJECTIVE_AUDIT_2026-10-09.md", "tests/test_window_selection.py",
        "notebooks/verify_window_selection.py", "notebooks/paper_alignment.py", "notebooks/paper_maskfree_selection.py",
        "notebooks/paper_training_alignment.py", "notebooks/paper_selection_stability.py",
        "notebooks/verify_training_alignment.py")]
    watched += [OUT / "literature_access.json", OUT / "pytest.xml"]
    plan = {
        "authorization": "User requested autonomous justified CPU research with frozen plans and independent verification, preserving GPU scope",
        "hypothesis_H1": "Matching selection to box-product extraction improves second-family stability over point selection under identical phase10 draws",
        "hypothesis_H2": "Internal out-of-bag second-family box/rank1 medians predict fresh clean profiling medians within .02 and agree at threshold .05 for both selectors",
        "H3_deferred": "Stable profiling signal is insufficient to guarantee SR18/20 at2000 on a prospectively frozen independently acquired actual key; requires new key/acquisition evidence, no attack experiment here",
        "adaptive_scope": "Motivated by selector/feature objective mismatch and primary literature, after phase10; prior failures remain. No evaluated attack or confirmation used to pick a winner or tune parameters",
        "dataset": "data/ASCAD_variable.h5", "width": 1400, "byte": 2,
        "training": "Exactly original10000 traces/provided identity labels. Unchanged phase10 twenty paired draws and phase9 trace-only offsets/template",
        "baseline": "All immutable phase10 point-selector fits, including all failures; not a selected draw",
        "alternative": "All845650 eligible centers searched using absolute Pearson of centered11-sample mean products; no scheme-aware restriction",
        "selection_margin": 25, "radius": 5, "separation": 50, "diversity": 20,
        "ties": "First row-major upper-triangle exact maximum, as baseline",
        "features": FEATURES, "selectors": SELECTORS, "draws": 20,
        "controls": "Point/box/rank1 at each selector's pairs, shared per-draw centers, common trace-only evaluation offsets; both family ranks retained",
        "preprocessing_limit": "Conditional on fixed original10000-trace unlabeled preprocessing. OOB rows excluded from draw fit/selection labels but originally contributed to unlabeled alignment",
        "fresh_rows_each": 10000, "pool_seeds": [20261020, 20261021],
        "excluded_profiling_rows": 150000, "exclusion_provenance": provenance,
        "conditions": [{"name": "clean", "max_shift": 0, "noise_factor": 0.},
                       {"name": "combined5", "max_shift": 5, "noise_factor": .1}],
        "randomness": "Identical U9101/Z9102 per equal-sized pool, same as previous protocols. No new neural seed; all draws reused byte-for-byte",
        "primary_endpoint": "Clean box-product familyrank2: median of20 paired correlation differences box_selector minus point_selector, in each fresh pool",
        "primary_criterion": "Both pools: median paired difference>=.02, window median>=.05, >=16/20 positive window draws; familyrank1 median paired change>=-.01 in both pools",
        "H2_secondary_criterion": "For each selector and box/rank1 familyrank2: OOB median and each fresh clean median within.02, and agree whether median>=.05. All four configurations/eight checks must pass",
        "secondary": "All960 fresh coefficients and240 internal OOB coefficients, rank1 and point controls, combined5 and positions; never substitute for primary",
        "inference": "Descriptive conditional perturbation criterion, no independent-binomial, bootstrap-draw significance, formal stability-selection guarantee or across-phase alpha-spending",
        "interpretation": "Changing only training selection objective in matched pipeline tests this bounded explanation; positive result does not prove unique cause or independent information in second pair",
        "cost_cap_seconds": 600, "stopping_rule": "One execution, no HPO/refit/winner/ensemble. Stop on failed correctness/preservation or600s experiment time; preserve partial access and never reopen reserved rows as unseen",
        "rows_after_completion": 170000, "unused_after_completion": 30000,
        "attack_payloads_or_metadata_read": False, "new_gpu_trainings": 0, "new_optimizer_updates": 0,
        "novelty_verified": False, "production_source_sha256": EXPECTED_SOURCE,
        "script_sha256": sha(Path(__file__)),
        "input_hashes": {p.relative_to(ROOT).as_posix(): sha(p) for p in watched}}
    assert code_identity()["source_sha256"] == EXPECTED_SOURCE
    if (OUT / "plan.json").exists():
        old = read(OUT / "plan.json")
        assert {k: v for k, v in old.items() if k not in ("frozen_utc", "splits_sha256")} == plan
        plan = old
    else:
        plan["frozen_utc"] = utc()
        np.savez_compressed(OUT / "splits.npz", training=training, excluded=excluded, primary=primary, replication=replication)
        plan["splits_sha256"] = sha(OUT / "splits.npz")
        write_json(OUT / "plan.json", plan)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    # Existing freezes are immutable and compared after removing derived split hash.
    if (OUT / "plan.json").exists():
        plan = read(OUT / "plan.json")
        assert sha(Path(__file__)) == plan["script_sha256"]
        assert sha(OUT / "splits.npz") == plan["splits_sha256"]
        for rel, digest in plan["input_hashes"].items():
            assert sha(ROOT / rel) == digest, rel
    else:
        plan = make_plan()
    if args.prepare_only:
        print("Frozen protocol:", OUT / "plan.json", flush=True)
        return
    if any((OUT / n).exists() for n in ("training_access.json", "evaluation_access.json", "results.json")):
        raise FileExistsError("Completed or partial viewed execution is protected")
    torch.set_num_threads(2)
    started = time.perf_counter()
    def check_cost():
        if time.perf_counter() - started > plan["cost_cap_seconds"]:
            raise TimeoutError("Frozen CPU stopping rule reached; retain partial evidence")
    with np.load(OUT / "splits.npz", allow_pickle=False) as f:
        splits = {k: f[k] for k in f.files}
    with np.load(OLD / "fit.npz", allow_pickle=False) as f:
        baseline = {k: f[k] for k in f.files}
    old_fit = read(OLD / "fit.json")
    with np.load(ALIGN / "fit.npz", allow_pickle=False) as f:
        original = {k: f[k] for k in f.files}
    write_json(OUT / "training_access.json", {"started_utc": utc(), "plan_sha256": sha(OUT / "plan.json")})
    with h5py.File(ROOT / plan["dataset"], "r") as f:
        raw = f["Profiling_traces/traces"][splits["training"]].astype(float)
        target = HW[f["Profiling_traces/labels"][splits["training"]]]
    aligned = shifted(raw, -original["training_offsets"])
    draws = baseline["draw_indices"]
    fits = {"started_utc": utc(), "draws": [], "oob_coefficients": []}
    fit_arrays = {"draw_indices": draws, "training_target": target}
    for number, ids in enumerate(draws):
        check_cost()
        x, y = aligned[ids], target[ids]
        pairs, count, matrix = select_box_pairs(x, y)
        prefix = "draw" + str(number)
        center = x.mean(0)
        np.testing.assert_array_equal(center, baseline[prefix + "__center"])
        fit_arrays[prefix + "__center"] = center
        oob = oob_indices(ids, len(aligned))
        fit_arrays[prefix + "__oob"] = oob
        row = {"draw": number, "pairs": pairs, "eligible_candidates": count,
               "oob_rows": len(oob), "selection_coefficients": {}, "features": {}}
        for family, pair in pairs.items():
            weights, info, covariance = fit_simple_features(x, y, pair)
            row["features"][family] = info
            row["selection_coefficients"][family] = float(matrix[pair[0]-25, pair[1]-25])
            np.testing.assert_allclose(abs(row["selection_coefficients"][family]), info["training_correlations"]["box_product"], atol=1e-12)
            fit_arrays[prefix + "__" + family + "__target_covariance"] = covariance
            for feature, w in weights.items():
                fit_arrays[prefix + "__" + family + "__" + feature] = w
        for selector, bundle, selected in (("point_selector", baseline, old_fit["draws"][number]["pairs"]),
                                           ("box_selector", fit_arrays, pairs)):
            for family, pair in selected.items():
                weights = {feature: bundle[prefix + "__" + family + "__" + feature] for feature in FEATURES}
                products = extract_simple(aligned[oob], center, pair, np.zeros(len(oob), dtype=np.int16), weights)
                fit_arrays[prefix + "__" + selector + "__" + family + "__oob_products"] = products
                for j, feature in enumerate(FEATURES):
                    fits["oob_coefficients"].append({"draw": number, "selector": selector, "family": family,
                        "feature": feature, "correlation": correlation(products[:, j], target[oob])})
        fits["draws"].append(row)
        print("Window-objective training draw:", number+1, "/20", pairs, flush=True)
    fits["finished_utc"] = utc()
    fits["seconds"] = time.perf_counter() - started
    np.savez_compressed(OUT / "fit.npz", **fit_arrays)
    write_json(OUT / "fit.json", fits)
    check_cost()
    write_json(OUT / "evaluation_access.json", {"started_utc": utc(), "plan_sha256": sha(OUT / "plan.json"),
        "fit_sha256": sha(OUT / "fit.npz"), "fit_record_sha256": sha(OUT / "fit.json"), "metadata_or_attack_read": False})
    del raw, aligned, x
    arrays, rows, rng_states = {}, [], {}
    template = {"mean": original["raw__mean"], "variance": original["raw__variance"]}
    median_range = read(ALIGN / "fit.json")["median_raw_training_feature_range"]
    for pool in ("primary", "replication"):
        check_cost()
        write_json(OUT / (pool + "_access.json"), {"started_utc": utc(), "rows": len(splits[pool])})
        with h5py.File(ROOT / plan["dataset"], "r") as f:
            x = f["Profiling_traces/traces"][splits[pool]].astype(float)
            y = HW[f["Profiling_traces/labels"][splits[pool]]]
        ur, zr = np.random.default_rng(9101), np.random.default_rng(9102)
        u, z = ur.random(len(x)), zr.standard_normal(x.shape)
        arrays[pool + "__target"] = y
        rng_states[pool] = {"uniform": ur.bit_generator.state, "normal": zr.bit_generator.state}
        for condition in plan["conditions"]:
            check_cost()
            name, bound = condition["name"], condition["max_shift"]
            injected = np.floor(u * (2*bound+1)).astype(np.int16)-bound
            values = shifted(x, injected) + z * condition["noise_factor"] * median_range
            delta = offsets_batched(values, template)
            prefix = pool + "__" + name
            arrays[prefix + "__offsets"] = delta
            for number in range(20):
                fp = "draw" + str(number)
                for selector, bundle, selected in (("point_selector", baseline, old_fit["draws"][number]["pairs"]),
                                                    ("box_selector", fit_arrays, fits["draws"][number]["pairs"])):
                    for family, pair in selected.items():
                        weights = {feature: bundle[fp + "__" + family + "__" + feature] for feature in FEATURES}
                        products = extract_simple(values, fit_arrays[fp + "__center"], pair, delta, weights)
                        arrays[prefix + "__" + fp + "__" + selector + "__" + family] = products
                        for j, feature in enumerate(FEATURES):
                            rows.append({"pool": pool, "condition": name, "draw": number, "selector": selector,
                                "family": family, "feature": feature, "pair": pair, "correlation": correlation(products[:, j], y)})
            print("Fresh objective confirmation:", pool, name, flush=True)
    summaries = []
    for pool in ("primary", "replication"):
        for condition in ("clean", "combined5"):
            for family in ("pair1", "pair2"):
                for feature in FEATURES:
                    values = [[r["correlation"] for r in rows if (r["pool"], r["condition"], r["family"], r["feature"], r["selector"])
                               == (pool, condition, family, feature, sel)] for sel in SELECTORS]
                    summaries.append({"pool": pool, "condition": condition, "family": family, "feature": feature,
                                      **summarize_pair(values[1], values[0])})
    primary = [r for r in summaries if r["condition"] == "clean" and r["feature"] == "box_product"]
    support = all(r["median_paired_difference"] >= -.01 if r["family"] == "pair1" else
        r["median_paired_difference"] >= .02 and r["window_median"] >= .05 and r["window_positive_draws"] >= 16 for r in primary)
    prediction = []
    for selector in SELECTORS:
        for feature in ("box_product", "covariance_rank1"):
            internal = np.median([r["correlation"] for r in fits["oob_coefficients"]
                                  if (r["selector"], r["family"], r["feature"]) == (selector, "pair2", feature)])
            for pool in ("primary", "replication"):
                fresh = np.median([r["correlation"] for r in rows if (r["selector"], r["family"], r["feature"], r["pool"], r["condition"])
                                   == (selector, "pair2", feature, pool, "clean")])
                prediction.append({"selector": selector, "feature": feature, "pool": pool,
                    "oob_median": float(internal), "fresh_median": float(fresh),
                    "support": bool(abs(internal-fresh) <= .02 and (internal >= .05) == (fresh >= .05))})
    assert len(rows) == 960 and len(fits["oob_coefficients"]) == 240 and len(prediction) == 8
    for rel, digest in plan["input_hashes"].items():
        assert sha(ROOT / rel) == digest, rel
    assert code_identity()["source_sha256"] == EXPECTED_SOURCE
    np.savez_compressed(OUT / "arrays.npz", **arrays)
    result = {"plan_sha256": sha(OUT / "plan.json"), "fit_sha256": sha(OUT / "fit.npz"),
        "arrays_sha256": sha(OUT / "arrays.npz"), "correlations": rows, "summaries": summaries,
        "H1_primary_met": bool(support), "H2_secondary_met": all(r["support"] for r in prediction),
        "oob_prediction": prediction, "seconds": time.perf_counter()-started, "rng_states": rng_states,
        "environment": environment(torch.device("cpu")), "new_attack_reads": False,
        "new_gpu_trainings": 0, "new_optimizer_updates": 0, "variable_viewed_profiling_rows": 170000,
        "remaining_unused_profiling_rows": 30000, "production_source_sha256": EXPECTED_SOURCE}
    write_json(OUT / "results.json", result)
    print(json.dumps({"seconds": result["seconds"], "H1_primary_met": support,
                      "H2_secondary_met": result["H2_secondary_met"], "primary": primary}, indent=2), flush=True)


if __name__ == "__main__":
    main()
