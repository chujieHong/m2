from pathlib import Path
from kb.bm25 import BM25
from kb.ingestion import load_document
from dotenv import load_dotenv
from llm_toolkit.providers import close_all, get_provider
import numpy as np

from kb.embeddings import LocalEmbedding
from kb.fusion import reciprocal_rank_fusion
from rewrite_query import rewrite_query


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

cases = [
    {
        "name": "历史明确，可以补全",
        "history": [
            {
                "role": "user",
                "content": "退款有什么使用时长限制？",
            },
            {
                "role": "assistant",
                "content": "累计使用超过2小时的订单不支持退款。",
            },
        ],
        "question": "那超过了呢？",
    },
    {
        "name": "没有历史，保留原问题",
        "history": [],
        "question": "退款审核通过后多久到账？",
    },
    {
        "name": "指代不明确，不应猜测",
        "history": [
            {
                "role": "user",
                "content": "我想了解退款和发票。",
            },
            {
                "role": "assistant",
                "content": "你想了解哪一项？",
            },
        ],
        "question": "那个要多久？",
    },
]

sections = load_document(ROOT / "examples" / "refund_policy.md")
retriever = BM25([section.text for section in sections])
embedding = LocalEmbedding(
    model_name="BAAI/bge-small-zh-v1.5",
    cache_dir=ROOT / "data" / "models",
)

document_matrix = np.asarray(
    embedding.embed_documents([section.text for section in sections]),
    dtype=np.float32,
)
document_norms = np.linalg.norm(document_matrix, axis=1)

if np.any(document_norms == 0):
    raise ValueError("文档中存在零向量")

def retrieve_heading(question: str) -> str | None:
    bm25_scores = retriever.score(question)
    bm25_ranked = sorted(
        enumerate(bm25_scores),
        key=lambda item: item[1],
        reverse=True,
    )
    bm25_ids = [
        str(index)
        for index, score in bm25_ranked
        if score > 0
    ][:3]

    query_vector = np.asarray(
        embedding.embed_query(question),
        dtype=np.float32,
    )
    query_norm = np.linalg.norm(query_vector)

    if query_norm == 0:
        raise ValueError("问题向量不能为零")

    similarities = (
        document_matrix @ query_vector
        / (document_norms * query_norm)
    )
    vector_ranked = sorted(
        enumerate(similarities),
        key=lambda item: item[1],
        reverse=True,
    )
    vector_ids = [
        str(index)
        for index, _ in vector_ranked[:3]
    ]

    fused = reciprocal_rank_fusion(
        [bm25_ids, vector_ids],
        top_k=1,
    )

    if not fused:
        return None

    index = int(fused[0][0])
    heading_path = sections[index].heading_path
    return heading_path[-1] if heading_path else None


expected_headings = ["退款", "退款", None]
original_hits = 0
rewritten_hits = 0
scored_count = 0

try:
    provider = get_provider("deepseek")

    for case, expected in zip(cases, expected_headings):
        question = case["question"]
        rewritten = rewrite_query(
            provider,
            history=case["history"],
            question=question,
        )

        print(f"\n===== {case['name']} =====")
        print("原问题：", question)
        print("改写后：", rewritten)

        if not case["history"]:
            assert rewritten == question

        if expected is None:
            print("指代不明确，没有唯一预期依据，不纳入命中率。")
            print("是否原样保留：", rewritten == question)
            print("需要核对是否擅自选择了退款或发票。")
            continue

        original_result = retrieve_heading(question)
        rewritten_result = retrieve_heading(rewritten)

        original_hits += int(original_result == expected)
        rewritten_hits += int(rewritten_result == expected)
        scored_count += 1

        print("预期章节：", expected)
        print("原问题命中：", original_result)
        print("改写后命中：", rewritten_result)

finally:
    close_all()

print(f"\n原问题首位命中：{original_hits}/{scored_count}")
print(f"改写后首位命中：{rewritten_hits}/{scored_count}")