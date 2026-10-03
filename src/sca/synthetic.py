"""Clearly marked fixtures for code checks, not physical measurement evidence."""
from pathlib import Path
import h5py
import numpy as np
from .aes import identity_labels


def create_fixture(path, n_profiling=512, n_attack=128, seed=123):
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    metadata_dtype = np.dtype([("plaintext", "u1", (16,)), ("key", "u1", (16,)),
                              ("masks", "u1", (18,))])
    with h5py.File(path, "w") as f:
        f.attrs["synthetic"] = True
        f.attrs["description"] = "Unmasked artificial identity leakage; code validation only"
        for group, count in (("Profiling_traces", n_profiling), ("Attack_traces", n_attack)):
            m = np.zeros(count, dtype=metadata_dtype)
            m["plaintext"] = rng.integers(0, 256, (count, 16), dtype=np.uint8)
            m["key"][:] = np.arange(16, dtype=np.uint8) + 32
            y = identity_labels(m["plaintext"], m["key"])
            x = rng.normal(0, 1, (count, 700)).astype(np.float32)
            x[:, 340:348] += np.unpackbits(y[:, None], axis=1).astype(np.float32) * 3
            g = f.create_group(group)
            g.create_dataset("traces", data=x)
            g.create_dataset("labels", data=y)
            g.create_dataset("metadata", data=m)
