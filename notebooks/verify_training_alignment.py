"""Independent coordinates, selection, fitted weights and fresh confirmation replay."""
from datetime import datetime
import json
import time
import xml.etree.ElementTree as ET
import h5py
import numpy as np
from sca.train import code_identity, write_json
from paper_alignment import ROOT, read, sha
from verify_window_regression import corr
from verify_precision_replication import aggregate_delta

OUT=ROOT/"outputs/paper_training_alignment_2026-10-06"
HW=np.array([v.bit_count() for v in range(256)])


def direct_offsets(x,mean,variance,batch_size=256):
    columns=np.arange(20,x.shape[1]-20)
    candidates=np.array(sorted(range(-10,11),key=lambda d:(abs(d),d)))
    result=[]
    for start in range(0,len(x),batch_size):
        sample=x[start:start+batch_size]
        scores=np.column_stack([np.mean(np.square(sample[:,columns+d]-mean[columns])/variance[columns]
            +np.log(variance[columns]),axis=1) for d in candidates])
        result.extend(candidates[np.argmin(scores,axis=1)])
    return np.asarray(result)


def verify_training(splits,plan,fit,arrays):
    with h5py.File(ROOT/plan["dataset"],"r") as f:
        raw=f["Profiling_traces/traces"][splits["training"]].astype(float)
        y=HW[f["Profiling_traces/labels"][splits["training"]]]
    np.testing.assert_array_equal(y,arrays["training_target"])
    mu,var=raw.mean(0),raw.var(0)
    floor=max(float(np.median(var[10:-10]))*1e-6,1e-12);var=np.maximum(var,floor)
    d=direct_offsets(raw,mu,var)
    np.testing.assert_array_equal(d,arrays["training_offsets"])
    columns=np.arange(1400)[None,:]+d[:,None]
    aligned=np.where((columns>=0)&(columns<1400),np.take_along_axis(raw,columns.clip(0,1399),axis=1),0.)
    pair_checks,weight_checks=0,0
    for stage,x in (("raw",raw),("aligned_once",aligned)):
        center,v=x.mean(0),x.var(0);floor=max(float(np.median(v[10:-10]))*1e-6,1e-12)
        np.testing.assert_array_equal(center,arrays[stage+"__mean"])
        np.testing.assert_array_equal(np.maximum(v,floor),arrays[stage+"__variance"])
        assert floor==fit["stages"][stage]["variance_floor"]
        z=x[:,25:-25]-center[25:-25];h=y-y.mean();n=len(x)
        ep=z.T@z/n;vp=np.maximum(np.square(z).T@np.square(z)/n-ep*ep,0)
        covariance=z.T@(z*h[:,None])/n
        denominator=np.sqrt(vp*np.mean(h*h))
        matrix=np.clip(np.divide(covariance,denominator,out=np.zeros_like(covariance),where=denominator>0),-1,1)
        np.testing.assert_allclose(matrix,arrays[stage+"__selection_correlations"],atol=1e-12)
        a,b=np.triu_indices(1350,k=50);candidates=np.column_stack((a,b));score=np.abs(matrix[a,b])
        first=candidates[score.argmax()]
        allowed=np.all(np.abs(candidates[:,:,None]-first[None,None,:])>=20,axis=(1,2))
        second=candidates[np.flatnonzero(allowed)[score[allowed].argmax()]]
        assert fit["stages"][stage]["eligible_candidates"]==len(candidates)==845650
        for family,points in (("selected_pair1",first+25),("selected_pair2",second+25)):
            np.testing.assert_array_equal(points,fit["stages"][stage]["pairs"][family])
        # Direct individual-product coefficients provide a separate numerical formulation.
        selected_indices=np.linspace(0,len(a)-1,32,dtype=int)
        for idx in selected_indices:
            np.testing.assert_allclose(corr(z[:,a[idx]]*z[:,b[idx]],y),matrix[a[idx],b[idx]],atol=1e-12)
            pair_checks+=1
        for family,pair in fit["stages"][stage]["pairs"].items():
            if family.startswith("old_"):assert pair==plan["old_pairs"][family[4:]]
            ca,cb=[np.arange(p-5,p+6) for p in pair]
            aa,bb=x[:,ca]-center[ca],x[:,cb]-center[cb]
            products=np.einsum("ni,nj->nij",aa,bb).reshape(len(x),-1)
            c=np.mean((products-products.mean(0))*(y-y.mean())[:,None],axis=0)
            np.testing.assert_allclose(c,arrays[stage+"__"+family+"__target_covariance"],atol=1e-9,rtol=1e-12)
            u,s,vh=np.linalg.svd(c.reshape(11,11),full_matrices=False)
            point=np.zeros((11,11));point[5,5]=1
            weights={"point":point.ravel(),"box_product":np.ones(121)/11,
                "covariance_rank1":np.outer(u[:,0],vh[0]).ravel()}
            np.testing.assert_allclose(s,fit["stages"][stage]["features"][family]["singular_values"],atol=1e-9)
            for feature,w in weights.items():
                w=w/np.linalg.norm(w)
                if corr(products@w,y)<0:w=-w
                np.testing.assert_allclose(w,arrays[stage+"__"+family+"__"+feature],atol=1e-11)
                np.testing.assert_allclose(corr(products@w,y),fit["stages"][stage]["features"][family]["training_correlations"][feature],atol=1e-12)
                weight_checks+=1
    assert fit["median_raw_training_feature_range"]==float(np.median(np.ptp(raw,axis=0)))
    return len(d),pair_checks,weight_checks


