"""Turning :class:`SeriesSpec` entries into numeric arrays ready for drawing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..errors import DataError
from ..spec.schema import PanelSpec, SeriesSpec, Spec
from .table import Table, load_table

__all__ = [
    "PreparedFigure",
    "PreparedPanel",
    "PreparedSeries",
    "prepare_figure",
    "prepare_series",
]


@dataclass(frozen=True)
class PreparedSeries:
    """Numeric arrays for one series, plus where they came from."""

    kind: str
    x: np.ndarray
    ys: tuple[np.ndarray, ...]
    errors: tuple[np.ndarray, ...] | None = None
    labels: tuple[str, ...] | None = None
    colors: tuple[str, ...] | None = None
    matrix: np.ndarray | None = None
    row_labels: tuple[str, ...] | None = None
    col_labels: tuple[str, ...] | None = None
    source: str | None = None
    fingerprint: dict[str, Any] | None = None

    @property
    def is_categorical(self) -> bool:
        return bool(self.x.dtype == object)


@dataclass(frozen=True)
class PreparedPanel:
    """A panel with every series resolved."""

    spec: PanelSpec
    series: tuple[PreparedSeries, ...]


@dataclass(frozen=True)
class PreparedFigure:
    """The whole figure: resolved panels plus the data files it depends on."""

    spec: Spec
    panels: tuple[PreparedPanel, ...]
    inputs: tuple[dict[str, Any], ...] = field(default_factory=tuple)


def _float_array(values: np.ndarray, path: str) -> np.ndarray:
    array = np.asarray(values)
    if array.dtype == object:
        try:
            array = array.astype(float)
        except (TypeError, ValueError) as exc:
            raise DataError(f"expected numeric values: {exc}", path=path) from exc
    array = array.astype(float, copy=False)
    if array.size and not np.all(np.isfinite(array)):
        bad = int(np.flatnonzero(~np.isfinite(array))[0])
        raise DataError(
            f"non-finite value at row {bad + 1}",
            path=path,
            hint="remove NaN/inf rows, or clean them upstream of figspec",
        )
    return array


def _resolve_x(series: SeriesSpec, table: Table | None, length: int, path: str) -> np.ndarray:
    if table is not None:
        if series.x_values is not None:
            raise DataError(
                "'x' must be a column name when 'data' is used",
                path=f"{path}.x",
                hint="point 'x' at a column, or drop 'data' and give arrays inline",
            )
        if series.x_column is not None:
            return table.column(series.x_column)
        return np.arange(length)
    if series.x_values is None:
        return np.arange(length)
    x = np.asarray(series.x_values)
    if x.dtype.kind in ("U", "S"):
        return x.astype(object)
    if x.dtype == object:
        return x
    return _float_array(x, f"{path}.x")


def _resolve_ys(series: SeriesSpec, table: Table | None, path: str) -> tuple[np.ndarray, ...]:
    if table is not None:
        if not series.y_columns:
            raise DataError(
                "series needs 'y' column names when 'data' is used",
                path=path,
            )
        arrays = tuple(table.column(name) for name in series.y_columns)
        numeric = tuple(_float_array(array, f"{path}.y") for array in arrays)
        return numeric
    if series.y_values is None:
        raise DataError("series needs 'y' values", path=path)
    return tuple(_float_array(np.asarray(values), f"{path}.y") for values in series.y_values)


def _resolve_errors(
    series: SeriesSpec, table: Table | None, path: str
) -> tuple[np.ndarray, ...] | None:
    if table is not None and series.error_column is not None:
        return (_float_array(table.column(series.error_column), f"{path}.error"),)
    if series.error_values is not None:
        return (_float_array(np.asarray(series.error_values), f"{path}.error"),)
    return None


def prepare_series(
    series: SeriesSpec,
    spec: Spec,
    path: str,
    cache: dict[str, Table] | None = None,
) -> PreparedSeries:
    """Resolve one series against its data source."""
    table: Table | None = None
    if series.data is not None:
        data_path = spec.resolve(series.data)
        key = str(data_path)
        if cache is not None and key in cache:
            table = cache[key]
        else:
            table = load_table(data_path)
            if cache is not None:
                cache[key] = table

    if series.kind == "heatmap":
        return _prepare_heatmap(series, table, path)

    ys = _resolve_ys(series, table, path)
    if not ys:
        raise DataError("series has no data", path=path)

    lengths = {len(values) for values in ys}
    if len(lengths) != 1:
        raise DataError(
            f"column lengths differ: {sorted(lengths)}",
            path=path,
            hint="all columns of one series must have the same number of rows",
        )
    length = lengths.pop()
    if length == 0:
        raise DataError("series contains no rows", path=path)

    x = _resolve_x(series, table, length, path)
    if len(x) != length:
        raise DataError(
            f"'x' has {len(x)} values but 'y' has {length}",
            path=path,
        )
    if x.dtype != object:
        x = _float_array(x, f"{path}.x")

    errors = _resolve_errors(series, table, path)
    if errors is not None:
        error_length = len(errors[0])
        if error_length != length:
            raise DataError(
                f"'error' has {error_length} values but 'y' has {length}",
                path=path,
            )

    labels: tuple[str, ...] | None = series.labels
    if labels is None and len(series.y_columns) > 1:
        labels = tuple(dict.fromkeys(series.y_columns))
    if labels is not None and len(labels) != len(ys):
        raise DataError(
            f"{len(labels)} labels for {len(ys)} data columns",
            path=f"{path}.labels",
        )

    return PreparedSeries(
        kind=series.kind,
        x=x,
        ys=ys,
        errors=errors,
        labels=labels,
        colors=series.colors,
        source=series.data,
        fingerprint=table.fingerprint if table is not None else None,
    )


def _prepare_heatmap(series: SeriesSpec, table: Table | None, path: str) -> PreparedSeries:
    matrix: np.ndarray
    if series.matrix is not None:
        matrix = np.asarray(series.matrix, dtype=float)
    elif table is not None:
        key = "matrix" if "matrix" in table.columns else next(iter(table.columns))
        matrix = np.asarray(table.column(key), dtype=float)
        if matrix.ndim != 2:  # pragma: no cover - defensive
            raise DataError("heatmap data must be a 2-D array", path=path)
    else:
        raise DataError(
            "heatmap needs an inline 'matrix' or a 'data' file with a matrix",
            path=path,
        )

    if matrix.ndim != 2 or matrix.shape[0] < 1 or matrix.shape[1] < 1:
        raise DataError(f"heatmap expects a 2-D matrix, got shape {matrix.shape}", path=path)
    if not np.all(np.isfinite(matrix)):
        raise DataError("heatmap contains non-finite values", path=path)

    rows, cols = matrix.shape
    row_labels = series.row_labels
    col_labels = series.col_labels
    if row_labels is None:
        row_labels = tuple(str(index) for index in range(rows))
    if col_labels is None:
        col_labels = tuple(str(index) for index in range(cols))
    if len(row_labels) != rows or len(col_labels) != cols:
        raise DataError(
            f"labels do not match matrix shape {rows}x{cols}",
            path=path,
        )

    return PreparedSeries(
        kind="heatmap",
        x=np.arange(rows),
        ys=(np.asarray(matrix),),
        matrix=matrix,
        row_labels=tuple(row_labels),
        col_labels=tuple(col_labels),
        labels=series.labels,
        colors=series.colors,
        source=series.data,
        fingerprint=table.fingerprint if table is not None else None,
    )


def prepare_figure(spec: Spec) -> PreparedFigure:
    """Resolve every panel of ``spec``, sharing loaded tables across series."""
    cache: dict[str, Table] = {}
    fingerprints: dict[str, dict[str, Any]] = {}
    panels: list[PreparedPanel] = []

    for panel_index, panel in enumerate(spec.panels):
        prepared = []
        for series_index, series in enumerate(panel.series):
            path = f"panels[{panel_index}].series[{series_index}]"
            item = prepare_series(series, spec, path, cache)
            prepared.append(item)
            if item.fingerprint is not None:
                fingerprints[item.fingerprint["path"]] = dict(item.fingerprint)
        panels.append(PreparedPanel(spec=panel, series=tuple(prepared)))

    return PreparedFigure(
        spec=spec,
        panels=tuple(panels),
        inputs=tuple(sorted(fingerprints.values(), key=lambda item: item["path"])),
    )
