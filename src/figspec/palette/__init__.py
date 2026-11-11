"""Colour palettes, accessibility simulation and colour-difference math."""

from __future__ import annotations

from .color import (
    contrast_ratio,
    delta_e_76,
    delta_e_ciede2000,
    hex_to_rgb,
    parse_color,
    relative_luminance,
    rgb_to_hex,
    rgb_to_lab,
)
from .cvd import CVD_KINDS, simulate, simulate_hex, simulate_pair_distance
from .palettes import (
    RAINBOW_COLORMAPS,
    Palette,
    get_palette,
    is_rainbow,
    list_palettes,
    palette_colors,
)

__all__ = [
    "CVD_KINDS",
    "RAINBOW_COLORMAPS",
    "Palette",
    "contrast_ratio",
    "delta_e_76",
    "delta_e_ciede2000",
    "get_palette",
    "hex_to_rgb",
    "is_rainbow",
    "list_palettes",
    "palette_colors",
    "parse_color",
    "relative_luminance",
    "rgb_to_hex",
    "rgb_to_lab",
    "simulate",
    "simulate_hex",
    "simulate_pair_distance",
]
