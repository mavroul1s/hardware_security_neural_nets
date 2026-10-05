# Σχέδιο project

Ημερομηνία έναρξης: 2026-10-03 (Europe/Athens). Ο χρήστης έχει ένα εξάμηνο,
χωρίς ακόμη συγκεκριμένη ημερομηνία ή κριτήρια μαθήματος. Έχει ήδη πρόσβαση Kaggle GPU.
Δεν μετατρέπουμε αυθαίρετα το εξάμηνο σε δεσμευτική ημερομηνία παράδοσης.
Ο χρήστης ζήτησε ελαχιστοποίηση Kaggle εκπαιδεύσεων και notebooks. Το προηγούμενο
πλάνο46 trainings και το μεταγενέστερο τεσσάρων στρατηγικών αντικαταστάθηκαν:
**ένα notebook, νέο baseline και conditional combined, έως4 trainings συνολικά**.
Έχουν ολοκληρωθεί δύο αποτυχημένα baseline trainings, ReLU και LeakyReLU0,1,
με ίδιο10k/5k/seed0/50epochs/LR0,001. Και τα δύο είχαν clean validation SR0/20.
Διατηρούμε τα αρνητικά αποτελέσματα. Δεν εκτελούμε single noise/shift ή αυτόματο HPO.
Η read-only masking διάγνωση βρήκε δεύτερης τάξης leakage που διατηρείται στο
validation. Προετοιμάστηκε untrained literature-inspired CNN16.952 parameters.
Ο χρήστης ενέκρινε τον περιορισμό σε νέο baseline και conditional combined (έως4 trainings
μαζί με τα δύο failures). Οι single noise/shift εκπαιδεύσεις καταργούνται.
Ενεργό μοντέλο `cnn_literature` /16.952 parameters, train-only per-position MinMax.
Gate πριν το combined: clean validation SR@2.000≥0,90, δηλαδή18/20 permutations.
Αποτέλεσμα version7: baselineSR0/20, gate failed, combined skipped. Σύνολο3 πλήρη
GPU trainings. Το M3 robustness comparison δεν ολοκληρώθηκε· δεν τεκμηριώνεται
όφελος ή βλάβη του training augmentation. ΝέαGPU πρόταση μόνο μετά από διάγνωση.
CPU διάγνωση4/10: υπάρχοντα training-selected centered products181×521 και156×517
δίνουν20/20 clean validation recovery με correlation/HW hypothesis scoring.
Η πληροφορία στα δεδομένα είναι αξιοποιήσιμη· το τρέχον CNN setup δεν τη γενικεύει
επαρκώς. BN counterfactual χωρίς weight updates δεν επανέφερε ανάκτηση.
CPU sensitivity της 5/10 με τα ίδια σημεία/κέντρα: θόρυβος σ=0,1 δίνει 20/20 στα
δύο σταθερά ζεύγη, combined σ=0,1/shift±5 δίνει 1/20 και 11/20, γνωστή τεχνητή
μετατόπιση επαναφέρει 20/20. Το oracle είναι διαγνωστικός έλεγχος, όχι έτοιμη μέθοδος
ευθυγράμμισης. Στο σ=0,2 δεν φτάνει 18/20 εντός 2.000 traces. Zero/edge padding
δίνει ίδια προϊόντα στα εσωτερικά σημεία. Πέρασαν 640 endpoint checks και 44 tests.
Οι αλλοιώσεις εφαρμόστηκαν μόνο σε profiling validation, μετά το MinMax, χωρίς
νέες εκπαιδεύσεις ή ένταση επιλεγμένη από attack.
Ο διαγνωστικός έλεγχος δεν αλλάζει το CNN gate ή το budget. Επόμενο: σύνθεση
ευρημάτων/ορίων και έλεγχος του ερευνητικού ερωτήματος πριν από νέα GPU πρόταση.
Για νέο baseline+combined θα απαιτούνταν δύο νέα GPU trainings, πέρα από το
αρχικό όριο 4 με τα 3 ήδη ολοκληρωμένα· χρειάζεται συμφωνία αλλαγής scope/ορίου.

