"""Replay saved CPU validation metrics using an isolated source snapshot and venv."""
import argparse
from contextlib import redirect_stdout
import hashlib
from importlib.metadata import distributions, version
import json
from pathlib import Path
import re
import site
import sys
import time

import h5py
import matplotlib
import numpy as np
import torch
import sca
from sca.aes import candidate_labels, identity_labels
from sca.data import fit_normalizer, normalize, split_identifier
from sca.metrics import evaluate_key_recovery
from sca.models import build_model
from sca.train import code_identity, environment, write_json

# -I removes the script directory; only explicitly add the isolated companions.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_correlation_robustness as robustness
import verify_correlation_robustness as robustness_verifier
from diagnose_second_order_correlation import prefix_correlations, conservative_absolute_ranks

EXPECTED_SOURCE = "84eff3cde04c0e9a1756a3d29c44ec82e115a1a08575132686a02520333e2b5c"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def predict_log_probabilities(model, data):
    chunks = []
    with torch.no_grad():
        for start in range(0, len(data), 128):
            logits = model(torch.from_numpy(data[start:start + 128]))
            chunks.append(torch.log_softmax(logits.double(), dim=1).numpy())
    return np.concatenate(chunks)


def classification(log_probabilities, labels):
    return {"cross_entropy": float(-log_probabilities[np.arange(len(labels)), labels].mean()),
            "accuracy": float((log_probabilities.argmax(axis=1) == labels).mean())}


