# Bilinear CNN — περιορισμένος έλεγχος πρωτογενών πηγών, 11/10/2026

Η [πανεπιστημιακή σελίδα του συγγραφέα](https://www.cs.sjtu.edu.cn/jiaoshiml/caopei.html)
καταγράφει Cao et al., *Improving Deep Learning Based Second-Order Side-Channel
Analysis With Bilinear CNN*, IEEE TIFS 17, 3863–3876 (2022).
Η DOI 10.1109/TIFS.2022.3216959 δεν ήταν προσβάσιμη με το εργαλείο περιήγησης.
Δεν επιβεβαιώθηκαν οι πλήρεις ενότητες του paper ή οι αριθμητικές claims του.

Το [repository των συγγραφέων](https://github.com/loccs-cp/Bilinear-CNN-for-SCA)
περιγράφει ενσωματωμένα προϊόντα διαρροής και layer-wise correlation.
Επιθεωρήθηκε μόνο ο κώδικας του [fixed-key notebook σε συγκεκριμένο commit](https://github.com/loccs-cp/Bilinear-CNN-for-SCA/blob/06a674afd25d51df4cd0d2f4b52cb33a36052e3f/ASCAD_fixed_key/ASCAD_fixed_key.ipynb).
Δεν εκτελέστηκε ο κώδικας, δεν λήφθηκαν traces/weights και δεν εξετάστηκαν τα outputs.

Ο encoder παράγει δέκα χαρακτηριστικά, σχηματίζει self outer product μέσω
`torch.bmm` και ταξινομεί τις εκατό συνιστώσες. Ρυθμίσεις: identity256, 700samples,
45k/5k, batch200, 50epochs, Adam και OneCycleLR max0,01. Ο κώδικας κάνει
StandardScaler και MinMax fit στο `X_train` πριν από την τομή train/validation.
Το σχήμα δείχνει πιθανή συμμετοχή validation στο fit· δεν ελέγχθηκε το ίδιο το array.
Η δική μας baseline χρησιμοποιεί χωριστό train-only fit, διαφορετική αρχιτεκτονική
και batch50/cycle0,005. Δεν είναι matched B-CNN replication.

Συμπέρασμα του ελέγχου: η γενική ιδέα neural product combinations έχει άμεσο
prior art. Αυτό δεν εξηγεί αιτιακά τις δικές μας αποτυχίες και δεν αποτελεί νέα
πειραματική σύγκριση. Χρειάζεται full-text πρόσβαση πριν από ακριβείς ισχυρισμούς
για το δημοσιευμένο πρωτόκολλο. Δεν προστίθεται neural model ή training στο scope.

Commit: `06a674afd25d51df4cd0d2f4b52cb33a36052e3f`. Τοπικό access/hash record:
`runs/literature/bilinear_2026-10-11/access.json` (ignored).
