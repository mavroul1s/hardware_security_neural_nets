# Σχέδιο project

Νεότερη απόφαση11/10: εγκρίθηκε μία baseline45k και cap5, ίδιο CNN/seed0/50epochs/
batch50/authorcycle, nestedtraining και originalvalidation5k/refittedtrain-onlyMinMax.
Το [συγκεκριμένο πρωτόκολλο](docs/PAPER_NEXT_PROTOCOL_2026-10-11.md) είναι εγκεκριμένο,
με104passingCPUtests πριν το freeze και105 μετά τη διόρθωση μεταφοράς bytes.
OAuth/account revision ολοκληρώθηκαν. Version1 απέτυχε πριν από training· η χωριστά
εγκεκριμένη version2 ολοκληρώθηκε και επαληθεύτηκε:20/20 clean validation recovery,
GE0, minimumCE5,539754/epoch21. Έλεγχοι45000LRvalues/40000ranks/5000CPU predictions.
Actual5trainings/cap5exhausted. Version3 QUICK_SAVE original source χωρίςrun.
No combined/attack authorization. Το αρχικό minimal study/failed gate διατηρούνται.
Η [αναφορά](outputs/kaggle_budget_2026-10-11/api/REPORT_EL.md) τεκμηριώνει το joint
sample/update/scaler diagnostic στο ήδη viewed validation. Για επόμενο training
χρειάζεται νέα συγκεκριμένη υπόθεση και συμφωνία χρήστη.
[Paper αποτίμηση](outputs/paper_readiness_2026-10-11/REPORT_EL.md) και
[working draft](docs/PAPER_DRAFT_2026-10-11.md): failure-analysis κατεύθυνση, όχι novelty claim.


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
Η αναπαραγωγή σε νέο CPU venv ολοκληρώθηκε στις5/10: 27 exact dependency wheels,
ξεχωριστό source snapshot, 44 tests passed/14warnings, ίδια best/last CNN CE/ranks,
ίδιες δύο raw correlation curves και32 sensitivity rows/138 arrays. Επαληθεύτηκαν
640 Pearson endpoints. Πραγματικό replay62,36s, suite597,51s· χωρίς νέαGPU ή
real-data optimizer updates. Ίδιο Windows host/base interpreter, όχι cross-device proof.
Αναφορά `outputs/cpu_reproduction_2026-10-05/REPORT_EL.md`, οδηγίες
`docs/CPU_REPRODUCTION.md`.

Νεότερη εντολή της 5/10: ο χρήστης ζήτησε πρόσθετα πειράματα προς paper και ένταξή
τους στην εργασία. Εκτελέστηκαν τρεις CPU φάσεις με πάγωμα κάθε πλάνου πριν τη
δική του εκτέλεση: trace-only shift estimation, coordinate-consistent normalization
comparison, training-label-only point selection. Χωριστές profiling confirmation
pools των5.000 με seeds20261005/6/7, χωρίς αύξηση training10k ή νέα GPU εκπαίδευση.
Η πρώτη ένδειξη raw Gaussian20/20 και στα δύο παλιά ζεύγη δεν επαναλήφθηκε
στο δεύτερο confirmation:11/20,20/20. Με νέα train-label-only σημεία και τρίτη pool:
20/20,18/20 έναντι fixed0/20,0/20 στο ±5/σraw1,3· OOD±10/σraw2,6 μόνο6/20,0/20.
Η αρχική surrogate σύγκριση είχε λάθος raw-domain centering· διατηρήθηκε και ελέγχθηκε
προοπτικά σε σωστό domain. Δεν εξηγεί το clean CNN failure ούτε αποδεικνύει novelty.
Αναφορά `outputs/paper_extension_2026-10-05/REPORT_EL.md`, ενσωμάτωση στη§12 της
τελικής αναφοράς,288 recovery summaries/5.760 independent CPA endpoints/57 tests.
Επόμενο: primary overlap/baseline comparison και ανεξάρτητη campaign/key αξιολόγηση
με νέο frozen protocol. Όλες οι confirmation pools τώρα έχουν εξεταστεί και δεν
επαναχρησιμοποιούνται ως αθέατες. Παραμένουν3 GPU trainings, cap4,1notebook, failed gate.

