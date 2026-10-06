"""Verify the frozen CPU experiment, reporting tables and sampled trace-only scores."""
import hashlib
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import h5py
import numpy as np
from sca.train import code_identity, write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/paper_alignment_2026-10-05"
RUN = ROOT / "runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def direct_shift(row, offset):
    result = np.zeros_like(row)
    if offset >= 0:
        result[offset:] = row[:len(row) - offset]
    else:
        result[:offset] = row[-offset:]
    return result


def main():
    started = time.perf_counter()
    plan, record = read(OUT / "plan.json"), read(OUT / "results.json")
    assert record["plan_sha256"] == sha(OUT / "plan.json")
    assert plan["experiment_script_sha256"] == sha(ROOT / "notebooks/paper_alignment.py")
    assert code_identity()["source_sha256"] == plan["source_sha256"]
    for relative, expected in plan["input_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    assert plan["input_hashes"]["data/ASCAD.h5"] == read(RUN / "manifest.json")["dataset_sha256"]
    with np.load(OUT / "splits.npz", allow_pickle=False) as split_archive:
        splits = {name: split_archive[name] for name in split_archive.files}
    assert len(splits["training"]) == 10000 and len(splits["validation"]) == len(splits["confirmation"]) == 5000
    assert len(np.unique(np.concatenate(list(splits.values())))) == 20000
    with np.load(RUN / "splits.npz", allow_pickle=False) as original:
        for name in ("training", "validation"):
            assert np.array_equal(splits[name], original[name])
    remaining = np.setdiff1d(np.arange(50000), np.union1d(splits["training"], splits["validation"]))
    expected_confirm = np.sort(np.random.default_rng(20261005).choice(remaining, 5000, replace=False))
    assert np.array_equal(expected_confirm, splits["confirmation"])
    result_lookup = {(r["pool"], r["condition"], r["pipeline"], r["method"], r["family"]): r for r in record["results"]}
    assert len(result_lookup) == len(record["results"]) == 128
    suite = ET.parse(OUT / "pytest.xml").getroot().find("testsuite")
    assert int(suite.attrib["tests"]) == 52
    assert all(int(suite.attrib[field]) == 0 for field in ("errors", "failures", "skipped"))
    states, estimated_rows_checked, summaries_checked = {}, 0, 0
    with np.load(OUT / "arrays.npz", allow_pickle=False) as arrays:
        mean, variance = arrays["template_mean"], arrays["template_variance"]
        with h5py.File(ROOT / "data/ASCAD.h5", "r") as handle:
            train = handle["Profiling_traces/traces"][splits["training"]].astype(np.float64)
        assert np.array_equal(mean, train.mean(axis=0))
        floor = max(float(np.median(train.var(axis=0))) * 1e-6, 1e-12)
        assert np.array_equal(variance, np.maximum(train.var(axis=0), floor))
        minimum, scale = train.min(axis=0), train.max(axis=0) - train.min(axis=0)
        scale[scale == 0] = 1
        assert float(np.median(scale)) == record["training_range_median"]
        columns = np.arange(20, 680)
        candidates = sorted(range(-10, 11), key=lambda d: (abs(d), d))
        for pool in ("validation", "confirmation"):
            uniform_rng, noise_rng = np.random.default_rng(9101), np.random.default_rng(9102)
            u = uniform_rng.random(5000)
            z = noise_rng.standard_normal((5000, 700))
            assert np.array_equal(u, arrays[pool + "__uniform_draws"])
            states[pool] = {"uniform_final_state": uniform_rng.bit_generator.state,
                "noise_final_state": noise_rng.bit_generator.state,
                "standard_normal_draws_sha256": hashlib.sha256(z.tobytes()).hexdigest(),
                "note": "States reconstructed from frozen seed/shape/version, with saved uniform draws verified"}
            with h5py.File(ROOT / "data/ASCAD.h5", "r") as handle:
                x = handle["Profiling_traces/traces"][splits[pool][:8]].astype(np.float64)
            for condition in plan["conditions"]:
                name, width = condition["name"], condition["max_shift"]
                true_offsets = np.floor(u * (2 * width + 1)).astype(np.int16) - width
                prefix = pool + "__" + name
                assert np.array_equal(true_offsets, arrays[prefix + "__true_offsets"])
                noise = z[:8] * condition["noise_factor"] * float(np.median(scale))
                raw = np.stack([direct_shift(row, int(d)) for row, d in zip(x, true_offsets[:8])]) + noise
                normalized = (x - minimum) / scale
                surrogate = np.stack([direct_shift(row, int(d)) for row, d in zip(normalized, true_offsets[:8])]) * scale + minimum + noise
                for pipeline, values in (("raw_shift", raw), ("feature_shift_surrogate", surrogate)):
                    for method in ("ncc_template", "gaussian_template"):
                        for index, row in enumerate(values):
                            scores = []
                            for candidate in candidates:
                                sample = row[columns + candidate]
                                reference = mean[columns]
                                if method == "gaussian_template":
                                    scores.append(float(np.mean(np.square(sample - reference) / variance[columns] + np.log(variance[columns]))))
                                else:
                                    a, b = sample - sample.mean(), reference - reference.mean()
                                    denominator = np.sqrt(np.dot(a, a) * np.dot(b, b))
                                    scores.append(-float(np.dot(a, b) / denominator) if denominator else 0.)
                            expected = candidates[int(np.argmin(scores))]
                            saved = arrays[prefix + "__" + pipeline + "__" + method + "__estimated_offsets"][index]
                            assert expected == saved
                            estimated_rows_checked += 1
                    for method in plan["methods"]:
                        stem = prefix + "__" + pipeline + "__" + method
                        offsets = arrays[stem + "__estimated_offsets"]
                        assert offsets.shape == (5000,) and np.all(np.abs(offsets) <= 10)
                        for family in plan["pairs"]:
                            ranks = arrays[stem + "__" + family + "__ranks"]
                            assert ranks.shape == (20, 2000) and np.issubdtype(ranks.dtype, np.integer)
                            assert np.all((ranks >= 0) & (ranks <= 255))
                            item = result_lookup[(pool, name, pipeline, method, family)]
                            ge, sr = ranks.mean(axis=0), (ranks == 0).mean(axis=0)
                            assert item["ge_at_budget"] == float(ge[-1]) and item["sr_at_budget"] == float(sr[-1])
                            reached = np.flatnonzero(np.logical_and.accumulate((sr >= .9)[::-1])[::-1])
                            assert item["traces_to_sustained_sr90"] == (int(reached[0] + 1) if len(reached) else None)
                            summaries_checked += 1
        cnn = arrays["confirmation__frozen_cnn_clean_ranks"]
        assert record["frozen_cnn_clean_confirmation"]["ge_at_budget"] == float(cnn[:, -1].mean())
        assert record["frozen_cnn_clean_confirmation"]["sr_at_budget"] == float((cnn[:, -1] == 0).mean())
    assert summaries_checked == 128 and estimated_rows_checked == 256
    assert record["independent_cpa_endpoint_checks"] == 2560
    assert all(c["affine_transport_max_absolute_error"] <= 1e-10 and c["scalar_affine_interior_commutes"] for c in record["controls"])
    assert all(a["zero_edge_estimates_and_scores_identical"] for a in record["alignment"])
    assert plan["no_post_validation_method_or_parameter_selection"]
    assert not record["confirmation_method_selection_performed"]
    assert not read(RUN.parent / "baseline_gate.json")["passed"]
    assert not (RUN.parent / "combined_seed0").exists()
    assert len(list((ROOT / "notebooks").glob("*.ipynb"))) == 1
    assert record["new_gpu_trainings"] == record["new_real_data_optimizer_updates"] == 0
    assert record["final_attack_payloads_read"] is False
    verification = {"result_summaries_verified": summaries_checked, "sampled_trace_only_shift_estimates_independently_verified": estimated_rows_checked,
        "cpa_endpoints_independently_checked_during_execution": 2560,
        "disjoint_confirmation_indices_verified": True, "template_fit_training_only_verified": True,
        "rng_draws_and_reconstructed_states": states, "original_artifacts_preserved": True,
        "source_sha256": plan["source_sha256"], "tests": 52, "failures": 0,
        "pytest_junit_seconds": float(suite.attrib["time"]), "gate_still_failed": True,
        "full_gpu_trainings_total": 3, "canonical_notebook_count": 1, "new_gpu_trainings": 0,
        "new_real_data_optimizer_updates": 0, "final_attack_payloads_read": False,
        "seconds": time.perf_counter() - started,
        "artifact_sha256": {name: sha(OUT / name) for name in ("plan.json", "results.json", "splits.npz", "arrays.npz", "pytest.xml")}}
    write_json(OUT / "verification.json", verification)
    print(json.dumps({k: v for k, v in verification.items() if k not in ("rng_draws_and_reconstructed_states", "artifact_sha256")}, indent=2))


if __name__ == "__main__":
    main()
