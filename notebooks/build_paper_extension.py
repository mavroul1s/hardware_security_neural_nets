"""Build a measured Greek report and scientific figures for three CPU research phases."""
import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sca.train import write_json
from verify_paper_followups import read, sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/paper_extension_2026-10-05"
DIRECTORIES = [ROOT / "outputs" / name for name in
    ("paper_alignment_2026-10-05", "paper_alignment_coordinates_2026-10-05", "paper_maskfree_2026-10-05")]
METHODS = ("fixed", "ncc_template", "gaussian_template", "oracle_known_shift")
LABELS = ("Fixed", "NCC", "Gaussian", "Known shift")
CONDITIONS = ("clean", "shift5", "combined5", "combined10_ood")
CONDITION_LABELS = ("Clean", "Shift ±5", "Shift ±5 + σ=1.3", "Shift ±10 + σ=2.6")


def row_lookup(record):
    return {(row["pool"], row["condition"], row.get("pipeline", "raw_shift"), row["method"], row["family"]): row
            for row in record["results"]}


def successes(row):
    return f"{round(row['sr_at_budget'] * 20)}/20"


def fmt(value, digits=2):
    return f"{value:.{digits}f}".replace(".", ",")


def sr_table(record, families, pipeline="raw_shift"):
    lookup = row_lookup(record)
    lines = ["| Συνθήκη | " + " | ".join(f"{label} {family}" for label in LABELS for family in families) + " |",
             "|---|" + "---:|" * 8]
    for condition, label in zip(CONDITIONS, CONDITION_LABELS):
        cells = [successes(lookup[("confirmation", condition, pipeline, method, family)])
                 for method in METHODS for family in families]
        lines.append("| " + label + " | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def plots(records):
    lookup = row_lookup(records[1])
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 4.8), layout="constrained")
    columns = [f"{label}\n{family}" for label in ("Fixed", "NCC", "Gauss.", "Known\nshift") for family in ("rout", "r3")]
    for axis, pipeline, title in zip(axes, ("raw_shift", "feature_shift_surrogate"),
                                    ("Raw waveform shifts", "Feature-shift surrogate; corrected coordinates")):
        values = np.array([[lookup[("confirmation", condition, pipeline, method, family)]["sr_at_budget"]
                            for method in METHODS for family in ("rout", "r3")] for condition in CONDITIONS])
        axis.imshow(values, vmin=0, vmax=1, cmap="Blues", aspect="auto")
        axis.set_xticks(range(8), columns, fontsize=9)
        axis.set_yticks(range(4), CONDITION_LABELS, fontsize=10)
        axis.set_title(title, fontsize=12)
        for i in range(4):
            for j in range(8):
                axis.text(j, i, f"{round(values[i, j] * 20)}/20", ha="center", va="center",
                          fontsize=10, color="white" if values[i, j] > .6 else "#152235")
    fig.suptitle("Phase 2: SR@2000 on fresh profiling confirmation (one key byte; 20 overlapping orders)", fontsize=13)
    fig.savefig(OUT / "coordinate_confirmation.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.6), layout="constrained", sharey=True)
    colors = ("#64748b", "#2563eb", "#d97706", "#16856b")
    with np.load(DIRECTORIES[2] / "arrays.npz", allow_pickle=False) as arrays:
        for axis, family in zip(axes, ("pair1", "pair2")):
            for method, label, color in zip(METHODS, LABELS, colors):
                ranks = arrays[f"confirmation__combined5__{method}__{family}__ranks"]
                axis.plot(np.arange(1, 2001), (ranks == 0).mean(axis=0), label=label, color=color, lw=1.7)
            axis.axhline(.9, color="#94a3b8", ls=":", lw=1)
            pair = records[2]["pairs"][family]
            axis.set_title(f"{family}: samples {pair[0]} × {pair[1]}")
            axis.set_xlabel("Traces")
            axis.set_xlim(0, 2000)
            axis.set_ylim(-.03, 1.03)
            axis.grid(alpha=.18)
    axes[0].set_ylabel("Success rate; rank 0")
    axes[1].legend(loc="lower right", framealpha=.95)
    fig.suptitle("Phase 3: training-label-only selection, raw shift ±5 + noise σ=1.3", fontsize=13)
    fig.savefig(OUT / "training_label_confirmation.png", dpi=160)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = [read(directory / "results.json") for directory in DIRECTORIES]
    verifications = [read(directory / "verification.json") for directory in DIRECTORIES]
    for directory, verification in zip(DIRECTORIES, verifications):
        for name, expected in verification["artifact_sha256"].items():
            assert sha(directory / name) == expected
    plans = [read(directory / "plan.json") for directory in DIRECTORIES]
    suite = ET.parse(DIRECTORIES[2] / "pytest.xml").getroot().find("testsuite")
    tests = {field: int(suite.attrib[field]) for field in ("tests", "failures", "errors", "skipped")}
    tests["seconds"] = float(suite.attrib["time"])
    tests["warnings"] = 14
    assert tests["tests"] == 57 and tests["failures"] == tests["errors"] == tests["skipped"] == 0
    lookup = row_lookup(records[2])
    support = all(lookup[("confirmation", "combined5", "raw_shift", "gaussian_template", family)]["sr_at_budget"] >= .9
                  and lookup[("confirmation", "combined5", "raw_shift", "gaussian_template", family)]["sr_at_budget"] - lookup[("confirmation", "combined5", "raw_shift", "fixed", family)]["sr_at_budget"] >= .1
                  and lookup[("confirmation", "clean", "raw_shift", "gaussian_template", family)]["sr_at_budget"] >= lookup[("confirmation", "clean", "raw_shift", "fixed", family)]["sr_at_budget"] - .1
                  for family in ("pair1", "pair2"))
    rows = [{"phase": index + 1, **row} for index, record in enumerate(records) for row in record["results"]]
    assert len(rows) == 288
    fields = ("phase", "pool", "condition", "pipeline", "method", "family", "pair", "ge_at_budget", "sr_at_budget", "traces_to_sustained_sr90", "recovery_censored")
    with (OUT / "all_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    total_seconds = sum(record["seconds"] for record in records)
    input_hashes = {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
                   for directory in DIRECTORIES for path in directory.iterdir() if path.suffix in (".json", ".npz", ".xml")}
    evidence = {"authorization": plans[0]["authorization"], "phase_rows": [len(record["results"]) for record in records],
        "total_recovery_summaries": len(rows), "independent_execution_cpa_endpoints": 5760,
        "sampled_independent_shift_estimates": sum(record.get("sampled_trace_only_shift_estimates_independently_verified", record.get("sampled_trace_only_estimates_independently_verified", 0)) for record in verifications),
        "input_sha256": input_hashes, "original_inputs_sha256": plans[0]["input_hashes"],
        "source_sha256": plans[0]["source_sha256"], "phase_seconds": [record["seconds"] for record in records],
        "experiment_seconds_total": total_seconds, "mask_free_selection": read(DIRECTORIES[2] / "selection.json"),
        "phase_three_predefined_support_criterion_met": support,
        "phase_two_both_original_pairs_sr90_criterion_met": all(row_lookup(records[1])[("confirmation", "combined5", "raw_shift", "gaussian_template", family)]["sr_at_budget"] >= .9 for family in ("rout", "r3")),
        "all_results": rows, "tests": tests, "novelty_verified": False, "paper_ready": False,
        "new_gpu_trainings": 0, "full_gpu_trainings_total": 3, "canonical_notebook_count": 1,
        "new_real_data_optimizer_updates": 0, "final_attack_payloads_read": False,
        "confirmation_pools_now_viewed": [20261005, 20261006, 20261007]}
    write_json(OUT / "evidence.json", evidence)
    plots(records)
    first_primary = row_lookup(records[0])
    second_primary = row_lookup(records[1])
    selection = evidence["mask_free_selection"]
    primary_table = ["| Μέθοδος | pair1 SR | pair1 GE | pair1 sustained SR90 | pair2 SR | pair2 GE | pair2 sustained SR90 |",
                     "|---|---:|---:|---:|---:|---:|---:|"]
    for method, label in zip(METHODS, LABELS):
        cells = []
        for family in ("pair1", "pair2"):
            row = lookup[("confirmation", "combined5", "raw_shift", method, family)]
            cells.extend((successes(row), fmt(row["ge_at_budget"]), str(row["traces_to_sustained_sr90"] or ">2000")))
        primary_table.append("| " + label + " | " + " | ".join(cells) + " |")
    report = f"""# Νέα πειράματα προς πιθανή δημοσίευση — 2026-10-05

Εκτελέστηκαν τρεις CPU φάσεις με πραγματικά ASCAD profiling traces και προκαθορισμένες
συνθετικές αλλοιώσεις. Η επιλογή σημείων μόνο από training labels, μαζί με εκτίμηση
μετατόπισης από το waveform, πέτυχε **20/20 και18/20** ανακτήσεις του byte στη συνθήκη
raw shift±5/θόρυβοςσ=1,3, έναντι **0/20 και0/20** χωρίς alignment. Το αυστηρότερο
shift±10/σ=2,6 παρέμεινε ανεπαρκές. Το θετικό αποτέλεσμα δεν τεκμηριώνει νέα τεχνική,
γενίκευση σε άλλη συσκευή ή ετοιμότητα paper.

Η επέκταση εγκρίθηκε από τον χρήστη στις5/10 για έρευνα και ένταξη στην τελική εργασία.
Το original augmentation CNN ερώτημα εξακολουθεί να μην έχει μετρηθεί: failed gate,
combined skipped, τρία υπάρχοντα GPU trainings, ένα Kaggle notebook.

## 1. Προοπτικό πρωτόκολλο και πληροφορία

ASCAD fixed-key,700 samples, zero-based byte2. Διατηρήθηκαν τα αρχικά10.000 training
και5.000 validation rows. Κάθε φάση πάγωσε δικό της plan/script hash πριν την εκτέλεση,
με νέο confirmation5.000 rows: seeds20261005,20261006,20261007. Οι τρεις pools είναι
αμοιβαία disjoint και χωριστοί από train/validation:30.000 μοναδικά profiling rows
συνολικά. Η official attack ομάδα δεν διαβάστηκε από αυτά τα νέα πειράματα.
Οι confirmation pools έχουν πλέον εξεταστεί· δεν θεωρούνται νέα αθέατη επιβεβαίωση
για επόμενες επιλογές. Η δεύτερη και τρίτη φάση προέκυψαν από ευρήματα της προηγούμενης,
και αποτελούν διαδοχική διερευνητική έρευνα, όχι μία ενιαία προεγγραφή.

Κοινά20 permutations/subsets των2.000 traces από κάθε pool5.000, seed8001. Είναι
επικαλυπτόμενες σειρές του **ίδιου key byte**, όχι20 ανεξάρτητα κλειδιά ή training seeds.
Δεν υπολογίζονται p-values ή ανεξάρτητες binomial confidence intervals.
Rank0=best, conservative absolute-correlation ties με ανοχή1e−12. SR90 σημαίνει
ότι SR≥0,9 διατηρείται σε όλα τα επόμενα prefixes μέχρι2.000· απουσία δηλώνεται censored.

Για alignment χρησιμοποιούνται μόνο traces: unconditional mean/diagonal variance
από train10k, NCC ή Gaussian score, candidates−10…10. Template columns20…679,
παρατηρούμενες columns10…689: κανένα padding sample δεν εισέρχεται στο score υπό
τις δοκιμασμένες πραγματικές shifts. Variance floor=max(median(train variance)×1e−6,1e−12).
Ties: μικρότερο|shift|, αρνητικό πριν θετικό. Το true injected shift χρησιμοποιείται
μόνο στο διαγνωστικό Known shift control και στη μέτρηση σφάλματος εκτίμησης.

Τα centered products βαθμολογούνται με absolute Pearson ως προς
HW(SBOX(plaintext_byte2 xor candidate_byte)). Τα plaintexts είναι δημόσιες
υποθέσεις αξιολόγησης· το σωστό key byte χρησιμοποιείται μόνο για rank/SR.
Δεν παρέχεται key, mask, plaintext ή label στον alignment estimator.

## 2. Θόρυβος και σειρά κανονικοποίησης

Ο scalerN(x)=(x−minimum)/scale προσαρμόζεται μόνο στα training traces, χωρίς clipping.
Median training feature range={records[0]['training_range_median']:.0f} raw units.
Οι τέσσερις συνθήκες είναι clean, shift±5, combined±5/σ=1,3 και combined±10/σ=2,6.
Ο θόρυβος είναι Gaussian **ομοιόμορφης raw-unit διασποράς**. Δεν είναι η παλαιότερη
feature-space σ=0,1/0,2 μετά το per-position MinMax· αυτά τα protocols δεν εξισώνονται.
U seed9101 καιZ seed9102 διατηρούνται κοινά ανά pool μεταξύ συνθηκών/μεθόδων.
Χρησιμοποιούνται τα ίδια RNG streams και στις ίσου μεγέθους pools: paired αλλοιώσεις,
όχι ανεξάρτητες corruption seeds. RNG states/draw hashes είναι στα verification records.

- Raw pipeline: S(x)+ε.
- Feature-shift surrogate: N⁻¹(S(N(x)))+ε. Δεν είναι φυσική μετατόπιση raw waveform.
- Affine transport S(N(x))×S(scale)+S(minimum)+ε επαναφέρει το raw pipeline
  με σφάλμα≤1e−10. Scalar affine normalization αντιμετατίθεται στο εσωτερικό.

Zero/edge padding έδωσαν ίδια selected products και shift estimates στις τρεις φάσεις.
Αυτό ελέγχει τους συγκεκριμένους εσωτερικούς estimators/features· δεν αποδεικνύει
γενική CNN border invariance. Ο known-shift έλεγχος δεν αποτελεί αυστηρό άνω όριο SR:
το τέλειο synthetic alignment δεν μεγιστοποιεί υποχρεωτικά την πεπερασμένη noisy CPA.

## 3. Φάση1: frozen παλαιά σημεία και πρώτος έλεγχος

Χρησιμοποιήθηκαν τα παλιά181×521(rout),156×517(r3), επιλεγμένα παλαιότερα μόνο στο
training αλλά με πρόσβαση σε mask/share metadata. Στο πρώτο confirmation, raw combined5
Gaussian SR={successes(first_primary[('confirmation','combined5','raw_shift','gaussian_template','rout')])} και{successes(first_primary[('confirmation','combined5','raw_shift','gaussian_template','r3')])}
για rout/r3, έναντι0/20 και0/20 fixed. Το υπάρχον CNN minimum-CE checkpoint είχε
clean confirmation GE112/SR0/20, χωρίς εκπαίδευση.

Η αρχική surrogate σύγκριση βαθμολόγησε και τις δύο pipelines στο raw training
σύστημα. Αυτό αναμειγνύει normalization order με λάθος centering/scales του
μετατοπισμένου normalized σήματος. Το surrogate known-shift0/20 δεν ερμηνεύεται
ως αδυναμία που παραμένει με σωστή εξαγωγή. Το αρχικό αποτέλεσμα διατηρείται ως
έλεγχος λανθασμένων συντεταγμένων, και διορθώθηκε προοπτικά στη φάση2.

## 4. Φάση2: σωστές συντεταγμένες και δεύτερο confirmation

Raw scoring στο raw training domain. Surrogate scoring στο N(observation),
με mean/variance και product centers από N(training). Ίδιο search/μέθοδοι/παλιά
σημεία· νέα poolseed20261006, χωρίς fit ή επιλογή σε προηγούμενο confirmation.

**Raw pipeline, SR@2.000:**

{sr_table(records[1], ('rout','r3'))}

**Feature-shift surrogate, corrected coordinates, SR@2.000:**

{sr_table(records[1], ('rout','r3'), 'feature_shift_surrogate')}

![Σύγκριση στο δεύτερο confirmation](coordinate_confirmation.png)

Το πρώτο raw20/20 και στα δύο ζεύγη **δεν επαναλήφθηκε**: Gaussian combined5
στο δεύτερο confirmation={successes(second_primary[('confirmation','combined5','raw_shift','gaussian_template','rout')])},
{successes(second_primary[('confirmation','combined5','raw_shift','gaussian_template','r3')])}.
Το προκαθορισμένο κριτήριο≥18/20 και στα δύο αποτυγχάνει. Η διόρθωση στο surrogate
δίνει known-shift18/20,20/20 αντί της αρχικής raw-coordinate αποτυχίας· διαφορετικές
pools δεν επιτρέπουν καθαρή αριθμητική before/after αιτιώδη σύγκριση.

Παραμένουν διαφορετικά αποτελέσματα μεταξύ pipelines. Στο combined5 η Gaussian
εκτίμηση shift είναι ακριβής στο92,94% των raw traces έναντι66,52% surrogate.
Η σύγκριση περιλαμβάνει το waveform/scale/noise interaction που ορίζει κάθε pipeline·
δεν αποδεικνύει μόνο έναν απομονωμένο παράγοντα ούτε εξηγεί το **clean CNN failure**,
όπου η injected shift είναι μηδενική.

## 5. Φάση3: επιλογή μόνο με training labels

Η επιλογή χρειάζεται τα ίδια10k training traces και τα παρεχόμενα identity labels·
δεν διαβάζει training key/mask/share metadata. ΣτόχοςHW(identity label), absolute
Pearson του train-centered product για όλα τα211.575 eligible pairs με απόσταση≥50
samples. Επιλέγεται το μέγιστο και δεύτερο με κάθε point≥20samples από τα δύο πρώτα.
Constraints/ties πάγωσαν πριν την επιλογή· δεν χαλαρώθηκαν μετά validation.
Τρία matrix products υπολογίζουν τις coefficients, χωρίς optimizer updates.

Επιλέχθηκαν **156×521(pair1)** και **182×547(pair2)**. Training correlations
{fmt(selection['training_correlations']['pair1'],6)} και{fmt(selection['training_correlations']['pair2'],6)}.
Η επιλογή αποθηκεύτηκε πριν διαβαστούν validation/confirmation payloads.
Χρόνος υπολογισμού επιλογής{fmt(selection['selection_seconds'],3)}s, όχι συνολικό I/O.
Υπάρχει supervised feature engineering και HW objective· δεν τεκμηριώνεται γενική
υπεροχή αυτής της CPA έναντι του CNN identity objective.

**Νέο confirmation seed20261007, raw pipeline:**

{sr_table(records[2], ('pair1','pair2'))}

**Κύρια combined5 συνθήκη σε2.000 traces:**

{chr(10).join(primary_table)}

![Καμπύλες στο τρίτο confirmation](training_label_confirmation.png)

Το προκαθορισμένο κριτήριο Gaussian≥18/20, βελτίωση≥0,10 έναντι fixed και clean
υποβάθμιση≤0,10 επιτεύχθηκε σε αυτή την pool. Η ακριβής Gaussian shift εκτίμηση
ήταν92,44%. Στο δυσκολότερο OOD η Gaussian έδωσε **6/20 και0/20** και κανένα
ζεύγος δεν έφτασε sustained SR90. Δεν αλλάζουμε ένταση/ζεύγη για να κρύψουμε το όριο.
Η αλλαγή σημείων και η νέα confirmation pool δεν επιτρέπουν ισχυρισμό ότι η νέα
επιλογή είναι ανώτερη από την προηγούμενη σε κοινή ανεξάρτητη σύγκριση.

## 6. Επαλήθευση, αρχεία και πραγματικό κόστος

- 128+96+64={len(rows)} recovery summaries, συνολικά5.760 CPA endpoint ranks ελεγμένα
  με ανεξάρτητο Pearson κατά την εκτέλεση. Επιπλέον576 sampled trace-only estimates
  επαναϋπολογίστηκαν ανεξάρτητα, GE/SR/sustained summaries ελέγχθηκαν από τις curves.
- Train-label selection:13 πραγματικές training pair coefficients ελέγχθηκαν με
  ανεξάρτητο np.corrcoef, μαζί με maxima, constraints και disjoint seed replay.
- Full suite57 passed/14υπάρχοντα warnings σε{fmt(tests['seconds'])}s,0failures/errors/skips.
  Συνθετικά fixtures ελέγχουν κώδικα· οι αποτελεσματικότητες παραπάνω χρησιμοποιούν
  πραγματικά traces με συνθετικές αλλοιώσεις.
- Μετρημένοι CPU experiment loops: {fmt(records[0]['seconds'])}s + {fmt(records[1]['seconds'])}s
  + {fmt(records[2]['seconds'])}s = **{fmt(total_seconds)}s** ({fmt(total_seconds/60)}min),
  μετά τις εισαγωγές βιβλιοθηκών. Δεν περιλαμβάνουν όλη τη συνεδρία, tests/report ή
  ανεξάρτητους verifiers. Καμία νέα Kaggle εκτέλεση, πραγματικά optimizer updates0.
- Source84eff…, best/last checkpoints, active Input/code packet και μοναδικό canonical
  notebook διατηρήθηκαν βάσει SHA256. Failed CNN gate/combined skipped διατηρούνται.

[Όλα τα288 αποτελέσματα CSV](all_results.csv), [machine-readable evidence](evidence.json),
[τελική επαλήθευση](verification.json). Φάσεις: [1plan](../paper_alignment_2026-10-05/plan.json),
[1results](../paper_alignment_2026-10-05/results.json),
[1verification](../paper_alignment_2026-10-05/verification.json),
[2plan](../paper_alignment_coordinates_2026-10-05/plan.json),
[2results](../paper_alignment_coordinates_2026-10-05/results.json),
[2verification](../paper_alignment_coordinates_2026-10-05/verification.json),
[3plan](../paper_maskfree_2026-10-05/plan.json),
[3selection](../paper_maskfree_2026-10-05/selection.json),
[3results](../paper_maskfree_2026-10-05/results.json),
[3verification](../paper_maskfree_2026-10-05/verification.json).

## 7. Τι σημαίνει για paper και τελική εργασία

Έχουμε τεκμηριωμένο όφελος απλών trace-only aligners για συγκεκριμένα second-order
features και bounded synthetic shifts, με επιβεβαίωση χωρίς mask-aided point selection,
αρνητικό OOD και διακύμανση μεταξύ pools. Αυτά προστίθενται στην τελική πανεπιστημιακή
εργασία. **Δεν έχουμε ακόμη τεκμηριωμένη δημοσιεύσιμη πρωτοτυπία.**

Το πρόβλημα position-wise normalization/misalignment είναι ήδη συζητημένο στο
[Krček et al., preprint2023/1100, §2/§5.1](https://eprint.iacr.org/2023/1100.pdf).
Second-order alignment έχει προηγούμενα, όπως το
[Second-order Scatter Attack2019](https://eprint.iacr.org/2019/345).
NCC/Gaussian templates, centered products και supervised feature selection δεν
παρουσιάζονται ως νέα τεχνική. [Βιβλιογραφικό audit και κενά](../../literature/PAPER_ALIGNMENT_AUDIT_2026-10-05.md).

Η επίδοση αφορά μία fixed-key campaign και ένα byte,700cropped samples, global
synthetic translations και προσθετικό Gaussian noise. Δεν έχει ελεγχθεί φυσικό
desynchronization, unknown-key/cross-device transfer, δεύτερο dataset, διαφορετικά
training seeds ή ισχυρά διαθέσιμα alignment baselines. Δεν ανακτήθηκε ολόκληρο AES key.

Επόμενο ερευνητικό βήμα: στοχευμένη primary comparison με υπάρχοντες second-order
aligners και προοπτικό πρωτόκολλο ανεξάρτητης campaign/key επιβεβαίωσης. Αν δεν υπάρχει
ουσιαστικό βιβλιογραφικό κενό, η κατεύθυνση παραμένει replication/robustness case study.
Ένα υπόλοιπο GPU training στοcap4 δεν αρκεί για νέο baseline+combined· δεν ξοδεύτηκε
χωρίς συγκεκριμένη υπόθεση. Το original final attack set παραμένει για frozen τελική
αξιολόγηση και δεν χρησιμοποιείται για τις επόμενες επιλογές.
"""
    (OUT / "REPORT_EL.md").write_text(report, encoding="utf-8")
    print(json.dumps({"rows": len(rows), "cpu_experiment_seconds": total_seconds,
                      "phase_three_support_criterion_met": support, "report": str(OUT / "REPORT_EL.md")}, indent=2))


if __name__ == "__main__":
    main()
