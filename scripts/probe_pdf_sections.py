from pathlib import Path

from kb.bm25 import BM25
from kb.ingestion import load_document


ROOT = Path(__file__).resolve().parents[1]
pdf_path = ROOT / "output" / "pdf" / "day16_table_sample.pdf"

sections = load_document(pdf_path)

print("读取结果：")
for index, section in enumerate(sections):
    print(f"\n第 {index} 条：")
    print("位置：", section.heading_path)
    print(section.text)

question = "专业版退款审核通过后，多久能到账？"

retriever = BM25([section.text for section in sections])
scores = retriever.score(question)

index, score = max(
    enumerate(scores),
    key=lambda item: item[1],
)

if score <= 0:
    raise ValueError("没有匹配的内容")

hit = sections[index]

print("\n问题：", question)
print("命中的依据：\n", hit.text)
print("来源文件：", hit.source)
print("页码：", hit.page)
print("表格位置：", hit.heading_path)