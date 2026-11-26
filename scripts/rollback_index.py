import argparse
import json
from pathlib import Path

import chromadb


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--document",
        type=Path,
        default=ROOT / "examples" / "refund_policy.md",
    )
    args = parser.parse_args()

    document_key = str(args.document.resolve())
    state_path = ROOT / "data" / "day17" / "index_state.json"
    states = json.loads(state_path.read_text(encoding="utf-8"))

    current = states.get(document_key)
    if not current or not current.get("previous_collection"):
        raise ValueError("没有可回退的上一版本")

    client = chromadb.PersistentClient(
        path=str(ROOT / "data" / "chroma")
    )
    previous = client.get_collection(
        current["previous_collection"],
        embedding_function=None,
    )

    metadata = previous.metadata or {}
    if (
        metadata.get("status") != "ready"
        or not metadata.get("fingerprint")
        or not metadata.get("embedding_model")
    ):
        raise ValueError("旧集合没有完整的就绪标记")

    ids = set(previous.get(include=[])["ids"])
    if not ids or ids != {
        f"chunk-{index}" for index in range(len(ids))
    }:
        raise ValueError("旧集合的片段编号检查失败")

    states[document_key] = {
        "fingerprint": metadata["fingerprint"],
        "collection": previous.name,
        "chunk_count": len(ids),
        "previous_collection": current["collection"],
    }

    temporary_path = state_path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(states, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(state_path)

    print("已切换到：", previous.name)
    print("向量模型：", metadata["embedding_model"])
    print("切换前的集合仍然保留：", current["collection"])


if __name__ == "__main__":
    main()