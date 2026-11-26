from collections import Counter
from pathlib import Path
from rapidocr import RapidOCR
import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
pdf_path = ROOT / "output" / "pdf" / "day16_mixed_sample.pdf"

edge_counts = Counter()
engine = None
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        left, top, right, bottom = page.bbox
        height = bottom - top

        bands = [
            (left, top, right, top + height * 0.15),
            (left, bottom - height * 0.10, right, bottom),
        ]

        edge_lines = set()

        for bbox in bands:
            region = page.crop(bbox)
            text = region.extract_text() or ""
            lines = text.splitlines()

            if region.images:
                if engine is None:
                    engine = RapidOCR()

                rendered = region.to_image(resolution=144)

                try:
                    with rendered.original.convert("RGB") as bitmap:
                        result = engine(bitmap)
                finally:
                    rendered.original.close()

                if result.txts:
                    lines.extend(result.txts)
                else:
                    print(
                        f"第 {page.page_number} 页的一个边缘区域"
                        "包含图片，但 OCR 没有读到文字，需要检查。"
                    )

            for line in lines:
                line = line.strip()
                if line:
                    edge_lines.add(line)

        edge_counts.update(edge_lines)

for line, page_count in edge_counts.items():
    if page_count >= 3:
        print(f"候选内容：{line}，出现于 {page_count} 页")