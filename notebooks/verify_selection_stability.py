"""Independent full-search, all-weight and fresh bootstrap selection-audit replay."""
from datetime import datetime
import json
import time
import xml.etree.ElementTree as ET
import h5py
import numpy as np
from sca.train import code_identity,write_json
from paper_alignment import ROOT,read,sha
from verify_window_regression import corr
from verify_precision_replication import aggregate_delta
from verify_training_alignment import direct_offsets

OUT=ROOT/"outputs/paper_selection_stability_2026-10-06"
PREVIOUS=ROOT/"outputs/paper_training_alignment_2026-10-06"
HW=np.array([v.bit_count() for v in range(256)])


def replay_training(plan,splits,fit,arrays,old):
    with h5py.File(ROOT/plan["dataset"],"r") as f:
        x=f["Profiling_traces/traces"][splits["training"]].astype(float)
        y=HW[f["Profiling_traces/labels"][splits["training"]]]
    np.testing.assert_array_equal(y,old["training_target"])
    columns=np.arange(1400)[None,:]+old["training_offsets"][:,None]
    x=np.where((columns>=0)&(columns<1400),np.take_along_axis(x,columns.clip(0,1399),axis=1),0.)
    rng=np.random.default_rng(2026)
    ids=rng.integers(0,10000,(20,10000),dtype=np.int32)
    np.testing.assert_array_equal(ids,arrays["draw_indices"])
    assert fit["draw_rng_final_state"]==rng.bit_generator.state
    weight_checks,pair_coefficients=0,0
    a,b=np.triu_indices(1350,k=50);candidates=np.column_stack((a,b))
    for number,indices in enumerate(ids):
        xx,yy=x[indices],y[indices];center=xx.mean(0);z=xx[:,25:-25]-center[25:-25];h=yy-yy.mean()
        prefix="draw"+str(number);row=fit["draws"][number]
        assert row["draw"]==number and row["unique_training_rows"]==len(np.unique(indices))
        np.testing.assert_array_equal(center,arrays[prefix+"__center"])
        mean_product=z.T@z/len(z);v=np.maximum(np.square(z).T@np.square(z)/len(z)-mean_product**2,0)
        covariance=z.T@(z*h[:,None])/len(z);denominator=np.sqrt(v*np.mean(h*h))
        matrix=np.clip(np.divide(covariance,denominator,out=np.zeros_like(covariance),where=denominator>0),-1,1)
        scores=np.abs(matrix[a,b]);first=candidates[scores.argmax()]
        allowed=np.all(np.abs(candidates[:,:,None]-first[None,None,:])>=20,axis=(1,2))
        second=candidates[np.flatnonzero(allowed)[scores[allowed].argmax()]]
        assert row["eligible_candidates"]==len(a)==845650
        for family,points in (("pair1",first+25),("pair2",second+25)):
            np.testing.assert_array_equal(points,row["pairs"][family])
            selected_coefficient=corr((xx[:,points[0]]-center[points[0]])*(xx[:,points[1]]-center[points[1]]),yy)
            np.testing.assert_allclose(selected_coefficient,row["selection_coefficients"][family],atol=1e-12)
            np.testing.assert_allclose(selected_coefficient,matrix[points[0]-25,points[1]-25],atol=1e-12)
            pair_coefficients+=1
            ca,cb=[np.arange(p-5,p+6) for p in points]
            aa,bb=xx[:,ca]-center[ca],xx[:,cb]-center[cb]
            products=np.einsum("ni,nj->nij",aa,bb).reshape(len(xx),-1)
            c=np.mean((products-products.mean(0))*h[:,None],axis=0)
            np.testing.assert_allclose(c,arrays[prefix+"__"+family+"__target_covariance"],atol=1e-9,rtol=1e-12)
            u,s,vh=np.linalg.svd(c.reshape(11,11),full_matrices=False)
            np.testing.assert_allclose(s,row["features"][family]["singular_values"],atol=1e-9)
            point=np.zeros((11,11));point[5,5]=1
            weights={"point":point.ravel(),"box_product":np.ones(121)/11,
                "covariance_rank1":np.outer(u[:,0],vh[0]).ravel()}
            for feature,w in weights.items():
                w=w/np.linalg.norm(w)
                if corr(products@w,yy)<0:w=-w
                np.testing.assert_allclose(w,arrays[prefix+"__"+family+"__"+feature],atol=1e-11)
                np.testing.assert_allclose(corr(products@w,yy),row["features"][family]["training_correlations"][feature],atol=1e-12)
                weight_checks+=1
        print("Independent full-search fit replay:",number+1,"/20",flush=True)
    references=np.array([fit["controls"]["aligned_selected_pair"+str(j)]["pair"] for j in (1,2)])
    points=np.array([[row["pairs"]["pair"+str(j)] for j in (1,2)] for row in fit["draws"]])
    d=np.max(np.abs(points[:,:,None,:]-references[None,None,:,:]),axis=-1)
    for tolerance,summary in zip((5,20),fit["locations"]):
        assert summary["tolerance"]==tolerance
        assert summary["ordered_hits"]==[(d[:,j,j]<=tolerance).sum() for j in (0,1)]
        assert summary["either_family_hits"]==(d<=tolerance).any(1).sum(0).tolist()
        assert summary["ordered_median_max_point_distance"]==[float(np.median(d[:,j,j])) for j in (0,1)]
    return weight_checks,pair_coefficients


