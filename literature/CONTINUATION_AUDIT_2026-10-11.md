# Συμπληρωματικός έλεγχος prior art — 11/10/2026

Ο έλεγχος έγινε παράλληλα με την εγκεκριμένη combined εκπαίδευση, χωρίς αλλαγή
του frozen πρωτοκόλλου, μοντέλου ή endpoints. Δεν εκτελέστηκε author code.

Η [publisher HTML του Li–Perin](https://link.springer.com/article/10.1007/s13389-024-00363-3)
επιβεβαιώνει τη χωριστή μελέτη noise/desynchronization και αναφέρει combined
στρατηγικές ως μελλοντική εργασία. Αυτό αφορά εκείνο το paper· δεν αποδεικνύει
ότι απουσιάζει κάθε μεταγενέστερη joint μελέτη.

Η [publisher HTML του CL-SCCA](https://link.springer.com/article/10.1186/s42400-026-00658-4)
καταγράφει publication10October2026, Cybersecurity9/article232. Ελέγχθηκαν οι
ενότητες pretraining/data augmentation και references. Χρησιμοποιεί multi-byte
contrastive collision/key-difference recovery και random shift/crop/denoising.
Η σύγκριση threat model με τη δική μας supervised identity-byte ταξινόμηση είναι
δική μας αποτίμηση: δεν είναι matched baseline για το συγκεκριμένο Gaussian/shift
πείραμα. Παραμένει σχετικό prior art για combined μετασχηματισμούς και neural SCA.
Δεν υιοθετούνται αριθμητικά efficacy claims ούτε συγκρίνονται ασύμβατα trace counts.

Το bilinear πλήρες paper παραμένει access gap: η DOI και το συγκεκριμένο DBLP
record δεν ήταν προσβάσιμα με το web εργαλείο. Ο προηγούμενος
[code-only audit](BILINEAR_CODE_AUDIT_2026-10-11.md) παραμένει το επαληθευμένο scope.
Η [πανεπιστημιακή σελίδα συγγραφέα](https://www.cs.sjtu.edu.cn/jiaoshiml/caopei.html)
και το [author repository](https://github.com/loccs-cp/Bilinear-CNN-for-SCA)
επιβεβαιώνουν το bibliographic/repository context, όχι πλήρη ανάγνωση του paper.

Queries: scoped IACR Gaussian/augmentation2026, TCHES noise/desynchronization,
Springer combined/augmentation/noise. TCHES robots block διατηρείται ως κενό.
Η αναζήτηση δεν είναι exhaustive ή απουσία-απόδειξη. Δεν τεκμηριώθηκε novelty,
ούτε προστέθηκε νέο μοντέλο/seed/fit ή experimental comparator από τις πηγές.
