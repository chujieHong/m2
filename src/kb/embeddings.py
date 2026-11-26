from pathlib import Path
from threading import Lock

from fastembed import TextEmbedding

from kb.embedding_cache import EmbeddingCache, make_embedding_key


class LocalEmbedding:
    def __init__(
        self,
        model_name: str,
        cache_dir: Path,
        query_instruction: str | None = None,
        *,
        vector_cache_path: Path | None = None,
    ) -> None:
        self.model_name = model_name
        self.query_instruction = query_instruction
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_stats_lock = Lock()
        self.cache = (
            EmbeddingCache(vector_cache_path)
            if vector_cache_path is not None
            else None
        )

        self.model = TextEmbedding(
            model_name=model_name,
            cache_dir=str(cache_dir),
            threads=2,
            local_files_only=True,
        )
        
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts or any(not text.strip() for text in texts):
            raise ValueError("文档列表不能为空，也不能包含空白文本")

        if self.cache is None:
            return [
                vector.tolist()
                for vector in self.model.passage_embed(texts, batch_size=1)
            ]

        results: list[list[float]] = []

        for text in texts:
            key = make_embedding_key(
                text,
                model_name=self.model_name,
                kind="document",
            )
            vector = self.cache.get(key)

            if vector is None:
                encoded = list(
                    self.model.passage_embed([text], batch_size=1)
                )[0]
                vector = encoded.tolist()
                self.cache.put(key, vector)

            results.append(vector)

        return results

    def embed_query(self, question: str) -> list[float]:
        if not question.strip():
            raise ValueError("问题不能为空")

        key = make_embedding_key(
            question,
            model_name=self.model_name,
            kind="query",
            query_instruction=self.query_instruction,
        )

        if self.cache is not None:
            cached = self.cache.get(key)

            with self.cache_stats_lock:
                if cached is not None:
                    self.cache_hits += 1
                else:
                    self.cache_misses += 1

            if cached is not None:
                return cached

        if self.query_instruction is not None:
            question = (
                f"Instruct: {self.query_instruction}\n"
                f"Query:{question}"
            )

        vector = list(self.model.query_embed(question))[0]
        result = vector.tolist()

        if self.cache is not None:
            self.cache.put(key, result)

        return result

    def get_cache_stats(self) -> dict[str, int | float]:
        with self.cache_stats_lock:
            hits = self.cache_hits
            misses = self.cache_misses

        total = hits + misses

        return {
            "hits": hits,
            "misses": misses,
            "total": total,
            "hit_rate": hits / total if total else 0.0,
        }
