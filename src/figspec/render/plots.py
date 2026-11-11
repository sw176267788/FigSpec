"""Plot-type implementations.

Each ``draw_*`` function takes a :class:`PanelState` (axes + style + running
colour cursor), the resolved data and the original series spec.  Adding a new
plot type means writing one function and registering it in :data:`DRAWERS`; the
rest of the pipeline (validation, linting, provenance) is type agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.colors import Normalize, to_rgb
from matplotlib.patches import Patch

from ..data.series import PreparedSeries
from ..errors import RenderError
from ..spec.schema import SeriesSpec
from .theme import ResolvedStyle

__all__ = ["DRAWERS", "PanelState", "draw_series"]

_LINESTYLES = ("-", "--", "-.", ":")


@dataclass
class PanelState:
    """Mutable drawing state for one axes."""

    ax: Axes
    style: ResolvedStyle
    color_index: int = 0
    handles: list[Artist] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    series_colors: list[str] = field(default_factory=list)
    thin_colors: list[str] = field(default_factory=list)

    def take_colors(
        self, count: int, explicit: Sequence[str] | None, *, thin: bool = True
    ) -> list[str]:
        palette = self.style.palette
        if explicit:
            colors = [explicit[index % len(explicit)] for index in range(count)]
        else:
            colors = [palette.color(self.color_index + index) for index in range(count)]
        self.color_index += count
        self.series_colors.extend(colors)
        if thin:
            self.thin_colors.extend(colors)
        return colors

    def cycle_index(self, count: int) -> int:
        palette_len = max(1, len(self.style.palette.colors))
        return (self.color_index - count) // palette_len

    def add_handle(self, artist: Artist, label: str | None) -> None:
        if label:
            self.handles.append(artist)
            self.labels.append(label)


def _label(prepared: PreparedSeries, index: int) -> str | None:
    if prepared.labels is None:
        return None
    if index >= len(prepared.labels):
        return None
    return prepared.labels[index]


def _error_array(prepared: PreparedSeries, index: int) -> np.ndarray | None:
    if not prepared.errors:
        return None
    errors = prepared.errors[0]
    if np.all(np.asarray(errors) == 0):
        return None
    return np.asarray(errors, dtype=float)


def _as_positions(x: np.ndarray) -> tuple[np.ndarray, list[str] | None]:
    if x.dtype == object:
        categories = [str(value) for value in x]
        return np.arange(len(categories), dtype=float), categories
    return np.asarray(x, dtype=float), None


def _text_colour(background: Sequence[float]) -> str:
    from ..palette.color import relative_luminance

    return "black" if relative_luminance(background) > 0.45 else "white"


def _apply_category_ticks(ax: Axes, prepared: PreparedSeries, spec: SeriesSpec) -> None:
    """Rotate category labels when the series carries strings on x."""
    if prepared.x.dtype != object:
        return
    rotation = spec.params.get("x_rotation", 0) if spec.params else 0
    if not rotation:
        return
    ax.tick_params(axis="x", labelrotation=rotation)
    for tick in ax.get_xticklabels():
        tick.set_ha("right")


def draw_line(state: PanelState, prepared: PreparedSeries, spec: SeriesSpec) -> None:
    ax = state.ax
    colors = state.take_colors(len(prepared.ys), prepared.colors)
    cycle = state.cycle_index(len(prepared.ys))
    linestyle = spec.linestyle or _LINESTYLES[cycle % len(_LINESTYLES)]
    linewidth = spec.linewidth or state.style.line_width
    marker = spec.marker
    markersize = spec.markersize or state.style.marker_size
    alpha = spec.alpha if spec.alpha is not None else 1.0
    zorder = spec.zorder if spec.zorder is not None else 2

    for index, values in enumerate(prepared.ys):
        label = _label(prepared, index)
        line = ax.plot(
            prepared.x,
            values,
            color=colors[index],
            linestyle=linestyle,
            linewidth=linewidth,
            marker=marker,
            markersize=markersize,
            alpha=alpha,
            zorder=zorder,
            label=label or "_nolegend_",
        )[0]
        state.add_handle(line, label)

        errors = _error_array(prepared, index)
        if errors is None:
            continue
        if spec.error_kind == "band":
            ax.fill_between(
                prepared.x,
                np.asarray(values) - errors,
                np.asarray(values) + errors,
                color=colors[index],
                alpha=state.style.error_band_alpha,
                linewidth=0,
                zorder=zorder - 1,
            )
        else:
            ax.errorbar(
                prepared.x,
                values,
                yerr=errors,
                fmt="none",
                ecolor=colors[index],
                elinewidth=linewidth * 0.8,
                capsize=2,
                capthick=linewidth * 0.8,
                alpha=alpha,
                zorder=zorder,
            )
    _apply_category_ticks(ax, prepared, spec)


def draw_errorbar(state: PanelState, prepared: PreparedSeries, spec: SeriesSpec) -> None:
    ax = state.ax
    colors = state.take_colors(len(prepared.ys), prepared.colors)
    markersize = spec.markersize or state.style.marker_size
    marker = spec.marker or "o"
    linewidth = spec.linewidth or state.style.line_width

    for index, values in enumerate(prepared.ys):
        label = _label(prepared, index)
        errors = prepared.errors[0] if prepared.errors else np.zeros_like(values)
        container = ax.errorbar(
            prepared.x,
            values,
            yerr=errors,
            fmt=marker,
            linestyle=spec.linestyle or "none",
            linewidth=linewidth,
            markersize=markersize,
            color=colors[index],
            ecolor=colors[index],
            elinewidth=linewidth * 0.8,
            capsize=2,
            capthick=linewidth * 0.8,
            alpha=spec.alpha if spec.alpha is not None else 1.0,
            zorder=spec.zorder if spec.zorder is not None else 2,
            label=label or "_nolegend_",
        )
        if label:
            state.add_handle(container.lines[0], label)
    _apply_category_ticks(ax, prepared, spec)


def draw_scatter(state: PanelState, prepared: PreparedSeries, spec: SeriesSpec) -> None:
    ax = state.ax
    colors = state.take_colors(len(prepared.ys), prepared.colors)
    marker = spec.marker or "o"
    size = (spec.markersize or state.style.marker_size) ** 2 * 1.4

    for index, values in enumerate(prepared.ys):
        label = _label(prepared, index)
        collection = ax.scatter(
            prepared.x,
            values,
            s=size,
            c=colors[index],
            marker=marker,
            alpha=spec.alpha if spec.alpha is not None else 0.9,
            linewidths=0.3,
            edgecolors="white",
            zorder=spec.zorder if spec.zorder is not None else 2,
            label=label or "_nolegend_",
        )
        state.add_handle(collection, label)
    _apply_category_ticks(ax, prepared, spec)


def draw_bar(state: PanelState, prepared: PreparedSeries, spec: SeriesSpec) -> None:
    ax = state.ax
    colors = state.take_colors(len(prepared.ys), prepared.colors, thin=False)
    positions, categories = _as_positions(prepared.x)
    groups = len(prepared.ys)
    total_width = spec.width or 0.8
    bar_width = total_width / groups
    offsets = (np.arange(groups) - (groups - 1) / 2.0) * bar_width
    alpha = spec.alpha if spec.alpha is not None else 1.0
    zorder = spec.zorder if spec.zorder is not None else 2

    for index, values in enumerate(prepared.ys):
        label = _label(prepared, index)
        bars = ax.bar(
            positions + offsets[index],
            values,
            width=bar_width,
            color=colors[index],
            alpha=alpha,
            linewidth=0.4,
            edgecolor="white",
            zorder=zorder,
            label=label or "_nolegend_",
        )
        state.add_handle(bars[0], label)
        errors = _error_array(prepared, index)
        if errors is not None:
            ax.errorbar(
                positions + offsets[index],
                values,
                yerr=errors,
                fmt="none",
                ecolor="#333333",
                elinewidth=state.style.line_width * 0.8,
                capsize=2,
                zorder=zorder + 1,
            )

    if categories is not None:
        rotation = spec.params.get("x_rotation", 0) if spec.params else 0
        ax.set_xticks(positions, categories, rotation=rotation)
        if rotation:
            for tick in ax.get_xticklabels():
                tick.set_ha("right")


def draw_box(state: PanelState, prepared: PreparedSeries, spec: SeriesSpec) -> None:
    ax = state.ax
    if prepared.x.dtype == object and len(prepared.ys) == 1:
        categories = list(dict.fromkeys(str(value) for value in prepared.x))
        values = np.asarray(prepared.ys[0], dtype=float)
        groups = [values[np.asarray(prepared.x, dtype=object) == category] for category in categories]
        labels: list[str] = categories
    else:
        groups = [np.asarray(values, dtype=float) for values in prepared.ys]
        labels = list(prepared.labels or spec.labels or ())
        if len(labels) != len(groups):
            labels = [f"group {index + 1}" for index in range(len(groups))]

    if not groups:
        raise RenderError("box plot has no groups to draw")

    colors = state.take_colors(len(groups), prepared.colors, thin=False)
    positions = np.arange(1, len(groups) + 1)
    linewidth = max(0.5, state.style.line_width * 0.8)
    box = ax.boxplot(
        groups,
        positions=positions,
        widths=spec.width or 0.55,
        patch_artist=True,
        showfliers=False,
        medianprops={"color": "#1a1a1a", "linewidth": linewidth},
        whiskerprops={"color": "#1a1a1a", "linewidth": linewidth},
        capprops={"color": "#1a1a1a", "linewidth": linewidth},
        boxprops={"color": "#1a1a1a", "linewidth": linewidth},
    )
    for index, patch in enumerate(box["boxes"]):
        patch.set_facecolor(colors[index])
        patch.set_alpha(spec.alpha if spec.alpha is not None else 0.75)

    rotation = spec.params.get("x_rotation", 0) if spec.params else 0
    ax.set_xticks(positions, labels, rotation=rotation)
    if rotation:
        for tick in ax.get_xticklabels():
            tick.set_ha("right")
    if len(groups) > 1:
        for index, label in enumerate(labels):
            state.add_handle(Patch(facecolor=colors[index], edgecolor="0.2"), label)


def draw_area(state: PanelState, prepared: PreparedSeries, spec: SeriesSpec) -> None:
    ax = state.ax
    colors = state.take_colors(len(prepared.ys), prepared.colors, thin=False)
    baseline = float(spec.params.get("baseline", 0.0)) if spec.params else 0.0
    alpha = spec.alpha if spec.alpha is not None else 0.35
    linewidth = spec.linewidth or state.style.line_width

    for index, values in enumerate(prepared.ys):
        label = _label(prepared, index)
        values = np.asarray(values, dtype=float)
        artist = ax.fill_between(
            prepared.x,
            baseline,
            values,
            color=colors[index],
            alpha=alpha,
            linewidth=0,
            zorder=spec.zorder if spec.zorder is not None else 2,
            label=label or "_nolegend_",
        )
        ax.plot(
            prepared.x,
            values,
            color=colors[index],
            linewidth=linewidth,
            zorder=(spec.zorder if spec.zorder is not None else 2) + 1,
        )
        state.add_handle(artist, label)


def draw_heatmap(state: PanelState, prepared: PreparedSeries, spec: SeriesSpec) -> None:
    ax = state.ax
    matrix = prepared.matrix
    if matrix is None:
        raise RenderError("heatmap series has no matrix")

    palette = state.style.palette
    cmap = spec.cmap or (palette.name if palette.kind == "sequential" else "viridis")
    normalizer = Normalize(vmin=spec.vmin, vmax=spec.vmax)
    image = ax.imshow(
        matrix,
        cmap=cmap,
        norm=normalizer,
        aspect="auto",
        interpolation="nearest",
        origin="upper",
    )

    rows, cols = matrix.shape
    col_rotation = spec.params.get("x_rotation", 45) if spec.params else 45
    ax.set_xticks(range(cols), list(prepared.col_labels or ()), rotation=col_rotation)
    if col_rotation:
        for tick in ax.get_xticklabels():
            tick.set_ha("right")
    ax.set_yticks(range(rows), list(prepared.row_labels or ()))

    if spec.annotate:
        colour_map = image.cmap
        values = np.asarray(matrix, dtype=float)
        decimals = 0
        for candidate in (0, 1, 2):
            if np.allclose(values, np.round(values, candidate)):
                decimals = candidate
                break
        template = f"{{:.{decimals}f}}"
        for row in range(rows):
            for column in range(cols):
                value = float(matrix[row, column])
                text_colour = _text_colour(to_rgb(colour_map(normalizer(value)))[:3])
                ax.text(
                    column,
                    row,
                    template.format(value),
                    ha="center",
                    va="center",
                    color=text_colour,
                    fontsize=state.style.tick_size,
                )

    label = None
    if spec.params:
        label = spec.params.get("colorbar_label")
    colourbar = ax.figure.colorbar(image, ax=ax, fraction=0.05, pad=0.02)
    colourbar.ax.tick_params(labelsize=state.style.tick_size, width=state.style.axis_linewidth)
    if label:
        colourbar.set_label(label, fontsize=state.style.label_size)


DRAWERS: dict[str, Callable[[PanelState, PreparedSeries, SeriesSpec], None]] = {
    "area": draw_area,
    "bar": draw_bar,
    "box": draw_box,
    "errorbar": draw_errorbar,
    "heatmap": draw_heatmap,
    "line": draw_line,
    "scatter": draw_scatter,
}


def draw_series(state: PanelState, prepared: PreparedSeries, spec: SeriesSpec) -> None:
    """Dispatch to the drawing function registered for ``spec.kind``."""
    drawer = DRAWERS.get(prepared.kind)
    if drawer is None:  # pragma: no cover - guarded by schema validation
        raise RenderError(f"no renderer registered for series type '{prepared.kind}'")
    if spec.params:
        _check_params(spec)
    try:
        drawer(state, prepared, spec)
    except RenderError:
        raise
    except (TypeError, ValueError) as exc:
        raise RenderError(
            f"could not draw {prepared.kind} series: {exc}",
            hint="check 'params' for options the plot type does not accept",
        ) from exc


def _check_params(spec: SeriesSpec) -> None:
    if not isinstance(spec.params, dict):  # pragma: no cover - schema guarantees a mapping
        raise RenderError("'params' must be a mapping")
