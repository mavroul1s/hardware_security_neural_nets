"""Collect compatible cached wheels and an isolated, byte-preserving source snapshot."""
import argparse
from email.parser import BytesParser
import hashlib
from importlib.metadata import distributions, version
import json
from pathlib import Path
import platform
import re
import shutil
import sys
import zipfile

from packaging.tags import parse_tag, sys_tags

EXPECTED_SOURCE = "84eff3cde04c0e9a1756a3d29c44ec82e115a1a08575132686a02520333e2b5c"


def canonical(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_hash(root):
    files = sorted([*root.glob("src/**/*.py"), *root.glob("scripts/*.py"),
                    *root.glob("configs/*.json"), root / "pyproject.toml"])
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def wheel_specification(path, targets, tag_priority):
    try:
        with zipfile.ZipFile(path) as archive:
            # Setuptools also ships vendored distributions with nested metadata.
            metadata_paths = [n for n in archive.namelist()
                              if n.count("/") == 1 and n.endswith(".dist-info/METADATA")]
            if len(metadata_paths) != 1:
                return None
            metadata_path = metadata_paths[0]
            metadata = BytesParser().parsebytes(archive.read(metadata_path))
            name, package_version = canonical(metadata["Name"]), metadata["Version"]
            if targets.get(name) != package_version:
                return None
            dist_info = metadata_path.rsplit("/", 1)[0]
            wheel = BytesParser().parsebytes(archive.read(dist_info + "/WHEEL"))
            compatible = [(tag_priority[tag], str(tag)) for value in wheel.get_all("Tag", [])
                          for tag in parse_tag(value) if tag in tag_priority]
            if not compatible:
                return None
            priority, tag = min(compatible)
            stem = dist_info.removesuffix(".dist-info")
            build = "-" + wheel["Build"] if wheel["Build"] else ""
            return {"name": name, "version": package_version, "tag": tag,
                    "filename": stem + build + "-" + tag + ".whl", "priority": priority}
    except (zipfile.BadZipFile, KeyError):
        return None


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    root, work, output = args.root.resolve(), args.work.resolve(), args.output.resolve()
    if not work.is_relative_to(root / "runs") or not output.is_relative_to(root / "outputs"):
        raise ValueError("Reproduction paths must stay inside the project runs/ and outputs/")
    if source_hash(root) != EXPECTED_SOURCE:
        raise ValueError("Pinned production source changed")
    wheelhouse = work / "wheelhouse"
    wheelhouse.mkdir(parents=True, exist_ok=True)
    tag_priority = {tag: index for index, tag in enumerate(sys_tags())}
    plan_path = output / "plan.json"
    if not args.finalize:
        if plan_path.exists():
            raise FileExistsError("Preparation already exists; use --finalize after filling missing wheels")
        targets = {canonical(item.metadata["Name"]): item.version for item in distributions()
                   if canonical(item.metadata["Name"]) not in {"pip", "hardware-sca"}}
        if len(targets) != 27:
            raise ValueError("Unexpected reference dependency set")
        selections = {}
        if args.cache is None:
            raise ValueError("An explicit read-only HTTP cache path is required")
        for body in args.cache.rglob("*.body"):
            item = wheel_specification(body, targets, tag_priority)
            if item is not None and (item["name"] not in selections or
                                     item["priority"] < selections[item["name"]][0]["priority"]):
                selections[item["name"]] = (item, body)
        cached = []
        for name, (item, body) in sorted(selections.items()):
            destination = wheelhouse / item["filename"]
            if destination.exists():
                raise FileExistsError(destination)
            shutil.copyfile(body, destination)
            cached.append({k: v for k, v in item.items() if k != "priority"} |
                          {"sha256": sha256(destination), "bytes": destination.stat().st_size,
                           "origin": "Local pip HTTP cache; original URL not reconstructed"})
            print("Copied cached wheel:", name, item["version"], item["tag"], flush=True)
        snapshot = work / "source"
        if snapshot.exists():
            raise FileExistsError(snapshot)
        source_paths = sorted(set([*root.glob("src/**/*.py"), *root.glob("scripts/*.py"),
            *root.glob("configs/*.json"), *root.glob("tests/*.py"), *root.glob("notebooks/*.py"),
            root / "notebooks/kaggle_baseline.ipynb", root / "pyproject.toml"]))
        snapshot_files = []
        for source in source_paths:
            relative = source.relative_to(root)
            destination = snapshot / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            snapshot_files.append({"path": relative.as_posix(), "sha256": sha256(destination)})
        assert source_hash(snapshot) == EXPECTED_SOURCE
        plan = {"scope": "Fresh CPU venv, fixed saved checkpoints and profiling validation; no real-data training",
            "python": platform.python_version(), "reference_executable": sys.executable,
            "base_executable": sys._base_executable, "reference_pip": version("pip"),
            "platform": platform.platform(), "targets": targets, "cached_wheels": cached,
            "missing_wheels": sorted(set(targets) - set(selections)),
            "snapshot_files": snapshot_files, "source_sha256": EXPECTED_SOURCE,
            "checkpoint_ce_absolute_tolerance": 1e-7, "saved_cpu_rank_curves_require_exact_match": True,
            "attack_dataset_payloads_allowed": False, "full_gpu_trainings_total": 3,
            "new_gpu_trainings": 0, "new_real_data_optimizer_updates": 0,
            "limitations": "Same Windows host and base interpreter; not an independent OS/device replication"}
        write_json(plan_path, plan)
        print("Missing exact wheels:", plan["missing_wheels"], flush=True)
        return
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    targets = plan["targets"]
    wheels = {}
    for path in sorted(wheelhouse.glob("*.whl")):
        item = wheel_specification(path, targets, tag_priority)
        if item is None or item["name"] in wheels:
            raise ValueError("Unexpected, incompatible or duplicate wheel: " + path.name)
        wheels[item["name"]] = {k: v for k, v in item.items() if k != "priority"} | {
            "filename": path.name, "sha256": sha256(path), "bytes": path.stat().st_size,
            "origin": next((v["origin"] for v in plan["cached_wheels"] if v["name"] == item["name"]),
                           "Exact wheel downloaded from PyPI after cache inspection")}
    if set(wheels) != set(targets):
        raise ValueError("Missing exact wheels: " + str(sorted(set(targets) - set(wheels))))
    assert source_hash(work / "source") == EXPECTED_SOURCE
    lock = root / "requirements-lock-cpu-reproduction.txt"
    if lock.exists():
        raise FileExistsError(lock)
    header = "# Windows AMD64 / CPython 3.12 / CPU-only. Install project snapshot separately.\n"
    lines = [f"{name}=={item['version']} --hash=sha256:{item['sha256']}" for name, item in sorted(wheels.items())]
    lock.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    write_json(output / "wheels.json", {"wheels": wheels, "lock_sha256": sha256(lock),
        "cache_bytes": sum(v["bytes"] for v in wheels.values() if v["origin"].startswith("Local")),
        "downloaded_bytes": sum(v["bytes"] for v in wheels.values() if not v["origin"].startswith("Local")),
        "filenames": "Cache filenames reconstructed from unchanged wheel METADATA/WHEEL tags; bytes not repackaged"})
    print("Finalized exact hashed CPU lock:", lock, flush=True)


if __name__ == "__main__":
    main()
