from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.cli import main  # noqa: E402
from redaction_assistant.registration import (  # noqa: E402
    ANNUAL_FEE_CNY,
    RegistrationRequiredError,
    TrialLimitExceededError,
    build_registration_request,
    consume_trial_or_raise,
    registration_status,
    write_registration_request,
)


class M248RegistrationTrialGateTests(unittest.TestCase):
    def test_registration_request_records_fee_and_trial_limit(self):
        request = build_registration_request(edition="community", email="user@example.com")

        self.assertEqual(ANNUAL_FEE_CNY, 80)
        self.assertEqual(request["annual_fee_cny"], 80)
        self.assertEqual(request["trial_file_limit"], 50)
        self.assertIn("每年80元", "".join(request["boundary"]))

    def test_trial_requires_registration_before_consuming_files(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(RegistrationRequiredError):
                consume_trial_or_raise(1, registration_dir=td)

    def test_registered_community_user_can_use_50_files_then_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            request = build_registration_request(edition="community", email="user@example.com")
            write_registration_request(root, request)

            first = consume_trial_or_raise(49, registration_dir=root)
            second = consume_trial_or_raise(1, registration_dir=root)

            self.assertEqual(first["gate"], "trial")
            self.assertEqual(second["used_files"], 50)
            with self.assertRaises(TrialLimitExceededError) as ctx:
                consume_trial_or_raise(1, registration_dir=root)
            self.assertIn("80元/年", str(ctx.exception))

    def test_cli_registration_request_trial_status_and_disabled_license_issuer(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            code = main(["registration-request", "--email", "user@example.com", "--out", str(root)])
            self.assertEqual(0, code)
            self.assertTrue((root / "registration_request.json").exists())
            data = json.loads((root / "registration_request.json").read_text(encoding="utf-8"))
            self.assertEqual(data["annual_fee_cny"], 80)

            status_code = main(["trial-status", "--registration-dir", str(root)])
            self.assertEqual(0, status_code)
            self.assertEqual(registration_status(root)["trial_file_limit"], 50)

            license_code = main(["write-license", "--output", str(root / "license.json")])
            self.assertEqual(1, license_code)
            self.assertFalse((root / "license.json").exists())

    def test_cli_build_package_blocks_when_trial_quota_is_exceeded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registration_dir = root / "registration"
            write_registration_request(registration_dir, build_registration_request(email="user@example.com"))
            files = []
            for index in range(51):
                path = root / f"source_{index:02d}.txt"
                path.write_text(f"项目名称：测试项目{index}", encoding="utf-8")
                files.append(str(path))

            code = main([
                "build-package",
                "--project-alias-id",
                "quota-test",
                "--registration-dir",
                str(registration_dir),
                "--out",
                str(root / "out"),
                *files,
            ])

            self.assertEqual(1, code)
            self.assertFalse((root / "out" / "redaction_upload_package.json").exists())

    def test_local_service_blocks_when_trial_quota_is_exceeded(self):
        from redaction_assistant.local_service import handle_request

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registration_dir = root / "registration"
            write_registration_request(registration_dir, build_registration_request(email="user@example.com"))
            files = []
            for index in range(51):
                path = root / f"source_{index:02d}.txt"
                path.write_text(f"项目名称：测试项目{index}", encoding="utf-8")
                files.append(str(path))

            response = handle_request({
                "action": "build_package",
                "project_alias_id": "quota-service-test",
                "registration_dir": str(registration_dir),
                "out": str(root / "out"),
                "files": files,
            })

            self.assertFalse(response["success"])
            self.assertIn("80元/年", response["error"])


if __name__ == "__main__":
    unittest.main()
