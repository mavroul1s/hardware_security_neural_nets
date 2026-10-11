"""Audit saved evidence and evaluation sampling without opening trace datasets."""
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from sca.data import make_splits
from sca.train import code_identity

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/paper_readiness_2026-10-11'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    started = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    paths = [ROOT / 'outputs' / folder / name for folder, name in [
        ('kaggle_recipe_2026-10-09', 'results.json'),
        ('kaggle_recipe_2026-10-09', 'verification.json'),
        ('paper_window_selection_2026-10-09', 'evidence.json'),
        ('paper_precision_replication_2026-10-06', 'evidence.json')]]
    records = [json.loads(p.read_text(encoding='utf-8')) for p in paths]
    recipe, _, selection, precision = records
    assert recipe['complete'] and not recipe['primary_met']
    assert recipe['full_gpu_trainings_total'] == 4
    assert recipe['validation'][0]['sr_at_budget'] == 0
    assert selection['variable_viewed_profiling_rows'] == 170000
    assert selection['variable_unused_profiling_rows'] == 30000
    assert not selection['paper_ready'] and not selection['novelty_verified']
    assert precision['support_met']
    old = ROOT / 'runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0'
    preserved = {name: sha(old / name) for name in recipe['baseline_hashes']}
    assert preserved == recipe['baseline_hashes']
    source = code_identity()['source_sha256']
    assert source == '84eff3cde04c0e9a1756a3d29c44ec82e115a1a08575132686a02520333e2b5c'
    # Reconstruct the exact sampling rule; these are shared row IDs, not new trials.
    rng = np.random.default_rng(8001)
    orders = np.stack([rng.permutation(5000)[:2000] for _ in range(20)])
    membership = np.zeros((20, 5000), dtype=np.int64)
    for i, order in enumerate(orders):
        assert len(np.unique(order)) == 2000
        membership[i, order] = 1
    matrix = membership @ membership.T
    overlaps = matrix[np.triu_indices(20, 1)]
    # Independent set-intersection implementation checks every pair.
    for i in range(20):
        for j in range(i + 1, 20):
            assert matrix[i, j] == len(set(orders[i]) & set(orders[j]))
    original = np.load(old / 'splits.npz')
    train, validation = make_splits(50000, 45000, 5000, 2026)
    assert np.array_equal(validation, original['validation'])
    assert np.isin(original['training'], train).all()
    assert not np.intersect1d(train, validation).size
    assert len(np.union1d(train, validation)) == 50000
    np.savez_compressed(OUT / 'sampling_and_proposed_splits.npz', orders=orders,
                        overlaps=matrix, proposed_training=train, validation=validation)
    result = {
        'scope': 'Saved-evidence and sampling correctness audit; no new physical experiment',
        'input_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in paths},
        'production_source_sha256': source, 'original_baseline_hashes': preserved,
        'sampling': {'seed': 8001, 'pool_size': 5000, 'budget': 2000, 'orders': 20,
                     'pairs_checked': 190, 'shared_rows_min': int(overlaps.min()),
                     'shared_rows_mean': float(overlaps.mean()), 'shared_rows_max': int(overlaps.max()),
                     'expected_shared_rows_under_sampling_rule': 800,
                     'unique_rows_across_orders': int(np.count_nonzero(membership.sum(0))),
                     'interpretation': 'Conditional trace-order summaries, not twenty independent keys or acquisitions; overlap does not estimate outcome correlation or effective sample size'},
        'proposed_split_checks': {'training': 45000, 'validation': 5000,
                                 'original_training_nested': True, 'same_validation': True,
                                 'disjoint': True, 'new_unviewed_confirmation': False,
                                 'training_exposures_50epochs': 2250000,
                                 'updates_batch50_50epochs': 45000,
                                 'status': 'Proposal only; budget expansion not executed'},
        'attack_payloads_read': False, 'trace_payloads_read': False,
        'new_gpu_trainings': 0, 'new_neural_optimizer_updates': 0,
        'unused_variable_profiling_rows_unchanged': 30000,
        'paper_ready': False, 'novelty_verified': False,
        'seconds': time.perf_counter() - started,
        'script_sha256': sha(Path(__file__)),
        'arrays_sha256': sha(OUT / 'sampling_and_proposed_splits.npz')}
    (OUT / 'audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('sampling', 'proposed_split_checks', 'seconds')}, indent=2))


if __name__ == '__main__':
    main()
