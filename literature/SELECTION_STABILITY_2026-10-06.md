# Point-selection resampling audit — sources and limits, 2026-10-06

Frozen before phase10 training diagnostics and unused profiling confirmations.

[Official SciPy bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html),
accessed 2026-10-06, parameters `paired`, `n_resamples`, and Pearson example:
bootstrap resamples have replacement and the original sample length; paired
statistics share indices across arrays. This supports preserving trace/label
pairing in our implementation. SciPy distinguishes percentile, basic and BCa
intervals; this project uses its own paired percentile implementation, not SciPy's
default BCa. Approximate conditional intervals are not a universal coverage proof.

Phase10 training draws each contain 10,000 positions from the original 10k training
rows. Duplicate rows reduce the number of distinct observations. These draws are
conditional perturbation diagnostics, not independent acquisitions, new neural
training seeds, or a change to the approved 10k unique-trace neural budget.
All 20 draws and their selected points/weights are retained; none is selected for
deployment, hyperparameter tuning, ensemble construction or attack evaluation.

The original phase9 label-free alignment template and training offsets stay
fixed. Training centers, full pair selection and simple quadratic weights are
recomputed inside each paired draw. The audit is conditional on preprocessing
estimated from the original sample, not a full end-to-end bootstrap of alignment.
Argmax selection is discontinuous; twenty draws support descriptive location and
signal sensitivity summaries, not asymptotic selection-confidence statements.

Formal stability selection is a distinct prior-art topic. A publisher access
attempt for Meinshausen/Buehlmann's DOI
[10.1111/j.1467-9868.2010.00740.x](https://doi.org/10.1111/j.1467-9868.2010.00740.x)
failed through the web tool on 2026-10-06. We do not infer its full content or invoke
its error-control guarantees. Our paired bootstrap audit does not implement or
claim formal stability selection or familywise control of selected false points.

The phase9 secondary signal is not retroactively made primary. This adaptive
follow-up freezes new endpoints on new rows: both original aligned selected
rank1 features must meet the signal criterion, and the entire reselection pipeline
must meet the predefined sensitivity criterion. No overall alpha-spending rule
has been maintained across research phases, and no constant-key attack is performed.
