"""Journal presets."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from figspec.errors import ConfigError
from figspec.journals import (
    get_journal,
    list_journals,
    load_journal_file,
    parse_journal_mapping,
)


def test_all_bundled_presets_load():
    names = list_journals()
    assert len(names) >= 8
    for name in names:
        preset = get_journal(name)
        assert preset.name == name
        assert preset.column_widths["single"] > 0
        assert preset.column_widths["double"] > preset.column_widths["single"]
        assert 0 < preset.min_font_size <= preset.font_size
        assert preset.raster_dpi >= 300


def test_width_for_layout():
    nature = get_journal("nature")
    assert nature.width_for("single") == pytest.approx(3.504)
    assert nature.width_for("double") == pytest.approx(7.205)
    assert nature.width_for("nonsense") is None


def test_unknown_preset_lists_alternatives():
    with pytest.raises(ConfigError) as info:
        get_journal("nope")
    assert "available presets" in str(info.value)


def test_custom_journal_file(tmp_path: Path):
    payload = {
        "name": "custom",
        "display_name": "Custom Journal",
        "column_widths": {"single": 3.0, "double": 6.0},
        "font": {"family": ["DejaVu Sans"], "size": 8, "min_size": 6},
    }
    path = tmp_path / "custom.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    preset = load_journal_file(path)
    assert preset.name == "custom"
    assert preset.width_for("single") == 3.0


def test_missing_required_key_is_reported():
    with pytest.raises(ConfigError, match="missing required key"):
        parse_journal_mapping({"name": "x"}, where="test")


def test_widths_must_define_single_and_double():
    payload = {
        "name": "x",
        "display_name": "X",
        "column_widths": {"single": 3.0},
        "font": {"family": ["DejaVu Sans"]},
    }
    with pytest.raises(ConfigError, match="double"):
        parse_journal_mapping(payload, where="test")


def test_negative_width_is_rejected():
    payload = {
        "name": "x",
        "display_name": "X",
        "column_widths": {"single": -1, "double": 6.0},
        "font": {"family": ["DejaVu Sans"]},
    }
    with pytest.raises(ConfigError, match="positive"):
        parse_journal_mapping(payload, where="test")
