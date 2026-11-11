"""Findings and report formats (text, JSON, SARIF)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from .._version import __version__

__all__ = ["Finding", "LintReport", "SEVERITIES", "SEVERITY_ORDER"]

SEVERITIES = ("error", "warning", "info")
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}
_ANSI = {"error": "\x1b[31m", "warning": "\x1b[33m", "info": "\x1b[36m"}
_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_RESET = "\x1b[0m"


@dataclass(frozen=True)
class Finding:
    """One lint observation."""

    code: str
    severity: str
    message: str
    hint: str | None = None
    detail: Mapping[str, Any] = field(default_factory=dict)
    rule_title: str = ""

    def __post_init__(self) -> None:
        if self.severity not in SEVERITY_ORDER:
            raise ValueError(f"unknown severity '{self.severity}'")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }
        if self.hint:
            payload["hint"] = self.hint
        if self.detail:
            payload["detail"] = dict(self.detail)
        if self.rule_title:
            payload["title"] = self.rule_title
        return payload


@dataclass(frozen=True)
class LintReport:
    """The result of running every enabled rule over one figure."""

    findings: tuple[Finding, ...]
    spec_path: str | None = None

    def counts(self) -> dict[str, int]:
        counts = dict.fromkeys(SEVERITIES, 0)
        for finding in self.findings:
            counts[finding.severity] += 1
        return counts

    def sorted(self) -> tuple[Finding, ...]:
        return tuple(sorted(self.findings, key=lambda item: (SEVERITY_ORDER[item.severity], item.code)))

    def failed(self, fail_on: str = "error") -> bool:
        """Whether the report should fail a build given a ``--fail-on`` level."""
        if fail_on == "none":
            return False
        threshold = {"error": 0, "warning": 1}.get(fail_on)
        if threshold is None:
            raise ValueError(f"unknown fail-on level '{fail_on}'")
        return any(SEVERITY_ORDER[finding.severity] <= threshold for finding in self.findings)

    def to_dict(self) -> dict[str, Any]:
        counts = self.counts()
        return {
            "version": 1,
            "figspec": __version__,
            "spec": self.spec_path,
            "summary": counts,
            "findings": [finding.to_dict() for finding in self.sorted()],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_text(self, *, color: bool = False) -> str:
        counts = self.counts()
        header = (
            f"{self.spec_path or '<spec>'}: "
            f"{counts['error']} error(s), {counts['warning']} warning(s), {counts['info']} note(s)"
        )
        lines = [_BOLD + header + _RESET if color else header]
        for finding in self.sorted():
            label = finding.severity.upper()
            if color:
                label = f"{_ANSI[finding.severity]}{label:<7}{_RESET}"
            else:
                label = f"{label:<7}"
            title = f"{finding.code} {finding.message}"
            if color:
                title = f"{_BOLD}{title}{_RESET}"
            lines.append(f"  {label} {title}")
            if finding.hint:
                hint = f"hint: {finding.hint}"
                lines.append(f"          {_DIM}{hint}{_RESET}" if color else f"          {hint}")
        if not self.findings:
            lines.append("  no findings")
        return "\n".join(lines)

    def to_sarif(self) -> str:
        from .rules import RULE_REGISTRY

        rules = []
        for code in sorted(RULE_REGISTRY):
            meta = RULE_REGISTRY[code]
            rules.append(
                {
                    "id": meta.code,
                    "name": meta.title,
                    "shortDescription": {"text": meta.title},
                    "defaultConfiguration": {"level": _sarif_level(meta.severity)},
                    "help": {"text": meta.description},
                }
            )

        results = []
        for finding in self.sorted():
            result: dict[str, Any] = {
                "ruleId": finding.code,
                "level": _sarif_level(finding.severity),
                "message": {"text": finding.message},
            }
            if self.spec_path:
                result["locations"] = [
                    {"physicalLocation": {"artifactLocation": {"uri": self.spec_path}}}
                ]
            results.append(result)

        payload = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "figspec",
                            "version": __version__,
                            "informationUri": "https://github.com/figspec/figspec",
                            "rules": rules,
                        }
                    },
                    "results": results,
                }
            ],
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)


def _sarif_level(severity: str) -> str:
    return {"error": "error", "warning": "warning", "info": "note"}.get(severity, "note")
