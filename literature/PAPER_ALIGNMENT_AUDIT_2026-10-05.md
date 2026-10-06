# Έλεγχος πριν από τα νέα πειράματα για πιθανή δημοσίευση

Ο χρήστης ζήτησε στις5/10 νέα πειράματα με στόχο paper και ένταξή τους στην τελική
εργασία. Το πρώτο επέκτεινε τα CPU diagnostics: πραγματική εκτίμηση shifts από traces,
έλεγχος της σειράς MinMax/shift και επιβεβαίωση σε5.000 άλλα profiling rows.
Το [παγωμένο πλάνο](../outputs/paper_alignment_2026-10-05/plan.json) προηγείται της εκτέλεσης.

## Πρωτογενή προηγούμενα που περιορίζουν την πρωτοτυπία

- **Krček, Wu, Perin, Picek, Shift-Invariance Robustness**, preprint
  [2023/1100, §2 και §5.1](https://eprint.iacr.org/2023/1100.pdf), τελική έκδοση
  [Mathematics2024](https://doi.org/10.3390/math12203279). Το preprint εξηγεί ρητά ότι
  position-wise normalization σε μη ευθυγραμμισμένα traces παραμορφώνει τα features,
  χρησιμοποιεί horizontal MinMax και αναφέρει διαφορετική απόδοση από τα αρχικά CNN
  recipes λόγω normalization. Αυτό ήδη καλύπτει τη γενική ιδέα του προβλήματος.
  Δεν επαληθεύτηκε πλήρης final/preprint αντιπαραβολή· τα παραπάνω αποδίδονται στο preprint.
- **Thiebeauld, Vasselle, Wurcker, Second-order Scatter Attack**, preprint2019,
  [primary record](https://eprint.iacr.org/2019/345). Το abstract περιγράφει το πρόβλημα
  ευθυγράμμισης δεύτερης τάξης και προσέγγιση joint-distribution υπό misalignment.
  Η ύπαρξη επιτυχημένης statistical recovery ή alignment δεν είναι νέα συνεισφορά από μόνη της.
- **Karayalcin, Krcek, Picek, A Practical Tutorial on Deep Learning-based Side-channel
  Analysis**, [ePrint2025/471](https://eprint.iacr.org/2025/471), received12March2025,
  revised17July2025. Το primary metadata/abstract επιβεβαιώνει πρακτικό εκπαιδευτικό
  tutorial με δημόσια datasets/code snippets. Indexed PDF preprocessing excerpts
  δείχνουν standardization/normalization· δεν χρησιμοποιούνται ως απόδειξη novelty gap.

Η normalized cross-correlation προς training mean και η diagonal Gaussian
template score χρησιμοποιούνται ως απλές baseline εκτιμήσεις, χωρίς ισχυρισμό ότι
επινοήθηκαν εδώ. Δεν εφαρμόζουν Scatter, DTW ή learned domain adaptation.

## Ελέγξιμο ερώτημα και όρια

Στο παγωμένο ASCADf/10k setup, πόση απόσταση χωρίζει δύο απλές trace-only εκτιμήσεις
από το known-shift control για second-order recovery; Πώς αλλάζει η απάντηση όταν
ένα position-wise scaler χρησιμοποιείται πριν αντί μετά τη μετατόπιση;
Η συγκεκριμένη paired ποσοτικοποίηση σε disjoint profiling confirmation είναι η
υπό εξέταση κατεύθυνση, όχι επιβεβαιωμένο ακάλυπτο βιβλιογραφικό κενό.

Για να στηρίξει πιθανή δημοσίευση, θα χρειαστεί ουσιαστικό αποτέλεσμα που αντέχει
σε κατάλληλες υπάρχουσες συγκρίσεις και ισχυρότερη ανεξάρτητη αξιολόγηση. Η same-key,
same-device confirmation και οι γνωστές baseline μέθοδοι από μόνες τους δεν αρκούν
για να ονομαστεί νέα τεχνική. Η κανονικοποίηση affine transport είναι μαθηματικός
έλεγχος υλοποίησης, όχι νέος αλγόριθμος cryptanalysis.

## Αναζήτηση και κενά

Queries: `"side channel" "feature-wise" "normalization" "shift" MinMax`,
`"side-channel" "second-order" "alignment" "profiling" 2025 2026`,
`"side-channel" "normalization" "desynchronization" data augmentation`,
`"side-channel" "normalization" "preprocessing" "MinMaxScaler"`,
`"side-channel" "alignment" "variance" template traces`,
`"side-channel" "normalization" "before" "shifting"`.

Οι μη πρωτογενείς aggregators/reposts δεν χρησιμοποιήθηκαν για συμπεράσματα.
Η αναζήτηση δεν ήταν systematic review ή πλήρες forward-citation search.
Δεν τεκμηριώθηκε απουσία ίδιου πειράματος από όλη τη βιβλιογραφία· δεν γίνεται novelty claim.

## Αποτελέσματα της διαδοχικής επέκτασης

Τρεις CPU φάσεις ολοκληρώθηκαν, με διαφορετικές confirmation pools και χωριστά
prospective plans. Η πρώτη surrogate σύγκριση είχε επιπλέον coordinate-domain
confound στο centering/scaling, που ελέγχθηκε στη δεύτερη φάση με normalized-domain
template/extraction. Αυτό είναι έλεγχος ορθής απόδοσης αποτελέσματος, όχι νέα τεχνική.
Το raw combined5 Gaussian20/20 και στα δύο παλιά ζεύγη στην πρώτη pool δεν διατηρήθηκε
στη δεύτερη:11/20 και20/20. Τα αποτελέσματα δεν επιλέγονται εκ των υστέρων.

Η τρίτη φάση επιλέγει δύο centered-product points από τα παρεχόμενα training
identity labels/HW, χωρίς training key/mask/share metadata. Σαρώνει211.575 pairs
με προπαγωμένους separation/diversity constraints και τρία matrix products.
Η αποτελεσματική matrix υλοποίηση και το supervised second-order selection
δεν παρουσιάζονται ως επινόηση. Νέα pool: Gaussian20/20 και18/20 στοraw±5/σ1,3
έναντιfixed0/20 και0/20, αλλάOOD±10/σ2,6 μόνο6/20 και0/20.

[Πλήρης αναφορά και όρια](../outputs/paper_extension_2026-10-05/REPORT_EL.md).
Το επόμενο literature work πρέπει να ελέγξει άμεσους υπάρχοντες aligners και
αν το ίδιο ειδικό protocol έχει ήδη καλυφθεί. Δεν επαληθεύτηκε ισχυρός συγκριτικός
baseline από Scatter/DTW ή independent-key/campaign replication. Οι παρούσες
φάσεις δεν αρκούν από μόνες τους για confirmed novelty ή paper acceptance.
