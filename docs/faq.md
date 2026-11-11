# FAQ

### Is figspec a plotting library?

No. It is a build system and linter around matplotlib. You describe a figure,
figspec configures matplotlib, draws it, checks the result and records what went
in. Anything figspec cannot express yet is best done with plain matplotlib.

### Why YAML instead of Python?

Because figure definitions are reviewed, diffed and generated. A YAML spec can be
produced by a training script, reviewed in a pull request and rendered by CI
without executing arbitrary code. If a figure needs real logic, generate the
spec; the Python API is there for that.

### Can I keep my existing matplotlib scripts?

Yes. Export the data they produce to CSV, point a spec at it and let figspec own
the final, submission-facing rendering. The two can live in the same repository;
figspec only needs the data.

### Does it work in Jupyter?

```python
import figspec
outcome = figspec.render("figure.yaml", "out/", formats=("png",), dpi=200)
outcome.close()
```

Returned paths are ordinary files, so `IPython.display.Image` works too.

### Why does the same spec look different on another machine?

Usually fonts. A preset asks for Arial; if Arial is missing, matplotlib falls back
to the next family in the stack. Install the font, or set `style.font_family` to a
font you ship. The provenance manifest records the versions, not the font files.

### Can I use LaTeX for labels?

Set `style.use_tex: true`. That requires a working TeX installation and makes
builds slower; the default mathtext handles most cases without it.

### Is figspec on PyPI?

Not yet. Install from the repository until the first release is published:

```bash
pip install "git+https://github.com/sw176267788/FigSpec.git"
```

### How is it different from SciencePlots or DVC?

SciencePlots provides matplotlib style sheets: colours and fonts. DVC versions
data and pipeline outputs. figspec covers the layer in between — a validated
figure definition, journal constraints enforced as lint rules, deterministic
rendering and a per-figure manifest. They compose well: use SciencePlots' colour
taste inside a `figspec` spec if you like.

### Can it make tables too?

Not yet. LaTeX table export is on the roadmap; the panel and provenance machinery
will be reused.

### Does it support R or Julia?

No. figspec is Python-only. The manifest and SARIF outputs are language-agnostic,
so other tools can consume them.

### How do I add my journal?

Drop a YAML file in `src/figspec/journals/data/` following
[journals.md](journals.md), or pass `--journal-file my-journal.yaml` for a local
one without touching the package.
