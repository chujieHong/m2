from pathlib import Path
import json

import chromadb
from fastembed.rerank.cross_encoder import TextCrossEncoder

ROOT = Path(__file__).resolve().parents[1]

reranker = TextCrossEncoder(
    model_name="BAAI/bge-reranker-v2-m3-int8",
    cache_dir=str(ROOT / "data" / "models"),
    threads=2,
    cuda=False,
    local_files_only=True,
)

question = "Bucket ACL 和 Object ACL 默认值有何不同？"

bm25_path = ROOT / "data" / "eval_results" / "day11" / (
    "bm25_top10_1792208177908962900.json"
)
vector_path = ROOT / "data" / "eval_results" / "day9" / (
    "Qwen3-Embedding-0.6B-Q_top10_1791949120216611000.json"
)

bm25_report = json.loads(bm25_path.read_text(encoding="utf-8"))
vector_report = json.loads(vector_path.read_text(encoding="utf-8"))

case_id = "comparison_001"

bm25_case = next(
    item for item in bm25_report["cases"]
    if item["id"] == case_id
)
vector_case = next(
    item for item in vector_report["cases"]
    if item["id"] == case_id
)

candidate_ids = sorted(
    set(bm25_case["retrieved_ids"])
    | set(vector_case["retrieved_ids"])
)

client = chromadb.PersistentClient(
    path=str(ROOT / "data" / "chroma")
)
collection = client.get_collection(
    bm25_report["collection"],
    embedding_function=None,
)
records = collection.get(include=["documents"])

stored_documents = records["documents"]
if stored_documents is None:
    raise ValueError("集合没有返回正文")

document_by_id = dict(
    zip(records["ids"], stored_documents)
)

documents = [
    document_by_id[chunk_id]
    for chunk_id in candidate_ids
]

print("候选数量：", len(candidate_ids))

scores = list(
    reranker.rerank(
        query=question,
        documents=documents,
        batch_size=1,
    )
)

ranked_scores = sorted(
    enumerate(scores),
    key=lambda item: item[1],
    reverse=True,
)

print("\n重排序后的前五名：")
for index, score in ranked_scores[:5]:
    print(
        f"\n片段 ID：{candidate_ids[index]}，"
        f"相关性分数：{score:.4f}"
    )
    print(documents[index])