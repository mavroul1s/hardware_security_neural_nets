"""Verify Input layouts and checkpoint preservation without starting training."""
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest


BOOTSTRAP_PATH = Path(__file__).resolve().parents[1] / "notebooks/kaggle_bootstrap.py"
SPEC = importlib.util.spec_from_file_location("kaggle_bootstrap", BOOTSTRAP_PATH)
BOOTSTRAP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOOTSTRAP)


def make_inputs(tmp_path):
    source = tmp_path / "source"
    for name, content in {"pyproject.toml": "[project]\nname='fixture'\n",
                          "src/sca/train.py": "# Fixture source; never executed.\n",
                          "scripts/example.py": "# Example\n",
                          "configs/example.json": "{}",
                          "requirements.txt": "", "tests/test_core.py": ""}.items():
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    source_sha = BOOTSTRAP.project_sha256(source)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    with zipfile.ZipFile(inputs / "kaggle_project.zip", "w") as archive:
        for path in source.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(source).as_posix())
    dataset = inputs / "ASCAD.h5"
    dataset.write_bytes(b"dataset fixture, not training data")
    dataset_sha = BOOTSTRAP.file_sha256(dataset)
    with zipfile.ZipFile(inputs / "sca_runs_minimal_v1.zip", "w") as archive:
        archive.writestr("none_seed0/last.pt", b"checkpoint fixture, never loaded")
        archive.writestr("none_seed0/manifest.json", json.dumps({"code": {"source_sha256": source_sha},
                                                                "dataset_sha256": dataset_sha}))
        archive.writestr("none_seed0/history.json", '[{"epoch": 3}]')
    return inputs, source, dataset_sha, source_sha


@pytest.mark.parametrize("layout", ["flat", "duplicates", "packed", "results", "fully_extracted"])
def test_bootstrap_restores_supported_layouts_without_overwriting_advanced_checkpoint(tmp_path, layout):
    inputs, source, dataset_sha, source_sha = make_inputs(tmp_path)
    if layout == "duplicates":
        (inputs / "duplicate").mkdir()
        (inputs / "duplicate/kaggle_project.zip").write_bytes((inputs / "kaggle_project.zip").read_bytes())
    elif layout == "packed":
        payloads = {p.name: p.read_bytes() for p in inputs.iterdir()}
        for path in list(inputs.iterdir()):
            path.unlink()
        with zipfile.ZipFile(inputs / "kaggle_resume_input.zip", "w") as archive:
            for name, payload in payloads.items():
                archive.writestr(name, payload)
    elif layout == "results":
        (inputs / "kaggle_project.zip").unlink()
        with zipfile.ZipFile(inputs / "results.zip", "w") as archive:
            for path in source.rglob("*"):
                if path.is_file():
                    archive.write(path, "hardware_sca/" + path.relative_to(source).as_posix())
    elif layout == "fully_extracted":
        for name, target in (("kaggle_project.zip", "kaggle_project"),
                             ("sca_runs_minimal_v1.zip", "sca_runs_minimal_v1")):
            with zipfile.ZipFile(inputs / name) as archive:
                archive.extractall(inputs / target)
            (inputs / name).unlink()
    project = tmp_path / "work/hardware_sca"
    runs = tmp_path / "work/runs/minimal_v1"
    dataset = BOOTSTRAP.bootstrap_inputs(inputs, project, runs, dataset_sha, source_sha)
    assert BOOTSTRAP.file_sha256(dataset) == dataset_sha
    assert BOOTSTRAP.project_sha256(project) == source_sha
    checkpoint = runs / "none_seed0/last.pt"
    assert checkpoint.read_bytes() == b"checkpoint fixture, never loaded"
    checkpoint.write_bytes(b"advanced checkpoint must remain untouched")
    BOOTSTRAP.bootstrap_inputs(inputs, project, runs, dataset_sha, source_sha)
    assert checkpoint.read_bytes() == b"advanced checkpoint must remain untouched"


def test_missing_code_reports_the_missing_input_instead_of_starting_training(tmp_path):
    inputs, _, dataset_sha, source_sha = make_inputs(tmp_path)
    (inputs / "kaggle_project.zip").unlink()
    with pytest.raises(RuntimeError, match="Project code is missing"):
        BOOTSTRAP.bootstrap_inputs(inputs, tmp_path / "work/project", tmp_path / "work/runs", dataset_sha, source_sha)


def test_conflicting_extracted_checkpoint_is_rejected_before_training(tmp_path):
    inputs, _, dataset_sha, source_sha = make_inputs(tmp_path)
    with zipfile.ZipFile(inputs / "sca_runs_minimal_v1.zip") as archive:
        archive.extractall(inputs / "different")
    (inputs / "different/none_seed0/last.pt").write_bytes(b"different checkpoint")
    with pytest.raises(RuntimeError, match="Different restore checkpoints"):
        BOOTSTRAP.bootstrap_inputs(inputs, tmp_path / "work/project", tmp_path / "work/runs", dataset_sha, source_sha)


def test_input_zip_cannot_write_outside_destination(tmp_path):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../escaped.txt", "must not be written")
    with pytest.raises(ValueError, match="Unsafe"):
        BOOTSTRAP.extract_checked(archive, tmp_path / "destination")
    assert not (tmp_path / "escaped.txt").exists()


def test_fresh_study_requires_explicit_bootstrap_opt_in(tmp_path):
    inputs, _, dataset_sha, source_sha = make_inputs(tmp_path)
    (inputs / "sca_runs_minimal_v1.zip").unlink()
    project, runs = tmp_path / "work/project", tmp_path / "work/runs"
    with pytest.raises(RuntimeError, match="Checkpoint Input is missing"):
        BOOTSTRAP.bootstrap_inputs(inputs, project, runs, dataset_sha, source_sha)
    dataset = BOOTSTRAP.bootstrap_inputs(inputs, project, runs, dataset_sha, source_sha,
                                        require_checkpoint=False)
    assert BOOTSTRAP.file_sha256(dataset) == dataset_sha
    assert not (runs / "none_seed0/last.pt").exists()
