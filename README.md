# Hardware Security × Neural Networks

Ερευνητικό project εξαμήνου: profiling side-channel analysis σε masked AES,
με Python/PyTorch, ανάπτυξη σε Windows CPU και μεγαλύτερα πειράματα στο Kaggle GPU.
Το αρχικό pipeline λειτουργεί. Η πρωτοτυπία και η αποτελεσματικότητα των augmentations
δεν έχουν ακόμη επιβεβαιωθεί.

Τρέχον παραδοτέο: [ενιαία ελληνική ερευνητική αναφορά](outputs/study_synthesis_2026-10-05/REPORT_EL.md)
με τα τρία CNN failures, τις CPU διαγνώσεις, τα όρια και το πραγματικό κόστος.
Η [αναπαραγωγή από καθαρό CPU περιβάλλον](outputs/cpu_reproduction_2026-10-05/REPORT_EL.md)
ολοκληρώθηκε: 44 tests, ίδια best/last CNN metrics και ακριβώς ίδια sensitivity arrays.
Το αρχικό ερώτημα augmentation παραμένει αναπάντητο μετά το failed gate.
Η [βιβλιογραφική ενημέρωση της 5/10](literature/PRIMARY_AUDIT_2026-10-05.md)
ελέγχει primary protocols και καταγράφει κενά πρόσβασης, χωρίς novelty claim.

Με νέα εντολή χρήστη για πειράματα προς paper, ολοκληρώθηκαν
[τρεις πρόσθετες CPU φάσεις](outputs/paper_extension_2026-10-05/REPORT_EL.md):
trace-only alignment, έλεγχος συντεταγμένων και επιλογή σημείων μόνο από training labels.
Στο τρίτο disjoint profiling confirmation, raw shift ±5/σ=1,3: Gaussian alignment
20/20 και 18/20 έναντι fixed 0/20 και 0/20. Στο ±10/σ=2,6: 6/20 και 0/20.
57 tests passed, 5.760 ανεξάρτητοι CPA endpoint έλεγχοι, κανένα νέο Kaggle training.
Η πρωτοτυπία παραμένει ανεπιβεβαίωτη· τα αποτελέσματα ενσωματώθηκαν στη §12 της εργασίας.

Η [τέταρτη CPU φάση](outputs/paper_alignment_controls_2026-10-05/REPORT_EL.md)
συνέκρινε γνωστές SAD παραλλαγές και λανθασμένη αντιστοίχιση shifts σε νέο confirmation5k.
Gaussian/NCC/SAD mean έδωσαν20/20 και20/20 στο±5/σraw1,3· wrong-row0/20,0/20.
Η SAD ισοφαρίζει το primary SR endpoint, άρα δεν τεκμηριώνεται Gaussian advantage.
61 tests passed/14 υπάρχοντα warnings. Τέσσερις φάσεις:400 summaries/8.000 execution
endpoint checks,112 πρόσθετα replays. Ενσωματώθηκαν στη§13, χωρίς νέο Kaggle training.

Η [πέμπτη CPU φάση](outputs/paper_variable_campaign_2026-10-05/REPORT_EL.md)
επανέλαβε το παγωμένο πρωτόκολλο στο επίσημο ASCAD variable-key1400samples,
με νέο training-only fit10k και διαφορετικό πραγματικό attack key, απόν από το training.
Combined5: όλες οι μέθοδοι0/20,0/20· clean Gaussian15/20,0/20 έναντι fixed10/20,0/20.
Το κριτήριο γενίκευσης απέτυχε. Οι noise factors είναι ίδιοι, αλλά σraw4,8/9,6 εδώ·
δεν απομονώνεται η αλλαγή κλειδιού από τις υπόλοιπες διαφορές καμπάνιας.
65 tests passed. Προστέθηκαν48 summaries/960 execution checks· §14 της εργασίας.
Το νέο attack subset είναι πλέον viewed evidence, αποκλεισμένο από tuning.
Το αρχικό fixed-key attack παραμένει κλειστό. Ένα notebook/3 GPU trainings διατηρούνται.

