"""Lint rules and report formats."""

from __future__ import annotations

import json

import pytest

from figspec.lint import lint_result, lint_spec
from figspec.render import build
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


def _lint(data, **kwargs):
    result = build(load_spec_dict(data))
    try:
        return lint_result(result, **kwargs)
    finally:
        result.close()


def _codes(report):
    return {finding.code for finding in report.findings}


def test_clean_figure_has_no_findings():
    report = _lint(_spec())
    assert report.findings == ()
    assert report.counts() == {"error": 0, "warning": 0, "info": 0}


def test_font_below_minimum_is_an_error():
    data = _spec()
    data["style"] = {"font_size": 3.0}
    report = _lint(data)
    assert "FS001" in _codes(report)
    assert report.counts()["error"] >= 1


def test_low_raster_dpi_is_an_error():
    data = _spec()
    data["figure"] = {"size": [3.5, 2.4], "formats": ["png"], "dpi": 72}
    assert "ST002" in _codes(_lint(data))


def test_raster_only_output_warns():
    data = _spec()
    data["figure"] = {"size": [3.5, 2.4], "formats": ["png"]}
    assert "ST001" in _codes(_lint(data))


def test_truncated_bar_axis_warns():
    data = {
        "version": 1,
        "figure": {"size": [3.5, 2.4]},
        "axes": {"x": {"label": "m"}, "y": {"label": "acc", "limits": [50, 100]}},
        "series": [{"type": "bar", "x": ["a", "b"], "y": [76.0, 82.0]}],
    }
    report = _lint(data)
    assert "DA003" in _codes(report)


def test_bar_from_zero_is_clean():
    data = {
        "version": 1,
        "figure": {"size": [3.5, 2.4]},
        "axes": {"x": {"label": "m"}, "y": {"label": "acc", "limits": [0, 100]}},
        "series": [{"type": "bar", "x": ["a", "b"], "y": [76.0, 82.0]}],
    }
    assert "DA003" not in _codes(_lint(data))


def test_rainbow_colormap_warns():
    data = {
        "version": 1,
        "figure": {"size": [3.5, 2.4]},
        "series": [{"type": "heatmap", "matrix": [[1, 2], [3, 4]], "cmap": "jet"}],
    }
    assert "CO003" in _codes(_lint(data))


def test_low_contrast_colour_warns():
    data = _spec()
    data["series"][0]["colors"] = ["#F0E442"]
    assert "CO001" in _codes(_lint(data))


def test_missing_axis_label_is_noted():
    data = _spec()
    data["axes"] = {"x": {"label": ""}, "y": {"label": "Loss"}}
    report = _lint(data)
    assert "ST004" in _codes(report)


def test_missing_legend_warns():
    data = _spec()
    data["legend"] = {"show": False}
    assert "ST003" in _codes(_lint(data))


def test_figure_width_mismatch_warns():
    data = _spec()
    data["figure"] = {"journal": "nature", "layout": "single", "size": [5.0, 3.0]}
    assert "FS003" in _codes(_lint(data))


def test_ignore_accepts_globs():
    data = _spec()
    data["figure"] = {"size": [3.5, 2.4], "formats": ["png"]}
    assert "ST001" in _codes(_lint(data))
    assert "ST001" not in _codes(_lint(data, ignore=["ST*"]))


def test_fail_thresholds():
    data = _spec()
    data["figure"] = {"size": [3.5, 2.4], "formats": ["png"]}
    report = _lint(data)
    assert report.failed("error") is False
    assert report.failed("warning") is True
    assert report.failed("none") is False


def test_report_json_is_serialisable():
    report = _lint(_spec())
    payload = json.loads(report.to_json())
    assert payload["summary"] == {"error": 0, "warning": 0, "info": 0}
    assert payload["spec"] is None


def test_report_sarif_structure():
    data = _spec()
    data["figure"] = {"size": [3.5, 2.4], "formats": ["png"]}
    report = _lint(data)
    payload = json.loads(report.to_sarif())
    assert payload["version"] == "2.1.0"
    results = payload["runs"][0]["results"]
    assert results and results[0]["ruleId"] == "ST001"
    assert payload["runs"][0]["tool"]["driver"]["name"] == "figspec"


def test_report_text_contains_hint():
    data = _spec()
    data["style"] = {"font_size": 3.0}
    text = _lint(data).to_text()
    assert "FS001" in text
    assert "hint:" in text


def test_lint_spec_convenience(minimal, make_spec):
    path = make_spec(minimal)
    report = lint_spec(path)
    assert report.counts()["error"] == 0


def test_rule_failure_does_not_crash(monkeypatch):
    from figspec.lint import rules

    def broken(_context):
        raise RuntimeError("boom")

    monkeypatch.setitem(
        rules.RULE_REGISTRY,
        "ZZ999",
        rules.RuleMeta("ZZ999", "broken", "warning", "broken rule", broken),
    )
    data = _spec()
    report = _lint(data)
    assert "LINT999" in _codes(report)


def test_tiny_line_width_warns():
    data = _spec()
    data["series"][0]["linewidth"] = 0.05
    assert "FS002" in _codes(_lint(data))


def test_spec_error_for_unknown_journal(minimal, make_spec):
    minimal["figure"]["journal"] = "unknown"
    with pytest.raises(Exception):
        lint_spec(make_spec(minimal))
