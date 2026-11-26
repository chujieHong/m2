import json
from pathlib import Path

import chromadb
from fastembed.rerank.cross_encoder import TextCrossEncoder

ROOT = Path(__file__).resolve().parents[1]

report_path = ROOT / "data" / "eval_results" / "day13" / (
    "reranker_top5_1792239873697678300.json"
)
report = json.loads(report_path.read_text(encoding="utf-8"))

case_result = next(
    item
    for item in report["cases"]
    if item["id"] == "multi_hop_011"
)
candidate_ids = case_result["candidate_ids"]

cases_path = ROOT / "examples" / "day6" / "oss_cases_100.json"
cases = json.loads(cases_path.read_text(encoding="utf-8"))
case = next(
    item for item in cases
    if item["id"] == "multi_hop_011"
)

client = chromadb.PersistentClient(
    path=str(ROOT / "data" / "chroma")
)
collection = client.get_collection(
    report["collection"],
    embedding_function=None,
)
records = collection.get(
    ids=candidate_ids,
    include=["documents"],
)

document_by_id = dict(
    zip(records["ids"], records["documents"])
)
documents = [
    document_by_id[chunk_id]
    for chunk_id in candidate_ids
]

reranker = TextCrossEncoder(
    model_name=report["model_name"],
    cache_dir=str(ROOT / "data" / "models"),
    threads=2,
    cuda=False,
    local_files_only=True,
)

questions = [
    ("原问题", case["question"]),
    ("明确中间条件", "当前版本为删除标记时，读取当前版本会怎样？"),
]

for name, question in questions:
    scores = list(
        reranker.rerank(
            query=question,
            documents=documents,
            batch_size=1,
        )
    )

    ranked = sorted(
        zip(candidate_ids, scores),
        key=lambda item: item[1],
        reverse=True,
    )

    print(f"\n{name}：{question}")
    for rank, (chunk_id, score) in enumerate(ranked, 1):
        print(f"{rank:2d}  {chunk_id}  {score:.4f}")