"""Data loading and series preparation."""

from __future__ import annotations

from .series import (
    PreparedFigure,
    PreparedPanel,
    PreparedSeries,
    prepare_figure,
    prepare_series,
)
from .table import Table, load_table

__all__ = [
    "PreparedFigure",
    "PreparedPanel",
    "PreparedSeries",
    "Table",
    "load_table",
    "prepare_figure",
    "prepare_series",
]
