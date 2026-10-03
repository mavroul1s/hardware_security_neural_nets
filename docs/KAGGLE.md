# Εκτέλεση στο Kaggle

Χρησιμοποιούμε **ένα notebook και τέσσερα CNN trainings συνολικά**, σε ένα budget10k
και seed0. Τα 3 benchmark epochs είναι μέρος του none baseline των 50 epochs.
Η νέα επιλογή αντικαθιστά το παλιό πλάνο 46 trainings. Δεν δημιουργούμε ξεχωριστά notebooks ανά πείραμα.

Έλεγχος δημόσιας τεκμηρίωσης: 2026-10-03. Ο χρήστης επιβεβαίωσε ενεργή πρόσβαση GPU.
Δεν συνδεθήκαμε στον λογαριασμό ούτε επιθεωρήσαμε προσωπικό quota. Στις 2026-10-03
παραλήφθηκε `results.zip` με πραγματικό 3-epoch benchmark στην Tesla T4· δείτε την
[αναφορά benchmark](../outputs/kaggle_benchmark_2026-10-03_07b13e6f/REPORT_EL.md).
Το επόμενο βήμα είναι `STAGE="baseline"` με συνέχεια του ίδιου run.

## Προτεινόμενη συνέχεια μετά το Input-discovery error

1. Ανέβασε το έτοιμο `outputs/kaggle_resume_input.zip` σε ένα private Kaggle Dataset
   και πρόσθεσέ το ως Input στο **ίδιο notebook**. Περιέχει `kaggle_project.zip`,
   `ASCAD.h5`, `ASCAD.provenance.json` και `sca_runs_minimal_v1.zip`.
2. Αντικατάστησε την πρώτη code cell με το περιεχόμενο του `outputs/kaggle_first_cell.py`,
   ή χρησιμοποίησε την ενημερωμένη έκδοση του μοναδικού `notebooks/kaggle_baseline.ipynb`.
3. Κράτα `STAGE="baseline"`, `RUN_TAG="minimal_v1"`, `RESTORE_ARCHIVE=None`.
   Η διορθωμένη πρώτη cell επαναφέρει το checkpoint αυτόματα και εμφανίζει
   `Completed epoch: 3` πριν αρχίσει οποιαδήποτε εκπαίδευση. Προχωράμε στις υπόλοιπες cells.

Η cell δέχεται είτε extracted περιεχόμενα είτε το ίδιο το Input ZIP, και αποδέχεται
duplicate code Inputs όταν το source fingerprint είναι ίδιο. Διαφορετικές checkpoint
εκδόσεις αναφέρονται ως ambiguity. Το `sca_runs_minimal_v1.zip` μόνο του δεν περιέχει
ASCAD ή πλήρες project. Το `results.zip` περιέχει κώδικα/checkpoints αλλά επίσης χρειάζεται
το ASCAD Input. Το ενιαίο πακέτο αποφεύγει αυτή την ασάφεια.

Ο κώδικας εκπαίδευσης έχει το ίδιο hash με το υπάρχον checkpoint. Η διόρθωση αφορά μόνο
την notebook bootstrap cell. Σε διαφορετική GPU/runtime παραμένει ο έλεγχος exact resume.

