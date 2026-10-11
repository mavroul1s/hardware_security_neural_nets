# Παράθυρα, regression και αναλυτικός θόρυβος — έλεγχος 6/10/2026

Η νέα CPU φάση είναι prospective comparison γνωστών οικογενειών μεθόδων.
Δεν έχει επιβεβαιωθεί πρωτοτυπία και δεν ισχυριζόμαστε νέα επίθεση από τη χρήση
averaging, SVD, ridge regression ή της ισοδυναμίας noise augmentation/regularization.

| Primary source | Τι ελέγχθηκε | Συνέπεια / όριο |
|---|---|---|
| [Won et al., Back To The Basics](https://eprint.iacr.org/2020/1134), [PDF](https://eprint.iacr.org/2020/1134.pdf) | Metadata και PDF §2.3: moving-average preprocessing για jitter, μειωμένη variance και προηγούμενη χρήση correlation/t-test | Local averaging γνωστό baseline, όχι novelty |
| [Wu & Picek, Remove Some Noise](https://eprint.iacr.org/2019/1474), [PDF](https://eprint.iacr.org/2019/1474.pdf) | Metadata και PDF §§2.4/3.2: fixed/random-key ASCAD, denoising με autoencoders, averaging/spectral references | Denoising/ASCAD robustness έχουν προηγούμενο. Δεν εκπαιδεύουμε autoencoder ή αναπαράγουμε το δικό τους protocol |
| [Thiebeauld et al., Second-order Scatter](https://eprint.iacr.org/2019/345.pdf) | PDF §§2.2,3.5,4: window integration, centering, dilution από non-leaking points, joint distributions | Η έννοια second-order windows και οι περιορισμοί centering γνωστοί. Δεν εφαρμόζουμε Scatter και δεν συγκρίνουμε τη δική μας bilinear regression σαν να ήταν Scatter |
| [Bishop, Training with Noise is Equivalent to Tikhonov Regularization](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/bishop-tikhonov-nc-95.pdf) | Primary author-hosted PDF abstract και publication metadata, Neural Computation7(1),1995,108–116 | Η γενική σύνδεση noise/regularization προϋπάρχει. Η συγκεκριμένη παρακάτω quadratic identity παράγεται ανεξάρτητα· δεν ισχυριζόμαστε first discovery |
| [Second-Order SCA Based on Orthogonal Transform Nonlinear Regression](https://www.mdpi.com/1099-4300/25/3/505) | Primary publisher search excerpt: orthogonal regression και παλιότερη ridge template analysis. Full publisher άνοιγμα failed, PMC captcha | Καταγράφεται άμεσο prior-art lead. Δεν ισχυριζόμαστε υπεροχή ή απουσία της συγκεκριμένης noise correction χωρίς πλήρη ανάγνωση |

Οι αναζητήσεις second-order/noise-aware/ridge δεν αποτελούν exhaustive novelty review.
Το IEEE άρθρο Dabosville/Doget/Prouff (2013, DOI10.1109/TC.2012.112) βρέθηκε
ως lead από secondary index· δεν χρησιμοποιείται για technical assertion πριν
ελεγχθεί primary full text. Scheme-aware modeling2022/493 επίσης παραμένει lead
που απαιτεί λεπτομερή σύγκριση πριν υποβολή.

## Συγκεκριμένη υπόθεση και ανεξάρτητη παραγωγή

Για disjoint centered windows A∈Rᵃ, B∈Rᵇ και product vector Pᵢⱼ=AᵢBⱼ,
προσθέτουμε ανεξάρτητο zero-mean iid noise ε,η με variance σ².
Η νέα product mean δεν αλλάζει. Η target covariance επίσης δεν αλλάζει, εφόσον
ο πρόσθετος θόρυβος είναι ανεξάρτητος από labels και τις παρατηρημένες training rows.
Η expected increment στην covariance του P είναι ακριβώς

`N = σ²(C_A ⊗ I_B + I_A ⊗ C_B) + σ⁴ I`.

Οι cross terms μηδενίζονται λόγω ανεξαρτησίας/disjoint windows. Δεν προϋποτίθεται
Gaussian distribution για την identity, αλλά το πείραμα χρησιμοποιεί Gaussian noise.
Έτσι η expected squared loss προσθέτει το quadratic penalty `wᵀNw`.
Η παραγωγή αφορά τεχνητό additive noise, conditional στις ήδη noisy training
μετρήσεις. Δεν εκτιμά native noise και δεν περιγράφει την effective noise distribution
μετά από noise-dependent επιλογή alignment offset. Τα synthetic Monte Carlo tests
ελέγχουν μόνο την identity και τον κώδικα, όχι physical attack efficacy.

Η αξιολόγηση συγκρίνει raw point, box product, diagonal product average,
rank1 target-covariance SVD και ridge clean/noise σε ένα προεπιλεγμένο radius5.
Το ίδιο standardized ridge penalty0,01 διατηρείται στα δύο ridge fits· δεν γίνεται
hyperparameter/radius search. Τα πάντα fit από το αρχικό training10k, χωρίς masks,
keys ή plaintext. Το υπάρχον attack failure δεν χρησιμοποιείται για επιλογή parameters.
Δύο unused profiling pools ανά campaign και fresh disjoint variable attack rows
παγώνουν πριν τα payloads. Το νέο attack χρησιμοποιεί το ήδη εξετασμένο κλειδί
της ίδιας καμπάνιας· δεν είναι νέο unseen key/device. Όλες οι μέθοδοι δημοσιεύονται,
είτε έχουν θετικό είτε αρνητικό αποτέλεσμα. Η πιθανή αξία για paper είναι μια
ελεγμένη μεθοδολογική/πειραματική συνεισφορά, η οποία μένει να αποδειχθεί.
