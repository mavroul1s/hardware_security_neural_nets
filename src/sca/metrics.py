"""Float64 log-likelihood accumulation and conservative zero-based key ranks."""
import numpy as np
from .aes import candidate_labels


def rank_curve(log_probabilities, plaintext_byte, true_key):
    lp = np.asarray(log_probabilities, dtype=np.float64)
    labels = candidate_labels(plaintext_byte)
    if lp.shape != labels.shape or not np.isfinite(lp).all() or not 0 <= true_key < 256:
        raise ValueError("Expected finite [N,256] log probabilities and a byte key")
    scores = np.cumsum(lp[np.arange(len(lp))[:, None], labels], axis=0, dtype=np.float64)
    correct = scores[:, true_key, None]
    # Every equally good incorrect key precedes the true key: no false recovery on ties.
    return np.sum(scores >= correct, axis=1) - 1


def evaluate_key_recovery(log_probabilities, plaintext_byte, true_key,
                          budget=2000, repetitions=100, seed=8001, success_threshold=0.9):
    n = len(log_probabilities)
    if not 1 <= budget <= n or repetitions < 1 or not 0 < success_threshold <= 1:
        raise ValueError("Invalid budget/repetition count/criterion")
    rng = np.random.default_rng(seed)
    ranks = np.empty((repetitions, budget), dtype=np.int16)
    for i in range(repetitions):
        order = rng.permutation(n)[:budget]
        ranks[i] = rank_curve(log_probabilities[order], np.asarray(plaintext_byte)[order], true_key)
    ge = ranks.mean(axis=0)
    sr = (ranks == 0).mean(axis=0)
    # A sustained criterion avoids claiming success from a transient early crossing.
    sustained = np.logical_and.accumulate((sr >= success_threshold)[::-1])[::-1]
    reached = np.flatnonzero(sustained)
    traces = int(reached[0] + 1) if len(reached) else None
    summary = {"budget": budget, "attack_pool_size": n, "repetitions": repetitions,
        "attack_order_seed": seed, "rank_convention": "zero_based_conservative_ties",
        "ge_at_budget": float(ge[-1]), "sr_at_budget": float(sr[-1]),
        "success_threshold": success_threshold, "traces_to_sustained_success": traces,
        "recovery_censored": traces is None,
        "criterion": "SR >= threshold at every remaining trace count through budget"}
    return summary, {"trace_counts": np.arange(1, budget + 1), "ge": ge, "sr": sr, "ranks": ranks}
