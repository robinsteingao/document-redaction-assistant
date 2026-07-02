from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Entity:
    kind: str
    original: str
    placeholder_prefix: str
    strategy: str
    replacement_hint: str | None = None


LABEL_PATTERNS = [
    ("project_name", "项目", "pseudonym", re.compile(r"项目名称[:：]\s*([^。；;，,\n|]+)")),
    ("organization", "单位", "pseudonym", re.compile(r"(?:承担单位|项目单位|合作单位|应用单位)[:：]\s*([^。；;，,\n|]+)")),
    ("person", "人员", "pseudonym", re.compile(r"(?:联系人|负责人|项目负责人|经办人)[:：]\s*([\u4e00-\u9fa5]{2,4})")),
    ("amount", "金额区间", "range", re.compile(r"(?:Amount|Budget|Cost|Revenue|金额|合同金额|预算|收益)[:：]\s*(\$?\s*\d+(?:\.\d+)?\s*(?:亿元|万元|元|USD|RMB|CNY|dollars?)?)", re.IGNORECASE)),
]

REGEX_PATTERNS = [
    ("id_card", "身份证", "mask", re.compile(r"\b[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b")),
    ("bank_card", "银行卡", "mask", re.compile(r"\b(?:4[0-9]{12,18}|5[1-5][0-9]{14,17}|3[47][0-9]{13}|3[068][0-9]{12}|6(?:011|5[0-9]{2})[0-9]{12,15}|62[0-9]{14,17}|(?:2131|1800|35\d{3})\d{11})\b")),
    ("passport", "护照", "mask", re.compile(r"\b[GEDSMPFT]\d{7,8}\b", re.IGNORECASE)),
    ("unified_social_credit_code", "信用代码", "pseudonym", re.compile(r"\b[0-9A-HJ-NP-RTUW-Y]{2}\d{6}[0-9A-HJ-NP-RTUW-Y]{10}\b", re.IGNORECASE)),
    ("address", "地址", "mask", re.compile(r"(?:北京市|天津市|上海市|重庆市|河北省|山西省|辽宁省|吉林省|黑龙江省|江苏省|浙江省|安徽省|福建省|江西省|山东省|河南省|湖北省|湖南省|广东省|海南省|四川省|贵州省|云南省|陕西省|甘肃省|青海省|台湾省|内蒙古自治区|广西壮族自治区|西藏自治区|宁夏回族自治区|新疆维吾尔自治区|香港特别行政区|澳门特别行政区)[\u4e00-\u9fa5A-Za-z0-9（）()\-]{2,60}(?:路|街|道|巷|号|室|楼|层|村|镇|区|县|市)")),
    ("contract_id", "合同编号", "pseudonym", re.compile(r"\bHT-\d{4}-\d{3,}\b", re.IGNORECASE)),
    ("phone", "电话", "mask", re.compile(r"\b1[3-9]\d{9}\b")),
    ("email", "邮箱", "mask", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("patent_id", "专利", "pseudonym", re.compile(r"\b(?:ZL|CN)\d{9,13}(?:\.\d)?\b", re.IGNORECASE)),
    ("software_copyright", "软著", "pseudonym", re.compile(r"\b\d{4}SR\d{5,8}\b", re.IGNORECASE)),
    ("amount", "金额区间", "range", re.compile(r"(?<![A-Za-z0-9])\d+(?:\.\d+)?\s*(?:亿元|万元|元)")),
    ("technical_metric", "技术指标", "keep", re.compile(r"(?:≤|>=|≥|<=)?\s*\d+(?:\.\d+)?\s*(?:kV|KV|%|％|次|天|小时|h|MW|kW|MWh|kWh)")),
    ("validation_evidence", "验证信息", "keep", re.compile(r"(?:试运行|现场验证|示范应用|第三方检测|验收结论)[^。；;\n]{0,30}")),
]

TECHNICAL_SIGNAL = re.compile(r"(?:kV|KV|误差|精度|试运行|试验|验证|达标|样机|现场|≤|>=|%|％|\d+\s*天)")


def detect_entities(texts: Iterable[str]) -> list[Entity]:
    seen: set[tuple[str, str]] = set()
    entities: list[Entity] = []
    for text in texts:
        for kind, prefix, strategy, pattern in LABEL_PATTERNS:
            for match in pattern.finditer(text):
                value = _clean_labeled_value(match.group(1))
                _append(entities, seen, Entity(kind, value, prefix, strategy))
        for kind, prefix, strategy, pattern in REGEX_PATTERNS:
            for match in pattern.finditer(text):
                value = match.group(0).strip()
                hint = amount_range(value) if kind == "amount" else None
                _append(entities, seen, Entity(kind, value, prefix, strategy, hint))
    # Replace longer entities first to avoid replacing sub-parts inside label values.
    return sorted(entities, key=lambda e: (-len(e.original), e.kind, e.original))


def detect_entities_with_dictionary(texts: Iterable[str], customer_dictionary: Path | str | dict | None = None) -> list[Entity]:
    buffered = list(texts)
    entities = detect_entities(buffered)
    dictionary = load_customer_dictionary(customer_dictionary)
    seen = {(entity.kind, entity.original) for entity in entities}
    joined = "\n".join(buffered)
    for kind, values in dictionary.items():
        prefix = {
            "organization": "单位",
            "project_name": "项目",
            "person": "人员",
            "technical_term": "技术要素",
        }.get(kind, "自定义")
        for value in values:
            value = str(value).strip()
            if value and value in joined and (kind, value) not in seen:
                seen.add((kind, value))
                entities.append(Entity(kind, value, prefix, "pseudonym"))
    return sorted(entities, key=lambda e: (-len(e.original), e.kind, e.original))


def load_customer_dictionary(customer_dictionary: Path | str | dict | None) -> dict[str, list[str]]:
    if not customer_dictionary:
        return {}
    if isinstance(customer_dictionary, dict):
        data = customer_dictionary
    else:
        data = json.loads(Path(customer_dictionary).read_text(encoding="utf-8"))
    normalized: dict[str, list[str]] = {}
    for kind, values in data.items():
        if isinstance(values, str):
            normalized[str(kind)] = [values]
        elif isinstance(values, list):
            normalized[str(kind)] = [str(v) for v in values if str(v).strip()]
    return normalized


def contains_technical_signal(text: str) -> bool:
    return bool(TECHNICAL_SIGNAL.search(text or ""))


def _append(entities: list[Entity], seen: set[tuple[str, str]], entity: Entity) -> None:
    if not entity.original:
        return
    key = (entity.kind, entity.original)
    if key not in seen:
        seen.add(key)
        entities.append(entity)


def _clean_labeled_value(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^(为|是)\s*", "", value)
    return value.strip(" ：:，,。；;")


def amount_range(value: str) -> str:
    number_match = re.search(r"\d+(?:\.\d+)?", value)
    if not number_match:
        return "金额区间未知"
    number = float(number_match.group(0))
    unit = "元"
    normalized = value.lower()
    if "亿元" in value:
        number *= 10000
        unit = "万元"
    elif "万元" in value:
        unit = "万元"
    elif "元" in value:
        number /= 10000
        unit = "万元"
    elif "$" in value or "usd" in normalized or "dollar" in normalized:
        number = number * 7.2 / 10000
        unit = "万元"
    elif "rmb" in normalized or "cny" in normalized:
        number /= 10000
        unit = "万元"

    if number < 10:
        label = "低于10万"
    elif number < 50:
        label = "10万至50万"
    elif number < 100:
        label = "50万至100万"
    elif number < 500:
        label = "100万至500万"
    elif number < 1000:
        label = "500万至1000万"
    elif number < 5000:
        label = "1000万至5000万"
    else:
        label = "高于5000万"
    return label if unit in {"万元", "外币金额"} else label
