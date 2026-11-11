"""The command line interface."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from figspec.cli import main

SPEC = {
    "version": 1,
    "figure": {"size": [3.5, 2.4], "formats": ["pdf", "png"]},
    "axes": {"x": {"label": "Epoch"}, "y": {"label": "Loss"}},
    "series": [{"type": "line", "x": [1, 2, 3], "y": [[1.0, 0.8, 0.6]], "label": "run"}],
}


def _write(path: Path, spec: dict) -> Path:
    path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    return path


def test_version_flag(capsys):
    assert main(["--version"]) == 0
    assert "figspec" in capsys.readouterr().out.lower()


def test_help_lists_commands(capsys):
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "render" in out and "lint" in out and "verify" in out


def test_init_creates_starter(tmp_path: Path, capsys):
    target = tmp_path / "demo"
    assert main(["init", str(target)]) == 0
    assert (target / "figure.yaml").exists()
    assert (target / "data" / "loss.csv").exists()
    assert "next:" in capsys.readouterr().out


def test_init_does_not_overwrite_without_force(tmp_path: Path, capsys):
    target = tmp_path / "demo"
    main(["init", str(target)])
    assert main(["init", str(target)]) == 0
    assert "skip" in capsys.readouterr().out


def test_render_writes_files_and_manifest(tmp_path: Path, capsys):
    spec = _write(tmp_path / "figure.yaml", SPEC)
    out = tmp_path / "out"
    assert main(["render", str(spec), "-o", str(out)]) == 0
    assert (out / "figure.pdf").exists()
    assert (out / "figure.png").exists()
    assert (out / "figure.figspec.json").exists()
    assert "rendered 2 file(s)" in capsys.readouterr().out


def test_render_quiet(tmp_path: Path, capsys):
    spec = _write(tmp_path / "figure.yaml", SPEC)
    assert main(["render", str(spec), "-o", str(tmp_path / "out"), "--quiet"]) == 0
    assert capsys.readouterr().out == ""


def test_render_strict_fails_on_error(tmp_path: Path, capsys):
    spec = dict(SPEC)
    spec["style"] = {"font_size": 3.0}
    path = _write(tmp_path / "figure.yaml", spec)
    code = main(["render", str(path), "-o", str(tmp_path / "out"), "--strict"])
    assert code == 4
    assert not (tmp_path / "out" / "figure.pdf").exists()


def test_lint_json_exit_code(tmp_path: Path, capsys):
    spec = _write(tmp_path / "figure.yaml", SPEC)
    assert main(["lint", str(spec), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["error"] == 0


def test_lint_failure_exit_code(tmp_path: Path):
    spec = dict(SPEC)
    spec["style"] = {"font_size": 3.0}
    path = _write(tmp_path / "figure.yaml", spec)
    assert main(["lint", str(path)]) == 1


def test_lint_sarif_output(tmp_path: Path, capsys):
    spec = _write(tmp_path / "figure.yaml", SPEC)
    assert main(["lint", str(spec), "--format", "sarif"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"] == "2.1.0"


def test_verify_roundtrip(tmp_path: Path):
    spec = _write(tmp_path / "figure.yaml", SPEC)
    out = tmp_path / "out"
    main(["render", str(spec), "-o", str(out), "--quiet"])
    assert main(["verify", str(out / "figure.figspec.json")]) == 0


def test_verify_reports_drift(tmp_path: Path):
    spec = _write(tmp_path / "figure.yaml", SPEC)
    out = tmp_path / "out"
    main(["render", str(spec), "-o", str(out), "--quiet"])
    (out / "figure.pdf").unlink()
    assert main(["verify", str(out / "figure.figspec.json")]) == 1


def test_unknown_journal_exits_with_spec_error(tmp_path: Path, capsys):
    spec = _write(tmp_path / "figure.yaml", SPEC)
    assert main(["render", str(spec), "--journal", "nope"]) == 2
    assert "unknown journal" in capsys.readouterr().err


def test_unknown_command_exits_2(capsys):
    assert main(["frobnicate"]) == 2


def test_journals_table_and_json(capsys):
    assert main(["journals"]) == 0
    assert "nature" in capsys.readouterr().out
    assert main(["journals", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert any(item["name"] == "nature" for item in payload)


def test_palettes_listing(capsys):
    assert main(["palettes"]) == 0
    assert "okabe-ito" in capsys.readouterr().out


def test_rules_listing(capsys):
    assert main(["rules"]) == 0
    assert "FS001" in capsys.readouterr().out


def test_doctor(capsys):
    assert main(["doctor", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["figspec"]
    assert payload["lint_rules"] >= 10


def test_gallery_from_directory(tmp_path: Path, capsys):
    examples = tmp_path / "examples"
    examples.mkdir()
    _write(examples / "a.yaml", SPEC)
    out = tmp_path / "site"
    assert main(["gallery", str(examples), "-o", str(out)]) == 0
    index = out / "index.html"
    assert index.exists()
    assert "figure" in index.read_text(encoding="utf-8").lower()
    assert (out / "assets" / "a.png").exists()


def test_missing_spec_file_is_a_usage_error(capsys):
    assert main(["render", "does-not-exist.yaml"]) == 2
