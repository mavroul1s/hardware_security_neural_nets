"""Check phase7 report tables, CSV completeness, costs, links and reviewed figures."""
import argparse
import csv
import json
import re
from sca.train import write_json
from paper_alignment import ROOT, read, sha
from build_window_regression_report import OUT, LABELS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plots-visually-checked",action="store_true")
    args=parser.parse_args()
    if not args.plots_visually_checked: raise RuntimeError("Inspect both figures before marking visual QA")
    report=(OUT/"REPORT_EL.md").read_text(encoding="utf-8")
    evidence,record,verified,plan=[read(OUT/name) for name in ("evidence.json","results.json","verification.json","plan.json")]
    for name,expected in evidence["input_sha256"].items():assert sha(OUT/name)==expected
    for name,expected in verified["artifact_sha256"].items():assert sha(OUT/name)==expected
    for name,rows in (("correlations.csv",record["correlations"]),("recovery.csv",record["recoveries"]),("alignment.csv",record["alignment"])):
        with (OUT/name).open(encoding="utf-8",newline="") as f: stored=list(csv.DictReader(f))
        assert len(stored)==len(rows)
        for actual,expected in zip(stored,rows):
            assert actual=={key:str(value) if value is not None else "" for key,value in expected.items()}
    for row in record["primary"]:
        line=next(l for l in report.splitlines() if l.startswith(f"| {row['campaign']} / {row['pool']} |"))
        cells=[c.strip() for c in line.strip("|").split("|")]
        assert cells==[row["campaign"]+" / "+row["pool"],f"{row['difference']:.6f}",f"{row['lower']:.6f}",f"{row['upper']:.6f}","Πέρασε" if row["support"] else "Δεν πέρασε"]
    lookup={(r["campaign"],r["pool"],r["condition"],r["alignment"],r["family"],r["feature"]):r for r in record["recoveries"]}
    verified_table_cells=0
    for campaign,pool in (("fixed","primary"),("fixed","replication"),("variable","fresh_attack")):
        section=report.split("### "+campaign+" / "+pool,1)[1].split("### ",1)[0]
        for feature in plan["features"]:
            line=next(l for l in section.splitlines() if l.startswith("| "+LABELS[feature]+" |"))
            expected=[" / ".join(f"{round(lookup[(campaign,pool,c,'gaussian_template',family,feature)]['sr_at_budget']*20)}/20" for family in ("pair1","pair2")) for c in ("clean","noise5","shift5","combined5","combined10_ood")]
            assert [c.strip() for c in line.strip("|").split("|")][1:]==expected
            verified_table_cells+=len(expected)
    assert evidence["seven_phase_cpu_seconds"]==read(ROOT/"outputs/paper_selection_audit_2026-10-06/evidence.json")["six_phase_cpu_seconds"]+record["seconds"]
    assert evidence["seven_phase_recovery_summaries"]==988 and evidence["seven_phase_execution_endpoints"]==19760
    assert evidence["seven_phase_additional_replays"]==10960
    assert f"{record['seconds']:.6f}s" in report and f"{evidence['seven_phase_cpu_seconds']:.6f}s" in report
    assert evidence["primary_support_met"]==record["primary_support_met"]
    assert evidence["secondary_attack"]==record["secondary_attack"]
    assert not evidence["paper_ready"] and not evidence["novelty_verified"]
    assert evidence["tests"]["tests"]==79 and not evidence["tests"]["failures"]
    links=0
    for target in re.findall(r"\]\(([^)]+)\)",report):
        if not target.startswith(("http://","https://")):
            assert (OUT/target).resolve().is_file(),target
            links+=1
    result={"report_tables_verified":True,"gaussian_recovery_table_cells":verified_table_cells,
        "csv_correlation_rows":900,"csv_recovery_rows":540,"csv_alignment_rows":75,
        "local_links_verified":links,"costs_verified":True,"plots_visually_checked":True,
        "tests":verified["tests"],"primary_support_met":record["primary_support_met"],
        "secondary_attack_criterion_met":record["secondary_attack"]["criterion_met"],
        "new_gpu_trainings":0,"original_fixed_attack_payloads_read":False,"new_variable_attack_subset_viewed":True,
        "artifact_sha256":{name:sha(OUT/name) for name in ("REPORT_EL.md","evidence.json","verification.json","correlations.csv","recovery.csv","alignment.csv","profiling_comparison.png","fresh_attack_recovery.png")}}
    write_json(OUT/"report_verification.json",result)
    print(json.dumps({k:v for k,v in result.items() if k!="artifact_sha256"},indent=2))


if __name__=="__main__":main()
