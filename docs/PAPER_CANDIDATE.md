# Υποψήφιος άξονας paper — ενημέρωση11/10/2026

Νεότερο αποτέλεσμα: η [baseline45k](../outputs/kaggle_budget_2026-10-11/api/REPORT_EL.md)
έδωσε20/20 clean validation recovery/GE0 έναντι0/20 τηςrecipe10k. Το κοινό
validation ήταν ήδη viewed και η επέκταση αλλάζει μαζί samples/updates/scalerfit.
Δεν απομονώνει αιτία ή ανεξάρτητη efficacy. Όλες οι προηγούμενες10k και CPU
αποτυχίες παραμένουν. Το [αγγλικό working draft](PAPER_DRAFT_2026-10-11.md)
εστιάζει πλέον στη διάκριση leakage, selection stability και budget-dependent
key recovery. Η ενιαία εργασία περιλαμβάνει το αποτέλεσμα στη§23.
Actual5GPUtrainings/cap5exhausted,105tests passed. Combined/attack δεν εκτελέστηκαν.
Οι παρακάτω CPU προτάσεις και διαδοχικές ενημερώσεις διατηρούνται ιστορικά.

**Prospective Robustness Evaluation of Quadratic Feature Extraction for Masked AES**

Πρόκειται για συγκεκριμένη ερευνητική πρόταση με εκτελεσμένα αποτελέσματα.
Η μελέτη δεν έχει ακόμη επιβεβαιωμένη πρωτοτυπία ή επαρκές independent-key/device
evidence για submission. Η τελική εργασία περιλαμβάνει ήδη όλα τα πειράματα.

## Υπό εξέταση συμβολή

Αξιολογούμε αν η ενσωμάτωση γειτονικών δειγμάτων και η analytic input-noise
regularization στα quadratic features βελτιώνουν robustness χωρίς νέες neural
εκπαιδεύσεις. Παρέχουμε frozen train-label-only επιλογή, disjoint prospective
confirmations, ομοιόμορφα baselines, πραγματικά failures και reproduction artifacts.
Ο πιθανός άξονας είναι η συγκριτική μέτρηση και τα failure boundaries· averaging,
regression, SVD και noise regularization έχουν γνωστό prior art.
Προστίθεται πλέον η διάκριση μεταξύ signal σε συγκεκριμένα frozen points και
σταθερότητας του πλήρους training-label-only selector υπό paired resampling.

Η exact bilinear covariance correction
`σ²(C_A⊗I+I⊗C_B)+σ⁴I` προσφέρει κλειστή λύση expected noisy squared loss,
conditional στα training traces. Είναι χρήσιμο μαθηματικό/implementation εργαλείο,
αλλά η στοιχειώδης παραγωγή δεν αρκεί για novelty claim. Αφορά ανεξάρτητο πρόσθετο
θόρυβο σε disjoint windows, χωρίς noise-dependent offset selection στην identity.

## Προσωρινή περίληψη με πραγματικά αποτελέσματα

Σε δύο δημόσιες καμπάνιες masked AES/ASCAD συγκρίναμε έξι quadratic feature
extractors, με original10k training ανά campaign και αποκλειστικά training-label
πληροφορία για τα βάρη. Όλα τα σημεία/παράμετροι πάγωσαν πριν τα holdouts.
Στο fixed-key campaign, υπό raw±10/σ2,6 και Gaussian alignment, box averaging,
rank1 και analytic noise ridge ανέκτησαν το AES byte σε20/20 κοινά trace orders
και στα δύο pairs, σε δύο νέα profiling5k pools. Point extraction είχε10/20,3/20
και7/20,3/20. Οι window baselines ισοφαρίζουν· δεν προκύπτει superiority του
analytic method. Στο variable-key campaign, δύο επόμενα untouched profiling20k
pools έδωσαν noise-minus-clean ridge Δr0,041891 και0,051852, με θετικά nominal
99,75% paired-row/index-cluster bootstrap intervals. Παρ' όλα αυτά, box/rank1
παρέμειναν καλύτερα στο endpoint και η πραγματική variable attack αξιολόγηση
έδωσε3/20 γιαnoise ridge,4/20 γιαrank1,0/20 γιαpoint/clean ridge στοcombined5/pair1,
με budget2.000. Τοcriterion18/20 απέτυχε. Τα results δείχνουν conditional signal
robustness και όρια αξιοποίησης· δεν τεκμηριώνουν αξιόπιστη γενική key recovery,
νέα επίθεση ή cross-device transfer. Τοphase7globalprimaryfailure διατηρείται.

