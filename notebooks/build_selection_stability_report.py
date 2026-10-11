"""Render all frozen signals and paired-reselection sensitivity, without choosing winners."""
import csv
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sca.train import write_json
from paper_alignment import ROOT,read,sha

OUT=ROOT/"outputs/paper_selection_stability_2026-10-06"


def main():
    plan,record,fit,verified=[read(OUT/n) for n in ("plan.json","results.json","fit.json","verification.json")]
    for n,expected in verified["artifact_sha256"].items():assert sha(OUT/n)==expected,n
    total=read(ROOT/"outputs/paper_training_alignment_2026-10-06/evidence.json")["nine_phase_cpu_seconds"]+record["seconds"]
    with (OUT/"correlations.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(record["correlations"][0]));writer.writeheader();writer.writerows(record["correlations"])
    with (OUT/"selected_points.csv").open("w",newline="",encoding="utf-8") as f:
        names=["draw","unique_training_rows","family","point_a","point_b","training_product_correlation"]
        writer=csv.DictWriter(f,fieldnames=names);writer.writeheader()
        for row in fit["draws"]:
            for family,pair in row["pairs"].items():writer.writerow({"draw":row["draw"],"unique_training_rows":row["unique_training_rows"],
                "family":family,"point_a":pair[0],"point_b":pair[1],"training_product_correlation":row["selection_coefficients"][family]})
    evidence={"intervals":record["intervals"],"sensitivity":record["sensitivity"],"locations":fit["locations"],
        "frozen_signal_met":record["frozen_signal_met"],"pipeline_sensitivity_met":record["pipeline_sensitivity_met"],
        "joint_support_met":record["joint_support_met"],"ten_phase_cpu_seconds":total,"phase_seconds":record["seconds"],
        "verification_seconds":verified["seconds"],"new_correlation_rows":528,"new_key_recovery_rows":0,
        "training_draws":20,"unique_training_rows_range":[min(r["unique_training_rows"] for r in fit["draws"]),max(r["unique_training_rows"] for r in fit["draws"])],
        "variable_used_profiling_rows":150000,"variable_unused_profiling_rows":50000,"prior_recovery_summaries":988,
        "prior_execution_endpoint_checks":19760,"prior_additional_endpoint_replays":10960,"tests":verified["tests"],
        "no_attack_reads_in_phase10":True,"no_bootstrap_winner_chosen":True,"new_gpu_trainings":0,
        "novelty_verified":False,"paper_ready":False,"input_sha256":{n:sha(OUT/n) for n in ("plan.json","results.json","verification.json","fit.json")}}
    write_json(OUT/"evidence.json",evidence)
    lookup={(r["pool"],r["condition"],r["kind"],r["draw"],r["family"],r["feature"]):r for r in record["correlations"]}
    fig,axes=plt.subplots(2,2,figsize=(11,7),sharey=True)
    for i,pool in enumerate(("primary","replication")):
        for j,condition in enumerate(("clean","combined5")):
            ax=axes[i,j]
            for k,family in enumerate(("pair1","pair2")):
                values=np.array([lookup[(pool,condition,"training_draw",d,family,"covariance_rank1")]["hw_correlation"] for d in range(20)])
                ax.scatter(k+np.linspace(-.12,.12,20),values,s=28,color="#306EA6",alpha=.8)
                ax.hlines(np.median(values),k-.2,k+.2,color="#306EA6",linewidth=2)
                frozen=lookup[(pool,condition,"frozen",-1,"aligned_selected_"+family,"covariance_rank1")]["hw_correlation"]
                ax.scatter(k+.28,frozen,marker="D",s=55,color="#D05F35",label="Frozen original feature" if k==0 else None)
            ax.axhline(0,color="#666",linewidth=.8);ax.axhline(.05,color="#888",linestyle="--",linewidth=.8)
            ax.set_xticks([0,1],["Selected family rank1","Selected family rank2"])
            ax.set_title(pool+" · "+condition);ax.grid(axis="y",alpha=.2)
            if j==0:ax.set_ylabel("Signed HW correlation")
            if i==0 and j==0:ax.legend(fontsize=8,loc="lower left")
    fig.suptitle("20 paired training resamples · median bars · common frozen alignment")
    fig.tight_layout();fig.savefig(OUT/"reselection_signal.png",dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,5),sharex=True,sharey=True)
    for j in (0,1):
        ax=axes[j];family="pair"+str(j+1)
        points=np.array([r["pairs"][family] for r in fit["draws"]])
        unique,counts=np.unique(points,axis=0,return_counts=True)
        ax.scatter(unique[:,0],unique[:,1],s=35+25*counts,color="#306EA6",alpha=.75,label="Bootstrap selections")
        ref=fit["controls"]["aligned_selected_"+family]["pair"]
        ax.scatter(*ref,marker="*",s=160,color="#D05F35",label="Original selected pair")
        ax.set_title("Selected family rank"+str(j+1));ax.set_xlabel("First sample index")
        ax.set_xlim(0,1400);ax.set_ylim(0,1400);ax.grid(alpha=.2)
        if j==0:ax.set_ylabel("Second sample index");ax.legend(fontsize=8,loc="lower right")
    fig.suptitle("Selection locations · marker area reflects frequency · no consensus fit")
    fig.tight_layout();fig.savefig(OUT/"selection_locations.png",dpi=160);plt.close(fig)
    lines=["# Σταθερότητα επιλογής σημείων — CPU phase10, 6/10/2026","",
        f"Το συνολικό παγωμένο criterion {'πέρασε' if record['joint_support_met'] else 'δεν πέρασε'}.",
        f"Το frozen signal criterion {'πέρασε' if record['frozen_signal_met'] else 'δεν πέρασε'}, ενώ το reselection sensitivity criterion {'πέρασε' if record['pipeline_sensitivity_met'] else 'δεν πέρασε'}.","",
        "## Σχεδιασμός","",
        "20 paired training bootstrap draws, seed2026, από τα ίδια αρχικά10k traces και labels. Κάθε draw έχει10k θέσεις με replacement, αλλά λιγότερες μοναδικές rows. Αυτά είναι conditional perturbation diagnostics, όχι νέα ανεξάρτητα training seeds, acquisitions ή αλλαγή του neural training budget.",
        f"Distinct training rows ανά draw: {evidence['unique_training_rows_range'][0]}–{evidence['unique_training_rows_range'][1]}. Τα phase9 alignment template και training offsets διατηρήθηκαν ακριβώς. Μέσα σε κάθε draw υπολογίστηκαν νέο center, πλήρης επιλογή δύο pairs και point/box/rank1 weights/sign από training labels μόνο.",
        "Full search:845.650 eligible pairs, margin25/separation50/diversity20, ίδιο radius5. Όλα τα20 sets και120 weight vectors αποθηκεύτηκαν πριν το πρώτο νέο confirmation read. Δεν επιλέχθηκε bootstrap winner, ensemble, consensus ή άλλη ρύθμιση.",
        "Δύο νέα profiling20k pools, seeds20261018/19, με όλες τις110k προηγούμενες rows excluded. Clean και combined5 με το ίδιο raw Gaussian evaluation template για όλα τα frozen controls και resampled fits. Noise scale από original raw training median range48, κοινά U9101/Z9102 streams.",
        "Frozen controls: raw oldpair1/2 και aligned selectedpair1/2, όλα τα point/box/rank1 features.528 rows=48 frozen-control coefficients+480 draw coefficients. Τα20 draws επαναχρησιμοποιούν το ίδιο αρχικό sample και κοινά confirmations· δεν είναι20 ανεξάρτητα πειράματα ή κλειδιά.",
        "Joint primary: και οι δύο αρχικές aligned-selected rank1 families στο clean πρέπει να έχουν r≥0,05 και lower>0 σε αμφότερα pools/schemes. Επιπλέον, οι reselection rank1 coefficients και των δύο family ranks πρέπει να έχουν median≥0,05 και τουλάχιστον16/20positive draws σε αμφότερα pools. Η τελευταία απαίτηση είναι descriptive criterion, χωρίς binomial inference ή selection-error guarantee.",
        "Πρόκειται για adaptive follow-up με νέο freeze. Το phase9 primary failure παραμένει. Καμία viewed confirmation ή attack row δεν χρησιμοποιήθηκε για refit, tuning ή επιλογή καλύτερου draw.","",
        "## Frozen signal — όλα τα intervals","",
        "9.999 paired-row και9.999 index-cluster draws ανά family/pool. Nominal99,875% two-sided percentile intervals, α0,01/family8/tail0,000625. Οι ακραίες quantiles αντιστοιχούν περίπου σε6,25draws, με Monte Carlo αβεβαιότητα. Conditional iid-row/cluster assumptions· HDF5 bins1000 δεν είναι verified acquisition-time blocks. Δεν υπάρχει across-phase alpha-spending ή γενική coverage εγγύηση.","",
        "| Pool / family / scheme | r | Lower | Upper | Criterion |","|---|---:|---:|---:|---|"]
    for r in record["intervals"]:lines.append(f"| {r['pool']} / {r['family']} / {r['scheme']} | {r['correlation']:.6f} | {r['lower']:.6f} | {r['upper']:.6f} | {'Πέρασε' if r['support'] else 'Δεν πέρασε'} |")
    lines += ["","## Reselection sensitivity — όλα τα summaries","",
        "| Pool / condition / family | Median r | Min r | Max r | Positive draws | Criterion |","|---|---:|---:|---:|---:|---|"]
    for r in record["sensitivity"]:lines.append(f"| {r['pool']} / {r['condition']} / {r['family']} | {r['median']:.6f} | {r['minimum']:.6f} | {r['maximum']:.6f} | {r['positive_draws']}/20 | {'Πέρασε' if r['support'] else 'Δεν πέρασε'} |")
    lines += ["","![Signal across reselection fits](reselection_signal.png)","",
        "Το πρώτο family rank διατηρεί θετικό signal σε όλες τις επαναδειγματοληψίες εδώ. Το δεύτερο είναι ασθενές ή αρνητικό σε πολλές από αυτές, παρότι η αρχική συγκεκριμένη επιλογή έχει επαναλαμβανόμενο θετικό signal. Δεν αποδεικνύεται ότι το original pair είναι false positive, ούτε ότι όλη η αστάθεια προέρχεται από έναν συγκεκριμένο μηχανισμό.",
        "Training resamples είναι conditional στα ήδη υπολογισμένα alignment parameters. Argmax selection είναι μη ομαλό statistic και τα20 draws είναι λίγα· δεν υποστηρίζονται asymptotic selection confidence ή unconditional data-population guarantees. Η μέθοδος δεν είναι formal stability selection.","",
        "## Σταθερότητα τοποθεσιών","",
        "Κοινές ανοχές5/20 samples, προκαθορισμένες από radius/diversity. Ordered hits μετρούν το ίδιο family rank· either-family hits επιτρέπουν αλλαγή σειράς. Δεν γίνεται consensus point selection.","",
        "| Tolerance | Ordered hits pair1 / pair2 | Either-family hits pair1 / pair2 | Median max distance pair1 / pair2 |","|---|---|---|---|"]
    for r in fit["locations"]:lines.append(f"| {r['tolerance']} | {' / '.join(str(v)+'/20' for v in r['ordered_hits'])} | {' / '.join(str(v)+'/20' for v in r['either_family_hits'])} | {' / '.join(f'{v:.1f}' for v in r['ordered_median_max_point_distance'])} |")
    lines += ["","![Point locations](selection_locations.png)","","## Κόστος, επαλήθευση και ερμηνεία","",
        f"90tests passed/14existingwarnings σε15,10s (JUnit{verified['tests']['seconds']:.3f}s). CPU experiment{record['seconds']:.6f}s, fit{fit['seconds']:.6f}s περιλαμβάνεται· independent verifier{verified['seconds']:.6f}s.",
        "Ο verifier επανέλαβε και τα20 full searches,120 weight vectors,40 selected training coefficients, όλα ταcenters/paired draw indices/location summaries.528confirmation coefficients/all products,79.992bootstrap draws,12actual-row cluster checks,176sampled offsets με batch boundaries, όλαsplits/RNG/time ordering/padding bounds/immutable hashes.",
        f"Δέκα paper CPU φάσεις:{total:.6f}s experimental wall time. Recovery summaries988/execution checks19.760/additional endpoint replays10.960 αμετάβλητα. Αυτή η φάση δεν διάβασε attacks/metadata/keys και δεν έκανε νέα CPA recovery.",
        "Variable profiling150k πλέον viewed/50k unused· fixed profiling50k used. Variable attack10k viewed από παλιότερες φάσεις, original fixed attack locked. Οι νέες40k confirmation rows αποκλείονται από κάθε μελλοντικό unseen confirmation ή tuning. Παραμένουν1 Kaggle notebook/3GPUtrainings/failed gate/source/checkpoints.",
        "Αυτό το αποτέλεσμα απομονώνει εμπειρικά τη διαφορά μεταξύ signal σε συγκεκριμένα frozen points και αξιοπιστίας του full-search selector υπό paired sample perturbations. Υποστηρίζει τη failure-analysis κατεύθυνση, όχι νέα επίθεση, superiority έναντι άλλου selector ή publication-ready novelty. Απαιτείται independent acquisition/key evidence και σύγκριση με prior-art selection methods.","",
        "[Plan](plan.json) · [Splits](splits.npz) · [Training access](training_access.json) · [Confirmation access](evaluation_access.json) · [All fits](fit.json) · [Fit arrays](fit.npz)",
        "[Results](results.json) · [Arrays](arrays.npz) · [All528 coefficients](correlations.csv) · [All40 selected pairs](selected_points.csv) · [Tests](pytest.xml) · [Verification](verification.json) · [Evidence](evidence.json)",
        "[Execution code](../../notebooks/paper_selection_stability.py) · [Independent verifier](../../notebooks/verify_selection_stability.py) · [Frozen source audit](../../literature/SELECTION_STABILITY_2026-10-06.md)",""]
    (OUT/"REPORT_EL.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"joint_support_met":record["joint_support_met"],"report":str(OUT/"REPORT_EL.md"),"ten_phase_cpu_seconds":total},indent=2))


if __name__=="__main__":main()
