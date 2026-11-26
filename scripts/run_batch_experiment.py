"""Day 8：固定题集批量实验，默认仅检索，--generate 可接通生成。"""

import argparse
import hashlib
import json
from pathlib import Path
from statistics import median
from time import perf_counter, time_ns
from typing import Any

from dotenv import load_dotenv
from llm_toolkit.providers import close_all, get_provider

from kb.experiment_config import load_experiment_config
from kb.metrics import ndcg_at_k, recall_at_k, reciprocal_rank_at_k
from kb.pipeline import TIMING_SCOPE, run_case
from kb.retrieval import VectorRetriever


ROOT = Path(__file__).resolve().parents[1]


def summarize(records: list[dict[str, Any]], top_k: int) -> dict[str, Any]:
    metrics = {}
    for k in sorted({1, 3, top_k}):
        if k > top_k:
            continue
        scored = [r for r in records if r["relevant_ids"]]
        metrics[str(k)] = {
            "scored_count": len(scored),
            "unscored_count": len(records) - len(scored),
            "recall": sum(recall_at_k(r["results"]["ids"][0], set(r["relevant_ids"]), k) or 0.0 for r in scored) / len(scored) if scored else None,
            "mrr": sum(reciprocal_rank_at_k(r["results"]["ids"][0], set(r["relevant_ids"]), k) or 0.0 for r in scored) / len(scored) if scored else None,
            "ndcg": sum(ndcg_at_k(r["results"]["ids"][0], set(r["relevant_ids"]), k) or 0.0 for r in scored) / len(scored) if scored else None,
        }
    successful = [r for r in records if r["status"] == "ok"]
    return {
        "processed_count": len(records),
        "status_counts": {status: sum(r["status"] == status for r in records) for status in sorted({r["status"] for r in records})},
        "retrieval_metrics_at_k": metrics,
        "retrieval_p50_seconds": median(r["retrieval_seconds"] for r in records) if records else None,
        "rag_success_count": len(successful),
        "rag_success_p50_seconds": median(r["rag_seconds"] for r in successful) if successful else None,
        "generation_success_p50_seconds": median(r["generation_seconds"] for r in successful) if successful else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args()
    config = load_experiment_config(args.config)
    cases_path = ROOT / "examples" / "day6" / "oss_cases_100.json"
    labels_path = ROOT / "examples" / "day7" / "relevance_labels.json"
    cases_bytes = cases_path.read_bytes()
    labels_bytes = labels_path.read_bytes()
    cases = json.loads(cases_bytes)
    labels = json.loads(labels_bytes)
    if hashlib.sha256(cases_bytes).hexdigest() != labels["cases_sha256"]:
        raise ValueError("题集与标签内容不一致")
    if config.collection != labels["collection"]:
        raise ValueError("配置集合与固定题集标签不一致")
    gold = labels["relevant_ids_by_case"]
    case_ids = [case["id"] for case in cases]
    if len(case_ids) != len(set(case_ids)) or set(case_ids) != set(gold):
        raise ValueError("题集与标签 ID 不一致")
    if args.case_id:
        if len(args.case_id) != len(set(args.case_id)) or not set(args.case_id) <= set(case_ids):
            raise ValueError("指定题目 ID 重复或不存在")
        cases = [case for case in cases if case["id"] in args.case_id]

    started = perf_counter()
    retriever = VectorRetriever(config, ROOT)
    initialization_seconds = perf_counter() - started
    if retriever.collection.count() != labels["collection_count"]:
        raise ValueError("集合条数与标签不一致")
    if config.top_k > retriever.collection.count():
        raise ValueError("top_k 超过集合条数")
    snapshot = retriever.collection.get(include=["documents", "metadatas", "embeddings"])
    embeddings = snapshot["embeddings"]
    if embeddings is None or snapshot["documents"] is None or snapshot["metadatas"] is None:
        raise ValueError("集合缺少文档、元数据或向量")
    snapshot_records = sorted([
        {"id": chunk_id, "document": document, "metadata": metadata, "embedding": embedding.tolist()}
        for chunk_id, document, metadata, embedding in zip(snapshot["ids"], snapshot["documents"], snapshot["metadatas"], embeddings)
    ], key=lambda record: record["id"])
    if not set().union(*(set(v) for v in gold.values())) <= set(snapshot["ids"]):
        raise ValueError("相关片段标签指向不存在的片段")
    snapshot_bytes = json.dumps(snapshot_records, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")

    provider = None
    if args.generate:
        load_dotenv(ROOT / ".env")
        provider = get_provider("deepseek")
    report: dict[str, Any] = {
        "stage": "rag_batch" if args.generate else "retrieval_batch",
        "config": config.model_dump(),
        "config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
        "cases_path": str(cases_path),
        "cases_sha256": hashlib.sha256(cases_bytes).hexdigest(),
        "labels_sha256": hashlib.sha256(labels_bytes).hexdigest(),
        "label_basis": labels["label_basis"],
        "index_snapshot_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
        "collection_count": retriever.collection.count(),
        "initialization_seconds": initialization_seconds,
        "timing_scope": TIMING_SCOPE,
        "planned_count": len(cases),
        "complete": False,
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in [Path(__file__), ROOT / "src/kb/pipeline.py", ROOT / "src/kb/retrieval.py", ROOT / "src/kb/generation.py", ROOT / "src/kb/experiment_config.py", ROOT / "src/kb/metrics.py"]},
        "cases": [],
    }
    output_dir = ROOT / "data" / "eval_results" / "day8"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{report['stage']}_{time_ns()}.json"
    try:
        for case in cases:
            record = run_case(
                retriever, config, case["question"],
                case.get("common_assumptions", ""), provider,
            )
            # 标注仅进入评测记录，不传给 run_case 或模型。
            record.update({"id": case["id"], "category": case["category"], "answerable": case["answerable"], "relevant_ids": gold[case["id"]]})
            report["cases"].append(record)
            report["complete"] = len(report["cases"]) == len(cases)
            report["summary"] = summarize(report["cases"], config.top_k)
            output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            if len(report["cases"]) % 20 == 0 or report["complete"]:
                print(f"已完成 {len(report['cases'])}/{len(cases)}", flush=True)
    finally:
        close_all()
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print("记录已保存：", output_path)
    if any(r["status"] in {"error", "invalid_response"} for r in report["cases"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
