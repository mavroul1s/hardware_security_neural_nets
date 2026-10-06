# Άμεσες συγκρίσεις ευθυγράμμισης και έλεγχος ερμηνείας — 2026-10-05

Μετά τις πρώτες τρεις CPU φάσεις ο χρήστης ζήτησε συνέχιση. Η τέταρτη φάση συγκρίνει
τις υπάρχουσες NCC/Gaussian εκτιμήσεις με δύο SAD παραλλαγές και έλεγχο λανθασμένης
αντιστοίχισης shifts, με νέο confirmation. Το πλάνο αποθηκεύτηκε πριν την εκτέλεση:
[plan.json](../outputs/paper_alignment_controls_2026-10-05/plan.json).

## Πρωτογενείς πηγές που ελέγχθηκαν στις 5/10

Η [επίσημη τεκμηρίωση ChipWhisperer ResyncSAD](https://chipwhisperer.readthedocs.io/en/latest/analyzer-api.html#chipwhisperer.analyzer.preprocessing.resync_sad.ResyncSAD)
περιγράφει αναζήτηση της μετατόπισης που ελαχιστοποιεί το άθροισμα απόλυτων διαφορών
ως προς παράθυρο ενός reference trace. Ο
[επίσημος πηγαίος κώδικας](https://raw.githubusercontent.com/newaetech/chipwhisperer/develop/software/chipwhisperer/analyzer/preprocessing/resync_sad.py)
δείχνει αποκλεισμό του θετικού άκρου της αναζήτησης, negative-first argmin και απόρριψη
traces πάνω από reference-derived threshold. Το URL develop είναι μεταβλητό· η
ανάγνωση καταγράφεται για τις 5/10, χωρίς ισχυρισμό pinned package reproduction.

Η δική μας σύγκριση εφαρμόζει την κλασική SAD objective με κοινό παράθυρο 20:680,
inclusive ±10, ίδια abs-offset tie rule με NCC/Gaussian και διατήρηση όλων των traces.
Δύο references: training mean και training trace που βρίσκεται πλησιέστερα στο mean
με MSE στο ίδιο παράθυρο. Η επιλογή χρησιμοποιεί μόνο τα αρχικά 10k training waveforms.
Πρόκειται για προσαρμογές SAD, όχι αναπαραγωγή του package ή νέα μέθοδο. Δεν
εγκαταστάθηκε το ChipWhisperer και δεν αντιγράφηκε ο πηγαίος κώδικάς του.

Το [Second-order Scatter Attack, §1.1, §2.2 και §3.1](https://eprint.iacr.org/2019/345.pdf)
διακρίνει στατικές μετατοπίσεις από elastic jitter/shuffling και αναλύει window-based
συνδυασμούς και joint-distribution επιλογές. Οι δικές μας global synthetic shifts
καλύπτουν μόνο την απλούστερη περίπτωση. Το Scatter δεν εκτελέστηκε εδώ, ούτε
μεταφέρουμε τους ισχυρισμούς από το δικό του benchmark στο ASCAD protocol μας.

## Ελέγξιμο νέο ερώτημα

Με τα ήδη παγωμένα training-label-only points 156×521 και 182×547, ποια είναι η
περιγραφική διαφορά recovery ανάμεσα σε NCC, Gaussian και γνωστή SAD objective;
Αν κρατήσουμε ακριβώς το histogram των Gaussian-estimated offsets αλλά τα
αντιστοιχίσουμε στο προηγούμενο αντί στο σωστό trace, διατηρείται το όφελος;

Ο δεύτερος έλεγχος χρησιμοποιεί deterministic roll κατά μία row, χωρίς νέα
corruption/training seed, και εκτελείται μόνο ως diagnostic counterfactual. Δεν
αποτελεί πρακτική μέθοδο. Αξιολογείται σε common corrupted traces/orders και δεν
περιέχει πληροφορία για τα σωστά injected shifts στην εκτίμηση ή επιλογή του roll.

Νέο confirmation 5k με seed20261008, αποκλείοντας train, validation και τις τρεις
προηγούμενες confirmation pools. Η επιλογή σημείων, search window, conditions,
συνθετικός θόρυβος και training10k παραμένουν ίδια. Δεν επιλέγουμε καλύτερο SAD
reference ή μέθοδο από confirmation αποτελέσματα.

Η σύγκριση δεν μπορεί να επιβεβαιώσει novelty, φυσικό jitter, unknown-key transfer
ή cross-device γενίκευση. Παραμένουν απαραίτητες οι ισχυρότερες κατάλληλες συγκρίσεις
και ένα ανεξάρτητο campaign/key protocol πριν από ισχυρισμό paper. Η στοχευμένη
ανάγνωση δύο primary πηγών δεν είναι εξαντλητικό literature review.
