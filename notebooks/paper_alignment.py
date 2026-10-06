"""Frozen CPU experiment: trace-only alignment and normalization/shift ordering."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import h5py
import numpy as np
import torch
from sca.aes import candidate_labels
from sca.data import fit_normalizer, normalize, split_identifier
from sca.metrics import evaluate_key_recovery
from sca.models import build_model
from sca.train import code_identity, environment, write_json
from audit_correlation_robustness import recovery, selected_product

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/paper_alignment_2026-10-05"
RUN = ROOT / "runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0"
EXPECTED_SOURCE = "84eff3cde04c0e9a1756a3d29c44ec82e115a1a08575132686a02520333e2b5c"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def shifted(values, offsets, padding="zero"):
    """Positive offsets move the waveform right; never circularly wrap."""
    x = np.asarray(values, dtype=np.float64)
    offsets = np.asarray(offsets)
    if (x.ndim != 2 or offsets.shape != (len(x),) or
            not np.issubdtype(offsets.dtype, np.integer) or
            np.any(np.abs(offsets) >= x.shape[1]) or not np.isfinite(x).all()):
        raise ValueError("Expected finite traces and one bounded integer offset per row")
    if padding not in ("zero", "edge"):
        raise ValueError("Unsupported padding")
    columns = np.arange(x.shape[1])[None, :] - offsets[:, None]
    valid = (columns >= 0) & (columns < x.shape[1])
    result = x[np.arange(len(x))[:, None], columns.clip(0, x.shape[1] - 1)]
    return np.where(valid, result, 0.) if padding == "zero" else result


def corruption_pipelines(x, minimum, scale, offsets, noise, padding="zero"):
    """Share physical-unit noise; return the raw and feature-shift surrogate domains."""
    x, minimum, scale = [np.asarray(v, dtype=np.float64) for v in (x, minimum, scale)]
    if minimum.shape != (x.shape[1],) or scale.shape != minimum.shape or np.any(scale <= 0):
        raise ValueError("Expected positive per-position affine scales")
    raw = shifted(x, offsets, padding) + noise
    # Express both outputs in raw units so the same estimator/features are compared.
    feature = shifted((x - minimum) / scale, offsets, padding) * scale + minimum + noise
    transported = (shifted((x - minimum) / scale, offsets, padding) *
                   shifted(np.broadcast_to(scale, x.shape), offsets, padding) +
                   shifted(np.broadcast_to(minimum, x.shape), offsets, padding) + noise)
    return {"raw_shift": raw, "feature_shift_surrogate": feature}, transported


def fit_template(training):
    """Unconditional moments: no labels, plaintexts, keys or mask metadata."""
    x = np.asarray(training, dtype=np.float64)
    if x.ndim != 2 or not len(x) or not np.isfinite(x).all():
        raise ValueError("Expected finite training traces")
    mean, variance = x.mean(axis=0), x.var(axis=0)
    floor = max(float(np.median(variance)) * 1e-6, 1e-12)
    return {"mean": mean, "variance": np.maximum(variance, floor), "variance_floor": floor}


def estimate_offsets(traces, template, method, max_shift=10):
    """Search bounded shifts from waveform alone; all scored points avoid border cues."""
    x = np.asarray(traces, dtype=np.float64)
    mean, variance = np.asarray(template["mean"]), np.asarray(template["variance"])
    if (x.ndim != 2 or mean.shape != (x.shape[1],) or variance.shape != mean.shape or
            not np.isfinite(x).all() or np.any(variance <= 0) or max_shift < 0 or
            x.shape[1] <= 4 * max_shift + 2):
        raise ValueError("Invalid template, trace or search bound")
    # At actual shifts <= max_shift, none of these candidate samples can be padding.
    columns = np.arange(2 * max_shift, x.shape[1] - 2 * max_shift)
    candidates = sorted(range(-max_shift, max_shift + 1), key=lambda d: (abs(d), d))
    scores = np.empty((len(x), len(candidates)))
    reference = mean[columns]
    centered_reference = reference - reference.mean()
    for index, offset in enumerate(candidates):
        values = x[:, columns + offset]
        if method == "gaussian_template":
            scores[:, index] = ((values - reference) ** 2 / variance[columns] +
                                np.log(variance[columns])).mean(axis=1)
        elif method == "ncc_template":
            centered = values - values.mean(axis=1, keepdims=True)
            denominator = np.sqrt(np.square(centered).sum(axis=1) * np.square(centered_reference).sum())
            scores[:, index] = -np.divide(centered @ centered_reference, denominator,
                                         out=np.zeros(len(x)), where=denominator > 0)
        else:
            raise ValueError("Unknown trace-only alignment method")
    estimates = np.asarray(candidates, dtype=np.int16)[scores.argmin(axis=1)]
    return estimates, scores


def confirm_indices(training, validation, n_profiling=50000, count=5000, seed=20261005):
    excluded = np.union1d(training, validation)
    remaining = np.setdiff1d(np.arange(n_profiling), excluded)
    if len(remaining) < count:
        raise ValueError("Not enough unused profiling rows")
    return np.sort(np.random.default_rng(seed).choice(remaining, count, replace=False))


def make_plan():
    if (OUT / "results.json").exists():
        raise FileExistsError("Completed experiment is protected")
    OUT.mkdir(parents=True, exist_ok=True)
    selection = ROOT / "outputs/masking_diagnosis_2026-10-03/diagnosis.json"
    points = read(selection)
    with np.load(RUN / "splits.npz", allow_pickle=False) as bundle:
        training, validation = bundle["training"], bundle["validation"]
    confirmation = confirm_indices(training, validation)
    watched = [RUN / name for name in ("best.pt", "last.pt", "splits.npz", "manifest.json")]
    watched += [ROOT / "data/ASCAD.h5", selection, ROOT / "notebooks/kaggle_baseline.ipynb",
                ROOT / "outputs/kaggle_resume_input_literature.zip", ROOT / "outputs/kaggle_project_literature.zip"]
    plan = {"authorization": "User requested experiments toward a paper, also included in final coursework, on 2026-10-05",
        "hypotheses": ["Trace-only alignment can improve second-order recovery under bounded global shifts",
                       "Per-position normalization and waveform shifting alter each other; order may change robustness attribution"],
        "novelty": "Unverified. Normalization/alignment issue already discussed in Krcek et al. 2023/1100; estimators are baselines, not claimed novel",
        "training_rows": 10000, "validation_rows": 5000, "confirmation_rows": 5000,
        "confirmation_selection_seed": 20261005, "confirmation_role": "Previously unused for fitting or reported recovery; same fixed-key profiling campaign, not final attack",
        "original_split_id": split_identifier(training, validation),
        "confirmation_split_id": split_identifier(training, confirmation),
        "pairs": {name: value["selected_pair"] for name, value in points["selected_products"].items()},
        "point_selection": "Frozen prior training-only mask/share-aided selection; identical points for all CPA methods; no equal-information CNN superiority claim",
        "methods": ["fixed", "ncc_template", "gaussian_template", "oracle_known_shift"],
        "template_fit": "Unlabeled original 10k raw training traces only; mean and diagonal variance",
        "alignment_search_bound": 10, "alignment_template_columns": [20, 680],
        "tie_rule": "Lowest absolute offset first, negative before positive; no use of true shift",
        "gaussian_variance_floor": "max(median(training variance)*1e-6, 1e-12)",
        "pipelines": ["raw_shift", "feature_shift_surrogate"],
        "pipeline_formulas": {"raw_shift": "S(x)+epsilon", "feature_shift_surrogate": "N^-1(S(N(x)))+epsilon"},
        "normalizer": "Training-only feature MinMax; affine coordinate transform, no clipping",
        "noise_definition": "Uniform raw-unit Gaussian std = factor * median(training feature range); same realized epsilon for both pipelines",
        "conditions": [{"name": "clean", "max_shift": 0, "noise_factor": 0.},
            {"name": "shift5", "max_shift": 5, "noise_factor": 0.},
            {"name": "combined5", "max_shift": 5, "noise_factor": .1},
            {"name": "combined10_ood", "max_shift": 10, "noise_factor": .2}],
        "randomness": {"uniform_shift_seed": 9101, "standard_normal_seed": 9102, "order_seed": 8001},
        "randomness_pairing": "Common U and Z within pool across conditions/pipelines; same streams on both equal-size profiling pools, not independent experimental seeds",
        "repetitions": 20, "budget": 2000, "rank_tolerance": 1e-12,
        "primary_condition": "combined5", "primary_estimator": "gaussian_template",
        "primary_contrast": "Gaussian-template minus fixed SR@2000, reported separately for both pairs/pipelines/pools",
        "support_criterion": "In confirmation raw_shift/combined5: both pairs reach SR>=.9 with estimated shifts and improve fixed SR by >=.1; clean SR decreases by <=.1",
        "order_effect_criterion": "Confirmation shift5 or combined5: absolute SR difference >=.1 for same pair/method between pipelines; descriptive, not a novelty test",
        "no_post_validation_method_or_parameter_selection": True,
        "frozen_cnn_confirmation": "Existing minimum-CE best.pt, clean confirmation only, same normalizer; no real-data weight updates",
        "source_sha256": EXPECTED_SOURCE, "experiment_script_sha256": sha(Path(__file__)),
        "input_hashes": {p.relative_to(ROOT).as_posix(): sha(p) for p in watched},
        "final_attack_payloads_read": False, "new_gpu_trainings": 0, "new_real_data_optimizer_updates": 0}
    assert code_identity()["source_sha256"] == EXPECTED_SOURCE
    if (OUT / "plan.json").exists():
        assert read(OUT / "plan.json") == plan, "Plan changed after freezing"
    else:
        write_json(OUT / "plan.json", plan)
        np.savez_compressed(OUT / "splits.npz", training=training, validation=validation, confirmation=confirmation)
    return plan


def independent_endpoint(product, hypotheses, true_key, order):
    a = product[order] - product[order].mean()
    b = hypotheses[order].astype(np.float64)
    b -= b.mean(axis=0)
    denominator = np.sqrt(np.square(a).sum() * np.square(b).sum(axis=0))
    scores = np.abs(np.divide((a[:, None] * b).sum(axis=0), denominator,
                             out=np.zeros(256), where=denominator > 0))
    return int((scores >= scores[true_key] - 1e-12).sum() - 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    plan = make_plan()
    if args.prepare_only:
        print("Frozen plan:", OUT / "plan.json", flush=True)
        return
    torch.set_num_threads(2)
    started = time.perf_counter()
    with np.load(OUT / "splits.npz", allow_pickle=False) as bundle:
        splits = {name: bundle[name] for name in bundle.files}
    assert len(np.unique(np.concatenate(list(splits.values())))) == 20000
    manifest = read(RUN / "manifest.json")
    with h5py.File(ROOT / "data/ASCAD.h5", "r") as handle:
        training = handle["Profiling_traces/traces"][splits["training"]].astype(np.float64)
    stats = fit_normalizer(training, "feature_minmax_training_only")
    assert stats == manifest["normalizer"]
    minimum, scale = np.asarray(stats["minimum"]), np.asarray(stats["scale"])
    template = fit_template(training)
    range_median = float(np.median(scale))
    results, arrays, alignment, controls = [], {"template_mean": template["mean"], "template_variance": template["variance"]}, [], []
    verified_endpoints = 0
    for pool in ("validation", "confirmation"):
        with h5py.File(ROOT / "data/ASCAD.h5", "r") as handle:
            group = handle["Profiling_traces"]
            x = group["traces"][splits[pool]].astype(np.float64)
            metadata = group["metadata"][splits[pool]]
        plaintext = metadata["plaintext"][:, 2]
        keys = np.unique(metadata["key"][:, 2])
        assert len(keys) == 1
        key = int(keys[0])  # Reporting only, never an estimator input.
        hypotheses = np.array([i.bit_count() for i in range(256)])[candidate_labels(plaintext)]
        rng = np.random.default_rng(plan["randomness"]["order_seed"])
        orders = [rng.permutation(len(x))[:plan["budget"]] for _ in range(plan["repetitions"])]
        u = np.random.default_rng(9101).random(len(x))
        z = np.random.default_rng(9102).standard_normal(x.shape)
        arrays[pool + "__uniform_draws"] = u
        cache = {}
        for condition in plan["conditions"]:
            name, width = condition["name"], condition["max_shift"]
            offsets = (np.floor(u * (2 * width + 1)).astype(np.int16) - width)
            noise = z * condition["noise_factor"] * range_median
            pipelines, transported = corruption_pipelines(x, minimum, scale, offsets, noise)
            edges, transported_edge = corruption_pipelines(x, minimum, scale, offsets, noise, "edge")
            assert np.allclose(transported, pipelines["raw_shift"], atol=1e-10, rtol=0)
            assert np.allclose(transported_edge, edges["raw_shift"], atol=1e-10, rtol=0)
            # Scalar affine normalization commutes on safe interior points.
            scalar_min, scalar_scale = np.full(700, minimum.mean()), np.full(700, scale.mean())
            scalar, _ = corruption_pipelines(x, scalar_min, scalar_scale, offsets, noise)
            assert np.allclose(scalar["raw_shift"][:, 10:-10], scalar["feature_shift_surrogate"][:, 10:-10], atol=1e-10, rtol=0)
            prefix = pool + "__" + name
            arrays[prefix + "__true_offsets"] = offsets
            delta = pipelines["raw_shift"][:, 10:-10] - pipelines["feature_shift_surrogate"][:, 10:-10]
            control = {"pool": pool, "condition": name, "raw_noise_std": condition["noise_factor"] * range_median,
                "order_difference_rms_raw_units": float(np.sqrt(np.square(delta).mean())),
                "affine_transport_max_absolute_error": float(np.abs(transported - pipelines["raw_shift"]).max()),
                "scalar_affine_interior_commutes": True, "border_cues_excluded_from_alignment": True}
            controls.append(control)
            for pipeline, values in pipelines.items():
                estimates = {"fixed": np.zeros(len(x), dtype=np.int16), "oracle_known_shift": offsets}
                for method in ("ncc_template", "gaussian_template"):
                    estimates[method], scores = estimate_offsets(values, template, method)
                    edge_offsets, edge_scores = estimate_offsets(edges[pipeline], template, method)
                    assert np.array_equal(estimates[method], edge_offsets) and np.array_equal(scores, edge_scores)
                    alignment.append({"pool": pool, "condition": name, "pipeline": pipeline, "method": method,
                        "exact_shift_fraction": float((estimates[method] == offsets).mean()),
                        "mean_absolute_shift_error": float(np.abs(estimates[method].astype(int) - offsets).mean()),
                        "zero_edge_estimates_and_scores_identical": True})
                for method in plan["methods"]:
                    stem = prefix + "__" + pipeline + "__" + method
                    arrays[stem + "__estimated_offsets"] = estimates[method]
                    for family, pair in plan["pairs"].items():
                        product = selected_product(values, template["mean"], pair, estimates[method])
                        product_edge = selected_product(edges[pipeline], template["mean"], pair, estimates[method])
                        assert np.array_equal(product, product_edge)
                        digest = hashlib.sha256(product.tobytes()).hexdigest()
                        if digest not in cache:
                            cache[digest] = recovery(product, hypotheses, key, orders)
                        summary, curves = cache[digest]
                        for index, order in enumerate(orders):
                            assert independent_endpoint(product, hypotheses, key, order) == curves["ranks"][index, -1]
                            verified_endpoints += 1
                        arrays[stem + "__" + family + "__ranks"] = curves["ranks"]
                        results.append({"pool": pool, "condition": name, "pipeline": pipeline,
                            "method": method, "family": family, "pair": pair, **summary})
            print("Completed paper experiment:", pool, name, flush=True)
        if pool == "confirmation":
            checkpoint = torch.load(RUN / "best.pt", map_location="cpu", weights_only=False)
            assert checkpoint["normalizer"] == stats and checkpoint["code"]["source_sha256"] == EXPECTED_SOURCE
            model = build_model(checkpoint["config"]["model"])
            model.load_state_dict(checkpoint["model"])
            model.eval()
            lp = []
            xn = normalize(x, stats)
            with torch.no_grad():
                for start in range(0, len(x), 128):
                    lp.append(torch.log_softmax(model(torch.from_numpy(xn[start:start + 128])).double(), dim=1).numpy())
            cnn_summary, cnn_curves = evaluate_key_recovery(np.concatenate(lp), plaintext, key, budget=2000, repetitions=20, seed=8001)
            arrays["confirmation__frozen_cnn_clean_ranks"] = cnn_curves["ranks"]
    lookup = {(r["pool"], r["condition"], r["pipeline"], r["method"], r["family"]): r for r in results}
    primary = []
    for pipeline in plan["pipelines"]:
        for family in plan["pairs"]:
            get = lambda condition, method: lookup[("confirmation", condition, pipeline, method, family)]["sr_at_budget"]
            improvement = get("combined5", "gaussian_template") - get("combined5", "fixed")
            clean_loss = get("clean", "fixed") - get("clean", "gaussian_template")
            primary.append({"pipeline": pipeline, "family": family, "confirmation_sr_difference": improvement,
                "confirmation_gaussian_sr": get("combined5", "gaussian_template"), "clean_sr_loss": clean_loss,
                "support_criterion_passed": bool(get("combined5", "gaussian_template") >= .9 and
                    improvement >= .1 - 1e-12 and clean_loss <= .1 + 1e-12)})
    for relative, expected in plan["input_hashes"].items():
        assert sha(ROOT / relative) == expected
    assert code_identity()["source_sha256"] == EXPECTED_SOURCE
    assert sha(Path(__file__)) == plan["experiment_script_sha256"]
    assert len(results) == 128 and verified_endpoints == 2560
    np.savez_compressed(OUT / "arrays.npz", **arrays)
    record = {"plan_sha256": sha(OUT / "plan.json"), "environment": environment(torch.device("cpu")),
        "results": results, "alignment": alignment, "controls": controls, "primary_contrasts": primary,
        "training_range_median": range_median, "template_variance_floor": template["variance_floor"],
        "frozen_cnn_clean_confirmation": cnn_summary, "independent_cpa_endpoint_checks": verified_endpoints,
        "confirmation_method_selection_performed": False, "all_original_inputs_preserved": True,
        "new_gpu_trainings": 0, "full_gpu_trainings_total": 3, "new_real_data_optimizer_updates": 0,
        "final_attack_payloads_read": False, "seconds": time.perf_counter() - started,
        "limitations": "Same-key/same-campaign profiling confirmation; synthetic global shifts/noise, not cross-device. Existing alignment baselines and mask-aided CPA point selection; novelty unverified"}
    write_json(OUT / "results.json", record)
    print(json.dumps({"seconds": record["seconds"], "primary": primary, "cnn_confirmation": cnn_summary}, indent=2), flush=True)


if __name__ == "__main__":
    main()
