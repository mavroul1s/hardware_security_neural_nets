# Orthogonal-regression comparison — 2026-10-08

This post-execution review changes no frozen real-data experiment or parameter.

## Primary material actually read

Jiang and Ding, *Second-Order Side-Channel Analysis Based on Orthogonal Transform
Nonlinear Regression*, Entropy2023,25(3),505,
[publisher](https://www.mdpi.com/1099-4300/25/3/505),
[PMC mirror](https://pmc.ncbi.nlm.nih.gov/articles/PMC10048069/),
[DOI](https://doi.org/10.3390/e25030505).

Indexed primary-page text returned sections2–5 and equations15–18. Section3 centers
and projects a design matrix onto covariance eigenvectors. Equation17 reports
`W=(XᵀX)⁻¹(XᵀY−AI)`; equation18 squares a centered trace sample. Its template
regresses intermediate Hamming-distance predictors toward transformed power and
compares candidate-key predictions with measured traces. Section3.3 selects A=2000
from key-guessing experiments. Section5 concerns a SAKURA-G/FPGA AES tenth-round
target, Gaussian noise2/4 and GE approaching1.

Direct PMC access still returned a browser challenge; publisher access returned429.
EuropePMC HTML/XML also failed. The relevant equations and prose were read through
search-indexed primary pages, not a downloaded, visually checked PDF. Notation and
figure interpretation therefore remain partly unresolved. This narrows the previous
access gap; it does not justify claiming a complete implementation audit.

## Our algebraic assessment

For a full square orthogonal Q, `rank(XQ)=rank(X)` and `Qᵀ(XᵀX)Q` has the same
eigenvalues as `XᵀX`. Rotation alone cannot repair singularity. Projection onto
only positive-eigenvalue components is a different operation: it reduces dimension
and can yield an invertible Gram matrix in the retained subspace. The paper's
equation15 uses an n×k projection, so rank invariance of a full rotation does not
establish a defect in that implementation. Its component-retention rule needs
further checking before reproduction.

Interpreting the reported AI as a dimensionally compatible fixed offset c gives
`Gw=b−c`. An objective `||Xw−y||²+2cᵀw` has Hessian2G and shifts the normal-equation
right-hand side. This is a mathematical interpretation; the cached scalar/vector
notation does not fully specify the authors' multi-output implementation.

Our bilinear independent-input-noise objective instead adds
`Ω=σ²(C_A⊗I+I⊗C_B)+σ⁴I` to G. With positive-semidefinite C_A,C_B and σ>0,
Ω is positive definite, with eigenvalues at leastσ⁴. It changes the Hessian and
can make a singular Gram matrix invertible. A fixed right-hand-side subtraction
and this covariance correction are different algebraic forms in general. That
distinction is not proof that our correction lacks other prior art or is novel.
Orthogonal transforms, ridge and noise-induced regularization remain established.

Our feature fits map centered trace products to training-label HW. This direction,
training-only hyperparameters, ASCAD target and rank0 convention differ from the
reported template setup. Numerical correlations/GE cannot establish superiority
without matched information, data and endpoints. We did not import its attack-based
parameter selection, implement its model or open our locked attack data.

## Deterministic correctness checks

[Executable audit](../notebooks/audit_regression_prior_art.py) and
[saved arrays/checks](../outputs/regression_prior_art_audit_2026-10-08/verification.json)
verify five algebra statements: rank/eigenvalues under rotation, separate eigenspace
truncation, pseudoinverse transport, positive noise correction, and the unchanged
Hessian under a linear penalty. A collinear5×2 matrix retains rank1 after rotation;
the noise example lifts a rank2/4 Gram matrix to rank4. All assertions passed.

These deterministic synthetic examples use no real traces, random seed, new model,
GPU training or recovery trial. Runtime was not measured separately from tooling;
they are excluded from the ten-phase real-data experiment cost. They are
correctness evidence only. Remaining work includes author-code/notation resolution,
broader citation search and an independently justified benchmark; novelty and
physical efficacy remain unverified.
