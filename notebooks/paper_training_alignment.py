"""Frozen prospective CPU test of aligning training before quadratic feature fitting."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import h5py
import numpy as np
import torch
from sca.train import code_identity, environment, write_json
from paper_alignment import ROOT, RUN, EXPECTED_SOURCE, read, sha, shifted, estimate_offsets
from paper_maskfree_selection import pair_correlations, select_pairs
from paper_selection_audit import fresh_rows, correlation
from paper_window_regression import window_columns, orient_weight, bootstrap_difference
from paper_precision_replication import cluster_moments, cluster_bootstrap, moment_difference

OUT = ROOT / "outputs/paper_training_alignment_2026-10-06"
PREVIOUS = ROOT / "outputs/paper_precision_replication_2026-10-06"
WINDOW = ROOT / "outputs/paper_window_regression_2026-10-06"
FEATURES = ["point", "box_product", "covariance_rank1"]
STAGES = ["raw", "aligned_once"]
ALIGNMENTS = ["fixed", "gaussian_raw", "gaussian_aligned"]
HW = np.array([v.bit_count() for v in range(256)])


def utc():
    return datetime.now(timezone.utc).isoformat()


def safe_template(training, bound=10):
    """Unlabeled moments; padded edges cannot determine the variance floor."""
    x = np.asarray(training, dtype=float)
    if x.ndim != 2 or not len(x) or bound < 1 or x.shape[1] <= 4 * bound + 2 or not np.isfinite(x).all():
        raise ValueError("Expected finite traces with a valid interior")
    mean, variance = x.mean(0), x.var(0)
    floor = max(float(np.median(variance[bound:-bound])) * 1e-6, 1e-12)
    return {"mean": mean, "variance": np.maximum(variance, floor), "variance_floor": floor}


def offsets_batched(traces, template, bound=10, batch_size=1000):
    if batch_size < 1 or not len(traces):
        raise ValueError("Expected nonempty traces and a positive batch size")
    return np.concatenate([estimate_offsets(traces[i:i+batch_size], template,
        "gaussian_template", max_shift=bound)[0] for i in range(0, len(traces), batch_size)])


def align_training_once(training, bound=10, batch_size=1000):
    """One trace-only pass from original rows, with no labels or iterative shifts."""
    template = safe_template(training, bound)
    offsets = offsets_batched(training, template, bound, batch_size)
    aligned = shifted(training, -offsets)
    return aligned, offsets, template, safe_template(aligned, bound)


def interior_selection(training, target, margin=25, separation=50, diversity=20):
    """Apply identical eligibility to raw and aligned fits; slice both matrix axes."""
    x = np.asarray(training)
    if margin < 0 or x.ndim != 2 or x.shape[1] <= 2*margin+separation+diversity*2:
        raise ValueError("Invalid selection margin or width")
    matrix = pair_correlations(x[:, margin:x.shape[1]-margin], target)
    pairs, count = select_pairs(matrix, separation, diversity)
    pairs = {name: [p+margin for p in pair] for name, pair in pairs.items()}
    return pairs, count, matrix


def fit_simple_features(training, target, pair, radius=5):
    """Training-only point/box/leading covariance rank-one weights; no ridge search."""
    x, y = np.asarray(training, dtype=float), np.asarray(target, dtype=float)
    if x.ndim != 2 or y.shape != (len(x),) or len(x)<2 or not np.isfinite(x).all() or not np.isfinite(y).all() or not y.std():
        raise ValueError("Expected finite training traces and a nonconstant target")
    a, b = window_columns(pair, radius, x.shape[1])
    center = x.mean(0)
    p = ((x[:, a]-center[a])[:, :, None]*(x[:, b]-center[b])[:, None, :]).reshape(len(x), -1)
    covariance = (p-p.mean(0)).T@(y-y.mean())/len(x)
    m = len(a)
    u, singular, vh = np.linalg.svd(covariance.reshape(m,m), full_matrices=False)
    point = np.zeros((m,m)); point[radius,radius] = 1
    candidates = {"point":point.ravel(), "box_product":np.ones(m*m)/(m*m),
        "covariance_rank1":np.outer(u[:,0],vh[0]).ravel()}
    weights, scores = {}, {}
    for name, weight in candidates.items():
        weights[name], scores[name] = orient_weight(weight,p,y)
    return weights, {"training_correlations":scores,"singular_values":singular.tolist()}, covariance


def extract_simple(traces, center, pair, offsets, weights, radius=5):
    x, mu, d = np.asarray(traces,dtype=float), np.asarray(center), np.asarray(offsets)
    if x.ndim!=2 or mu.shape!=(x.shape[1],) or d.shape!=(len(x),) or not np.issubdtype(d.dtype,np.integer):
        raise ValueError("Invalid traces, training center or offsets")
    a,b = window_columns(pair,radius,x.shape[1])
    ia,ib = a[None,:]+d[:,None],b[None,:]+d[:,None]
    if min(ia.min(),ib.min())<0 or max(ia.max(),ib.max())>=x.shape[1]:
        raise ValueError("Window cropped after alignment")
    aa=x[np.arange(len(x))[:,None],ia]-mu[a]
    bb=x[np.arange(len(x))[:,None],ib]-mu[b]
    products=(aa[:,:,None]*bb[:,None,:]).reshape(len(x),-1)
    return np.column_stack([products@weights[name] for name in FEATURES])


def make_plan():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/"results.json").exists():raise FileExistsError("Completed phase is protected")
    with np.load(PREVIOUS/"splits.npz",allow_pickle=False) as f:
        excluded=np.unique(np.concatenate([f[n] for n in ("excluded","primary","replication")]))
    with np.load(WINDOW/"splits.npz",allow_pickle=False) as f:training=f["variable__training"]
    assert len(excluded)==70000 and len(training)==10000 and np.isin(training,excluded).all()
    primary=fresh_rows(200000,excluded,count=20000,seed=20261016)
    replication=fresh_rows(200000,np.union1d(excluded,primary),count=20000,seed=20261017)
    watched=[PREVIOUS/n for n in ("plan.json","results.json","splits.npz")]
    watched += [WINDOW/n for n in ("plan.json","results.json","fit.json","fit.npz","splits.npz")]
    watched += [RUN/n for n in ("best.pt","last.pt","manifest.json","splits.npz")]
    watched += [ROOT/n for n in ("data/ASCAD_variable.h5","notebooks/kaggle_baseline.ipynb",
        "outputs/kaggle_project_literature.zip","outputs/kaggle_resume_input_literature.zip",
        "literature/TRAINING_ALIGNMENT_2026-10-06.md")]
    watched += [ROOT/"notebooks"/n for n in ("paper_alignment.py","paper_maskfree_selection.py",
        "paper_selection_audit.py","paper_window_regression.py","paper_precision_replication.py")]
    plan={"authorization":"User requested further paper experiments; proposed CPU training-side alignment, no extra neural/GPU scope",
        "reason":"Official variable-key traces have native desynchronization; previous closed-form fits used unaligned training. Test train/evaluation preprocessing consistency. Design comes from profiling methodology and literature, never attack-guided tuning",
        "novelty":"Unverified; training preprocessing, bounded alignment, averaging and SVD are known baselines",
        "dataset":"data/ASCAD_variable.h5","width":1400,"training_rows":10000,
        "stages":STAGES,"alignment_bound":10,"training_alignment_iterations":1,
        "training_alignment":"Initial unconditional raw mean/diagonal variance Gaussian; one pass on original rows. No labels, keys, masks or metadata enter offsets",
        "template_floor":"max(median variance over columns10:1390)*1e-6,1e-12); excludes potentially padded edges",
        "score_columns":[20,1380],"offset_ties":"Smallest absolute offset, negative before positive",
        "features":FEATURES,"alignments":ALIGNMENTS,"radius":5,"selection_margin":25,
        "margin_reason":"25=radius5+estimated bound10+maximum injected shift10; selected windows never sample injected padding or training-alignment padding",
        "old_pairs":read(WINDOW/"plan.json")["campaigns"]["variable"]["pairs"],
        "families":["old_pair1","old_pair2","selected_pair1","selected_pair2"],
        "point_selection":"Training HW identity labels only; full absolute centered-product Pearson maximum, separation50/diversity20/row-major exact ties, same interior in both stages",
        "feature_fit":"Each stage center and sign are fitted on its training rows only; leading covariance SVD maximizes train covariance with unit-norm rank-one weights. No optimization or parameter search",
        "conditions":[{"name":"clean","max_shift":0,"noise_factor":0.},
            {"name":"combined5","max_shift":5,"noise_factor":.1},
            {"name":"combined10_ood","max_shift":10,"noise_factor":.2}],
        "noise_scale":"Same original raw training median feature range for every fit and condition; U9101/Z9102 common within pool across pipelines",
        "new_confirmation_pools":2,"rows_per_pool":20000,"pool_seeds":[20261016,20261017],
        "excluded_profiling_rows":70000,"primary":"Aligned-once minus raw signed HW correlation, old_pair1/covariance_rank1/clean/gaussian_raw. Holding evaluation offsets identical isolates changed feature fit rather than a different evaluation alignment rule",
        "support_criterion":"Delta>=.01 and lower interval>0 in both pools under both paired-row and index-cluster bootstrap schemes",
        "bootstrap_draws":9999,"bootstrap_seed":2026,"cluster_width":1000,
        "interval_alpha":.01,"interval_family":4,"two_sided_tail":.01/8,
        "interval_limits":"Conditional approximate paired percentile intervals; HDF5 index bins are a row-order proxy, not verified acquisition-time blocks. Adaptive phase choice has no across-phase alpha-spending guarantee",
        "secondary_scope":"Report all432 coefficients; new selected pairs and refined-template crosses are secondary, never replace the primary. No attack efficacy or causal native-jitter proof from correlation",
        "attack_payloads_or_metadata_read":False,"new_gpu_trainings":0,"new_optimizer_updates":0,
        "production_source_sha256":EXPECTED_SOURCE,"script_sha256":sha(Path(__file__)),
        "input_hashes":{p.relative_to(ROOT).as_posix():sha(p) for p in watched}}
    assert code_identity()["source_sha256"]==EXPECTED_SOURCE
    if (OUT/"plan.json").exists():
        old=read(OUT/"plan.json");assert {k:v for k,v in old.items() if k!="frozen_utc"}==plan
        plan=old
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
    if args.prepare_only:print("Frozen training alignment plan:",OUT/"plan.json",flush=True);return
    if (OUT/"training_access.json").exists() or (OUT/"evaluation_access.json").exists():raise FileExistsError("Partial viewed execution is protected")
    torch.set_num_threads(2);started=time.perf_counter()
    with np.load(OUT/"splits.npz",allow_pickle=False) as f:splits={k:f[k] for k in f.files}
    write_json(OUT/"training_access.json",{"started_utc":utc(),"plan_sha256":sha(OUT/"plan.json")})
    with h5py.File(ROOT/plan["dataset"],"r") as f:
        training=f["Profiling_traces/traces"][splits["training"]].astype(float)
        target=HW[f["Profiling_traces/labels"][splits["training"]]]
    aligned,deltas,raw_template,aligned_template=align_training_once(training)
    median_range=float(np.median(np.ptp(training,axis=0)))
    fit_arrays={"training_offsets":deltas,"training_target":target}
    fits={"started_utc":utc(),"median_raw_training_feature_range":median_range,"stages":{}}
    for stage,x,template in (("raw",training,raw_template),("aligned_once",aligned,aligned_template)):
        for name in ("mean","variance"):fit_arrays[stage+"__"+name]=template[name]
        selected,count,matrix=interior_selection(x,target)
        fit_arrays[stage+"__selection_correlations"]=matrix
        pairs={"old_"+name:pair for name,pair in plan["old_pairs"].items()}
        pairs.update({"selected_"+name:pair for name,pair in selected.items()})
        fits["stages"][stage]={"pairs":pairs,"eligible_candidates":count,"variance_floor":template["variance_floor"],"features":{}}
        for family,pair in pairs.items():
            weights,info,covariance=fit_simple_features(x,target,pair)
            fits["stages"][stage]["features"][family]=info
            fit_arrays[stage+"__"+family+"__target_covariance"]=covariance
            for name,w in weights.items():fit_arrays[stage+"__"+family+"__"+name]=w
        print("Training fit complete:",stage,selected,flush=True)
    fits["finished_utc"]=utc();fits["seconds"]=time.perf_counter()-started
    np.savez_compressed(OUT/"fit.npz",**fit_arrays);write_json(OUT/"fit.json",fits)
    write_json(OUT/"evaluation_access.json",{"started_utc":utc(),"plan_sha256":sha(OUT/"plan.json"),
        "fit_sha256":sha(OUT/"fit.npz"),"fit_record_sha256":sha(OUT/"fit.json"),"attack_payloads_or_metadata_read":False})
    arrays,rows,intervals,rng_states={},[],[],{}
    del training,aligned
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
            values=shifted(x,injected)+z*condition["noise_factor"]*median_range
            offsets={"fixed":np.zeros(len(x),dtype=np.int16),
                "gaussian_raw":offsets_batched(values,raw_template),
                "gaussian_aligned":offsets_batched(values,aligned_template)}
            for method,delta in offsets.items():
                prefix=pool+"__"+name+"__"+method;arrays[prefix+"__offsets"]=delta
                for stage in STAGES:
                    center=fit_arrays[stage+"__mean"]
                    for family,pair in fits["stages"][stage]["pairs"].items():
                        weights={feature:fit_arrays[stage+"__"+family+"__"+feature] for feature in FEATURES}
                        products=extract_simple(values,center,pair,delta,weights)
                        arrays[prefix+"__"+stage+"__"+family+"__products"]=products
                        for j,feature in enumerate(FEATURES):
                            rows.append({"pool":pool,"condition":name,"alignment":method,"stage":stage,
                                "family":family,"feature":feature,"pair":pair,"hw_correlation":correlation(products[:,j],y)})
                if name=="clean" and method=="gaussian_raw":
                    a=arrays[prefix+"__aligned_once__old_pair1__products"][:,2]
                    b=arrays[prefix+"__raw__old_pair1__products"][:,2]
                    observed=correlation(a,y)-correlation(b,y)
                    draws,state=bootstrap_difference(a,b,y,count=9999)
                    blocks,moments=cluster_moments(a,b,y,splits[pool],1000)
                    np.testing.assert_allclose(moment_difference(moments.sum(0)),observed,atol=1e-12)
                    cd,ids,cs=cluster_bootstrap(moments)
                    arrays[pool+"__cluster_blocks"]=blocks;arrays[pool+"__cluster_moments"]=moments;arrays[pool+"__cluster_ids"]=ids
                    for scheme,d,rs in (("paired_rows",draws,state),("index_clusters",cd,cs)):
                        lo,hi=np.quantile(d,[.01/8,1-.01/8]);arrays[pool+"__"+scheme+"__draws"]=d
                        intervals.append({"pool":pool,"scheme":scheme,"difference":observed,"lower":float(lo),"upper":float(hi),
                            "support":bool(observed>=.01 and lo>0),"clusters":len(blocks),"rng_final_state":rs})
            print("Fresh training-alignment confirmation:",pool,name,flush=True)
    assert len(rows)==432 and len(intervals)==4
    for rel,expected in plan["input_hashes"].items():assert sha(ROOT/rel)==expected,rel
    assert sha(Path(__file__))==plan["script_sha256"] and code_identity()["source_sha256"]==EXPECTED_SOURCE
    np.savez_compressed(OUT/"arrays.npz",**arrays)
    record={"plan_sha256":sha(OUT/"plan.json"),"fit_sha256":sha(OUT/"fit.npz"),"access_sha256":sha(OUT/"evaluation_access.json"),
        "arrays_sha256":sha(OUT/"arrays.npz"),"correlations":rows,"intervals":intervals,"support_met":all(v["support"] for v in intervals),
        "rng_states":rng_states,"seconds":time.perf_counter()-started,"environment":environment(torch.device("cpu")),
        "production_source_sha256":EXPECTED_SOURCE,"variable_used_profiling_rows":110000,"new_attack_reads":False,
        "no_holdout_tuning":True,"new_gpu_trainings":0,"new_optimizer_updates":0}
    write_json(OUT/"results.json",record)
    print(json.dumps({"seconds":record["seconds"],"intervals":intervals,"support_met":record["support_met"]},indent=2),flush=True)


if __name__=="__main__":main()
