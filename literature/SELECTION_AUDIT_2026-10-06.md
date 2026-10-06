# Πηγές και όρια του point-selection audit — 6/10/2026

- [SciPy permutation_test documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html), ελεγμένο6/10/2026: pairing permutations για correlation, υπό τυχαία αντιστοίχιση/exchangeability. Για randomized tests περιγράφει τη συντηρητική προσθήκη1 σε αριθμητή και παρονομαστή. Η υλοποίηση εδώ είναι δική μας NumPy και δεν καλεί SciPy.
- Phipson και Smyth, [Permutation p-values should never be zero](https://arxiv.org/abs/1603.05766). Ελέγχθηκαν primary metadata/abstract, journal reference2010 και arXiv deposition2016. Δεν έγινε νέο πλήρες τεχνικό audit του άρθρου. Το +1 αποφεύγει μηδενικά Monte Carlo p-values· δεν αίρει τις υποθέσεις ανταλλαξιμότητας ή την αβεβαιότητα από περιορισμένες permutations.
- Fan, Zhou, Zhang και Feng, [How to Choose Interesting Points for Template Attacks?](https://eprint.iacr.org/2014/332). Ελέγχθηκαν primary abstract/metadata, υποβολή2014 και revision2015. Η επιλογή σημείων και η επίδρασή της στην ταξινόμηση έχουν προηγούμενα. Δεν αναπαράχθηκαν οι μέθοδοι/πίνακες τους και δεν τεκμηριώθηκε πλήρης επικάλυψη με το δικό μας second-order permutation audit.

Το training diagnostic χρησιμοποιεί maximum|r| σε όλο το αρχικό candidate domain
ανά shuffled-label matrix, όχι null μόνο στα προεπιλεγμένα σημεία. Είναι conditional
global-no-association diagnostic υπό exchangeable labels, όχι εκτίμηση της
πιθανότητας ότι ένα συγκεκριμένο pair είναι ψευδές ή proof strong FWER υπό partial
alternatives. Η υποχρεωτική επιλογή δεύτερου pair παραμένει αμετάβλητη.

Στη νέα disjoint confirmation τα τέσσερα pairs έχουν ήδη παγώσει και το direction
κλειδώθηκε από το ιστορικό training coefficient. Χρησιμοποιούνται τέσσερις signed
pairing-permutation tests με Bonferroni4×p, χωρίς επιλογή πλευράς ή pair από τη
confirmation. Υπό exchangeability αυτή η διόρθωση είναι συντηρητική· δεν ελέγχθηκε
stationarity κάθε φυσικής απόκτησης και δεν ισχυριζόμαστε unconditional security proof.

Τα99/999 randomized draws έχουν resolution0,01/0,001, ίδια streams στις δύο
καμπάνιες, όχι independent training seeds ή νέες φυσικές αποκτήσεις. Δεν δηλώνουμε
exact exhaustive permutation p-values, probability of null, causal overfitting,
νέα τεχνική, φυσική attack efficacy ή επαληθευμένη novelty για paper.
