# Κατάσταση project — 2026-10-03

## Συμφωνημένο πλαίσιο

Εξάμηνο διαθέσιμο, χωρίς συγκεκριμένα κριτήρια μαθήματος. Ο χρήστης έχει Kaggle GPU access.
Ακριβής ημερομηνία παράδοσης και προσωπικό GPU quota δεν έχουν δοθεί/ελεγχθεί.
Ανάπτυξη στα ελληνικά ως επικοινωνία, κώδικας στα αγγλικά. Καμία ανάγκη API keys/πληρωμένων υπηρεσιών.
Νεότερη απαίτηση χρήστη: ελάχιστες Kaggle εκπαιδεύσεις/notebooks. Συμφωνημένο νέο πλάνο:
**ένα notebook, 4 CNN trainings, 10k training traces, seed0**. Τα πρώτα 3 benchmark epochs
συνεχίζονται στο ίδιο none baseline, χωρίς πρόσθετο run. Δεν εκτελούνται MLP/5k/multiple seeds.

## Ολοκληρωμένα στην πρώτη συνεδρία

- Το αρχικό workspace ήταν κενό εκτός από `.git`, χωρίς commits ή υπάρχουσες οδηγίες.
- CPU: Ryzen 5 7535HS, 12 logical CPUs. Python3.12.14 από Codex runtime,
  απομονωμένο `.venv`, PyTorch2.8.0+cpu, pinned core dependencies και πλήρες freeze.
- Υλοποίηση HDF5 inspection/loading, byte2 identity labels, train-only normalization,
  nested train/validation splits, MLP/CNN, online noise/shift/combined, training,
  checkpoints με RNG και source snapshots, explicit validation/attack evaluation, GE/SR/CSV/PNG.
- Επίσημο ASCAD.h5 αποκτήθηκε με HTTP ranges: 46.566.904 bytes το αρχείο,
  23.880.483 bytes μεταφοράς, χωρίς raw archive. Επίσημο SHA-256 verified.
- Ελέγχθηκαν όλα τα profiling και attack labels έναντι metadata. Στην εκπαίδευση,
  attack labels/keys δεν διαβάζονται. Το schema-only inspection είναι χωριστό από attack metrics.
- 50k×700 profiling, 10k×700 attack, int8 traces, int64 labels,
  plaintext/ciphertext/key/masks uint8[16], desync uint32[1].
- Meaningful tests για AES/candidates, oracle/ties/censoring, splits/normalization,
  transforms, HDF5, model shapes, pipeline, exact resume και validation/attack paths.
  Τελικός έλεγχος: 15 passed, 14 dependency deprecation warnings, 5,99 s.
  Το `pip check` δεν βρήκε ασύμβατες εξαρτήσεις.
  Μετά την αλλαγή σε ελάχιστο Kaggle πλάνο: **16 passed, 14 warnings, 10,10 s**.
  Περιλαμβάνονται έλεγχοι ότι completed checkpoints/evaluations επαναχρησιμοποιούνται
  και dry run των notebook stages χωρίς πέμπτο μοντέλο ή πρόσθετα training epochs.
- Έγινε πραγματικός CPU pilot (2048 train / 512 validation / 3 epochs), και δύο
  επαναλήψεις verification με ακριβώς ίδια losses/GE/SR. Δεν είναι independent-seed replication.
  Κύριο τελικό artifact: `runs/ascad_cpu_release`, με snapshot του κώδικα και καταγεγραμμένο hash.
- Έγινε synthetic CPU smoke test 384/128, 2 epochs και synthetic ranking· code validation μόνο.
- Έγινε training-only boundary audit 10k/5k. First-order identity SNR είναι αδύναμο και
  δεν πιστοποιεί διατήρηση masked leakage· sensitivity παραμένει ανοιχτό.
- Δημιουργήθηκαν literature comparison/BibTeX για 10 εργασίες, πρωτόκολλο και σχέδιο εξαμήνου.
  Πρόσβαση σε ορισμένα full papers παραμένει περιορισμένη και αναφέρεται ανά εργασία.
