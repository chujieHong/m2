import hashlib
import json
from pathlib import Path
from time import perf_counter, time_ns

import chromadb
from fastembed.rerank.cross_encoder import TextCrossEncoder

from kb.metrics import recall_at_k

ROOT = Path(__file__).resolve().parents[1]

bm25_path = ROOT / "data" / "eval_results" / "day11" / (
    "bm25_top10_1792208177908962900.json"
)
vector_path = ROOT / "data" / "eval_results" / "day9" / (
    "Qwen3-Embedding-0.6B-Q_top10_1791949120216611000.json"
)
cases_path = ROOT / "examples" / "day6" / "oss_cases_100.json"
labels_path = ROOT / "examples" / "day7" / "relevance_labels.json"

bm25_report = json.loads(bm25_path.read_text(encoding="utf-8"))
vector_report = json.loads(vector_path.read_text(encoding="utf-8"))
cases_bytes = cases_path.read_bytes()
cases = json.loads(cases_bytes)
labels = json.loads(labels_path.read_text(encoding="utf-8"))

if hashlib.sha256(cases_bytes).hexdigest() != labels["cases_sha256"]:
    raise ValueError("题目文件与标签版本不一致")

bm25_by_id = {
    item["id"]: item
    for item in bm25_report["cases"]
}
vector_by_id = {
    item["id"]: item
    for item in vector_report["cases"]
}

expected_ids = {case["id"] for case in cases}
if set(bm25_by_id) != expected_ids:
    raise ValueError("BM25 报告与题目集不匹配")
if set(vector_by_id) != expected_ids:
    raise ValueError("向量报告与题目集不匹配")

for field in ["collection", "document_count", "top_k"]:
    if bm25_report[field] != vector_report[field]:
        raise ValueError(f"两路报告的 {field} 不一致")

client = chromadb.PersistentClient(
    path=str(ROOT / "data" / "chroma")
)
collection = client.get_collection(
    bm25_report["collection"],
    embedding_function=None,
)
records = collection.get(include=["documents"])

stored_documents = records["documents"]
if not stored_documents:
    raise ValueError("集合没有正文")

document_by_id = dict(
    zip(records["ids"], stored_documents)
)

model_name = "BAAI/bge-reranker-v2-m3-int8"
reranker = TextCrossEncoder(
    model_name=model_name,
    cache_dir=str(ROOT / "data" / "models"),
    threads=2,
    cuda=False,
    local_files_only=True,
)

print("准备完成，题目数量：", len(cases))

top_k = 5
recalls = []
case_results = []
rerank_times = []

for number, case in enumerate(cases, 1):
    case_id = case["id"]

    candidate_ids = sorted(
        set(bm25_by_id[case_id]["retrieved_ids"])
        | set(vector_by_id[case_id]["retrieved_ids"])
    )
    documents = [
        document_by_id[chunk_id]
        for chunk_id in candidate_ids
    ]

    started = perf_counter()

    scores = list(
        reranker.rerank(
            query=case["question"],
            documents=documents,
            batch_size=1,
        )
    )

    rerank_seconds = perf_counter() - started
    rerank_times.append(rerank_seconds)

    if len(scores) != len(candidate_ids):
        raise ValueError(f"{case_id} 的评分数量与候选数量不一致")

    ranked_scores = sorted(
        enumerate(scores),
        key=lambda item: item[1],
        reverse=True,
    )[:top_k]

    retrieved_ids = [
        candidate_ids[index]
        for index, score in ranked_scores
    ]

    relevant_ids = set(
        labels["relevant_ids_by_case"][case_id]
    )
    recall = recall_at_k(retrieved_ids, relevant_ids, top_k)

    case_results.append({
        "id": case_id,
        "candidate_ids": candidate_ids,
        "retrieved_ids": retrieved_ids,
        "ranked_scores": [
            {
                "chunk_id": candidate_ids[index],
                "score": score,
            }
            for index, score in ranked_scores
        ],
        "recall": recall,
        "rerank_seconds": rerank_seconds,
    })

    if recall is not None:
        recalls.append(recall)

    print(
        f"{number}/{len(cases)}：{case_id}，"
        f"候选 {len(candidate_ids)} 个，"
        f"重排耗时 {rerank_seconds:.2f} 秒",
        flush=True,
    )

if recalls:
    average_recall = sum(recalls) / len(recalls)
    print(f"\n平均 Recall@{top_k}：{average_recall:.2%}")

if rerank_times:
    average_seconds = sum(rerank_times) / len(rerank_times)
    print(f"平均每题重排耗时：{average_seconds:.2f} 秒")
    
report = {
    "method": "cross_encoder_rerank",
    "model_name": model_name,
    "collection": bm25_report["collection"],
    "candidate_k_per_retriever": bm25_report["top_k"],
    "top_k": top_k,
    "threads": 2,
    "batch_size": 1,
    "selected_count": len(case_results),
    "scored_count": len(recalls),
    "average_recall": (
        sum(recalls) / len(recalls)
        if recalls
        else None
    ),
    "average_rerank_seconds": (
        sum(rerank_times) / len(rerank_times)
        if rerank_times
        else None
    ),
    "timing_scope": "rerank 调用及评分迭代，不含模型加载和数据库读取",
    "cases_sha256": hashlib.sha256(cases_bytes).hexdigest(),
    "labels_sha256": hashlib.sha256(
        labels_path.read_bytes()
    ).hexdigest(),
    "input_reports": {
        "bm25": {
            "path": str(bm25_path.relative_to(ROOT)),
            "sha256": hashlib.sha256(
                bm25_path.read_bytes()
            ).hexdigest(),
        },
        "vector": {
            "path": str(vector_path.relative_to(ROOT)),
            "sha256": hashlib.sha256(
                vector_path.read_bytes()
            ).hexdigest(),
        },
    },
    "cases": case_results,
}

output_dir = ROOT / "data" / "eval_results" / "day13"
output_dir.mkdir(parents=True, exist_ok=True)

output_path = output_dir / (
    f"reranker_top{top_k}_{time_ns()}.json"
)
output_path.write_text(
    json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    ),
    encoding="utf-8",
)

print("报告已保存：", output_path)