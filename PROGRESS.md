# Κατάσταση project — 2026-10-03

## Συμφωνημένο πλαίσιο

Εξάμηνο διαθέσιμο, χωρίς συγκεκριμένα κριτήρια μαθήματος. Ο χρήστης έχει Kaggle GPU access.
Ακριβής ημερομηνία παράδοσης και προσωπικό GPU quota δεν έχουν δοθεί/ελεγχθεί.
Ανάπτυξη στα ελληνικά ως επικοινωνία, κώδικας στα αγγλικά. Καμία ανάγκη API keys/πληρωμένων υπηρεσιών.

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
- Έγινε πραγματικός CPU pilot (2048 train / 512 validation / 3 epochs), και δύο
  επαναλήψεις verification με ακριβώς ίδια losses/GE/SR. Δεν είναι independent-seed replication.
  Κύριο τελικό artifact: `runs/ascad_cpu_release`, με snapshot του κώδικα και καταγεγραμμένο hash.
- Έγινε synthetic CPU smoke test 384/128, 2 epochs και synthetic ranking· code validation μόνο.
- Έγινε training-only boundary audit 10k/5k. First-order identity SNR είναι αδύναμο και
  δεν πιστοποιεί διατήρηση masked leakage· sensitivity παραμένει ανοιχτό.
- Δημιουργήθηκαν literature comparison/BibTeX για 10 εργασίες, πρωτόκολλο και σχέδιο εξαμήνου.
  Πρόσβαση σε ορισμένα full papers παραμένει περιορισμένη και αναφέρεται ανά εργασία.
- Δημιουργήθηκαν Kaggle notebook/code bundle, με 4 GPU benchmarks και CNN/MLP baselines.
  Ελέγχθηκαν συντακτικά οι 6 code cells, χωρίς αποθηκευμένα execution outputs.
  Το bundle εξαιρεί δεδομένα, runs, checkpoints, `.venv` και `.git`.
  **Δεν εκτελέστηκε στο Kaggle** και δεν ελέγχθηκε το προσωπικό GPU quota.

## Πραγματικά αποτελέσματα έως τώρα

Τα pilots δεν απέδειξαν ανάκτηση. Clean validation GE@128=125,8, SR@128=0%,
10 attack-order repetitions από pool512, selected epoch1. Το τελικό attack/test δεν
χρησιμοποιήθηκε για metrics ή επιλογή υπερπαραμέτρων. Δεν υπάρχουν πραγματικές συγκρίσεις
augmentation, 5 independent seeds ή πλήρης baseline 50 epochs ακόμη.

Στο `runs/ascad_cpu_release` μετρήθηκαν 48 optimization steps, 1,640 s training loops
και 0,158 s validation loops, σε CPU με 2 PyTorch threads. Αυτοί οι χρόνοι εξαιρούν
setup/inspection/checkpoint I/O. Το CNN έχει 197.424 parameters. Τα manifests/history/summary
αντιγράφηκαν στο `outputs/ascad_cpu_release_record/` και οι GE/SR curves βρίσκονται στο
`outputs/ascad_cpu_release_validation/`. Η μικρή CPU extrapolation δεν είναι GPU κόστος.

## Ακριβές επόμενο βήμα

1. Ανέβασε `outputs/kaggle_project.zip` και το verified `data/ASCAD.h5` ως private Inputs,
   εισήγαγε `notebooks/kaggle_baseline.ipynb` και διάβασε `docs/KAGGLE.md`.
2. Κατάγραψε actual GPU/remaining quota και εκτέλεσε 3-epoch benchmark των 4 strategies.
3. Εκτέλεσε CNN/MLP seed0 baseline10k/50epochs, διάγνωσε clean/corrupted validation.
4. Εξέτασε padding/boundary sensitivity στο validation και ακριβή overlap με EquivSCA/RFA/CutMix.
5. Πάγωσε config/criterion/code πριν το τελικό attack. Μετρημένο GPU κόστος καθορίζει
   αν χωράει το matrix40runs/119ksteps. Πέντε seeds είναι στόχος, όχι ολοκληρωμένο αποτέλεσμα.

Ελληνική αναφορά: `outputs/SESSION_REPORT_EL.md`. Αγγλικό paper draft αναβάλλεται μέχρι
να υπάρχουν επαρκή πραγματικά ευρήματα και συμφωνία με τον καθηγητή.
