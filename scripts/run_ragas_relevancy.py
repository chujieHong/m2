"""比较一条真实回答与两条教学反例的 RAGAS 回答相关性。"""

import asyncio
import hashlib
import json
import math
import os
from importlib.metadata import version
from pathlib import Path

os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")

import numpy as np
from dotenv import load_dotenv
from fastembed import TextEmbedding
from llm_toolkit.providers import close_all, get_provider
from ragas.metrics.collections import AnswerRelevancy

from kb.ragas_adapter import M1RagasLLM
from kb.ragas_embeddings import BGERagasEmbedding


ROOT = Path(__file__).resolve().parents[1]


async def main() -> None:
    source = ROOT / "data/eval_results/day7_answers_100_top3.json"
    source_bytes = source.read_bytes()
    records = json.loads(source_bytes.decode("utf-8"))
    original = next(case for case in records["cases"] if case["id"] == "single_hop_001")
    samples = [
        {"id": "original", "answer": original["answer"], "origin": "saved_real_response"},
        {"id": "wrong_fact", "answer": "Bucket ACL 的默认权限值是 public-read。", "origin": "assistant_written_counterexample"},
        {"id": "wrong_topic", "answer": "UploadPart 对应的权限 Action 是 oss:PutObject。", "origin": "assistant_written_counterexample"},
    ]
    model = TextEmbedding(
        model_name="BAAI/bge-small-zh-v1.5", cache_dir=str(ROOT / "data/models"),
        threads=2, local_files_only=True,
    )
    embeddings = BGERagasEmbedding(model)
    load_dotenv(ROOT / ".env")
    output = {
        "source_answers_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "ragas_version": version("ragas"), "embedding_model": "BAAI/bge-small-zh-v1.5",
        "embedding_encoding": "query_embed for both original and generated questions",
        "strictness": 3, "question": original["question"], "cases": [],
    }
    target = ROOT / "data/eval_results/ragas_relevancy_comparison.json"
    try:
        provider = get_provider("deepseek")
        output["judge_model"] = provider.model
        for sample in samples:
            adapter = M1RagasLLM(provider)
            metric = AnswerRelevancy(llm=adapter, embeddings=embeddings, strictness=3)
            result = dict(sample, status="pending", answer_relevancy=None)
            print("Scoring:", sample["id"], flush=True)
            try:
                score = await metric.ascore(user_input=original["question"], response=sample["answer"])
                if not math.isfinite(score.value):
                    result.update(status="unscorable", reason="RAGAS 返回非有限分数")
                else:
                    result.update(status="ok", answer_relevancy=score.value)
                generated = [trace["output"] for trace in adapter.trace]
                questions = [record["question"] for record in generated if record["question"]]
                result["generated_questions"] = generated
                result["unique_generated_question_count"] = len(set(questions))
                if questions:
                    # 本地核对实际公式，不能将此相似度称为正确概率。
                    vectors = np.asarray(embeddings.embed_texts([original["question"], *questions]))
                    cosine = (vectors[1:] @ vectors[0]) / (
                        np.linalg.norm(vectors[1:], axis=1) * np.linalg.norm(vectors[0])
                    )
                    result["cosine_similarities"] = cosine.tolist()
                    expected = float(cosine.mean()) * int(not all(record["noncommittal"] for record in generated if record["question"]))
                    result["formula_verified"] = math.isclose(score.value, expected, abs_tol=1e-6)
                    if not result["formula_verified"]:
                        raise ValueError("本地公式核对与RAGAS结果不同")
            except Exception as exc:
                result.update(status="error", error_type=type(exc).__name__, error=str(exc))
            result["adapter_trace"] = adapter.trace
            output["cases"].append(result)
            target.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            print("Status:", result["status"], "Score:", result["answer_relevancy"], flush=True)
    finally:
        close_all()
    print(target)


if __name__ == "__main__":
    asyncio.run(main())
