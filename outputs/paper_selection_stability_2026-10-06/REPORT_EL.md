# Σταθερότητα επιλογής σημείων — CPU phase10, 6/10/2026

Το συνολικό παγωμένο criterion δεν πέρασε.
Το frozen signal criterion πέρασε, ενώ το reselection sensitivity criterion δεν πέρασε.

## Σχεδιασμός

20 paired training bootstrap draws, seed2026, από τα ίδια αρχικά10k traces και labels. Κάθε draw έχει10k θέσεις με replacement, αλλά λιγότερες μοναδικές rows. Αυτά είναι conditional perturbation diagnostics, όχι νέα ανεξάρτητα training seeds, acquisitions ή αλλαγή του neural training budget.
Distinct training rows ανά draw: 6281–6417. Τα phase9 alignment template και training offsets διατηρήθηκαν ακριβώς. Μέσα σε κάθε draw υπολογίστηκαν νέο center, πλήρης επιλογή δύο pairs και point/box/rank1 weights/sign από training labels μόνο.
Full search:845.650 eligible pairs, margin25/separation50/diversity20, ίδιο radius5. Όλα τα20 sets και120 weight vectors αποθηκεύτηκαν πριν το πρώτο νέο confirmation read. Δεν επιλέχθηκε bootstrap winner, ensemble, consensus ή άλλη ρύθμιση.
Δύο νέα profiling20k pools, seeds20261018/19, με όλες τις110k προηγούμενες rows excluded. Clean και combined5 με το ίδιο raw Gaussian evaluation template για όλα τα frozen controls και resampled fits. Noise scale από original raw training median range48, κοινά U9101/Z9102 streams.
Frozen controls: raw oldpair1/2 και aligned selectedpair1/2, όλα τα point/box/rank1 features.528 rows=48 frozen-control coefficients+480 draw coefficients. Τα20 draws επαναχρησιμοποιούν το ίδιο αρχικό sample και κοινά confirmations· δεν είναι20 ανεξάρτητα πειράματα ή κλειδιά.
Joint primary: και οι δύο αρχικές aligned-selected rank1 families στο clean πρέπει να έχουν r≥0,05 και lower>0 σε αμφότερα pools/schemes. Επιπλέον, οι reselection rank1 coefficients και των δύο family ranks πρέπει να έχουν median≥0,05 και τουλάχιστον16/20positive draws σε αμφότερα pools. Η τελευταία απαίτηση είναι descriptive criterion, χωρίς binomial inference ή selection-error guarantee.
Πρόκειται για adaptive follow-up με νέο freeze. Το phase9 primary failure παραμένει. Καμία viewed confirmation ή attack row δεν χρησιμοποιήθηκε για refit, tuning ή επιλογή καλύτερου draw.

## Frozen signal — όλα τα intervals

9.999 paired-row και9.999 index-cluster draws ανά family/pool. Nominal99,875% two-sided percentile intervals, α0,01/family8/tail0,000625. Οι ακραίες quantiles αντιστοιχούν περίπου σε6,25draws, με Monte Carlo αβεβαιότητα. Conditional iid-row/cluster assumptions· HDF5 bins1000 δεν είναι verified acquisition-time blocks. Δεν υπάρχει across-phase alpha-spending ή γενική coverage εγγύηση.

| Pool / family / scheme | r | Lower | Upper | Criterion |
|---|---:|---:|---:|---|
| primary / aligned_selected_pair1 / paired_rows | 0.092582 | 0.069857 | 0.114048 | Πέρασε |
| primary / aligned_selected_pair1 / index_clusters | 0.092582 | 0.070777 | 0.114921 | Πέρασε |
| primary / aligned_selected_pair2 / paired_rows | 0.081028 | 0.058652 | 0.103391 | Πέρασε |
| primary / aligned_selected_pair2 / index_clusters | 0.081028 | 0.060218 | 0.101185 | Πέρασε |
| replication / aligned_selected_pair1 / paired_rows | 0.094329 | 0.072218 | 0.117443 | Πέρασε |
| replication / aligned_selected_pair1 / index_clusters | 0.094329 | 0.071823 | 0.116769 | Πέρασε |
| replication / aligned_selected_pair2 / paired_rows | 0.078217 | 0.055184 | 0.102346 | Πέρασε |
| replication / aligned_selected_pair2 / index_clusters | 0.078217 | 0.057646 | 0.099147 | Πέρασε |

## Reselection sensitivity — όλα τα summaries

