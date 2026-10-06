"""Build the Greek selection-diagnostic report using verified frozen results."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sca.train import write_json
from paper_alignment import ROOT, read, sha

OUT = ROOT / "outputs/paper_selection_audit_2026-10-06"


def main():
    plan, record, verified = (read(OUT / name) for name in ("plan.json", "results.json", "verification.json"))
    for name, expected in verified["artifact_sha256"].items():
        assert sha(OUT / name) == expected
    rows = record["results"]
    with np.load(OUT / "arrays.npz", allow_pickle=False) as arrays:
        maxima = [arrays[campaign + "__null_maxima"] for campaign in ("fixed", "variable")]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.9))
    axes[0].boxplot(maxima, positions=[0, 1], widths=.35, patch_artist=True,
                   boxprops={"facecolor": "#cbd5e1"}, medianprops={"color": "#334155"})
    for family, color, marker, delta in (("pair1", "#2463a5", "o", -.09), ("pair2", "#c97915", "s", .09)):
        selected = [row for row in rows if row["family"] == family]
        axes[0].scatter([i + delta for i in range(2)], [abs(row["training_correlation"]) for row in selected],
                        color=color, marker=marker, label="Observed " + family, zorder=3)
    axes[0].set_xticks([0, 1], ["Fixed key: 211,575 pairs", "Variable key: 885,115 pairs"], fontsize=9)
    axes[0].set_ylabel("Absolute training correlation")
    axes[0].set_title("Boxes: 99 shuffled-label full-search maxima", fontsize=10)
    axes[0].legend(frameon=False, fontsize=9)
    indices = np.arange(4)
    axes[1].bar(indices - .17, [abs(row["training_correlation"]) for row in rows], width=.34, color="#94a3b8", label="Training10k")
    axes[1].bar(indices + .17, [row["signed_confirmation_correlation"] for row in rows], width=.34, color="#2463a5", label="Fresh profiling5k")
    axes[1].set_xticks(indices, ["Fixed\npair1", "Fixed\npair2", "Variable\npair1", "Variable\npair2"])
    axes[1].set_ylabel("Correlation in frozen training direction")
    axes[1].set_title("Four fixed-pair tests; direction locked before confirmation", fontsize=10)
    for index, row in enumerate(rows):
        axes[1].text(index, max(abs(row["training_correlation"]), row["signed_confirmation_correlation"]) + .008,
                     f"p adj={row['confirmation_bonferroni_p']:.3f}", ha="center", fontsize=8)
    axes[1].legend(frameon=False, fontsize=9, loc="upper right")
    for ax in axes:
        ax.set_ylim(0, .26)
        ax.grid(axis="y", alpha=.2)
        ax.set_axisbelow(True)
    fig.suptitle("Frozen-point replication and label-permutation diagnostic\nConditional statistics; exchangeable-label null, no new attack evaluation", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, .89))
    fig.savefig(OUT / "selection_replication.png", dpi=170)
    plt.close(fig)
    table = ["| Campaign / pair | Training r | Fresh confirmation r | Train max-null tail | Confirmation p adjusted | Criterion |",
             "|---|---:|---:|---:|---:|---|"]
    for row in rows:
        table.append(f"| {row['campaign']} / {row['family']} | {row['training_correlation']:.6f} | "
            f"{row['confirmation_correlation']:.6f} | {row['training_global_max_null_tail']:.2f} | "
            f"{row['confirmation_bonferroni_p']:.3f} | {'Πέρασε' if row['signed_signal_replicates'] else 'Δεν πέρασε'} |")
    five_seconds = read(ROOT / "outputs/paper_variable_campaign_2026-10-05/evidence.json")["five_phase_cpu_seconds"]
    report = f"""# Σταθερότητα επιλεγμένου σήματος και permutation audit — 6/10/2026

Τρία από τα τέσσερα παγωμένα ζεύγη επανέλαβαν signed συσχέτιση σε νέο disjoint profiling
confirmation5k, με το προκαθορισμένο corrected-p criterion. Και τα δύο fixed-key ζεύγη
και το πρώτο variable-key πέρασαν. Το δεύτερο variable-key δεν πέρασε:
rtrain=−0,037942, rconfirmation=−0,026326, pBonferroni=0,092. Δεν ισχυριζόμαστε ότι
η διαρροή του είναι μηδενική ή ότι αποδείχθηκε causal overfitting.

## 1. Παγωμένο scope και ανεξαρτησία δεδομένων

Το [plan.json](plan.json) γράφτηκε πριν από τη δοκιμή. Ίδια ιστορικά training10k/splitseed2026,
ίδια points156×521/182×547 για fixed-key και187×1080/334×573 για variable-key.
Δεν επιλέχθηκε άλλο ζεύγος, model, training budget ή normalization. Οι label permutations
είναι null diagnostics, όχι πρόσθετες training seeds ή νέα fitted attack models.