Σύνθεση της5/10 ολοκληρώθηκε στο `outputs/study_synthesis_2026-10-05/REPORT_EL.md`.
Η ελεγμένη τρέχουσα κατεύθυνση είναι διαγνωστική πανεπιστημιακή μελέτη περίπτωσης,
με σύνδεση στα CNN failures και την υπάρχουσα δεύτερης τάξης διαρροή. Το αρχικό
augmentation ερώτημα παραμένει ανοικτό· δεν μετρήθηκε επίδραση training augmentation.
Η βιβλιογραφία δεν τεκμηριώνει νέα τεχνική ή εγγυημένο ερευνητικό κενό.
Επόμενο βήμα μέσα στο ισχύον scope: αναπαραγωγή/έλεγχος των υπαρχόντων artifacts
από καθαρό CPU περιβάλλον, χωρίς αλλαγή models, budgets, seeds ή πρωτοκόλλου.

## Προσωρινό ερευνητικό ερώτημα

Αρχικό ερώτημα, ακόμη αναπάντητο μετά το failed baseline gate:

Με 10.000 μοναδικά profiling traces, κοινό μικρό CNN και ίδιο πλήθος
optimization steps, ποια είναι η επίδραση του συνδυασμού Gaussian noise και
μη κυκλικών χρονικών μετατοπίσεων στο SR@2.000 απέναντι σε προκαθορισμένες ταυτόχρονες
αλλοιώσεις εκτός των training εντάσεων, έναντι εκπαίδευσης χωρίς augmentation,
χωρίς adaptation σε δεδομένα του target;
Ποιο είναι το κόστος του σε πραγματικό χρόνο στην ίδια GPU και η επίδραση στο clean SR;

Η ενεργή μελέτη είναι διερευνητική σύγκριση baseline/combined robustness και κόστους
σε ένα περιορισμένο data budget. Με ένα seed δεν εκτιμάται μεταβλητότητα μεταξύ trainings
ούτε εξάρτηση από διαφορετικά data budgets. Η ιδέα «augmentation βοηθά» έχει ήδη μελετηθεί. Η πρωτοτυπία
του συγκεκριμένου συνδυασμού/πρωτοκόλλου **δεν έχει επιβεβαιωθεί**.
Η βιβλιογραφία 2025–2026 προσθέτει diffusion, domain adaptation και equivariant CNNs·
πρέπει να ελεγχθεί η άμεση επικάλυψη πριν διατυπωθεί ισχυρισμός paper.

## Milestones και κριτήρια ολοκλήρωσης

| Στάδιο | Ενδεικτικός χρόνος από την έναρξη | Κριτήριο |
|---|---|---|
| M0: υποδομή/αρχική χαρτογράφηση | εβδομάδες 1–2 | επίσημο checksum, schema/labels verified, tests, CPU pilot, Kaggle notebook |
| M1: πραγματικό baseline | εβδομάδες 2–4 | πρώτες 3 CNN epochs ως benchmark, συνέχιση του ίδιου run σε 50, validation key-rank |
| M2: οριστικοποίηση ερωτήματος | εβδομάδες 3–6 | πλήρης έλεγχος επικαλύψεων και padding/cropping, πάγωμα protocol/config hash πριν attack |
| M3: μικρή σύγκριση | εβδομάδες 6–12 | 2 τρέχοντα CNNs: none/combined, ίδιο seed/split/steps· δύο παλιότερα failures διατηρούνται |
| M4: έλεγχος ευρήματος | εβδομάδες 12–17 | ανάλυση ορίων και overlap· πρόσθετα trainings μόνο με συγκεκριμένο λόγο και συμφωνία χρήστη |
| M5: αναφορά | εβδομάδες 17–22 | ελληνική αναφορά με μεθόδους, γραφήματα, όρια και αρνητικά αποτελέσματα |
| M6: σύνθεση/παράδοση | υπόλοιπο εξαμήνου | αναπαραγωγή από καθαρό environment, συζήτηση καθηγητή, αγγλικό draft μόνο αν επαρκούν τα ευρήματα |

## Αποφάσεις

1. ASCAD original fixed-key 700 samples, zero-based byte 2, 256 identity classes.
2. JSON configs, PyTorch2.8.0, per-position MinMax fit μόνο στα training rows.
   Global scalar normalization παραμένει για ανάγνωση των δύο ιστορικών runs.
3. MLP 700→128→64→256. CNN Conv(1→8,k11), pool2, Conv(8→16,k11), pool2,
   dense64→256, αρχικά ReLU και στην εγκεκριμένη διορθωτική έκδοση LeakyReLU0,1.
   Μικρό δικό μας baseline, όχι αναπαραγωγή SOTA αρχιτεκτονικής.
   Ενεργό CNN: Conv4/k1, SELU/BatchNorm, pool2, dense10×2 και logits256·16.952 parameters.
