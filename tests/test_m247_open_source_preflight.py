from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.cli import main  # noqa: E402
from redaction_assistant.open_source_preflight import (  # noqa: E402
    REQUIRED_DOCS,
    run_open_source_release_preflight,
    write_open_source_preflight_report,
)


class M247OpenSourcePreflightTests(unittest.TestCase):
    def test_clean_minimal_release_root_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_required_docs(root)
            self._write_safe_gitignore(root)
            (root / "src" / "redaction_assistant").mkdir(parents=True)
            (root / "src" / "redaction_assistant" / "__init__.py").write_text("", encoding="utf-8")

            report = run_open_source_release_preflight(root)

            self.assertEqual(report["status"], "passed")
            self.assertEqual([], report["issues"])

    def test_blocked_when_release_artifacts_or_local_private_files_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_required_docs(root)
            self._write_safe_gitignore(root)
            for relative in [".release_20260612/snapshot.json", "local_mapping.private.json", "license.json"]:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")

            report = run_open_source_release_preflight(root)

            self.assertEqual(report["status"], "blocked")
            blocked_paths = {issue["path"] for issue in report["issues"] if issue["check"] == "blocked_filename"}
            self.assertIn(".release_20260612/snapshot.json", blocked_paths)
            self.assertIn("local_mapping.private.json", blocked_paths)
            self.assertIn("license.json", blocked_paths)

    def test_blocked_when_possible_secret_content_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_required_docs(root)
            self._write_safe_gitignore(root)
            secret_file = root / "config" / "example.py"
            secret_file.parent.mkdir(parents=True)
            secret_file.write_text(("api_" + "key = " + "abcdefghijklmnop"), encoding="utf-8")

            report = run_open_source_release_preflight(root)

            self.assertEqual(report["status"], "blocked")
            self.assertTrue(any(issue["check"] == "sensitive_content" for issue in report["issues"]))

    def test_write_report_is_read_only_for_scanned_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pkg"
            root.mkdir()
            self._write_required_docs(root)
            self._write_safe_gitignore(root)
            private_file = root / "local_mapping.private.json"
            private_file.write_text('{"local":"only"}', encoding="utf-8")
            before = private_file.read_text(encoding="utf-8")

            report_path = Path(tmp) / "preflight_report.json"
            write_open_source_preflight_report(root, report_path)

            self.assertTrue(report_path.exists())
            self.assertEqual(before, private_file.read_text(encoding="utf-8"))
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "blocked")

    def test_cli_writes_report_and_returns_status_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pkg"
            root.mkdir()
            self._write_required_docs(root)
            self._write_safe_gitignore(root)
            report_path = Path(tmp) / "cli_report.json"

            code = main(["open-source-preflight", "--root", str(root), "--output", str(report_path)])

            self.assertEqual(0, code)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual("passed", report["status"])

    def test_cli_returns_one_when_preflight_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pkg"
            root.mkdir()
            self._write_required_docs(root)
            self._write_safe_gitignore(root)
            (root / "license.json").write_text("{}", encoding="utf-8")
            report_path = Path(tmp) / "blocked_report.json"

            code = main(["open-source-preflight", "--root", str(root), "--output", str(report_path)])

            self.assertEqual(1, code)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual("blocked", report["status"])

    def _write_required_docs(self, root: Path) -> None:
        for relative in REQUIRED_DOCS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {relative}\n", encoding="utf-8")

    def _write_safe_gitignore(self, root: Path) -> None:
        (root / ".gitignore").write_text(
            "\n".join(
                [
                    ".release*",
                    "local_mapping.private*",
                    "trial_usage_*.json",
                    "registration_request.json",
                    "license.json",
                    "stpe_upload_package/",
                ]
            )
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
