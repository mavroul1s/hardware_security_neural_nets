# Νευρωνικά δίκτυα και διαρροή masked AES: διαγνωστική μελέτη περιορισμένου κόστους

Προσωρινή ελληνική ερευνητική αναφορά για το μάθημα Hardware Security.
Κατάσταση: **2026-10-06**. Πρόκειται για σύνθεση των εκτελεσμένων πειραμάτων,
όχι για ολοκληρωμένη μελέτη augmentation ή επιβεβαιωμένη συνεισφορά paper.

Ενημέρωση της5/10: η [αναπαραγωγή σε καθαρό CPU περιβάλλον](../cpu_reproduction_2026-10-05/REPORT_EL.md)
ολοκληρώθηκε μετά την αρχική σύνθεση, χωρίς νέα GPU εκπαίδευση. Βλ. §11 για το scope.
Με νεότερη εντολή χρήστη εκτελέστηκαν [τρεις πρόσθετες CPU ερευνητικές φάσεις](../paper_extension_2026-10-05/REPORT_EL.md)
και ενσωματώθηκαν στη §12. Η έρευνα προς πιθανό paper συνεχίζεται χωρίς επιβεβαιωμένη πρωτοτυπία.
Στη συνέχεια ολοκληρώθηκε [τέταρτη CPU φάση με SAD και correspondence control](../paper_alignment_controls_2026-10-05/REPORT_EL.md),
ενσωματωμένη στη §13. Η γνωστή SAD ισοφαρίζει το κύριο Gaussian SR endpoint.
Η [πέμπτη CPU φάση σε νέο ASCAD campaign/attack key](../paper_variable_campaign_2026-10-05/REPORT_EL.md)
ενσωματώθηκε στη§14: η combined5 επιτυχία δεν επαναλήφθηκε και το criterion απέτυχε.
Στις6/10 προστέθηκε [έκτη CPU φάση selected-signal replication/permutation audit](../paper_selection_audit_2026-10-06/REPORT_EL.md),
στη§15. Τρία από τέσσερα παγωμένα pairs επανέλαβαν signed συσχέτιση σε φρέσκο profiling.

## Περίληψη

Μελετήσαμε την ανάκτηση ενός AES key byte από δημόσιες πραγματικές μετρήσεις του
ASCAD fixed-key, με 10.000 training traces, 5.000 validation traces, ένα seed και
περιορισμό στις GPU εκπαιδεύσεις. Τρία CNN baselines ολοκλήρωσαν 50 epochs αλλά
δεν ανέκτησαν το byte σε καμία από τις 20 clean validation επαναλήψεις με budget
2.000 traces. Το προαποφασισμένο κριτήριο επιτυχίας απέτυχε, οπότε η εκπαίδευση
combined augmentation δεν εκτελέστηκε.

Οι CPU διαγνώσεις δείχνουν ότι η αποτυχία του τελευταίου CNN συνυπάρχει με αξιοποιήσιμη
δεύτερης τάξης διαρροή: correlation scoring σε δύο training-selected centered
products έδωσε 20/20 clean validation ανακτήσεις. Οι σταθερές θέσεις είναι ευαίσθητες
σε τεχνητές μετατοπίσεις. Με σ=0,1 και shifts±5 οι επιτυχίες πέφτουν σε 1/20 και 11/20·
γνωστή oracle διόρθωση επαναφέρει 20/20. Αυτό είναι διαγνωστικό control, όχι πρακτική
ευθυγράμμιση. Οι μέθοδοι έχουν διαφορετική profiling information και δεν αποτελούν
δίκαιη σύγκριση υπεροχής CNN/correlation. Δεν χρησιμοποιήθηκε το αρχικό fixed-key attack set.

Η επέκταση εξέτασε πρακτική trace-only εκτίμηση μετατόπισης, normalization coordinates
και επιλογή σημείων μόνο με training labels. Στο τρίτο χωριστό profiling confirmation,
raw shifts±5/σ=1,3: Gaussian alignment20/20 και18/20 ανακτήσεις έναντι fixed0/20 και0/20.
Στο δυσκολότερο±10/σ=2,6:6/20 και0/20. Οι νέες raw-unit αλλοιώσεις διαφέρουν από
την παλιά feature-space sensitivity. Το αποτέλεσμα δεν τεκμηριώνει νέα τεχνική ή
cross-device/unknown-key γενίκευση.

Στη νέα variable-key καμπάνια, με νέο fit10k και διαφορετικό πραγματικό attack key,
Gaussian clean15/20 και0/20, combined5 0/20 και0/20. Το ίδιο primary criterion απέτυχε.
Μεταβάλλονται καμπάνια, φυσική χρονική μεταβλητότητα, window και απόλυτα noise units·
δεν απομονώνεται μόνο το key effect. Δεν τεκμηριώνεται γενική robustness υπεροχή.

Το νέο profiling-only audit της6/10 διατηρεί τα τέσσερα επιλεγμένα pairs και
επιβεβαιώνει signed συσχέτιση σε τρία. Το δεύτερο variable-key pair δεν πέρασε
το corrected criterion, παρότι είχε ασθενή συσχέτιση ίδιου προσήμου στη νέα pool.
Το πρώτο variable-key pair επανέλαβε profiling signal και είχε αποτύχει στην παλιά
combined επίθεση· δεν εξηγείται όλη η αποτυχία μόνο από μη διατήρηση των σημείων.

## 1. Στόχος και βασικές έννοιες

Ένα trace είναι η ακολουθία μετρήσεων φυσικής διαρροής κατά την εκτέλεση AES σε hardware.
Το νευρωνικό δίκτυο λαμβάνει μόνο αυτή την ακολουθία και προβλέπει 256 πιθανότητες
για την τιμή ενός ενδιάμεσου byte. Το γνωστό plaintext επιτρέπει να μετατρέψουμε
αυτές τις πιθανότητες σε scores για 256 υποψήφια key bytes. Η συσσώρευση πληροφορίας
από πολλά traces αποσκοπεί στο να φέρει πρώτο το σωστό byte. Δεν επιχειρούμε
ανάκτηση ολόκληρου του AES key.

