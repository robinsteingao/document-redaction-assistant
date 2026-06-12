from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


REQUIRED_DOCS = [
    "README.md",
    "LICENSE",
    "PRIVACY.md",
    "COMMERCIAL.md",
    "DISCLAIMER.md",
    "docs/OPEN_SOURCE_RELEASE_GUIDE.md",
]

BLOCKED_NAME_PATTERNS = [
    re.compile(r"(^|/|\\)\.release", re.IGNORECASE),
    re.compile(r"local_mapping\.private", re.IGNORECASE),
    re.compile(r"trial_usage_.*\.json$", re.IGNORECASE),
    re.compile(r"registration_request\.json$", re.IGNORECASE),
    re.compile(r"registration_mailto\.txt$", re.IGNORECASE),
    re.compile(r"(^|/|\\)license\.json$", re.IGNORECASE),
    re.compile(r"private[_-]?key", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"\.env$", re.IGNORECASE),
    re.compile(r"\.(pem|key)$", re.IGNORECASE),
]

SENSITIVE_CONTENT_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?key|secret|smtp[_-]?password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
]

TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".toml", ".bat", ".html", ".yml", ".yaml", ".gitignore", ""}


def run_open_source_release_preflight(root: Path | str) -> dict[str, Any]:
    package_root = Path(root)
    issues: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    if not package_root.exists():
        return {
            "schema_version": "document_redaction_open_source_preflight.v1",
            "status": "blocked",
            "root": str(package_root),
            "issues": [{"check": "root_exists", "severity": "high", "path": str(package_root), "message": "package root not found"}],
            "checks": [],
        }

    _check_required_docs(package_root, issues, checks)
    _check_gitignore(package_root, issues, checks)
    _scan_files(package_root, issues, checks)

    high_or_medium = [issue for issue in issues if issue.get("severity") in {"high", "medium"}]
    return {
        "schema_version": "document_redaction_open_source_preflight.v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "blocked" if high_or_medium else "passed",
        "root": str(package_root),
        "issues": issues,
        "checks": checks,
    }


def write_open_source_preflight_report(root: Path | str, output: Path | str) -> Path:
    report = run_open_source_release_preflight(root)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def report_fingerprint(report: dict[str, Any]) -> str:
    public = {key: value for key, value in report.items() if key != "created_at"}
    raw = json.dumps(public, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _check_required_docs(root: Path, issues: list[dict[str, Any]], checks: list[dict[str, Any]]) -> None:
    for relative in REQUIRED_DOCS:
        exists = (root / relative).exists()
        checks.append({"check": "required_doc", "path": relative, "status": "pass" if exists else "fail"})
        if not exists:
            issues.append({"check": "required_doc", "severity": "high", "path": relative, "message": "required open-source boundary document is missing"})


def _check_gitignore(root: Path, issues: list[dict[str, Any]], checks: list[dict[str, Any]]) -> None:
    path = root / ".gitignore"
    required_tokens = [".release*", "local_mapping.private", "trial_usage_", "registration_request.json", "license.json", "stpe_upload_package"]
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    missing = [token for token in required_tokens if token not in text]
    checks.append({"check": "gitignore_release_safety", "status": "pass" if not missing else "fail", "missing": missing})
    if missing:
        issues.append({"check": "gitignore_release_safety", "severity": "medium", "path": ".gitignore", "message": "missing ignore tokens: " + ", ".join(missing)})


def _scan_files(root: Path, issues: list[dict[str, Any]], checks: list[dict[str, Any]]) -> None:
    scanned = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if _skip_scan(relative):
            continue
        scanned += 1
        for pattern in BLOCKED_NAME_PATTERNS:
            if pattern.search(relative):
                issues.append({"check": "blocked_filename", "severity": "high", "path": relative, "message": "file should not be present in open-source release scope"})
                break
        if _is_text_file(path):
            _scan_text_file(path, relative, issues)
    checks.append({"check": "file_scan", "status": "pass", "scanned_files": scanned})


def _scan_text_file(path: Path, relative: str, issues: list[dict[str, Any]]) -> None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return
    for pattern in SENSITIVE_CONTENT_PATTERNS:
        if pattern.search(text):
            issues.append({"check": "sensitive_content", "severity": "high", "path": relative, "message": "possible key/secret assignment detected"})
            return


def _skip_scan(relative: str) -> bool:
    parts = set(relative.split("/"))
    return bool(parts & {"__pycache__", ".pytest_cache", "dist", "build"})


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name == ".gitignore"
