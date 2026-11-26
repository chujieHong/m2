from uuid import uuid4

import chromadb


client = chromadb.EphemeralClient()

collection = client.create_collection(
    name=f"day18_{uuid4().hex}",
    embedding_function=None,
    configuration={"hnsw": {"space": "cosine"}},
)

collection.upsert(
    ids=["a-refund", "b-refund"],
    documents=[
        "公司A：退款在审核通过后3个工作日内到账。",
        "公司B：退款在审核通过后5个工作日内到账。",
    ],
    embeddings=[
        [0.9, 0.1],
        [1.0, 0.0],
    ],
    metadatas=[
        {"tenant_id": "tenant-a"},
        {"tenant_id": "tenant-b"},
    ],
)

# 模拟服务端确认的登录身份，不是用户在问题里填写的租户。
current_user = {
    "user_id": "user-001",
    "tenant_id": "tenant-a",
}

query_vector = [1.0, 0.0]

unfiltered = collection.query(
    query_embeddings=[query_vector],
    n_results=1,
    include=["documents", "metadatas"],
)

filtered = collection.query(
    query_embeddings=[query_vector],
    n_results=1,
    where={"tenant_id": current_user["tenant_id"]},
    include=["documents", "metadatas"],
)

print("未限定租户：", unfiltered["documents"][0])
print("限定当前租户：", filtered["documents"][0])

assert unfiltered["ids"][0] == ["b-refund"]
assert filtered["ids"][0] == ["a-refund"]

print("验证通过：即使其他租户的向量更接近，也只返回当前租户的资料。")