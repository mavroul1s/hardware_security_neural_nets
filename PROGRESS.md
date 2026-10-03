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
3. Το baseline ολοκληρώθηκε μέσω API (version3): epoch3→50, 3.950 συνολικά steps.
   Clean validation SR@2.000=0/20 και best epoch2. Διάγνωσε πρώτα την έλλειψη χρήσιμης
   generalization στο profiling/validation. Το `compare` παραμένει το επόμενο training stage,
   αλλά δεν ξεκίνησε αυτόματα μετά αυτό το αρνητικό baseline. Επαναχρησιμοποίησε το epoch50 archive.
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

## Εκτέλεση μέσω Kaggle API — 2026-10-03

Με ρητή εξουσιοδότηση χρήστη χρησιμοποιήθηκε το τοπικό `api_key/kaggle.json`.
Ο φάκελος credential και το ξεχωριστό `.venv-kaggle/` εξαιρούνται από Git/Inputs.
Το επίσημο Kaggle CLI 2.2.4 εγκαταστάθηκε μόνο στο περιβάλλον διαχείρισης.

- Εντοπίστηκε και διατηρήθηκε το υπάρχον ιδιωτικό notebook `con1los/hw-sec-exp2`.
- Δημιουργήθηκε ιδιωτικό Input `con1los/hardware-sca-resume`, με ASCAD, ίδιο κώδικα
  και verified checkpoint των 3 epochs. Κανένα credential δεν περιλαμβάνεται στο Input.
- Το Kaggle αποσυμπιέζει αναδρομικά και τα εσωτερικά ZIP. Η πρώτη cell υποστηρίζει
  πλέον και extracted checkpoint folders, απορρίπτει conflicting checkpoints και
  προστατεύει υπάρχον advanced checkpoint. Το training source hash παραμένει ίδιο.
- Τοπικοί έλεγχοι μετά τη διόρθωση: 24 passed, 14 warnings σε 8,42s.
- Υποβλήθηκε version 3 του ίδιου notebook, `STAGE="baseline"`, target50 epochs,
  GPU T4 και το προηγούμενο Docker image. Το API επιβεβαίωσε RUNNING· η ολοκλήρωση
  και η ακριβής συνέχεια από epoch3 δεν έχουν ακόμη επαληθευθεί από τα outputs.
- Submission record: `outputs/kaggle_execution_status.json`.

### Επαληθευμένη ολοκλήρωση baseline

- Το API επέστρεψε COMPLETE. Manifest `resumed_at_epoch=3`, history50 epochs,
  steps3.950· οι πρώτες3 epochs, splits, normalizer και environment διατηρήθηκαν.
- Best checkpoint παραμένει epoch2 / CE5,547229, byte-identical με το benchmark.
  Στην epoch50 train CE5,450314 / accuracy1,10%, validation CE5,616101 / accuracy0,32%.
- Validation20 permutations / 2.000 traces: clean GE103,50 / SR0%, matched GE109,85 / SR0%,
  OOD GE109,25 / SR0%. Ελέγχθηκαν όλα τα curves από τα stored ranks.
- Νέες training loops16,462s· συνολικές18,079s· continuation call29,175s.
  Notebook log περίπου277s με setup/tests/export, χωρίς επαληθευμένο προσωπικό quota.
- Output archive SHA256 `68940b28675fcb1f47937163723016871bdb96a378eb2c6637115a0b404a0132`,
  CRC και49 αρχεία ελεγμένα byte-for-byte. Path `runs/kaggle_control/baseline_v3_output/sca_runs_minimal_v1.zip`.
- Αναφορά/γραφικά: `outputs/kaggle_baseline_v3_2026-10-03/REPORT_EL.md`.
- Ένα πλήρες CNN από4. Δεν εκτελέστηκαν noise/shift/combined ή final attack evaluation.
  Πριν από τα επόμενα trainings, διάγνωση baseline χωρίς αλλαγή τρέχοντος fingerprint.
