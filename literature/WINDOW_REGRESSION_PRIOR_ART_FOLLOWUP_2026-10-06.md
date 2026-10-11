# Πρόσθετος έλεγχος primary sources μετά το protocol freeze

Το frozen `WINDOW_REGRESSION_2026-10-06.md` διατηρείται αμετάβλητο μαζί με το
πειραματικό πλάνο. Η παρούσα ενημέρωση δεν αλλάζει κανένα parameter/criterion.

[Bishop primary PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/bishop-tikhonov-nc-95.pdf)
άνοιξε πλήρως: §2 εξισώσεις8–11,18–19 και §3. Ο συγγραφέας εφαρμόζει Taylor
expansion για small input-noise amplitude και διατηρεί όρους ως δεύτερη τάξη.
Η σύνδεση expected noisy loss/regularization και η γενίκευση πέρα από neural
networks είναι ρητές. Η δική μας disjoint bilinear derivation διατηρεί ακριβώς
τον σ⁴ term, αλλά αυτό από μόνο του δεν τεκμηριώνει πρωτοτυπία: οι polynomial
noise moments είναι στοιχειώδης υπολογισμός και απαιτείται έλεγχος μεταγενέστερης
βιβλιογραφίας για ίδια/ισοδύναμη regularizer σε SCA και γενική regression.

[Scheme-Aware Modeling metadata](https://eprint.iacr.org/2022/493)
προσπελάστηκε· το άνοιγμα του αντίστοιχου PDF μέσω web tool επέστρεψε internal
error. Δεν έχει ελεγχθεί η λεπτομερής συνάφεια με τα features της μελέτης.
Το publisher full text του orthogonal nonlinear regression25/3/505 επίσης δεν
προσπελάστηκε, ενώ το PMC endpoint ζήτησε captcha. Παραμένουν συγκεκριμένα
access/comparison gaps, όχι στοιχεία απουσίας prior art.

Publication claim χρειάζεται primary full-text comparison και διατύπωση γύρω
από το πραγματικό παρατηρημένο εύρημα, όχι γενικό «πρώτη noise-aware SCA».
