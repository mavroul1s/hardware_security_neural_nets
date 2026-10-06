"""Prospective CPU protocol replication on the official ASCAD variable-key campaign."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import h5py
import numpy as np
import torch
from sca.aes import SBOX, candidate_labels
from sca.data import make_splits
from sca.train import code_identity, environment, write_json
from paper_alignment import ROOT, RUN, EXPECTED_SOURCE, read, sha, fit_template, estimate_offsets, shifted, independent_endpoint
from paper_maskfree_selection import pair_correlations, select_pairs
from paper_alignment_controls import sad_offsets, roll_offsets
from audit_correlation_robustness import selected_product, recovery
from download_ascad_variable import EXPECTED, SOURCE

OUT = ROOT / "outputs/paper_variable_campaign_2026-10-05"
DATA = ROOT / "data/ASCAD_variable.h5"
HW = np.array([value.bit_count() for value in range(256)])
METHODS = ["fixed", "ncc_template", "gaussian_template", "sad_training_mean",
           "gaussian_offsets_rolled", "known_injected_shift"]


def utc():
    return datetime.now(timezone.utc).isoformat()


def bytes_sha(values):
    return hashlib.sha256(np.asarray(values).tobytes()).hexdigest()


def constant_evaluation_key(keys):
    """Require an actual constant full AES key; never fabricate it from per-trace keys."""
    keys = np.asarray(keys)
    if keys.ndim != 2 or keys.shape[1] != 16 or not len(keys):
        raise ValueError("Expected nonempty full AES key metadata")
    unique = np.unique(keys, axis=0)
    if len(unique) != 1:
        raise ValueError("Variable attack keys cannot be accumulated as an unknown constant key")
    return unique[0].copy()


def interior_pairs(correlations, margin=10):
    """Exclude padding-exposed points before fitting, with the frozen separation/diversity."""
    if len(correlations) <= 2 * margin + 100:
        raise ValueError("Insufficient interior points")
    pairs, count = select_pairs(correlations[margin:-margin, margin:-margin], separation=50, diversity=20)
    return {name: [p + margin for p in pair] for name, pair in pairs.items()}, count


def make_plan():
    if (OUT / "results.json").exists():
        raise FileExistsError("Completed campaign is protected; no retuning/re-execution")
    assert sha(DATA) == EXPECTED
    assert code_identity()["source_sha256"] == EXPECTED_SOURCE
    OUT.mkdir(parents=True, exist_ok=True)
    # Shapes and dtypes only: no profiling/attack values read before freezing.
    with h5py.File(DATA, "r") as f:
        schema = {group: {name: {"shape": list(value.shape), "dtype": str(value.dtype)}
                          for name, value in f[group].items()}
                  for group in ("Profiling_traces", "Attack_traces")}
    assert schema["Profiling_traces"]["traces"]["shape"] == [200000, 1400]
    assert schema["Attack_traces"]["traces"]["shape"] == [100000, 1400]
    training, validation = make_splits(200000, 10000, 5000, 2026)
    attack = np.sort(np.random.default_rng(20261009).choice(100000, 5000, replace=False))
    watched = [RUN / name for name in ("best.pt", "last.pt", "splits.npz", "manifest.json")]
    watched += [ROOT / "data/ASCAD.h5", ROOT / "notebooks/kaggle_baseline.ipynb",
                ROOT / "outputs/kaggle_resume_input_literature.zip", ROOT / "outputs/kaggle_project_literature.zip"]
    for name in ("paper_alignment_2026-10-05", "paper_alignment_coordinates_2026-10-05",
                 "paper_maskfree_2026-10-05", "paper_alignment_controls_2026-10-05"):
        watched += [ROOT / "outputs" / name / "results.json", ROOT / "outputs" / name / "plan.json"]
    helpers = ["paper_alignment.py", "paper_maskfree_selection.py", "paper_alignment_controls.py",
               "audit_correlation_robustness.py", "download_ascad_variable.py"]
    watched += [ROOT / "notebooks" / name for name in helpers]
    plan = {"authorization": "User approved paper-oriented experiments and continuation to a new-key campaign on 2026-10-05",
        "scope": "CPU protocol replication with fresh campaign-specific training fit; not zero-shot transfer or cross-device proof",
        "dataset_sha256": EXPECTED, "official_source": SOURCE, "schema": schema,
        "campaign": "ATMega8515 variable-key, original 1400-sample extracted file, naturally unsynchronized per authors; no desync50/100 variant",
        "training_rows": 10000, "validation_rows": 5000, "final_attack_rows": 5000,
        "profiling_split_seed": 2026, "attack_subset_seed": 20261009, "target_byte": 2,
        "selection": "Same training-label HW/centered-product absolute Pearson, separation50/diversity20, two pairs; exclude point margins10 before any fit to avoid padding under the frozen ±10 search",
        "no_training_keys_or_masks_for_fit": True,
        "training_alignment": "None; select points and fit moments on original raw training traces as in phase3",
        "validation_role": "Descriptive feature/HW correlations only; variable keys preclude unknown-constant-key CPA; no tuning",
        "attack_role": "One prospective evaluation matrix after all fits frozen; metadata keys only verify constant key and rank it",
        "methods": METHODS, "search_bound": 10, "score_columns": [20, 1380],
        "tie_rule": "Smallest absolute offset, negative before positive",
        "conditions": read(ROOT / "outputs/paper_alignment_2026-10-05/plan.json")["conditions"],
        "noise": "Uniform raw Gaussian sigma = factor * median(training max-min); zero training ranges replaced by1",
        "known_shift_scope": "Removes only the extra injected global shift; naturally present timing variation remains unknown",
        "randomness": {"uniform_seed": 9101, "normal_seed": 9102, "order_seed": 8001},
        "budget": 2000, "repetitions": 20, "rank_tolerance": 1e-12,
        "primary_condition": "combined5", "primary_method": "gaussian_template",
        "support_criterion": "Both pairs on final attack: Gaussian SR>=.90, Gaussian-fixed SR>=.10, fixed-clean minus Gaussian-clean SR<=.10; report naturally unsynchronized clean results separately",
        "scope_limitations": "One real attack key, 20 overlapping orders, one training split; added shifts/noise synthetic, not extra physical acquisitions",
        "no_attack_based_selection": True, "no_adaptation_after_validation": True,
        "source_sha256": EXPECTED_SOURCE, "script_sha256": sha(Path(__file__)),
        "input_hashes": {p.relative_to(ROOT).as_posix(): sha(p) for p in watched},
        "new_gpu_trainings": 0, "new_optimizer_updates": 0,
        "original_fixed_key_attack_payloads_read": False}
    if (OUT / "plan.json").exists():
        old = read(OUT / "plan.json")
        assert {k: v for k, v in old.items() if k != "frozen_utc"} == plan
        plan = old
    else:
        plan["frozen_utc"] = utc()
        write_json(OUT / "plan.json", plan)
        np.savez_compressed(OUT / "splits.npz", training=training, validation=validation, attack=attack)
    return plan


def estimates_for(values, template, true_offsets):
    estimates = {"fixed": np.zeros(len(values), dtype=np.int16), "known_injected_shift": true_offsets}
    for method in ("ncc_template", "gaussian_template"):
        estimates[method] = estimate_offsets(values, template, method, 10)[0]
    estimates["sad_training_mean"] = sad_offsets(values, template["mean"], 10)[0]
    estimates["gaussian_offsets_rolled"] = roll_offsets(estimates["gaussian_template"])
    return estimates


def feature_correlation(product, target):
    if np.std(product) == 0 or np.std(target) == 0:
        return 0.
    return float(np.corrcoef(product, target)[0, 1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    plan = make_plan()
    if args.prepare_only:
        print("Frozen prospective campaign plan:", OUT / "plan.json", flush=True)
        return
    if (OUT / "fit.json").exists() or (OUT / "evaluation_access.json").exists():
        raise FileExistsError("Existing fit/evaluation is protected; inspect incomplete execution before retrying")
    torch.set_num_threads(2)
    started = time.perf_counter()
    with np.load(OUT / "splits.npz", allow_pickle=False) as f:
        splits = {name: f[name] for name in f.files}
    with h5py.File(DATA, "r") as f:
        training = f["Profiling_traces/traces"][splits["training"]].astype(np.float64)
        labels = f["Profiling_traces/labels"][splits["training"]]
    fit_started = time.perf_counter()
    correlations = pair_correlations(training, HW[labels])
    pairs, count = interior_pairs(correlations)
    template = fit_template(training)
    ranges = np.ptp(training, axis=0)
    ranges[ranges == 0] = 1
    median_range = float(np.median(ranges))
    np.savez_compressed(OUT / "fit.npz", mean=template["mean"], variance=template["variance"],
                        correlations=correlations, ranges=ranges)
    fit = {"pairs": pairs, "candidate_pairs": count,
        "training_coefficients": {name: float(correlations[tuple(pair)]) for name, pair in pairs.items()},
        "training_range_median": median_range, "variance_floor": template["variance_floor"],
        "keys_masks_read_for_fitting": False, "only_training_traces_and_labels": True,
        "plan_sha256": sha(OUT / "plan.json"), "fit_npz_sha256": sha(OUT / "fit.npz"),
        "fit_seconds": time.perf_counter() - fit_started, "frozen_utc": utc()}
    write_json(OUT / "fit.json", fit)  # Before any validation/attack values or key metadata.
    print("Frozen new-campaign fit:", pairs, "coefficients:", fit["training_coefficients"], flush=True)
    arrays, validation_rows, results, alignment, rng_states = {}, [], [], [], {}
    write_json(OUT / "evaluation_access.json", {"started_utc": utc(),
        "plan_sha256": sha(OUT / "plan.json"), "fit_sha256": sha(OUT / "fit.json"),
        "validation_and_new_attack_opened_only_after_fit": True,
        "original_fixed_key_attack_payloads_read": False})
    key_audit = None
    for pool in ("validation", "attack"):
        group = "Profiling_traces" if pool == "validation" else "Attack_traces"
        with h5py.File(DATA, "r") as f:
            x = f[group + "/traces"][splits[pool]].astype(np.float64)
            if pool == "validation":
                target = HW[f[group + "/labels"][splits[pool]]]
            else:
                # Model and alignment inputs never include these evaluation metadata.
                metadata = f[group + "/metadata"][splits[pool]]
                key = constant_evaluation_key(metadata["key"])
                plaintext = metadata["plaintext"][:, 2]
                hypotheses = HW[candidate_labels(plaintext)]
                attack_labels = f[group + "/labels"][splits[pool]]
                assert np.array_equal(attack_labels, SBOX[plaintext ^ key[2]])
                training_metadata = f["Profiling_traces/metadata"][splits["training"]]
                assert np.array_equal(labels, SBOX[training_metadata["plaintext"][:, 2] ^ training_metadata["key"][:, 2]])
        if pool == "attack":
            with np.load(RUN / "splits.npz", allow_pickle=False) as f:
                old_row = int(f["training"][0])
            with h5py.File(ROOT / "data/ASCAD.h5", "r") as f:
                old_key = f["Profiling_traces/metadata"][old_row]["key"]
            key_audit = {"actual_constant_full_attack_key": True,
                "attack_key_hex": bytes(key).hex(), "target_key_byte": int(key[2]),
                "different_full_key_from_original": not np.array_equal(key, old_key),
                "different_target_byte_from_original": int(key[2]) != int(old_key[2]),
                "attack_full_key_present_in_training_rows": bool(np.all(training_metadata["key"] == key, axis=1).any()),
                "training_unique_full_keys": len(np.unique(training_metadata["key"], axis=0)),
                "training_and_attack_labels_verified": True,
                "training_metadata_read_after_frozen_fit_only_for_audit": True,
                "simulated_constant_key_or_plaintext_key_adjustment": False}
            assert key_audit["different_full_key_from_original"]
            assert not key_audit["attack_full_key_present_in_training_rows"]
        ur, zr, order_rng = np.random.default_rng(9101), np.random.default_rng(9102), np.random.default_rng(8001)
        u, z = ur.random(len(x)), zr.standard_normal(x.shape)
        orders = np.stack([order_rng.permutation(len(x))[:2000] for _ in range(20)])
        arrays[pool + "__uniform"] = u
        arrays[pool + "__orders"] = orders
        rng_states[pool] = {"uniform_final_state": ur.bit_generator.state, "normal_final_state": zr.bit_generator.state,
            "order_final_state": order_rng.bit_generator.state, "normal_draw_sha256": bytes_sha(z)}
        cache, checked = {}, 0
        for condition in plan["conditions"]:
            name, width = condition["name"], condition["max_shift"]
            true_offsets = np.floor(u * (2 * width + 1)).astype(np.int16) - width
            values = shifted(x, true_offsets) + z * condition["noise_factor"] * median_range
            estimates = estimates_for(values, template, true_offsets)
            prefix = pool + "__" + name
            arrays[prefix + "__injected_offsets"] = true_offsets
            for method in METHODS:
                offsets = estimates[method]
                arrays[prefix + "__" + method + "__offsets"] = offsets
                alignment.append({"pool": pool, "condition": name, "method": method,
                    "fraction_matching_extra_injected_shift": float((offsets == true_offsets).mean()),
                    "scope": "Natural timing shift has no ground truth; matching extra injection is not total alignment accuracy"})
                for family, pair in pairs.items():
                    product = selected_product(values, template["mean"], pair, offsets)
                    arrays[prefix + "__" + method + "__" + family + "__product"] = product
                    if pool == "validation":
                        validation_rows.append({"condition": name, "method": method, "family": family,
                            "pair": pair, "hw_correlation": feature_correlation(product, target)})
                    else:
                        digest = bytes_sha(product)
                        if digest not in cache:
                            cache[digest] = recovery(product, hypotheses, int(key[2]), orders)
                        summary, curves = cache[digest]
                        for index, order in enumerate(orders):
                            assert independent_endpoint(product, hypotheses, int(key[2]), order) == curves["ranks"][index, -1]
                            checked += 1
                        arrays[prefix + "__" + method + "__" + family + "__ranks"] = curves["ranks"]
                        results.append({"pool": pool, "condition": name, "method": method, "family": family,
                                        "pair": pair, **summary})
            print("Completed frozen campaign:", pool, name, flush=True)
    lookup = {(r["condition"], r["method"], r["family"]): r for r in results}
    primary = []
    for family in pairs:
        get = lambda c, m: lookup[(c, m, family)]["sr_at_budget"]
        sr = get("combined5", "gaussian_template")
        improvement = sr - get("combined5", "fixed")
        loss = get("clean", "fixed") - get("clean", "gaussian_template")
        primary.append({"family": family, "gaussian_sr": sr, "sr_improvement": improvement,
            "clean_sr_loss": loss, "criterion_met": sr >= .9 and improvement >= .1 and loss <= .1})
    assert len(results) == 48 and checked == 960
    for relative, expected in plan["input_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    assert sha(DATA) == EXPECTED and code_identity()["source_sha256"] == EXPECTED_SOURCE
    assert sha(Path(__file__)) == plan["script_sha256"]
    assert sha(OUT / "fit.npz") == fit["fit_npz_sha256"]
    np.savez_compressed(OUT / "arrays.npz", **arrays)
    record = {"plan_sha256": sha(OUT / "plan.json"), "fit_sha256": sha(OUT / "fit.json"),
        "access_sha256": sha(OUT / "evaluation_access.json"), "results": results,
        "validation_correlations": validation_rows, "alignment": alignment, "key_audit": key_audit,
        "rng_final_states": rng_states, "primary": primary,
        "replication_support_criterion_met": all(r["criterion_met"] for r in primary),
        "independent_execution_endpoints": checked, "seconds": time.perf_counter() - started,
        "environment": environment(torch.device("cpu")), "source_sha256": EXPECTED_SOURCE,
        "original_artifacts_preserved": True, "original_fixed_key_attack_payloads_read": False,
        "new_variable_key_attack_subset_viewed": True, "no_tuning_after_evaluation": True,
        "new_gpu_trainings": 0, "full_gpu_trainings_total": 3, "new_optimizer_updates": 0}
    write_json(OUT / "results.json", record)
    print(json.dumps({"seconds": record["seconds"], "primary": primary, "key_audit": key_audit}, indent=2), flush=True)


if __name__ == "__main__":
    main()