- Το ιδιωτικό Input ενημερώθηκε σε version2 με το verified epoch50 archive και την
  τρέχουσα bootstrap. Το fully extracted packet ελέγχθηκε τοπικά χωρίς training.
- Η version4 του ίδιου notebook αποθηκεύτηκε ως QUICK_SAVE μέσω επίσημου SDK,
  χωρίς νέα εκτέλεση GPU. Το default baseline μπορεί πλέον να επαναχρησιμοποιήσει
  το ολοκληρωμένο checkpoint. Η πραγματική εκτέλεση είναι η version3.
- Management CLI στα Windows χρειάζεται native paths και PYTHONUTF8=1.
  Οι handlers βρίσκονται μόνο στο ignored `runs/kaggle_control/`, εκτός training hash.

## Διάγνωση baseline χωρίς GPU training — 2026-10-03

Με το αίτημα «πάμε στο επόμενο» έγινε read-only CPU διάγνωση, χωρίς attack evaluation.
Ελέγχθηκαν50k profiling labels, checksum, ακριβή/disjoint splits, normalizer, finite
parameters και Adam steps. Όλα πέρασαν· όλες οι256 κλάσεις έχουν22–56 training traces.

- Best epoch2: validation CE5,547229 έναντι5,547203 με μία fixed shuffled-label control.
- Last epoch50: validation CE5,616101 έναντι5,611338 στο ίδιο control.
- Στο validation, best dense48/64 και last dense53/64 ReLU units δεν ενεργοποιούνται.
  Last conv2:12/16 inactive channels. Δεν αποδεικνύεται μοναδική αιτία αποτυχίας.
- Προετοιμάστηκε `notebooks/candidate_cnn.py`: μόνο ReLU→LeakyReLU0,1, ίδιο197.424 parameters.
  Fixed-weight gradient probe σε128 training rows: zero dense gradients53/64→0/64,
  χωρίς optimizer step ή αλλαγή checkpoint. Δεν αποτελεί trained-performance evidence.
- `src/scripts/configs` δεν άλλαξαν· ίδιο pinned source hash. Δεν έγινε νέο Kaggle run.
- Πρόταση: μία διορθωτική baseline εκπαίδευση, ίδιο10k/5k/seed0/50epochs/LR0,001.
  Με διατήρηση παλιού failure και4 νέα study models, το σύνολο θα είναι5 trainings.
  Χρειάζεται επιλογή χρήστη λόγω της ρητής οδηγίας AGENTS για additional models.
- Εναλλακτική: οι ήδη προγραμματισμένες3 augmentations στο παλιό CNN, σύνολο4 trainings.
- Αναφορά και αριθμητικά δεδομένα: `outputs/baseline_diagnosis_2026-10-03/REPORT_EL.md`.

## Εγκεκριμένο διορθωτικό baseline — 2026-10-03

Ο χρήστης απάντησε «συνέχισε» στην πρόταση για ένα διορθωμένο baseline (+1 training).
Εφαρμόζεται μόνο η αλλαγή ReLU→LeakyReLU0,1 με νέο model ID `cnn_leaky`.
Το `cnn` παραμένει διαθέσιμο για ανάγνωση/διάγνωση των προηγούμενων checkpoints.
Ίδια initialization/parameters, seed0,10k/5k split, LR0,001, batch128 και50 epochs.

Το νέο study run tag είναι `minimal_v2_leaky`, από την αρχή με νέο source fingerprint.
Το παλιό `minimal_v1` και το αρχείο epoch50 διατηρούνται ως καταγεγραμμένο failure.
Δεν μεταφέρουμε weights/optimizer από το παλιό μοντέλο. Το initial Input δεν έχει
παλιό checkpoint και το fresh-start opt-in αφορά μόνο αυτή την εγκεκριμένη εκτέλεση.
Μετά την ολοκλήρωση επαναφέρουμε την απαίτηση checkpoint και ανεβάζουμε το νέο archive.
Η ιστορική απαγόρευση αλλαγής του παλιού source hash δεν αφορά αυτή τη νέα study έκδοση.

