# Recipes

Copy-paste patterns for common figure problems. Every snippet is a complete
`series` or `panel` entry; drop it into a spec and render.

## Error band instead of error bars

```yaml
series:
  - type: line
    data: data/runs.csv
    x: step
    y: mean
    error: std
    error_kind: band
    label: Mean ± 1 s.d.
```

`error_kind: band` fills `y ± error`; the default `bar` draws capped error bars.

## Grouped bars

```yaml
series:
  - type: bar
    data: data/scores.csv
    x: dataset
    y: [baseline, ours]
    labels: [Baseline, Ours]
    width: 0.7
    params: {x_rotation: 20}
```

Each `y` column becomes one group inside the category.

## Dot plot instead of a truncated bar chart

```yaml
axes:
  y: {label: Top-1 accuracy (%), limits: [72, 84]}
series:
  - type: errorbar
    data: data/bench.csv
    x: model
    y: accuracy
    error: std
    markersize: 4
    params: {x_rotation: 32}
```

Position encodes the value, so the axis may start above zero without misleading
the reader — and `DA003` stays quiet.

## Log–log scaling law

```yaml
axes:
  x: {label: Parameters (M), scale: log}
  y: {label: Validation loss, scale: log}
series:
  - {type: scatter, data: data/scaling.csv, x: params, y: loss, label: Measured}
  - {type: line, data: data/scaling.csv, x: params, y: fit, label: Fit, linestyle: "--"}
```

Narrow log axes get plain decimal tick labels automatically.

## Heatmap with annotations and a labelled colour bar

```yaml
series:
  - type: heatmap
    cmap: cividis
    matrix:
      - [68.2, 72.4, 74.1]
      - [74.9, 79.2, 80.6]
    row_labels: ["d=6", "d=12"]
    col_labels: ["p=8", "p=16", "p=32"]
    annotate: true
    params:
      colorbar_label: Top-1 accuracy (%)
      x_rotation: 45
```

## Panel letters and shared axes

```yaml
figure:
  journal: acm
  layout: double
  grid: [1, 2]
panels:
  - title: (a)
    share_y: true
    axes: {y: {label: Loss}}
    series: [{type: line, data: data/a.csv, x: step, y: [train, val], labels: [Train, Val]}]
  - title: (b)
    share_y: true
    series: [{type: line, data: data/b.csv, x: step, y: [train, val], labels: [Train, Val]}]
```

The right panel reuses the left panel's y scale and hides its tick labels.

## Annotations with arrows

```yaml
annotations:
  - text: best checkpoint
    xy: [32, 0.41]
    xytext: [18, 0.6]
    arrow: true
  - text: "(a)"
    xy_axes: [0.01, 0.99]
    font_size: 7
```

Use `xy` for data coordinates, `xy_axes` for fractions of the axes box.

## Explicit colours for one series

```yaml
series:
  - type: line
    x: [1, 2, 3]
    y: [[1.0, 0.9, 0.8]]
    color: "#0072B2"
    marker: o
```

`colors: [...]` sets several at once; anything you leave out comes from the
palette.

## Reusing a style across many figures

`base.yaml`:

```yaml
version: 1
style:
  palette: tol-muted
  font_size: 7
axes:
  x: {label: Epoch}
```

`figure-a.yaml`:

```yaml
extends: base.yaml
series:
  - {type: line, data: data/a.csv, x: epoch, y: [train, val], labels: [Train, Val]}
```

Maps merge recursively; the child wins.

## Environment-specific paths

```yaml
series:
  - type: line
    data: ${DATA_DIR:-data}/runs.csv
    x: step
    y: [ours]
```

```bash
DATA_DIR=/scratch/run42 figspec render figure.yaml
```
