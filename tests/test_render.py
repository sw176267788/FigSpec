"""Building and exporting figures."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from figspec.errors import SpecError
from figspec.render import build, export
from figspec.spec import load_spec_dict


def _spec(**overrides):
    data = {
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
    data.update(overrides)
    return data


def test_default_size_comes_from_the_spec():
    result = build(load_spec_dict(_spec()))
    try:
        width, height = result.figure.get_size_inches()
        assert width == pytest.approx(3.5)
        assert height == pytest.approx(2.4)
    finally:
        result.close()


def test_journal_column_width_is_used():
    data = _spec()
    data["figure"] = {"journal": "nature", "layout": "single", "formats": ["pdf"]}
    result = build(load_spec_dict(data))
    try:
        assert result.figure.get_size_inches()[0] == pytest.approx(3.504)
        assert result.journal is not None and result.journal.name == "nature"
    finally:
        result.close()


def test_custom_layout_requires_size():
    data = _spec()
    data["figure"] = {"layout": "custom"}
    with pytest.raises(SpecError, match="custom"):
        build(load_spec_dict(data))


def test_export_writes_every_format(tmp_path: Path):
    result = build(load_spec_dict(_spec()))
    try:
        outputs = export(result, tmp_path)
        assert {output.format for output in outputs} == {"pdf", "svg", "png"}
        for output in outputs:
            assert output.path.exists()
            assert output.bytes > 0
            digest = hashlib.sha256(output.path.read_bytes()).hexdigest()
            assert digest == output.sha256
        assert (tmp_path / "figure.png").stat().st_size > 1000
    finally:
        result.close()


@pytest.mark.parametrize("suffix", ["pdf", "svg", "png", "eps"])
def test_export_is_byte_deterministic(tmp_path: Path, suffix: str):
    data = _spec()
    data["figure"] = {"size": [3.5, 2.4], "formats": [suffix]}
    digests = []
    for run in ("a", "b"):
        result = build(load_spec_dict(data))
        try:
            export(result, tmp_path / run)
        finally:
            result.close()
        digests.append((tmp_path / run / f"figure.{suffix}").read_bytes())
    assert digests[0] == digests[1]


def test_text_is_present_in_svg(tmp_path: Path):
    result = build(load_spec_dict(_spec()))
    try:
        export(result, tmp_path, formats=["svg"])
        svg = (tmp_path / "figure.svg").read_text(encoding="utf-8")
        assert "Epoch" in svg and "Loss" in svg
    finally:
        result.close()


def _series_specs():
    return {
        "line": [
            {
                "type": "line",
                "x": [1, 2, 3],
                "y": [[1.0, 0.9, 0.8]],
                "labels": ["a"],
            }
        ],
        "scatter": [
            {"type": "scatter", "x": [1, 2, 3], "y": [[1.0, 0.9, 0.8]], "label": "a"}
        ],
        "bar": [
            {
                "type": "bar",
                "x": ["a", "b", "c"],
                "y": [[1.0, 2.0, 3.0]],
                "error": [0.1, 0.2, 0.3],
            }
        ],
        "box": [
            {
                "type": "box",
                "x": ["a", "a", "b", "b"],
                "y": [[1.0, 1.2, 2.0, 2.2]],
            }
        ],
        "area": [{"type": "area", "x": [1, 2, 3], "y": [[1.0, 2.0, 1.5]]}],
        "errorbar": [
            {
                "type": "errorbar",
                "x": [1, 2, 3],
                "y": [[1.0, 2.0, 1.5]],
                "error": [0.1, 0.2, 0.1],
                "label": "a",
            }
        ],
        "heatmap": [
            {"type": "heatmap", "matrix": [[1.0, 2.0], [3.0, 4.0]], "annotate": True}
        ],
    }


@pytest.mark.parametrize("kind", sorted(_series_specs()))
def test_every_series_kind_renders(kind: str):
    data = {
        "version": 1,
        "figure": {"size": [3.5, 2.4]},
        "axes": {"x": {"label": "x"}, "y": {"label": "y"}},
        "series": _series_specs()[kind],
    }
    result = build(load_spec_dict(data))
    try:
        assert result.figure.axes
        if kind != "heatmap":
            assert len(result.series_colors) >= 1
    finally:
        result.close()


def test_multi_panel_grid():
    data = {
        "version": 1,
        "figure": {"size": [7.0, 5.0], "grid": [2, 2]},
        "panels": [
            {"title": "(a)", "series": [{"type": "line", "x": [1, 2], "y": [1, 2]}]},
            {"title": "(b)", "series": [{"type": "line", "x": [1, 2], "y": [2, 1]}]},
            {"title": "(c)", "series": [{"type": "line", "x": [1, 2], "y": [1, 3]}]},
            {"title": "(d)", "series": [{"type": "line", "x": [1, 2], "y": [3, 1]}]},
        ],
    }
    result = build(load_spec_dict(data))
    try:
        assert len(result.figure.axes) == 4
        titles = [axis.get_title(loc="left") for axis in result.figure.axes]
        assert titles == ["(a)", "(b)", "(c)", "(d)"]
    finally:
        result.close()


def test_too_many_panels_for_grid():
    data = {
        "version": 1,
        "figure": {"size": [4, 3], "grid": [1, 1]},
        "panels": [
            {"series": [{"type": "line", "x": [1, 2], "y": [1, 2]}]},
            {"series": [{"type": "line", "x": [1, 2], "y": [2, 1]}]},
        ],
    }
    with pytest.raises(SpecError, match="do not fit"):
        build(load_spec_dict(data))


def test_explicit_cells_are_respected():
    data = {
        "version": 1,
        "figure": {"size": [7, 3], "grid": [1, 2]},
        "panels": [
            {
                "cell": [0, 1],
                "title": "right",
                "series": [{"type": "line", "x": [1, 2], "y": [1, 2]}],
            },
            {
                "cell": [0, 0],
                "title": "left",
                "series": [{"type": "line", "x": [1, 2], "y": [2, 1]}],
            },
        ],
    }
    result = build(load_spec_dict(data))
    try:
        titles = [axis.get_title(loc="left") for axis in result.figure.axes]
        assert titles == ["right", "left"]
    finally:
        result.close()


def test_shared_axes_hide_inner_labels():
    data = {
        "version": 1,
        "figure": {"size": [3.5, 6.0], "grid": [2, 1]},
        "panels": [
            {
                "share_x": True,
                "axes": {"x": {"label": "Epoch"}},
                "series": [{"type": "line", "x": [1, 2], "y": [1, 2]}],
            },
            {
                "share_x": True,
                "axes": {"x": {"label": "Epoch"}},
                "series": [{"type": "line", "x": [1, 2], "y": [2, 1]}],
            },
        ],
    }
    result = build(load_spec_dict(data))
    try:
        top, bottom = result.figure.axes
        assert top.get_xlabel() == ""
        assert bottom.get_xlabel() == "Epoch"
    finally:
        result.close()


def test_explicit_margins_switch_off_constrained_layout():
    data = _spec()
    data["figure"] = {
        "size": [3.5, 2.4],
        "margins": {"left": 0.2, "right": 0.95, "bottom": 0.25, "top": 0.9},
    }
    result = build(load_spec_dict(data))
    try:
        assert result.figure.get_layout_engine() is None
        assert result.figure.axes[0].get_position().x0 == pytest.approx(0.2)
    finally:
        result.close()


def test_legend_outside_does_not_change_size():
    data = _spec()
    data["legend"] = {"location": "outside right"}
    result = build(load_spec_dict(data))
    try:
        assert result.figure.get_size_inches()[0] == pytest.approx(3.5)
    finally:
        result.close()


def test_annotations_are_rendered():
    from matplotlib.text import Text

    data = _spec()
    data["annotations"] = [
        {"text": "best", "xy": [3, 0.6], "xytext": [2, 0.9], "arrow": True},
        {"text": "panel note", "xy_axes": [0.02, 0.98]},
    ]
    result = build(load_spec_dict(data))
    try:
        texts = [text.get_text() for text in result.figure.findobj(Text)]
        assert "best" in texts
        assert "panel note" in texts
    finally:
        result.close()
