"""Colour-vision-deficiency simulation.

Uses the Machado, Oliveira & Fernandes (2009) matrices at full severity, applied
in linear-light RGB.  That is a good approximation of dichromatic vision and is
widely used to audit scientific figures; it is not a medical tool.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .color import linear_to_srgb, parse_color, srgb_to_linear

__all__ = ["CVD_KINDS", "simulate", "simulate_hex", "simulate_pair_distance"]

CVD_KINDS = ("protanopia", "deuteranopia", "tritanopia")

_MATRICES: dict[str, tuple[tuple[float, float, float], ...]] = {
    "protanopia": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deuteranopia": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "tritanopia": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}


def simulate(rgb: Sequence[float], kind: str) -> np.ndarray:
    """Simulate how an sRGB colour looks with the given colour vision deficiency."""
    try:
        matrix = np.asarray(_MATRICES[kind], dtype=float)
    except KeyError:
        raise ValueError(
            f"unknown colour vision deficiency '{kind}'",
        ) from None
    linear = srgb_to_linear(np.asarray(rgb, dtype=float))
    converted = matrix @ linear
    return np.clip(linear_to_srgb(np.clip(converted, 0.0, 1.0)), 0.0, 1.0)


def simulate_hex(value: str, kind: str) -> np.ndarray:
    """Convenience wrapper: hex colour in, simulated sRGB triple out."""
    return simulate(parse_color(value), kind)


def simulate_pair_distance(first: str, second: str, kind: str) -> float:
    """CIEDE2000 distance between two colours as seen with a given deficiency."""
    from .color import delta_e_ciede2000, rgb_to_lab

    colour_a = rgb_to_lab(simulate(parse_color(first), kind))
    colour_b = rgb_to_lab(simulate(parse_color(second), kind))
    return delta_e_ciede2000(colour_a, colour_b)
