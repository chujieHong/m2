"""Day 16：混合解析文字层和图片，并保存逐页诊断。"""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from kb.ingestion import DocumentSection
from kb.pdf_parsing import parse_pdf


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument(
    "--pdf", type=Path,
    default=ROOT / "output" / "pdf" / "refund_policy_image_only.pdf",
)
args = parser.parse_args()
pdf_path = args.pdf
pages = parse_pdf(pdf_path)
sections = []

for page in pages:
    print(f"\n===== 第 {page.page} 页 =====")
    print(
        f"文字层字符数：{len(page.native_text)}，图片数：{page.image_count}，"
        f"OCR 区域数：{page.ocr_regions}，去重行数：{page.duplicates_removed}"
    )
    for note in page.warnings:
        print("检查提示：", note)
    print(page.text)
    if page.text:
        sections.append(DocumentSection(
            text=page.text, source=pdf_path.name, page=page.page,
        ))

output_dir = ROOT / "data" / "day16"
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / f"{pdf_path.stem}_parse.json"
output_path.write_text(
    json.dumps({
        "source": pdf_path.name,
        "pages": [asdict(page) for page in pages],
        "sections": [asdict(section) for section in sections],
    }, ensure_ascii=False, indent=2, allow_nan=False),
    encoding="utf-8",
)
print(f"\n获得 {len(sections)} 个页面文本，诊断已保存：{output_path}")
