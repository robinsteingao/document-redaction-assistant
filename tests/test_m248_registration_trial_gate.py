from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.cli import main  # noqa: E402


class M248OpenSourceNoGateContractTests(unittest.TestCase):
    """0.27.0 去门禁契约：注册/试用/授权命令保留弃用提示，不再产生任何效果。"""

    def test_registration_and_license_modules_are_removed(self):
        with self.assertRaises(ImportError):
            __import__("redaction_assistant.registration")
        with self.assertRaises(ImportError):
            __import__("redaction_assistant.local_license")

    def test_deprecated_commands_print_notice_and_create_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.assertEqual(0, main(["registration-request", "--email", "user@example.com", "--out", str(root)]))
            self.assertEqual(0, main(["trial-status", "--registration-dir", str(root)]))
            self.assertEqual(0, main(["write-license", "--output", str(root / "license.json")]))
            self.assertEqual(0, main(["validate-license", "--input", str(root / "license.json")]))
            self.assertFalse((root / "registration_request.json").exists())
            self.assertFalse((root / "registration_mailto.txt").exists())
            self.assertFalse((root / "trial_usage_community.json").exists())
            self.assertFalse((root / "license.json").exists())

    def test_legacy_files_are_not_read_modified_or_deleted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            legacy_license = root / "license.json"
            legacy_usage = root / "trial_usage_community.json"
            legacy_request = root / "registration_request.json"
            legacy_license.write_text('{"schema_version": "document_redaction_local_license.v1"}', encoding="utf-8")
            legacy_usage.write_text('{"used_files": 50}', encoding="utf-8")
            legacy_request.write_text('{"email": "old@example.com"}', encoding="utf-8")
            before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.iterdir()}

            self.assertEqual(0, main(["validate-license", "--input", str(legacy_license)]))
            self.assertEqual(0, main(["trial-status", "--registration-dir", str(root)]))

            after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.iterdir()}
            self.assertEqual(before, after)

    def test_build_package_has_no_quota_and_rejects_legacy_registration_flag(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            files = []
            for index in range(51):
                path = root / f"source_{index:02d}.txt"
                path.write_text(f"项目名称：测试项目{index}", encoding="utf-8")
                files.append(str(path))

            code = main([
                "build-package", "--project-alias-id", "no-quota", "--out", str(root / "out"), *files,
            ])
            self.assertEqual(0, code)
            self.assertTrue((root / "out" / "redaction_upload_package.json").exists())

            with self.assertRaises(SystemExit):
                main([
                    "build-package", "--project-alias-id", "legacy-flag",
                    "--registration-dir", str(root), "--out", str(root / "out2"), *files,
                ])

    def test_local_service_builds_without_registration_dir(self):
        from redaction_assistant.local_service import handle_request

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "source_00.txt"
            path.write_text("项目名称：测试项目", encoding="utf-8")
            response = handle_request({
                "action": "build_package",
                "project_alias_id": "no-gate-service",
                "out": str(root / "out"),
                "files": [str(path)],
            })
            self.assertTrue(response["success"], response)
            self.assertIn("package", response["result"])


if __name__ == "__main__":
    unittest.main()
