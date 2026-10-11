"""Independently verify schedule, saved GPU ranks, CPU inference, and preservation."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
import h5py

from sca.aes import SBOX
from sca.data import load_profiling, normalize, fit_normalizer
from sca.models import build_model
from sca.train import code_identity, write_json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/kaggle_budget_2026-10-11'
OLD=ROOT/'runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0'


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',type=Path,required=True)
    args=parser.parse_args()
    started=time.perf_counter()
    artifact=args.download
    plan=read(OUT/'plan.json')
    assert read(artifact/'plan.json')==plan
    for name,digest in plan['input_hashes'].items():assert sha(ROOT/name)==digest,name
    assert code_identity()['source_sha256']==plan['production_source_sha256']
    assert {n:sha(OLD/n) for n in plan['baseline_hashes']}==plan['baseline_hashes']
    result=read(artifact/'results.json')
    run=artifact/'none_seed0'
    history=read(run/'history.json')
    best=torch.load(run/'best.pt',map_location='cpu',weights_only=False)
    last=torch.load(run/'last.pt',map_location='cpu',weights_only=False)
    assert len(history)==50 and last['epoch']==50 and last['steps']==45000
    assert best['epoch']==int(np.argmin([r['validation_loss'] for r in history]))+1
    assert best['best_loss']==min(r['validation_loss'] for r in history)
    rates=np.load(artifact/'learning_rates.npy')
    expected=np.interp(np.arange(45000),[0,18000,36000,45000],[.0005,.005,.0005,.000005])
    np.testing.assert_allclose(rates,expected,rtol=1e-12,atol=1e-18)
    assert last['optimizer']['author_cycle']['completed_updates']==45000
    assert last['config']['recipe_extension_sha256']==plan['extension_sha256']
    splits=np.load(run/'splits.npz')
    old_splits=np.load(OLD/'splits.npz')
    assert np.array_equal(splits['validation'],old_splits['validation'])
    assert np.isin(old_splits['training'],splits['training']).all()
    assert len(splits['training'])==45000
    assert not np.intersect1d(splits['training'],splits['validation']).size
    xt,yt,xv,yv=load_profiling(ROOT/'data/ASCAD.h5',splits['training'],splits['validation'])
    assert best['normalizer']==fit_normalizer(xt,'feature_minmax_training_only')
    lp=np.load(artifact/'validation/log_probabilities.npy')
    plaintext=np.load(artifact/'validation/plaintext_byte.npy')
    key=read(artifact/'validation/evaluation_key.json')['true_key_byte']
    with h5py.File(ROOT/'data/ASCAD.h5','r') as handle:
        metadata=handle['Profiling_traces/metadata'][splits['validation']]
    assert np.array_equal(plaintext,metadata['plaintext'][:,2])
    assert np.array_equal(np.unique(metadata['key'][:,2]),[key])
    labels=SBOX[np.asarray(plaintext,dtype=np.uint8)[:,None]^np.arange(256,dtype=np.uint8)[None,:]]
    rng=np.random.default_rng(8001)
    ranks=[]
    for _ in range(20):
        order=rng.permutation(5000)[:2000]
        increments=lp[order[:,None],labels[order]]
        scores=np.add.accumulate(increments,axis=0)
        ranks.append(np.count_nonzero(scores>=scores[:,key,None],axis=1)-1)
    ranks=np.asarray(ranks,dtype=np.int16)
    saved=np.load(artifact/'validation/clean_curves.npz')
    assert np.array_equal(ranks,saved['ranks'])
    assert np.array_equal(ranks.mean(axis=0),saved['ge'])
    assert np.array_equal((ranks==0).mean(axis=0),saved['sr'])
    sr=float((ranks[:,-1]==0).mean());ge=float(ranks[:,-1].mean())
    assert sr==result['validation'][0]['sr_at_budget'] and ge==result['validation'][0]['ge_at_budget']
    assert result['primary_met']==(sr>=.9)
    torch.set_num_threads(2)
    model=build_model('cnn_literature')
    model.load_state_dict(best['model']);model.eval()
    normalized=normalize(xv,best['normalizer'])
    with torch.no_grad():
        cpu_lp=np.concatenate([torch.log_softmax(model(torch.from_numpy(normalized[i:i+256])).double(),dim=1).numpy() for i in range(0,5000,256)])
    error=float(np.max(np.abs(cpu_lp-lp)))
    assert error<1e-4,error
    ce=float(-cpu_lp[np.arange(5000),yv].mean())
    assert abs(ce-best['best_loss'])<1e-5
    assert result['full_gpu_trainings_total']==5 and result['new_gpu_trainings']==1
    assert not result['combined_training_performed'] and not result['attack_payloads_read']
    record={'verified':True,'primary_met':result['primary_met'],'sr_at_2000':sr,'ge_at_2000':ge,
        'best_epoch':best['epoch'],'minimum_validation_ce':best['best_loss'],'cpu_validation_ce':ce,
        'schedule_values_verified':45000,'rank_prefixes_verified':40000,'gpu_predictions_verified':5000,
        'cpu_gpu_max_logprob_error':error,'source_preserved':True,'old_checkpoints_preserved':True,
        'original_notebook_v8_preserved':True,'new_confirmation_rows':0,'variable_unused_rows':30000,
        'full_gpu_trainings_total':5,'attack_payloads_read':False,'seconds':time.perf_counter()-started,
        'artifact_sha256':{str(p.relative_to(artifact)).replace('\\','/'):sha(p) for p in artifact.rglob('*') if p.is_file()},
        'plan_sha256':sha(OUT/'plan.json')}
    write_json(OUT/'verification.json',record)
    print(json.dumps({k:v for k,v in record.items() if k!='artifact_sha256'},indent=2))


if __name__=='__main__':main()
