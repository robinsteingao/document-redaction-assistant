from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


def launch_desktop_app(
    app_dir: Path | str,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    wait_seconds: int = 12,
) -> dict:
    app = Path(app_dir)
    if not app.is_absolute():
        app = Path(os.getcwd()) / app
    app = app.resolve()
    generated = app.parent / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    service_url = f"http://{host}:{port}"
    service_ready = _is_service_ready(service_url)
    process_id = None
    if not service_ready:
        process = _start_service(app, host=host, port=port, log_path=generated / "desktop_service.log")
        process_id = process.pid
        service_ready = _wait_for_service(service_url, timeout=wait_seconds)
    index = app / "desktop_shell" / "index.html"
    if service_ready and index.exists():
        webbrowser.open(index.resolve().as_uri())
    return {
        "schema_version": "document_redaction_desktop_launch.v1",
        "status": "started" if service_ready else "service_not_ready",
        "service_url": service_url,
        "service_process_id": process_id,
        "desktop_shell": str(index),
        "log": str(generated / "desktop_service.log"),
    }


def _start_service(app: Path, *, host: str, port: int, log_path: Path) -> subprocess.Popen:
    cmd = [
        "cmd.exe",
        "/c",
        str(app / "run_cli.bat"),
        "serve-local",
        "--host",
        host,
        "--port",
        str(port),
    ]
    log = log_path.open("a", encoding="utf-8")
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(
        cmd,
        cwd=str(app),
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )


def _wait_for_service(service_url: str, *, timeout: int) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _is_service_ready(service_url):
            return True
        time.sleep(0.5)
    return False


def _is_service_ready(service_url: str) -> bool:
    try:
        with urllib.request.urlopen(service_url + "/ocr-status", timeout=1.5) as response:
            return 200 <= response.status < 300
    except (OSError, urllib.error.URLError):
        return False
