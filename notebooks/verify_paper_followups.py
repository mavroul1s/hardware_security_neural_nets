"""Independently verify prospective coordinate and training-label-only follow-ups."""
import hashlib
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import h5py
import numpy as np
from sca.train import code_identity, write_json

ROOT = Path(__file__).resolve().parents[1]
FIRST = ROOT / "outputs/paper_alignment_2026-10-05"
SECOND = ROOT / "outputs/paper_alignment_coordinates_2026-10-05"
THIRD = ROOT / "outputs/paper_maskfree_2026-10-05"
RUN = ROOT / "runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shift_row(row, offset):
    result = np.zeros_like(row)
    if offset >= 0:
        result[offset:] = row[:len(row) - offset]
    else:
        result[:offset] = row[-offset:]
    return result


def independent_estimate(row, mean, variance, method):
    columns = np.arange(20, 680)
    offsets = sorted(range(-10, 11), key=lambda value: (abs(value), value))
    scores = []
    for offset in offsets:
        observed, reference = row[columns + offset], mean[columns]
        if method == "gaussian_template":
            score = np.mean((observed - reference) ** 2 / variance[columns] + np.log(variance[columns]))
        else:
            a, b = observed - observed.mean(), reference - reference.mean()
            denominator = np.sqrt(np.dot(a, a) * np.dot(b, b))
            score = -np.dot(a, b) / denominator if denominator else 0.
        scores.append(float(score))
    return offsets[int(np.argmin(scores))]


