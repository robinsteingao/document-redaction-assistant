import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.workflow import build_redaction_package, restore_text


def write_minimal_docx(path: Path, body: str) -> None:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        f"<w:p><w:r><w:t>{body}</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", document_xml)


def write_minimal_xlsx(path: Path, rows: list[list[str]]) -> None:
    values = [cell for row in rows for cell in row]
    shared = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        + "".join(f"<si><t>{value}</t></si>" for value in values)
        + "</sst>"
    )
    idx = 0
    row_xml = []
    for r_idx, row in enumerate(rows, start=1):
        cells = []
        for c_idx, _ in enumerate(row):
            col = chr(ord("A") + c_idx)
            cells.append(f'<c r="{col}{r_idx}" t="s"><v>{idx}</v></c>')
            idx += 1
        row_xml.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData></worksheet>'
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("xl/sharedStrings.xml", shared)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)


def write_text_pdf(path: Path, text: str) -> None:
    path.write_bytes(
        (
            "%PDF-1.4\n"
            "1 0 obj <<>> stream\n"
            f"BT ({text}) Tj ET\n"
            "endstream endobj\n%%EOF"
        ).encode("utf-8")
    )


class M1WorkflowTests(unittest.TestCase):
    def test_build_package_redacts_identity_but_preserves_analysis_factors(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            docx = root / "project.docx"
            xlsx = root / "benefit.xlsx"
            pdf = root / "contract.pdf"
            write_minimal_docx(
                docx,
                "项目名称：配网智能监测项目。承担单位：国网四川省电力公司。"
                "技术指标：10kV线路故障定位误差≤1%，现场试运行30天。",
            )
            write_minimal_xlsx(
                xlsx,
                [["合同编号", "HT-2026-001"], ["合同金额", "350万元"], ["年度节约成本", "80万元"]],
            )
            write_text_pdf(pdf, "专利号：ZL202310123456.7，联系电话：13812345678。")

            package, mapping = build_redaction_package(
                [docx, xlsx, pdf],
                project_alias_id="2026-STPE-001",
            )

        serialized_package = json.dumps(package, ensure_ascii=False)
        serialized_mapping = json.dumps(mapping, ensure_ascii=False)

        self.assertNotIn("配网智能监测项目", serialized_package)
        self.assertNotIn("国网四川省电力公司", serialized_package)
        self.assertNotIn("HT-2026-001", serialized_package)
        self.assertNotIn("13812345678", serialized_package)
        self.assertIn("项目A", serialized_package)
        self.assertIn("单位A", serialized_package)
        self.assertIn("合同编号A", serialized_package)
        self.assertIn("100万至500万", serialized_package)
        self.assertIn("10kV", serialized_package)
        self.assertIn("≤1%", serialized_package)
        self.assertIn("30天", serialized_package)
        self.assertIn("配网智能监测项目", serialized_mapping)
        self.assertIn("国网四川省电力公司", serialized_mapping)
        self.assertEqual(package["project_alias_id"], "2026-STPE-001")
        self.assertTrue(package["analysis_preservation_flags"]["trl_factors_preserved"])
        self.assertTrue(package["analysis_preservation_flags"]["benefit_factors_preserved"])
        self.assertTrue(package["field_mappings_hash"])

    def test_restore_text_uses_local_mapping_without_server_package_values(self):
        mapping = {
            "items": [
                {"placeholder": "项目A", "original": "配网智能监测项目"},
                {"placeholder": "单位A", "original": "国网四川省电力公司"},
                {"placeholder": "金额区间A", "original": "350万元"},
            ]
        }

        restored = restore_text("项目A由单位A承担，合同金额为金额区间A。", mapping)

        self.assertEqual(restored, "配网智能监测项目由国网四川省电力公司承担，合同金额为350万元。")


if __name__ == "__main__":
    unittest.main()
