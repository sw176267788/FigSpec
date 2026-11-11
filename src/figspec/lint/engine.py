"""Running rules over a built figure."""

from __future__ import annotations

from dataclasses import replace
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from ..render.figure import RenderResult, build
from ..spec.loader import load_spec
from ..spec.schema import Spec
from .context import make_context
from .report import Finding, LintReport
from .rules import RULE_REGISTRY

__all__ = ["lint_result", "lint_spec"]


def _matches(code: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch(code, pattern) for pattern in patterns)


def lint_result(
    result: RenderResult,
    *,
    ignore: Sequence[str] = (),
    severity_overrides: Mapping[str, str] | None = None,
) -> LintReport:
    """Run every registered rule over an already built figure."""
    context = make_context(result)
    findings: list[Finding] = []

    for code in sorted(RULE_REGISTRY):
        if _matches(code, ignore):
            continue
        meta = RULE_REGISTRY[code]
        try:
            produced = list(meta.func(context))
        except Exception as exc:  # pragma: no cover - defensive: a rule bug must not kill the build
            produced = [
                Finding(
                    code="LINT999",
                    severity="warning",
                    message=f"lint rule {code} crashed: {exc!r}",
                    rule_title="Internal lint error",
                )
            ]
        for finding in produced:
            if severity_overrides and finding.code in severity_overrides:
                finding = replace(finding, severity=severity_overrides[finding.code])
            findings.append(finding)

    return LintReport(
        findings=tuple(findings),
        spec_path=str(result.spec.path) if result.spec.path is not None else None,
    )


def lint_spec(
    spec: Spec | str | Path,
    *,
    journal: str | None = None,
    journal_file: str | Path | None = None,
    ignore: Sequence[str] = (),
    severity_overrides: Mapping[str, str] | None = None,
) -> LintReport:
    """Build a spec (or spec file) and lint the result."""
    resolved = spec if isinstance(spec, Spec) else load_spec(spec)
    result = build(resolved, journal=journal, journal_file=journal_file)
    try:
        return lint_result(result, ignore=ignore, severity_overrides=severity_overrides)
    finally:
        result.close()
