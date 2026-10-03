# Πειραματικό πρωτόκολλο v0.3 — εγκεκριμένη σύγκριση baseline/combined

Αίτημα χρήστη: ένα Kaggle notebook και όσο λιγότερες εκπαιδεύσεις γίνεται.
Συγκρίνουμε2 νέα CNNs,10k training traces,seed0. Διατηρούνται δύο ιστορικά failures.
Έως4 GPU trainings συνολικά. Combined μόνο αν baseline clean SR@2000≥0,90 (18/20).
Δεν τρέχουμε single noise/shift, MLP, δεύτερο budget ή seed sweep.

## Threat model και περιορισμοί

Ο profiling attacker έχει πρόσβαση σε αντίστοιχη συσκευή με ελεγχόμενο/γνωστό κλειδί,
γνωστά plaintexts και labeled traces. Στη φάση attack γνωρίζει plaintexts και λαμβάνει traces,
ενώ το target key είναι άγνωστο. Το δίκτυο λαμβάνει **μόνο το trace**· plaintexts χρησιμοποιούνται
στη μετατροπή class likelihoods σε scores για τις 256 υποθέσεις κλειδιού.
Το secret key χρησιμοποιείται μόνο για υπολογισμό του πραγματικού rank/SR στην αξιολόγηση.

Το ASCAD fixed-key έχει το ίδιο κλειδί στο profiling και attack campaign. Άρα δεν ελέγχει
μεταφορά σε άγνωστο νέο κλειδί ή διαφορετική φυσική συσκευή. Η γνωστή profiling συσκευή
ουσιαστικά αποκαλύπτει το ίδιο key, οπότε εδώ μελετάμε benchmark της διαρροής/κατάταξης,
όχι ρεαλιστική επίθεση σε ανεξάρτητο άγνωστο key. Το μικρό 700-point window έχει ήδη επιλεγεί
από τους δημιουργούς. Variable-key/δεύτερο dataset χρειάζεται για ισχυρότερη γενίκευση.

## Split και κανονικοποίηση

Χρησιμοποιούμε ανεξάρτητο `default_rng(split_seed=2026)` για permutation των profiling rows.
Οι πρώτες 5.000 είναι validation· τα επόμενα 10.000 είναι το μοναδικό training budget.
Αποθηκεύουμε πραγματικά indices και SHA-256 split identifier. Τα 10.000 επίσημα attack rows
κρατούνται αποκλειστικά για τελική αξιολόγηση. Τα μικρά pilot configs έχουν δικά τους μικρότερα splits.
Κάθε online augmented view δημιουργείται αφού επιλεγεί το αρχικό trace από το training split.

Ενεργή έκδοση: `z[t]=(x[t]−min_train[t])/(max_train[t]−min_train[t])`, ανά χρονική θέση.
Fit float64 στα10k training rows, output float32. Constant-column scale=1.
Ίδια training-only στατιστικά για validation/attack, χωρίς refit ή clipping.
Οι δύο στρατηγικές έχουν κοινό fit. Τα ιστορικά ReLU/Leaky runs είχαν global scalar μ/σ.
Δεν αποτελούν matched ablation της νέας normalization/architecture.

## Αλλοιώσεις

1. Μετά την κανονικοποίηση, κάθε trace παίρνει ανεξάρτητο integer shift
   `d ~ DiscreteUniform{-s,…,+s}`. `d>0` μετακινεί το σήμα δεξιά.
2. Το output παραμένει μήκους 700. Τα samples έξω από το παράθυρο απορρίπτονται.
   Οι κενές θέσεις παίρνουν0 σε normalized μονάδες, δηλαδή per-position training minimum
   στην ενεργή MinMax έκδοση. Η παλιά scalar έκδοση αντιστοιχούσε σε training mean.
   Δεν υπάρχει circular wrap. Κάθε trace μπορεί να χάσει έως s/700 των samples του.
3. Ακολουθεί ανεξάρτητος θόρυβος σε **όλες** τις output θέσεις:
   `ε[t] ~ Normal(0,a²)` σε normalized μονάδες, per-position inverse raw std
   `a × (max_train[t]−min_train[t])` στην ενεργή έκδοση.
   Άρα και το padding παίρνει θόρυβο στις combined/noise συνθήκες.
4. Training: online αντικατάσταση, ένα view ανά trace ανά epoch. Validation training-loop: καθαρό.
   Δεν δημιουργούμε επιπλέον optimization steps.

Το zero padding μπορεί να αποκαλύπτει το shift ή να δημιουργεί border cues. Το edge padding
υλοποιείται για sensitivity: επαναλαμβάνει την κοντινότερη πραγματική ακραία τιμή.
Και αυτή η επιλογή μπορεί να δημιουργεί τεχνητά patterns. Δεν αποτελεί φυσική προσομοίωση
της έξω από το παράθυρο κυματομορφής. Πριν το κύριο matrix εξετάζουμε training-only SNR/waveforms
με `scripts/audit_boundaries.py`, label/mask-related περιοχές και padding sensitivity σε validation.
First-order identity SNR σε masked implementation **δεν αποδεικνύει** ότι διατηρήθηκε όλη η διαρροή.
Αν κρίσιμα samples είναι κοντά στα borders, μειώνουμε shifts ή αιτιολογούμε μεγαλύτερο window
και τότε μόνο τη λήψη πρόσθετων δεδομένων. Τα shifts 5/10 είναι αρχικές επιλογές, όχι πιστοποιημένα ασφαλή.
Με per-position scaling, shift μετά την normalization δεν ισοδυναμεί με physical raw shift
πριν από αυτή. Η μελέτη αφορά αυτές τις συγκεκριμένες synthetic feature-space corruptions,
χωρίς ισχυρισμό φυσικής προσομοίωσης jitter/noise ή γενίκευσης σε νέα συσκευή.

