# Provenance

Every `figspec render` (unless `--no-manifest`) writes `<stem>.figspec.json`
next to the outputs. The file answers one question: *would this figure still be
the same if I rebuilt it today?*

```json
{
  "schema": "figspec/provenance/v1",
  "generated_at": "2026-11-11T12:00:00Z",
  "spec": {
    "hash": "9c1f...",
    "path": "../figure.yaml",
    "file_sha256": "4d2a..."
  },
  "environment": {
    "figspec": "0.1.0",
    "python": "3.11.5",
    "platform": "Windows-11-10.0.26100-SP0",
    "matplotlib": "3.10.9",
    "numpy": "2.3.1",
    "pyyaml": "6.0.3"
  },
  "figure": {
    "width_in": 3.504,
    "height_in": 2.173,
    "dpi": 600,
    "formats": ["pdf", "svg", "png"],
    "journal": "nature",
    "palette": "okabe-ito",
    "colors": ["#000000", "#0072b2"]
  },
  "inputs": [
    {"path": "data/loss.csv", "sha256": "b1e0...", "bytes": 728}
  ],
  "outputs": [
    {"path": "figure.pdf", "format": "pdf", "sha256": "0a7c...", "bytes": 25852, "dpi": null},
    {"path": "figure.png", "format": "png", "sha256": "77d4...", "bytes": 138563, "dpi": 600}
  ],
  "git": {"commit": "3f9c...", "dirty": false},
  "lint": {"error": 0, "warning": 0, "info": 0}
}
```

Paths are relative: the spec relative to the manifest, inputs relative to the
spec's directory, outputs relative to the manifest. A manifest and its outputs
can be committed, archived or attached to a paper.

## Verification

```bash
figspec verify out/figure.figspec.json
```

```
verifying out/figure.figspec.json
  OK   schema: figspec/provenance/v1
  OK   spec: figure.yaml matches
  OK   input loss.csv: loss.csv matches
  OK   output figure.pdf: figure.pdf matches
  OK   output figure.svg: figure.svg matches
  OK   environment: tool versions match
```

`verify` recomputes every hash and compares recorded tool versions. Missing or
changed files fail; version drift is a warning because a newer matplotlib may
legitimately re-render the same inputs differently.

Exit codes: `0` clean, `1` drift, `5` unreadable manifest.

`--json` returns the same information machine-readably:

```bash
figspec verify out/figure.figspec.json --json | jq '.checks[] | select(.status != "ok")'
```

## Determinism

All four supported vector/raster formats are byte-identical across builds in the
same environment:

| Format | How stability is achieved |
|---|---|
| PDF | `CreationDate` removed via `savefig(metadata={"CreationDate": None})` |
| SVG | `Date` removed; `svg.hashsalt` pins element ids |
| PNG | no wall-clock metadata; fixed encoder settings |
| EPS | `%%CreationDate` header stripped after export |

Other measures: `path.simplify` off, `agg.path.chunksize` fixed, fonts resolved
from the same family stack, and no random ids. Set `SOURCE_DATE_EPOCH` to pin the
manifest's `generated_at` as well.

What determinism does **not** promise: identical bytes after upgrading matplotlib
or installing a different font. That is exactly why the manifest records versions
— `verify` will tell you the environment moved.

## Using it in a paper repository

```bash
figures/
├── figure.yaml
├── data/
│   └── loss.csv
└── out/
    ├── figure.pdf
    ├── figure.svg
    └── figure.figspec.json
```

- Commit the manifest with the outputs; reviewers can check hashes without
  running anything.
- In CI, rebuild into a temporary directory and compare SHA-256 values against
  the committed manifest. A mismatch means either the inputs changed or the
  environment drifted — both worth knowing before submission.

```bash
figspec render figure.yaml -o /tmp/check --quiet
figspec verify /tmp/check/figure.figspec.json
```

## Limitations

- The manifest records the spec *file* hash and a semantic hash of the resolved
  mapping; it does not record the font binaries.
- Data files are hashed as bytes, so re-exporting a CSV with different line
  endings changes the hash even when the values are identical.
- `git` state is best-effort: outside a repository the field is `null`.