Νέα profiling confirmation5k ανά καμπάνια, seed20261010, αποκλείουν κάθε προηγούμενο
training/validation/confirmation index. Fixed-key αποκλείει35k, μετά έχει40k viewed/fit rows.
Variable-key αποκλείει15k profiling rows, μετά έχει20k. Οι αρχικές val pools και το evaluated
variable-key attack5k δεν ανακυκλώθηκαν. Καμία Attack_traces ή metadata/keys/masks/plaintext
ανάγνωση από αυτή τη φάση. Χρησιμοποιούνται traces και παρεχόμενα identity labels→HW.
Train means διατηρούνται για centered products στη confirmation, χωρίς refit.

Το [calibration.json](calibration.json) γράφτηκε πριν το
[confirmation access record](confirmation_access.json), με UTC/hash. Η προηγούμενη
αποτυχία έδωσε το διαγνωστικό ερώτημα· η νέα confirmation δεν χρησιμοποιείται για tuning
και δεν επαληθεύει νέους ισχυρισμούς αποτελεσματικότητας σε άγνωστο key.

## 2. Τυχαίο maximum μετά από πλήρη αναζήτηση

Με99 training-label permutations ανά καμπάνια, κάθε φορά υπολογίζεται maximum|Pearson|
σε όλους τους αρχικά επιλέξιμους centered-product συνδυασμούς:211.575 για fixed-key,
885.115 για variable-key. Mean/product variance είναι training-only και επαναχρησιμοποιούνται·
η label-dependent covariance επανυπολογίζεται. Border/separation domain και ties παραμένουν
ίδια με την παλιά επιλογή. Δεν συγκρίνουμε το observed selected score μόνο με null
ενός σταθερού pair, που θα αγνοούσε την προηγούμενη αναζήτηση.

Median null maximum:fixed={record['calibrations']['fixed']['null_maximum_median']:.6f},
variable={record['calibrations']['variable']['null_maximum_median']:.6f}.
Στο variable pair2,68/99 null maxima είναι τουλάχιστον όσο|rtrain| με tolerance1e−12,
άρα συντηρητικό tail=(68+1)/(99+1)=0,69. Το observed score βρίσκεται στη συνήθη
κλίμακα μεγάλων τυχαίων συσχετίσεων αυτής της αναζήτησης. Τα άλλα τρία scores είναι
μεγαλύτερα από τα99 null maxima, tail0,01 — το ελάχιστο διαθέσιμο με99 draws.

Αυτό είναι conditional global-no-association diagnostic υπό exchangeable labels,
όχι πιθανότητα ότι το pair2 είναι ψευδές, proof strong FWER υπό partial alternatives,
απόδειξη ότι δεν υπάρχει φυσική διαρροή ή adaptive selection rule για νέα μέθοδο.
Η diversity επιλογή του δεύτερου pair διατηρείται, ενώ το null threshold αφορά
συντηρητικά το global maximum, όχι ειδικό null για δεύτερη θέση.

## 3. Προοπτική επιβεβαίωση των ήδη επιλεγμένων σημείων

Στις φρέσκες profiling rows, statistic=correlation×sign(historical training r),
με direction παγωμένο πριν την ανάγνωση.999 common pairing permutations των labels,
ίδια indices και streams στις δύο ίσου μεγέθους καμπάνιες, όχι ανεξάρτητες training seeds.
Monte Carlo p=(1+count(null≥observed−1e−12))/(999+1). Διόρθωση Bonferroni για τέσσερις
προκαθορισμένους ελέγχους, pAdjusted=min(4p,1). Criterion:signedr>0 και pAdjusted≤0,05.

{chr(10).join(table)}

Το raw p του variable pair2 είναι0,023, μετά τη διόρθωση0,092. Υπάρχει ασθενής
ίδιου προσήμου συσχέτιση στη νέα pool, αλλά δεν καλύπτει το προκαθορισμένο criterion.
Η παλαιότερη validation είχε σχεδόν μηδενική συσχέτιση· η διαφορά δεν επιτρέπει
επιλογή ευνοϊκής pool ή βεβαιότητα για απουσία σήματος. Τα τρία pAdjusted0,004
προέρχονται από raw0,001, το Monte Carlo floor, όχι ακριβή exhaustive p-values.

![Παγωμένα σημεία, τυχαία maxima και fresh confirmation](selection_replication.png)

## 4. Τι προσθέτει στο ερευνητικό αποτέλεσμα

Η αναζήτηση επιβάλλει δύο pairs ακόμη και αν ένα δεύτερο score δεν ξεχωρίζει από
μεγάλα τυχαία maxima. Αυτό καταγράφει κίνδυνο επιλογής και άνιση signal replication,
όχι νέο αποτελεσματικό attack. Η φάση ελέγχει σταθερότητα του **επιλεγμένου σήματος**,
όχι spatial stability των argmax points σε πολλές ανεξάρτητες εκπαιδεύσεις.

