import json
from pathlib import Path

import chromadb

from kb.embeddings import LocalEmbedding

ROOT = Path(__file__).resolve().parents[1]

report_path = ROOT / "data" / "eval_results" / "day13" / (
    "followup_multi_hop_005_1792295279617590400.json"
)
report = json.loads(report_path.read_text(encoding="utf-8"))

client = chromadb.PersistentClient(
    path=str(ROOT / "data" / "chroma")
)
collection = client.get_collection(
    "day10_oss_qwen_06b_v1",
    embedding_function=None,
)
metadata = collection.metadata or {}

embedding = LocalEmbedding(
    model_name=metadata["embedding_model"],
    cache_dir=ROOT / "data" / "models",
)

queries = [
    ("原后续问题", report["plan"]["followup_question"]),
    ("私有权限规则", "Object ACL 为 private 时，哪些用户可以读取？"),
    ("独立权限规则", "Object 独立设置 ACL 时，是否继承 Bucket ACL？"),
]

split_ids = set()

for number, (name, query) in enumerate(queries):
    query_vector = embedding.embed_query(query)

    if len(query_vector) != metadata["embedding_dimension"]:
        raise ValueError("查询向量维度与索引不一致")

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=5,
        include=["documents", "distances"],
    )

    documents = results["documents"]
    distances = results["distances"]
    if documents is None or distances is None:
        raise ValueError("检索结果缺少正文或距离")

    print(f"\n{name}：{query}")
    for rank, (chunk_id, document, distance) in enumerate(
        zip(
            results["ids"][0],
            documents[0],
            distances[0],
        ),
        1,
    ):
        print(f"\n{rank}. {chunk_id}，距离 {distance:.4f}")
        print(document)

    if number > 0:
        split_ids.update(results["ids"][0])

print("\n两个拆分问题合并后的片段 ID：")
print(sorted(split_ids))