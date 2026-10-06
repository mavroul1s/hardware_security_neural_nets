"""Verify report tables, source links, costs and the displayed scientific artifact."""
import argparse
import json
import re

from sca.train import write_json
from paper_alignment import ROOT, read, sha

OUT = ROOT / "outputs/paper_selection_audit_2026-10-06"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plot-visually-checked", action="store_true")
    args = parser.parse_args()
    assert args.plot_visually_checked, "Inspect selection_replication.png first"
    evidence, verified, record = (read(OUT / name) for name in ("evidence.json", "verification.json", "results.json"))
    for name, expected in {**evidence["input_sha256"], **verified["artifact_sha256"]}.items():
        assert sha(OUT / name) == expected, name
    assert evidence["results"] == record["results"]
    report = (OUT / "REPORT_EL.md").read_text(encoding="utf-8")
    for row in record["results"]:
        label = row["campaign"] + " / " + row["family"]
        line = next(line for line in report.splitlines() if line.startswith("| " + label + " |"))
        cells = [c.strip() for c in line.strip("|").split("|")][1:]
        expected = [f"{row['training_correlation']:.6f}", f"{row['confirmation_correlation']:.6f}",
            f"{row['training_global_max_null_tail']:.2f}", f"{row['confirmation_bonferroni_p']:.3f}",
            "Πέρασε" if row["signed_signal_replicates"] else "Δεν πέρασε"]
        assert cells == expected, label
    assert evidence["replicated_pairs"] == sum(row["signed_signal_replicates"] for row in record["results"]) == 3
    prior = read(ROOT / "outputs/paper_variable_campaign_2026-10-05/evidence.json")
    assert evidence["six_phase_cpu_seconds"] == prior["five_phase_cpu_seconds"] + record["seconds"]
    assert f"{record['seconds']:.6f}s" in report and f"{evidence['six_phase_cpu_seconds']:.6f}s" in report
    assert evidence["prior_recovery_summaries"] == 448 and evidence["no_new_recovery_summaries"]
    assert evidence["prior_execution_endpoints"] == 8960 and evidence["prior_additional_replays"] == 160
    assert not evidence["novelty_verified"] and not evidence["paper_ready"]
    assert evidence["tests"]["tests"] == 70 and not evidence["tests"]["failures"]
    assert not evidence["attack_payloads_or_key_metadata_read_in_this_audit"]
    local_links = 0
    for target in re.findall(r"\]\(([^)]+)\)", report):
        if not target.startswith(("https://", "http://")):
            assert (OUT / target).resolve().is_file(), target
            local_links += 1
    result = {"result_rows": 4, "replicated_pairs": 3, "report_table_verified": True,
        "local_links_verified": local_links, "costs_verified": True, "plot_visually_checked": True,
        "no_new_key_recovery_results": True, "new_gpu_trainings": 0,
        "attack_payloads_or_key_metadata_read_in_this_audit": False, "tests": verified["tests"],
        "artifact_sha256": {name: sha(OUT / name) for name in
            ("REPORT_EL.md", "evidence.json", "selection_replication.png", "verification.json")}}
    write_json(OUT / "report_verification.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "artifact_sha256"}, indent=2))


if __name__ == "__main__":
    main()
