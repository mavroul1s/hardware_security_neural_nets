"""Verify the Greek report tables, CSV, evidence and visually checked figures."""
import argparse
import ast
import csv
import json
import re
from sca.train import write_json
from paper_alignment import ROOT,read,sha

OUT=ROOT/"outputs/paper_training_alignment_2026-10-06"


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--plots-visually-checked",action="store_true");args=parser.parse_args()
    assert args.plots_visually_checked,"Inspect both generated figures first"
    plan,record,fit,verified,evidence=[read(OUT/n) for n in ("plan.json","results.json","fit.json","verification.json","evidence.json")]
    for n,expected in verified["artifact_sha256"].items():assert sha(OUT/n)==expected,n
    for n,expected in evidence["input_sha256"].items():assert sha(OUT/n)==expected,n
    assert evidence["support_met"]==verified["support_met"]==record["support_met"]
    assert not evidence["novelty_verified"] and not evidence["paper_ready"] and evidence["no_attack_reads_in_phase9"]
    total=read(ROOT/"outputs/paper_precision_replication_2026-10-06/evidence.json")["eight_phase_cpu_seconds"]+record["seconds"]
    assert evidence["nine_phase_cpu_seconds"]==total
    report=(OUT/"REPORT_EL.md").read_text(encoding="utf-8")
    for r in record["intervals"]:
        line=next(l for l in report.splitlines() if l.startswith("| "+r["pool"]+" / "+r["scheme"]+" |"))
        assert [c.strip() for c in line.strip("|").split("|")][1:]==[f"{r['difference']:.6f}",f"{r['lower']:.6f}",f"{r['upper']:.6f}","Πέρασε" if r["support"] else "Δεν πέρασε"]
    lookup={(r["pool"],r["condition"],r["alignment"],r["stage"],r["family"],r["feature"]):r for r in record["correlations"]}
    table_checks=0
    for pool in ("primary","replication"):
        for condition in ("clean","combined5","combined10_ood"):
            line=next(l for l in report.splitlines() if l.startswith("| "+pool+" / "+condition+" |"))
            expected=[" / ".join(f"{lookup[(pool,condition,'gaussian_raw',s,f,'covariance_rank1')]['hw_correlation']:.6f}" for s in plan["stages"]) for f in plan["families"]]
            assert [c.strip() for c in line.strip("|").split("|")][1:]==expected;table_checks+=8
    for stage in plan["stages"]:
        line=next(l for l in report.splitlines() if l.startswith("| "+stage+" |"))
        assert [c.strip() for c in line.strip("|").split("|")][1:]==["×".join(str(p) for p in fit["stages"][stage]["pairs"][f]) for f in plan["families"]]
    with (OUT/"correlations.csv").open(newline="",encoding="utf-8") as f:csv_rows=list(csv.DictReader(f))
    assert len(csv_rows)==len(record["correlations"])==432
    for row,expected in zip(csv_rows,record["correlations"]):
        assert ast.literal_eval(row.pop("pair"))==expected["pair"]
        assert float(row.pop("hw_correlation"))==expected["hw_correlation"]
        assert row=={k:v for k,v in expected.items() if k not in ("pair","hw_correlation")}
    links=0
    for target in re.findall(r"\]\(([^)]+)\)",report):
        if not target.startswith(("http://","https://")):assert (OUT/target).resolve().is_file(),target;links+=1
    assert f"{total:.6f}s" in report and "86tests passed" in report and "110kused/90kunused" in report
    result={"primary_interval_rows":4,"rank1_control_table_values":table_checks,"all_csv_rows_verified":432,
        "local_links_verified":links,"plots_visually_checked":["training_alignment_intervals.png","training_alignment_families.png"],
        "tests":verified["tests"],"support_met":record["support_met"],"new_gpu_trainings":0,"new_attack_reads":False,
        "artifact_sha256":{n:sha(OUT/n) for n in ("REPORT_EL.md","correlations.csv","evidence.json","verification.json","training_alignment_intervals.png","training_alignment_families.png")}}
    write_json(OUT/"report_verification.json",result);print(json.dumps({k:v for k,v in result.items() if k!="artifact_sha256"},indent=2))


if __name__=="__main__":main()
