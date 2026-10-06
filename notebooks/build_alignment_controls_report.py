"""Generate a measured Greek SAD/control report, CSV and scientific comparison figure."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sca.train import write_json
from verify_paper_followups import read, sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/paper_alignment_controls_2026-10-05"
METHODS = ("fixed", "ncc_template", "gaussian_template", "sad_training_mean", "sad_training_reference",
           "gaussian_offsets_rolled", "oracle_known_shift")
LABELS = ("Fixed", "NCC", "Gaussian", "SAD mean", "SAD reference", "Wrong row", "Known shift")
CONDITIONS = ("clean", "shift5", "combined5", "combined10_ood")
CONDITION_LABELS = ("Clean", "Shift ±5", "Shift ±5 + σ=1.3", "Shift ±10 + σ=2.6")


def fmt(value, digits=2):
    return f"{value:.{digits}f}".replace(".", ",")


def successes(row):
    return f"{round(row['sr_at_budget'] * 20)}/20"


def main():
    record, plan, verification = [read(OUT / name) for name in ("results.json", "plan.json", "verification.json")]
    for name, expected in verification["artifact_sha256"].items():
        assert sha(OUT / name) == expected
    lookup = {(row["pool"], row["condition"], row["method"], row["family"]): row for row in record["results"]}
    sr_table = ["| Συνθήκη | " + " | ".join(LABELS) + " |", "|---|" + "---:|" * 7]
    for condition, label in zip(CONDITIONS, CONDITION_LABELS):
        cells = [", ".join(successes(lookup[("confirmation", condition, method, family)]) for family in ("pair1", "pair2")) for method in METHODS]
        sr_table.append("| " + label + " | " + " | ".join(cells) + " |")
    primary_table = ["| Μέθοδος | pair1 SR | pair1 GE | pair1 sustained SR90 | pair2 SR | pair2 GE | pair2 sustained SR90 |",
                     "|---|---:|---:|---:|---:|---:|---:|"]
    for method, label in zip(METHODS, LABELS):
        cells = []
        for family in ("pair1", "pair2"):
            row = lookup[("confirmation", "combined5", method, family)]
            cells.extend((successes(row), fmt(row["ge_at_budget"]), str(row["traces_to_sustained_sr90"] or ">2000")))
        primary_table.append("| " + label + " | " + " | ".join(cells) + " |")
    alignment = {row["method"]: row for row in record["alignment"] if row["pool"] == "confirmation" and row["condition"] == "combined5"}
    timings = {row["method"]: row for row in record["inference_timings"] if row["pool"] == "confirmation" and row["condition"] == "combined5"}
    timing_table = ["| Εκτιμητής | Ακριβές injected shift | MAE (samples) | Χρόνος για 5k (s) | μs/trace |",
                    "|---|---:|---:|---:|---:|"]
    for method, label in zip(METHODS[1:5], LABELS[1:5]):
        timing_table.append(f"| {label} | {fmt(alignment[method]['exact_shift_fraction'] * 100)}% | "
            f"{fmt(alignment[method]['mean_absolute_error'],4)} | {fmt(timings[method]['inference_seconds'],4)} | {fmt(timings[method]['microseconds_per_trace'])} |")
    with (OUT / "all_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ("pool", "condition", "method", "family", "pair", "ge_at_budget", "sr_at_budget", "traces_to_sustained_sr90", "recovery_censored")
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(record["results"])
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True, layout="constrained")
    x = np.arange(len(METHODS))
    for axis, condition, title in zip(axes, ("combined5", "combined10_ood"),
                                     ("Raw shift ±5 + noise σ=1.3", "Raw shift ±10 + noise σ=2.6")):
        for family, delta, color in (("pair1", -.18, "#2563eb"), ("pair2", .18, "#d97706")):
            values = [lookup[("confirmation", condition, method, family)]["sr_at_budget"] for method in METHODS]
            bars = axis.bar(x + delta, values, width=.34, color=color, label=family)
            for bar, value in zip(bars, values):
                axis.text(bar.get_x() + bar.get_width()/2, value + .018, str(round(value * 20)), ha="center", fontsize=8)
        axis.set_xticks(x, ["Fixed", "NCC", "Gaussian", "SAD\nmean", "SAD\nreference", "Wrong\nrow", "Known\nshift"], fontsize=9)
        axis.set_ylim(0, 1.16)
        axis.set_yticks(np.linspace(0, 1, 6))
        axis.set_title(title)
        axis.grid(axis="y", alpha=.2)
        axis.set_axisbelow(True)
    axes[0].set_ylabel("SR@2000; labels are successes out of 20")
    axes[1].legend(loc="upper right", ncol=2, fontsize=9)
    fig.suptitle("Phase 4: frozen training-label-only pairs; fresh profiling confirmation", fontsize=13)
    fig.savefig(OUT / "sad_and_correspondence.png", dpi=160)
    plt.close(fig)
    reference = read(OUT / "reference.json")
    previous = read(ROOT / "outputs/paper_extension_2026-10-05/evidence.json")
    evidence = {"results": record["results"], "primary_confirmation_condition": "combined5",
        "predefined_correspondence_criterion_met": verification["predefined_correspondence_criterion_met"],
        "gaussian_better_than_sad_mean_at_primary_endpoint": False,
        "shift_inference_timings": record["inference_timings"], "tests": verification["tests"],
        "new_recovery_summaries": 112, "new_independent_execution_cpa_endpoints": 2240,
        "additional_independent_endpoint_replays": 112, "new_sampled_independent_shift_estimates": 256,
        "four_phase_recovery_summaries": 400, "four_phase_independent_execution_cpa_endpoints": 8000,
        "four_phase_cpu_experiment_seconds": previous["experiment_seconds_total"] + record["seconds"],
        "phase_four_cpu_experiment_seconds": record["seconds"], "novelty_verified": False,
        "new_gpu_trainings": 0, "full_gpu_trainings_total": 3, "canonical_notebook_count": 1,
        "new_real_data_optimizer_updates": 0, "final_attack_payloads_read": False,
        "input_sha256": {name: sha(OUT / name) for name in ("plan.json", "results.json", "reference.json", "splits.npz", "arrays.npz", "verification.json", "pytest.xml")}}
    assert all(lookup[("confirmation", "combined5", "gaussian_template", family)]["sr_at_budget"] ==
               lookup[("confirmation", "combined5", "sad_training_mean", family)]["sr_at_budget"] for family in ("pair1", "pair2"))
    write_json(OUT / "evidence.json", evidence)
    report = f"""# SAD και έλεγχος σωστής αντιστοίχισης μετατόπισης — 2026-10-05

