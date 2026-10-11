"""Render larger profiling confirmation with all controls, uncertainty and scope limits."""
import csv
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sca.train import write_json
from paper_alignment import ROOT,read,sha
from build_window_regression_report import LABELS

OUT=ROOT/"outputs/paper_precision_replication_2026-10-06"
PREVIOUS=ROOT/"outputs/paper_window_regression_2026-10-06"


def main():
    plan,record,verified=[read(OUT/n) for n in ("plan.json","results.json","verification.json")]
    for name,expected in verified["artifact_sha256"].items():assert sha(OUT/name)==expected
    previous=read(PREVIOUS/"evidence.json")
    total=previous["seven_phase_cpu_seconds"]+record["seconds"]
    lookup={(r["pool"],r["condition"],r["alignment"],r["family"],r["feature"]):r for r in record["correlations"]}
    with (OUT/"correlations.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(record["correlations"][0]));writer.writeheader();writer.writerows(record["correlations"])
    evidence={"intervals":record["intervals"],"support_met":record["support_met"],"eight_phase_cpu_seconds":total,
        "new_correlation_rows":360,"no_new_key_recovery_rows":True,"phase_seconds":record["seconds"],
        "verification_seconds":verified["seconds"],"prior_recovery_summaries":988,"prior_execution_endpoint_checks":19760,
        "prior_additional_endpoint_replays":10960,"tests":verified["tests"],"paper_ready":False,"novelty_verified":False,
        "phase7_primary_failure_preserved":True,"no_attack_reads_in_phase8":True,"new_gpu_trainings":0,
        "input_sha256":{n:sha(OUT/n) for n in ("plan.json","results.json","verification.json")}}
    write_json(OUT/"evidence.json",evidence)
    fig,ax=plt.subplots(figsize=(9,4.4))
    for i,row in enumerate(record["intervals"]):
        color="#306EA6" if row["scheme"]=="paired_rows" else "#D05F35"
        ax.errorbar(i,row["difference"],yerr=[[row["difference"]-row["lower"]],[row["upper"]-row["difference"]]],fmt="o",color=color,capsize=5,markersize=7)
    ax.axhline(0,color="#666",linestyle="--",linewidth=1)
    ax.axhline(.01,color="#888",linestyle=":",linewidth=1)
    ax.set_xticks(np.arange(4),["Primary\nrow bootstrap","Primary\nindex clusters","Replication\nrow bootstrap","Replication\nindex clusters"])
    ax.set_ylabel("Signed correlation difference: ridge noise − clean")
    ax.set_title("Variable-key profiling · two fresh 20k pools · nominal 99.75% intervals")
    ax.grid(axis="y",alpha=.2);fig.tight_layout();fig.savefig(OUT/"precision_intervals.png",dpi=160);plt.close(fig)
    lines=["# Μεγαλύτερη prospective επιβεβαίωση χωρίς νέο fit — 6/10/2026","",
        f"Το προκαθορισμένο phase8 criterion {'πέρασε' if record['support_met'] else 'δεν πέρασε'} και στα δύο νέα variable-key profiling20k pools.",
        "Τα βάρη/radius/points/normalization/σ/methods παρέμειναν ακριβώς ίδια μεphase7. Το παλιότερο primary failure και το χαμηλό attack SR δεν αλλάζουν.","",
        "## Σχεδιασμός και ερμηνεία","",
        "Η follow-up φάση σχεδιάστηκε μετά τα θετικά αλλά imprecise profiling contrasts τηςphase7. Αιτία ήταν η εκτίμηση precision, όχι επιλογή μοντέλου/υπερπαραμέτρων από attack αποτελέσματα.",
        "Δύο20k pools, seeds20261014/15, από unused variable profiling rows, disjoint από κάθε παλιότερη training/validation/confirmation row. Το training budget παραμένει10k· δεν έγινε refit ή νέο model seed.",
        "Κάθε νέο plan/split/hash πάγωσε πριν payload access. Κανένα metadata/attack/key read σε αυτή τη φάση. Same provided HW labels μόνο για evaluation της signed correlation.",
        "Primary pair1/combined5/Gaussian: Δr noise ridge−clean≥0,01 και positive lower bound και στα δύο pools, υπό αμφότερα bootstrap schemes. Τα υπόλοιπα360 rows δημοσιεύονται ως controls/descriptive evidence.",
        "9.999 paired-row και9.999 paired-cluster draws ανά pool. Clusters=200 bins των1.000 συνεχόμενων HDF5 profiling indices· επιλεγμένες rows≈100 ανά bin. Resampling whole index bins, unequal counts retained μέσω sufficient moments.",
        "Two-sided percentile99,75% intervals: nominalα0,01/family4/tail0,00125. Conditional στη fixed fitted direction/realized corruption, με iid-row ή iid-index-cluster assumptions. Δεν ελέγχθηκε η πραγματική acquisition-time αντιστοίχιση ή η ανεξαρτησία blocks.",
        "Η επιλογή μεγαλύτερου follow-up μετά τα προηγούμενα CI είναι adaptive study planning. Δεν διατηρήθηκε προκαθορισμένο συνολικό alpha-spending για όλη την ερευνητική ακολουθία· δεν ισχυριζόμαστε overall optional-stopping-controlled significance. Τοphase7primary παραμένειfailed.","",
        "## Όλα τα prospective intervals","",
        "| Pool / scheme | Δr | Lower | Upper | Criterion |","|---|---:|---:|---:|---|"]
    for r in record["intervals"]:
        lines.append(f"| {r['pool']} / {r['scheme']} | {r['difference']:.6f} | {r['lower']:.6f} | {r['upper']:.6f} | {'Πέρασε' if r['support'] else 'Δεν πέρασε'} |")
    lines += ["","![Intervals](precision_intervals.png)","","## Τα απλά controls διατηρούνται","",
        "Pair1/combined5/Gaussian, signed HW correlation:","",
        "| Pool | "+" | ".join(LABELS[f] for f in plan["features"])+" |","|---|"+"---:|"*6]
    for pool in ("primary","replication"):
        vals=[lookup[(pool,"combined5","gaussian_template","pair1",f)]["hw_correlation"] for f in plan["features"]]
        lines.append("| "+pool+" | "+" | ".join(f"{v:.6f}" for v in vals)+" |")
    lines += ["",
        "Η noise correction βελτιώνει την clean ridge, αλλά box averaging καιrank1 παραμένουν ισχυρότερα εδώ. Δεν αποδείχθηκε superiority της προτεινόμενης correction έναντι φθηνότερων baselines.",
        "Τα πραγματικά variable attack αποτελέσματα τηςphase7 παραμένουν3/20 γιαnoise ridge και4/20 γιαrank1 στοcombined5/pair1, με18/20 criterionfailed. Αυτή η φάση μετρά profiling signal, όχι νέο key recovery. Καλύτερη συσχέτιση δεν ισοδυναμεί με αξιόπιστη ανάκτηση μέσα στοbudget2.000.",
        "Same campaign, original training και shared RNG streams· disjoint row pools δεν είναι νέες συσκευές/κλειδιά ή ανεξάρτητες acquisition campaigns. Δεν ελέγχεται causal key-change effect. Τα νέα40k rows είναι πλέον viewed evidence, αποκλείονται από future unseen confirmation/tuning.","",
        "## Επαλήθευση, κόστος και συνέχεια προς paper","",
        f"82tests passed/14existingwarnings· JUnit{verified['tests']['seconds']:.3f}s. Phase8 CPU{record['seconds']:.6f}s, independent verifier{verified['seconds']:.6f}s.",
        "Verifier:360corr rows/all products,39.996bootstrap draws,6sampled cluster draws με actual duplicated row lists,720sampled alignment offsets με batch-boundary checks, όλα τα moments/splits/RNG και immutable weights.",
        f"Οκτώ paper CPU φάσεις:{total:.6f}s experimental wall time. Recovery summaries988/executionendpoints19.760/additionalreplays10.960 δεν αυξάνονται από αυτή τη profiling-only φάση. Οι νέες δύοφάσεις προσθέτουν1.260correlation comparisons και540recovery summaries, όχι ανεξάρτητα κλειδιά/συσκευές.",
        "Παραμένουν1 Kaggle notebook/3GPU trainings/failed CNN gate/source/checkpoints. Fixed profiling50k used, variableprofiling70k used/130k unused· variableattack10k viewed απόphase5/7, originalfixedattacklocked.",
        "Η υποψήφια συνεισφορά περιορίζεται σε prospectively replicated robustness/failure boundaries και reproducible analytical baseline. Averaging, regression και input-noise regularization είναι γνωστά. Απαιτείται full-text novelty comparison και independently acquired/key evidence πριν publication claim.","",
        "[Plan](plan.json) · [Splits](splits.npz) · [Access](evaluation_access.json) · [Results](results.json) · [Arrays](arrays.npz) · [All CSV rows](correlations.csv)",
        "[Tests](pytest.xml) · [Verification](verification.json) · [Evidence](evidence.json) · [Phase7 με όλα τα recovery failures](../paper_window_regression_2026-10-06/REPORT_EL.md)",
        "[Execution code](../../notebooks/paper_precision_replication.py) · [Independent verifier](../../notebooks/verify_precision_replication.py) · [Primary bibliography](../../literature/WINDOW_REGRESSION_2026-10-06.md)",""]
    (OUT/"REPORT_EL.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"support_met":record["support_met"],"report":str(OUT/"REPORT_EL.md")},indent=2))


if __name__=="__main__":main()
