# CLI reference

```
figspec [--no-color] [-V/--version] COMMAND [ARGS]
```

| Command | Purpose |
|---|---|
| `init` | Create a starter spec and dataset |
| `render` | Build PDF/SVG/PNG/EPS from a spec |
| `lint` | Check a figure without writing files |
| `verify` | Check a manifest and its outputs |
| `gallery` | Render many specs into a static HTML page |
| `journals` | List bundled presets |
| `palettes` | List colour palettes |
| `rules` | List lint rules |
| `doctor` | Report versions, backend and fonts |

## render

```bash
figspec render SPEC [-o DIR] [-f FORMAT ...] [-j NAME] [--journal-file FILE]
                    [--dpi N] [--stem NAME] [--strict] [--fail-on LEVEL]
                    [--ignore CODE ...] [--no-lint] [--no-manifest] [-q]
```

| Flag | Meaning |
|---|---|
| `-o, --out` | Output directory (default `out`) |
| `-f, --format` | Repeatable; overrides `figure.formats` |
| `-j, --journal` | Preset name, overrides `figure.journal` |
| `--journal-file` | Custom preset YAML |
| `--dpi` | Raster resolution override |
| `--stem` | Output file stem (defaults to the spec name) |
| `--strict` | Abort before writing when lint fails |
| `--fail-on` | `error` (default), `warning` or `none` |
| `--ignore` | Rule code or glob, repeatable |
| `--no-lint` | Skip linting |
| `--no-manifest` | Do not write the provenance manifest |
| `-q, --quiet` | Print nothing on success |

Exit codes: `0` success, `2` spec/data error, `3` render error, `4` strict lint
failure.

## lint

```bash
figspec lint SPEC [--format text|json|sarif] [-j NAME] [--ignore CODE ...]
                  [--fail-on LEVEL]
```

Returns `1` when a finding at or above the threshold exists, `0` otherwise.

## verify

```bash
figspec verify MANIFEST [--json]
```

Returns `1` on drift, `5` when the manifest cannot be read.

## init

```bash
figspec init [DIR] [--force] [--journal NAME]
```

Writes `figure.yaml` and `data/loss.csv`, skipping existing files unless
`--force` is given.

## gallery

```bash
figspec gallery SOURCES... [-o DIR] [-j NAME] [--dpi N] [--title TEXT]
```

Each source may be a directory of `*.yaml`/`*.yml`/`*.json` or individual specs.
The output directory receives `index.html` and `assets/*.png`; the page is
self-contained apart from those images and works from `file://`.

## Reference commands

```bash
figspec journals [--json]
figspec palettes [--json] [-n 6]
figspec rules [--json]
figspec doctor [--json]
```

`palettes` prints ANSI true-colour swatches when stdout is a terminal;
`--json` gives `{"palette": ["#...", ...]}`.

## Environment variables

| Variable | Effect |
|---|---|
| `NO_COLOR` | Disable ANSI colours, as per no-color.org |
| `SOURCE_DATE_EPOCH` | Pin the manifest timestamp |
| `FIGSPEC_*` | Available to `${...}` interpolation inside specs |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Lint findings reached the threshold, or manifest drift |
| `2` | Invalid spec, data or configuration (also CLI usage errors) |
| `3` | Render or export failure |
| `4` | `--strict` aborted the build |
| `5` | Manifest missing or unreadable |
| `130` | Interrupted |
