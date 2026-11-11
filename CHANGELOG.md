# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-11-11

First public release.

### Added

- Declarative YAML/JSON figure specifications with strict validation, helpful
  error paths and "did you mean" suggestions for unknown keys.
- Spec inheritance through `extends`, plus `${ENV}` / `${ENV:-default}`
  interpolation.
- Series types: `line`, `scatter`, `bar`, `box`, `errorbar`, `area`, `heatmap`.
- Data loading from CSV, TSV, JSON, `.npy` and `.npz`, with numeric/categorical
  column detection and content fingerprints.
- Eight journal presets: Nature, Science, Cell, IEEE, ACM, Elsevier, Springer and
  PLOS, plus custom presets through `--journal-file`.
- Colour-blind aware palettes (`okabe-ito`, `tol-bright`, `tol-muted`, `ibm`,
  `tableau`, `grayscale`, `dark`) and sequential colormaps.
- Linting (18 rules) for typography, WCAG contrast, CIEDE2000 colour separation
  under simulated dichromacy, DPI, output formats, legends, axis labels and
  truncated bar axes. Reports as text, JSON or SARIF 2.1.0.
- Deterministic PDF, SVG, PNG and EPS export: identical bytes across runs in the
  same environment.
- Provenance manifests recording spec, input and output hashes, tool versions and
  git state; `figspec verify` detects drift.
- Multi-panel figures with explicit or automatic grid placement and shared axes.
- CLI: `init`, `render`, `lint`, `verify`, `gallery`, `journals`, `palettes`,
  `rules`, `doctor`.
- Python API: `figspec.render`, `figspec.lint`, `figspec.verify` and the
  lower-level `build`/`export`/`lint_result`/`create_manifest` functions.
- Static HTML gallery generation for example suites and docs.
- 138 tests, GitHub Actions CI across three operating systems and three Python
  versions.

[0.1.0]: https://github.com/sw176267788/FigSpec/releases/tag/v0.1.0
