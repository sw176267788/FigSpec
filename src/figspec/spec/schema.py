"""Data model for figspec figure specifications.

The model is deliberately boring: frozen dataclasses, no hidden state and no
business logic beyond validation.  Everything the renderer needs can be read
off a :class:`Spec` instance, which makes it cheap to hash, cache and test.

A specification is a mapping (YAML or JSON) validated into these objects::

    version: 1
    figure:  { ... }
    style:   { ... }
    axes:    { x: {...}, y: {...} }
    series:  [ {type: line, ...} ]

Multi-panel figures replace the top-level ``axes``/``series`` pair with a
``panels`` list; each panel carries its own axes and series.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

from ..errors import SpecError

__all__ = [
    "AnnotationSpec",
    "AxisSpec",
    "FigureSpec",
    "LegendSpec",
    "MetaSpec",
    "PanelSpec",
    "SeriesSpec",
    "Spec",
    "StyleSpec",
    "SUPPORTED_VERSION",
]

SUPPORTED_VERSION = 1
LAYOUTS = ("single", "1.5", "double", "custom")
SCALES = ("linear", "log", "symlog", "logit")
FORMATS = ("pdf", "svg", "png", "eps", "jpg", "tif", "ps")
SERIES_KINDS = ("line", "scatter", "bar", "box", "errorbar", "area", "heatmap")
SPINES = ("left", "right", "top", "bottom")
LEGEND_LOCATIONS = (
    "best",
    "upper right",
    "upper left",
    "lower left",
    "lower right",
    "center left",
    "center right",
    "lower center",
    "upper center",
    "center",
    "outside right",
    "outside bottom",
)


# ---------------------------------------------------------------------------
# validation helpers
# ---------------------------------------------------------------------------


def _err(path: str, message: str, hint: str | None = None) -> NoReturn:
    raise SpecError(message, path=path, hint=hint)


def _check_keys(mapping: Mapping[str, Any], allowed: Sequence[str], path: str) -> None:
    for key in mapping:
        if key in allowed:
            continue
        suggestion = difflib.get_close_matches(str(key), list(allowed), n=1, cutoff=0.6)
        hint = (
            f"did you mean '{suggestion[0]}'?"
            if suggestion
            else f"allowed keys: {', '.join(sorted(allowed))}"
        )
        _err(f"{path}.{key}" if path else str(key), "unknown key", hint)


def _as_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _err(path, f"expected a mapping, got {type(value).__name__}")
    return value


def _as_str(value: Any, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        _err(path, f"expected a string, got {type(value).__name__}")
    if not allow_empty and not value.strip():
        _err(path, "must not be empty")
    return value


def _as_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        _err(path, f"expected true/false, got {type(value).__name__}")
    return value


def _as_number(
    value: Any,
    path: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    positive: bool = False,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _err(path, f"expected a number, got {type(value).__name__}")
    number = float(value)
    if positive and number <= 0:
        _err(path, f"must be > 0, got {number:g}")
    if minimum is not None and number < minimum:
        _err(path, f"must be >= {minimum:g}, got {number:g}")
    if maximum is not None and number > maximum:
        _err(path, f"must be <= {maximum:g}, got {number:g}")
    return number


def _as_int(value: Any, path: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _err(path, f"expected an integer, got {type(value).__name__}")
    if minimum is not None and value < minimum:
        _err(path, f"must be >= {minimum}, got {value}")
    return value


def _as_choice(value: Any, path: str, options: Sequence[str]) -> str:
    text = _as_str(value, path)
    if text not in options:
        _err(path, f"expected one of {', '.join(options)}, got '{text}'")
    return text


def _as_str_tuple(value: Any, path: str) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, (list, tuple)):
        _err(path, f"expected a string or list of strings, got {type(value).__name__}")
    return tuple(_as_str(item, f"{path}[{index}]") for index, item in enumerate(value))


def _as_number_tuple(value: Any, path: str) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)):
        _err(path, f"expected a list of numbers, got {type(value).__name__}")
    return tuple(
        _as_number(item, f"{path}[{index}]") for index, item in enumerate(value)
    )


def _as_pair(value: Any, path: str) -> tuple[float, float]:
    numbers = _as_number_tuple(value, path)
    if len(numbers) != 2:
        _err(path, f"expected exactly 2 numbers, got {len(numbers)}")
    return numbers[0], numbers[1]


# ---------------------------------------------------------------------------
# style
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LegendSpec:
    """Legend placement and styling."""

    show: bool = True
    location: str = "best"
    frame: bool = False
    font_size: float | None = None
    columns: int = 1
    title: str | None = None

    ALLOWED = ("show", "location", "frame", "font_size", "columns", "title")

    @classmethod
    def from_mapping(cls, data: Any, path: str) -> LegendSpec:
        if data is None:
            return cls()
        mapping = _as_mapping(data, path)
        _check_keys(mapping, cls.ALLOWED, path)
        location = mapping.get("location", "best")
        if location not in LEGEND_LOCATIONS:
            _err(
                f"{path}.location",
                f"unknown legend location '{location}'",
                f"allowed: {', '.join(LEGEND_LOCATIONS)}",
            )
        font_size = mapping.get("font_size")
        return cls(
            show=_as_bool(mapping["show"], f"{path}.show") if "show" in mapping else True,
            location=str(location),
            frame=_as_bool(mapping["frame"], f"{path}.frame") if "frame" in mapping else False,
            font_size=(
                _as_number(font_size, f"{path}.font_size", positive=True)
                if font_size is not None
                else None
            ),
            columns=_as_int(mapping.get("columns", 1), f"{path}.columns", minimum=1),
            title=_as_str(mapping["title"], f"{path}.title") if "title" in mapping else None,
        )


@dataclass(frozen=True)
class StyleSpec:
    """Visual style shared by every panel."""

    font_family: tuple[str, ...] | None = None
    font_size: float | None = None
    palette: str | None = None
    grid: bool | None = None
    spines: tuple[str, ...] | None = None
    legend: LegendSpec = field(default_factory=LegendSpec)
    axes_linewidth: float | None = None
    tick_direction: str = "out"
    tick_length: float | None = None
    error_band_alpha: float = 0.25
    use_tex: bool = False

    ALLOWED = (
        "font_family",
        "font_size",
        "palette",
        "grid",
        "spines",
        "legend",
        "axes_linewidth",
        "tick_direction",
        "tick_length",
        "error_band_alpha",
        "use_tex",
    )

    @classmethod
    def from_mapping(cls, data: Any, path: str) -> StyleSpec:
        if data is None:
            return cls()
        mapping = _as_mapping(data, path)
        _check_keys(mapping, cls.ALLOWED, path)

        spines = mapping.get("spines")
        if spines is not None:
            spines_tuple = _as_str_tuple(spines, f"{path}.spines")
            for name in spines_tuple:
                if name not in SPINES:
                    _err(f"{path}.spines", f"unknown spine '{name}'", f"allowed: {', '.join(SPINES)}")
        else:
            spines_tuple = None

        direction = mapping.get("tick_direction", "out")
        if direction not in ("in", "out", "inout"):
            _err(f"{path}.tick_direction", "expected 'in', 'out' or 'inout'")

        font_size = mapping.get("font_size")
        linewidth = mapping.get("axes_linewidth")
        tick_length = mapping.get("tick_length")

        return cls(
            font_family=(
                _as_str_tuple(mapping["font_family"], f"{path}.font_family")
                if "font_family" in mapping
                else None
            ),
            font_size=(
                _as_number(font_size, f"{path}.font_size", positive=True)
                if font_size is not None
                else None
            ),
            palette=(
                _as_str(mapping["palette"], f"{path}.palette") if "palette" in mapping else None
            ),
            grid=_as_bool(mapping["grid"], f"{path}.grid") if "grid" in mapping else None,
            spines=spines_tuple,
            legend=LegendSpec.from_mapping(mapping.get("legend"), f"{path}.legend"),
            axes_linewidth=(
                _as_number(linewidth, f"{path}.axes_linewidth", positive=True)
                if linewidth is not None
                else None
            ),
            tick_direction=direction,
            tick_length=(
                _as_number(tick_length, f"{path}.tick_length", minimum=0)
                if tick_length is not None
                else None
            ),
            error_band_alpha=_as_number(
                mapping.get("error_band_alpha", 0.25),
                f"{path}.error_band_alpha",
                minimum=0,
                maximum=1,
            ),
            use_tex=_as_bool(mapping["use_tex"], f"{path}.use_tex") if "use_tex" in mapping else False,
        )


# ---------------------------------------------------------------------------
# figure
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FigureSpec:
    """Physical properties of the canvas."""

    journal: str | None = None
    layout: str = "single"
    size: tuple[float, float] | None = None
    height: float | None = None
    aspect: float | None = None
    dpi: int | None = None
    formats: tuple[str, ...] | None = None
    transparent: bool = False
    background: str | None = None
    pad: float = 0.02
    margins: Mapping[str, float] | None = None
    grid: tuple[int, int] | None = None

    ALLOWED = (
        "journal",
        "layout",
        "size",
        "height",
        "aspect",
        "dpi",
        "formats",
        "transparent",
        "background",
        "pad",
        "margins",
        "grid",
    )

    @classmethod
    def from_mapping(cls, data: Any, path: str) -> FigureSpec:
        mapping = _as_mapping(data or {}, path)
        _check_keys(mapping, cls.ALLOWED, path)

        size = mapping.get("size")
        if size is not None:
            width, height = _as_pair(size, f"{path}.size")
            if width <= 0 or height <= 0:
                _err(f"{path}.size", "width and height must be > 0")
            size_pair: tuple[float, float] | None = (width, height)
        else:
            size_pair = None

        formats: tuple[str, ...] | None = None
        if "formats" in mapping:
            raw_formats = mapping["formats"]
            if isinstance(raw_formats, str):
                raw_formats = [raw_formats]
            if not isinstance(raw_formats, (list, tuple)) or not raw_formats:
                _err(f"{path}.formats", "expected a non-empty list of formats")
            normalized: list[str] = []
            for index, item in enumerate(raw_formats):
                fmt = _as_choice(item, f"{path}.formats[{index}]", FORMATS)
                if fmt not in normalized:
                    normalized.append(fmt)
            formats = tuple(normalized)

        grid = mapping.get("grid")
        grid_pair: tuple[int, int] | None = None
        if grid is not None:
            rows, cols = _as_pair(grid, f"{path}.grid")
            if rows < 1 or cols < 1 or rows != int(rows) or cols != int(cols):
                _err(f"{path}.grid", "expected two positive integers [rows, cols]")
            grid_pair = (int(rows), int(cols))

        margins = mapping.get("margins")
        margins_map: dict[str, float] | None = None
        if margins is not None:
            raw_margins = _as_mapping(margins, f"{path}.margins")
            _check_keys(raw_margins, ("left", "right", "bottom", "top"), f"{path}.margins")
            margins_map = {
                key: _as_number(value, f"{path}.margins.{key}", minimum=0, maximum=0.99)
                for key, value in raw_margins.items()
            }

        height = mapping.get("height")
        aspect = mapping.get("aspect")
        if height is not None and aspect is not None:
            _err(path, "specify either 'height' or 'aspect', not both")

        return cls(
            journal=_as_str(mapping["journal"], f"{path}.journal") if "journal" in mapping else None,
            layout=_as_choice(mapping.get("layout", "single"), f"{path}.layout", LAYOUTS),
            size=size_pair,
            height=(
                _as_number(height, f"{path}.height", positive=True) if height is not None else None
            ),
            aspect=(
                _as_number(aspect, f"{path}.aspect", positive=True) if aspect is not None else None
            ),
            dpi=_as_int(mapping["dpi"], f"{path}.dpi", minimum=72) if "dpi" in mapping else None,
            formats=formats,
            transparent=(
                _as_bool(mapping["transparent"], f"{path}.transparent")
                if "transparent" in mapping
                else False
            ),
            background=(
                _as_str(mapping["background"], f"{path}.background")
                if "background" in mapping
                else None
            ),
            pad=_as_number(mapping.get("pad", 0.02), f"{path}.pad", minimum=0, maximum=0.5),
            margins=margins_map,
            grid=grid_pair,
        )


# ---------------------------------------------------------------------------
# axes / annotations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AxisSpec:
    """Configuration of one axis."""

    label: str | None = None
    scale: str = "linear"
    limits: tuple[float, float] | None = None
    ticks: tuple[float, ...] | None = None
    tick_format: str | None = None
    minor_ticks: bool = False
    grid: bool | None = None
    hide: bool = False
    invert: bool = False
    label_size: float | None = None
    tick_size: float | None = None

    ALLOWED = (
        "label",
        "scale",
        "limits",
        "ticks",
        "tick_format",
        "minor_ticks",
        "grid",
        "hide",
        "invert",
        "label_size",
        "tick_size",
    )

    @classmethod
    def from_mapping(cls, data: Any, path: str) -> AxisSpec:
        if data is None:
            return cls()
        mapping = _as_mapping(data, path)
        _check_keys(mapping, cls.ALLOWED, path)

        limits = mapping.get("limits")
        ticks = mapping.get("ticks")
        label_size = mapping.get("label_size")
        tick_size = mapping.get("tick_size")

        return cls(
            label=_as_str(mapping["label"], f"{path}.label", allow_empty=True)
            if "label" in mapping
            else None,
            scale=_as_choice(mapping.get("scale", "linear"), f"{path}.scale", SCALES),
            limits=_as_pair(limits, f"{path}.limits") if limits is not None else None,
            ticks=_as_number_tuple(ticks, f"{path}.ticks") if ticks is not None else None,
            tick_format=(
                _as_str(mapping["tick_format"], f"{path}.tick_format")
                if "tick_format" in mapping
                else None
            ),
            minor_ticks=(
                _as_bool(mapping["minor_ticks"], f"{path}.minor_ticks")
                if "minor_ticks" in mapping
                else False
            ),
            grid=_as_bool(mapping["grid"], f"{path}.grid") if "grid" in mapping else None,
            hide=_as_bool(mapping["hide"], f"{path}.hide") if "hide" in mapping else False,
            invert=_as_bool(mapping["invert"], f"{path}.invert") if "invert" in mapping else False,
            label_size=(
                _as_number(label_size, f"{path}.label_size", positive=True)
                if label_size is not None
                else None
            ),
            tick_size=(
                _as_number(tick_size, f"{path}.tick_size", positive=True)
                if tick_size is not None
                else None
            ),
        )


@dataclass(frozen=True)
class AnnotationSpec:
    """A text label placed on a panel, optionally with an arrow."""

    text: str
    xy: tuple[float, float] | None = None
    xy_axes: tuple[float, float] | None = None
    xytext: tuple[float, float] | None = None
    arrow: bool = False
    font_size: float | None = None
    color: str | None = None
    ha: str = "left"
    va: str = "baseline"
    rotation: float = 0.0

    ALLOWED = (
        "text",
        "xy",
        "xy_axes",
        "xytext",
        "arrow",
        "font_size",
        "color",
        "ha",
        "va",
        "rotation",
    )

    @classmethod
    def from_mapping(cls, data: Any, path: str) -> AnnotationSpec:
        mapping = _as_mapping(data, path)
        _check_keys(mapping, cls.ALLOWED, path)
        if "text" not in mapping:
            _err(path, "annotation requires a 'text' field")

        xy = mapping.get("xy")
        xy_axes = mapping.get("xy_axes")
        if xy is not None and xy_axes is not None:
            _err(path, "specify either 'xy' (data coordinates) or 'xy_axes' (0-1 axes coordinates)")

        ha = str(mapping.get("ha", "left"))
        if ha not in ("left", "center", "right"):
            _err(f"{path}.ha", "expected 'left', 'center' or 'right'")
        va = str(mapping.get("va", "baseline"))
        if va not in ("top", "center", "bottom", "baseline", "center_baseline"):
            _err(f"{path}.va", "expected one of top, center, bottom, baseline")

        xytext = mapping.get("xytext")
        font_size = mapping.get("font_size")
        rotation = mapping.get("rotation", 0.0)

        return cls(
            text=_as_str(mapping["text"], f"{path}.text", allow_empty=True),
            xy=_as_pair(xy, f"{path}.xy") if xy is not None else None,
            xy_axes=_as_pair(xy_axes, f"{path}.xy_axes") if xy_axes is not None else None,
            xytext=_as_pair(xytext, f"{path}.xytext") if xytext is not None else None,
            arrow=_as_bool(mapping["arrow"], f"{path}.arrow") if "arrow" in mapping else False,
            font_size=(
                _as_number(font_size, f"{path}.font_size", positive=True)
                if font_size is not None
                else None
            ),
            color=_as_str(mapping["color"], f"{path}.color") if "color" in mapping else None,
            ha=ha,
            va=va,
            rotation=_as_number(rotation, f"{path}.rotation"),
        )


# ---------------------------------------------------------------------------
# series
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SeriesSpec:
    """One drawing instruction inside a panel."""

    kind: str
    data: str | None = None
    x_column: str | None = None
    x_values: tuple[float | str, ...] | None = None
    y_columns: tuple[str, ...] = ()
    y_values: tuple[tuple[float, ...], ...] | None = None
    error_column: str | None = None
    error_values: tuple[float, ...] | None = None
    error_kind: str = "bar"
    labels: tuple[str, ...] | None = None
    colors: tuple[str, ...] | None = None
    label: str | None = None
    linestyle: str | None = None
    marker: str | None = None
    linewidth: float | None = None
    markersize: float | None = None
    alpha: float | None = None
    zorder: float | None = None
    width: float | None = None
    cmap: str | None = None
    vmin: float | None = None
    vmax: float | None = None
    annotate: bool = False
    matrix: tuple[tuple[float, ...], ...] | None = None
    row_labels: tuple[str, ...] | None = None
    col_labels: tuple[str, ...] | None = None
    params: Mapping[str, Any] = field(default_factory=dict)

    ALLOWED = (
        "type",
        "data",
        "x",
        "y",
        "error",
        "error_kind",
        "label",
        "labels",
        "colors",
        "color",
        "linestyle",
        "marker",
        "linewidth",
        "markersize",
        "alpha",
        "zorder",
        "width",
        "cmap",
        "vmin",
        "vmax",
        "annotate",
        "matrix",
        "row_labels",
        "col_labels",
        "params",
    )

    @property
    def is_heatmap(self) -> bool:
        return self.kind == "heatmap"

    @classmethod
    def from_mapping(cls, data: Any, path: str) -> SeriesSpec:
        mapping = _as_mapping(data, path)
        _check_keys(mapping, cls.ALLOWED, path)

        kind = _as_choice(mapping.get("type"), f"{path}.type", SERIES_KINDS)
        if "data" in mapping:
            data_path = _as_str(mapping["data"], f"{path}.data")
        else:
            data_path = None

        x_column: str | None = None
        x_values: tuple[float | str, ...] | None = None
        raw_x = mapping.get("x")
        if isinstance(raw_x, str):
            x_column = _as_str(raw_x, f"{path}.x")
        elif isinstance(raw_x, (list, tuple)):
            if raw_x and all(isinstance(item, str) for item in raw_x):
                x_values = tuple(_as_str(item, f"{path}.x") for item in raw_x)
            else:
                x_values = _as_number_tuple(raw_x, f"{path}.x")
        elif raw_x is not None:
            _err(f"{path}.x", "expected a column name or a list of numbers")

        y_columns: tuple[str, ...] = ()
        y_values: tuple[tuple[float, ...], ...] | None = None
        raw_y = mapping.get("y")
        if raw_y is not None:
            if isinstance(raw_y, str):
                y_columns = (_as_str(raw_y, f"{path}.y"),)
            elif isinstance(raw_y, (list, tuple)) and all(isinstance(item, str) for item in raw_y):
                y_columns = _as_str_tuple(raw_y, f"{path}.y")
            elif isinstance(raw_y, (list, tuple)) and all(
                isinstance(item, (list, tuple)) for item in raw_y
            ):
                y_values = tuple(
                    _as_number_tuple(item, f"{path}.y[{index}]")
                    for index, item in enumerate(raw_y)
                )
            elif isinstance(raw_y, (list, tuple)):
                y_values = (_as_number_tuple(raw_y, f"{path}.y"),)
            else:
                _err(f"{path}.y", "expected a column name, a list of numbers or a list of lists")

        error_column: str | None = None
        error_values: tuple[float, ...] | None = None
        raw_error = mapping.get("error")
        if isinstance(raw_error, str):
            error_column = _as_str(raw_error, f"{path}.error")
        elif isinstance(raw_error, (list, tuple)):
            error_values = _as_number_tuple(raw_error, f"{path}.error")
        elif raw_error is not None:
            _err(f"{path}.error", "expected a column name or a list of numbers")

        matrix: tuple[tuple[float, ...], ...] | None = None
        raw_matrix = mapping.get("matrix")
        if raw_matrix is not None:
            if not isinstance(raw_matrix, (list, tuple)) or not all(
                isinstance(row, (list, tuple)) for row in raw_matrix
            ):
                _err(f"{path}.matrix", "expected a list of rows, each row a list of numbers")
            matrix = tuple(
                _as_number_tuple(row, f"{path}.matrix[{index}]")
                for index, row in enumerate(raw_matrix)
            )
            widths = {len(row) for row in matrix}
            if len(widths) != 1:
                _err(f"{path}.matrix", "all rows must have the same number of columns")

        error_kind = str(mapping.get("error_kind", "bar"))
        if error_kind not in ("bar", "band"):
            _err(f"{path}.error_kind", "expected 'bar' or 'band'")

        colors: tuple[str, ...] | None = None
        if "colors" in mapping:
            colors = _as_str_tuple(mapping["colors"], f"{path}.colors")
        elif "color" in mapping:
            colors = (_as_str(mapping["color"], f"{path}.color"),)

        labels: tuple[str, ...] | None = None
        if "labels" in mapping:
            labels = _as_str_tuple(mapping["labels"], f"{path}.labels")
        elif "label" in mapping:
            labels = (_as_str(mapping["label"], f"{path}.label", allow_empty=True),)

        params = mapping.get("params")
        if params is not None:
            params_map = _as_mapping(params, f"{path}.params")
        else:
            params_map = {}

        def opt_number(key: str) -> float | None:
            value = mapping.get(key)
            if value is None:
                return None
            return _as_number(value, f"{path}.{key}", positive=True)

        return cls(
            kind=kind,
            data=data_path,
            x_column=x_column,
            x_values=x_values,
            y_columns=y_columns,
            y_values=y_values,
            error_column=error_column,
            error_values=error_values,
            error_kind=error_kind,
            labels=labels,
            colors=colors,
            label=labels[0] if labels else None,
            linestyle=(
                _as_str(mapping["linestyle"], f"{path}.linestyle")
                if "linestyle" in mapping
                else None
            ),
            marker=(
                _as_str(mapping["marker"], f"{path}.marker") if "marker" in mapping else None
            ),
            linewidth=opt_number("linewidth"),
            markersize=opt_number("markersize"),
            alpha=(
                _as_number(mapping["alpha"], f"{path}.alpha", minimum=0, maximum=1)
                if "alpha" in mapping
                else None
            ),
            zorder=(
                _as_number(mapping["zorder"], f"{path}.zorder") if "zorder" in mapping else None
            ),
            width=(
                _as_number(mapping["width"], f"{path}.width", positive=True)
                if "width" in mapping
                else None
            ),
            cmap=_as_str(mapping["cmap"], f"{path}.cmap") if "cmap" in mapping else None,
            vmin=(
                _as_number(mapping["vmin"], f"{path}.vmin") if "vmin" in mapping else None
            ),
            vmax=(
                _as_number(mapping["vmax"], f"{path}.vmax") if "vmax" in mapping else None
            ),
            annotate=(
                _as_bool(mapping["annotate"], f"{path}.annotate")
                if "annotate" in mapping
                else False
            ),
            matrix=matrix,
            row_labels=(
                _as_str_tuple(mapping["row_labels"], f"{path}.row_labels")
                if "row_labels" in mapping
                else None
            ),
            col_labels=(
                _as_str_tuple(mapping["col_labels"], f"{path}.col_labels")
                if "col_labels" in mapping
                else None
            ),
            params=params_map,
        )


# ---------------------------------------------------------------------------
# panels and root
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PanelSpec:
    """A single axes area with its own series."""

    axes: Mapping[str, AxisSpec] = field(default_factory=dict)
    series: tuple[SeriesSpec, ...] = ()
    title: str | None = None
    cell: tuple[int, int] | None = None
    legend: LegendSpec | None = None
    annotations: tuple[AnnotationSpec, ...] = ()
    share_x: bool | None = None
    share_y: bool | None = None

    ALLOWED = ("axes", "series", "title", "cell", "legend", "annotations", "share_x", "share_y")

    @classmethod
    def from_mapping(cls, data: Any, path: str) -> PanelSpec:
        mapping = _as_mapping(data, path)
        _check_keys(mapping, cls.ALLOWED, path)

        axes_raw = mapping.get("axes") or {}
        axes_mapping = _as_mapping(axes_raw, f"{path}.axes")
        _check_keys(axes_mapping, ("x", "y"), f"{path}.axes")
        axes = {
            name: AxisSpec.from_mapping(axes_mapping[name], f"{path}.axes.{name}")
            for name in ("x", "y")
            if name in axes_mapping
        }

        series_raw = mapping.get("series")
        if series_raw is None:
            series_raw = []
        if not isinstance(series_raw, (list, tuple)):
            _err(f"{path}.series", "expected a list of series entries")
        series = tuple(
            SeriesSpec.from_mapping(item, f"{path}.series[{index}]")
            for index, item in enumerate(series_raw)
        )
        if not series:
            _err(f"{path}.series", "a panel needs at least one series")

        cell = mapping.get("cell")
        cell_pair = _as_pair(cell, f"{path}.cell") if cell is not None else None
        if cell_pair is not None:
            row, col = cell_pair
            if row != int(row) or col != int(col) or row < 0 or col < 0:
                _err(f"{path}.cell", "expected two non-negative integers [row, col]")
            cell_pair = (int(row), int(col))

        annotations_raw = mapping.get("annotations") or []
        if not isinstance(annotations_raw, (list, tuple)):
            _err(f"{path}.annotations", "expected a list of annotations")
        annotations = tuple(
            AnnotationSpec.from_mapping(item, f"{path}.annotations[{index}]")
            for index, item in enumerate(annotations_raw)
        )

        return cls(
            axes=axes,
            series=series,
            title=_as_str(mapping["title"], f"{path}.title") if "title" in mapping else None,
            cell=cell_pair,
            legend=(
                LegendSpec.from_mapping(mapping["legend"], f"{path}.legend")
                if "legend" in mapping
                else None
            ),
            annotations=annotations,
            share_x=(
                _as_bool(mapping["share_x"], f"{path}.share_x") if "share_x" in mapping else None
            ),
            share_y=(
                _as_bool(mapping["share_y"], f"{path}.share_y") if "share_y" in mapping else None
            ),
        )


@dataclass(frozen=True)
class MetaSpec:
    """Free-form metadata used by galleries and provenance."""

    title: str | None = None
    description: str | None = None
    caption: str | None = None
    tags: tuple[str, ...] = ()
    author: str | None = None

    ALLOWED = ("title", "description", "caption", "tags", "author")

    @classmethod
    def from_mapping(cls, data: Any, path: str) -> MetaSpec:
        if data is None:
            return cls()
        mapping = _as_mapping(data, path)
        _check_keys(mapping, cls.ALLOWED, path)
        return cls(
            title=_as_str(mapping["title"], f"{path}.title") if "title" in mapping else None,
            description=(
                _as_str(mapping["description"], f"{path}.description")
                if "description" in mapping
                else None
            ),
            caption=_as_str(mapping["caption"], f"{path}.caption") if "caption" in mapping else None,
            tags=_as_str_tuple(mapping.get("tags", ()), f"{path}.tags") if "tags" in mapping else (),
            author=_as_str(mapping["author"], f"{path}.author") if "author" in mapping else None,
        )


@dataclass(frozen=True)
class Spec:
    """A fully validated figure specification."""

    version: int
    meta: MetaSpec
    figure: FigureSpec
    style: StyleSpec
    panels: tuple[PanelSpec, ...]
    path: Path | None = None
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def directory(self) -> Path:
        """Directory that relative data paths are resolved against."""
        return self.path.parent if self.path is not None else Path.cwd()

    def resolve(self, reference: str) -> Path:
        """Resolve a path written inside the spec."""
        candidate = Path(reference)
        return candidate if candidate.is_absolute() else self.directory / candidate

    @property
    def is_multi_panel(self) -> bool:
        return len(self.panels) > 1

    @classmethod
    def from_mapping(cls, data: Any, path: Path | None = None) -> Spec:
        mapping = _as_mapping(data, "spec")
        allowed = ("version", "meta", "figure", "style", "axes", "series", "panels", "legend", "annotations", "share_x", "share_y")
        _check_keys(mapping, allowed, "")

        version = mapping.get("version", SUPPORTED_VERSION)
        if version != SUPPORTED_VERSION:
            _err(
                "version",
                f"unsupported spec version {version!r}",
                f"this release understands version {SUPPORTED_VERSION}",
            )

        figure = FigureSpec.from_mapping(mapping.get("figure"), "figure")
        style = StyleSpec.from_mapping(mapping.get("style"), "style")
        meta = MetaSpec.from_mapping(mapping.get("meta"), "meta")

        panels_raw = mapping.get("panels")
        if panels_raw is None:
            if "series" not in mapping:
                _err("series", "missing required key: a spec needs 'series' or 'panels'")
            root_legend = mapping.get("legend")
            root_annotations = mapping.get("annotations")
            panel_mapping: dict[str, Any] = {
                "axes": mapping.get("axes") or {},
                "series": mapping["series"],
            }
            if root_legend is not None:
                panel_mapping["legend"] = root_legend
            if root_annotations is not None:
                panel_mapping["annotations"] = root_annotations
            if "share_x" in mapping:
                panel_mapping["share_x"] = mapping["share_x"]
            if "share_y" in mapping:
                panel_mapping["share_y"] = mapping["share_y"]
            panels: tuple[PanelSpec, ...] = (PanelSpec.from_mapping(panel_mapping, "panel"),)
        else:
            if "series" in mapping:
                _err("spec", "use either top-level 'series' or 'panels', not both")
            if not isinstance(panels_raw, (list, tuple)) or not panels_raw:
                _err("panels", "expected a non-empty list of panels")
            panels = tuple(
                PanelSpec.from_mapping(item, f"panels[{index}]")
                for index, item in enumerate(panels_raw)
            )

        assigned_cells = [panel.cell for panel in panels if panel.cell is not None]
        if len({cell for cell in assigned_cells}) != len(assigned_cells):
            _err("panels", "two panels claim the same [row, col] cell")

        return cls(
            version=version,
            meta=meta,
            figure=figure,
            style=style,
            panels=panels,
            path=path,
            raw=dict(mapping),
        )
