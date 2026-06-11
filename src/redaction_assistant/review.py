from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any, Iterable

from .parsers import parse_file
from .impact import ASSESSMENT_IMPACT
from .redactor import candidate_id_for
from .rules import detect_entities_with_dictionary
from .workflow import build_restore_preview, build_review_report


def build_review_workspace(
    files: Iterable[Path | str],
    *,
    project_alias_id: str,
    customer_dictionary: Path | str | dict | None = None,
) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    for file in files:
        parsed_blocks, item = parse_file(Path(file))
        blocks.extend(parsed_blocks)
        manifest.append(item)
    entities = detect_entities_with_dictionary(
        (block.get("text", "") for block in blocks),
        customer_dictionary=customer_dictionary,
    )
    candidates = []
    for entity in entities:
        candidates.append({
            "candidate_id": candidate_id_for(entity),
            "kind": entity.kind,
            "original": entity.original,
            "default_strategy": entity.strategy,
            "recommended_action": "keep" if entity.strategy == "keep" else "redact",
            "placeholder_prefix": entity.placeholder_prefix,
            "preservation_value": entity.replacement_hint,
            "review_hint": _review_hint(entity.kind, entity.strategy),
            "impact": ASSESSMENT_IMPACT.get(entity.kind, {"domain": "other", "level": "low"}),
        })
    return {
        "schema_version": "redaction_review_workspace.v1",
        "project_alias_id": project_alias_id,
        "source_file_manifest": manifest,
        "review_candidates": candidates,
    }