Το variable pair1 επαναλαμβάνει συσχέτιση σε profiling, αλλά είχε ήδη αποτύχει στο
παγωμένο combined5 attack της προηγούμενης φάσης. Επομένως η αστάθεια του pair2
δεν επαρκεί μόνη της να εξηγήσει όλη την αποτυχία. Δεν απομονώθηκε αιτιωδώς noise,
timing variation, campaign ή key effect. Δεν αλλάζει το failed CNN gate, το GPU cap
ή το αρχικό αναπάντητο augmentation ερώτημα. Δεν υποστηρίζεται νέα τεχνική ή paper-ready claim.

## 5. Πηγές, επαλήθευση και πραγματικό κόστος

Pairing correlation permutations και +1 randomized correction τεκμηριώνονται στην
[επίσημη SciPy documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html).
Χρησιμοποιείται δική μας NumPy υλοποίηση· δεν εκτελέστηκε SciPy permutation_test.
Η έγκυρη ερμηνεία προϋποθέτει random pairing/exchangeability, όχι ανεξαρτησία φυσικών
traces που αποδείχθηκε εδώ. Δεν έγινε stationarity audit κάθε acquisition sequence.
Ο [πρωτογενής έλεγχος πηγών/novelty](../../literature/SELECTION_AUDIT_2026-10-06.md)
καταγράφει τα όρια abstract-only ανάγνωσης και τα γνωστά προηγούμενα επιλογής σημείων.

[Ανεξάρτητη επαλήθευση](verification.json):598 πραγματικοί training/null coefficients,
6 sampled πλήρεις matrix-max επαναϋπολογισμοί, όλα τα3.996 confirmation-null coefficients,
και οι4 τελικές γραμμές/statistics/p-values. Επαληθεύτηκαν splits/disjointness,
όλες οι permutation indices/RNG final states, χρονική σειρά calibration/access,
old hashes/source/checkpoints/notebook/packets. Οι198 πλήρεις null maxima δεν
επανυπολογίστηκαν όλοι από δεύτερη matrix implementation:6 είναι ανεξάρτητα full-search
replays και τα υπόλοιπα ελέγχθηκαν στο αποθηκευμένο maximizing pair και στο frozen score.

Πέρασαν70tests/14 υπάρχονταwarnings, JUnit{verified['tests']['seconds']:.3f}s
(pytest console19,43s). Νέα GPU trainings0/optimizer updates0, συνολικάGPU3/cap4,
ένα Kaggle notebook, original gatefailed/combinedabsent. Actual CPU experiment
{record['seconds']:.6f}s μετάimports, verifier{verified['seconds']:.6f}s. Περιλαμβάνει
calibration, confirmation, εγγραφές και preservation checks, όχι imports/tests/report/session.
Έξι CPU ερευνητικές φάσεις:recorded experiment loops
{five_seconds + record['seconds']:.6f}s. Τα recovery summaries παραμένουν448/8.960 execution
endpoints/160additional replays· οι τέσσερις νέες γραμμές είναι correlations, όχι νέες key recoveries.

Οι δύο νέες profiling confirmation pools είναι τώρα viewed evidence και αποκλείονται
από tuning. Τα παλαιά αποτελέσματα διατηρήθηκαν. Αν υπάρξει επόμενη μεθοδολογική
πρόταση, χρειάζεται ξεχωριστό frozen training-only σχέδιο και άλλη αχρησιμοποίητη
profiling επιβεβαίωση, χωρίς adaptation στο προηγούμενο attack subset.

Artifacts: [results.json](results.json), [arrays.npz](arrays.npz), [splits.npz](splits.npz),
[pytest.xml](pytest.xml). Ενσωμάτωση στη§15 της ενιαίας εργασίας.
"""
    (OUT / "REPORT_EL.md").write_text(report, encoding="utf-8")
    evidence = {"results": rows, "calibrations": record["calibrations"], "replicated_pairs": sum(row["signed_signal_replicates"] for row in rows),
        "no_new_recovery_summaries": True, "six_phase_cpu_seconds": five_seconds + record["seconds"],
        "prior_recovery_summaries": 448, "prior_execution_endpoints": 8960, "prior_additional_replays": 160,
        "tests": verified["tests"], "new_gpu_trainings": 0, "paper_ready": False, "novelty_verified": False,
        "attack_payloads_or_key_metadata_read_in_this_audit": False,
        "input_sha256": {name: sha(OUT / name) for name in ("plan.json", "results.json", "verification.json", "pytest.xml")}}
    write_json(OUT / "evidence.json", evidence)
    print("Built:", OUT / "REPORT_EL.md")


if __name__ == "__main__":
    main()
