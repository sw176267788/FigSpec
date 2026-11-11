"""figspec - declarative, publication-ready, reproducible scientific figures.

The public API is import-light: nothing pulls in matplotlib until you actually
build a figure.

    >>> import figspec
    >>> spec = figspec.load_spec("figure.yaml")
    >>> result = figspec.render(spec, "out/")
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from ._version import __version__, __version_info__
from .errors import (
    ConfigError,
    DataError,
    FigspecError,
    LintFailure,
    ProvenanceError,
    RenderError,
    SpecError,
)
from .spec import Spec, load_spec, load_spec_dict

__all__ = [
    "ConfigError",
    "DataError",
    "FigspecError",
    "LintFailure",
    "ProvenanceError",
    "RenderError",
    "Spec",
    "SpecError",
    "__version__",
    "__version_info__",
    "load_spec",
    "load_spec_dict",
    "render",
    "lint",
    "verify",
]

_LAZY = {
    "render": ("figspec.api", "render"),
    "lint": ("figspec.api", "lint"),
    "verify": ("figspec.api", "verify"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute = _LAZY[name]
    except KeyError:
        raise AttributeError(f"module 'figspec' has no attribute {name!r}") from None
    return getattr(import_module(module_name), attribute)


def __dir__() -> list[str]:
    return sorted(__all__)
