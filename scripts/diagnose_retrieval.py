"""Day 6：诊断一个失败样例；子问题为人工设计，不调用生成模型。"""

import json
from pathlib import Path

import chromadb
from fastembed import TextEmbedding


ROOT = Path(__file__).resolve().parents[1]
cases = json.loads(
    (ROOT / "examples" / "oss_acl_cases.json").read_text(encoding="utf-8")
)
case = next(case for case in cases if case["id"] == "oss_inherited_public_read")
collection = chromadb.PersistentClient(
    path=str(ROOT / "data" / "chroma")
).get_collection("oss_acl_bge_small_zh_v1", embedding_function=None)
model = TextEmbedding(
    model_name="BAAI/bge-small-zh-v1.5",
    cache_dir=str(ROOT / "data" / "models"),
    threads=2,
)


def retrieve(question: str, count: int) -> dict:
    vector = list(model.query_embed(question))[0]
    return collection.query(
        query_embeddings=[vector.tolist()],
        n_results=count,
        include=["documents", "metadatas", "distances"],
    )


def summarize(label: str, ids: list[str], documents: list[str]) -> dict:
    missing = [
        evidence
        for evidence in case["required_evidence"]
        if not any(evidence in document for document in documents)
    ]
    summary = {
        "strategy": label,
        "retrieved_ids": ids,
        "retrieved_char_count": sum(len(document) for document in documents),
        "coverage": 1 - len(missing) / len(case["required_evidence"]),
        "missing_evidence": missing,
    }
    print(label, json.dumps(summary, ensure_ascii=False))
    return summary


all_records = collection.get(include=["documents"])
for evidence in case["required_evidence"]:
    assert any(evidence in document for document in all_records["documents"]), (
        f"依据未完整入库：{evidence}"
    )
print("两条必要依据均完整存在于集合中。")

ranked = retrieve(case["question"], collection.count())
ranking = []
for index, chunk_id in enumerate(ranked["ids"][0]):
    item = {
        "rank": index + 1,
        "id": chunk_id,
        "heading_path": ranked["metadatas"][0][index]["heading_path"],
        "distance": ranked["distances"][0][index],
    }
    ranking.append(item)
    print(json.dumps(item, ensure_ascii=False))

strategies = []
for k in (1, 2, 3):
    result = retrieve(case["question"], k)
    strategies.append(
        summarize(f"原问题 top-{k}", result["ids"][0], result["documents"][0])
    )

subquestions = [
    "上传 Object 时未指定 ACL，它会采用什么权限？",
    "public-read 给匿名用户哪些读取和写入权限？",
]
merged = {}
for question in subquestions:
    result = retrieve(question, 1)
    for chunk_id, document in zip(result["ids"][0], result["documents"][0]):
        merged[chunk_id] = document
strategies.append(
    summarize("人工拆成两个子问题，各取 top-1 并按 ID 去重", list(merged), list(merged.values()))
)

output_path = ROOT / "data" / "eval_results" / "oss_multi_hop_diagnosis.json"
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(
    json.dumps(
        {"case_id": case["id"], "ranking": ranking, "subquestions": subquestions, "strategies": strategies},
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print("诊断结果已保存：", output_path)