- Αρχικά δημιουργήθηκαν Kaggle notebook/code bundle με 4 GPU benchmarks και CNN/MLP baselines.
  Αντικαταστάθηκαν από το ενιαίο ελάχιστο workflow `benchmark/baseline/compare/attack`:
  ένα reusable benchmark, ίδιο none baseline και τρεις επιπλέον CNN στρατηγικές.
  Προστέθηκαν ασφαλής επαναχρησιμοποίηση completed runs και cache evaluations.
  Ελέγχθηκαν συντακτικά οι 6 code cells, χωρίς αποθηκευμένα execution outputs.
  Το bundle εξαιρεί δεδομένα, runs, checkpoints, `.venv` και `.git`.
  Κατά την αρχική δημιουργία δεν είχε εκτελεστεί στο Kaggle. Αργότερα παραλήφθηκε
  πραγματικό benchmark output (βλ. παρακάτω). Το προσωπικό GPU quota δεν καταγράφηκε.

Οι τοπικοί stage checks είναι orchestration dry runs και synthetic CPU tests, όχι πραγματικές
GPU εκτελέσεις. Ο νέος πηγαίος κώδικας έχει διαφορετικό hash από τα ιστορικά ASCAD pilots·
τα original snapshots/manifests διατηρούνται ώστε τα παλιά πραγματικά αποτελέσματα να είναι αναπαραγώγιμα.

## Πραγματικά αποτελέσματα έως τώρα

Τα CPU pilots δεν απέδειξαν ανάκτηση. Clean validation GE@128=125,8, SR@128=0%,
10 attack-order repetitions από pool512, selected epoch1. Το τελικό attack/test δεν
χρησιμοποιήθηκε για metrics ή επιλογή υπερπαραμέτρων. Δεν υπάρχουν πραγματικές συγκρίσεις
augmentation ή πλήρης baseline 50 epochs ακόμη. Το τρέχον πλάνο έχει ένα seed και
επομένως δεν θα εκτιμά μεταξύ-training μεταβλητότητα.

Στο `runs/ascad_cpu_release` μετρήθηκαν 48 optimization steps, 1,640 s training loops
και 0,158 s validation loops, σε CPU με 2 PyTorch threads. Αυτοί οι χρόνοι εξαιρούν
setup/inspection/checkpoint I/O. Το CNN έχει 197.424 parameters. Τα manifests/history/summary
αντιγράφηκαν στο `outputs/ascad_cpu_release_record/` και οι GE/SR curves βρίσκονται στο
`outputs/ascad_cpu_release_validation/`. Η μικρή CPU extrapolation δεν είναι GPU κόστος.

### Παραληφθέν Kaggle benchmark — 2026-10-03

Εισήχθη το `C:/Users/nickb/Downloads/results.zip`, SHA-256
`07b13e6f526e1e2fae5947da5f5bed489dfa4b541f63c53dbba5a045e5e16c5e`.
Περιέχει μόνο το στάδιο benchmark: none CNN, seed0, 10k train/5k validation,
3 epochs/237 steps, Tesla T4, Python3.13.15, torch2.8.0+cu126, CUDA12.6.

- Training loops1,617s, validation loops0,239s· training call με setup/checkpoints11,495s.
- Best epoch2, validation CE5,547229. Clean validation GE@128=113,1, SR@128=10%
  (1/10 permutations). Το sustained SR90% criterion απέτυχε· `>128` censored.
- Dataset/source/checkpoint checksums, splits, train-only normalizer και curves
  ελέγχθηκαν ανεξάρτητα. Δεν έγινε νέα εκπαίδευση ή εκτέλεση uploaded κώδικα.
- Source hash `e641690a163be60d7b7288f1ead8e9d1726a00e403a26af1146a41b1a38d8f87`
  ταιριάζει με τον τρέχοντα κώδικα· δεν αλλάζουμε src/scripts/configs πριν τη συνέχεια.
- Records/report: `outputs/kaggle_benchmark_2026-10-03_07b13e6f/REPORT_EL.md`.
- Checkpoints: `runs/kaggle_imports/2026-10-03_07b13e6f/minimal_v1/none_seed0/`.
- Έτοιμο restore Input: `runs/kaggle_imports/2026-10-03_07b13e6f/sca_runs_minimal_v1.zip`.
- Δεν υπάρχουν ακόμη full baseline, οι άλλες 3 στρατηγικές ή τελικό attack metrics.
  Πλήρεις εκπαιδεύσεις: 0/4· none έχει ολοκληρώσει τις πρώτες 3/50 epochs.
