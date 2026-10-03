"""Estimate training loop cost only, using measurements from the same device."""
import argparse
import json
import math
from pathlib import Path


def estimate(run_dir, matrix_path):
    run_dir = Path(run_dir)
    history = json.loads((run_dir / "history.json").read_text(encoding="utf-8"))
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    matrix = json.loads(Path(matrix_path).read_text(encoding="utf-8"))
    base = json.loads(Path(matrix["base_config"]).read_text(encoding="utf-8"))
    rows = history[1:] if len(history) > 1 else history
    seconds_per_epoch = sum(r["train_seconds"] for r in rows) / len(rows)
    seconds_per_step = seconds_per_epoch / math.ceil(config["n_train"] / config["batch_size"])
    runs_per_budget = len(matrix["strategies"]) * len(matrix["seeds"])
    steps = sum(math.ceil(n / base["batch_size"]) * base["epochs"] * runs_per_budget
                for n in matrix["training_budgets"])
    return {"device": manifest["environment"], "benchmark_config": config,
        "measured_seconds_per_step": seconds_per_step, "estimated_matrix_steps": steps,
        "estimated_training_hours_same_device": steps * seconds_per_step / 3600,
        "estimated_hours_with_50pct_margin": steps * seconds_per_step * 1.5 / 3600,
        "scope": "training loop only; excludes validation, evaluation, I/O, HPO and corruption overhead differences",
        "matrix_snapshot": matrix,
        "warning": "Same-device reference estimate only; one strategy does not measure the others' augmentation overhead. CPU timings are not Kaggle GPU timings."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("--matrix", default="configs/matrix.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = estimate(args.run_dir, args.matrix)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
