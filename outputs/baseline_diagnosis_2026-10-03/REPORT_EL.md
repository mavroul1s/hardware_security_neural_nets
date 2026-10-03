# Διάγνωση του baseline — 2026-10-03

Πραγματοποιήθηκε read-only έλεγχος σε CPU, χωρίς νέα εκπαίδευση, optimizer step
ή αξιολόγηση στο final attack set. Ο υπάρχων training κώδικας και τα checkpoints
παρέμειναν ανέπαφα. Τα scripts βρίσκονται στο `notebooks/`, εκτός του training fingerprint.

## Έλεγχοι δεδομένων και pipeline

Το αρχείο συμφωνεί με το official checksum. Και τα 50.000 profiling labels
συμφωνούν με `SBOX(plaintext[2] xor key[2])`. Τα training/validation indices
συμφωνούν ακριβώς με τα saved splits, χωρίς overlap. Ο normalizer συμφωνεί
με το manifest και δίνει training mean περίπου0 / std1. Όλες οι 256 κλάσεις
υπάρχουν στο training subset, με22–56 παραδείγματα ανά κλάση.

Οι παράμετροι είναι finite. Το Adam state έχει158 steps για τον best checkpoint
και3.950 για τον last, σε όλες τις παραμέτρους. Τα CPU validation CE/accuracy
αναπαράγουν τα GPU αποτελέσματα με τις αναμενόμενες αριθμητικές αποκλίσεις.
Δεν εντοπίστηκε σφάλμα στα παραπάνω ελεγχόμενα μέρη του pipeline.

## Ενδείξεις αποτυχίας μάθησης

| Έλεγχος | Best, epoch2 | Last, epoch50 |
|---|---:|---:|
| Validation CE | 5,547229 | 5,616101 |
| CE με μία σταθερή τυχαία permutation των validation labels | 5,547203 | 5,611338 |
| Validation accuracy | 0,34% | 0,32% |
| Dense ReLU units που δεν ενεργοποιήθηκαν σε κανένα validation trace | 48/64 | 53/64 |
| Conv2 ReLU channels που δεν ενεργοποιήθηκαν στο validation | 3/16 | 12/16 |

Στη σταθερή permutation των labels, η CE είναι σχεδόν ίδια ή καλύτερη· αυτό αποτελεί
diagnostic control και όχι confidence interval ή απόδειξη πλήρους ανεξαρτησίας.
Το τελευταίο checkpoint βελτιώνει το training αλλά χειροτερεύει στο validation.
Η uniform CE είναι5,545177. Το train-prior-only control έχει train CE5,532561
και validation CE5,557023. Το καλύτερο δίκτυο δεν ξεπερνά την uniform CE στο validation.

Η αδράνεια των ReLU είναι ισχυρή ένδειξη περιορισμού της ενεργού χωρητικότητας.
Δεν έχει αποδειχθεί ότι αποτελεί τη μοναδική αιτία της αποτυχίας· το masked target,
το μικρό data budget και οι optimization επιλογές παραμένουν πιθανοί παράγοντες.

## Συγκεκριμένη υποψήφια διόρθωση

Προετοιμάστηκε το `notebooks/candidate_cnn.py`: αντικαθιστά μόνο τις τρεις ReLU
με `LeakyReLU(negative_slope=0.1)`. Διατηρεί ακριβώς τις διαστάσεις και τις197.424
παραμέτρους. Η αρνητική κλίση επιτρέπει gradient και στην αρνητική περιοχή,
όπως ορίζει η [τεκμηρίωση PyTorch2.8](https://docs.pytorch.org/docs/2.8/generated/torch.nn.LeakyReLU.html).

Σε fixed-weight probe με τον δικό μας epoch50 checkpoint και128 training traces,
ο υπάρχων dense layer είχε53/64 units με μηδενικό weight gradient. Η υποψήφια
έκδοση είχε0/64. Δεν έγινε optimizer step και το checkpoint checksum έμεινε ίδιο.
Αυτό ελέγχει τον μηχανισμό gradient· δεν αποδεικνύει καλύτερη generalization ή key recovery.

Δεν τεκμηριώνεται ότι χρειαζόμαστε απλώς μεγαλύτερο CNN: ο
[επίσημος ASCAD CNN](https://github.com/ANSSI-FR/ASCAD/blob/master/ASCAD_train_models.py)
είναι διαφορετικός, αλλά ο [author code μικρού CNN για ASCAD](https://github.com/gabzai/Methodology-for-efficient-CNN-architectures-in-SCA/blob/master/ASCAD/N0%3D0/cnn_architecture.py)
χρησιμοποιεί επίσης μικρή αρχιτεκτονική με SELU/BatchNorm και διαφορετική
normalization/LR policy. Πρόκειται για πηγές σύγκρισης, όχι αναπαραγωγή των δικών τους αποτελεσμάτων.

## Επιλογή επόμενης εκτέλεσης

Η προτεινόμενη επιλογή είναι **μία διορθωτική baseline εκπαίδευση** από την αρχή,
με LeakyReLU και ίδιο seed0,10k/5k split, normalization, Adam LR0,001, batch128 και50 epochs.
Δεν αλλάζουμε ταυτόχρονα architecture size, data budget, LR ή epoch count.
Το προηγούμενο run διατηρείται ως αποτυχημένο baseline. Αν η νέα έκδοση δώσει χρήσιμο
validation σήμα, οι τρεις augmentations θα συγκριθούν με την ίδια νέα έκδοση.

Αυτό προσθέτει μία εκπαίδευση: **έως5 συνολικά**, δηλαδή1 παλιό baseline +4 τελικά
μοντέλα, με ένα notebook. Αν αποτύχει και το διορθωμένο baseline, σταματάμε για νέα
διάγνωση πριν τις augmentations, χωρίς αυτόματη αναζήτηση hyperparameters.
Εναλλακτικά, εκτελούνται μόνο οι ήδη προγραμματισμένες3 augmentations του παλιού CNN,
με σύνολο4 trainings και με την αδράνεια τεκμηριωμένη ως περιορισμό.

Το [AGENTS.md](../../AGENTS.md) ορίζει:
“Additional budgets, models or seeds require a research reason and user agreement.”
Η διάγνωση δίνει τον research reason· η μία πρόσθετη εκπαίδευση χρειάζεται την επιλογή του χρήστη.

Αρχεία: `diagnosis.json`, `candidate_gradient_probe.json` και `proposal.json`.
