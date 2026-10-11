"""Recompute all locked attack ranks with independent formulas and retain negatives."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from sca.aes import SBOX
from sca.data import sha256_file
from sca.train import write_json
from paper_confirmation import OUT, read, require_authorization


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attack-output',type=Path,required=True)
    args = parser.parse_args()
    artifact, started = args.attack_output, time.perf_counter()
    plan, authorization = read(OUT/'plan.json'), read(OUT/'authorization.json')
    require_authorization(plan,authorization,'attack_evaluation')
    result = read(artifact/'results.json')
    config = plan['attack_config']
    assert result['complete']
    assert result['model_corrupted_inputs_sha256']['baseline'] == result['model_corrupted_inputs_sha256']['combined']
    assert result['common_corrupted_inputs_sha256'] == result['model_corrupted_inputs_sha256']['baseline']
    assert len(result['common_corrupted_inputs_sha256']) == len(config['conditions'])
    assert result['attack_orders_sha256'] == sha256_file(artifact/'attack_orders.npy')
    saved_orders = np.load(artifact/'attack_orders.npy')
    plaintext_reference,key_reference = None,None
    summaries, endpoints = {}, {}
    for label in ('baseline','combined'):
        plaintext = np.load(artifact/label/'plaintext_byte.npy')
        key = read(artifact/label/'evaluation_key.json')['true_key_byte']
        assert len(plaintext) == 10000
        if plaintext_reference is None:
            plaintext_reference,key_reference = plaintext,key
        else:
            assert np.array_equal(plaintext,plaintext_reference) and key == key_reference
        labels = SBOX[plaintext[:,None] ^ np.arange(256,dtype=np.uint8)[None,:]]
        summaries[label] = {r['condition']:r for r in result['models'][label]}
        for condition in config['conditions']:
            name = condition['name']
            lp = np.load(artifact/label/(name+'_log_probabilities.npy'))
            assert lp.shape == (10000,256) and np.isfinite(lp).all()
            np.testing.assert_allclose(np.exp(lp).sum(axis=1),1.,rtol=0,atol=1e-12)
            ranks, rng = [], np.random.default_rng(config['attack_order_seed'])
            for repetition in range(config['repetitions']):
                order = rng.permutation(len(lp))[:config['budget']]
                assert np.array_equal(order,saved_orders[repetition])
                scores = np.add.accumulate(lp[order[:,None],labels[order]],axis=0)
                ranks.append(np.count_nonzero(scores >= scores[:,key,None],axis=1)-1)
            ranks = np.asarray(ranks)
            saved = np.load(artifact/label/(name+'_curves.npz'))
            assert np.array_equal(ranks,saved['ranks'])
            sr,ge = (ranks == 0).mean(axis=0), ranks.mean(axis=0)
            assert np.array_equal(sr,saved['sr']) and np.array_equal(ge,saved['ge'])
            summary = summaries[label][name]
            assert float(sr[-1]) == summary['sr_at_budget'] and float(ge[-1]) == summary['ge_at_budget']
            sustained = np.flatnonzero(np.minimum.accumulate(sr[::-1])[::-1] >= .9)
            assert summary['traces_to_sustained_success'] == (int(sustained[0]+1) if len(sustained) else None)
            endpoints[label,name] = ranks[:,-1] == 0
    for name in [c['name'] for c in config['conditions']]:
        baseline,combined = endpoints['baseline',name], endpoints['combined',name]
        paired = result['paired'][name]
        assert paired['baseline_only'] == int(np.count_nonzero(baseline & ~combined))
        assert paired['combined_only'] == int(np.count_nonzero(~baseline & combined))
        assert paired['both_success'] == int(np.count_nonzero(baseline & combined))
        assert paired['neither_success'] == int(np.count_nonzero(~baseline & ~combined))
        assert paired['delta_sr'] == float(combined.mean()-baseline.mean())
    h1 = summaries['baseline']['clean']['sr_at_budget'] >= .9
    h2 = (summaries['combined']['combined_both_ood']['sr_at_budget'] >= .9 and
          result['paired']['combined_both_ood']['delta_sr'] > 0 and summaries['combined']['clean']['sr_at_budget'] >= .9)
    assert result['baseline_clean_confirmation_met'] == h1 and result['augmentation_joint_primary_met'] == h2
    assert result['new_optimizer_updates'] == 0 and not result['selection_from_attack']
    record = {'verified':True,'rank_prefixes_verified':2*8*100*2000,
              'baseline_clean_confirmation_met':bool(h1),'augmentation_joint_primary_met':bool(h2),
              'conditional_orders_not_independent_keys':True,'new_optimizer_updates':0,
              'seconds':time.perf_counter()-started,
              'artifact_sha256':{p.relative_to(artifact).as_posix():sha256_file(p) for p in artifact.rglob('*') if p.is_file()}}
    write_json(OUT/'attack_verification.json',record)
    print(json.dumps({k:v for k,v in record.items() if k != 'artifact_sha256'},indent=2))


if __name__ == '__main__':
    main()