def main():
    started=time.perf_counter()
    plan,record,fit,access,training_access=[read(OUT/n) for n in ("plan.json","results.json","fit.json","evaluation_access.json","training_access.json")]
    assert record["plan_sha256"]==access["plan_sha256"]==training_access["plan_sha256"]==sha(OUT/"plan.json")
    assert record["fit_sha256"]==access["fit_sha256"]==sha(OUT/"fit.npz")
    assert record["access_sha256"]==sha(OUT/"evaluation_access.json") and record["arrays_sha256"]==sha(OUT/"arrays.npz")
    assert access["fit_record_sha256"]==sha(OUT/"fit.json")
    assert datetime.fromisoformat(plan["frozen_utc"])<datetime.fromisoformat(training_access["started_utc"])<datetime.fromisoformat(fit["finished_utc"])<datetime.fromisoformat(access["started_utc"])
    assert sha(ROOT/"notebooks/paper_training_alignment.py")==plan["script_sha256"]
    assert code_identity()["source_sha256"]==plan["production_source_sha256"]==record["production_source_sha256"]
    for rel,expected in plan["input_hashes"].items():assert sha(ROOT/rel)==expected,rel
    assert not plan["attack_payloads_or_metadata_read"] and not access["attack_payloads_or_metadata_read"] and not record["new_attack_reads"]
    with np.load(OUT/"splits.npz",allow_pickle=False) as f:splits={k:f[k] for k in f.files}
    with np.load(ROOT/"outputs/paper_precision_replication_2026-10-06/splits.npz",allow_pickle=False) as f:
        excluded=np.unique(np.concatenate([f[n] for n in ("excluded","primary","replication")]))
    np.testing.assert_array_equal(excluded,splits["excluded"])
    with np.load(ROOT/"outputs/paper_window_regression_2026-10-06/splits.npz",allow_pickle=False) as f:
        np.testing.assert_array_equal(splits["training"],f["variable__training"])
    for pool,seed in (("primary",20261016),("replication",20261017)):
        expected=np.sort(np.random.default_rng(seed).choice(np.setdiff1d(np.arange(200000),excluded),20000,replace=False))
        np.testing.assert_array_equal(expected,splits[pool]);excluded=np.union1d(excluded,expected)
    assert len(excluded)==110000 and np.isin(splits["training"],splits["excluded"]).all()
    lookup={(r["pool"],r["condition"],r["alignment"],r["stage"],r["family"],r["feature"]):r for r in record["correlations"]}
    coefficient_checks,bootstrap_checks,cluster_row_replays,evaluation_offset_checks=0,0,0,0
    with np.load(OUT/"fit.npz",allow_pickle=False) as fits,np.load(OUT/"arrays.npz",allow_pickle=False) as arrays:
        training_offset_checks,pair_checks,weight_checks=verify_training(splits,plan,fit,fits)
        print("Independent training/selection/fit replay complete",flush=True)
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
                values=np.where((columns>=0)&(columns<1400),np.take_along_axis(x,columns.clip(0,1399),axis=1),0.)+z*condition["noise_factor"]*fit["median_raw_training_feature_range"]
                for method in plan["alignments"]:
                    prefix=pool+"__"+name+"__"+method;d=arrays[prefix+"__offsets"]
                    if method=="fixed":np.testing.assert_array_equal(d,np.zeros(len(x),dtype=int))
                    else:
                        sample=np.unique(np.concatenate((np.linspace(0,len(x)-1,40,dtype=int),[999,1000,1999,2000])))
                        ts="raw" if method=="gaussian_raw" else "aligned_once"
                        expected=direct_offsets(values[sample],fits[ts+"__mean"],fits[ts+"__variance"])
                        np.testing.assert_array_equal(expected,d[sample]);evaluation_offset_checks+=len(sample)
                    for stage in plan["stages"]:
                        center=fits[stage+"__mean"]
                        for family,pair in fit["stages"][stage]["pairs"].items():
                            ca,cb=[np.arange(p-5,p+6) for p in pair]
                            ia,ib=ca[None,:]+d[:,None],cb[None,:]+d[:,None]
                            # Every feature index avoids artificial injected padding as predeclared.
                            assert (ia-injected[:,None]>=0).all() and (ia-injected[:,None]<1400).all()
                            assert (ib-injected[:,None]>=0).all() and (ib-injected[:,None]<1400).all()
                            a=np.take_along_axis(values,ia,axis=1)-center[ca]
                            b=np.take_along_axis(values,ib,axis=1)-center[cb]
                            products=np.column_stack([np.einsum("ni,ij,nj->n",a,fits[stage+"__"+family+"__"+f].reshape(11,11),b) for f in plan["features"]])
                            np.testing.assert_allclose(products,arrays[prefix+"__"+stage+"__"+family+"__products"],atol=1e-10,rtol=1e-10)
                            for j,feature in enumerate(plan["features"]):
                                row=lookup[(pool,name,method,stage,family,feature)]
                                assert row["pair"]==pair
                                np.testing.assert_allclose(corr(products[:,j],y),row["hw_correlation"],atol=1e-12);coefficient_checks+=1
                    if name=="clean" and method=="gaussian_raw":
                        a=arrays[prefix+"__aligned_once__old_pair1__products"][:,2]
                        b=arrays[prefix+"__raw__old_pair1__products"][:,2]
                        blocks=np.unique(splits[pool]//1000);moments=[]
                        for block in blocks:
                            mask=splits[pool]//1000==block;aa,bb,yy=a[mask],b[mask],y[mask]
                            moments.append([mask.sum(),aa.sum(),bb.sum(),yy.sum(),np.square(aa).sum(),np.square(bb).sum(),np.square(yy).sum(),np.dot(aa,yy),np.dot(bb,yy)])
                        moments=np.array(moments)
                        np.testing.assert_allclose(moments,arrays[pool+"__cluster_moments"],atol=1e-8,rtol=1e-11)
                        np.testing.assert_array_equal(blocks,arrays[pool+"__cluster_blocks"])
                        rng=np.random.default_rng(2026);row_draws=[]
                        for _ in range(9999):
                            ids=rng.integers(0,len(y),len(y));row_draws.append(corr(a[ids],y[ids])-corr(b[ids],y[ids]))
                        row_state=rng.bit_generator.state;rng=np.random.default_rng(2026)
                        ids=rng.integers(0,len(blocks),(9999,len(blocks)))
                        np.testing.assert_array_equal(ids,arrays[pool+"__cluster_ids"])
                        cluster_draws=aggregate_delta(moments[ids].sum(1))
                        for idx in (0,4999,9998):
                            actual=np.concatenate([np.flatnonzero(splits[pool]//1000==blocks[i]) for i in ids[idx]])
                            np.testing.assert_allclose(cluster_draws[idx],corr(a[actual],y[actual])-corr(b[actual],y[actual]),atol=1e-12);cluster_row_replays+=1
                        for scheme,draws,state in (("paired_rows",np.array(row_draws),row_state),("index_clusters",cluster_draws,rng.bit_generator.state)):
                            np.testing.assert_allclose(draws,arrays[pool+"__"+scheme+"__draws"],atol=1e-12)
                            lo,hi=np.quantile(draws,[.01/8,1-.01/8]);difference=corr(a,y)-corr(b,y)
                            row=next(r for r in record["intervals"] if r["pool"]==pool and r["scheme"]==scheme)
                            np.testing.assert_allclose([difference,lo,hi],[row["difference"],row["lower"],row["upper"]],atol=1e-12)
                            assert row["rng_final_state"]==state and row["support"]==bool(difference>=.01 and lo>0)
                            bootstrap_checks+=len(draws)
            print("Independent training-alignment confirmation replay:",pool,flush=True)
    assert coefficient_checks==432 and bootstrap_checks==39996 and cluster_row_replays==6 and evaluation_offset_checks==528
    assert training_offset_checks==10000 and pair_checks==64 and weight_checks==24
    assert record["support_met"]==all(r["support"] for r in record["intervals"])
    suite=ET.parse(OUT/"pytest.xml").getroot().find("testsuite")
    tests={n:int(suite.attrib[n]) for n in ("tests","failures","errors","skipped")};tests["seconds"]=float(suite.attrib["time"])
    assert tests["tests"]==86 and tests["failures"]==tests["errors"]==tests["skipped"]==0
    result={"correlation_rows_verified":coefficient_checks,"bootstrap_draws_replayed":bootstrap_checks,
        "sampled_cluster_draws_replayed_with_actual_rows":cluster_row_replays,"sampled_evaluation_offsets_replayed":evaluation_offset_checks,
        "all_training_offsets_replayed":training_offset_checks,"training_selection_matrices_replayed":2,
        "individual_training_pair_coefficients_replayed":pair_checks,"all_feature_weight_vectors_replayed":weight_checks,
        "all_splits_rng_and_moments_replayed":True,"training_fit_preceded_confirmation":True,"feature_windows_avoid_padding":True,
        "variable_used_profiling_rows":110000,"new_attack_reads":False,"new_gpu_trainings":0,"new_optimizer_updates":0,
        "tests":tests,"support_met":record["support_met"],"seconds":time.perf_counter()-started,
        "production_source_sha256":record["production_source_sha256"],
        "artifact_sha256":{n:sha(OUT/n) for n in ("plan.json","splits.npz","training_access.json","evaluation_access.json","fit.json","fit.npz","arrays.npz","results.json","pytest.xml")}}
    write_json(OUT/"verification.json",result)
    print(json.dumps({k:v for k,v in result.items() if k!="artifact_sha256"},indent=2),flush=True)


if __name__=="__main__":main()
