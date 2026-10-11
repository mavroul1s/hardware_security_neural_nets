# Μεγαλύτερη prospective επιβεβαίωση χωρίς νέο fit — 6/10/2026

Το προκαθορισμένο phase8 criterion πέρασε και στα δύο νέα variable-key profiling20k pools.
Τα βάρη/radius/points/normalization/σ/methods παρέμειναν ακριβώς ίδια μεphase7. Το παλιότερο primary failure και το χαμηλό attack SR δεν αλλάζουν.

## Σχεδιασμός και ερμηνεία

Η follow-up φάση σχεδιάστηκε μετά τα θετικά αλλά imprecise profiling contrasts τηςphase7. Αιτία ήταν η εκτίμηση precision, όχι επιλογή μοντέλου/υπερπαραμέτρων από attack αποτελέσματα.
Δύο20k pools, seeds20261014/15, από unused variable profiling rows, disjoint από κάθε παλιότερη training/validation/confirmation row. Το training budget παραμένει10k· δεν έγινε refit ή νέο model seed.
Κάθε νέο plan/split/hash πάγωσε πριν payload access. Κανένα metadata/attack/key read σε αυτή τη φάση. Same provided HW labels μόνο για evaluation της signed correlation.
Primary pair1/combined5/Gaussian: Δr noise ridge−clean≥0,01 και positive lower bound και στα δύο pools, υπό αμφότερα bootstrap schemes. Τα υπόλοιπα360 rows δημοσιεύονται ως controls/descriptive evidence.
9.999 paired-row και9.999 paired-cluster draws ανά pool. Clusters=200 bins των1.000 συνεχόμενων HDF5 profiling indices· επιλεγμένες rows≈100 ανά bin. Resampling whole index bins, unequal counts retained μέσω sufficient moments.
Two-sided percentile99,75% intervals: nominalα0,01/family4/tail0,00125. Conditional στη fixed fitted direction/realized corruption, με iid-row ή iid-index-cluster assumptions. Δεν ελέγχθηκε η πραγματική acquisition-time αντιστοίχιση ή η ανεξαρτησία blocks.
Η επιλογή μεγαλύτερου follow-up μετά τα προηγούμενα CI είναι adaptive study planning. Δεν διατηρήθηκε προκαθορισμένο συνολικό alpha-spending για όλη την ερευνητική ακολουθία· δεν ισχυριζόμαστε overall optional-stopping-controlled significance. Τοphase7primary παραμένειfailed.

## Όλα τα prospective intervals

| Pool / scheme | Δr | Lower | Upper | Criterion |
|---|---:|---:|---:|---|
| primary / paired_rows | 0.041891 | 0.018122 | 0.064650 | Πέρασε |
| primary / index_clusters | 0.041891 | 0.020496 | 0.064878 | Πέρασε |
| replication / paired_rows | 0.051852 | 0.029698 | 0.074123 | Πέρασε |
| replication / index_clusters | 0.051852 | 0.030005 | 0.073925 | Πέρασε |

![Intervals](precision_intervals.png)

## Τα απλά controls διατηρούνται

Pair1/combined5/Gaussian, signed HW correlation:

| Pool | Σημείο | Box | Diagonal | Rank1 | Ridge clean | Ridge noise |
|---|---:|---:|---:|---:|---:|---:|
| primary | 0.035736 | 0.076518 | 0.051349 | 0.086685 | 0.018872 | 0.060763 |
| replication | 0.031059 | 0.075836 | 0.052272 | 0.086388 | 0.010942 | 0.062794 |

Η noise correction βελτιώνει την clean ridge, αλλά box averaging καιrank1 παραμένουν ισχυρότερα εδώ. Δεν αποδείχθηκε superiority της προτεινόμενης correction έναντι φθηνότερων baselines.
Τα πραγματικά variable attack αποτελέσματα τηςphase7 παραμένουν3/20 γιαnoise ridge και4/20 γιαrank1 στοcombined5/pair1, με18/20 criterionfailed. Αυτή η φάση μετρά profiling signal, όχι νέο key recovery. Καλύτερη συσχέτιση δεν ισοδυναμεί με αξιόπιστη ανάκτηση μέσα στοbudget2.000.
Same campaign, original training και shared RNG streams· disjoint row pools δεν είναι νέες συσκευές/κλειδιά ή ανεξάρτητες acquisition campaigns. Δεν ελέγχεται causal key-change effect. Τα νέα40k rows είναι πλέον viewed evidence, αποκλείονται από future unseen confirmation/tuning.

## Επαλήθευση, κόστος και συνέχεια προς paper

82tests passed/14existingwarnings· JUnit22.163s. Phase8 CPU252.684873s, independent verifier88.282784s.
Verifier:360corr rows/all products,39.996bootstrap draws,6sampled cluster draws με actual duplicated row lists,720sampled alignment offsets με batch-boundary checks, όλα τα moments/splits/RNG και immutable weights.
Οκτώ paper CPU φάσεις:2142.197628s experimental wall time. Recovery summaries988/executionendpoints19.760/additionalreplays10.960 δεν αυξάνονται από αυτή τη profiling-only φάση. Οι νέες δύοφάσεις προσθέτουν1.260correlation comparisons και540recovery summaries, όχι ανεξάρτητα κλειδιά/συσκευές.
Παραμένουν1 Kaggle notebook/3GPU trainings/failed CNN gate/source/checkpoints. Fixed profiling50k used, variableprofiling70k used/130k unused· variableattack10k viewed απόphase5/7, originalfixedattacklocked.
Η υποψήφια συνεισφορά περιορίζεται σε prospectively replicated robustness/failure boundaries και reproducible analytical baseline. Averaging, regression και input-noise regularization είναι γνωστά. Απαιτείται full-text novelty comparison και independently acquired/key evidence πριν publication claim.

[Plan](plan.json) · [Splits](splits.npz) · [Access](evaluation_access.json) · [Results](results.json) · [Arrays](arrays.npz) · [All CSV rows](correlations.csv)
[Tests](pytest.xml) · [Verification](verification.json) · [Evidence](evidence.json) · [Phase7 με όλα τα recovery failures](../paper_window_regression_2026-10-06/REPORT_EL.md)
[Execution code](../../notebooks/paper_precision_replication.py) · [Independent verifier](../../notebooks/verify_precision_replication.py) · [Primary bibliography](../../literature/WINDOW_REGRESSION_2026-10-06.md)
