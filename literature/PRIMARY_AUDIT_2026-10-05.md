# Στοχευμένος έλεγχος πρωτογενών πηγών — 2026-10-05

Σκοπός: έλεγχος της επικάλυψης και των διαφορών πρωτοκόλλου πριν από νέα GPU πρόταση.
Χρησιμοποιήθηκαν author code, publisher pages και IACR preprints. Αυτό δεν είναι
εξαντλητική ανασκόπηση ή απόδειξη ότι ένα ερευνητικό κενό παραμένει ακάλυπτο.
Ο [πίνακας βιβλιογραφίας](REVIEW.md) διατηρεί authors/venue/DOI και πρόσβαση ανά εργασία.

| Πρωτογενής πηγή / περιοχή ελέγχου | Επιβεβαιωμένο στοιχείο | Επίπτωση για εμάς |
|---|---|---|
| [Zaid et al. author code, ASCAD/N0=0](https://github.com/gabzai/Methodology-for-efficient-CNN-architectures-in-SCA/blob/master/ASCAD/N0%3D0/cnn_architecture.py), initialization/training/preprocessing | 45k/5k,50epochs,batch50,OneCycle maxLR0,005. StandardScaler και MinMax fit σε όλο το profiling πριν από το45k/5k split στον συγκεκριμένο δημόσιο κώδικα. | Το δικό μας10k/batch128/constantLR0,001/train-only fit είναι προσαρμογή. Εξίσωση architecture/epochs δεν εξισώνει training recipe. Δεν αντιγράφουμε fit που περιλαμβάνει validation rows. |
| [Li–Perin 2024](https://link.springer.com/article/10.1007/s13389-024-00363-3), §§2.3/4/6 | ASCADr/DPAv4.2, HPO/augmentation grid, χωριστές countermeasure μελέτες· η συνδυασμένη περίπτωση αναφέρεται ως μελλοντική δουλειά. | Αφετηρία πιθανού joint ερωτήματος, όχι επιβεβαίωση πρωτοτυπίας το2026. Οι εντάσεις/steps/data δεν μεταφέρονται αυτούσια. |
| [Krček et al. 2024 preprint](https://eprint.iacr.org/2023/1100.pdf), §5, και [publisher record](https://www.mdpi.com/2227-7390/12/20/3279) | Ελέγχει όρια shift robustness και augmentation/ensembles. Publisher metadata και επιλεγμένα indexed final-text αποσπάσματα προσβάσιμα. | Η ιδέα shift augmentation και η μη εγγυημένη shift invariance έχουν προηγούμενο. Η άμεση final HTML/PDF πρόσβαση απέτυχε· δεν δηλώνεται πλήρης final/preprint αντιπαραβολή. |
| [EquivSCA preprint](https://eprint.iacr.org/2025/1379.pdf), §§5.2–5.3, [τελική έκδοση](https://doi.org/10.1007/978-3-032-22931-1_8) | Shift/time-scale experiments,100epochs,batch256,OneCycle,GE-based epoch selection,5 runs. Τελικό chapter metadata: CT-RSAC2026,198–228, online2July2026. | Διαφορετικός κανόνας επιλογής checkpoint και κόστος· δεν συγκρίνουμε δημοσιευμένα GE με τα δικά μας σαν κοινό benchmark. Δεν εντοπίστηκε joint Gaussian/shift training factorial experiment στις ελεγμένες ενότητες. |
| [RFA-SCA publisher PDF](https://file.techscience.com/files/onlinefirst/2026/6.11/TSP_CMC_81308/TSP_CMC_81308.pdf), §§3.6/4.1/4.3/5 | Unlabeled target adaptation. Table2: ξεχωριστά ASCAD desync/jitter/noise. Main comparison seed8, ablation5seeds, ιδιαίτερη noise seed sensitivity. | Διαφορετικό threat model. Οι ελεγμένες συνθήκες δεν αποδεικνύουν απουσία κάθε joint study. Ο [publisher](https://doi.org/10.32604/cmc.2026.081308) καταγράφει πλέον88(3), issue23July2026. |
| [Prouff–Rivain–Bévan revised preprint](https://eprint.iacr.org/2010/646), abstract/metadata και indexed PDF excerpt | Revised έκδοση IEEE TC2009· combining/correlation υπό HW και Gaussian noise assumptions. | Η δεύτερης τάξης στατιστική τεχνική είναι υπάρχουσα. Άμεσο PDF blocked· δεν δηλώνεται πλήρης ανάγνωση ή καθολική optimality. |
| [Second-order Scatter Attack](https://eprint.iacr.org/2019/345.pdf), §§2/4 | Περιγράφει centered products, πρόβλημα επιλογής σημείων/ευθυγράμμισης, window/joint-distribution εναλλακτικές και πρακτική masked AES/EM περίπτωση. | Η ευαισθησία των fixed points σε shifts δεν είναι νέο εύρημα πεδίου. Το δικό μας oracle παραμένει συγκεκριμένο διαγνωστικό control. Code URL δεν επαληθεύτηκε. |

Αριθμητική συνέπεια της ανάγνωσης του author code: `ceil(45.000/50)×50 = 45.000`
updates, ενώ εμείς `ceil(10.000/128)×50 = 3.950`. Οι τελευταίοι είναι περίπου11,39
φορές λιγότεροι. Αυτό είναι **δικός μας υπολογισμός**, όχι ισχυρισμός του paper.
Εκθέσεις σε training traces:2.250.000 έναντι 500.000, με διαφορετικά unique budgets.
Η διαφορά δεν αποδεικνύει αιτία αποτυχίας ή ότι μεγαλύτερο budget θα την διορθώσει.
Το StandardScaler→MinMax του ίδιου fit set είναι κατ' αρχήν affine-equivalent με
άμεσο feature MinMax· δεν χαρακτηρίζουμε την απουσία του πρώτου scaler ως αποδεδειγμένο bug.

## Πρόσβαση και εκκρεμότητες

- Το τελικό EquivSCA chapter είναι subscription preview· χρησιμοποιήθηκε το δωρεάν
  preprint. Το επίσημο shortened code link `https://shorturl.at/lxW7K` απέτυχε·
  ο προορισμός παραμένει άγνωστος, δεν δηλώνεται ότι δεν υπάρχει code.
- Το RFA PDF προσβάστηκε. Δεν επαληθεύτηκε δημόσιο code repository.
- Τα παλιότερα κενά CutMix/IEEE diffusion-synthesis full text δεν λύθηκαν σε αυτή
  τη συνεδρία. Δεν αγόρασα πρόσβαση και δεν απέκτησα institution credentials.
- Search crawled/published dates δεν χρησιμοποιούνται ως publication years·
  προτεραιότητα στα publisher/ePrint metadata. Αποτελέσματα με μεταγενέστερη
  ημερομηνία έκδοσης χωρίς σαφές προγενέστερο online record δεν έγιναν τρέχοντες comparators.

## Καταγραφή αναζήτησης

Χρησιμοποιήθηκαν οι queries:

1. `"side-channel" "augmentation" "noise" "desynchronization" 2025 2026`
2. `"side-channel" "combined" "noise" "augmentation" 2026`
3. `"side-channel" "augmentation" "Gaussian noise" "2025"`
4. `"side-channel" "augmentation" "2026"`
5. `"second-order" "centered product" "correlation" masking`
6. `"Statistical Analysis of Second Order Differential Power Analysis" Prouff Rivain Bevan`
7. `"Shift-Invariance Robustness" "3279" pdf`

Οι πρόσφατες queries ήταν scoped σε IACR/publishers και επέστρεψαν περιορισμένα ή
άσχετα αποτελέσματα. Δεν αποτελούν πλήρες forward-citation search· η πρόσβαση στο
TCHES domain αναφέρθηκε blocked. Ελέγχθηκαν απευθείας οι ήδη εντοπισμένες κύριες
πηγές. Η μη εύρεση νέου ακριβούς comparator εδώ **δεν είναι απόδειξη απουσίας**.

Απόφαση: δεν διατυπώνουμε novelty claim για joint augmentation, centered products ή
alignment. Το παρόν υλικό στηρίζει πανεπιστημιακή διαγνωστική μελέτη περίπτωσης.
Αν ζητηθεί paper, χρειάζεται αυτοτελές τεκμηριωμένο κενό και ισχυρότερο πρωτόκολλο.
