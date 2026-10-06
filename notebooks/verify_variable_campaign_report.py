"""Check the new-campaign report tables, costs, links and source evidence."""
import argparse
import csv
import json
import re

from sca.train import write_json
from paper_alignment import ROOT, read, sha

OUT = ROOT / "outputs/paper_variable_campaign_2026-10-05"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plot-visually-checked", action="store_true")
    args = parser.parse_args()
    assert args.plot_visually_checked, "Inspect campaign_replication.png first"
    evidence, verified, record = (read(OUT / name) for name in ("evidence.json", "verification.json", "results.json"))
    for name, expected in {**evidence["input_sha256"], **verified["artifact_sha256"]}.items():
        assert sha(OUT / name) == expected, name
    report = (OUT / "REPORT_EL.md").read_text(encoding="utf-8")
    with (OUT / "recovery_summary.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(record["results"]) == 48
    for observed, actual in zip(rows, record["results"]):
        for name, value in actual.items():
            assert observed[name] == ("" if value is None else str(value)), name
    lookup = {(r["condition"], r["method"], r["family"]): r for r in record["results"]}
    labels = ("Fixed", "NCC", "Gaussian", "SAD mean", "Gaussian wrong row", "Known injected shift")
    plan = read(OUT / "plan.json")
    for method, label in zip(plan["methods"], labels):
        line = next(line for line in report.splitlines() if line.startswith("| " + label + " |"))
        cells = [cell.strip() for cell in line.strip("|").split("|")][1:]
        expected = [" / ".join(f"{round(lookup[(condition['name'], method, family)]['sr_at_budget'] * 20)}/20"
                              for family in ("pair1", "pair2")) for condition in plan["conditions"]]
        assert cells == expected, label
    fit = read(OUT / "fit.json")
    validation = {(r["condition"], r["method"], r["family"]): r for r in record["validation_correlations"]}
    for family in ("pair1", "pair2"):
        line = next(line for line in report.splitlines() if line.startswith("| " + family + " |"))
        cells = [cell.strip() for cell in line.strip("|").split("|")][1:]
        assert cells == [f"{fit['training_coefficients'][family]:.6f}",
            f"{validation[('clean','fixed',family)]['hw_correlation']:.6f}",
            f"{validation[('clean','gaussian_template',family)]['hw_correlation']:.6f}"]
    previous_seconds = sum(read(ROOT / "outputs" / name / "results.json")["seconds"] for name in
        ("paper_alignment_2026-10-05", "paper_alignment_coordinates_2026-10-05", "paper_maskfree_2026-10-05", "paper_alignment_controls_2026-10-05"))
    assert evidence["five_phase_cpu_seconds"] == previous_seconds + record["seconds"]
    assert f"{record['seconds']:.6f}s" in report and f"{evidence['five_phase_cpu_seconds']:.6f}s" in report
    assert evidence["five_phase_recovery_summaries"] == 448 and evidence["five_phase_execution_endpoints"] == 8960
    assert evidence["additional_endpoint_replays"] == 160
    assert not evidence["support_criterion_met"] and not evidence["novelty_verified"] and not evidence["paper_ready"]
    assert evidence["tests"]["tests"] == 65 and not evidence["tests"]["failures"]
    local_links = 0
    for target in re.findall(r"\]\(([^)]+)\)", report):
        if not target.startswith(("https://", "http://")):
            assert (OUT / target).resolve().is_file(), target
            local_links += 1
    result = {"recovery_rows": 48, "report_recovery_table_verified": True,
        "validation_table_verified": True, "csv_verified": True, "costs_verified": True,
        "local_links_verified": local_links, "plot_visually_checked": True,
        "five_phase_recovery_summaries": 448, "five_phase_execution_endpoints": 8960,
        "additional_endpoint_replays": 160, "support_criterion_met": False,
        "new_variable_key_attack_subset_viewed": True, "original_fixed_key_attack_payloads_read": False,
        "new_gpu_trainings": 0, "tests": verified["tests"],
        "artifact_sha256": {name: sha(OUT / name) for name in
            ("REPORT_EL.md", "evidence.json", "recovery_summary.csv", "campaign_replication.png", "verification.json")}}
    write_json(OUT / "report_verification.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "artifact_sha256"}, indent=2))


if __name__ == "__main__":
    main()