Μία ακόμη prospective φάση, με τα ίδια10k training και δύο νέα20k profiling pools,
έλεγξε single-pass alignment πριν το feature fit. Στο παλιό πρώτο pair/rank1/clean,
με κοινά evaluation offsets, έδωσε Δr0,003601/0,006085 με intervals που περιλαμβάνουν
το μηδέν· το προκαθορισμένο criterion απέτυχε. Η training-only επανεπιλογή σημείων
έδωσε δεύτερο pair με clean r0,076546/0,079067, δευτερεύον profiling αποτέλεσμα.
Δεν προστέθηκαν attack αποτελέσματα ούτε υποστηρίζεται causal εξήγηση μέσω jitter.

Σε επόμενο frozen follow-up,20 paired bootstrap draws από το ίδιο training10k
ξαναέκαναν επιλογή/fit, με σταθερές alignment παραμέτρους. Δύο νέα20k profiling
pools διατήρησαν τα originalalignedselectedrank1signals: pair1r0,092582/0,094329,
pair2r0,081028/0,078217, μεpositive nominal99,875%row/index-cluster intervals.
Όμως το reselected δεύτερο familyrank είχεmedianr0,012320/0,003294 και14/20,
15/20positive draws. Τοjointcriterion απέτυχε. Conditionalperturbations μεshared
training/confirmations, όχι20independentreplications. Δεν επιλέχθηκε καλύτεροdraw.
Το συγκεκριμένο originalpair δεν αποδεικνύεται false positive· η διαδικασία
επανεπιλογής δεν δίνει σταθερά αντίστοιχο δεύτερο signal σε αυτές τις perturbations.

## Σκελετός manuscript

1. Ερώτημα: ποια πολυπλοκότητα preprocessing/feature extraction δικαιολογείται,
   και πότε profiling signal improvement μεταφράζεται σε ανάκτηση byte;
2. Prior art: ASCAD/SAD/second-order windows/denoising/regression/noise penalties.
3. Μέθοδοι: point,box,diagonal,rank1,standardized ridge και exact noisy loss.
4. Προοπτικό protocol: ίδιοtraining10k,labels-only fit, αρχικό attack locked,
   disjoint pools, κοινές corruptions/orders, conservative rank ties, explicit units.
5. Θετικό fixed-key secondary OOD αποτέλεσμα και ισοδυναμία γνωστών baselines.
6. Variable-key negative recovery, μεγαλύτερη signal replication και controls.
   Training-side alignment failure και frozen-signal/reselection-stability διάκριση.
7. Όρια: one acquisition/campaign/key per attack, correlated orders, known artificial
   noise σ, unequal raw amplitudes μεταξύ campaigns, adaptive follow-up χωρίς global
   alpha-spending guarantee, approximate bootstrap assumptions.
8. Reproducibility/costs και τι απαιτείται για independently acquired confirmation.

## Πίνακας claims για review

| Claim | Κατάσταση |
|---|---|
| Fixed-key OOD window robustness επαναλαμβάνεται σε δύο untouched pools | Supported secondary result, γνωστά baselines |
| Analytic correction βελτιώνει clean ridge στο predefined signal endpoint | Supported conditional profiling contrasts, με stated bootstrap assumptions |
| Noise ridge καλύτερη από box/rank1 | Unsupported: controls καλύτερα/ίσα |
| Reliable variable-key recovery στο2k budget | Unsupported: criterion failed |
| Training-side single-pass alignment βελτιώνει oldpair1 cleanrank1 κατά≥0,01 | Unsupported: prospective criterionfailed, intervalsinclude0 |
| Νέοtraining-selectedpair199×1013 δίνει θετικήcleancorrelation σε δύοunused20k pools | Supported secondaryprofiling result, χωρίςνέοattackclaim |
| Τα συγκεκριμένα phase9alignedselectedrank1pairs διατηρούν clean signal σε δύο ακόμηunused20k pools | Supported frozen-signal criterion στηphase10, conditional bootstrap assumptions |
| Full-searchreselection δίνει σταθερά δύο usefulfamilyranks στο αρχικό10k | Unsupported: δεύτεροfamilymedian0,012320/0,003294, jointcriterionfailed |
| Αποτυχίαreselection αποδεικνύει falsepositive originalpair ήcausaloverfitting | Unsupported |
| Window-objective selection αρκεί για σταθερό δεύτερο box family | Unsupported: phase11 primary failed, median0,007642/0,006647 |
| Αλλαγή selection objective βελτιώνει πρώτο box family σε αυτό το conditional diagnostic | Supported descriptive matched contrast, median pairedΔ0,032106/0,015716· όχι recovery claim |
| OOB προβλέπει ακριβώς fresh medians εντός0,02 για όλες τις frozen configurations | Unsupported joint criterion:7/8passed· threshold0,05 agreement8/8 |
| Exact polynomial noise covariance identity | Algebra και synthetic correctness verified; novelty unverified |
| Νέα masking attack/cross-device/key-general robustness | Unsupported |
| Περισσότερα trials σημαίνουν περισσότερα ανεξάρτητα keys | Unsupported: orders overlapping, νέο attack subset ίδιο ήδη εξετασμένοkey |