def main():
    started = time.perf_counter()
    first_plan = read(FIRST / "plan.json")
    for relative, expected in first_plan["input_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    assert code_identity()["source_sha256"] == first_plan["source_sha256"]
    assert sha(ROOT / "notebooks/paper_alignment.py") == first_plan["experiment_script_sha256"]
    with np.load(FIRST / "splits.npz", allow_pickle=False) as bundle:
        initial = {name: bundle[name] for name in bundle.files}
    with np.load(RUN / "splits.npz", allow_pickle=False) as bundle:
        for name in ("training", "validation"):
            assert np.array_equal(initial[name], bundle[name])
    seen = np.unique(np.concatenate(list(initial.values())))
    assert len(seen) == 20000
    with h5py.File(ROOT / "data/ASCAD.h5", "r") as handle:
        training = handle["Profiling_traces/traces"][initial["training"]].astype(np.float64)
        labels = handle["Profiling_traces/labels"][initial["training"]]
    minimum = training.min(axis=0)
    scale = training.max(axis=0) - minimum
    scale[scale == 0] = 1
    assert np.median(scale) == 13.
    suite = ET.parse(THIRD / "pytest.xml").getroot().find("testsuite")
    assert int(suite.attrib["tests"]) == 57
    assert all(int(suite.attrib[field]) == 0 for field in ("errors", "failures", "skipped"))
    totals = {"summaries": 0, "shift_estimates": 0, "execution_endpoints": 0}
    for directory, seed, expected_rows, expected_checks in ((SECOND, 20261006, 96, 1920), (THIRD, 20261007, 64, 1280)):
        plan, record = read(directory / "plan.json"), read(directory / "results.json")
        assert record["plan_sha256"] == sha(directory / "plan.json")
        script = "paper_alignment_coordinates.py" if directory == SECOND else "paper_maskfree_selection.py"
        assert plan["script_sha256"] == sha(ROOT / "notebooks" / script)
        assert plan["source_sha256"] == first_plan["source_sha256"]
        for relative, expected in plan.get("previous_results_sha256", {}).items():
            assert sha(ROOT / relative) == expected
        if directory == SECOND:
            assert plan["phase_one_results_sha256"] == sha(FIRST / "results.json")
        with np.load(directory / "splits.npz", allow_pickle=False) as bundle:
            splits = {name: bundle[name] for name in bundle.files}
        for name in ("training", "validation"):
            assert np.array_equal(splits[name], initial[name])
        remaining = np.setdiff1d(np.arange(50000), seen)
        expected = np.sort(np.random.default_rng(seed).choice(remaining, 5000, replace=False))
        assert np.array_equal(expected, splits["confirmation"])
        seen = np.union1d(seen, splits["confirmation"])
        selection_checks = None
        if directory == THIRD:
            selection = read(THIRD / "selection.json")
            assert record["selection_sha256"] == sha(THIRD / "selection.json")
            assert selection["plan_sha256"] == sha(THIRD / "plan.json")
            assert selection["training_only"] and not selection["mask_metadata_read_for_selection"] and not selection["keys_read_for_selection"]
            assert not record["mask_metadata_used_for_selection"] and not record["confirmation_used_for_selection"]
            with np.load(THIRD / "training_pair_scores.npz", allow_pickle=False) as bundle:
                scores = bundle["correlations"]
            assert scores.shape == (700, 700) and np.isfinite(scores).all()
            a, b = np.triu_indices(700, k=50)
            assert len(a) == selection["candidate_pairs"] == record["candidate_pairs"] == 211575
            first_index = int(np.argmax(np.abs(scores[a, b])))
            first = np.array((a[first_index], b[first_index]))
            allowed = (np.minimum(np.abs(a - first[0]), np.abs(a - first[1])) >= 20) & (np.minimum(np.abs(b - first[0]), np.abs(b - first[1])) >= 20)
            valid_indices = np.flatnonzero(allowed)
            second_index = valid_indices[int(np.argmax(np.abs(scores[a[allowed], b[allowed]])))]
            pairs = {"pair1": first.tolist(), "pair2": [int(a[second_index]), int(b[second_index])]}
            assert pairs == record["pairs"] == selection["pairs"]
            hw_labels = np.array([value.bit_count() for value in range(256)])[labels]
            centered = training - training.mean(axis=0)
            sampled = list(pairs.values()) + [[int(a[index]), int(b[index])] for index in np.linspace(0, len(a) - 1, 11, dtype=int)]
            for i, j in sampled:
                coefficient = float(np.corrcoef(centered[:, i] * centered[:, j], hw_labels)[0, 1])
                assert abs(coefficient - scores[i, j]) <= 1e-12
            for family, pair in pairs.items():
                assert selection["training_correlations"][family] == float(scores[tuple(pair)])
            selection_checks = {"candidate_pairs": len(a), "independent_real_training_pearson_checks": len(sampled),
                                "pairs": pairs, "mask_and_key_metadata_used_for_selection": False}
        else:
            pairs = plan["pairs"]
        lookup = {(row["pool"], row["condition"], row.get("pipeline", "raw_shift"), row["method"], row["family"]): row for row in record["results"]}
        assert len(lookup) == expected_rows
        summaries, estimated_checks, states = 0, 0, {}
        with np.load(directory / "arrays.npz", allow_pickle=False) as arrays:
            for pool in ("validation", "confirmation"):
                ur, zr = np.random.default_rng(9101), np.random.default_rng(9102)
                u, z = ur.random(5000), zr.standard_normal((5000, 700))
                states[pool] = {"uniform_final_state": ur.bit_generator.state, "noise_final_state": zr.bit_generator.state,
                                "standard_normal_sha256": hashlib.sha256(z.tobytes()).hexdigest(),
                                "note": "Reconstructed from frozen seed, shape and NumPy version; offsets verified"}
                with h5py.File(ROOT / "data/ASCAD.h5", "r") as handle:
                    x = handle["Profiling_traces/traces"][splits[pool][:8]].astype(np.float64)
                for condition in plan["conditions"]:
                    name, width = condition["name"], condition["max_shift"]
                    offsets = np.floor(u * (2 * width + 1)).astype(np.int16) - width
                    prefix = pool + "__" + name
                    assert np.array_equal(offsets, arrays[prefix + "__true_offsets"])
                    noise = z[:8] * condition["noise_factor"] * 13.
                    domains = plan[pool + "_pipelines"] if directory == SECOND else ["raw_shift"]
                    for pipeline in domains:
                        if pipeline == "raw_shift":
                            train_domain = training
                            values = np.stack([shift_row(row, int(d)) for row, d in zip(x, offsets[:8])]) + noise
                        else:
                            train_domain = (training - minimum) / scale
                            normalized = (x - minimum) / scale
                            represented = np.stack([shift_row(row, int(d)) for row, d in zip(normalized, offsets[:8])]) * scale + minimum + noise
                            values = (represented - minimum) / scale
                        mean, variance = train_domain.mean(axis=0), train_domain.var(axis=0)
                        variance = np.maximum(variance, max(float(np.median(variance)) * 1e-6, 1e-12))
                        for method in plan["methods"]:
                            stem = prefix + ("__" + pipeline if directory == SECOND else "") + "__" + method
                            saved = arrays[stem + "__estimated_offsets"]
                            assert saved.shape == (5000,) and np.all(np.abs(saved) <= 10)
                            if method == "fixed":
                                assert not saved.any()
                            elif method == "oracle_known_shift":
                                assert np.array_equal(saved, offsets)
                            else:
                                for index, row in enumerate(values):
                                    assert independent_estimate(row, mean, variance, method) == saved[index]
                                    estimated_checks += 1
                            for family in pairs:
                                ranks = arrays[stem + "__" + family + "__ranks"]
                                assert ranks.shape == (20, 2000) and np.issubdtype(ranks.dtype, np.integer)
                                assert np.all((ranks >= 0) & (ranks <= 255))
                                item = lookup[(pool, name, pipeline, method, family)]
                                ge, sr = ranks.mean(axis=0), (ranks == 0).mean(axis=0)
                                assert item["ge_at_budget"] == float(ge[-1]) and item["sr_at_budget"] == float(sr[-1])
                                reached = np.flatnonzero(np.logical_and.accumulate((sr >= .9)[::-1])[::-1])
                                assert item["traces_to_sustained_sr90"] == (int(reached[0] + 1) if len(reached) else None)
                                summaries += 1
        assert summaries == expected_rows and record["independent_endpoint_checks"] == expected_checks
        assert all(row["padding_independent"] for row in record["alignment"])
        assert not record["final_attack_payloads_read"] and record["new_gpu_trainings"] == record["new_real_data_optimizer_updates"] == 0
        verification = {"result_summaries_verified": summaries, "sampled_trace_only_estimates_independently_verified": estimated_checks,
            "cpa_endpoints_independently_checked_during_execution": expected_checks,
            "disjoint_confirmation_and_seed_selection_verified": True, "selection_checks": selection_checks,
            "rng_reconstructed_states": states, "original_inputs_preserved": True,
            "tests": 57, "failures": 0, "pytest_junit_seconds": float(suite.attrib["time"]),
            "source_sha256": first_plan["source_sha256"], "full_gpu_trainings_total": 3,
            "new_gpu_trainings": 0, "new_real_data_optimizer_updates": 0, "final_attack_payloads_read": False,
            "artifact_sha256": {name: sha(directory / name) for name in ("plan.json", "results.json", "splits.npz", "arrays.npz")}}
        if directory == THIRD:
            verification["artifact_sha256"].update({name: sha(directory / name) for name in ("selection.json", "training_pair_scores.npz", "pytest.xml")})
        write_json(directory / "verification.json", verification)
        for field, value in (("summaries", summaries), ("shift_estimates", estimated_checks), ("execution_endpoints", expected_checks)):
            totals[field] += value
    assert len(seen) == 30000
    assert not read(RUN.parent / "baseline_gate.json")["passed"]
    assert not (RUN.parent / "combined_seed0").exists()
    assert len(list((ROOT / "notebooks").glob("*.ipynb"))) == 1
    print(json.dumps({**totals, "training_validation_three_confirmations_unique_rows": len(seen),
                      "source_and_original_artifacts_preserved": True, "seconds": time.perf_counter() - started}, indent=2))


if __name__ == "__main__":
    main()