def review_decisions_from_mapping(raw: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    for candidate_id, decision in raw.items():
        action = decision.get("action", "redact")
        strategy = decision.get("strategy")
        if action not in {"redact", "keep"}:
            action = "redact"
        if strategy not in {None, "pseudonym", "mask", "range", "keep"}:
            strategy = None
        decisions[str(candidate_id)] = {"action": action, "strategy": strategy}
    return decisions


def export_review_workspace(
    output_dir: Path | str,
    package: dict[str, Any],
    mapping: dict[str, Any],
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    candidates_path = output / "review_candidates.json"
    preview_path = output / "restore_preview.json"
    html_path = output / "review_workspace.html"
    report_path = output / "redaction_review_report.md"

    candidates = _mapping_to_candidates(mapping, package)
    preview = build_restore_preview(package, mapping)
    candidates_path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    preview_path.write_text(json.dumps(preview, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_review_report(package), encoding="utf-8")
    html_path.write_text(_render_review_html(package, candidates, preview), encoding="utf-8")
    return {
        "review_candidates": candidates_path,
        "restore_preview": preview_path,
        "review_html": html_path,
        "review_report": report_path,
    }


def _mapping_to_candidates(mapping: dict[str, Any], package: dict[str, Any] | None = None) -> dict[str, Any]:
    items = [
        {
            "candidate_id": item.get("candidate_id"),
            "kind": item.get("kind"),
            "placeholder": item.get("placeholder"),
            "replacement": item.get("replacement"),
            "strategy": item.get("strategy"),
            "preservation_value": item.get("preservation_value"),
            "impact_level": ASSESSMENT_IMPACT.get(str(item.get("kind")), {}).get("level", "low"),
            "impact_message": ASSESSMENT_IMPACT.get(str(item.get("kind")), {}).get("message", "请复核是否影响评价。"),
        }
        for item in mapping.get("items", [])
    ]
    seen = {item.get("candidate_id") for item in items}
    for impact_item in (package or {}).get("redaction_impact_summary", {}).get("items", []):
        candidate_id = impact_item.get("candidate_id")
        if candidate_id in seen:
            continue
        items.append({
            "candidate_id": candidate_id,
            "kind": impact_item.get("kind"),
            "placeholder": "",
            "replacement": "",
            "strategy": impact_item.get("strategy") or "keep",
            "preservation_value": None,
            "impact_level": impact_item.get("impact_level"),
            "impact_message": impact_item.get("message"),
        })
    return {
        "schema_version": "redaction_review_candidates.v1",
        "items": items,
    }


def _review_hint(kind: str, strategy: str) -> str:
    if kind == "amount":
        return "金额影响效益分析，推荐区间化；强脱敏会降低经济性判断可信度。"
    if kind in {"technical_metric", "validation_evidence"}:
        return "该字段参与 STPE-AI 评价，默认建议保留；如涉及密级可选择脱敏，但需确认评价降级风险。"
    if kind in {"project_name", "organization", "contract_id", "phone", "email"}:
        return "身份识别字段，推荐稳定假名化或强脱敏。"
    if kind == "patent_id":
        return "知识产权字段，推荐保留类型和数量，隐藏真实编号。"
    if strategy == "range":
        return "建议保留区间或比例，避免评估因子丢失。"
    return "请复核是否需要脱敏。"


KIND_LABELS = {
    "amount": "金额信息",
    "technical_metric": "技术指标",
    "validation_evidence": "验证/试验信息",
    "project_name": "项目名称",
    "organization": "单位名称",
    "contract_id": "合同编号",
    "phone": "联系电话",
    "email": "电子邮箱",
    "patent_id": "专利/知识产权编号",
    "person": "人员姓名",
    "software_copyright": "软件著作权编号",
    "technical_term": "技术术语",
}

STRATEGY_LABELS = {
    "pseudonym": "替换为假名",
    "mask": "遮盖隐藏",
    "range": "保留区间",
    "keep": "保留原样",
}

IMPACT_LABELS = {
    "none": "无明显影响",
    "low": "低影响",
    "medium": "中等影响",
    "high": "高影响",
}


def _kind_label(kind: Any) -> str:
    text = str(kind or "")
    return KIND_LABELS.get(text, text or "未分类字段")


def _strategy_label(strategy: Any) -> str:
    text = str(strategy or "")
    return STRATEGY_LABELS.get(text, text or "按默认方式处理")


def _impact_label(level: Any) -> str:
    text = str(level or "")
    return IMPACT_LABELS.get(text, text or "需人工判断")


def _yes_no(value: Any) -> str:
    return "是" if value is True else "否" if value is False else str(value or "未返回")


def _render_review_html(package: dict[str, Any], candidates: dict[str, Any], preview: dict[str, Any]) -> str:
    rows = []
    for item in candidates.get("items", []):
        rows.append(
            "<tr>"
            f"<td>{escape(_kind_label(item.get('kind')))}</td>"
            f"<td>{escape(str(item.get('placeholder') or ''))}</td>"
            f"<td>{escape(_strategy_label(item.get('strategy')))}</td>"
            f"<td>{escape(str(item.get('preservation_value') or ''))}</td>"
            f"<td>{escape(_impact_label(item.get('impact_level')))}</td>"
            f"<td>{escape(str(item.get('impact_message') or ''))}</td>"
            "</tr>"
        )
    warnings = "".join(f"<li>{escape(str(w))}</li>" for w in package.get("review_warnings", [])) or "<li>未发现阻断性脱敏风险。</li>"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>文档安全脱敏助手 - 字段复核</title>
  <style>
    :root {{
      --ink:#101820; --muted:#5d6873; --line:#d8e0e8; --panel:#f7f9fb;
      --accent:#0f766e; --warn:#b45309;
    }}
    body {{ margin:0; font-family:"Microsoft YaHei", "Segoe UI", sans-serif; color:var(--ink); background:#eef3f6; }}
    main {{ max-width:1080px; margin:0 auto; padding:28px; }}
    h1 {{ margin:0 0 8px; font-size:26px; }}
    h2 {{ margin-top:26px; font-size:18px; }}
    .summary {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:18px 0; }}
    .metric {{ background:white; border:1px solid var(--line); border-radius:8px; padding:14px; }}
    .metric strong {{ display:block; font-size:18px; margin-top:4px; }}
    section {{ background:white; border:1px solid var(--line); border-radius:8px; padding:18px; margin:14px 0; }}
    table {{ width:100%; border-collapse:collapse; table-layout:fixed; }}
    th, td {{ border-bottom:1px solid var(--line); padding:10px; text-align:left; word-break:break-word; }}
    th {{ background:var(--panel); }}
    .preview {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
    pre {{ white-space:pre-wrap; background:#0f172a; color:#e2e8f0; padding:14px; border-radius:8px; min-height:130px; }}
    .warn li {{ color:var(--warn); margin:6px 0; }}
  </style>
</head>
<body>
<main>
  <h1>字段复核</h1>
    <p>项目代号：{escape(str(package.get("project_alias_id") or ""))}</p>
  <div class="summary">
    <div class="metric">识别字段<strong>{len(candidates.get("items", []))}</strong></div>
    <div class="metric">映射表是否上传<strong>{escape(_yes_no(package.get("redaction_policy", {}).get("mapping_uploaded")))}</strong></div>
    <div class="metric">技术评价信息是否保留<strong>{escape(_yes_no(package.get("analysis_preservation_flags", {}).get("trl_factors_preserved")))}</strong></div>
    <div class="metric">效益评价信息是否保留<strong>{escape(_yes_no(package.get("analysis_preservation_flags", {}).get("benefit_factors_preserved")))}</strong></div>
  </div>
  <section>
    <h2>候选字段</h2>
    <p>本页可用于本地复核。需要调整处理方式时，可点击下方“导出复核选择文件”，用记事本打开 <code>review_decisions.json</code>，按说明修改后粘贴回产品界面的“自定义字段处理方式”。</p>
    <table>
      <thead><tr><th>字段类别</th><th>脱敏显示名</th><th>处理方式</th><th>保留的评价信息</th><th>影响程度</th><th>评价影响提示</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </section>
  <section>
    <h2>评估影响</h2>
    <ul class="warn">{warnings}</ul>
  </section>
  <section>
    <h2>本地还原预演</h2>
    <div class="preview">
      <div><h3>脱敏版</h3><pre>{escape(preview.get("redacted_preview", ""))}</pre></div>
      <div><h3>还原版</h3><pre>{escape(preview.get("restored_preview", ""))}</pre></div>
    </div>
  </section>
  <section>
    <h2>复核选择文件（JSON）</h2>
    <textarea id="decisions" style="width:100%;min-height:150px;border:1px solid var(--line);border-radius:8px;padding:12px;">{escape(_default_decisions_json(candidates))}</textarea>
    <p><button onclick="downloadDecisions()" style="padding:9px 14px;border:0;border-radius:6px;background:var(--accent);color:white;">导出复核选择文件</button></p>
  </section>
</main>
<script>
function downloadDecisions() {{
  const blob = new Blob([document.getElementById('decisions').value], {{type: 'application/json'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'review_decisions.json';
  a.click();
  URL.revokeObjectURL(url);
}}
</script>
</body>
</html>"""


def _default_decisions_json(candidates: dict[str, Any]) -> str:
    decisions = {}
    for item in candidates.get("items", []):
        candidate_id = item.get("candidate_id")
        if candidate_id:
            decisions[candidate_id] = {
                "action": "keep" if item.get("strategy") == "keep" else "redact",
                "strategy": item.get("strategy") or "pseudonym",
            }
    return json.dumps(decisions, ensure_ascii=False, indent=2)
