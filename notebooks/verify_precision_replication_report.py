"""Verify larger confirmation report and reviewed plot without changing experiment evidence."""
import argparse
import csv
import json
import re
from sca.train import write_json
from paper_alignment import ROOT,read,sha
from build_precision_replication_report import OUT,PREVIOUS,LABELS


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--plot-visually-checked",action="store_true");args=parser.parse_args()
    if not args.plot_visually_checked:raise RuntimeError("Inspect precision_intervals.png first")
    report=(OUT/"REPORT_EL.md").read_text(encoding="utf-8")
    plan,record,verified,evidence=[read(OUT/n) for n in ("plan.json","results.json","verification.json","evidence.json")]
    for name,expected in evidence["input_sha256"].items():assert sha(OUT/name)==expected
    for name,expected in verified["artifact_sha256"].items():assert sha(OUT/name)==expected
    for row in record["intervals"]:
        label=row["pool"]+" / "+row["scheme"]
        line=next(l for l in report.splitlines() if l.startswith("| "+label+" |"))
        assert [c.strip() for c in line.strip("|").split("|")]==[label,f"{row['difference']:.6f}",f"{row['lower']:.6f}",f"{row['upper']:.6f}","Πέρασε" if row["support"] else "Δεν πέρασε"]
    with (OUT/"correlations.csv").open(encoding="utf-8",newline="") as f:rows=list(csv.DictReader(f))
    assert len(rows)==360
    for actual,expected in zip(rows,record["correlations"]):assert actual=={k:str(v) for k,v in expected.items()}
    lookup={(r["pool"],r["condition"],r["alignment"],r["family"],r["feature"]):r for r in record["correlations"]}
    for pool in ("primary","replication"):
        line=next(l for l in report.splitlines() if l.startswith("| "+pool+" |"))
        expected=[f"{lookup[(pool,'combined5','gaussian_template','pair1',f)]['hw_correlation']:.6f}" for f in plan["features"]]
        assert [c.strip() for c in line.strip("|").split("|")][1:]==expected
    assert evidence["eight_phase_cpu_seconds"]==read(PREVIOUS/"evidence.json")["seven_phase_cpu_seconds"]+record["seconds"]
    assert f"{record['seconds']:.6f}s" in report and f"{evidence['eight_phase_cpu_seconds']:.6f}s" in report
    assert evidence["phase7_primary_failure_preserved"] and evidence["no_new_key_recovery_rows"] and evidence["no_attack_reads_in_phase8"]
    assert evidence["tests"]["tests"]==82 and not evidence["paper_ready"] and not evidence["novelty_verified"]
    links=0
    for target in re.findall(r"\]\(([^)]+)\)",report):
        if not target.startswith(("http://","https://")):assert (OUT/target).resolve().is_file(),target;links+=1
    result={"report_tables_verified":True,"csv_rows_verified":360,"local_links_verified":links,"plot_visually_checked":True,
        "costs_verified":True,"support_met":record["support_met"],"tests":verified["tests"],"new_attack_reads":False,"new_gpu_trainings":0,
        "artifact_sha256":{n:sha(OUT/n) for n in ("REPORT_EL.md","evidence.json","verification.json","correlations.csv","precision_intervals.png")}}
    write_json(OUT/"report_verification.json",result);print(json.dumps({k:v for k,v in result.items() if k!="artifact_sha256"},indent=2))


if __name__=="__main__":main()
