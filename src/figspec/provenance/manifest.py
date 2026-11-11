"""Provenance manifests: what went in, what came out, in which environment."""

from __future__ import annotations

import json
import os
import platform
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .._version import __version__
from ..errors import ProvenanceError
from ..render.figure import RenderResult
from ..utils.hashing import sha256_file, sha256_json

__all__ = ["MANIFEST_SCHEMA", "Manifest", "create_manifest", "load_manifest"]

MANIFEST_SCHEMA = "figspec/provenance/v1"


def _relative(path: Path, base: Path) -> str:
    try:
        return Path(os.path.relpath(path.resolve(), base.resolve())).as_posix()
    except ValueError:  # pragma: no cover - different drives on Windows
        return path.resolve().as_posix()


def _timestamp() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        moment = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    else:
        moment = datetime.now(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_state(directory: Path) -> dict[str, Any] | None:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if commit.returncode != 0:
            return None
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return {
            "commit": commit.stdout.strip(),
            "dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
        }
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - git optional
        return None


def _environment() -> dict[str, str]:
    import matplotlib
    import numpy
    import yaml

    return {
        "figspec": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "matplotlib": matplotlib.__version__,
        "numpy": numpy.__version__,
        "pyyaml": yaml.__version__,
    }


@dataclass(frozen=True)
class Manifest:
    """A provenance record for one build."""

    data: Mapping[str, Any]
    path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.data)

    def to_json(self) -> str:
        return json.dumps(self.data, indent=2, ensure_ascii=False, sort_keys=False) + "\n"

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_json(), encoding="utf-8")
        return target

    @property
    def spec_hash(self) -> str:
        return str(self.data.get("spec", {}).get("hash", ""))

    @property
    def outputs(self) -> list[dict[str, Any]]:
        return list(self.data.get("outputs", []))

    @classmethod
    def load(cls, path: str | Path) -> Manifest:
        source = Path(path)
        if not source.exists():
            raise ProvenanceError("manifest not found", path=str(source))
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProvenanceError(f"cannot read manifest: {exc}", path=str(source)) from exc
        if not isinstance(payload, dict):
            raise ProvenanceError("manifest must contain a JSON object", path=str(source))
        schema = payload.get("schema")
        if schema != MANIFEST_SCHEMA:
            raise ProvenanceError(
                f"unsupported manifest schema {schema!r}",
                path=str(source),
                hint=f"this release writes and reads '{MANIFEST_SCHEMA}'",
            )
        return cls(data=payload, path=source)


def load_manifest(path: str | Path) -> Manifest:
    """Load a manifest from disk."""
    return Manifest.load(path)


def create_manifest(
    result: RenderResult,
    manifest_path: str | Path,
    *,
    lint_summary: Mapping[str, int] | None = None,
) -> Manifest:
    """Build and write the manifest describing ``result``."""
    target = Path(manifest_path)
    base = target.parent
    spec_path = result.spec.path
    spec_dir = spec_path.parent if spec_path is not None else Path.cwd()

    spec_info: dict[str, Any] = {
        "hash": sha256_json(dict(result.spec.raw)),
        "path": _relative(spec_path, base) if spec_path is not None else None,
        "file_sha256": sha256_file(spec_path) if spec_path is not None and spec_path.exists() else None,
    }

    inputs = []
    for fingerprint in result.prepared.inputs:
        original = Path(fingerprint["path"])
        inputs.append(
            {
                "path": _relative(original, spec_dir),
                "sha256": fingerprint["sha256"],
                "bytes": fingerprint["bytes"],
            }
        )

    outputs = [
        {
            "path": _relative(output.path, base),
            "format": output.format,
            "sha256": output.sha256,
            "bytes": output.bytes,
            "dpi": output.dpi,
        }
        for output in result.outputs
    ]

    payload: dict[str, Any] = {
        "schema": MANIFEST_SCHEMA,
        "generated_at": _timestamp(),
        "spec": spec_info,
        "environment": _environment(),
        "figure": {
            "width_in": round(result.style.width, 4),
            "height_in": round(result.style.height, 4),
            "dpi": result.style.dpi,
            "formats": list(result.style.formats),
            "journal": result.journal.name if result.journal else None,
            "palette": result.style.palette.name,
            "colors": list(result.series_colors),
        },
        "inputs": inputs,
        "outputs": outputs,
        "git": _git_state(spec_dir),
    }
    if lint_summary is not None:
        payload["lint"] = dict(lint_summary)

    manifest = Manifest(data=payload, path=target)
    manifest.write(target)
    return manifest
