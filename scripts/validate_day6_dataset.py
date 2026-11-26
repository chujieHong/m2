"""独立检查生成后的题集、资料、索引和基线报告，不调用模型接口。"""

import hashlib
import json
from collections import Counter
from pathlib import Path

import chromadb


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "examples" / "day6"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    cases_path = DATA / "oss_cases_100.json"
    corpus_path = DATA / "oss_corpus.md"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    corpus = corpus_path.read_text(encoding="utf-8")
    facts = {item["id"]: item for item in json.loads((DATA / "facts.json").read_text(encoding="utf-8"))}
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    expected = {"single_hop": 40, "multi_hop": 20, "comparison": 15, "table_numeric": 15, "unanswerable": 10}
    require(len(cases) == 100, "题数必须为 100")
    require(dict(Counter(case["category"] for case in cases)) == expected, "题型配比错误")
    require(len({case["id"] for case in cases}) == 100, "重复题目 ID")
    require(len({"".join(case["question"].split()) for case in cases}) == 100, "重复问题文本")
    for case in cases:
        case_id = case["id"]
        require(type(case["answerable"]) is bool, f"{case_id}: answerable 必须是布尔值")
        require(bool(case["question"].strip()) and bool(case["expected_answer"].strip()), f"{case_id}: 空问题或答案")
        require(case["split"] == "development", f"{case_id}: 不应将已查看题目标为独立测试集")
        evidence = case["required_evidence"]
        refs = case["evidence_ids"]
        require(bool(evidence) == case["answerable"], f"{case_id}: 可回答性与依据不一致")
        require(len(evidence) == len(set(evidence)), f"{case_id}: 重复依据")
        for ref in refs:
            require(ref in facts, f"{case_id}: 未知事实 ID")
        for quote in evidence:
            require(quote in corpus, f"{case_id}: 依据不在配套资料中")
            require(any(quote in facts[ref]["text"] for ref in refs), f"{case_id}: 来源映射错误")
        urls = list(dict.fromkeys(facts[ref]["source_url"] for ref in refs))
        require(urls == case["source_urls"], f"{case_id}: 来源 URL 不一致")
        if case["category"] == "multi_hop":
            require(len(set(refs)) >= 2, f"{case_id}: 多跳题必须有多个规则来源")
        if not case["answerable"]:
            require(not refs and bool(case["unanswerable_reason"].strip()), f"{case_id}: 缺少拒答原因")
    for name, path in (("cases", cases_path), ("corpus", corpus_path)):
        require(hashlib.sha256(path.read_bytes()).hexdigest() == manifest[f"{name}_sha256"], f"{name} 内容指纹不匹配")

    collection = chromadb.PersistentClient(path=str(ROOT / "data" / "chroma")).get_collection(
        "day6_oss_v1_bge_small_zh", embedding_function=None
    )
    indexed = collection.get(include=["documents", "metadatas"])
    documents_by_id = dict(zip(indexed["ids"], indexed["documents"]))
    require(collection.count() == 53, "固定 v1 索引条数与预期不一致")
    require(all(item["source"] == "oss_corpus.md" for item in indexed["metadatas"]), "集合混入其他文档")
    for case in cases:
        for quote in case["required_evidence"]:
            require(any(quote in document for document in indexed["documents"]), f"{case['id']}: 依据未完整入库")

    summaries = []
    for k in (1, 3):
        path = ROOT / "data" / "eval_results" / f"day6_oss_v1_bge_small_zh_oss_cases_100_top{k}.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        require(report["top_k"] == k and report["collection"] == collection.name, "基线参数错误")
        require(report["collection_count"] == 53 and report["scored_count"] == 90, "基线计数错误")
        require(len(report["cases"]) == 100, "报告漏题")
        by_id = {case["id"]: case for case in cases}
        require({result["id"] for result in report["cases"]} == set(by_id), "报告题目 ID 不对应")
        scores = []
        for result in report["cases"]:
            case = by_id[result["id"]]
            require(result["category"] == case["category"], "报告题型不对应")
            require(result["question"] == case["question"] and result["answerable"] == case["answerable"], "报告题目或标签不对应")
            ids = result["retrieved_ids"]
            require(len(ids) == len(set(ids)) == k, "候选数量或去重状态错误")
            require(all(item in documents_by_id for item in ids), "报告引用未知片段")
            documents = [documents_by_id[item] for item in ids]
            require(result["retrieved_char_count"] == sum(len(document) for document in documents), "检索文本长度不一致")
            if case["answerable"]:
                missing = result["missing_evidence"]
                expected_missing = [quote for quote in case["required_evidence"] if not any(quote in document for document in documents)]
                require(missing == expected_missing, "缺失依据与实际候选正文不一致")
                require(all(item in case["required_evidence"] for item in missing), "未知缺失依据")
                score = (len(case["required_evidence"]) - len(missing)) / len(case["required_evidence"])
                require(abs(score - result["coverage"]) < 1e-12, "逐题评分不一致")
                scores.append(score)
            else:
                require(result["coverage"] is None and result["missing_evidence"] is None, "资料不足题不应被算为检索成功")
        require(abs(report["average_coverage"] - sum(scores) / len(scores)) < 1e-12, "平均分错误")
        for category, summary in report["category_summary"].items():
            group = [result["coverage"] for result in report["cases"] if result["category"] == category and result["coverage"] is not None]
            require(summary["scored_count"] == len(group), "题型计数错误")
            require(abs(summary["average_coverage"] - sum(group) / len(group)) < 1e-12, "题型均值错误")
        summaries.append({"top_k": k, "average_coverage": report["average_coverage"], "category_summary": report["category_summary"], "report_path": str(path)})
    summary = {
        "dataset_version": "v1",
        "cases_sha256": manifest["cases_sha256"],
        "corpus_sha256": manifest["corpus_sha256"],
        "collection": collection.name,
        "collection_count": collection.count(),
        "case_count": 100,
        "scored_count": 90,
        "unanswerable_count": 10,
        "baselines": summaries,
        "generation_evaluated": False,
        "review_status": "assistant_reviewed_and_programmatically_checked",
    }
    (DATA / "baseline.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("100 题配比、唯一性、标注、来源、指纹、索引和报告一致性检查通过。")
    for item in summaries:
        print(f"top-{item['top_k']}: {item['average_coverage']:.2%}")
        for category, value in item["category_summary"].items():
            print(f"  {category}: {value['average_coverage']:.2%}")


if __name__ == "__main__":
    main()
