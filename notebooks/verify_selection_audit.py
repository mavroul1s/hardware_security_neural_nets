"""Independent profiling-only verification of the frozen permutation/replication audit."""
from datetime import datetime
import json
import time
import xml.etree.ElementTree as ET

import h5py
import numpy as np
from sca.train import code_identity, write_json
from paper_alignment import ROOT, read, sha

OUT = ROOT / "outputs/paper_selection_audit_2026-10-06"


def direct_correlation(a, b):
    return float(np.corrcoef(a, b)[0, 1]) if np.std(a) and np.std(b) else 0.


def replay_maximum(x, target, margin):
    centered = x - np.mean(x, axis=0)
    h = target - target.mean()
    product_mean = np.dot(centered.T, centered) / len(x)
    squares = centered ** 2
    product_variance = np.maximum(np.dot(squares.T, squares) / len(x) - product_mean ** 2, 0)
    covariance = np.dot((centered * h[:, None]).T, centered) / len(x)
    denominator = np.sqrt(product_variance * np.var(target))
    scores = np.abs(np.divide(covariance, denominator, out=np.zeros_like(covariance), where=denominator > 0))
    # Enumerate row-major positions without using the experiment candidate routine.
    candidates = np.array([(a, b) for a in range(margin, x.shape[1] - margin)
                           for b in range(a + 50, x.shape[1] - margin)])
    index = np.argmax(scores[candidates[:, 0], candidates[:, 1]])
    pair = candidates[index]
    return float(scores[tuple(pair)]), pair


