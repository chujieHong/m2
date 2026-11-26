# Day 4：文档读取与统一数据结构。
from dataclasses import dataclass
import re
from pathlib import Path
import warnings
from docx import Document
from kb.pdf_parsing import parse_pdf

@dataclass
class DocumentSection:
    text: str
    source: str
    page: int | None = None
    heading_path: tuple[str, ...] = ()
    
def load_markdown(path: Path) -> list[DocumentSection]:
    document = path.read_text(encoding="utf-8")

    sections: list[DocumentSection] = []
    headings: list[tuple[int, str]] = []
    lines: list[str] = []

    def save_section() -> None:
        text = "\n".join(lines).strip()

        if text:
            sections.append(
                DocumentSection(
                    text=text,
                    source=path.name,
                    heading_path=tuple(
                        title for _, title in headings
                    ),
                )
            )

    for line in document.splitlines():
        match = re.match(r"^(#{1,6})[ \t]+(.+)$", line)

        if match is None:
            lines.append(line)
            continue

        save_section()
        lines.clear()

        level = len(match.group(1))
        title = match.group(2).strip()

        while headings and headings[-1][0] >= level:
            headings.pop()

        headings.append((level, title))

    save_section()
    return sections
    
def load_pdf(path: Path) -> list[DocumentSection]:
    sections: list[DocumentSection] = []

    for page in parse_pdf(path):
        for note in page.warnings:
            warnings.warn(f"{path.name} 第 {page.page} 页：{note}", stacklevel=2)
        if page.text:
            sections.append(
                DocumentSection(
                    text=page.text,
                    source=path.name,
                    page=page.page,
                )
            )

        for table in page.tables:
            for row_number, text in table.rows:
                sections.append(
                    DocumentSection(
                        text=text,
                        source=path.name,
                        page=page.page,
                        heading_path=(
                            path.stem,
                            f"表格{table.table_number}",
                            f"数据行{row_number}",
                        ),
                    )
                )

    return sections
    
def load_docx(path: Path) -> list[DocumentSection]:
    document = Document(str(path))

    sections: list[DocumentSection] = []
    headings: list[tuple[int, str]] = []
    lines: list[str] = []

    def save_section() -> None:
        text = "\n".join(lines).strip()

        if text:
            sections.append(
                DocumentSection(
                    text=text,
                    source=path.name,
                    heading_path=tuple(
                        title for _, title in headings
                    ),
                )
            )

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if not text:
            continue

        style_name = (
            paragraph.style.name or ""
            if paragraph.style is not None
            else ""
        )
        match = re.match(
            r"^Heading ([1-9])$",
            style_name,
        )

        if match is None:
            lines.append(text)
            continue

        save_section()
        lines.clear()

        level = int(match.group(1))

        while headings and headings[-1][0] >= level:
            headings.pop()

        headings.append((level, text))

    save_section()
    return sections
    
def load_document(path: Path) -> list[DocumentSection]:
    suffix = path.suffix.lower()

    if suffix == ".md":
        return load_markdown(path)

    if suffix == ".pdf":
        return load_pdf(path)

    if suffix == ".docx":
        return load_docx(path)

    raise ValueError(f"不支持的文件格式：{suffix}")
