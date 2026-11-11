"""Exception hierarchy for figspec.

Every error carries a human readable message, an optional ``path`` pointing at
the offending location inside a spec (``series[0].y``) and an optional ``hint``
that tells the user how to fix the problem.  The CLI prints ``str(err)`` and
exits with ``err.exit_code``.
"""

from __future__ import annotations

__all__ = [
    "ConfigError",
    "DataError",
    "FigspecError",
    "LintFailure",
    "ProvenanceError",
    "RenderError",
    "SpecError",
]


class FigspecError(Exception):
    """Base class for all errors raised by figspec."""

    exit_code: int = 1

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        path: str | None = None,
    ) -> None:
        self.message = message
        self.hint = hint
        self.path = path
        super().__init__(self.render())

    def render(self) -> str:
        prefix = f"{self.path}: " if self.path else ""
        text = f"{prefix}{self.message}"
        if self.hint:
            text = f"{text}\n  hint: {self.hint}"
        return text

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.render()


class SpecError(FigspecError):
    """The figure specification is malformed or internally inconsistent."""

    exit_code = 2


class ConfigError(FigspecError):
    """A user configuration file (journal preset, palette, config) is invalid."""

    exit_code = 2


class DataError(FigspecError):
    """A data source is missing, unreadable or does not contain required columns."""

    exit_code = 2


class RenderError(FigspecError):
    """The figure could not be rendered or exported."""

    exit_code = 3


class LintFailure(FigspecError):
    """Strict mode aborted the build because lint reported findings."""

    exit_code = 4


class ProvenanceError(FigspecError):
    """A provenance manifest is missing, malformed or reports drift."""

    exit_code = 5
