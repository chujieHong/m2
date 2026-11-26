from pathlib import Path
from kb.bm25 import BM25
import pdfplumber
from kb.pdf_tables import table_to_text_rows

ROOT = Path(__file__).resolve().parents[1]
pdf_path = ROOT / "output" / "pdf" / "day16_table_sample.pdf"
chunks = []

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]

    print("普通文本提取：")
    print(page.extract_text())

    tables = page.extract_tables()

    print("\n检测到的表格数量：", len(tables))

    for table_number, table in enumerate(tables, start=1):
        print(f"\n===== 表格 {table_number} =====")

        rows = table_to_text_rows(
            table,
            title="退款办理时限",
        )

        for row_number, chunk in rows:

            chunks.append({
                "text": chunk,
                "source": pdf_path.name,
                "page": page.page_number,
                "table_number": table_number,
                "row_number": row_number,
            })

            print(f"\n第 {row_number} 行生成的文本：")
            print(chunk)

question = "专业版退款审核通过后，多久能到账？"

retriever = BM25([item["text"] for item in chunks])
scores = retriever.score(question)

index, score = max(
    enumerate(scores),
    key=lambda item: item[1],
)

if score <= 0:
    raise ValueError("没有匹配的表格行")

hit = chunks[index]

print("\n问题：", question)
print("命中的内容：\n", hit["text"])
print(
    f"来源：{hit['source']}，第 {hit['page']} 页，"
    f"第 {hit['table_number']} 个表格，"
    f"第 {hit['row_number']} 条数据行"
)
