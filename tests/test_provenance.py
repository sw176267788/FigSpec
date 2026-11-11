"""Provenance manifests and drift detection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from figspec.api import render
from figspec.errors import ProvenanceError
from figspec.provenance import Manifest, verify

DATA = "epoch,train,val\n1,1.0,1.2\n2,0.8,1.0\n3,0.6,0.9\n"


@pytest.fixture
def rendered(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "loss.csv").write_text(DATA, encoding="utf-8")
    spec = {
        "version": 1,
        "figure": {"size": [3.5, 2.4], "formats": ["pdf", "svg"]},
        "axes": {"x": {"label": "Epoch"}, "y": {"label": "Loss"}},
        "series": [
            {
                "type": "line",
                "data": "data/loss.csv",
                "x": "epoch",
                "y": ["train", "val"],
                "labels": ["Train", "Validation"],
            }
        ],
    }
    spec_path = tmp_path / "figure.yaml"
    spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    outdir = tmp_path / "out"
    outcome = render(spec_path, outdir)
    outcome.close()
    return tmp_path, spec_path, outdir / "figure.figspec.json"


def test_manifest_records_everything(rendered):
    _, spec_path, manifest_path = rendered
    manifest = Manifest.load(manifest_path)
    payload = manifest.data
    assert payload["schema"] == "figspec/provenance/v1"
    assert payload["spec"]["hash"]
    assert payload["spec"]["file_sha256"]
    assert payload["inputs"][0]["path"] == "data/loss.csv"
    assert {output["format"] for output in payload["outputs"]} == {"pdf", "svg"}
    assert payload["figure"]["width_in"] == pytest.approx(3.5)
    assert payload["environment"]["python"]
    assert payload["lint"] == {"error": 0, "warning": 0, "info": 0}


def test_verify_reports_success(rendered):
    _, _, manifest_path = rendered
    result = verify(manifest_path)
    assert result.ok
    assert {check.name for check in result.checks} >= {"schema", "spec", "environment"}


def test_verify_detects_changed_input(rendered):
    root, _, manifest_path = rendered
    (root / "data" / "loss.csv").write_text(DATA + "4,0.5,0.8\n", encoding="utf-8")
    result = verify(manifest_path)
    assert not result.ok
    failed = [check for check in result.checks if check.status == "failed"]
    assert any(check.name.startswith("input") for check in failed)


def test_verify_detects_deleted_output(rendered):
    _, _, manifest_path = rendered
    (manifest_path.parent / "figure.pdf").unlink()
    result = verify(manifest_path)
    assert not result.ok
    assert any("missing file" in check.message for check in result.checks)


def test_verify_detects_changed_output(rendered):
    _, _, manifest_path = rendered
    target = manifest_path.parent / "figure.svg"
    target.write_text("<svg/>", encoding="utf-8")
    assert not verify(manifest_path).ok


def test_timestamp_is_pinned_by_source_date_epoch(rendered, monkeypatch):
    _, _, manifest_path = rendered
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
    # Re-render with the pinned timestamp.
    root = manifest_path.parent.parent
    outcome = render(root / "figure.yaml", manifest_path.parent)
    outcome.close()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["generated_at"] == "2023-11-14T22:13:20Z"


def test_unknown_schema_is_rejected(tmp_path: Path):
    path = tmp_path / "bad.figspec.json"
    path.write_text(json.dumps({"schema": "something/else"}), encoding="utf-8")
    with pytest.raises(ProvenanceError, match="unsupported manifest schema"):
        Manifest.load(path)


def test_missing_manifest_raises(tmp_path: Path):
    with pytest.raises(ProvenanceError, match="not found"):
        Manifest.load(tmp_path / "nope.json")


def test_malformed_manifest_raises(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ProvenanceError, match="cannot read manifest"):
        Manifest.load(path)


def test_render_without_manifest(rendered):
    root = rendered[0]
    outcome = render(root / "figure.yaml", root / "out2", manifest=False)
    outcome.close()
    assert not (root / "out2" / "figure.figspec.json").exists()
