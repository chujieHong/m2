import argparse
import json
from pathlib import Path
from uuid import uuid4

import chromadb
from chromadb.errors import NotFoundError

from kb.chunking import split_text
from kb.embeddings import LocalEmbedding
from kb.index_fingerprint import make_index_fingerprint
from kb.ingestion import load_document


ROOT = Path(__file__).resolve().parents[1]
MODEL_NAME = "BAAI/bge-small-zh-v1.5"
PARSER_VERSION = "pdf-v1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--document",
        type=Path,
        default=ROOT / "examples" / "refund_policy.md",
    )
    parser.add_argument("--chunk-size", type=int, default=400)
    parser.add_argument(
        "--embedding-model",
        default=MODEL_NAME,
        choices=[
            "BAAI/bge-small-zh-v1.5",
            "Qwen/Qwen3-Embedding-0.6B-Q",
        ],
    )
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--owner-id", required=True)
    parser.add_argument(
        "--visibility",
        choices=["tenant", "private"],
        default="private",
    )
    args = parser.parse_args()
    if not args.tenant_id.strip() or not args.owner_id.strip():
        raise ValueError("租户和所有者不能为空")

    access_policy = {
        "tenant_id": args.tenant_id,
        "owner_id": args.owner_id,
        "visibility": args.visibility,
    }
    model_name = args.embedding_model

    document_path = args.document.resolve()
    content = document_path.read_bytes()
    document_key = json.dumps(
        [args.tenant_id, str(document_path)],
        ensure_ascii=False,
    )

    fingerprint = make_index_fingerprint(
        content,
        embedding_model=model_name,
        chunk_size=args.chunk_size,
        parser_version=PARSER_VERSION,
        access_policy=access_policy,
    )

    state_path = ROOT / "data" / "day18" / "index_state.json"
    states = (
        json.loads(state_path.read_text(encoding="utf-8"))
        if state_path.exists()
        else {}
    )
    previous = states.get(document_key)

    client = chromadb.PersistentClient(
        path=str(ROOT / "data" / "chroma")
    )

    if previous and previous["fingerprint"] == fingerprint:
        try:
            collection = client.get_collection(
                previous["collection"],
                embedding_function=None,
            )
        except NotFoundError:
            print("记录存在，但对应集合已丢失，需要重建。")
        else:
            metadata = collection.metadata or {}
            expected_ids = {
                f"chunk-{index}"
                for index in range(previous["chunk_count"])
            }
            actual_ids = set(collection.get(include=[])["ids"])

            if (
                metadata.get("fingerprint") == fingerprint
                and metadata.get("status") == "ready"
                and actual_ids == expected_ids
                and expected_ids
            ):
                print("内容与配置未变，已有索引完整，跳过建库。")
                print("当前集合：", collection.name)
                return

            print("已有集合未通过完整性检查，需要重建。")

    chunks = []
    metadatas = []

    for section in load_document(document_path):
        heading = " > ".join(section.heading_path)

        for body in split_text(section.text, args.chunk_size):
            chunks.append(f"{heading}\n{body}".strip())

            metadata = {
                "source": section.source,
                "heading_path": heading,
                **access_policy,
            }
            if section.page is not None:
                metadata["page"] = section.page

            metadatas.append(metadata)

    if not chunks:
        raise ValueError("没有可入库的正文")

    if document_path.read_bytes() != content:
        raise ValueError("文档在处理期间发生变化，请重新运行")

    embedding = LocalEmbedding(
        model_name=model_name,
        cache_dir=ROOT / "data" / "models",
    )
    vectors = embedding.embed_documents(chunks)

    collection = client.create_collection(
        name=f"day17_{uuid4().hex}",
        embedding_function=None,
        configuration={"hnsw": {"space": "cosine"}},
        metadata={
            "fingerprint": fingerprint,
            "embedding_model": model_name,
            "status": "building",
        },
    )

    ids = [f"chunk-{index}" for index in range(len(chunks))]

    collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=vectors,
        metadatas=metadatas,
    )

    if set(collection.get(include=[])["ids"]) != set(ids):
        raise ValueError("写入后的片段编号不完整，不切换当前版本")

    if document_path.read_bytes() != content:
        raise ValueError("文档在建库期间发生变化，不切换当前版本")

    collection.modify(metadata={
        "fingerprint": fingerprint,
        "embedding_model": model_name,
        "status": "ready",
    })

    states[document_key] = {
        "fingerprint": fingerprint,
        "collection": collection.name,
        "chunk_count": len(chunks),
        "previous_collection": (
            previous["collection"] if previous else None
        ),
    }

    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = state_path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(states, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(state_path)

    print("当前版本已更新：", collection.name)
    print("片段数：", len(chunks))
    print("旧集合保留：", states[document_key]["previous_collection"])


if __name__ == "__main__":
    main()
