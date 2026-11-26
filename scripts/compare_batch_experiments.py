"""读取两组已完成的批量运行与裁判记录，保存配对对照；不调用模型。"""

import argparse
import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any

from kb.answer_evaluation import parse_judge_result


DIMENSIONS = ("correctness", "faithfulness", "relevance")
ROOT = Path(__file__).resolve().parents[1]


def read_arm(batch_path: Path, judge_path: Path) -> tuple[dict, dict]:
    batch_bytes = batch_path.read_bytes()
    batch = json.loads(batch_bytes)
    judge = json.loads(judge_path.read_bytes())
    exported_bytes = Path(judge["source_answers"]).read_bytes()
    exported = json.loads(exported_bytes)
    if hashlib.sha256(exported_bytes).hexdigest() != judge["source_answers_sha256"] or hashlib.sha256(batch_bytes).hexdigest() != exported["source_batch_sha256"]:
        raise ValueError("评分不是来自指定的批量回答")
    if batch["stage"] != "rag_batch" or not batch["complete"]:
        raise ValueError("完整问答实验尚未完成")
    by_id = {r["id"]: r for r in batch["cases"]}
    judged = {r["id"]: r for r in judge["cases"]}
    if len(by_id) != len(batch["cases"]) or len(judged) != len(judge["cases"]) or set(by_id) != set(judged):
        raise ValueError("回答或评分 ID 重复或缺失")
    for case_id, r in judged.items():
        if r["answer"] != by_id[case_id].get("answer") or r["question"] != by_id[case_id]["question"]:
            raise ValueError("裁判记录与原回答不一致")
        if r["status"] == "ok":
            if by_id[case_id]["status"] != "ok":
                raise ValueError("生成失败却获得有效评分")
            parse_judge_result(json.dumps(r["scores"]))
    successful = [r for r in by_id.values() if r["status"] == "ok"]
    scored = [r for r in judged.values() if r["status"] == "ok"]
    usage = [r["usage"] for r in successful if r.get("usage") is not None]
    tokens = {field: sum(u[field] for u in usage) for field in ("prompt_tokens", "completion_tokens", "total_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens")}
    if tokens["prompt_tokens"] != tokens["prompt_cache_hit_tokens"] + tokens["prompt_cache_miss_tokens"]:
        raise ValueError("缓存用量与输入用量不一致")
    summary: dict[str, Any] = {
        "config": batch["config"], "selected_count": len(by_id),
        "generation_success_count": len(successful), "generation_failure_count": len(by_id) - len(successful),
        "judged_count": len(scored), "judgment_failure_or_skipped_count": len(by_id) - len(scored),
        "usage_available_count": len(usage), "generation_tokens": tokens,
        "rag_p50_seconds": median(r["rag_seconds"] for r in successful) if successful else None,
        "generation_p50_seconds": median(r["generation_seconds"] for r in successful) if successful else None,
        "mean_scores": {d: sum(r["scores"][d]["score"] for r in scored) / len(scored) if scored else None for d in DIMENSIONS},
        "category_mean_scores": {},
    }
    for category in sorted({r["category"] for r in by_id.values()}):
        group = [r for r in scored if by_id[r["id"]]["category"] == category]
        summary["category_mean_scores"][category] = {
            "scored_count": len(group),
            "mean_scores": {d: sum(r["scores"][d]["score"] for r in group) / len(group) if group else None for d in DIMENSIONS},
        }
    return {"batch": batch, "judged": judged, "summary": summary}, judge


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", type=Path, required=True)
    parser.add_argument("--b", type=Path, required=True)
    parser.add_argument("--judge-a", type=Path, required=True)
    parser.add_argument("--judge-b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pricing-snapshot", type=Path, default=ROOT / "examples/day8/baseline_v1.json")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("输出文件已存在，避免覆盖历史对照")
    a, ja = read_arm(args.a, args.judge_a)
    b, jb = read_arm(args.b, args.judge_b)
    pricing_bytes = args.pricing_snapshot.read_bytes()
    prices = json.loads(pricing_bytes)["generation_cost_estimate"]["prices"]
    for arm in (a, b):
        if arm["summary"]["config"]["chat_model"] != "deepseek-flash":
            raise ValueError("当前价格快照仅适用于deepseek-flash")
        tokens = arm["summary"]["generation_tokens"]
        costs = {
            period: (tokens["prompt_cache_hit_tokens"] * rate["cache_hit"]
                     + tokens["prompt_cache_miss_tokens"] * rate["cache_miss"]
                     + tokens["completion_tokens"] * rate["output"]) / 1_000_000
            for period, rate in (("off_peak", prices["off_peak"]), ("peak", prices["peak"]))
        }
        arm["summary"]["generation_cost_estimate_usd"] = {
            "total_scenarios": costs,
            "mean_per_success_scenarios": {period: cost / arm["summary"]["generation_success_count"] if arm["summary"]["generation_success_count"] else None for period, cost in costs.items()},
            "scope": "仅已保存usage的成功答案生成；全低峰/全高峰假设，非实际账单；不含裁判与其他调用。",
        }
    for key in ("cases_sha256", "labels_sha256", "index_snapshot_sha256", "source_sha256"):
        if a["batch"][key] != b["batch"][key]:
            raise ValueError(f"实验共同条件变化：{key}")
    for key in ("rubric_sha256", "evaluator_sha256", "judge_model", "judge_options"):
        if ja[key] != jb[key]:
            raise ValueError(f"评分共同条件变化：{key}")
    if {k: v for k, v in a["batch"]["config"].items() if k not in ("name", "top_k")} != {k: v for k, v in b["batch"]["config"].items() if k not in ("name", "top_k")}:
        raise ValueError("本对照仅允许改变top_k和实验名称")
    ac = {r["id"]: r for r in a["batch"]["cases"]}
    bc = {r["id"]: r for r in b["batch"]["cases"]}
    if set(ac) != set(bc):
        raise ValueError("两组实际题目不一致")
    for case_id in ac:
        if any(ac[case_id][k] != bc[case_id][k] for k in ("question", "assumptions", "category")):
            raise ValueError("两组题目内容或前提不一致")
    paired = [case_id for case_id in ac if a["judged"][case_id]["status"] == b["judged"][case_id]["status"] == "ok"]
    paired_summary = {}
    changed = []
    for d in DIMENSIONS:
        deltas = [b["judged"][i]["scores"][d]["score"] - a["judged"][i]["scores"][d]["score"] for i in paired]
        paired_summary[d] = {"compared_count": len(paired), "improved_count": sum(v > 0 for v in deltas), "unchanged_count": deltas.count(0), "worsened_count": sum(v < 0 for v in deltas), "mean_score_delta": sum(deltas) / len(deltas) if deltas else None}
    for i in paired:
        delta = {d: b["judged"][i]["scores"][d]["score"] - a["judged"][i]["scores"][d]["score"] for d in DIMENSIONS}
        if any(delta.values()):
            changed.append({"id": i, "score_delta_b_minus_a": delta, "a_answer": ac[i]["answer"], "b_answer": bc[i]["answer"], "a_judgment": a["judged"][i]["scores"], "b_judgment": b["judged"][i]["scores"]})
    output = {
        "a": a["summary"], "b": b["summary"], "paired_comparison": paired_summary, "changed_cases": changed,
        "price_assumptions": prices,
        "pricing_snapshot_sha256": hashlib.sha256(pricing_bytes).hexdigest(),
        "source_sha256": {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.a, args.b, args.judge_a, args.judge_b)},
        "limitations": ["固定开发题集上的一次顺序运行，非独立测试集或随机交叉重复实验。", "评分为未独立校准的DeepSeek模型裁判自定义0至2分，不是人工准确率或RAGAS。", "费用未核对账单，token总量不能代替实际费用；统计仅含本轮生成，不含评分和其他调用。", "平均分差异需要查看逐题原因，失败或无效评分不当作0分。", "耗时受网络、服务和缓存影响，只是本轮观察。"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"a": output["a"], "b": output["b"], "paired_comparison": paired_summary}, ensure_ascii=False, indent=2))
    print(args.output)


if __name__ == "__main__":
    main()
