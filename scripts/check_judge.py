"""使用虚构样例检查裁判；预设标签不进入模型输入。"""

import argparse
import hashlib
import json
from pathlib import Path

from dotenv import load_dotenv
from llm_toolkit.exceptions import LLMToolkitError
from llm_toolkit.providers import close_all, get_provider

from kb.answer_evaluation import evaluate_answer


ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = ("correctness", "faithfulness", "relevance")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--output", type=Path, default=ROOT / "data/eval_results/day7_judge_checks.json")
    args = parser.parse_args()
    source = ROOT / "examples/day7/judge_checks.json"
    sample_bytes = source.read_bytes()
    samples = json.loads(sample_bytes.decode("utf-8"))
    # 只发送规则，去掉已带分数的教学示例，避免它直接看到本次样例的标签。
    rubric = (ROOT / "examples/day7/generation_rubric.md").read_text(encoding="utf-8").split("## 教学反例", 1)[0]
    selected = args.case_id or [case["id"] for case in samples["cases"]]
    known_ids = {case["id"] for case in samples["cases"]}
    if len(selected) != len(set(selected)) or not set(selected) <= known_ids:
        raise ValueError("指定样例重复或不存在")
    output_path = args.output
    if output_path.resolve() == source.resolve():
        raise ValueError("结果不能覆盖样例文件")
    output = {
        "source": str(source),
        "source_sha256": hashlib.sha256(sample_bytes).hexdigest(),
        "rubric_sent": rubric,
        "selected_ids": selected,
        "judge_options": {"temperature": 0.0, "max_tokens": 1024, "response_format": {"type": "json_object"}},
        "label_source": samples["label_source"],
        "human_review_status": "pending_review",
        "independent_calibration": False,
        "cases": [],
    }
    load_dotenv(ROOT / ".env")
    try:
        provider = get_provider("deepseek")
        output["judge_model"] = provider.model
        for case in samples["cases"]:
            if case["id"] not in selected:
                continue
            record = {"id": case["id"], "expected_scores": case["expected_scores"], "status": "pending"}
            try:
                scores = evaluate_answer(
                    provider, rubric, case["question"], case["assumptions"],
                    case["documents"], case["answer"], case["reference_answer"],
                )
                actual = {dimension: scores[dimension]["score"] for dimension in DIMENSIONS}
                record.update(status="ok", scores=scores, actual_scores=actual)
                record["differences"] = {
                    dimension: {"expected": case["expected_scores"][dimension], "actual": actual[dimension]}
                    for dimension in DIMENSIONS
                    if actual[dimension] != case["expected_scores"][dimension]
                }
            except (LLMToolkitError, ValueError) as exc:
                record.update(status="judge_error", error=str(exc))
            output["cases"].append(record)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(case["id"], record["status"], record.get("differences"), flush=True)
    finally:
        close_all()


if __name__ == "__main__":
    main()
