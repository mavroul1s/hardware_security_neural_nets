"""Independently reconstruct corruption products and check saved Pearson endpoints."""
import hashlib
import json
from pathlib import Path
import time
import zipfile

import h5py
import numpy as np
import torch
from sca.aes import candidate_labels
from sca.augment import augment_batch
from sca.data import split_identifier
from sca.train import code_identity, write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/correlation_robustness_2026-10-05"
RUN = ROOT / "runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    started = time.perf_counter()
    torch.set_num_threads(2)
    record = read(OUT / "results.json")
    plan = read(OUT / "plan.json")
    assert plan == record["plan"] and sha(OUT / "plan.json") == record["plan_sha256"]
    assert sha(ROOT / "notebooks/audit_correlation_robustness.py") == record["audit_script_sha256"]
    assert sha(ROOT / "configs/evaluation_final.json") == plan["grid_config_sha256"]
    assert sha(ROOT / "outputs/masking_diagnosis_2026-10-03/diagnosis.json") == plan["point_selection_record_sha256"]
    assert len(record["results"]) == len(plan["conditions"]) * len(plan["pairs"]) * 2 == 32
    manifest = read(RUN / "manifest.json")
    with np.load(RUN / "splits.npz", allow_pickle=False) as bundle:
        training, validation = bundle["training"], bundle["validation"]
    assert not np.intersect1d(training, validation).size
    assert split_identifier(training, validation) == plan["split_id"]
    dataset = ROOT / "data/ASCAD.h5"
    assert sha(dataset) == plan["dataset_sha256"]
    with h5py.File(dataset, "r") as handle:
        group = handle["Profiling_traces"]
        xt = group["traces"][training].astype(np.float64)
        xv = group["traces"][validation].astype(np.float64)
        metadata = group["metadata"][validation]
        plaintext = metadata["plaintext"][:, 2]
        key = int(np.unique(metadata["key"][:, 2]).item())
    minimum = xt.min(axis=0)
    scale = xt.max(axis=0) - minimum
    scale[scale == 0] = 1
    assert np.array_equal(minimum, manifest["normalizer"]["minimum"])
    assert np.array_equal(scale, manifest["normalizer"]["scale"])
    center = ((xt - minimum) / scale).astype(np.float32).mean(axis=0, dtype=np.float64)
    x = ((xv - minimum) / scale).astype(np.float32)
    hw = np.array([v.bit_count() for v in range(256)])
    hypotheses = hw[candidate_labels(plaintext)].astype(np.float64)
    rng = np.random.default_rng(plan["order_seed"])
    orders = [rng.permutation(len(x))[:plan["budget"]] for _ in range(plan["repetitions"])]
    centered_hypotheses = [hypotheses[o] - hypotheses[o].mean(axis=0) for o in orders]
    hypothesis_squares = [(b * b).sum(axis=0) for b in centered_hypotheses]
    verified = []
    transforms = {r["condition"]:r for r in record["transforms"]}
    results = {(r["condition"], r["family"], r["method"]):r for r in record["results"]}
    assert len(results) == 32
    with np.load(OUT / "audit_arrays.npz", allow_pickle=False) as arrays:
        assert np.array_equal(arrays["center"], center)
        assert np.array_equal(arrays["validation_indices"], validation)
        for condition in plan["conditions"]:
            name = condition["name"]
            corrupted = {}
            for padding in ("zero", "edge"):
                generator = torch.Generator().manual_seed(plan["corruption_seed"])
                batches = []
                for start in range(0, len(x), plan["batch_size"]):
                    batch = torch.from_numpy(x[start:start + plan["batch_size"]])
                    batches.append(augment_batch(batch, condition["noise_std"], condition["max_shift"],
                                                  padding, generator).numpy())
                corrupted[padding] = np.concatenate(batches)
                assert hashlib.sha256(corrupted[padding].tobytes()).hexdigest() == transforms[name][padding + "_tensor_sha256"]
            assert int((corrupted["zero"] != corrupted["edge"]).sum()) == transforms[name]["zero_edge_changed_samples"]
            # Independently replay random draws to verify the oracle's injected offsets.
            generator = torch.Generator().manual_seed(plan["corruption_seed"])
            offset_batches = []
            for start in range(0, len(x), plan["batch_size"]):
                shape = x[start:start + plan["batch_size"]].shape
                offsets = (torch.randint(-condition["max_shift"], condition["max_shift"] + 1,
                           (shape[0],), generator=generator) if condition["max_shift"] else torch.zeros(shape[0], dtype=torch.int64))
                offset_batches.append(offsets.numpy())
                if condition["noise_std"]:
                    torch.randn(shape, generator=generator, dtype=torch.float32)
            offsets = np.concatenate(offset_batches)
            assert np.array_equal(offsets, arrays[name + "__offsets"])
            assert float(np.abs(offsets).mean()) == transforms[name]["mean_absolute_shift"]
            assert float(np.abs(offsets).sum() / x.size) == transforms[name]["discarded_waveform_sample_fraction"]
            for family, pair in plan["pairs"].items():
                for method in ("fixed", "oracle_known_shift"):
                    prefix = name + "__" + family + "__" + method
                    columns = np.asarray(pair)[:, None] + (offsets[None, :] if method != "fixed" else 0)
                    assert np.all((columns >= 0) & (columns < x.shape[1]))
                    products = []
                    for padding in ("zero", "edge"):
                        selected = corrupted[padding][np.arange(len(x)), columns].astype(np.float64)
                        products.append((selected[0] - center[pair[0]]) * (selected[1] - center[pair[1]]))
                    product = arrays[prefix + "__product"]
                    assert np.array_equal(products[0], product) and np.array_equal(products[1], product)
                    assert product.shape == (len(validation),) and np.isfinite(product).all()
                    ranks, ge, sr = [arrays[prefix + "__" + field] for field in ("ranks", "ge", "sr")]
                    assert ranks.shape == (plan["repetitions"], plan["budget"])
                    assert np.issubdtype(ranks.dtype, np.integer) and np.all((ranks >= 0) & (ranks <= 255))
                    assert np.array_equal(ge, ranks.mean(axis=0))
                    assert np.array_equal(sr, (ranks == 0).mean(axis=0))
                    for index, order in enumerate(orders):
                        a = product[order] - product[order].mean()
                        b = centered_hypotheses[index]
                        denominator = np.sqrt((a * a).sum() * hypothesis_squares[index])
                        scores = np.abs(np.divide((a[:, None] * b).sum(axis=0), denominator,
                                                  out=np.zeros(256), where=denominator > 0))
                        endpoint_rank = int((scores >= scores[key] - 1e-12).sum() - 1)
                        assert endpoint_rank == ranks[index, -1], prefix
                    result = results[(name, family, method)]
                    assert result["ge_at_budget"] == float(ge[-1]) and result["sr_at_budget"] == float(sr[-1])
                    sustained = np.flatnonzero(np.logical_and.accumulate((sr >= .9)[::-1])[::-1])
                    assert result["traces_to_sustained_sr90"] == (int(sustained[0] + 1) if len(sustained) else None)
                    assert result["recovery_censored"] == (not bool(len(sustained)))
                    verified.append({"condition":name, "family":family, "method":method,
                                     "independent_endpoint_checks":len(orders), "products_and_curves_verified":True})
        previous = ROOT / "outputs/literature_diagnosis_2026-10-04/second_order_correlation_curves.npz"
        with np.load(previous, allow_pickle=False) as prior:
            for family in plan["pairs"]:
                agreement = float((arrays["clean__" + family + "__fixed__ranks"] == prior[family + "_ranks"]).mean())
                assert record["clean_vs_previous_raw_rank_agreement"][family] == agreement
    original = read(ROOT / "outputs/kaggle_literature_v7_2026-10-03/verification.json")
    preservation = read(ROOT / "outputs/literature_artifact_verification.json")
    assert code_identity()["source_sha256"] == plan["source_sha256"] == original["training_source_sha256"]
    for name in ("best.pt", "last.pt"):
        expected = original["training_results"]["none"]["checkpoint_checks"][name]["sha256"]
        assert sha(RUN / name) == record["checkpoint_hashes_unchanged"][name] == expected
    assert sha(ROOT / "outputs/kaggle_resume_input_literature.zip") == preservation["packet_sha256"]
    with zipfile.ZipFile(ROOT / "outputs/kaggle_resume_input_literature.zip") as bundle:
        assert bundle.testzip() is None
    notebook = read(ROOT / "notebooks/kaggle_baseline.ipynb")
    remote = read(ROOT / "runs/kaggle_control/saved_kernel_v8/hw-sec-exp2.ipynb")
    assert len(notebook["cells"]) == len(remote["cells"])
    assert all(a["cell_type"] == b["cell_type"] and "".join(a["source"]) == "".join(b["source"])
               for a,b in zip(notebook["cells"], remote["cells"]))
    assert len(list((ROOT / "notebooks").glob("*.ipynb"))) == 1
    gate = read(RUN.parent / "baseline_gate.json")
    assert gate["passed"] is False and gate["observed_clean_sr"] == 0
    assert not (RUN.parent / "combined_seed0").exists()
    assert plan["new_optimization_steps"] == plan["new_kaggle_runs"] == 0
    assert plan["final_attack_set_read"] is False and record["final_attack_evaluation_performed"] is False
    verification = {"independent_method":"Centered-dot-product Pearson endpoints; direct NumPy extraction; production augment_batch replay",
        "endpoint_checks":sum(v["independent_endpoint_checks"] for v in verified), "verified_results":verified,
        "production_corrupted_tensor_hashes_match":True, "oracle_offsets_replayed":True,
        "zero_and_edge_products_exactly_equal":True, "training_only_normalizer_and_center_verified":True,
        "production_source_unchanged":True, "original_checkpoints_unchanged":True,
        "resume_packet_unchanged":True, "notebook_matches_saved_version8":True, "notebook_count":1,
        "cnn_gate_still_failed":True, "new_kaggle_execution":False, "full_gpu_trainings_total":3,
        "final_attack_set_read":False, "seconds":time.perf_counter() - started,
        "results_sha256":sha(OUT / "results.json"), "arrays_sha256":sha(OUT / "audit_arrays.npz")}
    assert verification["endpoint_checks"] == 640
    write_json(OUT / "verification.json", verification)
    print(json.dumps({k:v for k,v in verification.items() if k != "verified_results"}, indent=2))


if __name__ == "__main__":
    main()
