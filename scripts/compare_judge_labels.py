"""比较实际填写的人工分数与模型裁判，不自动补人工标注。"""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = ("correctness", "faithfulness", "relevance")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, default=ROOT / "examples/day7/human_calibration_40.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/eval_results/day7_human_judge_agreement.json")
    parser.add_argument("--reviewer", choices=("human", "assistant"), default="human")
    args = parser.parse_args()
    labels = json.loads(args.labels.read_text(encoding="utf-8"))
    if args.reviewer == "assistant" and labels.get("reviewer_type") != "assistant":
        raise ValueError("AI复核必须提供标为assistant的记录")
    if args.reviewer == "human" and labels.get("reviewer_type") == "assistant":
        raise ValueError("AI复核不能作为人工评分")
    if args.reviewer == "assistant" and args.output.resolve() == (ROOT / "data/eval_results/day7_human_judge_agreement.json").resolve():
        raise ValueError("AI比较必须使用单独的输出路径")
    answers_path = Path(labels["source_answers"])
    judges_path = Path(labels["source_judgments"])
    if args.output.resolve() in {path.resolve() for path in (args.labels, answers_path, judges_path)}:
        raise ValueError("输出不能覆盖输入")
    answers_bytes = answers_path.read_bytes()
    judges_bytes = judges_path.read_bytes()
    if hashlib.sha256(answers_bytes).hexdigest() != labels["source_answers_sha256"]:
        raise ValueError("原始回答已变化")
    if hashlib.sha256(judges_bytes).hexdigest() != labels["source_judgments_sha256"]:
        raise ValueError("裁判评分已变化")
    answers = {case["id"]: case for case in json.loads(answers_bytes.decode("utf-8"))["cases"]}
    judgments = json.loads(judges_bytes.decode("utf-8"))
    if judgments["rubric_sha256"] != labels["rubric_sha256"]:
        raise ValueError("评分规则版本不一致")
    judges = {case["id"]: case for case in judgments["cases"]}
    ids = [case["id"] for case in labels["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError("人工标尺存在重复 ID")

    matched = {dimension: 0 for dimension in DIMENSIONS}
    compared = []
    pending = []
    judge_failures = []
    disagreements = []
    for case in labels["cases"]:
        answer = answers[case["id"]]
        judge = judges[case["id"]]
        if (case["question"] != answer["question"] or case["answer"] != answer["answer"]
                or case["documents"] != answer["documents"] or case["reference_answer"] != answer["expected_answer"]):
            raise ValueError("审核表的题目、资料或回答已变化")
        human_scores = case["human_scores" if args.reviewer == "human" else "assistant_scores"]
        if not isinstance(human_scores, dict) or set(human_scores) != set(DIMENSIONS):
            raise ValueError("人工分数必须包含三个维度")
        for score in human_scores.values():
            if score is not None and (type(score) is not int or score not in {0, 1, 2}):
                raise ValueError("人工分数必须为 0、1、2 或尚未填写的 null")
        if any(score is None for score in human_scores.values()):
            pending.append(case["id"])
            continue
        if judge["status"] != "ok":
            judge_failures.append(case["id"])
            continue
        compared.append(case["id"])
        differences = {}
        for dimension in DIMENSIONS:
            human = human_scores[dimension]
            model = judge["scores"][dimension]["score"]
            if human == model:
                matched[dimension] += 1
            else:
                differences[dimension] = {args.reviewer: human, "judge": model}
        if differences:
            disagreements.append({"id": case["id"], "differences": differences,
                                  "reviewer_notes": case["human_notes" if args.reviewer == "human" else "assistant_notes"]})

    count = len(compared)
    result = {
        "source_labels": str(args.labels.resolve()),
        "source_labels_sha256": hashlib.sha256(args.labels.read_bytes()).hexdigest(),
        "source_judgments_sha256": labels["source_judgments_sha256"],
        "rubric_sha256": labels["rubric_sha256"],
        "selected_count": len(ids), "compared_count": count,
        "reviewer_type": args.reviewer,
        "score_basis": ("human_scores 初次评分；不使用助手讲解后形成的 discussion_scores"
                        if args.reviewer == "human" else "assistant_scores AI复核，不是人工评分"),
        "pending_ids": pending, "judge_failure_ids": judge_failures,
        "dimension_agreement": {
            dimension: {"matched": matched[dimension], "compared": count,
                        "rate": matched[dimension] / count if count else None}
            for dimension in DIMENSIONS
        },
        "all_three_agreement": {
            "matched": count - len(disagreements), "compared": count,
            "rate": (count - len(disagreements)) / count if count else None,
        },
        "disagreements": disagreements,
        "calibration_status": ("assistant_comparison_not_human_calibration" if args.reviewer == "assistant"
                               else ("pending_human_labels" if pending else "review_disagreements")),
        "limitation": "分层困难样例的一致率不是生产准确率；高一致也不能证明双方判断正确。",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Compared:", count, "Pending:", len(pending))


if __name__ == "__main__":
    main()
