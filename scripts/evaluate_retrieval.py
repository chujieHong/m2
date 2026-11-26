# Day 6：读取评测样例，批量检查检索证据。
import json
import argparse
from pathlib import Path
import chromadb
from fastembed import TextEmbedding

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser()
parser.add_argument("--top-k", type=int, default=1)
parser.add_argument(
    "--cases", type=Path, default=ROOT / "examples" / "eval_cases.json"
)
parser.add_argument("--collection", default="refund_bge_small_zh_v1")
args = parser.parse_args()

cases = json.loads(
    args.cases.read_text(
        encoding="utf-8"
    )
)

if not cases:
    raise ValueError("评测集不能为空")

print(f"共读取 {len(cases)} 道评测题")

client = chromadb.PersistentClient(
    path=str(ROOT / "data" / "chroma")
)

collection = client.get_collection(
    name=args.collection,
    embedding_function=None,
)

model = TextEmbedding(
    model_name="BAAI/bge-small-zh-v1.5",
    cache_dir=str(ROOT / "data" / "models"),
    threads=2,
)

top_k = args.top_k

if not 1 <= top_k <= collection.count():
    raise ValueError("top-k 必须在 1 到集合记录数之间")

coverages: list[float] = []
case_results: list[dict] = []
category_scores: dict[str, list[float]] = {}

for case in cases:
    print("\n题目 ID：", case["id"])
    print("问题：", case["question"])
    print("资料能否回答：", case["answerable"])
    print("必要依据数量：", len(case["required_evidence"]))
    query_vector = list(
        model.query_embed(case["question"])
    )[0]

    results = collection.query(
        query_embeddings=[query_vector.tolist()],
        n_results=top_k,
        include=["documents"],
    )

    documents = results["documents"][0]
    ids = results["ids"][0]
    
    case_result = {
        "id": case["id"],
        "question": case["question"],
        "answerable": case["answerable"],
        "category": case["category"],
        "retrieved_ids": ids,
        "retrieved_char_count": sum(len(document) for document in documents),
        "coverage": None,
        "missing_evidence": None,
    }
    case_results.append(case_result)

    for chunk_id, document in zip(ids, documents):
        print("命中片段：", chunk_id)
        print(document)

    if not case["answerable"]:
        print("此题资料不足，暂不计算依据覆盖率。")
        continue

    required_evidence = case["required_evidence"]

    if not required_evidence:
        raise ValueError("可回答题目必须标注必要依据")

    hit_count = 0
    missing_evidence: list[str] = []

    for evidence in required_evidence:
        found = False

        for document in documents:
            if evidence in document:
                found = True
                break

        if found:
            hit_count += 1
        else:
            missing_evidence.append(evidence)

        print("依据：", evidence)
        print("是否找到：", found)

    coverage = hit_count / len(required_evidence)
    case_result["coverage"] = coverage
    case_result["missing_evidence"] = missing_evidence
    coverages.append(coverage)
    category = case["category"]

    if category not in category_scores:
        category_scores[category] = []

    category_scores[category].append(coverage)

    print(
        f"依据覆盖率：{hit_count}/"
        f"{len(required_evidence)} = {coverage:.0%}"
    )
    if missing_evidence:
        print("缺失依据：", missing_evidence)
    
print("\n=== 评测汇总 ===")
print("候选数量：", top_k)
print("参与覆盖率评分的题数：", len(coverages))
print("未参与评分的题数：", len(cases) - len(coverages))

if coverages:
    average_coverage = sum(coverages) / len(coverages)
    print(f"平均依据覆盖率：{average_coverage:.0%}")
else:
    print("没有可计算覆盖率的题目。")
    
report = {
    "cases_path": str(args.cases.resolve()),
    "collection": args.collection,
    "collection_count": collection.count(),
    "embedding_model": "BAAI/bge-small-zh-v1.5",
    "top_k": top_k,
    "scored_count": len(coverages),
    "average_coverage": (
        sum(coverages) / len(coverages)
        if coverages
        else None
    ),
    "cases": case_results,
    "category_summary": {
        category: {
            "scored_count": len(scores),
            "average_coverage": sum(scores) / len(scores),
        }
        for category, scores in category_scores.items()
    },
}

output_dir = ROOT / "data" / "eval_results"
output_dir.mkdir(parents=True, exist_ok=True)

output_path = output_dir / (
    f"{args.collection}_{args.cases.stem}_top{top_k}.json"
)

output_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("结果已保存：", output_path)

print("\n=== 按题型汇总 ===")

for category, scores in category_scores.items():
    average = sum(scores) / len(scores)

    print(
        f"{category}：{len(scores)} 题，"
        f"平均依据覆盖率 {average:.0%}"
    )
