# Ερευνητική αποτίμηση και επόμενη εκτέλεση — 11/10/2026

Το project μελετά profiling side-channel analysis σε masked AES. Τα νευρωνικά
μοντέλα δέχονται μόνο traces και προβλέπουν256 identity classes για το byte2.
Η ανάκτηση αξιολογείται χωριστά μέσω συσσωρευμένων key scores. Στη συνέχεια
προστέθηκαν training-only στατιστικά χαρακτηριστικά δεύτερης τάξης, trace-only
alignment και προοπτικοί έλεγχοι σταθερότητας σε χωριστά profiling subsets.

## Αποτίμηση για paper

Υπάρχει υλικό για **benchmark/replication και failure analysis**, με προτεινόμενο
θέμα: «Second-order leakage, feature-selection stability and key recovery under
limited profiling budgets». Δεν υπάρχει ακόμη τεκμηριωμένη νέα μέθοδος ή έτοιμη
submission. Τα αρνητικά αποτελέσματα αποτελούν μέρος του ερευνητικού ερωτήματος.

| Ερώτημα | Αποθηκευμένη ένδειξη | Επιτρεπτή ερμηνεία |
|---|---|---|
| Αρκεί το μικρό CNN10k; | Τέσσερα recipes: clean SR0/20 | Αποτυχία των συγκεκριμένων setups· δεν μετρήθηκε augmentation effect |
| Υπάρχει αξιοποιήσιμη δεύτερης τάξης διαρροή; | Frozen fixed-key features και CPU recovery | Θετική ένδειξη στο συγκεκριμένο benchmark |
| Είναι Gaussian alignment/ noise ridge νέα καλύτερη μέθοδος; | SAD και box/rank1 ισοφαρίζουν ή υπερτερούν | Superiority/novelty claim δεν στηρίζεται |
| Ανακτά αξιόπιστα variable-key attack; | Το παγωμένο criterion απέτυχε | Δεν τεκμηριώνεται γενίκευση recovery |
| Σταθεροποιείται ο δεύτερος επιλεγμένος family rank; | Phase10/11 joint criteria απέτυχαν | Frozen-pair signal και selector stability διαφέρουν |
| Αρκεί το συγκεκριμένο45k setup; |20/20 clean validation recovery, GE0, epoch21 | Θετική διάγνωση στο κοινό viewed validation· joint samples/updates/scaler |

