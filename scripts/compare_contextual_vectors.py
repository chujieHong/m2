import json
from pathlib import Path

import numpy as np

from kb.embeddings import LocalEmbedding


ROOT = Path(__file__).resolve().parents[1]
records_path = ROOT / "data" / "day15" / "refund_contexts.json"
records = json.loads(records_path.read_text(encoding="utf-8"))

embedding = LocalEmbedding(
    model_name="BAAI/bge-small-zh-v1.5",
    cache_dir=ROOT / "data" / "models",
)

text_groups = {
    "原始片段": [
        record["original_text"]
        for record in records
    ],
    "标题＋原文": [
        " > ".join(record["heading_path"])
        + "\n"
        + record["original_text"]
        for record in records
    ],
    "补充语境": [
        record["index_text"]
        for record in records
    ],
}

matrices = {}

for name, texts in text_groups.items():
    vectors = embedding.embed_documents(texts)
    matrices[name] = np.asarray(vectors, dtype=np.float32)

    print(name, "向量矩阵形状：", matrices[name].shape)
    
question = "退款到账时限是什么？"

query_vector = np.asarray(
    embedding.embed_query(question),
    dtype=np.float32,
)
query_norm = np.linalg.norm(query_vector)

if query_norm == 0:
    raise ValueError("问题向量不能是零向量")

for name, matrix in matrices.items():
    document_norms = np.linalg.norm(matrix, axis=1)

    if np.any(document_norms == 0):
        raise ValueError("文档向量不能包含零向量")

    scores = (
        matrix @ query_vector
        / (document_norms * query_norm)
    )

    ranked = sorted(
        enumerate(scores),
        key=lambda item: item[1],
        reverse=True,
    )

    print(f"\n{name}的前 3 个结果：")

    for rank, (index, score) in enumerate(ranked[:3], start=1):
        record = records[index]

        print(f"\n第 {rank} 名：{record['id']}，相似度：{score:.4f}")
        print(record["original_text"])
        
cases = [
    ("退款到账时限是什么？", "chunk-2"),
    ("购买多久以内可以申请退款？", "chunk-1"),
    ("使用超过两小时还能退款吗？", "chunk-1"),
    ("电子发票申请后多久开具？", "chunk-3"),
    ("紧急故障通过什么渠道提交？", "chunk-4"),
]

query_vectors = [
    np.asarray(embedding.embed_query(question), dtype=np.float32)
    for question, _ in cases
]

for name, matrix in matrices.items():
    document_norms = np.linalg.norm(matrix, axis=1)
    hits = 0

    print(f"\n===== {name}：小样本检查 =====")

    for (question, expected_id), query_vector in zip(cases, query_vectors):
        query_norm = np.linalg.norm(query_vector)

        if query_norm == 0 or np.any(document_norms == 0):
            raise ValueError("不能使用零向量计算余弦相似度")

        scores = (
            matrix @ query_vector
            / (document_norms * query_norm)
        )

        index = int(np.argmax(scores))
        retrieved_id = records[index]["id"]
        matched = retrieved_id == expected_id
        hits += int(matched)

        print(
            f"{question}\n"
            f"预期：{expected_id}，实际：{retrieved_id}，命中：{matched}"
        )

    print(f"首位命中：{hits}/{len(cases)}")