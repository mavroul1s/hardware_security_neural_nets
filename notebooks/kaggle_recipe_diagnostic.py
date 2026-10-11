"""A declared optimizer extension for one frozen same-model Kaggle diagnostic."""
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from sca.data import sha256_file, load_validation_evaluation, normalize
from sca.evaluate import evaluate
from sca.models import build_model
from sca.train import code_identity, train, write_json

BaseAdam = torch.optim.Adam


def author_cycle_lr(completed_updates, total_updates, maximum=0.005):
    """Port the author's three linear phases, without momentum cycling."""
    if total_updates < 5 or not 0 <= completed_updates <= total_updates:
        raise ValueError("Invalid schedule position")
    middle = int(total_updates * 0.8 / 2)
    if completed_updates <= middle:
        return maximum * 0.1 * (1 + 9 * completed_updates / middle)
    if completed_updates <= 2 * middle:
        return maximum * 0.1 * (1 + 9 * (1 - (completed_updates - middle) / middle))
    return maximum * 0.1 * (1 - 0.99 * (completed_updates - 2 * middle) / (total_updates - 2 * middle))


class AuthorCycleAdam(BaseAdam):
    """Keep Adam semantics and checkpoint the exact schedule position."""
    def __init__(self, params, lr, *, total_updates, **kwargs):
        super().__init__(params, lr=author_cycle_lr(0, total_updates, lr), **kwargs)
        self.maximum = lr
        self.total_updates = total_updates
        self.completed_updates = 0
        self.used_rates = []
        self.started = time.perf_counter()

    def step(self, closure=None):
        if self.completed_updates >= self.total_updates:
            raise RuntimeError("Frozen optimizer update budget exhausted")
        if time.perf_counter() - self.started > 600:
            raise RuntimeError("Frozen training-loop cost cap exceeded")
        gradients = [p.grad.reshape(-1) for group in self.param_groups for p in group['params'] if p.grad is not None]
        if gradients and not bool(torch.isfinite(torch.cat(gradients)).all()):
            raise FloatingPointError("Nonfinite gradients; no automatic retry")
        self.used_rates.append(float(self.param_groups[0]["lr"]))
        result = super().step(closure)
        self.completed_updates += 1
        for group in self.param_groups:
            group["lr"] = author_cycle_lr(self.completed_updates, self.total_updates, self.maximum)
        return result

    def state_dict(self):
        state = super().state_dict()
        state["author_cycle"] = {"maximum": self.maximum, "total_updates": self.total_updates,
            "completed_updates": self.completed_updates, "used_rates": self.used_rates.copy()}
        return state

    def load_state_dict(self, state):
        state = dict(state)
        cycle = state.pop("author_cycle")
        if cycle["total_updates"] != self.total_updates or cycle["maximum"] != self.maximum:
            raise ValueError("Schedule identity mismatch")
        super().load_state_dict(state)
        self.completed_updates = cycle["completed_updates"]
        self.used_rates = cycle["used_rates"].copy()


def train_with_cycle(config, **kwargs):
    total = config["epochs"] * math.ceil(config["n_train"] / config["batch_size"])
    def optimizer_factory(params, lr):
        return AuthorCycleAdam(params, lr, total_updates=total)
    # The frozen production trainer remains unchanged; the extension is explicit in config/plan.
    with patch("torch.optim.Adam", optimizer_factory):
        return train(config, **kwargs)


