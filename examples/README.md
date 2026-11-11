# Examples

Six figures covering the plot types and layout features figspec supports. All of
them are lint-clean against their target journal presets.

| File | Shows | Preset |
|---|---|---|
| `01-learning-curves.yaml` | two-series line plot, legend, limits | Nature, single |
| `02-benchmark-accuracy.yaml` | dot plot with error bars, rotated categories | IEEE, single |
| `03-ablation-heatmap.yaml` | annotated heatmap with a labelled colour bar | Cell, single |
| `04-scaling-law.yaml` | log–log axes, scatter plus fitted line | Science, 1.5 |
| `05-latency-box.yaml` | box plots on a log axis | Cell, single |
| `06-multi-panel.yaml` | 2×2 panels, shared styling, panel letters | ACM, double |

Data lives in `examples/data/` and is regenerated deterministically by
`scripts/make_example_data.py`.

## Render everything

```bash
figspec gallery examples -o site
open site/index.html        # Windows: start site/index.html
```

Or one at a time:

```bash
figspec render examples/01-learning-curves.yaml -o build/examples
figspec lint   examples/01-learning-curves.yaml
```

From the repository root without installing:

```bash
PYTHONPATH=src python -m figspec render examples/01-learning-curves.yaml -o build/examples
```

## What each example demonstrates

**01-learning-curves** — the default path: a CSV with two numeric columns, a
legend, a marker, and an axis limit that leaves room for the annotation.

**02-benchmark-accuracy** — a dot plot rather than a bar chart, because the axis
starts at 72% and bar length would exaggerate the differences. `DA003` would
flag the bar-chart version.

**03-ablation-heatmap** — an inline matrix, categorical labels on both axes,
value annotations with automatic text contrast, and a colour bar with a unit.

**04-scaling-law** — both axes on log scales, a scatter series without lines and
a power-law fit drawn as a dashed line; narrow log axes get plain tick labels.

**05-latency-box** — a tidy long-format CSV (`method,latency_ms`), a log y axis
and a legend suppressed in favour of the category labels.

**06-multi-panel** — an explicit 2×2 grid, panel letters, per-panel legends and a
colour bar inside one cell.
