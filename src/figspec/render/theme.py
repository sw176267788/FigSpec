"""Resolving journal + spec + defaults into one concrete style.

Three layers decide what a figure looks like: the journal preset (hard limits),
the spec's ``style``/``figure`` blocks (author intent) and figspec's defaults.
This module flattens them into a single :class:`ResolvedStyle` so that the
renderer and the linter agree on every number.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ..errors import SpecError
from ..journals import JournalPreset
from ..palette import Palette, get_palette
from ..spec.schema import Spec

__all__ = ["DEFAULT_FORMATS", "ResolvedStyle", "infer_font_category", "resolve_style", "rc_params"]

DEFAULT_FORMATS = ("pdf", "svg", "png")
DEFAULT_PALETTE = "okabe-ito"

_LAYOUT_WIDTHS = {"single": 3.5, "1.5": 5.25, "double": 7.16, "custom": 7.0}
_SERIF_HINTS = ("times", "serif", "libertine", "georgia", "cambria", "garamond", "book")


def infer_font_category(family: Sequence[str]) -> str:
    """Guess whether a font list should drive the ``serif`` or ``sans-serif`` slot."""
    for name in family:
        lowered = name.lower()
        if any(hint in lowered for hint in _SERIF_HINTS):
            return "serif"
    return "sans-serif"


@dataclass(frozen=True)
class ResolvedStyle:
    """Every number the renderer needs, already reconciled."""

    width: float
    height: float
    font_family: tuple[str, ...]
    font_category: str
    base_size: float
    label_size: float
    tick_size: float
    legend_size: float
    title_size: float
    line_width: float
    marker_size: float
    axis_linewidth: float
    tick_length: float
    dpi: int
    formats: tuple[str, ...]
    palette: Palette
    background: str
    spines: tuple[str, ...]
    grid: bool
    tick_direction: str
    error_band_alpha: float
    min_font_size: float
    min_line_width: float
    journal: JournalPreset | None
    use_tex: bool = False

    @property
    def size(self) -> tuple[float, float]:
        return (self.width, self.height)


def _figure_size(spec: Spec, journal: JournalPreset | None) -> tuple[float, float]:
    figure = spec.figure
    if figure.size is not None:
        return figure.size

    if journal is not None:
        width = journal.width_for(figure.layout)
    else:
        width = None
    if width is None:
        if figure.layout == "custom":
            raise SpecError(
                "layout 'custom' requires an explicit figure size",
                path="figure.size",
                hint="add 'size: [width_in, height_in]' under figure",
            )
        width = _LAYOUT_WIDTHS.get(figure.layout, 3.5)

    if figure.height is not None:
        height = figure.height
    elif figure.aspect is not None:
        height = width * figure.aspect
    else:
        height = width * 0.62
    return (float(width), float(height))


def resolve_style(
    spec: Spec,
    journal: JournalPreset | None,
    *,
    dpi: int | None = None,
    formats: Sequence[str] | None = None,
) -> ResolvedStyle:
    """Merge defaults, journal constraints and spec overrides."""
    style = spec.style
    width, height = _figure_size(spec, journal)

    base_size = style.font_size or (journal.font_size if journal else 7.0)
    min_font_size = journal.min_font_size if journal else 5.0
    label_size = (journal.label_size if journal and journal.label_size else base_size + 0.5)
    tick_size = max(min_font_size, base_size - 0.5)
    legend_size = max(min_font_size, base_size - 0.5)
    title_size = base_size + 1.0

    line_width = journal.line_width if journal else 1.0
    marker_size = journal.marker_size if journal else 3.5
    axis_linewidth = style.axes_linewidth or (journal.line_width if journal else 0.8)
    tick_length = style.tick_length if style.tick_length is not None else 3.0

    palette_name = style.palette or (journal.preferred_palette if journal else DEFAULT_PALETTE)
    palette = get_palette(palette_name)

    family = style.font_family or (journal.font_family if journal else ("DejaVu Sans",))
    resolved_formats = tuple(formats) if formats else (spec.figure.formats or (journal.formats if journal else DEFAULT_FORMATS))

    return ResolvedStyle(
        width=width,
        height=height,
        font_family=tuple(family),
        font_category=infer_font_category(family),
        base_size=float(base_size),
        label_size=float(label_size),
        tick_size=float(tick_size),
        legend_size=float(legend_size),
        title_size=float(title_size),
        line_width=float(line_width),
        marker_size=float(marker_size),
        axis_linewidth=float(axis_linewidth),
        tick_length=float(tick_length),
        dpi=int(dpi or spec.figure.dpi or (journal.raster_dpi if journal else 300)),
        formats=resolved_formats,
        palette=palette,
        background=spec.figure.background or "white",
        spines=style.spines if style.spines is not None else ("left", "bottom"),
        grid=bool(style.grid) if style.grid is not None else False,
        tick_direction=style.tick_direction,
        error_band_alpha=style.error_band_alpha,
        min_font_size=float(min_font_size),
        min_line_width=float(journal.min_line_width if journal else 0.25),
        journal=journal,
        use_tex=style.use_tex,
    )


def rc_params(style: ResolvedStyle) -> Mapping[str, Any]:
    """matplotlib rcParams implementing ``style``."""
    from cycler import cycler

    family = [*style.font_family, "DejaVu Sans"]
    return {
        "figure.facecolor": style.background,
        "figure.edgecolor": style.background,
        "figure.autolayout": False,
        "figure.dpi": 100,
        "savefig.facecolor": style.background,
        "savefig.edgecolor": style.background,
        "savefig.transparent": False,
        "savefig.bbox": "standard",
        "savefig.pad_inches": 0.02,
        "font.family": style.font_category,
        f"font.{style.font_category}": family,
        "font.size": style.base_size,
        "axes.labelsize": style.label_size,
        "axes.titlesize": style.title_size,
        "axes.linewidth": style.axis_linewidth,
        "axes.facecolor": style.background,
        "axes.grid": style.grid,
        "axes.axisbelow": True,
        "axes.unicode_minus": True,
        "axes.prop_cycle": cycler(color=list(style.palette.colors)),
        "axes.spines.left": "left" in style.spines,
        "axes.spines.right": "right" in style.spines,
        "axes.spines.top": "top" in style.spines,
        "axes.spines.bottom": "bottom" in style.spines,
        "xtick.labelsize": style.tick_size,
        "ytick.labelsize": style.tick_size,
        "xtick.direction": style.tick_direction,
        "ytick.direction": style.tick_direction,
        "xtick.major.size": style.tick_length,
        "ytick.major.size": style.tick_length,
        "xtick.major.width": style.axis_linewidth,
        "ytick.major.width": style.axis_linewidth,
        "xtick.minor.size": style.tick_length * 0.6,
        "ytick.minor.size": style.tick_length * 0.6,
        "lines.linewidth": style.line_width,
        "lines.markersize": style.marker_size,
        "lines.markeredgewidth": 0.0,
        "legend.fontsize": style.legend_size,
        "legend.frameon": False,
        "legend.handlelength": 1.8,
        "legend.borderaxespad": 0.3,
        "text.usetex": style.use_tex,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.hashsalt": "figspec",
        "path.simplify": False,
        "agg.path.chunksize": 0,
        "image.cmap": "viridis",
        "image.interpolation": "nearest",
        "lines.antialiased": True,
        "patch.antialiased": True,
    }