- Προσωπικό quota/session limit παραμένει άγνωστο. Η πρόβλεψη1,81min αφορά μόνο
  training loops του υπολοίπου, με margin50% από none, χωρίς measured augmentation overhead.

## Ακριβές επόμενο βήμα

1. Κράτα το ίδιο Kaggle notebook. Μετά από reported Input-discovery error διορθώθηκε
   η πρώτη cell και η προεπιλογή είναι πλέον `STAGE="baseline"`.
2. Προτεινόμενο νέο Input: `outputs/kaggle_resume_input.zip`, με code ZIP, ASCAD/provenance
   και το verified checkpoint archive. Η πρώτη cell αναγνωρίζει packed/extracted Inputs,
   duplicates με ίδιο source hash και το προηγούμενο `results.zip`, εμφανίζει paths και
   επαναφέρει αυτόματα το none checkpoint. `RESTORE_ARCHIVE=None` αρκεί σε αυτό το workflow.
3. `STAGE="baseline"`, `RUN_TAG="minimal_v1"`: το ίδιο none run συνεχίζει από epoch3 σε 50.
   Έλεγξε validation· μετά `STAGE="compare"` εκπαιδεύει noise/shift/combined, χωρίς νέο none run.
4. Εξέτασε padding/boundary sensitivity στο validation και ακριβή overlap με EquivSCA/RFA/CutMix.
5. Πάγωσε config/criterion/code πριν το `STAGE="attack"`, που μόνο αξιολογεί τα 4 μοντέλα.
   Το νέο matrix έχει 4 runs / 15.800 steps, χωρίς αυτόματες πρόσθετες εκπαιδεύσεις.
   Πρόσθετα seeds/budgets μόνο με συγκεκριμένο λόγο και συμφωνία χρήστη. Το παλιό 40-run matrix αποσύρθηκε.
6. Διατήρησε το output archive για restore σε νέο session, ώστε να μη χαθούν checkpoints
   και να μη χρειαστούν επαναλήψεις. Ο ακριβής τρόπος περιγράφεται στο `docs/KAGGLE.md`.

Ελληνική αναφορά: `outputs/SESSION_REPORT_EL.md`. Αγγλικό paper draft αναβάλλεται μέχρι
να υπάρχουν επαρκή πραγματικά ευρήματα και συμφωνία με τον καθηγητή.

## Διόρθωση αναζήτησης Kaggle Inputs — 2026-10-03

Ο χρήστης ανέφερε `Add exactly one project code Input` στην αρχική cell. Το traceback
δεν δείχνει τα actual Input paths/counts· μπορεί να λείπει code Input ή να υπάρχουν duplicates.
Η διόρθωση εμφανίζει τα paths, αναγνωρίζει το results archive, deduplicates ίδιο κώδικα
και ελέγχει fingerprints πριν copy/restore. Missing checkpoint δεν ξεκινά νέο baseline από την αρχή.

- Διατηρήθηκε ένα `.ipynb`, με έξι code cells. Companion: `notebooks/kaggle_bootstrap.py`.
- Η πρώτη cell δίνεται και ως `outputs/kaggle_first_cell.py` για αντιγραφή στο ίδιο Kaggle notebook.
- Το training source hash παραμένει `e641690a163be60d7b7288f1ead8e9d1726a00e403a26af1146a41b1a38d8f87`.
- `src/`, `scripts/`, `configs/`, `pyproject.toml` δεν άλλαξαν. Η notebook/bootstrap αλλαγή
  είναι εκτός του υπάρχοντος training fingerprint· δεν αλλάζει μοντέλο, splits ή optimizer.
- **Μην τρέξεις `scripts/prepare_kaggle.py` τώρα**: ο παλιός generator είναι μέρος του pinned
  hash και θα αντικαθιστούσε τη διορθωμένη cell. Το υπάρχον notebook ενημερώνεται απευθείας
  μέχρι να ολοκληρωθούν τα τρέχοντα runs. Μελλοντική αλλαγή generator απαιτεί νέο code snapshot.
- Τελικοί τοπικοί έλεγχοι: **22 passed, 14 warnings σε 9,64s**. Περιλαμβάνουν flat, packed,
  duplicate και results layouts, preservation υπάρχοντος checkpoint και missing-code diagnostics.
- Δεν εκτελέστηκε η διόρθωση στο Kaggle ούτε προστέθηκε νέο training.
