"""企业知识库问答系统（RAG）。

分层（见 PLAN.md 的「架构定位」）：
- providers/   EmbeddingProvider 抽象（DashScope / 本地 BGE）
- ingest/      文档解析 / 清洗 / 元数据
- chunking/    多策略切片（中文特化）
- store/       向量存储（Chroma）
- retrieve/    向量 / BM25 / RRF / Rerank
- generate/    提示词 / 引用 / 拒答
- eval/        LLM-as-Judge 评测
- api/         FastAPI（SSE）

注意：模型调用【不在这里】—— 那是上游 M1（chujie-llm-toolkit）的职责。
"""
