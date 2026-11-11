"""Tabular data loading and series preparation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from figspec.data import load_table, prepare_figure
from figspec.data.series import prepare_series
from figspec.errors import DataError
from figspec.spec import load_spec_dict


def test_loads_numeric_csv(tmp_path: Path):
    path = tmp_path / "data.csv"
    path.write_text("x,y\n1,2.5\n2,3.5\n", encoding="utf-8")
    table = load_table(path)
    assert set(table.columns) == {"x", "y"}
    assert table.column("y").tolist() == [2.5, 3.5]
    assert len(table) == 2
    assert table.fingerprint["sha256"]


def test_loads_categorical_column(tmp_path: Path):
    path = tmp_path / "data.csv"
    path.write_text("model,accuracy\nResNet,76.1\nViT,81.8\n", encoding="utf-8")
    table = load_table(path)
    assert table.column("model").dtype == object
    assert table.column("model").tolist() == ["ResNet", "ViT"]


def test_missing_column_lists_available(tmp_path: Path):
    path = tmp_path / "data.csv"
    path.write_text("x,y\n1,2\n", encoding="utf-8")
    table = load_table(path)
    with pytest.raises(DataError) as info:
        table.column("nope")
    assert "available columns" in str(info.value)


def test_tsv_and_comment_lines(tmp_path: Path):
    path = tmp_path / "data.tsv"
    path.write_text("# generated\nx\ty\n1\t2\n3\t4\n", encoding="utf-8")
    assert load_table(path).column("y").tolist() == [2.0, 4.0]


def test_json_records(tmp_path: Path):
    path = tmp_path / "data.json"
    path.write_text('[{"x": 1, "y": 2}, {"x": 2, "y": 3}]', encoding="utf-8")
    assert load_table(path).column("y").tolist() == [2.0, 3.0]


def test_json_columns(tmp_path: Path):
    path = tmp_path / "data.json"
    path.write_text('{"x": [1, 2], "name": ["a", "b"]}', encoding="utf-8")
    table = load_table(path)
    assert table.column("name").tolist() == ["a", "b"]


def test_numpy_input(tmp_path: Path):
    path = tmp_path / "data.npy"
    np.save(path, np.array([[1.0, 2.0], [3.0, 4.0]]))
    table = load_table(path)
    assert table.column("col1").tolist() == [2.0, 4.0]


def test_unsupported_format(tmp_path: Path):
    path = tmp_path / "data.xlsx"
    path.write_bytes(b"")
    with pytest.raises(DataError, match="unsupported data format"):
        load_table(path)


def test_missing_data_file(tmp_path: Path):
    with pytest.raises(DataError, match="not found"):
        load_table(tmp_path / "nope.csv")


def test_duplicate_columns_are_rejected(tmp_path: Path):
    path = tmp_path / "data.csv"
    path.write_text("x,x\n1,2\n", encoding="utf-8")
    with pytest.raises(DataError, match="duplicate column"):
        load_table(path)


def test_inline_x_with_data_is_rejected(tmp_path: Path):
    path = tmp_path / "data.csv"
    path.write_text("x,y\n1,2\n2,3\n3,4\n", encoding="utf-8")
    spec = load_spec_dict(
        {
            "version": 1,
            "series": [{"type": "line", "data": str(path), "x": [1, 2], "y": "y"}],
        }
    )
    with pytest.raises(DataError, match="column name"):
        prepare_figure(spec)


def test_error_length_mismatch_is_reported(tmp_path: Path):
    path = tmp_path / "data.csv"
    path.write_text("x,y\n1,2\n2,3\n3,4\n", encoding="utf-8")
    spec = load_spec_dict(
        {
            "version": 1,
            "series": [
                {
                    "type": "errorbar",
                    "data": str(path),
                    "x": "x",
                    "y": "y",
                    "error": [0.1, 0.2],
                }
            ],
        }
    )
    with pytest.raises(DataError, match="'error' has 2 values"):
        prepare_figure(spec)


def test_non_finite_values_are_rejected(tmp_path: Path):
    path = tmp_path / "data.csv"
    path.write_text("x,y\n1,2\n2,nan\n", encoding="utf-8")
    spec = load_spec_dict(
        {"version": 1, "series": [{"type": "line", "data": str(path), "x": "x", "y": "y"}]}
    )
    with pytest.raises(DataError, match="non-finite"):
        prepare_figure(spec)


def test_default_x_is_row_index(tmp_path: Path):
    path = tmp_path / "data.csv"
    path.write_text("y\n5\n6\n7\n", encoding="utf-8")
    spec = load_spec_dict(
        {"version": 1, "series": [{"type": "line", "data": str(path), "y": "y"}]}
    )
    prepared = prepare_figure(spec)
    assert prepared.panels[0].series[0].x.tolist() == [0, 1, 2]


def test_error_column_is_prepared(tmp_path: Path):
    path = tmp_path / "data.csv"
    path.write_text("x,acc,std\nA,76.1,0.4\nB,81.8,0.3\n", encoding="utf-8")
    spec = load_spec_dict(
        {
            "version": 1,
            "series": [
                {"type": "bar", "data": str(path), "x": "x", "y": "acc", "error": "std"}
            ],
        }
    )
    series = prepare_figure(spec).panels[0].series[0]
    assert series.errors is not None
    assert series.errors[0].tolist() == [0.4, 0.3]
    assert series.fingerprint is not None


def test_heatmap_requires_matrix():
    spec = load_spec_dict({"version": 1, "series": [{"type": "heatmap", "y": [1, 2]}]})
    with pytest.raises(DataError, match="matrix"):
        prepare_figure(spec)


def test_inline_heatmap_labels():
    spec = load_spec_dict(
        {
            "version": 1,
            "series": [
                {
                    "type": "heatmap",
                    "matrix": [[1, 2], [3, 4]],
                    "row_labels": ["a", "b"],
                    "col_labels": ["c", "d"],
                }
            ],
        }
    )
    series = prepare_figure(spec).panels[0].series[0]
    assert series.matrix is not None and series.matrix.shape == (2, 2)
    assert series.row_labels == ("a", "b")


def test_prepare_series_shares_loaded_tables(tmp_path: Path):
    from figspec.data.table import Table

    path = tmp_path / "data.csv"
    path.write_text("x,y\n1,2\n2,3\n", encoding="utf-8")
    spec = load_spec_dict(
        {
            "version": 1,
            "series": [
                {"type": "line", "data": str(path), "x": "x", "y": "y"},
                {"type": "line", "data": str(path), "x": "x", "y": "y"},
            ],
        }
    )
    cache: dict[str, Table] = {}
    for index, series in enumerate(spec.panels[0].series):
        prepare_series(series, spec, f"series[{index}]", cache)
    assert len(cache) == 1
