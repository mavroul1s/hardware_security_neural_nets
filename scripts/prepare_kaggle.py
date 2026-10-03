"""Generate a notebook calling the shared package and a data-free upload bundle."""
import ast
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cell(kind, content):
    result = {"cell_type": kind, "metadata": {}, "source": content.strip() + "\n"}
    if kind == "code":
        ast.parse(result["source"])
        result.update(execution_count=None, outputs=[])
    return result


def prepare():
    cells = [
        cell("markdown", """
# ASCAD fixed-key: ένα notebook, τέσσερις εκπαιδεύσεις

Αυτό το notebook καλεί τον κοινό κώδικα `src/sca`, χωρίς αντιγραφή training/ranking.
Δεν έχει εκτελεστεί στο Kaggle από τη δημιουργία του. Πρόσθεσε ως Inputs το code bundle
και το επίσημο `ASCAD.h5`. Έλεγξε Accelerator/remaining GPU quota πριν την εκτέλεση.
Στάδια στο ίδιο notebook: `benchmark` → `baseline` → `compare` → `attack`.
Το benchmark είναι οι πρώτες 3 epochs του baseline και συνεχίζεται από checkpoint.
Τέσσερα CNNs συνολικά: none/noise/shift/combined, 10k traces, seed0. Κανένα MLP ή seed sweep.
Το τελικό attack set μένει κλειστό μέχρι το protocol freeze. Ένα seed δίνει διερευνητικό αποτέλεσμα.
        """),
        cell("code", """
import os
import sys
import json
import shutil
import zipfile
import subprocess
import time
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
PROJECT_ROOT = Path("/kaggle/working/hardware_sca")
INPUT_ROOT = Path("/kaggle/input")
archives = list(INPUT_ROOT.rglob("kaggle_project.zip"))
roots = [p.parent for p in INPUT_ROOT.rglob("pyproject.toml") if (p.parent / "src/sca/train.py").is_file()]
if not PROJECT_ROOT.exists():
    if len(archives) == 1:
        PROJECT_ROOT.mkdir(parents=True)
        with zipfile.ZipFile(archives[0]) as bundle:
            for member in bundle.infolist():
                destination = (PROJECT_ROOT / member.filename).resolve()
                if not destination.is_relative_to(PROJECT_ROOT.resolve()):
                    raise ValueError("Unsafe bundle member")
            bundle.extractall(PROJECT_ROOT)
    elif len(roots) == 1:
        shutil.copytree(roots[0], PROJECT_ROOT)
    else:
        raise RuntimeError("Add exactly one project code Input: kaggle_project.zip or its extracted files")
os.chdir(PROJECT_ROOT)
datasets = list(INPUT_ROOT.rglob("ASCAD.h5"))
if len(datasets) != 1:
    raise RuntimeError("Add exactly one Input containing the official synchronized ASCAD.h5")
DATASET_PATH = datasets[0]
print("Project:", PROJECT_ROOT, "Dataset:", DATASET_PATH)
        """),
        cell("markdown", """
## Environment

Η εγκατάσταση απαιτεί Internet on. Αν έχεις offline pinned wheels ή επιλέξεις το Kaggle
preinstalled runtime, βάλε `PIN_DEPENDENCIES=False`. Οι πραγματικές εκδόσεις αποθηκεύονται.
Αν το kernel έχει ήδη εισαγάγει παλιές εκδόσεις, κάνε restart και ξανατρέξε τις cells.
        """),
        cell("code", """
PIN_DEPENDENCIES = True
if PIN_DEPENDENCIES:
    subprocess.run([sys.executable, "-m", "pip", "install", "torch==2.8.0",
                    "--index-url", "https://download.pytorch.org/whl/cu126"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt",
                    "setuptools==78.1.0"], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", "--no-build-isolation", "-e", "."], check=True)
sys.path.insert(0, str(PROJECT_ROOT / "src"))
import torch
from sca.train import train, environment, write_json, code_identity
from sca.data import inspect_dataset
from sca.evaluate import evaluate_cached

if not torch.cuda.is_available():
    raise RuntimeError("CUDA is unavailable. Select a GPU in Notebook Settings before the GPU experiment")
print(environment(torch.device("cuda")))
print(inspect_dataset(DATASET_PATH, verify_attack=False))
subprocess.run([sys.executable, "-m", "pytest", "-q"], check=True)
freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
(Path("/kaggle/working") / "environment-freeze.txt").write_text(freeze)
        """),
        cell("code", """
# Enter the quota shown in your account; no default quota is assumed.
AVAILABLE_GPU_HOURS = None
SESSION_LIMIT_HOURS = None
STAGE = "benchmark"  # benchmark, baseline, compare, attack
PROTOCOL_FROZEN = False
RUN_TAG = "minimal_v1"
RESTORE_ARCHIVE = None  # Previous sca_runs_minimal_v1.zip added as a private Input, if needed.

base = json.loads(Path("configs/baseline_cnn.json").read_text())
matrix = json.loads(Path("configs/matrix.json").read_text())
validation_config = json.loads(Path("configs/evaluation_final.json").read_text())
validation_config["conditions"] = [c for c in validation_config["conditions"]
    if c["name"] in ("clean", "combined_matched", matrix["primary_condition"])]
validation_config["repetitions"] = 20
benchmark_evaluation = json.loads(Path("configs/evaluation_pilot.json").read_text())
run_root = Path("/kaggle/working/runs") / RUN_TAG
if STAGE not in ("benchmark", "baseline", "compare", "attack"):
    raise ValueError("Unknown STAGE")
if matrix["training_budgets"] != [base["n_train"]] or matrix["seeds"] != [base["seed"]]:
    raise ValueError("This notebook supports the minimal one-budget, one-seed study")
if len(matrix["strategies"]) != matrix["training_runs"] or matrix["training_runs"] != 4:
    raise ValueError("The minimal study requires exactly four strategies")
if RESTORE_ARCHIVE and (not run_root.exists() or not any(run_root.iterdir())):
    run_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(RESTORE_ARCHIVE) as previous:
        for member in previous.infolist():
            if not (run_root / member.filename).resolve().is_relative_to(run_root.resolve()):
                raise ValueError("Unsafe run archive member")
        previous.extractall(run_root)
write_json(Path("/kaggle/working") / "account_budget.json", {
    "available_gpu_hours_user_entered": AVAILABLE_GPU_HOURS,
    "session_limit_hours_user_entered": SESSION_LIMIT_HOURS,
    "device": environment(torch.device("cuda")), "code": code_identity()})
        """),
        cell("code", """
import math

def train_strategy(strategy, epochs):
    config = {**base, "dataset": str(DATASET_PATH), "device": "cuda", "epochs": epochs,
              "run_dir": str(run_root / (strategy + "_seed0")),
              "augmentation": matrix["strategies"][strategy]}
    resume = (Path(config["run_dir"]) / "last.pt").exists()
    started = time.perf_counter()
    summary = train(config, resume=resume, reuse_completed=True)
    print(strategy, summary)
    write_json(Path(config["run_dir"]) / ("call_" + STAGE + ".json"), {
        "stage": STAGE, "training_call_seconds": time.perf_counter() - started,
        "requested_epochs": epochs, "resume_or_reuse": resume})
    return config, summary

if STAGE != "attack":
    config, summary = train_strategy("none", matrix["benchmark_epochs"] if STAGE == "benchmark" else base["epochs"])
    history = json.loads((Path(config["run_dir"]) / "history.json").read_text())
    measured = history[1:matrix["benchmark_epochs"]]
    steps_per_epoch = math.ceil(base["n_train"] / base["batch_size"])
    per_step = sum(r["train_seconds"] for r in measured) / (len(measured) * steps_per_epoch)
    total_steps = matrix["training_runs"] * base["epochs"] * steps_per_epoch
    completed_steps = sum(json.loads(p.read_text())[-1]["steps"]
                          for p in run_root.glob("*_seed0/history.json"))
    report = {"planned_unique_trainings": 4, "benchmark_additional_trainings": 0,
        "planned_total_steps": total_steps, "completed_steps": completed_steps,
        "reference_seconds_per_step_none": per_step,
        "estimated_remaining_training_hours_with_50pct_margin":
            max(0, total_steps - completed_steps) * per_step * 1.5 / 3600,
        "scope": "same GPU, none reference only; augmentation overhead unmeasured",
        "excluded_costs": "validation, evaluation, HPO, setup and I/O"}
    write_json(Path("/kaggle/working") / "gpu_cost_estimate.json", report)
    print(json.dumps(report, indent=2))
    diagnostics = benchmark_evaluation if STAGE == "benchmark" else validation_config
    evaluate_cached(config["run_dir"], diagnostics, device="cuda", split="validation",
                    dataset_override=DATASET_PATH)
        """),
        cell("markdown", """
Διάβασε το `gpu_cost_estimate.json` και τα validation αποτελέσματα πριν την πλήρη εκπαίδευση.
Τα benchmark runs δεν είναι ανεξάρτητα seed sweeps ούτε τελική ερευνητική απόδειξη.
Στο `baseline` συνεχίζονται οι πρώτες 3 epochs μέχρι 50· δεν ξεκινά νέο μοντέλο.
Έλεγξε το baseline στο validation πριν επιλέξεις `compare` για τις άλλες 3 στρατηγικές.
Ολοκληρωμένα runs και ίδιες αξιολογήσεις επαναχρησιμοποιούνται. Πάγωσε το πρωτόκολλο πριν το `attack`.
        """),
        cell("code", """
if STAGE == "compare":
    for strategy in matrix["strategies"]:
        if strategy == "none":
            continue
        config, summary = train_strategy(strategy, base["epochs"])
        evaluate_cached(config["run_dir"], validation_config, device="cuda", split="validation",
                        dataset_override=DATASET_PATH)

if STAGE == "attack":
    if not PROTOCOL_FROZEN:
        raise RuntimeError("Freeze and review the protocol before final attack evaluation")
    final_config = json.loads(Path("configs/evaluation_final.json").read_text())
    records = {}
    current_source = code_identity()["source_sha256"]
    for strategy in matrix["strategies"]:
        path = run_root / (strategy + "_seed0")
        history = json.loads((path / "history.json").read_text())
        if history[-1]["epoch"] != base["epochs"]:
            raise RuntimeError("Complete all four trainings before the final attack stage")
        records[strategy] = json.loads((path / "manifest.json").read_text())
        actual = records[strategy]
        expected = {**base, "augmentation": matrix["strategies"][strategy], "device": "cuda"}
        ignored = {"dataset", "run_dir"}
        if {k: v for k, v in actual["config"].items() if k not in ignored} != {
            k: v for k, v in expected.items() if k not in ignored}:
            raise RuntimeError("Training config differs from the planned four-strategy comparison")
        if actual["code"]["source_sha256"] != current_source:
            raise RuntimeError("Code changed since training; review before freezing the protocol")
    freeze = {"matrix": matrix, "base_config": base, "evaluation_config": final_config,
              "training_manifests": records, "evaluation_code": code_identity()}
    freeze_path = run_root / "protocol_freeze.json"
    if freeze_path.exists() and json.loads(freeze_path.read_text()) != freeze:
        raise RuntimeError("Frozen protocol changed; do not tune after viewing attack results")
    write_json(freeze_path, freeze)
    for strategy in matrix["strategies"]:
        evaluate_cached(run_root / (strategy + "_seed0"), final_config, device="cuda", split="attack",
                        dataset_override=DATASET_PATH)
        """),
        cell("code", """
# Save and download this archive plus the small output JSON files before ending the session.
if run_root.exists():
    summaries = {strategy: json.loads((run_root / (strategy + "_seed0") / "summary.json").read_text())
                 for strategy in matrix["strategies"]
                 if (run_root / (strategy + "_seed0") / "summary.json").exists()}
    write_json(run_root / "study_summary.json", {"stage": STAGE, "training_summaries": summaries,
        "unique_trainings": len(summaries), "planned_unique_trainings": 4,
        "completed_training_steps": sum(s["optimization_steps"] for s in summaries.values()),
        "measured_training_loop_seconds": sum(s["train_seconds"] for s in summaries.values()),
        "uncertainty": "one seed; no estimate of between-training variability"})
    archive_path = shutil.make_archive(str(Path("/kaggle/working") / ("sca_runs_" + RUN_TAG)), "zip", run_root)
    print("Download:", archive_path)
print("Notebook creation alone is not execution; retain Kaggle Save & Run All output")
        """),
    ]
    notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"}}, "nbformat": 4, "nbformat_minor": 4}
    (ROOT / "notebooks").mkdir(exist_ok=True)
    (ROOT / "notebooks/kaggle_baseline.ipynb").write_text(json.dumps(notebook, indent=2, ensure_ascii=False), encoding="utf-8")
    (ROOT / "outputs").mkdir(exist_ok=True)
    allowed_dirs = ("src", "scripts", "configs", "notebooks", "tests", "docs", "literature")
    files = []
    for directory in allowed_dirs:
        files.extend(p for p in (ROOT / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts
                     and p.suffix in (".py", ".json", ".ipynb", ".md", ".bib"))
    files.extend(ROOT / name for name in ("README.md", "AGENTS.md", "PROJECT_PLAN.md", "PROGRESS.md",
        "pyproject.toml", "requirements.txt", "requirements-lock-cpu.txt") if (ROOT / name).exists())
    archive_path = ROOT / "outputs/kaggle_project.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, path.relative_to(ROOT).as_posix())
    print(json.dumps({"notebook": "notebooks/kaggle_baseline.ipynb", "syntax_checked_code_cells": sum(c["cell_type"] == "code" for c in cells),
        "bundle": str(archive_path), "bundle_bytes": archive_path.stat().st_size, "files": len(files)}))


if __name__ == "__main__":
    prepare()
