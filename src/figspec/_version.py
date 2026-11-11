"""Single source of truth for the figspec version."""

from __future__ import annotations

__version__ = "0.1.0"
__version_info__ = tuple(int(part) for part in __version__.split(".") if part.isdigit())
