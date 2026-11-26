import json
from pathlib import Path
from time import perf_counter, time_ns
from kb.metrics import recall_at_k
import numpy as np
import chromadb
import argparse
from kb.embeddings import LocalEmbedding

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser()

parser.add_argument(
    "--model",
    choices=["bge", "qwen"],
    default="bge",
)
parser.add_argument("--with-instruction", action="store_true")
parser.add_argument("--top-k", type=int, default=5)

parser.add_argument("--inspect-case")

args = parser.parse_args()

if args.model == "bge" and args.with_instruction:
    parser.error("当前实验只给 Qwen 添加任务指令")

model_names = {
    "bge": "BAAI/bge-small-zh-v1.5",
    "qwen": "Qwen/Qwen3-Embedding-0.6B-Q",
}

query_instruction = None

if args.with_instruction:
    query_instruction = (
        "Given a question, retrieve passages from Chinese "
        "cloud-service documentation that answer the question."
    )

collection = chromadb.PersistentClient(
    path=str(ROOT / "data" / "chroma")
).get_collection(
    "day6_oss_v1_bge_small_zh",
    embedding_function=None,
)

records = collection.get(include=["documents"])

chunk_ids = records["ids"]
documents = records["documents"]

if documents is None or not documents:
    raise ValueError("集合中没有文档正文")

top_k = args.top_k

if not 1 <= top_k <= len(documents):
    parser.error("top-k 必须在 1 到文档片段数量之间")

cases = json.loads(
    (ROOT / "examples" / "day6" / "oss_cases_100.json")
    .read_text(encoding="utf-8")
)

if args.inspect_case:
    cases = [
        case
        for case in cases
        if case["id"] == args.inspect_case
    ]

    if not cases:
        parser.error("指定的题目 ID 不存在")

    if not cases[0]["answerable"]:
        parser.error("当前诊断入口先只检查可回答题")

print("文档片段数量：", len(documents))
print("评测问题数量：", len(cases))

embedding = LocalEmbedding(
    model_name=model_names[args.model],
    cache_dir=ROOT / "data" / "models",
    query_instruction=query_instruction,
)

started = perf_counter()

document_vectors = embedding.embed_documents(documents)

document_matrix = np.asarray(
    document_vectors,
    dtype=np.float32,
)

print("文档向量矩阵形状：", document_matrix.shape)
print(f"文档向量化耗时：{perf_counter() - started:.2f} 秒")

question = cases[0]["question"]

query_vector = np.asarray(
    embedding.embed_query(question),
    dtype=np.float32,
)

document_norms = np.linalg.norm(document_matrix, axis=1)

scores = (
    document_matrix @ query_vector
) / (
    document_norms * np.linalg.norm(query_vector)
)

best_index = int(np.argmax(scores))

print("\n问题：", question)
print("第一名片段 ID：", chunk_ids[best_index])
print("相似度：", float(scores[best_index]))
print("片段正文：", documents[best_index])

top_indices = np.argsort(-scores)[:top_k]

retrieved_ids = [
    chunk_ids[int(index)]
    for index in top_indices
]

print(f"\n前 {top_k} 名片段：")

for rank, index in enumerate(top_indices, start=1):
    index = int(index)

    print(
        f"第 {rank} 名：{chunk_ids[index]}，"
        f"相似度 {float(scores[index]):.4f}"
    )
    
labels = json.loads(
    (ROOT / "examples" / "day7" / "relevance_labels.json")
    .read_text(encoding="utf-8")
)

case_id = cases[0]["id"]

relevant_ids = set(
    labels["relevant_ids_by_case"][case_id]
)

recall = recall_at_k(
    retrieved_ids,
    relevant_ids,
    top_k,
)

print("\n题目 ID：", case_id)
print("标注的相关片段：", relevant_ids)
print("实际检索片段：", retrieved_ids)
print(f"Recall@{top_k}：", recall)

if args.inspect_case:
    all_indices = np.argsort(-scores)

    rank_by_id = {
        chunk_ids[int(index)]: rank
        for rank, index in enumerate(all_indices, start=1)
    }

    print("\n必要依据在全部候选中的排名：")

    for chunk_id in sorted(relevant_ids):
        print(f"{chunk_id}：第 {rank_by_id[chunk_id]} 名")

recall_scores = []
case_results = []

for case in cases:
    query_vector = np.asarray(
        embedding.embed_query(case["question"]),
        dtype=np.float32,
    )

    scores = (
        document_matrix @ query_vector
    ) / (
        document_norms * np.linalg.norm(query_vector)
    )

    top_indices = np.argsort(-scores)[:top_k]
    retrieved_ids = [
        chunk_ids[int(index)]
        for index in top_indices
    ]

    relevant_ids = set(
        labels["relevant_ids_by_case"][case["id"]]
    )

    recall = recall_at_k(retrieved_ids, relevant_ids, top_k)

    case_results.append({
        "id": case["id"],
        "retrieved_ids": retrieved_ids,
        "recall": recall,
    })

    if recall is not None:
        recall_scores.append(recall)

if args.inspect_case:
    cases = [
        case
        for case in cases
        if case["id"] == args.inspect_case
    ]

    if not cases:
        parser.error("指定的题目 ID 不存在")

    if not cases[0]["answerable"]:
        parser.error("当前诊断入口先只检查可回答题")

print("\n参与评分的题数：", len(recall_scores))
print("未参与评分的题数：", len(cases) - len(recall_scores))

average_recall = sum(recall_scores) / len(recall_scores)
print(f"平均 Recall@{top_k}：{average_recall:.2%}")

report = {
    "model_name": embedding.model_name,
    "query_instruction": embedding.query_instruction,
    "retrieval_method": "exact_cosine_numpy",
    "collection": collection.name,
    "document_count": len(documents),
    "vector_dimension": int(document_matrix.shape[1]),
    "top_k": top_k,
    "selected_count": len(cases),
    "scored_count": len(recall_scores),
    "average_recall": average_recall,
    "cases": case_results,
}

output_dir = ROOT / "data" / "eval_results" / "day9"
output_dir.mkdir(parents=True, exist_ok=True)

model_tag = embedding.model_name.split("/")[-1]
output_path = output_dir / (
    f"{model_tag}_top{top_k}_{time_ns()}.json"
)

output_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
    encoding="utf-8",
)

print("结果已保存：", output_path)
