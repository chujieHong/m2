from uuid import uuid4

import chromadb
import pytest

from kb.permissions import query_with_permissions


@pytest.fixture
def collection():
    client = chromadb.EphemeralClient()
    collection = client.create_collection(
        name=f"permission_test_{uuid4().hex}",
        embedding_function=None,
        configuration={"hnsw": {"space": "cosine"}},
    )

    records = [
        ("a-public", {
            "tenant_id": "a",
            "visibility": "tenant",
            "owner_id": "admin",
        }),
        ("a-mine", {
            "tenant_id": "a",
            "visibility": "private",
            "owner_id": "u1",
        }),
        ("a-other", {
            "tenant_id": "a",
            "visibility": "private",
            "owner_id": "u2",
        }),
        ("b-public", {
            "tenant_id": "b",
            "visibility": "tenant",
            "owner_id": "admin",
        }),
        ("unknown-visibility", {
            "tenant_id": "a",
            "visibility": "unknown",
            "owner_id": "u1",
        }),
        ("missing-tenant", {
            "visibility": "tenant",
            "owner_id": "u1",
        }),
    ]

    collection.upsert(
        ids=[record_id for record_id, _ in records],
        documents=[record_id for record_id, _ in records],
        embeddings=[[1.0, 0.0] for _ in records],
        metadatas=[metadata for _, metadata in records],
    )

    yield collection
    client.delete_collection(collection.name)


@pytest.mark.parametrize(
    "tenant_id,user_id,expected",
    [
        ("a", "u1", {"a-public", "a-mine"}),
        ("a", "u2", {"a-public", "a-other"}),
        ("a", "u3", {"a-public"}),
        ("b", "u1", {"b-public"}),
        ("unknown", "u1", set()),
    ],
)
def test_only_authorized_records_are_returned(
    collection, tenant_id, user_id, expected
):
    result = query_with_permissions(
        collection,
        [1.0, 0.0],
        tenant_id=tenant_id,
        user_id=user_id,
        top_k=6,
    )

    assert set(result["ids"][0]) == expected


@pytest.mark.parametrize(
    "tenant_id,user_id",
    [
        ("", "u1"),
        ("a", ""),
        ("   ", "u1"),
    ],
)
def test_missing_identity_is_rejected(collection, tenant_id, user_id):
    with pytest.raises(ValueError):
        query_with_permissions(
            collection,
            [1.0, 0.0],
            tenant_id=tenant_id,
            user_id=user_id,
        )


def test_invalid_top_k_is_rejected(collection):
    with pytest.raises(ValueError):
        query_with_permissions(
            collection,
            [1.0, 0.0],
            tenant_id="a",
            user_id="u1",
            top_k=0,
        )