# Πειραματικό πρωτόκολλο v0.3 — εγκεκριμένη σύγκριση baseline/combined

Αίτημα χρήστη: ένα Kaggle notebook και όσο λιγότερες εκπαιδεύσεις γίνεται.
Προβλεπόμενη σύγκριση:2 νέα CNNs,10k training traces,seed0. Διατηρούνται δύο ιστορικά failures.
Έως4 GPU trainings συνολικά. Combined μόνο αν baseline clean SR@2000≥0,90 (18/20).
Δεν τρέχουμε single noise/shift, MLP, δεύτερο budget ή seed sweep.

Κατάσταση στις2026-10-05: το literature baseline ολοκληρώθηκε και το minimum-clean-CE
checkpoint έδωσε SR0/20. Το gate απέτυχε και το combined δεν εκπαιδεύτηκε. Σύνολο3
πλήρη GPU trainings/1 notebook. Η προβλεπόμενη σύγκριση augmentation δεν έχει μετρηθεί.
Οι CPU masking/correlation/sensitivity diagnostics είναι ξεχωριστοί profiling-validation
έλεγχοι. Η επιτυχία τους δεν αντικαθιστά το CNN gate και δεν ξεκλειδώνει final attack.

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
Το Kaggle `study_summary.json` αφορά την εκάστοτε έκδοση. Η σύνθεση όλων των τριών
ολοκληρωμένων baselines καταγράφεται στο `outputs/study_synthesis_2026-10-05/evidence.json`.
Δεν προστίθενται CPU timings στους GPU loop χρόνους ως συγκρίσιμο κόστος.

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
GE/SR curves και τις προβλεπόμενες paired περιγραφικές διαφορές none/combined. Οι 100 permutations
έχουν κοινά traces και δεν είναι ανεξάρτητα trainings. Με ένα seed δεν υπολογίζουμε
between-training SD, seed bootstrap intervals ή ισχυρισμούς σταθερού οφέλους μεταξύ seeds.
Δεν ελέγχουμε εξάρτηση από το data budget με ένα μόνο budget. Πρόσθετα seeds/budgets
απαιτούν συγκεκριμένο ερευνητικό λόγο και συμφωνία του χρήστη.

Κύριο endpoint n_train10k, combined_both_ood, SR@2000. GE και censored threshold traces
υποστηρίζουν την ερμηνεία, μαζί με clean ζημιά και GPU κόστος. Το ερευνητικό αποτέλεσμα
θα κριθεί μετά το κύριο matrix, την επιβεβαίωση και συζήτηση με τον καθηγητή.

## Ξεχωριστές CPU διαγνώσεις — τι εκτελέστηκε

Το παγωμένο sensitivity protocol είναι στο
`outputs/correlation_robustness_2026-10-05/plan.json`. Training-selected points και centers,
ίδιο10k/5k split, profiling-validation pool5k,20 κοινές σειρές seed8001/budget2000,
corruption9001/batch256. Οι eight corruption conditions αξιολογήθηκαν χωρίς training.
Το μοντέλο HW hypothesis και τα προϊόντα δεν είναι identity-label neural classifier.
Training mask/share metadata χρησιμοποιήθηκε μόνο στην προηγούμενη επιλογή σημείων,
με διαφορετικό profiling information από το CNN. True validation key μόνο για reporting rank.

Το oracle διαβάζει point+injected_shift με γνωστή τεχνητή μετατόπιση, δεν εκτιμά την
ευθυγράμμιση από το trace. Fixed/oracle χρησιμοποιούν κοινά corrupted tensors εντός
συνθήκης· common trace orders σε όλες. Interleaved shift/noise RNG δεν εγγυάται κοινά
offsets μεταξύ διαφορετικών συνθηκών. Zero/edge padding δίνει ίδια επιλεγμένα προϊόντα,
αλλά αυτό δεν αποκλείει CNN border cues. Feature-space corruptions μετά το MinMax.

Πλήρεις μετρήσεις/περιορισμοί:
[CPU correlation diagnosis](../outputs/literature_diagnosis_2026-10-04/REPORT_EL.md) και
[CPU sensitivity](../outputs/correlation_robustness_2026-10-05/REPORT_EL.md).
Δεν έγινε final attack ούτε επαναπροσδιορίστηκε checkpoint/μοντέλο από final attack metrics.

## Αναπαραγωγή υπαρχόντων CPU αποτελεσμάτων — 2026-10-05

Νέο CPU venv από27 hashed exact wheels και ξεχωριστό frozen source snapshot,
ίδιο split/normalizer/checkpoints/seeds. Πέρασαν44 tests με14 υπάρχοντα warnings.
Best/last CNN CE/accuracy/ranks, δύο raw correlation curves και32 sensitivity rows/
138 arrays αναπαράχθηκαν ακριβώς, με640 ανεξάρτητα Pearson endpoint checks.
Δεν επαναλήφθηκε επιλογή features, BN counterfactual ή shuffled controls· δεν έγιναν
real-data weight updates ή Kaggle execution. Το final ASCAD attack payload δεν διαβάστηκε.
Το CNN gate παραμένει failed και combined skipped. Το αποτέλεσμα αφορά ίδιο
Windows host/base interpreter, όχι ανεξάρτητη GPU training ή cross-device αναπαραγωγή.
[Αναφορά και πραγματικοί χρόνοι](../outputs/cpu_reproduction_2026-10-05/REPORT_EL.md),
[οδηγίες](CPU_REPRODUCTION.md).