Συνέχεια της5/10: τέταρτη CPU φάση με frozen train-label-only pairs και νέο confirmation5k
seed20261008. Σύγκριση NCC/Gaussian με SAD training mean, SAD training-selected reference
και deterministic rolled-Gaussian offset control. Gaussian/NCC/SADmean20/20,20/20
στη combined5, rolled0/20,0/20, SADreference20/20,19/20. GaussianOOD2/20,3/20,
SADmean2/20,6/20· κανέναOOD sustainedSR90. Η γνωστή SAD ισοφαρίζει το κύριοendpoint,
δεν τεκμηριώνεται νέα Gaussian μέθοδος.61tests/112νέαsummaries/2.240νέαendpointchecks,
112 πρόσθετα independent replays. Αναφορά `outputs/paper_alignment_controls_2026-10-05/REPORT_EL.md`.
Η τέταρτη confirmation pool έχει πλέον εξεταστεί· συνολικά35k unique train/val/confirm rows.
Επόμενο παραμένει ανεξάρτητη campaign/key αξιολόγηση και κατάλληλη ισχυρή baseline
σύγκριση, όχι νέο Gaussian superiority claim από το ίδιο fixed-key benchmark.

Τρέχουσα συνέχεια της5/10: ολοκληρώθηκε πέμπτη CPU φάση στην επίσημη variable-key
καμπάνια1400samples, με νέα train10k/val5k και prospective final attack5k.
Point selection/moments πάγωσαν πριν από validation/attack. Το νέο πραγματικό key
και byte2 διαφέρουν από το αρχικό· το πλήρες key απουσιάζει από το training10k.
Combined5: όλες οι έξι μέθοδοι0/20 και στα δύο pairs. Clean Gaussian15/20,0/20,
fixed10/20,0/20. Δεν πέρασε το προκαθορισμένο criterion. Fit στην καινούρια καμπάνια,
όχι zero-shot/cross-device proof ή απομόνωση μόνο της αλλαγής κλειδιού.
Θόρυβοςσraw4,8/9,6 από train median range48, ίδιοι relative factors με τις παλιές φάσεις.
Αναφορά `outputs/paper_variable_campaign_2026-10-05/REPORT_EL.md`, ενσωμάτωση στη§14,
65tests/48νέαsummaries/960νέαexecutionchecks/48additionalreplays, χωρίς νέαGPU.
Το νέο attack subset εξετάστηκε και αποκλείεται από tuning. Original fixed-key attack locked.
Επόμενο ερευνητικό ερώτημα: σταθερότητα και false-selection έλεγχος της point επιλογής
μόνο σε νέα profiling rows, με νέο frozen plan· καμία επαναρρύθμιση πάνω στο evaluated attack.

Στις6/10 ολοκληρώθηκε το προοπτικό diagnostic signal-replication/permutation audit.
Ίδια original training10k/points,99 shuffled-label full-search matrices ανά καμπάνια,
νέο profiling confirmation5k ανά καμπάνια μετά την παγίωση/calibration. Excluded
35k/15k rows πριν,40k/20k συνολικές viewed/fit profiling rows μετά. Καμία νέα training
seed, model, budget ή optimizer· οι permutations είναι null diagnostic draws.
Τα δύο fixed-key και το πρώτο variable-key ζεύγος πέρασαν signed confirmation
με Bonferroni4×p. Variable pair2:trainr−0,037942/newconfirmationr−0,026326,
max-nulltail0,69/confirmationpAdjusted0,092,criterion failed. Δεν αποδεικνύει μηδενικό
signal ή ότι αυτή μόνο η αστάθεια εξηγεί την προηγούμενη αποτυχία του attack.
70tests passed/73,42s recorded CPU experiment, source/GPU study διατηρούνται.
Αναφορά `outputs/paper_selection_audit_2026-10-06/REPORT_EL.md`, §15 της εργασίας.
Η φάση είναι conditional statistical diagnosis, χωρίς νέα key-recovery αποτελέσματα.
Τα νέα confirmation rows είναι viewed, αποκλείονται από tuning. Καμία attack
ανάγνωση από αυτή τη φάση. Επόμενο: σύνθεση του publication scope και ορίων πριν
από πρόταση νέας μεθόδου· κάθε τέτοια πρόταση θέλει νέο training-only frozen plan
και αχρησιμοποίητη profiling επιβεβαίωση, χωρίς evaluated-attack adaptation.

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

