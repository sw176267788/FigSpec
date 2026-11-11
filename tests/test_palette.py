"""Colour science and palette registry."""

from __future__ import annotations

import pytest

from figspec.errors import ConfigError
from figspec.palette import (
    contrast_ratio,
    delta_e_ciede2000,
    hex_to_rgb,
    is_rainbow,
    list_palettes,
    palette_colors,
    parse_color,
    rgb_to_hex,
    rgb_to_lab,
    simulate_pair_distance,
)

# Reference pairs from Sharma, Wu & Dalal (2005), table 1.
SHARMA = [
    ((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485), 2.0425),
    ((50.0, 3.1571, -77.2803), (50.0, 0.0, -82.7485), 2.8615),
    ((50.0, 2.8361, -74.0200), (50.0, 0.0, -82.7485), 3.4412),
    ((50.0, -1.3802, -84.2814), (50.0, 0.0, -82.7485), 1.0000),
    ((50.0, -1.1848, -84.8006), (50.0, 0.0, -82.7485), 1.0000),
    ((50.0, -0.9009, -85.5211), (50.0, 0.0, -82.7485), 1.0000),
]


@pytest.mark.parametrize(("first", "second", "expected"), SHARMA)
def test_ciede2000_matches_reference_values(first, second, expected):
    assert delta_e_ciede2000(first, second) == pytest.approx(expected, abs=1e-4)


def test_ciede2000_is_symmetric():
    first = rgb_to_lab(parse_color("#0072B2"))
    second = rgb_to_lab(parse_color("#D55E00"))
    assert delta_e_ciede2000(first, second) == pytest.approx(
        delta_e_ciede2000(second, first), abs=1e-9
    )


def test_contrast_black_on_white_is_21():
    assert contrast_ratio(hex_to_rgb("#000000"), hex_to_rgb("#ffffff")) == pytest.approx(21.0)


def test_contrast_same_colour_is_one():
    colour = hex_to_rgb("#4E79A7")
    assert contrast_ratio(colour, colour) == pytest.approx(1.0)


def test_hex_roundtrip():
    assert rgb_to_hex(hex_to_rgb("#0072B2")) == "#0072b2"
    assert rgb_to_hex(hex_to_rgb("#abc")) == "#aabbcc"


def test_parse_named_colour():
    assert parse_color("black").tolist() == [0.0, 0.0, 0.0]


def test_parse_bad_colour_raises():
    with pytest.raises(ValueError, match="unknown colour"):
        parse_color("not-a-colour")


def test_cvd_simulation_collapses_red_green():
    normal = delta_e_ciede2000(
        rgb_to_lab(parse_color("#D55E00")), rgb_to_lab(parse_color("#009E73"))
    )
    deuteranopia = simulate_pair_distance("#D55E00", "#009E73", "deuteranopia")
    assert normal > 20
    assert deuteranopia < normal / 2


def test_unknown_cvd_kind():
    from figspec.palette import simulate

    with pytest.raises(ValueError, match="unknown colour vision deficiency"):
        simulate([1, 0, 0], "tetrachromacy")


def test_palette_registry_lists_palettes():
    names = list_palettes()
    assert "okabe-ito" in names
    assert "viridis" in names


def test_palette_cycles_to_requested_length():
    colours = palette_colors("okabe-ito", 12)
    assert len(colours) == 12
    assert colours[0] == colours[8]


def test_first_five_okabe_colours_clear_three_to_one():
    for colour in palette_colors("okabe-ito", 5):
        assert contrast_ratio(parse_color(colour), (1.0, 1.0, 1.0)) >= 3.0


def test_unknown_palette_raises_with_hint():
    with pytest.raises(ConfigError) as info:
        palette_colors("not-a-palette")
    assert "available palettes" in str(info.value)


def test_rainbow_detection():
    assert is_rainbow("jet")
    assert not is_rainbow("viridis")
