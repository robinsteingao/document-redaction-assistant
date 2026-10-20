"""仅用标准库完成启动前检查；可由未安装依赖的 Python 直接执行。"""
from __future__ import annotations

import importlib
import importlib.metadata
import re
import sys


REQUIREMENTS = {
    "pypdf": ((4, 0, 0), None),
    "defusedxml": ((0, 7, 1), None),
    "cryptography": ((41, 0, 0), (43, 0, 0)),
}


def check_core_dependencies() -> tuple[int, list[str]]:
    errors = []
    incompatible = sys.version_info < (3, 10)
    if incompatible:
        errors.append("需要 Python 3.10 或更新版本")
    for name, (minimum, maximum) in REQUIREMENTS.items():
        try:
            raw = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            errors.append(f"缺少依赖：{name}")
            continue
        match = re.fullmatch(r"(\d+)\.(\d+)(?:\.(\d+))?", raw)
        version = tuple(int(p or 0) for p in match.groups()) if match else None
        if version is None or version < minimum or (maximum and version >= maximum):
            incompatible = True
            errors.append(f"依赖版本不兼容：{name} {raw}")
        try:
            importlib.import_module(name)
        except Exception:
            errors.append(f"依赖无法导入：{name}")
    return (2 if incompatible else 1 if errors else 0), errors


if __name__ == "__main__":
    code, errors = check_core_dependencies()
    for error in errors:
        print(error)
    raise SystemExit(code)
