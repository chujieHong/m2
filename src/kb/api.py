from collections import Counter
from contextlib import asynccontextmanager
import json
from pathlib import Path
from threading import Lock
from typing import Any, AsyncIterator, Iterator, Literal
from uuid import uuid4

import chromadb
import numpy as np
from chromadb.api.models.Collection import Collection
from chromadb.errors import NotFoundError
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from llm_toolkit.exceptions import LLMToolkitError
from llm_toolkit.providers import ChatOptions, close_all, get_provider
from llm_toolkit.providers.base import extract_answer
from openai.types.chat import ChatCompletion
from pydantic import BaseModel, ConfigDict, Field

from kb.chunking import split_text
from kb.embeddings import LocalEmbedding
from kb.evidence import check_evidence
from kb.generation import build_answer_messages
from kb.grounding import check_answer_support
from kb.ingestion import load_document
from kb.index_fingerprint import make_index_fingerprint
from kb.observability import measure_stage, write_event, write_model_usage
from kb.permissions import build_permission_filter, query_with_permissions


ROOT = Path(__file__).resolve().parents[2]

CURRENT_USER = {
    "tenant_id": "tenant-a",
    "user_id": "user-001",
}

INDEX_CHUNK_SIZE = 400
INDEX_PARSER_VERSION = "api-upload-v1"
INDEX_LOCK = Lock()


class SearchRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        strict=True,
    )

    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=3, ge=1, le=10)
    document_id: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{32}$",
    )


class SearchHit(BaseModel):
    chunk_id: str
    text: str
    source: str
    distance: float


class SearchResponse(BaseModel):
    question: str
    hits: list[SearchHit]


class AskResponse(BaseModel):
    status: Literal["answered", "refused", "blocked"]
    answer: str
    hits: list[SearchHit]


class SourceSummary(BaseModel):
    source: str
    chunk_count: int


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    size_bytes: int


class IndexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    document_id: str = Field(pattern=r"^[0-9a-f]{32}$")


class IndexResponse(BaseModel):
    document_id: str
    status: Literal["indexed", "unchanged"]
    chunk_count: int


def resolve_uploaded_file(document_id: str) -> tuple[Path, str]:
    upload_dir = (
        ROOT / "data" / "uploads"
        / CURRENT_USER["tenant_id"]
        / CURRENT_USER["user_id"]
        / document_id
    )
    metadata_path = upload_dir / "metadata.json"

    if not metadata_path.is_file():
        raise HTTPException(status_code=404, detail="找不到该上传文件。")

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail="上传记录读取失败。",
        ) from exc

    if not isinstance(metadata, dict):
        raise HTTPException(status_code=500, detail="上传记录格式异常。")

    stored_name = metadata.get("stored_name")
    filename = metadata.get("filename")

    if (
        metadata.get("document_id") != document_id
        or not isinstance(stored_name, str)
        or stored_name not in {"document.md", "document.pdf", "document.docx"}
        or not isinstance(filename, str)
        or not filename.strip()
    ):
        raise HTTPException(status_code=500, detail="上传记录内容异常。")

    document_path = upload_dir / stored_name
    if not document_path.is_file():
        raise HTTPException(status_code=404, detail="上传文件已丢失。")

    return document_path, filename


def prepare_index_data(
    document_path: Path,
    filename: str,
    document_id: str,
) -> tuple[list[str], list[dict[str, Any]]]:
    chunks: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for section in load_document(document_path):
        heading = " > ".join(section.heading_path)

        for body in split_text(section.text, INDEX_CHUNK_SIZE):
            chunks.append(f"{heading}\n{body}".strip())

            metadata: dict[str, Any] = {
                "source": filename,
                "document_id": document_id,
                "heading_path": heading,
                "tenant_id": CURRENT_USER["tenant_id"],
                "owner_id": CURRENT_USER["user_id"],
                "visibility": "private",
            }

            if section.page is not None:
                metadata["page"] = section.page

            metadatas.append(metadata)

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="文件中没有可入库的正文。",
        )

    return chunks, metadatas


