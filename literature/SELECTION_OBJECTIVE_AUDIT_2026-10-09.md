# Επιλογή training στόχου και prior art — 9/10/2026

Το audit προηγήθηκε του phase11 freeze και των νέων confirmation payloads.
Ο άξονας είναι replication/benchmark/failure analysis. Δεν τεκμηριώνεται νέα μέθοδος.

## Claims που στηρίζονται και ερωτήματα που παραμένουν

| Claim | Αποτίμηση |
|---|---|
| Τα τρία CNN recipes απέτυχαν στο εγκεκριμένο budget/gate | Τεκμηριωμένο· δεν δοκιμάστηκε combined training |
| Window/box/rank1 robustness στο fixed campaign | Τεκμηριωμένο secondary αποτέλεσμα υπό συγκεκριμένες synthetic corruptions |
| Noise correction έναντι clean ridge | Positive conditional profiling replication phase8· phase7 global failure διατηρείται |
| Noise correction έναντι απλών controls | Υπεροχή δεν στηρίζεται |
| Τα phase9 frozen pairs έχουν clean signal | Επιβεβαιώθηκε phase10 σε δύο νέες pools |
| Ο point selector δίνει σταθερά δεύτερο useful family | Το phase10 joint criterion απέτυχε |
| Το original pair είναι false positive / απομονώθηκε causal failure | Δεν προκύπτει από το reselection failure |
| Profiling r σημαίνει αξιόπιστη key recovery | Δεν προκύπτει· variable attack criterion απέτυχε, διαφορετικός στόχος/κατανομή |
| Paper novelty / cross-device efficacy | Ανοικτά· χρειάζεται independently acquired actual-key evidence |

## Πρωτογενείς συγκρίσεις