Η τέταρτη CPU φάση επιβεβαίωσε recovery **20/20 και 20/20** στη μέτρια raw αλλοίωση
με Gaussian, NCC και SAD training mean, στα δύο παγωμένα ζεύγη. Το όφελος χάθηκε
όταν τα ίδια Gaussian offsets αντιστοιχίστηκαν σε λάθος ίχνη: **0/20 και 0/20**.
Η γνωστή SAD μέθοδος ισοφάρισε τη Gaussian στο κύριο SR endpoint. Δεν προκύπτει
υπεροχή ή νέα τεχνική Gaussian alignment από αυτό το πείραμα.

## 1. Τι πάγωσε πριν την εκτέλεση

Ίδια original training10k/validation5k, ASCAD fixed-key, 700 samples, byte2.
Σημεία 156×521 και 182×547 από την προηγούμενη training-label-only επιλογή,
χωρίς νέο pair search ή fit σε confirmation. Unconditional training mean/variance.
Το νέο confirmation έχει 5.000 rows, seed20261008, αποκλείοντας train, validation
και τις τρεις προηγούμενες pools. Συνολικά 35.000 μοναδικά profiling rows καλύπτονται
από train/validation/τέσσερα confirmations. Απομένουν 15.000 profiling rows εκτός
αυτών των pools· δεν υποστηρίζεται ότι είναι άγνωστα σε κάθε ιστορικό schema diagnostic.
Το original Attack_traces payload δεν χρησιμοποιήθηκε στην επέκταση.

Κοινά 20 overlapping orders των 2.000 traces, seed8001, και ίδια U/Z seeds9101/2,
όπως πριν. Οι same-sized pools χρησιμοποιούν κοινά RNG streams, όχι ανεξάρτητες
corruption seeds. Τα trials αφορούν το ίδιο key byte, όχι 20 ανεξάρτητα κλειδιά.
RNG final states, draws, orders και hashes αποθηκεύτηκαν και επαληθεύτηκαν.

Search ±10, template window20:680, κοινή tie rule μικρότερου |shift| και negative
πριν positive. Τα scored samples είναι στο εσωτερικό και αποκλείουν το padding
για injected shifts έως±10. Zero/edge scores, estimates και products ήταν ίδια.

