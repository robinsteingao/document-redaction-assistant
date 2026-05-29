from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from statistics import mean
from typing import Any, Callable


def get_ocr_status() -> dict[str, Any]:
    configured = os.getenv("DRA_OCR_ENGINE", "").strip().lower()
    rapidocr_available = importlib.util.find_spec("rapidocr_onnxruntime") is not None
    paddleocr_available = importlib.util.find_spec("paddleocr") is not None
    if configured:
        available = (
            (configured == "rapidocr" and rapidocr_available)
            or (configured == "paddleocr" and paddleocr_available)
        )
        return {
            "status": "available" if available else "not_configured",
            "engine": configured,
            "rapidocr_available": rapidocr_available,
            "paddleocr_available": paddleocr_available,
            "required_for_text_pdf": False,
            "message": "OCR 引擎可用。" if available else "已配置 OCR 引擎但当前环境未安装对应依赖。",
        }
    return {
        "status": "not_configured",
        "engine": None,
        "rapidocr_available": rapidocr_available,
        "paddleocr_available": paddleocr_available,
        "required_for_text_pdf": False,
        "message": "未配置 OCR 引擎；文本型 PDF、DOCX、XLSX 不受影响，扫描件需后续接入 OCR。",
    }


def extract_text_with_ocr(
    path: Path | str,
    engine: Any | None = None,
    engine_loader: Callable[[str], Any] | None = None,
    max_pages: int | None = None,
) -> dict[str, Any]:
    target = Path(path)
    if engine is not None:
        result = engine.extract_text(target)
        return {
            "status": result.get("status", "ok"),
            "engine": result.get("engine", getattr(engine, "name", "custom")),
            "text": result.get("text", ""),
            "confidence": float(result.get("confidence", 0.0) or 0.0),
        }
    configured = os.getenv("DRA_OCR_ENGINE", "").strip().lower()
    status = get_ocr_status()
    if status["status"] != "available" and engine_loader is None:
        return {
            "status": "unavailable",
            "engine": status.get("engine"),
            "text": "",
            "confidence": 0.0,
            "message": status.get("message"),
        }
    if configured == "rapidocr":
        ocr = engine_loader("rapidocr") if engine_loader else _load_rapidocr()
        try:
            return _extract_with_rapidocr(target, ocr, max_pages=max_pages)
        except Exception as exc:
            return _ocr_failed("rapidocr", exc)
    if configured == "paddleocr":
        ocr = engine_loader("paddleocr") if engine_loader else _load_paddleocr()
        try:
            return _extract_with_paddleocr(target, ocr, max_pages=max_pages)
        except Exception as exc:
            return _ocr_failed("paddleocr", exc)
    return {
        "status": "unavailable",
        "engine": configured or status.get("engine"),
        "text": "",
        "confidence": 0.0,
        "message": "当前 OCR 引擎未启用真实抽取适配。",
    }


def _load_rapidocr() -> Any:
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def _load_paddleocr() -> Any:
    from paddleocr import PaddleOCR

    return PaddleOCR(use_angle_cls=True, lang="ch")


def _extract_with_rapidocr(path: Path, ocr: Any, *, max_pages: int | None = None) -> dict[str, Any]:
    with _ocr_input_paths(path, engine="rapidocr", max_pages=max_pages) as prepared:
        if prepared["status"] != "ok":
            return prepared
        page_results = [_rapidocr_image(target, ocr) for target in prepared["paths"]]
    return _merge_page_results("rapidocr", page_results)


def _rapidocr_image(path: Path, ocr: Any) -> dict[str, Any]:
    result, _ = ocr(str(path))
    lines = []
    confidences = []
    for item in result or []:
        if len(item) >= 3:
            lines.append(str(item[1]))
            confidences.append(float(item[2] or 0.0))
    return {
        "status": "ok" if lines else "empty",
        "engine": "rapidocr",
        "text": "\n".join(lines),
        "confidence": sum(confidences) / len(confidences) if confidences else 0.0,
    }


def _extract_with_paddleocr(path: Path, ocr: Any, *, max_pages: int | None = None) -> dict[str, Any]:
    with _ocr_input_paths(path, engine="paddleocr", max_pages=max_pages) as prepared:
        if prepared["status"] != "ok":
            return prepared
        page_results = [_paddleocr_image(target, ocr) for target in prepared["paths"]]
    return _merge_page_results("paddleocr", page_results)


def _paddleocr_image(path: Path, ocr: Any) -> dict[str, Any]:
    result = ocr.ocr(str(path), cls=True)
    lines = []
    confidences = []
    for page in result or []:
        for item in page or []:
            if len(item) >= 2 and len(item[1]) >= 2:
                lines.append(str(item[1][0]))
                confidences.append(float(item[1][1] or 0.0))
    return {
        "status": "ok" if lines else "empty",
        "engine": "paddleocr",
        "text": "\n".join(lines),
        "confidence": sum(confidences) / len(confidences) if confidences else 0.0,
    }


@contextmanager
def _ocr_input_paths(path: Path, engine: str, max_pages: int | None = None):
    if path.suffix.lower() != ".pdf":
        yield {"status": "ok", "paths": [path]}
        return
    if not _module_available("pypdfium2"):
        yield {
            "status": "unsupported",
            "engine": engine,
            "text": "",
            "confidence": 0.0,
            "message": "PDF OCR 需要 pypdfium2 渲染组件，当前离线包未启用该组件。",
        }
        return
    import pypdfium2

    max_pages = _pdf_ocr_max_pages(max_pages)
    with tempfile.TemporaryDirectory(prefix="dra_pdf_ocr_") as td:
        doc = pypdfium2.PdfDocument(str(path))
        try:
            page_count = len(doc)
            paths: list[Path] = []
            for index in range(min(page_count, max_pages)):
                image_path = Path(td) / f"page_{index + 1:04d}.png"
                doc[index].render(scale=2.0).to_pil().save(str(image_path))
                paths.append(image_path)
            yield {
                "status": "ok",
                "paths": paths,
                "page_count": page_count,
                "pages_processed": len(paths),
                "page_limit_reached": page_count > len(paths),
            }
        finally:
            close = getattr(doc, "close", None)
            if callable(close):
                close()


def _pdf_ocr_max_pages(override: int | None = None) -> int:
    if override is not None:
        return max(1, int(override))
    raw = os.getenv("DRA_OCR_MAX_PAGES", "5").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 5


def _module_available(name: str) -> bool:
    if name in sys.modules:
        return True
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _merge_page_results(engine: str, page_results: list[dict[str, Any]]) -> dict[str, Any]:
    lines = [result.get("text", "") for result in page_results if result.get("text")]
    confidences = [
        float(result.get("confidence", 0.0) or 0.0)
        for result in page_results
        if float(result.get("confidence", 0.0) or 0.0) > 0
    ]
    return {
        "status": "ok" if lines else "empty",
        "engine": engine,
        "text": "\n".join(lines),
        "confidence": mean(confidences) if confidences else 0.0,
        "pages_processed": len(page_results),
    }


def _ocr_failed(engine: str, exc: Exception) -> dict[str, Any]:
    return {
        "status": "failed",
        "engine": engine,
        "text": "",
        "confidence": 0.0,
        "message": f"{type(exc).__name__}: {exc}",
    }
