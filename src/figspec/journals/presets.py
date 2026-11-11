"""Journal presets.

A preset bundles the numbers a journal actually enforces: column widths, font
sizes, minimum line widths and raster resolutions.  Presets are plain YAML files
under ``journals/data`` so that contributors can add one without touching Python
code, and users can point at their own file with ``--journal-file``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

from ..errors import ConfigError

__all__ = [
    "JournalPreset",
    "get_journal",
    "list_journals",
    "load_journal_file",
    "parse_journal_mapping",
]

_DATA_DIR = Path(__file__).parent / "data"


@dataclass(frozen=True)
class JournalPreset:
    """Constraints and defaults imposed by one journal."""

    name: str
    display_name: str
    publisher: str
    column_widths: Mapping[str, float]
    max_height: float | None
    font_family: tuple[str, ...]
    font_size: float
    min_font_size: float
    label_size: float | None
    line_width: float
    min_line_width: float
    marker_size: float
    raster_dpi: int
    lineart_dpi: int
    formats: tuple[str, ...]
    preferred_palette: str
    max_colors: int
    notes: str = ""
    source: str = ""

    def width_for(self, layout: str) -> float | None:
        """Column width in inches for a layout, or ``None`` if not defined."""
        if layout in self.column_widths:
            return float(self.column_widths[layout])
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "publisher": self.publisher,
            "column_widths": dict(self.column_widths),
            "max_height": self.max_height,
            "font_family": list(self.font_family),
            "font_size": self.font_size,
            "min_font_size": self.min_font_size,
            "label_size": self.label_size,
            "line_width": self.line_width,
            "min_line_width": self.min_line_width,
            "marker_size": self.marker_size,
            "raster_dpi": self.raster_dpi,
            "lineart_dpi": self.lineart_dpi,
            "formats": list(self.formats),
            "preferred_palette": self.preferred_palette,
            "max_colors": self.max_colors,
            "notes": self.notes,
            "source": self.source,
        }


def _require(mapping: Mapping[str, Any], key: str, *, where: str) -> Any:
    if key not in mapping:
        raise ConfigError(f"missing required key '{key}'", path=where)
    return mapping[key]


def _positive(value: Any, where: str, key: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(f"'{key}' must be a positive number, got {value!r}", path=where)
    return float(value)


def parse_journal_mapping(data: Mapping[str, Any], *, where: str) -> JournalPreset:
    """Validate a journal preset mapping (from YAML or a dict)."""
    if not isinstance(data, Mapping):
        raise ConfigError("journal preset must be a mapping", path=where)

    for key in ("name", "display_name", "column_widths", "font"):
        if key not in data:
            raise ConfigError(f"missing required key '{key}'", path=where)

    widths_raw = data["column_widths"]
    if not isinstance(widths_raw, Mapping):
        raise ConfigError("'column_widths' must be a mapping of layout -> inches", path=where)
    widths = {
        str(layout): _positive(value, where, f"column_widths.{layout}")
        for layout, value in widths_raw.items()
    }
    for required in ("single", "double"):
        if required not in widths:
            raise ConfigError(f"'column_widths' must define '{required}'", path=where)

    font = data["font"]
    if not isinstance(font, Mapping):
        raise ConfigError("'font' must be a mapping", path=where)

    family = font.get("family", ["DejaVu Sans"])
    if isinstance(family, str):
        family = [family]
    if not isinstance(family, (list, tuple)) or not family:
        raise ConfigError("'font.family' must be a string or a non-empty list", path=where)

    line = data.get("line", {}) or {}
    dpi = data.get("dpi", {}) or {}
    max_height = data.get("max_height")

    return JournalPreset(
        name=str(_require(data, "name", where=where)),
        display_name=str(_require(data, "display_name", where=where)),
        publisher=str(data.get("publisher", "")),
        column_widths=widths,
        max_height=_positive(max_height, where, "max_height") if max_height is not None else None,
        font_family=tuple(str(item) for item in family),
        font_size=_positive(font.get("size", 7), where, "font.size"),
        min_font_size=_positive(font.get("min_size", 5), where, "font.min_size"),
        label_size=(
            _positive(font["label_size"], where, "font.label_size")
            if font.get("label_size") is not None
            else None
        ),
        line_width=_positive(line.get("width", 0.75), where, "line.width"),
        min_line_width=_positive(line.get("min_width", 0.25), where, "line.min_width"),
        marker_size=_positive(line.get("marker_size", 3), where, "line.marker_size"),
        raster_dpi=int(dpi.get("raster", 300)),
        lineart_dpi=int(dpi.get("lineart", 600)),
        formats=tuple(str(item) for item in data.get("formats", ["pdf", "svg", "png"])),
        preferred_palette=str(data.get("preferred_palette", "okabe-ito")),
        max_colors=int(data.get("max_colors", 8)),
        notes=str(data.get("notes", "")),
        source=str(data.get("source", "")),
    )


@lru_cache(maxsize=1)
def _builtin() -> dict[str, JournalPreset]:
    presets: dict[str, JournalPreset] = {}
    if not _DATA_DIR.exists():  # pragma: no cover - defensive
        return presets
    for path in sorted(_DATA_DIR.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        preset = parse_journal_mapping(data, where=str(path))
        if preset.name in presets:
            raise ConfigError(
                f"duplicate journal preset '{preset.name}'",
                path=str(path),
            )
        presets[preset.name] = preset
    return presets


def list_journals() -> tuple[str, ...]:
    """Names of all bundled journal presets."""
    return tuple(sorted(_builtin()))


def get_journal(name: str) -> JournalPreset:
    """Look up a bundled preset by name."""
    presets = _builtin()
    try:
        return presets[name.strip().lower()]
    except KeyError:
        raise ConfigError(
            f"unknown journal preset '{name}'",
            hint=f"available presets: {', '.join(list_journals())}",
        ) from None


def load_journal_file(path: str | Path) -> JournalPreset:
    """Load a custom preset from a YAML file."""
    resolved = Path(path)
    if not resolved.exists():
        raise ConfigError("journal preset file not found", path=str(resolved))
    try:
        with resolved.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML: {exc}", path=str(resolved)) from exc
    return parse_journal_mapping(data, where=str(resolved))
