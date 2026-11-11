"""Built-in colour palettes.

Qualitative palettes are curated and colour-blind aware; sequential palettes are
thin wrappers around matplotlib colormaps and are mainly used by heatmaps.  The
registry is intentionally small and reviewable: every palette lists where it
comes from and how it was validated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..errors import ConfigError
from ..utils.hashing import sha256_json

__all__ = [
    "Palette",
    "get_palette",
    "is_rainbow",
    "list_palettes",
    "palette_colors",
    "palette_fingerprint",
]

RAINBOW_COLORMAPS = frozenset(
    {"jet", "rainbow", "gist_rainbow", "hsv", "nipy_spectral", "gist_ncar", "CMRmap"}
)


@dataclass(frozen=True)
class Palette:
    """A named sequence of colours plus provenance."""

    name: str
    colors: tuple[str, ...]
    kind: str  # "qualitative" | "sequential" | "diverging"
    description: str
    source: str

    @property
    def length(self) -> int:
        return len(self.colors)

    def color(self, index: int) -> str:
        return self.colors[index % len(self.colors)]


_QUALITATIVE: dict[str, Palette] = {
    "okabe-ito": Palette(
        name="okabe-ito",
        colors=(
            "#000000",
            "#0072B2",
            "#D55E00",
            "#009E73",
            "#CC79A7",
            "#E69F00",
            "#56B4E9",
            "#F0E442",
        ),
        kind="qualitative",
        description=(
            "Okabe & Ito colour universal design palette, ordered so the first five "
            "colours clear 3:1 contrast on white"
        ),
        source="Okabe & Ito (2008), Color Universal Design",
    ),
    "tol-bright": Palette(
        name="tol-bright",
        colors=("#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"),
        kind="qualitative",
        description="Paul Tol's bright scheme",
        source="Tol (2021), Technical Note: Colour Schemes",
    ),
    "tol-muted": Palette(
        name="tol-muted",
        colors=(
            "#332288",
            "#88CCEE",
            "#44AA99",
            "#117733",
            "#999933",
            "#DDCC77",
            "#CC6677",
            "#882255",
            "#AA4499",
        ),
        kind="qualitative",
        description="Paul Tol's muted scheme",
        source="Tol (2021), Technical Note: Colour Schemes",
    ),
    "ibm": Palette(
        name="ibm",
        colors=("#648FFF", "#785EF0", "#DC267F", "#FE6100", "#FFB000"),
        kind="qualitative",
        description="IBM Design Library colour-blind safe palette",
        source="IBM Design Language, accessible colour",
    ),
    "tableau": Palette(
        name="tableau",
        colors=(
            "#4E79A7",
            "#F28E2B",
            "#E15759",
            "#76B7B2",
            "#59A14F",
            "#EDC948",
            "#B07AA1",
            "#FF9DA7",
            "#9C755F",
            "#BAB0AC",
        ),
        kind="qualitative",
        description="Tableau 10, tabular default",
        source="Tableau Public colour palettes",
    ),
    "grayscale": Palette(
        name="grayscale",
        colors=("#000000", "#4D4D4D", "#808080", "#B3B3B3", "#D9D9D9"),
        kind="qualitative",
        description="Neutral greys for print or single-colour reproduction",
        source="figspec",
    ),
    "dark": Palette(
        name="dark",
        colors=("#1B1B1B", "#C0392B", "#2980B9", "#27AE60", "#8E44AD", "#D35400"),
        kind="qualitative",
        description="High-contrast dark set for slides and screens",
        source="figspec",
    ),
}

_SEQUENTIAL_NAMES = (
    "viridis",
    "cividis",
    "magma",
    "inferno",
    "plasma",
    "Greys",
    "Blues",
    "Reds",
    "YlGnBu",
)

_SEQUENTIAL_DESCRIPTIONS = {
    "viridis": "Perceptually uniform, colour-blind safe sequential map",
    "cividis": "Perceptually uniform and colour-blind optimised sequential map",
    "magma": "Perceptually uniform sequential map, dark to light",
    "inferno": "Perceptually uniform sequential map, dark to light",
    "plasma": "Perceptually uniform sequential map, dark to light",
    "Greys": "Neutral greyscale, safe for single-colour printing",
    "Blues": "Single-hue sequential map",
    "Reds": "Single-hue sequential map",
    "YlGnBu": "Multi-hue sequential map",
}

_SAMPLES = 9


def _sample_colormap(name: str, count: int = _SAMPLES) -> tuple[str, ...]:
    from matplotlib import colormaps
    from matplotlib.colors import to_hex

    try:
        cmap = colormaps[name]
    except KeyError:
        available = ", ".join(sorted(_QUALITATIVE) + list(_SEQUENTIAL_NAMES))
        raise ConfigError(
            f"unknown palette '{name}'",
            hint=f"available palettes: {available}",
        ) from None

    import numpy as np

    positions = np.linspace(0.08, 0.92, count)
    return tuple(to_hex(cmap(float(position)), keep_alpha=False) for position in positions)


def get_palette(name: str) -> Palette:
    """Return a palette by name, sampling matplotlib colormaps on demand."""
    if name in _QUALITATIVE:
        return _QUALITATIVE[name]
    if name in _SEQUENTIAL_NAMES or name in RAINBOW_COLORMAPS:
        return Palette(
            name=name,
            colors=_sample_colormap(name),
            kind="sequential",
            description=_SEQUENTIAL_DESCRIPTIONS.get(name, "matplotlib colormap"),
            source="matplotlib",
        )
    available = ", ".join(sorted(_QUALITATIVE) + list(_SEQUENTIAL_NAMES))
    raise ConfigError(f"unknown palette '{name}'", hint=f"available palettes: {available}")


def list_palettes() -> tuple[str, ...]:
    """All palette names accepted by :func:`get_palette`."""
    return tuple(sorted(_QUALITATIVE)) + _SEQUENTIAL_NAMES


def is_rainbow(name: str) -> bool:
    """Whether a colormap is a rainbow-style map that should be avoided."""
    return name in RAINBOW_COLORMAPS


def palette_colors(name: str, count: int | None = None) -> tuple[str, ...]:
    """Colours of a palette, cycled to ``count`` entries when given."""
    palette = get_palette(name)
    if count is None:
        return palette.colors
    if count <= 0:
        return ()
    return tuple(palette.color(index) for index in range(count))


def palette_fingerprint(colors: Sequence[str]) -> str:
    """Stable digest of an ordered colour sequence."""
    return sha256_json(list(colors))
