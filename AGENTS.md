# Stable project instructions

- Communicate with the user in Greek; code, identifiers and code comments in English.
- Read README.md, PROJECT_PLAN.md and PROGRESS.md before continuing work.
- Use Python/PyTorch, local CPU for smoke tests and Kaggle CUDA for full experiments.
- Keep a single Kaggle notebook and the approved minimal study: baseline versus combined,
  one training budget, one seed. Reuse benchmark epochs and completed checkpoints.
  Additional budgets, models or seeds require a research reason and user agreement.
- Preserve the two failed ReLU/LeakyReLU baselines. The user approved one literature
  CNN baseline (16,952 parameters, same10k/5k/seed0/50epochs, train-only feature MinMax).
  Run only combined if clean validation SR@2000 >= 0.90 (18/20), minimum-CE checkpoint.
  At most four full GPU trainings including the two failures; no single noise/shift runs.
- No paid services, OpenAI API or API keys are required.
- Start with ASCAD fixed-key, 700 samples, zero-based byte 2, identity labels.
- Keep train/validation/attack separate. Fit normalization only on training traces.
- Never use attack results to select models, transformations or hyperparameters.
- Attack keys belong only to evaluation; model inputs are traces alone.
- Use paired seeds and common splits, rank 0 = best; document ties and failures.
- Synthetic tests are correctness checks, never evidence of physical attack efficacy.
- Verify citations and novelty. Record access gaps, negative results and actual costs.
- Keep data/, runs/, .venv/ out of Git. Persist configs, splits, provenance and RNG states.
- Update PROGRESS.md after meaningful work; do not fabricate execution or results.
- Run meaningful tests after changes to labels, ranking, splits, transforms or checkpoints.
- On 2026-10-05 the user authorized further experiments toward a paper, also included
  in the final coursework. The current extension is CPU trace-only alignment and
  normalization-order comparisons and training-label-only point selection, with each
  plan frozen before execution and disjoint profiling confirmation.
  Preserve the existing GPU study, source hash, checkpoints, failed gate and single notebook.
  Confirmation rows become viewed evidence after execution; do not reuse them for tuning.
- The 2026-10-05 variable-key CPU replication is complete: original official 1400-sample
  campaign, a fresh training-only 10k fit, and one new constant-key attack5k subset.
  Its primary criterion failed; preserve all results and do not tune on that viewed
  attack subset. The original fixed-key attack remains locked in this extension.
  Future point-selection diagnostics must freeze a new plan and use unused profiling
  confirmation rows. No extra GPU trainings, notebooks or neural-model scope was added.
- On 2026-10-06 the user requested more paper experiments. CPU window/regression
  and larger no-refit precision replications are complete. Preserve phase7's failed
  global primary and variable attack criterion and phase8's positive profiling-only
  result. Simple box/rank1 controls match or outperform noise ridge; novelty is unverified.
  All fixed profiling50k are now viewed; variable profiling70k and attack10k are viewed.
  Future confirmations must use unused variable profiling rows with a new frozen plan.
  No attack-driven tuning, new GPU training or additional Kaggle notebook was authorized
  by these CPU phases.
- The 2026-10-06 phase9 CPU training-side alignment is complete. Same original10k,
  one trace-only Gaussian pass and training-label-only point/box/rank1 fits, with
  two fresh20k profiling confirmations. Preserve its failed primary contrast at
  oldpair1/clean/common raw-template offsets; new selected pair2's positive clean
  correlation is secondary, not attack efficacy. Variable profiling110k are now
  viewed/90k unused; attack10k unchanged and original fixed attack locked. Future
  exclusions must union all phase9 splits, with a new frozen plan; never retune
  on viewed confirmation/attack rows. One notebook/3GPUtrainings remain unchanged.
- The 2026-10-06 phase10 CPU paired-selection audit is complete. All20 bootstrap
  draws reuse the same original10k training, with fixed phase9 alignment parameters.
  Preserve both the positive frozen-pair signal and the failed joint criterion:
  reselected family rank2 is unstable in both fresh20k profiling pools. All draws
  are retained; no winner, ensemble or consensus was chosen. These are conditional
  sample perturbations, not independent neural seeds or acquisition replications.
  Variable profiling150k are viewed/50k unused; attack10k unchanged. Future exclusions
  must union all phase10 splits. No new GPU training or Kaggle notebook was added.
- The 2026-10-09 phase11 matched point versus box-objective selection is complete.
  Reused all20 phase10 paired draws and fixed phase9 preprocessing, with two fresh10k
  profiling confirmations. Preserve H1 primary failure: second-family box medians
  0.007642/0.006647,12/20 and13/20positive; first-family improvement is descriptive.
  H2 OOB joint criterion failed1/8 numerical checks, although threshold agreement
  held8/8. No causal failure attribution or recovery claim follows. Variable profiling
  170k are viewed/30k unused; future exclusions must union every phase11 split and
  verify the phase5-through-phase10 provenance chain. Attacks/GPU/notebook unchanged.
  New selector/window/region trials require a new discriminating frozen hypothesis;
  no winner, ensemble or consensus was chosen. Latest full suite95passing tests.
- On 2026-10-09 the user permitted a Kaggle experiment. One fourth full GPU baseline
  is complete: same literature CNN16952 parameters/original10k/5k/seed0/50epochs,
  batch50 and author three-phase linear LR cycle max0.005. Updates10000 versus3950,
  same500000 trace exposures; joint recipe diagnostic, not equal-update causal isolation.
  Clean validation SR@2000 remains0/20; minimum-CE checkpoint epoch1. Preserve the
  three original failures and original failed gate. No combined or attack run occurred.
  Same private notebook executed version9; version10 is QUICK_SAVE restoring original
  source, without execution. Original source/checkpoints/Input/canonical notebook hashes
  remain unchanged. Cap4 is exhausted; further GPU training requires a new research
  reason and user agreement. Variable profiling170k viewed/30k unused unchanged.
  This diagnostic used previously viewed shared validation, not a new confirmation.
  Latest full suite99passing tests; independent saved-rank and CPU inference verification.
