"""Prospective follow-up: fit and extract features in each pipeline's own coordinates."""
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
from paper_alignment import (ROOT, RUN, EXPECTED_SOURCE, read, sha, fit_template, estimate_offsets,
    corruption_pipelines, independent_endpoint)
from audit_correlation_robustness import selected_product, recovery

OUT = ROOT / "outputs/paper_alignment_coordinates_2026-10-05"
FIRST = ROOT / "outputs/paper_alignment_2026-10-05"


def coordinate_domain(values, training, minimum, scale, pipeline):
    """Represent both template and observations in the domain in which shifts act."""
    if pipeline == "raw_shift":
        return np.asarray(values, dtype=np.float64), fit_template(training)
    if pipeline != "feature_shift_surrogate":
        raise ValueError("Unknown corruption coordinates")
    training_n = (np.asarray(training, dtype=np.float64) - minimum) / scale
    values_n = (np.asarray(values, dtype=np.float64) - minimum) / scale
    return values_n, fit_template(training_n)


def make_plan():
    if (OUT / "results.json").exists():
        raise FileExistsError("Completed follow-up is protected")
    OUT.mkdir(parents=True, exist_ok=True)
    with np.load(FIRST / "splits.npz", allow_pickle=False) as bundle:
        training, validation, viewed_confirmation = [bundle[n] for n in ("training", "validation", "confirmation")]
    excluded = np.unique(np.concatenate((training, validation, viewed_confirmation)))
    remaining = np.setdiff1d(np.arange(50000), excluded)
    confirmation = np.sort(np.random.default_rng(20261006).choice(remaining, 5000, replace=False))
    first = read(FIRST / "plan.json")
    plan = {"authorization": first["authorization"],
        "reason": "Phase-one raw-domain scoring on a feature-shift surrogate also changes centering/scales; isolate this with coordinate-consistent templates/extraction",
        "relationship_to_first_confirmation": "First confirmation has been viewed. Not reused for fit, tuning or new confirmation; follow-up has a fresh disjoint profiling pool",
        "training_rows": 10000, "validation_rows": 5000, "fresh_confirmation_rows": 5000,
        "confirmation_seed": 20261006, "original_confirmation_excluded": True,
        "conditions": first["conditions"], "pairs": first["pairs"], "methods": first["methods"],
        "validation_pipelines": ["feature_shift_surrogate"],
        "confirmation_pipelines": first["pipelines"],
        "domains": {"raw_shift": "Raw waveform mean/variance and raw-centered products",
                    "feature_shift_surrogate": "N(observation), moments fitted on N(training), normalized-centered products"},
        "estimator": "Same NCC/diagonal-Gaussian scores and ±10 search as phase one; no new hyperparameters",
        "randomness": first["randomness"], "budget": 2000, "repetitions": 20,
        "noise": first["noise_definition"],
        "primary_condition": "combined5", "primary_method": "gaussian_template",
        "criterion": "Fresh confirmation: both raw-shift pairs have SR>=.9 and improvement over fixed>=.1 without clean loss>.1",
        "order_comparison": "Compare raw and surrogate with coordinate-consistent extraction; attribute only remaining difference to pipeline/model interactions",
        "novelty": "Unverified; methods and normalization issue have known precedents. Affine coordinate correction is an implementation/attribution control",
        "no_post_validation_parameter_selection": True,
        "source_sha256": EXPECTED_SOURCE, "script_sha256": sha(Path(__file__)),
        "phase_one_script_sha256": sha(ROOT / "notebooks/paper_alignment.py"),
        "phase_one_results_sha256": sha(FIRST / "results.json"),
        "input_hashes": first["input_hashes"],
        "final_attack_payloads_read": False, "new_gpu_trainings": 0, "new_real_data_optimizer_updates": 0}
    assert code_identity()["source_sha256"] == EXPECTED_SOURCE
    if (OUT / "plan.json").exists():
        assert read(OUT / "plan.json") == plan
    else:
        write_json(OUT / "plan.json", plan)
        np.savez_compressed(OUT / "splits.npz", training=training, validation=validation,
                            confirmation=confirmation, excluded_first_confirmation=viewed_confirmation)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    plan = make_plan()
    if args.prepare_only:
        print("Frozen coordinate follow-up:", OUT / "plan.json", flush=True)
        return
    torch.set_num_threads(2)
    started = time.perf_counter()
    with np.load(OUT / "splits.npz", allow_pickle=False) as archive:
        splits = {name: archive[name] for name in archive.files}
    assert len(np.unique(np.concatenate(list(splits.values())))) == 25000
    with h5py.File(ROOT / "data/ASCAD.h5", "r") as handle:
        training = handle["Profiling_traces/traces"][splits["training"]].astype(np.float64)
    minimum, scale = training.min(axis=0), training.max(axis=0) - training.min(axis=0)
    scale[scale == 0] = 1
    median_range = float(np.median(scale))
    rows, alignments, arrays, checks = [], [], {}, 0
    for pool in ("validation", "confirmation"):
        with h5py.File(ROOT / "data/ASCAD.h5", "r") as handle:
            group = handle["Profiling_traces"]
            x = group["traces"][splits[pool]].astype(np.float64)
            metadata = group["metadata"][splits[pool]]
        plaintext = metadata["plaintext"][:, 2]
        keys = np.unique(metadata["key"][:, 2])
        assert len(keys) == 1
        key = int(keys[0])
        hypotheses = np.array([i.bit_count() for i in range(256)])[candidate_labels(plaintext)]
        rng = np.random.default_rng(8001)
        orders = [rng.permutation(len(x))[:2000] for _ in range(20)]
        u = np.random.default_rng(9101).random(len(x))
        z = np.random.default_rng(9102).standard_normal(x.shape)
        cache = {}
        for condition in plan["conditions"]:
            name, width = condition["name"], condition["max_shift"]
            offsets = np.floor(u * (2 * width + 1)).astype(np.int16) - width
            noise = z * condition["noise_factor"] * median_range
            pipelines, _ = corruption_pipelines(x, minimum, scale, offsets, noise)
            edges, _ = corruption_pipelines(x, minimum, scale, offsets, noise, "edge")
            prefix = pool + "__" + name
            arrays[prefix + "__true_offsets"] = offsets
            names = plan["validation_pipelines"] if pool == "validation" else plan["confirmation_pipelines"]
            for pipeline in names:
                values, template = coordinate_domain(pipelines[pipeline], training, minimum, scale, pipeline)
                edge, _ = coordinate_domain(edges[pipeline], training, minimum, scale, pipeline)
                estimates = {"fixed": np.zeros(len(x), dtype=np.int16), "oracle_known_shift": offsets}
                for method in ("ncc_template", "gaussian_template"):
                    estimates[method], scores = estimate_offsets(values, template, method)
                    edge_estimates, edge_scores = estimate_offsets(edge, template, method)
                    assert np.array_equal(estimates[method], edge_estimates)
                    assert np.allclose(scores, edge_scores, atol=1e-12, rtol=0)
                    alignments.append({"pool": pool, "condition": name, "pipeline": pipeline, "method": method,
                        "exact_shift_fraction": float((estimates[method] == offsets).mean()),
                        "mean_absolute_error": float(np.abs(estimates[method].astype(int) - offsets).mean()),
                        "padding_independent": True})
                for method in plan["methods"]:
                    stem = prefix + "__" + pipeline + "__" + method
                    arrays[stem + "__estimated_offsets"] = estimates[method]
                    for family, pair in plan["pairs"].items():
                        product = selected_product(values, template["mean"], pair, estimates[method])
                        product_edge = selected_product(edge, template["mean"], pair, estimates[method])
                        assert np.array_equal(product, product_edge)
                        digest = hashlib.sha256(product.tobytes()).hexdigest()
                        if digest not in cache:
                            cache[digest] = recovery(product, hypotheses, key, orders)
                        summary, curves = cache[digest]
                        for index, order in enumerate(orders):
                            assert independent_endpoint(product, hypotheses, key, order) == curves["ranks"][index, -1]
                            checks += 1
                        arrays[stem + "__" + family + "__ranks"] = curves["ranks"]
                        rows.append({"pool": pool, "condition": name, "pipeline": pipeline,
                            "method": method, "family": family, **summary})
            print("Completed coordinate follow-up:", pool, name, flush=True)
    assert len(rows) == 96 and checks == 1920
    for relative, expected in plan["input_hashes"].items():
        assert sha(ROOT / relative) == expected
    assert sha(Path(__file__)) == plan["script_sha256"]
    assert sha(FIRST / "results.json") == plan["phase_one_results_sha256"]
    assert code_identity()["source_sha256"] == EXPECTED_SOURCE
    np.savez_compressed(OUT / "arrays.npz", **arrays)
    record = {"plan_sha256": sha(OUT / "plan.json"), "results": rows, "alignment": alignments,
        "environment": environment(torch.device("cpu")), "training_range_median": median_range,
        "independent_endpoint_checks": checks, "original_inputs_preserved": True,
        "confirmation_selection_performed_after_results": False,
        "new_gpu_trainings": 0, "full_gpu_trainings_total": 3,
        "new_real_data_optimizer_updates": 0, "final_attack_payloads_read": False,
        "seconds": time.perf_counter() - started}
    write_json(OUT / "results.json", record)
    print(json.dumps({"seconds": record["seconds"], "confirmation": [r for r in rows if
        r["pool"] == "confirmation" and r["condition"] == "combined5"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