Raw S(x)+ε, uniform raw Gaussian σ=1,3 για combined5 και σ=2,6 για combined10_ood.
Αυτά παραμένουν διαφορετικά από το προηγούμενο normalized-space σ=0,1/0,2 protocol.
Δεν αυξήθηκε training budget, δεν έγιναν optimizer updates ή GPU εκτελέσεις.

## 2. Γνωστά baselines και counterfactual

- NCC και diagonal Gaussian: οι ακριβώς ίδιες frozen trace-only εκτιμήσεις.
- SAD training mean: ελάχιστο sum absolute difference ως προς το training mean.
- SAD reference: ίδια objective ως προς ένα training trace, επιλεγμένο χωρίς labels,
  key ή mask ως το πλησιέστερο στο mean με MSE στο fixed score window. Training
  index {reference['sorted_training_row_index']}, profiling row {reference['profiling_row_index']}.
- Wrong row: deterministic roll κατά μία row των Gaussian-estimated offsets.
  Διατηρεί ακριβώς το histogram, αλλά διακόπτει την αντιστοίχιση trace/estimate.
  Diagnostic counterfactual, χωρίς χρήση των σωστών injected shifts στην κατασκευή του.
- Fixed και Known shift: χωρίς alignment και γνωστή synthetic μετατόπιση αντίστοιχα.
  Το known-shift SR δεν είναι αυστηρό άνω όριο σε πεπερασμένη noisy CPA.

