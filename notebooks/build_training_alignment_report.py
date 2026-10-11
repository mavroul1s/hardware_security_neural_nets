"""Report every training-alignment coefficient, frozen primary and actual costs."""
import csv
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sca.train import write_json
from paper_alignment import ROOT,read,sha

OUT=ROOT/"outputs/paper_training_alignment_2026-10-06"


def main():
    plan,record,fit,verified=[read(OUT/n) for n in ("plan.json","results.json","fit.json","verification.json")]
    for n,expected in verified["artifact_sha256"].items():assert sha(OUT/n)==expected,n
    total=read(ROOT/"outputs/paper_precision_replication_2026-10-06/evidence.json")["eight_phase_cpu_seconds"]+record["seconds"]
    lookup={(r["pool"],r["condition"],r["alignment"],r["stage"],r["family"],r["feature"]):r for r in record["correlations"]}
    with (OUT/"correlations.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(record["correlations"][0]));writer.writeheader();writer.writerows(record["correlations"])
    evidence={"intervals":record["intervals"],"support_met":record["support_met"],"nine_phase_cpu_seconds":total,
        "new_correlation_rows":432,"new_key_recovery_rows":0,"phase_seconds":record["seconds"],"verification_seconds":verified["seconds"],
        "prior_recovery_summaries":988,"prior_execution_endpoint_checks":19760,"prior_additional_endpoint_replays":10960,
        "training_selected_pairs":{stage:fit["stages"][stage]["pairs"] for stage in plan["stages"]},
        "tests":verified["tests"],"paper_ready":False,"novelty_verified":False,"no_attack_reads_in_phase9":True,
        "variable_used_profiling_rows":110000,"variable_unused_profiling_rows":90000,"new_gpu_trainings":0,
        "input_sha256":{n:sha(OUT/n) for n in ("plan.json","results.json","verification.json","fit.json")}}
    write_json(OUT/"evidence.json",evidence)
    fig,ax=plt.subplots(figsize=(9,4.4))
    for i,row in enumerate(record["intervals"]):
        color="#306EA6" if row["scheme"]=="paired_rows" else "#D05F35"
        ax.errorbar(i,row["difference"],yerr=[[max(row["difference"]-row["lower"],0)],[max(row["upper"]-row["difference"],0)]],fmt="o",color=color,capsize=5,markersize=7)
    ax.axhline(0,color="#666",linestyle="--",linewidth=1);ax.axhline(.01,color="#888",linestyle=":",linewidth=1)
    ax.set_xticks(range(4),["Primary\nrow bootstrap","Primary\nindex clusters","Replication\nrow bootstrap","Replication\nindex clusters"])
    ax.set_ylabel("Signed HW correlation difference\nAligned fit − raw fit")
    ax.set_title("Frozen primary · old pair1 / rank1 / clean / common raw Gaussian offsets")
    ax.grid(axis="y",alpha=.2);fig.tight_layout();fig.savefig(OUT/"training_alignment_intervals.png",dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(13,7),sharey=True)
    families=plan["families"];xx=np.arange(4)
    for i,pool in enumerate(("primary","replication")):
        for j,condition in enumerate(("clean","combined5","combined10_ood")):
            ax=axes[i,j]
            for stage,displacement,color in (("raw",-.19,"#306EA6"),("aligned_once",.19,"#D05F35")):
                values=[lookup[(pool,condition,"gaussian_raw",stage,f,"covariance_rank1")]["hw_correlation"] for f in families]
                ax.bar(xx+displacement,values,width=.36,color=color,label=stage)
            ax.axhline(0,color="#666",linewidth=.8);ax.set_xticks(xx,["Old 1","Old 2","Selected 1","Selected 2"])
            ax.set_title(pool+" · "+condition);ax.grid(axis="y",alpha=.2)
            if j==0:ax.set_ylabel("Signed HW correlation")
            if i==0 and j==0:ax.legend(fontsize=8)
    fig.suptitle("All rank1 families · common raw-template evaluation offsets · selected points differ by fit")
    fig.tight_layout();fig.savefig(OUT/"training_alignment_families.png",dpi=160);plt.close(fig)
    lines=["# Training-side ευθυγράμμιση — prospective CPU phase9, 6/10/2026","",
        f"Το παγωμένο primary criterion {'πέρασε' if record['support_met'] else 'δεν πέρασε'}. Δημοσιεύονται και οι432 συγκρίσεις· κανένα νέο attack payload ή Kaggle training.","",
        "## Τι ελέγχθηκε","",
        "Η επίσημη variable-key καμπάνια έχει native desynchronization. Τα προηγούμενα feature fits γίνονταν σε unaligned training. Η νέα φάση ελέγχει ένα συγκεκριμένο consistency hypothesis, όχι αιτιώδη απόδειξη ότι το jitter εξηγεί παλιότερες αποτυχίες.",
        "Ίδιο αρχικό training10k. Μία trace-only Gaussian alignment pass με raw unconditional mean/diagonal variance, inclusive±10, tie(absδ,δ), scoring columns20:1380. Άμεση μετατόπιση των original rows κατά−δ, χωρίς επαναληπτικό shifting ή labels στα offsets.",
        "Raw και aligned-once fits έχουν δικά τους training centers και point/box/leading-covariance-rank1 weights. Orientation και επιλογή points από HW των provided training identity labels μόνο. Κανένα mask/key/plaintext/metadata fit input.",
        "Τα δύο παλιά pairs διατηρούνται και στα δύο fits. Κάθε fit επιλέγει επίσης δύο pairs, πλήρες |Pearson(centered product,HW)| search, separation50/diversity20, κοινόmargin25.845.650 eligible candidates ανά stage. Margin25 προστατεύει τα11-sample windows και από training padding και από maximum injected shift10 συν candidate offset10.",
        "Νέα δύο profiling20k pools, seeds20261016/17, όλα τα70k ήδη viewed rows excluded. Κάθε fit αποθηκεύτηκε πριν το πρώτο confirmation read. Τα40k νέα rows είναι τώρα viewed evidence· future unseen confirmation πρέπει να τα αποκλείει.",
        "432 rows=2pools×3conditions×3evaluationalignments×2fits×4pairfamilies×3features. Raw-selected pairs συμπίπτουν εδώ με τα παλιά pairs: κάποιες rows είναι αριθμητικά ίδιες. Ο αριθμός rows δεν μετρά ανεξάρτητα experiments, keys ή devices.",
        "Primary: aligned-once−raw signed HW correlation, old_pair1/covariance_rank1/clean, με ακριβώς ίδια gaussian_raw evaluation offsets. Έτσι ελέγχεται αλλαγή feature fitting (center και weights), ενώ ο evaluation alignment κανόνας παραμένει σταθερός. Δr≥0,01 και lower>0 και στα δύο pools και στα δύο bootstrap schemes.",
        "Refined Gaussian template, νέα points, fixed/no-alignment καιcombined5/OOD αποτελούν προκαθορισμένα secondary controls. Δεν αντικαθιστούν το primary ούτε επιλέγουν επόμενο μοντέλο από viewed attack data.","",
        "## Παγωμένο primary και uncertainty","",
        "9.999 paired-row και9.999 index-cluster draws ανά pool, 200HDF5 bins των1.000 indices. Nominal99,75% two-sided percentile intervals (α0,01/family4). Index bins δεν έχουν επαληθευτεί ως acquisition-time blocks· iid-row/cluster assumptions είναι προσεγγιστικές. Conditional στη fitted direction/realized data και χωρίς συνολικό across-phase alpha-spending για adaptive research.","",
        "| Pool / scheme | Δr | Lower | Upper | Criterion |","|---|---:|---:|---:|---|"]
    for r in record["intervals"]:lines.append(f"| {r['pool']} / {r['scheme']} | {r['difference']:.6f} | {r['lower']:.6f} | {r['upper']:.6f} | {'Πέρασε' if r['support'] else 'Δεν πέρασε'} |")
    lines += ["","![Primary intervals](training_alignment_intervals.png)","","## Training-only points και πλήρεις controls","",
        "| Fit | Old1 | Old2 | Selected1 | Selected2 |","|---|---|---|---|---|"]
    for stage in plan["stages"]:
        pairs=fit["stages"][stage]["pairs"]
        lines.append("| "+stage+" | "+" | ".join("×".join(str(v) for v in pairs[f]) for f in plan["families"])+" |")
    lines += ["","Gaussian raw-template evaluation, rank1 signed correlations. Κάθε κελί δείχνει raw fit / aligned fit:","",
        "| Pool / condition | Old1 | Old2 | Selected1 | Selected2 |","|---|---:|---:|---:|---:|"]
    for pool in ("primary","replication"):
        for condition in ("clean","combined5","combined10_ood"):
            vals=[" / ".join(f"{lookup[(pool,condition,'gaussian_raw',stage,f,'covariance_rank1')]['hw_correlation']:.6f}" for stage in plan["stages"]) for f in plan["families"]]
            lines.append("| "+pool+" / "+condition+" | "+" | ".join(vals)+" |")
    lines += ["","![Families](training_alignment_families.png)","",
        "Τα selected-family comparisons αλλάζουν points και feature fit μαζί, άρα δεν απομονώνουν alignment effect στην ίδια περιοχή. Signed directions ήταν frozen από training: αρνητική confirmation correlation διατηρείται, δεν αναστρέφεται εκ των υστέρων.",
        "Αυτά είναι correlation endpoints με γνωστές profiling labels, όχι constant-key recovery ή νέα πραγματικά attack results. Δεν αποδεικνύουν reliable variable-key attack στοbudget2.000. Παραμένουν τα phase7 attack3/20–4/20, το failed18/20 criterion και τα προηγούμενα primary failures.","",
        "## Επαλήθευση, κόστος και paper claim","",
        f"86tests passed/14existingwarnings σε15,43s (JUnit{verified['tests']['seconds']:.3f}s). CPU experiment{record['seconds']:.6f}s, independent verifier{verified['seconds']:.6f}s. Fit κόστος{fit['seconds']:.6f}s περιλαμβάνεται στο experiment.",
        "Verifier: όλα10.000training offsets,2full selection matrices,64direct individual-product coefficients,24weight vectors καιtraining correlations.432confirmation correlations/all products,39.996bootstrap draws,6actual-row cluster replay checks,528sampled evaluation offsets, splits/RNG/timestamps/hash preservation και feature-padding bounds.",
        f"Εννέα φάσεις experimental CPU wall time{total:.6f}s· verifier/test/report χρόνοι καταγράφονται χωριστά. Recovery summaries988/execution checks19.760/additional endpoint replays10.960 παραμένουν ίδια. Αυτή η φάση δεν κάνει CPA recovery.",
        "Fixed profiling50kused· variableprofiling110kused/90kunused· variableattack10kviewed, originalfixedattacklocked. Παραμένουν1.ipynb/3GPUtrainings/failedCNNgate/source/checkpoints, μηδέν optimizerupdates στη νέα φάση.",
        "Training-side alignment, window averaging καιSVD έχουν prior art. Η συγκριτική εμπειρική μελέτη δεν τεκμηριώνει νέα επίθεση ή publication-ready novelty. Χρειάζεται πλήρης σύγκριση με prior methods και independent acquisition/key evidence για efficacy claim.","",
        "[Plan](plan.json) · [Splits](splits.npz) · [Training access](training_access.json) · [Confirmation access](evaluation_access.json) · [Fit](fit.json) · [Fit arrays](fit.npz)",
        "[Results](results.json) · [All arrays](arrays.npz) · [All432 CSV rows](correlations.csv) · [Tests](pytest.xml) · [Verification](verification.json) · [Evidence](evidence.json)",
        "[Execution code](../../notebooks/paper_training_alignment.py) · [Independent verifier](../../notebooks/verify_training_alignment.py) · [Primary audit](../../literature/TRAINING_ALIGNMENT_2026-10-06.md)",""]
    (OUT/"REPORT_EL.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"support_met":record["support_met"],"report":str(OUT/"REPORT_EL.md"),"nine_phase_cpu_seconds":total},indent=2))


if __name__=="__main__":main()
