"""Colour science primitives used by the accessibility checks.

Everything here is pure numpy: sRGB decoding, CIELAB conversion, the CIEDE2000
colour difference (Sharma et al., 2005) and the WCAG 2.1 contrast ratio.  The
math is deliberately spelled out instead of hidden behind a dependency, both to
keep figspec installable anywhere and to make the checks auditable.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

__all__ = [
    "contrast_ratio",
    "delta_e_ciede2000",
    "delta_e_76",
    "hex_to_rgb",
    "parse_color",
    "relative_luminance",
    "rgb_to_hex",
    "rgb_to_lab",
    "srgb_to_linear",
]

_D65 = np.array([0.95047, 1.00000, 1.08883])
_EPSILON = 216.0 / 24389.0
_KAPPA = 24389.0 / 27.0


def srgb_to_linear(rgb: np.ndarray | Sequence[float]) -> np.ndarray:
    """Decode sRGB (0-1) into linear-light RGB."""
    values = np.asarray(rgb, dtype=float)
    return np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(rgb: np.ndarray | Sequence[float]) -> np.ndarray:
    """Encode linear-light RGB into sRGB (0-1)."""
    values = np.asarray(rgb, dtype=float)
    return np.where(values <= 0.0031308, values * 12.92, 1.055 * values ** (1 / 2.4) - 0.055)


def parse_color(value: str) -> np.ndarray:
    """Parse a matplotlib/CSS colour string into an sRGB triple in 0-1.

    Supports ``#rgb``, ``#rrggbb``, ``rgb(...)`` and the CSS colour names that
    matplotlib knows about.
    """
    from matplotlib.colors import to_rgb

    try:
        return np.asarray(to_rgb(value), dtype=float)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"unknown colour '{value}'") from exc


def rgb_to_hex(rgb: Sequence[float]) -> str:
    """Format an sRGB triple in 0-1 as ``#rrggbb``."""
    values = np.clip(np.asarray(rgb, dtype=float), 0.0, 1.0)
    return "#" + "".join(f"{int(round(channel * 255)):02x}" for channel in values)


def hex_to_rgb(value: str) -> np.ndarray:
    """Parse ``#rrggbb`` (or ``#rgb``) into an sRGB triple in 0-1."""
    text = value.strip().lstrip("#")
    if len(text) == 3:
        text = "".join(channel * 2 for channel in text)
    if len(text) != 6:
        raise ValueError(f"invalid hex colour '{value}'")
    try:
        return np.asarray([int(text[i : i + 2], 16) / 255.0 for i in (0, 2, 4)])
    except ValueError as exc:
        raise ValueError(f"invalid hex colour '{value}'") from exc


def relative_luminance(rgb: Sequence[float]) -> float:
    """WCAG 2.1 relative luminance of an sRGB colour."""
    linear = srgb_to_linear(np.asarray(rgb, dtype=float))
    return float(0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2])


def contrast_ratio(first: Sequence[float], second: Sequence[float]) -> float:
    """WCAG 2.1 contrast ratio between two sRGB colours (1.0 - 21.0)."""
    lum_a = relative_luminance(first)
    lum_b = relative_luminance(second)
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


def rgb_to_lab(rgb: Sequence[float]) -> np.ndarray:
    """Convert an sRGB triple to CIELAB (D65 white point)."""
    linear = srgb_to_linear(np.asarray(rgb, dtype=float))
    xyz = np.array(
        [
            0.4124564 * linear[0] + 0.3575761 * linear[1] + 0.1804375 * linear[2],
            0.2126729 * linear[0] + 0.7151522 * linear[1] + 0.0721750 * linear[2],
            0.0193339 * linear[0] + 0.1191920 * linear[1] + 0.9503041 * linear[2],
        ]
    )
    ratio = xyz / _D65

    def pivot(value: float) -> float:
        return value ** (1 / 3) if value > _EPSILON else (_KAPPA * value + 16) / 116

    f_x, f_y, f_z = (pivot(float(value)) for value in ratio)
    return np.array([116 * f_y - 16, 500 * (f_x - f_y), 200 * (f_y - f_z)])


