# Leakage, Augmentation Failure, and Feature-Selection Stability in Masked AES

Working empirical paper draft, 11 October 2026. Not submission ready. Includes the
completed, independently verified 45k baseline/combined comparison and final
fixed-key attack evaluation; preserves all earlier failures.

## Abstract

We investigate the distinction between detectable second-order leakage, stability
of supervised feature selection, and cryptographic key recovery in masked AES
side-channel benchmarks. Four neural training configurations at a fixed 10,000-trace
profiling budget failed a predefined clean validation recovery threshold. A fifth
configuration with 45,000 nested training traces passed on the same viewed validation:
20/20 trace orders recovered the key at 2000 traces, versus 0/20 for its 10k comparator.
This jointly changed unique samples, optimizer updates and the fitted scaler;
it does not isolate a cause. A sixth training matched the expanded recipe while
adding combined shift/noise augmentation. Both minimum-validation-loss checkpoints
were locked before the first fixed-key attack access. The baseline recovered the
byte in 100/100 clean trace orders, whereas the combined model recovered it in
0/100 orders in all eight frozen conditions. The joint augmentation criterion
failed. These outcomes concern one training seed, one fixed key and one acquisition
campaign, with overlapping trace orders and synthetic perturbations. The CPU
diagnostics used training-only feature fits and separately frozen, disjoint
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
profiling CNN. The original 10k baseline gate failed and remains a negative result.
A separately approved 45k diagnostic passed on viewed validation, enabling a frozen
matched augmentation comparison and a final held-out trace evaluation. The revised
question asks which conclusions remain justified when a masked implementation
exhibits measurable second-order signal, neural recovery varies with a joint
training-budget change, a specified augmentation recipe fails, and supervised
feature reselection is unstable under restricted profiling conditions.

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
attack subset is excluded from tuning. The original fixed-key attack was first
accessed in the final phase after both neural checkpoints were locked. Its 10k
traces are now viewed and excluded from future tuning. They hold out traces from
the same fixed-key acquisition campaign, rather than introducing a new key/device.

Twenty orders of2000 traces drawn from one5000-trace pool are conditional order
summaries. Exact reconstruction yields mean pairwise overlap800.94 traces,
range758–847, and5000 distinct rows across all orders. They are not twenty
independent acquisitions or keys. This overlap alone does not determine score
correlation or an effective sample size.

The final attack uses 100 common orders of 2000 traces from its 10k pool. These are
also conditional summaries with overlapping traces, rather than independent keys,
training seeds or acquisition replications. We report success counts and paired
contrasts without treating them as independent Bernoulli observations.

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

The sixth training matches the fifth in architecture, initialization seed, nested
45k/5k split, training-only scaler, 50 epochs, batch size 50, 45,000 updates and
2,250,000 trace exposures. Its sole recipe change is augmentation: a uniformly
sampled global shift from -5 through +5, with zero padding, followed by independent
Gaussian noise with standard deviation 0.1 after MinMax normalization, without
clipping. Separate augmentation and loader generators preserve common shuffle
orders. Each model is selected by minimum clean validation cross-entropy; no attack
result selects a checkpoint, transformation or hyperparameter.

The [frozen final protocol](PAPER_CONFIRMATION_PROTOCOL_2026-10-11.md) specifies eight
conditions: clean, matched noise, matched shift, matched combined, mild combined,
noise OOD, shift OOD and both OOD. Each condition uses one common corruption
realization across models, corruption seed 9001 and the same 100 orders generated
with seed 8001, through 2000 traces. H1 requires baseline clean SR >= 0.90. H2, the
joint primary augmentation criterion, requires combined both-OOD SR >= 0.90,
strictly positive paired SR improvement over the baseline in that condition, and
combined clean SR >= 0.90. Other conditions and GE/sustained-SR endpoints are
descriptive. The attack is performed once on local CPU after checkpoint locking.

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
baseline gate remains preserved. The separately approved combined45k training
selects epoch 4, CE 5.549329338, with viewed clean validation SR 1/20 and GE 107.2.

| Configuration | Training traces | Updates | Best epoch | Minimum CE | SR@2000 | GE@2000 |
|---|---:|---:|---:|---:|---:|---:|
| Author cycle10k | 10000 | 10000 | 1 | 5.560471 | 0/20 | 96.000000 |
| Author cycle45k | 45000 | 45000 | 21 | 5.539754 | 20/20 | 0.000000 |
| Combined45k | 45000 | 45000 | 4 | 5.549329 | 1/20 | 107.200000 |

Values come from the [verified budget report](../outputs/kaggle_budget_2026-10-11/api/REPORT_EL.md)
and [verified final comparison](../outputs/paper_confirmation_2026-10-11/REPORT_EL.md).

The final fixed-key attack confirms baseline recovery on held-out traces from
the same campaign. H1 passes with clean SR 100/100, GE 0, and sustained SR >= 0.90
from 479 traces through 2000. The combined checkpoint has no successful endpoint
order in any condition. Its clean SR is 0/100, both-OOD SR is 0/100 and paired
both-OOD improvement is -0.04. All three H2 components fail. No alternative
checkpoint or new recipe is evaluated on the viewed attack set.

