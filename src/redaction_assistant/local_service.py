from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .office_converter import convert_legacy_office_files
from .ocr_adapter import get_ocr_status
from .review import export_review_workspace, review_decisions_from_mapping
from .sandbox import build_sandbox_import_package
from .user_batch import collect_user_inputs, ocr_max_pages_for_mode
from .workflow import build_redaction_package, write_package

_JOBS: dict[str, dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()


class JobCancelled(RuntimeError):
    pass


def handle_request(payload: dict[str, Any]) -> dict[str, Any]:
    action = payload.get("action")
    try:
        if action == "ocr_status":
            return {"success": True, "result": get_ocr_status()}
        if action == "plan_inputs":
            paths = payload.get("input_paths") or payload.get("files") or []
            if not paths:
                raise ValueError("input_paths are required")
            return {"success": True, "result": collect_user_inputs(paths)}
        if action == "start_build_package":
            return _start_build_job(payload)
        if action == "cancel_job":
            return _cancel_job(payload)
        if action == "retry_job":
            return _retry_job(payload)
        if action == "job_status":
            job_id = payload.get("job_id")
            if not job_id:
                raise ValueError("job_id is required")
            with _JOBS_LOCK:
                job = dict(_JOBS.get(str(job_id)) or {})
            if not job:
                raise ValueError(f"job not found: {job_id}")
            return {"success": True, "result": job}
        if action == "build_package":
            files = payload.get("files") or []
            if payload.get("input_paths"):
                plan = collect_user_inputs(payload.get("input_paths") or [])
                prepared = _prepare_files_from_plan(plan, out=payload.get("out"), alias=payload.get("project_alias_id"), payload=payload)
                files = prepared["files"]
            out = payload.get("out")
            alias = payload.get("project_alias_id")
            if not files or not out or not alias:
                raise ValueError("files, out and project_alias_id are required")
            decisions = None
            if payload.get("review_decisions"):
                decisions = review_decisions_from_mapping(payload["review_decisions"])
            try:
                outputs = _build_outputs(
                    files,
                    out,
                    alias,
                    customer_dictionary=payload.get("customer_dictionary"),
                    review_decisions=decisions,
                    customer_confirmed_degradation_risk=_explicit_bool(payload.get("customer_confirmed_degradation_risk")),
                    ocr_mode=payload.get("ocr_mode"),
                )
            finally:
                if payload.get("input_paths"):
                    _cleanup_conversion_workspace(prepared)
            return {
                "success": True,
                "result": {name: str(path) for name, path in outputs.items()},
            }
        raise ValueError(f"unsupported action: {action}")
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _start_build_job(payload: dict[str, Any]) -> dict[str, Any]:
    paths = payload.get("input_paths") or payload.get("files") or []
    out = payload.get("out")
    alias = payload.get("project_alias_id")
    if not paths or not out or not alias:
        raise ValueError("input_paths/files, out and project_alias_id are required")
    plan = collect_user_inputs(paths)
    if not plan["processable_files"] and not plan.get("convertible_files"):
        raise ValueError("no processable files found")
    job_id = uuid.uuid4().hex
    job = {
        "job_id": job_id,
        "status": "queued",
        "started_at": None,
        "completed_at": None,
        "duration_seconds": None,
        "plan": plan,
        "progress": {"current": 0, "total": plan["processable_count"] + plan.get("convertible_count", 0), "file_name": None},
        "outputs": {},
        "requested_output_dir": str(out),
        "payload": _public_job_payload(payload),
        "cancel_requested": False,
        "conversion_report": None,
        "error": None,
    }
    with _JOBS_LOCK:
        _JOBS[job_id] = job
    thread = threading.Thread(
        target=_run_build_job,
        args=(job_id, plan["processable_files"], out, alias, payload),
        daemon=True,
    )
    thread.start()
    return {"success": True, "result": {"job_id": job_id, "status": "queued", "plan": plan}}


def _cancel_job(payload: dict[str, Any]) -> dict[str, Any]:
    job_id = str(payload.get("job_id") or "")
    if not job_id:
        raise ValueError("job_id is required")
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            raise ValueError(f"job not found: {job_id}")
        if job.get("status") in {"completed", "failed", "cancelled"}:
            return {"success": True, "result": dict(job)}
        job["cancel_requested"] = True
    return {"success": True, "result": {"job_id": job_id, "status": "cancelling"}}


def _retry_job(payload: dict[str, Any]) -> dict[str, Any]:
    job_id = str(payload.get("job_id") or "")
    if not job_id:
        raise ValueError("job_id is required")
    with _JOBS_LOCK:
        job = dict(_JOBS.get(job_id) or {})
    if not job:
        raise ValueError(f"job not found: {job_id}")
    if job.get("status") not in {"failed", "cancelled"}:
        raise ValueError("only failed or cancelled jobs can be retried")
    retry_payload = dict(job.get("payload") or {})
    if not retry_payload:
        raise ValueError("job payload is not available for retry")
    return _start_build_job(retry_payload)


def _run_build_job(job_id: str, files: list[str], out: str, alias: str, payload: dict[str, Any]) -> None:
    started = time.monotonic()
    def update(**changes: Any) -> None:
        with _JOBS_LOCK:
            _JOBS[job_id].update(changes)

    def progress(event: dict[str, Any]) -> None:
        with _JOBS_LOCK:
            if _JOBS[job_id].get("cancel_requested"):
                raise JobCancelled("user_cancelled")
            _JOBS[job_id]["status"] = "running"
            _JOBS[job_id]["progress"] = {
                "stage": event.get("stage"),
                "current": event.get("current"),
                "total": event.get("total"),
                "file_name": event.get("file_name"),
                "parser_status": event.get("parser_status"),
                "ocr_status": event.get("ocr_status"),
            }

    try:
        update(status="running", started_at=datetime.now().isoformat(timespec="seconds"))
        decisions = None
        if payload.get("review_decisions"):
            decisions = review_decisions_from_mapping(payload["review_decisions"])
        prepared = _prepare_files_from_plan(
            payload.get("_plan") or collect_user_inputs(payload.get("input_paths") or payload.get("files") or []),
            out=out,
            alias=alias,
            payload=payload,
            job_id=job_id,
        )
        if not prepared["files"]:
            raise ValueError("no files available after office conversion")
        try:
            outputs = _build_outputs(
                prepared["files"],
                prepared["output_dir"],
                alias,
                customer_dictionary=payload.get("customer_dictionary"),
                review_decisions=decisions,
                customer_confirmed_degradation_risk=_explicit_bool(payload.get("customer_confirmed_degradation_risk")),
                ocr_mode=payload.get("ocr_mode"),
                progress_cb=progress,
            )
        finally:
            _cleanup_conversion_workspace(prepared)
        update(
            status="completed",
            completed_at=datetime.now().isoformat(timespec="seconds"),
            duration_seconds=round(time.monotonic() - started, 2),
            outputs={name: str(path) for name, path in outputs.items()},
            conversion_report=prepared.get("conversion_report"),
        )
    except JobCancelled as exc:
        update(
            status="cancelled",
            completed_at=datetime.now().isoformat(timespec="seconds"),
            duration_seconds=round(time.monotonic() - started, 2),
            error=str(exc),
        )
    except Exception as exc:  # keep service alive and expose failure to user
        update(
            status="failed",
            completed_at=datetime.now().isoformat(timespec="seconds"),
            duration_seconds=round(time.monotonic() - started, 2),
            error=f"{type(exc).__name__}: {exc}",
        )


def _prepare_files_from_plan(
    plan: dict[str, Any],
    *,
    out: str | Path,
    alias: str,
    payload: dict[str, Any],
    job_id: str | None = None,
) -> dict[str, Any]:
    output_dir = _prepare_output_dir(out, alias)
    files = list(plan.get("processable_files") or [])
    conversion_report = None
    convertible = [item["path"] for item in plan.get("convertible_files") or []]
    if convertible and payload.get("enable_conversion", True):
        if job_id:
            _update_job_progress(job_id, {
                "stage": "conversion",
                "current": 0,
                "total": len(convertible),
                "file_name": None,
            })
        with tempfile.TemporaryDirectory(prefix="dra_office_convert_") as td:
            conversion_report = convert_legacy_office_files(convertible, workspace=td)
            files.extend(item["converted_path"] for item in conversion_report["converted_files"])
            # Keep converted files alive through package build by copying into output temp slot.
            keep_dir = output_dir / ".converted_inputs"
            keep_dir.mkdir(parents=True, exist_ok=True)
            kept = []
            for item in conversion_report["converted_files"]:
                source = Path(item["converted_path"])
                target = keep_dir / source.name
                target.write_bytes(source.read_bytes())
                item["converted_path"] = str(target)
                kept.append(str(target))
            files = list(plan.get("processable_files") or []) + kept
    return {
        "files": files,
        "output_dir": output_dir,
        "conversion_report": conversion_report,
        "conversion_workspace": str(output_dir / ".converted_inputs") if conversion_report else None,
    }


def _cleanup_conversion_workspace(prepared: dict[str, Any]) -> None:
    workspace = prepared.get("conversion_workspace")
    if not workspace:
        return
    path = Path(workspace)
    if path.name != ".converted_inputs":
        return
    shutil.rmtree(path, ignore_errors=True)


def _update_job_progress(job_id: str, progress: dict[str, Any]) -> None:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return
        if job.get("cancel_requested"):
            raise JobCancelled("user_cancelled")
        job["status"] = "running"
        job["progress"] = progress


def _public_job_payload(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "input_paths",
        "files",
        "out",
        "project_alias_id",
        "customer_dictionary",
        "review_decisions",
        "customer_confirmed_degradation_risk",
        "ocr_mode",
        "enable_conversion",
    }
    return {key: value for key, value in payload.items() if key in allowed}


def _explicit_bool(value: Any) -> bool:
    return value is True


def _build_outputs(
    files: list[str] | list[Path],
    out: str | Path,
    alias: str,
    *,
    customer_dictionary: Path | str | dict | None = None,
    review_decisions: dict[str, dict[str, Any]] | None = None,
    customer_confirmed_degradation_risk: bool = False,
    ocr_mode: str | None = None,
    progress_cb=None,
) -> dict[str, Path]:
    output_dir = _prepare_output_dir(out, alias)
    package, mapping = build_redaction_package(
        files,
        project_alias_id=alias,
        customer_dictionary=customer_dictionary,
        review_decisions=review_decisions,
        customer_confirmed_degradation_risk=customer_confirmed_degradation_risk,
        ocr_max_pages=ocr_max_pages_for_mode(ocr_mode),
        progress_cb=progress_cb,
    )
    outputs = write_package(output_dir, package, mapping)
    outputs.update(export_review_workspace(output_dir, package, mapping))
    sandbox_path = output_dir / "sandbox_import_package.json"
    sandbox_path.write_text(
        json.dumps(build_sandbox_import_package(package), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    outputs["output_dir"] = output_dir
    outputs["sandbox_import"] = sandbox_path
    return outputs


def _prepare_output_dir(out: str | Path, alias: str) -> Path:
    requested = Path(out)
    target = requested if requested.is_absolute() else _default_output_root() / requested
    try:
        target.mkdir(parents=True, exist_ok=True)
        return target
    except PermissionError:
        fallback = _default_output_root() / f"{_safe_name(alias)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _default_output_root() -> Path:
    configured = os.getenv("DRA_OUTPUT_ROOT")
    if configured:
        return Path(configured)
    home = Path.home()
    if str(home) and home.exists():
        return home / "Documents" / "文档安全脱敏助手输出"
    return Path(tempfile.gettempdir()) / "文档安全脱敏助手输出"


def _safe_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value.strip())
    return cleaned[:48] or "redaction_output"


def run_local_service(host: str = "127.0.0.1", port: int = 8765) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path.rstrip("/") == "/ocr-status":
                self._send(handle_request({"action": "ocr_status"}))
            elif self.path.startswith("/job-status"):
                from urllib.parse import parse_qs, urlparse

                params = parse_qs(urlparse(self.path).query)
                self._send(handle_request({"action": "job_status", "job_id": (params.get("job_id") or [""])[0]}))
            else:
                self._send({"success": False, "error": "not found"}, status=404)

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                self._send({"success": False, "error": str(exc)}, status=400)
                return
            if self.path.rstrip("/") == "/build-package":
                payload["action"] = "build_package"
                self._send(handle_request(payload))
            elif self.path.rstrip("/") == "/plan-inputs":
                payload["action"] = "plan_inputs"
                self._send(handle_request(payload))
            elif self.path.rstrip("/") == "/start-build":
                payload["action"] = "start_build_package"
                self._send(handle_request(payload))
            elif self.path.rstrip("/") == "/cancel-job":
                payload["action"] = "cancel_job"
                self._send(handle_request(payload))
            elif self.path.rstrip("/") == "/retry-job":
                payload["action"] = "retry_job"
                self._send(handle_request(payload))
            else:
                self._send({"success": False, "error": "not found"}, status=404)

        def do_OPTIONS(self):  # noqa: N802
            self.send_response(204)
            self._send_cors_headers()
            self.end_headers()

        def _send(self, data: dict[str, Any], status: int = 200) -> None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(body)

        def _send_cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def log_message(self, format, *args):  # noqa: A002
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"document-redaction-assistant local service: http://{host}:{port}")
    server.serve_forever()