## Πρόσθετο ερώτημα της επέκτασης προς paper

Με μόνο training traces/identity labels για επιλογή centered-product σημείων και
trace-only inference για shifts, πόση recovery διατηρούν απλές NCC/Gaussian εκτιμήσεις
υπό bounded raw shifts και noise; Πώς αλλάζει η εκτίμηση με feature-space surrogate
και σωστό coordinate domain; Η θέση του normalization και second-order alignment
έχουν γνωστά προηγούμενα. Η paired ποσοτικοποίηση/όρια αποτελούν υπό εξέταση
replication/robustness κατεύθυνση, χωρίς επιβεβαιωμένο νέο βιβλιογραφικό κενό.
Οι20 κοινές σειρές δεν αποτελούν ανεξάρτητα training seeds ή κλειδιά· same-campaign
confirmation δεν αντικαθιστά unknown-key/cross-device evidence.

Η phase5 προσθέτει πραγματική αξιολόγηση ενός νέου άγνωστου attack key, μετά από
campaign-specific training fit. Το primary criterion απέτυχε. Δεν υποστηρίζεται
γενική robustness πρόταση· οι διαφορές καμπάνιας/κλειδιού/noise units παραμένουν
συγχυτικοί παράγοντες. Οι είκοσι σειρές δεν πολλαπλασιάζουν τα ανεξάρτητα κλειδιά.

## Συνέχεια6/10: windows και analytic noise regression

Η νέα εντολή χρήστη για περισσότερα paper experiments εκτελέστηκε σε δύο πρόσθετες
CPU φάσεις, χωρίςαλλαγή neural/GPU scope ή training10k. Phase7: έξι featurevariants,
radius5/ίδιαfrozenpoints, ίδιοridge0,01, πέντεconditions/τρίαalignments·900corrrows
και540recoveries σε νέαprofiling5k pools καιfresh variableattack5k. Knownaveraging/
SVD/regression/noiseregpriorart. Primarycrosscampaigncriterionfailed:fixedcontrast
positive, variableintervalswide. Variableattacknoiseridge3/20/target18failed,
rank14/20. FixedOODbox/rank1/noiseridge20/20bothpairs/bothpools, knownbaselineeffect.

Phase8: ηprecisionαξιολόγηση απόprofilingμόνο δικαιολόγησε μεγαλύτεραunused20k
confirmationpools, χωρίςrefit/parameterchange. Pairedrows/indexclusters μεbootstrap
9.999draws/nominalalpha0,01/family4·Δr0,041891/0,051852 καιpositiveboundsπαντού.
Adaptivefollowup, χωρίςglobalalphaspendingguarantee· phase7failurepreserved και
κανένανέοkeyrecoveryclaim. Box/rank1παραμένουνισχυρότερααπόnoisecorrection.

