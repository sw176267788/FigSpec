"""The ``figspec`` command line interface."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import click

from ._version import __version__
from .api import lint as api_lint
from .api import render as api_render
from .api import verify as api_verify
from .errors import FigspecError
from .gallery import build_gallery
from .journals import get_journal, list_journals
from .lint import RULE_REGISTRY
from .palette import list_palettes, palette_colors
from .spec.schema import FORMATS
from .utils.text import human_size

__all__ = ["cli", "main"]

_CONTEXT = {"help_option_names": ["-h", "--help"], "max_content_width": 100}


def _use_color(disabled: bool) -> bool:
    if disabled or os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


def _table(rows: Sequence[Sequence[Any]], headers: Sequence[str]) -> str:
    material = [list(map(str, row)) for row in rows]
    widths = [
        max(len(str(headers[index])), *(len(row[index]) for row in material))
        if material
        else len(str(headers[index]))
        for index in range(len(headers))
    ]
    template = "  ".join(f"{{:<{width}}}" for width in widths)
    lines = [template.format(*headers), template.format(*["-" * width for width in widths])]
    lines.extend(template.format(*row) for row in material)
    return "\n".join(lines)


@click.group(context_settings=_CONTEXT, no_args_is_help=True)
@click.version_option(__version__, "-V", "--version", prog_name="figspec")
@click.option("--no-color", is_flag=True, help="Disable ANSI colours.")
@click.pass_context
def cli(ctx: click.Context, no_color: bool) -> None:
    """Declarative, publication-ready, reproducible scientific figures."""
    ctx.ensure_object(dict)
    ctx.obj["color"] = _use_color(no_color)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("spec", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o",
    "--out",
    "outdir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("out"),
    show_default=True,
    help="Directory for rendered files.",
)
@click.option(
    "-f",
    "--format",
    "formats",
    multiple=True,
    type=click.Choice(FORMATS, case_sensitive=False),
    help="Output format, repeatable. Defaults to the spec (pdf, svg, png).",
)
@click.option("-j", "--journal", metavar="NAME", help="Journal preset to target.")
@click.option(
    "--journal-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Custom journal preset (YAML).",
)
@click.option("--dpi", type=int, help="Raster resolution in dots per inch.")
@click.option("--stem", help="Output file stem (defaults to the spec name).")
@click.option("--strict", is_flag=True, help="Abort before writing if lint fails.")
@click.option(
    "--fail-on",
    type=click.Choice(["error", "warning", "none"]),
    default="error",
    show_default=True,
    help="Lowest severity that fails --strict.",
)
@click.option("--ignore", multiple=True, metavar="CODE", help="Rule code or glob to skip.")
@click.option("--no-lint", is_flag=True, help="Skip linting entirely.")
@click.option("--no-manifest", is_flag=True, help="Do not write a provenance manifest.")
@click.option("-q", "--quiet", is_flag=True, help="Only print errors.")
@click.pass_context
def render(
    ctx: click.Context,
    spec: Path,
    outdir: Path,
    formats: tuple[str, ...],
    journal: str | None,
    journal_file: Path | None,
    dpi: int | None,
    stem: str | None,
    strict: bool,
    fail_on: str,
    ignore: tuple[str, ...],
    no_lint: bool,
    no_manifest: bool,
    quiet: bool,
) -> int:
    """Render SPEC into PDF, SVG, PNG (or any subset)."""
    color = bool(ctx.obj.get("color"))
    started = time.perf_counter()
    outcome = api_render(
        spec,
        outdir,
        journal=journal,
        journal_file=journal_file,
        dpi=dpi,
        formats=tuple(formats) or None,
        stem=stem,
        strict=strict,
        fail_on=fail_on,
        ignore=ignore,
        lint=not no_lint,
        manifest=not no_manifest,
    )
    elapsed = time.perf_counter() - started
    try:
        if quiet:
            return 0
        for output in outcome.outputs:
            name = output.path.name
            label = "ok" if color else "ok"
            click.echo(f"  [{label}] {name:<24} {human_size(output.bytes):>9}")
        click.echo(f"rendered {len(outcome.outputs)} file(s) in {elapsed:.2f}s")

        if outcome.report.findings:
            click.echo(outcome.report.to_text(color=color))
        else:
            click.echo("lint: clean")
        if outcome.manifest is not None and outcome.manifest.path is not None:
            click.echo(f"provenance: {outcome.manifest.path}")
        return 0
    finally:
        outcome.close()


# ---------------------------------------------------------------------------
# lint
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("spec", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "sarif"]),
    default="text",
    show_default=True,
)
@click.option("-j", "--journal", metavar="NAME", help="Journal preset to check against.")
@click.option(
    "--journal-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Custom journal preset (YAML).",
)
@click.option("--ignore", multiple=True, metavar="CODE", help="Rule code or glob to skip.")
@click.option(
    "--fail-on",
    type=click.Choice(["error", "warning", "none"]),
    default="error",
    show_default=True,
)
@click.pass_context
def lint(
    ctx: click.Context,
    spec: Path,
    output_format: str,
    journal: str | None,
    journal_file: Path | None,
    ignore: tuple[str, ...],
    fail_on: str,
) -> int:
    """Check a figure against journal and accessibility rules."""
    report = api_lint(spec, journal=journal, journal_file=journal_file, ignore=ignore)
    if output_format == "json":
        click.echo(report.to_json())
    elif output_format == "sarif":
        click.echo(report.to_sarif())
    else:
        click.echo(report.to_text(color=bool(ctx.obj.get("color"))))
    return 1 if report.failed(fail_on) else 0


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("manifest", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Machine readable output.")
@click.pass_context
def verify(ctx: click.Context, manifest: Path, as_json: bool) -> int:
    """Check that a figure still matches its provenance manifest."""
    result = api_verify(manifest)
    if as_json:
        click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        click.echo(result.to_text(color=bool(ctx.obj.get("color"))))
    return 0 if result.ok else 1


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

_STARTER_SPEC = """\
# A figspec figure definition.  Run `figspec render figure.yaml` to build it.
# Reference: https://github.com/sw176267788/FigSpec/blob/main/docs/spec-reference.md
version: 1

