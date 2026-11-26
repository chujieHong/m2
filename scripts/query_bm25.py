import argparse
from pathlib import Path

import chromadb

from kb.bm25 import BM25

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser()
parser.add_argument("question")
args = parser.parse_args()

client = chromadb.PersistentClient(
    path=str(ROOT / "data" / "chroma")
)
collection = client.get_collection(
    "day10_oss_qwen_06b_v1",
    embedding_function=None,
)

records = collection.get(
    include=["documents", "metadatas"]
)

documents = records["documents"]
metadatas = records["metadatas"]
if not documents or metadatas is None:
    raise ValueError("集合缺少正文或元数据")

retriever = BM25(documents)
scores = retriever.score(args.question)

ranked_scores = sorted(
    enumerate(scores),
    key=lambda item: item[1],
    reverse=True,
)

hits = [
    (index, score)
    for index, score in ranked_scores
    if score > 0
][:5]

if not hits:
    print("没有匹配到查询词的片段。")

for index, score in hits:
    metadata = metadatas[index] or {}

    print(f"\n片段 ID：{records['ids'][index]}")
    print(f"BM25 分数：{score:.4f}")
    print("标题路径：", metadata.get("heading_path", "未知"))
    print("正文：", documents[index])