"""Prospective CPU window features and exact additive-noise second-order regression."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import h5py
import numpy as np
import torch
from sca.aes import SBOX, candidate_labels
from sca.train import code_identity, environment, write_json
from paper_alignment import ROOT, RUN, EXPECTED_SOURCE, read, sha, fit_template, estimate_offsets, shifted, independent_endpoint
from paper_alignment_controls import sad_offsets
from paper_selection_audit import correlation, fresh_rows
from paper_variable_campaign import constant_evaluation_key, bytes_sha
from audit_correlation_robustness import recovery

OUT = ROOT / "outputs/paper_window_regression_2026-10-06"
PRIOR = ROOT / "outputs/paper_selection_audit_2026-10-06"
HW = np.array([v.bit_count() for v in range(256)])
FEATURES = ["point", "box_product", "diagonal_products", "covariance_rank1", "ridge_clean", "ridge_noise"]
ALIGNMENTS = ["fixed", "gaussian_template", "sad_training_mean"]


def utc():
    return datetime.now(timezone.utc).isoformat()


def window_columns(pair, radius, width):
    if len(pair) != 2 or radius < 0:
        raise ValueError("Expected two disjoint interior windows")
    a, b = [np.arange(p - radius, p + radius + 1) for p in pair]
    if a[0] < 0 or b[-1] >= width or np.intersect1d(a, b).size:
        raise ValueError("Windows must be in bounds and disjoint")
    return a, b


def noise_product_covariance(a, b, sigma):
    """Exact expected covariance increment for disjoint centered windows and iid noise.

    P_ij=A_i*B_j. N= sigma^2*(C_A kron I + I kron C_B)+sigma^4*I.
    This conditions on the observed training rows; it does not model native noise.
    """
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.ndim != 2 or b.ndim != 2 or len(a) != len(b) or not len(a) or sigma < 0 or not np.isfinite(sigma):
        raise ValueError("Expected two finite equally sized centered windows and nonnegative noise")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Nonfinite windows")
    return (sigma ** 2 * (np.kron(a.T @ a / len(a), np.eye(b.shape[1])) +
                         np.kron(np.eye(a.shape[1]), b.T @ b / len(b))) +
            sigma ** 4 * np.eye(a.shape[1] * b.shape[1]))


def orient_weight(weight, products, target):
    """Fix scale and direction using training only; positive train correlation."""
    w = np.asarray(weight, dtype=float).ravel().copy()
    norm = np.linalg.norm(w)
    if norm == 0 or not np.isfinite(w).all():
        raise ValueError("Degenerate fitted weight")
    w /= norm
    r = correlation(products @ w, target)
    if r < 0:
        w *= -1
    return w, abs(r)


def fit_weights(training, target, pair, radius=5, sigma=0., ridge=.01):
    """One closed-form fit at the original 10k budget; no optimization or tuning."""
    x, y = np.asarray(training, dtype=float), np.asarray(target, dtype=float)
    if x.ndim != 2 or y.shape != (len(x),) or len(x) < 2 or ridge <= 0:
        raise ValueError("Invalid fit data or ridge penalty")
    if not np.isfinite(x).all() or not np.isfinite(y).all() or not y.std():
        raise ValueError("Expected finite nonconstant fit data")
    ca, cb = window_columns(pair, radius, x.shape[1])
    center = x.mean(axis=0)
    a, b = x[:, ca] - center[ca], x[:, cb] - center[cb]
    products = (a[:, :, None] * b[:, None, :]).reshape(len(x), -1)
    q = products - products.mean(axis=0)
    g = q.T @ q / len(x)
    c = q.T @ (y - y.mean()) / len(x)
    floor = max(float(np.median(np.diag(g))) * 1e-12, 1e-12)
    scale = np.sqrt(np.maximum(np.diag(g), floor))
    scaled_g = g / scale[:, None] / scale[None, :]
    n = noise_product_covariance(a, b, sigma)
    scaled_n = n / scale[:, None] / scale[None, :]
    m = len(ca)
    point = np.zeros((m, m)); point[radius, radius] = 1
    u, singular, vh = np.linalg.svd(c.reshape(m, m), full_matrices=False)
    weights = {"point": point.ravel(), "box_product": np.ones(m * m) / (m * m),
               "diagonal_products": (np.eye(m) / m).ravel(),
               "covariance_rank1": np.outer(u[:, 0], vh[0]).ravel()}
    for name, increment in (("ridge_clean", 0.), ("ridge_noise", scaled_n)):
        weights[name] = np.linalg.solve(scaled_g + increment + ridge * np.eye(m * m), c / scale) / scale
    fitted, scores = {}, {}
    for name, w in weights.items():
        fitted[name], scores[name] = orient_weight(w, products, y)
    return fitted, {"training_correlations": scores, "singular_values": singular.tolist(),
        "product_variance_floor": floor, "ridge_penalty_in_training_standardized_product_coordinates": ridge,
        "sigma_raw": sigma}, {"product_covariance": g, "target_covariance": c,
        "noise_covariance": n, "product_scale": scale}


def extract_features(traces, center, pair, radius, offsets, weights):
    x, mean = np.asarray(traces, dtype=float), np.asarray(center, dtype=float)
    ca, cb = window_columns(pair, radius, x.shape[1])
    delta = np.asarray(offsets)
    if delta.shape != (len(x),) or not np.issubdtype(delta.dtype, np.integer) or mean.shape != (x.shape[1],):
        raise ValueError("Invalid offsets or training center")
    ia, ib = ca[None, :] + delta[:, None], cb[None, :] + delta[:, None]
    if min(ia.min(), ib.min()) < 0 or max(ia.max(), ib.max()) >= x.shape[1]:
        raise ValueError("Window cropped after alignment")
    a = x[np.arange(len(x))[:, None], ia] - mean[ca]
    b = x[np.arange(len(x))[:, None], ib] - mean[cb]
    p = (a[:, :, None] * b[:, None, :]).reshape(len(x), -1)
    return np.column_stack([p @ np.asarray(weights[name]) for name in FEATURES])


def bootstrap_difference(a, b, target, count=1999, seed=2026):
    """Paired row percentile bootstrap; conditional on fit and realized corruption."""
    data = np.column_stack((a, b, target)).astype(float)
    rng = np.random.default_rng(seed)
    draws = []
    for start in range(0, count, 32):
        idx = rng.integers(0, len(data), (min(32, count - start), len(data)))
        z = data[idx]; z -= z.mean(axis=1, keepdims=True)
        denominators = np.sqrt(np.sum(z[:, :, :2] ** 2, axis=1) * np.sum(z[:, :, 2] ** 2, axis=1)[:, None])
        corr = np.divide(np.sum(z[:, :, :2] * z[:, :, 2, None], axis=1), denominators,
                         out=np.zeros_like(denominators), where=denominators > 0)
        draws.extend(corr[:, 0] - corr[:, 1])
    return np.asarray(draws), rng.bit_generator.state


def make_plan():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "results.json").exists():
        raise FileExistsError("Completed prospective experiment is protected")
    assert code_identity()["source_sha256"] == EXPECTED_SOURCE
    split_arrays, campaigns = {}, {}
    with np.load(PRIOR / "splits.npz", allow_pickle=False) as old:
        for campaign, width, total, selection in (
            ("fixed", 700, 50000, "outputs/paper_maskfree_2026-10-05/selection.json"),
            ("variable", 1400, 200000, "outputs/paper_variable_campaign_2026-10-05/fit.json")):
            excluded = np.union1d(old[campaign + "__excluded"], old[campaign + "__confirmation"])
            primary = fresh_rows(total, excluded, seed=20261011)
            replication = fresh_rows(total, np.union1d(excluded, primary), seed=20261012)
            for role, rows in (("training", old[campaign + "__training"]), ("excluded", excluded),
                               ("primary", primary), ("replication", replication)):
                split_arrays[campaign + "__" + role] = rows
            campaigns[campaign] = {"dataset": "data/ASCAD" + ("_variable" if campaign == "variable" else "") + ".h5",
                "width": width, "profiling_rows": total, "pairs": read(ROOT / selection)["pairs"],
                "previously_viewed_profiling_rows": len(excluded), "selection_record": selection}
    with np.load(ROOT / "outputs/paper_variable_campaign_2026-10-05/splits.npz", allow_pickle=False) as old:
        split_arrays["variable__excluded_attack"] = old["attack"]
        split_arrays["variable__fresh_attack"] = fresh_rows(100000, old["attack"], seed=20261013)
    watched = [PRIOR / n for n in ("plan.json", "results.json", "splits.npz")]
    watched += [RUN / n for n in ("best.pt", "last.pt", "manifest.json", "splits.npz")]
    watched += [ROOT / n for n in ("notebooks/kaggle_baseline.ipynb", "outputs/kaggle_resume_input_literature.zip", "outputs/kaggle_project_literature.zip")]
    for config in campaigns.values():
        watched += [ROOT / config["dataset"], ROOT / config["selection_record"]]
    watched += [ROOT / "outputs/paper_variable_campaign_2026-10-05/splits.npz"]
    dependencies = ["paper_alignment.py", "paper_alignment_controls.py", "paper_selection_audit.py", "paper_variable_campaign.py", "audit_correlation_robustness.py", "diagnose_second_order_correlation.py"]
    watched += [ROOT / "notebooks" / n for n in dependencies]
    plan = {"authorization": "User explicitly requested more paper-oriented experiments on 2026-10-06; CPU statistical feature fits, preserving neural/GPU scope",
        "research_reason": "Test local signed leakage cancellation and whether exact quadratic-feature noise covariance improves over equal-budget clean regression; hypothesis from training-only features, algebra and known literature, no attack-guided tuning",
        "novelty": "Unverified: averaging, SVD, second-order regression and input-noise regularization are known; this is a controlled prospective evaluation of an analytic quadratic-noise correction",
        "campaigns": campaigns, "training_rows_each": 10000, "new_profiling_pools_each": ["primary", "replication"],
        "pool_rows": 5000, "pool_seeds": [20261011, 20261012], "fresh_attack_seed": 20261013,
        "new_attack_scope": "Disjoint variable-key attack rows, same previously evaluated constant key/campaign; not a new unseen key or device. Original fixed attack remains locked. No method or parameter selection based on any attack result",
        "features": FEATURES, "alignments": ALIGNMENTS, "radius": 5, "window_width": 11, "ridge": .01,
        "window_reason": "Fixed symmetric local support spanning the primary injected shift bound; no radius search",
        "fit": "Original raw training10k/provided identity labels converted to HW; original pair centers. Standardized 121 cross-products. Ridge .01 in both fits; noise correction sigma=.1*median(training feature range), not tuned",
        "noise_formula": "sigma^2*(C_A kron I_B + I_A kron C_B)+sigma^4*I; disjoint windows, zero-mean iid added noise independent of observed training traces and labels",
        "noise_limitations": "Exact for known artificial additive noise before an externally fixed extraction; not native/colored noise, physical hiding, or after noise-dependent alignment selection",
        "comparability": "Six feature variants share frozen point centers and training rows; windows use 22 inputs vs point's 2; rank1 has train-label weights; ridge 121 coefficients. No equal-information CNN claim",
        "conditions": [{"name": "clean", "max_shift": 0, "noise_factor": 0.},
            {"name": "noise5", "max_shift": 0, "noise_factor": .1},
            {"name": "shift5", "max_shift": 5, "noise_factor": 0.},
            {"name": "combined5", "max_shift": 5, "noise_factor": .1},
            {"name": "combined10_ood", "max_shift": 10, "noise_factor": .2}],
        "corruption": "S(raw x)+sigma*z, zero padding. No clipping/MinMax transform. Relative noise factors equal, raw units campaign-dependent, not a pure key-change experiment",
        "alignment": "Training-only unconditional mean/variance; inclusive [-10,10], same prior tie rules, SAD adaptation. No labels or keys in alignment",
        "randomness": {"uniform": 9101, "normal": 9102, "orders": 8001, "bootstrap": 2026},
        "pairing": "Same U/Z/orders for methods within pools and same restarted streams across pools of equal size; orders overlap, not independent training runs or keys",
        "budget": 2000, "repetitions": 20, "rank_tolerance": 1e-12,
        "primary": "Pair1 combined5/Gaussian signed HW correlation: ridge_noise minus ridge_clean in each of four new profiling pools",
        "primary_support": "All four differences >=.01 and all four lower Bonferroni percentile bootstrap bounds >0",
        "bootstrap": {"draws": 1999, "family_tests": 4, "alpha": .05, "two_sided_tail": .05 / 8,
            "scope": "Paired row bootstrap, approximate percentile intervals; conditional on original fit/realized corruption, iid-row assumption. No exact coverage or independent-acquisition claim"},
        "secondary_attack": "Report every frozen method. Predefined ridge_noise/Gaussian pair1 combined5 SR>=18/20 and >=2/20 better than both point and ridge_clean; descriptive one-key benchmark",
        "no_holdout_selection": True, "original_fixed_attack_payloads_read": False, "new_gpu_trainings": 0,
        "new_optimizer_updates": 0, "production_source_sha256": EXPECTED_SOURCE,
        "script_sha256": sha(Path(__file__)), "input_hashes": {p.relative_to(ROOT).as_posix(): sha(p) for p in watched}}
    if (OUT / "plan.json").exists():
        previous = read(OUT / "plan.json")
        assert {k: v for k, v in previous.items() if k != "frozen_utc"} == plan
        plan = previous
        with np.load(OUT / "splits.npz", allow_pickle=False) as f:
            for name, rows in split_arrays.items():
                np.testing.assert_array_equal(rows, f[name])
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
        print("Frozen plan:", OUT / "plan.json", flush=True); return
    if (OUT / "fit.json").exists() or (OUT / "evaluation_access.json").exists():
        raise FileExistsError("Partial execution protected; inspect before retry")
    torch.set_num_threads(2)
    started = time.perf_counter()
    with np.load(OUT / "splits.npz", allow_pickle=False) as f:
        splits = {n: f[n] for n in f.files}
    fit_arrays, fit_records, fit_times = {}, {}, {}
    for campaign, config in plan["campaigns"].items():
        t = time.perf_counter()
        with h5py.File(ROOT / config["dataset"], "r") as f:
            x = f["Profiling_traces/traces"][splits[campaign + "__training"]].astype(float)
            y = HW[f["Profiling_traces/labels"][splits[campaign + "__training"]]]
        template = fit_template(x)
        raw_range = float(np.median(np.ptp(x, axis=0)))
        fit_arrays[campaign + "__mean"] = template["mean"]
        fit_arrays[campaign + "__variance"] = template["variance"]
        fit_records[campaign] = {"median_training_feature_range": raw_range, "families": {}}
        for family, pair in config["pairs"].items():
            weights, stats, moments = fit_weights(x, y, pair, plan["radius"], .1 * raw_range, plan["ridge"])
            fit_records[campaign]["families"][family] = stats
            for name, w in weights.items():
                fit_arrays[campaign + "__" + family + "__" + name] = w
            for name, values in moments.items():
                fit_arrays[campaign + "__" + family + "__" + name] = values
        fit_times[campaign] = time.perf_counter() - t
        print("Completed training-only fit:", campaign, fit_records[campaign], flush=True)
    np.savez_compressed(OUT / "fit.npz", **fit_arrays)
    fit = {"completed_utc": utc(), "campaigns": fit_records, "seconds": fit_times,
        "plan_sha256": sha(OUT / "plan.json"), "fit_npz_sha256": sha(OUT / "fit.npz"),
        "evaluation_payloads_or_metadata_read": False}
    write_json(OUT / "fit.json", fit)
    write_json(OUT / "evaluation_access.json", {"started_utc": utc(), "fit_sha256": sha(OUT / "fit.json"),
        "original_fixed_attack_payloads_read": False, "variable_fresh_attack_rows_will_be_viewed": True})
    arrays, correlations, recoveries, alignment, bootstrap_rows, rng_states, key_audits = {}, [], [], [], [], {}, {}
    checks = 0
    for campaign, config in plan["campaigns"].items():
        center, variance = fit_arrays[campaign + "__mean"], fit_arrays[campaign + "__variance"]
        raw_range = fit_records[campaign]["median_training_feature_range"]
        for pool in ["primary", "replication"] + (["fresh_attack"] if campaign == "variable" else []):
            pool_id = campaign + "__" + pool
            group = "Attack_traces" if pool == "fresh_attack" else "Profiling_traces"
            recover = campaign == "fixed" or pool == "fresh_attack"
            with h5py.File(ROOT / config["dataset"], "r") as f:
                x = f[group + "/traces"][splits[pool_id]].astype(float)
                labels = f[group + "/labels"][splits[pool_id]]
                y = HW[labels]
                if recover:
                    metadata = f[group + "/metadata"][splits[pool_id]]
                    key = constant_evaluation_key(metadata["key"])
                    plaintext = metadata["plaintext"][:, 2]
                    np.testing.assert_array_equal(labels, SBOX[plaintext ^ key[2]])
                    hypotheses = HW[candidate_labels(plaintext)]
                    key_audits[pool_id] = {"full_key_hex": bytes(key).hex(), "target_byte": int(key[2]),
                        "labels_verified": True, "key_read_after_frozen_fit_for_evaluation_only": True}
                    if pool == "fresh_attack":
                        train_keys = f["Profiling_traces/metadata"][splits[campaign + "__training"]]["key"]
                        present = bool(np.all(train_keys == key, axis=1).any())
                        assert not present
                        key_audits[pool_id]["full_key_present_in_training"] = present
                        key_audits[pool_id]["same_key_as_previously_evaluated_campaign"] = bytes(key).hex() == read(ROOT / "outputs/paper_variable_campaign_2026-10-05/results.json")["key_audit"]["attack_key_hex"]
            ur, zr, order_rng = np.random.default_rng(9101), np.random.default_rng(9102), np.random.default_rng(8001)
            u, z = ur.random(len(x)), zr.standard_normal(x.shape)
            orders = np.stack([order_rng.permutation(len(x))[:2000] for _ in range(20)])
            arrays[pool_id + "__orders"] = orders.astype(np.int16)
            arrays[pool_id + "__target"] = y
            rng_states[pool_id] = {"uniform": ur.bit_generator.state, "normal": zr.bit_generator.state,
                "orders": order_rng.bit_generator.state, "normal_draw_sha256": bytes_sha(z)}
            cache = {}
            for condition in plan["conditions"]:
                name, bound = condition["name"], condition["max_shift"]
                true_offsets = np.floor(u * (2 * bound + 1)).astype(np.int16) - bound
                values = shifted(x, true_offsets) + z * condition["noise_factor"] * raw_range
                offsets = {"fixed": np.zeros(len(x), dtype=np.int16),
                    "gaussian_template": estimate_offsets(values, {"mean": center, "variance": variance}, "gaussian_template")[0],
                    "sad_training_mean": sad_offsets(values, center)}
                for method, delta in offsets.items():
                    prefix = pool_id + "__" + name + "__" + method
                    arrays[prefix + "__offsets"] = delta
                    alignment.append({"campaign": campaign, "pool": pool, "condition": name, "alignment": method,
                        "fraction_matching_extra_injected_shift": float(np.mean(delta == true_offsets))})
                    for family, pair in config["pairs"].items():
                        weights = {feature: fit_arrays[campaign + "__" + family + "__" + feature] for feature in FEATURES}
                        products = extract_features(values, center, pair, plan["radius"], delta, weights)
                        arrays[prefix + "__" + family + "__products"] = products
                        for col, feature in enumerate(FEATURES):
                            r = correlation(products[:, col], y)
                            row = {"campaign": campaign, "pool": pool, "condition": name, "alignment": method,
                                "family": family, "feature": feature, "hw_correlation": r}
                            correlations.append(row)
                            if recover:
                                digest = bytes_sha(products[:, col])
                                if digest not in cache:
                                    cache[digest] = recovery(products[:, col], hypotheses, int(key[2]), orders)
                                summary, curves = cache[digest]
                                for j, order in enumerate(orders):
                                    assert independent_endpoint(products[:, col], hypotheses, int(key[2]), order) == curves["ranks"][j, -1]
                                    checks += 1
                                arrays[prefix + "__" + family + "__" + feature + "__ranks"] = curves["ranks"]
                                recoveries.append({**row, **summary})
                        if family == "pair1" and name == "combined5" and method == "gaussian_template" and pool != "fresh_attack":
                            difference = correlation(products[:, 5], y) - correlation(products[:, 4], y)
                            null, state = bootstrap_difference(products[:, 5], products[:, 4], y)
                            lower, upper = np.quantile(null, [.05 / 8, 1 - .05 / 8])
                            arrays[prefix + "__bootstrap_differences"] = null
                            bootstrap_rows.append({"campaign": campaign, "pool": pool, "difference": difference,
                                "lower": float(lower), "upper": float(upper), "support": bool(difference >= .01 and lower > 0), "rng_final_state": state})
                print("Completed prospective comparison:", campaign, pool, name, flush=True)
    assert len(correlations) == 900 and len(recoveries) == 540 and checks == 10800 and len(bootstrap_rows) == 4
    attack = {(r["condition"], r["alignment"], r["family"], r["feature"]): r for r in recoveries if r["pool"] == "fresh_attack"}
    get = lambda f: attack[("combined5", "gaussian_template", "pair1", f)]["sr_at_budget"]
    attack_primary = {"ridge_noise_sr": get("ridge_noise"), "point_sr": get("point"), "ridge_clean_sr": get("ridge_clean")}
    attack_primary["criterion_met"] = get("ridge_noise") >= .9 and get("ridge_noise") - get("point") >= .1 - 1e-12 and get("ridge_noise") - get("ridge_clean") >= .1 - 1e-12
    for relative, expected in plan["input_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    assert sha(Path(__file__)) == plan["script_sha256"] and code_identity()["source_sha256"] == EXPECTED_SOURCE
    np.savez_compressed(OUT / "arrays.npz", **arrays)
    record = {"plan_sha256": sha(OUT / "plan.json"), "fit_sha256": sha(OUT / "fit.json"),
        "access_sha256": sha(OUT / "evaluation_access.json"), "arrays_sha256": sha(OUT / "arrays.npz"),
        "correlations": correlations, "recoveries": recoveries, "alignment": alignment,
        "primary": bootstrap_rows, "primary_support_met": all(r["support"] for r in bootstrap_rows),
        "secondary_attack": attack_primary, "rng_states": rng_states, "key_audits": key_audits,
        "execution_endpoint_checks": checks, "seconds": time.perf_counter() - started,
        "environment": environment(torch.device("cpu")), "production_source_sha256": EXPECTED_SOURCE,
        "all_fits_frozen_before_any_holdout": True, "no_holdout_tuning": True, "original_artifacts_preserved": True,
        "original_fixed_attack_payloads_read": False, "new_variable_attack_subset_viewed": True,
        "full_gpu_trainings_total": 3, "new_gpu_trainings": 0, "new_optimizer_updates": 0}
    write_json(OUT / "results.json", record)
    print(json.dumps({"seconds": record["seconds"], "primary": bootstrap_rows, "secondary_attack": attack_primary}, indent=2), flush=True)


if __name__ == "__main__":
    main()
