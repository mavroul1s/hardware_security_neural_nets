"""Frozen SAD baselines and broken-correspondence control on fresh profiling rows."""
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
from paper_alignment import ROOT, RUN, EXPECTED_SOURCE, read, sha, fit_template, estimate_offsets, shifted, independent_endpoint
from audit_correlation_robustness import selected_product, recovery

OUT = ROOT / "outputs/paper_alignment_controls_2026-10-05"
PHASES = [ROOT / "outputs" / name for name in
    ("paper_alignment_2026-10-05", "paper_alignment_coordinates_2026-10-05", "paper_maskfree_2026-10-05")]
METHODS = ["fixed", "ncc_template", "gaussian_template", "sad_training_mean",
           "sad_training_reference", "gaussian_offsets_rolled", "oracle_known_shift"]


def sad_offsets(traces, reference, max_shift=10):
    """SAD shift search with inclusive bounds and the shared offset tie rule."""
    x, reference = np.asarray(traces, dtype=np.float64), np.asarray(reference, dtype=np.float64)
    if (x.ndim != 2 or reference.shape != (x.shape[1],) or max_shift < 0 or
            x.shape[1] <= 4 * max_shift + 2 or not np.isfinite(x).all() or not np.isfinite(reference).all()):
        raise ValueError("Expected finite traces, reference and a valid search bound")
    columns = np.arange(2 * max_shift, x.shape[1] - 2 * max_shift)
    candidates = sorted(range(-max_shift, max_shift + 1), key=lambda value: (abs(value), value))
    scores = np.stack([np.abs(x[:, columns + offset] - reference[columns]).sum(axis=1) for offset in candidates], axis=1)
    return np.asarray(candidates, dtype=np.int16)[scores.argmin(axis=1)], scores


def representative_reference(training):
    """Select the closest training trace to its unlabeled mean in the fixed score window."""
    x = np.asarray(training, dtype=np.float64)
    if x.ndim != 2 or len(x) == 0 or x.shape[1] != 700 or not np.isfinite(x).all():
        raise ValueError("Expected nonempty finite 700-sample training traces")
    squared_distance = np.mean((x[:, 20:680] - x.mean(axis=0)[20:680]) ** 2, axis=1)
    index = int(np.argmin(squared_distance))
    return index, x[index].copy(), squared_distance


def roll_offsets(offsets):
    """Preserve the shift histogram exactly but break trace-to-estimate correspondence."""
    offsets = np.asarray(offsets)
    if offsets.ndim != 1 or len(offsets) < 2 or not np.issubdtype(offsets.dtype, np.integer):
        raise ValueError("Expected at least two integer shifts")
    return np.roll(offsets, 1)


