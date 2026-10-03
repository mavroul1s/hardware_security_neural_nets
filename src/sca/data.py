"""Inspect ASCAD and load profiling and attack data through separate interfaces."""
import hashlib
from pathlib import Path

import h5py
import numpy as np
from .aes import identity_labels

OFFICIAL_SHA256 = "f56625977fb6db8075ab620b1f3ef49a2a349ae75511097505855376e9684f91"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inspect_dataset(path, target_byte=2, verify_attack=True):
    path = Path(path)
    report = {"path": str(path.resolve()), "bytes": path.stat().st_size,
              "sha256": sha256_file(path), "target_byte": target_byte, "groups": {}}
    with h5py.File(path, "r") as f:
        report["synthetic"] = bool(f.attrs.get("synthetic", False))
        for group in ("Profiling_traces", "Attack_traces"):
            g = f[group]
            x, y, m = g["traces"], g["labels"], g["metadata"]
            if x.ndim != 2 or x.shape[1] != 700 or y.shape != (len(x),) or len(m) != len(x):
                raise ValueError(f"Invalid ASCAD 700-sample schema in {group}")
            if not np.issubdtype(x.dtype, np.number) or not np.issubdtype(y.dtype, np.integer):
                raise ValueError("Traces must be numeric and labels must be integers")
            if not {"plaintext", "key"}.issubset(m.dtype.names or ()):
                raise ValueError("Missing plaintext/key metadata")
            for field in ("plaintext", "key"):
                dtype = m.dtype.fields[field][0]
                if dtype.shape != (16,) or dtype.base != np.dtype("uint8"):
                    raise ValueError(f"Expected {field}: uint8[16]")
            checked = group == "Profiling_traces" or verify_attack
            if checked:
                for start in range(0, len(x), 4096):
                    stop = min(start + 4096, len(x))
                    metadata = m[start:stop]
                    labels = y[start:stop]
                    if np.any((labels < 0) | (labels > 255)) or not np.array_equal(
                        labels, identity_labels(metadata["plaintext"], metadata["key"], target_byte)
                    ):
                        raise ValueError(f"Identity labels mismatch for byte {target_byte} in {group}")
                    if not np.isfinite(x[start:stop]).all():
                        raise ValueError("Non-finite traces")
            report["groups"][group] = {"traces_shape": list(x.shape), "traces_dtype": str(x.dtype),
                "labels_dtype": str(y.dtype), "metadata_dtype": str(m.dtype), "labels_verified": checked}
    report["official_checksum_match"] = report["sha256"] == OFFICIAL_SHA256
    return report


def make_splits(n_profiling, n_train, n_validation, seed):
    if n_train < 1 or n_validation < 1 or n_train + n_validation > n_profiling:
        raise ValueError("Invalid profiling split sizes")
    permutation = np.random.default_rng(seed).permutation(n_profiling)
    # Validation is constant across nested training budgets.
    val = np.sort(permutation[:n_validation])
    train = np.sort(permutation[n_validation:n_validation + n_train])
    return train, val


def split_identifier(train, validation):
    h = hashlib.sha256()
    for values in (train, validation):
        h.update(np.asarray([len(values)], dtype="<i8").tobytes())
        h.update(np.asarray(values, dtype="<i8").tobytes())
    return h.hexdigest()


def load_profiling(path, train_indices, val_indices):
    if np.intersect1d(train_indices, val_indices).size:
        raise ValueError("Training and validation overlap")
    with h5py.File(path, "r") as f:
        g = f["Profiling_traces"]
        return (g["traces"][train_indices].astype(np.float32), g["labels"][train_indices].astype(np.int64),
                g["traces"][val_indices].astype(np.float32), g["labels"][val_indices].astype(np.int64))


def load_attack(path, target_byte=2):
    with h5py.File(path, "r") as f:
        g = f["Attack_traces"]
        m = g["metadata"][:]
        keys = np.unique(m["key"][:, target_byte])
        if len(keys) != 1:
            raise ValueError("This evaluator requires a constant attack key byte")
        return g["traces"][:].astype(np.float32), m["plaintext"][:, target_byte], int(keys[0])


def load_validation_evaluation(path, indices, target_byte=2):
    """Use held-out profiling rows for diagnostics without opening the final attack set."""
    with h5py.File(path, "r") as f:
        g = f["Profiling_traces"]
        m = g["metadata"][indices]
        keys = np.unique(m["key"][:, target_byte])
        if len(keys) != 1:
            raise ValueError("This evaluator requires a constant validation key byte")
        return g["traces"][indices].astype(np.float32), m["plaintext"][:, target_byte], int(keys[0])


def fit_normalizer(training_traces, kind="global_scalar_training_only"):
    if kind == "feature_minmax_training_only":
        values = np.asarray(training_traces, dtype=np.float64)
        if values.ndim != 2 or not len(values) or not np.isfinite(values).all():
            raise ValueError("Expected finite nonempty 2D training traces")
        minimum = values.min(axis=0)
        scale = values.max(axis=0) - minimum
        scale[scale == 0] = 1
        return {"minimum": minimum.tolist(), "scale": scale.tolist(), "kind": kind}
    if kind != "global_scalar_training_only":
        raise ValueError("Unknown normalizer kind")
    mean = float(np.mean(training_traces, dtype=np.float64))
    std = float(np.std(training_traces, dtype=np.float64))
    if not np.isfinite([mean, std]).all() or std < 1e-8:
        raise ValueError("Cannot normalize non-finite or constant training data")
    return {"mean": mean, "std": std, "kind": "global_scalar_training_only"}


def normalize(traces, stats):
    if stats.get("kind") == "feature_minmax_training_only":
        values = np.asarray(traces, dtype=np.float64)
        minimum, scale = np.asarray(stats["minimum"]), np.asarray(stats["scale"])
        if (values.ndim != 2 or minimum.shape != (values.shape[1],) or scale.shape != minimum.shape
                or not np.isfinite(minimum).all() or not np.isfinite(scale).all() or np.any(scale <= 0)):
            raise ValueError("Invalid feature MinMax statistics or trace shape")
        # Training fit only. Validation/attack values may lie outside [0,1]; do not clip.
        return ((values - minimum) / scale).astype(np.float32)
    return ((traces - stats["mean"]) / stats["std"]).astype(np.float32)