Όλαενσωματώθηκανστηνενιαίαεργασία§16–17.82tests passed. Η συγκεκριμένη
πρόταση[paper](docs/PAPER_CANDIDATE.md) περιλαμβάνειsupportmatrix/outline καιεπόμενα
κενά:primary fulltextnoveltycomparison, training-side alignment hypothesis σεunused
variableprofiling καιindependently acquired/newactualkeyevidence μετάfreeze.
Η training-side alignment πρόταση εκτελέστηκε στηphase9 με νέοfrozenplan:
ίδια10k training, μία unlabeled Gaussian pass±10, point/box/rank1 fits και παλιά
ή training-reselectedpairs, δύοunusedprofiling20k pools/seed20261016/17.
Primary κρατά ίδιαoldpair1/evaluation offsets, αλλάζοντας μόνοfeaturefit:
Δr0,003601/0,006085, όλα τα row/clusterintervals περιλαμβάνουν0· criterionfailed.
Νέο δεύτερο selectedpair199×1013 έχει cleanrank1r0,076546/0,079067, secondary
profiling evidence· δεν αποδεικνύει attack recovery ή causal jitter explanation.
432νέεςcomparisons/86tests· κανένανέοattackread/GPUtraining/notebook.
Fixedprofiling50kviewed, variableprofiling110kviewed/90kunused, variableattack10kviewed.
Επόμενα απαιτούν ξεκάθαρη research hypothesis καιunused confirmations μετά νέοfreeze.
Prior-art full-text gaps καιindependentacquisition/key evidence παραμένουν ανοικτά.

## Συνέχεια6/10: selection sensitivity αντί περισσότερων neural trainings

Ηphase10 πάγωσε20 paired bootstrap draws των ίδιων original10k training, με
σταθερά phase9 alignment parameters. Επανυπολογίστηκαν όλα τα training-only
centers/full pair searches/point-box-rank1 fits πριν δύοunused20k confirmations.
All528coefficients retained, χωρίς καλύτερο draw ή consensus. Frozenpairs clean
rank1r≈0,09/0,08 μεpositive intervals: frozen-signalcriterionpassed.
Reselectedfamilyrank2medianr0,012320/0,003294,14/20 και15/20positive: sensitivity
καιjointcriteriafailed. Αυτό δεν αποδεικνύει ότι το originalpair είναι false positive.
20 draws conditional στο originalsample/alignment, όχι20 ανεξάρτηταexperiments.

Ενσωματώθηκε στη§19.90tests passed, δέκαφάσειςCPU2.596,295861s,
988recoveries/19.760executionchecks/10.960replays αμετάβλητα. Variableprofiling
150kviewed/50kunused, futureexclusions=unionphase10splits· attacksunchanged.
Το scheme-aware publishedPDF έγινεaccessible καισυγκρίθηκανrelevantsections,
με[νέοaudit](literature/SCHEME_AWARE_FULLTEXT_AUDIT_2026-10-06.md).
Orthogonalregression/fullcitationsearch καιindependentacquisition/key evidence
παραμένουν ανοικτά. Επόμενη selectorcomparison χρειάζεται training-only νέοfreeze,
όχι επιλογή bootstrapwinner από τα viewed results. One notebook/3GPUtrainings.

Στις8/10 συμπληρώθηκε [orthogonalregression comparison](literature/REGRESSION_PRIOR_ART_COMPARISON_2026-10-08.md)
μέσωindexedprimarytext, ενώdirectaccess παραμένειfailed. Πέντεdeterministic
syntheticalgebrachecks passed, χωρίςreal-datareads ήνέαμετρημένηefficacy (§20).
Απομένουν notation/authorimplementation resolution, matchedpriorartcomparison
καιindependentkey/acquisition evidence. Το πλήθοςcoefficients δεν αντικαθιστά
αυτάτακενά, καικαμίαviewedrow δεν διατίθεταιγιαtuning/νέαunseenconfirmation.

## Συνέχεια9/10: matched objective αντί νέου trial sweep

