"""Check phase-four report tables, CSV, figure review and preserved inputs."""
import argparse
import csv
import json
from pathlib import Path
import re

from sca.train import code_identity, write_json
from verify_paper_followups import read, sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/paper_alignment_controls_2026-10-05"
METHODS = ("fixed", "ncc_template", "gaussian_template", "sad_training_mean", "sad_training_reference",
           "gaussian_offsets_rolled", "oracle_known_shift")
LABELS = ("Fixed", "NCC", "Gaussian", "SAD mean", "SAD reference", "Wrong row", "Known shift")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plot-visually-checked", action="store_true")
    args = parser.parse_args()
    assert args.plot_visually_checked, "Inspect the exported figure before marking it verified"
    evidence, record, verified, plan = [read(OUT / name) for name in ("evidence.json", "results.json", "verification.json", "plan.json")]
    report = (OUT / "REPORT_EL.md").read_text(encoding="utf-8")
    for name, expected in evidence["input_sha256"].items():
        assert sha(OUT / name) == expected
    for relative, expected in plan["input_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    assert code_identity()["source_sha256"] == verified["source_sha256"] == plan["source_sha256"]
    assert evidence["results"] == record["results"] and len(record["results"]) == 112
    lookup = {(row["pool"], row["condition"], row["method"], row["family"]): row for row in record["results"]}
    for condition, label in zip(("clean", "shift5", "combined5", "combined10_ood"),
                                ("Clean", "Shift ±5", "Shift ±5 + σ=1.3", "Shift ±10 + σ=2.6")):
        line = next(line for line in report.splitlines() if line.startswith("| " + label + " |"))
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        expected = [", ".join(f"{round(lookup[('confirmation', condition, method, family)]['sr_at_budget'] * 20)}/20" for family in ("pair1", "pair2")) for method in METHODS]
        assert cells[1:] == expected
    primary_section = report.split("**Κύρια combined5 συνθήκη:**", 1)[1].split("## 4.", 1)[0]
    for method, label in zip(METHODS, LABELS):
        line = next(line for line in primary_section.splitlines() if line.startswith("| " + label + " |"))
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        for i, family in enumerate(("pair1", "pair2")):
            item = lookup[("confirmation", "combined5", method, family)]
            start = 1 + 3 * i
            assert cells[start] == f"{round(item['sr_at_budget'] * 20)}/20"
            assert float(cells[start + 1].replace(",", ".")) == item["ge_at_budget"]
            assert cells[start + 2] == str(item["traces_to_sustained_sr90"] or ">2000")
    alignment = {row["method"]: row for row in record["alignment"] if row["pool"] == "confirmation" and row["condition"] == "combined5"}
    timing = {row["method"]: row for row in record["inference_timings"] if row["pool"] == "confirmation" and row["condition"] == "combined5"}
    timing_section = report.split("## 4.", 1)[1]
    for method, label in zip(METHODS[1:5], LABELS[1:5]):
        line = next(line for line in timing_section.splitlines() if line.startswith("| " + label + " |"))
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        expected = [f"{alignment[method]['exact_shift_fraction'] * 100:.2f}%",
                    f"{alignment[method]['mean_absolute_error']:.4f}", f"{timing[method]['inference_seconds']:.4f}",
                    f"{timing[method]['microseconds_per_trace']:.2f}"]
        assert cells[1:] == [cell.replace(".", ",") for cell in expected]
    with (OUT / "all_results.csv").open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert len(csv_rows) == 112
    for observed, expected in zip(csv_rows, record["results"]):
        for field in ("pool", "condition", "method", "family"):
            assert observed[field] == expected[field]
        for field in ("ge_at_budget", "sr_at_budget"):
            assert float(observed[field]) == expected[field]
        assert (int(observed["traces_to_sustained_sr90"]) if observed["traces_to_sustained_sr90"] else None) == expected["traces_to_sustained_sr90"]
    previous = read(ROOT / "outputs/paper_extension_2026-10-05/evidence.json")
    assert evidence["four_phase_recovery_summaries"] == previous["total_recovery_summaries"] + len(record["results"]) == 400
    assert evidence["four_phase_independent_execution_cpa_endpoints"] == previous["independent_execution_cpa_endpoints"] + verified["independent_endpoint_checks_during_execution"] == 8000
    assert evidence["additional_independent_endpoint_replays"] == verified["additional_independent_endpoint_replays"] == 112
    assert evidence["four_phase_cpu_experiment_seconds"] == previous["experiment_seconds_total"] + record["seconds"]
    assert evidence["predefined_correspondence_criterion_met"] == verified["predefined_correspondence_criterion_met"] is True
    assert evidence["tests"] == verified["tests"] and evidence["tests"]["tests"] == 61
    assert not evidence["gaussian_better_than_sad_mean_at_primary_endpoint"] and not evidence["novelty_verified"]
    for family in ("pair1", "pair2"):
        assert lookup[("confirmation", "combined5", "gaussian_template", family)]["sr_at_budget"] == lookup[("confirmation", "combined5", "sad_training_mean", family)]["sr_at_budget"] == 1.
        assert lookup[("confirmation", "combined5", "gaussian_offsets_rolled", family)]["sr_at_budget"] == 0.
    links = 0
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", report):
        if target.startswith("https://") or target == "report_verification.json":
            continue
        assert (OUT / target).resolve().is_file(), target
        links += 1
    verification = {"report_sr_table_rows_verified": 4, "primary_ge_sr_sustained_table_verified": True,
        "alignment_accuracy_and_single_call_timings_verified": True, "csv_rows_verified": 112,
        "report_local_links_verified": links, "all_input_sha256_verified": True,
        "source_checkpoint_packet_and_canonical_notebook_preserved": True,
        "tests": verified["tests"], "four_phase_recovery_summaries": 400,
        "four_phase_independent_execution_cpa_endpoints": 8000, "additional_independent_endpoint_replays": 112,
        "gaussian_primary_sr_equal_to_sad_mean": True, "wrong_correspondence_primary_sr_zero": True,
        "novelty_unverified": True, "new_gpu_trainings": 0, "full_gpu_trainings_total": 3,
        "canonical_notebook_count": 1, "final_attack_payloads_read": False,
        "plots_visually_checked": ["sad_and_correspondence.png"],
        "artifact_sha256": {name: sha(OUT / name) for name in ("REPORT_EL.md", "all_results.csv", "evidence.json", "sad_and_correspondence.png", "verification.json")},
        "companion_sha256": {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in
            [ROOT / "notebooks" / name for name in ("paper_alignment_controls.py", "verify_alignment_controls.py", "build_alignment_controls_report.py", "verify_alignment_controls_report.py")]
            + [ROOT / "tests/test_alignment_controls.py", ROOT / "literature/ALIGNMENT_BASELINES_2026-10-05.md"]}}
    write_json(OUT / "report_verification.json", verification)
    print(json.dumps({key: value for key, value in verification.items() if key not in ("artifact_sha256", "companion_sha256")}, indent=2))


if __name__ == "__main__":
    main()
