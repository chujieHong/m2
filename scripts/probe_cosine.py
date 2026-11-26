from pathlib import Path
from fastembed import TextEmbedding
import numpy as np


def cosine_similarity(a: list[float], b: list[float]) -> float:
    denominator = float(
        np.linalg.norm(a) * np.linalg.norm(b)
    )

    if denominator == 0:
        raise ValueError("零向量无法计算余弦相似度")

    return float(np.dot(a, b) / denominator)
    
ROOT = Path(__file__).resolve().parents[1]

model = TextEmbedding(
    model_name="BAAI/bge-small-zh-v1.5",
    cache_dir=str(ROOT / "data" / "models"),
    threads=2,
    local_files_only=True,
)

sentences = [
    "匿名用户不能写入这个文件。",
    "匿名用户没有权限修改这个文件。",
    "匿名用户可以写入这个文件。",
    "今天的天气很晴朗。",
]

vectors = list(model.embed(sentences))

scores = []

for sentence, vector in zip(sentences[1:], vectors[1:]):
    score = cosine_similarity(
        vectors[0].tolist(),
        vector.tolist(),
    )
    scores.append((score, sentence))
    print(f"相似度 {score:.4f}：{sentence}")

scores.sort(reverse=True)

print("\n按相似度从高到低排列：")
for score, sentence in scores:
    print(f"{score:.4f}：{sentence}")
    
text = "匿名用户可以写入这个文件吗？"

query_vector = list(model.query_embed(text))[0]
passage_vector = list(model.passage_embed([text]))[0]

print(
    "\n同一文本的两种向量是否近似相等：",
    np.allclose(query_vector, passage_vector),
)

document_a = [1.0, 0.0]
query_a = [1.0, 0.0]

document_b = [0.0, 1.0]
query_b = [0.0, 1.0]

print("\nA 问题与 A 文档：", cosine_similarity(query_a, document_a))
print("B 问题与 B 文档：", cosine_similarity(query_b, document_b))
print("B 问题与 A 文档：", cosine_similarity(query_b, document_a))

def normalize(vector: list[float]) -> np.ndarray:
    array = np.array(vector)
    length = np.linalg.norm(array)

    if length == 0:
        raise ValueError("零向量无法归一化")

    return array / length


query_unit = normalize([1.0, 0.0])

print("\n归一化后比较：")

for candidate in [[10.0, 0.0], [1.0, 1.0]]:
    candidate_unit = normalize(candidate)

    similarity = float(np.dot(query_unit, candidate_unit))
    distance = float(np.linalg.norm(query_unit - candidate_unit))

    print(
        f"原向量 {candidate}："
        f"相似度 {similarity:.4f}，"
        f"距离 {distance:.4f}"
    )
    
print("\nBGE 向量的长度：")

for sentence, vector in zip(sentences, vectors):
    length = float(np.linalg.norm(vector))
    print(f"{length:.8f}：{sentence}")