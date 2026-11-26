from pathlib import Path

import chromadb

from kb.embeddings import LocalEmbedding

ROOT = Path(__file__).resolve().parents[1]

client = chromadb.PersistentClient(
    path=str(ROOT / "data" / "chroma")
)

source_collection = client.get_collection(
    "day6_oss_v1_bge_small_zh",
    embedding_function=None,
)

records = source_collection.get(
    include=["documents", "metadatas"]
)

chunk_ids = records["ids"]
documents = records["documents"]
metadatas = records["metadatas"]

if not documents or metadatas is None:
    raise ValueError("源集合缺少正文或元数据")

print("读取片段数量：", len(chunk_ids))
print("第一个片段 ID：", chunk_ids[0])
print("第一个片段的元数据：", metadatas[0])

embedding = LocalEmbedding(
    model_name="Qwen/Qwen3-Embedding-0.6B-Q",
    cache_dir=ROOT / "data" / "models",
)

vectors = embedding.embed_documents(documents)

if len(vectors) != len(chunk_ids):
    raise ValueError("向量数量与片段数量不一致")

dimension = len(vectors[0])

print("使用的模型：", embedding.model_name)
print("向量数量：", len(vectors))
print("实际向量维度：", dimension)

target_collection = client.get_or_create_collection(
    name="day10_oss_qwen_06b_v1",
    embedding_function=None,
    configuration={"hnsw": {"space": "cosine"}},
    metadata={
        "embedding_model": embedding.model_name,
        "embedding_dimension": dimension,
    },
)

index_metadata = target_collection.metadata or {}

if (
    index_metadata.get("embedding_model") != embedding.model_name
    or index_metadata.get("embedding_dimension") != dimension
):
    raise ValueError("目标集合记录的模型或维度不匹配")

target_collection.upsert(
    ids=chunk_ids,
    documents=documents,
    embeddings=vectors,
    metadatas=metadatas,
)

print("\n目标集合：", target_collection.name)
print("集合中的片段数量：", target_collection.count())
print("集合元数据：", target_collection.metadata)