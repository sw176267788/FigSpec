"""Content hashing used for provenance manifests and reproducibility checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

__all__ = ["file_fingerprint", "sha256_bytes", "sha256_file", "sha256_json"]

_CHUNK = 1024 * 1024


def sha256_bytes(data: bytes) -> str:
    """Return the hex sha256 digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    """Return the hex sha256 digest of a file, streaming it in chunks."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(payload: Any) -> str:
    """Hash a JSON-serialisable object using a canonical encoding.

    Keys are sorted and separators are compact so that the digest only depends
    on the value, never on dict insertion order or whitespace.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(canonical.encode("utf-8"))


def file_fingerprint(path: str | Path) -> dict[str, Any]:
    """Return a provenance-friendly fingerprint of a file."""
    resolved = Path(path)
    return {
        "path": resolved.as_posix(),
        "sha256": sha256_file(resolved),
        "bytes": resolved.stat().st_size,
    }
