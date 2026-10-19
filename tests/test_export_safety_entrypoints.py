from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.cli import main
from redaction_assistant.local_service import handle_request
from redaction_assistant.workflow import build_redaction_package, write_package


def _assert_batch_matches_manifest(batch: Path, manifest_path: Path) -> dict:
    assert manifest_path.parent == batch
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    exported = [item["output_name"] for item in manifest["files"] if item["status"] == "exported"]
    assert {path.name for path in batch.iterdir()} == {manifest_path.name, *exported}
    assert all((batch / name).stat().st_size > 0 for name in exported)
    assert not list(batch.rglob("local_mapping*"))
    return manifest


def test_cli_returns_new_batch_for_each_run(tmp_path: Path, capsys):
    source = tmp_path / "private-customer.txt"
    source.write_text("联系人：张三。技术指标：10kV。", encoding="utf-8")
    batches = []
    for _ in range(2):
        assert main([
            "build-package", "--project-alias-id", "SYNTHETIC-CLI",
            "--out", str(tmp_path / "out"), str(source),
        ]) == 0
        paths = {}
        for line in capsys.readouterr().out.splitlines():
            name, separator, value = line.partition(": ")
            if separator:
                paths[name] = Path(value)
        batch = paths["external_release"]
        assert batch.parent == tmp_path / "out" / "external_release"
        manifest = _assert_batch_matches_manifest(batch, paths["external_release_manifest"])
        assert manifest["exported_count"] == 1
        assert "private-customer" not in paths["external_release_manifest"].read_text(encoding="utf-8")
        batches.append(batch)
    assert batches[0] != batches[1]
    assert batches[0].exists()


def test_local_service_keeps_private_mapping_out_of_returned_batch(tmp_path: Path):
    source = tmp_path / "private-source.txt"
    source.write_text("联系人：张三。技术指标：10kV。", encoding="utf-8")
    response = handle_request({
        "action": "build_package", "project_alias_id": "SYNTHETIC-SERVICE",
        "out": str(tmp_path / "out"),
        "files": [str(source)],
    })
    assert response["success"] is True
    result = response["result"]
    batch = Path(result["external_release"])
    manifest = _assert_batch_matches_manifest(batch, Path(result["external_release_manifest"]))
    assert manifest["exported_count"] == 1
    assert Path(result["mapping"]).is_file()
    assert Path(result["mapping"]).parent != batch
    exported = next(item for item in manifest["files"] if item["status"] == "exported")
    content = (batch / exported["output_name"]).read_text(encoding="utf-8")
    assert "张三" not in content
    assert "10kV" in content


def test_service_does_not_read_or_touch_legacy_license_files(tmp_path: Path):
    source = tmp_path / "sample.txt"
    source.write_text("synthetic", encoding="utf-8")
    legacy = tmp_path / "registration"
    legacy.mkdir()
    (legacy / "license.json").write_text('{"legacy": true}', encoding="utf-8")
    (legacy / "registration_request.json").write_text('{"email": "old@example.com"}', encoding="utf-8")
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in legacy.iterdir()}
    response = handle_request({
        "action": "build_package", "project_alias_id": "SYNTHETIC-LEGACY",
        "out": str(tmp_path / "out"), "files": [str(source)],
    })
    assert response["success"] is True
    after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in legacy.iterdir()}
    assert after == before
    assert not list(legacy.glob("trial_usage_*"))
    assert source.read_text(encoding="utf-8") == "synthetic"


def test_workflow_rejects_source_changed_after_analysis(tmp_path: Path):
    source = tmp_path / "changed.txt"
    source.write_text("联系人：张三。技术指标：10kV。", encoding="utf-8")
    package, mapping = build_redaction_package([source], project_alias_id="SYNTHETIC-CHANGED")
    source.write_text("联系人：李四。技术指标：10kV。", encoding="utf-8")
    outputs = write_package(tmp_path / "out", package, mapping, source_files=[source])
    manifest = _assert_batch_matches_manifest(outputs["external_release"], outputs["external_release_manifest"])
    assert manifest["exported_count"] == 0
    assert manifest["blocked_count"] == 1
    assert source.read_text(encoding="utf-8").startswith("联系人：李四")
