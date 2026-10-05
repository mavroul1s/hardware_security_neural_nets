# Αναπαραγωγή αποθηκευμένων αποτελεσμάτων σε καθαρό CPU περιβάλλον

Ημερομηνία: 2026-10-05. **Ο έλεγχος αναπαραγωγής πέρασε.** Νέο venv από wheels,
ξεχωριστό αντίγραφο source, ίδια δεδομένα/splits/checkpoints και profiling validation.
Δεν έγινε νέα εκπαίδευση στα πραγματικά δεδομένα ή στο Kaggle.

## Τι επιβεβαιώθηκε

| Αποθηκευμένο checkpoint | Epoch | Clean validation CE | GE@2.000 | SR@2.000 |
|---|---:|---:|---:|---:|
| Literature CNN best | 4 | 5.560781941575 | 114.25 | 0/20 |
| Literature CNN last | 50 | 5.814249784537 | 117.00 | 0/20 |

Οι training/validation CE και accuracy συμφωνούν ακριβώς με την προηγούμενη CPU
διάγνωση: μετρημένη απόκλιση CE **0**, με ανοχή 1e-7 παγωμένη πριν την εκτέλεση.
Και οι 40.000 prefix ranks ανά checkpoint συμφωνούν με τα προηγούμενα CPU arrays.
Η σύγκριση αφορά αποθηκευμένο CPU inference· οι ήδη καταγεγραμμένες μικρές διαφορές
CPU/GPU σε ενδιάμεσα prefixes δεν επαναβαπτίζονται σε bitwise GPU αναπαραγωγή.
Τα ReLU/LeakyReLU historical trainings διατηρήθηκαν, αλλά δεν επαναξιολογήθηκαν εδώ.

Τα παγωμένα centered-product ζεύγη **181×521** και **156×517** διατηρούν clean
SR20/20 και GE0. Sustained SR90 στα **631** και **481** traces αντίστοιχα.
Άλλοι 80.000 raw-product prefix ranks συμφωνούν ακριβώς με την προηγούμενη διάγνωση.
Δεν επαναλήφθηκε επιλογή σημείων ή αναζήτηση καλύτερου ζεύγους.

Επαναλήφθηκαν οι **8 υπάρχουσες συνθήκες × 2 ζεύγη × 2 τρόποι εξαγωγής**:
και οι **32 γραμμές αποτελεσμάτων**, τα **138 arrays** (ίδια dtype/shape/bytes),
οι offsets, τα tensor hashes και οι έλεγχοι padding συμφωνούν. Αυτό περιλαμβάνει
1.280.000 sensitivity rank values. Ο ανεξάρτητος Pearson endpoint έλεγχος επαλήθευσε
ξανά **640 endpoints** και ανακατασκεύασε τα tensors με το production augment_batch.

## Καθαρό περιβάλλον και προέλευση

Windows AMD64, Python 3.12.14, PyTorch 2.8.0+cpu,
NumPy 2.2.6, h5py 3.14.0, matplotlib 3.10.5.
Το νέο περιβάλλον είναι στο `runs/cpu_reproduction_2026-10-05/venv` και το source
στο `runs/cpu_reproduction_2026-10-05/source`. Εγκαταστάθηκαν **27 exact dependency
wheels** με `--no-index --require-hashes`, έπειτα editable project από το snapshot
με `--no-deps --no-build-isolation`. Το pip25.0.1 προήλθε από τη δημιουργία του venv.
Δεν αντιγράφηκαν εγκατεστημένα site-packages από το προηγούμενο venv.

Χρησιμοποιήθηκαν 26 αμετάβλητα wheel αρχεία από την τοπική cache
(664,536,135 bytes). Κατέβηκε μόνο το setuptools78.1.0 από το PyPI
(1,256,108 bytes, περίπου1,26MB wheel· δεν μετρήθηκε συνολικό HTTP traffic).
Τα filenames των cached wheels ανασυντέθηκαν από METADATA/WHEEL tags, χωρίς
repackaging ή αλλαγή των bytes. Τα hashes όλων των 27 wheels επαληθεύτηκαν ξανά.

Το [νέο CPU lockfile](../../requirements-lock-cpu-reproduction.txt) έχει exact versions
και SHA256 ανά συμβατό Windows/CPython3.12 wheel. Δεν είναι CUDA ή cross-platform lock.
Το παλιό `requirements-lock-cpu.txt` διατηρείται ως ιστορικό: η editable Git αναφορά
στο παλιό commit3cc007d δεν χρησιμοποιήθηκε για αυτόν τον έλεγχο.