def verify_isolation(root, output):
    work = root / "runs/cpu_reproduction_2026-10-05"
    snapshot, venv = work / "source", work / "venv"
    assert Path(sys.prefix).resolve() == venv.resolve()
    assert sys.flags.isolated == 1 and site.ENABLE_USER_SITE is False
    assert Path(__file__).resolve().is_relative_to(snapshot.resolve())
    assert Path(sca.__file__).resolve().is_relative_to((snapshot / "src").resolve())
    module_paths = {module.__name__: str(Path(module.__file__).resolve())
                    for module in (torch, np, h5py, matplotlib)}
    assert all(Path(path).is_relative_to(venv.resolve()) for path in module_paths.values())
    assert not any(Path(path).is_relative_to((root / ".venv").resolve()) for path in sys.path)
    targets = read(output / "plan.json")["targets"]
    installed = {canonical(item.metadata["Name"]): item.version for item in distributions()
                 if canonical(item.metadata["Name"]) not in {"pip", "hardware-sca"}}
    assert installed == targets
    assert code_identity()["source_sha256"] == EXPECTED_SOURCE
    write_json(output / "environment.json", {"runtime": environment(torch.device("cpu")),
        "executable": sys.executable, "prefix": sys.prefix, "base_prefix": sys.base_prefix,
        "isolated_flag": sys.flags.isolated, "user_site_enabled": site.ENABLE_USER_SITE,
        "sys_path": sys.path, "module_paths": module_paths, "sca_module": sca.__file__,
        "packages": installed, "pip": version("pip"), "project": version("hardware-sca"),
        "source_sha256": EXPECTED_SOURCE,
        "scope": "Fresh packages and isolated source; same Windows host and base interpreter"})
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if not output.is_relative_to(root / "outputs"):
        raise ValueError("Output must stay in project outputs/")
    if (output / "evaluation_plan.json").exists():
        raise FileExistsError("Replay already started; preserve its evidence")
    torch.set_num_threads(2)
    started = time.perf_counter()
    snapshot = verify_isolation(root, output)
    run = root / "runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0"
    previous = root / "outputs/literature_diagnosis_2026-10-04"
    sensitivity = root / "outputs/correlation_robustness_2026-10-05"
    selection_path = root / "outputs/masking_diagnosis_2026-10-03/diagnosis.json"
    watched = [root / "data/ASCAD.h5", run / "best.pt", run / "last.pt", run / "splits.npz",
        run / "manifest.json", root / "outputs/kaggle_resume_input_literature.zip",
        root / "outputs/kaggle_project_literature.zip", root / "notebooks/kaggle_baseline.ipynb",
        root / "runs/kaggle_control/saved_kernel_v8/hw-sec-exp2.ipynb", selection_path,
        previous / "diagnosis.json", previous / "rank_controls.npz",
        previous / "second_order_correlation.json", previous / "second_order_correlation_curves.npz",
        sensitivity / "plan.json", sensitivity / "results.json", sensitivity / "audit_arrays.npz",
        root / "requirements-lock-cpu-reproduction.txt"]
    # Freeze inputs and equality criteria before reading any HDF5 trace payload.
    input_hashes = {path.relative_to(root).as_posix(): sha256(path) for path in watched}
    baseline = read(previous / "diagnosis.json")
    selection = read(selection_path)
    previous_correlation = read(previous / "second_order_correlation.json")
    previous_sensitivity = read(sensitivity / "results.json")
    plan = {"input_hashes": input_hashes, "source_sha256": EXPECTED_SOURCE,
        "checkpoint_ce_absolute_tolerance": read(output / "plan.json")["checkpoint_ce_absolute_tolerance"],
        "cnn_rank_prefixes": "Exact equality to previous CPU best/last curves",
        "correlation_rank_prefixes": "Exact equality to previous raw CPU curves",
        "sensitivity": "All 32 saved result rows, arrays, offsets and transform records must match exactly",
        "new_real_data_optimizer_updates": 0, "new_gpu_trainings": 0,
        "hdf5_group_read_allowlist": ["Profiling_traces"], "final_attack_payloads_read": False}
    write_json(output / "evaluation_plan.json", plan)
    manifest = read(run / "manifest.json")
    assert input_hashes["data/ASCAD.h5"] == manifest["dataset_sha256"] == selection["dataset_sha256"]
    with np.load(run / "splits.npz", allow_pickle=False) as bundle:
        indices = {"training": bundle["training"], "validation": bundle["validation"]}
    assert not np.intersect1d(indices["training"], indices["validation"]).size
    assert split_identifier(indices["training"], indices["validation"]) == manifest["split_id"]
    data = {}
    with h5py.File(root / "data/ASCAD.h5", "r") as handle:
        profiling = handle["Profiling_traces"]
        for split, rows in indices.items():
            metadata = profiling["metadata"][rows]
            labels = profiling["labels"][rows]
            assert np.array_equal(labels, identity_labels(metadata["plaintext"], metadata["key"], 2))
            keys = np.unique(metadata["key"][:, 2])
            assert len(keys) == 1
            data[split] = {"raw": profiling["traces"][rows].astype(np.float32),
                "labels": labels, "plaintext": metadata["plaintext"][:, 2], "key": int(keys[0])}
    stats = fit_normalizer(data["training"]["raw"], "feature_minmax_training_only")
    assert stats == manifest["normalizer"]
    for item in data.values():
        item["normalized"] = normalize(item["raw"], stats)
    checkpoints, arrays = {}, {}
    with np.load(previous / "rank_controls.npz", allow_pickle=False) as saved:
        for name in ("best", "last"):
            checkpoint = torch.load(run / (name + ".pt"), map_location="cpu", weights_only=False)
            assert checkpoint["normalizer"] == stats and checkpoint["code"]["source_sha256"] == EXPECTED_SOURCE
            model = build_model(checkpoint["config"]["model"])
            model.load_state_dict(checkpoint["model"])
            model.eval()
            state_before = {key: value.clone() for key, value in model.state_dict().items()}
            entry = {"epoch": checkpoint["epoch"], "splits": {}}
            for split, item in data.items():
                lp = predict_log_probabilities(model, item["normalized"])
                observed = classification(lp, item["labels"])
                expected = baseline["checkpoints"][name]["splits"][split]["metrics"]
                error = abs(observed["cross_entropy"] - expected["cross_entropy"])
                assert error <= plan["checkpoint_ce_absolute_tolerance"]
                assert observed["accuracy"] == expected["accuracy"]
                entry["splits"][split] = {**observed, "previous_ce_absolute_error": error}
                if split == "validation":
                    summary, curves = evaluate_key_recovery(lp, item["plaintext"], item["key"],
                                                           budget=2000, repetitions=20, seed=8001)
                    assert summary == baseline["checkpoints"][name]["validation_key_recovery"]
                    assert np.array_equal(curves["ranks"], saved[name + "_ranks"])
                    entry["key_recovery"] = summary
                    entry["all_40000_saved_cpu_ranks_equal"] = True
                    arrays[name + "_ranks"] = curves["ranks"]
            assert all(torch.equal(value, model.state_dict()[key]) for key, value in state_before.items())
            checkpoints[name] = entry
            print("Reproduced CNN checkpoint:", name, "GE", entry["key_recovery"]["ge_at_budget"], flush=True)
    raw_mean = data["training"]["raw"].mean(axis=0, dtype=np.float64)
    validation = data["validation"]
    hw = np.array([value.bit_count() for value in range(256)])
    hypotheses = hw[candidate_labels(validation["plaintext"])]
    rng = np.random.default_rng(8001)
    orders = [rng.permutation(len(validation["raw"]))[:2000] for _ in range(20)]
    correlation = {}
    with np.load(previous / "second_order_correlation_curves.npz", allow_pickle=False) as saved:
        for family, specification in selection["selected_products"].items():
            assert specification["training_only_centering_and_selection"]
            pair = specification["selected_pair"]
            raw = validation["raw"].astype(np.float64)
            product = (raw[:, pair[0]] - raw_mean[pair[0]]) * (raw[:, pair[1]] - raw_mean[pair[1]])
            ranks = np.stack([conservative_absolute_ranks(prefix_correlations(product[o], hypotheses[o]),
                              validation["key"]) for o in orders])
            assert np.array_equal(ranks, saved[family + "_ranks"])
            ge, sr = ranks.mean(axis=0), (ranks == 0).mean(axis=0)
            sustained = np.flatnonzero(np.logical_and.accumulate((sr >= .9)[::-1])[::-1])
            summary = {"pair": pair, "ge_at_budget": float(ge[-1]), "sr_at_budget": float(sr[-1]),
                "traces_to_sustained_sr90": int(sustained[0] + 1) if len(sustained) else None,
                "all_40000_saved_cpu_ranks_equal": True}
            assert all(summary[key] == previous_correlation["results"][family][key]
                       for key in ("pair", "ge_at_budget", "sr_at_budget", "traces_to_sustained_sr90"))
            correlation[family] = summary
            arrays[family + "_ranks"] = ranks
            print("Reproduced raw correlation pair:", family, flush=True)
    np.savez_compressed(output / "clean_ranks.npz", **arrays)
    clean_seconds = time.perf_counter() - started
    replay = output / "sensitivity"
    robustness.ROOT, robustness.RUN, robustness.OUT = root, run, replay
    assert sha256(snapshot / "notebooks/audit_correlation_robustness.py") == sha256(root / "notebooks/audit_correlation_robustness.py")
    saved_argv = sys.argv
    try:
        sys.argv = ["audit_correlation_robustness.py"]
        with (output / "sensitivity_replay.log").open("w", encoding="utf-8") as log, redirect_stdout(log):
            robustness.main()
        robustness_verifier.ROOT, robustness_verifier.RUN, robustness_verifier.OUT = root, run, replay
        with (output / "sensitivity_verification.log").open("w", encoding="utf-8") as log, redirect_stdout(log):
            robustness_verifier.main()
    finally:
        sys.argv = saved_argv
    reproduced = read(replay / "results.json")
    assert reproduced["results"] == previous_sensitivity["results"]
    assert reproduced["transforms"] == previous_sensitivity["transforms"]
    assert reproduced["padding_checks"] == previous_sensitivity["padding_checks"]
    with np.load(replay / "audit_arrays.npz", allow_pickle=False) as actual, \
            np.load(sensitivity / "audit_arrays.npz", allow_pickle=False) as saved:
        assert set(actual.files) == set(saved.files)
        assert all(np.array_equal(actual[name], saved[name]) for name in saved.files)
        array_count = len(actual.files)
    assert input_hashes == {path.relative_to(root).as_posix(): sha256(path) for path in watched}
    assert code_identity()["source_sha256"] == EXPECTED_SOURCE
    record = {"scope": plan["hdf5_group_read_allowlist"], "checkpoints": checkpoints,
        "raw_correlation": correlation, "sensitivity": {"all_32_result_rows_exact": True,
            "all_saved_arrays_exact": True, "array_count": array_count,
            "transforms_and_padding_exact": True, "seconds": reproduced["seconds"],
            "independent_verification": read(replay / "verification.json")},
        "clean_replay_seconds": clean_seconds, "total_replay_seconds": time.perf_counter() - started,
        "inputs_preserved": True, "input_hashes": input_hashes,
        "source_sha256": EXPECTED_SOURCE, "new_real_data_optimizer_updates": 0,
        "new_gpu_trainings": 0, "full_gpu_trainings_total": 3, "canonical_kaggle_notebooks": 1,
        "cnn_gate": "Failed original minimum-CE baseline; combined remains skipped",
        "final_attack_payloads_read": False,
        "limitations": "Same Windows host/interpreter. Checkpoint inference and diagnostics replay, not a fresh GPU training or independent device replication"}
    write_json(output / "results.json", record)
    print("Reproduced sensitivity:", len(reproduced["results"]), "rows,", array_count, "arrays; inputs unchanged", flush=True)


if __name__ == "__main__":
    main()