Στις6/10 ολοκληρώθηκε [έλεγχος επιλεγμένου σήματος και τυχαίων maxima](outputs/paper_selection_audit_2026-10-06/REPORT_EL.md)
σε νέο profiling5k ανά καμπάνια, με τα ήδη παγωμένα σημεία. Τρία από τέσσερα ζεύγη
πέρασαν signed-correlation confirmation: δύο fixed-key και variable pair1.
Το variable pair2 είχε r−0,026326/pBonferroni0,092 και δεν πέρασε το criterion.
Το training score του δεν ξεχωρίζει από συνήθη μεγάλα τυχαία maxima μετά την πλήρη
αναζήτηση· δεν αποδεικνύεται μηδενική διαρροή ή causal overfitting.70tests passed,
κανένα attack payload/key read ή νέοGPU. Ενσωμάτωση στη§15 της εργασίας.

Ένα **trace** είναι μια ακολουθία μετρήσεων φυσικής διαρροής κατά την κρυπτογράφηση.
Στο **profiling**, ο επιτιθέμενος διαθέτει μετρήσεις με γνωστές εσωτερικές τιμές και
εκπαιδεύει ένα μοντέλο. Το μοντέλο εκτιμά 256 πιθανότητες για ένα ενδιάμεσο AES byte.
Στην αξιολόγηση, το γνωστό plaintext μετατρέπει αυτές τις πιθανότητες σε βαθμολογίες
για κάθε υποψήφιο key byte. Πολλά traces συνδυάζονται για να διακριθεί το σωστό byte.
Ο στόχος μας είναι **ένα byte**, όχι ολόκληρο κλειδί AES.

## Έναρξη σε Windows

Απαιτείται Python 3.11+ 64 bit. Στην πρώτη συνεδρία βρέθηκε Python 3.12.14 από το
bundled runtime του Codex και δημιουργήθηκε `.venv`. Δεν χρειάζεται activation:

```powershell
# From the project root, once Python is installed:
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
& .\.venv\Scripts\python.exe -m pytest -q
```