## Training και συγκρίσεις

Το `cnn_literature` είναι κοινό στις `none/combined`: Conv4/k1, SELU/BN, AvgPool2,
dense10×2, logits256,16.952 parameters. Initial σ=0,1, s=5 σε MinMax μονάδες.
Adam lr=0,001, batch128, 50 epochs, χωρίς early stopping. Ίδια initial model seed0 και
ανεξάρτητος common shuffle generator `seed+10000`. 10.000 traces: 79 steps/epoch,
3.950/run. Τα δύο τρέχοντα trainings έχουν έως7.900steps.
Το default compare εκτελεί το none σε50epochs και χρησιμοποιεί τις πρώτες3 για
cost reference. Το προαιρετικό benchmark stage εκτελεί3 και συνεχίζει άλλες47 στο
ίδιο checkpoint. Και στις δύο περιπτώσεις το σύνολο παραμένει50epochs.

Μετράμε training-loop wall time μετά από CUDA synchronize, μαζί με augmentation και transfers.
Validation time χωριστά. Setup, HDF5 inspection και checkpoint I/O δεν περιλαμβάνονται σε αυτόν
τον training-loop χρόνο· για συνολικό κόστος καταγράφουμε επιπλέον notebook elapsed time.
Ίδιο πλήθος steps δεν εγγυάται ίδιο wall time· αποφεύγουμε ισχυρισμό «ίδιο συνολικό compute».
Κόστος HPO και exploratory pilots αναφέρεται χωριστά. Η πρώτη εκτίμηση χρησιμοποιεί τις
3 αρχικές none epochs στην ίδια GPU. Το overhead των άλλων augmentations είναι ακόμη
άγνωστο πριν εκτελεστεί· αναφέρουμε πρόβλεψη αναφοράς με margin και πραγματικό κόστος κάθε run.
Τα πραγματικά κόστη όλων των runs καταγράφονται στο `study_summary.json`.

Αν χρειαστεί tuning, αλλάζουμε μόνο βάσει validation και κρατάμε log κάθε δοκιμής.
Οριστικοποιούμε configs/criterion/code hash σε artifact πριν την πρώτη τελική attack αξιολόγηση.
Δεν επιλέγουμε θόρυβο, shifts, epoch ή μοντέλο επειδή κερδίζουν στο attack set.

## Evaluation grid και κύριες μετρικές

Το `configs/evaluation_final.json` προκαθορίζει clean, noise0,1, shift5, combined0,1/5,
combined0,05/2, και OOD 0,2/5, 0,1/10, 0,2/10. «Matched» σημαίνει matched intensity με
τη σχετική training στρατηγική, όχι κοινή training distribution για όλα τα μοντέλα.
Οι προσθήκες είναι **συνθετικές αλλοιώσεις πραγματικών μετρήσεων**, όχι cross-device traces.

Inference κάνει `log_softmax` σε float64. Για κάθε trace i και candidate k:
`score[k] += log P(class=SBOX(plaintext_i[2] XOR k) | trace_i)`.
Δεν πολλαπλασιάζουμε πιθανότητες. Rank 0 σημαίνει καλύτερος υποψήφιος. Σε ακριβή ισοβαθμία,
όλες οι equally-scored λάθος υποθέσεις μετρούν πριν το σωστό byte (conservative rank).
Uniform predictions δίνουν rank255 και SR0, αποφεύγοντας πλασματική επιτυχία με ties.

Ανά training seed και condition: 100 permutations, χωρίς replacement μέσα σε κάθε επανάληψη,
2.000 traces από διαθέσιμο pool10.000, κοινό attack-order seed8001. Το corruption realization
παραμένει σταθερό ανά condition, generated σε CPU με seed9001/batch256 και επαναχρησιμοποιείται
σε όλα τα trainings. Η attack-order μεταβλητότητα είναι conditional στο συγκεκριμένο corruption
realization· robustness σε άλλα corruption seeds αποτελεί ξεχωριστή sensitivity.

- GE(n) = μέσο zero-based rank σε attack repetitions.
- SR(n) = ποσοστό repetitions με rank0· classification accuracy/loss είναι βοηθητικά.
- Traces to success = ελάχιστο n με SR≥0,90 για **όλα** τα επόμενα counts μέχρι 2.000.
  Αν αποτύχει: `null`, `recovery_censored=true`, παρουσίαση `>2000`. Δεν αντικαθιστούμε
  τα failures με 2000 και δεν παίρνουμε απλό μέσο όρο μόνο των επιτυχιών.
- Model size = trainable parameters και checkpoint bytes, με optimizer μέσα στο checkpoint.

## Αβεβαιότητα και ερμηνεία

Κρατάμε ranks ανά attack repetition στο μοναδικό training seed0. Τα plots δείχνουν
GE/SR curves και paired περιγραφικές διαφορές των τεσσάρων στρατηγικών. Οι 100 permutations
έχουν κοινά traces και δεν είναι ανεξάρτητα trainings. Με ένα seed δεν υπολογίζουμε
between-training SD, seed bootstrap intervals ή ισχυρισμούς σταθερού οφέλους μεταξύ seeds.
Δεν ελέγχουμε εξάρτηση από το data budget με ένα μόνο budget. Πρόσθετα seeds/budgets
απαιτούν συγκεκριμένο ερευνητικό λόγο και συμφωνία του χρήστη.

Κύριο endpoint n_train10k, combined_both_ood, SR@2000. GE και censored threshold traces
υποστηρίζουν την ερμηνεία, μαζί με clean ζημιά και GPU κόστος. Το ερευνητικό αποτέλεσμα
θα κριθεί μετά το κύριο matrix, την επιβεβαίωση και συζήτηση με τον καθηγητή.
