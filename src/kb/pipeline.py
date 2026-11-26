"""单题 RAG 流程，交互入口和批量实验共用。"""

from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from llm_toolkit.exceptions import LLMToolkitError
from llm_toolkit.providers import ChatOptions
from llm_toolkit.providers.base import BaseProvider, extract_answer

from kb.experiment_config import ExperimentConfig
from kb.generation import build_answer_messages
from kb.retrieval import VectorRetriever


def run_case(
    retriever: VectorRetriever,
    config: ExperimentConfig,
    question: str,
    assumptions: str = "",
    provider: BaseProvider | None = None,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    rag_started = perf_counter()
    results = retriever.retrieve(question, config.top_k)
    retrieval_seconds = perf_counter() - rag_started
    documents = results["documents"]
    if documents is None:
        raise ValueError("检索没有返回 documents")

    record: dict[str, Any] = {
        "question": question,
        "assumptions": assumptions,
        "results": results,
        "status": "retrieved",
        "rag_started_at_utc": started_at,
        "retrieval_seconds": retrieval_seconds,
        "generation_seconds": None,
        "rag_seconds": None,
    }
    if provider is None:
        return record

    messages = build_answer_messages(question, documents[0], assumptions)
    record["messages"] = messages
    record["generation_started_at_utc"] = datetime.now(timezone.utc).isoformat()
    generation_started = perf_counter()
    try:
        response = provider.call(
            messages,
            options=ChatOptions(
                model=config.chat_model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            ),
        )
        record["response_model"] = response.model
        record["usage"] = response.usage.model_dump() if response.usage else None
        record["finish_reason"] = response.choices[0].finish_reason if response.choices else None
        record["answer"] = extract_answer(response) if response.choices else None
        record["status"] = (
            "ok" if record["finish_reason"] == "stop" and record["answer"]
            and record["answer"].strip() else "invalid_response"
        )
    except LLMToolkitError as exc:
        record["status"] = "error"
        record["error"] = str(exc)
    finally:
        record["generation_seconds"] = perf_counter() - generation_started
    record["rag_seconds"] = perf_counter() - rag_started
    return record


TIMING_SCOPE = (
    "retrieval_seconds=问题向量化+Chroma查询；generation_seconds=模型调用+回答解析；"
    "rag_seconds=检索+提示词拼接+生成+响应处理。"
    "不含模型/数据库初始化、provider对象创建、结果文件写入、评分。"
    "包含首次查询及首次API调用的连接开销；批量运行复用模型和provider，"
    "不同阶段的p50不能直接相加得到完整链路p50。"
)
