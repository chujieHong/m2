from pathlib import Path
import numpy as np
from fastembed import TextEmbedding


ROOT = Path(__file__).resolve().parents[1]

model = TextEmbedding(
    model_name="BAAI/bge-small-zh-v1.5",
    cache_dir=str(ROOT / "data" / "models"),
    threads=2,
)

document = (ROOT / "examples" / "refund_policy.md").read_text(
    encoding="utf-8"
)

texts = []

for index, section in enumerate(document.split("\n## ")):
    chunk = section if index == 0 else "\n## " + section
    texts.append(chunk)

vectors = list(model.passage_embed(texts))
vector = vectors[0]

print("原文：", texts[0])
print("向量维度：", len(vector))
print("前 8 个数字：", vector[:8])

question = "买了以后还能把钱退回来吗？"
query_vector = list(model.query_embed(question))[0]

scores = []

for text, vector in zip(texts, vectors):
    score = float(
        np.dot(query_vector, vector)
        / (np.linalg.norm(query_vector) * np.linalg.norm(vector))
    )
    scores.append(score)
    print(f"相似度 {score:.4f}：{text}")

best_index = int(np.argmax(scores))
print("问题：", question)
print("最相近的片段：", texts[best_index])

from dotenv import load_dotenv
from llm_toolkit.providers import ChatOptions, close_all, get_provider
from llm_toolkit.providers.base import extract_answer, extract_usage


load_dotenv(ROOT / ".env")
provider = get_provider("deepseek")

context = texts[best_index]

messages = [
    {
        "role": "system",
        "content": (
            "只依据提供的资料回答问题。"
            "资料没有说明时，回答“资料未说明”，不要猜测。"
        ),
    },
    {
        "role": "user",
        "content": f"资料：\n{context}\n\n问题：{question}",
    },
]

try:
    response = provider.call(
        messages,
        options=ChatOptions(temperature=0.0, max_tokens=256),
    )

    print("回答：", extract_answer(response))
    print("输入 token：", extract_usage(response).prompt_tokens)
finally:
    close_all()