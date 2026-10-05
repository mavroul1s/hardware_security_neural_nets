"""Consolidate existing verified artifacts without training or reading trace groups."""
import hashlib
import json
from pathlib import Path
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sca.train import code_identity, write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/study_synthesis_2026-10-05"
EXPECTED = "84eff3cde04c0e9a1756a3d29c44ec82e115a1a08575132686a02520333e2b5c"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    started = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = {}

    def read(relative):
        path = ROOT / relative
        inputs[relative] = sha(path)
        return json.loads(path.read_text(encoding="utf-8"))

    assert code_identity()["source_sha256"] == EXPECTED
    rows, histories, manifests = [], [], []
    descriptors = [("ReLU", "baseline_v3_output", "minimal_v1", "kaggle_baseline_v3_2026-10-03"),
                   ("LeakyReLU", "leaky_v5_output", "minimal_v2_leaky", "kaggle_leaky_v5_2026-10-03"),
                   ("Literature CNN", "literature_v7_output", "minimal_v3_literature", "kaggle_literature_v7_2026-10-03")]
    for name, folder, tag, output in descriptors:
        run = f"runs/kaggle_control/{folder}/runs/{tag}/none_seed0"
        manifest = read(run + "/manifest.json")
        summary = read(run + "/summary.json")
        history = read(run + "/history.json")
        verification = read(f"outputs/{output}/verification.json")
        config = manifest["config"]
        assert config["n_train"] == 10000 and config["n_validation"] == 5000
        assert config["seed"] == 0 and config["target_byte"] == 2 and config["batch_size"] == 128
        assert config["augmentation"]["noise_std"] == config["augmentation"]["max_shift"] == 0
        assert summary["epochs"] == len(history) == 50 and summary["optimization_steps"] == 3950
        assert [r["epoch"] for r in history] == list(range(1, 51))
        assert [r["steps"] for r in history] == [79 * i for i in range(1, 51)]
        assert np.isclose(sum(r["train_seconds"] for r in history), summary["train_seconds"], atol=1e-8, rtol=0)
        best = history[int(np.argmin([r["validation_loss"] for r in history]))]
        assert best["validation_loss"] == summary["best_validation_loss"]
        assert verification["final_attack_evaluation_performed"] is False
        archive = ROOT / f"runs/kaggle_control/{folder}/sca_runs_{tag}.zip"
        assert sha(archive) == verification["archive_sha256"]
        inputs[str(archive.relative_to(ROOT)).replace("\\", "/")] = verification["archive_sha256"]
        expected_source = verification.get("training_source_sha256", verification.get("code_sha256"))
        assert manifest["code"]["source_sha256"] == expected_source
        if name == "Literature CNN":
            validated = verification["training_results"]["none"]
            evaluations = validated["validation_results"]
            assert validated["best_epoch"] == best["epoch"]
            for checkpoint in ("best.pt", "last.pt"):
                assert sha(ROOT / run / checkpoint) == validated["checkpoint_checks"][checkpoint]["sha256"]
        else:
            evaluations = verification["validation_results"]
            assert verification["best_epoch"] == best["epoch"]
        clean = next(r for r in evaluations if r["condition"] == "clean")
        assert clean["budget"] == 2000 and clean["repetitions"] == 20
        assert clean["sr_at_budget"] == 0 and clean["ge_at_budget"] > 0
        rows.append({"name":name, "run_tag":tag, "parameters":summary["parameters"],
            "normalization":manifest["normalizer"].get("kind", "global_scalar_training_only"),
            "best_epoch":best["epoch"], "minimum_validation_ce":best["validation_loss"],
            "last_logged_training_ce":history[-1]["train_loss"],
            "last_validation_ce":history[-1]["validation_loss"],
            "clean_ge_at_2000":clean["ge_at_budget"], "clean_sr_at_2000":clean["sr_at_budget"],
            "epochs":summary["epochs"], "optimization_steps":summary["optimization_steps"],
            "training_loop_seconds":summary["train_seconds"], "validation_loop_seconds":summary["validation_seconds"],
            "device_name":manifest["environment"]["device_name"], "source_sha256":expected_source,
            "best_checkpoint_bytes":summary["best_checkpoint_bytes"]})
        histories.append(history)
        manifests.append(manifest)
    assert len({m["split_id"] for m in manifests}) == len({m["dataset_sha256"] for m in manifests}) == 1
    preservation = read("outputs/literature_artifact_verification.json")
    assert sha(ROOT / "outputs/kaggle_resume_input_literature.zip") == preservation["packet_sha256"]
    diagnostic = read("outputs/literature_diagnosis_2026-10-04/diagnosis.json")
    correlation = read("outputs/literature_diagnosis_2026-10-04/second_order_correlation.json")
    sensitivity = read("outputs/correlation_robustness_2026-10-05/results.json")
    checked = read("outputs/correlation_robustness_2026-10-05/artifact_verification.json")
    for filename, expected in checked["artifact_sha256"].items():
        assert sha(ROOT / "outputs/correlation_robustness_2026-10-05" / filename) == expected
    assert checked["production_state_preserved"] and checked["independent_endpoint_checks"] == 640
    assert diagnostic["final_attack_set_read"] is False and correlation["attack_set_read"] is False
    assert sensitivity["final_attack_evaluation_performed"] is False
    assert len(list((ROOT / "notebooks").glob("*.ipynb"))) == 1
    gate = read("runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/baseline_gate.json")
    assert not gate["passed"] and gate["observed_clean_sr"] == 0
    assert not (ROOT / "runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/combined_seed0").exists()

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), sharey=True)
    for axis, row, history in zip(axes, rows, histories):
        epochs = [r["epoch"] for r in history]
        axis.plot(epochs, [r["train_loss"] for r in history], label="Logged training CE (online)", color="#2166ac")
        axis.plot(epochs, [r["validation_loss"] for r in history], label="Clean validation CE (eval)", color="#b2182b")
        axis.scatter([row["best_epoch"]], [row["minimum_validation_ce"]], marker="*", s=70, color="#b2182b", zorder=3)
        axis.axhline(np.log(256), linestyle="--", color="gray", linewidth=.8)
        axis.set_title(row["name"] + "\n" + f"{row['parameters']:,} parameters; clean SR 0/20", fontsize=10)
        axis.set_xlabel("Epoch")
        axis.grid(alpha=.2)
    axes[0].set_ylabel("Cross-entropy (256 identity classes)")
    axes[0].legend(fontsize=7, loc="lower left")
    fig.suptitle("Archived baseline histories: 10k training / 5k validation, seed0, 50 epochs", fontsize=12)
    fig.text(.5, .015, "ReLU/LeakyReLU use global scalar scaling; literature CNN uses feature MinMax.\n"
             "Different setups; this is not a controlled architecture/normalization ablation. Dashed: ln(256).", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .09, 1, .94))
    fig.savefig(OUT / "baseline_histories.png", dpi=180)
    plt.close(fig)
    cpu_metrics = {name:{"epoch":entry["epoch"],
        "training_eval_ce":entry["splits"]["training"]["metrics"]["cross_entropy"],
        "validation_eval_ce":entry["splits"]["validation"]["metrics"]["cross_entropy"],
        "bn_recalibration_validation_ce":entry["batchnorm"]["training_moments_counterfactual"]["validation"]["cross_entropy"],
        "validation_sr":entry["validation_key_recovery"]["sr_at_budget"]}
        for name,entry in diagnostic["checkpoints"].items()}
    evidence = {"scope":"Consolidation of existing profiling-validation evidence; no new experiments",
        "date":"2026-10-05", "baseline_runs":rows, "cnn_cpu_diagnosis":cpu_metrics,
        "correlation_results":{family:{k:v for k,v in row.items() if k != "row_shuffled_product_controls"}
                               for family,row in correlation["results"].items()},
        "sensitivity_results":sensitivity["results"], "local_tests":checked["local_tests"],
        "input_sha256":inputs, "production_source_sha256":EXPECTED,
        "dataset_sha256":manifests[0]["dataset_sha256"], "split_id":manifests[0]["split_id"],
        "full_gpu_trainings_total":3, "gpu_optimization_steps_total":sum(r["optimization_steps"] for r in rows),
        "training_loop_seconds_total":sum(r["training_loop_seconds"] for r in rows),
        "validation_loop_seconds_total":sum(r["validation_loop_seconds"] for r in rows),
        "full_notebook_session_seconds_total":None, "session_cost_note":"Total sessions/setup/IO not reconstructed from loop timings",
        "comparison_status":"Combined absent after failed original minimum-CE CNN gate; augmentation effect unmeasured",
        "cnn_gate_passed":False, "remaining_full_gpu_trainings_under_cap":1,
        "notebook_count":1, "new_training_performed":False, "new_kaggle_execution":False,
        "final_attack_set_read":False, "consolidation_seconds":time.perf_counter() - started}
    write_json(OUT / "evidence.json", evidence)
    assert code_identity()["source_sha256"] == EXPECTED
    print(json.dumps({k:evidence[k] for k in ("baseline_runs", "gpu_optimization_steps_total", "training_loop_seconds_total",
        "validation_loop_seconds_total", "full_gpu_trainings_total", "notebook_count", "consolidation_seconds")}, indent=2))


if __name__ == "__main__":
    main()