Πάγωσαν δύο διαψεύσιμες υποθέσεις και καταγράφηκε τρίτο ανοικτό ερώτημα στο
[primary/code audit](literature/SELECTION_OBJECTIVE_AUDIT_2026-10-09.md): objective
mismatch, internal OOB prediction και profiling-to-actual-recovery gap. Επιλέχθηκε
η πρώτη ως primary CPU σύγκριση, με δεύτερη ως diagnostic και τρίτη deferred
μέχρι independently acquired actual-key evidence. Window selection έχει prior art.

Η [phase11](outputs/paper_window_selection_2026-10-09/REPORT_EL.md) επαναχρησιμοποίησε
ακριβώς τα20phase10 draws/10k training/phase9preprocessing. Σύγκρινε point-Pearson
selection με centered11sample-mean-product Pearson, ίδια eligible centers/radius/
diversity και point/box/rank1 controls. Verified150k προηγούμενη union, νέοfreeze πριν
twofresh10k payloads· όλα fits/OOBcoefficients πριν νέοconfirmationread.
Primary second-family boxmedian0,007642/0,006647,12/20 και13/20positive,
medianpairedΔ−0,004170/−0,006408: failed. Firstfamilypositivecontrast δεν το αναιρεί.
H2strictjointfailed1/8numericalchecks, ενώthreshold0,05agreement8/8.

95tests passed· experiment74,974746s/verifier111,776592s, κανένα νέοattack/GPU.
Variableprofiling170kviewed/30kunused, exclusions=allphase11splitsunion· όλεςοι
φάσειςκαιτοlockedfixedattackδιατηρούνται. Το fullorthogonalXML access gap έκλεισε,
αλλάnotation/authorimplementation resolution καιmatchedbenchmark παραμένουν.
Pinned scheme-aware implementation επιθεωρήθηκεμερικώς χωρίςεκτέλεση.
Δεν επιλέγεταιwinner/consensus ήαυτόματοwidth/region/selectorfollowup. Το επόμενο
freeze πρέπει να διακρίνει άλλη εξήγηση καινα δικαιολογεί τατελευταία30k· paperaxis
replication/benchmark/failureanalysis, χωρίςnovelty ή γενικήrecoveryclaim.

## Νέα άδεια Kaggle 9/10: ένα training-recipe diagnostic — ολοκληρώθηκε

Το [παγωμένο πλάνο](outputs/kaggle_recipe_2026-10-09/plan.json) αιτιολόγησε μία
νέα baseline του ίδιου CNN, με ίδια original 10k/5k, seed 0 και 50 epochs.
Αλλάζει joint recipe: batch 50 και author linear cycle max 0,005, χωρίς momentum
cycling. Οι εκθέσεις traces είναι ίδιες· updates 3.950 → 10.000. Πρόκειται για
έλεγχο του recipe στο περιορισμένο sample, χωρίς equal-update ή πλήρες 45k replication.

Η [εκτέλεση version 9](outputs/kaggle_recipe_2026-10-09/REPORT_EL.md) έδωσε
clean validation SR0/20, GE96 και minimum CE5,560471 στην epoch1. Primary failed.
Το καλύτερο training loss δεν συνδυάστηκε με validation recovery. Το παλιό gate
και όλες οι CPU αποτυχίες διατηρούνται. Το κοινό validation ήταν ήδη viewed.
Δεν γίνεται νέο independent-key efficacy ή causal claim.

99 tests, 10.000 LR values, 40.000 rank prefixes και CPU/GPU predictions verified.
Experiment70,122321s μετά το setup· verifier8,430090s χωριστά. Δεν μετρήθηκε
ολόκληρη η GPU session χρέωση. Ένα notebook, συνολικά4 full trainings/cap4,
version10 QUICK_SAVE original πηγής χωρίς run. Source/checkpoints/Input διατηρούνται.
Combined/attacks δεν εκτελέστηκαν και οι variable unused30k παραμένουν αχρησιμοποίητες.
Νέα GPU εκπαίδευση πέρα από το cap απαιτεί νέα αιτιολόγηση και συμφωνία χρήστη.
