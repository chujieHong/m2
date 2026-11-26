from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
pdf_path = ROOT / "output" / "pdf" / "refund_policy_image_only.pdf"

reader = PdfReader(pdf_path)

print("PDF 总页数：", len(reader.pages))

for page_number, page in enumerate(reader.pages, start=1):
    text = page.extract_text() or ""

    print(f"\n===== 第 {page_number} 页 =====")
    print("提取字符数：", len(text.strip()))
    print("原始文本：", repr(text))

    image_count = len(page.images)
    print("可枚举的图片数量：", image_count)

    if not text.strip():
        if image_count > 0:
            print("提示：没有提取到文字，但包含图片，可能需要 OCR。")
        else:
            print("提示：没有提取到文字或图片，需要查看页面确认。")