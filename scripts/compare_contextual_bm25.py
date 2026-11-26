import json
from pathlib import Path

from kb.bm25 import BM25


ROOT = Path(__file__).resolve().parents[1]
records_path = ROOT / "data" / "day15" / "refund_contexts.json"

records = json.loads(records_path.read_text(encoding="utf-8"))

retrievers = {
    "原始片段": BM25([
        record["original_text"]
        for record in records
    ]),
    "补充语境": BM25([
        record["index_text"]
        for record in records
    ]),
}

retrievers["标题＋原文"] = BM25([
    " > ".join(record["heading_path"])
    + "\n"
    + record["original_text"]
    for record in records
])

question = "退款到账时限是什么？"

for name, retriever in retrievers.items():
    scores = retriever.score(question)

    ranked = sorted(
        enumerate(scores),
        key=lambda item: item[1],
        reverse=True,
    )

    print(f"\n{name}的前 3 个结果：")

    for rank, (index, score) in enumerate(ranked[:3], start=1):
        record = records[index]

        print(f"\n第 {rank} 名：{record['id']}，得分：{score:.4f}")
        print(record["original_text"])
        
cases = [
    ("退款到账时限是什么？", "chunk-2"),
    ("购买多久以内可以申请退款？", "chunk-1"),
    ("使用超过两小时还能退款吗？", "chunk-1"),
    ("电子发票申请后多久开具？", "chunk-3"),
    ("紧急故障通过什么渠道提交？", "chunk-4"),
]

for name, retriever in retrievers.items():
    hits = 0
    print(f"\n===== {name}：小样本检查 =====")

    for question, expected_id in cases:
        scores = retriever.score(question)
        index, score = max(
            enumerate(scores),
            key=lambda item: item[1],
        )

        retrieved_id = records[index]["id"] if score > 0 else None
        matched = retrieved_id == expected_id
        hits += int(matched)

        print(
            f"{question}\n"
            f"预期：{expected_id}，实际：{retrieved_id}，命中：{matched}"
        )

    print(f"首位命中：{hits}/{len(cases)}")