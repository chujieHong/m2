"""Day 7：用已有本地 BGE 模型满足 RAGAS 的向量接口。"""

import asyncio
from typing import Any

from fastembed import TextEmbedding
from ragas.embeddings.base import BaseRagasEmbedding


class BGERagasEmbedding(BaseRagasEmbedding):
    def __init__(self, model: TextEmbedding) -> None:
        super().__init__()
        self.model = model

    def embed_text(self, text: str, **kwargs: Any) -> list[float]:
        return self.embed_texts([text], **kwargs)[0]

    def embed_texts(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        if not texts or any(not text.strip() for text in texts):
            raise ValueError("评测问题必须是非空文本")
        # 两边均为问题，统一使用 query_embed，不采用 query/passage 混合编码。
        return [vector.tolist() for vector in self.model.query_embed(texts)]

    async def aembed_text(self, text: str, **kwargs: Any) -> list[float]:
        return await asyncio.to_thread(self.embed_text, text, **kwargs)

    async def aembed_texts(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        return await asyncio.to_thread(self.embed_texts, texts, **kwargs)