4. Ίδια epochs και batches στις 2 στρατηγικές εντός κάθε budget. Online replacement
   augmentation: μία όψη ανά αρχικό trace ανά epoch, χωρίς αύξηση αριθμού batches.
5. Split seed 2026, training seed 0, test-corruption seed 9001, attack-order seed 8001.
6. Αρχικές training εντάσεις sigma=0,1 σε normalized μονάδες και shifts uniform{-5,…,5}.
   OOD κύρια συνθήκη sigma=0,2 και shifts{-10,…,10}. Προσωρινές μέχρι validation/boundary audit.
7. Validation 5.000 rows και training 10.000 από τις υπόλοιπες rows. Δεν τρέχουμε δεύτερο budget.
8. CPU pilot αξιολογείται σε profiling validation. Το τελικό attack set δεν χρησιμοποιείται
   για pilot tuning. Ο πλήρης baseline προορίζεται για GPU.
9. Checkpoint επιλογή clean validation CE, fixed epochs· GE/SR ως κύριες τελικές μετρικές.
10. Αν όλες οι στρατηγικές αποτυγχάνουν, δεν συμπεραίνουμε ότι το augmentation δεν ωφελεί.
    Πρώτα ελέγχουμε model capacity/εκπαίδευση σε validation και τη δυσκολία του budget.
11. Ένα Kaggle notebook με `STAGE=benchmark/baseline/compare/attack`. Οι πρώτες 3 epochs
    του none αποτελούν μέρος των 50 epochs του baseline, όχι πρόσθετο training.
    Ίδια ολοκληρωμένα checkpoints/evaluations επαναχρησιμοποιούνται. Η προβλεπόμενη
    none/combined σύγκριση είχε έως7.900 steps· εκτελέστηκε μόνο το none3.950 μετά το failed gate.
12. MLP, δεύτερο budget και πολλά seeds μένουν διαθέσιμα ως μελλοντικές επιλογές,
    χωρίς προεπιλεγμένη εκτέλεση. Με δύο μοντέλα συγκρίνουμε μόνο none/combined·
    δεν αποδίδουμε αποτέλεσμα στον συνδυασμό έναντι κάθε single στρατηγικής.

## Πότε υποστηρίζεται ή αποδυναμώνεται η πρόταση

Κύριο endpoint: paired διαφορά SR@2.000 για combined έναντι none baseline,
στην `combined_both_ood` με n_train=10.000. Ενδεικτικός στόχος πρακτικού οφέλους:
τουλάχιστον +0,10 SR και clean υποβάθμιση όχι πάνω από 0,10. Αυτά είναι δικά μας
προκαθορισμένα κριτήρια, όχι συμπεράσματα πηγών. Με seed0 τα αποτελέσματα είναι περιγραφικά.

Πρώτη ένδειξη: όφελος στο κοινό seed0, ίδιο step budget και ανεκτό measured overhead.
Ισχυρότερη υποστήριξη απαιτεί ανεξάρτητα training seeds και επιβεβαίωση με άλλη padding
policy ή dataset· αυτά δεν καλύπτονται από το τωρινό ελάχιστο πλάνο.
Αποδυνάμωση: μηδενικό/αρνητικό όφελος, όφελος μόνο in-distribution, μεγάλη clean ζημιά,
ή αποτέλεσμα που εξηγείται από extra steps, tuning ή τεχνητά borders.
Το ενεργό πλάνο δεν εκτιμά factorial interaction ή την καλύτερη single στρατηγική.
Αν νεότερη πρωτογενής εργασία καλύπτει το ίδιο protocol, αναπροσαρμόζουμε σε replication
και cost/small-data analysis χωρίς ισχυρισμό νέας τεχνικής.

## Ερώτημα της τρέχουσας σύνθεσης

Στο συγκεκριμένο ASCAD fixed-key/10k-training setup, τι αποκαλύπτουν οι παγωμένοι
training-only στατιστικοί έλεγχοι και οι frozen CNN διαγνώσεις για την αποτυχία
ανάκτησης του byte; Πώς αλλάζει η υπάρχουσα fixed-point correlation με τις ήδη
προκαθορισμένες feature-space corruptions, και ποια όρια έχει το known-shift control;
Αυτό περιγράφει τα εκτελεσμένα validation πειράματα· δεν είναι νέο GPU scope,
equal-information μέτρηση υπεροχής correlation ή τελική attack επιβεβαίωση.
