"""Day 16：合并 PDF 文字层与图片 OCR，不重建表格或解释图形关系。"""
from kb.text_cleaning import normalize_letters_and_digits
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
import re
import unicodedata
from typing import Any
from kb.pdf_tables import table_to_text_rows
import pdfplumber
from PIL import Image


@dataclass
class ParsedPDFTable:
    table_number: int
    bbox: tuple[float, float, float, float]
    rows: list[tuple[int, str]]


@dataclass
class ParsedPDFPage:
    page: int
    native_text: str
    ocr_text: str
    text: str
    image_count: int
    ocr_regions: int
    duplicates_removed: int
    warnings: list[str] = field(default_factory=list)
    tables: list[ParsedPDFTable] = field(default_factory=list)

def _comparison_key(text: str) -> str:
    # 只在比较时忽略空白和全/半角差异，不改写原始正文。
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


def _normalize_time_ranges(text: str) -> str:
    # 沿用已核对的时间连接符规则；native_text/ocr_text 保留未改写结果。
    return re.sub(
        r"(\d{2}:\d{2})\s*[一—–－]\s*(\d{2}:\d{2})",
        r"\1-\2", text,
    )


def parse_pdf(
    path: Path,
    *,
    ocr: Callable[[Image.Image], list[str]] | None = None,
) -> list[ParsedPDFPage]:
    """文字层和图片都读取，返回所有页的正文与诊断。

    ocr 可传入测试替身。图片中的新文字追加在文字层之后，
    不承诺多栏、复杂图表的阅读顺序。
    """
    engine: Any = None

    def recognize(image: Image.Image) -> list[str]:
        nonlocal engine
        if ocr is not None:
            return ocr(image)
        if engine is None:
            from rapidocr import RapidOCR

            engine = RapidOCR()
        result = engine(image)
        return list(result.txts) if result.txts else []

    pages: list[ParsedPDFPage] = []
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            native_text = (page.extract_text() or "").strip()
            notes: list[str] = []
            boxes: list[tuple[float, float, float, float]] = []
            tables = []

            for table_number, table in enumerate(page.find_tables(), start=1):
                try:
                    rows = table_to_text_rows(
                        table.extract(),
                        title=path.stem,
                    )
                except ValueError as error:
                    notes.append(f"表格 {table_number} 未转换：{error}")
                    continue

                if not rows:
                    notes.append(f"表格 {table_number} 没有可转换的数据行。")
                    continue

                tables.append(
                    ParsedPDFTable(
                        table_number=table_number,
                        bbox=table.bbox,
                        rows=rows,
                    )
                )
            # 表格行已单独保存；这里只排除普通正文中的同一份表格字符。
            def outside_tables(obj: dict[str, Any]) -> bool:
                if obj.get("object_type") != "char":
                    return True

                for table in tables:
                    left, top, right, bottom = table.bbox

                    if (
                        left <= obj["x0"]
                        and obj["x1"] <= right
                        and top <= obj["top"]
                        and obj["bottom"] <= bottom
                    ):
                        return False

                return True

            body_text = (
                page.filter(outside_tables).extract_text() or ""
            ).strip()
            for image in page.images:
                bbox = (
                    max(float(image["x0"]), float(page.bbox[0])),
                    max(float(image["top"]), float(page.bbox[1])),
                    min(float(image["x1"]), float(page.bbox[2])),
                    min(float(image["bottom"]), float(page.bbox[3])),
                )
                if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
                    notes.append("图片区域无效，需要检查原页。")
                elif bbox not in boxes:
                    boxes.append(bbox)

            # 没有文字也没有可枚举图片时，整页尝试一次。
            # 仍不能据此区分空白页和未识别出的内容。
            if not boxes and not native_text:
                x0, top, x1, bottom = page.bbox
                boxes.append((float(x0), float(top), float(x1), float(bottom)))

            raw_lines: list[str] = []
            added_lines: list[str] = []
            duplicates_removed = 0

            for bbox in boxes:
                region = page.crop(bbox)
                region_native = _comparison_key(region.extract_text() or "")
                rendered = region.to_image(resolution=144)
                try:
                    # 传入普通 RGB 图片，避免将调色板索引交给 OCR。
                    with rendered.original.convert("RGB") as bitmap:
                        lines = recognize(bitmap)
                finally:
                    rendered.original.close()

                if not lines:
                    notes.append("某图片/渲染区域未识别到文字，可能无字或识别失败。")

                added_in_region = False
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    raw_lines.append(line)
                    key = _comparison_key(line)
                    # 只和同一区域的文字层比较，不跨区域、不做模糊去重。
                    if key and key in region_native:
                        duplicates_removed += 1
                    else:
                        added_lines.append(line)
                        added_in_region = True

                if region_native and added_in_region:
                    notes.append("图片识别结果与重叠文字层未完全对应，已保留两者，需要核对。")

            text = "\n".join(
                part for part in [body_text, "\n".join(added_lines)] if part
            )
            text = _normalize_time_ranges(text)
            text = normalize_letters_and_digits(text)
            if not text and not tables:
                notes.append("整页没有得到正文，需要检查，不能直接认定为空白。")

            pages.append(ParsedPDFPage(
                page=page_number,
                native_text=native_text,
                ocr_text="\n".join(raw_lines),
                text=text,
                image_count=len(page.images),
                ocr_regions=len(boxes),
                duplicates_removed=duplicates_removed,
                warnings=notes,
                tables=tables,
            ))

    return pages