## Επέκταση προς paper με εντολή χρήστη — τρεις CPU φάσεις

Ο χρήστης ενέκρινε στις5/10 πρόσθετα πειράματα και ένταξή τους στην εργασία.
Πλάνα πριν την αντίστοιχη εκτέλεση: `outputs/paper_alignment_2026-10-05/plan.json`,
`outputs/paper_alignment_coordinates_2026-10-05/plan.json`,
`outputs/paper_maskfree_2026-10-05/plan.json`. Οι φάσεις ήταν διαδοχικές, με νέες
ερωτήσεις μετά τα προηγούμενα αποτελέσματα· δεν αποτελούν ενιαία προεγγραφή.

Train10k/validation5k διατηρούνται. Confirmation pools5k με seeds20261005/6/7,
αμοιβαία disjoint και χωριστά από train/validation, μόνο από Profiling_traces.
Mean/variance/scaler fit αποκλειστικά στο training. Η φάση3 επιλέγει μόνο από
παρεχόμενα training identity labels/HW, χωρίς training mask/share/key metadata.
Η επιλογή και τα211.575 scores αποθηκεύονται πριν validation/confirmation reads.
Οι εξετασμένες confirmation pools δεν ανακυκλώνονται ως αθέατες.

Raw pipeline S(x)+ε έναντι surrogate N⁻¹(S(N(x)))+ε. Θόρυβος ομοιόμορφου rawσ
1,3/2,6 από median train range13, διαφορετικός από την παλιά normalized sensitivity.
Η πρώτη surrogate εξαγωγή με raw centers/scales είχε coordinate confound· η φάση2
το ελέγχει σε σωστό normalized domain. Δεν αποδίδεται το clean CNN failure στη
σειρά normalization ούτε το finite-sample known-shift SR θεωρείται αυστηρό upper bound.

Trace-only NCC/Gaussian alignment ±10, template20…679 για αποκλεισμό padding.
20 common overlapping orders/budget2000/seed8001, U/Z seeds9101/2 κοινά και στις
ίσου μεγέθους pools. Ένα key byte/campaign, χωρίς independent keys ή training seeds.
Known injected shift μόνο diagnostic control. True key μόνο rank reporting· δημόσιο
plaintext μόνο candidate hypothesis scoring. Καμία final Attack_traces ανάγνωση από
τα νέα πειράματα, νέα GPU trainings0, real-data optimizer updates0.

[Πλήρη αποτελέσματα, verification και όρια](../outputs/paper_extension_2026-10-05/REPORT_EL.md).
Για έλεγχο αποθηκευμένων αποτελεσμάτων:

```powershell
& .\.venv\Scripts\python.exe notebooks/verify_paper_alignment.py
& .\.venv\Scripts\python.exe notebooks/verify_paper_followups.py
& .\.venv\Scripts\python.exe notebooks/build_paper_extension.py
# Inspect both figures before setting the visual-check flag:
& .\.venv\Scripts\python.exe notebooks/verify_paper_extension.py --plots-visually-checked
& .\.venv\Scripts\python.exe notebooks/verify_study_synthesis.py
```

Τα completed experiment directories προστατεύονται από αντικατάσταση. Τα παραπάνω
επαληθεύουν/συνθέτουν stored evidence, χωρίς νέο training. Η ανεξάρτητη CPU
αναπαραγωγή της προηγούμενης ενότητας καλύπτει το παλιό frozen suite44tests· η νέα
πλήρης εκτέλεση57tests έγινε στο ενεργό `.venv`, χωρίς νέο clean environment claim
για τα13 νέα tests.

## Τέταρτη CPU φάση: SAD και correspondence control

Frozen protocol `outputs/paper_alignment_controls_2026-10-05/plan.json`, πριν run.
Ίδια points156×521/182×547, raw conditions, training10k/validation5k, κοινά U/Z/orders.
Νέο confirmation5kseed20261008, disjoint από train/validation/τρία παλιά confirmations.
Mean/variance και representative reference αποκλειστικά από original training traces.
Reference επιλέγεται ως closest-to-mean trace στο fixed window20:680, χωρίς labels/keys/masks.

SAD mean/reference συγκρίνονται με NCC/Gaussian στο κοινό inclusive±10 search,
common tie rule και no rejection. Πρόκειται για SAD adaptations, όχι exact ChipWhisperer
reproduction. Wrong-row control=np.roll(Gaussian offsets,1), exact ίδιο histogram,
χωρίς επιλογή roll από τα αποτελέσματα ή injected shifts. Diagnostic μόνο.
Προκαθορισμένο primary criterion: Gaussian≥18/20 σε κάθε pair, Gaussian−rolled≥0,10,
clean loss≤0,10. SAD contrasts περιγραφικά, χωρίς επιλογή καλύτερης μεθόδου από confirmation.

