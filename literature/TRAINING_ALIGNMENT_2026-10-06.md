# Training-side alignment — primary-source audit, 2026-10-06

This note is frozen with phase9 before new confirmation payloads. It supports a
controlled preprocessing experiment, not an originality claim.

- [Official ANSSI variable-key ASCAD description](https://github.com/ANSSI-FR/ASCAD/blob/master/ATMEGA_AES_v1/ATM_AES_v1_variable_key/Readme.md),
  accessed 2026-10-06: original acquisitions are unsynchronized; original extracted
  database has 1400 samples and differs from additional synthetic desync50/100 files.
  This motivates checking consistent train/evaluation preprocessing. It does not
  establish that one bounded global shift represents all native misalignment.
- [NewAE ChipWhisperer ResyncSAD source](https://raw.githubusercontent.com/newaetech/chipwhisperer/develop/software/chipwhisperer/analyzer/preprocessing/resync_sad.py),
  accessed 2026-10-06, `get_trace`, `_findSAD`, `calcRefTrace`: reference-based bounded
  trace shifting is established preprocessing. Our Gaussian mean/variance score,
  inclusive endpoints and no rejection differ; phase9 is not this exact package.
- [Thiebeauld, Vasselle and Wurcker, Second-order Scatter Attack](https://eprint.iacr.org/2019/345.pdf),
  accessed 2026-10-06, §1.1–1.2: static/global displacement differs from elastic
  misalignment and shuffling. Combining two leaking regions can need fine alignment;
  joint-distribution/window techniques are prior work. Our 11-sample box product and
  leading covariance rank-one weights do not implement Scatter or solve elastic jitter.

Phase9 uses one pass of the existing trace-only Gaussian baseline on the original
10k training traces. Signed HW covariance weights and point selection use only
training labels. Its primary contrast holds evaluation offsets and old pair1 fixed;
changes in fitting, including center and weights, are the tested intervention.
Refined-template crosses and newly selected points are secondary. No offsets are
chosen using HW labels, keys, plaintexts, masks, or confirmation results.

The primary-source comparisons establish precedent for alignment and window
integration. They do not establish novelty of the particular experimental package;
full comparisons with other second-order regression and scheme-aware methods remain
incomplete, as documented in WINDOW_REGRESSION_PRIOR_ART_FOLLOWUP_2026-10-06.md.