**Durvaux et al., COSADE2015, Efficient Selection of Time Samples for Higher-Order
DPA with Projection Pursuits.** Διαβάστηκαν introduction και window-search
sections στο [author university PDF](https://research.dial.uclouvain.be/bitstreams/6343c079-4c42-44e0-90cf-d9c271b1eee2/download).
Η επιλογή projections/windows με higher-order objective έχει ήδη προηγούμενο.
Η δική μας πλήρης search centered box products με fixed width11 δεν αναπαράγει
το heuristic projection-pursuit algorithm. Η συνάφεια στηρίζει matched-objective
control, όχι novelty. Δεν εντοπίστηκε/εκτελέστηκε author implementation σε αυτό το audit.

**Perin, Wu, Picek, TCHES2022(4),828–861**, DOI
[10.46586/tches.v2022.i4.828-861](https://doi.org/10.46586/tches.v2022.i4.828-861).
Διαβάστηκαν §§2–4 και NOPOI resampling στα
[published university PDF](https://pure.tudelft.nl/ws/portalfiles/portal/131308710/document.pdf).
Window averaging/overlap και leakage dilution–misalignment tradeoff έχουν
μελετηθεί. Εκεί υπάρχουν διαφορετικά raw intervals, budgets και neural search.
Το paper δείχνει [author repository](https://github.com/AISyLab/feature_selection_dlsca),
που καταγράφεται ως διαθέσιμο link· individual code δεν επιθεωρήθηκε εδώ.
Δεν εισάγονται τα neural models ή η parameter search στη δική μας CPU φάση.

**Lomné, Prouff, Rivain, Roche, Thillard, CHES2014, How to Estimate the Success
Rate of Higher-Order Side-Channel Attacks.** Διαβάστηκαν ορισμοί/μεθοδολογία
στο [IACR proceedings PDF](https://www.iacr.org/archive/ches2014/87310195/87310195.pdf).
Η εκτίμηση recovery εξαρτάται από τη joint score distribution/competitors και
υποθέσεις leakage, όχι από μία scalar target correlation μόνο. Δεν εφαρμόσαμε
το θεωρητικό Gaussian estimator στα ASCAD δεδομένα ούτε ισχυριζόμαστε ότι οι
υποθέσεις του ελέγχθηκαν. Στη δική μας μελέτη το r endpoint και το πραγματικό SR
διατηρούνται διακριτά, χωρίς κατασκευασμένο fixed-key attack από varying labels.

**Meinshausen–Bühlmann, Stability Selection**, primary
[arXiv record](https://arxiv.org/abs/0809.2932), published DOI
[10.1111/j.1467-9868.2010.00740.x](https://doi.org/10.1111/j.1467-9868.2010.00740.x).
Το abstract επιβεβαιώνει διαφορετικό framework με error-control claims· university
PDF access απέτυχε. Δεν μεταφέρουμε αυτές τις εγγυήσεις στα20 paired bootstrap
draws. Εδώ δεν κατασκευάζουμε consensus selector ή formal selection-error bound.

## Πρόσβαση σε notation και author code

**Jiang–Ding, Entropy2023,25(3),505**, DOI
[10.3390/e25030505](https://doi.org/10.3390/e25030505).
Το web publisher επέστρεψε429 και PMC challenge. Η κανονική λήψη του
[EuropePMC full-text XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10048069/fullTextXML)
πέτυχε:182577bytes, SHA256
`c9828bbc0e983e409c66be7002089baee9d98c99adb0af32dde49f167458e700`.
Διαβάστηκαν §§2–4/Algorithm1 και XML MathML15–18. Το Algorithm1 συνδυάζει
eight-bit HD predictors, intercept, eigenvector projection και squared centered
trace responses. Δεν ορίζει component-retention tolerance· η notation αW/AI
δεν καθορίζει πλήρως multi-output penalty dimensions. Matching centering γράφεται
στο matching set. Author code link δεν βρέθηκε στο XML ή στις δύο targeted
title/author/code searches, χωρίς συμπέρασμα ανυπαρξίας κώδικα. Το full-text access
gap έκλεισε για XML, όχι για visually checked PDF ή matched reproduction.
Η rank-invariance παρατήρηση παραμένει conditional σε full rotation· δεν αποδίδεται
implementation defect χωρίς retention rule. Το προηγούμενο8/10 audit διατηρείται.

**Masure et al., Scheme-Aware Architectures**, DOI
[10.46586/tches.v2023.i1.32-59](https://doi.org/10.46586/tches.v2023.i1.32-59).
Στο [author repository](https://github.com/uclcrypto/Scheme-Aware-Architectures)
πάγωσε commit `39add3742576c7add6cd87477f05e87dc5c75a31`.
Επιθεωρήθηκαν `models.py` recombination/ASCADNet, simulation class και experiment
entrypoints. GroupRecombine χρησιμοποιεί Boolean Walsh–Hadamard ή arithmetic FFT,
με branch outputs και επιλογή probability normalization. ASCADNet καλεί CNN
branches και Boolean recombination· το simulation.ASCAD αφορά affine synthetic
leakage, όχι loader του real variable1400 campaign. Το tree έχει simulation
entrypoints, χωρίς real-ASCAD training entrypoint. Αυτό περιορίζει την διαθέσιμη
αναπαραγωγή, δεν αμφισβητεί τα δημοσιευμένα αποτελέσματα. Κανένα τρίτο-party αρχείο
δεν εισήχθη ως executable dependency ή εκτελέστηκε. Individual CUDA kernel και
ολόκληρο repository δεν αποτελούν audited implementation. Saved hashes/access
metadata: `outputs/paper_window_selection_2026-10-09/literature_access.json`.

Επιπλέον backward leads: regression Sugawara et al.2010 και ridge references της
Jiang–Ding· forward leads: scheme-aware paper και Perin2022 από το σχετικό
higher-order/profiling corpus. Targeted search, όχι systematic citation census.
Missing code/PDF και μη αναγνωσμένα references παραμένουν unknowns. Το γνωστό
noise–regularization prior art της8/10 διατηρείται· δεν απαιτείται νέο algebra claim.

## Τρεις διαψεύσιμες υποθέσεις και επιλογή

1. **H1, primary:** η ασυμφωνία point-selection/box-extraction αποτελεί έναν
   ελέγξιμο περιορισμό. Στα ίδια20 phase10 paired draws, selection βάσει centered
   window-mean προϊόντων θα βελτιώσει τη median paired clean correlation του
   δεύτερου box family κατά≥0,02 σε δύο νέες pools· median≥0,05,≥16/20positive,
   και first-family median paired loss≤0,01. Αν οποιαδήποτε απαίτηση αποτύχει,
   το criterion αποτυγχάνει. Positive αποτέλεσμα αφορά αυτή τη bounded intervention,
   όχι αποκλειστική causal εξήγηση ή ανεξαρτησία δεύτερης leakage family.
2. **H2, secondary:** οι internal out-of-bag medians του δεύτερου box/rank1
   family προβλέπουν fresh clean medians εντός0,02 και συμφωνούν στο threshold0,05
   για both selectors/both pools. Τα OOB labels δεν συμμετέχουν στο draw fit,
   αλλά οι traces συνέβαλαν στο αρχικό unlabeled preprocessing· conditional
   diagnostic, όχι ανεξάρτητο test ή νέα μέθοδος επιλογής.
3. **H3, deferred:** ακόμη και σταθερή profiling median≥0,05 δεν εγγυάται
   unknown-key SR≥18/20 στα2.000. Η προοπτική διάψευση απαιτεί παγωμένη μέθοδο
   και independently acquired actual-key pool. Δεν χρησιμοποιούνται viewed attacks
   ούτε μετατρέπονται varying-label profiling rows σε τεχνητή «key recovery».

Επιλέγεται H1 με H2 diagnostic: αλλάζει μόνο το training-only selection objective
σε matched pipeline. Δεν επιλέγονται neighborhoods από phase10 winners/locations,
code-informed regions, νέα widths ή alignment παράμετροι. Radius5 και όλα τα draws
είναι ήδη frozen historical controls. Κόστος αναμενόμενα λίγα CPU λεπτά, cap600s
experiment, μία εκτέλεση. Δύο10000-row confirmations, unions όλωνphase10splits και
αναδρομικός έλεγχος provenance150k. Παραμένουν30000unused· stop χωρίς νέο trial
ή adaptation, όποιο και αν είναι το outcome. Πλήρες machine-readable plan/hash
και fits πριν οποιοδήποτε νέο payload. Το paper παραμένει υπό αποτίμηση.
