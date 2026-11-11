"""High level, notebook friendly API.

``figspec.render`` is the one-call entry point: it loads the spec, builds the
figure, lints it, writes every output format and records a provenance manifest.
The lower level pieces remain public for people who want to drive each step.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .errors import LintFailure
from .lint import LintReport, lint_result
from .provenance import Manifest, create_manifest
from .provenance.verify import VerificationResult, verify as _verify
from .render.figure import OutputFile, RenderResult, build, export
from .spec.loader import load_spec
from .spec.schema import Spec

__all__ = ["RenderOutcome", "lint", "render", "verify"]


@dataclass(frozen=True)
class RenderOutcome:
    """What :func:`render` produced."""

    result: RenderResult
    report: LintReport
    manifest: Manifest | None

    @property
    def outputs(self) -> list[OutputFile]:
        return self.result.outputs

    def close(self) -> None:
        self.result.close()


def _as_spec(source: str | Path | Spec) -> Spec:
    return source if isinstance(source, Spec) else load_spec(source)


def render(
    source: str | Path | Spec,
    outdir: str | Path = "out",
    *,
    journal: str | None = None,
    journal_file: str | Path | None = None,
    dpi: int | None = None,
    formats: Sequence[str] | None = None,
    stem: str | None = None,
    strict: bool = False,
    fail_on: str = "error",
    ignore: Sequence[str] = (),
    lint: bool = True,
    manifest: bool = True,
) -> RenderOutcome:
    """Build, lint, export and record one figure."""
    spec = _as_spec(source)
    result = build(spec, journal=journal, journal_file=journal_file, dpi=dpi, formats=formats)
    try:
        report = (
            lint_result(result, ignore=ignore)
            if lint
            else LintReport(findings=(), spec_path=str(spec.path) if spec.path else None)
        )
        if strict and report.failed(fail_on):
            counts = report.counts()
            raise LintFailure(
                f"lint failed: {counts['error']} error(s), {counts['warning']} warning(s)",
                path=str(spec.path) if spec.path else None,
                hint="fix the findings or relax --fail-on",
            )
        export(result, outdir, stem=stem, formats=formats)
        record: Manifest | None = None
        if manifest:
            name = stem or (spec.path.stem if spec.path else "figure")
            record = create_manifest(
                result,
                Path(outdir) / f"{name}.figspec.json",
                lint_summary=report.counts(),
            )
    except BaseException:
        result.close()
        raise
    return RenderOutcome(result=result, report=report, manifest=record)


def lint(
    source: str | Path | Spec,
    *,
    journal: str | None = None,
    journal_file: str | Path | None = None,
    ignore: Sequence[str] = (),
) -> LintReport:
    """Build a figure and return its lint report without writing anything."""
    spec = _as_spec(source)
    result = build(spec, journal=journal, journal_file=journal_file)
    try:
        return lint_result(result, ignore=ignore)
    finally:
        result.close()


def verify(manifest_path: str | Path) -> VerificationResult:
    """Verify one provenance manifest."""
    return _verify(manifest_path)
