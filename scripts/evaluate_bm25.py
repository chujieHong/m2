import argparse
import hashlib
import json
from pathlib import Path
from time import time_ns
import chromadb

from kb.bm25 import BM25
from kb.metrics import recall_at_k

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser()
parser.add_argument("--top-k", type=int, default=5)
parser.add_argument(
    "--drop-he",
    action="store_true",
    help="实验：从查询词中去掉“和”",
)
parser.add_argument(
    "--search-mode",
    action="store_true",
    help="使用 jieba 搜索模式分词",
)
args = parser.parse_args()

cases_path = ROOT / "examples" / "day6" / "oss_cases_100.json"
labels_path = ROOT / "examples" / "day7" / "relevance_labels.json"

cases_bytes = cases_path.read_bytes()
cases = json.loads(cases_bytes)
labels = json.loads(labels_path.read_text(encoding="utf-8"))

if hashlib.sha256(cases_bytes).hexdigest() != labels["cases_sha256"]:
    raise ValueError("当前题目文件与标签记录的版本不一致")

client = chromadb.PersistentClient(
    path=str(ROOT / "data" / "chroma")
)
collection = client.get_collection(
    labels["collection"],
    embedding_function=None,
)

records = collection.get(include=["documents"])
documents = records["documents"]
chunk_ids = records["ids"]

if not documents:
    raise ValueError("集合没有文档")
if len(documents) != labels["collection_count"]:
    raise ValueError("集合记录数与标签记录不一致")
if not 1 <= args.top_k <= len(documents):
    raise ValueError("top-k 必须在 1 到文档总数之间")

retriever = BM25(
    documents,
    search_mode=args.search_mode,
)
recalls = []
case_results = []

query_stop_words = {"和"} if args.drop_he else set()

for case in cases:
    scores = retriever.score(
        case["question"],
        query_stop_words=query_stop_words,
    )

    ranked_scores = sorted(
        enumerate(scores),
        key=lambda item: item[1],
        reverse=True,
    )

    retrieved_ids = [
        chunk_ids[index]
        for index, score in ranked_scores
        if score > 0
    ][:args.top_k]

    relevant_ids = set(
        labels["relevant_ids_by_case"][case["id"]]
    )
    if not relevant_ids.issubset(set(chunk_ids)):
        raise ValueError("必要依据 ID 不在当前集合中")

    recall = recall_at_k(
        retrieved_ids,
        relevant_ids,
        args.top_k,
    )

    case_results.append({
        "id": case["id"],
        "retrieved_ids": retrieved_ids,
        "recall": recall,
    })

    if recall is not None:
        recalls.append(recall)

print("题目数量：", len(cases))
print("top-k：", args.top_k)
print("参与评分：", len(recalls))
print("未参与评分：", len(cases) - len(recalls))

if recalls:
    average_recall = sum(recalls) / len(recalls)
    print(f"平均必要依据覆盖率：{average_recall:.2%}")
else:
    print("没有可计算覆盖率的题目")
    
report = {
    "retrieval_method": "bm25",
    "search_mode": retriever.search_mode,
    "query_stop_words": sorted(query_stop_words),
    "collection": collection.name,
    "document_count": len(documents),
    "cases_sha256": hashlib.sha256(cases_bytes).hexdigest(),
    "labels_sha256": hashlib.sha256(
        labels_path.read_bytes()
    ).hexdigest(),
    "k1": retriever.k1,
    "b": retriever.b,
    "top_k": args.top_k,
    "selected_count": len(cases),
    "scored_count": len(recalls),
    "average_recall": (
        sum(recalls) / len(recalls) if recalls else None
    ),
    "cases": case_results,
}

output_dir = ROOT / "data" / "eval_results" / "day11"
output_dir.mkdir(parents=True, exist_ok=True)

output_path = output_dir / (
    f"bm25_top{args.top_k}_{time_ns()}.json"
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

print("结果已保存：", output_path)