"""Check consolidated evidence, report tables, links and preserved production files."""
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

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
    windows = ROOT / "outputs/paper_window_regression_2026-10-06"
    windows_report = read(windows / "report_verification.json")
    windows_verified = read(windows / "verification.json")
    windows_evidence = read(windows / "evidence.json")
    precision = ROOT / "outputs/paper_precision_replication_2026-10-06"
    precision_report = read(precision / "report_verification.json")
    precision_verified = read(precision / "verification.json")
    precision_evidence = read(precision / "evidence.json")
    for directory, final_check in ((windows, windows_report), (precision, precision_report)):
        for name, expected in final_check["artifact_sha256"].items():
            assert sha(directory / name) == expected, name
    assert windows_verified["production_source_sha256"] == precision_verified["production_source_sha256"] == evidence["production_source_sha256"]
    assert windows_verified["correlation_rows_verified"] == 900 and windows_verified["additional_endpoint_replays"] == 10800
    assert windows_verified["paired_bootstrap_samples_replayed"] == 7996
    assert precision_verified["correlation_rows_verified"] == 360 and precision_verified["bootstrap_draws_replayed"] == 39996
    assert precision_verified["unchanged_fit_verified"] and not precision_verified["new_attack_reads"]
    assert not windows_evidence["primary_support_met"] and not windows_evidence["secondary_attack"]["criterion_met"]
    assert precision_evidence["support_met"] and precision_evidence["phase7_primary_failure_preserved"]
    assert not windows_evidence["paper_ready"] and not precision_evidence["paper_ready"]
    assert not windows_evidence["novelty_verified"] and not precision_evidence["novelty_verified"]
    assert windows_report["tests"]["tests"] == 79 and precision_report["tests"]["tests"] == 82
    assert "## 16." in report and "## 17." in report and "2.142,197628s" in report
    assert round(precision_evidence["eight_phase_cpu_seconds"], 6) == 2142.197628
    assert precision_evidence["prior_recovery_summaries"] == 988 and precision_evidence["prior_execution_endpoint_checks"] == 19760
    assert precision_evidence["prior_additional_endpoint_replays"] == 10960
    for section_number, results in (("16", windows_evidence["primary"]), ("17", precision_evidence["intervals"])):
        section = report.split("## " + section_number + ".", 1)[1]
        for row in results:
            label = (row["campaign"] + " / " + row["pool"]) if section_number == "16" else row["pool"] + " / " + row["scheme"]
            line = next(l for l in section.splitlines() if l.startswith("| " + label + " |"))
            expected = [f"{row['difference']:.6f}", f"{row['lower']:.6f}", f"{row['upper']:.6f}", "Πέρασε" if row["support"] else "Δεν πέρασε"]
            assert [c.strip() for c in line.strip("|").split("|")][1:] == expected
    training_alignment = ROOT / "outputs/paper_training_alignment_2026-10-06"
    training_report = read(training_alignment / "report_verification.json")
    training_verified = read(training_alignment / "verification.json")
    training_evidence = read(training_alignment / "evidence.json")
    training_results = read(training_alignment / "results.json")
    for name, expected in training_report["artifact_sha256"].items():
        assert sha(training_alignment / name) == expected, name
    assert training_verified["production_source_sha256"] == evidence["production_source_sha256"]
    assert training_verified["correlation_rows_verified"] == training_report["all_csv_rows_verified"] == 432
    assert training_verified["all_training_offsets_replayed"] == 10000
    assert training_verified["training_selection_matrices_replayed"] == 2
    assert training_verified["all_feature_weight_vectors_replayed"] == 24
    assert training_verified["bootstrap_draws_replayed"] == 39996
    assert training_verified["sampled_evaluation_offsets_replayed"] == 528
    assert training_verified["training_fit_preceded_confirmation"] and training_verified["feature_windows_avoid_padding"]
    assert not training_evidence["support_met"] and not training_verified["new_attack_reads"]
    assert not training_evidence["novelty_verified"] and not training_evidence["paper_ready"]
    assert training_report["tests"]["tests"] == 86 and not training_report["tests"]["failures"]
    assert "## 18." in report and "2.374,714738s" in report
    assert round(training_evidence["nine_phase_cpu_seconds"], 6) == 2374.714738
    assert training_evidence["nine_phase_cpu_seconds"] == precision_evidence["eight_phase_cpu_seconds"] + training_results["seconds"]
    section = report.split("## 18.", 1)[1]
    for row in training_evidence["intervals"]:
        label = row["pool"] + " / " + row["scheme"]
        line = next(l for l in section.splitlines() if l.startswith("| " + label + " |"))
        expected = [f"{row['difference']:.6f}", f"{row['lower']:.6f}", f"{row['upper']:.6f}", "Πέρασε" if row["support"] else "Δεν πέρασε"]
        assert [c.strip() for c in line.strip("|").split("|")][1:] == expected
    training_lookup = {(r["pool"],r["condition"],r["alignment"],r["stage"],r["family"],r["feature"]):r for r in training_results["correlations"]}
    for pool in ("primary", "replication"):
        for condition in ("clean", "combined5", "combined10_ood"):
            line = next(l for l in section.splitlines() if l.startswith("| " + pool + " / " + condition + " |"))
            expected = [" / ".join(f"{training_lookup[(pool,condition,'gaussian_raw',s,f,'covariance_rank1')]['hw_correlation']:.6f}" for s in ("raw","aligned_once")) for f in ("old_pair1","old_pair2","selected_pair1","selected_pair2")]
            assert [c.strip() for c in line.strip("|").split("|")][1:] == expected
    stability = ROOT / "outputs/paper_selection_stability_2026-10-06"
    stability_report = read(stability / "report_verification.json")
    stability_verified = read(stability / "verification.json")
    stability_evidence = read(stability / "evidence.json")
    stability_results = read(stability / "results.json")
    for name, expected in stability_report["artifact_sha256"].items():
        assert sha(stability / name) == expected, name
    for name, expected in stability_verified["artifact_sha256"].items():
        assert sha(stability / name) == expected, name
    assert stability_verified["production_source_sha256"] == evidence["production_source_sha256"]
    assert stability_verified["correlation_rows_verified"] == stability_report["all_csv_rows_verified"] == 528
    assert stability_verified["all_training_full_searches_replayed"] == 20
    assert stability_verified["all_training_weight_vectors_replayed"] == 120
    assert stability_verified["direct_selected_training_coefficients_replayed"] == 40
    assert stability_verified["bootstrap_draws_replayed"] == 79992
    assert stability_verified["sampled_cluster_draws_replayed_with_actual_rows"] == 12
    assert stability_verified["sampled_evaluation_offsets_replayed"] == 176
    assert stability_verified["all_locations_splits_rng_and_centers_replayed"]
    assert stability_verified["training_fit_preceded_confirmation"] and stability_verified["feature_windows_avoid_padding"]
    assert stability_verified["frozen_controls_unchanged"] and stability_verified["no_bootstrap_winner_chosen"]
    assert not stability_verified["new_attack_reads"]
    assert stability_verified["new_gpu_trainings"] == stability_verified["new_optimizer_updates"] == 0
    assert stability_evidence["frozen_signal_met"] and not stability_evidence["pipeline_sensitivity_met"]
    assert not stability_evidence["joint_support_met"]
    assert not stability_evidence["novelty_verified"] and not stability_evidence["paper_ready"]
    assert stability_report["tests"]["tests"] == 90
    assert stability_report["tests"]["failures"] == stability_report["tests"]["errors"] == 0
    assert stability_report["all_selected_pairs_csv_rows_verified"] == 40
    assert stability_evidence["new_key_recovery_rows"] == 0
    assert stability_evidence["variable_used_profiling_rows"] == 150000
    assert stability_evidence["variable_unused_profiling_rows"] == 50000
    assert "## 19." in report and "2.596,295861s" in report
    assert round(stability_evidence["ten_phase_cpu_seconds"], 6) == 2596.295861
    assert stability_evidence["ten_phase_cpu_seconds"] == training_evidence["nine_phase_cpu_seconds"] + stability_results["seconds"]
    section = report.split("## 19.", 1)[1]
    for row in stability_evidence["intervals"]:
        label = row["pool"] + " / " + row["family"] + " / " + row["scheme"]
        line = next(l for l in section.splitlines() if l.startswith("| " + label + " |"))
        expected = [f"{row['correlation']:.6f}", f"{row['lower']:.6f}", f"{row['upper']:.6f}", "Πέρασε" if row["support"] else "Δεν πέρασε"]
        assert [c.strip() for c in line.strip("|").split("|")][1:] == expected
    for row in stability_evidence["sensitivity"]:
        label = row["pool"] + " / " + row["condition"] + " / " + row["family"]
        line = next(l for l in section.splitlines() if l.startswith("| " + label + " |"))
        expected = [f"{row['median']:.6f}", f"{row['minimum']:.6f}", f"{row['maximum']:.6f}", f"{row['positive_draws']}/20", "Πέρασε" if row["support"] else "Δεν πέρασε"]
        assert [c.strip() for c in line.strip("|").split("|")][1:] == expected
    for row in stability_evidence["locations"]:
        line = next(l for l in section.splitlines() if l.startswith("| " + str(row["tolerance"]) + " |"))
        expected = [" / ".join(str(v) + "/20" for v in row[k]) for k in ("ordered_hits", "either_family_hits")]
        expected += [" / ".join(f"{v:.1f}" for v in row["ordered_median_max_point_distance"])]
        assert [c.strip() for c in line.strip("|").split("|")][1:] == expected
    algebra = ROOT / "outputs/regression_prior_art_audit_2026-10-08"
    algebra_verified = read(algebra / "verification.json")
    assert sha(ROOT / "notebooks/audit_regression_prior_art.py") == algebra_verified["source_sha256"]
    assert sha(algebra / "arrays.npz") == algebra_verified["arrays_sha256"]
    assert algebra_verified["deterministic_synthetic_algebra_checks"] == 5
    assert not algebra_verified["physical_efficacy_evidence"]
    assert algebra_verified["new_real_data_reads"] == algebra_verified["new_gpu_trainings"] == algebra_verified["new_models_trained"] == 0
    with np.load(algebra / "arrays.npz", allow_pickle=False) as a:
        assert np.allclose(a["q"].T @ a["q"], np.eye(2))
        assert np.linalg.matrix_rank(a["x"]) == np.linalg.matrix_rank(a["x"] @ a["q"]) == 1
        assert np.allclose(np.linalg.eigvalsh(a["covariance"]), np.linalg.eigvalsh(a["rotated"]))
        assert a["retained"].shape == (5, 1) and np.linalg.matrix_rank(a["retained"]) == 1
        assert np.allclose(np.linalg.pinv(a["x"] @ a["q"]) @ a["x"][:, 0], a["q"].T @ np.linalg.pinv(a["x"]) @ a["x"][:, 0])
        expected = .4**2 * (np.kron(a["ca"], np.eye(2)) + np.kron(np.eye(2), a["cb"])) + .4**4 * np.eye(4)
        assert np.allclose(a["correction"], expected) and np.allclose(a["corrected"], a["gram"] + expected)
        assert np.linalg.matrix_rank(a["gram"]) == 2 and np.linalg.matrix_rank(a["corrected"]) == 4
        assert np.linalg.eigvalsh(expected).min() == algebra_verified["minimum_noise_correction_eigenvalue"]
        assert np.linalg.eigvalsh(a["corrected"]).min() == algebra_verified["minimum_corrected_gram_eigenvalue"]
        assert np.allclose(a["g"] @ a["w_linear"] - a["b"] + a["c"], 0)
        assert np.allclose((a["g"] + .4**2 * np.eye(2)) @ a["w_quadratic"], a["b"])
        assert not np.allclose(a["w_linear"], a["w_quadratic"])
    assert "## 20." in report and "Πέντε deterministic synthetic correctness checks" in report
    assert "minimumcorrectioneigenvalue0,276751, correctedGram0,288114" in report
    proposal = (ROOT / "docs/PAPER_CANDIDATE.md").read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)]+)\)", proposal):
        if not target.startswith(("http://", "https://")):
            assert (ROOT / "docs" / target).resolve().is_file(), target
    objective = ROOT / "outputs/paper_window_selection_2026-10-09"
    objective_report = read(objective / "report_verification.json")
    objective_verified = read(objective / "verification.json")
    objective_evidence = read(objective / "evidence.json")
    objective_results = read(objective / "results.json")
    for name, expected in objective_report["artifact_sha256"].items():
        assert sha(objective / name) == expected, name
    for name, expected in objective_verified["artifacts_sha256"].items():
        assert sha(objective / name) == expected, name
    assert objective_verified["full_searches"] == 40 and objective_verified["training_weight_vectors"] == 240
    assert objective_verified["selected_coefficients"] == 80 and objective_verified["oob_coefficients"] == 240
    assert objective_verified["fresh_coefficients"] == objective_report["fresh_csv_rows"] == 960
    assert objective_verified["sampled_offset_checks"] == 100
    assert objective_verified["all_split_unions_replayed"] and objective_verified["source_preserved"]
    assert objective_verified["no_attack_reads"] and objective_verified["passing_tests"] == 95
    assert not objective_results["H1_primary_met"] and not objective_results["H2_secondary_met"]
    assert objective_results["new_gpu_trainings"] == objective_results["new_optimizer_updates"] == 0
    assert objective_evidence["new_key_recovery_rows"] == 0
    assert objective_evidence["variable_viewed_profiling_rows"] == 170000 and objective_evidence["variable_unused_profiling_rows"] == 30000
    assert objective_evidence["eleven_phase_cpu_seconds"] == stability_evidence["ten_phase_cpu_seconds"] + objective_results["seconds"]
    assert not objective_evidence["novelty_verified"] and not objective_evidence["paper_ready"]
    assert "## 21." in report and "170k viewed/30k unused" in report and "95 tests passed" in report
    for row in objective_evidence["primary"]:
        line = f"| {row['pool']} / {row['family']} | {row['baseline_median']:.6f} | {row['window_median']:.6f} | {row['median_paired_difference']:.6f} | {row['window_positive_draws']}/20 |"
        assert line in report
    assert sum(row["support"] for row in objective_results["oob_prediction"]) == 7
    assert f"{objective_results['seconds']:.6f}s" in report and f"{objective_evidence['eleven_phase_cpu_seconds']:.6f}s" in report
    recipe = ROOT / "outputs/kaggle_recipe_2026-10-09"
    recipe_report = read(recipe / "report_verification.json")
    recipe_evidence = read(recipe / "evidence.json")
    recipe_verified = read(recipe / "verification.json")
    recipe_plan = read(recipe / "plan.json")
    recipe_results = read(recipe / "results.json")
    for name, expected in recipe_report["artifact_sha256"].items():
        assert sha(recipe / name) == expected, name
    for relative, expected in recipe_plan["input_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    assert recipe_report["same_runtime_environment"] and recipe_report["original_remote_source_restored"]
    assert recipe_report["safe_quick_save_version"] == 10 and recipe_report["same_private_notebook"]
    assert recipe_verified["rank_prefixes_verified"] == 40000 and recipe_verified["schedule_values_verified"] == 10000
    assert recipe_verified["gpu_predictions_verified"] == 5000 and recipe_verified["source_preserved"]
    assert recipe_verified["old_checkpoints_preserved"] and recipe_verified["original_notebook_v8_preserved"]
    assert recipe_results["new_gpu_trainings"] == 1 and recipe_results["full_gpu_trainings_total"] == 4
    assert not recipe_results["primary_met"] and not recipe_results["combined_training_performed"]
    assert not recipe_results["attack_payloads_read"] and recipe_results["new_confirmation_rows"] == 0
    assert int(recipe_plan["tests"]["tests"]) == 99 and int(recipe_plan["tests"]["failures"]) == int(recipe_plan["tests"]["errors"]) == 0
    assert "## 22." in report and "99 tests passed" in report
    for row in recipe_evidence["comparisons"]:
        line = f"| {row['recipe']} | {row['updates']} | {row['best_epoch']} | {row['minimum_ce']:.6f} | {round(row['sr']*20)}/20 | {row['ge']:.6f} |"
        assert line in report
    assert f"{recipe_evidence['experiment_seconds']:.6f}s" in report
    budget = ROOT / "outputs/kaggle_budget_2026-10-11/api"
    budget_report = read(budget / "report_verification.json")
    budget_evidence = read(budget / "evidence.json")
    budget_verified = read(budget / "verification.json")
    budget_plan = read(budget / "plan.json")
    budget_results = read(budget / "results.json")
    for name, expected in budget_report["artifact_sha256"].items():
        assert sha(budget / name) == expected, name
    for relative, expected in budget_plan["input_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    assert budget_report["verified"] and budget_report["preserved_original_files"] == 26
    assert budget_report["original_remote_source_restored"] and budget_report["safe_quick_save_version"] == 3
    assert budget_results["primary_met"] and budget_results["full_gpu_trainings_total"] == 5
    assert not budget_results["combined_training_performed"] and not budget_results["attack_payloads_read"]
    assert budget_verified["schedule_values_verified"] == 45000 and budget_verified["rank_prefixes_verified"] == 40000
    assert budget_verified["gpu_predictions_verified"] == 5000
    assert budget_evidence["same_runtime_environment"] and budget_evidence["traces_to_sustained_sr90"] == 504
    budget_tests = ET.parse(budget.parent / "transport_repair/portable_pytest.xml").getroot().find("testsuite").attrib
    assert int(budget_tests["tests"]) == 105 and budget_tests["failures"] == budget_tests["errors"] == "0"
    assert "## 23." in report and "105 tests passed" in report and "66.850" in report
    for row in budget_evidence["comparisons"]:
        line = f"| {row['name']} | {row['n_train']} | {row['updates']} | {row['best_epoch']} | {row['minimum_ce']:.6f} | {round(row['sr']*20)}/20 | {row['ge']:.6f} |"
        assert line in report
    assert f"{budget_evidence['experiment_seconds']:.6f}s" in report
    record = {"artifact_inputs_verified":len(evidence["input_sha256"]),
        "baseline_report_table_verified":True, "sensitivity_report_table_verified":True,
        "report_local_links_verified":link_count, "cost_totals_verified":True,
        "production_source_unchanged":True, "checkpoint_sha256":checkpoint_hashes,
        "active_packet_unchanged":True, "notebook_matches_saved_private_version8":True, "notebook_count":1,
        "cnn_gate_still_failed":True, "original_study_gpu_trainings_total":3,
        "full_gpu_trainings_total":5, "new_training_performed":True,
        "new_kaggle_execution":True, "final_attack_set_read":False,
        "full_test_suite_at_original_synthesis":{**evidence["local_tests"], "rerun_for_document_synthesis":False},
        "latest_full_test_suite":{**budget_tests, "run_for_budget_transport_portability":True},
        "kaggle_budget_addendum_verified":True,"kaggle_budget_primary_passed":True,
        "kaggle_budget_actual_updates":45000,"five_gpu_trainings_total_updates":66850,
        "five_gpu_trainings_total_exposures":4250000,
        "five_gpu_training_loop_seconds":evidence["training_loop_seconds_total"]+recipe_evidence["training_loop_seconds"]+budget_evidence["training_seconds"],
        "five_gpu_validation_loop_seconds":evidence["validation_loop_seconds_total"]+recipe_evidence["validation_loop_seconds"]+budget_evidence["validation_seconds"],
        "kaggle_budget_sha256":{n:sha(budget/n) for n in ("REPORT_EL.md","evidence.json","verification.json","report_verification.json","plan.json")},
        "active_continuation_notebook_count":1,"preserved_previous_account_notebook":True,
        "active_account":"nmavros","active_safe_saved_kernel_version":3,
        "window_selection_full_test_suite":{**objective_evidence["tests"], "run_for_window_selection":True},
        "kaggle_recipe_addendum_verified":True,"kaggle_recipe_primary_failed":True,
        "kaggle_recipe_actual_updates":10000,"four_gpu_trainings_total_updates":21850,
        "four_gpu_trainings_loop_seconds":evidence["training_loop_seconds_total"]+recipe_evidence["training_loop_seconds"],
        "four_gpu_validation_loop_seconds":evidence["validation_loop_seconds_total"]+recipe_evidence["validation_loop_seconds"],
        "kaggle_recipe_experiment_seconds":recipe_evidence["experiment_seconds"],
        "kaggle_recipe_rank_prefixes_verified":40000,"safe_saved_kernel_version":10,
        "kaggle_recipe_sha256":{n:sha(recipe/n) for n in ("REPORT_EL.md","evidence.json","verification.json","report_verification.json","plan.json")},
        "selection_stability_full_test_suite":{**stability_report["tests"], "run_for_selection_stability":True},
        "training_alignment_full_test_suite":{**training_report["tests"], "run_for_training_side_alignment":True},
        "precision_replication_full_test_suite":{**precision_report["tests"], "run_for_larger_profiling_replication":True},
        "selection_audit_full_test_suite":{**audit_report["tests"], "run_for_selection_audit":True},
        "window_regression_full_test_suite":{**windows_report["tests"], "run_for_window_regression":True},
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
        "eight_phase_recorded_cpu_experiment_seconds":precision_evidence["eight_phase_cpu_seconds"],
        "window_regression_and_precision_addenda_verified":True,
        "new_correlation_comparisons":3180,"new_recovery_summaries":540,
        "new_comparisons_field_scope":"Phases7/8/9/10/11 fresh computational rows; phase11 internal240OOB rows separate; shared fits/confirmations, not independent keys or acquisitions",
        "eight_phase_recovery_summaries":988,"eight_phase_execution_endpoints":19760,
        "eight_phase_additional_endpoint_replays":10960,
        "fixed_used_profiling_rows":50000,"variable_used_profiling_rows":170000,"variable_viewed_attack_rows":10000,
        "variable_unused_profiling_rows":30000,
        "eleven_phase_recorded_cpu_experiment_seconds":objective_evidence["eleven_phase_cpu_seconds"],
        "window_selection_addendum_verified":True,"window_selection_primary_failed":True,
        "window_selection_secondary_joint_failed":True,"window_selection_new_fresh_correlations":960,
        "window_selection_internal_oob_coefficients":240,"window_selection_no_attack_reads":True,
        "window_selection_sha256":{n:sha(objective/n) for n in ("REPORT_EL.md","evidence.json","verification.json","report_verification.json")},
        "nine_phase_recorded_cpu_experiment_seconds":training_evidence["nine_phase_cpu_seconds"],
        "ten_phase_recorded_cpu_experiment_seconds":stability_evidence["ten_phase_cpu_seconds"],
        "selection_stability_addendum_verified":True,"selection_stability_joint_primary_failed":True,
        "selection_stability_frozen_signal_passed":True,"selection_stability_sensitivity_failed":True,
        "selection_stability_new_correlation_rows":528,"selection_stability_training_draws":20,
        "selection_stability_no_attack_reads":True,"selection_stability_no_winner_chosen":True,
        "selection_stability_sha256":{n:sha(stability/n) for n in ("REPORT_EL.md","evidence.json","verification.json","report_verification.json")},
        "regression_prior_art_algebra_addendum_verified":True,
        "deterministic_synthetic_algebra_checks":5,"algebra_checks_are_physical_efficacy_evidence":False,
        "regression_prior_art_sha256":{n:sha(algebra/n) for n in ("arrays.npz","verification.json")},
        "training_alignment_addendum_verified":True,"training_alignment_primary_failed":True,
        "training_alignment_no_attack_reads":True,"training_alignment_new_correlation_rows":432,
        "cpu_closed_form_feature_fits_performed_in_phase9":True,
        "training_alignment_sha256":{n:sha(training_alignment/n) for n in ("REPORT_EL.md","evidence.json","verification.json","report_verification.json")},
        "new_training_performed_field_scope":"Kaggle recipe10000updates and nested45k45000updates; original synthesis3trainings preserved. CPU phases7/9/10/11 fits recorded separately",
        "cpu_closed_form_feature_fits_performed_in_phase11":True,
        "cpu_closed_form_feature_fits_performed_in_phase10":True,
        "cpu_closed_form_feature_fits_performed_in_phase7":True,"no_new_fit_in_phase8":True,
        "window_regression_sha256":{n:sha(windows/n) for n in ("REPORT_EL.md","evidence.json","verification.json","report_verification.json")},
        "precision_replication_sha256":{n:sha(precision/n) for n in ("REPORT_EL.md","evidence.json","verification.json","report_verification.json")},
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
            ("README.md", "PROJECT_PLAN.md", "PROGRESS.md", "docs/EXPERIMENT_PROTOCOL.md", "docs/KAGGLE.md",
             "literature/REVIEW.md", "literature/PRIMARY_AUDIT_2026-10-05.md",
             "literature/PAPER_ALIGNMENT_AUDIT_2026-10-05.md", "literature/ALIGNMENT_BASELINES_2026-10-05.md",
             "literature/VARIABLE_CAMPAIGN_2026-10-05.md", "literature/SELECTION_AUDIT_2026-10-06.md",
             "literature/WINDOW_REGRESSION_2026-10-06.md", "literature/WINDOW_REGRESSION_PRIOR_ART_FOLLOWUP_2026-10-06.md",
             "literature/TRAINING_ALIGNMENT_2026-10-06.md", "literature/SELECTION_STABILITY_2026-10-06.md",
             "literature/SCHEME_AWARE_FULLTEXT_AUDIT_2026-10-06.md",
             "literature/REGRESSION_PRIOR_ART_COMPARISON_2026-10-08.md",
             "literature/SELECTION_OBJECTIVE_AUDIT_2026-10-09.md", "literature/bibliography.bib",
             "docs/PAPER_CANDIDATE.md", "AGENTS.md")}}
    write_json(OUT / "verification.json", record)
    print(json.dumps({k:v for k,v in record.items() if k not in ("artifact_sha256", "documentation_sha256", "checkpoint_sha256")}, indent=2))


if __name__ == "__main__":
    main()
