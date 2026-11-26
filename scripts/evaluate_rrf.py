import json
import argparse
from pathlib import Path
import hashlib
from time import time_ns
from kb.fusion import reciprocal_rank_fusion
from kb.metrics import recall_at_k

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--rank-constant", type=int, default=60)
args = parser.parse_args()

bm25_path = ROOT / "data" / "eval_results" / "day11" / (
    "bm25_top10_1792208177908962900.json"
)
vector_path = ROOT / "data" / "eval_results" / "day9" / (
    "Qwen3-Embedding-0.6B-Q_top10_1791949120216611000.json"
)

labels_path = ROOT / "examples" / "day7" / "relevance_labels.json"

bm25_report = json.loads(bm25_path.read_text(encoding="utf-8"))
vector_report = json.loads(vector_path.read_text(encoding="utf-8"))
labels = json.loads(labels_path.read_text(encoding="utf-8"))

for field in ["collection", "document_count", "top_k"]:
    if bm25_report[field] != vector_report[field]:
        raise ValueError(f"两路报告的 {field} 不一致")

bm25_by_id = {
    item["id"]: item
    for item in bm25_report["cases"]
}
vector_by_id = {
    item["id"]: item
    for item in vector_report["cases"]
}

if len(bm25_by_id) != len(bm25_report["cases"]):
    raise ValueError("BM25 报告有重复题目 ID")
if len(vector_by_id) != len(vector_report["cases"]):
    raise ValueError("向量报告有重复题目 ID")
if set(bm25_by_id) != set(vector_by_id):
    raise ValueError("两路报告的题目 ID 不一致")

print("配对题数：", len(bm25_by_id))

top_k = 5
rank_constant = args.rank_constant

recalls = []
candidate_recalls = []
case_results = []

for case_id, bm25_case in bm25_by_id.items():
    vector_case = vector_by_id[case_id]

    fused_results = reciprocal_rank_fusion(
        rankings=[
            bm25_case["retrieved_ids"],
            vector_case["retrieved_ids"],
        ],
        top_k=top_k,
        rank_constant=rank_constant,
    )

    fused_ids = [
        chunk_id
        for chunk_id, score in fused_results
    ]

    relevant_ids = set(
        labels["relevant_ids_by_case"][case_id]
    )

    recall = recall_at_k(
        fused_ids,
        relevant_ids,
        top_k,
    )

    case_results.append({
        "id": case_id,
        "retrieved_ids": fused_ids,
        "fused_results": fused_results,
        "recall": recall,
    })

    if recall is not None:
        recalls.append(recall)

        candidate_ids = set(
            bm25_case["retrieved_ids"]
            + vector_case["retrieved_ids"]
        )
        candidate_recall = (
            len(candidate_ids & relevant_ids)
            / len(relevant_ids)
        )
        candidate_recalls.append(candidate_recall)

print("融合后返回数量：", top_k)
print("RRF 常数：", rank_constant)
print("参与评分：", len(recalls))

if recalls:
    average_recall = sum(recalls) / len(recalls)
    print(f"RRF 平均必要依据覆盖率：{average_recall:.2%}")
else:
    print("没有可计算覆盖率的题目")

if candidate_recalls:
    average_candidate_recall = (
        sum(candidate_recalls) / len(candidate_recalls)
    )
    print(
        f"候选池平均必要依据覆盖率："
        f"{average_candidate_recall:.2%}"
    )

report = {
    "retrieval_method": "rrf",
    "candidate_k": {
        "bm25": bm25_report["top_k"],
        "vector": vector_report["top_k"],
    },
    "top_k": top_k,
    "rank_constant": rank_constant,
    "selected_count": len(case_results),
    "scored_count": len(recalls),
    "average_recall": (
        sum(recalls) / len(recalls) if recalls else None
    ),
    "input_reports": {
        "bm25": {
            "path": str(bm25_path),
            "sha256": hashlib.sha256(
                bm25_path.read_bytes()
            ).hexdigest(),
        },
        "vector": {
            "path": str(vector_path),
            "sha256": hashlib.sha256(
                vector_path.read_bytes()
            ).hexdigest(),
        },
    },
    "labels_sha256": hashlib.sha256(
        labels_path.read_bytes()
    ).hexdigest(),
    "cases": case_results,
}

output_dir = ROOT / "data" / "eval_results" / "day12"
output_dir.mkdir(parents=True, exist_ok=True)

output_path = output_dir / f"rrf_top{top_k}_{time_ns()}.json"
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

