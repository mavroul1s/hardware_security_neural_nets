"""Independent split, train-fit, RNG, offset and CPA replay for the new campaign."""
from datetime import datetime
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import h5py
import numpy as np
from sca.aes import SBOX
from sca.train import code_identity, write_json
from paper_alignment import ROOT, RUN, read, sha

OUT = ROOT / "outputs/paper_variable_campaign_2026-10-05"
DATA = ROOT / "data/ASCAD_variable.h5"


def estimate(row, mean, variance, method):
    columns = np.arange(20, len(mean) - 20)
    candidates = sorted(range(-10, 11), key=lambda value: (abs(value), value))
    scores = []
    reference = mean[columns]
    for offset in candidates:
        observed = row[columns + offset]
        if method == "sad_training_mean":
            score = sum(abs(float(a) - float(b)) for a, b in zip(observed, reference))
        elif method == "gaussian_template":
            score = sum(((float(a) - float(b)) ** 2 / float(v) + np.log(v))
                        for a, b, v in zip(observed, reference, variance[columns])) / len(columns)
        else:
            a, b = observed - observed.mean(), reference - reference.mean()
            denominator = np.linalg.norm(a) * np.linalg.norm(b)
            score = -np.dot(a, b) / denominator if denominator else 0.
        scores.append(score)
    return candidates[int(np.argmin(scores))]


def shift_rows(x, offsets):
    rows = []
    for row, d in zip(x, offsets):
        shifted = np.zeros(len(row))
        if d > 0:
            shifted[d:] = row[:-d]
        elif d < 0:
            shifted[:d] = row[-d:]
        else:
            shifted[:] = row
        rows.append(shifted)
    return np.stack(rows)


def independent_rank(product, hypotheses, true_key, order):
    a, b = product[order], hypotheses[order].astype(float)
    a, b = a - a.mean(), b - b.mean(axis=0)
    denominator = np.linalg.norm(a) * np.sqrt(np.sum(b * b, axis=0))
    scores = np.abs(np.divide(np.sum(a[:, None] * b, axis=0), denominator,
                             out=np.zeros(256), where=denominator > 0))
    return int(np.count_nonzero(scores >= scores[true_key] - 1e-12) - 1)


