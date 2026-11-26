"""只读取保存记录，分开汇总生成评分与拒答行为，不调用模型。"""

import argparse
import hashlib
import json
from pathlib import Path

from kb.answer_evaluation import parse_judge_result


ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = ("correctness", "faithfulness", "relevance")


def unique_cases(data: dict) -> dict:
    cases = {case["id"]: case for case in data["cases"]}
    if len(cases) != len(data["cases"]):
        raise ValueError("存在重复题目 ID")
    return cases


def fraction(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": numerator / denominator if denominator else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--answers", type=Path, default=ROOT / "data/eval_results/day7_answers_sample.json")
    parser.add_argument("--judgments", type=Path, default=ROOT / "data/eval_results/day7_judge_sample.json")
    parser.add_argument("--behaviors", type=Path, default=ROOT / "examples/day7/response_behavior_labels.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/eval_results/day7_generation_summary.json")
    args = parser.parse_args()
    if args.output.resolve() in {path.resolve() for path in (args.answers, args.judgments, args.behaviors)}:
        raise ValueError("输出不能覆盖输入")
    answer_bytes = args.answers.read_bytes()
    judgments = json.loads(args.judgments.read_text(encoding="utf-8"))
    behaviors = json.loads(args.behaviors.read_text(encoding="utf-8"))
    digest = hashlib.sha256(answer_bytes).hexdigest()
    if digest != judgments["source_answers_sha256"] or digest != behaviors["source_answers_sha256"]:
        raise ValueError("评分或行为标注并非来自这份回答记录")
    answers = unique_cases(json.loads(answer_bytes.decode("utf-8")))
    judges = unique_cases(judgments)
    labels = unique_cases(behaviors)
    if set(answers) != set(judges) or set(answers) != set(labels):
        raise ValueError("回答、评分、行为标注的题目集合不一致")

    scored = []
    generated = []
    for case_id, answer in answers.items():
        judge = judges[case_id]
        label = labels[case_id]
        if answer["question"] != judge["question"] or answer["answer"] != judge["answer"]:
            raise ValueError("评分对应的问题或回答已变化")
        if type(label["refused"]) is not bool:
            raise ValueError("拒答标注必须是布尔值")
        if "response_behavior" in label:
            if label["response_behavior"] not in {"answered", "partial_answer", "refused"}:
                raise ValueError("未知回答行为标签")
            if label["refused"] != (label["response_behavior"] == "refused"):
                raise ValueError("完整拒答与回答行为标签不一致")
        if label["context_sufficient"] is not None and type(label["context_sufficient"]) is not bool:
            raise ValueError("资料充分性必须是布尔值或 null")
        if type(answer["answerable"]) is not bool:
            raise ValueError("题集可回答性标注必须是布尔值")
        if answer["status"] == "ok":
            generated.append(answer)
            if judge["status"] == "ok":
                parse_judge_result(json.dumps(judge["scores"]))
                scored.append(answer)

    by_dimension = {}
    for dimension in DIMENSIONS:
        scores = [judges[answer["id"]]["scores"][dimension]["score"] for answer in scored]
        by_dimension[dimension] = {
            "scored_count": len(scores),
            "mean_score": sum(scores) / len(scores) if scores else None,
            "score_counts": {str(score): scores.count(score) for score in (0, 1, 2)},
            "full_score_fraction": fraction(scores.count(2), len(scores)),
        }

    category_summary = {}
    for category in sorted({answer["category"] for answer in answers.values()}):
        category_cases = [answer for answer in scored if answer["category"] == category]
        category_summary[category] = {
            "selected_count": sum(answer["category"] == category for answer in answers.values()),
            "scored_count": len(category_cases),
            "mean_scores": {
                dimension: (
                    sum(judges[answer["id"]]["scores"][dimension]["score"] for answer in category_cases) / len(category_cases)
                    if category_cases else None
                )
                for dimension in DIMENSIONS
            },
        }

    # 题集整体是否有答案，与本次检索片段是否足够，是不同的条件。
    corpus_answerable = [answer for answer in generated if answer["answerable"]]
    corpus_unanswerable = [answer for answer in generated if not answer["answerable"]]
    context_sufficient = [answer for answer in generated if labels[answer["id"]]["context_sufficient"] is True]
    context_insufficient = [answer for answer in generated if labels[answer["id"]]["context_sufficient"] is False]
    count_refusals = lambda group: sum(labels[answer["id"]]["refused"] for answer in group)
    output = {
        "source_answers": str(args.answers.resolve()),
        "source_judgments": str(args.judgments.resolve()),
        "source_behaviors": str(args.behaviors.resolve()),
        "source_answers_sha256": digest,
        "judgments_sha256": hashlib.sha256(args.judgments.read_bytes()).hexdigest(),
        "behaviors_sha256": hashlib.sha256(args.behaviors.read_bytes()).hexdigest(),
        "judge_rubric_sha256": judgments["rubric_sha256"],
        "judge_model": judgments["judge_model"],
        "calibration_status": judgments["calibration_status"],
        "behavior_label_source": behaviors["label_source"],
        "refusal_definition": behaviors.get("refusal_definition", "refused 统计完整拒答"),
        "human_review_status": "pending_review",
        "selected_count": len(answers),
        "generation_success_count": len(generated),
        "generation_failure_count": len(answers) - len(generated),
        "judged_count": len(scored),
        "successful_answers_without_valid_judgment": len(generated) - len(scored),
        "scores": by_dimension,
        "category_summary": category_summary,
        "refusal_behavior": {
            "partial_answer_count": sum(labels[answer["id"]].get("response_behavior") == "partial_answer" for answer in generated),
            "all_successful_answers": fraction(count_refusals(generated), len(generated)),
            "corpus_unanswerable": fraction(count_refusals(corpus_unanswerable), len(corpus_unanswerable)),
            "corpus_answerable": fraction(count_refusals(corpus_answerable), len(corpus_answerable)),
            "context_sufficient_unnecessary_refusal": fraction(count_refusals(context_sufficient), len(context_sufficient)),
            "context_insufficient_refusal": fraction(count_refusals(context_insufficient), len(context_insufficient)),
            "context_sufficiency_pending_ids": [answer["id"] for answer in generated if labels[answer["id"]]["context_sufficient"] is None],
        },
        "limitations": [
            "仅汇总本次选择的开发题集回答，不代表独立测试集或生产分布。",
            "平均分及满分比例是模型裁判结果，不是独立人工准确率。",
            "拒答行为来自助手审核标注，不以关键词猜测替代语义标注。",
            "接口或评分失败单独计数，不当作得分 0 或非拒答。",
            "题集可回答题的拒答不一定是错误拒答，可能是检索片段不足。",
            "分母为 0 时比例为 null，不记为 0%。",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Summarized", len(generated), "answers and", len(scored), "valid judgments")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
