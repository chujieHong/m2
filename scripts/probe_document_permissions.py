from uuid import uuid4
from kb.permissions import (
    build_permission_filter,
    query_with_permissions,
)
import chromadb


client = chromadb.EphemeralClient()
collection = client.create_collection(
    name=f"day18_permissions_{uuid4().hex}",
    embedding_function=None,
    configuration={"hnsw": {"space": "cosine"}},
)

collection.upsert(
    ids=["a-public", "a-mine", "a-other", "b-public"],
    documents=[
        "公司A：租户内公开资料。",
        "公司A：user-001 的私人资料。",
        "公司A：user-002 的私人资料。",
        "公司B：租户内公开资料。",
    ],
    embeddings=[
        [0.8, 0.2],
        [0.9, 0.1],
        [1.0, 0.0],
        [1.0, 0.0],
    ],
    metadatas=[
        {
            "tenant_id": "tenant-a",
            "visibility": "tenant",
            "owner_id": "admin-a",
        },
        {
            "tenant_id": "tenant-a",
            "visibility": "private",
            "owner_id": "user-001",
        },
        {
            "tenant_id": "tenant-a",
            "visibility": "private",
            "owner_id": "user-002",
        },
        {
            "tenant_id": "tenant-b",
            "visibility": "tenant",
            "owner_id": "admin-b",
        },
    ],
)

# 模拟已经由服务端确认的用户身份。
cases = [
    ("tenant-a", "user-001", {"a-public", "a-mine"}),
    ("tenant-a", "user-002", {"a-public", "a-other"}),
    ("tenant-b", "user-001", {"b-public"}),
    ("tenant-unknown", "user-001", set()),
]

for tenant_id, user_id, expected_ids in cases:
    result = query_with_permissions(
        collection,
        [1.0, 0.0],
        tenant_id=tenant_id,
        user_id=user_id,
        top_k=4,
    )

    actual_ids = set(result["ids"][0])

    print(tenant_id, user_id, "→", sorted(actual_ids))
    assert actual_ids == expected_ids

for tenant_id, user_id in [
    ("", "user-001"),
    ("tenant-a", ""),
    ("   ", "user-001"),
]:
    try:
        build_permission_filter(
            tenant_id=tenant_id,
            user_id=user_id,
        )
    except ValueError:
        print("已拒绝缺失身份的请求。")
    else:
        raise AssertionError("缺失身份时不应允许继续检索")

print("全部权限场景验证通过。")