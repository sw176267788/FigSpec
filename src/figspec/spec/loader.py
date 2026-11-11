"""Reading figure specifications from disk.

The loader owns everything that happens *before* validation:

* YAML / JSON parsing with useful syntax errors,
* ``${ENV_VAR}`` interpolation (``${VAR:-default}`` is supported),
* spec inheritance through ``extends`` (deep merge, child wins),
* programmatic overrides, mostly used by CLI flags.

Relative data paths are intentionally *not* resolved here.  They stay exactly
as the author wrote them, are hashed as such and are resolved against
``Spec.directory`` at render time.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

import yaml

from ..errors import SpecError
from .schema import Spec

__all__ = ["deep_merge", "interpolate_env", "load_spec", "load_spec_dict"]

_ENV_PATTERN = re.compile(r"\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?::-?(?P<default>[^}]*))?\}")


def _yaml_error(path: Path, exc: yaml.YAMLError) -> SpecError:
    mark = getattr(exc, "problem_mark", None)
    where = f"{path}:{mark.line + 1}:{mark.column + 1}" if mark is not None else str(path)
    problem = getattr(exc, "problem", None) or str(exc).splitlines()[0]
    context = getattr(exc, "context", None)
    message = f"{context}, {problem}" if context else str(problem)
    return SpecError(message, path=where, hint="check indentation and quoting around this line")


def interpolate_env(value: Any, *, source: Path | None = None) -> Any:
    """Recursively substitute ``${VAR}`` and ``${VAR:-default}`` in strings."""
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            name = match.group("name")
            default = match.group("default")
            if name in os.environ:
                return os.environ[name]
            if default is not None:
                return default
            raise SpecError(
                f"environment variable '{name}' is not set",
                path=str(source) if source else None,
                hint=f"set {name}, or write ${{{name}:-fallback}} to provide a default",
            )

        return _ENV_PATTERN.sub(replace, value)
    if isinstance(value, Mapping):
        return {key: interpolate_env(item, source=source) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [interpolate_env(item, source=source) for item in value]
    return value


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Merge ``override`` into ``base`` recursively; ``override`` wins for scalars.

    Lists are replaced, not concatenated: ``series`` and ``formats`` are ordered
    and merging them would almost never do the right thing.
    """
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            merged[key] = deep_merge(current, value)
        else:
            merged[key] = value
    return merged


def _read_mapping(path: Path, stack: tuple[Path, ...]) -> dict[str, Any]:
    resolved = path.resolve()
    if resolved in stack:
        chain = " -> ".join(str(item) for item in (*stack, resolved))
        raise SpecError("circular 'extends' chain", path=chain)

    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise SpecError(f"cannot read spec: {exc.strerror or exc}", path=str(path)) from exc

    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            raw: Any = json.loads(text)
        else:
            raw = yaml.safe_load(text)
    except json.JSONDecodeError as exc:
        raise SpecError(
            exc.msg,
            path=f"{path}:{exc.lineno}:{exc.colno}",
        ) from exc
    except yaml.YAMLError as exc:
        raise _yaml_error(path, exc) from exc

    if raw is None:
        raise SpecError("spec file is empty", path=str(path))
    if not isinstance(raw, Mapping):
        raise SpecError(
            f"expected a mapping at the top level, got {type(raw).__name__}",
            path=str(path),
        )

    data: dict[str, Any] = interpolate_env(dict(raw), source=path)

    extends = data.pop("extends", None)
    if extends is not None:
        references = [extends] if isinstance(extends, str) else list(extends)
        for reference in references:
            if not isinstance(reference, str):
                raise SpecError("'extends' must be a path or a list of paths", path=str(path))
            parent = (path.parent / reference).resolve()
            if not parent.exists():
                raise SpecError(
                    f"'extends' target not found: {reference}",
                    path=str(path),
                    hint=f"resolved to {parent}",
                )
            base = _read_mapping(parent, (*stack, resolved))
            data = deep_merge(base, data)

    return data


def load_spec(source: str | Path, *, overrides: Mapping[str, Any] | None = None) -> Spec:
    """Load, inherit, interpolate and validate a spec from ``source``."""
    path = Path(source)
    if not path.exists():
        raise SpecError("spec file not found", path=str(path), hint="check the path or run 'figspec init'")
    if path.is_dir():
        raise SpecError("expected a spec file, got a directory", path=str(path))

    data = _read_mapping(path, ())
    if overrides:
        data = deep_merge(data, overrides)
    return Spec.from_mapping(data, path=path)


def load_spec_dict(data: Mapping[str, Any], *, path: Path | None = None) -> Spec:
    """Validate an already-parsed mapping (useful in tests and notebooks)."""
    return Spec.from_mapping(interpolate_env(dict(data)), path=path)
