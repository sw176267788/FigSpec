"""Build the images embedded in the README and the docs site.

    python scripts/build_assets.py

The hero image and the per-figure PNGs are written under ``docs/assets`` and are
committed. The browsable HTML gallery is written to ``build/gallery`` (ignored by
git) so the repository only carries the images it actually references.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from figspec.api import render
from figspec.gallery import build_gallery

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
ASSETS = ROOT / "docs" / "assets"
GALLERY = ROOT / "build" / "gallery"
TMP = ROOT / "build" / "assets-tmp"

CAPTIONS = {
    "01-learning-curves": "Learning curves",
    "02-benchmark-accuracy": "Benchmark dot plot",
    "03-ablation-heatmap": "Ablation heatmap",
    "04-scaling-law": "Scaling law",
    "05-latency-box": "Latency distributions",
    "06-multi-panel": "Four-panel figure",
}

CELL_WIDTH = 760
PADDING = 26
CAPTION_HEIGHT = 46


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    import matplotlib

    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    path = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / name
    return ImageFont.truetype(str(path), size)


def render_examples() -> dict[str, Path]:
    TMP.mkdir(parents=True, exist_ok=True)
    rendered: dict[str, Path] = {}
    for spec_path in sorted(EXAMPLES.glob("*.yaml")):
        outcome = render(spec_path, TMP, formats=("png",), dpi=200, manifest=False, lint=False)
        try:
            rendered[spec_path.stem] = TMP / f"{spec_path.stem}.png"
        finally:
            outcome.close()
    return rendered


def compose_hero(images: dict[str, Path], destination: Path) -> None:
    order = [name for name in CAPTIONS if name in images]
    columns, rows = 2, 3
    cells: list[tuple[Image.Image, str]] = []
    for name in order:
        image = Image.open(images[name]).convert("RGB")
        ratio = CELL_WIDTH / image.width
        resized = image.resize((CELL_WIDTH, int(image.height * ratio)), Image.LANCZOS)
        cells.append((resized, CAPTIONS[name]))

    row_heights = [
        max(cells[index][0].height for index in range(row * columns, row * columns + columns))
        for row in range(rows)
    ]
    width = columns * CELL_WIDTH + (columns + 1) * PADDING
    height = sum(row_heights) + rows * (CAPTION_HEIGHT + PADDING) + PADDING
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    caption_font = _font(24)

    y = PADDING
    for row in range(rows):
        for column in range(columns):
            index = row * columns + column
            if index >= len(cells):
                continue
            image, caption = cells[index]
            x = PADDING + column * (CELL_WIDTH + PADDING)
            canvas.paste(image, (x, y))
            draw.text((x + 4, y + image.height + 10), caption, fill="#444444", font=caption_font)
        y += row_heights[row] + CAPTION_HEIGHT + PADDING

    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="PNG", optimize=True)
    print(f"wrote {destination.relative_to(ROOT)} ({canvas.width}x{canvas.height})")


def copy_gallery_images(images: dict[str, Path]) -> None:
    target = ASSETS / "gallery"
    target.mkdir(parents=True, exist_ok=True)
    for name, path in images.items():
        destination = target / f"{name}.png"
        destination.write_bytes(path.read_bytes())
        print(f"wrote {destination.relative_to(ROOT)}")


def compose_social(hero_figure: Path, destination: Path) -> None:
    """Build the 1280x640 image GitHub uses for link previews."""
    canvas = Image.new("RGB", (1280, 640), "white")
    shot = Image.open(hero_figure).convert("RGB")
    width = 760
    ratio = width / shot.width
    shot = shot.resize((width, int(shot.height * ratio)), Image.LANCZOS)
    if shot.height > 560:
        top = (shot.height - 560) // 2
        shot = shot.crop((0, top, shot.width, top + 560))
    canvas.paste(shot, (1280 - width - 40, (640 - shot.height) // 2))

    draw = ImageDraw.Draw(canvas)
    draw.text((56, 190), "figspec", fill="#111111", font=_font(104, bold=True))
    draw.text((60, 320), "Figures as code.", fill="#1f6feb", font=_font(38))
    draw.text((60, 384), "Declarative specs, journal checks,", fill="#444444", font=_font(22))
    draw.text((60, 416), "byte-reproducible output.", fill="#444444", font=_font(22))

    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="PNG", optimize=True)
    print(f"wrote {destination.relative_to(ROOT)} (1280x640)")


def main() -> None:
    images = render_examples()
    compose_hero(images, ASSETS / "hero.png")
    compose_social(images["06-multi-panel"], ASSETS / "social-preview.png")
    copy_gallery_images(images)
    index = build_gallery(
        sorted(EXAMPLES.glob("*.yaml")),
        GALLERY,
        dpi=140,
        title="figspec · example gallery",
    )
    print(f"wrote {index.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