Στο παρόν laptop το `.venv` είναι ήδη εγκατεστημένο, παρότι το `py` δεν εντοπίζει system Python.
Το base executable που χρησιμοποιήθηκε ήταν
`C:\Users\nickb\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.
Αν αφαιρεθεί αυτό το runtime, μπορεί να χρειαστεί αναδημιουργία του `.venv` με κανονική Python.
Το `requirements-lock-cpu.txt` καταγράφει ακριβώς την εγκατάσταση της πρώτης συνεδρίας·
η editable Git αναφορά στο τέλος δείχνει παλιότερο commit. Δεν είναι CUDA lockfile.
Για το τρέχον frozen source χρησιμοποιείται το νέο `requirements-lock-cpu-reproduction.txt`
με hashes· [οδηγίες και όρια αναπαραγωγής](docs/CPU_REPRODUCTION.md).

## Πραγματικά δεδομένα και CPU pilot

```powershell
& .\.venv\Scripts\python.exe scripts/download_ascad.py
& .\.venv\Scripts\python.exe -m sca.cli inspect data/ASCAD.h5 --output outputs/ascad_inspection.json
& .\.venv\Scripts\python.exe -m sca.cli train --config configs/pilot_real.json --run-dir runs/ascad_cpu_pilot_new
& .\.venv\Scripts\python.exe -m sca.cli evaluate --run-dir runs/ascad_cpu_pilot_new --config configs/evaluation_pilot.json --split validation --device cpu
```

Η λήψη αποσπά αποκλειστικά το προεπεξεργασμένο HDF5 από το επίσημο ZIP και ελέγχει
το επίσημο checksum. Δεν κατεβάζει raw traces. Το HDF5 έχει 50.000×700 profiling,
10.000×700 attack, traces int8, labels int64 και structured metadata.
Πηγή/schema: [επίσημος κώδικας παραγωγής](https://github.com/ANSSI-FR/ASCAD/blob/master/ASCAD_generate.py).

Τα paths των configs είναι σχετικά με τον τρέχοντα root· `--dataset`, `--run-dir`,
`--device cpu|cuda|auto` και `--epochs` επιτρέπουν αλλαγή χωρίς αντιγραφή κώδικα.
Η εκπαίδευση σταματά αν το πραγματικό dataset δεν έχει το επίσημο fixed-key checksum.
Το attack set δεν ανοίγεται για εκπαίδευση ή επιλογή μοντέλου.

## Συνθετική δοκιμή και checkpoint

```powershell
& .\.venv\Scripts\python.exe -m sca.cli synthetic data/synthetic_new.h5
& .\.venv\Scripts\python.exe -m sca.cli train --config configs/pilot_synthetic.json --dataset data/synthetic_new.h5 --run-dir runs/synthetic_new
& .\.venv\Scripts\python.exe -m sca.cli train --config configs/pilot_synthetic.json --dataset data/synthetic_new.h5 --run-dir runs/synthetic_new --epochs 3 --resume
```

Το fixture είναι τεχνητή, unmasked διαρροή bits για **έλεγχο κώδικα**.
Η συνέχιση γίνεται στα όρια epochs, με model/optimizer, Python/NumPy/Torch/CUDA RNG
και RNG του shuffle. Για ακριβή συνέχεια επιτρέπεται αύξηση epochs και μεταφορά paths,
με ίδιο περιεχόμενο δεδομένων, code hash, συσκευή, dependencies και ρυθμίσεις.
Φορτώνουμε μόνο έμπιστα δικά μας checkpoints (`torch.load` περιέχει Python objects).
Τα υπάρχοντα run directories προστατεύονται από ακούσια αντικατάσταση.

## Baseline και τελική αξιολόγηση

Το [Kaggle notebook](notebooks/kaggle_baseline.ipynb) καλεί τον ίδιο κώδικα.
Κρατάμε **ένα notebook και δύο τρέχουσες CNN στρατηγικές**: none/combined,
10.000 traces, seed0, 50 epochs. Το προηγούμενο πλάνο 46 trainings αντικαταστάθηκε μετά
από αίτημα του χρήστη για ελάχιστο Kaggle κόστος. Το MLP και δεύτερα budgets/seeds δεν εκτελούνται.

Στο ίδιο αρχείο αλλάζουμε μόνο `STAGE`: `benchmark` (οι πρώτες 3 epochs του none),
`baseline` (ολοκλήρωση/επαναχρησιμοποίηση του baseline σε50), `compare` (baseline και conditional combined),
`attack` (μόνο αξιολόγηση μετά το protocol freeze). Ολοκληρωμένα runs και ίδιες evaluations
επαναχρησιμοποιούνται. Οι 3 benchmark epochs περιλαμβάνονται στις 50· δεν υπάρχει extra training.
Ένα seed επιτρέπει διερευνητική σύγκριση και όχι εκτίμηση training variability.

Η ενεργή έκδοση έχει `STAGE="compare"`, `RUN_TAG="minimal_v3_literature"`,
`model="cnn_literature"`,16.952 parameters και train-only per-position MinMax.
Το ίδιο notebook εκτελεί baseline50epochs και combined μόνο αν clean validation
SR@2.000≥0,90 (18/20), με το minimum-CE checkpoint. Διαφορετικά εξάγει το failure
χωρίς να ξεκινήσει combined. Έως4 trainings συνολικά με τα δύο ιστορικά failures.

Ιστορικό: το αρχικό ReLU baseline ολοκληρώθηκε στο ίδιο `con1los/hw-sec-exp2`, version3:
συνέχεια epoch3→50, ίδιο περιβάλλον/splits/source. Clean validation SR@2.000=0/20·
best checkpoint epoch2. Η [αναφορά baseline](outputs/kaggle_baseline_v3_2026-10-03/REPORT_EL.md)
περιέχει ελεγμένες καμπύλες και περιορισμούς.
Ο χρήστης ενέκρινε ένα διορθωτικό baseline με LeakyReLU0,1 μετά τη διάγνωση inactive units.
Η προηγούμενη έκδοση χρησιμοποίησε `model="cnn_leaky"`, `RUN_TAG="minimal_v2_leaky"`, ίδιο
seed/split/budget/optimizer. Το παλιό ReLU run διατηρείται. Το τότε πλάνο έως5
trainings αντικαταστάθηκε πριν γίνουν οι augmentations. Η version5 ολοκλήρωσε το διορθωμένο
baseline από epoch0→50. Best epoch1 / CE5,547114, clean validation GE89,25 / SR0/20.
Στην epoch50 train CE5,267826, validation CE5,809435: η γενίκευση παραμένει ανεπαρκής.
Η [αναφορά διορθωτικού baseline](outputs/kaggle_leaky_v5_2026-10-03/REPORT_EL.md)
περιέχει την επαλήθευση και τη σύγκριση. Έγιναν δύο πλήρη GPU trainings συνολικά.
Οι τότε προγραμματισμένες3 augmentations δεν εκτελέστηκαν και το πλάνο αντικαταστάθηκε.
Η [διάγνωση masking](outputs/masking_diagnosis_2026-10-03/REPORT_EL.md) βρήκε
mask/share leakage και training-selected centered products που διατηρούν διαρροή
στο validation. Δεν αποδεικνύουν key recovery. Προετοιμάστηκε untrained literature
CNN prototype16.952 parameters. Ο χρήστης ενέκρινε την ενσωμάτωσή του και το μειωμένο
πλάνο baseline/combined. Η έκδοση δεν αποτελεί ακριβή αναπαραγωγή της δημοσίευσης.
Το ενεργό Input packet είναι `outputs/kaggle_resume_input_literature.zip`.
Η version7 ολοκλήρωσε το νέο baseline: best epoch4, clean validation CE5,560782,
GE114,25 και SR0/20. Το gate18/20 απέτυχε, επομένως combined δεν εκπαιδεύτηκε.
Έγιναν3 πλήρη GPU trainings συνολικά στο ίδιο notebook. Η
[νέα αναφορά](outputs/kaggle_literature_v7_2026-10-03/REPORT_EL.md) περιέχει τους
ελέγχους, το κόστος και τους περιορισμούς. Καμία νέαGPU εκτέλεση δεν ξεκινά αυτόματα.
Στη [CPU διάγνωση της4/10](outputs/literature_diagnosis_2026-10-04/REPORT_EL.md),
δεύτερης τάξης συσχέτιση με δύο ήδη training-selected ζεύγη ανέκτησε το byte σε20/20
clean validation permutations. Το CNN διατηρεί mask/share signal, αλλά ανεπαρκές
unmasked-target generalization. Training-only BN recalibration δεν αποκατέστησε SR.
Ο στατιστικός έλεγχος είναι διαγνωστικός, με διαφορετική πληροφορία στην επιλογή
features· δεν αντικαθιστά το CNN gate. Παραμένουν3 GPU trainings και1 notebook.
Στον [CPU έλεγχο ευαισθησίας της 5/10](outputs/correlation_robustness_2026-10-05/REPORT_EL.md),
θόρυβος σ=0,1 διατηρεί 20/20 και στα δύο σταθερά ζεύγη, ενώ ο συνδυασμός με
μετατόπιση ±5 πέφτει σε 1/20 και 11/20. Με γνωστή τεχνητή μετατόπιση η εξαγωγή
επανέρχεται σε 20/20· αυτό είναι oracle διάγνωση, όχι έτοιμη πρακτική ευθυγράμμιση.
Στο σ=0,2 το oracle δεν φτάνει 18/20. Πέρασαν 640 endpoint checks και 44 tests,
χωρίς νέο GPU training.
Το original fixed-key final attack παραμένει κλειστό. Η σύνθεση και η αναπαραγωγή
σε νέο CPU venv ολοκληρώθηκαν. Οι έξι paper CPU φάσεις περιλαμβάνονται στην
εργασία, μαζί με το failed primary criterion σε νέο variable-key attack subset.
Το signal-replication/permutation audit ολοκληρώθηκε. Πρόσθετη μεθοδολογική πρόταση
χρειάζεται νέο frozen training-only plan και unused profiling confirmation.
Τα εξετασμένα confirmation/νέοattack subsets δεν χρησιμοποιούνται
για tuning ή ως αθέατες επιβεβαιώσεις. Το GPU cap4 διατηρείται.
Το fresh-start opt-in αφορά μόνο το εγκεκριμένο νέο baseline· μετά την ολοκλήρωση
το packet διατηρεί το νέο checkpoint και η πρώτη cell απαιτεί restore.
Τα `kaggle_resume_input_leaky.zip` και `kaggle_resume_input.zip` διατηρούν τα παλιά
checkpoints/source snapshots και δεν ταιριάζουν με την ενεργή έκδοση.
Η διορθωμένη πρώτη cell κάνει discovery/restore και εμφανίζει τα paths και το ολοκληρωμένο epoch.
Για αντιγραφή στο ίδιο Kaggle notebook υπάρχει το `outputs/kaggle_first_cell.py`.

```powershell
# Only after freezing the protocol and checkpoint-selection rule:
& .\.venv\Scripts\python.exe -m sca.cli evaluate --run-dir runs/minimal_v3_literature/none_seed0 --config configs/evaluation_final.json --split attack
```

Κάθε run γράφει config, inspection, train/validation indices, split ID, normalizer,
εκδόσεις, συσκευή, Git commit όπου υπάρχει, source hash, χρόνο, steps, history,
`best.pt`, `last.pt` και summary. Η αξιολόγηση γράφει GE/SR curves ως CSV/NPZ,
ανά επανάληψη ranks, censoring, χρόνους και PNG. Το checkpoint επιλέγεται με ελάχιστο
clean validation cross-entropy, από κοινό και σταθερό πλήθος epochs.

## Αρχεία για τη συνέχεια

- [PROJECT_PLAN.md](PROJECT_PLAN.md): ερώτημα, milestones και αποφάσεις.
- [PROGRESS.md](PROGRESS.md): πραγματική κατάσταση και ακριβές επόμενο βήμα.
- [Πρωτόκολλο](docs/EXPERIMENT_PROTOCOL.md): splits, threat model, μετασχηματισμοί και μετρικές.
- [Αναπαραγωγή σε CPU](docs/CPU_REPRODUCTION.md): exact hashed dependencies και ελεγμένο replay.
- [Νέα πειράματα για paper](outputs/paper_extension_2026-10-05/REPORT_EL.md): τρεις φάσεις,
  disjoint confirmations, training-label-only επιλογή, θετικά και αρνητικά αποτελέσματα.
- [SAD και έλεγχος αντιστοίχισης](outputs/paper_alignment_controls_2026-10-05/REPORT_EL.md):
  τέταρτο disjoint confirmation, γνωστά baselines και περιορισμός Gaussian novelty claim.
- [Kaggle](docs/KAGGLE.md): setup, έλεγχος GPU quota, benchmark και αποθήκευση.
- [Βιβλιογραφία](literature/REVIEW.md): συγκριτικός πίνακας, επιβεβαιωμένα στοιχεία και κενά πρόσβασης.
- [Διάγνωση masking και αρχιτεκτονικής](outputs/masking_diagnosis_2026-10-03/REPORT_EL.md):
  profiling-only έλεγχοι και συγκεκριμένη πρόταση συνέχειας χωρίς νέα GPU εκτέλεση.
- [Αναφορά πρώτης συνεδρίας](outputs/SESSION_REPORT_EL.md): τι εκτελέστηκε και τι σημαίνουν τα αποτελέσματα.
- [Πρώτο Kaggle benchmark](outputs/kaggle_benchmark_2026-10-03_07b13e6f/REPORT_EL.md):
  πραγματικό 3-epoch T4 output και συνέχεια στο ίδιο baseline checkpoint.

Τα `data/`, `runs/`, `.venv/` αγνοούνται από το Git. Τα επιλεγμένα παραδοτέα είναι στο `outputs/`.
Μην διαβάζετε έναν χαμηλό classification loss ως απόδειξη ανάκτησης κλειδιού.
