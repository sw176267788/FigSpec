"""Verifying a manifest: has anything drifted since the figure was built?"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .._version import __version__
from ..errors import ProvenanceError
from ..utils.hashing import sha256_file
from .manifest import MANIFEST_SCHEMA, Manifest

__all__ = ["Check", "VerificationResult", "verify"]

_OK = "ok"
_WARNING = "warning"
_FAILED = "failed"
_RANK = {_OK: 0, _WARNING: 1, _FAILED: 2}


@dataclass(frozen=True)
class Check:
    """One verification step."""

    name: str
    status: str
    message: str


@dataclass(frozen=True)
class VerificationResult:
    """The outcome of verifying one manifest."""

    manifest_path: Path
    checks: tuple[Check, ...]

    @property
    def ok(self) -> bool:
        return all(check.status != _FAILED for check in self.checks)

    @property
    def worst(self) -> str:
        return max(self.checks, key=lambda check: _RANK[check.status]).status if self.checks else _OK

    def to_text(self, *, color: bool = False) -> str:
        markers = {_OK: "OK  ", _WARNING: "WARN", _FAILED: "FAIL"}
        colors = {_OK: "\x1b[32m", _WARNING: "\x1b[33m", _FAILED: "\x1b[31m"}
        lines = [f"verifying {self.manifest_path}"]
        for check in self.checks:
            prefix = f"{colors[check.status]}{markers[check.status]}\x1b[0m" if color else markers[check.status]
            lines.append(f"  {prefix} {check.name}: {check.message}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": str(self.manifest_path),
            "ok": self.ok,
            "worst": self.worst,
            "checks": [
                {"name": check.name, "status": check.status, "message": check.message}
                for check in self.checks
            ],
        }


def _check_hash(name: str, path: Path, expected: str, *, missing_status: str = _FAILED) -> Check:
    if not path.exists():
        return Check(name=name, status=missing_status, message=f"missing file {path}")
    actual = sha256_file(path)
    if actual == expected:
        return Check(name=name, status=_OK, message=f"{path.name} matches")
    return Check(
        name=name,
        status=_FAILED,
        message=f"{path.name} changed (expected {expected[:12]}…, found {actual[:12]}…)",
    )


def verify(manifest_path: str | Path) -> VerificationResult:
    """Check spec, inputs, outputs and environment against a manifest."""
    manifest = Manifest.load(manifest_path)
    source = Path(manifest_path)
    base = source.parent
    checks: list[Check] = []

    checks.append(Check(name="schema", status=_OK, message=MANIFEST_SCHEMA))

    spec_info = manifest.data.get("spec", {})
    spec_reference = spec_info.get("path")
    spec_dir = base
    if spec_reference:
        spec_path = (base / spec_reference).resolve()
        spec_dir = spec_path.parent
        expected_file = spec_info.get("file_sha256")
        if expected_file:
            checks.append(_check_hash("spec", spec_path, expected_file))
        else:
            checks.append(
                Check(
                    name="spec",
                    status=_WARNING,
                    message="manifest does not record a spec file hash",
                )
            )
    else:
        checks.append(Check(name="spec", status=_WARNING, message="manifest has no spec path"))

    inputs = manifest.data.get("inputs", [])
    if not inputs:
        checks.append(Check(name="inputs", status=_OK, message="no external data files"))
    for entry in inputs:
        path = Path(entry["path"])
        resolved = path if path.is_absolute() else spec_dir / path
        checks.append(_check_hash(f"input {path.name}", resolved, entry["sha256"]))

    outputs = manifest.data.get("outputs", [])
    if not outputs:
        checks.append(Check(name="outputs", status=_WARNING, message="manifest lists no outputs"))
    for entry in outputs:
        path = Path(entry["path"])
        resolved = path if path.is_absolute() else base / path
        checks.append(_check_hash(f"output {path.name}", resolved, entry["sha256"]))

    recorded_env = manifest.data.get("environment", {})
    drift = [
        f"{key} {recorded_env[key]} -> {current}"
        for key, current in (
            ("figspec", __version__),
            ("matplotlib", _current("matplotlib")),
            ("numpy", _current("numpy")),
        )
        if recorded_env.get(key) and recorded_env.get(key) != current
    ]
    if drift:
        checks.append(
            Check(
                name="environment",
                status=_WARNING,
                message="; ".join(drift) + " (rebuild to refresh the record)",
            )
        )
    else:
        checks.append(Check(name="environment", status=_OK, message="tool versions match"))

    return VerificationResult(manifest_path=source, checks=tuple(checks))


def _current(package: str) -> str:  # pragma: no cover - trivial
    module = __import__(package)
    return str(module.__version__)


def verify_or_raise(manifest_path: str | Path) -> VerificationResult:
    """Like :func:`verify`, but raise :class:`ProvenanceError` on drift."""
    result = verify(manifest_path)
    if not result.ok:
        failures = [check for check in result.checks if check.status == _FAILED]
        summary = "; ".join(f"{check.name}: {check.message}" for check in failures[:3])
        raise ProvenanceError(
            f"manifest drift detected ({len(failures)} failing check(s)): {summary}",
            path=str(result.manifest_path),
            hint="rebuild the figure or restore the original inputs",
        )
    return result
