# Architecture

figspec is a compiler with four stages: **load → prepare → draw → verify**.

```
spec.yaml
   │  spec/loader.py      YAML/JSON, ${ENV}, extends
   ▼
Spec (frozen dataclasses, spec/schema.py)
   │  data/series.py      CSV/TSV/JSON/NPY → numpy, length & finiteness checks
   ▼
PreparedFigure
   │  render/theme.py     journal + style + defaults → ResolvedStyle
   │  render/figure.py    panels, axes, legends, annotations
   │  render/plots.py     one function per series type
   ▼
RenderResult ──► lint/engine.py ──► LintReport ──► text/json/sarif
   │
   └──► render/figure.py::export ──► PDF/SVG/PNG/EPS
                                      │
                                      └──► provenance/manifest.py
```

## Module map

| Module | Responsibility |
|---|---|
| `spec/schema.py` | Frozen dataclasses, key validation, helpful errors |
| `spec/loader.py` | Parsing, env interpolation, `extends` merging |
| `data/table.py` | Format dispatch, column typing, fingerprints |
| `data/series.py` | Series → arrays; heatmap matrices; error columns |
| `journals/presets.py` | Loading and validating presets |
| `palette/color.py` | sRGB→Lab, CIEDE2000, WCAG contrast |
| `palette/cvd.py` | Machado dichromacy simulation |
| `palette/palettes.py` | Curated palettes and colormap sampling |
| `render/theme.py` | Defaults ← journal ← spec, then rcParams |
| `render/plots.py` | `draw_line`, `draw_bar`, … behind one registry |
| `render/figure.py` | Grid layout, axes config, export, `build()` |
| `lint/context.py` | Snapshot of texts, lines and series colours |
| `lint/rules.py` | 18 rules registered by decorator |
| `lint/engine.py` | Runs rules, applies ignores and overrides |
| `lint/report.py` | Text, JSON and SARIF renderers |
| `provenance/manifest.py` | Builds and writes the manifest |
| `provenance/verify.py` | Recomputes hashes, compares environment |
| `api.py` | `render`, `lint`, `verify` one-call helpers |
| `cli.py` | click commands, exit-code mapping |
| `gallery.py` | Static HTML gallery |

## Key design decisions

**Frozen dataclasses for the spec.** Everything downstream reads the same
immutable object, so the renderer and the linter cannot disagree about a value.
Validation happens once, at the boundary, with paths like `series[0].y`.

**The linter inspects the built figure, not the spec.** Font sizes are only known
after layout; tick labels are created by matplotlib; the actual line width may be
an rcParam. Running rules on the real artists is slower but correct.

**Constrained layout by default.** Figures keep the exact journal width (unlike
`bbox_inches="tight"`, which would crop and rescale). `figure.margins` switches
to manual `subplots_adjust` for people who need pixel control.

**Determinism is a build property, not a promise about matplotlib.** The
renderer pins hash salts, disables path simplification and strips timestamps at
export time. If the environment changes, the manifest's recorded versions make
that visible instead of silent.

**No global state.** `build()` uses `matplotlib.rc_context`, creates a bare
`Figure` and returns it. Nothing touches `pyplot` state, so parallel builds and
notebooks are safe. (`pyplot` is only imported to close figures.)

## Extending

### A new series type

```python
# src/figspec/render/plots.py
@register("violin")
def draw_violin(state, prepared, spec):
    ...
```

Add the identifier to `SERIES_KINDS` in `spec/schema.py`, register the drawer in
`DRAWERS`, add a test to `tests/test_render.py` and a row to the type table in
`docs/spec-reference.md`.

### A new lint rule

```python
@rule("ST008", "Short title", "warning", "Why it matters.")
def check_something(ctx: LintContext) -> list[Finding]:
    if not _problem(ctx):
        return []
    return [_finding("ST008", "message with numbers", hint="how to fix", detail=...)]
```

The decorator registers it; the CLI, JSON and SARIF outputs pick it up
automatically.

### A new journal preset

Add a YAML file under `src/figspec/journals/data/`. No code required. See
[journals.md](journals.md).

## Testing strategy

- **Unit tests** for colour math (CIEDE2000 verified against Sharma's reference
  pairs), parsing, data typing and validation messages.
- **Render tests** parametrised over every series type.
- **Determinism tests** that render twice and compare bytes for PDF, SVG, PNG and
  EPS.
- **CLI tests** that drive `main(argv)` and assert exit codes and files.
- **Provenance tests** that tamper with inputs and outputs to prove drift is
  detected.

The suite runs without network access and completes in under ten seconds.