def create_uploaded_collection(
    request: Request,
    chunks: list[str],
    metadatas: list[dict[str, Any]],
    fingerprint: str,
) -> Collection:
    if not chunks or len(chunks) != len(metadatas):
        raise ValueError("片段与元数据数量异常")

    embedding = request.app.state.embedding
    client = request.app.state.chroma

    vectors = np.asarray(
        embedding.embed_documents(chunks),
        dtype=np.float32,
    )

    collection_metadata = {
        "fingerprint": fingerprint,
        "embedding_model": embedding.model_name,
        "status": "building",
    }

    collection = client.create_collection(
        name=f"upload_{uuid4().hex}",
        embedding_function=None,
        configuration={"hnsw": {"space": "cosine"}},
        metadata=collection_metadata,
    )

    ids = [f"chunk-{index}" for index in range(len(chunks))]

    collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=vectors,
        metadatas=metadatas,
    )

    actual_ids = set(collection.get(include=[])["ids"])
    if actual_ids != set(ids):
        raise ValueError("片段写入不完整，不启用该集合")

    collection.modify(
        metadata={
            **collection_metadata,
            "status": "ready",
        }
    )

    return collection


def get_search_collection(
    document_id: str | None,
    request: Request,
) -> Collection:
    if document_id is None:
        return request.app.state.collection

    document_path, _ = resolve_uploaded_file(document_id)
    state_path = document_path.parent / "index.json"

    if not state_path.is_file():
        raise HTTPException(
            status_code=409,
            detail="该文件尚未建库，请先调用建库接口。",
        )

    state = json.loads(state_path.read_text(encoding="utf-8"))

    try:
        collection = request.app.state.chroma.get_collection(
            state["collection"],
            embedding_function=None,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=409,
            detail="对应索引已丢失，请重新建库。",
        ) from exc

    metadata = collection.metadata or {}
    expected_ids = {
        f"chunk-{index}"
        for index in range(state["chunk_count"])
    }
    actual_ids = set(collection.get(include=[])["ids"])

    if (
        not expected_ids
        or actual_ids != expected_ids
        or metadata.get("status") != "ready"
        or metadata.get("fingerprint") != state["fingerprint"]
        or metadata.get("embedding_model")
        != request.app.state.embedding.model_name
    ):
        raise HTTPException(
            status_code=409,
            detail="索引状态异常或模型不匹配，请重新建库。",
        )

    return collection


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    load_dotenv(ROOT / ".env")

    try:
        document_path = ROOT / "examples" / "refund_policy.md"
        document_key = json.dumps(
            [CURRENT_USER["tenant_id"], str(document_path.resolve())],
            ensure_ascii=False,
        )

        state_path = ROOT / "data" / "day18" / "index_state.json"
        states = json.loads(state_path.read_text(encoding="utf-8"))
        current = states.get(document_key)

        if current is None:
            raise ValueError("退款文档尚未建立索引")

        app.state.chroma = chromadb.PersistentClient(
            path=str(ROOT / "data" / "chroma"),
        )
        collection = app.state.chroma.get_collection(
            current["collection"],
            embedding_function=None,
        )

        metadata = collection.metadata or {}

        if (
            metadata.get("status") != "ready"
            or metadata.get("fingerprint") != current["fingerprint"]
        ):
            raise ValueError("索引状态与集合记录不一致")

        chunk_count = collection.count()
        if chunk_count != current["chunk_count"] or chunk_count == 0:
            raise ValueError("索引片段数量异常")

        model_name = metadata.get("embedding_model")
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("集合缺少有效的向量模型名称")

        app.state.collection = collection
        app.state.embedding = LocalEmbedding(
            model_name=model_name,
            cache_dir=ROOT / "data" / "models",
            vector_cache_path=ROOT / "data" / "embedding_cache.sqlite3",
        )
        app.state.provider = get_provider("deepseek")

        print("当前集合：", collection.name)
        print("片段数量：", chunk_count)
        print("服务资源初始化完成")
        yield
    finally:
        close_all()
        app.state.collection = None
        app.state.chroma = None
        app.state.embedding = None
        app.state.provider = None
        print("服务资源清理完成")


app = FastAPI(
    title="企业知识库问答系统",
    lifespan=lifespan,
)