def main():
    started = time.perf_counter()
    plan, record, calibration, access = (read(OUT / name) for name in
        ("plan.json", "results.json", "calibration.json", "confirmation_access.json"))
    assert sha(OUT / "plan.json") == record["plan_sha256"] == calibration["plan_sha256"]
    assert sha(OUT / "calibration.json") == record["calibration_sha256"] == access["calibration_sha256"]
    assert sha(OUT / "confirmation_access.json") == record["access_sha256"]
    assert datetime.fromisoformat(plan["frozen_utc"]) < datetime.fromisoformat(calibration["completed_utc"]) < datetime.fromisoformat(access["started_utc"])
    assert not calibration["confirmation_payloads_read"] and access["frozen_pairs_unchanged"]
    assert not access["attack_payloads_or_metadata_read"]
    assert sha(ROOT / "notebooks/paper_selection_audit.py") == plan["script_sha256"]
    assert code_identity()["source_sha256"] == plan["source_sha256"] == record["source_sha256"]
    for relative, expected in plan["input_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    with np.load(OUT / "splits.npz", allow_pickle=False) as f:
        splits = {name: f[name] for name in f.files}
    hw = np.array([value.bit_count() for value in range(256)])
    lookup = {(r["campaign"], r["family"]): r for r in record["results"]}
    coefficient_checks, full_maxima, confirmation_null_checks = 0, 0, 0
    paired_orders = {}
    with np.load(OUT / "arrays.npz", allow_pickle=False) as arrays:
        for campaign, config in plan["campaigns"].items():
            with np.load(ROOT / config["splits"], allow_pickle=False) as f:
                old_training, old_validation = f["training"], f["validation"]
                excluded = np.unique(np.concatenate([f[name] for name in f.files if name != "attack"]))
            for name, expected in (("training", old_training), ("validation", old_validation), ("excluded", excluded)):
                np.testing.assert_array_equal(splits[campaign + "__" + name], expected)
            remaining = np.setdiff1d(np.arange(config["n"]), excluded)
            confirmation = np.sort(np.random.default_rng(20261010).choice(remaining, 5000, replace=False))
            np.testing.assert_array_equal(confirmation, splits[campaign + "__confirmation"])
            assert not np.intersect1d(confirmation, excluded).size
            assert len(np.union1d(excluded, confirmation)) == (40000 if campaign == "fixed" else 20000)
            with h5py.File(ROOT / config["dataset"], "r") as f:
                x = f["Profiling_traces/traces"][old_training].astype(float)
                y = hw[f["Profiling_traces/labels"][old_training]].astype(float)
                xc = f["Profiling_traces/traces"][confirmation].astype(float)
                yc = hw[f["Profiling_traces/labels"][confirmation]].astype(float)
            mean = x.mean(axis=0)
            np.testing.assert_array_equal(mean, arrays[campaign + "__training_mean"])
            selection = read(ROOT / config["selection"])
            assert selection["pairs"] == config["pairs"]
            for family, pair in config["pairs"].items():
                product = (x[:, pair[0]] - mean[pair[0]]) * (x[:, pair[1]] - mean[pair[1]])
                np.testing.assert_allclose(direct_correlation(product, y), config["training_scores"][family], atol=1e-12, rtol=1e-12)
                coefficient_checks += 1
            train_rng = np.random.default_rng(2026)
            orders = np.stack([train_rng.permutation(10000) for _ in range(99)])
            np.testing.assert_array_equal(orders, arrays[campaign + "__train_permutations"])
            if "training" in paired_orders:
                np.testing.assert_array_equal(paired_orders["training"], orders)
            else:
                paired_orders["training"] = orders
            assert train_rng.bit_generator.state == record["calibrations"][campaign]["rng_final_state"]
            maxima, pairs = arrays[campaign + "__null_maxima"], arrays[campaign + "__null_max_pairs"]
            assert maxima.shape == (99,) and pairs.shape == (99, 2)
            for index, order in enumerate(orders):
                pair = pairs[index]
                assert config["margin"] <= pair[0] < pair[1] < config["width"] - config["margin"] and pair[1] - pair[0] >= 50
                product = (x[:, pair[0]] - mean[pair[0]]) * (x[:, pair[1]] - mean[pair[1]])
                np.testing.assert_allclose(abs(direct_correlation(product, y[order])), maxima[index], atol=1e-12, rtol=1e-12)
                coefficient_checks += 1
                for column, pair in enumerate(config["pairs"].values()):
                    product = (x[:, pair[0]] - mean[pair[0]]) * (x[:, pair[1]] - mean[pair[1]])
                    np.testing.assert_allclose(direct_correlation(product, y[order]),
                        arrays[campaign + "__null_frozen_pair_correlations"][index, column], atol=1e-12, rtol=1e-12)
                    coefficient_checks += 1
                if index in (0, 49, 98):
                    maximum, maximizing_pair = replay_maximum(x, y[order], config["margin"])
                    np.testing.assert_allclose(maximum, maxima[index], atol=1e-12, rtol=1e-12)
                    np.testing.assert_array_equal(maximizing_pair, pairs[index])
                    full_maxima += 1
            cal = record["calibrations"][campaign]
            assert cal["null_maximum_median"] == float(np.median(maxima))
            assert cal["null_maximum_range"] == [float(min(maxima)), float(max(maxima))]
            assert cal["observed_maximum"] == abs(config["training_scores"]["pair1"])
            for family, score in config["training_scores"].items():
                expected = (1 + sum(float(value) >= abs(score) - 1e-12 for value in maxima)) / 100
                assert cal["max_null_tail"][family] == expected
            assert {k: v for k, v in cal.items() if k != "confirmation_rng_final_state"} == calibration["campaigns"][campaign]
            confirmation_rng = np.random.default_rng(2026)
            confirm_orders = np.stack([confirmation_rng.permutation(5000) for _ in range(999)])
            np.testing.assert_array_equal(confirm_orders, arrays[campaign + "__confirmation_permutations"])
            assert confirmation_rng.bit_generator.state == cal["confirmation_rng_final_state"]
            if "confirmation" in paired_orders:
                np.testing.assert_array_equal(paired_orders["confirmation"], confirm_orders)
            else:
                paired_orders["confirmation"] = confirm_orders
            for column, (family, pair) in enumerate(config["pairs"].items()):
                product = (xc[:, pair[0]] - mean[pair[0]]) * (xc[:, pair[1]] - mean[pair[1]])
                np.testing.assert_array_equal(product, arrays[campaign + "__confirmation_products"][:, column])
                observed = direct_correlation(product, yc)
                a, b = product - product.mean(), yc - yc.mean()
                null = np.einsum("ij,j->i", b[confirm_orders], a) / np.sqrt(np.sum(a * a) * np.sum(b * b))
                np.testing.assert_allclose(null, arrays[campaign + "__confirmation_null_correlations"][:, column], atol=1e-12, rtol=1e-12)
                confirmation_null_checks += len(null)
                sign = np.sign(config["training_scores"][family])
                p = (1 + sum(float(value) * sign >= observed * sign - 1e-12 for value in null)) / 1000
                row = lookup[(campaign, family)]
                assert row["pair"] == pair and row["training_correlation"] == config["training_scores"][family]
                np.testing.assert_allclose(row["confirmation_correlation"], observed, atol=1e-12, rtol=1e-12)
                np.testing.assert_allclose(row["signed_confirmation_correlation"], observed * sign, atol=1e-12, rtol=1e-12)
                assert row["training_global_max_null_tail"] == cal["max_null_tail"][family]
                assert row["confirmation_one_sided_p"] == p and row["confirmation_bonferroni_p"] == min(4 * p, 1.)
                assert row["signed_signal_replicates"] == bool(observed * sign > 0 and min(4 * p, 1.) <= .05)
    suite = ET.parse(OUT / "pytest.xml").getroot().find("testsuite")
    tests = {k: int(suite.attrib[k]) for k in ("tests", "failures", "errors", "skipped")}
    tests["seconds"] = float(suite.attrib["time"])
    assert tests["tests"] == 70 and tests["failures"] == tests["errors"] == 0
    assert coefficient_checks == 598 and full_maxima == 6 and confirmation_null_checks == 3996
    assert not record["attack_payloads_or_key_metadata_read_in_this_audit"]
    assert record["new_gpu_trainings"] == record["new_optimizer_updates"] == 0
    result = {"source_sha256": record["source_sha256"], "result_rows_verified": 4,
        "training_correlations_independently_replayed": coefficient_checks,
        "sampled_full_search_null_maxima_replayed": full_maxima,
        "confirmation_null_correlations_replayed": confirmation_null_checks,
        "all_splits_and_permutation_rng_replayed": True, "calibration_completed_before_fresh_confirmation": True,
        "new_confirmation_rows_each": 5000, "fixed_used_rows_total": 40000, "variable_used_profiling_rows_total": 20000,
        "original_artifacts_preserved": True, "attack_payloads_or_key_metadata_read_in_this_audit": False,
        "new_gpu_trainings": 0, "new_optimizer_updates": 0, "tests": tests,
        "seconds": time.perf_counter() - started,
        "artifact_sha256": {name: sha(OUT / name) for name in ("plan.json", "splits.npz", "calibration.json",
            "confirmation_access.json", "arrays.npz", "results.json", "pytest.xml")}}
    write_json(OUT / "verification.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "artifact_sha256"}, indent=2))


if __name__ == "__main__":
    main()
