"""Day 8：整理已有证据，固定第一份基线；不重新调用模型。"""

import hashlib
import json
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "examples/day8"


def main() -> None:
    paths = {
        "manifest": ROOT / "examples/day6/manifest.json",
        "retrieval": ROOT / "examples/day7/retrieval_baseline.json",
        "answers": ROOT / "data/eval_results/day7_answers_100_top3.json",
        "generation": ROOT / "data/eval_results/day7_generation_summary_100_top3_format.json",
        "ai_review": ROOT / "data/eval_results/day7_ai_judge_agreement_39.json",
        "ragas_faithfulness": ROOT / "data/eval_results/ragas_faithfulness_single_hop_001_numbered.json",
        "ragas_relevancy": ROOT / "data/eval_results/ragas_relevancy_comparison.json",
    }
    data = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in paths.items()}
    answers = data["answers"]
    generation = data["generation"]
    digest = hashlib.sha256(paths["answers"].read_bytes()).hexdigest()
    if digest != generation["source_answers_sha256"]:
        raise ValueError("生成汇总与原始回答不一致")
    if answers["cases_sha256"] != data["manifest"]["cases_sha256"]:
        raise ValueError("题集版本不一致")
    successful = [case for case in answers["cases"] if case["status"] == "ok"]
    if len(successful) != 100 or any(not case.get("usage") for case in successful):
        raise ValueError("基线要求完整100条成功生成及其用量")
    tokens = {"input": 0, "cache_hit": 0, "cache_miss": 0, "output": 0}
    for case in successful:
        usage = case["usage"]
        hit = usage["prompt_cache_hit_tokens"]
        miss = usage["prompt_cache_miss_tokens"]
        if hit + miss != usage["prompt_tokens"]:
            raise ValueError("缓存用量与输入总数不一致")
        tokens["input"] += usage["prompt_tokens"]
        tokens["cache_hit"] += hit
        tokens["cache_miss"] += miss
        tokens["output"] += usage["completion_tokens"]
    # 2026-10-13 核对官方价目，单位USD/百万token。历史记录无每请求开始UTC时间。
    prices = {
        "checked_on": "2026-10-13", "unit": "USD per million tokens",
        "source": "https://api-docs.deepseek.com/quick_start/pricing/",
        "off_peak": {"cache_hit": 0.003, "cache_miss": 0.15, "output": 0.60},
        "peak": {"cache_hit": 0.006, "cache_miss": 0.30, "output": 1.20},
    }
    estimates = {
        period: sum(tokens[key] * price for key, price in prices[period].items()) / 1_000_000
        for period in ("off_peak", "peak")
    }
    latency = median(case["elapsed_seconds"] for case in successful)
    baseline = {
        "baseline_version": "day8-v1", "prepared_on": "2026-10-13",
        "configuration": {
            "dataset_version": "v1", "case_count": 100,
            "cases_sha256": answers["cases_sha256"],
            "corpus_sha256": data["manifest"]["corpus_sha256"],
            "collection": answers["collection"], "collection_count": 53,
            "embedding_model": "BAAI/bge-small-zh-v1.5", "embedding_dimensions": 512,
            "chunk_body_size": 400, "overlap": 0,
            "generation_top_k": answers["top_k"], "model": answers["model"],
            "generation_options": answers["generation_options"],
            "judge_rubric_sha256": generation["judge_rubric_sha256"],
        },
        "retrieval": data["retrieval"],
        "generation_custom": generation["scores"],
        "generation_category_summary": generation["category_summary"],
        "refusals": {
            "corpus_unanswerable": generation["refusal_behavior"]["corpus_unanswerable"],
            "corpus_answerable": generation["refusal_behavior"]["corpus_answerable"],
            "partial_answer_count": generation["refusal_behavior"]["partial_answer_count"],
            "label_source": generation["behavior_label_source"],
        },
        "latency": {
            "generation_call_p50_seconds": latency, "sample_count": 100,
            "scope": "保存片段后计时，含M1非流式调用及返回结果处理；不含检索、向量化、模型初始化或裁判评分",
            "full_rag_p50_seconds": None, "time_to_first_token_seconds": None,
        },
        "generation_tokens": tokens,
        "generation_cost_estimate": {
            "prices": prices, "total_100_usd": estimates,
            "mean_per_question_usd": {period: cost / 100 for period, cost in estimates.items()},
            "scope": "只估算100次答案生成；不含开发探针、裁判、RAGAS、重试与本地机器成本；不是实际账单",
            "limitation": "用本次核对价格与保存的缓存用量重估；无逐请求开始UTC时间，列全低峰/全高峰两种假设",
        },
        "ragas_small_examples": {
            "faithfulness": data["ragas_faithfulness"]["faithfulness"], "faithfulness_case_count": 1,
            "answer_relevancy": [
                {key: case[key] for key in ("id", "origin", "answer_relevancy")}
                for case in data["ragas_relevancy"]["cases"]
            ],
            "scope": "小样例与教学反例，不是100题RAGAS整体指标",
        },
        "ai_review": {
            "case_count": 39, "dimension_agreement": data["ai_review"]["dimension_agreement"],
            "all_three_agreement": data["ai_review"]["all_three_agreement"],
            "scope": "AI交叉审核，不是独立人工校准",
        },
        "sources": {name: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for name, path in paths.items()},
        "remaining": ["统一配置与实验入口", "完整RAG端到端延迟", "实际账单核对", "独立人工校准或独立测试集"],
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "baseline_v1.json").write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = "\n".join(
        f"| {row['k']} | {row['mean_recall']:.2%} | {row['mrr']:.4f} | {row['mean_ndcg']:.4f} |"
        for row in data["retrieval"]["results"]
    )
    markdown = f"""# Day 8：初始基线 v1

整理日期：2026-10-13。此报告汇总已保存的真实运行，没有重新生成答案。配置及证据指纹见 baseline_v1.json；后续优化须保持可比较的题集、资料版本与评分方法。

固定100题开发/回归集，53条索引；BGE-small-zh-v1.5（512维），正文上限400字符、overlap=0、Chroma cosine。答案生成使用top-3、DeepSeek Flash、temperature=0、max_tokens=512。

## 检索基线

90道可回答题计入均值，10道资料不足题不计入检索指标。标签是必要事实对应片段，不是全部语义相关片段的穷尽标注。

| k | Recall@k | MRR@k | nDCG@k |
| --- | ---: | ---: | ---: |
{rows}

## 生成与拒答

100题自定义裁判平均分：正确性1.91/2、忠实度1.96/2、相关性2.00/2。与上表不同，生成只使用top-3；不能说top-20生成已验证。尚非独立人工校准分数。

完整资料不足题拒答10/10；可回答题完整拒答4/90；另有4条部分回答。拒答行为由助手审核；可回答题拒答不自动等于错误拒答，需检查实际片段充分性。

## 延迟与成本

100次非流式答案生成调用p50：**{latency:.4f}秒**。范围是调用及返回处理，不含检索、向量化、模型初始化、裁判或RAGAS。完整RAG端到端p50及首token延迟尚未测量，不能用此值代替。

生成输入总计{tokens['input']} tokens（缓存命中{tokens['cache_hit']}、未命中{tokens['cache_miss']}），输出{tokens['output']} tokens。

按2026-10-13核对价格，100次生成在全低峰/全高峰假设下估算 **${estimates['off_peak']:.6f}～${estimates['peak']:.6f}**，平均每题 **${estimates['off_peak']/100:.8f}～${estimates['peak']/100:.8f}**。仅为按用量重估，不是实际账单；不含所有开发、裁判与重试调用费用。[DeepSeek官方价目](https://api-docs.deepseek.com/quick_start/pricing/)

## RAGAS 与复核的范围

RAGAS Faithfulness仅实测一条真实回答和编号格式对照；AnswerRelevancy实测同一问题的一条真实回答与两条教学反例，不记为100题均值。39条由当前助手交叉审核，1条有用户初次评分，不冒充40条独立人工校准。

## 接下来

统一配置与实验入口，并在同一题集上一次只改变一个因素。补测完整链路延迟时使用一致计时边界；修改裁判规则需单独版本，不能与优化模型同时改变后混算收益。
"""
    (OUTPUT / "baseline_v1.md").write_text(markdown, encoding="utf-8")
    print("Generation call p50:", latency)
    print("Generation cost estimates:", estimates)
    print(OUTPUT / "baseline_v1.md")


if __name__ == "__main__":
    main()
