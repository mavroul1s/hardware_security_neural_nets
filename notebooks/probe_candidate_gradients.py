"""Check gradients with fixed checkpoint weights; never take an optimizer step."""
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from sca.data import load_profiling, normalize
from sca.models import build_model
from candidate_cnn import build_candidate_cnn

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/kaggle_control/baseline_v3_output/runs/minimal_v1/none_seed0"
torch.set_num_threads(2)
checkpoint_path = RUN / "last.pt"
before = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
# Our own checkpoint from the verified notebook run, loaded for a fixed-weight probe.
checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
with np.load(RUN / "splits.npz", allow_pickle=False) as splits:
    x, y, _, _ = load_profiling(ROOT / "data/ASCAD.h5", splits["training"][:128], splits["validation"][:1])
x = torch.from_numpy(normalize(x, checkpoint["normalizer"]))
y = torch.from_numpy(y)
report = {"scope": "fixed-weight gradient probe on 128 training rows, no optimizer steps",
          "candidate_change": "ReLU -> LeakyReLU(negative_slope=0.1), all three activations",
          "checkpoint_epoch": int(checkpoint["epoch"]), "models": {}}
for name, model in (("existing", build_model("cnn")), ("candidate", build_candidate_cnn())):
    model.load_state_dict(checkpoint["model"])
    model.eval()
    logits = model(x)
    assert logits.shape == (128, 256) and torch.isfinite(logits).all()
    loss = torch.nn.functional.cross_entropy(logits, y)
    loss.backward()
    assert all(torch.isfinite(parameter.grad).all() for parameter in model.parameters())
    gradient = model[8].weight.grad.norm(dim=1)
    report["models"][name] = {"parameters": sum(p.numel() for p in model.parameters()),
        "dense_units_zero_weight_gradient": int((gradient == 0).sum()),
        "dense_units_nonzero_weight_gradient": int((gradient > 0).sum()),
        "loss_at_existing_weights": float(loss.detach()),
        "meaning": "candidate logits/loss are a diagnostic, not trained model performance"}
    assert report["models"][name]["parameters"] == 197424
assert hashlib.sha256(checkpoint_path.read_bytes()).hexdigest() == before
report["checkpoint_unchanged"] = True
(ROOT / "outputs/baseline_diagnosis_2026-10-03/candidate_gradient_probe.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