Η SAD είναι κλασική objective, όπως περιγράφεται στην
[επίσημη τεκμηρίωση ChipWhisperer](https://chipwhisperer.readthedocs.io/en/latest/analyzer-api.html#chipwhisperer.analyzer.preprocessing.resync_sad.ResyncSAD).
Οι δύο δικές μας παραλλαγές κρατούν όλα τα traces, inclusive search bounds και κοινά
tie rules. **Δεν είναι exact ChipWhisperer package reproduction**, το οποίο χρησιμοποιεί
ένα reference trace και δικό του rejection/search handling. Δεν εγκαταστάθηκε package.
[Primary code και αναλυτικές διαφορές](../../literature/ALIGNMENT_BASELINES_2026-10-05.md).

## 3. Νέο confirmation, SR@2.000

Κάθε cell δείχνει pair1, pair2. Οι μέθοδοι δεν επιλέχθηκαν από τα αποτελέσματα.

{chr(10).join(sr_table)}

![SAD και έλεγχος αντιστοίχισης](sad_and_correspondence.png)

**Κύρια combined5 συνθήκη:**

{chr(10).join(primary_table)}

Το predefined correspondence criterion επιτεύχθηκε: Gaussian SR≥0,90 σε κάθε pair,
βελτίωση≥0,10 έναντι wrong-row και clean Gaussian απώλεια≤0,10 έναντι fixed.
Gaussian clean SR20/20 και στα δύο. Το histogram μόνο του δεν διατηρεί το όφελος
όταν αφαιρεθεί η σωστή αντιστοίχιση στην παρούσα bounded synthetic-shift περίπτωση.
Αυτός ο αρνητικός έλεγχος δεν αποκλείει όλους τους πιθανούς alignment confounders.

SAD mean/NCC/Gaussian έχουν ίδια endpoint SR στη combined5, αλλά διαφορετικά prefix
thresholds. Η Gaussian φτάνει sustained SR90 στο pair2 στα1.606 traces, SAD mean/NCC
στα1.888, SAD reference στα1.300 με endpoint19/20. Δεν επιλέγουμε εκ των υστέρων
ποιο metric ευνοεί ποια μέθοδο· δεν παρουσιάζεται γενικός ισχυρισμός υπεροχής.

Στο OOD όλες οι πρακτικές μέθοδοι απέτυχαν στο threshold18/20: Gaussian **2/20,3/20**,
NCC **2/20,5/20**, SAD mean **2/20,6/20**, SAD reference **1/20,6/20**.
Η ύπαρξη περίπου93% ακριβών shifts δεν συνεπάγεται ότι το noisy second-order feature
αρκεί για recovery· alignment και feature SNR δεν είναι η ίδια μέτρηση.

## 4. Ακρίβεια εκτίμησης και καταγεγραμμένο κόστος

Confirmation combined5:

{chr(10).join(timing_table)}

Wrong-row shift accuracy {fmt(alignment['gaussian_offsets_rolled']['exact_shift_fraction'] * 100)}%,
Gaussian {fmt(alignment['gaussian_template']['exact_shift_fraction'] * 100)}%.
Οι χρόνοι είναι **μία inference call για 5k traces** ανά μέθοδο/condition, σε fixed
σειρά μέσα στην ίδια CPU εκτέλεση. Δεν περιλαμβάνουν edge replay, I/O, CPA, setup ή
όλη τη συνεδρία. Δεν μετρήθηκαν repeated timing variance, ανεξάρτητοι devices ή
συμμετρικό warm-up· δεν προκύπτει σταθερό speedup από αυτά τα τέσσερα timings.

Phase4 experiment loop: **{fmt(record['seconds'])}s** μετά imports. Ανεξάρτητος verifier:
{fmt(verification['seconds'])}s. Τέσσερις CPU experiment loops συνολικά
{fmt(evidence['four_phase_cpu_experiment_seconds'])}s, ξεχωριστά από tests/reports/verifiers.
Full suite **61 passed / 14 υπάρχοντα warnings** σε {fmt(verification['tests']['seconds'])}s.
Η νέα φάση ελέγχθηκε στο ενεργό venv· το προηγούμενο clean CPU replay κάλυπτε το παλιό suite44.

## 5. Επαλήθευση και σχέση με paper

112 νέες recovery summaries, 2.240 ανεξάρτητα Pearson endpoints κατά εκτέλεση και
112 πρόσθετα endpoint replays από άλλη υλοποίηση. Ελέγχθηκαν ανεξάρτητα 256 sampled
shift estimates, πλήρη GE/SR/sustained summaries, disjoint splits/seed replay,
training-only reference, frozen pairs, RNG draws/orders/final states και exact rolled
histograms. Σύνολο τεσσάρων φάσεων: **400 summaries και 8.000 execution endpoint checks**,
με τα112 επιπλέον replays καταγεγραμμένα χωριστά.

Source84eff…, checkpoints, datasets, αρχικά splits, active Input και μοναδικό canonical
Kaggle notebook διατηρήθηκαν με hashes. Σύνολο GPU trainings3, νέα0, cap4, CNN gate
failed/combined skipped. Καμία νέα πραγματική optimizer ενημέρωση, final attack reads0
από αυτή τη φάση. Το νέο confirmation είναι πλέον viewed evidence και δεν
επαναχρησιμοποιείται ως αθέατο για μελλοντικές επιλογές.

Η τέταρτη φάση ενισχύει την ερμηνεία ότι η σωστή αντιστοίχιση shift/trace έχει
πρακτική σημασία και ότι το αποτέλεσμα της phase3 επαναλήφθηκε με frozen pairs.
Παράλληλα περιορίζει την υπόθεση Gaussian advantage: μια γνωστή SAD objective
ισοφαρίζει το primary endpoint. Πρόκειται ακόμη για same-key/campaign case study,
με global synthetic shifts και noise, όχι φυσικό local jitter ή unknown-key transfer.
Το [Second-order Scatter Attack, §1.1](https://eprint.iacr.org/2019/345.pdf) ήδη
διακρίνει τις απλές global μετατοπίσεις από elastic misalignment/shuffling.
Δεν εκτελέστηκε Scatter/DTW και δεν τεκμηριώθηκε νέο βιβλιογραφικό κενό.

Επόμενο: διαμόρφωση ανεξάρτητης campaign/key αξιολόγησης και κατάλληλων ισχυρών
συγκρίσεων πριν από νέο claim. Δεν αλλάζουμε το final attack set σε tuning pool.
Τα τωρινά αποτελέσματα εντάσσονται στην πανεπιστημιακή εργασία· paper novelty
παραμένει ανεπιβεβαίωτη.

[Frozen plan](plan.json), [αποτελέσματα](results.json), [112 rows CSV](all_results.csv),
[reference provenance](reference.json), [ανεξάρτητη verification](verification.json),
[evidence](evidence.json), [report verification](report_verification.json),
[προηγούμενες τρεις φάσεις](../paper_extension_2026-10-05/REPORT_EL.md).
"""
    (OUT / "REPORT_EL.md").write_text(report, encoding="utf-8")
    print(json.dumps({"report": str(OUT / "REPORT_EL.md"), "rows": len(record["results"]),
                      "four_phase_cpu_seconds": evidence["four_phase_cpu_experiment_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