| Attack condition | Noise sigma | Maximum shift | Baseline SR@2000 | Baseline GE@2000 | Combined SR@2000 | Combined GE@2000 |
|---|---:|---:|---:|---:|---:|---:|
| clean | 0.00 | 0 | 100/100 | 0.00 | 0/100 | 92.42 |
| noise_matched | 0.10 | 0 | 100/100 | 0.00 | 0/100 | 86.99 |
| shift_matched | 0.00 | 5 | 54/100 | 4.77 | 0/100 | 99.44 |
| combined_matched | 0.10 | 5 | 44/100 | 5.17 | 0/100 | 102.98 |
| combined_mild | 0.05 | 2 | 97/100 | 0.05 | 0/100 | 92.14 |
| combined_noise_ood | 0.20 | 5 | 27/100 | 10.19 | 0/100 | 101.06 |
| combined_shift_ood | 0.10 | 10 | 8/100 | 36.93 | 0/100 | 116.65 |
| combined_both_ood | 0.20 | 10 | 4/100 | 51.62 | 0/100 | 112.87 |

![Final fixed-key attack success curves](../outputs/paper_confirmation_2026-10-11/sr_attack.png)

This is a failure of the specified combined recipe and its predefined checkpoint
selection rule in one paired-seed comparison. It does not estimate an average
effect across neural seeds, attribute failure to noise versus shift, or establish
that augmentation is generally harmful. Baseline degradation under larger
synthetic shifts also limits robustness claims.

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

[Li and Perin](https://link.springer.com/article/10.1007/s13389-024-00363-3)
provide direct noise/desynchronization augmentation context. A newly published
[contrastive collision approach](https://link.springer.com/article/10.1186/s42400-026-00658-4)
uses a different multi-byte objective and threat model. These sources support
placing the present diagnostic within established research, rather than claiming
the absence of augmentation prior art. The
[continuation audit](../literature/CONTINUATION_AUDIT_2026-10-11.md) records access
gaps and the limited search scope. No matched replication or exhaustive novelty
verification follows from this search.

Synthetic correctness fixtures establish implementation properties only. Injected
global perturbations on real traces do not constitute new physically acquired
misalignment conditions. Profiling correlations, actual-key recovery, independent
training seeds and independent acquisitions remain separate evidence levels.
The present study lacks independent device/acquisition replication and a successful
variable-key recovery confirmation. It should not claim universal robustness or
publication readiness.

## 6. Reproducibility, costs and remaining paper gaps

Configs, source hashes, splits, RNG states, checkpoint histories and independent
rank checks are retained. The current full CPU suite passes 112 tests, including
schedule/continuation, nested splits, synthetic smoke and exact notebook-byte
transport. The remote frozen package passes 33 tests. Independent checks verify
45,000 learning rates, 40,000 validation rank prefixes, 5000 CPU predictions and
the training-only scaler for each 45k training. The maximum CPU/GPU log-probability
difference is 7.495e-6 for the baseline and 4.917491e-7 for the combined model.
The final attack verifier reconstructs all 3,200,000 rank prefixes and paired
counts. All 40 artifacts in the final preservation map retain their hashes,
including the original 26 and completed baseline45k outputs.

The first Kaggle attempt failed before training because text transport normalized
CRLF to LF and violated the frozen extension hash. It performed zero optimizer
updates. A separately approved correction preserved exact bytes and completed
one45000-update training. Both attempt histories remain available. Training loops
took156.097364s, validation loops6.375075s and the experiment180.865040s after
setup. These are not total GPU-account charging measurements. The recorded T4
environment matches the10k comparator. The account migrated to nmavros with
private continuation notebook/input; the original con1los history is preserved.

The first final-comparison submission was rejected with HTTP 400 before creating
a version or starting training; its precise server-side cause remains unresolved.
A separately approved correction used a smaller transport containing exactly the
same reference checkpoint bytes and previously successful metadata. Version 4
completed the sole new combined training. Its training loops took 181.405335s and
validation loops 6.612318s. Local CPU attack evaluation took 32.868586s, with an
additional 21.687648s for independent rank verification. The downloaded result ZIP
was valid despite a later Windows log-encoding failure; complete UTF-8 logs were
retained through read-only API capture. None of these component measurements is
presented as total GPU account charging time.

Six full GPU trainings exhaust cap6, with 111,850 optimizer updates and 6,500,000
trace exposures across the complete neural history. Version 5 is a QUICK_SAVE of
the original notebook source without execution, independently checked cell by
cell; executed version 4 outputs are retained. The original source, Input packet,
canonical notebook and prior checkpoints remain unchanged. Fixed-key attack10k
is now viewed and excluded from tuning. Variable profiling30k remain unused and
the viewed variable-key attack is unchanged.

The authorized experiment sequence is complete. A stronger paper claim would
require separately planned independent keys/acquisitions and neural seeds, plus
resolved full-text prior-art comparisons; these are remaining evidence gaps, not
automatic new runs. The defensible present contribution is a bounded empirical
diagnostic connecting conditional recovery, augmentation failure and selection
instability while retaining negative outcomes.
