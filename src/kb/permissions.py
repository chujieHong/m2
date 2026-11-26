from typing import Any
from chromadb.api.models.Collection import Collection
from chromadb.api.types import QueryResult
import numpy as np
def build_permission_filter(
    *,
    tenant_id: str,
    user_id: str,
) -> dict[str, Any]:
    if not tenant_id.strip() or not user_id.strip():
        raise ValueError("缺少租户或用户身份，拒绝检索")

    return {
        "$and": [
            {"tenant_id": tenant_id},
            {
                "$or": [
                    {"visibility": "tenant"},
                    {
                        "$and": [
                            {"visibility": "private"},
                            {"owner_id": user_id},
                        ]
                    },
                ]
            },
        ]
    }
    
def query_with_permissions(
    collection: Collection,
    query_vector: list[float],
    *,
    tenant_id: str,
    user_id: str,
    top_k: int = 5,
    source: str | None = None,
) -> QueryResult:
    if top_k <= 0:
        raise ValueError("top_k 必须大于 0")

    permission_filter = build_permission_filter(
        tenant_id=tenant_id,
        user_id=user_id,
    )

    if source is not None:
        if not source.strip():
            raise ValueError("source 不能是空白字符串")

        permission_filter = {
            "$and": [
                permission_filter,
                {"source": source},
            ]
        }

    return collection.query(
        query_embeddings=np.asarray(
            [query_vector],
            dtype=np.float32,
        ),
        n_results=top_k,
        where=permission_filter,
        include=["documents", "metadatas", "distances"],
    )