Η [επίσημη τεκμηρίωση](https://www.kaggle.com/docs/notebooks) αναφέρει επιλογές P100/T4×2,
sessions μέχρι 12 ώρες CPU/GPU και 20 GB αποθηκευόμενου χώρου `/kaggle/working`.
Η [GPU τεκμηρίωση](https://www.kaggle.com/docs/efficient-gpu-usage) αναφέρει quota συνήθως
30 ώρες/εβδομάδα, ενίοτε υψηλότερο ανάλογα με ζήτηση/πόρους. Η διαθεσιμότητα περιορίζεται
και μπορεί να υπάρχει ουρά. Αυτά δεν εγγυώνται το σημερινό quota ή hardware του λογαριασμού.

## Βήματα

1. Δημιούργησε **ένα private Kaggle Dataset** με `outputs/kaggle_project.zip`,
   `data/ASCAD.h5` και `data/ASCAD.provenance.json`. Το code zip εξαιρεί `.venv`,
   datasets, runs και checkpoints. Το notebook δέχεται όλα τα αρχεία στο ίδιο Input.
   Δεν χρειάζεται να ανεβάσεις το raw ZIP των 4,4 GB.
2. Δημιούργησε notebook με **Import Notebook** και διάλεξε `notebooks/kaggle_baseline.ipynb`.
   Με **Add Input** πρόσθεσε το παραπάνω dataset.
3. Settings → Accelerator → διαθέσιμη GPU. Έλεγξε το εμφανιζόμενο remaining quota,
   runtime limit και internet toggle. Αποθήκευσε τα πραγματικά στοιχεία στο αρχείο budget
   του notebook. Το παρόν PyTorch pipeline χρησιμοποιεί **μία** GPU ακόμη και με T4×2.
4. Εκτέλεσε τις discovery/setup cells. Το notebook εντοπίζει το code ZIP και `ASCAD.h5`,
   ελέγχει checksum, CUDA και GPU name και κρατά `pip freeze`. Για pinned CUDA torch2.8
   επιλέγει το official cu126 wheel· μπορείς να χρησιμοποιήσεις το έτοιμο Kaggle torch
   απενεργοποιώντας εγκατάσταση, με τις αποκλίσεις καταγραμμένες και χωρίς ισχυρισμό ίδιο environment.
5. Το πρώτο `STAGE="benchmark"` έχει ήδη εκτελεστεί. Έγιναν μόνο οι πρώτες 3 epochs του none CNN,
   n_train10k/validation5k. Το `gpu_cost_estimate.json` είναι πρόβλεψη αναφοράς από αυτό
   το μοντέλο, όχι μετρημένο overhead των άλλων στρατηγικών. Εξέτασε χρόνο/quota και diagnostics.
6. Στο **ίδιο notebook**, η τρέχουσα προεπιλογή είναι `STAGE="baseline"`. Τρέξε τις settings/training/output
   cells. Το ίδιο run συνεχίζει από epoch3 σε epoch50. Έλεγξε clean/matched-joint/OOD-joint
   validation πριν αλλάξεις σε `STAGE="compare"`. Τότε εκπαιδεύονται οι άλλες τρεις
   στρατηγικές: noise, shift, combined. Το ήδη ολοκληρωμένο none δεν ξαναεκπαιδεύεται.
7. Με `STAGE="attack"` γίνονται **μόνο αξιολογήσεις**, χωρίς training. Προϋπόθεση:
   τέσσερα πλήρη runs, review/freeze του protocol και `PROTOCOL_FROZEN=True`.
   Το `protocol_freeze.json` αποθηκεύεται πριν τα πρώτα attack metrics και ελέγχεται σε
   επανεκτέλεση. Δεν αλλάζουμε ρυθμίσεις επειδή είδαμε το attack αποτέλεσμα.
8. **Save Version → Save & Run All** για αναπαραγώγιμη αποθηκευμένη εκτέλεση.
   Κατέβασε το output archive από `/kaggle/working`, μαζί με checkpoint/logs/versions.
   Quick Save μόνο δεν αποδεικνύει ότι εκτελέστηκε το notebook. Απενεργοποίησε GPU όταν τελειώσεις.

## Συνέχιση χωρίς διπλές εκπαιδεύσεις

Μέσα στο ίδιο ενεργό session κρατάμε `RUN_TAG="minimal_v1"`. Σε νέο session ή νέο
Save & Run All δεν θεωρούμε ότι το προηγούμενο `/kaggle/working` διατηρείται.
Κατέβασε το `sca_runs_minimal_v1.zip`, ανέβασέ το ως private Input και βάλε
`RESTORE_ARCHIVE="/kaggle/input/<your-input>/sca_runs_minimal_v1.zip"` στο ίδιο notebook.
Έπειτα διάλεξε το επόμενο `STAGE`. Η εξαγωγή δεν αντικαθιστά υπάρχοντα run folders.
Κράτα το ίδιο source bundle, dependency versions και GPU/runtime για ακριβή resume.
Αν αλλάξει το περιβάλλον, η συνέχεια απορρίπτεται· δεν ξεκινά αυτόματα νέο run.

Ο runner ελέγχει config/data/source/environment πριν επαναχρησιμοποιήσει ολοκληρωμένο
checkpoint. Οι evaluations έχουν cache με checksum checkpoint/dataset, code, συσκευή
και ρυθμίσεις. Αλλαγή checkpoint ή conditions δημιουργεί νέα αξιολόγηση, όχι νέα εκπαίδευση.
Το `study_summary.json` μετρά μοναδικά trainings, πραγματικά steps και training-loop χρόνους.

Το ελάχιστο πλήρες πλάνο είναι **4 × 50 epochs = 200 epochs / 15.800 steps**,
συμπεριλαμβανομένων των 3 αρχικών benchmark epochs. Τα 4 × 8 = 32 τελικά condition
evaluations και οι permutations δεν είναι πρόσθετα trainings. Ένα seed δεν εκτιμά
μεταβλητότητα μεταξύ ανεξάρτητων εκπαιδεύσεων. Πρόσθετα μοντέλα/budgets/seeds δεν εκκινούν αυτόματα.

Αν Internet είναι off, οι εξαρτήσεις πρέπει να είναι ήδη στο Kaggle image ή να προστεθούν
ως wheel dataset. Δεν αντιγράφουμε το Windows CPU venv σε Linux CUDA. Δεν απαιτείται
Kaggle API token για αυτή τη χειροκίνητη ροή.