def main():
    started = time.perf_counter()
    plan, fit, record = (read(OUT / name) for name in ("plan.json", "fit.json", "results.json"))
    assert sha(DATA) == plan["dataset_sha256"]
    assert code_identity()["source_sha256"] == plan["source_sha256"] == record["source_sha256"]
    assert sha(ROOT / "notebooks/paper_variable_campaign.py") == plan["script_sha256"]
    for relative, expected in plan["input_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    assert sha(OUT / "plan.json") == record["plan_sha256"] == fit["plan_sha256"]
    assert sha(OUT / "fit.json") == record["fit_sha256"]
    assert sha(OUT / "fit.npz") == fit["fit_npz_sha256"]
    assert sha(OUT / "evaluation_access.json") == record["access_sha256"]
    access = read(OUT / "evaluation_access.json")
    assert access["fit_sha256"] == record["fit_sha256"]
    assert datetime.fromisoformat(plan["frozen_utc"]) < datetime.fromisoformat(fit["frozen_utc"]) < datetime.fromisoformat(access["started_utc"])
    amendment = read(OUT / "protocol_correctness_fix.json")
    assert amendment["old_plan_sha256"] == sha(OUT / "plan_before_correctness_fix.json")
    assert amendment["failed_pytest_sha256"] == sha(OUT / "pytest_before_correctness_fix.xml")
    before_tests = ET.parse(OUT / "pytest_before_correctness_fix.xml").getroot().find("testsuite")
    assert int(before_tests.attrib["failures"]) == 1 and amendment["before_any_real_payload_read"]
    old_plan = read(OUT / "plan_before_correctness_fix.json")
    assert {k: v for k, v in plan.items() if k not in ("script_sha256", "frozen_utc")} == {
        k: v for k, v in old_plan.items() if k not in ("script_sha256", "frozen_utc")}
    with np.load(OUT / "splits.npz", allow_pickle=False) as f:
        splits = {name: f[name] for name in f.files}
    permutation = np.random.default_rng(2026).permutation(200000)
    assert np.array_equal(splits["validation"], np.sort(permutation[:5000]))
    assert np.array_equal(splits["training"], np.sort(permutation[5000:15000]))
    assert not np.intersect1d(splits["training"], splits["validation"]).size
    assert np.array_equal(splits["attack"], np.sort(np.random.default_rng(20261009).choice(100000, 5000, replace=False)))
    hw = np.array([value.bit_count() for value in range(256)])
    with h5py.File(DATA, "r") as f:
        training = f["Profiling_traces/traces"][splits["training"]].astype(float)
        labels = f["Profiling_traces/labels"][splits["training"]]
        training_metadata = f["Profiling_traces/metadata"][splits["training"]]
    assert np.array_equal(labels, np.asarray(SBOX)[training_metadata["plaintext"][:, 2] ^ training_metadata["key"][:, 2]])
    mean, variance = training.mean(axis=0), training.var(axis=0)
    floor = max(float(np.median(variance)) * 1e-6, 1e-12)
    variance = np.maximum(variance, floor)
    ranges = np.ptp(training, axis=0)
    ranges[ranges == 0] = 1
    with np.load(OUT / "fit.npz", allow_pickle=False) as f:
        np.testing.assert_array_equal(mean, f["mean"])
        np.testing.assert_array_equal(variance, f["variance"])
        np.testing.assert_array_equal(ranges, f["ranges"])
        correlations = f["correlations"]
    assert fit["training_range_median"] == float(np.median(ranges))
    assert fit["variance_floor"] == floor and fit["only_training_traces_and_labels"] and not fit["keys_masks_read_for_fitting"]
    # Independently enumerate the frozen eligible candidates and tie/diversity rules.
    candidates = np.array([(a, b) for a in range(10, 1390) for b in range(a + 50, 1390)])
    scores = np.abs(correlations[candidates[:, 0], candidates[:, 1]])
    first = candidates[np.argmax(scores)]
    eligible = np.array([all(abs(int(point) - int(previous)) >= 20 for point in pair for previous in first)
                         for pair in candidates])
    second = candidates[np.flatnonzero(eligible)[np.argmax(scores[eligible])]]
    assert fit["pairs"] == {"pair1": first.tolist(), "pair2": second.tolist()}
    assert fit["candidate_pairs"] == len(candidates) == 885115
    checks = list(map(tuple, fit["pairs"].values())) + [(10, 60), (51, 120), (100, 1389), (500, 1000), (800, 1350)]
    for a, b in checks:
        product = (training[:, a] - mean[a]) * (training[:, b] - mean[b])
        np.testing.assert_allclose(correlations[a, b], np.corrcoef(product, hw[labels])[0, 1], atol=1e-12, rtol=1e-12)
    for family, pair in fit["pairs"].items():
        assert fit["training_coefficients"][family] == correlations[tuple(pair)]
    lookup = {(r["condition"], r["method"], r["family"]): r for r in record["results"]}
    val_lookup = {(r["condition"], r["method"], r["family"]): r for r in record["validation_correlations"]}
    align_lookup = {(r["pool"], r["condition"], r["method"]): r for r in record["alignment"]}
    summaries, shift_checks, endpoint_checks, val_checks = 0, 0, 0, 0
    with np.load(OUT / "arrays.npz", allow_pickle=False) as arrays:
        for pool in ("validation", "attack"):
            group = "Profiling_traces" if pool == "validation" else "Attack_traces"
            with h5py.File(DATA, "r") as f:
                x = f[group + "/traces"][splits[pool]].astype(float)
                labels = f[group + "/labels"][splits[pool]]
                metadata = f[group + "/metadata"][splits[pool]]
            assert np.array_equal(labels, np.asarray(SBOX)[metadata["plaintext"][:, 2] ^ metadata["key"][:, 2]])
            if pool == "attack":
                keys = np.unique(metadata["key"], axis=0)
                assert len(keys) == 1
                key = keys[0]
                assert not np.all(training_metadata["key"] == key, axis=1).any()
                assert bytes(key).hex() == record["key_audit"]["attack_key_hex"]
                assert len(np.unique(training_metadata["key"], axis=0)) == record["key_audit"]["training_unique_full_keys"]
                with np.load(RUN / "splits.npz", allow_pickle=False) as f:
                    old_row = int(f["training"][0])
                with h5py.File(ROOT / "data/ASCAD.h5", "r") as f:
                    old_key = f["Profiling_traces/metadata"][old_row]["key"]
                assert not np.array_equal(key, old_key)
                assert record["key_audit"]["different_target_byte_from_original"] == (int(key[2]) != int(old_key[2]))
                hypotheses = hw[np.asarray(SBOX)[metadata["plaintext"][:, 2, None] ^ np.arange(256, dtype=np.uint8)]]
            ur, zr, order_rng = np.random.default_rng(9101), np.random.default_rng(9102), np.random.default_rng(8001)
            u, z = ur.random(5000), zr.standard_normal((5000, 1400))
            orders = np.stack([order_rng.permutation(5000)[:2000] for _ in range(20)])
            np.testing.assert_array_equal(u, arrays[pool + "__uniform"])
            np.testing.assert_array_equal(orders, arrays[pool + "__orders"])
            import hashlib
            states = {"uniform_final_state": ur.bit_generator.state, "normal_final_state": zr.bit_generator.state,
                "order_final_state": order_rng.bit_generator.state, "normal_draw_sha256": hashlib.sha256(z.tobytes()).hexdigest()}
            assert states == record["rng_final_states"][pool]
            for condition in plan["conditions"]:
                name, width = condition["name"], condition["max_shift"]
                injected = np.floor(u * (2 * width + 1)).astype(np.int16) - width
                values = shift_rows(x, injected) + z * condition["noise_factor"] * float(np.median(ranges))
                prefix = pool + "__" + name
                np.testing.assert_array_equal(injected, arrays[prefix + "__injected_offsets"])
                for method in plan["methods"]:
                    offsets = arrays[prefix + "__" + method + "__offsets"]
                    if method == "fixed":
                        assert not offsets.any()
                    elif method == "known_injected_shift":
                        np.testing.assert_array_equal(offsets, injected)
                    elif method == "gaussian_offsets_rolled":
                        gaussian = arrays[prefix + "__gaussian_template__offsets"]
                        np.testing.assert_array_equal(offsets, np.concatenate((gaussian[-1:], gaussian[:-1])))
                    else:
                        for index in range(8):
                            assert estimate(values[index], mean, variance, method) == offsets[index]
                            shift_checks += 1
                    assert np.all(np.abs(offsets) <= 10)
                    assert align_lookup[(pool, name, method)]["fraction_matching_extra_injected_shift"] == float((offsets == injected).mean())
                    for family, pair in fit["pairs"].items():
                        product = np.array([(row[pair[0] + d] - mean[pair[0]]) * (row[pair[1] + d] - mean[pair[1]])
                                            for row, d in zip(values, offsets)])
                        np.testing.assert_array_equal(product, arrays[prefix + "__" + method + "__" + family + "__product"])
                        if pool == "validation":
                            expected = float(np.corrcoef(product, hw[labels])[0, 1])
                            np.testing.assert_allclose(expected, val_lookup[(name, method, family)]["hw_correlation"], atol=1e-14, rtol=0)
                            val_checks += 1
                        else:
                            ranks = arrays[prefix + "__" + method + "__" + family + "__ranks"]
                            assert ranks.shape == (20, 2000) and np.all((ranks >= 0) & (ranks <= 255))
                            sr = (ranks == 0).mean(axis=0)
                            row = lookup[(name, method, family)]
                            assert row["ge_at_budget"] == float(ranks[:, -1].mean()) and row["sr_at_budget"] == float(sr[-1])
                            reached = np.flatnonzero(np.logical_and.accumulate((sr >= .9)[::-1])[::-1])
                            assert row["traces_to_sustained_sr90"] == (int(reached[0] + 1) if len(reached) else None)
                            assert independent_rank(product, hypotheses, int(key[2]), orders[0]) == int(ranks[0, -1])
                            summaries += 1
                            endpoint_checks += 1
    for primary in record["primary"]:
        family = primary["family"]
        get = lambda c, m: lookup[(c, m, family)]["sr_at_budget"]
        sr = get("combined5", "gaussian_template")
        improvement = sr - get("combined5", "fixed")
        loss = get("clean", "fixed") - get("clean", "gaussian_template")
        assert primary == {"family": family, "gaussian_sr": sr, "sr_improvement": improvement,
            "clean_sr_loss": loss, "criterion_met": sr >= .9 and improvement >= .1 and loss <= .1}
    assert record["replication_support_criterion_met"] == all(r["criterion_met"] for r in record["primary"])
    assert summaries == endpoint_checks == val_checks == 48 and shift_checks == 192
    testsuite = ET.parse(OUT / "pytest.xml").getroot().find("testsuite")
    tests = {k: int(testsuite.attrib[k]) for k in ("tests", "failures", "errors", "skipped")}
    tests["seconds"] = float(testsuite.attrib["time"])
    assert tests["tests"] == 65 and tests["failures"] == tests["errors"] == 0
    assert not record["key_audit"]["simulated_constant_key_or_plaintext_key_adjustment"]
    assert record["original_fixed_key_attack_payloads_read"] is False
    assert record["new_gpu_trainings"] == record["new_optimizer_updates"] == 0
    verified = {"source_sha256": plan["source_sha256"], "recovery_rows": summaries,
        "validation_correlations_verified": val_checks, "sampled_offset_estimates_verified": shift_checks,
        "training_pair_coefficients_verified": len(checks), "independent_endpoint_replays": endpoint_checks,
        "independent_execution_endpoints": record["independent_execution_endpoints"],
        "fit_frozen_before_validation_and_attack": True, "split_and_rng_replayed": True,
        "actual_constant_new_attack_key_verified": True, "new_key_absent_from_training_full_keys": True,
        "original_artifacts_preserved": True, "original_fixed_key_attack_payloads_read": False,
        "variable_key_attack_subset_is_viewed_evidence": True, "tests": tests,
        "new_gpu_trainings": 0, "new_optimizer_updates": 0, "seconds": time.perf_counter() - started,
        "artifact_sha256": {name: sha(OUT / name) for name in ("plan.json", "splits.npz", "fit.json", "fit.npz",
            "evaluation_access.json", "arrays.npz", "results.json", "pytest.xml", "protocol_correctness_fix.json")}}
    write_json(OUT / "verification.json", verified)
    print(json.dumps({k: v for k, v in verified.items() if k != "artifact_sha256"}, indent=2))


if __name__ == "__main__":
    main()
