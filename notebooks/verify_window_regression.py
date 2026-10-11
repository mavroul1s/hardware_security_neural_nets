"""Independent direct-product, fit, split, bootstrap and endpoint replay of phase7."""
from datetime import datetime
import json
import time
import xml.etree.ElementTree as ET
import h5py
import numpy as np
from sca.aes import SBOX
from sca.train import code_identity, write_json
from paper_alignment import ROOT, read, sha

OUT = ROOT / "outputs/paper_window_regression_2026-10-06"
HW = np.array([v.bit_count() for v in range(256)])


def corr(a, b):
    return float(np.corrcoef(a, b)[0, 1]) if np.std(a) and np.std(b) else 0.


def independently_fit(x, y, pair, radius, sigma, ridge):
    columns = [np.arange(point - radius, point + radius + 1) for point in pair]
    centered = x - np.mean(x, axis=0)
    a, b = [centered[:, c] for c in columns]
    m = len(columns[0]); n = len(x)
    p = np.column_stack([a[:, i] * b[:, j] for i in range(m) for j in range(m)])
    q = p - p.mean(0)
    g = np.einsum("ni,nj->ij", q, q) / n
    c = np.array([np.mean((v - v.mean()) * (y - y.mean())) for v in p.T])
    ca, cb = a.T @ a / n, b.T @ b / n
    increment = np.zeros((m * m, m * m))
    for i in range(m):
        for j in range(m):
            for k in range(m):
                for l in range(m):
                    increment[i*m+j, k*m+l] = (sigma ** 2 * ((ca[i,k] if j == l else 0.) +
                        (cb[j,l] if i == k else 0.)) + (sigma ** 4 if i == k and j == l else 0.))
    floor = max(np.median(np.diag(g)) * 1e-12, 1e-12)
    scale = np.sqrt(np.maximum(np.diag(g), floor))
    u, _, vh = np.linalg.svd(c.reshape(m, m), full_matrices=False)
    point = np.zeros((m, m)); point[radius, radius] = 1
    weights = {"point": point.ravel(), "box_product": np.ones(m*m),
        "diagonal_products": np.eye(m).ravel(), "covariance_rank1": np.outer(u[:,0], vh[0]).ravel()}
    # Solve in raw product coordinates; independent of experiment's scaled solve.
    for name, addition in (("ridge_clean", 0), ("ridge_noise", increment)):
        weights[name] = np.linalg.solve(g + addition + ridge * np.diag(scale ** 2), c)
    for name, w in weights.items():
        w /= np.linalg.norm(w)
        if corr(p @ w, y) < 0: w *= -1
        weights[name] = w
    return weights, g, c, increment, scale


def replay_bootstrap(a, b, y, count, seed):
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(count):
        rows = rng.integers(0, len(y), len(y))
        values.append(corr(a[rows], y[rows]) - corr(b[rows], y[rows]))
    return np.asarray(values), rng.bit_generator.state


