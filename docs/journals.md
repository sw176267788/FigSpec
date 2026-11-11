# Journal presets

A preset bundles the numbers a journal actually enforces: column widths, font
sizes, minimum stroke weights, raster resolution and preferred formats. Presets
are plain YAML under `src/figspec/journals/data/`, so adding one is a data
change, not a code change.

## Bundled presets

| Preset | Publisher | Single (in) | Double (in) | Font (min) | Raster DPI |
|---|---|---|---|---|---|
| `nature` | Springer Nature | 3.504 | 7.205 | 7 (5) | 600 |
| `science` | AAAS | 2.165 | 7.244 | 6 (5) | 300 |
| `cell` | Cell Press | 3.346 | 6.850 | 6 (5) | 300 |
| `ieee` | IEEE | 3.500 | 7.160 | 8 (6) | 300 |
| `acm` | ACM | 3.330 | 7.000 | 8 (6) | 300 |
| `elsevier` | Elsevier | 3.543 | 7.480 | 8 (6) | 300 |
| `springer` | Springer | 3.307 | 6.850 | 8 (6) | 300 |
| `plos` | PLOS | 3.270 | 6.810 | 8 (6) | 300 |

Each preset also records the preferred palette, maximum sensible number of
series colours, the submission formats and a source URL. Inspect them with:

```bash
figspec journals
figspec journals --json
```

## How a preset is applied

1. `figure.size` wins outright.
2. Otherwise `journal.width_for(layout)` supplies the width; `aspect` or
   `height` supplies the height (default aspect `0.62`).
3. Fonts, line weights and DPI come from the preset unless `style` or `figure`
   overrides them.
4. The linter compares the result against the same preset — width deviation,
   minimum font size, line weight and raster DPI.

Without a preset, figspec falls back to generic defaults: 3.5 in single column,
7 pt text, 5 pt minimum, 300 dpi.

## Using a preset

```bash
figspec render figure.yaml --journal ieee
figspec lint figure.yaml --journal ieee
```

or pin it in the spec (recommended, so the build does not depend on a flag):

```yaml
figure:
  journal: ieee
  layout: double
```

A `--journal` flag overrides the spec; `--journal-file` replaces it with a custom
preset.

## Custom presets

```yaml
# my-journal.yaml
name: my-journal
display_name: Journal of Reproducible Figures
publisher: Example Society
column_widths:
  single: 3.4
  1.5: 5.0
  double: 7.0
max_height: 9.0
font:
  family: [Arial, DejaVu Sans]
  size: 8
  min_size: 6
  label_size: 9
line:
  width: 0.6
  min_width: 0.25
  marker_size: 3
dpi:
  raster: 300
  lineart: 600
formats: [pdf, svg]
preferred_palette: okabe-ito
max_colors: 8
notes: >
  Free text shown by `figspec journals --json`.
source: https://example.org/author-guide
```

```bash
figspec render figure.yaml --journal-file my-journal.yaml
```

Required keys are `name`, `display_name`, `column_widths` (must define `single`
and `double`) and `font`. Everything else has a default.

## Adding a preset upstream

1. Drop a YAML file in `src/figspec/journals/data/`.
2. Add a row to the table above.
3. Run `pytest tests/test_journals.py` — every bundled preset is validated.

Presets are intentionally conservative. When a journal publishes a range (for
example 300–600 dpi), figspec records the stricter value so that a passing build
is safe everywhere.
