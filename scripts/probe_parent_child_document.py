from pathlib import Path
from kb.bm25 import BM25
from kb.chunking import split_text
from kb.ingestion import load_document


ROOT = Path(__file__).resolve().parents[1]
sections = load_document(ROOT / "examples" / "refund_policy.md")

parents = {}
children = []

for section_index, section in enumerate(sections):
    parent_id = f"parent-{section_index}"
    heading = " > ".join(section.heading_path)

    parents[parent_id] = (
        f"{heading}\n{section.text}".strip()
    )

    pieces = split_text(section.text, chunk_size=40)

    for child_index, text in enumerate(pieces):
        children.append({
            "id": f"{parent_id}-child-{child_index}",
            "parent_id": parent_id,
            "text": f"{heading}\n{text}".strip(),
        })

print("父块数量：", len(parents))
print("子块数量：", len(children))

for child in children:
    print("\n子块 ID：", child["id"])
    print("所属父块：", child["parent_id"])
    print("内容：", child["text"])
    
question = "申请退款有哪些时间和使用时长限制？审核通过后多久到账？"

retriever = BM25([
    child["text"]
    for child in children
])
scores = retriever.score(question)

ranked = sorted(
    enumerate(scores),
    key=lambda item: item[1],
    reverse=True,
)

index, score = ranked[0]
if score <= 0:
    raise ValueError("没有匹配的子块")

hit = children[index]
parent_text = parents[hit["parent_id"]]

print("\n问题：", question)
print("\n命中的子块：\n", hit["text"])
print("\n取回的父块：\n", parent_text)

required_evidence = [
    "用户可在购买后 7 天内申请退款。",
    "累计使用时长超过 2 小时的订单不支持退款。",
    "审核通过后，退款将在 3 个工作日内原路退回。",
]

contexts = {
    "只返回子块": hit["text"],
    "返回完整父块": parent_text,
}

for name, context in contexts.items():
    covered = sum(
        evidence in context
        for evidence in required_evidence
    )

    print(f"\n{name}：")
    print(f"上下文长度：{len(context)} 个字符")
    print(f"必要依据覆盖：{covered}/{len(required_evidence)}")