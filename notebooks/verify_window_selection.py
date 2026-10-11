"""Independent direct window selection, weights, OOB and fresh coefficient replay."""
from datetime import datetime
import json
import time
import xml.etree.ElementTree as ET

import h5py
import numpy as np
import torch
from sca.train import code_identity, write_json
from paper_alignment import ROOT, read, sha
from verify_training_alignment import direct_offsets

OUT = ROOT / "outputs/paper_window_selection_2026-10-09"
OLD = ROOT / "outputs/paper_selection_stability_2026-10-06"
ALIGN = ROOT / "outputs/paper_training_alignment_2026-10-06"
FEATURES = ["point", "box_product", "covariance_rank1"]
HW = np.array([v.bit_count() for v in range(256)])


def corr(a,b):
    a,b=np.asarray(a,float),np.asarray(b,float)
    a,b=a-a.mean(),b-b.mean()
    norm=np.linalg.norm(a)*np.linalg.norm(b)
    return float(np.dot(a,b)/norm) if norm else 0.


def direct_products(x, center, pair, delta, weights):
    a,b=[np.arange(p-5,p+6) for p in pair]
    aa=np.take_along_axis(x,a[None,:]+delta[:,None],1)-center[a]
    bb=np.take_along_axis(x,b[None,:]+delta[:,None],1)-center[b]
    return np.einsum('ni,nj->nij',aa,bb).reshape(len(x),121) @ np.column_stack([weights[k] for k in FEATURES])


def search(x,y,box):
    center=x.mean(0)
    if box:
        # Sum explicit columns, independently of sliding_window_view implementation.
        z=sum(x[:,25+d:x.shape[1]-25+d]-center[25+d:x.shape[1]-25+d] for d in range(-5,6))/11
    else:
        z=x[:,25:-25]-center[25:-25]
    n=len(x);h=y-y.mean();m=z.T@z/n
    variance=np.maximum(np.square(z).T@np.square(z)/n-m*m,0.)
    covariance=(z*h[:,None]).T@z/n;den=np.sqrt(variance*np.mean(h*h))
    matrix=np.clip(np.divide(covariance,den,out=np.zeros_like(covariance),where=den>0),-1,1)
    a,b=np.triu_indices(z.shape[1],k=50);scores=abs(matrix[a,b]);candidates=np.column_stack([a,b])
    first=candidates[scores.argmax()]
    allowed=np.ones(len(a),bool)
    for p in first:
        allowed &= (abs(a-p)>=20)&(abs(b-p)>=20)
    second=candidates[np.flatnonzero(allowed)[scores[allowed].argmax()]]
    return {'pair1':(first+25).tolist(),'pair2':(second+25).tolist()},matrix


