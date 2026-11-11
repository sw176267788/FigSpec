"""Specification parsing, validation and loading."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from figspec.errors import ConfigError, SpecError
from figspec.spec import load_spec
from figspec.spec.schema import Spec


def test_minimal_spec_parses(minimal, make_spec):
    path = make_spec(minimal)
    spec = load_spec(path)
    assert isinstance(spec, Spec)
    assert spec.figure.layout == "single"
    assert len(spec.panels) == 1
    assert spec.panels[0].series[0].kind == "line"
    assert spec.directory == path.parent


def test_defaults_are_applied(minimal, make_spec):
    spec = load_spec(make_spec(minimal))
    assert spec.style.palette is None
    assert spec.panels[0].series[0].x_column is None
    assert spec.panels[0].series[0].x_values == (1.0, 2.0, 3.0, 4.0)


def test_formats_default_to_none_and_are_resolved_at_build_time(make_spec):
    spec = load_spec(make_spec({"version": 1, "series": [{"type": "line", "x": [1, 2], "y": [1, 2]}]}))
    assert spec.figure.formats is None


def test_unknown_key_suggests_typo(minimal, make_spec):
    minimal["figure"]["formats"] = ["pdf"]
    minimal["figure"]["format"] = ["pdf"]
    with pytest.raises(SpecError) as info:
        load_spec(make_spec(minimal))
    assert "unknown key" in str(info.value)
    assert "formats" in str(info.value)


def test_unsupported_version_raises(minimal, make_spec):
    minimal["version"] = 99
    with pytest.raises(SpecError, match="unsupported spec version"):
        load_spec(make_spec(minimal))


def test_series_and_panels_are_mutually_exclusive(minimal, make_spec):
    minimal["panels"] = [{"series": [{"type": "line", "x": [1, 2], "y": [1, 2]}]}]
    with pytest.raises(SpecError, match="either"):
        load_spec(make_spec(minimal))


def test_missing_series_raises(make_spec):
    with pytest.raises(SpecError, match="series"):
        load_spec(make_spec({"version": 1, "figure": {}}))


def test_unknown_series_type(minimal, make_spec):
    minimal["series"][0]["type"] = "violin"
    with pytest.raises(SpecError, match="expected one of"):
        load_spec(make_spec(minimal))


def test_axis_scale_is_validated(minimal, make_spec):
    minimal["axes"]["x"]["scale"] = "quadratic"
    with pytest.raises(SpecError, match="expected one of"):
        load_spec(make_spec(minimal))


def test_negative_figure_size_is_rejected(minimal, make_spec):
    minimal["figure"]["size"] = [3.5, -1]
    with pytest.raises(SpecError, match="must be > 0"):
        load_spec(make_spec(minimal))


def test_height_and_aspect_conflict(minimal, make_spec):
    minimal["figure"]["height"] = 2.0
    minimal["figure"]["aspect"] = 0.6
    with pytest.raises(SpecError, match="height"):
        load_spec(make_spec(minimal))


def test_duplicate_panel_cells(minimal, make_spec):
    spec = {
        "version": 1,
        "figure": {"size": [7, 3], "grid": [1, 2]},
        "panels": [
            {"cell": [0, 0], "series": [{"type": "line", "x": [1, 2], "y": [1, 2]}]},
            {"cell": [0, 0], "series": [{"type": "line", "x": [1, 2], "y": [1, 2]}]},
        ],
    }
    with pytest.raises(SpecError, match="claim the same"):
        load_spec(make_spec(spec))


def test_env_interpolation(monkeypatch, make_spec):
    monkeypatch.setenv("FIGSPEC_TEST_LABEL", "Accuracy")
    spec = {
        "version": 1,
        "axes": {"y": {"label": "${FIGSPEC_TEST_LABEL}"}},
        "series": [{"type": "line", "x": [1, 2], "y": [1, 2]}],
    }
    loaded = load_spec(make_spec(spec))
    assert loaded.panels[0].axes["y"].label == "Accuracy"


def test_env_default_value(make_spec):
    spec = {
        "version": 1,
        "axes": {"y": {"label": "${FIGSPEC_TEST_MISSING:-Fallback}"}},
        "series": [{"type": "line", "x": [1, 2], "y": [1, 2]}],
    }
    assert load_spec(make_spec(spec)).panels[0].axes["y"].label == "Fallback"


def test_missing_env_without_default_raises(make_spec):
    spec = {
        "version": 1,
        "axes": {"y": {"label": "${FIGSPEC_TEST_MISSING}"}},
        "series": [{"type": "line", "x": [1, 2], "y": [1, 2]}],
    }
    with pytest.raises(SpecError, match="not set"):
        load_spec(make_spec(spec))


def test_extends_merges_parents(tmp_path: Path):
    (tmp_path / "base.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "figure": {"journal": "nature", "layout": "double"},
                "axes": {"x": {"label": "Epoch"}},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "child.yaml").write_text(
        yaml.safe_dump(
            {
                "extends": "base.yaml",
                "figure": {"layout": "single"},
                "series": [{"type": "line", "x": [1, 2], "y": [1, 2]}],
            }
        ),
        encoding="utf-8",
    )
    spec = load_spec(tmp_path / "child.yaml")
    assert spec.figure.journal == "nature"
    assert spec.figure.layout == "single"
    assert spec.panels[0].axes["x"].label == "Epoch"


def test_circular_extends_is_detected(tmp_path: Path):
    (tmp_path / "a.yaml").write_text("extends: b.yaml\nversion: 1\n", encoding="utf-8")
    (tmp_path / "b.yaml").write_text("extends: a.yaml\nversion: 1\n", encoding="utf-8")
    with pytest.raises(SpecError, match="circular"):
        load_spec(tmp_path / "a.yaml")


def test_unknown_journal_raises_list(minimal, make_spec):
    minimal["figure"]["journal"] = "nope"
    with pytest.raises(ConfigError, match="unknown journal preset"):
        from figspec.render import build

        build(load_spec(make_spec(minimal)))


def test_broken_yaml_reports_position(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text("version: 1\nfigure: [unclosed\n", encoding="utf-8")
    with pytest.raises(SpecError):
        load_spec(path)


def test_non_mapping_spec_is_rejected(tmp_path: Path):
    path = tmp_path / "list.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(SpecError, match="mapping"):
        load_spec(path)


def test_load_spec_dict(minimal):
    from figspec.spec import load_spec_dict

    spec = load_spec_dict(minimal)
    assert spec.path is None
    assert spec.panels[0].series[0].labels == ("train", "val")
