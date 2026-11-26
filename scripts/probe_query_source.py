from pathlib import Path
from uuid import uuid4

import chromadb
from dotenv import load_dotenv
from llm_toolkit.providers import close_all, get_provider

from kb.permissions import query_with_permissions
from plan_query import plan_query


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

client = chromadb.EphemeralClient()
collection = client.create_collection(
    name=f"day19_source_{uuid4().hex}",
    embedding_function=None,
)

collection.upsert(
    ids=["refund", "invoice", "private"],
    embeddings=[[1.0, 0.0]] * 3,
    metadatas=[
        {"source": "refund_policy.md", "tenant_id": "a", "visibility": "tenant"},
        {"source": "invoice_policy.md", "tenant_id": "a", "visibility": "tenant"},
        {
            "source": "private_policy.md",
            "tenant_id": "a",
            "visibility": "private",
            "owner_id": "u2",
        },
    ],
)

cases = [
    ("退款多久到账？", None, {"refund", "invoice"}),
    ("只查 refund_policy.md，退款多久到账？", "refund_policy.md", {"refund"}),
    ("只查 private_policy.md，退款多久到账？", "private_policy.md", set()),
    ("只查 missing.md，退款多久到账？", "missing.md", set()),
]

try:
    provider = get_provider("deepseek")

    for question, expected_source, expected_ids in cases:
        plan = plan_query(provider, history=[], question=question)

        assert plan.action == "search", plan
        assert plan.source == expected_source, plan

        result = query_with_permissions(
            collection,
            [1.0, 0.0],
            tenant_id="a",
            user_id="u1",
            source=plan.source,
            top_k=3,
        )

        actual_ids = set(result["ids"][0])
        print(question, "→", plan.source, "→", sorted(actual_ids))
        assert actual_ids == expected_ids, (question, actual_ids)

    print("四组文件范围检查通过。")
finally:
    close_all()