def run_experiment(dataset, old_run, output, plan):
    old_run, output = Path(old_run), Path(output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("No automatic repeat or overwrite is authorized")
    output.mkdir(parents=True)
    started = time.perf_counter()
    source = code_identity()["source_sha256"]
    if source != plan["production_source_sha256"]:
        raise ValueError("Production source changed")
    if sha256_file(dataset) != plan["dataset_sha256"]:
        raise ValueError("Dataset changed")
    extension_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if extension_hash != plan["extension_sha256"]:
        raise ValueError("Optimizer extension changed")
    old_hashes = {name: sha256_file(old_run / name) for name in plan["baseline_hashes"]}
    if old_hashes != plan["baseline_hashes"]:
        raise ValueError("Baseline artifacts changed")
    original = json.loads((old_run / "config.json").read_text(encoding="utf-8"))
    config = dict(original)
    config.update(dataset=str(dataset), run_dir=str(output / "none_seed0"),
        batch_size=50, learning_rate=0.005, device="cuda",
        recipe_extension_sha256=extension_hash, recipe="author_linear_cycle_no_momentum")
    expected = {"n_train":10000,"n_validation":5000,"epochs":50,"seed":0,
        "split_seed":2026,"model":"cnn_literature","normalization":"feature_minmax_training_only"}
    if any(config[k] != v for k,v in expected.items()) or config["augmentation"]["noise_std"] != 0 or config["augmentation"]["max_shift"] != 0:
        raise ValueError("Frozen training scope mismatch")
    write_json(output / "plan.json", plan)
    write_json(output / "access.json", {"started_utc": datetime.now(timezone.utc).isoformat(),
        "attack_payloads_read":False,"new_confirmation_rows":0,"new_training_started":True})
    summary = train_with_cycle(config)
    run = output / "none_seed0"
    manifest = json.loads((run / "manifest.json").read_text())
    old_manifest = json.loads((old_run / "manifest.json").read_text())
    assert manifest["normalizer"] == old_manifest["normalizer"]
    assert manifest["split_id"] == old_manifest["split_id"]
    assert manifest["parameters"] == 16952 and summary["optimization_steps"] == 10000
    for name in ("training","validation"):
        assert np.array_equal(np.load(run / "splits.npz")[name], np.load(old_run / "splits.npz")[name])
    evaluation_config = plan["evaluation_config"]
    validation = evaluate(run, evaluation_config, device="cuda", split="validation", output_dir=output / "validation")
    best = torch.load(run / "best.pt", map_location="cpu", weights_only=False)
    traces, plaintext, key = load_validation_evaluation(dataset, np.load(run / "splits.npz")["validation"], 2)
    traces = normalize(traces, best["normalizer"])
    model = build_model("cnn_literature").cuda()
    model.load_state_dict(best["model"])
    model.eval()
    with torch.no_grad():
        lp = np.concatenate([torch.log_softmax(model(torch.from_numpy(traces[i:i+256]).cuda()).double(),dim=1).cpu().numpy()
            for i in range(0,len(traces),256)])
    np.save(output / "validation/log_probabilities.npy", lp)
    np.save(output / "validation/plaintext_byte.npy", plaintext)
    write_json(output / "validation/evaluation_key.json", {"true_key_byte":int(key),"evaluation_only":True})
    state = torch.load(run / "last.pt", map_location="cpu", weights_only=False)
    rates = state["optimizer"]["author_cycle"]["used_rates"]
    np.save(output / "learning_rates.npy", rates)
    assert len(rates) == 10000 and state["optimizer"]["author_cycle"]["completed_updates"] == 10000
    criterion = validation[0]["sr_at_budget"] >= 0.9
    after = {name: sha256_file(old_run / name) for name in old_hashes}
    assert after == old_hashes and code_identity()["source_sha256"] == source
    result = {"complete":True,"primary_met":bool(criterion),"validation":validation,"summary":summary,
        "experiment_seconds":time.perf_counter()-started,"new_gpu_trainings":1,"full_gpu_trainings_total":4,
        "combined_training_performed":False,"original_cnn_gate_unchanged":True,"attack_payloads_read":False,
        "new_confirmation_rows":0,"new_seeds":0,"same_epochs_and_trace_exposures":True,
        "update_budget_changed":True,"baseline_updates":3950,"new_updates":10000,
        "production_source_preserved":True,"baseline_hashes":after,"extension_sha256":extension_hash,
        "selection_rule":"minimum validation CE","interpretation":"Joint batch/schedule diagnostic; previously viewed validation, no independent efficacy or isolated-cause claim"}
    write_json(output / "results.json", result)
    print(json.dumps(result, indent=2), flush=True)
    return result
