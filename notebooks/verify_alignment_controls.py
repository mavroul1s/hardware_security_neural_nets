"""Independent replay of alignment-control provenance, estimates, ranks and RNG states."""
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import h5py
import numpy as np
from sca.aes import SBOX
from sca.train import code_identity, write_json
from verify_paper_followups import read, sha, shift_row, independent_estimate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/paper_alignment_controls_2026-10-05"
RUN = ROOT / "runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0"


def main():
    started = time.perf_counter()
    plan, record = read(OUT / "plan.json"), read(OUT / "results.json")
    assert record["plan_sha256"] == sha(OUT / "plan.json")
    assert sha(ROOT / "notebooks/paper_alignment_controls.py") == plan["script_sha256"]
    assert code_identity()["source_sha256"] == plan["source_sha256"]
    for relative, expected in plan["input_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    with np.load(OUT / "splits.npz", allow_pickle=False) as bundle:
        splits = {name: bundle[name] for name in bundle.files}
    with np.load(RUN / "splits.npz", allow_pickle=False) as bundle:
        for name in ("training", "validation"):
            assert np.array_equal(splits[name], bundle[name])
    previous = []
    for name in ("paper_alignment_2026-10-05", "paper_alignment_coordinates_2026-10-05", "paper_maskfree_2026-10-05"):
        with np.load(ROOT / "outputs" / name / "splits.npz", allow_pickle=False) as bundle:
            previous.append(bundle["confirmation"])
    assert np.array_equal(splits["previous_confirmations"], np.concatenate(previous))
    excluded = np.unique(np.concatenate((splits["training"], splits["validation"], *previous)))
    assert len(excluded) == 30000
    remaining = np.setdiff1d(np.arange(50000), excluded)
    expected = np.sort(np.random.default_rng(20261008).choice(remaining, 5000, replace=False))
    assert np.array_equal(expected, splits["confirmation"])
    assert len(np.union1d(excluded, expected)) == 35000
    with h5py.File(ROOT / "data/ASCAD.h5", "r") as handle:
        training = handle["Profiling_traces/traces"][splits["training"]].astype(np.float64)
    mean, variance = training.mean(axis=0), training.var(axis=0)
    variance = np.maximum(variance, max(float(np.median(variance)) * 1e-6, 1e-12))
    ranges = training.max(axis=0) - training.min(axis=0)
    ranges[ranges == 0] = 1
    assert float(np.median(ranges)) == record["training_range_median"] == 13.
    reference_record = read(OUT / "reference.json")
    assert record["reference_sha256"] == sha(OUT / "reference.json")
    assert reference_record["plan_sha256"] == sha(OUT / "plan.json")
    distance = training[:, 20:680] - mean[20:680]
    distances = np.einsum("ij,ij->i", distance, distance) / 660
    reference_index = int(np.argmin(distances))
    assert reference_index == reference_record["sorted_training_row_index"]
    assert int(splits["training"][reference_index]) == reference_record["profiling_row_index"]
    reference = training[reference_index]
    assert sha_bytes(reference) == reference_record["training_trace_sha256"]
    assert reference_record["training_only"] and not reference_record["keys_masks_labels_used"]
    selection = read(ROOT / "outputs/paper_maskfree_2026-10-05/selection.json")
    assert plan["pairs"] == selection["pairs"]
    lookup = {(row["pool"], row["condition"], row["method"], row["family"]): row for row in record["results"]}
    alignments = {(row["pool"], row["condition"], row["method"]): row for row in record["alignment"]}
    summaries, estimate_checks, endpoint_replays, contrasts = 0, 0, 0, []
    candidates = sorted(range(-10, 11), key=lambda d: (abs(d), d))
    with np.load(OUT / "arrays.npz", allow_pickle=False) as arrays:
        assert np.array_equal(arrays["training_mean"], mean) and np.array_equal(arrays["training_variance"], variance)
        assert np.array_equal(arrays["training_reference"], reference)
        np.testing.assert_allclose(arrays["reference_distances"], distances, atol=1e-12, rtol=1e-12)
        for pool in ("validation", "confirmation"):
            with h5py.File(ROOT / "data/ASCAD.h5", "r") as handle:
                x = handle["Profiling_traces/traces"][splits[pool]].astype(np.float64)
                metadata = handle["Profiling_traces/metadata"][splits[pool]]
            true_keys = np.unique(metadata["key"][:, 2])
            assert len(true_keys) == 1
            true_key = int(true_keys[0])
            plaintext = metadata["plaintext"][:, 2]
            hypotheses = np.array([value.bit_count() for value in range(256)])[np.asarray(SBOX)[np.bitwise_xor(plaintext[:, None], np.arange(256, dtype=np.uint8))]]
            ur, zr, order_rng = np.random.default_rng(9101), np.random.default_rng(9102), np.random.default_rng(8001)
            u, z = ur.random(5000), zr.standard_normal((5000, 700))
            orders = np.stack([order_rng.permutation(5000)[:2000] for _ in range(20)])
            assert np.array_equal(arrays[pool + "__uniform_draws"], u)
            assert np.array_equal(arrays[pool + "__orders"], orders)
            states = {"orders_final_state": order_rng.bit_generator.state, "uniform_final_state": ur.bit_generator.state,
                      "noise_final_state": zr.bit_generator.state, "noise_draw_sha256": sha_bytes(z)}
            assert states == record["rng_final_states"][pool]
            for condition in plan["conditions"]:
                name, width = condition["name"], condition["max_shift"]
                true_offsets = np.floor(u * (2 * width + 1)).astype(np.int16) - width
                prefix = pool + "__" + name
                assert np.array_equal(true_offsets, arrays[prefix + "__true_offsets"])
                noise = z * condition["noise_factor"] * 13.
                values = np.stack([shift_row(row, int(d)) for row, d in zip(x, true_offsets)]) + noise
                gaussian = arrays[prefix + "__gaussian_template__offsets"]
                rolled = arrays[prefix + "__gaussian_offsets_rolled__offsets"]
                assert np.array_equal(rolled, np.concatenate((gaussian[-1:], gaussian[:-1])))
                assert np.array_equal(np.sort(rolled), np.sort(gaussian))
                for method in plan["methods"]:
                    offsets = arrays[prefix + "__" + method + "__offsets"]
                    assert offsets.shape == (5000,) and np.all(np.abs(offsets) <= 10)
                    if method == "fixed":
                        assert not offsets.any()
                    elif method == "oracle_known_shift":
                        assert np.array_equal(offsets, true_offsets)
                    elif method != "gaussian_offsets_rolled":
                        for index, row in enumerate(values[:8]):
                            if method.startswith("sad_"):
                                target = mean if method == "sad_training_mean" else reference
                                scores = [sum(abs(float(row[column + d]) - float(target[column])) for column in range(20, 680)) for d in candidates]
                                predicted = candidates[int(np.argmin(scores))]
                            else:
                                predicted = independent_estimate(row, mean, variance, method)
                            assert predicted == offsets[index]
                            estimate_checks += 1
                    align = alignments[(pool, name, method)]
                    assert align["exact_shift_fraction"] == float((offsets == true_offsets).mean())
                    assert align["mean_absolute_error"] == float(np.abs(offsets.astype(int) - true_offsets).mean())
                    for family, pair in plan["pairs"].items():
                        ranks = arrays[prefix + "__" + method + "__" + family + "__ranks"]
                        assert ranks.shape == (20, 2000) and np.all((ranks >= 0) & (ranks <= 255))
                        item = lookup[(pool, name, method, family)]
                        ge, sr = ranks.mean(axis=0), (ranks == 0).mean(axis=0)
                        assert item["ge_at_budget"] == float(ge[-1]) and item["sr_at_budget"] == float(sr[-1])
                        reached = np.flatnonzero(np.logical_and.accumulate((sr >= .9)[::-1])[::-1])
                        assert item["traces_to_sustained_sr90"] == (int(reached[0] + 1) if len(reached) else None)
                        assert item["pair"] == pair
                        # Independent full-vector Pearson on the first common order of each row.
                        order = orders[0]
                        product = np.array([(values[index, pair[0] + offsets[index]] - mean[pair[0]]) *
                            (values[index, pair[1] + offsets[index]] - mean[pair[1]]) for index in order])
                        xc = product - product.mean()
                        hc = hypotheses[order].astype(np.float64)
                        hc -= hc.mean(axis=0)
                        numerator = xc @ hc
                        denominator = np.sqrt(np.square(xc).sum() * np.square(hc).sum(axis=0))
                        coefficient = np.divide(numerator, denominator, out=np.zeros(256), where=denominator > 0)
                        absolute = np.abs(coefficient)
                        target = absolute[true_key]
                        expected_rank = int(np.count_nonzero(absolute >= target - 1e-12) - 1)
                        assert expected_rank == ranks[0, -1]
                        endpoint_replays += 1
                        summaries += 1
                if pool == "confirmation":
                    for family in plan["pairs"]:
                        get = lambda method, condition=name: lookup[(pool, condition, method, family)]["sr_at_budget"]
                        contrasts.append({"condition": name, "family": family,
                            "gaussian_sr": get("gaussian_template"), "rolled_sr": get("gaussian_offsets_rolled"),
                            "gaussian_minus_rolled_sr": get("gaussian_template") - get("gaussian_offsets_rolled"),
                            "sad_mean_minus_gaussian_sr": get("sad_training_mean") - get("gaussian_template"),
                            "sad_reference_minus_gaussian_sr": get("sad_training_reference") - get("gaussian_template"),
                            "clean_gaussian_loss_vs_fixed": get("fixed", "clean") - get("gaussian_template", "clean")})
    assert summaries == len(record["results"]) == 112 and estimate_checks == 256 and endpoint_replays == 112
    assert record["independent_endpoint_checks"] == 2240
    primary = [row for row in contrasts if row["condition"] == "combined5"]
    supported = all(row["gaussian_sr"] >= .9 and row["gaussian_minus_rolled_sr"] >= .1 and row["clean_gaussian_loss_vs_fixed"] <= .1 for row in primary)
    suite = ET.parse(OUT / "pytest.xml").getroot().find("testsuite")
    tests = {name: int(suite.attrib[name]) for name in ("tests", "failures", "errors", "skipped")}
    tests.update({"seconds": float(suite.attrib["time"]), "warnings": 14})
    assert tests["tests"] == 61 and tests["failures"] == tests["errors"] == tests["skipped"] == 0
    assert "61 passed, 14 warnings in 14.88s" in (ROOT / "runs/kaggle_control/tests_alignment_controls_2026-10-05.log").read_text(encoding="utf-8-sig")
    assert not read(RUN.parent / "baseline_gate.json")["passed"]
    assert not (RUN.parent / "combined_seed0").exists() and len(list((ROOT / "notebooks").glob("*.ipynb"))) == 1
    assert not record["confirmation_used_for_fit_or_selection"] and not record["final_attack_payloads_read"]
    assert record["new_gpu_trainings"] == record["new_real_data_optimizer_updates"] == 0
    verification = {"result_summaries_verified": summaries, "sampled_shift_estimates_independently_verified": estimate_checks,
        "independent_endpoint_checks_during_execution": 2240, "additional_independent_endpoint_replays": endpoint_replays,
        "disjoint_splits_and_confirmation_seed_replayed": True, "unique_training_validation_four_confirmation_rows": 35000,
        "training_only_reference_and_frozen_points_verified": True, "rng_draws_orders_and_final_states_verified": True,
        "rolled_gaussian_histograms_exactly_preserved": True, "confirmation_contrasts": contrasts,
        "predefined_correspondence_criterion_met": supported, "tests": tests,
        "source_sha256": plan["source_sha256"], "full_gpu_trainings_total": 3, "canonical_notebook_count": 1,
        "new_gpu_trainings": 0, "new_real_data_optimizer_updates": 0, "final_attack_payloads_read": False,
        "cnn_gate_still_failed": True, "confirmation_pool_now_viewed": True,
        "seconds": time.perf_counter() - started,
        "artifact_sha256": {name: sha(OUT / name) for name in ("plan.json", "results.json", "reference.json", "arrays.npz", "splits.npz", "pytest.xml")}}
    write_json(OUT / "verification.json", verification)
    print(json.dumps({key: value for key, value in verification.items() if key not in ("artifact_sha256", "confirmation_contrasts")}, indent=2))


def sha_bytes(value):
    import hashlib
    return hashlib.sha256(value.tobytes()).hexdigest()


if __name__ == "__main__":
    main()
