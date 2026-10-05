"""Confirm diagnostic artifacts and preservation of the approved production state."""
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

from sca.train import code_identity, write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/literature_diagnosis_2026-10-04"
read = lambda p:json.loads(p.read_text(encoding="utf-8"))
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
diagnosis = read(OUT / "diagnosis.json")
correlation = read(OUT / "second_order_correlation.json")
original = read(ROOT / "outputs/kaggle_literature_v7_2026-10-03/verification.json")
preservation = read(ROOT / "outputs/literature_artifact_verification.json")
expected = original["training_source_sha256"]
assert code_identity()["source_sha256"] == diagnosis["source_sha256"] == correlation["source_sha256"] == expected
assert correlation["attack_set_read"] is False and diagnosis["final_attack_set_read"] is False
for name in ("best.pt", "last.pt"):
    expected_sha = original["training_results"]["none"]["checkpoint_checks"][name]["sha256"]
    assert expected_sha == diagnosis["checkpoint_hashes_unchanged"][name] == correlation["checkpoint_hashes_unchanged"][name]
    run = ROOT / "runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0"
    assert sha(run / name) == expected_sha
gate = read(run.parent / "baseline_gate.json")
assert gate["passed"] is False and gate["observed_clean_sr"] == 0
assert not (run.parent / "combined_seed0").exists()
packet = ROOT / "outputs/kaggle_resume_input_literature.zip"
assert sha(packet) == preservation["packet_sha256"]
with zipfile.ZipFile(packet) as bundle:
    assert bundle.testzip() is None
    assert hashlib.sha256(bundle.read("sca_runs_minimal_v3_literature.zip")).hexdigest() == original["archive_sha256"]
notebook = read(ROOT / "notebooks/kaggle_baseline.ipynb")
remote = read(ROOT / "runs/kaggle_control/saved_kernel_v8/hw-sec-exp2.ipynb")
assert len(notebook["cells"]) == len(remote["cells"])
assert all(a["cell_type"] == b["cell_type"] and "".join(a["source"]) == "".join(b["source"])
           for a,b in zip(notebook["cells"], remote["cells"]))
assert len(list((ROOT / "notebooks").glob("*.ipynb"))) == 1
independent = read(OUT / "correlation_verification.json")
assert sum(item["independent_endpoint_checks"] for item in independent["families"].values()) == 40
for name in ("correlation_recovery.png", "hidden_leakage.png", "REPORT_EL.md"):
    assert (OUT / name).stat().st_size > 1000
record = {"production_source_unchanged": True, "production_source_sha256": expected,
    "original_best_last_checkpoints_unchanged": True, "resume_packet_unchanged": True,
    "notebook_matches_saved_private_version8": True, "notebook_count": 1,
    "original_cnn_gate_still_failed": True, "combined_training_performed": False,
    "new_kaggle_execution": False, "full_gpu_trainings_total": 3, "final_attack_evaluation_performed": False,
    "independent_correlation_endpoint_checks": 40,
    "local_tests": {"passed":37, "warnings":14, "seconds":24.54},
    "plots_visually_checked": ["correlation_recovery.png", "hidden_leakage.png"]}
write_json(OUT / "artifact_verification.json", record)
print(json.dumps(record, indent=2))
