"""Day 7：对已保存的回答调用裁判，单独保存模型评分。"""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from llm_toolkit.exceptions import LLMToolkitError
from llm_toolkit.providers import close_all, get_provider

from kb.answer_evaluation import evaluate_answer


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--answers", type=Path, default=ROOT / "data/eval_results/day7_answers_sample.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/eval_results/day7_judge_sample.json")
    parser.add_argument("--case-id", action="append")
    args = parser.parse_args()
    if args.answers.resolve() == args.output.resolve():
        raise ValueError("评分输出不能覆盖原始回答")

    answer_bytes = args.answers.read_bytes()
    answers = json.loads(answer_bytes.decode("utf-8"))
    if args.case_id:
        known = {answer["id"] for answer in answers["cases"]}
        if len(args.case_id) != len(set(args.case_id)) or not set(args.case_id) <= known:
            raise ValueError("指定题目重复或不存在")
        answers["cases"] = [answer for answer in answers["cases"] if answer["id"] in args.case_id]
    cases_bytes = (ROOT / "examples/day6/oss_cases_100.json").read_bytes()
    if hashlib.sha256(cases_bytes).hexdigest() != answers["cases_sha256"]:
        raise ValueError("题集版本与回答记录不一致")
    cases = {case["id"]: case for case in json.loads(cases_bytes.decode("utf-8"))}
    rubric_path = ROOT / "examples/day7/generation_rubric.md"
    rubric_bytes = rubric_path.read_bytes()
    rubric = rubric_bytes.decode("utf-8")
    for answer in answers["cases"]:
        case = cases[answer["id"]]
        if case["question"] != answer["question"] or case["expected_answer"] != answer["expected_answer"]:
            raise ValueError("题目或参考答案与回答记录不一致")

    output = {
        "source_answers": str(args.answers.resolve()),
        "source_answers_sha256": hashlib.sha256(answer_bytes).hexdigest(),
        "cases_sha256": answers["cases_sha256"],
        "rubric_path": str(rubric_path),
        "rubric_sha256": hashlib.sha256(rubric_bytes).hexdigest(),
        "evaluator_sha256": hashlib.sha256((ROOT / "src/kb/answer_evaluation.py").read_bytes()).hexdigest(),
        "judge_options": {"temperature": 0.0, "max_tokens": 1024, "response_format": {"type": "json_object"}},
        "generator_model": answers["model"],
        "calibration_status": "not_calibrated",
        "human_review_status": "pending_review",
        "cases": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    load_dotenv(ROOT / ".env")
    try:
        provider = get_provider("deepseek")
        output["judge_model"] = provider.model
        for answer in answers["cases"]:
            case = cases[answer["id"]]
            record = {
                "id": answer["id"], "question": answer["question"],
                "answer": answer["answer"], "scores": None,
                "review_status": "pending_review", "status": "pending",
            }
            if answer["status"] != "ok":
                record["status"] = "skipped_generation_failure"
            else:
                started = perf_counter()
                print("评分：", answer["id"], flush=True)
                try:
                    record["scores"] = evaluate_answer(
                        provider=provider, rubric=rubric,
                        question=answer["question"],
                        assumptions=case.get("common_assumptions", ""),
                        documents=answer["documents"], answer=answer["answer"],
                        reference_answer=answer["expected_answer"],
                    )
                    record["status"] = "ok"
                    record["review_status"] = "llm_judged"
                except (LLMToolkitError, ValueError) as exc:
                    record["status"] = "judge_error"
                    record["error"] = str(exc)
                    if hasattr(exc, "raw_output"):
                        record["raw_output"] = exc.raw_output
                record["elapsed_seconds"] = perf_counter() - started
            output["cases"].append(record)
            args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(record, ensure_ascii=False), flush=True)
    finally:
        close_all()


if __name__ == "__main__":
    main()