Η αναζήτηση11/10 επιβεβαίωσε διαθέσιμα author repositories για
[window/feature-selection baselines](https://github.com/AISyLab/feature_selection_dlsca)
και [bilinear CNN product combinations](https://github.com/loccs-cp/Bilinear-CNN-for-SCA).
Η επιθεώρηση των README δεν ισοδυναμεί με matched reproduction ή πλήρη paper review.
Ο [code-only έλεγχος](../../literature/BILINEAR_CODE_AUDIT_2026-10-11.md) επιβεβαίωσε
outer-product layer και διαφορές πρωτοκόλλου σε συγκεκριμένο author commit.
Το πλήρες paper παραμένει μη προσβάσιμο. Δεν έγινε matched B-CNN execution.
Ο [επίσημος ASCAD κώδικας](https://github.com/ANSSI-FR/ASCAD) διατηρεί την πηγή
και τη διάκριση καμπανιών. Targeted έλεγχος, όχι εξαντλητική βιβλιογραφική κάλυψη.

## Νέος CPU έλεγχος που εκτελέστηκε

Ο companion `notebooks/audit_paper_readiness.py` έλεγξε αποθηκευμένα τεκμήρια,
production source hash και τα έξι original literature-baseline artifacts.
Δεν άνοιξε trace/attack payloads, δεν έκανε training ή νέο selection.
Ανακατασκεύασε ακριβώς20orders των2000 από5000 με seed8001.
Ανεξάρτητα set intersections επαλήθευσαν και τα190 ζεύγη: overlap758–847,
mean800,942105. Η ένωση περιέχει5000 μοναδικά rows, όχι40000 ανεξάρτητες παρατηρήσεις.
Δεν εκτιμάται effective sample size ή outcome correlation από την επικάλυψη.

Η υποψήφια45k/5k διάσπαση επαληθεύτηκε: το αρχικό training10k περιέχεται,
το validation είναι ακριβώς ίδιο και δεν επικαλύπτεται. Το audit εκτελέστηκε σε2,006s
μετά imports. Δεν παράγει νέα φυσική efficacy evidence.

Ο αρχικός full suite πέρασε99tests/46,56s, με14 υφιστάμενα warnings και ένα
pytest-cache permission warning. Με την πρόσθετη GPU extension πέρασαν104tests/
17,14s/14warnings, με απενεργοποιημένη cache. Τα πέντε πρόσθετα tests ελέγχουν
LR interpolation45k, optimizer continuation, invalid states, πραγματικό synthetic
CPU smoke/checkpoint reuse και τη nested/disjoint διάσπαση. Synthetic correctness μόνο.

## Εγκεκριμένη GPU συνέχεια και πραγματική κατάσταση

Ο χρήστης ενέκρινε μία baseline45k/cap5. Το
[αναλυτικό πρωτόκολλο](../../docs/PAPER_NEXT_PROTOCOL_2026-10-11.md), το
[machine-readable plan](../kaggle_budget_2026-10-11/plan.json) και το πακέτο
εκτέλεσης προετοιμάστηκαν· source, embedded extension και όλες οι notebook cells
ελέγχθηκαν. Primary: minimum-CE cleanSR@2000≥18/20 στο ήδη viewed validation.
Joint sample/update/refitted-scaler diagnostic, όχι isolated-cause ή fresh confirmation.

Η OAuth πρόσβαση αποκαταστάθηκε στον **nmavros** και καταγράφηκε account revision
πριν από την υποβολή. Το αρχικό con1los ιστορικό διατηρήθηκε. Η version1 του private
continuation notebook απέτυχε πριν από training λόγω CRLF/LF στη μεταφορά κειμένου,
με μηδέν optimizer updates. Ο χρήστης ενέκρινε μία διορθωμένη version2, με ακριβώς
ίδια frozen bytes/μοντέλο/πρωτόκολλο. Τα105tests πέρασαν και οι δύο προσπάθειες
διατηρούνται. Δεν έγινε αυτόματη επανάληψη.

Η [πέμπτη GPU baseline](../kaggle_budget_2026-10-11/api/REPORT_EL.md) ολοκληρώθηκε
και επαληθεύτηκε: **20/20 clean recovery στα2.000traces, GE0**, minimum-CE
checkpoint epoch21/CE5,539754. Η recipe10k είχε0/20, GE96, epoch1/CE5,560471.
Δευτερεύον sustainedSR90 από504 μέχρι2000traces. Ίδιο viewed validation, ένας
seed/κλειδί και20 επικαλυπτόμενα orders. Δεν απομονώνεται ο unique-sample effect
από update count ή scaler fit και δεν τεκμηριώνεται independent attack efficacy.

Ο verifier έλεγξε45000LRvalues/40000rankprefixes/5000CPU predictions και train-only
fit. MaxCPU/GPUlogproberror7,495e−6. Όλα26 original artifacts διατηρούν hashes.
Training156,097364s/validation6,375075s, experiment180,865040s μετάsetup· όχι συνολική
GPU χρέωση. Actual5trainings/cap5exhausted. Version3 QUICK_SAVE original source χωρίςrun.
Original fixed attack locked, variableattack10k viewed και variableprofiling30k unused.
Καμία credential τιμή δεν περιλαμβάνεται στα project artifacts.

## Τι απομένει

Η GPU baseline45k απάντησε θετικά το παγωμένο diagnostic question και η CPU
επαλήθευση ολοκληρώθηκε. Δεν κλείνει novelty ή independent acquisition/key gaps.
Επόμενη ερευνητική απόφαση είναι frozen αξιολόγηση του ήδη επιλεγμένου checkpoint
σε αθέατο attack, χωρίς tuning, και ενδεχόμενη κοινή baseline/combined σύγκριση.
Απαιτείται νέο συγκεκριμένο πρωτόκολλο και συμφωνία· δεν έχει προεγκριθεί attack
access ή έκτη εκπαίδευση. Όλα τα προηγούμενα negative results διατηρούνται.
Οι τελευταίες30k profiling rows διατηρούνται μέχρι διαφορετική διακριτική υπόθεση.
Η εργασία για paper χρειάζεται εστιασμένο αγγλικό manuscript, άμεση σύγκριση prior art
και σαφή όρια αντί για περισσότερα αδιάκριτα trials.