def make_plan():
    if (OUT / "results.json").exists():
        raise FileExistsError("Completed control experiment is protected")
    OUT.mkdir(parents=True, exist_ok=True)
    first = read(PHASES[0] / "plan.json")
    selection = read(PHASES[2] / "selection.json")
    with np.load(PHASES[2] / "splits.npz", allow_pickle=False) as bundle:
        training, validation = bundle["training"], bundle["validation"]
    previous = []
    for directory in PHASES:
        with np.load(directory / "splits.npz", allow_pickle=False) as bundle:
            previous.append(bundle["confirmation"])
    excluded = np.unique(np.concatenate((training, validation, *previous)))
    assert len(excluded) == 30000
    remaining = np.setdiff1d(np.arange(50000), excluded)
    confirmation = np.sort(np.random.default_rng(20261008).choice(remaining, 5000, replace=False))
    provenance_paths = [directory / name for directory in PHASES for name in ("results.json", "splits.npz")]
    provenance_paths += [PHASES[2] / "selection.json", ROOT / "notebooks/audit_correlation_robustness.py",
                         ROOT / "notebooks/paper_alignment.py"]
    plan = {"authorization": "User requested continuing the paper-oriented CPU extension on 2026-10-05",
        "reason": "Compare familiar SAD baselines and test whether per-trace offset correspondence, rather than its marginal histogram, explains recovery",
        "training_rows": 10000, "validation_rows": 5000, "fresh_confirmation_rows": 5000,
        "confirmation_seed": 20261008, "previous_confirmations_excluded": True,
        "pairs": selection["pairs"], "point_selection": "Frozen phase-three training-label-only selection; no new point search",
        "conditions": first["conditions"], "methods": METHODS, "pipeline": "raw_shift",
        "template": "Unconditional mean/diagonal variance from original 10k training traces only",
        "sad_reference": "Closest training trace to unlabeled training mean by MSE on columns20:680; first sorted-training row on exact tie",
        "sad_source": "https://chipwhisperer.readthedocs.io/en/latest/analyzer-api.html#chipwhisperer.analyzer.preprocessing.resync_sad.ResyncSAD",
        "sad_source_code": "https://raw.githubusercontent.com/newaetech/chipwhisperer/develop/software/chipwhisperer/analyzer/preprocessing/resync_sad.py",
        "sad_comparison_scope": "SAD adaptations, not package reproduction: train mean or train-selected reference, inclusive ±10, common abs-offset tie rule, no threshold-based trace rejection",
        "score_columns": [20, 680], "search_bound": 10,
        "tie_rule": "Smallest absolute shift first, negative before positive",
        "counterfactual": "Roll Gaussian-estimated offsets by exactly one row after inference; same histogram, wrong correspondence; diagnostic only",
        "randomness": first["randomness"], "randomness_scope": first["randomness_pairing"],
        "noise_definition": first["noise_definition"], "budget": 2000, "repetitions": 20,
        "primary_condition": "combined5", "primary_method": "gaussian_template",
        "support_criterion": "On fresh confirmation, both pairs Gaussian SR>=.90, Gaussian minus rolled SR>=.10, clean Gaussian loss versus fixed<=.10",
        "sad_contrast": "Report both SAD variants against Gaussian on common orders; no selection of best method from confirmation, no novelty or superiority claim from finite descriptive differences",
        "no_parameter_selection_after_validation": True, "source_sha256": EXPECTED_SOURCE,
        "script_sha256": sha(Path(__file__)), "input_hashes": {**first["input_hashes"],
            **{str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in provenance_paths}},
        "new_gpu_trainings": 0, "new_real_data_optimizer_updates": 0, "final_attack_payloads_read": False}
    assert code_identity()["source_sha256"] == EXPECTED_SOURCE
    if (OUT / "plan.json").exists():
        assert read(OUT / "plan.json") == plan
        with np.load(OUT / "splits.npz", allow_pickle=False) as bundle:
            assert np.array_equal(bundle["confirmation"], confirmation)
    else:
        write_json(OUT / "plan.json", plan)
        np.savez_compressed(OUT / "splits.npz", training=training, validation=validation,
                            confirmation=confirmation, previous_confirmations=np.concatenate(previous))
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    plan = make_plan()
    if args.prepare_only:
        print("Frozen control protocol:", OUT / "plan.json", flush=True)
        return
    torch.set_num_threads(2)
    started = time.perf_counter()
    with np.load(OUT / "splits.npz", allow_pickle=False) as bundle:
        splits = {name: bundle[name] for name in bundle.files}
    with h5py.File(ROOT / "data/ASCAD.h5", "r") as handle:
        training = handle["Profiling_traces/traces"][splits["training"]].astype(np.float64)
    template = fit_template(training)
    reference_index, reference, distances = representative_reference(training)
    reference_record = {"sorted_training_row_index": reference_index, "profiling_row_index": int(splits["training"][reference_index]),
        "selection_mse": float(distances[reference_index]), "training_trace_sha256": hashlib.sha256(reference.tobytes()).hexdigest(),
        "training_only": True, "keys_masks_labels_used": False, "plan_sha256": sha(OUT / "plan.json")}
    write_json(OUT / "reference.json", reference_record)
    ranges = training.max(axis=0) - training.min(axis=0)
    ranges[ranges == 0] = 1
    median_range = float(np.median(ranges))
    results, alignments, arrays, timings, states, checks = [], [], {"training_mean": template["mean"],
        "training_variance": template["variance"], "training_reference": reference, "reference_distances": distances}, [], {}, 0
    for pool in ("validation", "confirmation"):
        with h5py.File(ROOT / "data/ASCAD.h5", "r") as handle:
            x = handle["Profiling_traces/traces"][splits[pool]].astype(np.float64)
            metadata = handle["Profiling_traces/metadata"][splits[pool]]
        keys = np.unique(metadata["key"][:, 2])
        assert len(keys) == 1
        key = int(keys[0])
        hw = np.array([value.bit_count() for value in range(256)])
        hypotheses = hw[candidate_labels(metadata["plaintext"][:, 2])]
        order_rng, u_rng, z_rng = np.random.default_rng(8001), np.random.default_rng(9101), np.random.default_rng(9102)
        orders = [order_rng.permutation(len(x))[:2000] for _ in range(20)]
        u, z = u_rng.random(len(x)), z_rng.standard_normal(x.shape)
        states[pool] = {"orders_final_state": order_rng.bit_generator.state, "uniform_final_state": u_rng.bit_generator.state,
                        "noise_final_state": z_rng.bit_generator.state, "noise_draw_sha256": hashlib.sha256(z.tobytes()).hexdigest()}
        arrays[pool + "__uniform_draws"] = u
        arrays[pool + "__orders"] = np.stack(orders)
        cache = {}
        for condition in plan["conditions"]:
            name, width = condition["name"], condition["max_shift"]
            actual = np.floor(u * (2 * width + 1)).astype(np.int16) - width
            noise = z * condition["noise_factor"] * median_range
            values, edge = shifted(x, actual) + noise, shifted(x, actual, "edge") + noise
            prefix = pool + "__" + name
            arrays[prefix + "__true_offsets"] = actual
            offsets = {"fixed": np.zeros(len(x), dtype=np.int16), "oracle_known_shift": actual}
            for method in ("ncc_template", "gaussian_template", "sad_training_mean", "sad_training_reference"):
                tick = time.perf_counter()
                if method.startswith("sad_"):
                    target = template["mean"] if method == "sad_training_mean" else reference
                    offsets[method], scores = sad_offsets(values, target)
                    inference_seconds = time.perf_counter() - tick
                    edge_offsets, edge_scores = sad_offsets(edge, target)
                else:
                    offsets[method], scores = estimate_offsets(values, template, method)
                    inference_seconds = time.perf_counter() - tick
                    edge_offsets, edge_scores = estimate_offsets(edge, template, method)
                assert np.array_equal(offsets[method], edge_offsets) and np.array_equal(scores, edge_scores)
                timings.append({"pool": pool, "condition": name, "method": method, "traces": len(x),
                    "inference_seconds": inference_seconds, "microseconds_per_trace": inference_seconds * 1e6 / len(x),
                    "scope": "One original-padding inference call; excludes edge replay, I/O, setup and CPA"})
            offsets["gaussian_offsets_rolled"] = roll_offsets(offsets["gaussian_template"])
            assert np.array_equal(np.sort(offsets["gaussian_offsets_rolled"]), np.sort(offsets["gaussian_template"]))
            for method in plan["methods"]:
                arrays[prefix + "__" + method + "__offsets"] = offsets[method]
                alignments.append({"pool": pool, "condition": name, "method": method,
                    "exact_shift_fraction": float((offsets[method] == actual).mean()),
                    "mean_absolute_error": float(np.abs(offsets[method].astype(int) - actual).mean()),
                    "padding_independent_for_scored_methods": True})
                for family, pair in plan["pairs"].items():
                    product = selected_product(values, template["mean"], pair, offsets[method])
                    assert np.array_equal(product, selected_product(edge, template["mean"], pair, offsets[method]))
                    digest = hashlib.sha256(product.tobytes()).hexdigest()
                    if digest not in cache:
                        cache[digest] = recovery(product, hypotheses, key, orders)
                    summary, curves = cache[digest]
                    for index, order in enumerate(orders):
                        assert independent_endpoint(product, hypotheses, key, order) == curves["ranks"][index, -1]
                        checks += 1
                    arrays[prefix + "__" + method + "__" + family + "__ranks"] = curves["ranks"]
                    results.append({"pool": pool, "condition": name, "method": method, "family": family,
                                    "pair": pair, **summary})
            print("Completed controls:", pool, name, flush=True)
    assert len(results) == 112 and checks == 2240
    for relative, expected in plan["input_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    assert sha(Path(__file__)) == plan["script_sha256"] and code_identity()["source_sha256"] == EXPECTED_SOURCE
    np.savez_compressed(OUT / "arrays.npz", **arrays)
    record = {"plan_sha256": sha(OUT / "plan.json"), "reference_sha256": sha(OUT / "reference.json"),
        "results": results, "alignment": alignments, "inference_timings": timings, "rng_final_states": states,
        "environment": environment(torch.device("cpu")), "training_range_median": median_range,
        "independent_endpoint_checks": checks, "new_gpu_trainings": 0, "new_real_data_optimizer_updates": 0,
        "full_gpu_trainings_total": 3, "final_attack_payloads_read": False,
        "original_inputs_preserved": True, "confirmation_used_for_fit_or_selection": False,
        "seconds": time.perf_counter() - started}
    write_json(OUT / "results.json", record)
    print(json.dumps({"seconds": record["seconds"], "confirmation": [row for row in results if
        row["pool"] == "confirmation" and row["condition"] == "combined5"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
