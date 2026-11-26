"""把 Day 8 批量记录转换为已有 Day 7 裁判入口接受的格式，不调用模型。"""

import argparse
import hashlib
import json
from pathlib import Path

from kb.generation import build_answer_messages


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    args = parser.parse_args()
    batch_bytes = args.batch.read_bytes()
    batch = json.loads(batch_bytes)
    if batch["stage"] != "rag_batch" or not batch["complete"]:
        raise ValueError("只转换已完成的完整问答批量记录")
    cases_bytes = (ROOT / "examples/day6/oss_cases_100.json").read_bytes()
    if hashlib.sha256(cases_bytes).hexdigest() != batch["cases_sha256"]:
        raise ValueError("题集已变化")
    cases = {case["id"]: case for case in json.loads(cases_bytes)}
    converted = []
    ids = [record["id"] for record in batch["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError("回答题目重复")
    for record in batch["cases"]:
        case = cases[record["id"]]
        documents = record["results"]["documents"][0]
        if case["question"] != record["question"] or record["messages"] != build_answer_messages(case["question"], documents, case.get("common_assumptions", "")):
            raise ValueError("生成输入与题目、检索片段不一致")
        converted.append({
            **record,
            "documents": documents,
            "retrieved_ids": record["results"]["ids"][0],
            "expected_answer": case["expected_answer"],
            "required_evidence": case["required_evidence"],
            "elapsed_seconds": record["generation_seconds"],
        })
    output = {
        "source_batch": str(args.batch.resolve()),
        "source_batch_sha256": hashlib.sha256(batch_bytes).hexdigest(),
        "cases_sha256": batch["cases_sha256"],
        "collection": batch["config"]["collection"],
        "top_k": batch["config"]["top_k"],
        "model": batch["config"]["chat_model"],
        "generation_options": {key: batch["config"][key] for key in ("temperature", "max_tokens")},
        "timing_scope": batch["timing_scope"],
        "cases": converted,
    }
    path = args.batch.with_name(args.batch.stem + "_answers.json")
    if path.exists():
        raise ValueError("转换文件已存在，请使用原文件或另行保存")
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
