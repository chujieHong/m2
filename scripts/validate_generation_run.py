"""离线核对固定 100 题生成记录、评分与汇总的来源和完整性。"""

import hashlib
import json
from collections import Counter
from pathlib import Path

from kb.answer_evaluation import parse_judge_result
from generate_eval_answers import SYSTEM_PROMPT


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    folder = ROOT / "data/eval_results"
    answers_path = folder / "day7_answers_100_top3.json"
    answers = json.loads(answers_path.read_text(encoding="utf-8"))
    judges = json.loads((folder / "day7_judge_100_top3_v2_format.json").read_text(encoding="utf-8"))
    summary = json.loads((folder / "day7_generation_summary_100_top3_format.json").read_text(encoding="utf-8"))
    cases_bytes = (ROOT / "examples/day6/oss_cases_100.json").read_bytes()
    cases = {case["id"]: case for case in json.loads(cases_bytes.decode("utf-8"))}
    answer_ids = [answer["id"] for answer in answers["cases"]]
    judge_ids = [judge["id"] for judge in judges["cases"]]
    assert len(set(answer_ids)) == len(answer_ids) == 100
    assert len(set(judge_ids)) == len(judge_ids) == 100
    assert set(cases) == set(answer_ids) == set(judge_ids)
    assert judges["source_answers_sha256"] == hashlib.sha256(answers_path.read_bytes()).hexdigest()
    assert answers["cases_sha256"] == hashlib.sha256(cases_bytes).hexdigest()
    for answer in answers["cases"]:
        case = cases[answer["id"]]
        assert answer["question"] == case["question"]
        context = "\n\n".join(f"[{index}] {text}" for index, text in enumerate(answer["documents"], 1))
        expected_user = (
            f"情景前提：{case.get('common_assumptions', '')}\n\n"
            f"资料：\n{context}\n\n问题：{case['question']}"
        )
        # 逐条重建真正的生成输入：没有注入参考答案或评分标签。
        assert answer["messages"] == [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": expected_user},
        ]
        assert len(answer["documents"]) == len(answer["retrieved_ids"]) == 3
        assert answer["status"] == "ok" and answer["finish_reason"] == "stop"
    scored = [judge for judge in judges["cases"] if judge["status"] == "ok"]
    for judge in scored:
        parse_judge_result(json.dumps(judge["scores"]))
    assert summary["judged_count"] == len(scored) == 100
    assert summary["generation_failure_count"] == summary["successful_answers_without_valid_judgment"] == 0
    for dimension in ("correctness", "faithfulness", "relevance"):
        scores = [judge["scores"][dimension]["score"] for judge in scored]
        assert summary["scores"][dimension]["mean_score"] == sum(scores) / len(scores)
        assert summary["scores"][dimension]["score_counts"] == {str(score): Counter(scores)[score] for score in (0, 1, 2)}
    assert summary["refusal_behavior"]["corpus_unanswerable"]["denominator"] == 10
    assert summary["refusal_behavior"]["corpus_answerable"]["denominator"] == 90
    print("Verified 100 cases, generation inputs, provenance, score schema and aggregate accounting")
    print("Semantic correctness and human calibration remain separate review tasks")


if __name__ == "__main__":
    main()
