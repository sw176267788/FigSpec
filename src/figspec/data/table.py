"""Loading tabular data referenced by specs.

Supported formats are CSV, TSV (delimiter sniffed), JSON, ``.npy`` and
``.npz``.  Everything is converted to numpy arrays; columns that cannot be
parsed as floats are kept as ``object`` arrays so that categorical axes (model
names, ablation settings, …) work without extra ceremony.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from ..errors import DataError
from ..utils.hashing import file_fingerprint

__all__ = ["Table", "load_table"]

_TRY_FLOAT_LIMIT = 2000


@dataclass(frozen=True)
class Table:
    """A named-column table loaded from disk."""

    columns: Mapping[str, np.ndarray]
    source: Path
    fingerprint: Mapping[str, Any]

    def __len__(self) -> int:
        return len(next(iter(self.columns.values()))) if self.columns else 0

    def column(self, name: str) -> np.ndarray:
        try:
            return self.columns[name]
        except KeyError:
            available = ", ".join(sorted(self.columns)) or "<none>"
            raise DataError(
                f"column '{name}' not found in {self.source.name}",
                hint=f"available columns: {available}",
            ) from None


def _to_array(values: list[str]) -> np.ndarray:
    cleaned = [value.strip() for value in values]
    numeric = True
    parsed: list[float] = []
    for value in cleaned:
        if value == "":
            parsed.append(float("nan"))
            continue
        try:
            parsed.append(float(value))
        except ValueError:
            numeric = False
            break
    if numeric:
        return np.asarray(parsed, dtype=float)
    return np.asarray(cleaned, dtype=object)


def _read_delimited(path: Path, delimiter: str) -> Table:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            sample = handle.read(4096)
            handle.seek(0)
            if delimiter == "sniff":
                try:
                    delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
                except csv.Error:
                    delimiter = ","
            rows = [
                row
                for row in csv.reader(handle, delimiter=delimiter)
                if row and not row[0].lstrip().startswith("#")
            ]
    except OSError as exc:
        raise DataError(f"cannot read data file: {exc.strerror or exc}", path=str(path)) from exc

    if not rows:
        raise DataError("data file is empty", path=str(path))

    header = [cell.strip() for cell in rows[0]]
    if len(set(header)) != len(header):
        duplicates = sorted({name for name in header if header.count(name) > 1})
        raise DataError(
            f"duplicate column names: {', '.join(duplicates)}",
            path=str(path),
        )
    body = rows[1:]
    if not body:
        raise DataError("data file has a header but no rows", path=str(path))

    columns: dict[str, np.ndarray] = {}
    for index, name in enumerate(header):
        columns[name] = _to_array([row[index] if index < len(row) else "" for row in body])
    return Table(columns=columns, source=path, fingerprint=file_fingerprint(path))


def _records_to_table(records: list[Any], path: Path) -> Table:
    if not records or not isinstance(records[0], Mapping):
        raise DataError("JSON data must be a list of objects or a mapping of columns", path=str(path))
    keys = list(records[0].keys())
    for index, record in enumerate(records[1:], start=1):
        if list(record.keys()) != keys:
            raise DataError(
                f"record {index} has different keys than record 0",
                path=str(path),
                hint="every JSON record must share the same keys",
            )
    columns: dict[str, np.ndarray] = {}
    for key in keys:
        values = [record[key] for record in records]
        if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
            columns[key] = np.asarray(values, dtype=float)
        else:
            columns[key] = np.asarray([str(value) for value in values], dtype=object)
    return Table(columns=columns, source=path, fingerprint=file_fingerprint(path))


def _read_json(path: Path) -> Table:
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise DataError(exc.msg, path=f"{path}:{exc.lineno}:{exc.colno}") from exc
    except OSError as exc:
        raise DataError(f"cannot read data file: {exc.strerror or exc}", path=str(path)) from exc

    if isinstance(raw, list):
        return _records_to_table(raw, path)
    if isinstance(raw, Mapping):
        columns: dict[str, np.ndarray] = {}
        for key, value in raw.items():
            if not isinstance(value, list):
                raise DataError(
                    f"column '{key}' is not a list",
                    path=str(path),
                    hint="use either a list of records or a mapping of column name -> list",
                )
            if all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value):
                columns[str(key)] = np.asarray(value, dtype=float)
            else:
                columns[str(key)] = np.asarray([str(item) for item in value], dtype=object)
        return Table(columns=columns, source=path, fingerprint=file_fingerprint(path))
    raise DataError("unsupported JSON layout", path=str(path))


def _read_numpy(path: Path) -> Table:
    try:
        if path.suffix.lower() == ".npz":
            with np.load(path) as archive:
                columns = {name: np.asarray(archive[name]) for name in archive.files}
            if not columns:
                raise DataError("npz archive contains no arrays", path=str(path))
            return Table(columns=columns, source=path, fingerprint=file_fingerprint(path))

        array = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise DataError(f"cannot read numpy file: {exc}", path=str(path)) from exc

    array = np.asarray(array)
    if array.ndim == 1:
        columns = {"value": array.astype(float)}
    elif array.ndim == 2:
        columns = {f"col{index}": array[:, index].astype(float) for index in range(array.shape[1])}
    else:
        raise DataError(f"expected a 1-D or 2-D array, got {array.ndim}-D", path=str(path))
    return Table(columns=columns, source=path, fingerprint=file_fingerprint(path))


def load_table(path: str | Path) -> Table:
    """Load a table from ``path``, choosing the reader from the file suffix."""
    resolved = Path(path)
    if not resolved.exists():
        raise DataError("data file not found", path=str(resolved))
    if resolved.is_dir():
        raise DataError("expected a data file, got a directory", path=str(resolved))

    suffix = resolved.suffix.lower()
    if suffix in (".csv",):
        return _read_delimited(resolved, ",")
    if suffix in (".tsv", ".tab"):
        return _read_delimited(resolved, "\t")
    if suffix in (".txt", ".dat"):
        return _read_delimited(resolved, "sniff")
    if suffix == ".json":
        return _read_json(resolved)
    if suffix in (".npy", ".npz"):
        return _read_numpy(resolved)

    raise DataError(
        f"unsupported data format '{suffix or '<none>'}'",
        path=str(resolved),
        hint="supported formats: .csv, .tsv, .txt, .json, .npy, .npz",
    )
