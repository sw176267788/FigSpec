# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | ✅ |
| < 0.1 | ❌ |

## Reporting a vulnerability

Please **do not** open a public issue. Report privately through GitHub's
"Security → Report a vulnerability" form, or by email to `security@figspec.dev`.

Include:

- the figspec version (`figspec doctor`) and Python version;
- a minimal spec or script that reproduces the issue;
- what an attacker could achieve.

You can expect an acknowledgement within 72 hours and a decision within seven
days. We will credit reporters in the release notes unless asked not to.

## Scope

figspec reads YAML and data files and writes image files. The realistic risks
are therefore:

- **Path traversal**: specs referencing files outside the project. figspec
  resolves relative paths and does not sandbox them; only render specs you trust.
- **YAML deserialisation**: only `yaml.safe_load` is used, never `unsafe_load`.
- **Pickle**: `.npy` files are loaded with `allow_pickle=False`.
- **Denial of service**: very large matrices or deeply nested `extends` chains;
  `extends` cycles are detected and reported.

Reports about any of the above, or about dependency vulnerabilities, are welcome.
