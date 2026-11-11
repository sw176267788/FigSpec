# Contributing

Thanks for helping! The full guide lives in [docs/contributing.md](docs/contributing.md);
this page lists the rules that apply to every change.

## Quick start

```bash
git clone https://github.com/sw176267788/FigSpec
cd figspec
pip install -e ".[dev]"
pytest -q
```

## Ground rules

- Be kind. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- One logical change per pull request.
- New behaviour needs a test; bug fixes need a regression test.
- `pytest`, `ruff check` and `mypy` must pass.
- User-facing changes need docs and a CHANGELOG entry.
- Security issues go to the process in [SECURITY.md](SECURITY.md), not the issue
  tracker.

## Good first issues

- **Journal preset** — one YAML file in `src/figspec/journals/data/`.
- **Lint rule** — one decorated function in `src/figspec/lint/rules.py`.
- **Plot type** — one function in `src/figspec/render/plots.py`.
- **Docs** — a recipe in `docs/recipes.md` or a clearer error message.

Each of these is designed to touch one file plus one test. If an issue looks
bigger than that, say so in the thread and we will split it.

## Commit messages

```
feat(lint): flag truncated bar axes
fix(render): keep shared axes labels on the outer panel
docs(journals): add the PLOS preset
test(provenance): cover tampered outputs
```

## Developer certificate

By contributing you agree that your contribution is licensed under the project's
MIT licence and that you have the right to submit it.
