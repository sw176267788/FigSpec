# Spec reference

A spec is a YAML (or JSON) mapping. Unknown keys are rejected with a
"did you mean" hint rather than silently ignored, because a typo in a spec
usually means a figure renders with the wrong settings and nobody notices until
review.

```yaml
version: 1
extends: base.yaml        # optional, deep-merged first
meta:   { ... }
figure: { ... }
style:  { ... }
axes:   { x: {...}, y: {...} }
series: [ ... ]
```

Multi-panel figures replace `axes`/`series` with `panels: [ ... ]`. Supplying
both is an error.

## Top level

| Key | Type | Default | Meaning |
|---|---|---|---|
| `version` | int | `1` | Spec schema version |
| `extends` | str \| list | — | Parent spec(s) merged underneath this one |
| `meta` | mapping | `{}` | Title/description used by galleries and docs |
| `figure` | mapping | `{}` | Canvas, journal, formats |
| `style` | mapping | `{}` | Typography, palette, spines |
| `axes` | mapping | `{}` | Shorthand for the single panel's axes |
| `series` | list | — | Shorthand for the single panel's series |
| `panels` | list | — | Multi-panel layout |
| `legend` | mapping | `{}` | Default legend for every panel |
| `annotations` | list | `[]` | Default annotations for the single panel |
| `share_x` / `share_y` | bool | `false` | Shorthand sharing flags for a single panel |

`meta` accepts `title`, `description`, `caption`, `tags` (list) and `author`.

## figure

| Key | Type | Default | Meaning |
|---|---|---|---|
| `journal` | str | — | Preset name: `nature`, `science`, `cell`, `ieee`, `acm`, `elsevier`, `springer`, `plos` |
| `layout` | str | `single` | `single`, `1.5`, `double` or `custom` |
| `size` | `[w, h]` | — | Explicit size in inches; overrides the preset width |
| `height` | float | — | Height in inches when `size` is not given |
| `aspect` | float | `0.62` | Height = width × aspect |
| `dpi` | int | preset or `300` | Raster resolution for PNG/JPG/TIFF |
| `formats` | list | preset or `[pdf, svg, png]` | Any of `pdf`, `svg`, `png`, `eps`, `jpg`, `tif`, `ps` |
| `transparent` | bool | `false` | Transparent background in raster output |
| `background` | colour | `white` | Figure and axes background |
| `pad` | float | `0.02` | Padding (inches) for constrained layout |
| `margins` | mapping | — | `left`/`right`/`bottom`/`top`; **disables** constrained layout |
| `grid` | `[rows, cols]` | inferred | Panel grid |

`height` and `aspect` are mutually exclusive. `layout: custom` requires `size`.

Column widths, fallback sizes and DPI come from the preset; see
[journals.md](journals.md).

## style

| Key | Type | Default | Meaning |
|---|---|---|---|
| `font_family` | str \| list | preset | Font stack, e.g. `[Arial, DejaVu Sans]` |
| `font_size` | float | preset (`7`) | Base size in points; everything else is derived |
| `palette` | str | preset preferred, else `okabe-ito` | Qualitative palette or colormap name |
| `grid` | bool | `false` | Draw grid lines |
| `spines` | list | `[left, bottom]` | Which of `left`, `right`, `top`, `bottom` are visible |
| `legend` | mapping | see below | Default legend configuration |
| `axes_linewidth` | float | preset line width (`0.8`) | Spine and tick width |
| `tick_direction` | str | `out` | `in`, `out` or `inout` |
| `tick_length` | float | `3` | Major tick length in points |
| `error_band_alpha` | float | `0.25` | Fill opacity for `error_kind: band` |
| `use_tex` | bool | `false` | Render text through LaTeX (requires a TeX install) |

