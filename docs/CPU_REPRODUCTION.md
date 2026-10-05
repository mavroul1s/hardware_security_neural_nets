# Αναπαραγωγή σε CPU

Ο έλεγχος της 5/10/2026 πέρασε σε νέο venv και ξεχωριστό source snapshot.
[Αναφορά](../outputs/cpu_reproduction_2026-10-05/REPORT_EL.md),
[μετρήσεις](../outputs/cpu_reproduction_2026-10-05/results.json) και
[επαλήθευση](../outputs/cpu_reproduction_2026-10-05/verification.json).
Δεν εκτελέστηκε real-data training, Kaggle run ή final attack evaluation.

## Απαιτούμενα τοπικά artifacts

Χρειάζονται το επίσημο `data/ASCAD.h5`, τα ήδη ολοκληρωμένα literature CNN checkpoints
και splits κάτω από `runs/kaggle_control/literature_v7_output/`, τα saved version8
notebook bytes και τα υπάρχοντα diagnosis/sensitivity outputs. Το replay ελέγχει τα
hashes πριν διαβάσει profiling traces. Οι archived ReLU/LeakyReLU runs παραμένουν
ιστορικά αρνητικά αποτελέσματα και δεν επαναξιολογούνται σε αυτόν τον έλεγχο.

Το `runs/cpu_reproduction_2026-10-05/` διατηρεί:

- `wheelhouse/`: 27 exact wheels με hashes, συμβατά με Windows AMD64/CPython3.12.
- `source/`: ξεχωριστό αντίγραφο των frozen source/configs, tests και CPU companions.
- `venv/`: νέο περιβάλλον από wheels, χωρίς αντιγραφή παλιών site-packages.
- `install.log`, `project_install.log`, `pip_check.log`, `tests.log`, `replay.log`.

Το [requirements-lock-cpu-reproduction.txt](../requirements-lock-cpu-reproduction.txt)
δεν περιέχει editable Git URL ή παλιό commit. Το project εγκαθίσταται χωριστά από
το ελεγμένο source snapshot. Το lock αφορά μόνο CPU/Windows/CPython3.12, όχι Kaggle CUDA.
Το παλιό `requirements-lock-cpu.txt` παραμένει ιστορικό.

## Εντολές που εκτελέστηκαν

Οι παρακάτω εντολές τεκμηριώνουν την αρχική καθαρή εγκατάσταση από το project root.
Οι συγκεκριμένοι κατάλογοι υπάρχουν ήδη. Μην επανεγκαθιστάτε πάνω τους και μην
αντικαθιστάτε evidence· η δημιουργία νέου venv σε άλλο μηχάνημα απαιτεί διαθέσιμη
Python3.12, τα ίδια wheels και το ίδιο επαληθευμένο source/artifact tree.

```powershell
# Initial installation, in previously empty directories:
& 'C:/Users/nickb/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m venv runs/cpu_reproduction_2026-10-05/venv
& .\runs\cpu_reproduction_2026-10-05\venv\Scripts\python.exe -I -m pip install --no-index --find-links runs/cpu_reproduction_2026-10-05/wheelhouse --require-hashes -r requirements-lock-cpu-reproduction.txt
& .\runs\cpu_reproduction_2026-10-05\venv\Scripts\python.exe -I -m pip install --no-index --no-deps --no-build-isolation -e runs/cpu_reproduction_2026-10-05/source
& .\runs\cpu_reproduction_2026-10-05\venv\Scripts\python.exe -I -m pip check

# Tests were executed with the snapshot as the working directory:
Push-Location runs/cpu_reproduction_2026-10-05/source
& ..\venv\Scripts\python.exe -I -m pytest -q --junitxml=../../../outputs/cpu_reproduction_2026-10-05/pytest.xml
Pop-Location

# Initial replay; this exact output directory is now protected against reruns:
& .\runs\cpu_reproduction_2026-10-05\venv\Scripts\python.exe -I runs/cpu_reproduction_2026-10-05/source/notebooks/reproduce_cpu.py --root . --output outputs/cpu_reproduction_2026-10-05
& .\runs\cpu_reproduction_2026-10-05\venv\Scripts\python.exe -I notebooks/verify_cpu_reproduction.py
```

Το πραγματικό JUnit είναι αποθηκευμένο στο
`outputs/cpu_reproduction_2026-10-05/pytest.xml`. Πέρασαν44 tests με14 υπάρχοντα
matplotlib/pyparsing warnings σε597,51s. Τα synthetic fixtures ελέγχουν correctness,
και δεν προσμετρώνται ως πραγματικά GPU/ASCAD trainings ή evidence attack efficacy.

## Νέα επανάληψη με το ήδη ελεγμένο περιβάλλον

Για επανάληψη του inference/diagnostics, χρησιμοποίησε νέο output directory και
αντίγραφο του preparation plan. Αυτή η επανάληψη χρησιμοποιεί το υπάρχον καθαρό venv·
δεν αποτελεί δεύτερη ανεξάρτητη εγκατάσταση. Παράδειγμα, μόνο αν το νέο path δεν υπάρχει:

```powershell
New-Item -ItemType Directory -Path outputs/cpu_reproduction_repeat
Copy-Item -LiteralPath outputs/cpu_reproduction_2026-10-05/plan.json -Destination outputs/cpu_reproduction_repeat/plan.json
& .\runs\cpu_reproduction_2026-10-05\venv\Scripts\python.exe -I runs/cpu_reproduction_2026-10-05/source/notebooks/reproduce_cpu.py --root . --output outputs/cpu_reproduction_repeat
```

Το companion αρνείται υπάρχον `evaluation_plan.json`, ώστε να μη χαθεί προηγούμενη
εκτέλεση. Οι assertions συγκρίνουν νέες μετρήσεις/curves/arrays με τα παλιά results,
και γράφουν ξεχωριστές sensitivity μετρήσεις και ανεξάρτητη verification.
Ο `verify_cpu_reproduction.py` αφορά ειδικά τον ολοκληρωμένο έλεγχο της 5/10.

## Scope του ελέγχου

Οι έλεγχοι απαιτούν ίδια dependency versions, απομονωμένο venv/source, ίδιο hash84eff…,
train-only MinMax, ίδιο10k/5k split και έγκυρα checkpoints. Το `python -I` αποκλείει
inherited PYTHONPATH/user-site imports και οι module paths ελέγχονται μέσα στον κώδικα.
Το πραγματικό HDF5 ανοίγει μόνο το `Profiling_traces` για inference/diagnostics.
Whole-file checksum δεν σημαίνει αξιολόγηση του `Attack_traces` payload.

Αναπαράχθηκαν best/last CNN CE/accuracy και clean ranks, δύο raw correlation rank
curves, και32 sensitivity rows/138 arrays με640 ανεξάρτητα Pearson endpoint checks.
Δεν επαναλήφθηκαν οι BN counterfactual/shuffled controls, η επιλογή σημείων ή GPU
training. Το oracle εξακολουθεί να χρησιμοποιεί γνωστά injected shifts.

Ο έλεγχος στο ίδιο Windows host/base interpreter δεν αποδεικνύει cross-platform,
cross-device ή unknown-key generalization. Το original CNN gate παραμένει failed,
combined skipped· σύνολο3 full GPU trainings και1 canonical Kaggle notebook.