def delta_e_76(first: Sequence[float], second: Sequence[float]) -> float:
    """CIE76 colour difference (Euclidean distance in CIELAB)."""
    lab_a = np.asarray(first, dtype=float)
    lab_b = np.asarray(second, dtype=float)
    return float(np.linalg.norm(lab_a - lab_b))


def delta_e_ciede2000(
    lab_a: Sequence[float],
    lab_b: Sequence[float],
    *,
    k_l: float = 1.0,
    k_c: float = 1.0,
    k_h: float = 1.0,
) -> float:
    """CIEDE2000 colour difference between two CIELAB colours.

    Implements the formula of Sharma, Wu & Dalal (2005) with the standard
    parametric weights.
    """
    lightness_1, a_1, b_1 = (float(value) for value in lab_a)
    lightness_2, a_2, b_2 = (float(value) for value in lab_b)

    chroma_1 = math.hypot(a_1, b_1)
    chroma_2 = math.hypot(a_2, b_2)
    mean_chroma = (chroma_1 + chroma_2) / 2.0
    mean_chroma_7 = mean_chroma**7
    g = 0.5 * (1.0 - math.sqrt(mean_chroma_7 / (mean_chroma_7 + 25.0**7)))

    a_1p = (1.0 + g) * a_1
    a_2p = (1.0 + g) * a_2
    chroma_1p = math.hypot(a_1p, b_1)
    chroma_2p = math.hypot(a_2p, b_2)

    hue_1p = 0.0 if (a_1p == 0.0 and b_1 == 0.0) else math.degrees(math.atan2(b_1, a_1p)) % 360.0
    hue_2p = 0.0 if (a_2p == 0.0 and b_2 == 0.0) else math.degrees(math.atan2(b_2, a_2p)) % 360.0

    delta_lightness = lightness_2 - lightness_1
    delta_chroma = chroma_2p - chroma_1p
    chroma_product = chroma_1p * chroma_2p

    if chroma_product == 0.0:
        delta_hue_angle = 0.0
    else:
        delta_hue_angle = hue_2p - hue_1p
        if delta_hue_angle > 180.0:
            delta_hue_angle -= 360.0
        elif delta_hue_angle < -180.0:
            delta_hue_angle += 360.0
    delta_hue = 2.0 * math.sqrt(chroma_product) * math.sin(math.radians(delta_hue_angle / 2.0))

    mean_lightness = (lightness_1 + lightness_2) / 2.0
    mean_chroma_p = (chroma_1p + chroma_2p) / 2.0

    if chroma_product == 0.0:
        mean_hue = hue_1p + hue_2p
    elif abs(hue_1p - hue_2p) <= 180.0:
        mean_hue = (hue_1p + hue_2p) / 2.0
    elif hue_1p + hue_2p < 360.0:
        mean_hue = (hue_1p + hue_2p + 360.0) / 2.0
    else:
        mean_hue = (hue_1p + hue_2p - 360.0) / 2.0

    t = (
        1.0
        - 0.17 * math.cos(math.radians(mean_hue - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * mean_hue))
        + 0.32 * math.cos(math.radians(3.0 * mean_hue + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * mean_hue - 63.0))
    )
    delta_theta = 30.0 * math.exp(-(((mean_hue - 275.0) / 25.0) ** 2))
    mean_chroma_p_7 = mean_chroma_p**7
    rotation = 2.0 * math.sqrt(mean_chroma_p_7 / (mean_chroma_p_7 + 25.0**7))
    lightness_weight = 1.0 + (0.015 * (mean_lightness - 50.0) ** 2) / math.sqrt(
        20.0 + (mean_lightness - 50.0) ** 2
    )
    chroma_weight = 1.0 + 0.045 * mean_chroma_p
    hue_weight = 1.0 + 0.015 * mean_chroma_p * t
    rotation_term = -math.sin(math.radians(2.0 * delta_theta)) * rotation

    lightness_term = delta_lightness / (k_l * lightness_weight)
    chroma_term = delta_chroma / (k_c * chroma_weight)
    hue_term = delta_hue / (k_h * hue_weight)

    return math.sqrt(
        lightness_term**2
        + chroma_term**2
        + hue_term**2
        + rotation_term * chroma_term * hue_term
    )