- Source hash νέας έκδοσης: `6f72dd833c610ef73c9e1935dbd46b3acf245b3bf1910b9b80d09d3623d73126`.
  Από την υποβολή δεν αλλάζουμε src/scripts/configs μέχρι να ολοκληρωθεί το νέο study.
- Tests:26 passed,14 warnings σε10,37s. Το model test επιβεβαιώνει identical initial
  state_dict μεταξύ cnn/cnn_leaky στο ίδιο seed και negative-region gradient0,1.
- Το private Input `con1los/hardware-sca-resume` version3 περιέχει μόνο νέο code bundle,
  ASCAD/provenance. Το παλιό checkpoint δεν μεταφέρθηκε στη διορθωτική εκπαίδευση.
- Υποβλήθηκε version5 του ίδιου `hw-sec-exp2`, baseline50 epochs/T4/original Docker.
  Record: `outputs/kaggle_leaky_execution_status.json`. Η ολοκλήρωση εκκρεμεί.

### Επαληθευμένη ολοκλήρωση διορθωτικού baseline

- Version5 COMPLETE: fresh epoch0→50 / 3.950 steps, `cnn_leaky`,197.424 parameters.
  Ίδιο dataset, splits/normalizer, initialization, training config και GPU runtime.
- Best epoch1 / validation CE5,547114. Στην epoch50 train CE5,267826 / accuracy1,95%,
  validation CE5,809435 / accuracy0,38%. Uniform CE5,545177.
- Validation20 permutations / 2.000 traces: clean GE89,25 / SR0/20,
  matched GE92,50 / SR0/20 και OOD GE96,65 / SR0/20. Όλα τα curves επανελέγχθηκαν.
- Archive CRC21 αρχεία·7 independent downloads byte-identical. SHA256
  `7f9590e617ed70b9ba42eaea3afc0c2102989064cc9d8837c4ab07c072d4baa0`.
  Archive: `runs/kaggle_control/leaky_v5_output/sca_runs_minimal_v2_leaky.zip`.
- Read-only CPU review αναπαράγει best/last CE, ελέγχει3 Leaky layers και unchanged
  checkpoint hashes. Fixed128-row backward: dense nonzero gradient64/64 και στα δύο.
  No optimizer step / no extra training. Αυτό δεν αποκατέστησε τη γενίκευση.
- Training loops19,110s, validation3,925s, call33,796s. Notebook log περίπου359,754s
  μαζί με setup/tests/export. Προσωπικό quota παραμένει μη επαληθευμένο.
- Δύο πλήρη GPU trainings συνολικά. Baseline gate απέτυχε· οι άλλες3 augmentations
  μένουν σε αναμονή. Final attack evaluation δεν έγινε, protocol freeze=false.
- Αναφορά: `outputs/kaggle_leaky_v5_2026-10-03/REPORT_EL.md`.
  Επόμενο βήμα: profiling/model/label diagnosis χωρίς νέο GPU training.
- Επαναφέρθηκε `require_checkpoint=True`. Το ενεργό resume packet περιλαμβάνει
  το completed Leaky epoch50 archive. Fully extracted layout: restore50 verified,
  repeated bootstrap διατηρεί αμετάβλητο checkpoint χωρίς training.
- Το ίδιο private Input ενημερώθηκε σε version4 και επιβεβαιώθηκε ready.
  Remote history κατέβηκε και συμφωνεί byte-for-byte με τις50 epochs.
- Το ίδιο private notebook αποθηκεύτηκε σε version6 ως QUICK_SAVE, χωρίς νέα GPU
  εκτέλεση. Pulled notebook: όλα τα cell sources, ID136887556 και Input verified.
  Η πραγματική εκτέλεση παραμένει version5. Κανένα δεύτερο notebook δεν δημιουργήθηκε.
