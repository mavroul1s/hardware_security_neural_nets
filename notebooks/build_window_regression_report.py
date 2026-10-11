"""Generate phase7 research tables, figures and candid Greek report from verified data."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sca.train import write_json
from paper_alignment import ROOT, read, sha

OUT = ROOT / "outputs/paper_window_regression_2026-10-06"
LABELS = {"point":"Σημείο", "box_product":"Box", "diagonal_products":"Diagonal",
          "covariance_rank1":"Rank1", "ridge_clean":"Ridge clean", "ridge_noise":"Ridge noise"}


def main():
    plan, record, verified = [read(OUT / name) for name in ("plan.json", "results.json", "verification.json")]
    for name, expected in verified["artifact_sha256"].items(): assert sha(OUT/name)==expected
    lookup = {(r["campaign"],r["pool"],r["condition"],r["alignment"],r["family"],r["feature"]):r for r in record["correlations"]}
    recovery = {(r["campaign"],r["pool"],r["condition"],r["alignment"],r["family"],r["feature"]):r for r in record["recoveries"]}
    for name, rows in (("correlations.csv",record["correlations"]),("recovery.csv",record["recoveries"]),("alignment.csv",record["alignment"])):
        with (OUT/name).open("w",newline="",encoding="utf-8") as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    prior=read(ROOT/"outputs/paper_selection_audit_2026-10-06/evidence.json")
    total_seconds=prior["six_phase_cpu_seconds"]+record["seconds"]
    evidence={"primary":record["primary"],"primary_support_met":record["primary_support_met"],
        "secondary_attack":record["secondary_attack"],"seven_phase_cpu_seconds":total_seconds,
        "new_correlation_rows":900,"new_recovery_summaries":540,"new_execution_endpoints":10800,
        "seven_phase_recovery_summaries":448+540,"seven_phase_execution_endpoints":8960+10800,
        "seven_phase_additional_replays":160+verified["additional_endpoint_replays"],
        "tests":verified["tests"],"paper_ready":False,"novelty_verified":False,
        "original_fixed_attack_payloads_read":False,"new_variable_attack_rows":5000,
        "variable_attack_key_previously_viewed":True,"new_gpu_trainings":0,
        "phase_seconds":record["seconds"],"verification_seconds":verified["seconds"],
        "source_sha256":record["production_source_sha256"],
        "input_sha256":{name:sha(OUT/name) for name in ("plan.json","fit.json","results.json","verification.json")}}
    write_json(OUT/"evidence.json",evidence)
    features=plan["features"]
    fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True,sharey=True)
    colors=["#5C6670","#8998A6","#AEC3D0","#847AAE","#306EA6","#D05F35"]
    for ax,(campaign,pool) in zip(axes.ravel(),(("fixed","primary"),("fixed","replication"),("variable","primary"),("variable","replication"))):
        vals=[lookup[(campaign,pool,"combined5","gaussian_template","pair1",f)]["hw_correlation"] for f in features]
        ax.bar(np.arange(6),vals,color=colors)
        ax.axhline(0,color="#777",linewidth=.7)
        ax.set_title(campaign+" / "+pool);ax.set_xticks(np.arange(6),["Point","Box","Diag","Rank1","Ridge\nclean","Ridge\nnoise"])
        ax.grid(axis="y",alpha=.2);ax.set_axisbelow(True)
    axes[0,0].set_ylabel("Signed HW correlation");axes[1,0].set_ylabel("Signed HW correlation")
    fig.suptitle("Frozen pair1 · combined5 · Gaussian alignment · fresh profiling pools")
    fig.tight_layout();fig.savefig(OUT/"profiling_comparison.png",dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
    conditions=["clean","noise5","shift5","combined5","combined10_ood"]
    for ax,family in zip(axes,("pair1","pair2")):
        for feature,color in zip(features,colors):
            vals=[recovery[("variable","fresh_attack",c,"gaussian_template",family,feature)]["sr_at_budget"] for c in conditions]
            ax.plot(np.arange(5),vals,"o-",label=LABELS[feature],color=color,linewidth=1.5,markersize=4)
        ax.set_title("Variable-key fresh attack / "+family);ax.set_xticks(np.arange(5),["Clean","Noise","Shift","Combined","OOD"])
        ax.set_ylim(-.03,1.03);ax.grid(alpha=.2)
    axes[0].set_ylabel("SR@2000 (20 overlapping orders)");axes[1].legend(fontsize=8,loc="best")
    fig.tight_layout();fig.savefig(OUT/"fresh_attack_recovery.png",dpi=160);plt.close(fig)
    lines=["# Παράθυρα δεύτερης τάξης και αναλυτική noise-aware regression — 6/10/2026","",
        f"Πραγματική CPU εκτέλεση:900 correlation comparisons και540 recovery summaries, {record['seconds']:.6f}s.",
        "Είναι factorial rows, όχι900 ανεξάρτητα πειράματα/κλειδιά. Όλα τα fits και thresholds πάγωσαν πριν τα νέα δεδομένα.",
        f"Το primary criterion {'πέρασε' if record['primary_support_met'] else 'δεν πέρασε'}· το προκαθορισμένο secondary attack criterion {'πέρασε' if record['secondary_attack']['criterion_met'] else 'δεν πέρασε'}.",
        "Paper readiness και novelty παραμένουν ανεπιβεβαίωτα. Δεν αρκεί να διαλέξουμε το καλύτερο row για publication claim.","",
        "## Πρωτόκολλο και πληροφορία","",
        "Αρχικό10k training ανά campaign, ίδιοι frozen point centers, radius5/11samples, ένα closed-form fit/μέθοδο· κανένα optimizer/GPU training.",
        "Οι έξι μέθοδοι είναι point, product δύο box averages, average11 diagonal products, rank1 SVD της target covariance, ridge clean και ridge με analytic added-noise covariance.",
        "Τα train labels μετατρέπονται σε HW. Δεν χρησιμοποιούνται masks/keys/plaintext για επιλογή points/weights ή alignment. Window variants βλέπουν22 samples έναντι2 του point· δεν έχουν ίση capacity ή label information με CNN.",
        "Τα121 product features standardized από το training μόνο· ίδιο ridge0,01 και στις δύο ridge λύσεις. Η noise-aware λύση χρησιμοποιεί σraw1,3/fixed και4,8/variable, καθορισμένο από0,1×median training range.",
        "Πέντε συνθήκες clean/noise5/shift5/combined5/OOD και fixed/Gaussian/SAD mean alignment. Same U/Z/orders μέσα στα pools. Noise-only και shift-only είναι CPU evaluations, όχι πρόσθετα neural trainings.",
        "Δύο disjoint fresh profiling5k pools ανά campaign. Fresh variable attack5k αποκλείει τις προηγούμενες5k attack rows: νέο trace subset με το ίδιο ήδη εξετασμένο κλειδί/συσκευή/καμπάνια. Κανένα attack-based selection, όλα τα fits παγωμένα πριν οποιοδήποτε holdout.",
        "Τα variable profiling keys ποικίλλουν: εκεί μετράμε correlation, χωρίς fabricated constant-key CPA. CPA μόνο στα πραγματικά constant-key fixed profiling και variable fresh attack pools. Το original fixed-key final attack παραμένει locked.","",
        "## Primary: noise-aware έναντι clean ridge","",
        "Pair1/combined5/Gaussian, signed correlation (orientation από training). Support απαιτεί και στα τέσσερα profiling pools Δr≥0,01 και lower bound>0.",
        "1.999 paired row bootstraps ανά pool· two-sided percentile intervals98,75% (Bonferroni family4, tail0,00625). Είναι approximate conditional intervals υπό iid-row assumption, χωρίς exact coverage ή training/acquisition variability.","",
        "| Campaign / pool | Δr | Lower | Upper | Criterion |","|---|---:|---:|---:|---|"]
    for r in record["primary"]:
        lines.append(f"| {r['campaign']} / {r['pool']} | {r['difference']:.6f} | {r['lower']:.6f} | {r['upper']:.6f} | {'Πέρασε' if r['support'] else 'Δεν πέρασε'} |")
    lines += ["","![Profiling](profiling_comparison.png)","","## Όλες οι μέθοδοι: primary profiling endpoint","",
        "| Campaign / pool | "+" | ".join(LABELS[f] for f in features)+" |",
        "|---|"+"---:|"*6]
    for campaign,pool in (("fixed","primary"),("fixed","replication"),("variable","primary"),("variable","replication")):
        vals=[lookup[(campaign,pool,"combined5","gaussian_template","pair1",f)]["hw_correlation"] for f in features]
        lines.append("| "+campaign+" / "+pool+" | "+" | ".join(f"{v:.6f}" for v in vals)+" |")
    lines += ["","## Ανάκτηση πραγματικού byte: Gaussian alignment","",
        "Κάθε cell δίνει pair1/pair2 successes από20 κοινά, επικαλυπτόμενα trace orders, budget2.000. Rank0best, conservative ties1e−12. Οι20 orders δεν είναι20 ανεξάρτητα keys/training seeds.",""]
    for campaign,pool in (("fixed","primary"),("fixed","replication"),("variable","fresh_attack")):
        lines += ["### "+campaign+" / "+pool,"","| Feature | Clean | Noise5 | Shift5 | Combined5 | OOD |","|---|---|---|---|---|---|"]
        for feature in features:
            cells=[" / ".join(f"{round(recovery[(campaign,pool,c,'gaussian_template',family,feature)]['sr_at_budget']*20)}/20" for family in ("pair1","pair2")) for c in conditions]
            lines.append("| "+LABELS[feature]+" | "+" | ".join(cells)+" |")
        lines.append("")
    lines += ["![Fresh attack](fresh_attack_recovery.png)","",
        f"Secondary criterion αφορά ridge_noise/Gaussian/pair1/combined5: SR{round(record['secondary_attack']['ridge_noise_sr']*20)}/20, point{round(record['secondary_attack']['point_sr']*20)}/20, ridge clean{round(record['secondary_attack']['ridge_clean_sr']*20)}/20. Απαιτεί18/20 και τουλάχιστον2/20 βελτίωση από καθένα. Δεν επιλέγεται άλλη μέθοδος μετά την αξιολόγηση.","",
        "## Τι αποδεικνύει και τι μένει ανοικτό","",
        "Στο fixed-key OOD/Gaussian, box/rank1/ridge noise έδωσαν20/20 και στα δύο pairs, σε αμφότερα τα νέα pools. Point:10/20,3/20 και7/20,3/20· clean ridge:8/20,2/20 και13/20,0/20. Αυτό είναι σημαντικό secondary robustness εύρημα για γνωστά window baselines, όχι προαποφασισμένο primary success ή superiority της noise ridge από box/rank1.",
        "Στο variable-key fresh attack/Gaussian/combined5, rank1 έδωσε4/20 στοpair1 έναντι noise ridge3/20 και clean ridge/point0/20. Κανένα δεν φτάνει18/20· pair2όλες0/20. Η νέα correction δεν είναι ο γενικός winner και δεν αποδεικνύεται zero leakage από failures.",
        "Το analytic covariance increment N=σ²(C_A⊗I+I⊗C_B)+σ⁴I είναι exact conditional identity για disjoint windows και ανεξάρτητο zero-mean added noise. Δεν χρειάζεται Gaussian assumption για την identity. Οι9 νέες synthetic/unit checks ελέγχουν τον κώδικα, όχι φυσική efficacy.",
        "Η identity δεν αφαιρεί native noise, colored noise, local elastic jitter ή masking. Alignment offsets επιλέγονται από noisy waveforms· η effective noise μετά την επιλογή τους δεν ακολουθεί την ίδια iid assumption. Το known-σ fit εξετάζει το συγκεκριμένο artificial stress, δεν υποθέτει estimator του άγνωστου physical σ.",
        "Same relative noise factors σημαίνουν διαφορετικές raw amplitudes μεταξύ campaigns, όχι causal effect μόνο του key. Two row pools μοιράζονται training και acquisition campaign. Το variable attack key απουσιάζει από training full keys, αλλά είχε ήδη εξεταστεί στην παλιότερη φάση.",
        "Averaging/window integration/SVD/regression/noise regularization έχουν prior art. Δεν έχει ολοκληρωθεί η full-text σύγκριση με orthogonal regression/scheme-aware modeling. Άρα ακόμη και θετικό endpoint δεν τεκμηριώνει novel attack ή έτοιμο paper.",
        "Ένας υποψήφιος paper άξονας είναι το reproducible comparison της analytically noise-regularized quadratic extraction, μαζί με leakage cancellation, cross-campaign failure boundaries και prospective replications. Απαιτεί verified novelty, ισχυρότερα independently acquired/key datasets και επαρκή controls πριν υποβολή.","",
        "## Επαλήθευση, κόστος και αρχεία","",
        f"79tests passed/14 existing warnings· JUnit{verified['tests']['seconds']:.3f}s. Independent replay{verified['seconds']:.6f}s:24 weight vectors/all fit moments,900 correlation rows,10.800 επιπλέον endpoint replays,7.996 bootstrap draws,1.600 sampled alignment offsets και όλα τα splits/RNG.",
        "Δεν έγινε independent full-prefix replay όλων των CPA curves· τα endpoints επανυπολογίστηκαν άμεσα και τα αποθηκευμένα ranks ελέγχθηκαν για GE/SR/sustained thresholds. Οι replays δεν είναι πρόσθετο physical evidence.",
        f"Επτά CPU φάσεις:{total_seconds:.6f}s καταγεγραμμένου experimental wall time (δεν περιλαμβάνει verifiers/tests/literature/report writing). Recovery summaries988, execution endpoint checks19.760, additional endpoint replays10.960. Αυτά είναι computational counts, όχι ανεξάρτητες φυσικές επαναλήψεις.",
        "GPU νέα0, συνολικά3full trainings, ένα Kaggle notebook· failed gate/source/checkpoints/packets αμετάβλητα. Fixed profiling50k πλέον viewed/allocated, variable profiling30k, variable attack10k. Καμία viewed row δεν γίνεται future unseen confirmation.","",
        "[Frozen plan](plan.json) · [Splits](splits.npz) · [Fit](fit.json) · [Fit arrays](fit.npz) · [Access log](evaluation_access.json) · [Results](results.json) · [Arrays](arrays.npz)",
        "[Correlation CSV](correlations.csv) · [Recovery CSV](recovery.csv) · [Alignment CSV](alignment.csv) · [Tests](pytest.xml) · [Verification](verification.json) · [Evidence](evidence.json)",
        "[Κώδικας](../../notebooks/paper_window_regression.py) · [Independent verifier](../../notebooks/verify_window_regression.py) · [Βιβλιογραφία/παραγωγή identity](../../literature/WINDOW_REGRESSION_2026-10-06.md)",
        "[Πρόσθετος primary έλεγχος και access gaps](../../literature/WINDOW_REGRESSION_PRIOR_ART_FOLLOWUP_2026-10-06.md)",""]
    (OUT/"REPORT_EL.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"primary_support_met":record["primary_support_met"],"secondary_attack":record["secondary_attack"],"report":str(OUT/"REPORT_EL.md")},indent=2))


if __name__=="__main__":main()
