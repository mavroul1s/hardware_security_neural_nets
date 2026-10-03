# Πειραματικό πρωτόκολλο v0.1 — προσωρινό

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
Οι πρώτες 5.000 είναι validation· τα επόμενα 5.000/10.000 είναι nested training budgets.
Αποθηκεύουμε πραγματικά indices και SHA-256 split identifier. Τα 10.000 επίσημα attack rows
κρατούνται αποκλειστικά για τελική αξιολόγηση. Τα μικρά pilot configs έχουν δικά τους μικρότερα splits.
Κάθε online augmented view δημιουργείται αφού επιλεγεί το αρχικό trace από το training split.

`z=(x−μ_train)/σ_train`, με έναν scalar μ και σ από όλα τα training samples, float64 fit και
float32 inputs. Ο ίδιος μετασχηματισμός εφαρμόζεται σε validation/attack χωρίς νέο fit.
Μεγαλύτερα budgets έχουν δικό τους training-only fit· οι στρατηγικές στο ίδιο budget έχουν κοινό fit.

## Αλλοιώσεις

1. Μετά την κανονικοποίηση, κάθε trace παίρνει ανεξάρτητο integer shift
   `d ~ DiscreteUniform{-s,…,+s}`. `d>0` μετακινεί το σήμα δεξιά.
2. Το output παραμένει μήκους 700. Τα samples έξω από το παράθυρο απορρίπτονται.
   Οι κενές θέσεις παίρνουν 0 σε normalized μονάδες, δηλαδή training mean σε raw μονάδες.
   Δεν υπάρχει circular wrap. Κάθε trace μπορεί να χάσει έως s/700 των samples του.
3. Ακολουθεί ανεξάρτητος θόρυβος σε **όλες** τις output θέσεις:
   `ε[t] ~ Normal(0, a²)` σε normalized μονάδες, raw std `a × σ_train`.
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

## Training και συγκρίσεις

Το CNN είναι κοινό στις `none/noise/shift/combined`. Initial σ=0,1, s=5.
Adam lr=0,001, batch128, 50 epochs, χωρίς early stopping. Ίδια initial model seed και
ανεξάρτητος common shuffle generator `seed+10000`. 5.000 traces: 40 steps/epoch,
2.000/run. 10.000 traces: 79 steps/epoch, 3.950/run. Το matrix 40 trainings έχει 119.000 steps.
Τα steps μεταξύ **διαφορετικών** budgets δεν είναι ίσα· εξετάζουν χωριστές small-data συνθήκες.

Μετράμε training-loop wall time μετά από CUDA synchronize, μαζί με augmentation και transfers.
Validation time χωριστά. Setup, HDF5 inspection και checkpoint I/O δεν περιλαμβάνονται σε αυτόν
τον training-loop χρόνο· για συνολικό κόστος καταγράφουμε επιπλέον notebook elapsed time.
Ίδιο πλήθος steps δεν εγγυάται ίδιο wall time· αποφεύγουμε ισχυρισμό «ίδιο συνολικό compute».
Κόστος HPO και exploratory pilots αναφέρεται χωριστά. Πριν GPU sweep εκτελούμε 3-epoch
benchmarks ανά στρατηγική, στο ίδιο hardware, με margin και μετρημένο evaluation overhead.

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

Κρατάμε ranks ανά attack repetition **μέσα** σε κάθε training seed. Επίσημα plots δείχνουν
GE/SR curves και seed-level summaries. Οι 100 permutations δεν ισοδυναμούν με 100
ανεξάρτητα trainings και έχουν κοινά traces. Αναφέρουμε Monte Carlo εύρος χωριστά από
mean/SD μεταξύ 5 training seeds. Για paired διαφορές χρησιμοποιούμε seed-level bootstrap
exploratorily, με σαφή προειδοποίηση ότι n=5 δίνει ασταθή intervals. Δεν κάνουμε
pseudo-replication πολλαπλασιάζοντας seeds επί permutations.

Κύριο endpoint n_train10k, combined_both_ood, SR@2000. GE και censored threshold traces
υποστηρίζουν την ερμηνεία, μαζί με clean ζημιά και GPU κόστος. Το ερευνητικό αποτέλεσμα
θα κριθεί μετά το κύριο matrix, την επιβεβαίωση και συζήτηση με τον καθηγητή.
