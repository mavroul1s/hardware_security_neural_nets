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
# ASCAD fixed-key: GPU benchmark και πρώτο baseline

Αυτό το notebook καλεί τον κοινό κώδικα `src/sca`, χωρίς αντιγραφή training/ranking.
Δεν έχει εκτελεστεί στο Kaggle από τη δημιουργία του. Πρόσθεσε ως Inputs το code bundle
και το επίσημο `ASCAD.h5`. Έλεγξε Accelerator/remaining GPU quota πριν την εκτέλεση.
Αρχικά τρέχουμε μόνο benchmark. Το τελικό attack set μένει κλειστό μέχρι το protocol freeze.
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
from sca.evaluate import evaluate

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
RUN_BENCHMARK = True
RUN_BASELINES = False
RUN_FINAL_ATTACK = False
PROTOCOL_FROZEN = False
RUN_TAG = "session1"

base = json.loads(Path("configs/baseline_cnn.json").read_text())
matrix = json.loads(Path("configs/matrix.json").read_text())
validation_config = json.loads(Path("configs/evaluation_final.json").read_text())
validation_config["budget"] = 1000
validation_config["repetitions"] = 20
run_root = Path("/kaggle/working/runs") / RUN_TAG
write_json(Path("/kaggle/working") / "account_budget.json", {
    "available_gpu_hours_user_entered": AVAILABLE_GPU_HOURS,
    "session_limit_hours_user_entered": SESSION_LIMIT_HOURS,
    "device": environment(torch.device("cuda")), "code": code_identity()})
        """),
        cell("code", """
import math

benchmark_reports = []
if RUN_BENCHMARK:
    for strategy, augmentation in matrix["strategies"].items():
        config = {**base, "dataset": str(DATASET_PATH), "device": "cuda", "epochs": 3,
                  "run_dir": str(run_root / ("benchmark_" + strategy)), "augmentation": augmentation}
        started = time.perf_counter()
        summary = train(config)
        elapsed = time.perf_counter() - started
        evaluate(config["run_dir"], validation_config, device="cuda", split="validation")
        history = json.loads((Path(config["run_dir"]) / "history.json").read_text())
        per_step = sum(r["train_seconds"] for r in history[1:]) / (2 * math.ceil(config["n_train"] / config["batch_size"]))
        estimated_steps = sum(math.ceil(n / base["batch_size"]) * base["epochs"] * len(matrix["seeds"])
                              for n in matrix["training_budgets"])
        estimated_hours = per_step * estimated_steps / 3600
        benchmark_reports.append({"strategy": strategy, "training_summary": summary,
            "benchmark_elapsed_seconds_including_setup_checkpoint": elapsed,
            "estimated_matrix_training_hours_this_strategy": estimated_hours})
    report = {"benchmarks": benchmark_reports,
        "estimated_training_hours_with_50pct_margin": 1.5 * sum(r["estimated_matrix_training_hours_this_strategy"] for r in benchmark_reports),
        "excluded_costs": "full validation, final attack evaluation, HPO, larger-run setup and I/O"}
    write_json(Path("/kaggle/working") / "gpu_cost_estimate.json", report)
    print(json.dumps(report, indent=2))
        """),
        cell("markdown", """
Διάβασε το `gpu_cost_estimate.json` και τα validation αποτελέσματα πριν την πλήρη εκπαίδευση.
Τα benchmark runs δεν είναι ανεξάρτητα seed sweeps ούτε τελική ερευνητική απόδειξη.
Το πλήρες matrix δεν εκκινείται από το παρόν notebook. Πάγωσε το πρωτόκολλο πριν δεις attack metrics.
        """),
        cell("code", """
if RUN_BASELINES:
    for model_name in ("cnn", "mlp"):
        config = json.loads(Path("configs/baseline_" + model_name + ".json").read_text())
        config.update(dataset=str(DATASET_PATH), device="cuda",
                      run_dir=str(run_root / ("baseline_" + model_name + "_seed0")))
        started = time.perf_counter()
        train(config)
        write_json(Path(config["run_dir"]) / "notebook_elapsed.json", {
            "training_call_seconds": time.perf_counter() - started})
        evaluate(config["run_dir"], validation_config, device="cuda", split="validation")
        if RUN_FINAL_ATTACK:
            if not PROTOCOL_FROZEN:
                raise RuntimeError("Freeze the protocol before final attack evaluation")
            final_config = json.loads(Path("configs/evaluation_final.json").read_text())
            evaluate(config["run_dir"], final_config, device="cuda", split="attack")
        """),
        cell("code", """
# Save and download this archive plus the small output JSON files before ending the session.
if run_root.exists():
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
