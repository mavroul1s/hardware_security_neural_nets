"""Check consolidated evidence, report tables, links and preserved production files."""
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from sca.train import code_identity, write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/study_synthesis_2026-10-05"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def number(value):
    return float(value.replace(".", "").replace(",", "."))


def main():
    evidence = read(OUT / "evidence.json")
    report = (OUT / "REPORT_EL.md").read_text(encoding="utf-8")
    for relative, expected in evidence["input_sha256"].items():
        assert sha(ROOT / relative) == expected, relative
    rows = evidence["baseline_runs"]
    assert len(rows) == 3 and evidence["full_gpu_trainings_total"] == 3
    assert sum(r["optimization_steps"] for r in rows) == evidence["gpu_optimization_steps_total"] == 11850
    assert sum(r["training_loop_seconds"] for r in rows) == evidence["training_loop_seconds_total"]
    assert sum(r["validation_loop_seconds"] for r in rows) == evidence["validation_loop_seconds_total"]
    for label, row in zip(("ReLU", "LeakyReLU0,1", "Literature-inspired CNN"), rows):
        line = next(line for line in report.splitlines() if line.startswith("| " + label + " |"))
        cells = [c.strip() for c in line.strip("|").split("|")]
        assert number(cells[1]) == row["parameters"]
        assert number(cells[3]) == row["best_epoch"]
        assert abs(number(cells[4]) - row["minimum_validation_ce"]) < 5e-7
        assert number(cells[5]) == row["clean_ge_at_2000"]
        assert cells[6] == "0/20" and row["clean_sr_at_2000"] == 0
    labels = {"clean":"Clean", "noise_matched":"Noise matched", "shift_matched":"Shift matched",
              "combined_matched":"Combined matched", "combined_mild":"Combined mild",
              "combined_noise_ood":"Combined noise OOD", "combined_shift_ood":"Combined shift OOD",
              "combined_both_ood":"Combined both OOD"}
    lookup = {(r["condition"], r["family"], r["method"]):r for r in evidence["sensitivity_results"]}
    for condition, label in labels.items():
        line = next(line for line in report.splitlines() if line.startswith("|" + label + " ("))
        cells = line.strip("|").split("|")
        expected = [f"{int(round(lookup[(condition, family, method)]['sr_at_budget'] * 20))}/20"
                    for method in ("fixed", "oracle_known_shift") for family in ("rout", "r3")]
        assert cells[1:] == expected
    for relative in ("literature/REVIEW.md", "docs/EXPERIMENT_PROTOCOL.md"):
        contents = (ROOT / relative).read_text(encoding="utf-8")
        assert "4 στρατηγικές ×" not in contents and "διαφορές των τεσσάρων στρατηγικών" not in contents
    link_count = 0
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", report):
        if target.startswith("https://"):
            continue
        if target == "verification.json":
            continue
        assert (OUT / target).resolve().is_file(), target
        link_count += 1
    run = ROOT / "runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0"
    original = read(ROOT / "outputs/kaggle_literature_v7_2026-10-03/verification.json")
    checkpoint_hashes = {}
    for name in ("best.pt", "last.pt"):
        checkpoint_hashes[name] = sha(run / name)
        assert checkpoint_hashes[name] == original["training_results"]["none"]["checkpoint_checks"][name]["sha256"]
    preservation = read(ROOT / "outputs/literature_artifact_verification.json")
    assert sha(ROOT / "outputs/kaggle_resume_input_literature.zip") == preservation["packet_sha256"]
    assert code_identity()["source_sha256"] == evidence["production_source_sha256"] == original["training_source_sha256"]
    notebook = read(ROOT / "notebooks/kaggle_baseline.ipynb")
    saved = read(ROOT / "runs/kaggle_control/saved_kernel_v8/hw-sec-exp2.ipynb")
    assert len(notebook["cells"]) == len(saved["cells"])
    assert all(a["cell_type"] == b["cell_type"] and "".join(a["source"]) == "".join(b["source"])
               for a,b in zip(notebook["cells"], saved["cells"]))
    assert len(list((ROOT / "notebooks").glob("*.ipynb"))) == 1
    assert not read(run.parent / "baseline_gate.json")["passed"]
    assert not (run.parent / "combined_seed0").exists()
    assert evidence["final_attack_set_read"] is False and evidence["new_training_performed"] is False
    assert evidence["new_kaggle_execution"] is False
    record = {"artifact_inputs_verified":len(evidence["input_sha256"]),
        "baseline_report_table_verified":True, "sensitivity_report_table_verified":True,
        "report_local_links_verified":link_count, "cost_totals_verified":True,
        "production_source_unchanged":True, "checkpoint_sha256":checkpoint_hashes,
        "active_packet_unchanged":True, "notebook_matches_saved_private_version8":True, "notebook_count":1,
        "cnn_gate_still_failed":True, "full_gpu_trainings_total":3, "new_training_performed":False,
        "new_kaggle_execution":False, "final_attack_set_read":False,
        "latest_full_test_suite":{**evidence["local_tests"], "rerun_for_document_synthesis":False},
        "plots_visually_checked":["baseline_histories.png"],
        "artifact_sha256":{name:sha(OUT / name) for name in ("evidence.json", "baseline_histories.png", "REPORT_EL.md")},
        "documentation_sha256":{relative:sha(ROOT / relative) for relative in
            ("README.md", "PROJECT_PLAN.md", "PROGRESS.md", "docs/EXPERIMENT_PROTOCOL.md",
             "literature/REVIEW.md", "literature/PRIMARY_AUDIT_2026-10-05.md")}}
    write_json(OUT / "verification.json", record)
    print(json.dumps({k:v for k,v in record.items() if k not in ("artifact_sha256", "documentation_sha256", "checkpoint_sha256")}, indent=2))


if __name__ == "__main__":
    main()
