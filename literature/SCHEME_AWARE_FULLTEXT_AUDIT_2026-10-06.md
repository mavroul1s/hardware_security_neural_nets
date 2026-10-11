# Scheme-aware full-text follow-up — 2026-10-06

This is a post-execution literature audit. It changes no frozen experiment or fit.
The previously recorded ePrint PDF403 remains historical; access to the published
28-page paper now succeeds through the authors' university repository.

## Primary source and relevant comparison

Masure, Cristiani, Lecomte and Standaert, *Don't Learn What You Already Know:
Scheme-Aware Modeling for Profiling Side-Channel Analysis against Masking*,
TCHES2023(1),32–59, published2022-11-29,
[DOI](https://doi.org/10.46586/tches.v2023.i1.32-59),
[published PDF](https://research.dial.uclouvain.be/bitstreams/458a4563-f635-4432-a1ed-ff109cd0f434/download).

Sections2–3 use known masking structure and share regions without requiring random
share labels. GroupRecombine is a parameter-free discrete convolution of learned
share distributions, with Walsh–Hadamard/Fourier implementations. Section4.3.1
examines fixed700/variable1400-sample ASCAD targeting the third byte. Variable
700/700 region splitting fails for non-worst-case models; code-informed regions
[0,300]/[900,1200] improve selection. Their best scheme-aware model obtains positive
PI at70k profiling traces. Figure8 reports best-validation-loss learning curves.
These facts are from the published paper, not results of our implementation.

Our full-search centered-product/HW selector and bilinear point/box/rank1 fits
estimate scalar features; they do not learn share posteriors or implement the
convolution. Our10k fit, Pearson/CPA endpoints and prospective confirmations differ.
Consequently, the paper is relevant prior art about masking structure and region
selection; its reported PI cannot establish numerical superiority over our SR@2000.
Our frozen pairs lie in broadly related regions, but no code-informed restriction
was added after viewing confirmations. Phase10 still reports every selection.
This comparison is our inference, not a claim made by the authors about our study.

## Access and remaining work

[Author code repository](https://github.com/uclcrypto/Scheme-Aware-Architectures)
and its README were accessible. Individual implementation files were not inspected
or executed; no reproduction, dependency installation or GPU training occurred.
Relevant sections2/3/4.1/4.3 were reviewed, not an exhaustive full-paper/code audit.
The orthogonal-regression full text and broader backward/forward citation search
remain unresolved. Neither access success nor methodological differences establish
novelty. A matched benchmark would require a separately justified, frozen study.