Derived sizes: labels = `font_size + 0.5` (or the preset's value), ticks =
`font_size - 0.5` but never below the preset minimum, legend = same as ticks,
panel titles = `font_size + 1`.

### legend

| Key | Type | Default | Meaning |
|---|---|---|---|
| `show` | bool | `true` | Render the legend at all |
| `location` | str | `best` | `best`, `upper right`, `upper left`, `lower left`, `lower right`, `center left`, `center right`, `lower center`, `upper center`, `center`, `outside right`, `outside bottom` |
| `frame` | bool | `false` | Draw a frame around the legend |
| `font_size` | float | derived | Legend text size |
| `columns` | int | `1` | Number of legend columns |
| `title` | str | — | Legend title |

## axes

`axes.x` and `axes.y` accept the same keys.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `label` | str | — | Axis label; omit to leave it empty |
| `scale` | str | `linear` | `linear`, `log`, `symlog`, `logit` |
| `limits` | `[lo, hi]` | auto | Axis limits |
| `ticks` | list | auto | Explicit tick positions |
| `tick_format` | str | auto | `"%.1f"`-style format, `sci`, or `thousands` |
| `minor_ticks` | bool | `false` | Show minor ticks |
| `grid` | bool | style default | Per-axis grid override |
| `hide` | bool | `false` | Hide the axis entirely (hide both to remove the frame) |
| `invert` | bool | `false` | Reverse the direction |
| `label_size` | float | derived | Axis label size |
| `tick_size` | float | derived | Tick label size |

Narrow log axes (span under two decades) are labelled with plain decimals rather
than `3.2 x 10^0`.

## series

Every entry needs a `type`. Common keys:

| Key | Type | Default | Meaning |
|---|---|---|---|
| `type` | str | — | `line`, `scatter`, `bar`, `box`, `errorbar`, `area`, `heatmap` |
| `data` | str | — | Path to CSV/TSV/JSON/NPY/NPZ, relative to the spec |
| `x` | str \| list | row index | Column name (with `data`) or inline values |
| `y` | str \| list | — | Column name(s) or inline arrays |
| `error` | str \| list | — | Error column or inline errors |
| `error_kind` | str | `bar` | `bar` (error bars) or `band` (shaded ± error) |
| `label` | str | — | Legend label for a single series |
| `labels` | list | — | Legend labels, one per data column |
| `color` / `colors` | str \| list | palette | Explicit colour(s) |
| `linestyle` | str | cycle | matplotlib linestyle |
| `marker` | str | — | matplotlib marker, e.g. `o`, `s`, `^` |
| `linewidth` | float | style | Line width in points |
| `markersize` | float | style | Marker size in points |
| `alpha` | float | `1` | Opacity |
| `zorder` | float | `2` | Drawing order |
| `width` | float | type default | Bar width / box width |
| `cmap` | str | — | Heatmap colormap |
| `vmin` / `vmax` | float | data range | Colour limits |
| `annotate` | bool | `false` | Print values inside heatmap cells |
| `matrix` | list[list] | — | Inline heatmap matrix |
| `row_labels` / `col_labels` | list | — | Heatmap tick labels |
| `params` | mapping | `{}` | Type-specific options, see below |

### Data resolution

- With `data`, `x` and `y` **must** be column names. Mixing an inline `x` with a
  data file is an error.
- Without `data`, pass arrays inline. Numeric lists become floats; string lists
  become categories.
- If `x` is omitted, the row index is used.
- Columns that parse entirely as numbers become floats; anything else stays
  categorical.
- `NaN` is permitted (it renders as a gap in line plots), `inf` is rejected.
  Non-finite input is reported with the row number.
- Column lengths must agree; mismatches name both lengths.

### Type-specific notes

**line** — multiple `y` columns become multiple lines in palette order. `error`
adds error bars, or a shaded band when `error_kind: band`.

**scatter** — marker area derives from `markersize`; supports categorical `x`.

**bar** — category labels are taken from a categorical `x`; multiple `y` columns
become grouped bars. `params.x_rotation` rotates the labels.

**box** — with a categorical `x` and one `y` column, each category is a box.
With several `y` columns the columns are the groups. Whiskers are 1.5×IQR,
outliers are hidden.

**errorbar** — markers plus symmetric error bars; the series reads as a dot plot
that does not imply a zero baseline.

**area** — filled area between the line and `params.baseline` (default `0`).

**heatmap** — needs `matrix` or a data file with a matrix. Default colormap is
the palette if it is sequential, otherwise `viridis`. `params.colorbar_label`
labels the colour bar, `params.x_rotation` rotates the column labels.

## panels

| Key | Type | Default | Meaning |
|---|---|---|---|
| `axes` | mapping | `{}` | Per-panel axes configuration |
| `series` | list | — | At least one series |
| `title` | str | — | Bold, left-aligned panel label such as `(a)` |
| `cell` | `[row, col]` | auto | Explicit grid cell (0-based) |
| `legend` | mapping | — | Per-panel legend override |
| `annotations` | list | `[]` | Text and arrows |
| `share_x` / `share_y` | bool | `false` | Share and sync axes with the previous panel |

Panels without `cell` fill the remaining cells in row-major order.

## annotations

| Key | Type | Default | Meaning |
|---|---|---|---|
| `text` | str | — | Required |
| `xy` | `[x, y]` | — | Data coordinates for the anchor |
| `xy_axes` | `[x, y]` | — | Axes-fraction coordinates (0–1) |
| `xytext` | `[x, y]` | same as `xy` | Where the text sits |
| `arrow` | bool | `false` | Draw an arrow from text to `xy` |
| `font_size` | float | tick size | Text size |
| `color` | colour | `#222222` | Text colour |
| `ha` / `va` | str | `left` / `baseline` | Horizontal/vertical alignment |
| `rotation` | float | `0` | Rotation in degrees |

Use either `xy` or `xy_axes`, not both.

## Colours and palettes

Colours accept hex (`#0072B2`), short hex (`#07b`) or any CSS colour name
matplotlib understands.

Qualitative palettes: `okabe-ito`, `tol-bright`, `tol-muted`, `ibm`, `tableau`,
`grayscale`, `dark`. Sequential names: `viridis`, `cividis`, `magma`, `inferno`,
`plasma`, `Greys`, `Blues`, `Reds`, `YlGnBu`.

When a figure has more series than palette entries, colours cycle and line styles
switch so the series stay separable.

## Inheritance and environment

`extends` merges a parent spec beneath the current one (maps merge recursively,
lists replace). Chains are followed and cycles are reported.

`${VAR}` and `${VAR:-default}` are substituted in every string, which keeps data
paths and labels out of version control:

```yaml
figure:
  formats: ${FIGSPEC_FORMATS:-pdf,svg}
series:
  - type: line
    data: ${DATA_DIR}/runs.csv
```

A missing variable without a default is an error naming the variable and file.

## Validation

Errors carry a path such as `series[0].y` plus a hint:

```
figure.size: expected exactly 2 numbers, got 1
  hint: ...
series[0].y: series needs 'y' values
panels[1].series[0].data: data file not found
```

Exit codes: `2` for spec/data/config errors, `3` for render errors, `4` for
strict lint failures, `5` for provenance drift.
