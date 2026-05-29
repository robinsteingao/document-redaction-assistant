from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .crypto import encrypt_mapping_file
from .review import export_review_workspace
from .sandbox import build_sandbox_import_package
from .workflow import build_redaction_package, write_package


SUPPORTED_SUFFIXES = {".docx", ".xlsx", ".pdf", ".txt", ".md"}


def build_batch_packages(
    input_root: Path | str,
    output_root: Path | str,
    *,
    passphrase: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_root)
    output_path = Path(output_root)
    output_path.mkdir(parents=True, exist_ok=True)
    projects = []
    for project_dir in sorted(p for p in input_path.iterdir() if p.is_dir()):
        files = sorted(
            p for p in project_dir.iterdir()
            if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
        )
        if not files:
            continue
        alias = project_dir.name
        project_out = output_path / alias
        package, mapping = build_redaction_package(files, project_alias_id=alias)
        outputs = write_package(project_out, package, mapping)
        outputs.update(export_review_workspace(project_out, package, mapping))
        sandbox = build_sandbox_import_package(package)
        sandbox_path = project_out / "sandbox_import_package.json"
        sandbox_path.write_text(json.dumps(sandbox, ensure_ascii=False, indent=2), encoding="utf-8")

        mapping_path = outputs["mapping"]
        encrypted_mapping = None
        if passphrase:
            encrypted_mapping = encrypt_mapping_file(
                mapping_path,
                project_out / "local_mapping.private.enc",
                passphrase=passphrase,
            )
        projects.append({
            "project_alias_id": alias,
            "package": str(outputs["package"]),
            "mapping": str(mapping_path),
            "encrypted_mapping": str(encrypted_mapping) if encrypted_mapping else None,
            "review_html": str(outputs["review_html"]),
            "sandbox_import": str(sandbox_path),
            "file_count": len(files),
        })
    manifest = {
        "schema_version": "redaction_batch_manifest.v1",
        "project_count": len(projects),
        "projects": projects,
    }
    (output_path / "batch_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest
