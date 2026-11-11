"""Building and exporting figures from a :class:`~figspec.spec.Spec`."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import FormatStrFormatter, FuncFormatter, ScalarFormatter

from ..data.series import PreparedFigure, prepare_figure
from ..errors import RenderError, SpecError
from ..journals import JournalPreset, get_journal, load_journal_file
from ..spec.schema import AxisSpec, LegendSpec, PanelSpec, Spec
from ..utils.hashing import sha256_file
from .plots import PanelState, draw_series
from .theme import ResolvedStyle, rc_params, resolve_style

__all__ = ["OutputFile", "RenderResult", "build", "export", "render_spec"]

RASTER_FORMATS = frozenset({"png", "jpg", "tif"})


@dataclass(frozen=True)
class OutputFile:
    """One file written by :func:`export`."""

    path: Path
    format: str
    sha256: str
    bytes: int
    dpi: int | None


@dataclass
class RenderResult:
    """A built figure plus everything the linter and manifest need."""

    spec: Spec
    prepared: PreparedFigure
    style: ResolvedStyle
    figure: Figure
    journal: JournalPreset | None
    rcparams: dict[str, Any] = field(default_factory=dict)
    outputs: list[OutputFile] = field(default_factory=list)
    series_colors: tuple[str, ...] = ()
    thin_colors: tuple[str, ...] = ()

    def close(self) -> None:
        """Release the matplotlib figure."""
        from matplotlib import pyplot as plt

        plt.close(self.figure)


def resolve_journal(
    spec: Spec,
    journal: str | None = None,
    journal_file: str | Path | None = None,
) -> JournalPreset | None:
    """Pick the preset: explicit argument > custom file > spec > none."""
    if journal and journal_file:
        raise SpecError("pass either a journal name or a journal file, not both")
    if journal_file is not None:
        return load_journal_file(journal_file)
    if journal:
        return get_journal(journal)
    if spec.figure.journal:
        return get_journal(spec.figure.journal)
    return None


def _assign_cells(spec: Spec, rows: int, cols: int) -> list[tuple[int, int]]:
    used: set[tuple[int, int]] = set()
    cells: list[tuple[int, int] | None] = []
    for panel in spec.panels:
        if panel.cell is not None:
            row, column = panel.cell
            if row >= rows or column >= cols:
                raise SpecError(
                    f"cell {list(panel.cell)} is outside the {rows}x{cols} grid",
                    path="figure.grid",
                )
            if (row, column) in used:
                raise SpecError(f"cell {list(panel.cell)} is used twice", path="figure.grid")
            used.add((row, column))
            cells.append((row, column))
        else:
            cells.append(None)

    free = [(row, column) for row in range(rows) for column in range(cols) if (row, column) not in used]
    free_iter = iter(free)
    assigned: list[tuple[int, int]] = []
    for cell in cells:
        if cell is not None:
            assigned.append(cell)
            continue
        try:
            assigned.append(next(free_iter))
        except StopIteration:
            raise SpecError(
                f"{len(spec.panels)} panels do not fit in a {rows}x{cols} grid",
                path="figure.grid",
                hint="increase 'figure.grid' or remove explicit 'cell' entries",
            ) from None
    return assigned


def _grid_shape(spec: Spec) -> tuple[int, int]:
    if spec.figure.grid is not None:
        return spec.figure.grid
    count = len(spec.panels)
    if count == 1:
        return (1, 1)
    columns = math.ceil(math.sqrt(count))
    rows = math.ceil(count / columns)
    explicit = [panel.cell for panel in spec.panels if panel.cell is not None]
    if explicit:
        rows = max(rows, max(cell[0] for cell in explicit) + 1)
        columns = max(columns, max(cell[1] for cell in explicit) + 1)
    return (rows, columns)


def _tick_formatter(axis: AxisSpec) -> Any:
    spec = axis.tick_format
    if not spec:
        return None
    if spec in ("sci", "scientific"):
        formatter = ScalarFormatter(useMathText=True)
        formatter.set_powerlimits((0, 0))
        return formatter
    if spec in ("thousands", "comma"):
        return FuncFormatter(lambda value, _pos: f"{value:,.0f}")
    if "%" in spec:
        return FormatStrFormatter(spec)
    return None


def _configure_axes(
    ax: Axes,
    panel: PanelSpec,
    style: ResolvedStyle,
    *,
    is_bottom: bool,
    is_left: bool,
    share_x: bool,
    share_y: bool,
) -> None:
    x_axis = panel.axes.get("x", AxisSpec())
    y_axis = panel.axes.get("y", AxisSpec())

    if x_axis.hide and y_axis.hide:
        ax.set_axis_off()
        return

    if x_axis.hide:
        ax.xaxis.set_visible(False)
    else:
        ax.set_xscale(x_axis.scale)
        if x_axis.limits is not None:
            ax.set_xlim(*x_axis.limits)
        if x_axis.invert:
            ax.invert_xaxis()
        if x_axis.ticks is not None:
            ax.set_xticks(list(x_axis.ticks))
        formatter = _tick_formatter(x_axis)
        if formatter is not None:
            ax.xaxis.set_major_formatter(formatter)
            ax.xaxis._figspec_explicit_format = True  # type: ignore[attr-defined]
        if x_axis.minor_ticks:
            ax.minorticks_on()
        if x_axis.label is not None:
            ax.set_xlabel(x_axis.label, fontsize=x_axis.label_size or style.label_size)

    if y_axis.hide:
        ax.yaxis.set_visible(False)
    else:
        ax.set_yscale(y_axis.scale)
        if y_axis.limits is not None:
            ax.set_ylim(*y_axis.limits)
        if y_axis.invert:
            ax.invert_yaxis()
        if y_axis.ticks is not None:
            ax.set_yticks(list(y_axis.ticks))
        formatter = _tick_formatter(y_axis)
        if formatter is not None:
            ax.yaxis.set_major_formatter(formatter)
            ax.yaxis._figspec_explicit_format = True  # type: ignore[attr-defined]
        if y_axis.minor_ticks:
            ax.minorticks_on()
        if y_axis.label is not None:
            ax.set_ylabel(y_axis.label, fontsize=y_axis.label_size or style.label_size)

    grid_x = x_axis.grid if x_axis.grid is not None else style.grid
    grid_y = y_axis.grid if y_axis.grid is not None else style.grid
    grid_style = {"color": "0.82", "linewidth": 0.5, "linestyle": (0, (1, 2))}
    if grid_x:
        ax.grid(True, axis="x", **grid_style)
    else:
        ax.grid(False, axis="x")
    if grid_y:
        ax.grid(True, axis="y", **grid_style)
    else:
        ax.grid(False, axis="y")

    ax.tick_params(
        axis="both",
        which="major",
        labelsize=style.tick_size,
        width=style.axis_linewidth,
        length=style.tick_length,
        direction=style.tick_direction,
    )
    ax.tick_params(axis="both", which="minor", width=style.axis_linewidth * 0.8)

    if share_x and not is_bottom:
        ax.tick_params(labelbottom=False)
        ax.set_xlabel("")
    if share_y and not is_left:
        ax.tick_params(labelleft=False)
        ax.set_ylabel("")


def _add_legend(
    ax: Axes,
    panel: PanelSpec,
    state: PanelState,
    style: ResolvedStyle,
    default: LegendSpec,
) -> None:
    legend_spec = panel.legend or default
    if not legend_spec.show or not state.handles:
        return

    seen: set[str] = set()
    handles: list[Any] = []
    labels: list[str] = []
    for handle, label in zip(state.handles, state.labels, strict=False):
        if label in seen or label == "_nolegend_":
            continue
        seen.add(label)
        handles.append(handle)
        labels.append(label)
    if not handles:
        return

    kwargs: dict[str, Any] = {
        "loc": legend_spec.location,
        "frameon": legend_spec.frame,
        "fontsize": legend_spec.font_size or style.legend_size,
        "ncol": legend_spec.columns,
        "handlelength": 1.8,
        "borderaxespad": 0.3,
    }
    if legend_spec.title:
        kwargs["title"] = legend_spec.title
    location = legend_spec.location
    if location == "outside right":
        kwargs.update(loc="center left", bbox_to_anchor=(1.01, 0.5), borderaxespad=0.0)
    elif location == "outside bottom":
        kwargs.update(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.18),
            borderaxespad=0.0,
            ncol=max(legend_spec.columns, len(handles)),
        )
    ax.legend(handles, labels, **kwargs)


def _add_annotations(ax: Axes, panel: PanelSpec, style: ResolvedStyle) -> None:
    for annotation in panel.annotations:
        text_kwargs: dict[str, Any] = {
            "fontsize": annotation.font_size or style.tick_size,
            "color": annotation.color or "#222222",
            "ha": annotation.ha,
            "va": annotation.va,
            "rotation": annotation.rotation,
        }
        if annotation.xy_axes is not None:
            ax.text(
                annotation.xy_axes[0],
                annotation.xy_axes[1],
                annotation.text,
                transform=ax.transAxes,
                **text_kwargs,
            )
        elif annotation.xy is not None:
            kwargs = dict(text_kwargs)
            if annotation.arrow:
                kwargs["arrowprops"] = {
                    "arrowstyle": "-|>",
                    "color": "#333333",
                    "linewidth": 0.6,
                    "shrinkA": 0,
                    "shrinkB": 2,
                }
            xytext = annotation.xytext or annotation.xy
            ax.annotate(annotation.text, xy=annotation.xy, xytext=xytext, **kwargs)
        else:
            ax.text(0.02, 0.98, annotation.text, transform=ax.transAxes, va="top", **text_kwargs)


def _draw(
    spec: Spec, prepared: PreparedFigure, style: ResolvedStyle
) -> tuple[Figure, tuple[str, ...], tuple[str, ...]]:
    from matplotlib.figure import Figure

    rows, columns = _grid_shape(spec)
    cells = _assign_cells(spec, rows, columns)

    row_columns: dict[int, list[int]] = {}
    column_rows: dict[int, list[int]] = {}
    for row, column in cells:
        row_columns.setdefault(row, []).append(column)
        column_rows.setdefault(column, []).append(row)

    margins = spec.figure.margins
    figure = Figure(figsize=style.size, layout=None if margins else "constrained")
    if margins is None:
        engine = figure.get_layout_engine()
        if engine is not None:
            engine.set(w_pad=spec.figure.pad, h_pad=spec.figure.pad)

    grid = figure.add_gridspec(rows, columns)
    axes: list[Axes] = []
    reference: dict[str, Axes] = {}
    used_colors: list[str] = []
    thin_colors: list[str] = []

    for index, panel_spec in enumerate(spec.panels):
        row, column = cells[index]
        share_x = bool(panel_spec.share_x) and "x" in reference
        share_y = bool(panel_spec.share_y) and "y" in reference
        ax = figure.add_subplot(
            grid[row, column],
            sharex=reference.get("x") if share_x else None,
            sharey=reference.get("y") if share_y else None,
        )
        if panel_spec.share_x:
            reference.setdefault("x", ax)
        if panel_spec.share_y:
            reference.setdefault("y", ax)
        axes.append(ax)

    if margins:
        figure.subplots_adjust(**dict(margins))

    for index, (panel_spec, panel_data) in enumerate(zip(spec.panels, prepared.panels, strict=True)):
        row, column = cells[index]
        ax = axes[index]
        is_bottom = row == max(column_rows[column])
        is_left = column == min(row_columns[row])
        _configure_axes(
            ax,
            panel_spec,
            style,
            is_bottom=is_bottom,
            is_left=is_left,
            share_x=bool(panel_spec.share_x) and not is_bottom,
            share_y=bool(panel_spec.share_y) and not is_left,
        )

        state = PanelState(ax=ax, style=style)
        for series_spec, series_data in zip(panel_spec.series, panel_data.series, strict=True):
            draw_series(state, series_data, series_spec)
        used_colors.extend(state.series_colors)
        thin_colors.extend(state.thin_colors)

        _add_legend(ax, panel_spec, state, style, spec.style.legend)
        _add_annotations(ax, panel_spec, style)

        if panel_spec.title:
            ax.set_title(
                panel_spec.title,
                loc="left",
                fontsize=style.title_size,
                fontweight="bold",
                pad=4,
            )

    _finalise_log_axes(figure)
    return figure, tuple(dict.fromkeys(used_colors)), tuple(dict.fromkeys(thin_colors))


def _finalise_log_axes(figure: Figure) -> None:
    """Use plain decimal labels on narrow log axes.

    ``3.2 x 10^0`` is noise when a log axis spans less than two decades; the
    values themselves are already ordinary numbers.
    """
    from matplotlib.ticker import FuncFormatter, NullFormatter

    def plain(value: float, _position: float) -> str:
        return f"{value:g}"

    for ax in figure.axes:
        for axis in (ax.xaxis, ax.yaxis):
            if axis.get_scale() != "log":
                continue
            if getattr(axis, "_figspec_explicit_format", False):
                continue
            low, high = axis.get_view_interval()
            if low <= 0 or high / low >= 100:
                continue
            # With fewer than three major ticks in view, matplotlib either
            # labels the minor ticks or leaves the axis almost blank; plain
            # decimal labels read better than "3.2 x 10^0" in both cases.
            inside = [value for value in axis.get_majorticklocs() if low <= value <= high]
            if len(inside) >= 3:
                continue
            formatter = FuncFormatter(plain)
            axis.set_major_formatter(formatter if inside else NullFormatter())
            axis.set_minor_formatter(formatter)


def build(
    spec: Spec,
    *,
    journal: str | None = None,
    journal_file: str | Path | None = None,
    dpi: int | None = None,
    formats: Sequence[str] | None = None,
) -> RenderResult:
    """Validate data, resolve style and draw the figure (without writing files)."""
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    preset = resolve_journal(spec, journal, journal_file)
    prepared = prepare_figure(spec)
    style = resolve_style(spec, preset, dpi=dpi, formats=formats)
    params = dict(rc_params(style))

    with matplotlib.rc_context(params):
        figure, series_colors, thin_colors = _draw(spec, prepared, style)

    from matplotlib.backends.backend_agg import FigureCanvasAgg

    canvas = FigureCanvasAgg(figure)
    canvas.draw()

    return RenderResult(
        spec=spec,
        prepared=prepared,
        style=style,
        figure=figure,
        journal=preset,
        rcparams=params,
        series_colors=series_colors,
        thin_colors=thin_colors,
    )


_EPS_DATE = re.compile(rb"%%CreationDate: [^\r\n]*\r?\n")


def _normalise_eps(path: Path) -> None:
    """Remove the wall-clock header so EPS rebuilds are byte-identical."""
    data = path.read_bytes()
    normalised = _EPS_DATE.sub(b"", data)
    if normalised != data:
        path.write_bytes(normalised)


def export(
    result: RenderResult,
    outdir: str | Path,
    *,
    stem: str | None = None,
    formats: Sequence[str] | None = None,
) -> list[OutputFile]:
    """Write the built figure in every requested format."""
    import matplotlib

    target = Path(outdir)
    target.mkdir(parents=True, exist_ok=True)
    name = stem or (result.spec.path.stem if result.spec.path else "figure")
    requested = tuple(formats or result.style.formats)
    transparent = result.spec.figure.transparent
    outputs: list[OutputFile] = []

    with matplotlib.rc_context(result.rcparams):
        for fmt in requested:
            path = target / f"{name}.{fmt}"
            dpi = result.style.dpi if fmt in RASTER_FORMATS else None
            metadata: dict[str, Any] = {}
            if fmt == "pdf":
                metadata = {"CreationDate": None}
            elif fmt == "svg":
                metadata = {"Date": None}
            try:
                result.figure.savefig(
                    path,
                    format=fmt,
                    dpi=dpi or 100,
                    transparent=transparent,
                    facecolor=None if transparent else result.style.background,
                    edgecolor="none",
                    metadata=metadata,
                )
            except (ValueError, RuntimeError, OSError) as exc:
                raise RenderError(f"cannot export {fmt}: {exc}", path=str(path)) from exc
            if fmt == "eps":
                _normalise_eps(path)
            outputs.append(
                OutputFile(
                    path=path,
                    format=fmt,
                    sha256=sha256_file(path),
                    bytes=path.stat().st_size,
                    dpi=dpi,
                )
            )

    result.outputs = outputs
    return outputs


def render_spec(
    spec: Spec,
    outdir: str | Path = "out",
    *,
    journal: str | None = None,
    journal_file: str | Path | None = None,
    dpi: int | None = None,
    formats: Sequence[str] | None = None,
    stem: str | None = None,
) -> RenderResult:
    """Build and export in one call (no linting, no manifest)."""
    result = build(
        spec,
        journal=journal,
        journal_file=journal_file,
        dpi=dpi,
        formats=formats,
    )
    export(result, outdir, stem=stem, formats=formats)
    return result
