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
    reproduction = ROOT / "outputs/cpu_reproduction_2026-10-05"
    reproduction_record = read(reproduction / "verification.json")
    replay = read(reproduction / "results.json")
    assert reproduction_record["tests"]["tests"] == 44
    assert reproduction_record["tests"]["failures"] == reproduction_record["tests"]["errors"] == 0
    assert reproduction_record["sensitivity_arrays_bitwise_equal"] == 138
    assert reproduction_record["independent_endpoint_checks"] == 640
    assert reproduction_record["new_gpu_trainings"] == reproduction_record["new_real_data_optimizer_updates"] == 0
    assert reproduction_record["final_attack_payloads_read"] is False
    assert replay["source_sha256"] == evidence["production_source_sha256"]
    assert read(reproduction / "sensitivity/results.json")["results"] == evidence["sensitivity_results"]
    assert "44 passed/14 warnings σε597,51s" in report and "§11" in report
    paper = ROOT / "outputs/paper_extension_2026-10-05"
    paper_record = read(paper / "verification.json")
    paper_evidence = read(paper / "evidence.json")
    for name, expected in paper_record["artifact_sha256"].items():
        assert sha(paper / name) == expected
    assert paper_record["recovery_rows"] == 288 and paper_record["independent_execution_cpa_endpoints"] == 5760
    assert paper_record["tests"]["tests"] == 57 and paper_record["tests"]["failures"] == paper_record["tests"]["errors"] == 0
    assert paper_record["new_gpu_trainings"] == paper_record["new_real_data_optimizer_updates"] == 0
    assert not paper_record["final_attack_payloads_read"] and paper_record["cnn_gate_still_failed"]
    assert paper_evidence["source_sha256"] == evidence["production_source_sha256"]
    assert "## 12." in report and "57passed/14warnings σε19,43s" in report
    phase_rows = [row for row in paper_evidence["all_results"] if row["pool"] == "confirmation"
                  and row["condition"] == "combined5" and row["method"] == "gaussian_template"
                  and row.get("pipeline", "raw_shift") == "raw_shift"]
    for phase in (1, 2, 3):
        source_rows = [row for row in phase_rows if row["phase"] == phase]
        line = next(line for line in report.splitlines() if line.startswith("| Φάση" + str(phase) + ","))
        expected = ",".join(f"{round(row['sr_at_budget'] * 20)}/20" for row in source_rows)
        assert [cell.strip() for cell in line.strip("|").split("|")][1] == expected
    controls = ROOT / "outputs/paper_alignment_controls_2026-10-05"
    controls_report = read(controls / "report_verification.json")
    controls_verified = read(controls / "verification.json")
    controls_evidence = read(controls / "evidence.json")
    for name, expected in controls_report["artifact_sha256"].items():
        assert sha(controls / name) == expected
    assert controls_report["four_phase_recovery_summaries"] == 400
    assert controls_report["four_phase_independent_execution_cpa_endpoints"] == 8000
    assert controls_report["additional_independent_endpoint_replays"] == 112
    assert controls_report["tests"]["tests"] == 61 and controls_report["tests"]["failures"] == controls_report["tests"]["errors"] == 0
    assert controls_verified["source_sha256"] == evidence["production_source_sha256"]
    assert controls_verified["new_gpu_trainings"] == controls_verified["new_real_data_optimizer_updates"] == 0
    assert controls_verified["final_attack_payloads_read"] is False
    assert controls_report["gaussian_primary_sr_equal_to_sad_mean"]
    assert controls_report["wrong_correspondence_primary_sr_zero"]
    section = report.split("## 13.", 1)[1]
    controls_lookup = {(row["pool"], row["condition"], row["method"], row["family"]):row for row in controls_evidence["results"]}
    for method, label in zip(("fixed", "ncc_template", "gaussian_template", "sad_training_mean", "sad_training_reference", "gaussian_offsets_rolled", "oracle_known_shift"),
                              ("Fixed", "NCC", "Gaussian", "SAD mean", "SAD reference", "Gaussian wrong row", "Known shift")):
        line = next(line for line in section.splitlines() if line.startswith("| " + label + " |"))
        expected = [f"{round(controls_lookup[('confirmation', condition, method, family)]['sr_at_budget'] * 20)}/20"
                    for condition in ("combined5", "combined10_ood") for family in ("pair1", "pair2")]
        assert [cell.strip() for cell in line.strip("|").split("|")][1:] == expected
    variable = ROOT / "outputs/paper_variable_campaign_2026-10-05"
    variable_report = read(variable / "report_verification.json")
    variable_verified = read(variable / "verification.json")
    variable_evidence = read(variable / "evidence.json")
    for name, expected in variable_report["artifact_sha256"].items():
        assert sha(variable / name) == expected, name
    assert variable_verified["source_sha256"] == evidence["production_source_sha256"]
    assert variable_verified["fit_frozen_before_validation_and_attack"]
    assert variable_verified["actual_constant_new_attack_key_verified"]
    assert variable_verified["new_key_absent_from_training_full_keys"]
    assert variable_report["five_phase_recovery_summaries"] == 448
    assert variable_report["five_phase_execution_endpoints"] == 8960
    assert variable_report["additional_endpoint_replays"] == 160
    assert variable_report["tests"]["tests"] == 65 and not variable_report["tests"]["failures"]
    assert variable_report["new_gpu_trainings"] == 0
    assert variable_report["new_variable_key_attack_subset_viewed"]
    assert not variable_report["original_fixed_key_attack_payloads_read"]
    assert not variable_report["support_criterion_met"]
    assert not variable_evidence["paper_ready"] and not variable_evidence["novelty_verified"]
    assert "## 14." in report and "65tests passed/14warnings σε18,03s" in report
    assert "816,97s" in report and round(variable_evidence["five_phase_cpu_seconds"], 2) == 816.97
    section = report.split("## 14.", 1)[1]
    variable_lookup = {(row["condition"], row["method"], row["family"]):row for row in variable_evidence["results"]}
    for method, label in zip(("fixed", "ncc_template", "gaussian_template", "sad_training_mean", "gaussian_offsets_rolled", "known_injected_shift"),
                             ("Fixed", "NCC", "Gaussian", "SAD mean", "Gaussian wrong row", "Known injected shift")):
        line = next(line for line in section.splitlines() if line.startswith("| " + label + " |"))
        expected = [" / ".join(f"{round(variable_lookup[(condition, method, family)]['sr_at_budget'] * 20)}/20"
                               for family in ("pair1", "pair2")) for condition in ("clean", "shift5", "combined5", "combined10_ood")]
        assert [cell.strip() for cell in line.strip("|").split("|")][1:] == expected
    selection_audit = ROOT / "outputs/paper_selection_audit_2026-10-06"
    audit_report = read(selection_audit / "report_verification.json")
    audit_verified = read(selection_audit / "verification.json")
    audit_evidence = read(selection_audit / "evidence.json")
    for name, expected in audit_report["artifact_sha256"].items():
        assert sha(selection_audit / name) == expected, name
    assert audit_verified["source_sha256"] == evidence["production_source_sha256"]
    assert audit_verified["result_rows_verified"] == audit_report["result_rows"] == 4
    assert audit_report["replicated_pairs"] == 3
    assert audit_verified["training_correlations_independently_replayed"] == 598
    assert audit_verified["sampled_full_search_null_maxima_replayed"] == 6
    assert audit_verified["confirmation_null_correlations_replayed"] == 3996
    assert audit_verified["all_splits_and_permutation_rng_replayed"]
    assert audit_verified["calibration_completed_before_fresh_confirmation"]
    assert not audit_report["attack_payloads_or_key_metadata_read_in_this_audit"]
    assert audit_report["new_gpu_trainings"] == 0 and audit_report["no_new_key_recovery_results"]
    assert audit_report["tests"]["tests"] == 70 and not audit_report["tests"]["failures"]
    assert not audit_evidence["novelty_verified"] and not audit_evidence["paper_ready"]
    assert "## 15." in report and "70tests passed/14warnings σε19,43s" in report
    assert "890,388246s" in report and round(audit_evidence["six_phase_cpu_seconds"], 6) == 890.388246
    section = report.split("## 15.", 1)[1]
    for row in audit_evidence["results"]:
        label = row["campaign"] + " / " + row["family"]
        line = next(line for line in section.splitlines() if line.startswith("| " + label + " |"))
        expected = [f"{row['training_correlation']:.6f}", f"{row['confirmation_correlation']:.6f}",
            f"{row['training_global_max_null_tail']:.2f}", f"{row['confirmation_bonferroni_p']:.3f}",
            "Πέρασε" if row["signed_signal_replicates"] else "Δεν πέρασε"]
        assert [cell.strip() for cell in line.strip("|").split("|")][1:] == expected
    record = {"artifact_inputs_verified":len(evidence["input_sha256"]),
        "baseline_report_table_verified":True, "sensitivity_report_table_verified":True,
        "report_local_links_verified":link_count, "cost_totals_verified":True,
        "production_source_unchanged":True, "checkpoint_sha256":checkpoint_hashes,
        "active_packet_unchanged":True, "notebook_matches_saved_private_version8":True, "notebook_count":1,
        "cnn_gate_still_failed":True, "full_gpu_trainings_total":3, "new_training_performed":False,
        "new_kaggle_execution":False, "final_attack_set_read":False,
        "full_test_suite_at_original_synthesis":{**evidence["local_tests"], "rerun_for_document_synthesis":False},
        "latest_full_test_suite":{**audit_report["tests"], "run_for_selection_audit":True},
        "variable_campaign_full_test_suite":{**variable_report["tests"], "run_for_variable_campaign":True},
        "alignment_controls_full_test_suite":{**controls_report["tests"], "run_for_alignment_controls":True},
        "first_three_paper_phases_full_test_suite":{**paper_record["tests"], "run_for_paper_extension":True},
        "clean_cpu_reproduction_full_test_suite":{**reproduction_record["tests"], "run_for_clean_cpu_reproduction":True},
        "paper_extension_addendum_verified":True,
        "paper_extension_sha256":{name:sha(paper / name) for name in ("verification.json", "evidence.json", "REPORT_EL.md")},
        "alignment_controls_addendum_verified":True,
        "alignment_controls_sha256":{name:sha(controls / name) for name in ("verification.json", "report_verification.json", "evidence.json", "REPORT_EL.md")},
        "variable_campaign_addendum_verified":True,
        "variable_campaign_sha256":{name:sha(variable / name) for name in ("verification.json", "report_verification.json", "evidence.json", "REPORT_EL.md")},
        "selection_audit_addendum_verified":True,
        "selection_audit_sha256":{name:sha(selection_audit / name) for name in ("verification.json", "report_verification.json", "evidence.json", "REPORT_EL.md")},
        "selection_audit_no_attack_or_key_metadata_reads":True,
        "selection_audit_fixed_used_profiling_rows":40000,
        "selection_audit_variable_used_profiling_rows":20000,
        "six_phase_recorded_cpu_experiment_seconds":audit_evidence["six_phase_cpu_seconds"],
        "variable_key_attack_subset_viewed":True,
        "final_attack_set_read_field_scope":"Original fixed-key dataset; new variable-key subset evaluated only after frozen fit",
        "five_phase_recovery_summaries":448, "five_phase_execution_endpoint_checks":8960,
        "additional_independent_endpoint_replays":160,
        "cpu_reproduction_sha256":{name:sha(reproduction / name) for name in
            ("verification.json", "results.json", "REPORT_EL.md", "environment.json", "pytest.xml")},
        "reproduction_addendum_verified":True,
        "plots_visually_checked":["baseline_histories.png"],
        "artifact_sha256":{name:sha(OUT / name) for name in ("evidence.json", "baseline_histories.png", "REPORT_EL.md")},
        "documentation_sha256":{relative:sha(ROOT / relative) for relative in
            ("README.md", "PROJECT_PLAN.md", "PROGRESS.md", "docs/EXPERIMENT_PROTOCOL.md",
             "literature/REVIEW.md", "literature/PRIMARY_AUDIT_2026-10-05.md",
             "literature/PAPER_ALIGNMENT_AUDIT_2026-10-05.md", "literature/ALIGNMENT_BASELINES_2026-10-05.md",
             "literature/VARIABLE_CAMPAIGN_2026-10-05.md", "literature/SELECTION_AUDIT_2026-10-06.md", "AGENTS.md")}}
    write_json(OUT / "verification.json", record)
    print(json.dumps({k:v for k,v in record.items() if k not in ("artifact_sha256", "documentation_sha256", "checkpoint_sha256")}, indent=2))


if __name__ == "__main__":
    main()
