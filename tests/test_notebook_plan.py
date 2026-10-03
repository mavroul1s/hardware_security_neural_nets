"""Exercise notebook stage transitions without consuming a GPU or training models."""
import json
import math
import time
from pathlib import Path

import pytest

from sca.train import write_json


def test_single_notebook_reuses_epochs_for_four_current_study_models(tmp_path):
    root = Path(__file__).resolve().parents[1]
    notebook_paths = list((root / "notebooks").glob("*.ipynb"))
    assert len(notebook_paths) == 1
    notebook = json.loads(notebook_paths[0].read_text(encoding="utf-8"))
    cells = ["".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"]
    base = json.loads((root / "configs/baseline_cnn.json").read_text())
    matrix = json.loads((root / "configs/matrix.json").read_text())
    evaluation = json.loads((root / "configs/evaluation_final.json").read_text())
    assert matrix["training_runs"] == 4 and matrix["seeds"] == [0]
    assert matrix["training_budgets"] == [10000]
    states, added_epochs, evaluations = {}, [], []
    source = {"source_sha256": "dry-run-source", "git_commit": None, "git_dirty": None}

    def fake_train(config, resume=False, reuse_completed=False):
        assert reuse_completed and config["model"] == base["model"]
        name = Path(config["run_dir"]).name
        assert resume == (name in states)
        path = Path(config["run_dir"])
        path.mkdir(parents=True, exist_ok=True)
        previous = states.get(name, 0)
        epochs = max(previous, config["epochs"])
        added_epochs.append(epochs - previous)
        states[name] = epochs
        steps = math.ceil(config["n_train"] / config["batch_size"])
        write_json(path / "history.json", [{"epoch": n, "steps": n * steps,
                                            "train_seconds": 0.1} for n in range(1, epochs + 1)])
        write_json(path / "manifest.json", {"config": config, "code": source})
        (path / "last.pt").write_bytes(b"orchestration fixture, not a model")
        return {"epochs": epochs, "optimization_steps": epochs * steps}

    def fake_evaluate(*args, **kwargs):
        evaluations.append(kwargs["split"])
        return []

    namespace = {"json": json, "Path": Path, "time": time, "base": base, "matrix": matrix,
        "run_root": tmp_path / "runs", "DATASET_PATH": tmp_path / "unused.h5",
        "train": fake_train, "write_json": write_json, "evaluate_cached": fake_evaluate,
        "benchmark_evaluation": evaluation, "validation_config": evaluation,
        "code_identity": lambda: source, "PROTOCOL_FROZEN": False}
    # Redirect absolute output paths while keeping notebook logic unchanged.
    training_cell = cells[3].replace('Path("/kaggle/working")', "run_root")
    comparison_cell = cells[4].replace('Path("configs/evaluation_final.json")',
                                       "Path(" + repr(str(root / "configs/evaluation_final.json")) + ")")
    for stage in ("benchmark", "baseline", "compare", "compare"):
        namespace["STAGE"] = stage
        exec(training_cell, namespace)
        exec(comparison_cell, namespace)
    assert len(states) == 4 and set(states.values()) == {50}
    assert added_epochs[:2] == [3, 47]
    assert sum(added_epochs) == 200
    assert namespace["total_steps"] == 15800
    namespace["STAGE"] = "attack"
    before = len(added_epochs)
    with pytest.raises(RuntimeError, match="Freeze"):
        exec(comparison_cell, namespace)
    namespace["PROTOCOL_FROZEN"] = True
    exec(training_cell, namespace)
    exec(comparison_cell, namespace)
    assert len(added_epochs) == before
    assert evaluations.count("attack") == 4
