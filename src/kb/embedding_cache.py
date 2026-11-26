import hashlib
import json
import sqlite3
from pathlib import Path


def make_embedding_key(
    text: str,
    *,
    model_name: str,
    kind: str,
    query_instruction: str | None = None,
) -> str:
    payload = {
        "version": 1,
        "text": text,
        "model_name": model_name,
        "kind": kind,
        "query_instruction": query_instruction,
    }

    content = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class EmbeddingCache:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(self.db_path)
        try:
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS embeddings (
                        cache_key TEXT PRIMARY KEY,
                        vector_json TEXT NOT NULL
                    )
                """)
        finally:
            connection.close()

    def get(self, key: str) -> list[float] | None:
        connection = sqlite3.connect(self.db_path)
        try:
            row = connection.execute(
                """
                SELECT vector_json
                FROM embeddings
                WHERE cache_key = ?
                """,
                (key,),
            ).fetchone()
        finally:
            connection.close()

        if row is None:
            return None

        return json.loads(row[0])

    def put(self, key: str, vector: list[float]) -> None:
        content = json.dumps(vector, allow_nan=False)

        connection = sqlite3.connect(self.db_path)
        try:
            with connection:
                connection.execute(
                    """
                    INSERT INTO embeddings (cache_key, vector_json)
                    VALUES (?, ?)
                    ON CONFLICT(cache_key)
                    DO UPDATE SET vector_json = excluded.vector_json
                    """,
                    (key, content),
                )
        finally:
            connection.close()
