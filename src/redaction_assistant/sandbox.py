from __future__ import annotations

from typing import Any


def build_sandbox_import_package(package: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "stpe_sandbox_import.v1",
        "project_alias_id": package.get("project_alias_id"),
        "contains_original_files": False,
        "contains_local_mapping": False,
        "files": [
            {
                "file_name": item.get("file_name"),
                "file_type": item.get("file_type"),
                "file_hash": item.get("file_hash"),
                "parser_status": item.get("parser_status"),
                "warnings": item.get("warnings", []),
            }
            for item in package.get("source_file_manifest", [])
        ],
        "redacted_text_blocks": package.get("redacted_text_blocks", []),
        "structured_facts": package.get("structured_facts", {}),
        "analysis_preservation_flags": package.get("analysis_preservation_flags", {}),
        "review_warnings": package.get("review_warnings", []),
        "field_mappings_hash": package.get("field_mappings_hash"),
    }
