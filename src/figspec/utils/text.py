"""Text formatting helpers used by the CLI and by reports."""

from __future__ import annotations

__all__ = ["human_size", "plural", "truncate"]


def human_size(num_bytes: int | float) -> str:
    """Format a byte count using binary units (``1.4 MiB``)."""
    size = float(num_bytes)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(size) < 1024.0 or unit == "GiB":
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} GiB"  # pragma: no cover - unreachable


def plural(count: int, singular: str, plural_form: str | None = None) -> str:
    """Return ``"1 error"`` or ``"3 errors"``."""
    word = singular if count == 1 else (plural_form or f"{singular}s")
    return f"{count} {word}"


def truncate(text: str, width: int, suffix: str = "…") -> str:
    """Shorten ``text`` to at most ``width`` characters."""
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= len(suffix):
        return suffix[:width]
    return text[: width - len(suffix)] + suffix
