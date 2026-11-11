"""Rendering a directory of specs into a static HTML gallery."""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from .errors import FigspecError
from .lint import LintReport, lint_result
from .render.figure import build, export
from .spec.loader import load_spec

__all__ = ["GalleryEntry", "build_gallery"]

_SPEC_SUFFIXES = (".yaml", ".yml", ".json")


@dataclass
class GalleryEntry:
    """One figure in the gallery."""

    source: Path
    title: str
    description: str = ""
    tags: tuple[str, ...] = ()
    image: Path | None = None
    spec_text: str = ""
    report: LintReport | None = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


def discover_specs(directory: str | Path) -> list[Path]:
    """List ``*.yaml``/``*.yml``/``*.json`` specs directly inside ``directory``."""
    root = Path(directory)
    if root.is_file():
        return [root]
    if not root.is_dir():
        raise FigspecError("gallery path does not exist", path=str(root))
    found = [
        path
        for path in sorted(root.iterdir())
        if path.is_file() and path.suffix.lower() in _SPEC_SUFFIXES
    ]
    return found


def build_gallery(
    sources: str | Path | Sequence[str | Path],
    outdir: str | Path,
    *,
    journal: str | None = None,
    dpi: int = 140,
    title: str = "figspec gallery",
) -> Path:
    """Render every spec and write ``index.html``; returns the HTML path."""
    if isinstance(sources, (str, Path)):
        paths = discover_specs(sources)
    else:
        paths = [Path(item) for item in sources]

    target = Path(outdir)
    assets = target / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    if not paths:
        raise FigspecError("no specs found for the gallery")

    entries: list[GalleryEntry] = []
    for path in paths:
        entry = GalleryEntry(source=path, title=path.stem, description="")
        try:
            entry.spec_text = path.read_text(encoding="utf-8")
            spec = load_spec(path)
            entry.title = spec.meta.title or path.stem
            entry.description = spec.meta.description or spec.meta.caption or ""
            entry.tags = spec.meta.tags
            result = build(spec, journal=journal, dpi=dpi, formats=("png",))
            try:
                entry.report = lint_result(result)
                export(result, assets, stem=path.stem, formats=("png",))
            finally:
                result.close()
            entry.image = assets / f"{path.stem}.png"
        except FigspecError as exc:
            entry.error = str(exc)
        entries.append(entry)

    index = target / "index.html"
    index.write_text(_render_html(entries, title=title, journal=journal), encoding="utf-8")
    return index


def _badges(report: LintReport | None) -> str:
    if report is None:
        return ""
    counts = report.counts()
    parts = []
    for severity, label in (("error", "error"), ("warning", "warning"), ("info", "note")):
        if counts[severity]:
            parts.append(f'<span class="badge {severity}">{counts[severity]} {label}</span>')
    if not parts:
        parts.append('<span class="badge ok">clean</span>')
    return " ".join(parts)


def _render_html(entries: Sequence[GalleryEntry], *, title: str, journal: str | None) -> str:
    total = len(entries)
    failed = sum(1 for entry in entries if entry.error)
    subtitle = f"{total} figure(s)" + (f", {failed} failed" if failed else "")
    if journal:
        subtitle += f" · preset: {html.escape(journal)}"

    cards = []
    for entry in entries:
        if entry.error:
            body = f'<pre class="error">{html.escape(entry.error)}</pre>'
        else:
            body = (
                f'<img src="assets/{html.escape(entry.source.stem)}.png" '
                f'alt="{html.escape(entry.title)}">'
                if entry.image is not None
                else ""
            )
        tags = "".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in entry.tags)
        description = f'<p class="desc">{html.escape(entry.description)}</p>' if entry.description else ""
        cards.append(
            f"""
            <article class="card">
              {body}
              <div class="meta">
                <h2>{html.escape(entry.title)}</h2>
                {description}
                <div class="row">
                  <code>{html.escape(entry.source.name)}</code>
                  {_badges(entry.report)}
                </div>
                <div class="tags">{tags}</div>
                <details><summary>spec</summary><pre>{html.escape(entry.spec_text)}</pre></details>
              </div>
            </article>
            """
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #f6f7f9;
    --card: #ffffff;
    --ink: #14171a;
    --muted: #5b6570;
    --line: #e3e7ec;
    --accent: #1f6feb;
    --error: #c62828;
    --warning: #a86600;
    --info: #00607a;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #101418;
      --card: #171c22;
      --ink: #e8edf2;
      --muted: #9aa7b3;
      --line: #262d35;
      --accent: #6aa8ff;
      --error: #ff6b6b;
      --warning: #ffc247;
      --info: #5ad0ef;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 40px 24px 80px;
    background: var(--bg); color: var(--ink);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
  }}
  header {{ max-width: 1240px; margin: 0 auto 32px; }}
  header h1 {{ margin: 0 0 6px; font-size: 30px; letter-spacing: -0.02em; }}
  header p {{ margin: 0; color: var(--muted); }}
  .grid {{
    max-width: 1240px; margin: 0 auto;
    display: grid; gap: 22px;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  }}
  .card {{
    background: var(--card); border: 1px solid var(--line); border-radius: 14px;
    overflow: hidden; display: flex; flex-direction: column;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
  }}
  .card img {{ width: 100%; display: block; background: #fff; border-bottom: 1px solid var(--line); }}
  .meta {{ padding: 16px 18px 18px; display: flex; flex-direction: column; gap: 8px; }}
  .meta h2 {{ margin: 0; font-size: 16px; }}
  .desc {{ margin: 0; color: var(--muted); font-size: 13.5px; }}
  .row {{ display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; color: var(--muted); }}
  .tags {{ display: flex; gap: 6px; flex-wrap: wrap; }}
  .tag {{ font-size: 11.5px; color: var(--muted); border: 1px solid var(--line); border-radius: 999px; padding: 1px 8px; }}
  .badge {{ font-size: 11.5px; font-weight: 600; border-radius: 999px; padding: 1px 9px; border: 1px solid currentColor; }}
  .badge.error {{ color: var(--error); }}
  .badge.warning {{ color: var(--warning); }}
  .badge.info {{ color: var(--info); }}
  .badge.ok {{ color: var(--accent); }}
  details {{ margin-top: 4px; }}
  summary {{ cursor: pointer; color: var(--muted); font-size: 12.5px; }}
  pre {{ overflow: auto; background: rgba(127,127,127,0.08); padding: 12px; border-radius: 8px; font-size: 12px; }}
  pre.error {{ color: var(--error); }}
</style>
</head>
<body>
<header>
  <h1>{html.escape(title)}</h1>
  <p>{html.escape(subtitle)} · built with <a href="https://github.com/sw176267788/FigSpec">figspec</a></p>
</header>
<main class="grid">
{''.join(cards)}
</main>
</body>
</html>
"""
