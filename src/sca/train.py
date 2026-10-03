"""Training, provenance and exact epoch-boundary continuation."""
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import hashlib
import json
import platform
import random
import subprocess
import time
import zipfile
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import h5py
import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from .augment import augment_batch
from .data import (inspect_dataset, make_splits, split_identifier, load_profiling,
                   fit_normalizer, normalize)
from .models import build_model


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def select_device(request):
    if request == "auto":
        request = "cuda" if torch.cuda.is_available() else "cpu"
    if request not in ("cpu", "cuda"):
        raise ValueError("device must be auto, cpu or cuda")
    if request == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA explicitly requested but unavailable")
    return torch.device(request)


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False


def source_files(root):
    return sorted([*root.glob("src/**/*.py"), *root.glob("scripts/*.py"),
                   *root.glob("configs/*.json"), root / "pyproject.toml"])


def code_identity():
    root = Path(__file__).resolve().parents[2]
    files = source_files(root)
    digest = hashlib.sha256()
    for file in files:
        digest.update(str(file.relative_to(root)).replace("\\", "/").encode())
        digest.update(file.read_bytes())
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, stderr=subprocess.DEVNULL, text=True))
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    return {"git_commit": commit, "git_dirty": dirty, "source_sha256": digest.hexdigest()}


def environment(device):
    return {"python": platform.python_version(), "platform": platform.platform(),
        "processor": platform.processor(), "logical_cpu_count": os.cpu_count(),
        "versions": {name: version(name) for name in ("torch", "numpy", "h5py", "matplotlib")},
        "device": str(device), "device_name": torch.cuda.get_device_name(device) if device.type == "cuda" else "CPU",
        "cuda_runtime": torch.version.cuda, "torch_threads": torch.get_num_threads()}