## Επόμενες ερευνητικές ανάγκες

Το relevant-section scheme-aware publishedfulltext συγκρίθηκε με επιτυχή νέα
πρόσβαση μέσωuniversityrepository· [audit](../literature/SCHEME_AWARE_FULLTEXT_AUDIT_2026-10-06.md).
Στις9/10 επιθεωρήθηκε μερικώς το pinned author code (models/recombination και
simulation/entrypoints), χωρίς execution ή matched benchmark. Βλ.
[νέο source/notation audit](../literature/SELECTION_OBJECTIVE_AUDIT_2026-10-09.md).
Στις8/10 διαβάστηκαν καιrelevantorthogonalregressionequations μέσωindexedprimary
pages, με[ξεχωριστό algebra/access audit](../literature/REGRESSION_PRIOR_ART_COMPARISON_2026-10-08.md).
Τα ιστορικά directaccessfailures διατηρούνται· στις9/10 ανακτήθηκε full-textXML
και ελέγχθηκαν MathML15–18/Algorithm1. Το XML access gap έκλεισε, ενώ component
retention/penalty dimensions και author implementation παραμένουν unresolved.
Κανέναmatchedbenchmark. Απομένουν implementation/notation resolution, ισοδύναμοι polynomialnoisepenalties και
ευρύτερο citationsearch. Κενά πρόσβασης είναι recorded unknown,
όχι evidence απουσίας prior art. Αν η ιδέα είναι ισοδύναμη με γνωστή μέθοδο,
ο άξονας πρέπει να διατυπωθεί ως replication/benchmark/failure-analysis study.

Η **training-side trace-only alignment** εκτελέστηκε με νέο frozen plan στηphase9,
ίδιοoriginaltraining10k και δύοunused20kprofilingpools. Με ίδια oldpair1/evaluation
offsets το primaryrank1cleanΔr ήταν0,003601/0,006085, μεallintervalsinclude0 και
criterionfailed. Δεν τεκμηριώνεται πρακτικό όφελος≥0,01 από αυτόν τον bounded
single-pass fit ούτε ότι τοnativejitter εξηγεί την προηγούμενη attack αποτυχία.
Trainingreselectionμετάalignment έδωσε δεύτεροpair199×1013 μεcleanrank1
r0,076546/0,079067. Secondary, διαφορετικάpoints/fit, χωρίςνέοkeyrecoveryclaim.
Κανέναviewedattack χρησιμοποιήθηκεγια επιλογή μεθόδου ή παραμέτρων.

Ηphase10 ολοκλήρωσε selection-sensitivity audit, με όλα20fits retained και χωρίς
winner/ensemble/consensus. Τα viewed coefficients δεν μπορούν να χρησιμοποιηθούν
για επιλογή νέων points ή για «βελτίωση» του selector. Μια σύγκριση training-only
εναλλακτικών χρειάζεται νέο prospective freeze και unused profiling confirmations.
Η ονομαστική CIcoverage είναι conditional/approximate, όχι overalladaptivealpha
guarantee ή formal stabilityselectionerrorcontrol. Η περιορισμένη φυσική
replication παραμένει ουσιώδες κενό γιαpaper, ακόμηκαιμε περισσότερουςcoefficients.

Χρειάζεται και independently acquired/new actual-key benchmark μετά από πλήρες
freeze για ισχυρό efficacy claim. Τα εναπομείναντα variable attack rows έχουν
το ίδιο campaign/key context και δεν δημιουργούν από μόνα τους νέα key/device
replication. Δεν ξεκινά νέαGPU εκπαίδευση ή νέο Kaggle notebook από την πρόταση.

