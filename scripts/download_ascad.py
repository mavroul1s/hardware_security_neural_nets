"""Fetch only ASCAD.h5 from the official ZIP using verified HTTP byte ranges.

Aborts if ranges are unsupported; never falls back to a multi-gigabyte download.
"""
import argparse
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

URL = "https://www.data.gouv.fr/api/1/datasets/r/e7ab6f9e-79bf-431f-a5ed-faf0ebe9b08e"
SHA256 = "f56625977fb6db8075ab620b1f3ef49a2a349ae75511097505855376e9684f91"


class RangeReader(io.RawIOBase):
    def __init__(self, url):
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=45) as r:
            self.url = r.url
            self.size = int(r.headers["Content-Length"])
            self.etag = r.headers.get("ETag")
        self.position = 0
        self.transferred = 0

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        if self.position < 0:
            raise ValueError("Negative seek")
        return self.position

    def read(self, n=-1):
        stop = self.size if n < 0 else min(self.size, self.position + n)
        if stop <= self.position:
            return b""
        if stop - self.position > 128 * 1024**2:
            raise ValueError("Refusing an unexpectedly large range")
        headers = {"Range": f"bytes={self.position}-{stop - 1}", "Accept-Encoding": "identity"}
        if self.etag:
            headers["If-Match"] = self.etag
        request = urllib.request.Request(self.url, headers=headers)
        with urllib.request.urlopen(request, timeout=90) as r:
            expected = f"bytes {self.position}-{stop - 1}/{self.size}"
            if r.status != 206 or r.headers.get("Content-Range") != expected:
                raise RuntimeError("Server did not honor byte ranges; full archive NOT downloaded")
            block = r.read(stop - self.position + 1)
        if len(block) != stop - self.position:
            raise RuntimeError("Incomplete HTTP range")
        self.position = stop
        self.transferred += len(block)
        return block


def download(output):
    output = Path(output)
    if output.exists():
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        if digest != SHA256:
            raise ValueError("Existing file does not match the official checksum; refusing to overwrite")
        print("Existing ASCAD.h5 verified")
        return
    remote = RangeReader(URL)
    with zipfile.ZipFile(remote) as archive:
        matches = [i for i in archive.infolist() if re.search(r"(^|/)ASCAD_databases/ASCAD\.h5$", i.filename)]
        if len(matches) != 1:
            raise ValueError("Expected exactly one preprocessed ASCAD.h5 entry")
        entry = matches[0]
        if entry.file_size > 128 * 1024**2 or entry.compress_size > 128 * 1024**2:
            raise ValueError("Unexpectedly large preprocessed dataset; stopped before downloading")
        print(json.dumps({"member": entry.filename, "bytes": entry.file_size,
                          "compressed_bytes": entry.compress_size, "archive_bytes": remote.size}))
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".h5.part")
        if temporary.exists():
            raise FileExistsError(temporary)
        digest = hashlib.sha256()
        with archive.open(entry) as source, open(temporary, "xb") as destination:
            while block := source.read(1024 * 1024):
                digest.update(block)
                destination.write(block)
        if digest.hexdigest() != SHA256:
            raise ValueError("Official checksum mismatch; .part retained for diagnosis")
        temporary.replace(output)
    manifest = {"source_url": URL, "resolved_url": remote.url, "archive_etag": remote.etag,
        "archive_bytes": remote.size, "member": entry.filename, "file_bytes": entry.file_size,
        "downloaded_range_bytes": remote.transferred, "sha256": digest.hexdigest(),
        "expected_sha256": SHA256, "verified": True, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "version": "ASCAD fixed-key original synchronized, official 20180530 archive"}
    output.with_suffix(".provenance.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/ASCAD.h5")
    download(parser.parse_args().output)
