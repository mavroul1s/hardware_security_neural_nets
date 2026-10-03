# Σχέδιο project

Ημερομηνία έναρξης: 2026-10-03 (Europe/Athens). Ο χρήστης έχει ένα εξάμηνο,
χωρίς ακόμη συγκεκριμένη ημερομηνία ή κριτήρια μαθήματος. Έχει ήδη πρόσβαση Kaggle GPU.
Δεν μετατρέπουμε αυθαίρετα το εξάμηνο σε δεσμευτική ημερομηνία παράδοσης.
Ο χρήστης ζήτησε ελαχιστοποίηση Kaggle εκπαιδεύσεων και notebooks. Το προηγούμενο
πλάνο 46 trainings αντικαταστάθηκε: **ένα notebook, τέσσερις CNN στρατηγικές**.
Μετά το αποτυχημένο baseline και τη διάγνωση inactive ReLU units, ο χρήστης ενέκρινε
μία διορθωτική εκπαίδευση με LeakyReLU0,1, ίδιο10k/5k/seed0/50epochs/LR0,001.
Το original failure διατηρείται· έως5 trainings συνολικά με4 διορθωμένες στρατηγικές,
στο ίδιο notebook. Validation gate πριν τις άλλες3, χωρίς αυτόματο hyperparameter search.
Έχουν ολοκληρωθεί δύο baseline trainings. Το διορθωμένο baseline επίσης έχει SR0/20
στο clean validation· οι άλλες3 στρατηγικές παραμένουν σε αναμονή για διάγνωση.

## Προσωρινό ερευνητικό ερώτημα

Με 10.000 μοναδικά profiling traces, κοινό μικρό CNN και ίδιο πλήθος
optimization steps, βελτιώνει ο συνδυασμός Gaussian noise και
μη κυκλικών χρονικών μετατοπίσεων το SR@2.000 απέναντι σε προκαθορισμένες ταυτόχρονες
αλλοιώσεις εκτός των training εντάσεων, χωρίς adaptation σε δεδομένα του target;
Ποιο είναι το κόστος του σε πραγματικό χρόνο στην ίδια GPU και η επίδραση στο clean SR;

Η αρχική μελέτη θα είναι διερευνητική σύγκριση interaction/robustness και κόστους
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
| M3: μικρή σύγκριση | εβδομάδες 6–12 | 4 CNNs συνολικά: none/noise/shift/combined, ίδιο seed/split/steps, όλα τα failures |
| M4: έλεγχος ευρήματος | εβδομάδες 12–17 | ανάλυση ορίων και overlap· πρόσθετα trainings μόνο με συγκεκριμένο λόγο και συμφωνία χρήστη |
| M5: αναφορά | εβδομάδες 17–22 | ελληνική αναφορά με μεθόδους, γραφήματα, όρια και αρνητικά αποτελέσματα |
| M6: σύνθεση/παράδοση | υπόλοιπο εξαμήνου | αναπαραγωγή από καθαρό environment, συζήτηση καθηγητή, αγγλικό draft μόνο αν επαρκούν τα ευρήματα |

## Αποφάσεις

1. ASCAD original fixed-key 700 samples, zero-based byte 2, 256 identity classes.
2. JSON configs, PyTorch 2.8.0, global scalar normalization fit μόνο στα training rows.
3. MLP 700→128→64→256. CNN Conv(1→8,k11), pool2, Conv(8→16,k11), pool2,
   dense64→256, αρχικά ReLU και στην εγκεκριμένη διορθωτική έκδοση LeakyReLU0,1.
   Μικρό δικό μας baseline, όχι αναπαραγωγή SOTA αρχιτεκτονικής.
4. Ίδια epochs και batches στις 4 στρατηγικές εντός κάθε budget. Online replacement
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
    Ίδια ολοκληρωμένα checkpoints/evaluations επαναχρησιμοποιούνται. Συνολικά 15.800 steps.
12. MLP, δεύτερο budget και πολλά seeds μένουν διαθέσιμα ως μελλοντικές επιλογές,
    χωρίς προεπιλεγμένη εκτέλεση. Τα τέσσερα μοντέλα είναι το ελάχιστο για τη σύγκριση
    no augmentation / κάθε single / joint, όχι γενικό ελάχιστο κάθε SCA project.

## Πότε υποστηρίζεται ή αποδυναμώνεται η πρόταση

Κύριο endpoint: paired διαφορά SR@2.000 για combined έναντι κάθε single augmentation,
στην `combined_both_ood` με n_train=10.000. Ενδεικτικός στόχος πρακτικού οφέλους:
τουλάχιστον +0,10 SR και clean υποβάθμιση όχι πάνω από 0,10. Αυτά είναι δικά μας
προκαθορισμένα κριτήρια, όχι συμπεράσματα πηγών. Με seed0 τα αποτελέσματα είναι περιγραφικά.

Πρώτη ένδειξη: όφελος στο κοινό seed0, ίδιο step budget και ανεκτό measured overhead.
Ισχυρότερη υποστήριξη απαιτεί ανεξάρτητα training seeds και επιβεβαίωση με άλλη padding
policy ή dataset· αυτά δεν καλύπτονται από το τωρινό ελάχιστο πλάνο.
Αποδυνάμωση: μηδενικό/αρνητικό όφελος, όφελος μόνο in-distribution, μεγάλη clean ζημιά,
ή αποτέλεσμα που εξηγείται από extra steps, tuning ή τεχνητά borders.
Το factorial interaction `SR_combined − SR_noise − SR_shift + SR_none` αναφέρεται
εξερευνητικά· δεν το ταυτίζουμε με τη διαφορά από την καλύτερη single στρατηγική.
Αν νεότερη πρωτογενής εργασία καλύπτει το ίδιο protocol, αναπροσαρμόζουμε σε replication
και cost/small-data analysis χωρίς ισχυρισμό νέας τεχνικής.
