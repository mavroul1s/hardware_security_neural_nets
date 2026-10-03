# Εκτέλεση στο Kaggle

Έλεγχος δημόσιας τεκμηρίωσης: 2026-10-03. Ο χρήστης επιβεβαίωσε ενεργή πρόσβαση GPU.
Δεν συνδεθήκαμε στον λογαριασμό, δεν επιθεωρήσαμε προσωπικό quota και δεν εκτελέσαμε Kaggle training.

Η [επίσημη τεκμηρίωση](https://www.kaggle.com/docs/notebooks) αναφέρει επιλογές P100/T4×2,
sessions μέχρι 12 ώρες CPU/GPU και 20 GB αποθηκευόμενου χώρου `/kaggle/working`.
Η [GPU τεκμηρίωση](https://www.kaggle.com/docs/efficient-gpu-usage) αναφέρει quota συνήθως
30 ώρες/εβδομάδα, ενίοτε υψηλότερο ανάλογα με ζήτηση/πόρους. Η διαθεσιμότητα περιορίζεται
και μπορεί να υπάρχει ουρά. Αυτά δεν εγγυώνται το σημερινό quota ή hardware του λογαριασμού.

## Βήματα

1. Δημιούργησε **private Kaggle Dataset** με το zip του κώδικα
   `outputs/kaggle_project.zip`, που εξαιρεί `.venv`, datasets, runs και checkpoints.
   Πρόσθεσε ξεχωριστό dataset με `data/ASCAD.h5` και `data/ASCAD.provenance.json`.
   Δεν χρειάζεται να ανεβάσεις το raw ZIP των 4,4 GB.
2. Δημιούργησε notebook με **Import Notebook** και διάλεξε `notebooks/kaggle_baseline.ipynb`.
   Με **Add Input** πρόσθεσε τα δύο datasets.
3. Settings → Accelerator → διαθέσιμη GPU. Έλεγξε το εμφανιζόμενο remaining quota,
   runtime limit και internet toggle. Αποθήκευσε τα πραγματικά στοιχεία στο αρχείο budget
   του notebook. Το παρόν PyTorch pipeline χρησιμοποιεί **μία** GPU ακόμη και με T4×2.
4. Εκτέλεσε τις discovery/setup cells. Το notebook εντοπίζει το code ZIP και `ASCAD.h5`,
   ελέγχει checksum, CUDA και GPU name και κρατά `pip freeze`. Για pinned CUDA torch2.8
   επιλέγει το official cu126 wheel· μπορείς να χρησιμοποιήσεις το έτοιμο Kaggle torch
   απενεργοποιώντας εγκατάσταση, με τις αποκλίσεις καταγραμμένες και χωρίς ισχυρισμό ίδιο environment.
5. Άφησε πρώτα `RUN_BENCHMARK=True` και `RUN_BASELINES=False`. Γίνονται 3 epochs ανά
   στρατηγική, n_train10k/validation5k, και παράγονται κόστη. Εξέτασε τα πραγματικά timings,
   διαθέσιμο quota και validation diagnostics πριν ενεργοποιήσεις πλήρη εκπαίδευση.
6. Μετά, ενεργοποίησε `RUN_BASELINES=True`. Γίνονται οι δύο seed0 baselines 50 epochs.
   Το notebook έχει `RUN_FINAL_ATTACK=False`. Χρησιμοποιούμε αρχικά validation, ώστε
   το attack set να παραμείνει τελικό. Το notebook δεν ξεκινά αυτόματα το matrix των 40 runs.
7. Για συνέχεια, ανέβασε το προηγούμενο run folder ως private Input, αντέγραψέ το στο
   `/kaggle/working`, κράτησε το ίδιο runtime/code/dependencies και κάλεσε train(..., resume=True)
   με περισσότερα epochs. Κράτα όλα τα `.pt`, configs, indices και manifests. Η ακριβής
   συνέχιση απορρίπτεται αν άλλαξε συσκευή ή περιβάλλον· νέα GPU συνιστά νέο run.
8. **Save Version → Save & Run All** για αναπαραγώγιμη αποθηκευμένη εκτέλεση.
   Κατέβασε το output archive από `/kaggle/working`, μαζί με checkpoint/logs/versions.
   Quick Save μόνο δεν αποδεικνύει ότι εκτελέστηκε το notebook. Απενεργοποίησε GPU όταν τελειώσεις.

Αν Internet είναι off, οι εξαρτήσεις πρέπει να είναι ήδη στο Kaggle image ή να προστεθούν
ως wheel dataset. Δεν αντιγράφουμε το Windows CPU venv σε Linux CUDA. Δεν απαιτείται
Kaggle API token για αυτή τη χειροκίνητη ροή.