| Pool / condition / family | Median r | Min r | Max r | Positive draws | Criterion |
|---|---:|---:|---:|---:|---|
| primary / clean / pair1 | 0.093343 | 0.084066 | 0.120109 | 20/20 | Πέρασε |
| primary / clean / pair2 | 0.012320 | -0.015691 | 0.113520 | 14/20 | Δεν πέρασε |
| primary / combined5 / pair1 | 0.075745 | 0.059321 | 0.115463 | 20/20 | Πέρασε |
| primary / combined5 / pair2 | 0.007491 | -0.017676 | 0.040159 | 14/20 | Δεν πέρασε |
| replication / clean / pair1 | 0.096207 | 0.081304 | 0.115429 | 20/20 | Πέρασε |
| replication / clean / pair2 | 0.003294 | -0.003755 | 0.113507 | 15/20 | Δεν πέρασε |
| replication / combined5 / pair1 | 0.075027 | 0.056284 | 0.108487 | 20/20 | Πέρασε |
| replication / combined5 / pair2 | 0.005130 | -0.008588 | 0.046072 | 18/20 | Δεν πέρασε |

![Signal across reselection fits](reselection_signal.png)

Το πρώτο family rank διατηρεί θετικό signal σε όλες τις επαναδειγματοληψίες εδώ. Το δεύτερο είναι ασθενές ή αρνητικό σε πολλές από αυτές, παρότι η αρχική συγκεκριμένη επιλογή έχει επαναλαμβανόμενο θετικό signal. Δεν αποδεικνύεται ότι το original pair είναι false positive, ούτε ότι όλη η αστάθεια προέρχεται από έναν συγκεκριμένο μηχανισμό.
Training resamples είναι conditional στα ήδη υπολογισμένα alignment parameters. Argmax selection είναι μη ομαλό statistic και τα20 draws είναι λίγα· δεν υποστηρίζονται asymptotic selection confidence ή unconditional data-population guarantees. Η μέθοδος δεν είναι formal stability selection.

## Σταθερότητα τοποθεσιών

Κοινές ανοχές5/20 samples, προκαθορισμένες από radius/diversity. Ordered hits μετρούν το ίδιο family rank· either-family hits επιτρέπουν αλλαγή σειράς. Δεν γίνεται consensus point selection.

| Tolerance | Ordered hits pair1 / pair2 | Either-family hits pair1 / pair2 | Median max distance pair1 / pair2 |
|---|---|---|---|
| 5 | 8/20 / 4/20 | 8/20 / 4/20 | 11.5 / 115.5 |
| 20 | 11/20 / 4/20 | 11/20 / 4/20 | 11.5 / 115.5 |

![Point locations](selection_locations.png)

## Κόστος, επαλήθευση και ερμηνεία

90tests passed/14existingwarnings σε15,10s (JUnit15.069s). CPU experiment221.581124s, fit25.277187s περιλαμβάνεται· independent verifier113.115777s.
Ο verifier επανέλαβε και τα20 full searches,120 weight vectors,40 selected training coefficients, όλα ταcenters/paired draw indices/location summaries.528confirmation coefficients/all products,79.992bootstrap draws,12actual-row cluster checks,176sampled offsets με batch boundaries, όλαsplits/RNG/time ordering/padding bounds/immutable hashes.
Δέκα paper CPU φάσεις:2596.295861s experimental wall time. Recovery summaries988/execution checks19.760/additional endpoint replays10.960 αμετάβλητα. Αυτή η φάση δεν διάβασε attacks/metadata/keys και δεν έκανε νέα CPA recovery.
Variable profiling150k πλέον viewed/50k unused· fixed profiling50k used. Variable attack10k viewed από παλιότερες φάσεις, original fixed attack locked. Οι νέες40k confirmation rows αποκλείονται από κάθε μελλοντικό unseen confirmation ή tuning. Παραμένουν1 Kaggle notebook/3GPUtrainings/failed gate/source/checkpoints.
Αυτό το αποτέλεσμα απομονώνει εμπειρικά τη διαφορά μεταξύ signal σε συγκεκριμένα frozen points και αξιοπιστίας του full-search selector υπό paired sample perturbations. Υποστηρίζει τη failure-analysis κατεύθυνση, όχι νέα επίθεση, superiority έναντι άλλου selector ή publication-ready novelty. Απαιτείται independent acquisition/key evidence και σύγκριση με prior-art selection methods.

[Plan](plan.json) · [Splits](splits.npz) · [Training access](training_access.json) · [Confirmation access](evaluation_access.json) · [All fits](fit.json) · [Fit arrays](fit.npz)
[Results](results.json) · [Arrays](arrays.npz) · [All528 coefficients](correlations.csv) · [All40 selected pairs](selected_points.csv) · [Tests](pytest.xml) · [Verification](verification.json) · [Evidence](evidence.json)
[Execution code](../../notebooks/paper_selection_stability.py) · [Independent verifier](../../notebooks/verify_selection_stability.py) · [Frozen source audit](../../literature/SELECTION_STABILITY_2026-10-06.md)
