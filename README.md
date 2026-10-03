# Hardware Security × Neural Networks

Ερευνητικό project εξαμήνου: profiling side-channel analysis σε masked AES,
με Python/PyTorch, ανάπτυξη σε Windows CPU και μεγαλύτερα πειράματα στο Kaggle GPU.
Το αρχικό pipeline λειτουργεί. Η πρωτοτυπία και η αποτελεσματικότητα των augmentations
δεν έχουν ακόμη επιβεβαιωθεί.

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
το απόλυτο editable path στο τέλος αφορά αυτό το laptop. Δεν είναι CUDA lockfile.

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
Κρατάμε **ένα notebook και τέσσερις CNN εκπαιδεύσεις συνολικά**: none/noise/shift/combined,
10.000 traces, seed0, 50 epochs. Το προηγούμενο πλάνο 46 trainings αντικαταστάθηκε μετά
από αίτημα του χρήστη για ελάχιστο Kaggle κόστος. Το MLP και δεύτερα budgets/seeds δεν εκτελούνται.

Στο ίδιο αρχείο αλλάζουμε μόνο `STAGE`: `benchmark` (οι πρώτες 3 epochs του none),
`baseline` (συνέχιση του ίδιου checkpoint σε 50), `compare` (οι άλλες 3 στρατηγικές),
`attack` (μόνο αξιολόγηση μετά το protocol freeze). Ολοκληρωμένα runs και ίδιες evaluations
επαναχρησιμοποιούνται. Οι 3 benchmark epochs περιλαμβάνονται στις 50· δεν υπάρχει extra training.
Ένα seed επιτρέπει διερευνητική σύγκριση και όχι εκτίμηση training variability.

Η τελευταία έκδοση έχει προεπιλογή `STAGE="baseline"`, αφού το GPU benchmark ολοκληρώθηκε.
Το baseline πλέον ολοκληρώθηκε μέσω API στο ίδιο `con1los/hw-sec-exp2`, version3:
συνέχεια epoch3→50, ίδιο περιβάλλον/splits/source. Clean validation SR@2.000=0/20·
best checkpoint epoch2. Η [αναφορά baseline](outputs/kaggle_baseline_v3_2026-10-03/REPORT_EL.md)
περιέχει ελεγμένες καμπύλες και περιορισμούς. Διάγνωση πριν τις άλλες3 στρατηγικές.
Για νέο session ανέβασε το ενιαίο `outputs/kaggle_resume_input.zip` ως Input.
Η διορθωμένη πρώτη cell κάνει discovery/restore και εμφανίζει τα paths και το ολοκληρωμένο epoch.
Για αντιγραφή στο ίδιο Kaggle notebook υπάρχει το `outputs/kaggle_first_cell.py`.

```powershell
# Only after freezing the protocol and checkpoint-selection rule:
& .\.venv\Scripts\python.exe -m sca.cli evaluate --run-dir runs/minimal_v1/none_seed0 --config configs/evaluation_final.json --split attack
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
- [Kaggle](docs/KAGGLE.md): setup, έλεγχος GPU quota, benchmark και αποθήκευση.
- [Βιβλιογραφία](literature/REVIEW.md): συγκριτικός πίνακας, επιβεβαιωμένα στοιχεία και κενά πρόσβασης.
- [Αναφορά πρώτης συνεδρίας](outputs/SESSION_REPORT_EL.md): τι εκτελέστηκε και τι σημαίνουν τα αποτελέσματα.
- [Πρώτο Kaggle benchmark](outputs/kaggle_benchmark_2026-10-03_07b13e6f/REPORT_EL.md):
  πραγματικό 3-epoch T4 output και συνέχεια στο ίδιο baseline checkpoint.

Τα `data/`, `runs/`, `.venv/` αγνοούνται από το Git. Τα επιλεγμένα παραδοτέα είναι στο `outputs/`.
Μην διαβάζετε έναν χαμηλό classification loss ως απόδειξη ανάκτησης κλειδιού.
