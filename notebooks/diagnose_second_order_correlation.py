"""Profiling-validation correlation audit with previously training-selected pairs."""
import hashlib
import json
from pathlib import Path
import time

import h5py
import numpy as np
from sca.aes import candidate_labels
from sca.train import code_identity, write_json

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0"
OUTPUT = ROOT / "outputs/literature_diagnosis_2026-10-04"


def prefix_correlations(values, hypotheses):
    """Pearson correlation at every prefix; singleton/constant prefixes score zero."""
    values = np.asarray(values, dtype=np.float64)
    hypotheses = np.asarray(hypotheses, dtype=np.float64)
    if (values.ndim != 1 or hypotheses.ndim != 2 or len(values) != len(hypotheses)
            or not np.isfinite(values).all() or not np.isfinite(hypotheses).all()):
        raise ValueError("Expected aligned finite vector and hypothesis matrix")
    count = np.arange(1, len(values) + 1)[:, None]
    sx = values.cumsum()[:, None]
    sy = hypotheses.cumsum(axis=0)
    covariance = (values[:, None] * hypotheses).cumsum(axis=0) - sx * sy / count
    vx = np.maximum(np.square(values).cumsum()[:, None] - sx * sx / count, 0)
    vy = np.maximum(np.square(hypotheses).cumsum(axis=0) - sy * sy / count, 0)
    denominator = np.sqrt(vx * vy)
    correlations = np.divide(covariance, denominator, out=np.zeros_like(covariance), where=denominator > 0)
    return np.clip(correlations, -1, 1)


def conservative_absolute_ranks(correlations, true_key, tolerance=1e-12):
    scores = np.abs(correlations)
    # Near-exact two-point +/-1 correlations are ties, not evidence of early recovery.
    return (scores >= scores[:, true_key, None] - tolerance).sum(axis=1) - 1


def main():
    started = time.perf_counter()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    before = code_identity()["source_sha256"]
    hashes = {n:hashlib.sha256((RUN / n).read_bytes()).hexdigest() for n in ("best.pt", "last.pt")}
    read = lambda p:json.loads(p.read_text(encoding="utf-8"))
    selection = read(ROOT / "outputs/masking_diagnosis_2026-10-03/diagnosis.json")
    manifest = read(RUN / "manifest.json")
    assert selection["split_id"] == manifest["split_id"]
    dataset = ROOT / "data/ASCAD.h5"
    assert hashlib.sha256(dataset.read_bytes()).hexdigest() == selection["dataset_sha256"]
    with np.load(RUN / "splits.npz", allow_pickle=False) as archive:
        training, validation = archive["training"], archive["validation"]
    with h5py.File(dataset, "r") as handle:
        profiling = handle["Profiling_traces"]
        train_mean = profiling["traces"][training].mean(axis=0, dtype=np.float64)
        traces = profiling["traces"][validation].astype(np.float64)
        metadata = profiling["metadata"][validation]
        plaintext = metadata["plaintext"][:, 2]
        keys = np.unique(metadata["key"][:, 2])
        assert len(keys) == 1
        true_key = int(keys[0])
    hw = np.array([i.bit_count() for i in range(256)])
    hypotheses = hw[candidate_labels(plaintext)]
    rng = np.random.default_rng(8001)
    orders = [rng.permutation(len(traces))[:2000] for _ in range(20)]
    permutations = [np.random.default_rng(20261004 + i).permutation(len(traces)) for i in range(8)]
    results, curves = {}, {}
    for family, specification in selection["selected_products"].items():
        pair = specification["selected_pair"]
        assert specification["training_only_centering_and_selection"]
        values = (traces[:, pair[0]] - train_mean[pair[0]]) * (traces[:, pair[1]] - train_mean[pair[1]])
        ranks = np.stack([conservative_absolute_ranks(prefix_correlations(values[o], hypotheses[o]), true_key)
                          for o in orders])
        sr, ge = (ranks == 0).mean(axis=0), ranks.mean(axis=0)
        sustained = np.flatnonzero(np.logical_and.accumulate((sr >= .9)[::-1])[::-1])
        full_correlation = prefix_correlations(values, hypotheses)[-1]
        controls = []
        for permutation in permutations:
            control_ranks = np.array([conservative_absolute_ranks(
                prefix_correlations(values[permutation[o]], hypotheses[o])[-1:], true_key)[0] for o in orders])
            controls.append({"ge_at_budget": float(control_ranks.mean()),
                             "sr_at_budget": float((control_ranks == 0).mean())})
        results[family] = {"pair": pair, "selection": "Existing training-only PoI selection; no validation pair search",
            "ge_at_budget": float(ge[-1]), "sr_at_budget": float(sr[-1]),
            "traces_to_sustained_sr90": int(sustained[0] + 1) if len(sustained) else None,
            "full_validation_true_key_correlation": float(full_correlation[true_key]),
            "full_validation_absolute_rank": int(conservative_absolute_ranks(full_correlation[None], true_key)[0]),
            "row_shuffled_product_controls": controls}
        curves[family + "_ranks"] = ranks
        curves[family + "_sr"] = sr
        curves[family + "_ge"] = ge
        print("Completed correlation family:", family, flush=True)
    assert before == code_identity()["source_sha256"]
    assert hashes == {n:hashlib.sha256((RUN / n).read_bytes()).hexdigest() for n in hashes}
    record = {"scope": "CPU validation diagnosis with existing training-selected centered products; no classifier training",
        "split": "profiling_validation", "budget": 2000, "repetitions": 20, "order_seed": 8001,
        "control_product_permutations": 8, "control_seed_start": 20261004,
        "controls_are_descriptive_not_formal_p_values": True,
        "score": "Absolute prefix Pearson correlation with HW(Sbox(plaintext xor candidate key))",
        "rank": "zero based; all equally good wrong keys precede correct; tolerance1e-12",
        "model_inputs": "Selected trace products and public plaintext hypotheses; no validation masks or true key as input",
        "true_key_usage": "Only to report the correct hypothesis rank/correlation",
        "center_fit": "10k training traces only", "source_sha256": before,
        "checkpoint_hashes_unchanged": hashes, "attack_set_read": False,
        "full_gpu_trainings_total": 3, "results": results, "seconds": time.perf_counter() - started}
    write_json(OUTPUT / "second_order_correlation.json", record)
    np.savez_compressed(OUTPUT / "second_order_correlation_curves.npz", **curves)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
