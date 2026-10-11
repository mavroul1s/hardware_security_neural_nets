"""Verify phase10 report tables, all CSVs, figure review and recorded costs."""
import argparse
import ast
import csv
import json
import re
from sca.train import write_json
from paper_alignment import ROOT,read,sha

OUT=ROOT/"outputs/paper_selection_stability_2026-10-06"


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--plots-visually-checked",action="store_true");args=parser.parse_args()
    assert args.plots_visually_checked,"Inspect both generated figures first"
    record,fit,verified,evidence=[read(OUT/n) for n in ("results.json","fit.json","verification.json","evidence.json")]
    for n,expected in verified["artifact_sha256"].items():assert sha(OUT/n)==expected,n
    for n,expected in evidence["input_sha256"].items():assert sha(OUT/n)==expected,n
    assert evidence["frozen_signal_met"]==verified["frozen_signal_met"]==record["frozen_signal_met"]
    assert evidence["pipeline_sensitivity_met"]==verified["pipeline_sensitivity_met"]==record["pipeline_sensitivity_met"]
    assert evidence["joint_support_met"]==verified["joint_support_met"]==record["joint_support_met"]
    assert not evidence["novelty_verified"] and not evidence["paper_ready"] and evidence["no_attack_reads_in_phase10"]
    total=read(ROOT/"outputs/paper_training_alignment_2026-10-06/evidence.json")["nine_phase_cpu_seconds"]+record["seconds"]
    assert evidence["ten_phase_cpu_seconds"]==total
    report=(OUT/"REPORT_EL.md").read_text(encoding="utf-8")
    for r in record["intervals"]:
        label=r["pool"]+" / "+r["family"]+" / "+r["scheme"]
        line=next(l for l in report.splitlines() if l.startswith("| "+label+" |"))
        assert [c.strip() for c in line.strip("|").split("|")][1:]==[f"{r['correlation']:.6f}",f"{r['lower']:.6f}",f"{r['upper']:.6f}","Πέρασε" if r["support"] else "Δεν πέρασε"]
    for r in record["sensitivity"]:
        label=r["pool"]+" / "+r["condition"]+" / "+r["family"]
        line=next(l for l in report.splitlines() if l.startswith("| "+label+" |"))
        assert [c.strip() for c in line.strip("|").split("|")][1:]==[f"{r['median']:.6f}",f"{r['minimum']:.6f}",f"{r['maximum']:.6f}",str(r["positive_draws"])+"/20","Πέρασε" if r["support"] else "Δεν πέρασε"]
    for r in fit["locations"]:
        line=next(l for l in report.splitlines() if l.startswith("| "+str(r["tolerance"])+" |"))
        expected=[" / ".join(str(v)+"/20" for v in r[k]) for k in ("ordered_hits","either_family_hits")]+[" / ".join(f"{v:.1f}" for v in r["ordered_median_max_point_distance"])]
        assert [c.strip() for c in line.strip("|").split("|")][1:]==expected
    with (OUT/"correlations.csv").open(newline="",encoding="utf-8") as f:csv_rows=list(csv.DictReader(f))
    assert len(csv_rows)==len(record["correlations"])==528
    for row,expected in zip(csv_rows,record["correlations"]):
        assert ast.literal_eval(row.pop("pair"))==expected["pair"]
        assert int(row.pop("draw"))==expected["draw"]
        assert float(row.pop("hw_correlation"))==expected["hw_correlation"]
        assert row=={k:v for k,v in expected.items() if k not in ("pair","draw","hw_correlation")}
    with (OUT/"selected_points.csv").open(newline="",encoding="utf-8") as f:point_rows=list(csv.DictReader(f))
    assert len(point_rows)==40
    for row in point_rows:
        source=fit["draws"][int(row["draw"])];family=row["family"]
        assert int(row["unique_training_rows"])==source["unique_training_rows"]
        assert [int(row["point_a"]),int(row["point_b"])]==source["pairs"][family]
        assert float(row["training_product_correlation"])==source["selection_coefficients"][family]
    links=0
    for target in re.findall(r"\]\(([^)]+)\)",report):
        if not target.startswith(("http://","https://")):assert (OUT/target).resolve().is_file(),target;links+=1
    assert f"{total:.6f}s" in report and "90tests passed" in report and "150k πλέον viewed/50k unused" in report
    result={"primary_interval_rows":8,"sensitivity_rows":8,"location_rows":2,"all_csv_rows_verified":528,
        "all_selected_pairs_csv_rows_verified":40,"local_links_verified":links,
        "plots_visually_checked":["reselection_signal.png","selection_locations.png"],"tests":verified["tests"],
        "frozen_signal_met":record["frozen_signal_met"],"pipeline_sensitivity_met":record["pipeline_sensitivity_met"],
        "joint_support_met":record["joint_support_met"],"new_gpu_trainings":0,"new_attack_reads":False,
        "artifact_sha256":{n:sha(OUT/n) for n in ("REPORT_EL.md","correlations.csv","selected_points.csv","evidence.json","verification.json","reselection_signal.png","selection_locations.png")}}
    write_json(OUT/"report_verification.json",result);print(json.dumps({k:v for k,v in result.items() if k!="artifact_sha256"},indent=2))


if __name__=="__main__":main()
