import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.install_package import build_install_package
from redaction_assistant.report_delivery import build_report_delivery_package


class M13ReportRestoreTests(unittest.TestCase):
    def test_report_delivery_package_restores_with_local_mapping(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mapping = {
                "items": [
                    {
                        "original": "配网智能监测项目",
                        "placeholder": "项目A",
                        "kind": "project_name",
                    }
                ]
            }
            mapping_path = root / "local_mapping.private.json"
            mapping_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8-sig")
            evaluation_result = {
                "project_alias_id": "project_alpha",
                "report_title": "项目A 后评估报告",
                "summary": "项目A 已完成 10kV 现场试运行30天。",
                "recommendations": ["继续补充效益证明。"],
            }

            result = build_report_delivery_package(evaluation_result, mapping_path, root / "report_out")
            restored = result["restored_preview"].read_text(encoding="utf-8")
            manifest = json.loads(result["manifest"].read_text(encoding="utf-8"))

            self.assertTrue(result["redacted_report"].exists())
            self.assertIn("配网智能监测项目", restored)
            self.assertEqual(manifest["schema_version"], "document_redaction_report_delivery.v1")
            self.assertFalse(manifest["contains_local_mapping"])
            self.assertFalse(manifest["contains_original_files"])

    def test_install_package_contains_report_restore_demo_script(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.13.0-m13")
            package_dir = result["package_dir"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))

            self.assertTrue((package_dir / "app" / "build_report_delivery_demo.bat").exists())
            self.assertIn("report_delivery_demo", manifest["commands"])


if __name__ == "__main__":
    unittest.main()