def replay_interval(a,y,indices,arrays,prefix,row_lookup,pool,family):
    blocks=np.unique(indices//1000);moments=[]
    for block in blocks:
        mask=indices//1000==block;aa,yy=a[mask],y[mask]
        moments.append([mask.sum(),aa.sum(),0.,yy.sum(),np.square(aa).sum(),0.,np.square(yy).sum(),np.dot(aa,yy),0.])
    moments=np.array(moments)
    np.testing.assert_allclose(moments,arrays[prefix+"__cluster_moments"],atol=1e-8,rtol=1e-11)
    np.testing.assert_array_equal(blocks,arrays[prefix+"__cluster_blocks"])
    rng=np.random.default_rng(2026);row_draws=[]
    for _ in range(9999):
        ids=rng.integers(0,len(y),len(y));row_draws.append(corr(a[ids],y[ids]))
    row_state=rng.bit_generator.state;rng=np.random.default_rng(2026)
    ids=rng.integers(0,len(blocks),(9999,len(blocks)))
    np.testing.assert_array_equal(ids,arrays[prefix+"__cluster_ids"])
    cluster_draws=aggregate_delta(moments[ids].sum(1))
    for j in (0,4999,9998):
        rows=np.concatenate([np.flatnonzero(indices//1000==blocks[i]) for i in ids[j]])
        np.testing.assert_allclose(cluster_draws[j],corr(a[rows],y[rows]),atol=1e-12)
    for scheme,draws,state in (("paired_rows",np.array(row_draws),row_state),("index_clusters",cluster_draws,rng.bit_generator.state)):
        np.testing.assert_allclose(draws,arrays[prefix+"__"+scheme+"__draws"],atol=1e-12)
        lo,hi=np.quantile(draws,[.01/16,1-.01/16]);observed=corr(a,y);row=row_lookup[(pool,family,scheme)]
        np.testing.assert_allclose([observed,lo,hi],[row["correlation"],row["lower"],row["upper"]],atol=1e-12)
        assert row["rng_final_state"]==state and row["support"]==bool(observed>=.05 and lo>0)
    return 19998,3


def main():
    started=time.perf_counter()
    plan,record,fit,access,training_access=[read(OUT/n) for n in ("plan.json","results.json","fit.json","evaluation_access.json","training_access.json")]
    assert record["plan_sha256"]==access["plan_sha256"]==training_access["plan_sha256"]==sha(OUT/"plan.json")
    assert record["fit_sha256"]==access["fit_sha256"]==sha(OUT/"fit.npz")
    assert record["access_sha256"]==sha(OUT/"evaluation_access.json") and record["arrays_sha256"]==sha(OUT/"arrays.npz")
    assert access["fit_record_sha256"]==sha(OUT/"fit.json")
    assert datetime.fromisoformat(plan["frozen_utc"])<datetime.fromisoformat(training_access["started_utc"])<datetime.fromisoformat(fit["finished_utc"])<datetime.fromisoformat(access["started_utc"])
    assert sha(ROOT/"notebooks/paper_selection_stability.py")==plan["script_sha256"]
    assert code_identity()["source_sha256"]==plan["production_source_sha256"]==record["production_source_sha256"]
    for rel,expected in plan["input_hashes"].items():assert sha(ROOT/rel)==expected,rel
    assert not plan["attack_payloads_or_metadata_read"] and not access["attack_payloads_or_metadata_read"] and not record["new_attack_reads"]
    assert record["no_bootstrap_winner_chosen"]
    with np.load(OUT/"splits.npz",allow_pickle=False) as f:splits={k:f[k] for k in f.files}
    with np.load(PREVIOUS/"splits.npz",allow_pickle=False) as f:
        excluded=np.unique(np.concatenate([f[n] for n in ("training","excluded","primary","replication")]))
        np.testing.assert_array_equal(splits["training"],f["training"])
    np.testing.assert_array_equal(excluded,splits["excluded"])
    for pool,seed in (("primary",20261018),("replication",20261019)):
        expected=np.sort(np.random.default_rng(seed).choice(np.setdiff1d(np.arange(200000),excluded),20000,replace=False))
        np.testing.assert_array_equal(expected,splits[pool]);excluded=np.union1d(excluded,expected)
    assert len(excluded)==150000
    lookup={(r["pool"],r["condition"],r["kind"],r["draw"],r["family"],r["feature"]):r for r in record["correlations"]}
    intervals={(r["pool"],r["family"],r["scheme"]):r for r in record["intervals"]}
    coefficient_checks,bootstrap_checks,cluster_replays,offset_checks=0,0,0,0
    old_fit=read(PREVIOUS/"fit.json")
    with np.load(PREVIOUS/"fit.npz",allow_pickle=False) as old,np.load(OUT/"fit.npz",allow_pickle=False) as fits,np.load(OUT/"arrays.npz",allow_pickle=False) as arrays:
        weight_checks,pair_coefficients=replay_training(plan,splits,fit,fits,old)
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
                values=np.where((columns>=0)&(columns<1400),np.take_along_axis(x,columns.clip(0,1399),axis=1),0.)+z*condition["noise_factor"]*old_fit["median_raw_training_feature_range"]
                prefix=pool+"__"+name;d=arrays[prefix+"__offsets"]
                sample=np.unique(np.concatenate((np.linspace(0,len(x)-1,40,dtype=int),[999,1000,1999,2000])))
                np.testing.assert_array_equal(d[sample],direct_offsets(values[sample],old["raw__mean"],old["raw__variance"]))
                offset_checks+=len(sample)
                specs=[]
                for control,c in fit["controls"].items():
                    stage,family=c["stage"],c["source_family"]
                    assert c["pair"]==old_fit["stages"][stage]["pairs"][family]
                    specs.append(("frozen",-1,control,c["pair"],old[stage+"__mean"],{f:old[stage+"__"+family+"__"+f] for f in plan["features"]},prefix+"__"+control))
                for row in fit["draws"]:
                    number=row["draw"];fp="draw"+str(number)
                    for family,pair in row["pairs"].items():
                        specs.append(("training_draw",number,family,pair,fits[fp+"__center"],{f:fits[fp+"__"+family+"__"+f] for f in plan["features"]},prefix+"__"+fp+"__"+family))
                scores={"pair1":[],"pair2":[]}
                for kind,number,family,pair,center,weights,ap in specs:
                    ca,cb=[np.arange(p-5,p+6) for p in pair]
                    ia,ib=ca[None,:]+d[:,None],cb[None,:]+d[:,None]
                    assert (ia-injected[:,None]>=0).all() and (ia-injected[:,None]<1400).all()
                    assert (ib-injected[:,None]>=0).all() and (ib-injected[:,None]<1400).all()
                    a=np.take_along_axis(values,ia,axis=1)-center[ca]
                    b=np.take_along_axis(values,ib,axis=1)-center[cb]
                    products=np.column_stack([np.einsum("ni,ij,nj->n",a,weights[f].reshape(11,11),b) for f in plan["features"]])
                    np.testing.assert_allclose(products,arrays[ap+"__products"],atol=1e-10,rtol=1e-10)
                    for j,feature in enumerate(plan["features"]):
                        row=lookup[(pool,name,kind,number,family,feature)];assert row["pair"]==pair
                        np.testing.assert_allclose(corr(products[:,j],y),row["hw_correlation"],atol=1e-12);coefficient_checks+=1
                    if kind=="training_draw":scores[family].append(corr(products[:,2],y))
                    elif name=="clean" and family.startswith("aligned_"):
                        boot,cl=replay_interval(products[:,2],y,splits[pool],arrays,pool+"__"+family,intervals,pool,family)
                        bootstrap_checks+=boot;cluster_replays+=cl
                for family,values in scores.items():
                    row=next(r for r in record["sensitivity"] if r["pool"]==pool and r["condition"]==name and r["family"]==family)
                    positive=int(np.count_nonzero(np.asarray(values)>0));median=float(np.median(values))
                    np.testing.assert_allclose([median,min(values),max(values)],[row["median"],row["minimum"],row["maximum"]],atol=1e-12)
                    assert row["positive_draws"]==positive and row["draws"]==20 and row["support"]==bool(median>=.05 and positive>=16)
            print("Independent selection audit confirmation replay:",pool,flush=True)
    assert coefficient_checks==528 and bootstrap_checks==79992 and cluster_replays==12 and offset_checks==176
    assert weight_checks==120 and pair_coefficients==40
    signal=all(r["support"] for r in record["intervals"])
    pipeline=all(r["support"] for r in record["sensitivity"] if r["condition"]=="clean")
    assert record["frozen_signal_met"]==signal and record["pipeline_sensitivity_met"]==pipeline and record["joint_support_met"]==(signal and pipeline)
    suite=ET.parse(OUT/"pytest.xml").getroot().find("testsuite")
    tests={n:int(suite.attrib[n]) for n in ("tests","failures","errors","skipped")};tests["seconds"]=float(suite.attrib["time"])
    assert tests["tests"]==90 and tests["failures"]==tests["errors"]==tests["skipped"]==0
    result={"correlation_rows_verified":coefficient_checks,"all_training_full_searches_replayed":20,
        "all_training_weight_vectors_replayed":weight_checks,"direct_selected_training_coefficients_replayed":pair_coefficients,
        "bootstrap_draws_replayed":bootstrap_checks,"sampled_cluster_draws_replayed_with_actual_rows":cluster_replays,
        "sampled_evaluation_offsets_replayed":offset_checks,"all_locations_splits_rng_and_centers_replayed":True,
        "training_fit_preceded_confirmation":True,"frozen_controls_unchanged":True,"feature_windows_avoid_padding":True,
        "variable_used_profiling_rows":150000,"new_attack_reads":False,"no_bootstrap_winner_chosen":True,
        "new_gpu_trainings":0,"new_optimizer_updates":0,"tests":tests,"frozen_signal_met":signal,
        "pipeline_sensitivity_met":pipeline,"joint_support_met":signal and pipeline,"seconds":time.perf_counter()-started,
        "production_source_sha256":record["production_source_sha256"],
        "artifact_sha256":{n:sha(OUT/n) for n in ("plan.json","splits.npz","training_access.json","evaluation_access.json","fit.json","fit.npz","arrays.npz","results.json","pytest.xml")}}
    write_json(OUT/"verification.json",result)
    print(json.dumps({k:v for k,v in result.items() if k!="artifact_sha256"},indent=2),flush=True)


if __name__=="__main__":main()
