# Second-Order Leakage, Feature-Selection Stability, and Key Recovery under a Limited Profiling Budget

Working empirical paper draft, 11 October 2026. Not submission ready. Includes the
completed, independently verified45k GPU diagnostic; preserves all earlier failures.

## Abstract

We investigate the distinction between detectable second-order leakage, stability
of supervised feature selection, and cryptographic key recovery in masked AES
side-channel benchmarks. Four neural training configurations at a fixed 10,000-trace
profiling budget failed a predefined clean validation recovery threshold. A fifth
configuration with45,000 nested training traces passed on the same viewed validation:
20/20 trace orders recovered the key at2000 traces, versus0/20 for its10k comparator.
This jointly changed unique samples, optimizer updates and the fitted scaler;
it does not isolate a cause or establish independent attack efficacy. The
CPU diagnostics used training-only feature fits and separately frozen, disjoint
profiling confirmations. Trace alignment and simple window products provided useful
robustness on fixed-key traces under synthetic perturbations, while known SAD and
box/rank-one controls limited claims of methodological superiority. A variable-key
campaign failed its frozen attack criterion. Later paired training resampling
distinguished persistent signal at fixed selected points from unstable reselection
of a second feature family. Matching point selection to a window objective did not
satisfy the joint stability criterion. These findings support a bounded empirical
failure analysis rather than a new attack or a general robustness claim. We report
protocol adaptations, failed criteria, data-access history, and reproducibility
checks, and distinguish conditional trace-order outcomes from independent keys or
acquisitions.

## 1. Research question and intended contribution

The initial question concerned combined noise and shift augmentation for a small
profiling CNN. Its baseline gate failed, so combined training was not executed.
Consequently this study cannot estimate the effect of training augmentation.
The revised question asks which conclusions remain justified when a masked
implementation exhibits measurable second-order signal, neural recovery varies
with a joint training-budget change, and feature-selection stability fails under
restricted profiling conditions.

The intended contribution is an auditable sequence of benchmark diagnostics:
preserved neural failures, training-only statistical controls, prospective signal
confirmations, and explicit failed selection criteria. Publication merit depends on
the depth and usefulness of the empirical comparison. Novelty has not been established.
The use of centered products, projection/window selection, alignment, or noise
regularization is not itself claimed as a contribution.

## 2. Data and evaluation units

The initial study uses official ASCAD fixed-key traces with700 samples, zero-based
target byte2, and256 identity labels. Training10k and validation5k are disjoint;
normalization is fitted on training traces alone. Neural inputs contain traces only.
Plaintexts and evaluation keys enter key-ranking calculations after prediction.
Rank0 is best, with conservative treatment of ties. Minimum validation
cross-entropy selects the neural checkpoint.

The later official variable-key campaign contains1400-sample traces and uses a
fresh training-only fit. This changes multiple acquisition and leakage properties;
the campaign comparison does not isolate the effect of changing the key. Its viewed
attack subset is excluded from tuning. The original fixed-key attack remains locked.

Twenty orders of2000 traces drawn from one5000-trace pool are conditional order
summaries. Exact reconstruction yields mean pairwise overlap800.94 traces,
range758–847, and5000 distinct rows across all orders. They are not twenty
independent acquisitions or keys. This overlap alone does not determine score
correlation or an effective sample size.

## 3. Methods and chronology

The neural study retains ReLU and LeakyReLU failures, a small literature-inspired
CNN with16,952 parameters, and one author-cycle optimizer diagnostic. All four
use10k/5k, seed0 and50epochs. The fourth changes batch size and schedule together,
increasing updates to10000 from3950 while retaining500000 trace exposures.
Framework, initialization, optimizer and normalization differences prevent an
exact published-recipe reproduction claim.

The fifth training reuses the same CNN, seed0,50epochs, batch50 and linear cycle,
but increases nested training to45k, updates to45000 and exposures to2250000.
Training-only per-position MinMax is refitted on45k. Validation indices and all
twenty ranking orders are unchanged. This was separately approved and frozen
before execution; it is not an equal-compute or independent confirmation study.

CPU extensions fit alignment templates and second-order features on training
traces. Point selection uses training labels; confirmation labels do not select
points, windows, transformations, or hyperparameters. Known SAD, box products,
rank-one features and incorrect shift correspondence serve as controls.
Noise-corrected regression is compared with clean regression and simpler controls.
Later phases reuse twenty paired perturbations of the same original training
sample, retaining all draws without a winner or consensus selector.

Each phase froze its local plan before accessing its new confirmation payloads.
The sequence of follow-ups was adaptive to earlier evidence. Local preregistration
therefore does not imply globally controlled error rates over the complete research
history. Fixed profiling50k and variable profiling170k are viewed; variable
profiling30k remain unused. Future exclusions must include every historical split.

## 4. Existing results

