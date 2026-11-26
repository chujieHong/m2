"""Day 8：配置驱动的单题检索或完整 RAG 实验。"""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter, time_ns
from typing import Any

from dotenv import load_dotenv
from llm_toolkit.providers import close_all, get_provider

from kb.experiment_config import load_experiment_config
from kb.pipeline import TIMING_SCOPE, run_case
from kb.retrieval import VectorRetriever


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--assumptions", default="")
    parser.add_argument("--generate", action="store_true", help="调用 DeepSeek 生成答案")
    args = parser.parse_args()

    config = load_experiment_config(args.config)
    config_bytes = args.config.read_bytes()

    started = perf_counter()
    retriever = VectorRetriever(config, ROOT)
    initialization_seconds = perf_counter() - started

    provider = None
    if args.generate:
        load_dotenv(ROOT / ".env")
        provider = get_provider("deepseek")

    try:
        case_result = run_case(
            retriever, config, args.question, args.assumptions, provider
        )
    finally:
        close_all()
    results = case_result["results"]
    documents = results["documents"]

    report: dict[str, Any] = {
        "stage": "rag" if args.generate else "retrieval_only",
        "config_path": str(args.config.resolve()),
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "config": config.model_dump(),
        "collection_count": retriever.collection.count(),
        "initialization_seconds": initialization_seconds,
        "timing_scope": TIMING_SCOPE,
        **case_result,
    }
    # 使用时间编号保存每次运行，避免覆盖之前的实验记录。
    output_dir = ROOT / "data" / "eval_results" / "day8"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{report['stage']}_{time_ns()}.json"
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    print("实验：", config.name)
    print("检索数量：", len(results["ids"][0]))
    print(f"初始化耗时：{initialization_seconds:.3f} 秒")
    print(f"检索耗时：{report['retrieval_seconds']:.3f} 秒")
    if args.generate:
        print("生成状态：", report["status"])
        print("回答：", report.get("answer"))
        if report["status"] == "error":
            print("生成错误：", report["error"])
        print(f"生成耗时：{report['generation_seconds']:.3f} 秒")
        print(f"问答链路耗时：{report['rag_seconds']:.3f} 秒")
    for chunk_id, document in zip(results["ids"][0], documents[0]):
        print(f"\n{chunk_id}\n{document}")
    print("\n记录已保存：", output_path)
    if report["status"] in {"error", "invalid_response"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
