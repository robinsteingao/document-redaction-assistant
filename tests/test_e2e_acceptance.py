import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(WORKSPACE / "prototype" / "src" / "backend"))

from redaction_assistant.batch import build_batch_packages
from redaction_assistant.crypto import decrypt_mapping_file
from redaction_assistant.redactor import restore_text
try:  # pragma: no cover - 依赖 STPE-AI 主仓后端的跨仓集成测试
    from routers.redaction_sandbox import validate_redaction_sandbox_payload
except ImportError:  # pragma: no cover
    validate_redaction_sandbox_payload = None


class EndToEndAcceptanceTests(unittest.TestCase):
    @unittest.skipIf(
        validate_redaction_sandbox_payload is None,
        "STPE-AI backend (routers.redaction_sandbox) not available in this standalone checkout",
    )
    def test_local_batch_to_sandbox_import_to_restore_flow(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_root = root / "input"
            out_root = root / "out"
            alpha = input_root / "project_alpha"
            beta = input_root / "project_beta"
            alpha.mkdir(parents=True)
            beta.mkdir(parents=True)
            (alpha / "input.txt").write_text(
                "项目名称：配网智能监测项目。\n"
                "承担单位：示例省电力公司。\n"
                "合同编号：HT-2026-001。\n"
                "合同金额：350万元。\n"
                "联系电话：13812345678。\n"
                "技术指标：10kV线路故障定位误差≤1%，现场试运行30天。\n",
                encoding="utf-8",
            )
            (alpha / "scan.pdf").write_bytes(
                b"%PDF-1.4\n/Type /XObject /Subtype /Image\nstream\nbinary\nendstream\n%%EOF"
            )
            (beta / "input.txt").write_text(
                "项目名称：变电站辅助系统项目。\n"
                "承担单位：蜀能创新中心。\n"
                "合同金额：80万元。\n"
                "技术指标：现场验证完成。\n",
                encoding="utf-8",
            )

            manifest = build_batch_packages(input_root, out_root, passphrase="local-secret")

            self.assertEqual(manifest["project_count"], 2)
            alpha_result = next(item for item in manifest["projects"] if item["project_alias_id"] == "project_alpha")
            package_path = Path(alpha_result["package"])
            sandbox_path = Path(alpha_result["sandbox_import"])
            encrypted_mapping = Path(alpha_result["encrypted_mapping"])
            plain_mapping = alpha_result["mapping"]
            review_html = Path(alpha_result["review_html"])

            self.assertTrue(package_path.exists())
            self.assertTrue(sandbox_path.exists())
            self.assertTrue(encrypted_mapping.exists())
            # 带口令的批量导出从不落盘明文映射：manifest 返回 None 且目录内不存在明文文件。
            self.assertIsNone(plain_mapping)
            self.assertFalse(list(out_root.rglob("local_mapping.private.json")))
            self.assertTrue(review_html.exists())

            package_text = package_path.read_text(encoding="utf-8")
            encrypted_text = encrypted_mapping.read_text(encoding="utf-8")
            for sensitive in ["配网智能监测项目", "示例省电力公司", "HT-2026-001", "350万元", "13812345678"]:
                self.assertNotIn(sensitive, package_text)
                self.assertNotIn(sensitive, encrypted_text)

            sandbox_payload = json.loads(sandbox_path.read_text(encoding="utf-8"))
            import_result = validate_redaction_sandbox_payload(sandbox_payload)
            self.assertTrue(import_result["accepted"])
            self.assertEqual(import_result["project_alias_id"], "project_alpha")
            self.assertFalse(sandbox_payload["contains_original_files"])
            self.assertFalse(sandbox_payload["contains_local_mapping"])
            self.assertTrue(any(f["parser_status"] == "ocr_required" for f in sandbox_payload["files"]))

            mapping = decrypt_mapping_file(encrypted_mapping, passphrase="local-secret")
            redacted_text = "\n".join(block["text"] for block in sandbox_payload["redacted_text_blocks"])
            restored = restore_text(redacted_text, mapping)
            self.assertIn("配网智能监测项目", restored)
            self.assertIn("示例省电力公司", restored)
            self.assertIn("350万元", restored)
            self.assertIn("10kV", redacted_text)
            self.assertIn("30天", redacted_text)
            self.assertIn("downloadDecisions", review_html.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
