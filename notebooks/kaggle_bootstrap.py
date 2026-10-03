"""Discover project/data and restore existing runs before importing the training package."""
import hashlib
import json
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_sha256(root):
    root = Path(root)
    files = sorted([*root.glob("src/**/*.py"), *root.glob("scripts/*.py"),
                    *root.glob("configs/*.json"), root / "pyproject.toml"])
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def archive_project_sha256(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        required = {"pyproject.toml", "src/sca/train.py", "requirements.txt", "tests/test_core.py"}
        if not required.issubset(names):
            return None
        selected = sorted(name for name in names if name == "pyproject.toml" or
                          (name.startswith("src/") and name.endswith(".py")) or
                          (name.startswith("scripts/") and name.count("/") == 1 and name.endswith(".py")) or
                          (name.startswith("configs/") and name.count("/") == 1 and name.endswith(".json")))
        digest = hashlib.sha256()
        for name in selected:
            digest.update(name.encode())
            digest.update(archive.read(name))
        return digest.hexdigest()


def extract_checked(path, destination):
    destination = Path(destination).resolve()
    with zipfile.ZipFile(path) as archive:
        if sum(member.file_size for member in archive.infolist()) > 256 * 1024 * 1024:
            raise ValueError("Unexpectedly large project/run input archive")
        for member in archive.infolist():
            relative = PurePosixPath(member.filename)
            if (relative.is_absolute() or ".." in relative.parts or
                    "\\" in member.filename or ":" in member.filename or
                    stat.S_ISLNK(member.external_attr >> 16) or
                    not (destination / member.filename).resolve().is_relative_to(destination)):
                raise ValueError("Unsafe archive member: " + member.filename)
        destination.mkdir(parents=True, exist_ok=True)
        archive.extractall(destination)


def bootstrap_inputs(input_root, project_root, run_root, expected_dataset_sha256,
                     expected_source_sha256=None, require_checkpoint=True):
    input_root, project_root, run_root = map(Path, (input_root, project_root, run_root))
    staging = project_root.parent / "input_assets"
    search_roots = [input_root]
    print("Input folders:", [str(p) for p in sorted(input_root.iterdir())] if input_root.exists() else [])
    containers = [p for p in input_root.rglob("*.zip")
                  if p.stem.startswith(("kaggle_resume_input", "results"))]
    for container in sorted(containers):
        extracted = staging / file_sha256(container)[:16]
        marker = extracted / ".bootstrap_complete"
        if not marker.exists():
            extract_checked(container, extracted)
            marker.write_text(file_sha256(container), encoding="utf-8")
        search_roots.append(extracted)
    code_candidates, dataset_candidates, restore_candidates, restore_folders = [], [], [], []
    for search_root in search_roots:
        for path in search_root.rglob("pyproject.toml"):
            candidate = path.parent
            if (candidate / "src/sca/train.py").is_file() and (candidate / "requirements.txt").is_file():
                code_candidates.append((candidate, project_sha256(candidate), False))
        for path in search_root.rglob("*.zip"):
            identity = archive_project_sha256(path)
            if identity is not None:
                code_candidates.append((path, identity, True))
        dataset_candidates.extend(search_root.rglob("ASCAD*.h5"))
        restore_candidates.extend(search_root.rglob("sca_runs_minimal_v1.zip"))
        restore_folders.extend(path.parent.parent for path in search_root.rglob("last.pt")
                               if path.parent.name == "none_seed0" and
                               (path.parent / "manifest.json").is_file() and
                               (path.parent / "history.json").is_file())
    if (project_root / "src/sca/train.py").is_file():
        code_candidates.append((project_root, project_sha256(project_root), False))
    print("Code sources:", [(str(p), h) for p, h, _ in code_candidates])
    print("ASCAD files:", [str(p) for p in dataset_candidates])
    print("Restore archives:", [str(p) for p in restore_candidates])
    print("Extracted run folders:", [str(p) for p in restore_folders])
    valid_datasets = [p for p in sorted(set(dataset_candidates))
                      if file_sha256(p) == expected_dataset_sha256]
    if not valid_datasets:
        raise RuntimeError("ASCAD.h5 is missing or has the wrong checksum. Add the original data Input or kaggle_resume_input.zip.")
    restores = {file_sha256(p): p for p in sorted(set(restore_candidates))}
    if len(restores) > 1 and not (run_root / "none_seed0/last.pt").exists():
        raise RuntimeError("Different restore archives are attached. Keep only the intended checkpoint Input.")
    restore = next(iter(restores.values()), None)
    folders = {file_sha256(p / "none_seed0/last.pt"): p for p in sorted(set(restore_folders))}
    checkpoint_hashes = set(folders)
    for archive_path in restores.values():
        with zipfile.ZipFile(archive_path) as archive:
            checkpoint_hashes.add(hashlib.sha256(archive.read("none_seed0/last.pt")).hexdigest())
    if len(checkpoint_hashes) > 1 and not (run_root / "none_seed0/last.pt").exists():
        raise RuntimeError("Different restore checkpoints are attached. Keep only the intended checkpoint Input.")
    restore_folder = next(iter(folders.values()), None)
    manifest_path = run_root / "none_seed0/manifest.json"
    if manifest_path.exists():
        checkpoint_source = json.loads(manifest_path.read_text())["code"]["source_sha256"]
    elif restore is not None:
        with zipfile.ZipFile(restore) as archive:
            checkpoint_source = json.loads(archive.read("none_seed0/manifest.json"))["code"]["source_sha256"]
    elif restore_folder is not None:
        checkpoint_source = json.loads((restore_folder / "none_seed0/manifest.json").read_text())["code"]["source_sha256"]
    else:
        checkpoint_source = expected_source_sha256
    if expected_source_sha256 and checkpoint_source != expected_source_sha256:
        raise RuntimeError("The checkpoint uses a different code version.")
    matches = [(p, h, is_archive) for p, h, is_archive in code_candidates
               if checkpoint_source is None or h == checkpoint_source]
    if not matches:
        raise RuntimeError("Project code is missing or does not match the checkpoint. Add kaggle_project.zip or kaggle_resume_input.zip.")
    if len({h for _, h, _ in matches}) > 1:
        raise RuntimeError("Different code versions are attached. Select the intended project Input.")
    candidate, identity, is_archive = matches[0]
    if project_root.exists():
        if not (project_root / "src/sca/train.py").is_file() or project_sha256(project_root) != identity:
            raise RuntimeError("Existing working project is incomplete/different. Use a fresh session with the resume Input.")
    elif is_archive:
        extract_checked(candidate, project_root)
    else:
        shutil.copytree(candidate, project_root)
    if project_sha256(project_root) != identity:
        raise RuntimeError("Extracted project fingerprint mismatch")
    last_checkpoint = run_root / "none_seed0/last.pt"
    if not last_checkpoint.exists() and (restore is not None or restore_folder is not None):
        if run_root.exists() and any(run_root.iterdir()):
            raise RuntimeError("Existing run folder is incomplete; refusing to overwrite it.")
        if restore is not None:
            extract_checked(restore, run_root)
        else:
            run_root.mkdir(parents=True, exist_ok=True)
            for name in ("none_seed0", "noise_seed0", "shift_seed0", "combined_seed0"):
                if (restore_folder / name).is_dir():
                    shutil.copytree(restore_folder / name, run_root / name)
            for name in ("study_summary.json", "protocol_freeze.json"):
                if (restore_folder / name).is_file():
                    shutil.copy2(restore_folder / name, run_root / name)
    if require_checkpoint and not last_checkpoint.exists():
        raise RuntimeError("Checkpoint Input is missing. Add sca_runs_minimal_v1.zip or kaggle_resume_input.zip to continue baseline.")
    if last_checkpoint.exists():
        restored = json.loads((run_root / "none_seed0/manifest.json").read_text())
        if restored["code"]["source_sha256"] != identity or restored["dataset_sha256"] != expected_dataset_sha256:
            raise RuntimeError("Restored run does not match the selected code/data")
        history = json.loads((run_root / "none_seed0/history.json").read_text())
        print("Existing checkpoint kept. Completed epoch:", history[-1]["epoch"])
    print("Project:", project_root, "Dataset:", valid_datasets[0], "Source SHA256:", identity)
    return valid_datasets[0]
