"""Paired training-bootstrap point-selection sensitivity and fresh frozen signal audit."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import h5py
import numpy as np
import torch
from sca.train import code_identity, environment, write_json
from paper_alignment import ROOT, RUN, EXPECTED_SOURCE, read, sha, shifted
from paper_selection_audit import fresh_rows, correlation
from paper_training_alignment import (FEATURES, interior_selection, fit_simple_features,
    extract_simple, offsets_batched)
from paper_window_regression import bootstrap_difference
from paper_precision_replication import cluster_moments, cluster_bootstrap, moment_difference

OUT=ROOT/"outputs/paper_selection_stability_2026-10-06"
PREVIOUS=ROOT/"outputs/paper_training_alignment_2026-10-06"
HW=np.array([v.bit_count() for v in range(256)])


def utc():
    return datetime.now(timezone.utc).isoformat()


def paired_training_draws(n, count=20, seed=2026):
    """Diagnostic resamples of original nominal size; duplicates are retained."""
    if n<2 or count<1:
        raise ValueError("Expected positive draw count and at least two rows")
    rng=np.random.default_rng(seed)
    draws=rng.integers(0,n,(count,n),dtype=np.int32)
    return draws,rng.bit_generator.state


def location_summary(pairs, references, tolerance):
    """Ordered and order-insensitive neighborhood counts; no consensus selector."""
    p,r=np.asarray(pairs),np.asarray(references)
    if p.ndim!=3 or p.shape[1:]!=(2,2) or r.shape!=(2,2) or tolerance<0:
        raise ValueError("Expected two pairs per draw and two reference pairs")
    distance=np.max(np.abs(p[:,:,None,:]-r[None,None,:,:]),axis=-1)
    ordered=np.stack([distance[:,j,j]<=tolerance for j in range(2)],axis=1)
    either=(distance<=tolerance).any(axis=1)
    return {"tolerance":tolerance,"ordered_hits":ordered.sum(0).tolist(),"either_family_hits":either.sum(0).tolist(),
        "ordered_median_max_point_distance":[float(np.median(distance[:,j,j])) for j in range(2)]}


def sensitivity_summary(values, minimum_median=.05, minimum_positive=16):
    """All draw coefficients, descriptive criterion only; no binomial inference."""
    x=np.asarray(values,dtype=float)
    if x.ndim!=1 or not len(x) or not np.isfinite(x).all() or minimum_positive<0:
        raise ValueError("Expected finite one-dimensional draw coefficients")
    median=float(np.median(x));positive=int(np.count_nonzero(x>0))
    return {"median":median,"minimum":float(x.min()),"maximum":float(x.max()),"positive_draws":positive,
        "draws":len(x),"support":bool(median>=minimum_median and positive>=minimum_positive)}


def make_plan():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/"results.json").exists():raise FileExistsError("Completed audit is protected")
    with np.load(PREVIOUS/"splits.npz",allow_pickle=False) as f:
        training=f["training"]
        excluded=np.unique(np.concatenate([f[n] for n in ("training","excluded","primary","replication")]))
    assert len(training)==10000 and len(excluded)==110000
    primary=fresh_rows(200000,excluded,count=20000,seed=20261018)
    replication=fresh_rows(200000,np.union1d(excluded,primary),count=20000,seed=20261019)
    watched=[PREVIOUS/n for n in ("plan.json","splits.npz","results.json","fit.json","fit.npz","verification.json")]
    watched += [RUN/n for n in ("best.pt","last.pt","manifest.json","splits.npz")]
    watched += [ROOT/n for n in ("data/ASCAD_variable.h5","notebooks/kaggle_baseline.ipynb",
        "outputs/kaggle_project_literature.zip","outputs/kaggle_resume_input_literature.zip",
        "literature/SELECTION_STABILITY_2026-10-06.md")]
    watched += [ROOT/"notebooks"/n for n in ("paper_alignment.py","paper_maskfree_selection.py",
        "paper_selection_audit.py","paper_window_regression.py","paper_precision_replication.py","paper_training_alignment.py")]
    plan={"authorization":"User continued the paper-oriented CPU research. Statistical paired-resampling audit, preserving approved neural budget/seed/models and all attacks",
        "reason":"Full-search selected points can be sensitive to training sampling. Audit both frozen aligned families and the complete reselection pipeline, not a chosen bootstrap winner. Motivation is the training selection procedure, never attack-guided tuning",
        "adaptive_scope":"Planned after phase9; phase9 primary failure preserved. All phase9 confirmation rows excluded. New endpoints are not retroactive significance for its secondary results; no across-phase alpha-spending guarantee",
        "dataset":"data/ASCAD_variable.h5","width":1400,"original_training_rows":10000,
        "training_diagnostic_draws":20,"positions_per_draw":10000,"training_draw_seed":2026,
        "resampling":"Paired traces/labels with replacement. Each draw has nominal10k positions but fewer unique rows. Conditional diagnostics, not independent acquisitions or new neural model seeds",
        "fixed_preprocessing":"Immutable phase9 raw Gaussian template/training offsets, bound10; original training traces shifted once by stored negative offsets. No alignment refit per draw",
        "draw_refit":"Training center/full point selection/point-box-rank1 weights/sign recomputed from the paired draw only. No optimizer, winner selection or ensemble",
        "selection_margin":25,"separation":50,"diversity":20,"radius":5,"features":FEATURES,
        "frozen_controls":["raw_old_pair1","raw_old_pair2","aligned_selected_pair1","aligned_selected_pair2"],
        "confirmation_rows_each":20000,"pool_seeds":[20261018,20261019],"excluded_profiling_rows":110000,
        "conditions":[{"name":"clean","max_shift":0,"noise_factor":0.},
            {"name":"combined5","max_shift":5,"noise_factor":.1}],
        "evaluation_alignment":"Same immutable phase9 raw Gaussian offsets for all fits; bound10, columns20:1380/ties(absδ,δ)",
        "noise_scale":"Original raw training median feature range, shared U9101/Z9102 per pool",
        "primary_frozen_signal":"Both original aligned selected rank1 families, clean: r>=.05 and positive lower bound in both fresh pools under both row and index-cluster bootstrap schemes",
        "primary_pipeline_sensitivity":"Both rank1 family ranks from all20 paired reselection fits, clean: median r>=.05 and at least16/20 positive coefficients in both fresh pools. Descriptive conditional perturbation criterion, not a confidence interval or independent-binomial test",
        "joint_primary":"Both frozen signal and pipeline sensitivity criteria must pass; neither is substituted by a successful secondary condition",
        "bootstrap_draws":9999,"bootstrap_seed":2026,"cluster_width":1000,
        "interval_alpha":.01,"interval_family":8,"two_sided_tail":.01/16,
        "interval_limits":"Nominal99.875% paired percentile intervals with conditional iid-row/iid-index-cluster assumptions; row-order bins are not verified acquisition-time blocks. Tail estimated from about6.25 of9999 draws; no universal coverage or sequential significance guarantee",
        "location_tolerances":[5,20],"location_role":"Ordered and either-family matches to original selected pairs; descriptive, no consensus threshold/method fitted or deployed",
        "rows_reported":"All48 immutable-control and480 diagnostic-draw coefficients, including negative signs; all20 selected pair sets saved before fresh payloads",
        "attack_payloads_or_metadata_read":False,"new_gpu_trainings":0,"new_neural_training_seeds":0,
        "new_optimizer_updates":0,"novelty_verified":False,"production_source_sha256":EXPECTED_SOURCE,
        "script_sha256":sha(Path(__file__)),"input_hashes":{p.relative_to(ROOT).as_posix():sha(p) for p in watched}}
    assert code_identity()["source_sha256"]==EXPECTED_SOURCE
    if (OUT/"plan.json").exists():
        old=read(OUT/"plan.json");assert {k:v for k,v in old.items() if k!="frozen_utc"}==plan;plan=old
        with np.load(OUT/"splits.npz",allow_pickle=False) as f:
            for name,rows in (("training",training),("excluded",excluded),("primary",primary),("replication",replication)):
                np.testing.assert_array_equal(rows,f[name])
    else:
        plan["frozen_utc"]=utc();write_json(OUT/"plan.json",plan)
        np.savez_compressed(OUT/"splits.npz",training=training,excluded=excluded,primary=primary,replication=replication)
    return plan


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--prepare-only",action="store_true");args=parser.parse_args()
    plan=make_plan()
    if args.prepare_only:print("Frozen selection stability plan:",OUT/"plan.json",flush=True);return
    if (OUT/"training_access.json").exists() or (OUT/"evaluation_access.json").exists():raise FileExistsError("Partial viewed execution is protected")
    torch.set_num_threads(2);started=time.perf_counter()
    with np.load(OUT/"splits.npz",allow_pickle=False) as f:splits={k:f[k] for k in f.files}
    with np.load(PREVIOUS/"fit.npz",allow_pickle=False) as f:old={k:f[k] for k in f.files}
    old_fit=read(PREVIOUS/"fit.json")
    write_json(OUT/"training_access.json",{"started_utc":utc(),"plan_sha256":sha(OUT/"plan.json")})
    with h5py.File(ROOT/plan["dataset"],"r") as f:
        raw=f["Profiling_traces/traces"][splits["training"]].astype(float)
        target=HW[f["Profiling_traces/labels"][splits["training"]]]
    np.testing.assert_array_equal(target,old["training_target"])
    aligned=shifted(raw,-old["training_offsets"])
    draws,state=paired_training_draws(len(raw),20,2026)
    fit_arrays={"draw_indices":draws};fits={"draw_rng_final_state":state,"draws":[],"controls":{}}
    controls={}
    for stage,families in (("raw",("old_pair1","old_pair2")),("aligned_once",("selected_pair1","selected_pair2"))):
        for family in families:
            name=("raw_" if stage=="raw" else "aligned_")+family
            weights={feature:old[stage+"__"+family+"__"+feature] for feature in FEATURES}
            controls[name]={"pair":old_fit["stages"][stage]["pairs"][family],"center":old[stage+"__mean"],"weights":weights}
            fits["controls"][name]={"pair":controls[name]["pair"],"stage":stage,"source_family":family}
    for number,ids in enumerate(draws):
        x,y=aligned[ids],target[ids]
        selected,count,matrix=interior_selection(x,y)
        prefix="draw"+str(number);fit_arrays[prefix+"__center"]=x.mean(0)
        # Preserve the full search maximum and selected-pair coefficients without saving20 matrices.
        row={"draw":number,"unique_training_rows":int(len(np.unique(ids))),"pairs":selected,
            "eligible_candidates":count,"selection_coefficients":{},"features":{}}
        for family,pair in selected.items():
            weights,info,cov=fit_simple_features(x,y,pair)
            row["selection_coefficients"][family]=float(matrix[pair[0]-25,pair[1]-25])
            row["features"][family]=info;fit_arrays[prefix+"__"+family+"__target_covariance"]=cov
            for feature,w in weights.items():fit_arrays[prefix+"__"+family+"__"+feature]=w
        fits["draws"].append(row)
        print("Paired training selection draw:",number+1,"/20",selected,flush=True)
    refs=np.array([controls["aligned_selected_pair"+str(j)]["pair"] for j in (1,2)])
    points=np.array([[row["pairs"]["pair"+str(j)] for j in (1,2)] for row in fits["draws"]])
    fits["locations"]=[location_summary(points,refs,t) for t in plan["location_tolerances"]]
    fits["finished_utc"]=utc();fits["seconds"]=time.perf_counter()-started
    np.savez_compressed(OUT/"fit.npz",**fit_arrays);write_json(OUT/"fit.json",fits)
    write_json(OUT/"evaluation_access.json",{"started_utc":utc(),"plan_sha256":sha(OUT/"plan.json"),
        "fit_sha256":sha(OUT/"fit.npz"),"fit_record_sha256":sha(OUT/"fit.json"),"attack_payloads_or_metadata_read":False})
    del raw,aligned,x
    arrays,rows,intervals,sensitivity,rng_states={},[],[],[],{}
    template={"mean":old["raw__mean"],"variance":old["raw__variance"]}
    for pool in ("primary","replication"):
        with h5py.File(ROOT/plan["dataset"],"r") as f:
            x=f["Profiling_traces/traces"][splits[pool]].astype(float)
            y=HW[f["Profiling_traces/labels"][splits[pool]]]
        ur,zr=np.random.default_rng(9101),np.random.default_rng(9102)
        u,z=ur.random(len(x)),zr.standard_normal(x.shape)
        arrays[pool+"__target"]=y;rng_states[pool]={"uniform":ur.bit_generator.state,"normal":zr.bit_generator.state}
        for condition in plan["conditions"]:
            name,bound=condition["name"],condition["max_shift"]
            injected=np.floor(u*(2*bound+1)).astype(np.int16)-bound
            values=shifted(x,injected)+z*condition["noise_factor"]*old_fit["median_raw_training_feature_range"]
            delta=offsets_batched(values,template);prefix=pool+"__"+name
            arrays[prefix+"__offsets"]=delta
            for control,c in controls.items():
                products=extract_simple(values,c["center"],c["pair"],delta,c["weights"])
                arrays[prefix+"__"+control+"__products"]=products
                for j,feature in enumerate(FEATURES):rows.append({"pool":pool,"condition":name,"kind":"frozen",
                    "draw":-1,"family":control,"feature":feature,"pair":c["pair"],"hw_correlation":correlation(products[:,j],y)})
                if name=="clean" and control.startswith("aligned_"):
                    a=products[:,2];zero=np.zeros(len(a));observed=correlation(a,y)
                    rd,rs=bootstrap_difference(a,zero,y,count=9999)
                    blocks,moments=cluster_moments(a,zero,y,splits[pool],1000)
                    np.testing.assert_allclose(moment_difference(moments.sum(0)),observed,atol=1e-12)
                    cd,ids,cs=cluster_bootstrap(moments)
                    cp=pool+"__"+control
                    arrays[cp+"__cluster_blocks"]=blocks;arrays[cp+"__cluster_moments"]=moments;arrays[cp+"__cluster_ids"]=ids
                    for scheme,d,bs in (("paired_rows",rd,rs),("index_clusters",cd,cs)):
                        lo,hi=np.quantile(d,[.01/16,1-.01/16]);arrays[cp+"__"+scheme+"__draws"]=d
                        intervals.append({"pool":pool,"family":control,"scheme":scheme,"correlation":observed,
                            "lower":float(lo),"upper":float(hi),"support":bool(observed>=.05 and lo>0),"rng_final_state":bs})
            draw_scores={"pair1":[],"pair2":[]}
            for row in fits["draws"]:
                number=row["draw"];fp="draw"+str(number)
                for family,pair in row["pairs"].items():
                    weights={feature:fit_arrays[fp+"__"+family+"__"+feature] for feature in FEATURES}
                    products=extract_simple(values,fit_arrays[fp+"__center"],pair,delta,weights)
                    arrays[prefix+"__"+fp+"__"+family+"__products"]=products
                    for j,feature in enumerate(FEATURES):rows.append({"pool":pool,"condition":name,"kind":"training_draw",
                        "draw":number,"family":family,"feature":feature,"pair":pair,"hw_correlation":correlation(products[:,j],y)})
                    draw_scores[family].append(correlation(products[:,2],y))
            for family,scores in draw_scores.items():
                summary=sensitivity_summary(scores)
                sensitivity.append({"pool":pool,"condition":name,"family":family,**summary})
            print("Fresh selection-stability confirmation:",pool,name,flush=True)
    assert len(rows)==528 and len(intervals)==8 and len(sensitivity)==8
    for rel,expected in plan["input_hashes"].items():assert sha(ROOT/rel)==expected,rel
    assert sha(Path(__file__))==plan["script_sha256"] and code_identity()["source_sha256"]==EXPECTED_SOURCE
    np.savez_compressed(OUT/"arrays.npz",**arrays)
    signal=all(r["support"] for r in intervals)
    pipeline=all(r["support"] for r in sensitivity if r["condition"]=="clean")
    record={"plan_sha256":sha(OUT/"plan.json"),"fit_sha256":sha(OUT/"fit.npz"),"access_sha256":sha(OUT/"evaluation_access.json"),
        "arrays_sha256":sha(OUT/"arrays.npz"),"correlations":rows,"intervals":intervals,"sensitivity":sensitivity,
        "frozen_signal_met":signal,"pipeline_sensitivity_met":pipeline,"joint_support_met":signal and pipeline,
        "rng_states":rng_states,"seconds":time.perf_counter()-started,"environment":environment(torch.device("cpu")),
        "production_source_sha256":EXPECTED_SOURCE,"variable_used_profiling_rows":150000,"new_attack_reads":False,
        "no_holdout_tuning":True,"no_bootstrap_winner_chosen":True,"new_gpu_trainings":0,"new_optimizer_updates":0}
    write_json(OUT/"results.json",record)
    print(json.dumps({"seconds":record["seconds"],"frozen_signal_met":signal,"pipeline_sensitivity_met":pipeline,
        "joint_support_met":record["joint_support_met"],"sensitivity":sensitivity,"locations":fits["locations"]},indent=2),flush=True)


if __name__=="__main__":main()
