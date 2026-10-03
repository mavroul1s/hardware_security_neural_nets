# Kaggle: ενεργή μελέτη baseline/combined

Ένα ιδιωτικό notebook: https://www.kaggle.com/code/con1los/hw-sec-exp2.
Ένα ιδιωτικό Input: con1los/hardware-sca-resume.
Ο χρήστης εξουσιοδότησε API εκτέλεση και ενέκρινε νέα baseline/combined μελέτη.
Credentials και .venv-kaggle δεν ανεβαίνουν στα Inputs.

## Τρέχουσα έκδοση

RUN_TAG="minimal_v3_literature", STAGE="compare", model="cnn_literature".
16.952 parameters, train-only per-position MinMax,10k/5k,seed0,50epochs,batch128,
Adam LR0,001. Πρόκειται για προσαρμογή της reviewed μικρής αρχιτεκτονικής, όχι
ακριβή αναπαραγωγή των δημοσιευμένων45k/OneCycle/batch50 αποτελεσμάτων.

Το ίδιο Kaggle session εκπαιδεύει none50 και αξιολογεί το minimum-CE checkpoint.
Combined ξεκινά μόνο με clean validation SR@2000≥0,90 (18/20 permutations).
Αλλιώς παραλείπεται και εξάγεται το αρνητικό αποτέλεσμα. Δεν υπάρχει αυτόματο
hyperparameter search, ούτε single noise/shift training. Final attack παραμένει locked.

Έως4 full GPU trainings συνολικά μαζί με τα δύο διατηρημένα ReLU/Leaky failures.
Το προσωπικό GPU quota παραμένει άγνωστο· τα loop seconds δεν είναι session cost.
Το αρχικό Docker image/Tesla T4/Torch2.8.0+cu126/CUDA12.6 διατηρούνται.

## Πακέτο και checkpoints

Ενεργό Input: outputs/kaggle_resume_input_literature.zip.
Περιέχει whitelisted kaggle_project.zip, official ASCAD.h5 και provenance.
Για την εγκεκριμένη πρώτη εκτέλεση δεν περιέχει παλιό checkpoint και επιτρέπεται
ρητά fresh start. Μετά την ολοκλήρωση προστίθεται sca_runs_minimal_v3_literature.zip
και επανέρχεται require_checkpoint=True. Κάθε νέος session επαναφέρει αυτό το archive.
Η first cell υποστηρίζει και τα recursively extracted Kaggle ZIP layouts.

Ολοκληρωμένα none/combined checkpoints και οι ίδιες evaluations επαναχρησιμοποιούνται,
με config/data/source/environment fingerprints. Missing/conflicting checkpoint Input
ή αλλαγή source/runtime σταματούν τη συνέχεια. Δεν αλλάζουμε το pinned source κατά τα runs.
Το outputs/kaggle_first_cell.py αντιστοιχεί στην ενεργή first cell.

Τα παλιά packets kaggle_resume_input.zip και kaggle_resume_input_leaky.zip είναι
ιστορικά snapshots και δεν ταιριάζουν με το νέο source. Μην τα προσθέτεις μαζί.
Version3: ReLU epoch3→50. Version5: Leaky epoch0→50. Version6: QUICK_SAVE του Leaky,
χωρίς GPU εκτέλεση. Οι δύο ιστορικές εκπαιδεύσεις διατηρήθηκαν τοπικά και σε παλιές
private Input versions. Η νέα εκτέλεση καταγράφεται χωριστά στο execution status.

## Στάδια και περιορισμοί

benchmark:3 πρώτες epochs του none, μέρος των50. baseline:none50 μόνο.
compare:none50 και conditional combined. attack:μόνο evaluation μετά από πλήρη
δύο νέα runs, review/freeze και PROTOCOL_FROZEN=True. Δεν ενεργοποιείται τώρα.

Noise/shift εφαρμόζονται μετά το per-position MinMax. Πρόκειται για συγκεκριμένες
feature-space corruptions, όχι ισοδύναμη προσομοίωση raw physical jitter/noise.
Το zero padding αντιστοιχεί σε training minimum ανά output θέση.
Το ενεργό πλάνο εκτιμά none-versus-combined, χωρίς single-strategy attribution.

Μην τρέχεις scripts/prepare_kaggle.py: ο παλιός generator θα αντικαθιστούσε το
ενημερωμένο μοναδικό notebook. Το ενεργό notebook ενημερώνεται απευθείας.

Επίσημη τεκμηρίωση:
https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md
https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md
https://github.com/Kaggle/kaggle-cli/blob/main/docs/datasets.md
