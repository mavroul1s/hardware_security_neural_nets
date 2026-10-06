"""Acquire only the official extracted ASCAD variable-key file, with checksum verification."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.data.gouv.fr/api/1/datasets/r/b4ace767-c2a4-4db4-8e01-4527b5b91f00"
EXPECTED = "d834da6ca5a288c4ba5add8e336845270a055d6eaf854dcf2f325a2eb6d7de06"
SOURCE = "https://github.com/ANSSI-FR/ASCAD/blob/master/ATMEGA_AES_v1/ATM_AES_v1_variable_key/Readme.md"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    target = ROOT / "data/ASCAD_variable.h5"
    if target.exists():
        if digest(target) != EXPECTED:
            raise ValueError("Existing variable-key file does not match the official checksum")
        print("Already verified:", target, flush=True)
        return
    part = target.with_suffix(".h5.part")
    if part.exists():
        raise FileExistsError("Incomplete download exists; inspect it before retrying")
    request = urllib.request.Request(URL, headers={"User-Agent": "ASCAD-research-replication/1.0"})
    started, last, count = time.perf_counter(), time.perf_counter(), 0
    with urllib.request.urlopen(request, timeout=60) as response:
        final_url = response.url
        expected_bytes = response.headers.get("Content-Length")
        if expected_bytes and int(expected_bytes) > 600 * 1024 * 1024:
            raise ValueError("Refusing an unexpectedly large resource")
        with part.open("xb") as output:
            while block := response.read(1024 * 1024):
                count += len(block)
                if count > 600 * 1024 * 1024:
                    raise ValueError("Resource exceeds extracted-file size limit")
                output.write(block)
                if time.perf_counter() - last >= 10:
                    print(f"Downloaded {count / 1024**2:.1f} MiB", flush=True)
                    last = time.perf_counter()
    if expected_bytes and count != int(expected_bytes):
        raise ValueError("Incomplete HTTP response")
    actual = digest(part)
    if actual != EXPECTED:
        raise ValueError(f"Official checksum mismatch: {actual}")
    part.rename(target)
    provenance = {"source": SOURCE, "requested_url": URL, "resolved_url": final_url,
        "official_sha256": EXPECTED, "actual_sha256": actual, "bytes": count,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "download_seconds": time.perf_counter() - started,
        "variant": "original extracted variable-key campaign; no added desynchronization",
        "original_fixed_key_file_replaced": False}
    target.with_suffix(".provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print("Verified official dataset:", target, count, actual, flush=True)


if __name__ == "__main__":
    main()