Το fixed profiling50k έχει πλέον χρησιμοποιηθεί. Variableprofiling170k used/30k
unused μετάphase11, variableattack10k viewed, originalfixedattacklocked. Κάθε νέα φάση πρέπει
να ενσωματώνει όλους τους προηγούμενους exclusions και να αναφέρει adaptive design.

Η [phase11](../outputs/paper_window_selection_2026-10-09/REPORT_EL.md) εκτέλεσε
matched point-objective versus box-objective selection στα ακριβώς ίδια20 draws,
χωρίς αλλαγή alignment/radius/eligible centers ή επιλογή bootstrapwinner. Δύο
fresh10k confirmations απέκλεισαν ολόκληρη την verified phase10 union150k.
Primary second-family boxmedian0,007642/0,006647,12/20 και13/20positive· pairedΔ
−0,004170/−0,006408: criterionfailed. First family βελτιώθηκε, αλλά δεν αρκεί
για joint success. Rank1control second medians επίσης παραμένουν χαμηλές.
Άρα αυτή η objective-matching παρέμβαση δεν αποκαθιστά σταθερό δεύτερο signal,
χωρίς απόδειξη μοναδικής causal εξήγησης ή falsepositive originalpair.
OOBsecondary jointfailed, με7/8numericalchecks passed, thresholdagreement8/8· conditional
internal diagnostic με fixed original-trace preprocessing, όχι formal calibration.
95tests passed· νέοrecovery/GPU0. Futureexclusions=allphase11splitsunion.

Δύο testable υποθέσεις και ένα recovery ερώτημα καταγράφονται στο νέο audit: H1 objective mismatch
έγινε primary καιαπέτυχε, H2 OOBprediction secondary καιjointfailed, H3 reliable
actual-key recovery μετά verified signal παραμένει ανοικτό, deferred και χωρίς
operationalized experiment εδώ. Η επόμενη μελέτη πρέπει
να δικαιολογήσει νέα εξήγηση και τα τελευταία30k rows· δεν προτείνεται αυτόματο
width/region/selector sweep. Ο paper άξονας ενισχύεται ως prospective benchmark
και failure analysis, χωρίς τεκμηριωμένη νέα τεχνική ή submission readiness.

## Πρόσθετο Kaggle training-recipe diagnostic — 9/10

Η [τέταρτη GPU baseline](../outputs/kaggle_recipe_2026-10-09/REPORT_EL.md) κρατά
το ίδιο CNN/10k/5k/seed0/50epochs και αλλάζει batch/schedule βάσει author code.
Παρά10000updates αντί3950, clean validation SR@2000 παραμένει0/20 και το primary
criterion απέτυχε. Το minimum-CE checkpoint είναι epoch1. Η αλλαγή joint recipe
δεν αρκεί σε αυτό το sample· δεν απομονώνει μοναδική αιτία ή το effect των45k
unique training traces του πλήρους author protocol. Το validation είναι ήδη viewed.
Δεν εκτελέστηκε combined ή attack.99tests/χωριστός verifier, source/checkpoints
preserved· έναnotebook/4trainings/cap4, safeQUICK_SAVEversion10 χωρίςrun.
Δεν αλλάζει η αποτίμηση novelty/independent efficacy ούτε καταναλώνονται unused30k.

[Ενιαία εργασία](../outputs/study_synthesis_2026-10-05/REPORT_EL.md) ·
[Phase7](../outputs/paper_window_regression_2026-10-06/REPORT_EL.md) ·
[Phase8](../outputs/paper_precision_replication_2026-10-06/REPORT_EL.md) ·
[Phase9](../outputs/paper_training_alignment_2026-10-06/REPORT_EL.md) ·
[Phase10](../outputs/paper_selection_stability_2026-10-06/REPORT_EL.md) ·
[Selection stability frozen audit](../literature/SELECTION_STABILITY_2026-10-06.md) ·
[Training alignment primary audit](../literature/TRAINING_ALIGNMENT_2026-10-06.md) ·
[Frozen primary audit](../literature/WINDOW_REGRESSION_2026-10-06.md) ·
[Πρόσθετα prior-art/access gaps](../literature/WINDOW_REGRESSION_PRIOR_ART_FOLLOWUP_2026-10-06.md)
