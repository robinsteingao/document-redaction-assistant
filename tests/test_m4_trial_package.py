import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.ocr_quality import assess_ocr_quality
from redaction_assistant.review import export_review_workspace
from redaction_assistant.trial_package import build_trial_package
from redaction_assistant.workflow import build_redaction_package


class M4TrialPackageTests(unittest.TestCase):
    def test_ocr_quality_blocks_low_text_scanned_pdf(self):
        manifest = {
            "file_name": "scan.pdf",
            "file_type": "pdf",
            "parser_status": "ocr_required",
            "warnings": ["ocr_required"],
        }

        result = assess_ocr_quality(manifest, extracted_text="")

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "ocr_required")
        self.assertFalse(result["allow_upload"])

    def test_review_html_exposes_interactive_decision_export(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "input.txt"
            source.write_text("项目名称：配网智能监测项目。合同金额：350万元。技术指标：10kV试运行30天。", encoding="utf-8")
            package, mapping = build_redaction_package([source], project_alias_id="project_m4")
            outputs = export_review_workspace(root / "workspace", package, mapping)

            html = outputs["review_html"].read_text(encoding="utf-8")

        self.assertIn("downloadDecisions", html)
        self.assertIn("review_decisions.json", html)
        self.assertIn("textarea", html)
        self.assertIn("复核选择文件（JSON）", html)

    def test_trial_package_contains_required_customer_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            package_dir = build_trial_package(root, version="0.4.0-m4")

            required = [
                "START_HERE.md",
                "USER_GUIDE.md",
                "SECURITY_BOUNDARY.md",
                "PILOT_ACCEPTANCE_CHECKLIST.md",
                "sample_data/project_alpha/input.txt",
                "sample_data/project_beta/input.txt",
            ]
            for relative in required:
                self.assertTrue((package_dir / relative).exists(), relative)
            manifest = json.loads((package_dir / "trial_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], "0.4.0-m4")
            self.assertFalse(manifest["customer_installation_package"])


if __name__ == "__main__":
    unittest.main()
