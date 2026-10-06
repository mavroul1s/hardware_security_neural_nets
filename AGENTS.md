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
