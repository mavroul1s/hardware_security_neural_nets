"""Train-label-only full pair selection followed by prospective raw-domain recovery."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import h5py
import numpy as np
import torch
from sca.aes import candidate_labels
from sca.train import code_identity, environment, write_json
from paper_alignment import (ROOT, RUN, EXPECTED_SOURCE, read, sha, fit_template,
    estimate_offsets, shifted, independent_endpoint)
from audit_correlation_robustness import recovery, selected_product

OUT = ROOT / "outputs/paper_maskfree_2026-10-05"
FIRST = ROOT / "outputs/paper_alignment_2026-10-05"
SECOND = ROOT / "outputs/paper_alignment_coordinates_2026-10-05"


def pair_correlations(training, hw_labels):
    """All centered-product Pearson coefficients via three training-only matrix products."""
    x, labels = np.asarray(training, dtype=np.float64), np.asarray(hw_labels, dtype=np.float64)
    if x.ndim != 2 or labels.shape != (len(x),) or len(x) < 2 or not np.isfinite(x).all() or not np.isfinite(labels).all():
        raise ValueError("Expected finite aligned training traces and labels")
    centered = x - x.mean(axis=0)
    h = labels - labels.mean()
    h_variance = np.mean(h * h)
    if h_variance <= 0:
        raise ValueError("Constant target cannot select a pair")
    n = len(x)
    product_mean = centered.T @ centered / n
    square = centered * centered
    product_variance = np.maximum(square.T @ square / n - product_mean * product_mean, 0)
    covariance = centered.T @ (centered * h[:, None]) / n
    denominator = np.sqrt(product_variance * h_variance)
    return np.clip(np.divide(covariance, denominator, out=np.zeros_like(covariance), where=denominator > 0), -1, 1)


def select_pairs(correlations, separation=50, diversity=20):
    matrix = np.asarray(correlations, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or not np.isfinite(matrix).all():
        raise ValueError("Expected finite square correlation matrix")
    a, b = np.triu_indices(len(matrix), k=separation)
    candidates = np.column_stack((a, b))
    scores = np.abs(matrix[a, b])
    first = candidates[int(scores.argmax())]
    allowed = np.all(np.abs(candidates[:, :, None] - first[None, None, :]) >= diversity, axis=(1, 2))
    if not allowed.any():
        raise ValueError("No diverse second pair")
    indices = np.flatnonzero(allowed)
    second = candidates[indices[int(scores[allowed].argmax())]]
    return {"pair1": first.tolist(), "pair2": second.tolist()}, len(candidates)


def make_plan():
    if (OUT / "results.json").exists():
        raise FileExistsError("Completed mask-free experiment is protected")
    OUT.mkdir(parents=True, exist_ok=True)
    with np.load(SECOND / "splits.npz", allow_pickle=False) as bundle:
        training, validation = bundle["training"], bundle["validation"]
        excluded = np.unique(np.concatenate([bundle[name] for name in bundle.files]))
    remaining = np.setdiff1d(np.arange(50000), excluded)
    confirmation = np.sort(np.random.default_rng(20261007).choice(remaining, 5000, replace=False))
    first = read(FIRST / "plan.json")
    plan = {"authorization": first["authorization"],
        "reason": "Remove privileged mask/share metadata from point selection; compare train-label-accessible second-order features with frozen trace-only alignment",
        "training_rows": 10000, "validation_rows": 5000, "fresh_confirmation_rows": 5000,
        "confirmation_seed": 20261007, "previous_confirmations_excluded": True,
        "selection_target": "HW of provided profiling-training identity labels; no mask or training key metadata read",
        "selection_score": "Absolute Pearson(centered product, HW label) over all upper-triangle pairs separated by >=50 samples",
        "minimum_point_separation": 50, "second_pair_point_diversity": 20,
        "selection_ties": "First row-major upper-triangle pair at exact maximum",
        "pair_count": 2, "selection_repeated_after_validation": False,
        "methods": first["methods"], "conditions": first["conditions"],
        "alignment": "Same unconditional raw mean/diagonal variance or NCC; ±10 search, no labels/keys/masks at inference",
        "pipeline": "Raw global shift followed by uniform raw Gaussian noise; proper raw-centered extraction",
        "noise_definition": first["noise_definition"], "randomness": first["randomness"],
        "budget": 2000, "repetitions": 20, "primary_condition": "combined5",
        "primary_method": "gaussian_template",
        "support_criterion": "Fresh confirmation: both selected pairs have Gaussian SR>=.9 and >=.1 improvement over fixed, clean loss<=.1",
        "novelty": "Unverified; supervised second-order feature selection and alignment have precedents. Efficient matrix evaluation is not claimed novel",
        "source_sha256": EXPECTED_SOURCE, "script_sha256": sha(Path(__file__)),
        "alignment_script_sha256": sha(ROOT / "notebooks/paper_alignment.py"),
        "input_hashes": first["input_hashes"],
        "previous_results_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p)
                                   for p in (FIRST / "results.json", SECOND / "results.json")},
        "final_attack_payloads_read": False, "new_gpu_trainings": 0, "new_real_data_optimizer_updates": 0}
    assert code_identity()["source_sha256"] == EXPECTED_SOURCE
    if (OUT / "plan.json").exists():
        assert read(OUT / "plan.json") == plan
    else:
        write_json(OUT / "plan.json", plan)
        np.savez_compressed(OUT / "splits.npz", training=training, validation=validation, confirmation=confirmation)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    plan = make_plan()
    if args.prepare_only:
        print("Frozen mask-free plan:", OUT / "plan.json", flush=True)
        return
    torch.set_num_threads(2)
    started = time.perf_counter()
    with np.load(OUT / "splits.npz", allow_pickle=False) as bundle:
        splits = {name: bundle[name] for name in bundle.files}
    with h5py.File(ROOT / "data/ASCAD.h5", "r") as handle:
        group = handle["Profiling_traces"]
        training = group["traces"][splits["training"]].astype(np.float64)
        labels = group["labels"][splits["training"]]
    hw = np.array([value.bit_count() for value in range(256)])
    selection_started = time.perf_counter()
    correlations = pair_correlations(training, hw[labels])
    pairs, candidates = select_pairs(correlations)
    selection_seconds = time.perf_counter() - selection_started
    selection = {"pairs": pairs, "candidate_pairs": candidates,
        "training_correlations": {name: float(correlations[tuple(pair)]) for name, pair in pairs.items()},
        "training_only": True, "mask_metadata_read_for_selection": False,
        "keys_read_for_selection": False, "selection_seconds": selection_seconds,
        "plan_sha256": sha(OUT / "plan.json")}
    write_json(OUT / "selection.json", selection)  # Before reading validation/confirmation payloads.
    np.savez_compressed(OUT / "training_pair_scores.npz", correlations=correlations)
    print("Frozen training-label-only pairs:", pairs, flush=True)
    template = fit_template(training)
    ranges = training.max(axis=0) - training.min(axis=0)
    ranges[ranges == 0] = 1
    median_range = float(np.median(ranges))
    results, alignment, arrays, checked = [], [], {}, 0
    for pool in ("validation", "confirmation"):
        with h5py.File(ROOT / "data/ASCAD.h5", "r") as handle:
            group = handle["Profiling_traces"]
            x = group["traces"][splits[pool]].astype(np.float64)
            metadata = group["metadata"][splits[pool]]
        keys = np.unique(metadata["key"][:, 2])
        assert len(keys) == 1
        key = int(keys[0])
        hypotheses = hw[candidate_labels(metadata["plaintext"][:, 2])]
        rng = np.random.default_rng(8001)
        orders = [rng.permutation(len(x))[:2000] for _ in range(20)]
        u, z = np.random.default_rng(9101).random(len(x)), np.random.default_rng(9102).standard_normal(x.shape)
        cache = {}
        for condition in plan["conditions"]:
            name, width = condition["name"], condition["max_shift"]
            true_offsets = np.floor(u * (2 * width + 1)).astype(np.int16) - width
            noise = z * condition["noise_factor"] * median_range
            values = shifted(x, true_offsets) + noise
            edge = shifted(x, true_offsets, "edge") + noise
            prefix = pool + "__" + name
            arrays[prefix + "__true_offsets"] = true_offsets
            estimates = {"fixed": np.zeros(len(x), dtype=np.int16), "oracle_known_shift": true_offsets}
            for method in ("ncc_template", "gaussian_template"):
                estimates[method], scores = estimate_offsets(values, template, method)
                edge_estimates, edge_scores = estimate_offsets(edge, template, method)
                assert np.array_equal(estimates[method], edge_estimates) and np.array_equal(scores, edge_scores)
                alignment.append({"pool": pool, "condition": name, "method": method,
                    "exact_shift_fraction": float((estimates[method] == true_offsets).mean()),
                    "padding_independent": True})
            for method in plan["methods"]:
                arrays[prefix + "__" + method + "__estimated_offsets"] = estimates[method]
                for family, pair in pairs.items():
                    product = selected_product(values, template["mean"], pair, estimates[method])
                    assert np.array_equal(product, selected_product(edge, template["mean"], pair, estimates[method]))
                    digest = hashlib.sha256(product.tobytes()).hexdigest()
                    if digest not in cache:
                        cache[digest] = recovery(product, hypotheses, key, orders)
                    summary, curves = cache[digest]
                    for index, order in enumerate(orders):
                        assert independent_endpoint(product, hypotheses, key, order) == curves["ranks"][index, -1]
                        checked += 1
                    arrays[prefix + "__" + method + "__" + family + "__ranks"] = curves["ranks"]
                    results.append({"pool": pool, "condition": name, "method": method,
                                    "family": family, "pair": pair, **summary})
            print("Completed mask-free experiment:", pool, name, flush=True)
    assert len(results) == 64 and checked == 1280
    for relative, expected in {**plan["input_hashes"], **plan["previous_results_sha256"]}.items():
        assert sha(ROOT / relative) == expected
    assert sha(Path(__file__)) == plan["script_sha256"] and code_identity()["source_sha256"] == EXPECTED_SOURCE
    np.savez_compressed(OUT / "arrays.npz", **arrays)
    record = {"plan_sha256": sha(OUT / "plan.json"), "selection_sha256": sha(OUT / "selection.json"),
        "results": results, "alignment": alignment, "pairs": pairs,
        "candidate_pairs": candidates, "environment": environment(torch.device("cpu")),
        "independent_endpoint_checks": checked, "training_range_median": median_range,
        "mask_metadata_used_for_selection": False, "confirmation_used_for_selection": False,
        "original_artifacts_preserved": True, "final_attack_payloads_read": False,
        "new_gpu_trainings": 0, "full_gpu_trainings_total": 3, "new_real_data_optimizer_updates": 0,
        "selection_seconds": selection_seconds, "seconds": time.perf_counter() - started}
    write_json(OUT / "results.json", record)
    print(json.dumps({"seconds": record["seconds"], "pairs": pairs, "primary_confirmation": [r for r in results if
        r["pool"] == "confirmation" and r["condition"] == "combined5"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
