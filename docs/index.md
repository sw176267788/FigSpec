# figspec

**Figures as code: declarative, journal-compliant, reproducible.**

figspec turns a YAML description into publication-ready figures and tells you
when a figure would fail a journal's or a reader's expectations.

```bash
pip install "git+https://github.com/sw176267788/FigSpec.git"
figspec init my-paper
figspec render my-paper/figure.yaml -o figures
```

<div align="center">
<img src="assets/hero.png" alt="Six figures rendered by figspec" width="720">
</div>

## What it does

| Step | Command | Result |
|---|---|---|
| Describe | `figure.yaml` | A reviewable, diffable figure definition |
| Build | `figspec render` | PDF, SVG, PNG, EPS at the journal's exact width |
| Check | `figspec lint` | Typography, colour and data-integrity findings |
| Prove | `figspec verify` | Confirms inputs and outputs still match the manifest |

## Where to go next

- [Quickstart](quickstart.md) — from install to a compiled figure in two minutes.
- [Spec reference](spec-reference.md) — every key, every default.
- [Journal presets](journals.md) — what each preset enforces and how to add one.
- [Lint rules](lint-rules.md) — the 18 checks and why they exist.
- [Provenance](provenance.md) — what a manifest records and how verification works.
- [CLI](cli.md) and [architecture](architecture.md) — for daily use and for hacking.
- [Recipes](recipes.md) — common figure patterns, copy-paste ready.

## Design principles

1. **The figure is a build artefact.** Inputs are hashed, the build is
   deterministic, and the result is verifiable months later.
2. **Constraints belong in the tool.** Column widths and minimum font sizes are
   data, not folklore.
3. **Check what a reader would check.** Legibility at print size, colour
   separation under dichromacy, and charts that do not mislead.
4. **Stay close to matplotlib.** figspec does not hide the engine; it gives it a
   schema, defaults and a build system.