All four neural configurations have clean validation SR@2000=0/20. The adapted
author-cycle diagnostic has minimum validation CE5.560471 at epoch1 and GE96;
the earlier literature-inspired baseline has minimum CE5.560782 and GE114.25.
These10k outcomes do not identify a unique cause.

The45k diagnostic passes the frozen primary threshold. Its minimum-CE checkpoint
is epoch21, CE5.539753890, with SR@2000=20/20 and GE0. The descriptive sustained
SR≥0.90 endpoint starts at504 traces and holds through2000. The corresponding
10k author-cycle checkpoint is epoch1, CE5.560470867, SR0/20 and GE96.
The45k final training/validation CE values are5.409820/5.569779. The result supports
recovery for this specific expanded recipe on viewed validation; it does not
identify which part of the joint change caused improvement. The original failed
baseline gate remains preserved. Combined augmentation was not trained.

| Configuration | Training traces | Updates | Best epoch | Minimum CE | SR@2000 | GE@2000 |
|---|---:|---:|---:|---:|---:|---:|
| Author cycle10k | 10000 | 10000 | 1 | 5.560471 | 0/20 | 96.000000 |
| Author cycle45k | 45000 | 45000 | 21 | 5.539754 | 20/20 | 0.000000 |

All values come from the [verified budget report](../outputs/kaggle_budget_2026-10-11/api/REPORT_EL.md).

On the fixed-key campaign, frozen statistical features and trace alignment
recover signal under specified synthetic shifts/noise. SAD matches the main
Gaussian-alignment recovery endpoint. Window and rank-one controls match or exceed
noise ridge on relevant comparisons. Thus superiority over these known controls
is unsupported. Positive profiling contrasts for noise correction relative to
clean ridge are conditional signal results, not a new general attack result.

The variable-key attack criterion fails. Training-side single-pass alignment also
fails its original primary contrast. A new selected pair shows positive signal in
two fresh profiling pools, but the subsequent selection audit shows that persistent
signal at frozen points does not guarantee stable full-search reselection.

In the matched window-selection phase, second-family box medians are0.007642 and
0.006647 in two fresh pools, with12/20 and13/20 positive draws. The primary criterion
fails. First-family improvement is descriptive. OOB prediction satisfies7/8 numerical
checks and8/8 threshold checks, but fails its numerical joint criterion. These
outcomes establish neither a uniquely causal failure mechanism nor that every
original selected pair was a false positive.

## 5. Related work and limits

[ASCAD](https://github.com/ANSSI-FR/ASCAD) supplies the benchmark and source context.
[Higher-order projection pursuits](https://research.dial.uclouvain.be/bitstreams/6343c079-4c42-44e0-90cf-d9c271b1eee2/download)
and [feature-selection/resampling research](https://doi.org/10.46586/tches.v2022.i4.828-861)
are direct precedents for selection and window controls.
[Scheme-aware architectures](https://doi.org/10.46586/tches.v2023.i1.32-59)
provide relevant masking-aware neural context. The
[bilinear CNN repository](https://github.com/loccs-cp/Bilinear-CNN-for-SCA)
supplies direct prior art for neural product combinations. A
[code-only audit](../literature/BILINEAR_CODE_AUDIT_2026-10-11.md) confirms an explicit
outer-product layer and documents protocol differences. Full-paper access remains
unresolved; no matched implementation was executed.

Synthetic correctness fixtures establish implementation properties only. Injected
global perturbations on real traces do not constitute new physically acquired
misalignment conditions. Profiling correlations, actual-key recovery, independent
training seeds and independent acquisitions remain separate evidence levels.
The present study lacks independent device/acquisition replication and a successful
variable-key recovery confirmation. It should not claim universal robustness or
publication readiness.

## 6. Reproducibility and pending work

Configs, source hashes, splits, RNG states, checkpoint histories and independent
rank checks are retained. The current full CPU suite passes105 tests, including
schedule/continuation, nested splits, synthetic smoke and exact notebook-byte
transport. The remote frozen package passes33 tests. The verifier independently
checks45000 learning rates,40000 rank prefixes,5000 CPU predictions and the
training-only scaler; maximum CPU/GPU log-probability difference is7.495e−6.
All26 preserved original files retain their hashes.

The first Kaggle attempt failed before training because text transport normalized
CRLF to LF and violated the frozen extension hash. It performed zero optimizer
updates. A separately approved correction preserved exact bytes and completed
one45000-update training. Both attempt histories remain available. Training loops
took156.097364s, validation loops6.375075s and the experiment180.865040s after
setup. These are not total GPU-account charging measurements. The recorded T4
environment matches the10k comparator. The account migrated to nmavros with
private continuation notebook/input; the original con1los history is preserved.

Five full GPU trainings exhaust the approved cap5. Version3 is a QUICK_SAVE of
the original notebook source without execution. The original fixed attack remains
locked and30k variable profiling rows remain unused. Independent attack evidence
and a prospective augmentation comparison require a new frozen protocol and
explicit agreement for any additional training. Full-text prior-art access and a
focused manuscript remain publication gaps.
