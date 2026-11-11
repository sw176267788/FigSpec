<div align="center">

<img src="docs/assets/hero.png" alt="Six figures rendered from YAML specs by figspec" width="760">

# figspec

**Figures as code: declarative, journal-compliant, reproducible.**

[![CI](https://github.com/figspec/figspec/actions/workflows/ci.yml/badge.svg)](https://github.com/figspec/figspec/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-figspec.github.io-1f6feb.svg)](docs/index.md)

</div>

---

figspec compiles a small YAML file into publication-ready figures. It knows how
wide a Nature single column is, how small a 5 pt label renders, and which colour
pairs disappear under deuteranopia — so you do not have to re-learn that for
every submission.

```bash
pip install figspec
figspec init my-paper && figspec render my-paper/figure.yaml -o figures
```

That produces `figures/figure.pdf`, `figure.svg`, `figure.png` — plus a
provenance manifest that lets anyone verify the figure later.

## Why

A figure is a build artefact, but most labs treat it as a file someone tweaked by
hand. The symptoms are familiar:

- every journal requires a different column width, font size and DPI, and the
  numbers live in a style guide nobody reads until revision;
- figures are rebuilt by re-running a notebook with different matplotlib
  defaults, so two runs of "the same" plot are not the same file;
- colour choices silently exclude colour-blind readers, or vanish in print;
- six months later nobody can tell which CSV produced which panel.

figspec addresses these as engineering problems: a schema, a compiler, a linter
and a manifest.

## Features

- **Declarative specs.** One YAML file describes size, axes, series, legends,
  annotations and panel layout. Diffable, reviewable, and easy to generate from
  a script.
- **Journal presets.** Eight bundled presets (Nature, Science, Cell, IEEE, ACM,
  Elsevier, Springer, PLOS) plus `--journal-file` for your own.
- **Compliance linting.** 18 rules check font sizes at final print size, line
  weights, colour contrast (WCAG 2.1), colour-vision-deficiency separation
  (CIEDE2000 on simulated dichromacy), DPI, legend and axis labelling, rainbow
  colormaps and truncated bar axes.
- **Reproducible output.** PDF, SVG, PNG and EPS are byte-identical across runs
  in the same environment; timestamps and random ids are stripped.
- **Provenance manifests.** Every build records input hashes, versions, spec
  hash, output hashes and git state. `figspec verify` detects drift.
- **Multi-panel figures.** Shared axes, letters `(a)`–`(d)`, per-panel legends.
- **CI-ready.** `figspec lint --format sarif` and `figspec render --strict` turn
  figure quality into a build gate.
- **Library first.** The CLI is a thin shell over a typed Python API.

## Install

```bash
pip install figspec
```

From source:

```bash
git clone https://github.com/figspec/figspec
cd figspec
pip install -e ".[dev]"
pytest
```

Requires Python 3.10+ and matplotlib 3.7+. No LaTeX, no browser, no network.

## Quickstart

```bash
figspec init my-paper          # figure.yaml + data/loss.csv
figspec render my-paper/figure.yaml -o figures
figspec lint  my-paper/figure.yaml --journal nature
```

`render` prints what it wrote, the lint summary and the manifest path:

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
  tags: [deep-learning, training]

figure:
  journal: nature        # column grid, fonts, DPI and min sizes come from here
  layout: single         # single | 1.5 | double | custom
  formats: [pdf, svg, png]

style:
  palette: okabe-ito     # colour-blind safe, first five colours clear 3:1
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

Series types: `line`, `scatter`, `bar`, `box`, `errorbar`, `area`, `heatmap`.
Data can come from CSV, TSV, JSON, `.npy`/`.npz`, or be written inline.

The full schema, including panels, annotations, error bands, log axes and
colour bars, is documented in [docs/spec-reference.md](docs/spec-reference.md).

## Linting

```bash
figspec lint figure.yaml --journal nature
```

```
figure.yaml: 1 error(s), 1 warning(s), 0 note(s)
  ERROR   FS001 2 text elements render at 4.0 pt, below the 5.0 pt minimum
          hint: raise font_size, shorten tick labels, or drop the label 'validation split'
  WARNING DA003 panel 0 bars start at 50 instead of zero
          hint: set the y limit to 0, or switch the series to 'errorbar'
```

| Code | Default | What it catches |
|---|---|---|
| `FS001` | error | text below the journal's minimum font size |
| `FS002` | warning | hairlines that disappear in print |
| `FS003` | warning | figure width off the journal column grid |
| `FS004` | warning | figure taller than the page allows |
| `CO001` | warning | line/marker colours under 3:1 contrast |
| `CO002` | warning | colour pairs that collapse under deuteranopia/protanopia |
| `CO003` | warning | rainbow colormaps for continuous data |
| `CO004` | info | more distinct colours than a legend can carry |
| `ST001` | warning | raster-only output |
| `ST002` | error | DPI below the journal requirement |
| `ST003` | warning | labelled series with no legend |
| `ST004` | info | axis without a label |
| `ST005` | info | closed frame instead of open axes |
| `ST006` | warning | a line series with fewer than two points |
| `ST007` | warning | more than twelve category labels on one axis |
| `DA001` | info | missing values that render as gaps |
| `DA002` | warning | duplicate legend labels |
| `DA003` | warning | truncated bar-chart axis |

`--format json` and `--format sarif` are available for tooling;
`--ignore 'CO*'` silences a family of rules for one run.

## Reproducibility

```bash
figspec render figure.yaml -o out
figspec verify out/figure.figspec.json
```

```
verifying out/figure.figspec.json
  OK   schema: figspec/provenance/v1
  OK   spec: figure.yaml matches
  OK   input loss.csv: loss.csv matches
  OK   output figure.pdf: figure.pdf matches
  OK   environment: tool versions match
```

The manifest records:

- the spec hash and file hash,
- every data file with size and SHA-256,
- output files with SHA-256 and raster DPI,
- Python, figspec, matplotlib, numpy and PyYAML versions,
- the git commit and whether the tree was dirty,
- the lint summary.

If any input, output or the spec changes, `verify` exits non-zero and names the
mismatch. Set `SOURCE_DATE_EPOCH` to pin the manifest timestamp.

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

`figspec render --help` documents every flag; the common ones are `--journal`,
`--format`, `--dpi`, `--strict`, `--ignore` and `--fail-on`.

## Python API

```python
import figspec

outcome = figspec.render("figure.yaml", "out/", journal="nature", strict=True)
print(outcome.report.to_text())
for output in outcome.outputs:
    print(output.path, output.sha256[:12])
outcome.close()
```

Lower-level pieces are public too: `figspec.load_spec`, `figspec.render.build`,
`figspec.render.export`, `figspec.lint.lint_result`,
`figspec.provenance.create_manifest`.

## How figspec compares

| | figspec | journal styles (e.g. SciencePlots) | Vega-Lite / ggplot | notebook + DVC |
|---|---|---|---|---|
| Declarative spec | ✅ | ❌ | ✅ | ❌ |
| Journal compliance checks | ✅ | ❌ | ❌ | ❌ |
| Colour-vision auditing | ✅ | ❌ | ❌ | ❌ |
| Byte-reproducible output | ✅ | ❌ | partial | ❌ |
| Provenance manifest | ✅ | ❌ | ❌ | ✅ (for data) |
| Publication PDF/SVG | ✅ | ✅ | partial | ✅ |

figspec is deliberately narrow: it produces figures for papers, not dashboards,
and it assumes matplotlib is the rendering engine rather than hiding it.

## Project status

figspec is at **v0.1.0**: the spec, renderer, linter, manifest and CLI are usable
and covered by 138 tests. The public API may still change in minor releases
until v1.0.

Roadmap: LaTeX table export, violin/contour types, a Jupyter cell magic, a
reusable GitHub Action, and a plugin hook for third-party lint rules and plot
types. See [CHANGELOG.md](CHANGELOG.md) and the open issues.

## Contributing

Contributions are welcome — the easiest first pull request is adding a journal
preset (one YAML file) or a lint rule (one function). See
[CONTRIBUTING.md](CONTRIBUTING.md) and [docs/contributing.md](docs/contributing.md).

```bash
pip install -e ".[dev]"
pytest -q
```

## Citation

If figspec helps your paper, please cite it via [CITATION.cff](CITATION.cff).

## License

MIT — see [LICENSE](LICENSE).
