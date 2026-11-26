"""Day 7：对已保存的检索结果计算 Recall、MRR 和 nDCG，不重复调用模型。"""

import argparse
import hashlib
import json
from pathlib import Path

from kb.metrics import ndcg_at_k, recall_at_k, reciprocal_rank_at_k


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--labels", type=Path,
        default=ROOT / "examples" / "day7" / "relevance_labels.json",
    )
    parser.add_argument("--k", type=int)
    args = parser.parse_args()

    report_bytes = args.report.read_bytes()
    report = json.loads(report_bytes.decode("utf-8"))
    labels = json.loads(args.labels.read_text(encoding="utf-8"))
    k = args.k if args.k is not None else report["top_k"]
    if not 1 <= k <= report["top_k"]:
        raise ValueError("k 必须大于 0 且不超过报告实际检索的候选数")
    if report["collection"] != labels["collection"]:
        raise ValueError("报告与相关片段标签不属于同一集合")
    if report["collection_count"] != labels["collection_count"]:
        raise ValueError("索引条数与标签不一致，需要重新检查标签")
    cases_bytes = Path(report["cases_path"]).read_bytes()
    if hashlib.sha256(cases_bytes).hexdigest() != labels["cases_sha256"]:
        raise ValueError("题集与标签内容指纹不一致，需要重新检查标签")
    gold = labels["relevant_ids_by_case"]
    ids = [case["id"] for case in report["cases"]]
    if len(ids) != len(set(ids)) or set(ids) != set(gold):
        raise ValueError("报告与标签题目 ID 不一致")

    scores: list[float] = []
    rank_scores: list[float] = []
    ndcg_scores: list[float] = []
    groups: dict[str, list[float]] = {}
    rank_groups: dict[str, list[float]] = {}
    ndcg_groups: dict[str, list[float]] = {}
    results = []
    for case in report["cases"]:
        relevant_ids = set(gold[case["id"]])
        if bool(relevant_ids) != case["answerable"]:
            raise ValueError(f"{case['id']} 的可回答性与片段标签不一致")
        score = recall_at_k(case["retrieved_ids"], relevant_ids, k)
        rank_score = reciprocal_rank_at_k(case["retrieved_ids"], relevant_ids, k)
        ndcg_score = ndcg_at_k(case["retrieved_ids"], relevant_ids, k)
        if (score is None) != (rank_score is None) or (score is None) != (ndcg_score is None):
            raise ValueError("检索指标的未评分状态不一致")
        results.append({
            "id": case["id"],
            "category": case["category"],
            "relevant_ids": sorted(relevant_ids),
            "retrieved_ids": case["retrieved_ids"][:k],
            "recall": score,
            "reciprocal_rank": rank_score,
            "ndcg": ndcg_score,
        })
        if score is not None:
            assert rank_score is not None
            assert ndcg_score is not None
            scores.append(score)
            rank_scores.append(rank_score)
            ndcg_scores.append(ndcg_score)
            groups.setdefault(case["category"], []).append(score)
            rank_groups.setdefault(case["category"], []).append(rank_score)
            ndcg_groups.setdefault(case["category"], []).append(ndcg_score)

    summary = {
        "metrics": [f"Recall@{k}", f"MRR@{k}", f"nDCG@{k}"],
        "source_report": str(args.report.resolve()),
        "source_report_sha256": hashlib.sha256(report_bytes).hexdigest(),
        "labels_sha256": hashlib.sha256(args.labels.read_bytes()).hexdigest(),
        "label_basis": labels["label_basis"],
        "scored_count": len(scores),
        "unscored_count": len(results) - len(scores),
        "mean_recall": sum(scores) / len(scores) if scores else None,
        "mrr": sum(rank_scores) / len(rank_scores) if rank_scores else None,
        "mean_ndcg": sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else None,
        "category_summary": {
            name: {
                "count": len(values),
                "mean_recall": sum(values) / len(values),
                "mrr": sum(rank_groups[name]) / len(rank_groups[name]),
                "mean_ndcg": sum(ndcg_groups[name]) / len(ndcg_groups[name]),
            }
            for name, values in groups.items()
        },
        "cases": results,
    }
    output = ROOT / "data" / "eval_results" / f"{args.report.stem}_metrics{k}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Recall@{k} 参与评分 {len(scores)} 题，未评分 {len(results) - len(scores)} 题")
    if scores:
        print(f"平均 Recall@{k}：{summary['mean_recall']:.2%}")
        print(f"MRR@{k}：{summary['mrr']:.4f}")
        print(f"nDCG@{k}：{summary['mean_ndcg']:.4f}")
    for category, group in summary["category_summary"].items():
        print(f"{category}：Recall {group['mean_recall']:.2%}，MRR {group['mrr']:.4f}，nDCG {group['mean_ndcg']:.4f}")
    print("报告已保存：", output)


if __name__ == "__main__":
    main()