def rng_state(loader_generator):
    return {"python": random.getstate(), "numpy": np.random.get_state(), "torch": torch.get_rng_state(),
        "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        "loader": loader_generator.get_state()}


def restore_rng(state, loader_generator):
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch"].cpu())
    if state["cuda"] is not None and torch.cuda.is_available():
        torch.cuda.set_rng_state_all([item.cpu() for item in state["cuda"]])
    loader_generator.set_state(state["loader"].cpu())


def sync(device):
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def train(config, resume=False):
    config = dict(config)
    for key in ("epochs", "batch_size", "threads"):
        if not isinstance(config[key], int) or config[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    run_dir = Path(config["run_dir"])
    if run_dir.exists() and any(run_dir.iterdir()) and not resume:
        raise FileExistsError(f"Run already exists: {run_dir}; use --resume or a new directory")
    run_dir.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(config["threads"])
    device = select_device(config.get("device", "auto"))
    seed_everything(config["seed"])
    inspection = inspect_dataset(config["dataset"], config["target_byte"], verify_attack=False)
    if not inspection["synthetic"] and not inspection["official_checksum_match"]:
        raise ValueError("Expected the official ASCAD fixed-key checksum")
    n = inspection["groups"]["Profiling_traces"]["traces_shape"][0]
    train_indices, val_indices = make_splits(n, config["n_train"], config["n_validation"], config["split_seed"])
    split_id = split_identifier(train_indices, val_indices)
    xt, yt, xv, yv = load_profiling(config["dataset"], train_indices, val_indices)
    stats = fit_normalizer(xt)
    xt, xv = normalize(xt, stats), normalize(xv, stats)
    loader_generator = torch.Generator().manual_seed(config["seed"] + 10000)
    training_loader = DataLoader(TensorDataset(torch.from_numpy(xt), torch.from_numpy(yt)),
        batch_size=config["batch_size"], shuffle=True, generator=loader_generator, num_workers=0)
    validation_loader = DataLoader(TensorDataset(torch.from_numpy(xv), torch.from_numpy(yv)),
        batch_size=config["batch_size"], shuffle=False, num_workers=0)
    model = build_model(config["model"]).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
    criterion = torch.nn.CrossEntropyLoss()
    start_epoch, steps, best_loss = 0, 0, float("inf")
    history = []
    total_train_seconds, total_validation_seconds = 0.0, 0.0
    code = code_identity()
    current_environment = environment(device)
    if resume:
        # Only load checkpoints produced by this project from a trusted location.
        checkpoint = torch.load(run_dir / "last.pt", map_location=device, weights_only=False)
        ignored = {"epochs", "dataset", "run_dir"}
        if {k: v for k, v in checkpoint["config"].items() if k not in ignored} != {
            k: v for k, v in config.items() if k not in ignored
        } or checkpoint["dataset_sha256"] != inspection["sha256"] or checkpoint["split_id"] != split_id:
            raise ValueError("Resume config, dataset or splits mismatch")
        if checkpoint["code"]["source_sha256"] != code["source_sha256"]:
            raise ValueError("Code changed since checkpoint; exact continuation cannot be claimed")
        if checkpoint["environment"] != current_environment:
            raise ValueError("Environment/device changed since checkpoint")
        model.load_state_dict(checkpoint["model"])
        optimizer.load_state_dict(checkpoint["optimizer"])
        start_epoch, steps, best_loss = checkpoint["epoch"], checkpoint["steps"], checkpoint["best_loss"]
        history = checkpoint["history"]
        total_train_seconds = checkpoint["train_seconds"]
        total_validation_seconds = checkpoint["validation_seconds"]
        restore_rng(checkpoint["rng"], loader_generator)
        if config["epochs"] <= start_epoch:
            raise ValueError("Requested epochs must exceed completed epochs")
    np.savez(run_dir / "splits.npz", training=train_indices, validation=val_indices)
    if not resume:
        root = Path(__file__).resolve().parents[2]
        with zipfile.ZipFile(run_dir / "code_snapshot.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            for path in source_files(root):
                archive.write(path, path.relative_to(root).as_posix())
    write_json(run_dir / "config.json", config)
    write_json(run_dir / "inspection.json", inspection)
    manifest = {"started_utc": datetime.now(timezone.utc).isoformat(), "config": config,
        "dataset_sha256": inspection["sha256"], "synthetic": inspection["synthetic"],
        "split_id": split_id, "normalizer": stats, "environment": current_environment, "code": code,
        "parameters": sum(p.numel() for p in model.parameters()),
        "expected_steps": config["epochs"] * len(training_loader), "resumed_at_epoch": start_epoch,
        "selection_rule": "minimum clean profiling-validation cross-entropy across fixed epochs",
        "source_snapshot": "code_snapshot.zip"}
    write_json(run_dir / "manifest.json", manifest)
    for epoch in range(start_epoch, config["epochs"]):
        model.train()
        loss_sum, correct, samples = 0.0, 0, 0
        sync(device)
        started = time.perf_counter()
        for x, y in training_loader:
            x, y = x.to(device), y.to(device)
            x = augment_batch(x, **config["augmentation"])
            optimizer.zero_grad(set_to_none=True)
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
            loss_sum += float(loss.detach()) * len(y)
            correct += int((logits.argmax(1) == y).sum())
            samples += len(y)
            steps += 1
        sync(device)
        train_seconds = time.perf_counter() - started
        model.eval()
        validation_loss, validation_correct = 0.0, 0
        started = time.perf_counter()
        with torch.no_grad():
            for x, y in validation_loader:
                x, y = x.to(device), y.to(device)
                logits = model(x)
                validation_loss += float(criterion(logits, y)) * len(y)
                validation_correct += int((logits.argmax(1) == y).sum())
        sync(device)
        validation_seconds = time.perf_counter() - started
        val_loss = validation_loss / len(yv)
        row = {"epoch": epoch + 1, "steps": steps, "train_loss": loss_sum / samples,
            "train_accuracy": correct / samples, "validation_loss": val_loss,
            "validation_accuracy": validation_correct / len(yv),
            "train_seconds": train_seconds, "validation_seconds": validation_seconds}
        history.append(row)
        total_train_seconds += train_seconds
        total_validation_seconds += validation_seconds
        improved = val_loss < best_loss
        best_loss = min(best_loss, val_loss)
        state = {"model": model.state_dict(), "optimizer": optimizer.state_dict(), "epoch": epoch + 1,
            "steps": steps, "best_loss": best_loss, "rng": rng_state(loader_generator),
            "config": config, "dataset_sha256": inspection["sha256"], "split_id": split_id,
            "normalizer": stats, "history": history, "train_seconds": total_train_seconds,
            "validation_seconds": total_validation_seconds, "code": code, "environment": current_environment,
            "synthetic": inspection["synthetic"]}
        temporary = run_dir / "last.pt.tmp"
        torch.save(state, temporary)
        temporary.replace(run_dir / "last.pt")
        if improved:
            torch.save(state, run_dir / "best.pt")
        write_json(run_dir / "history.json", history)
        print(json.dumps(row), flush=True)
    summary = {"epochs": config["epochs"], "optimization_steps": steps,
        "train_seconds": total_train_seconds, "validation_seconds": total_validation_seconds,
        "best_validation_loss": best_loss, "parameters": manifest["parameters"],
        "best_checkpoint_bytes": (run_dir / "best.pt").stat().st_size,
        "synthetic": inspection["synthetic"], "device": str(device),
        "timing_scope": "epoch loops, including augmentation/transfers; excludes setup, inspection and checkpoint I/O"}
    write_json(run_dir / "summary.json", summary)
    return summary
