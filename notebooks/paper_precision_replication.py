"""Larger fresh profiling replication with unchanged phase7 weights and cluster sensitivity."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import h5py
import numpy as np
import torch
from sca.train import code_identity, environment, write_json
from paper_alignment import ROOT, EXPECTED_SOURCE, read, sha, shifted
from paper_selection_audit import fresh_rows, correlation
from paper_window_regression import FEATURES, ALIGNMENTS, extract_features, alignment_offsets, bootstrap_difference

OUT = ROOT / "outputs/paper_precision_replication_2026-10-06"
PREVIOUS = ROOT / "outputs/paper_window_regression_2026-10-06"
HW = np.array([v.bit_count() for v in range(256)])


def utc(): return datetime.now(timezone.utc).isoformat()


def cluster_moments(a, b, target, rows, block_width=1000):
    """Aggregate nine sufficient statistics per HDF5-index block, never refit."""
    a, b, y, indices = np.asarray(a), np.asarray(b), np.asarray(target), np.asarray(rows)
    if a.ndim != 1 or a.shape != b.shape or a.shape != y.shape or a.shape != indices.shape or block_width <= 0:
        raise ValueError("Expected equally sized vectors and positive block width")
    blocks, mapping = np.unique(indices // block_width, return_inverse=True)
    moments = np.column_stack([np.bincount(mapping, weights=value, minlength=len(blocks)) for value in
        (np.ones(len(a)), a, b, y, a*a, b*b, y*y, a*y, b*y)])
    return blocks, moments


def moment_difference(moments):
    m = np.asarray(moments, dtype=float)
    n, sa, sb, sy, saa, sbb, syy, say, sby = np.moveaxis(m, -1, 0)
    vy = np.maximum(syy - sy*sy/n, 0)
    da, db = np.sqrt(np.maximum(saa-sa*sa/n, 0)*vy), np.sqrt(np.maximum(sbb-sb*sb/n, 0)*vy)
    ra = np.divide(say-sa*sy/n, da, out=np.zeros_like(da), where=da>0)
    rb = np.divide(sby-sb*sy/n, db, out=np.zeros_like(db), where=db>0)
    return ra-rb


def cluster_bootstrap(moments, count=9999, seed=2026):
    rng = np.random.default_rng(seed)
    draws, indices = [], []
    for start in range(0, count, 64):
        ids = rng.integers(0, len(moments), (min(64, count-start), len(moments)))
        draws.extend(moment_difference(moments[ids].sum(axis=1)))
        indices.append(ids)
    return np.asarray(draws), np.concatenate(indices).astype(np.int16), rng.bit_generator.state


def make_plan():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/"results.json").exists(): raise FileExistsError("Completed follow-up is protected")
    old_plan=read(PREVIOUS/"plan.json")
    with np.load(PREVIOUS/"splits.npz",allow_pickle=False) as f:
        excluded=np.unique(np.concatenate([f["variable__"+n] for n in ("excluded","primary","replication")]))
    assert len(excluded)==30000
    primary=fresh_rows(200000,excluded,count=20000,seed=20261014)
    replication=fresh_rows(200000,np.union1d(excluded,primary),count=20000,seed=20261015)
    watched=[PREVIOUS/n for n in ("plan.json","results.json","fit.json","fit.npz","splits.npz")]
    watched += [ROOT/"notebooks"/n for n in ("paper_window_regression.py","paper_alignment.py","paper_alignment_controls.py","paper_selection_audit.py")]
    watched += [ROOT/"data/ASCAD_variable.h5"]
    plan={"authorization":"User requested more experiments toward a paper on 2026-10-06; independent larger CPU profiling confirmations, no change to training budget/models/seeds",
        "reason":"Phase7 profiling-only contrast estimates were positive with wide intervals; increase precision and audit row-order dependence using untouched rows, keeping all methods/parameters fixed. Attack results do not choose this design",
        "phase7_primary_failure_preserved":True,"no_retuning_or_new_fit":True,
        "campaign":"variable","dataset":"data/ASCAD_variable.h5","width":1400,
        "pairs":old_plan["campaigns"]["variable"]["pairs"],"features":FEATURES,"alignments":ALIGNMENTS,
        "conditions":old_plan["conditions"],"radius":old_plan["radius"],"original_training_rows":10000,
        "new_confirmation_pools":2,"rows_per_pool":20000,"pool_seeds":[20261014,20261015],
        "uniform_seed":9101,"normal_seed":9102,"bootstrap_seed":2026,"bootstrap_draws":9999,
        "primary":"Same frozen ridge_noise minus ridge_clean signed HW correlation, pair1/combined5/Gaussian; difference>=.01 and lower interval>0 for both pools under both bootstrap schemes",
        "cluster_width":1000,"cluster_definition":"Consecutive HDF5 profiling index bins; sensitivity proxy for row-order dependence, not verified acquisition-time blocks",
        "interval_alpha":.01,"interval_family":4,"two_sided_tail":.01/8,
        "interval_limitations":"Approximate paired percentile bootstrap: iid rows vs iid HDF5-index clusters. Phase chosen after phase7 profiling precision assessment. No overall alpha-spending/optional-stopping guarantee across adaptive research phases; not retroactive success of phase7",
        "methods_reported":"All360 correlation rows, both families, every feature/condition/alignment; no selected winner replacement",
        "attack_payloads_or_metadata_read":False,"new_gpu_trainings":0,"new_optimizer_updates":0,
        "production_source_sha256":EXPECTED_SOURCE,"script_sha256":sha(Path(__file__)),
        "input_hashes":{p.relative_to(ROOT).as_posix():sha(p) for p in watched}}
    assert code_identity()["source_sha256"]==EXPECTED_SOURCE
    if (OUT/"plan.json").exists():
        previous=read(OUT/"plan.json");assert {k:v for k,v in previous.items() if k!="frozen_utc"}==plan
        plan=previous
        with np.load(OUT/"splits.npz",allow_pickle=False) as f:
            for name,rows in (("excluded",excluded),("primary",primary),("replication",replication)):
                np.testing.assert_array_equal(rows,f[name])
    else:
        plan["frozen_utc"]=utc();write_json(OUT/"plan.json",plan)
        np.savez_compressed(OUT/"splits.npz",excluded=excluded,primary=primary,replication=replication)
    return plan


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--prepare-only",action="store_true");args=parser.parse_args()
    plan=make_plan()
    if args.prepare_only: print("Frozen larger replication:",OUT/"plan.json",flush=True);return
    if (OUT/"evaluation_access.json").exists():raise FileExistsError("Protect partial viewed execution")
    torch.set_num_threads(2);started=time.perf_counter()
    fits=read(PREVIOUS/"fit.json");median_range=fits["campaigns"]["variable"]["median_training_feature_range"]
    with np.load(PREVIOUS/"fit.npz",allow_pickle=False) as f:fit_arrays={name:f[name] for name in f.files if name.startswith("variable__")}
    center,variance=fit_arrays["variable__mean"],fit_arrays["variable__variance"]
    with np.load(OUT/"splits.npz",allow_pickle=False) as f:splits={name:f[name] for name in f.files}
    write_json(OUT/"evaluation_access.json",{"started_utc":utc(),"plan_sha256":sha(OUT/"plan.json"),
        "immutable_fit_sha256":sha(PREVIOUS/"fit.npz"),"attack_payloads_or_metadata_read":False})
    arrays,rows,intervals,rng_states={},[],[],{}
    for pool in ("primary","replication"):
        with h5py.File(ROOT/plan["dataset"],"r") as f:
            x=f["Profiling_traces/traces"][splits[pool]].astype(float)
            y=HW[f["Profiling_traces/labels"][splits[pool]]]
        ur,zr=np.random.default_rng(9101),np.random.default_rng(9102)
        u,z=ur.random(len(x)),zr.standard_normal(x.shape)
        arrays[pool+"__target"]=y
        rng_states[pool]={"uniform":ur.bit_generator.state,"normal":zr.bit_generator.state}
        for condition in plan["conditions"]:
            name,bound=condition["name"],condition["max_shift"]
            injected=np.floor(u*(2*bound+1)).astype(np.int16)-bound
            values=shifted(x,injected)+z*condition["noise_factor"]*median_range
            offsets={m:[] for m in ALIGNMENTS}
            for start in range(0,len(x),1000):
                batch=alignment_offsets(values[start:start+1000],center,variance)
                for method in ALIGNMENTS:offsets[method].append(batch[method])
            offsets={m:np.concatenate(v) for m,v in offsets.items()}
            for method,delta in offsets.items():
                prefix=pool+"__"+name+"__"+method
                arrays[prefix+"__offsets"]=delta
                for family,pair in plan["pairs"].items():
                    weights={feature:fit_arrays["variable__"+family+"__"+feature] for feature in FEATURES}
                    products=extract_features(values,center,pair,5,delta,weights)
                    arrays[prefix+"__"+family+"__products"]=products
                    for j,feature in enumerate(FEATURES):
                        rows.append({"pool":pool,"condition":name,"alignment":method,"family":family,
                            "feature":feature,"hw_correlation":correlation(products[:,j],y)})
                    if name=="combined5" and method=="gaussian_template" and family=="pair1":
                        observed=correlation(products[:,5],y)-correlation(products[:,4],y)
                        row_draws,row_state=bootstrap_difference(products[:,5],products[:,4],y,count=9999)
                        blocks,moments=cluster_moments(products[:,5],products[:,4],y,splits[pool],1000)
                        np.testing.assert_allclose(moment_difference(moments.sum(0)),observed,atol=1e-12)
                        cluster_draws,cluster_ids,cluster_state=cluster_bootstrap(moments)
                        arrays[pool+"__cluster_blocks"]=blocks;arrays[pool+"__cluster_moments"]=moments
                        arrays[pool+"__cluster_ids"]=cluster_ids
                        for scheme,draws,state in (("paired_rows",row_draws,row_state),("index_clusters",cluster_draws,cluster_state)):
                            lower,upper=np.quantile(draws,[.01/8,1-.01/8])
                            arrays[pool+"__"+scheme+"__draws"]=draws
                            intervals.append({"pool":pool,"scheme":scheme,"difference":observed,"lower":float(lower),"upper":float(upper),
                                "support":bool(observed>=.01 and lower>0),"rng_final_state":state,"clusters":len(blocks)})
            print("Larger frozen replication:",pool,name,flush=True)
    assert len(rows)==360 and len(intervals)==4
    for relative,expected in plan["input_hashes"].items():assert sha(ROOT/relative)==expected,relative
    assert sha(Path(__file__))==plan["script_sha256"] and code_identity()["source_sha256"]==EXPECTED_SOURCE
    np.savez_compressed(OUT/"arrays.npz",**arrays)
    record={"plan_sha256":sha(OUT/"plan.json"),"access_sha256":sha(OUT/"evaluation_access.json"),"arrays_sha256":sha(OUT/"arrays.npz"),
        "correlations":rows,"intervals":intervals,"support_met":all(r["support"] for r in intervals),"rng_states":rng_states,
        "seconds":time.perf_counter()-started,"environment":environment(torch.device("cpu")),"production_source_sha256":EXPECTED_SOURCE,
        "phase7_failure_preserved":True,"unchanged_fit":True,"variable_used_profiling_rows":70000,
        "new_attack_reads":False,"no_holdout_tuning":True,"new_gpu_trainings":0,"new_optimizer_updates":0}
    write_json(OUT/"results.json",record)
    print(json.dumps({"seconds":record["seconds"],"intervals":intervals,"support_met":record["support_met"]},indent=2),flush=True)


if __name__=="__main__":main()
