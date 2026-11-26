"""Day 7：复用已保存的真实回答，运行一题 RAGAS 忠实度。"""

import argparse
import asyncio
import hashlib
import json
import math
import os
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")

from dotenv import load_dotenv
from llm_toolkit.providers import close_all, get_provider
from ragas.metrics.collections import Faithfulness

from kb.ragas_adapter import M1RagasLLM


ROOT = Path(__file__).resolve().parents[1]


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", default="single_hop_001")
    parser.add_argument("--context-format", choices=("raw", "numbered"), default="numbered")
    args = parser.parse_args()
    path = ROOT / "data/eval_results/day7_answers_100_top3.json"
    source_bytes = path.read_bytes()
    data = json.loads(source_bytes.decode("utf-8"))
    cases = {case["id"]: case for case in data["cases"]}
    case = cases[args.case_id]
    if case["status"] != "ok":
        raise ValueError("生成失败的记录不进入忠实度评测")
    contexts = (
        [f"[{number}] {document}" for number, document in enumerate(case["documents"], 1)]
        if args.context_format == "numbered" else case["documents"]
    )
    load_dotenv(ROOT / ".env")
    provider = get_provider("deepseek")
    adapter = M1RagasLLM(provider)
    output = {
        "id": case["id"], "source_answers_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "ragas_version": version("ragas"), "judge_model": provider.model,
        "question": case["question"], "answer": case["answer"],
        "documents": case["documents"], "status": "pending", "faithfulness": None,
        "context_format": args.context_format, "retrieved_contexts": contexts,
    }
    started = perf_counter()
    try:
        metric = Faithfulness(llm=adapter)
        result = await metric.ascore(
            user_input=case["question"], response=case["answer"],
            retrieved_contexts=contexts,
        )
        if math.isfinite(result.value):
            output.update(status="ok", faithfulness=result.value)
        else:
            output.update(status="unscorable", reason="RAGAS 未生成可评分事实，结果非有限值")
    except Exception as exc:
        output.update(status="error", error_type=type(exc).__name__, error=str(exc))
    finally:
        close_all()
    output["elapsed_seconds"] = perf_counter() - started
    output["adapter_trace"] = adapter.trace
    target = ROOT / "data/eval_results" / f"ragas_faithfulness_{case['id']}_{args.context_format}.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("Status:", output["status"], "Faithfulness:", output["faithfulness"])
    print(target)


if __name__ == "__main__":
    asyncio.run(main())
