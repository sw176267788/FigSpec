"""Specification model and loading utilities."""

from __future__ import annotations

from .loader import deep_merge, interpolate_env, load_spec, load_spec_dict
from .schema import (
    SUPPORTED_VERSION,
    AnnotationSpec,
    AxisSpec,
    FigureSpec,
    LegendSpec,
    MetaSpec,
    PanelSpec,
    SeriesSpec,
    Spec,
    StyleSpec,
)

__all__ = [
    "SUPPORTED_VERSION",
    "AnnotationSpec",
    "AxisSpec",
    "FigureSpec",
    "LegendSpec",
    "MetaSpec",
    "PanelSpec",
    "SeriesSpec",
    "Spec",
    "StyleSpec",
    "deep_merge",
    "interpolate_env",
    "load_spec",
    "load_spec_dict",
]
