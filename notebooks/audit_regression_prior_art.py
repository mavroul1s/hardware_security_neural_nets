"""Deterministic algebra checks; no datasets, optimization or physical efficacy evidence."""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/regression_prior_art_audit_2026-10-08"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base = np.array([-2., -1., 0., 1., 2.])
    x = np.column_stack((base, 2 * base))
    q = np.array([[1., 1.], [-1., 1.]]) / np.sqrt(2.)
    covariance = x.T @ x / len(x)
    rotated = q.T @ covariance @ q
    assert np.allclose(q.T @ q, np.eye(2))
    assert np.linalg.matrix_rank(x) == np.linalg.matrix_rank(x @ q) == 1
    assert np.allclose(np.linalg.eigvalsh(covariance), np.linalg.eigvalsh(rotated))
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    retained = x @ eigenvectors[:, eigenvalues > 1e-10]
    assert retained.shape == (5, 1) and np.linalg.matrix_rank(retained) == 1
    assert np.allclose(np.linalg.pinv(x @ q) @ base, q.T @ np.linalg.pinv(x) @ base)

    ca = np.array([[2., .3], [.3, 1.]])
    cb = np.array([[1.5, -.2], [-.2, .7]])
    sigma = .4
    correction = sigma**2 * (np.kron(ca, np.eye(2)) + np.kron(np.eye(2), cb)) + sigma**4 * np.eye(4)
    gram = np.diag([2., 1., 0., 0.])
    corrected = gram + correction
    assert np.linalg.eigvalsh(correction).min() > 0
    assert np.linalg.matrix_rank(gram) == 2 and np.linalg.matrix_rank(corrected) == 4
    assert np.linalg.eigvalsh(corrected).min() > 0

    g = np.array([[2., .2], [.2, 1.]])
    b = np.array([1., -.5])
    c = np.array([.3, -.1])
    w_linear = np.linalg.solve(g, b - c)
    assert np.allclose(g @ w_linear - b + c, 0)
    step = np.array([.05, -.03])
    gradient = lambda w: 2 * g @ w - 2 * b + 2 * c
    assert np.allclose(gradient(w_linear + step) - gradient(w_linear), 2 * g @ step)
    w_quadratic = np.linalg.solve(g + sigma**2 * np.eye(2), b)
    assert not np.allclose(w_linear, w_quadratic)

    np.savez_compressed(OUT / "arrays.npz", x=x, q=q, covariance=covariance,
        rotated=rotated, retained=retained, ca=ca, cb=cb, correction=correction,
        gram=gram, corrected=corrected, g=g, b=b, c=c, w_linear=w_linear,
        w_quadratic=w_quadratic)
    record = {
        "deterministic_synthetic_algebra_checks": 5,
        "checks": ["orthogonal_rotation_preserves_rank_and_eigenvalues",
            "positive_eigenspace_truncation_is_a_separate_operation",
            "pseudoinverse_fit_transports_under_orthogonal_rotation",
            "bilinear_noise_correction_can_make_singular_gram_positive_definite",
            "linear_penalty_shifts_rhs_without_changing_hessian"],
        "interpretation": "Our analysis of algebraic forms; not an implementation or reproduction of the published template method",
        "original_rank": 1, "rotated_rank": 1, "retained_components": 1,
        "original_eigenvalues": np.linalg.eigvalsh(covariance).tolist(),
        "rotated_eigenvalues": np.linalg.eigvalsh(rotated).tolist(),
        "minimum_noise_correction_eigenvalue": float(np.linalg.eigvalsh(correction).min()),
        "minimum_corrected_gram_eigenvalue": float(np.linalg.eigvalsh(corrected).min()),
        "physical_efficacy_evidence": False, "new_real_data_reads": 0,
        "new_gpu_trainings": 0, "new_models_trained": 0,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "arrays_sha256": hashlib.sha256((OUT / "arrays.npz").read_bytes()).hexdigest(),
    }
    (OUT / "verification.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