Η φάση4 πέρασε61 tests. Η Gaussian/SADmean/NCC primarySR είναι ίδια· δεν τεκμηριώνεται
Gaussian superiority. Το νέο confirmation είναι πλέον viewed evidence.
[Μετρήσεις και κόστος](../outputs/paper_alignment_controls_2026-10-05/REPORT_EL.md),
[primary SAD/Scatter audit](../literature/ALIGNMENT_BASELINES_2026-10-05.md).

```powershell
& .\.venv\Scripts\python.exe notebooks/verify_alignment_controls.py
& .\.venv\Scripts\python.exe notebooks/build_alignment_controls_report.py
# Inspect sad_and_correspondence.png before setting the visual-check flag:
& .\.venv\Scripts\python.exe notebooks/verify_alignment_controls_report.py --plot-visually-checked
& .\.venv\Scripts\python.exe notebooks/verify_study_synthesis.py
```

## Πέμπτη CPU φάση: νέα καμπάνια και actual unknown attack key

Frozen plan `outputs/paper_variable_campaign_2026-10-05/plan.json`, πριν από τιμές
training/validation/attack. Επίσημο original ASCAD variable-key1400, ξεχωριστό από
το fixed-key700. Shapes/dtypes και checksum μόνο πριν την παγίωση. Training10k/val5k,
splitseed2026, attack5k από100k με subsetseed20261009. Ίδιες επιλογές pair separation50,
diversity20, relative raw-noise factors0,1/0,2, ±10search/common tie/20orders/budget2000.
Το interior margin10 παγώθηκε πριν fit για ασφαλή εξαγωγή με±10, 885.115 candidates.

Νέο fit από raw training traces/provided identity labels μόνο. Mean/variance και
pairs γράφτηκαν πριν το evaluation-access record. Δεν διαβάστηκαν keys/masks για
fitting, δεν έγινε training alignment, post-validation refit ή optimizer training.
Πρόκειται για campaign-specific protocol replication, όχι zero-shot, νέο CNN,
αλλαγή original production protocol ή απόδειξη διαφορετικής φυσικής συσκευής.

Validation varying-key rows: descriptive correlations προς HW labels μόνο.
Attack5k: ελέγχθηκε πραγματικό σταθερό πλήρες key, διαφορετικό από το αρχικό και
απόν από το επιλεγμένο train10k. Traces μόνο για μέθοδο, plaintext μόνο για256 CPA
candidate hypotheses· αληθινό key byte μόνο για correctness και rank reporting.
Δεν χρησιμοποιήθηκε simulated key/key-adjusted plaintext.

Gaussian/NCC/SADmean/fixed/wrong-row/known-extra-injection υπολογίστηκαν σε ένα
προκαθορισμένο matrix. Τα original traces έχουν ήδη φυσική χρονική ασυγχρονία:
known injection δεν είναι πλήρες alignment oracle, matching injection δεν είναι
μέτρηση total timing accuracy. Train median range48→σraw4,8/9,6, έναντι13→1,3/2,6
της πρώτης καμπάνιας. Οι εντάσεις δεν είναι ίδιες σε απόλυτες μονάδες και δεν
απομονώνεται μόνο η αλλαγή κλειδιού/καμπάνιας.

Primary combined5: και τα δύο pairs Gaussian≥18/20, SR improvement από fixed≥0,10,
clean loss≤0,10. Απέτυχε:0/20,0/20. Νέα καμπάνια clean15/20,0/20 με Gaussian,
fixed10/20,0/20. Καμία αλλαγή pair/μεθόδου/noise μετά την εξέταση αποτελεσμάτων.
Το variable-key attack subset είναι πλέον viewed evidence, αποκλεισμένο από tuning.
Το original fixed-key attack παραμένει κλειστό στην επέκταση· original CNN gate failed.

[Πλήρη αποτελέσματα/κόστος](../outputs/paper_variable_campaign_2026-10-05/REPORT_EL.md),
[official-source audit](../literature/VARIABLE_CAMPAIGN_2026-10-05.md).
Η ανεξάρτητη επαλήθευση επαναδιαβάζει τα ίδια viewed evidence για correctness,
χωρίς tuning, νέα attack pools ή νέα trainings.65tests passed,3GPUtrainings,1notebook.

```powershell
& .\.venv\Scripts\python.exe notebooks/verify_variable_campaign.py
& .\.venv\Scripts\python.exe notebooks/build_variable_campaign_report.py
# Inspect campaign_replication.png before setting the visual-check flag:
& .\.venv\Scripts\python.exe notebooks/verify_variable_campaign_report.py --plot-visually-checked
& .\.venv\Scripts\python.exe notebooks/verify_study_synthesis.py
```
