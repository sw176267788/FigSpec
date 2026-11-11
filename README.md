<div align="center">

<img src="docs/assets/hero.png" alt="Six publication figures rendered from YAML specs by figspec" width="780">

# figspec

**Figures as code: declarative, journal-compliant, reproducible.**

[![CI](https://github.com/sw176267788/FigSpec/actions/workflows/ci.yml/badge.svg)](https://github.com/sw176267788/FigSpec/actions/workflows/ci.yml)
[![Docs](https://github.com/sw176267788/FigSpec/actions/workflows/docs.yml/badge.svg)](https://sw176267788.github.io/FigSpec/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-3776ab.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f.svg)](LICENSE)

[English](README.md) · [简体中文](README.zh-CN.md)

</div>

figspec compiles a small YAML file into submission-ready figures. It resolves the
target journal's column width, fonts, stroke weights and DPI, renders
PDF/SVG/PNG, checks the result for legibility and colour accessibility, and
records a manifest so the build can be verified later.

```bash
figspec render figure.yaml -o figures     # → figures/figure.{pdf,svg,png}
figspec lint   figure.yaml --journal nature
figspec verify figures/figure.figspec.json
```

## Features

- **Declarative specs.** Size, axes, series, legends, annotations and panel
  layout live in one YAML/JSON file — diffable and reviewable.
- **8 journal presets.** Nature, Science, Cell, IEEE, ACM, Elsevier, Springer and
  PLOS, plus `--journal-file` for your own.
- **18 lint rules.** Minimum type size at final print size, stroke weights, WCAG
  contrast, colour-vision separation, DPI, legends, axis labels, rainbow
  colormaps and truncated bar axes.
- **Reproducible output.** PDF, SVG, PNG and EPS are byte-identical across runs in
  the same environment.
- **Provenance manifests.** Input and output hashes, versions and git state
  recorded on every build; `figspec verify` detects drift.
- **Multi-panel figures.** Explicit or automatic grids, shared axes, `(a)`–`(d)`
  labels, per-panel legends.
- **CI-ready.** `--strict`, `--fail-on`, JSON and SARIF 2.1.0 output.
- **Library first.** A typed Python API behind a thin CLI.

## Installation

figspec is not on PyPI yet. Install from the repository:

```bash
pip install "git+https://github.com/sw176267788/FigSpec.git"
```

or work on a clone:

```bash
git clone https://github.com/sw176267788/FigSpec.git
cd FigSpec
pip install -e ".[dev]"
pytest -q
```

Requires **Python 3.10+** and matplotlib 3.7+. Runtime dependencies are
matplotlib, numpy, PyYAML and click.

## Quick start

```bash
figspec init my-paper                     # figure.yaml + data/loss.csv
figspec render my-paper/figure.yaml -o figures
figspec lint   my-paper/figure.yaml --journal nature
```

```
  [ok] figure.pdf                23.1 KiB
  [ok] figure.svg                28.6 KiB
  [ok] figure.png               135.6 KiB
rendered 3 file(s) in 0.72s
lint: clean
provenance: figures/figure.figspec.json
```

## The spec format

```yaml
version: 1

meta:
  title: Training and validation loss

figure:
  journal: nature        # column grid, fonts, DPI and minimum sizes come from here
  layout: single         # single | 1.5 | double | custom
  formats: [pdf, svg, png]

style:
  palette: okabe-ito     # colour-blind safe; first five colours clear 3:1
  grid: true

axes:
  x: {label: Epoch, limits: [0, 41]}
  y: {label: Cross-entropy loss}

series:
  - type: line
    data: data/loss.csv
    x: epoch
    y: [train, val]
    labels: [Train, Validation]
    marker: o
    markersize: 2.2
```

Seven series types: `line`, `scatter`, `bar`, `box`, `errorbar`, `area` and
`heatmap`. Data comes from CSV, TSV, JSON, `.npy`/`.npz`, or inline arrays.
Specs can share a base through `extends` and read `${ENV}` variables. Every key
and default is documented in
[docs/spec-reference.md](docs/spec-reference.md).

## Journal presets

| Preset | Single column | Double column | Font (min) | Raster DPI |
|---|---|---|---|---|
| `nature` | 3.504 in | 7.205 in | 7 (5) pt | 600 |
| `science` | 2.165 in | 7.244 in | 6 (5) pt | 300 |
| `cell` | 3.346 in | 6.850 in | 6 (5) pt | 300 |
| `ieee` | 3.500 in | 7.160 in | 8 (6) pt | 300 |
| `acm` | 3.330 in | 7.000 in | 8 (6) pt | 300 |
| `elsevier` | 3.543 in | 7.480 in | 8 (6) pt | 300 |
| `springer` | 3.307 in | 6.850 in | 8 (6) pt | 300 |
| `plos` | 3.270 in | 6.810 in | 8 (6) pt | 300 |

```bash
figspec journals          # table
figspec journals --json   # machine readable, with source URLs
```

Adding a preset is one YAML file; see [docs/journals.md](docs/journals.md).

## Linting

`figspec lint` builds the figure, inspects the materialised artists and reports
findings with stable codes:

```
figure.yaml: 1 error(s), 1 warning(s), 0 note(s)
  ERROR   FS001 2 text elements render at 4.0 pt, below the 5.0 pt minimum
          hint: raise font_size, shorten tick labels, or drop the label 'validation split'
  WARNING DA003 panel 0 bars start at 50 instead of zero
          hint: set the y limit to 0, or switch the series to 'errorbar'
```

| Area | Codes | Examples |
|---|---|---|
| Typography | `FS001`–`FS004` | type smaller than the journal minimum, hairlines, width off the column grid |
| Colour | `CO001`–`CO004` | contrast under 3:1, pairs that collapse under dichromacy, rainbow maps |
| Structure | `ST001`–`ST007` | raster-only output, DPI too low, missing legend or axis labels |
| Data | `DA001`–`DA003` | missing values, duplicate labels, truncated bar axes |

Reports come as text, JSON or SARIF 2.1.0. Each rule is explained in
[docs/lint-rules.md](docs/lint-rules.md).

## Reproducible builds

Every build writes `<stem>.figspec.json` next to the outputs, recording the spec
hash, every input file's SHA-256, output hashes and DPI, tool versions and the
git commit:

```
$ figspec verify figures/figure.figspec.json
verifying figures/figure.figspec.json
  OK   schema: figspec/provenance/v1
  OK   spec: figure.yaml matches
  OK   input loss.csv: loss.csv matches
  OK   output figure.pdf: figure.pdf matches
  OK   environment: tool versions match
```

Rendering is deterministic for PDF, SVG, PNG and EPS in the same environment, so
a rebuild either matches or tells you exactly what moved. See
[docs/provenance.md](docs/provenance.md).

## CLI

```
figspec init [DIR]                 scaffold a spec and sample data
figspec render SPEC [-o DIR]       build PDF/SVG/PNG/EPS
figspec lint SPEC                  compliance and accessibility checks
figspec verify MANIFEST            detect drift against a manifest
figspec gallery SOURCES [-o DIR]   render specs into an HTML gallery
figspec journals                   list journal presets
figspec palettes                   list colour palettes
figspec rules                      list lint rules
figspec doctor                     environment report
```

Full reference, including exit codes: [docs/cli.md](docs/cli.md).

## Python API

```python
import figspec

outcome = figspec.render("figure.yaml", "out/", journal="nature", strict=True)
print(outcome.report.to_text())
for output in outcome.outputs:
    print(output.path, output.sha256[:12])
outcome.close()
```

Lower-level entry points: `figspec.load_spec`, `figspec.render.build`,
`figspec.render.export`, `figspec.lint.lint_result`,
`figspec.provenance.create_manifest`.

## Documentation

| Page | Contents |
|---|---|
| [Quickstart](docs/quickstart.md) | install to first figure |
| [Gallery](docs/gallery.md) | six complete figures with their specs |
| [Spec reference](docs/spec-reference.md) | every key and default |
| [Journal presets](docs/journals.md) | what each preset enforces |
| [Lint rules](docs/lint-rules.md) | the 18 checks and why they exist |
| [Provenance](docs/provenance.md) | manifest format and verification |
| [CLI](docs/cli.md) | commands, flags and exit codes |
| [Recipes](docs/recipes.md) | common figure patterns |
| [FAQ](docs/faq.md) | comparisons, fonts, notebooks |

## License

MIT — see [LICENSE](LICENSE).