def main():
    torch.set_num_threads(2)
    start=time.perf_counter()
    plan,fit,result=[read(OUT/n) for n in ('plan.json','fit.json','results.json')]
    assert result['plan_sha256']==sha(OUT/'plan.json')
    assert result['fit_sha256']==sha(OUT/'fit.npz') and result['arrays_sha256']==sha(OUT/'arrays.npz')
    assert sha(ROOT/'notebooks/paper_window_selection.py')==plan['script_sha256']
    assert sha(OUT/'splits.npz')==plan['splits_sha256']
    assert code_identity()['source_sha256']==plan['production_source_sha256']
    for path,digest in plan['input_hashes'].items():assert sha(ROOT/path)==digest,path
    with np.load(OUT/'splits.npz',allow_pickle=False) as f:splits={k:f[k] for k in f.files}
    with np.load(OLD/'fit.npz',allow_pickle=False) as f:baseline={k:f[k] for k in f.files}
    with np.load(OUT/'fit.npz',allow_pickle=False) as f:new={k:f[k] for k in f.files}
    with np.load(OUT/'arrays.npz',allow_pickle=False) as f:arrays={k:f[k] for k in f.files}
    with np.load(ALIGN/'fit.npz',allow_pickle=False) as f:original={k:f[k] for k in f.files}
    oldfit=read(OLD/'fit.json')
    prior=np.array([],int)
    for i,row in enumerate(plan['exclusion_provenance']):
        assert sha(ROOT/row['path'])==row['sha256']
        with np.load(ROOT/row['path'],allow_pickle=False) as f:
            if i==0:keys=['training','validation']
            elif i<3:
                np.testing.assert_array_equal(f['variable__excluded'],prior)
                keys=[k for k in f.files if k.startswith('variable__') and 'attack' not in k]
            else:
                np.testing.assert_array_equal(f['excluded'],prior);keys=f.files
            prior=np.unique(np.concatenate([f[k] for k in keys]))
        assert len(prior)==row['union_rows']
    np.testing.assert_array_equal(prior,splits['excluded'])
    assert len(prior)==150000
    for name,seed in [('primary',20261020),('replication',20261021)]:
        rng=np.random.default_rng(seed)
        expected=np.sort(rng.choice(np.setdiff1d(np.arange(200000),prior),10000,replace=False))
        np.testing.assert_array_equal(expected,splits[name]);prior=np.union1d(prior,expected)
    assert len(prior)==170000
    rng=np.random.default_rng(2026);draws=rng.integers(0,10000,(20,10000),dtype=np.int32)
    np.testing.assert_array_equal(draws,new['draw_indices']);np.testing.assert_array_equal(draws,baseline['draw_indices'])
    assert datetime.fromisoformat(plan['frozen_utc'])<datetime.fromisoformat(read(OUT/'training_access.json')['started_utc'])
    assert datetime.fromisoformat(fit['finished_utc'])<datetime.fromisoformat(read(OUT/'evaluation_access.json')['started_utc'])
    with h5py.File(ROOT/plan['dataset'],'r') as f:
        x=f['Profiling_traces/traces'][splits['training']].astype(float)
        y=HW[f['Profiling_traces/labels'][splits['training']]]
    np.testing.assert_array_equal(y,new['training_target'])
    columns=np.arange(1400)[None,:]+original['training_offsets'][:,None]
    aligned=np.where((columns>=0)&(columns<1400),np.take_along_axis(x,columns.clip(0,1399),1),0.)
    training_weights=0;oob_checks=0;selected_checks=0
    oob_lookup={(r['draw'],r['selector'],r['family'],r['feature']):r['correlation'] for r in fit['oob_coefficients']}
    for number,ids in enumerate(draws):
        xx,yy=aligned[ids],y[ids];center=xx.mean(0);fp='draw'+str(number)
        np.testing.assert_array_equal(center,new[fp+'__center'])
        oob=np.flatnonzero(np.bincount(ids,minlength=10000)==0)
        np.testing.assert_array_equal(oob,new[fp+'__oob'])
        for selector,bundle,row,box in [('point_selector',baseline,oldfit['draws'][number],False),('box_selector',new,fit['draws'][number],True)]:
            pairs,matrix=search(xx,yy,box)
            assert pairs==row['pairs'] and row['eligible_candidates']==845650
            for family,pair in pairs.items():
                a,b=[np.arange(p-5,p+6) for p in pair]
                products=np.einsum('ni,nj->nij',xx[:,a]-center[a],xx[:,b]-center[b]).reshape(10000,121)
                covariance=np.mean((products-products.mean(0))*(yy-yy.mean())[:,None],0)
                u,s,vh=np.linalg.svd(covariance.reshape(11,11),full_matrices=False)
                point=np.zeros(121);point[60]=1
                weights={'point':point,'box_product':np.ones(121),'covariance_rank1':np.outer(u[:,0],vh[0]).ravel()}
                for feature,w in weights.items():
                    w=w/np.linalg.norm(w)
                    if corr(products@w,yy)<0:w=-w
                    np.testing.assert_allclose(w,bundle[fp+'__'+family+'__'+feature],atol=1e-10)
                    weights[feature]=w;training_weights+=1
                    np.testing.assert_allclose(corr(products@w,yy),row['features'][family]['training_correlations'][feature],atol=1e-12)
                score=corr(products[:,60] if not box else products.mean(1),yy)
                np.testing.assert_allclose(score,row['selection_coefficients'][family],atol=1e-12);selected_checks+=1
                direct=direct_products(aligned[oob],center,pair,np.zeros(len(oob),int),weights)
                np.testing.assert_allclose(direct,new[fp+'__'+selector+'__'+family+'__oob_products'],atol=1e-9,rtol=1e-11)
                for j,feature in enumerate(FEATURES):
                    np.testing.assert_allclose(corr(direct[:,j],y[oob]),oob_lookup[(number,selector,family,feature)],atol=1e-12);oob_checks+=1
        print('Independent paired selector replay:',number+1,'/20',flush=True)
    lookup={(r['pool'],r['condition'],r['draw'],r['selector'],r['family'],r['feature']):r['correlation'] for r in result['correlations']}
    fresh_checks=0;offset_checks=0
    template={'mean':original['raw__mean'],'variance':original['raw__variance']}
    for pool in ('primary','replication'):
        assert datetime.fromisoformat(fit['finished_utc'])<datetime.fromisoformat(read(OUT/(pool+'_access.json'))['started_utc'])
        with h5py.File(ROOT/plan['dataset'],'r') as f:
            x=f['Profiling_traces/traces'][splits[pool]].astype(float);y=HW[f['Profiling_traces/labels'][splits[pool]]]
        np.testing.assert_array_equal(y,arrays[pool+'__target'])
        ur,zr=np.random.default_rng(9101),np.random.default_rng(9102)
        u,z=ur.random(len(x)),zr.standard_normal(x.shape)
        assert result['rng_states'][pool]=={'uniform':ur.bit_generator.state,'normal':zr.bit_generator.state}
        for condition in plan['conditions']:
            name,bound=condition['name'],condition['max_shift'];prefix=pool+'__'+name
            d=(np.floor(u*(2*bound+1))-bound).astype(int)
            cols=np.arange(1400)[None,:]-d[:,None]
            values=np.where((cols>=0)&(cols<1400),np.take_along_axis(x,cols.clip(0,1399),1),0.)+z*condition['noise_factor']*48
            offsets=arrays[prefix+'__offsets']
            sample=np.unique(np.r_[np.arange(0,10000,503),[999,1000,1999,2000,9999]])
            np.testing.assert_array_equal(direct_offsets(values[sample],template['mean'],template['variance']),offsets[sample]);offset_checks+=len(sample)
            for number in range(20):
                fp='draw'+str(number)
                for selector,bundle,row in [('point_selector',baseline,oldfit['draws'][number]),('box_selector',new,fit['draws'][number])]:
                    for family,pair in row['pairs'].items():
                        weights={k:bundle[fp+'__'+family+'__'+k] for k in FEATURES}
                        direct=direct_products(values,new[fp+'__center'],pair,offsets,weights)
                        np.testing.assert_allclose(direct,arrays[prefix+'__'+fp+'__'+selector+'__'+family],atol=1e-9,rtol=1e-11)
                        for j,feature in enumerate(FEATURES):
                            np.testing.assert_allclose(corr(direct[:,j],y),lookup[(pool,name,number,selector,family,feature)],atol=1e-12);fresh_checks+=1
            print('Independent fresh coefficient replay:',pool,name,flush=True)
    primary_pass=True
    for row in result['summaries']:
        values=[[lookup[(row['pool'],row['condition'],i,sel,row['family'],row['feature'])] for i in range(20)] for sel in ('point_selector','box_selector')]
        b,a=map(np.asarray,values)
        np.testing.assert_allclose([row['baseline_median'],row['window_median'],row['median_paired_difference']],[np.median(b),np.median(a),np.median(a-b)],atol=1e-12)
        assert row['window_positive_draws']==int((a>0).sum()) and row['baseline_positive_draws']==int((b>0).sum())
        if row['condition']=='clean' and row['feature']=='box_product':
            passed=np.median(a-b)>=-.01 if row['family']=='pair1' else np.median(a-b)>=.02 and np.median(a)>=.05 and (a>0).sum()>=16
            primary_pass &= bool(passed)
    assert result['H1_primary_met']==primary_pass
    h2=True
    for row in result['oob_prediction']:
        internal=np.median([oob_lookup[(i,row['selector'],'pair2',row['feature'])] for i in range(20)])
        fresh=np.median([lookup[(row['pool'],'clean',i,row['selector'],'pair2',row['feature'])] for i in range(20)])
        np.testing.assert_allclose([row['oob_median'],row['fresh_median']],[internal,fresh],atol=1e-12)
        passed=abs(internal-fresh)<=.02 and (internal>=.05)==(fresh>=.05)
        assert row['support']==passed;h2 &= bool(passed)
    assert result['H2_secondary_met']==h2
    for path,digest in plan['input_hashes'].items():assert sha(ROOT/path)==digest,path
    junit=ET.parse(OUT/'pytest.xml').getroot();suites=junit.findall('testsuite')
    assert sum(int(s.attrib.get('failures',0))+int(s.attrib.get('errors',0)) for s in suites)==0
    record={'verified':True,'seconds':time.perf_counter()-start,'full_searches':40,'training_weight_vectors':training_weights,
        'selected_coefficients':selected_checks,'oob_coefficients':oob_checks,'fresh_coefficients':fresh_checks,
        'sampled_offset_checks':offset_checks,'all_split_unions_replayed':True,'H1_primary_met':primary_pass,
        'H2_secondary_met':h2,'passing_tests':sum(int(s.attrib['tests']) for s in suites),
        'no_attack_reads':True,'remaining_unused_rows':30000,'source_preserved':True,
        'artifacts_sha256':{n:sha(OUT/n) for n in ['plan.json','splits.npz','fit.json','fit.npz','results.json','arrays.npz','pytest.xml']}}
    write_json(OUT/'verification.json',record)
    print(json.dumps({k:v for k,v in record.items() if k!='artifacts_sha256'},indent=2),flush=True)


if __name__=='__main__':main()