app.mount(
    "/ui",
    StaticFiles(
        directory=str(Path(__file__).resolve().parent / "static"),
        html=True,
    ),
    name="ui",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/upload", response_model=UploadResponse, status_code=201)
def upload(file: UploadFile) -> UploadResponse:
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()

    if suffix not in {".md", ".pdf", ".docx"}:
        raise HTTPException(
            status_code=415,
            detail="只支持 Markdown、PDF 和 DOCX 文件。",
        )

    max_bytes = 10 * 1024 * 1024
    content = file.file.read(max_bytes + 1)

    if not content:
        raise HTTPException(status_code=400, detail="文件不能为空。")

    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="文件不能超过10 MiB。")

    document_id = uuid4().hex
    upload_dir = (
        ROOT / "data" / "uploads"
        / CURRENT_USER["tenant_id"]
        / CURRENT_USER["user_id"]
        / document_id
    )
    upload_dir.mkdir(parents=True, exist_ok=False)

    stored_name = f"document{suffix}"
    (upload_dir / stored_name).write_bytes(content)

    metadata = {
        "document_id": document_id,
        "filename": filename,
        "stored_name": stored_name,
    }
    (upload_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return UploadResponse(
        document_id=document_id,
        filename=filename,
        size_bytes=len(content),
    )


@app.get("/api/sources", response_model=list[SourceSummary])
def list_sources(request: Request) -> list[SourceSummary]:
    collection = request.app.state.collection

    permission_filter = build_permission_filter(
        tenant_id=CURRENT_USER["tenant_id"],
        user_id=CURRENT_USER["user_id"],
    )

    result = collection.get(
        where=permission_filter,
        include=["metadatas"],
    )

    metadatas = result["metadatas"]
    if metadatas is None:
        raise ValueError("资料列表缺少元数据")

    counts = Counter(
        str((metadata or {}).get("source", "未知"))
        for metadata in metadatas
    )

    return [
        SourceSummary(source=source, chunk_count=count)
        for source, count in sorted(counts.items())
    ]


@app.post("/api/search", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    request: Request,
) -> SearchResponse:
    embedding = request.app.state.embedding
    collection = get_search_collection(
        payload.document_id,
        request,
    )

    limit = min(payload.top_k, collection.count())
    if limit == 0:
        return SearchResponse(question=payload.question, hits=[])

    query_vector = embedding.embed_query(payload.question)

    result = query_with_permissions(
        collection,
        query_vector,
        tenant_id=CURRENT_USER["tenant_id"],
        user_id=CURRENT_USER["user_id"],
        top_k=limit,
    )

    documents = result["documents"]
    metadatas = result["metadatas"]
    distances = result["distances"]

    if documents is None or metadatas is None or distances is None:
        raise ValueError("检索结果缺少必要字段")

    hits = [
        SearchHit(
            chunk_id=chunk_id,
            text=document,
            source=str((metadata or {}).get("source", "未知")),
            distance=distance,
        )
        for chunk_id, document, metadata, distance in zip(
            result["ids"][0],
            documents[0],
            metadatas[0],
            distances[0],
            strict=True,
        )
    ]

    return SearchResponse(question=payload.question, hits=hits)


@app.post("/api/ask", response_model=AskResponse)
def ask(
    payload: SearchRequest,
    request: Request,
) -> AskResponse:
    request_id = uuid4().hex
    log_path = ROOT / "data" / "logs" / "requests.jsonl"

    try:
        with measure_stage(log_path, request_id, "retrieval"):
            retrieval = search(payload, request)
        write_event(
            log_path,
            {
                "request_id": request_id,
                "event": "query_cache_snapshot",
                "stats": request.app.state.embedding.get_cache_stats(),
            },
        )
        write_event(
            log_path,
            {
                "request_id": request_id,
                "event": "retrieval_snapshot",
                "hits": [
                    {
                        "chunk_id": hit.chunk_id,
                        "source": hit.source,
                        "distance": hit.distance,
                    }
                    for hit in retrieval.hits
                ],
            },
        )
        documents = [hit.text for hit in retrieval.hits]
        provider = request.app.state.provider

        def record_evidence_usage(response: ChatCompletion) -> None:
            write_model_usage(log_path, request_id, "evidence", response)

        with measure_stage(log_path, request_id, "evidence"):
            decision = check_evidence(
                provider,
                question=payload.question,
                documents=documents,
                on_response=record_evidence_usage,
            )

        if not decision.answerable:
            missing = "；".join(decision.missing_information)
            return AskResponse(
                status="refused",
                answer=f"现有资料不足以完整回答。缺失或冲突：{missing}",
                hits=retrieval.hits,
            )

        with measure_stage(log_path, request_id, "generation"):
            response = provider.call(
                build_answer_messages(payload.question, documents),
                options=ChatOptions(
                    model="deepseek-flash",
                    temperature=0.0,
                    max_tokens=800,
                ),
            )
            write_model_usage(log_path, request_id, "generation", response)

            if not response.choices:
                raise ValueError("答案生成没有返回结果")

            if response.choices[0].finish_reason != "stop":
                raise ValueError("答案生成未正常完成")

            draft = extract_answer(response).strip()
            if not draft:
                raise ValueError("答案生成返回了空文本")

        def record_grounding_usage(response: ChatCompletion) -> None:
            write_model_usage(log_path, request_id, "grounding", response)

        with measure_stage(log_path, request_id, "grounding"):
            review = check_answer_support(
                provider,
                question=payload.question,
                documents=documents,
                answer=draft,
                on_response=record_grounding_usage,
            )

        if not review.supported:
            return AskResponse(
                status="blocked",
                answer="生成的回答未通过资料依据审核，暂不提供该答案。",
                hits=retrieval.hits,
            )

        return AskResponse(
            status="answered",
            answer=draft,
            hits=retrieval.hits,
        )

    except (LLMToolkitError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="问答处理失败，请稍后重试。",
        ) from exc


@app.post("/api/index", response_model=IndexResponse)
def index_document(
    payload: IndexRequest,
    request: Request,
) -> IndexResponse:
    with INDEX_LOCK:
        document_path, filename = resolve_uploaded_file(payload.document_id)
        content = document_path.read_bytes()
        embedding = request.app.state.embedding
        client = request.app.state.chroma

        access_policy = {
            "tenant_id": CURRENT_USER["tenant_id"],
            "owner_id": CURRENT_USER["user_id"],
            "visibility": "private",
        }

        fingerprint = make_index_fingerprint(
            content,
            embedding_model=embedding.model_name,
            chunk_size=INDEX_CHUNK_SIZE,
            parser_version=INDEX_PARSER_VERSION,
            access_policy=access_policy,
        )

        state_path = document_path.parent / "index.json"
        previous = (
            json.loads(state_path.read_text(encoding="utf-8"))
            if state_path.exists()
            else None
        )

        if previous and previous["fingerprint"] == fingerprint:
            try:
                existing = client.get_collection(
                    previous["collection"],
                    embedding_function=None,
                )
            except NotFoundError:
                pass
            else:
                metadata = existing.metadata or {}
                expected_ids = {
                    f"chunk-{i}"
                    for i in range(previous["chunk_count"])
                }
                actual_ids = set(existing.get(include=[])["ids"])

                if (
                    expected_ids
                    and actual_ids == expected_ids
                    and metadata.get("fingerprint") == fingerprint
                    and metadata.get("status") == "ready"
                    and metadata.get("embedding_model") == embedding.model_name
                ):
                    return IndexResponse(
                        document_id=payload.document_id,
                        status="unchanged",
                        chunk_count=previous["chunk_count"],
                    )

        chunks, metadatas = prepare_index_data(
            document_path,
            filename,
            payload.document_id,
        )

        collection = create_uploaded_collection(
            request,
            chunks,
            metadatas,
            fingerprint,
        )

        if document_path.read_bytes() != content:
            raise HTTPException(
                status_code=409,
                detail="文件在建库期间发生变化，请重新建库。",
            )

        state = {
            "fingerprint": fingerprint,
            "collection": collection.name,
            "chunk_count": len(chunks),
            "previous_collection": previous["collection"] if previous else None,
        }

        temporary_path = state_path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(state_path)

        return IndexResponse(
            document_id=payload.document_id,
            status="indexed",
            chunk_count=len(chunks),
        )


def format_sse(event: str, data: dict[str, Any]) -> str:
    content = json.dumps(
        data,
        ensure_ascii=False,
        allow_nan=False,
    )
    return f"event: {event}\ndata: {content}\n\n"


@app.post("/api/ask/stream")
def ask_stream(
    payload: SearchRequest,
    request: Request,
) -> StreamingResponse:
    def events() -> Iterator[str]:
        yield format_sse(
            "progress",
            {"stage": "processing", "message": "正在检索并处理问题"},
        )

        try:
            result = ask(payload, request)
        except HTTPException:
            yield format_sse(
                "error",
                {"message": "问答处理失败，请稍后重试。"},
            )
            return

        yield format_sse(
            "result",
            result.model_dump(mode="json"),
        )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