meta:
  title: Training and validation loss
  description: Loss curves for the baseline model on the development split.
  tags: [deep-learning, training]

figure:
  journal: {journal}
  layout: single           # single | 1.5 | double | custom
  formats: [pdf, svg, png]

style:
  palette: okabe-ito       # colour-blind safe
  grid: true

axes:
  x: {{label: Epoch}}
  y: {{label: Cross-entropy loss}}

series:
  - type: line
    data: data/loss.csv
    x: epoch
    y: [train, val]
    labels: [Train, Validation]
    marker: o
    markersize: 2.5
"""

_STARTER_DATA = """\
epoch,train,val
1,1.284,1.372
2,1.032,1.101
3,0.884,0.947
4,0.781,0.842
5,0.703,0.769
6,0.645,0.712
7,0.598,0.671
8,0.561,0.641
9,0.531,0.618
10,0.507,0.602
11,0.487,0.591
12,0.470,0.584
"""


@cli.command()
@click.argument("directory", type=click.Path(path_type=Path), default=Path())
@click.option("--force", is_flag=True, help="Overwrite existing files.")
@click.option("--journal", default="nature", show_default=True, help="Journal preset to start from.")
def init(directory: Path, force: bool, journal: str) -> int:
    """Create a starter spec and dataset in DIRECTORY."""
    get_journal(journal)  # validate early
    target = directory if directory != Path() else Path.cwd()
    target.mkdir(parents=True, exist_ok=True)
    data_dir = target / "data"
    data_dir.mkdir(exist_ok=True)

    files = {
        target / "figure.yaml": _STARTER_SPEC.format(journal=journal),
        data_dir / "loss.csv": _STARTER_DATA,
    }
    written: list[Path] = []
    for path, content in files.items():
        if path.exists() and not force:
            click.echo(f"skip {path} (exists; use --force to overwrite)")
            continue
        path.write_text(content, encoding="utf-8")
        written.append(path)

    if written:
        click.echo(f"created {len(written)} file(s) in {target}")
        click.echo("next: figspec render figure.yaml")
    return 0


# ---------------------------------------------------------------------------
# gallery
# ---------------------------------------------------------------------------


@cli.command()
@click.argument(
    "sources",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "-o",
    "--out",
    "outdir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("site"),
    show_default=True,
)
@click.option("-j", "--journal", metavar="NAME", help="Journal preset used for every figure.")
@click.option("--dpi", type=int, default=140, show_default=True, help="Preview resolution.")
@click.option("--title", default="figspec gallery", show_default=True)
def gallery(
    sources: tuple[Path, ...],
    outdir: Path,
    journal: str | None,
    dpi: int,
    title: str,
) -> int:
    """Render SOURCES (directories or spec files) into a static HTML gallery."""
    collected: list[Path] = []
    for source in sources:
        if source.is_dir():
            collected.extend(
                sorted(
                    path
                    for path in source.iterdir()
                    if path.suffix.lower() in (".yaml", ".yml", ".json")
                )
            )
        else:
            collected.append(source)
    index = build_gallery(collected, outdir, journal=journal, dpi=dpi, title=title)
    click.echo(f"gallery written to {index}")
    return 0


# ---------------------------------------------------------------------------
# reference information
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--json", "as_json", is_flag=True)
def journals(as_json: bool) -> int:
    """List bundled journal presets."""
    presets = [get_journal(name) for name in list_journals()]
    if as_json:
        click.echo(json.dumps([preset.to_dict() for preset in presets], indent=2))
        return 0
    rows = [
        [
            preset.name,
            f"{preset.width_for('single') or 0:.2f}/{preset.width_for('double') or 0:.2f}",
            f"{preset.font_size:g}/{preset.min_font_size:g}",
            f"{preset.raster_dpi}",
            preset.publisher,
        ]
        for preset in presets
    ]
    click.echo(_table(rows, ["name", "width in", "font/min", "dpi", "publisher"]))
    return 0


@cli.command()
@click.option("--json", "as_json", is_flag=True)
@click.option("-n", "--count", type=int, default=6, show_default=True, help="Colours to sample.")
@click.pass_context
def palettes(ctx: click.Context, as_json: bool, count: int) -> int:
    """List colour palettes with swatches."""
    names = list_palettes()
    if as_json:
        payload = {name: list(palette_colors(name, count)) for name in names}
        click.echo(json.dumps(payload, indent=2))
        return 0

    color = bool(ctx.obj.get("color"))
    for name in names:
        colors = palette_colors(name, count)
        if color:
            strip = "".join(_ansi_block(item) for item in colors)
        else:
            strip = " ".join(colors)
        click.echo(f"{name:<12} {strip}")
    return 0


def _ansi_block(value: str) -> str:
    from .palette import hex_to_rgb

    red, green, blue = (int(round(channel * 255)) for channel in hex_to_rgb(value))
    return f"\x1b[48;2;{red};{green};{blue}m    \x1b[0m"


@cli.command()
@click.option("--json", "as_json", is_flag=True)
def rules(as_json: bool) -> int:
    """List lint rules."""
    entries = [RULE_REGISTRY[code] for code in sorted(RULE_REGISTRY)]
    if as_json:
        payload = [
            {
                "code": entry.code,
                "severity": entry.severity,
                "title": entry.title,
                "description": entry.description,
            }
            for entry in entries
        ]
        click.echo(json.dumps(payload, indent=2))
        return 0
    rows = [[entry.code, entry.severity, entry.title] for entry in entries]
    click.echo(_table(rows, ["code", "default", "title"]))
    return 0


@cli.command()
@click.option("--json", "as_json", is_flag=True)
def doctor(as_json: bool) -> int:
    """Report versions, backend and available fonts."""
    import platform

    import matplotlib
    import numpy

    info: dict[str, Any] = {
        "figspec": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "matplotlib": matplotlib.__version__,
        "numpy": numpy.__version__,
        "backend": matplotlib.get_backend(),
        "journals": len(list_journals()),
        "lint_rules": len(RULE_REGISTRY),
    }
    try:
        from matplotlib import font_manager

        families = sorted({font.name for font in font_manager.fontManager.ttflist})
        info["font_families"] = len(families)
        info["has_dejavu"] = any("DejaVu" in family for family in families)
    except Exception:  # pragma: no cover - font cache issues are environment specific
        info["font_families"] = None
        info["has_dejavu"] = None

    if as_json:
        click.echo(json.dumps(info, indent=2))
        return 0
    click.echo(f"figspec     {info['figspec']}")
    click.echo(f"python      {info['python']}  ({info['platform']})")
    click.echo(f"matplotlib  {info['matplotlib']}  backend={info['backend']}")
    click.echo(f"numpy       {info['numpy']}")
    click.echo(f"journals    {info['journals']} presets")
    click.echo(f"lint rules  {info['lint_rules']}")
    if info["font_families"] is not None:
        click.echo(f"fonts       {info['font_families']} families (DejaVu present: {info['has_dejavu']})")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point that maps :class:`FigspecError` to its exit code."""
    args = list(argv) if argv is not None else None
    try:
        result = cli.main(args=args, standalone_mode=False, prog_name="figspec")
        return int(result or 0)
    except FigspecError as exc:
        click.echo(str(exc), err=True)
        return exc.exit_code
    except click.exceptions.Exit as exc:
        return int(exc.exit_code)
    except click.exceptions.UsageError as exc:
        exc.show()
        return 2
    except click.ClickException as exc:
        exc.show()
        return int(exc.exit_code)
    except (click.exceptions.Abort, KeyboardInterrupt):
        click.echo("aborted", err=True)
        return 130
    except BrokenPipeError:  # pragma: no cover - pipe handling
        return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