Το `python -I` απέκλεισε inherited PYTHONPATH και user-site imports. Ελέγχθηκαν
sys.prefix, module paths, dependency versions και sca path: οι βιβλιοθήκες φορτώθηκαν
από το νέο venv και το sca από το ξεχωριστό snapshot. Το frozen source hash παραμένει
`84eff3cde04c0e9a1756a3d29c44ec82e115a1a08575132686a02520333e2b5c` τόσο στο αρχικό project όσο και στο snapshot.
Το [environment.json](environment.json) καταγράφει τα πραγματικά paths/versions.

## Έλεγχοι και πραγματικό κόστος

Το πλήρες suite πέρασε: **44 passed, 14 warnings**, 597.51s
(JUnit 597.495s). Οι υπάρχουσες προειδοποιήσεις αφορούν deprecated
pyparsing interfaces μέσα στο matplotlib. Ο έλεγχος `pip check` πέρασε.
Ο χρόνος του suite ήταν μεγαλύτερος από προηγούμενες συνεδρίες· δεν μετρήθηκε η αιτία
και δεν αποδίδεται αυθαίρετα στο νέο venv ή σε αλλαγή αλγορίθμου.
Τα synthetic fixtures ελέγχουν correctness/continuation, όχι φυσική αποτελεσματικότητα.

Το πραγματικό validation replay πήρε **62.36s** μετά τις εισαγωγές:
clean CNN/raw correlation 15.81s,
sensitivity 37.20s και ανεξάρτητη verification
8.53s, συν μικρό υπόλοιπο ελέγχων/I/O.
Αυτοί δεν είναι συνολικοί χρόνοι λήψης, εγκατάστασης ή ολόκληρης συνεδρίας.
Νέες GPU εκπαιδεύσεις0, νέα optimizer updates σε πραγματικό ASCAD0.

## Προστασία του πρωτοκόλλου και όρια

Τα input hashes παγώθηκαν στο [evaluation_plan.json](evaluation_plan.json) πριν την
ανάγνωση traces και ελέγχθηκαν μετά: dataset, splits, best/last checkpoints,
παλιές διαγνωστικές μετρήσεις, active code/Input archives και canonical/saved notebook
διατηρήθηκαν. Το πραγματικό HDF5 διαβάστηκε μόνο στο Profiling_traces· τα synthetic
fixtures των tests είναι ξεχωριστά. Το final ASCAD Attack_traces payload δεν διαβάστηκε.

Το gate παραμένει failed: το minimum-CE CNN checkpoint έχει SR0/20, άρα combined
παραμένει skipped. Σύνολο3 full GPU trainings και1 canonical Kaggle notebook.
Το `.ipynb` μέσα στο snapshot είναι archival αντίγραφο του ίδιου notebook.
Η επιτυχία correlation δεν αλλάζει το gate και δεν αποδεικνύει όφελος training augmentation.
Το oracle εξακολουθεί να γνωρίζει την τεχνητή μετατόπιση· δεν είναι εκτιμημένη ευθυγράμμιση.

Η αναπαραγωγή ελέγχει checkpoint inference και CPU diagnostics στο ίδιο Windows
μηχάνημα και base interpreter. Δεν επανεκπαίδευσε CNN, δεν ελέγχει άλλο hardware,
άγνωστο κλειδί, άλλο dataset ή independent profiling device. Δεν είναι νέα ερευνητική
μέτρηση αποτελεσματικότητας ή εγγύηση μεταφοράς σε διαφορετικό περιβάλλον.

## Αρχεία και επανάληψη

Οι [μετρήσεις](results.json), το [JUnit](pytest.xml), τα [wheels/hashes](wheels.json),
η [τελική επαλήθευση](verification.json) και η
[ανεξάρτητη sensitivity verification](sensitivity/verification.json) περιέχουν τα τεκμήρια.
Οι companions είναι [reproduce_cpu.py](../../notebooks/reproduce_cpu.py),
[prepare_cpu_reproduction.py](../../notebooks/prepare_cpu_reproduction.py) και
[verify_cpu_reproduction.py](../../notebooks/verify_cpu_reproduction.py).
Installation/test logs, το wheelhouse και το source snapshot διατηρούνται κάτω από
`runs/cpu_reproduction_2026-10-05/`, εκτός Git. Δεν χρειάζονται Kaggle ή API credentials.

Η ακριβής σειρά που εκτελέστηκε ήταν: νέο venv → offline hashed dependencies →
editable snapshot → pip check → pytest από το snapshot → CPU replay → verification.
Οδηγίες με τις εντολές βρίσκονται στο [CPU_REPRODUCTION.md](../../docs/CPU_REPRODUCTION.md).
Το replay προστατεύει υπάρχοντα evidence directories και δεν επιτρέπει σιωπηρή αντικατάσταση.

Επόμενο βήμα: τελική επιμέλεια της ελληνικής διαγνωστικής μελέτης για συζήτηση στο μάθημα.
Νέο GPU πλάνο απαιτεί συγκεκριμένο ερευνητικό λόγο και συμφωνία αλλαγής scope/ορίου.
