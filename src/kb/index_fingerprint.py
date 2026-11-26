import hashlib
import json


def make_index_fingerprint(
    content: bytes,
    *,
    embedding_model: str,
    chunk_size: int,
    parser_version: str,
    access_policy: dict[str, str] | None = None,
) -> str:
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")

    description = {
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "embedding_model": embedding_model,
        "chunk_size": chunk_size,
        "parser_version": parser_version,
    }
    
    if access_policy is not None:
        description["access_policy"] = access_policy

    serialized = json.dumps(
        description,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()