def main():
    started = time.perf_counter()
    plan, record, fit, access = [read(OUT / name) for name in ("plan.json", "results.json", "fit.json", "evaluation_access.json")]
    assert sha(OUT / "plan.json") == record["plan_sha256"] == fit["plan_sha256"]
    assert sha(OUT / "fit.json") == record["fit_sha256"] == access["fit_sha256"]
    assert sha(OUT / "fit.npz") == fit["fit_npz_sha256"]
    assert sha(OUT / "arrays.npz") == record["arrays_sha256"]
    assert sha(OUT / "evaluation_access.json") == record["access_sha256"]
    assert datetime.fromisoformat(plan["frozen_utc"]) < datetime.fromisoformat(fit["completed_utc"]) < datetime.fromisoformat(access["started_utc"])
    assert not fit["evaluation_payloads_or_metadata_read"]
    assert sha(ROOT / "notebooks/paper_window_regression.py") == plan["script_sha256"]
    assert code_identity()["source_sha256"] == plan["production_source_sha256"] == record["production_source_sha256"]
    for relative, expected in plan["input_hashes"].items(): assert sha(ROOT / relative) == expected, relative
    with np.load(OUT / "splits.npz", allow_pickle=False) as f: splits = {n: f[n] for n in f.files}
    with np.load(ROOT / "outputs/paper_selection_audit_2026-10-06/splits.npz", allow_pickle=False) as f: old = {n: f[n] for n in f.files}
    correlation_lookup = {(r["campaign"], r["pool"], r["condition"], r["alignment"], r["family"], r["feature"]): r for r in record["correlations"]}
    recovery_lookup = {(r["campaign"], r["pool"], r["condition"], r["alignment"], r["family"], r["feature"]): r for r in record["recoveries"]}
    correlation_checks, endpoints, bootstrap_checks, weight_checks, sampled_alignment_checks = 0, 0, 0, 0, 0
    with np.load(OUT / "fit.npz", allow_pickle=False) as fits, np.load(OUT / "arrays.npz", allow_pickle=False) as arrays:
        for campaign, config in plan["campaigns"].items():
            excluded = np.union1d(old[campaign + "__excluded"], old[campaign + "__confirmation"])
            np.testing.assert_array_equal(splits[campaign + "__excluded"], excluded)
            np.testing.assert_array_equal(splits[campaign + "__training"], old[campaign + "__training"])
            for role, seed in (("primary", 20261011), ("replication", 20261012)):
                candidates = np.setdiff1d(np.arange(config["profiling_rows"]), excluded)
                expected_rows = np.sort(np.random.default_rng(seed).choice(candidates, 5000, replace=False))
                np.testing.assert_array_equal(splits[campaign + "__" + role], expected_rows)
                excluded = np.union1d(excluded, expected_rows)
            if campaign == "fixed": assert len(excluded) == 50000
            else:
                assert len(excluded) == 30000
                with np.load(ROOT / "outputs/paper_variable_campaign_2026-10-05/splits.npz", allow_pickle=False) as previous:
                    np.testing.assert_array_equal(splits["variable__excluded_attack"], previous["attack"])
                candidates = np.setdiff1d(np.arange(100000), splits["variable__excluded_attack"])
                np.testing.assert_array_equal(splits["variable__fresh_attack"], np.sort(np.random.default_rng(20261013).choice(candidates, 5000, replace=False)))
                assert not np.intersect1d(splits["variable__fresh_attack"], splits["variable__excluded_attack"]).size
            with h5py.File(ROOT / config["dataset"], "r") as f:
                x = f["Profiling_traces/traces"][splits[campaign + "__training"]].astype(float)
                y = HW[f["Profiling_traces/labels"][splits[campaign + "__training"]]]
            center = x.mean(0); variance = np.maximum(x.var(0), max(float(np.median(x.var(0))) * 1e-6, 1e-12))
            raw_range = np.median(np.ptp(x, axis=0))
            np.testing.assert_array_equal(center, fits[campaign + "__mean"])
            np.testing.assert_array_equal(variance, fits[campaign + "__variance"])
            assert raw_range == fit["campaigns"][campaign]["median_training_feature_range"]
            for family, pair in config["pairs"].items():
                weights, g, c, increment, scale = independently_fit(x, y, pair, plan["radius"], .1 * raw_range, plan["ridge"])
                for name, value in (("product_covariance", g), ("target_covariance", c), ("noise_covariance", increment), ("product_scale", scale)):
                    np.testing.assert_allclose(value, fits[campaign + "__" + family + "__" + name], atol=1e-9, rtol=1e-10)
                for name, w in weights.items():
                    np.testing.assert_allclose(w, fits[campaign + "__" + family + "__" + name], atol=2e-10, rtol=1e-9)
                    coefficient = (c @ w) / np.sqrt((w @ g @ w) * np.var(y))
                    np.testing.assert_allclose(coefficient, fit["campaigns"][campaign]["families"][family]["training_correlations"][name], atol=1e-12)
                    weight_checks += 1
            for pool in ["primary", "replication"] + (["fresh_attack"] if campaign == "variable" else []):
                pool_id = campaign + "__" + pool
                group = "Attack_traces" if pool == "fresh_attack" else "Profiling_traces"
                recover = campaign == "fixed" or pool == "fresh_attack"
                with h5py.File(ROOT / config["dataset"], "r") as f:
                    x = f[group + "/traces"][splits[pool_id]].astype(float)
                    labels = f[group + "/labels"][splits[pool_id]]; y = HW[labels]
                    if recover:
                        meta = f[group + "/metadata"][splits[pool_id]]
                        keys = np.unique(meta["key"], axis=0); assert len(keys) == 1
                        key = int(keys[0, 2]); plain = meta["plaintext"][:, 2]
                        np.testing.assert_array_equal(labels, SBOX[plain ^ key])
                        hypotheses = HW[SBOX[plain[:, None] ^ np.arange(256)[None, :]]].astype(float)
                        assert bytes(keys[0]).hex() == record["key_audits"][pool_id]["full_key_hex"]
                        if pool == "fresh_attack":
                            train_keys = f["Profiling_traces/metadata"][splits[campaign + "__training"]]["key"]
                            assert not np.all(train_keys == keys[0], axis=1).any()
                np.testing.assert_array_equal(y, arrays[pool_id + "__target"])
                ur, zr, order_rng = np.random.default_rng(9101), np.random.default_rng(9102), np.random.default_rng(8001)
                u, z = ur.random(len(x)), zr.standard_normal(x.shape)
                orders = np.stack([order_rng.permutation(len(x))[:2000] for _ in range(20)])
                np.testing.assert_array_equal(orders, arrays[pool_id + "__orders"])
                assert record["rng_states"][pool_id]["uniform"] == ur.bit_generator.state
                assert record["rng_states"][pool_id]["normal"] == zr.bit_generator.state
                assert record["rng_states"][pool_id]["orders"] == order_rng.bit_generator.state
                for condition in plan["conditions"]:
                    name, bound = condition["name"], condition["max_shift"]
                    injected = np.floor(u * (2 * bound + 1)).astype(int) - bound
                    indices = np.arange(x.shape[1])[None, :] - injected[:, None]
                    valid = (indices >= 0) & (indices < x.shape[1])
                    values = np.where(valid, np.take_along_axis(x, indices.clip(0, x.shape[1]-1), axis=1), 0.) + z * condition["noise_factor"] * raw_range
                    for method in plan["alignments"]:
                        prefix = pool_id + "__" + name + "__" + method
                        delta = arrays[prefix + "__offsets"]
                        # Replay 32 offset decisions per method/pool/condition directly.
                        selected = np.linspace(0, len(x)-1, 32, dtype=int)
                        columns = np.arange(20, x.shape[1]-20)
                        candidates = sorted(range(-10, 11), key=lambda d: (abs(d), d))
                        if method == "fixed": np.testing.assert_array_equal(delta, np.zeros(len(x), dtype=int))
                        else:
                            scores = []
                            for offset in candidates:
                                window = values[selected][:, columns + offset]
                                scores.append(np.mean((window-center[columns])**2/variance[columns] + np.log(variance[columns]), axis=1) if method == "gaussian_template" else np.sum(np.abs(window-center[columns]), axis=1))
                            expected = np.asarray(candidates)[np.argmin(np.column_stack(scores), axis=1)]
                            np.testing.assert_array_equal(delta[selected], expected)
                            sampled_alignment_checks += len(selected)
                        for family, pair in config["pairs"].items():
                            ca, cb = [np.arange(p-plan["radius"], p+plan["radius"]+1) for p in pair]
                            a = np.take_along_axis(values, ca[None,:]+delta[:,None], axis=1)-center[ca]
                            b = np.take_along_axis(values, cb[None,:]+delta[:,None], axis=1)-center[cb]
                            direct = []
                            for feature in plan["features"]:
                                w = fits[campaign + "__" + family + "__" + feature].reshape(len(ca),len(cb))
                                direct.append(np.einsum("ni,ij,nj->n", a, w, b))
                            products = np.column_stack(direct)
                            np.testing.assert_allclose(products, arrays[prefix + "__" + family + "__products"], atol=1e-10, rtol=1e-10)
                            for j, feature in enumerate(plan["features"]):
                                lookup_key = (campaign,pool,name,method,family,feature)
                                np.testing.assert_allclose(corr(products[:,j], y), correlation_lookup[lookup_key]["hw_correlation"], atol=1e-12)
                                correlation_checks += 1
                                if recover:
                                    ranks = arrays[prefix + "__" + family + "__" + feature + "__ranks"]
                                    for k, rows in enumerate(orders):
                                        aa = products[rows,j] - products[rows,j].mean()
                                        hh = hypotheses[rows] - hypotheses[rows].mean(0)
                                        denominator = np.linalg.norm(aa)*np.linalg.norm(hh,axis=0)
                                        scores = np.abs(np.divide(aa @ hh,denominator,out=np.zeros(256),where=denominator>0))
                                        actual = np.sum(scores>=scores[key]-1e-12)-1
                                        assert actual == ranks[k,-1], lookup_key
                                        endpoints += 1
                                    row = recovery_lookup[lookup_key]
                                    assert row["ge_at_budget"] == ranks[:,-1].mean()
                                    assert row["sr_at_budget"] == (ranks[:,-1]==0).mean()
                                    sr=(ranks==0).mean(0)
                                    sustained=np.flatnonzero(np.logical_and.accumulate((sr>=.9)[::-1])[::-1])
                                    assert row["traces_to_sustained_sr90"] == (int(sustained[0]+1) if len(sustained) else None)
                            if family=="pair1" and name=="combined5" and method=="gaussian_template" and pool!="fresh_attack":
                                bootstrap,state=replay_bootstrap(products[:,5],products[:,4],y,1999,2026)
                                np.testing.assert_allclose(bootstrap,arrays[prefix+"__bootstrap_differences"],atol=1e-12)
                                row=next(r for r in record["primary"] if r["campaign"]==campaign and r["pool"]==pool)
                                difference=corr(products[:,5],y)-corr(products[:,4],y)
                                lower,upper=np.quantile(bootstrap,[.05/8,1-.05/8])
                                np.testing.assert_allclose([difference,lower,upper],[row["difference"],row["lower"],row["upper"]],atol=1e-12)
                                assert row["support"] == bool(difference>=.01 and lower>0)
                                assert state==row["rng_final_state"]
                                bootstrap_checks += len(bootstrap)
                print("Independent replay complete:",campaign,pool,flush=True)
    assert correlation_checks==900 and endpoints==10800 and weight_checks==24 and bootstrap_checks==7996 and sampled_alignment_checks==1600
    assert record["primary_support_met"] == all(r["support"] for r in record["primary"])
    get=lambda f:recovery_lookup[("variable","fresh_attack","combined5","gaussian_template","pair1",f)]["sr_at_budget"]
    assert record["secondary_attack"]["criterion_met"] == bool(get("ridge_noise")>=.9 and get("ridge_noise")-get("point")>=.1-1e-12 and get("ridge_noise")-get("ridge_clean")>=.1-1e-12)
    suite=ET.parse(OUT/"pytest.xml").getroot().find("testsuite")
    tests={name: int(suite.attrib[name]) for name in ("tests","failures","errors","skipped")}
    tests["seconds"]=float(suite.attrib["time"])
    assert tests["tests"]==79 and tests["failures"]==tests["errors"]==tests["skipped"]==0
    result={"fit_weight_vectors_replayed":weight_checks,"all_fit_moments_replayed":True,
        "correlation_rows_verified":correlation_checks,"additional_endpoint_replays":endpoints,
        "paired_bootstrap_samples_replayed":bootstrap_checks,"sampled_alignment_offsets_replayed":sampled_alignment_checks,
        "all_splits_and_rng_replayed":True,"fits_frozen_before_holdouts":True,
        "fixed_used_profiling_rows":50000,"variable_used_profiling_rows":30000,"variable_viewed_attack_rows":10000,
        "original_fixed_attack_payloads_read":False,"new_variable_attack_subset_viewed":True,
        "production_source_sha256":record["production_source_sha256"],"original_artifacts_preserved":True,
        "new_gpu_trainings":0,"new_optimizer_updates":0,"tests":tests,"seconds":time.perf_counter()-started,
        "artifact_sha256":{name:sha(OUT/name) for name in ("plan.json","splits.npz","fit.json","fit.npz","evaluation_access.json","arrays.npz","results.json","pytest.xml")}}
    write_json(OUT/"verification.json",result)
    print(json.dumps({k:v for k,v in result.items() if k!="artifact_sha256"},indent=2),flush=True)


if __name__=="__main__": main()
