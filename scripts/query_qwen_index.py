from pathlib import Path
import argparse
import chromadb
from kb.generation import build_answer_messages
from kb.embeddings import LocalEmbedding
from dotenv import load_dotenv
from llm_toolkit.providers import ChatOptions, close_all, get_provider
from llm_toolkit.providers.base import extract_answer
import re

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser()
parser.add_argument(
    "--max-distance",
    type=float,
    default=None,
    help="只展示余弦距离不超过此值的片段",
)
parser.add_argument("question", help="要检索的问题")
parser.add_argument("--source", help="只检索指定来源的文档")
parser.add_argument(
    "--generate",
    action="store_true",
    help="根据检索到的资料调用 LLM 生成回答",
)
args = parser.parse_args()


where = None
if args.source is not None:
    where = {"source": args.source}

client = chromadb.PersistentClient(
    path=str(ROOT / "data" / "chroma")
)

collection = client.get_collection(
    "day10_oss_qwen_06b_v1",
    embedding_function=None,
)

index_metadata = collection.metadata or {}

model_name = index_metadata["embedding_model"]
dimension = index_metadata["embedding_dimension"]

print("集合：", collection.name)
print("片段数量：", collection.count())
print("索引使用的模型：", model_name)
print("索引向量维度：", dimension)

embedding = LocalEmbedding(
    model_name=model_name,
    cache_dir=ROOT / "data" / "models",
)

question = args.question.strip()
if not question:
    parser.error("问题不能为空")

query_vector = embedding.embed_query(question)

if len(query_vector) != dimension:
    raise ValueError("问题向量维度与索引记录不一致")

results = collection.query(
    query_embeddings=[query_vector],
    n_results=10,
    where=where,
    include=["documents", "metadatas", "distances"],
)

if not results["ids"][0]:
    print("当前筛选范围内没有找到文档片段，请检查 --source 参数。")
    raise SystemExit(0)

print("\n问题：", question)
print("检索到的片段 ID：", results["ids"][0])
print("对应的余弦距离：", results["distances"][0])

documents = results["documents"]
metadatas = results["metadatas"]
distances = results["distances"]

if documents is None or metadatas is None or distances is None:
    raise ValueError("查询结果缺少正文、元数据或距离")

kept_count = 0
answer_documents = []
answer_sources = []

for chunk_id, document, metadata, distance in zip(
    results["ids"][0],
    documents[0],
    metadatas[0],
    distances[0],
):
    if (
        args.max_distance is not None
        and distance > args.max_distance
    ):
        continue
    
    kept_count += 1
    answer_documents.append(document)
    metadata = metadata or {}
    answer_sources.append({
        "chunk_id": chunk_id,
        "source": metadata.get("source", "未知"),
        "heading_path": metadata.get("heading_path", "未知"),
    })
    
    print(f"\n片段 ID：{chunk_id}")
    print(f"余弦距离：{distance:.4f}")
    print("来源：", metadata.get("source", "未知"))
    print("标题路径：", metadata.get("heading_path", "未知"))
    print("正文：", document)

print(f"\n过滤后保留 {kept_count} 个片段。")

if kept_count == 0:
    print("候选片段的距离均超过设定阈值，请检查问题或阈值设置。")
    raise SystemExit(0)

messages = build_answer_messages(question, answer_documents)

print("\n准备发送给 LLM 的用户消息：")
print(messages[1]["content"])

if args.generate:
    load_dotenv(ROOT / ".env")

    try:
        provider = get_provider("deepseek")
        response = provider.call(
            messages,
            options=ChatOptions(
                model="deepseek-flash",
                temperature=0.0,
                max_tokens=512,
            ),
        )

        if not response.choices:
            raise ValueError("模型没有返回候选回答")

        if response.choices[0].finish_reason != "stop":
            raise ValueError("模型回答未正常完成")

        answer = extract_answer(response)
        if not answer.strip():
            raise ValueError("模型返回了空回答")

        cited_numbers = [
            int(number)
            for number in re.findall(r"\[([0-9]+)\]", answer)
        ]

        invalid_numbers = [
            number
            for number in cited_numbers
            if not 1 <= number <= len(answer_documents)
        ]

        if invalid_numbers:
            raise ValueError(
                f"回答引用了不存在的资料编号：{invalid_numbers}"
            )

        print("\n回答：", answer)
        print("\n本次提供给模型的资料编号：")
        for number, source in enumerate(answer_sources, 1):
            print(
                f"[{number}] {source['source']} | "
                f"{source['heading_path']} | "
                f"片段 ID：{source['chunk_id']}"
            )
    finally:
        close_all()