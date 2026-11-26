"""Day 8：供实验入口复用的本地向量检索。"""

from pathlib import Path

import chromadb
from chromadb.api.types import QueryResult
from fastembed import TextEmbedding

from kb.experiment_config import ExperimentConfig


class VectorRetriever:
    def __init__(self, config: ExperimentConfig, root: Path) -> None:
        self.collection = chromadb.PersistentClient(
            path=str(root / "data" / "chroma")
        ).get_collection(config.collection, embedding_function=None)

        # 当前固定索引由这个模型构建，不能只更换查询模型而沿用旧索引。
        if config.embedding_model != "BAAI/bge-small-zh-v1.5":
            raise ValueError("当前检索入口只支持现有 BGE-small 索引")

        self.model = TextEmbedding(
            model_name=config.embedding_model,
            cache_dir=str(root / "data" / "models"),
            threads=2,
            local_files_only=True,
        )

    def retrieve(self, question: str, top_k: int) -> QueryResult:
        if not question.strip():
            raise ValueError("检索问题不能为空")

        if not 1 <= top_k <= self.collection.count():
            raise ValueError("top_k 必须在 1 到集合记录数之间")

        query_vector = list(
            self.model.query_embed(question)
        )[0]

        return self.collection.query(
            query_embeddings=[query_vector.tolist()],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
