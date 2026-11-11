# Lint rules

`figspec lint` builds the figure, inspects the materialised artists and reports
findings with a stable code, a severity and a hint. Severities are `error`,
`warning` and `info`; `--fail-on` decides which ones fail a build, and
`--ignore` disables codes or globs (`--ignore 'CO*'`).

```bash
figspec lint figure.yaml --journal nature
figspec lint figure.yaml --format json
figspec lint figure.yaml --format sarif > figspec.sarif
figspec rules            # list every rule
```

## Typography

### FS001 — text below the minimum font size · `error`

Checks every text object after layout, including tick labels, legend entries,
colour-bar labels and annotations. The minimum comes from the preset (5 pt for
Nature, 6 pt for IEEE) or defaults to 5 pt.

Why: journals typeset at a fixed width; a 4 pt label is unreadable regardless of
how good it looks on a 4K monitor.

### FS002 — line thinner than the minimum stroke · `warning`

Flags lines below the preset's `min_width` (typically 0.25 pt).

Why: hairlines rasterise to grey or disappear when a figure is reduced.

### FS003 — figure off the journal column grid · `warning`

Compares the rendered width with the preset's width for the chosen layout and
flags deviations above 2%.

Why: printing a 5-inch figure in a 3.5-inch column rescales every font and
stroke, undoing the point sizes FS001 just checked.

### FS004 — figure taller than the page · `warning`

Flags heights above the preset's `max_height`.

Why: over-tall figures are shrunk on import, with the same consequence as above.

## Colour

### CO001 — insufficient contrast on the background · `warning`

Computes the WCAG 2.1 contrast ratio between each **thin** mark (line, marker,
error bar) and the background, flagging ratios below 3:1.

Why: pale yellow lines on white are a classic print failure. Fills are exempt
because large areas are readable at lower contrast.

### CO002 — colours collapse under colour-vision deficiency · `warning`

Simulates protanopia and deuteranopia with the Machado (2009) matrices, then
compares each pair of series colours with CIEDE2000. Pairs that are distinct
normally but fall below ΔE00 6 in simulation are reported.

Why: about 8% of men cannot separate red from green; a legend that relies on that
difference is unusable for them.

### CO003 — rainbow colormap · `warning`

Flags `jet`, `rainbow`, `hsv`, `nipy_spectral`, `gist_rainbow` and similar maps
on heatmaps.

Why: rainbow maps are not perceptually ordered and create phantom boundaries.

### CO004 — too many series colours · `info`

Warns when the number of distinct colours exceeds the preset's `max_colors`
(usually 8).

Why: readers cannot map more than about eight hues back to a legend.

## Structure and output

### ST001 — raster-only output · `warning`

Fires when no PDF, SVG or EPS is produced.

Why: typesetters need vector art to rescale and edit text.

### ST002 — raster DPI below requirement · `error`

Compares `figure.dpi` with the preset's `raster_dpi` (or 300).

### ST003 — labelled series without a legend · `warning`

Fires when two or more legend labels exist but no axes has a legend.

### ST004 — axis without a label · `info`

Single-panel figures only; heatmaps are exempt.

### ST005 — closed frame · `info`

All four spines visible. Most journals prefer open axes.

### ST006 — line series with fewer than two points · `warning`

Usually a data-selection bug rather than an intentional dot.

### ST007 — crowded categorical axis · `warning`

More than twelve category labels on one axis without rotation.

## Data

### DA001 — missing values · `info`

Counts NaNs in prepared data. They are legal (line plots show gaps) but often
indicate a failed join.

### DA002 — duplicate legend labels · `warning`

The legend keeps the first occurrence, so duplicates silently hide a series.

### DA003 — truncated bar axis · `warning`

A bar chart whose y limit does not include zero. Bar length encodes the value, so
cutting the axis exaggerates differences. Use a dot plot (`errorbar`) or start at
zero.

## Severity overrides

In Python:

```python
from figspec.lint import lint_result

report = lint_result(result, ignore=["CO*"], severity_overrides={"ST005": "warning"})
```

## SARIF

`--format sarif` emits SARIF 2.1.0 with rule metadata, so GitHub code scanning
and most IDEs can annotate pull requests:

```yaml
- run: figspec lint figures/*.yaml --format sarif > figspec.sarif
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: figspec.sarif
```
