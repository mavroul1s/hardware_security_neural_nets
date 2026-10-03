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
  **Δεν εκτελέστηκε στο Kaggle** και δεν ελέγχθηκε το προσωπικό GPU quota.

Οι τοπικοί stage checks είναι orchestration dry runs και synthetic CPU tests, όχι πραγματικές
GPU εκτελέσεις. Ο νέος πηγαίος κώδικας έχει διαφορετικό hash από τα ιστορικά ASCAD pilots·
τα original snapshots/manifests διατηρούνται ώστε τα παλιά πραγματικά αποτελέσματα να είναι αναπαραγώγιμα.

## Πραγματικά αποτελέσματα έως τώρα

Τα pilots δεν απέδειξαν ανάκτηση. Clean validation GE@128=125,8, SR@128=0%,
10 attack-order repetitions από pool512, selected epoch1. Το τελικό attack/test δεν
χρησιμοποιήθηκε για metrics ή επιλογή υπερπαραμέτρων. Δεν υπάρχουν πραγματικές συγκρίσεις
augmentation ή πλήρης baseline 50 epochs ακόμη. Το τρέχον πλάνο έχει ένα seed και
επομένως δεν θα εκτιμά μεταξύ-training μεταβλητότητα.

Στο `runs/ascad_cpu_release` μετρήθηκαν 48 optimization steps, 1,640 s training loops
και 0,158 s validation loops, σε CPU με 2 PyTorch threads. Αυτοί οι χρόνοι εξαιρούν
setup/inspection/checkpoint I/O. Το CNN έχει 197.424 parameters. Τα manifests/history/summary
αντιγράφηκαν στο `outputs/ascad_cpu_release_record/` και οι GE/SR curves βρίσκονται στο
`outputs/ascad_cpu_release_validation/`. Η μικρή CPU extrapolation δεν είναι GPU κόστος.

## Ακριβές επόμενο βήμα

1. Ανέβασε `outputs/kaggle_project.zip` και το verified `data/ASCAD.h5` ως private Inputs,
   εισήγαγε `notebooks/kaggle_baseline.ipynb` και διάβασε `docs/KAGGLE.md`.
2. Κατάγραψε actual GPU/remaining quota και άφησε `STAGE="benchmark"`: none CNN, 3 epochs.
3. Στο ίδιο notebook, `STAGE="baseline"` συνεχίζει το ίδιο run μέχρι 50 epochs.
   Έλεγξε validation· μετά `STAGE="compare"` εκπαιδεύει noise/shift/combined, χωρίς νέο none run.
4. Εξέτασε padding/boundary sensitivity στο validation και ακριβή overlap με EquivSCA/RFA/CutMix.
5. Πάγωσε config/criterion/code πριν το `STAGE="attack"`, που μόνο αξιολογεί τα 4 μοντέλα.
   Το νέο matrix έχει 4 runs / 15.800 steps, χωρίς αυτόματες πρόσθετες εκπαιδεύσεις.
   Πρόσθετα seeds/budgets μόνο με συγκεκριμένο λόγο και συμφωνία χρήστη. Το παλιό 40-run matrix αποσύρθηκε.
6. Διατήρησε το output archive για restore σε νέο session, ώστε να μη χαθούν checkpoints
   και να μη χρειαστούν επαναλήψεις. Ο ακριβής τρόπος περιγράφεται στο `docs/KAGGLE.md`.

Ελληνική αναφορά: `outputs/SESSION_REPORT_EL.md`. Αγγλικό paper draft αναβάλλεται μέχρι
να υπάρχουν επαρκή πραγματικά ευρήματα και συμφωνία με τον καθηγητή.
