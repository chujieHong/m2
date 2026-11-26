from pathlib import Path
from time import perf_counter
import numpy as np
from fastembed import TextEmbedding

ROOT = Path(__file__).resolve().parents[1]

started = perf_counter()

model = TextEmbedding(
    model_name="Qwen/Qwen3-Embedding-0.6B-Q",
    cache_dir=str(ROOT / "data" / "models"),
    threads=2,
)

print(f"下载及加载耗时：{perf_counter() - started:.2f} 秒")

started = perf_counter()

vector = list(
    model.passage_embed(["Bucket ACL 的默认权限值是 private。"])
)[0]

print("向量维度：", len(vector))
print("前 5 个数字：", vector[:5])
print(f"向量化耗时：{perf_counter() - started:.2f} 秒")

question = "Bucket ACL 默认是什么权限？"

task = (
    "Given a question, retrieve passages from Chinese "
    "cloud-service documentation that answer the question."
)

query_text = f"Instruct: {task}\nQuery:{question}"

query_vector = list(model.query_embed(query_text))[0]

print("\n实际送入模型的查询文本：")
print(query_text)
print("查询向量维度：", len(query_vector))

documents = [
    "Bucket ACL 的默认权限值是 private。",
    "Object ACL 的默认值是 default，表示继承 Bucket 的 ACL。",
    "UploadPart 对应的权限 Action 是 oss:PutObject。",
]

document_vectors = list(
    model.passage_embed(documents, batch_size=1)
)


def rank_documents(
    question_vector: np.ndarray,
) -> list[tuple[float, str]]:
    scores = []

    for document, document_vector in zip(documents, document_vectors):
        score = float(
            np.dot(question_vector, document_vector)
            / (
                np.linalg.norm(question_vector)
                * np.linalg.norm(document_vector)
            )
        )
        scores.append((score, document))

    return sorted(scores, reverse=True)


cases = [
    ("Bucket 的默认 ACL 是什么？", 0),
    ("Object 的默认 ACL 是什么？", 1),
    ("UploadPart 用哪个权限 Action？", 2),
    ("刚建好的存储空间采用哪种 ACL 权限？", 0),
    ("文件 ACL 使用默认值时会怎样确定权限？", 1),
    ("上传分片需要检查什么权限动作？", 2),
]
hit_counts = {
    "带任务指令": 0,
    "不带任务指令": 0,
}
for question, expected_index in cases:
    print(f"\n问题：{question}")
    
    for label, text in [
        ("带任务指令", f"Instruct: {task}\nQuery:{question}"),
        ("不带任务指令", question),
    ]:
        current_vector = list(model.query_embed(text))[0]

        top_score, top_document = rank_documents(current_vector)[0]
        expected_document = documents[expected_index]
        hit = top_document == expected_document
        if hit:
            hit_counts[label] += 1
        print(f"{label}：命中正确依据={hit}")
        print(f"第一名 {top_score:.4f}：{top_document}")
        
print("\nTop-1 命中汇总：")

for label, count in hit_counts.items():
    rate = count / len(cases)
    print(f"{label}：{count}/{len(cases)} = {rate:.1%}")