Το masking χωρίζει την ευαίσθητη τιμή σε τυχαία καλυμμένες ποσότητες. Η σύνδεση
με το μη καλυμμένο byte μπορεί να απαιτεί συνδυασμό διαφορετικών χρονικών σημείων.
Ο έλεγχος δεύτερης τάξης εδώ χρησιμοποιεί προϊόν δύο κεντραρισμένων μετρήσεων.
Τέτοιες στατιστικές επιθέσεις έχουν ήδη μελετηθεί· δεν εισάγουμε νέα τεχνική.
[Prouff–Rivain–Bévan, revised primary record](https://eprint.iacr.org/2010/646).

Το αρχικό ερευνητικό ερώτημα ήταν: με λίγα μοναδικά training traces και κοινό αριθμό
updates, βοηθά ο συνδυασμός Gaussian noise και χρονικών μετατοπίσεων σε αλλοιώσεις
διαφορετικών εντάσεων; Αυτό παραμένει **αναπάντητο**, επειδή δεν υπάρχει trained
combined comparator. Το ερώτημα που εξετάζει αυτή η αναφορά είναι πιο στενό:
τι αποκαλύπτουν τα παγωμένα διαγνωστικά για τα αποτυχημένα CNN baselines και για
την ευαισθησία της υπάρχουσας διαρροής στις συγκεκριμένες αλλοιώσεις;

## 2. Δεδομένα, attacker και διαχωρισμός

Χρησιμοποιήσαμε το επίσημο προεπεξεργασμένο ASCAD fixed-key,700 samples ανά trace,
zero-based byte2, με identity labels `Sbox(plaintext[2] XOR key[2])`.
Η προέλευση και το schema ελέγχονται από το [επίσημο repository](https://github.com/ANSSI-FR/ASCAD).
Το τοπικό HDF5 έχει 50.000 profiling και 10.000 attack traces. Για το κύριο scope
επιλέξαμε 10.000 training και 5.000 validation rows από το profiling, splitseed 2026.
Τα αποθηκευμένα indices είναι διακριτά και κοινά στα τρία baselines. Οι υπόλοιπες
profiling rows δεν αυξάνουν το εγκεκριμένο training budget.

Ο profiling attacker υποτίθεται ότι έχει γνωστές τιμές στην ελεγχόμενη profiling
συσκευή. Το CNN δεν λαμβάνει key, plaintext ή mask metadata ως inputs. Στο scoring
το plaintext χρησιμοποιείται για τις candidate hypotheses, το σωστό validation
key μόνο για το πραγματικό rank. Η παλιότερη επιλογή των correlation points
χρησιμοποίησε επιπλέον training mask/share metadata· αυτή η προνομιακή πληροφορία
καταγράφεται και δεν αποδίδεται στο CNN.

Το fixed-key campaign δεν αποδεικνύει μεταφορά σε νέο άγνωστο key ή άλλη συσκευή.
Το 700-point window είναι ήδη προεπιλεγμένο από τους δημιουργούς του dataset.
Όλα τα κύρια αποτελέσματα αυτής της αναφοράς προέρχονται από **profiling validation**,
το οποίο έχει επανειλημμένα χρησιμοποιηθεί για διάγνωση. Δεν είναι ανεξάρτητο τελικό test.
Το final attack παραμένει κλειστό· δεν εμφανίζουμε validation scores ως attack results.

Dataset SHA-256: `f56625977fb6db8075ab620b1f3ef49a2a349ae75511097505855376e9684f91`.
Split ID: `1c9656f9ba13791a7ba4781a5518420f4fef4e303c979d4c307cc6ed27ee9090`.

## 3. CNN πρωτόκολλο και πραγματική εκτέλεση

Κάθε baseline χρησιμοποίησε seed 0,50 epochs, batch 128, Adam LR 0,001 και 10k/5k split:
79 updates ανά epoch,3.950 συνολικά. Το checkpoint επιλέχθηκε από την ελάχιστη
**clean validation cross-entropy**, πριν από τον έλεγχο ανάκτησης. Δεν επιλέγουμε
epoch από final attack ή αλλάζουμε τον κανόνα για να περάσει το gate.

| Baseline | Parameters | Κανονικοποίηση | Best epoch | Minimum validation CE | Clean GE@2000 | Clean SR@2000 |
|---|---:|---|---:|---:|---:|---:|
| ReLU |197.424|Training-only global scalar|2|5,547229|103,50|0/20|
| LeakyReLU0,1 |197.424|Training-only global scalar|1|5,547114|89,25|0/20|
| Literature-inspired CNN |16.952|Training-only feature MinMax|4|5,560782|114,25|0/20|

Το τελευταίο CNN έχει Conv1d1→4/kernel 1, SELU/BatchNorm, AvgPool2 και dense 10→10→256
logits. Τα ReLU/Leaky αποτελέσματα διατηρούνται ως αρνητικά αποτελέσματα. Η αλλαγή
normalization/architecture στην τρίτη έκδοση σημαίνει ότι η σύγκριση και των τριών
δεν απομονώνει την επίδραση ενός παράγοντα. Η μικρότερη CE ή GE ανάμεσα σε failures
δεν αρκεί για να ονομάσουμε ένα επιτυχές ή σταθερά ανώτερο μοντέλο.

Το gate για combined ήταν cleanSR≥0,90, δηλαδή 18/20, στο original minimum-CE
checkpoint. Παρατηρήθηκε 0/20. Το combined παραλείφθηκε, χωρίς single noise/shift
trainings ή αυτόματο search. Άρα δεν μετρήθηκαν augmentation effect, combined
overhead ή factorial interaction.

![Καμπύλες των τριών αποθηκευμένων trainings](baseline_histories.png)

Οι καμπύλες training CE υπολογίστηκαν online μέσα στον training loop, ενώ validation
CE σε eval mode. Δεν είναι frozen-forward μέτρηση του ίδιου checkpoint στο training
set. Η ξεχωριστή CPU διάγνωση παρακάτω χρησιμοποιεί frozen-forward CE.
Η πτώση training CE και άνοδος validation CE είναι συμβατή με ανεπαρκή γενίκευση
του setup, αλλά δεν εντοπίζει από μόνη της μία μοναδική αιτία.

## 4. Ποια διαγνωστικά εκτελέστηκαν

Τα best/last checkpoints του literature CNN αξιολογήθηκαν σε CPU χωρίς νέα weight
updates. Η ελεγμένη, παγωμένη CE στο training ήταν 5,516667 για best και 5,240488
για last· στο validation5,560782 και 5,814250. Έλεγχοι label shuffles έδειξαν
training alignment χωρίς αντίστοιχο held-out alignment. Οι 10 dense μονάδες έχουν
μεταβλητά outputs, επομένως το τελευταίο failure δεν εξηγείται απλώς από πλήρη
σταθεροποίηση των outputs. Διατηρείται mask/share signal στη hidden representation,
ενώ η ένδειξη για τον unmasked στόχο παραμένει χαμηλή.

Ελέγχθηκε BatchNorm με training-only exact moments σε frozen-weight clones.
Δεν άλλαξαν τα αρχικά checkpoints. Η validation CE έγινε 5,569355(best) και
5,814538(last), με SR0/20 και στα δύο. Αυτό αποκλείει ως επαρκή λύση τον συγκεκριμένο
BN recalibration έλεγχο· δεν αποκλείει κάθε πιθανή αλλαγή training recipe.

Στη δεύτερης τάξης διάγνωση επαναχρησιμοποιήθηκαν τα υπάρχοντα training-selected
ζεύγη 181×521 και 156×517, χωρίς validation point search. Τα προϊόντα συσχετίζονται
με `HW(Sbox(plaintext_byte XOR candidate_key))` για κάθε υποψήφιο byte.
Η απόλυτη Pearson correlation δίνει τη βαθμολογία. Τα true-key ranks, GE, SR και
sustainedSR90 προκύπτουν από 20 κοινές σειρές των validation traces.

| Παγωμένο ζεύγος | Clean GE@2000 | Clean SR@2000 | Πρώτο sustainedSR90 prefix |
|---|---:|---:|---:|
|181×521 (rout)|0|20/20|631traces|
|156×517 (r3)|0|20/20|481traces|

Ο συνδυασμός διαρροών είναι αξιοποιήσιμος στο συγκεκριμένο validation. Δεν
συμπεραίνουμε ότι κάθε CNN αδυνατεί να τον μάθει, ότι correlation είναι καθολικά
ανώτερη ή ότι η επιτυχία θα μεταφερθεί σε νέο device/key. Τα δύο ζεύγη δεν
συνδυάστηκαν σε νέο classifier και δεν επιλέχθηκε validation winner.

## 5. Θόρυβος, shifts και oracle control

Οι οκτώ εντάσεις είχαν οριστεί στο υπάρχον evaluation grid. Χρησιμοποιήθηκαν
train-only feature MinMax, παγωμένα normalized training centers, seed 9001, batch 256,
shift→noise και 20 common orders/seed 8001. Αυτό είναι **evaluation αλλοιώσεων**,
όχι single-strategy training. Κάθε κελί παρακάτω αναφέρει επιτυχίες/20 στο budget 2000.

| Συνθήκη (σ; shift range) |Fixed181×521|Fixed156×517|Oracle181×521|Oracle156×517|
|---|---:|---:|---:|---:|
|Clean (0;0)|20/20|20/20|20/20|20/20|
|Noise matched (0,1;0)|20/20|20/20|20/20|20/20|
|Shift matched (0;±5)|6/20|17/20|20/20|20/20|
|Combined matched (0,1;±5)|1/20|11/20|20/20|20/20|
|Combined mild (0,05;±2)|20/20|20/20|20/20|20/20|
|Combined noise OOD (0,2;±5)|0/20|4/20|4/20|14/20|
|Combined shift OOD (0,1;±10)|0/20|2/20|20/20|20/20|
|Combined both OOD (0,2;±10)|0/20|1/20|9/20|10/20|

Το oracle διαβάζει τις θέσειςpoint+δ με τη **γνωστή injected μετατόπιση** του trace.
Δεν εκτιμά τη δ από μετρήσεις. Η επαναφορά σε 20/20 για σ=0,1 είναι διαγνωστική
ένδειξη ότι η θέση των features περιορίζει τη σταθερή εξαγωγή. Δεν αποτελεί learned
shift invariance ή έτοιμη πρακτική επίθεση. Στο σ=0,2 ούτε η oracle εξαγωγή φτάνει
18/20. Δεν βελτιστοποιήθηκαν οι εντάσεις ή τα ζεύγη από τις τωρινές επιδόσεις.

![Προκαθορισμένες εντάσεις, σταθερά σημεία και γνωστή μετατόπιση](../correlation_robustness_2026-10-05/success_grid.png)

Τα selected products είναι ακριβώς ίδια με zero και edge padding, καθώς τα σημεία
είναι εσωτερικά και κανένα δεν αποκόπηκε μέχρι±10. Αυτό δεν αποκλείει border cues
σε CNN που διαβάζει 700 points. Οι μετατοπίσεις/θόρυβος εφαρμόστηκαν **μετά** το
per-position MinMax και δεν ισοδυναμούν με physical raw jitter/noise πριν από αυτό.

Οι μέθοδοι μέσα σε κάθε συνθήκη έχουν ίδια corrupted traces. Οι σειρές traces
είναι κοινές σε όλες τις συνθήκες, αλλά το interleaved RNG δεν εγγυάται κοινά
offsets μεταξύ διαφορετικών συνθηκών. Για παράδειγμα, η διαφορά shift-only/combined
δεν απομονώνει αποκλειστικά τον θόρυβο. Δεν συμπεραίνουμε μονοτονική dose-response
από τις OOD διαφορές μίας corruption realization.

## 6. Μετρικές και αβεβαιότητα

Rank0 σημαίνει πρώτο υποψήφιο. GE είναι ο μέσος rank και SR το ποσοστό σειρών που
καταλήγουν στοrank0. Το CNN συσσωρεύει log probabilities. Η correlation χρησιμοποιεί
absolute prefix scores και συντηρητικά ties με tolerance1e−12. Οι δύο score methods
διαφέρουν και δεν συγκρίνονται ως CE. SustainedSR90 σημαίνειSR≥0,90 σε όλα τα
επόμενα prefixes μέχρι το budget, όχι μία μεμονωμένη πρώτη επιτυχία. Τα failures
καταγράφονται ως μη επίτευξη εντός 2000, όχι ως πλασματική επιτυχία στα 2000.

Οι 20 σειρές περιέχουν αλληλεπικαλυπτόμενα traces από κοινό pool· δεν είναι 20training
seeds ή ανεξάρτητες φυσικές campaigns. Τα τρία CNNs έχουν ένα κοινό training seed,
όχι επαναλήψεις της ίδιας αρχιτεκτονικής. Δεν αναφέρουμε confidence intervals ή
μεταβλητότητα μεταξύ trainings, corruption seeds ή συσκευών που δεν μετρήθηκαν.
Τα label/product shuffle controls είναι περιγραφικά, όχι αυτόματοι p-values.

## 7. Βιβλιογραφία και τι μπορεί να θεωρηθεί συνεισφορά

Noise/shifting augmentation και τα όρια CNN shift robustness έχουν ήδη προηγούμενο.
Η εργασίαLi–Perin του 2024 εξετάζει countermeasures χωριστά και αναφέρει joint
strategies ως future work· αυτό δεν πιστοποιεί σημερινό κενό.
[Publisher full text](https://link.springer.com/article/10.1007/s13389-024-00363-3).
Η εργασίαKrček et al. μελετά shift robustness και augmentation ensembles.
[Preprint](https://eprint.iacr.org/2023/1100.pdf),
[publisher record](https://www.mdpi.com/2227-7390/12/20/3279).

Το EquivSCA προσθέτει shift/temporal-scale equivariant αρχιτεκτονική με διαφορετικό
training/epoch-selection πρωτόκολλο. Το RFA-SCA χρησιμοποιεί unlabeled target
adaptation, δηλαδή διαφορετική πρόσβαση σε target data από τη δική μας.
[EquivSCA preprint](https://eprint.iacr.org/2025/1379.pdf),
[RFA-SCA publisher PDF](https://file.techscience.com/files/onlinefirst/2026/6.11/TSP_CMC_81308/TSP_CMC_81308.pdf).
Η σχέση centered products και ευθυγράμμισης επίσης έχει προηγούμενο.
[Second-order Scatter Attack](https://eprint.iacr.org/2019/345.pdf).

Η τρίτη CNN εκτέλεση είναι προσαρμογή της μικρής αρχιτεκτονικής τουZaid et al.,
όχι ακριβής αναπαραγωγή αποτελεσμάτων. Ο δημόσιος κώδικας ορίζει 45ktrain/batch 50/
OneCycle max LR 0,005, ενώ εμείς 10k/batch 128/constantLR0,001. Από αυτά προκύπτουν
45.000 έναντι 3.950 updates για 50 epochs, περίπου 11,39 φορές λιγότεροι δικοί μαςupdates.
Αυτή είναι δική μας αριθμητική σύγκριση· δεν αποδεικνύει αιτία failure ή ότι περισσότερα
updates θα το διορθώσουν. Η training-only κανονικοποίηση διατηρείται.
[Author code](https://github.com/gabzai/Methodology-for-efficient-CNN-architectures-in-SCA/blob/master/ASCAD/N0%3D0/cnn_architecture.py).

Με τα σημερινά δεδομένα, η τεκμηριωμένη συνεισφορά είναι **αναπαραγώγιμη πανεπιστημιακή
μελέτη περίπτωσης**: negative CNN results, diagnostics και περιορισμοί συγκεκριμένου
feature-space corruption protocol. Δεν επιβεβαιώνεται νέα μέθοδος, όφελος augmentation
ή δημοσιεύσιμο ερευνητικό κενό. Ο [πίνακας βιβλιογραφίας](../../literature/REVIEW.md)
και ο [στοχευμένος έλεγχος της 5/10](../../literature/PRIMARY_AUDIT_2026-10-05.md)
καταγράφουν authors/venue/DOI, πρόσβαση, διαφορές και εκκρεμότητες. Η αναζήτηση δεν ήταν
εξαντλητική· final chapters, code URLs και forward-citation gaps δεν ερμηνεύονται ως
απουσία εργασιών. Δεν αγοράστηκε πρόσβαση.

## 8. Πραγματικό κόστος και αναπαραγωγιμότητα

| Ολοκληρωμένο training | GPU | Epochs / steps | Training-loop seconds | Validation-loop seconds |
|---|---|---:|---:|---:|
|ReLU|TeslaT4|50/3.950|18,08|3,49|
|LeakyReLU|TeslaT4|50/3.950|19,11|3,93|
|Literature CNN|TeslaT4|50/3.950|14,85|3,42|
|Σύνολο|Ίδιος τύπος GPU|150/11.850|52,04|10,84|

Οι χρόνοι είναι synchronized epoch loops με transfers και augmentation, όχι πλήρες
Kaggle elapsed time. Δεν περιλαμβάνουν container startup, εγκαταστάσεις, ελέγχους,
HDF5 inspection και checkpoint I/O. Δεν ανασυνθέσαμε αξιόπιστο συνολικό κόστος όλων
των sessions από αυτούς τους αριθμούς. Ενδεικτικά η τελευταία εκτέλεση είχε log
μέχρι 300,285 s, με πολύ μεγαλύτερο setup κόστος από τον training loop. Οι πρώτες 3
benchmark epochs του αρχικού baseline επαναχρησιμοποιήθηκαν στις 50 και δεν
μετρήθηκαν ως πρόσθετο πλήρες training.

Η CPU sensitivity μέτρηση χρειάστηκε 47,52 s και η ανεξάρτητη επαλήθευση 6,07 s.
Αυτοί οι χρόνοι δεν προστίθενται σε GPU timings σαν κοινή compute σύγκριση.
Η παρούσα σύνθεση διαβάζει υπάρχοντα JSON/checksums, δεν ξανατρέχει εκπαίδευση
ή ανάκτηση. Συνολικά παραμένουν 3 πλήρη GPU trainings και 1 Kaggle notebook.
Ο source fingerprint είναι
`84eff3cde04c0e9a1756a3d29c44ec82e115a1a08575132686a02520333e2b5c`.

Κατά την αρχική σύνθεση, το τελευταίο πλήρες suite είχε 44 tests passed/14 υπάρχοντα deprecation warnings σε 32,51 s.
Οι CPU ranks επαληθεύτηκαν με ανεξάρτητο Pearson formula και production corruption
replay,640endpoints. Συνθετικά tests ελέγχουν κώδικα και όχι φυσική αποτελεσματικότητα.
Στη συνεδρία σύνθεσης δεν άλλαξαν labels/ranking/splits/transforms/checkpoints,
οπότε δεν δηλώνουμε νέα εκτέλεση του full suite. Ελέγχθηκαν απευθείας οι πίνακες,
οι πηγές τους και η διατήρηση των παγωμένων artifacts.

## 9. Συγκεκριμένη συνέχεια μέσα στο ισχύον όριο

Προτεινόμενη συνέχεια χωρίς νέα GPU εκπαίδευση: να χρησιμοποιήσουμε αυτή τη
διαγνωστική κατεύθυνση ως προσωρινό άξονα της πανεπιστημιακής εργασίας και να
χρησιμοποιήσουμε την ολοκληρωμένη αναπαραγωγή από καθαρό περιβάλλον, την ελεγμένη
βιβλιογραφία και την εξήγηση του threat model στην τελική επιμέλεια. Το αρχικό augmentation ερώτημα καταγράφεται ως
μη απαντημένο λόγω failed baseline gate· δεν αφαιρείται από το ιστορικό.

| Επιλογή συνέχειας | Πρόσθετα πλήρη GPU trainings | Τι μπορεί να απαντήσει | Κατάσταση |
|---|---:|---|---|
|Σύνθεση/αναπαραγωγή υπάρχοντων αποτελεσμάτων|0|Διαγνωστική μελέτη αυτού του setup και των ορίων του|Ολοκληρώθηκε· απομένει τελική επιμέλεια|
|Πρακτική ευθυγράμμιση από traces|0 κατ' αρχήν|Εκτίμηση shifts χωρίς γνωστήδ και diagnostic robustness|Δεν υλοποιήθηκε· απαιτεί ξεχωριστό παγωμένο πρωτόκολλο|
|Νέο CNN recipe baseline και conditional combined|1baseline +1combined αν περάσει|Αρχικό none/combined ερώτημα σε νέο setup|Σύνολο μπορεί να γίνει5· απαιτεί αλλαγή scope/ορίου και συμφωνία|

Απομένει μία πλήρης GPU εκπαίδευση κάτω από το cap4. Αυτό **δεν αρκεί** για νέο
baseline και επιτυχημένο conditional combined. Ο χρήστης στη συνέχεια ενέκρινε
πειράματα προς paper· εκτελέστηκε η CPU επέκταση της§12, διατηρώντας GPUcap4,
training10k και το CNN checkpoint rule. Δεν υποβλήθηκε νέο GPU run.
Η αρχική σύσταση είναι δική μας κρίση από τα ευρήματα, όχι κριτήριο
του καθηγητή ή εγγύηση αξιολόγησης. Δεν έχει δοθεί συγκεκριμένη ημερομηνία παράδοσης·
ο χρήστης ανέφερε διαθέσιμο εξάμηνο και απουσία κριτηρίων αξιολόγησης.

Για paper θα χρειαστεί να καθοριστεί ξεχωριστή νέα συνεισφορά και ισχυρότερη
επιβεβαίωση· η σημερινή αναφορά δεν προεξοφλεί τέτοιο αποτέλεσμα.

## 10. Αρχεία και επανάληψη της σύνθεσης

Η [evidence.json](evidence.json) συγκεντρώνει τους αριθμούς και SHA-256 κάθε
εισόδου. Ο companion `notebooks/build_study_synthesis.py` διαβάζει μόνο αποθηκευμένα
artifacts, επιβεβαιώνει 50 epochs/3.950 steps, minimum-CE selections, archive hashes,
κοινά split/data identifiers και το failed gate, και δημιουργεί το γράφημα ιστοριών.
Δεν ανοίγει HDF5 trace groups, δεν επιλέγει νέο μοντέλο και δεν καλεί Kaggle.

```powershell
& .\.venv\Scripts\python.exe notebooks/build_study_synthesis.py
```

Αναλυτικά τεκμήρια:

- [ReLU training και validation](../kaggle_baseline_v3_2026-10-03/REPORT_EL.md)
- [LeakyReLU training και validation](../kaggle_leaky_v5_2026-10-03/REPORT_EL.md)
- [Literature CNN training και gate](../kaggle_literature_v7_2026-10-03/REPORT_EL.md)
- [Masking/point selection](../masking_diagnosis_2026-10-03/REPORT_EL.md)
- [Frozen CNN και correlation diagnostics](../literature_diagnosis_2026-10-04/REPORT_EL.md)
- [Παγωμένη sensitivity, πλήρες GE/SR grid και oracle limits](../correlation_robustness_2026-10-05/REPORT_EL.md)
- [Πρωτόκολλο](../../docs/EXPERIMENT_PROTOCOL.md), [βιβλιογραφία](../../literature/REVIEW.md)

Τα προσωπικά credentials, το HDF5, τα run checkpoints και τα environments παραμένουν
εκτός Git. Η [verification.json](verification.json) καταγράφει την επαλήθευση της
σύνθεσης και τη διατήρηση του ενεργού notebook/checkpoint/packet.

## 11. Συμπληρωματικός έλεγχος αναπαραγωγής σε καθαρό CPU venv

Δημιουργήθηκε νέο περιβάλλον από27 exact wheels με hashes και ξεχωριστό αντίγραφο
του frozen source. Επαληθεύτηκαν imports/dependencies με `python -I` και πέρασε
το pip check. Το πλήρες suite πέρασε ξανά: **44 passed/14 warnings σε597,51s**.
Αυτό είναι η μεταγενέστερη εκτέλεση αναπαραγωγής, ξεχωριστή από τον αρχικό χρόνο32,51s.

Τα literature CNN best/last training και clean validation CE/accuracy συμφωνούν
ακριβώς με την προηγούμενη CPU διάγνωση, μαζί με80.000 prefix ranks. Τα δύο raw
correlation ζεύγη διατηρούν20/20 επιτυχίες και άλλους80.000 ίδιους prefix ranks.
Και οι32 sensitivity rows και138 arrays έχουν ίδια dtype/shape/bytes· ξαναπέρασαν
640 ανεξάρτητοι Pearson endpoint έλεγχοι. Το real-data CPU replay πήρε62,36s μετά imports.

Δεν επαναλήφθηκαν historical ReLU/LeakyReLU inference, BN counterfactual/shuffled
controls ή η επιλογή σημείων. Δεν έγιναν real-data optimization, νέαGPU εκτέλεση
ή final attack payload reads. Το original minimum-CE CNN gate παραμένειfailed,
combined skipped· σύνολο3 fullGPU trainings/1canonical Kaggle notebook.

Πρόκειται για checkpoint/diagnostic αναπαραγωγή στο ίδιο Windows host/base interpreter,
όχι νέα GPU training, cross-device ή unknown-key επιβεβαίωση. Οι ίδιοι oracle και
profiling-information περιορισμοί ισχύουν. Η καθαρή εγκατάσταση δεν προσθέτει
τεκμήριο οφέλους training augmentation ή novelty.

Αναλυτικά [μετρήσεις και όρια](../cpu_reproduction_2026-10-05/REPORT_EL.md),
[επαλήθευση](../cpu_reproduction_2026-10-05/verification.json) και
[οδηγίες](../../docs/CPU_REPRODUCTION.md). Τα νέα τεκμήρια διατηρούνται χωριστά
από το evidence.json της αρχικής σύνθεσης.

## 12. Επέκταση πειραμάτων προς πιθανό paper

Με εντολή χρήστη της5/10, προστέθηκαν τρεις πραγματικές CPU φάσεις στην εργασία:
trace-only NCC/Gaussian alignment, coordinate-consistent comparison raw/feature
shift και επιλογή δεύτερης τάξης σημείων μόνο από training identity labels/HW.
Διατηρήθηκαν train10k/validation5k· οι τρεις confirmation pools5k είναι disjoint,
με δικά τους plans παγωμένα πριν την αντίστοιχη εκτέλεση. Η επιλογή στην τρίτη
φάση δεν διάβασε training mask/share/key metadata ούτε validation/confirmation.

| Πείραμα | Gaussian raw combined5 SR@2.000 | Fixed SR | Κρίσιμο όριο |
|---|---|---|---|
| Φάση1, παλιά181×521/156×517, confirmation1 | 20/20,20/20 | 0/20,0/20 | Surrogate raw-domain scoring είχε coordinate confound |
| Φάση2, ίδια ζεύγη, corrected domain, confirmation2 | 11/20,20/20 | 0/20,0/20 | Το πρώτο20/20 δεν διατηρήθηκε και στα δύο |
| Φάση3, train-label-only156×521/182×547, confirmation3 | 20/20,18/20 | 0/20,0/20 | OODGaussian6/20,0/20· διαφορετική pool/σημεία |

Combined5 εδώ σημαίνει shift±5 και **ομοιόμορφο raw Gaussian σ=1,3**, όχι normalized
σ=0,1. OOD±10/σ=2,6. Τα20 orders επικαλύπτονται και αφορούν ένα key byte· δεν είναι
20training seeds/keys. Το γνωστό synthetic shift είναι μόνο diagnostic control.
Η coordinate correction ελέγχει λάθος centering/scales· δεν αποδεικνύει ότι η
σειρά normalization εξηγεί το clean CNN failure. Το αρχικό CNN augmentation
ερώτημα παραμένει αναπάντητο και το failed gate δεν αντικαταστάθηκε με CPA success.

Στην τρίτη φάση, Gaussian combined5 GE0/0,10 και sustainedSR90 στα899/1998 traces.
Clean20/20 και στα δύο. Στο OOD κανένα ζεύγος δεν έφτασε sustainedSR90 εντός2.000.
Αυτό είναι συγκεκριμένο εύρημα robustness με όρια· δεν αποτελεί γενική μέτρηση
υπεροχής της νέας επιλογής έναντι των προηγούμενων σε κοινή confirmation pool.

288 recovery summaries και5.760 ανεξάρτητοι CPA endpoints ελέγχθηκαν, μαζί με
576 sampled shift estimates και13 training pair coefficients. Πλήρες suite
57passed/14warnings σε19,43s. Οι τρεις CPU loops πήραν587,83s συνολικά μετά imports,
χωρίς tests/report/όλη τη συνεδρία. Νέα GPU trainings0, σύνολο3,1canonical notebook,
real-data optimizer updates0, original attack payload reads0 από αυτή την επέκταση.

Η βιβλιογραφία ήδη καλύπτει normalization/misalignment και second-order alignment.
Δεν τεκμηριώθηκε νέα τεχνική ή ακάλυπτο βιβλιογραφικό κενό. Παραμένει να καθοριστούν
κατάλληλες primary comparisons και independent campaign/key evidence για πιθανή
δημοσίευση. Οι τρεις confirmation pools έχουν πλέον εξεταστεί και δεν επαναχρησιμοποιούνται
ως αθέατες για επόμενες επιλογές.

[Πλήρης νέα αναφορά, δύο γραφήματα και κόστος](../paper_extension_2026-10-05/REPORT_EL.md),
[288 μετρήσεις](../paper_extension_2026-10-05/all_results.csv),
[evidence](../paper_extension_2026-10-05/evidence.json),
[verification](../paper_extension_2026-10-05/verification.json),
[primary audit](../../literature/PAPER_ALIGNMENT_AUDIT_2026-10-05.md).

## 13. SAD baselines και έλεγχος αντιστοίχισης shifts

Η τέταρτη CPU φάση πάγωσε το πρωτόκολλό της πριν την εκτέλεση, με τα ίδια training10k,
points156×521/182×547, raw conditions και κοινά RNG streams/orders. Νέο confirmation5k
seed20261008, χωριστό από train/validation και τις τρεις προηγούμενες confirmation pools.
Δεν έγινε νέο pair search. Το SAD reference επιλέχθηκε μόνο από training waveforms,
ως το πλησιέστερο στο training mean στο fixed window20:680, χωρίς labels/keys/masks.

| Μέθοδος | Combined5 pair1 SR | Combined5 pair2 SR | OOD pair1 SR | OOD pair2 SR |
|---|---:|---:|---:|---:|
| Fixed | 0/20 | 0/20 | 0/20 | 0/20 |
| NCC | 20/20 | 20/20 | 2/20 | 5/20 |
| Gaussian | 20/20 | 20/20 | 2/20 | 3/20 |
| SAD mean | 20/20 | 20/20 | 2/20 | 6/20 |
| SAD reference | 20/20 | 19/20 | 1/20 | 6/20 |
| Gaussian wrong row | 0/20 | 0/20 | 0/20 | 0/20 |
| Known shift | 20/20 | 19/20 | 1/20 | 4/20 |

Combined5=raw shift±5/σ1,3, OOD=±10/σ2,6. Wrong row σημαίνει deterministic roll των
Gaussian offsets κατά μία row, με ακριβώς ίδιο histogram και λανθασμένη αντιστοίχιση
trace/estimate. Η απώλεια20/20→0/20 στηρίζει τη σημασία σωστής αντιστοίχισης στην
παρούσα synthetic-shift περίπτωση. Το primary correspondence criterion πέρασε.

Η SAD είναι γνωστή objective, τεκμηριωμένη στο
[επίσημο ChipWhisperer API](https://chipwhisperer.readthedocs.io/en/latest/analyzer-api.html#chipwhisperer.analyzer.preprocessing.resync_sad.ResyncSAD).
Οι δικές μας train-mean/reference παραλλαγές διαφέρουν σε inclusive search, κοινό
tie rule και no rejection· δεν είναι exact package reproduction. SAD mean ισοφάρισε
Gaussian/NCC στο primarySR, συνεπώς δεν υπάρχει μετρημένη Gaussian υπεροχή σε αυτό
το endpoint ή νέα τεχνική. Prefix thresholds διαφέρουν χωρίς επιλογή ευνοϊκού metric:
Gaussian pair2 sustainedSR90 στα1606, SADmean1888, SADreference1300/endpoint19/20.

Όλες οι πρακτικές μέθοδοι απέτυχαν στοOOD threshold18/20. Global synthetic shifts
δεν καλύπτουν το δυσκολότερο elastic jitter/shuffling που ήδη διακρίνει το
[Second-order Scatter Attack §1.1](https://eprint.iacr.org/2019/345.pdf).
Στη φάση4 δεν εκτελέστηκαν Scatter/DTW ή ανεξάρτητη campaign/key αξιολόγηση.
Η μετέπειτα αξιολόγηση νέας καμπάνιας/κλειδιού περιγράφεται στη§14.

Η φάση πρόσθεσε112 summaries/2.240 independent execution endpoints και112 πρόσθετα
independent replays,256 sampled shift estimates. Πέρασαν61tests/14warnings σε14,88s.
Experiment loop136,87s/verifier5,90s μετάimports· τέσσερις CPU experiment loops724,71s,
400 summaries/8.000 execution endpoint checks συνολικά. Single-call inference timings
καταγράφονται χωριστά, χωρίς repeated variance ή σταθερό speedup claim.

Παγωμένος source/checkpoints/active Input/notebook διατηρήθηκαν. Νέα GPU trainings0,
σύνολο3/cap4/1notebook, original CNN gatefailed και combined absent, final attack reads0
από τη φάση4. Το τέταρτο confirmation πλέον έχει εξεταστεί και δεν ανακυκλώνεται ως
αθέατη επιβεβαίωση. Η Gaussian αναπαραγωγή επιτεύχθηκε με frozen pairs, αλλά η
same-key/campaign επιβεβαίωση δεν αρκεί για paper novelty ή cross-device claim.

[Αναφορά, κόστος και γράφημα](../paper_alignment_controls_2026-10-05/REPORT_EL.md),
[112 μετρήσεις CSV](../paper_alignment_controls_2026-10-05/all_results.csv),
[verification](../paper_alignment_controls_2026-10-05/verification.json),
[report verification](../paper_alignment_controls_2026-10-05/report_verification.json),
[primary baseline audit](../../literature/ALIGNMENT_BASELINES_2026-10-05.md).

## 14. Προοπτική επιβεβαίωση σε διαφορετική καμπάνια και κλειδί

Αποκτήθηκε το επίσημο αρχικό ASCAD variable-key,438.606.904bytes με επαληθευμένο
SHA-256. Profiling200k/attack100k,1400samples. Οι δημιουργοί περιγράφουν φυσική
ασυγχρονία σε αυτή την καμπάνια· χρησιμοποιήθηκε το original extracted αρχείο,
όχι desync50/100. [Επίσημη τεκμηρίωση](https://github.com/ANSSI-FR/ASCAD/blob/master/ATMEGA_AES_v1/ATM_AES_v1_variable_key/Readme.md).

Training10k/validation5k με seed2026, prospective attack5k με subsetseed20261009.
Το πρωτόκολλο και τα ζεύγη187×1080/334×573, training moments/variance πάγωσαν πριν
διαβαστούν validation ή attack τιμές. Η επιλογή χρησιμοποιεί μόνο training traces
και παρεχόμενα identity labels, με ίδιο separation50/diversity20 και προκαθορισμένο
interior margin10 για αποφυγή padding. Πρόκειται για νέο campaign-specific fit,
όχι zero-shot μεταφορά παλαιών σημείων/CNN ή απόδειξη διαφορετικής συσκευής.

Στις αξιολογημένες attack5k rows το πλήρες key είναι σταθερό, διαφορετικό από το
αρχικό, απόν από τα10.000 διαφορετικά training keys. Byte2=0x22, keys μόνο για
evaluation correctness/rank reporting. Δεν χρησιμοποιήθηκε simulated key ή
plaintext-key adjustment. Η αξιολόγηση αφορά ένα άγνωστο byte ενός νέου κλειδιού.

| Μέθοδος | Clean pair1 / pair2 | Shift5 pair1 / pair2 | Combined5 pair1 / pair2 | OOD pair1 / pair2 |
|---|---:|---:|---:|---:|
| Fixed | 10/20 / 0/20 | 0/20 / 0/20 | 0/20 / 0/20 | 0/20 / 0/20 |
| NCC | 14/20 / 0/20 | 14/20 / 0/20 | 0/20 / 0/20 | 0/20 / 0/20 |
| Gaussian | 15/20 / 0/20 | 15/20 / 0/20 | 0/20 / 0/20 | 0/20 / 0/20 |
| SAD mean | 12/20 / 0/20 | 12/20 / 0/20 | 0/20 / 0/20 | 0/20 / 0/20 |
| Gaussian wrong row | 3/20 / 0/20 | 0/20 / 0/20 | 0/20 / 0/20 | 0/20 / 0/20 |
| Known injected shift | 10/20 / 0/20 | 10/20 / 0/20 | 0/20 / 0/20 | 0/20 / 0/20 |

Budget2000/20 κοινές επικαλυπτόμενες σειρές/seed8001, ένα κλειδί και ένα training split.
Training median range48, συνεπώς combined5 raw±5/σ4,8 και OOD±10/σ9,6.
Τα relative noise factors0,1/0,2 είναι ίδια, αλλά οι απόλυτες εντάσεις διαφέρουν από
το fixed-key1,3/2,6. Φυσική ασυγχρονία/window/fitting/κλειδιά αλλάζουν μαζί·
δεν τεκμηριώνεται ότι μόνο η αλλαγή κλειδιού προκαλεί τη διαφορά. Known injected
shift αφαιρεί μόνο την πρόσθετη synthetic μετατόπιση, όχι την άγνωστη φυσική timing variation.

Και τα δύο primary criteria απέτυχαν: Gaussian SR0/20,0/20, GE105,90/164,55,
μηδενική SR improvement έναντι fixed στη combined5. Καμία γραμμή δεν έφτασε sustainedSR90.
Το δεύτερο pair δεν διατηρεί την training|r|≈0,038 στη clean validation, όπου r≈0,002.
Αυτό καταγράφει αστάθεια selected signal εκτός training· δεν αποδεικνύει από μόνο
του causal overfitting ή έλλειψη φυσικής διαρροής. Δεν αντικαταστάθηκε pair/μέθοδος
και δεν έγινε tuning από validation/attack. Η validation με varying keys είχε μόνο
descriptive HW correlations, όχι συσσώρευση ως υποτιθέμενο unknown fixed-key attack.

65tests passed/14warnings σε18,03s. 48νέα recovery summaries/960independent execution
endpoints,48additional replays,192sampled offset estimates,7real training coefficient checks.
Recorded CPU experiment92,26s μετάimports, fit1,82s περιλαμβανόμενο, verifier18,07s.
Πέντε paper φάσεις448summaries/8.960executionchecks/160additionalreplays,
816,97s συνολικού recorded CPU experiment time, όχι συνολικού session wall time.
Ένα synthetic test απέτυχε πριν οποιαδήποτε real-data ανάγνωση λόγω matrix slicing·
διορθώθηκε και διατηρήθηκαν failed test/παλιό plan με explicit correctness amendment.

Το νέο attack subset είναι πλέον viewed evidence και αποκλείεται από tuning.
Το αρχικό fixed-key attack payload δεν διαβάστηκε από αυτή την επέκταση. Source,
checkpoints/παλιά αρνητικά runs/failed gate/conditional combined/single notebook διατηρήθηκαν.
ΝέαGPU0, συνολικά3/cap4. Η προσπάθεια γενίκευσης απέτυχε· δεν θεμελιώνεται paper
νέας Gaussian μεθόδου ή γενικής robustness υπεροχής. Επόμενο ερώτημα είναι η
σταθερότητα/false-selection συμπεριφορά μόνο σε νέα profiling rows με νέο frozen plan.

[Πλήρης αναφορά και γράφημα](../paper_variable_campaign_2026-10-05/REPORT_EL.md),
[48μετρήσεις](../paper_variable_campaign_2026-10-05/recovery_summary.csv),
[independent verification](../paper_variable_campaign_2026-10-05/verification.json),
[report verification](../paper_variable_campaign_2026-10-05/report_verification.json),
[dataset/protocol audit](../../literature/VARIABLE_CAMPAIGN_2026-10-05.md).

## 15. Παγωμένα σημεία, τυχαία maxima και φρέσκο profiling confirmation

Στις6/10 προεγγράφηκε νέο diagnostic plan, με ίδια ιστορικά training10k και pairs,
χωρίς άλλο model/optimizer/budget/trainingseed.99 training-label permutations
ανά καμπάνια, με πλήρη αναζήτηση maximum|Pearson| στα211.575/885.115 αρχικά eligible
ζεύγη. Training moments/product variances επαναχρησιμοποιούνται. Το max null
δεν αφορά μόνο τα επιλεγμένα points: περιλαμβάνει την προηγούμενη πολλαπλή αναζήτηση.

Η calibration ολοκληρώθηκε πριν διαβαστούν νέες confirmation τιμές. Φρέσκο profiling5k
ανά campaign με seed20261010, excluded όλα τα προηγούμενα training/validation/
confirmation indices. Fixed35kexcluded→40kused,variable15kexcluded→20kprofilingused.
Καμία attack payload/key/mask/plaintext metadata ανάγνωση από αυτή τη φάση.
Οι ήδη εξετασμένες attack/confirmation pools δεν ανακυκλώνονται ως αθέατες.

Raw fixed-pair products με training centers. Direction κλειδώνει από το historical
training sign.999 pairing permutations στα νέα labels, statistic=sign(trainr)×r.
Criterion:signedr>0 και Bonferroni-adjustedp=min(4p,1)≤0,05 για τέσσερις tests.
Monte Carlo p=(1+count(null≥observed−1e−12))/(B+1), μη μηδενικό,
με resolution0,01 στο training diagnostic και0,001 στηconfirmation.
[Επίσημη τεκμηρίωση των pairing tests και +1 correction](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html).
Η υλοποίηση εδώ είναι NumPy, δεν καλεί SciPy. Random-pairing/exchangeability
assumption απαιτείται· δεν αποδεικνύεται acquisition stationarity ή unconditional security.

| Campaign / pair | Training r | Fresh confirmation r | Train max-null tail | Confirmation p adjusted | Criterion |
|---|---:|---:|---:|---:|---|
| fixed / pair1 | -0.198491 | -0.214335 | 0.01 | 0.004 | Πέρασε |
| fixed / pair2 | -0.164445 | -0.189627 | 0.01 | 0.004 | Πέρασε |
| variable / pair1 | -0.070405 | -0.105384 | 0.01 | 0.004 | Πέρασε |
| variable / pair2 | -0.037942 | -0.026326 | 0.69 | 0.092 | Δεν πέρασε |

Median training null maxima0,039628/0,039531. Στο variablepair2,68/99 full-search
maxima≥observed|r|−1e−12,tail0,69. Ο συνδυασμός δεν ξεχωρίζει από συνήθη μεγάλα
τυχαία maxima αυτής της αναζήτησης. Αυτό δεν είναι πιθανότητα ότι το pair είναι
ψευδές, proof strong FWER υπό partial alternatives ή απόδειξη μηδενικής leakage.
Το raw confirmationp του είναι0,023,διορθωμένο0,092. Η ίδια-sign correlation είναι
ασθενής, δεν καλύπτει το προκαθορισμένο criterion. Τα άλλα τρία pAdjusted0,004
προέρχονται από το Monte Carlo floor raw0,001, όχι exhaustive exact p-values.

Η επιλογή απαιτούσε δύο pairs χωρίς να ελέγχει αν το δεύτερο είναι διακριτό από
τυχαία maxima. Αυτό αναδεικνύει κίνδυνο selection και άνιση signal replication·
δεν αποδεικνύει causal overfitting. Ελέγχεται selected-signal stability, όχι spatial
argmax stability across training seeds. Το πρώτο variable-key pair παραμένει
profiling-informative, ενώ απέτυχε στο παλιό combined5 attack. Η αδυναμία του δεύτερου
δεν επαρκεί ως μοναδική εξήγηση της προηγούμενης αποτυχίας. Δεν τροποποιήθηκε pair,
μέθοδος/θόρυβος ή normalization και δεν πραγματοποιήθηκε νέα key recovery.

70tests passed/14warnings σε19,43s, JUnit19,422s. Independent verifier598train/null
coefficients,6sampled full-search matrix maxima,όλα3.996confirmation-null coefficients,
4τελικές γραμμές/splits/RNG/time ordering/artifact preservation. Δεν επανυπολογίστηκαν
όλα198null matrices με δεύτερη πλήρη implementation· τα198maximizing-pair scores
και6full-search replays ελέγχθηκαν χωριστά. CPUexperiment73,420532s μετάimports,
verifier20,746923s. Έξι recorded CPU experiment loops890,388246s συνολικά, εκτός
imports/tests/reports/session. Recovery summaries448/executionchecks8.960/
additionalreplays160 διατηρούνται· οι4νέες diagnostic γραμμές δεν είναι recoveries.

Τα νέα profiling confirmations είναι πλέον viewed evidence και αποκλείονται από
tuning. Ένα Kaggle notebook/3GPUtrainings/cap4/source/checkpoints/failed gate/combined absent
διατηρούνται. Η μελέτη τεκμηριώνει όρια και διαγνωστικά ευρήματα, όχι νέα attack
τεχνική ή paper-ready novelty. Πρόσθετη μέθοδος χρειάζεται ξεχωριστό training-only
frozen plan και αχρησιμοποίητη profiling επιβεβαίωση, χωρίς adaptation στο παλιό attack.

[Αναφορά και γράφημα](../paper_selection_audit_2026-10-06/REPORT_EL.md),
[τέσσερις γραμμές/statistics](../paper_selection_audit_2026-10-06/results.json),
[independent verification](../paper_selection_audit_2026-10-06/verification.json),
[report verification](../paper_selection_audit_2026-10-06/report_verification.json),
[sources/novelty/access limits](../../literature/SELECTION_AUDIT_2026-10-06.md).
