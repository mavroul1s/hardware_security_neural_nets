"""Verify the single proposed combined training without opening attack payloads."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import torch
from sca.aes import SBOX
from sca.data import fit_normalizer, load_profiling, load_validation_evaluation, normalize, sha256_file
from sca.models import build_model
from sca.train import write_json
from paper_confirmation import OUT, ROOT, REFERENCE, read, verify_reference, require_authorization


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',type=Path,required=True)
    args = parser.parse_args()
    artifact, started = args.download, time.perf_counter()
    plan, auth = read(OUT/'plan.json'), read(OUT/'authorization.json')
    require_authorization(plan,auth,'combined_training')
    verify_reference(REFERENCE,plan)
    assert sha256_file(ROOT/'data/ASCAD.h5') == plan['dataset_sha256']
    assert read(artifact/'plan.json') == plan and read(artifact/'authorization.json') == auth
    result = read(artifact/'results.json')
    assert result['complete'] and result['new_gpu_trainings'] == 1 and result['full_gpu_trainings_total'] == 6
    assert not result['attack_payloads_read']
    run = artifact/'combined_seed0'
    best = torch.load(run/'best.pt',map_location='cpu',weights_only=False)
    last = torch.load(run/'last.pt',map_location='cpu',weights_only=False)
    reference = torch.load(REFERENCE/'best.pt',map_location='cpu',weights_only=False)
    history = read(run/'history.json')
    assert len(history) == 50 and last['epoch'] == 50 and last['steps'] == 45000
    assert best['epoch'] == np.argmin([r['validation_loss'] for r in history])+1
    assert best['best_loss'] == min(r['validation_loss'] for r in history)
    assert best['normalizer'] == reference['normalizer']
    for state in (best,last):
        for name,value in plan['training_scope'].items():assert state['config'][name] == value, name
        assert state['code']['source_sha256'] == plan['production_source_sha256']
        assert state['dataset_sha256'] == plan['dataset_sha256'] and not state['synthetic']
    splits, original = np.load(run/'splits.npz'), np.load(REFERENCE/'splits.npz')
    assert all(np.array_equal(splits[k],original[k]) for k in ('training','validation'))
    assert not np.intersect1d(splits['training'],splits['validation']).size
    xt,yt,xv,yv = load_profiling(ROOT/'data/ASCAD.h5',splits['training'],splits['validation'])
    assert fit_normalizer(xt,'feature_minmax_training_only') == best['normalizer']
    rates = np.load(artifact/'learning_rates.npy')
    expected = np.interp(np.arange(45000),[0,18000,36000,45000],[.0005,.005,.0005,.000005])
    np.testing.assert_allclose(rates,expected,rtol=1e-12,atol=1e-18)
    assert last['optimizer']['author_cycle']['completed_updates'] == 45000
    lp = np.load(artifact/'validation/log_probabilities.npy')
    plaintext = np.load(artifact/'validation/plaintext_byte.npy')
    key = read(artifact/'validation/evaluation_key.json')['true_key_byte']
    _,expected_plaintext,expected_key = load_validation_evaluation(ROOT/'data/ASCAD.h5',splits['validation'],2)
    assert np.array_equal(plaintext,expected_plaintext) and key == expected_key
    assert lp.shape == (5000,256) and np.isfinite(lp).all()
    np.testing.assert_allclose(np.exp(lp).sum(axis=1),1.,rtol=0,atol=1e-12)
    ranks = []
    labels = SBOX[plaintext[:,None] ^ np.arange(256,dtype=np.uint8)[None,:]]
    rng = np.random.default_rng(8001)
    for _ in range(20):
        order = rng.permutation(5000)[:2000]
        scores = np.add.accumulate(lp[order[:,None],labels[order]],axis=0)
        ranks.append(np.count_nonzero(scores >= scores[:,key,None],axis=1)-1)
    saved = np.load(artifact/'validation/clean_curves.npz')
    assert np.array_equal(ranks,saved['ranks'])
    ranks = np.asarray(ranks)
    sr,ge = (ranks == 0).mean(axis=0),ranks.mean(axis=0)
    assert np.array_equal(sr,saved['sr']) and np.array_equal(ge,saved['ge'])
    validation = read(artifact/'validation/results.json')[0]
    assert float(sr[-1]) == validation['sr_at_budget'] and float(ge[-1]) == validation['ge_at_budget']
    sustained = np.flatnonzero(np.minimum.accumulate(sr[::-1])[::-1] >= .9)
    assert validation['traces_to_sustained_success'] == (int(sustained[0]+1) if len(sustained) else None)
    assert result['validation'] == [validation]
    torch.set_num_threads(2)
    model = build_model('cnn_literature');model.load_state_dict(best['model']);model.eval()
    normalized = normalize(xv,best['normalizer'])
    with torch.no_grad():
        cpu_lp = np.concatenate([torch.log_softmax(model(torch.from_numpy(normalized[i:i+256])).double(),dim=1).numpy()
                                 for i in range(0,5000,256)])
    error = float(np.max(np.abs(cpu_lp-lp)))
    assert error < 1e-4
    assert abs(float(-cpu_lp[np.arange(5000),yv].mean())-best['best_loss']) < 1e-5
    record = {'verified':True,'attack_payloads_read':False,'new_gpu_trainings':1,'full_gpu_trainings_total':6,
              'schedule_values_verified':45000,'rank_prefixes_verified':40000,'cpu_predictions_verified':5000,
              'best_epoch':int(best['epoch']),'minimum_validation_ce':best['best_loss'],
              'clean_validation_sr_at_2000':float(sr[-1]),'clean_validation_ge_at_2000':float(ge[-1]),
              'recorded_runtime_matches_baseline':best['environment'] == reference['environment'],
              'cpu_gpu_max_logprob_error':error,'seconds':time.perf_counter()-started,
              'artifact_sha256':{p.relative_to(artifact).as_posix():sha256_file(p) for p in artifact.rglob('*') if p.is_file()}}
    write_json(OUT/'training_verification.json',record)
    print(json.dumps({k:v for k,v in record.items() if k != 'artifact_sha256'},indent=2))


if __name__ == '__main__':
    main()
