import argparse
import json
from pathlib import Path
from kb.permissions import query_with_permissions
import chromadb

from kb.embeddings import LocalEmbedding


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--document",
        type=Path,
        default=ROOT / "examples" / "refund_policy.md",
    )
    parser.add_argument(
        "--question",
        default="退款审核通过后，多久能到账？",
    )
    args = parser.parse_args()

    # 教学用的固定身份；正式服务应从已验证的登录信息取得。
    current_user = {
        "tenant_id": "tenant-a",
        "user_id": "user-001",
    }

    document_key = json.dumps(
        [current_user["tenant_id"], str(args.document.resolve())],
        ensure_ascii=False,
    )
    state_path = ROOT / "data" / "day18" / "index_state.json"

    if not state_path.exists():
        raise ValueError("没有索引记录，请先运行增量建库脚本")

    states = json.loads(state_path.read_text(encoding="utf-8"))
    current = states.get(document_key)

    if current is None:
        raise ValueError("这个文档尚未建立索引")

    client = chromadb.PersistentClient(
        path=str(ROOT / "data" / "chroma")
    )
    collection = client.get_collection(
        current["collection"],
        embedding_function=None,
    )

    metadata = collection.metadata or {}

    if (
        metadata.get("status") != "ready"
        or metadata.get("fingerprint") != current["fingerprint"]
    ):
        raise ValueError("当前版本记录与集合状态不一致")

    if collection.count() != current["chunk_count"]:
        raise ValueError("集合片段数量与记录不一致")

    if collection.count() == 0:
        raise ValueError("当前集合为空")

    embedding = LocalEmbedding(
        model_name=metadata["embedding_model"],
        cache_dir=ROOT / "data" / "models",
    )
    query_vector = embedding.embed_query(args.question)

    result = query_with_permissions(
        collection,
        query_vector,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        top_k=min(3, collection.count()),
    )

    if not result["ids"][0]:
        print("没有检索到当前身份可访问的资料。")
        return
    print("当前集合：", collection.name)
    print("问题：", args.question)

    for chunk_id, document, source, distance in zip(
        result["ids"][0],
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
    ):
        print(f"\n片段：{chunk_id}，余弦距离：{distance:.4f}")
        print(document)
        print("来源：", source)


if __name__ == "__main__":
    main()