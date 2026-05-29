from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable


LEGACY_OFFICE_SUFFIXES = {".doc", ".xls", ".wps"}


def convert_legacy_office_files(
    files: Iterable[str | Path],
    *,
    workspace: str | Path,
    converter: str | Path | None = None,
    runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    workspace_path = Path(workspace).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    converter_path = Path(converter) if converter else find_office_converter()
    result = {
        "schema_version": "document_redaction_office_conversion.v1",
        "converter": str(converter_path) if converter_path else None,
        "converted_files": [],
        "failed_files": [],
        "converted_count": 0,
        "failed_count": 0,
    }
    if converter_path is None:
        for source in files:
            path = Path(source)
            result["failed_files"].append({
                "path": str(path),
                "file_name": path.name,
                "reason": "office_converter_not_found",
            })
        result["failed_count"] = len(result["failed_files"])
        return result

    run = runner or subprocess.run
    for source in files:
        path = Path(source)
        target_suffix = target_extension(path.suffix.lower())
        if target_suffix is None:
            result["failed_files"].append({
                "path": str(path),
                "file_name": path.name,
                "reason": "unsupported_conversion_source",
            })
            continue
        command = [
            str(converter_path),
            "--headless",
            "--invisible",
            "--nologo",
            "--nodefault",
            "--nofirststartwizard",
            "--nolockcheck",
        ]
        profile_context = tempfile.TemporaryDirectory(prefix="dra_lo_profile_") if _isolated_profile_enabled() else None
        try:
            if profile_context is not None:
                profile_dir = Path(profile_context.__enter__()).resolve()
                command.append(f"-env:UserInstallation={profile_dir.as_uri()}")
            command.extend([
                "--convert-to",
                target_suffix.lstrip("."),
                "--outdir",
                str(workspace_path),
                str(path.resolve()),
            ])
            try:
                completed = run(command, capture_output=True, text=True, timeout=_conversion_timeout_seconds())
            except subprocess.TimeoutExpired as exc:
                result["failed_files"].append({
                    "path": str(path),
                    "file_name": path.name,
                    "reason": "conversion_timeout",
                    "timeout_seconds": _conversion_timeout_seconds(),
                    "stderr": str(exc.stderr or "")[-800:],
                })
                continue
        finally:
            if profile_context is not None:
                profile_context.__exit__(None, None, None)
        expected = workspace_path / f"{path.stem}{target_suffix}"
        if getattr(completed, "returncode", 1) == 0 and expected.exists():
            result["converted_files"].append({
                "original_path": str(path),
                "converted_path": str(expected),
                "file_name": path.name,
                "converted_file_name": expected.name,
                "target_extension": target_suffix,
            })
        else:
            result["failed_files"].append({
                "path": str(path),
                "file_name": path.name,
                "reason": "conversion_failed",
                "returncode": getattr(completed, "returncode", None),
                "stderr": str(getattr(completed, "stderr", "") or "")[-800:],
            })

    result["converted_count"] = len(result["converted_files"])
    result["failed_count"] = len(result["failed_files"])
    return result


def find_office_converter() -> Path | None:
    configured = os.getenv("DRA_OFFICE_CONVERTER")
    if configured and Path(configured).exists():
        return Path(configured)
    candidates = []
    app_dir = os.getenv("DRA_APP_DIR")
    if app_dir:
        candidates.append(Path(app_dir) / "office_runtime")
    candidates.extend([
        Path.cwd() / "app" / "office_runtime",
        Path.cwd() / "office_runtime",
    ])
    for root in candidates:
        found = _find_converter_under(root)
        if found:
            return found
    return None


def _conversion_timeout_seconds() -> int:
    raw = os.getenv("DRA_OFFICE_CONVERSION_TIMEOUT", "240")
    try:
        return max(30, int(raw))
    except ValueError:
        return 240


def _isolated_profile_enabled() -> bool:
    return os.getenv("DRA_OFFICE_ISOLATED_PROFILE", "").strip().lower() in {"1", "true", "yes"}


def target_extension(suffix: str) -> str | None:
    if suffix == ".xls":
        return ".xlsx"
    if suffix in {".doc", ".wps"}:
        return ".docx"
    return None


def _find_converter_under(root: Path) -> Path | None:
    if not root.exists():
        return None
    for name in ("soffice.exe", "soffice", "wps.exe", "et.exe", "wpp.exe"):
        matches = list(root.rglob(name))
        if matches:
            return matches[0]
    return None
