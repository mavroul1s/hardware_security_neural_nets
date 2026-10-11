"""Independent direct-feature and row/cluster bootstrap replay of larger confirmation."""
from datetime import datetime
import json
import time
import xml.etree.ElementTree as ET
import h5py
import numpy as np
from sca.train import code_identity,write_json
from paper_alignment import ROOT,read,sha
from verify_window_regression import corr

OUT=ROOT/"outputs/paper_precision_replication_2026-10-06"
PREVIOUS=ROOT/"outputs/paper_window_regression_2026-10-06"
HW=np.array([v.bit_count() for v in range(256)])


def aggregate_delta(m):
    # Direct Pearson form n*sxy-sx*sy rather than the experiment's centered sums.
    n,sa,sb,sy,saa,sbb,syy,say,sby=np.moveaxis(m,-1,0)
    va=np.maximum(n*saa-sa*sa,0);vb=np.maximum(n*sbb-sb*sb,0);vy=np.maximum(n*syy-sy*sy,0)
    da,db=np.sqrt(va*vy),np.sqrt(vb*vy)
    return np.divide(n*say-sa*sy,da,out=np.zeros_like(da),where=da>0)-np.divide(n*sby-sb*sy,db,out=np.zeros_like(db),where=db>0)


def main():
    started=time.perf_counter();plan,record,access=[read(OUT/n) for n in ("plan.json","results.json","evaluation_access.json")]
    assert record["plan_sha256"]==access["plan_sha256"]==sha(OUT/"plan.json")
    assert record["access_sha256"]==sha(OUT/"evaluation_access.json") and record["arrays_sha256"]==sha(OUT/"arrays.npz")
    assert datetime.fromisoformat(plan["frozen_utc"])<datetime.fromisoformat(access["started_utc"])
    assert sha(PREVIOUS/"fit.npz")==access["immutable_fit_sha256"]
    assert sha(ROOT/"notebooks/paper_precision_replication.py")==plan["script_sha256"]
    assert code_identity()["source_sha256"]==plan["production_source_sha256"]==record["production_source_sha256"]
    for relative,expected in plan["input_hashes"].items():assert sha(ROOT/relative)==expected,relative
    assert not access["attack_payloads_or_metadata_read"] and not record["new_attack_reads"]
    with np.load(OUT/"splits.npz",allow_pickle=False) as f:splits={n:f[n] for n in f.files}
    with np.load(PREVIOUS/"splits.npz",allow_pickle=False) as f:
        excluded=np.unique(np.concatenate([f["variable__"+n] for n in ("excluded","primary","replication")]))
    np.testing.assert_array_equal(excluded,splits["excluded"])
    for pool,seed in (("primary",20261014),("replication",20261015)):
        candidates=np.setdiff1d(np.arange(200000),excluded)
        expected=np.sort(np.random.default_rng(seed).choice(candidates,20000,replace=False))
        np.testing.assert_array_equal(expected,splits[pool]);excluded=np.union1d(excluded,expected)
    assert len(excluded)==70000
    lookup={(r["pool"],r["condition"],r["alignment"],r["family"],r["feature"]):r for r in record["correlations"]}
    coefficient_checks,bootstrap_checks,cluster_row_replays,alignment_checks=0,0,0,0
    with np.load(PREVIOUS/"fit.npz",allow_pickle=False) as fits,np.load(OUT/"arrays.npz",allow_pickle=False) as arrays:
        center,variance=fits["variable__mean"],fits["variable__variance"]
        raw_range=read(PREVIOUS/"fit.json")["campaigns"]["variable"]["median_training_feature_range"]
        for pool in ("primary","replication"):
            with h5py.File(ROOT/plan["dataset"],"r") as f:
                x=f["Profiling_traces/traces"][splits[pool]].astype(float)
                y=HW[f["Profiling_traces/labels"][splits[pool]]]
            np.testing.assert_array_equal(y,arrays[pool+"__target"])
            ur,zr=np.random.default_rng(9101),np.random.default_rng(9102)
            u,z=ur.random(len(x)),zr.standard_normal(x.shape)
            assert record["rng_states"][pool]["uniform"]==ur.bit_generator.state and record["rng_states"][pool]["normal"]==zr.bit_generator.state
            for condition in plan["conditions"]:
                name,bound=condition["name"],condition["max_shift"]
                injected=np.floor(u*(2*bound+1)).astype(int)-bound
                columns=np.arange(1400)[None,:]-injected[:,None]
                values=np.where((columns>=0)&(columns<1400),np.take_along_axis(x,columns.clip(0,1399),axis=1),0.)+z*condition["noise_factor"]*raw_range
                for method in plan["alignments"]:
                    prefix=pool+"__"+name+"__"+method;delta=arrays[prefix+"__offsets"]
                    if method=="fixed":np.testing.assert_array_equal(delta,np.zeros(len(x),dtype=int))
                    else:
                        # Include rows on either side of the batched alignment boundaries.
                        sample=np.unique(np.concatenate((np.linspace(0,len(x)-1,32,dtype=int),[999,1000,1999,2000])))
                        score_columns=np.arange(20,1380);candidates=sorted(range(-10,11),key=lambda d:(abs(d),d))
                        scores=[]
                        for offset in candidates:
                            v=values[sample][:,score_columns+offset]
                            scores.append(np.mean((v-center[score_columns])**2/variance[score_columns]+np.log(variance[score_columns]),axis=1) if method=="gaussian_template" else np.sum(np.abs(v-center[score_columns]),axis=1))
                        np.testing.assert_array_equal(delta[sample],np.asarray(candidates)[np.argmin(np.column_stack(scores),axis=1)])
                        alignment_checks+=len(sample)
                    for family,pair in plan["pairs"].items():
                        ca,cb=[np.arange(p-5,p+6) for p in pair]
                        a=np.take_along_axis(values,ca[None,:]+delta[:,None],axis=1)-center[ca]
                        b=np.take_along_axis(values,cb[None,:]+delta[:,None],axis=1)-center[cb]
                        products=np.column_stack([np.einsum("ni,ij,nj->n",a,fits["variable__"+family+"__"+f].reshape(11,11),b) for f in plan["features"]])
                        np.testing.assert_allclose(products,arrays[prefix+"__"+family+"__products"],atol=1e-10,rtol=1e-10)
                        for j,f in enumerate(plan["features"]):
                            np.testing.assert_allclose(corr(products[:,j],y),lookup[(pool,name,method,family,f)]["hw_correlation"],atol=1e-12)
                            coefficient_checks+=1
                        if name=="combined5" and method=="gaussian_template" and family=="pair1":
                            a,b=products[:,5],products[:,4]
                            blocks=np.unique(splits[pool]//1000)
                            moments=[]
                            for block in blocks:
                                mask=splits[pool]//1000==block;aa,bb,yy=a[mask],b[mask],y[mask]
                                moments.append([mask.sum(),aa.sum(),bb.sum(),yy.sum(),np.square(aa).sum(),np.square(bb).sum(),np.square(yy).sum(),np.dot(aa,yy),np.dot(bb,yy)])
                            moments=np.array(moments)
                            np.testing.assert_allclose(moments,arrays[pool+"__cluster_moments"],atol=1e-8,rtol=1e-11)
                            np.testing.assert_array_equal(blocks,arrays[pool+"__cluster_blocks"])
                            rng=np.random.default_rng(2026);row_draws=[]
                            for _ in range(9999):
                                ids=rng.integers(0,len(y),len(y))
                                row_draws.append(corr(a[ids],y[ids])-corr(b[ids],y[ids]))
                            row_state=rng.bit_generator.state
                            rng=np.random.default_rng(2026)
                            cluster_ids=rng.integers(0,len(blocks),(9999,len(blocks)))
                            np.testing.assert_array_equal(cluster_ids,arrays[pool+"__cluster_ids"])
                            cluster_draws=aggregate_delta(moments[cluster_ids].sum(axis=1))
                            for index in (0,4999,9998):
                                rows=np.concatenate([np.flatnonzero(splits[pool]//1000==blocks[b]) for b in cluster_ids[index]])
                                np.testing.assert_allclose(cluster_draws[index],corr(a[rows],y[rows])-corr(b[rows],y[rows]),atol=1e-12)
                                cluster_row_replays+=1
                            for scheme,draws,state in (("paired_rows",np.array(row_draws),row_state),("index_clusters",cluster_draws,rng.bit_generator.state)):
                                np.testing.assert_allclose(draws,arrays[pool+"__"+scheme+"__draws"],atol=1e-12)
                                lower,upper=np.quantile(draws,[.01/8,1-.01/8]);difference=corr(a,y)-corr(b,y)
                                row=next(r for r in record["intervals"] if r["pool"]==pool and r["scheme"]==scheme)
                                np.testing.assert_allclose([difference,lower,upper],[row["difference"],row["lower"],row["upper"]],atol=1e-12)
                                assert row["rng_final_state"]==state and row["support"]==bool(difference>=.01 and lower>0)
                                bootstrap_checks+=len(draws)
            print("Larger independent replay:",pool,flush=True)
    assert coefficient_checks==360 and bootstrap_checks==39996 and cluster_row_replays==6 and alignment_checks==720
    assert record["support_met"]==all(r["support"] for r in record["intervals"])
    suite=ET.parse(OUT/"pytest.xml").getroot().find("testsuite")
    tests={n:int(suite.attrib[n]) for n in ("tests","failures","errors","skipped")};tests["seconds"]=float(suite.attrib["time"])
    assert tests["tests"]==82 and tests["failures"]==tests["errors"]==tests["skipped"]==0
    result={"correlation_rows_verified":coefficient_checks,"bootstrap_draws_replayed":bootstrap_checks,
        "sampled_cluster_draws_replayed_with_actual_rows":cluster_row_replays,"sampled_alignment_offsets_replayed":alignment_checks,
        "all_splits_rng_and_moments_replayed":True,"unchanged_fit_verified":True,"variable_used_profiling_rows":70000,
        "new_attack_reads":False,"new_gpu_trainings":0,"new_optimizer_updates":0,"tests":tests,
        "support_met":record["support_met"],"seconds":time.perf_counter()-started,
        "production_source_sha256":record["production_source_sha256"],
        "artifact_sha256":{n:sha(OUT/n) for n in ("plan.json","splits.npz","evaluation_access.json","arrays.npz","results.json","pytest.xml")}}
    write_json(OUT/"verification.json",result)
    print(json.dumps({k:v for k,v in result.items() if k!="artifact_sha256"},indent=2),flush=True)


if __name__=="__main__":main()