- Ο πρώτος έλεγχος έγκρισης απέρριψε την ενημέρωση Input ως μη ειδικά εξουσιοδοτημένη.
  Με πρόσθετα read-only στοιχεία του ιδιωτικού προορισμού, του εγκεκριμένου scope
  και85 αρχείων χωρίς credentials, η ίδια ενέργεια εγκρίθηκε και ολοκληρώθηκε.
- Τεκμήρια διατήρησης: `outputs/leaky_artifact_verification.json`,
  `outputs/kaggle_preservation_scope.json`, `outputs/kaggle_leaky_execution_status.json`.

## Διάγνωση masking / model geometry χωρίς νέα GPU εκτέλεση — 2026-10-03

Με το «προχώρα» ολοκληρώθηκε η profiling-only CPU διάγνωση στο ίδιο10k/5k split.
Το final attack group δεν ανοίχθηκε. Training source/checkpoint hashes αμετάβλητα.
Παραμένουν δύο πλήρη GPU trainings και ένα `.ipynb`.

- Επιβεβαιώθηκε ο επίσημος unmasked ID στόχος· masked ASCAD δεν σημαίνει λάθος labels.
  Paper metadata mapping: masks[0]=r[3], masks[15]=rout, ASCADv1.
- Weighted SNR σε ID/HW classes,8 shuffled controls/seed20261004. HW(z) observed peak
  0,001897 train /0,004026 val έναντι control maxima0,002801/0,005249.
  Mask/share peaks ισχυρά και σε κοινές θέσεις των δύο splits.
- Training-selected centered products181×521 και156×517: validation HW(z) SNR
  0,042566 και0,044072, έναντι max shuffled controls0,004420 και0,003810.
  Train-only centering και selection25 candidate pairs ανά family. Περιγραφικά controls,
  όχι confidence interval, trained classifier ή key-recovery evaluation.
- Local convolution RF34samples· dense64 layer βλέπει όλα700 samples. Η απόσταση
  των informative pairs340/361 δεν αποδεικνύει αδυναμία ολόκληρου του CNN.
- Untrained PyTorch literature candidate: Conv4/k1, SELU/BN, pool2, dense10×2,
  logits256 /16.952 parameters. Finite forward/backward128train rows, no optimizer step.
  Train-only per-position MinMax, χωρίς validation clipping/refit. Δεν προστέθηκε
  στο ενεργό pinned source/config/notebook και δεν υπάρχει performance evidence.
- Πρόταση: ένα επιπλέον baseline με ίδιο10k/5k/seed0/50epochs/batch128/Adam LR0,001.
  Gate clean SR@2000≥0,90 (18/20), minimum-CE checkpoint. Μόνο αν περάσει, ένα combined.
  Έως4 full GPU trainings συμπεριλαμβανομένων δύο failures. Αποσύρονται οι singles μόνο
  αν συμφωνήσει ο χρήστης· νέο ερώτημα baseline-versus-combined, χωρίς factorial attribution.
- Ζητήθηκε συμφωνία με async question για νέα αρχιτεκτονική/μικρότερο research scope,
  βάσει AGENTS: additional models/budgets/seeds require research reason/user agreement.
  Η απάντηση εκκρεμεί. Μην ξεκινήσεις εξαρτώμενο training χωρίς να δοθεί.
- Tests29 passed,14 warnings σε13,23s. Τα3 νέα arithmetic/scaling tests πέρασαν.
  Η suite περιέχει τα προηγούμενα synthetic CPU training checks, όχι νέα Kaggle runs.
- Έγινε visual QA στα `share_snr.png` και `second_order_evidence.png`.
- Scripts `notebooks/diagnose_masking.py`, `candidate_literature_cnn.py`,
  `audit_candidate_architecture.py`, `plot_masking_diagnosis.py`. Αναφορά και JSON:
  `outputs/masking_diagnosis_2026-10-03/REPORT_EL.md`.
