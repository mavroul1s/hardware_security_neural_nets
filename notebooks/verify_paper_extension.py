"""Verify consolidated paper-extension numbers, provenance and report links."""
import argparse
import csv
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from sca.train import code_identity, write_json
from verify_paper_followups import read, sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/paper_extension_2026-10-05"
PHASES = [ROOT / "outputs" / name for name in
    ("paper_alignment_2026-10-05", "paper_alignment_coordinates_2026-10-05", "paper_maskfree_2026-10-05")]
METHODS = ("fixed", "ncc_template", "gaussian_template", "oracle_known_shift")
CONDITIONS = ("clean", "shift5", "combined5", "combined10_ood")
LABELS = ("Clean", "Shift ±5", "Shift ±5 + σ=1.3", "Shift ±10 + σ=2.6")


def lookup(record):
    return {(row["pool"], row["condition"], row.get("pipeline", "raw_shift"), row["method"], row["family"]): row for row in record["results"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plots-visually-checked", action="store_true")
    args = parser.parse_args()
    assert args.plots_visually_checked, "Inspect both exported figures before marking the report verified"
    evidence = read(OUT / "evidence.json")
    report = (OUT / "REPORT_EL.md").read_text(encoding="utf-8")
    for mapping in ("input_sha256", "original_inputs_sha256"):
        for relative, expected in evidence[mapping].items():
            assert sha(ROOT / relative) == expected, relative
    assert code_identity()["source_sha256"] == evidence["source_sha256"]
    records = [read(path / "results.json") for path in PHASES]
    verifications = [read(path / "verification.json") for path in PHASES]
    rows = [{"phase": index + 1, **row} for index, record in enumerate(records) for row in record["results"]]
    assert rows == evidence["all_results"] and len(rows) == 288
    assert evidence["phase_rows"] == [128, 96, 64]
    assert evidence["experiment_seconds_total"] == sum(record["seconds"] for record in records)
    assert evidence["independent_execution_cpa_endpoints"] == sum(record.get("independent_cpa_endpoint_checks", record.get("independent_endpoint_checks", 0)) for record in records) == 5760
    assert evidence["sampled_independent_shift_estimates"] == sum(record.get("sampled_trace_only_shift_estimates_independently_verified", record.get("sampled_trace_only_estimates_independently_verified", 0)) for record in verifications) == 576
    with (OUT / "all_results.csv").open(encoding="utf-8-sig", newline="") as handle:
        exported = list(csv.DictReader(handle))
    assert len(exported) == len(rows)
    for expected, observed in zip(rows, exported):
        assert int(observed["phase"]) == expected["phase"]
        for field in ("pool", "condition", "method", "family"):
            assert observed[field] == expected[field]
        for field in ("ge_at_budget", "sr_at_budget"):
            assert float(observed[field]) == expected[field]
        assert (int(observed["traces_to_sustained_sr90"]) if observed["traces_to_sustained_sr90"] else None) == expected["traces_to_sustained_sr90"]
    tables_checked = 0
    for table_index, (record, families, pipeline) in enumerate(((records[1], ("rout", "r3"), "raw_shift"),
            (records[1], ("rout", "r3"), "feature_shift_surrogate"), (records[2], ("pair1", "pair2"), "raw_shift"))):
        source = lookup(record)
        for condition, label in zip(CONDITIONS, LABELS):
            matching = [line for line in report.splitlines() if line.startswith("| " + label + " |")]
            assert len(matching) == 3
            cells = [cell.strip() for cell in matching[table_index].strip("|").split("|")]
            expected = [f"{round(source[('confirmation', condition, pipeline, method, family)]['sr_at_budget'] * 20)}/20"
                        for method in METHODS for family in families]
            assert cells[1:] == expected
            tables_checked += 1
    source = lookup(records[2])
    for method, label in zip(METHODS, ("Fixed", "NCC", "Gaussian", "Known shift")):
        line = next(line for line in report.splitlines() if line.startswith("| " + label + " |"))
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        for index, family in enumerate(("pair1", "pair2")):
            item = source[("confirmation", "combined5", "raw_shift", method, family)]
            start = 1 + index * 3
            assert cells[start] == f"{round(item['sr_at_budget'] * 20)}/20"
            assert float(cells[start + 1].replace(",", ".")) == item["ge_at_budget"]
            assert cells[start + 2] == str(item["traces_to_sustained_sr90"] or ">2000")
    support = all(source[("confirmation", "combined5", "raw_shift", "gaussian_template", family)]["sr_at_budget"] >= .9
        and source[("confirmation", "combined5", "raw_shift", "gaussian_template", family)]["sr_at_budget"] - source[("confirmation", "combined5", "raw_shift", "fixed", family)]["sr_at_budget"] >= .1
        and source[("confirmation", "clean", "raw_shift", "gaussian_template", family)]["sr_at_budget"] >= source[("confirmation", "clean", "raw_shift", "fixed", family)]["sr_at_budget"] - .1
        for family in ("pair1", "pair2"))
    assert support == evidence["phase_three_predefined_support_criterion_met"] is True
    assert not evidence["phase_two_both_original_pairs_sr90_criterion_met"]
    assert evidence["mask_free_selection"]["pairs"] == records[2]["pairs"]
    assert verifications[2]["selection_checks"]["independent_real_training_pearson_checks"] == 13
    suite = ET.parse(PHASES[2] / "pytest.xml").getroot().find("testsuite")
    for field in ("tests", "failures", "errors", "skipped"):
        assert evidence["tests"][field] == int(suite.attrib[field])
    log = (ROOT / "runs/kaggle_control/tests_paper_extension_final_2026-10-05.log").read_text(encoding="utf-8-sig")
    assert "57 passed, 14 warnings in 19.43s" in log
    assert evidence["tests"]["seconds"] == float(suite.attrib["time"])
    assert not evidence["novelty_verified"] and not evidence["paper_ready"]
    links = 0
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", report):
        if target.startswith("https://") or target == "verification.json":
            continue
        assert (OUT / target).resolve().is_file(), target
        links += 1
    run = ROOT / "runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature"
    assert not read(run / "baseline_gate.json")["passed"] and not (run / "combined_seed0").exists()
    assert len(list((ROOT / "notebooks").glob("*.ipynb"))) == 1
    assert evidence["new_gpu_trainings"] == evidence["new_real_data_optimizer_updates"] == 0
    assert not evidence["final_attack_payloads_read"]
    verification = {"all_input_sha256_verified": True, "source_and_prior_checkpoint_packet_notebook_preserved": True,
        "recovery_rows": len(rows), "report_sr_table_rows_verified": tables_checked,
        "primary_ge_sr_sustained_table_verified": True, "csv_rows_verified": len(exported),
        "local_report_links_verified": links, "independent_execution_cpa_endpoints": 5760,
        "sampled_independent_shift_estimates": 576, "independent_training_pair_correlations": 13,
        "phase_three_support_criterion_met": support, "phase_two_primary_criterion_failed": True,
        "tests": evidence["tests"], "full_gpu_trainings_total": 3, "canonical_notebook_count": 1,
        "new_gpu_trainings": 0, "new_real_data_optimizer_updates": 0, "final_attack_payloads_read": False,
        "cnn_gate_still_failed": True, "confirmation_pools_are_now_viewed": True,
        "plots_visually_checked": ["coordinate_confirmation.png", "training_label_confirmation.png"],
        "artifact_sha256": {name: sha(OUT / name) for name in ("REPORT_EL.md", "evidence.json", "all_results.csv", "coordinate_confirmation.png", "training_label_confirmation.png")},
        "companion_sha256": {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in
            [ROOT / "notebooks" / name for name in ("paper_alignment.py", "paper_alignment_coordinates.py", "paper_maskfree_selection.py", "verify_paper_alignment.py", "verify_paper_followups.py", "build_paper_extension.py", "verify_paper_extension.py")]
            + [ROOT / "tests" / name for name in ("test_paper_alignment.py", "test_alignment_coordinates.py", "test_maskfree_selection.py")]}}
    write_json(OUT / "verification.json", verification)
    print(json.dumps({key: value for key, value in verification.items() if key not in ("artifact_sha256", "companion_sha256")}, indent=2))


if __name__ == "__main__":
    main()
