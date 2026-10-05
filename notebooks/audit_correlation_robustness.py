"""Frozen-pair CPU corruption audit; no training and no final attack reads."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import h5py
import numpy as np
import torch
from sca.aes import candidate_labels
from sca.augment import shift_batch
from sca.data import fit_normalizer, normalize, split_identifier
from sca.train import code_identity, environment, write_json
from diagnose_second_order_correlation import prefix_correlations, conservative_absolute_ranks

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0"
OUT = ROOT / "outputs/correlation_robustness_2026-10-05"
EXPECTED = "84eff3cde04c0e9a1756a3d29c44ec82e115a1a08575132686a02520333e2b5c"


def corrupt_with_offsets(data, condition, seed=9001, batch_size=256):
    """Match augment_batch exactly while recording the injected shifts for an oracle."""
    generator = torch.Generator().manual_seed(seed)
    outputs, offsets = [], []
    for start in range(0, len(data), batch_size):
        x = torch.as_tensor(data[start:start + batch_size])
        if condition["max_shift"]:
            shifts = torch.randint(-condition["max_shift"], condition["max_shift"] + 1,
                                   (len(x),), generator=generator)
            result = shift_batch(x, shifts, condition["padding"])
        else:
            shifts = torch.zeros(len(x), dtype=torch.int64)
            result = x
        if condition["noise_std"]:
            result = result + condition["noise_std"] * torch.randn(result.shape, generator=generator, dtype=x.dtype)
        outputs.append(result.numpy())
        offsets.append(shifts.numpy())
    return np.concatenate(outputs), np.concatenate(offsets)


def selected_product(data, center, pair, offsets=None):
    """Keep original training centers; oracle uses per-trace known injected offsets."""
    values = np.asarray(data)
    shifts = np.zeros(len(values), dtype=np.int64) if offsets is None else np.asarray(offsets)
    if shifts.shape != (len(values),) or not np.issubdtype(shifts.dtype, np.integer):
        raise ValueError("Expected one integer offset per trace")
    columns = [point + shifts for point in pair]
    if any(np.any((column < 0) | (column >= values.shape[1])) for column in columns):
        raise ValueError("Selected points were cropped; oracle cannot restore them")
    rows = np.arange(len(values))
    return (values[rows, columns[0]].astype(np.float64) - center[pair[0]]) * (
            values[rows, columns[1]].astype(np.float64) - center[pair[1]])


def recovery(product, hypotheses, true_key, orders):
    ranks = np.stack([conservative_absolute_ranks(prefix_correlations(product[o], hypotheses[o]), true_key)
                      for o in orders]).astype(np.int16)
    ge, sr = ranks.mean(axis=0), (ranks == 0).mean(axis=0)
    sustained = np.flatnonzero(np.logical_and.accumulate((sr >= .9)[::-1])[::-1])
    summary = {"ge_at_budget": float(ge[-1]), "sr_at_budget": float(sr[-1]),
        "traces_to_sustained_sr90": int(sustained[0] + 1) if len(sustained) else None,
        "recovery_censored": not bool(len(sustained))}
    return summary, {"ranks": ranks, "ge": ge, "sr": sr}


def make_plan():
    selection_path = ROOT / "outputs/masking_diagnosis_2026-10-03/diagnosis.json"
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    grid_path = ROOT / "configs/evaluation_final.json"
    grid = json.loads(grid_path.read_text(encoding="utf-8"))
    assert all(s["training_only_centering_and_selection"] for s in selection["selected_products"].values())
    return {"scope": "Profiling-validation sensitivity diagnosis, not final attack or trained-method comparison",
        "split_id": selection["split_id"], "dataset_sha256": selection["dataset_sha256"],
        "source_sha256": EXPECTED, "point_selection_record_sha256": hashlib.sha256(selection_path.read_bytes()).hexdigest(),
        "grid_config_sha256": hashlib.sha256(grid_path.read_bytes()).hexdigest(),
        "pairs": {f:s["selected_pair"] for f,s in selection["selected_products"].items()},
        "conditions": grid["conditions"], "budget": 2000, "repetitions": 20,
        "order_seed": grid["attack_order_seed"], "corruption_seed": grid["corruption_seed"],
        "batch_size": grid["batch_size"], "normalization": "feature_minmax_training_only",
        "centering": "Mean normalized training trace; frozen for all conditions",
        "primary_extraction": "Fixed training-selected pair",
        "oracle_extraction": "Read original points at point+injected_shift; known synthetic offsets, not an estimated alignment method",
        "padding_control": "Edge padding with identical within-condition RNG; inspect both products for exact equality",
        "paired_scope": "Same corrupted traces for both pairs and methods; common trace orders; interleaved RNG does not guarantee same offsets across different conditions",
        "new_optimization_steps": 0, "new_kaggle_runs": 0, "final_attack_set_read": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    plan = make_plan()
    assert code_identity()["source_sha256"] == EXPECTED
    plan_path = OUT / "plan.json"
    if plan_path.exists():
        assert json.loads(plan_path.read_text(encoding="utf-8")) == plan, "Frozen audit plan differs"
    else:
        write_json(plan_path, plan)
    if args.prepare_only:
        print(json.dumps(plan, indent=2))
        return
    started = time.perf_counter()
    torch.set_num_threads(2)
    before_hashes = {n:hashlib.sha256((RUN / n).read_bytes()).hexdigest() for n in ("best.pt", "last.pt")}
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    with np.load(RUN / "splits.npz", allow_pickle=False) as bundle:
        training, validation = bundle["training"], bundle["validation"]
    assert split_identifier(training, validation) == manifest["split_id"] == plan["split_id"]
    dataset = ROOT / "data/ASCAD.h5"
    assert hashlib.sha256(dataset.read_bytes()).hexdigest() == plan["dataset_sha256"]
    with h5py.File(dataset, "r") as handle:
        group = handle["Profiling_traces"]
        xt = group["traces"][training].astype(np.float32)
        xv = group["traces"][validation].astype(np.float32)
        metadata = group["metadata"][validation]
        plaintext = metadata["plaintext"][:, 2]
        true_keys = np.unique(metadata["key"][:, 2])
        assert len(true_keys) == 1
        true_key = int(true_keys[0])
    stats = fit_normalizer(xt, plan["normalization"])
    assert stats == manifest["normalizer"]
    center = normalize(xt, stats).mean(axis=0, dtype=np.float64)
    x = normalize(xv, stats)
    hw = np.array([i.bit_count() for i in range(256)])
    hypotheses = hw[candidate_labels(plaintext)]
    rng = np.random.default_rng(plan["order_seed"])
    orders = [rng.permutation(len(x))[:plan["budget"]] for _ in range(plan["repetitions"])]
    results, stored, padding_checks, transform_records = [], {"center": center, "validation_indices":validation}, [], []
    for condition in plan["conditions"]:
        name = condition["name"]
        corrupted, offsets = corrupt_with_offsets(x, condition, plan["corruption_seed"], plan["batch_size"])
        edge, edge_offsets = corrupt_with_offsets(x, {**condition, "padding":"edge"},
                                                  plan["corruption_seed"], plan["batch_size"])
        assert np.array_equal(offsets, edge_offsets)
        stored[name + "__offsets"] = offsets.astype(np.int16)
        transform_records.append({"condition":name,
            "zero_tensor_sha256":hashlib.sha256(corrupted.tobytes()).hexdigest(),
            "edge_tensor_sha256":hashlib.sha256(edge.tobytes()).hexdigest(),
            "zero_edge_changed_samples":int((corrupted != edge).sum()),
            "mean_absolute_shift":float(np.abs(offsets).mean()),
            "discarded_waveform_sample_fraction":float(np.abs(offsets).sum() / x.size)})
        for family, pair in plan["pairs"].items():
            fixed = selected_product(corrupted, center, pair)
            oracle = selected_product(corrupted, center, pair, offsets)
            fixed_edge = selected_product(edge, center, pair)
            oracle_edge = selected_product(edge, center, pair, offsets)
            assert np.array_equal(fixed, fixed_edge) and np.array_equal(oracle, oracle_edge)
            padding_checks.append({"condition":name, "family":family, "pair":pair,
                "fixed_products_equal":True, "oracle_products_equal":True, "selected_points_cropped":0})
            prior_curves = None
            for method, product in (("fixed", fixed), ("oracle_known_shift", oracle)):
                if method == "oracle_known_shift" and np.array_equal(product, fixed):
                    summary, curves = prior_curves
                else:
                    summary, curves = recovery(product, hypotheses, true_key, orders)
                prior_curves = (summary, curves)
                key = name + "__" + family + "__" + method
                stored[key + "__product"] = product
                for field, value in curves.items():
                    stored[key + "__" + field] = value
                results.append({"condition":name, "corruption":condition, "family":family, "pair":pair,
                    "method":method, **summary, "oracle_information_available_to_real_attacker":False if method != "fixed" else None})
        print("Completed frozen-pair corruption:", name, flush=True)
    old_path = ROOT / "outputs/literature_diagnosis_2026-10-04/second_order_correlation_curves.npz"
    with np.load(old_path, allow_pickle=False) as prior:
        clean_agreement = {family:float((stored["clean__" + family + "__fixed__ranks"] == prior[family + "_ranks"]).mean())
                           for family in plan["pairs"]}
    assert before_hashes == {n:hashlib.sha256((RUN / n).read_bytes()).hexdigest() for n in before_hashes}
    assert code_identity()["source_sha256"] == EXPECTED
    np.savez_compressed(OUT / "audit_arrays.npz", **stored)
    record = {"plan":plan, "plan_sha256":hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "audit_script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "environment":environment(torch.device("cpu")), "results":results,
        "padding_checks":padding_checks, "transforms":transform_records,
        "clean_vs_previous_raw_rank_agreement":clean_agreement,
        "checkpoint_hashes_unchanged":before_hashes, "full_gpu_trainings_total":3,
        "final_attack_evaluation_performed":False, "seconds":time.perf_counter() - started}
    write_json(OUT / "results.json", record)
    print(json.dumps({"seconds":record["seconds"], "results":[{k:v for k,v in item.items()
        if k in ("condition", "family", "method", "ge_at_budget", "sr_at_budget", "traces_to_sustained_sr90")}
        for item in results]}, indent=2))


if __name__ == "__main__":
    main()
