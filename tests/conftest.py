"""Shared fixtures for the figspec test suite."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import pytest
import yaml

CSV = "x,y\n1,1.0\n2,0.8\n3,0.6\n4,0.5\n"


@pytest.fixture
def make_spec(tmp_path: Path) -> Callable[..., Path]:
    """Write a spec (and optional data files) into ``tmp_path`` and return its path."""

    def factory(spec: dict[str, Any], data: dict[str, str] | None = None) -> Path:
        for name, content in (data or {}).items():
            target = tmp_path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        path = tmp_path / "figure.yaml"
        path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
        return path

    return factory


@pytest.fixture
def minimal() -> dict[str, Any]:
    """The smallest useful single-panel spec."""
    return {
        "version": 1,
        "figure": {"size": [3.5, 2.4], "formats": ["pdf", "svg", "png"]},
        "axes": {"x": {"label": "Epoch"}, "y": {"label": "Loss"}},
        "series": [
            {
                "type": "line",
                "x": [1, 2, 3, 4],
                "y": [[1.0, 0.8, 0.6, 0.5], [1.1, 0.85, 0.65, 0.52]],
                "labels": ["train", "val"],
            }
        ],
    }
