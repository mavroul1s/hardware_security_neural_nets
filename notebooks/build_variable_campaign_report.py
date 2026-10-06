"""Create the Greek campaign-replication report from verified, frozen evidence."""
import csv
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sca.train import write_json
from paper_alignment import ROOT, read, sha

OUT = ROOT / "outputs/paper_variable_campaign_2026-10-05"
LABELS = {"fixed": "Fixed", "ncc_template": "NCC", "gaussian_template": "Gaussian",
          "sad_training_mean": "SAD mean", "gaussian_offsets_rolled": "Gaussian wrong row",
          "known_injected_shift": "Known injected shift"}


def main():
    plan, fit, record, verified = (read(OUT / name) for name in ("plan.json", "fit.json", "results.json", "verification.json"))
    for name, expected in verified["artifact_sha256"].items():
        assert sha(OUT / name) == expected
    lookup = {(r["condition"], r["method"], r["family"]): r for r in record["results"]}
    conditions = [c["name"] for c in plan["conditions"]]
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
    colors = ["#2463a5", "#20804e", "#dc7d16", "#7851a9", "#727980", "#b3444e"]
    for column, family in enumerate(("pair1", "pair2")):
        for method, color in zip(plan["methods"], colors):
            values = [lookup[(c, method, family)] for c in conditions]
            axes[0, column].plot(range(4), [v["sr_at_budget"] for v in values], marker="o", color=color, label=LABELS[method])
            axes[1, column].plot(range(4), [v["ge_at_budget"] for v in values], marker="o", color=color)
        axes[0, column].set_title(f"{family}: {fit['pairs'][family]}")
        axes[0, column].axhline(.9, color="#999999", linestyle="--", linewidth=1)
        axes[0, column].set_ylim(-.04, 1.04)
        axes[0, column].set_ylabel("SR @2,000")
        axes[1, column].set_ylabel("Mean rank @2,000")
        axes[1, column].set_yscale("symlog", linthresh=1)
        axes[1, column].set_ylim(0, 255)
        axes[1, column].set_xticks(range(4), ["Original", "Extra shift ±5", "±5 + sigma 4.8", "±10 + sigma 9.6"], rotation=12)
        for ax in axes[:, column]:
            ax.grid(alpha=.2)
    fig.suptitle("ASCAD variable-key campaign: one new attack key, 20 overlapping orders\nFresh 10k profiling fit; original traces already have natural timing variation", fontsize=12)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(.5, .002))
    fig.tight_layout(rect=(0, .095, 1, .91))
    fig.savefig(OUT / "campaign_replication.png", dpi=160)
    plt.close(fig)
    with (OUT / "recovery_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(record["results"][0]))
        writer.writeheader()
        writer.writerows(record["results"])
    table = ["| Μέθοδος | Clean pair1 / pair2 | Shift5 pair1 / pair2 | Combined5 pair1 / pair2 | OOD pair1 / pair2 |",
             "|---|---:|---:|---:|---:|"]
    for method in plan["methods"]:
        cells = [" / ".join(f"{round(lookup[(c, method, f)]['sr_at_budget'] * 20)}/20" for f in ("pair1", "pair2")) for c in conditions]
        table.append("| " + LABELS[method] + " | " + " | ".join(cells) + " |")
    validation = {(r["condition"], r["method"], r["family"]): r for r in record["validation_correlations"]}
    coefficient_table = ["| Ζεύγος | Training correlation | Clean validation fixed | Clean validation Gaussian |",
                         "|---|---:|---:|---:|"]
    for family in ("pair1", "pair2"):
        coefficient_table.append(f"| {family} | {fit['training_coefficients'][family]:.6f} | "
            f"{validation[('clean', 'fixed', family)]['hw_correlation']:.6f} | "
            f"{validation[('clean', 'gaussian_template', family)]['hw_correlation']:.6f} |")
    provenance = read(ROOT / "data/ASCAD_variable.provenance.json")
    four_phase_seconds = sum(read(ROOT / "outputs" / name / "results.json")["seconds"] for name in
        ("paper_alignment_2026-10-05", "paper_alignment_coordinates_2026-10-05", "paper_maskfree_2026-10-05", "paper_alignment_controls_2026-10-05"))
    report = f"""# Επιβεβαίωση CPU πρωτοκόλλου σε νέα ASCAD καμπάνια — 5/10/2026

Το παγωμένο πρωτόκολλο δεν κάλυψε το κριτήριο γενίκευσης σε νέα καμπάνια και νέο attack key.
Στη combined5 όλες οι έξι μέθοδοι έδωσαν **0/20 και στα δύο training-selected ζεύγη**.
Στα αρχικά δεδομένα χωρίς πρόσθετη αλλοίωση, το pair1 έδωσε Fixed10/20,
Gaussian15/20, NCC14/20 και SAD12/20· το pair2 απέτυχε παντού.
Οι20 σειρές είναι επικαλυπτόμενες επιλογές από το ίδιο pool5k, **ένα κλειδί και ένα training split**.
Οι παλαιότερες επιτυχίες στο fixed-key profiling παραμένουν καταγεγραμμένες,
αλλά δεν επαρκούν για γενικό ισχυρισμό robustness ή για paper νέας μεθόδου.

## 1. Πρωτογενής πηγή και πρόσβαση

Αποκτήθηκε μόνο το επίσημο αρχικό extracted variable-key αρχείο, όχι raw71GB,
πρόσθετα desync50/100 datasets ή pretrained CNNs. Οι δημιουργοί περιγράφουν αυτή την
καμπάνια ως ήδη ασυγχρόνιστη, με δύο τυχαία κλειδιά και μία σταθερού κλειδιού
καταγραφή ανά τρεις. Τα επίσημα [στοιχεία και checksum]({plan['official_source']}) και
οι [παράμετροι διαχωρισμού](https://github.com/ANSSI-FR/ASCAD/blob/master/ATMEGA_AES_v1/ATM_AES_v1_variable_key/example_generate_params)
ελέγχθηκαν στις5/10/2026. Το example αφορά desync100· το αρχείο εδώ είναι το original,
επαληθευμένο από το διαφορετικό επίσημο checksum του.

Το τοπικό αρχείο έχει {provenance['bytes']:,}bytes, profiling200k/attack100k,
1400int8 δείγματα/trace και identity labels για zero-based byte2, επαληθευμένα στις
επιλεγμένες training/evaluation rows. SHA-256:
`{plan['dataset_sha256']}`.
Το [download provenance](../../data/ASCAD_variable.provenance.json) αποθηκεύει URL,
bytes, UTC και πραγματικό χρόνο λήψης. Το αρχικό fixed-key αρχείο700samples διατηρήθηκε.

## 2. Προοπτικό πρωτόκολλο και περιορισμοί ερμηνείας

Το [plan.json](plan.json) παγώθηκε πριν την ανάγνωση τιμών: profiling10k training/5k validation,
splitseed2026, ξεχωριστό attack5k από100k με subsetseed20261009. Δεν υπάρχει νέα training
seed ή optimizer. Επιλογή δύο centered-product ζευγών με absolute Pearson προς
HW των παρεχόμενων training identity labels, separation50/diversity20. Εξαιρέθηκαν
προκαθορισμένα μόνο τα πρώτα/τελευταία10 σημεία για ασφαλή εξαγωγή υπό shifts±10:
{fit['candidate_pairs']:,} υποψήφια ζεύγη. Training raw traces χωρίς προηγούμενο alignment.

Το [fit.json](fit.json) και το [fit.npz](fit.npz) γράφτηκαν πριν από το
[evaluation access record](evaluation_access.json): pairs {fit['pairs']['pair1']},
{fit['pairs']['pair2']}, raw unconditional training mean/diagonal variance,
floor=max(median variance×1e−6,1e−12). Δεν διαβάστηκαν keys/masks για fit/selection.
Η matrix επιλογή και εγγραφή fit χρειάστηκε {fit['fit_seconds']:.6f}s, περιλαμβανόμενα
στο συνολικό χρόνο. Δεν πραγματοποιήθηκε fit μετά τη validation ή attack αξιολόγηση.

Πρόκειται για **επανάληψη του πρωτοκόλλου με νέο fit στην καμπάνια**, όχι zero-shot
μεταφορά των παλαιών σημείων ή CNN checkpoint. Οι1400samples προέρχονται από το νέο
επίσημο window· το frozen CNN700samples δεν χρησιμοποιήθηκε εδώ. Η νέα καμπάνια
αλλάζει μαζί με κλειδιά, φυσική χρονική μεταβλητότητα, window και fitting δεδομένα.
Δεν απομονώνεται αιτιωδώς η επίδραση μόνο της αλλαγής κλειδιού και δεν αποδεικνύεται
διαφορετική φυσική συσκευή. Τα δύο datasets ανήκουν στην ίδια οικογένεια υλοποίησης.

NCC/Gaussian/SAD mean: trace-only search±10 στο window20:1380, κοινό tie rule
μικρότερο|offset|/negative-first. Η SAD είναι η ήδη τεκμηριωμένη προσαρμογή, όχι νέα
τεχνική ή ακριβής αναπαραγωγή ChipWhisperer. Το wrong-row control διατηρεί histogram
και αλλάζει αντιστοίχιση. Το known injected shift αφαιρεί μόνο την πρόσθετη τεχνητή
μετατόπιση· η φυσική ασυγχρονία παραμένει άγνωστη, άρα δεν είναι πλήρες alignment oracle.

Training median range={fit['training_range_median']:.0f} raw units, συνεπώς σcombined5=4,8,
σOOD=9,6. Τα noise factors0,1/0,2 είναι ίδια με τις προηγούμενες φάσεις, αλλά οι απόλυτες
εντάσεις διαφέρουν από1,3/2,6. Δεν είναι πείραμα ίδιου απόλυτου θορύβου μεταξύ datasets.
Common U/Z seeds9101/9102 και κοινές20 σειρές με seed8001/budget2000. Gaussian raw noise
και επιπλέον global shifts είναι synthetic stress tests πάνω σε πραγματικές traces,
όχι πρόσθετες φυσικές λήψεις ή αναπαραγωγή elastic jitter/shuffling.

## 3. Τελική επίθεση στο νέο κλειδί

Στις αξιολογημένες attack5k rows βρέθηκε ένα σταθερό πλήρες AES key, διαφορετικό από
το αρχικό fixed-key· byte2=0x22. Το πλήρες κλειδί απουσιάζει από τις10k training rows,
που έχουν10.000 διαφορετικά πλήρη κλειδιά. Αυτό ελέγχθηκε **μετά** την εγγραφή fit.
Η μέθοδος δέχεται traces μόνο. CPA υποθέσεις HW(SBOX(plaintext2 xor candidate)) για
και τους256 candidates· αληθινό key byte μόνο για τελικό rank. Δεν χρησιμοποιήθηκε
key-adjusted plaintext ή simulated constant key. Μετράται ανάκτηση ενός byte.

SR@2000, συντηρητικό rank0=μοναδικά καλύτερο, tolerance1e−12:

{chr(10).join(table)}

Στη combined5 Gaussian GE={lookup[('combined5','gaussian_template','pair1')]['ge_at_budget']:.2f}/
{lookup[('combined5','gaussian_template','pair2')]['ge_at_budget']:.2f}. Και τα δύο primary
criteria απέτυχαν: SR<0,90 και μηδενική SR βελτίωση από το fixed. Καμία γραμμή δεν φτάνει
sustainedSR90 εντός2.000 traces. Το clean15/20 στο pair1 δεν αλλάζει το primary endpoint.
Δεν επιλέχθηκε νέα μέθοδος/ζεύγος ή θόρυβος βάσει αυτών των αποτελεσμάτων.

![SR και GE της νέας καμπάνιας](campaign_replication.png)

## 4. Ανεξάρτητο profiling validation και μη διατήρηση της δεύτερης συσχέτισης

Τα validation keys μεταβάλλονται· χρησιμοποιήθηκαν μόνο descriptive correlations με
τα παρεχόμενα HW labels. Δεν συσσωρεύτηκαν ως μία επίθεση σε υποτιθέμενο σταθερό κλειδί.
Κάθε pair/μέθοδος διατηρήθηκε ανεξάρτητα από το validation αποτέλεσμα:

{chr(10).join(coefficient_table)}

Το pair2 έχει training|r|≈0,038 και σχεδόν μηδενική clean validation συσχέτιση.
Αυτό καταγράφει μη διατήρηση του selected signal εκτός training. Είναι συμβατό με
ασταθή επιλογή από πολλές candidates, αλλά δεν αποδεικνύει μόνο του causal overfitting,
μηδενική φυσική διαρροή ή αποτυχία κάθε second-order attack. Δεν αντικαταστάθηκε το pair2.

## 5. Επαλήθευση, κόστος και θέση στην εργασία

[Ανεξάρτητη επαλήθευση](verification.json):48 recovery summaries,48 validation
correlations,192 sampled shift estimates,7 πραγματικοί training pair coefficients,
48 επιπλέον endpoint replays. Κατά την εκτέλεση ελέγχθηκαν και οι960 CPA endpoints
με άλλο direct Pearson calculation. Splits/RNG/final states, timestamps fit/access,
train moments, point eligibility, key/labels και διατήρηση προηγούμενων artifacts ελέγχθηκαν.
Πλήρες suite:65passed/14 υπάρχονταwarnings, {verified['tests']['seconds']:.3f}s.

Πριν από οποιαδήποτε real-data ανάγνωση, το νέο synthetic test εντόπισε slicing μόνο
ενός αντί δύο axes στην interior matrix. Διορθώθηκε· το αρχικό plan και το failed
test1failed/64passed διατηρούνται στο [correctness amendment](protocol_correctness_fix.json).
Το νέο plan άλλαξε script hash/UTC, χωρίς αλλαγή υπερπαραμέτρων ή viewed-data tuning.

CPU πείραμα {record['seconds']:.6f}s μετά τα imports, verifier{verified['seconds']:.6f}s,
λήψη{provenance['download_seconds']:.3f}s. Το experiment time περιλαμβάνει fit και
εγγραφή/ελέγχους, όχι tests, imports, download, report ή session wall time.
Οι πέντε paper φάσεις έχουν448 recovery summaries,8.960 execution endpoint checks,
160 πρόσθετα replays και συνολικό recorded CPU experiment time
{four_phase_seconds + record['seconds']:.6f}s. Δεν είναι448 ανεξάρτητα πειράματα/κλειδιά.
Νέα GPU trainings0/optimizer updates0, συνολικά GPU trainings3, ένα Kaggle notebook,
failed CNN gate και combined absent. Το αρχικό fixed-key Attack_traces payload δεν
διαβάστηκε σε αυτή την επέκταση· το νέο variable-key attack subset είναι πλέον
**viewed evidence** και δεν επιτρέπεται να χρησιμοποιηθεί για tuning επόμενης μεθόδου.

Το αποτέλεσμα ενσωματώνεται ως αρνητική επιβεβαίωση στη§14 της ενιαίας εργασίας.
Δεν υποστηρίζεται paper νέας Gaussian τεχνικής ή γενικής robustness υπεροχής.
Χρήσιμη συνέχεια είναι προοπτική εξέταση σταθερότητας/false selections μόνο σε νέα
profiling δεδομένα, με νέο παγωμένο πλάνο· η ήδη αξιολογημένη attack5k παραμένει εκτός tuning.

Πλήρη evidence: [results.json](results.json), [CSV48γραμμών](recovery_summary.csv),
[arrays.npz](arrays.npz), [pytest.xml](pytest.xml),
[πηγές/όρια](../../literature/VARIABLE_CAMPAIGN_2026-10-05.md).
"""
    (OUT / "REPORT_EL.md").write_text(report, encoding="utf-8")
    evidence = {"results": record["results"], "validation_correlations": record["validation_correlations"],
        "primary": record["primary"], "support_criterion_met": record["replication_support_criterion_met"],
        "key_audit": record["key_audit"], "fit": fit, "paper_ready": False, "novelty_verified": False,
        "five_phase_recovery_summaries": 448, "five_phase_execution_endpoints": 8960,
        "additional_endpoint_replays": 160, "five_phase_cpu_seconds": four_phase_seconds + record["seconds"],
        "new_gpu_trainings": 0, "new_optimizer_updates": 0,
        "original_fixed_key_attack_payloads_read": False, "new_attack_subset_viewed": True,
        "tests": verified["tests"], "input_sha256": {name: sha(OUT / name) for name in
            ("plan.json", "fit.json", "results.json", "verification.json", "pytest.xml")}}
    write_json(OUT / "evidence.json", evidence)
    print("Built:", OUT / "REPORT_EL.md")


if __name__ == "__main__":
    main()
