import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.batch import build_batch_packages
from redaction_assistant.crypto import decrypt_mapping_file, encrypt_mapping_file
from redaction_assistant.parsers import parse_file
from redaction_assistant.sandbox import build_sandbox_import_package
from redaction_assistant.workflow import build_redaction_package, write_package


class M3TrialReadinessTests(unittest.TestCase):
    def test_mapping_can_be_encrypted_and_decrypted_with_passphrase(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mapping = {
                "schema_version": "redaction_mapping.v1",
                "items": [{"placeholder": "项目A", "original": "配网智能监测项目"}],
            }
            plain = root / "local_mapping.private.json"
            encrypted = root / "local_mapping.private.enc"
            plain.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")

            encrypt_mapping_file(plain, encrypted, passphrase="secret-pass")
            restored = decrypt_mapping_file(encrypted, passphrase="secret-pass")

            self.assertFalse(plain.exists())
            self.assertNotIn("配网智能监测项目", encrypted.read_text(encoding="utf-8"))
            self.assertEqual(restored["items"][0]["original"], "配网智能监测项目")
            with self.assertRaises(ValueError):
                decrypt_mapping_file(encrypted, passphrase="wrong-pass")

    def test_scanned_pdf_is_marked_as_ocr_required_not_silently_uploaded(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "scan.pdf"
            path.write_bytes(b"%PDF-1.4\n/Type /XObject /Subtype /Image\nstream\nnot text\nendstream\n%%EOF")

            blocks, manifest = parse_file(path)

            self.assertEqual(blocks, [])
            self.assertEqual(manifest["parser_status"], "ocr_required")
            self.assertIn("ocr_required", manifest["warnings"])

    def test_xlsx_table_structure_is_preserved_for_sandbox_import(self):
        from test_m1_workflow import write_minimal_xlsx

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            xlsx = root / "benefit.xlsx"
            write_minimal_xlsx(
                xlsx,
                [["指标", "数值"], ["合同金额", "350万元"], ["年度节约成本", "80万元"]],
            )

            package, mapping = build_redaction_package([xlsx], project_alias_id="2026-STPE-M3")
            sandbox = build_sandbox_import_package(package)

            table_blocks = [
                block for block in package["redacted_text_blocks"]
                if block.get("structure", {}).get("kind") == "table_row"
            ]
            self.assertGreaterEqual(len(table_blocks), 2)
            self.assertIn("A2", table_blocks[1]["structure"]["cells"][0]["ref"])
            self.assertEqual(sandbox["project_alias_id"], "2026-STPE-M3")
            self.assertFalse(sandbox["contains_local_mapping"])
            self.assertTrue(sandbox["files"])

    def test_batch_packages_use_project_directories_as_aliases(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p1 = root / "project_alpha"
            p2 = root / "project_beta"
            p1.mkdir()
            p2.mkdir()
            (p1 / "input.txt").write_text("项目名称：配网智能监测项目。合同金额：350万元。技术指标：10kV试运行30天。", encoding="utf-8")
            (p2 / "input.txt").write_text("项目名称：变电站辅助系统项目。合同金额：80万元。技术指标：现场验证完成。", encoding="utf-8")

            result = build_batch_packages(root, root / "out", passphrase="secret-pass")

            self.assertEqual(result["project_count"], 2)
            aliases = {item["project_alias_id"] for item in result["projects"]}
            self.assertEqual(aliases, {"project_alpha", "project_beta"})
            for item in result["projects"]:
                self.assertTrue(Path(item["package"]).exists())
                self.assertTrue(Path(item["encrypted_mapping"]).exists())
                self.assertFalse(Path(item["mapping"]).exists())


if __name__ == "__main__":
    unittest.main()
