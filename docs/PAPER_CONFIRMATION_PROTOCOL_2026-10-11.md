# Επόμενη φάση: μία combined45k και κλειδωμένη attack αξιολόγηση

Κατάσταση: συγκεκριμένη πρόταση προς έγκριση, όχι εξουσιοδότηση εκτέλεσης.
Η εντολή «συνέχισε με ό,τι χρειαστεί» επιτρέπει προετοιμασία και ελέγχους.
Το AGENTS.md κρατά cap5 και κλειστό το original fixed-key attack· απαιτείται
συγκεκριμένη συμφωνία για μία έκτη εκπαίδευση και την παρακάτω τελική αξιολόγηση.

## Ερευνητικό ερώτημα και σειρά

Η baseline45k πέρασε το προκαθορισμένο clean validation gate20/20. Αυτό επιτρέπει
να προταθεί η μία combined σύγκριση του αρχικού minimal study, με λειτουργική
baseline. Η τελική attack αξιολόγηση αφορά αθέατες traces της ίδιας fixed-key
καμπάνιας. Δεν αποτελεί νέο κλειδί, συσκευή ή ανεξάρτητη acquisition replication.

Κλειδώνουμε τώρα μοντέλο, split, κανονικοποίηση, augmentation, epochs, schedule,
checkpoints και όλα τα endpoints. Εκπαιδεύεται πρώτα η combined, επιλέγεται μόνο
minimum clean validation CE, επαληθεύεται και κλειδώνεται το checkpoint της.
Έπειτα ανοίγει μία φορά το attack10k για ΟΛΕΣ τις προαποφασισμένες συγκρίσεις.
Η σειρά αποκλείει χρήση baseline attack αποτελεσμάτων για επιλογή combined recipe.
Το αποτέλεσμα attack δεν ενεργοποιεί άλλη εκπαίδευση ή επαναρύθμιση.

## Μία πρόσθετη combined εκπαίδευση

- Επαναχρησιμοποιείται το ολοκληρωμένο baseline45k checkpoint epoch21, SHA256
  `d3e4a19d9696b39d8a5a881275023ff4ef0de8bdf8031425b0d7617b8bd0c557`.
- Ίδιο CNN16952, seed0, original split_seed2026,45k/5k,50epochs,batch50.
  Ίδιος author linear LR cycle: update knots0/18000/36000/45000 και rates
  0,0005/0,005/0,0005/0,000005, ίδια45000updates/2250000exposures.
- Ίδιο training-only feature MinMax, ακριβώς ίδια training/validation indices.
  Ίδια seed initialization και ανεξάρτητος shuffle generator του trainer.
- Η μόνη training recipe αλλαγή είναι η ήδη καθορισμένη combined στρατηγική:
  shifts uniform από−5 έως+5, zero padding, κατόπιν Gaussian noiseσ0,1.
  Εφαρμόζεται μετά το MinMax, χωρίς clipping ή domain-order search.
- Ένα training στο ίδιο private `nmavros/hw-sec-exp2`, ίδιο pinnedT4/image/Input.
  Το frozen baseline reference ενσωματώνεται ως επαληθευμένα bytes στο notebook·
  δεν αλλάζει το αρχικό private dataset ή Input packet.
- Cap5→6. Μία υποβολή, session1800s/training-loop900s, χωρίς benchmark retraining,
  seed/model/budget search, single noise/shift trainings ή automatic retry.
  Οποιοδήποτε partial/hash/nonfinite failure διατηρείται και σταματά τη φάση.

## Προκαθορισμένη τελική αξιολόγηση

Η αξιολόγηση γίνεται τοπικά σε CPU με τα δύο κλειδωμένα checkpoints, χωρίς optimizer.
Επίσημο ASCAD fixed-key700, byte2/identity256, πλήρες original attack pool10000.
Ο έλεγχος constant target-key/labels γίνεται μόνο τότε. Metadata/key χρησιμοποιούνται
μόνο στο ranking· μοντέλο inputs=traces. Καμία χρήση attack labels για fit/selection.

Επαναχρησιμοποιείται το υπάρχον `configs/evaluation_final.json`: budget2000,
100orders/seed8001, corruption_seed9001, batch256, threshold0,90, conservative ties,
rank0best. Οι100orders είναι conditional σε ένα pool/κλειδί και δεν είναι100
ανεξάρτητα trainings/keys/acquisitions. Ίδιες corrupted inputs και orders στα δύο μοντέλα.

| Condition | Noiseσ | Shift± |
|---|---:|---:|
| clean |0 |0 |
| noise_matched |0,1 |0 |
| shift_matched |0 |5 |
| combined_matched |0,1 |5 |
| combined_mild |0,05 |2 |
| combined_noise_ood |0,2 |5 |
| combined_shift_ood |0,1 |10 |
| combined_both_ood |0,2 |10 |

Όλες οι συνθήκες υπήρχαν πριν την attack πρόσβαση. Οι αλλοιώσεις είναι συνθετικές
σε πραγματικές traces, όχι νέα φυσικά αποκτημένη misalignment/noise καμπάνια.

H1 confirmation: frozen baseline clean SR@2000≥0,90. Αναφέρεται αυτοτελώς, μαζί
με όλες τις αποτυχίες και GE/sustainedSR. Δεν επιλέγεται νέο checkpoint από attack.

H2 augmentation primary: `combined_both_ood`, με τρία ταυτόχρονα κριτήρια:
combined SR@2000≥0,90, strictlypositive paired ΔSR έναντι baseline, και combined
cleanSR@2000≥0,90. Αν αποτύχει οποιοδήποτε, το joint criterion απέτυχε.
Δεν αλλάζει το primary σε matched/mild συνθήκη εκ των υστέρων.

Όλα τα υπόλοιπα contrasts/GE/sustainedSR και paired success discordances είναι
descriptive secondary. Διατηρούνται όλες οι100σειρές/8συνθήκες/2μοντέλα, predictions,
RNG/orders/input hashes, rank curves και τα censoring/failure records.
Δεν χρησιμοποιούνται independent Bernoulli CIs ή p-values για τις επικαλυπτόμενες σειρές.

## Επαλήθευση, κόστος και διατήρηση

Πριν έγκριση: synthetic CPU smoke, checkpoint/split/scaler και byte-transport
checks. Πριν εκτέλεση: immutable plan με code/protocol/test/artifact hashes και
χωριστό authorization record που αναφέρεται στο plan hash.
Μετά training:45000LRvalues,50epochs/minimumCE, ίδιοsplit/scaler, CPU/GPU inference.
Μετά attack: ανεξάρτητος replay όλων των rank prefixes από saved predictions,
paired comparisons και endpoints. CPU evaluation cap600s· όχι κόστος που μετρήθηκε ήδη.

Διατηρούνται τα πέντε trainings και τα δύο attempt histories, original source,
canonical notebook, dataset packet και παλιά checkpoints. Variableprofiling30k
παραμένουν unused και variableattack10k unchanged. Κανένα νέο profiling confirmation.
Μετά ολοκλήρωση: report/manuscript/coursework, ίδια notebook source με QUICK_SAVE
χωρίς run. Total6/cap6 exhausted. Επόμενο πείραμα χρειάζεται διαφορετική υπόθεση
και νέα συμφωνία· κανένα recovery/novelty/publication claim δεν προεξοφλείται.
