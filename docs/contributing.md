# Contributing to figspec

Thanks for considering a contribution. This page is the practical guide; the
repository-wide rules are in [CONTRIBUTING.md](https://github.com/figspec/figspec/blob/main/CONTRIBUTING.md).

## Set up

```bash
git clone https://github.com/figspec/figspec
cd figspec
python -m venv .venv
# Windows: .venv\Scripts\activate    Unix: source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

`pytest` should finish in about ten seconds. If it does not, something is wrong
with the environment, not with you.

Useful commands:

```bash
pytest -q                       # whole suite
pytest tests/test_lint.py -q    # one file
pytest -k determinism -q        # one topic
ruff check src tests            # lint the code
ruff format src tests           # format
mypy                            # type check
python scripts/build_assets.py  # regenerate docs images
```

## What to work on

Issues labelled `good first issue` are scoped to one file and one test. Three
typical shapes:

### Add a journal preset

One YAML file in `src/figspec/journals/data/`, one row in
[journals.md](journals.md), one test run. No Python required.

### Add a lint rule

One decorated function in `src/figspec/lint/rules.py` plus a test. Rules receive
a `LintContext` with the built figure, texts, lines and series colours.

### Add a plot type

One function in `src/figspec/render/plots.py`, registered in `DRAWERS`, plus the
name in `SERIES_KINDS` (`src/figspec/spec/schema.py`), a test and a docs row.

## Coding guidelines

- Python 3.10+, full type hints on public functions.
- Keep the runtime dependency set small: matplotlib, numpy, PyYAML, click. New
  dependencies need a discussion first.
- Every error message should say what was expected and how to fix it.
- No global state: use `rc_context`, create bare `Figure` objects, return them.
- Tests must not need network access.
- Public behaviour changes need a CHANGELOG entry.

## Error messages

Good errors are a feature. Compare:

```
y: bad value
```

with

```
series[0].y: expected a column name, a list of numbers or a list of lists, got dict
```

The second tells the user where the problem is and what shapes are legal. Use
`SpecError(message, path=..., hint=...)` and keep the path stable
(`panels[1].series[0].data`).

## Pull requests

1. One logical change per pull request.
2. Tests for new behaviour; a failing test first is ideal.
3. `pytest`, `ruff check` and `mypy` clean.
4. Update docs when you add or change a user-facing option.
5. Describe the user-visible effect in the PR body.

Commit messages follow conventional commits loosely:

```
feat(lint): flag truncated bar axes
fix(render): keep shared axes labels on the outer panel
docs(journals): add the PLOS preset
```

## Adding a test fixture

Prefer building specs with `load_spec_dict` and small fabricated data over adding
files to `tests/`. Golden files would make the suite sensitive to matplotlib
versions; assert on structure and properties instead.

## Release checklist

1. Bump `src/figspec/_version.py` and `pyproject.toml`.
2. Update `CHANGELOG.md`.
3. `pytest -q` and `python -m build`.
4. Tag `vX.Y.Z`, push, and let the release workflow publish.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](https://github.com/figspec/figspec/blob/main/CODE_OF_CONDUCT.md).
Be kind; assume good faith; critique the code, not the person.
