# Quickstart

## Install

figspec is not on PyPI yet; install it from the repository:

```bash
pip install "git+https://github.com/sw176267788/FigSpec.git"
```

or, for development, clone it and install the editable package:

```bash
git clone https://github.com/sw176267788/FigSpec.git
cd FigSpec
pip install -e ".[dev]"
```

Python 3.10+ is required. The only runtime dependencies are matplotlib, numpy,
PyYAML and click.

## Your first figure

```bash
figspec init my-paper
cd my-paper
figspec render figure.yaml -o ../figures
```

`figspec init` writes two files:

```
my-paper/
├── figure.yaml
└── data/
    └── loss.csv
```

`figure.yaml` targets the Nature preset at single-column width. Rendering it
produces:

```
../figures/figure.pdf
../figures/figure.svg
../figures/figure.png
../figures/figure.figspec.json
```

Open the PNG to check the result, and keep the PDF/SVG for submission.

## Check it before you submit

```bash
figspec lint figure.yaml --journal nature
```

The command prints findings and exits `1` if any rule at or above the
`--fail-on` level fires (`error` by default).

## Point it at your own data

Replace the `series` block:

```yaml
series:
  - type: line
    data: data/results.csv
    x: step
    y: [baseline, ours]
    labels: [Baseline, Ours]
```

`data` paths are relative to the spec file. When `data` is present, `x` and `y`
are column names; without `data`, pass arrays inline:

```yaml
series:
  - type: line
    x: [1, 2, 3, 4]
    y: [[1.0, 0.8, 0.6, 0.5], [1.1, 0.85, 0.65, 0.52]]
    labels: [train, val]
```

## Change the target journal

```yaml
figure:
  journal: ieee
  layout: double
```

List what is available:

```bash
figspec journals
```

## Multi-panel figures

```yaml
figure:
  journal: acm
  layout: double
  grid: [2, 2]

panels:
  - title: (a)
    axes:
      x: {label: Epoch}
      y: {label: Loss}
    series:
      - {type: line, data: data/loss.csv, x: epoch, y: [train, val], labels: [Train, Validation]}
  - title: (b)
    series:
      - {type: bar, data: data/bench.csv, x: model, y: accuracy, error: std}
  # ...
```

Panels are placed left-to-right, top-to-bottom; use `cell: [row, col]` to place
one explicitly. `share_x: true` on each panel links the x axes and hides inner
tick labels.

## Build from Python

```python
import figspec

outcome = figspec.render("figure.yaml", "out/", journal="nature")
print(outcome.report.to_text())
outcome.close()
```

## Use it in CI

```yaml
- run: pip install "git+https://github.com/sw176267788/FigSpec.git"
- run: figspec render figures/summary.yaml -o build --strict --fail-on warning
- run: figspec verify build/summary.figspec.json
```

`--strict` aborts before writing files when lint fails; `--format sarif` emits a
report GitHub code scanning can display.

## Next steps

- [Spec reference](spec-reference.md) for every option.
- [Recipes](recipes.md) for log axes, error bands, heatmaps and annotations.
- [Provenance](provenance.md) to understand the manifest.
