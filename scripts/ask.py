from pathlib import Path
from dotenv import load_dotenv
from llm_toolkit.providers import ChatOptions, close_all, get_provider
from llm_toolkit.providers.base import extract_answer
import chromadb
from fastembed import TextEmbedding
from llm_toolkit.exceptions import LLMToolkitError
from rewrite_query import rewrite_query

ROOT = Path(__file__).resolve().parents[1]

client = chromadb.PersistentClient(
    path=str(ROOT / "data" / "chroma")
)

collection = client.get_collection(
    name="refund_bge_small_zh_v1",
    embedding_function=None,
)

model = TextEmbedding(
    model_name="BAAI/bge-small-zh-v1.5",
    cache_dir=str(ROOT / "data" / "models"),
    threads=2,
)

load_dotenv(ROOT / ".env")
provider = get_provider("deepseek")

history = []

try:
    while True:
        question = input("\n请输入问题，输入 exit 退出：").strip()

        if question.lower() == "exit":
            break

        if not question:
            continue

        try:
            query = rewrite_query(provider, history, question)
        except (ValueError, LLMToolkitError) as exc:
            print("改写失败，使用原问题检索：", exc)
            query = question

        print("检索问题：", query)

        query_vector = list(model.query_embed(query))[0]

        results = collection.query(
            query_embeddings=[query_vector.tolist()],
            n_results=1,
            include=["documents", "metadatas", "distances"],
        )

        if not results["ids"][0]:
            print("没有检索结果。")
            continue

        context = results["documents"][0][0]
        metadata = results["metadatas"][0][0]

        messages = [
            {
                "role": "system",
                "content": (
                    "对话历史用于理解问题，事实依据只能来自本次资料。"
                    "根据资料回答时，在相关陈述后标注引用编号，例如 [1]。"
                    "引用编号只能使用本次资料中提供的编号，不能沿用历史编号。"
                    "资料没有说明时，只回答“资料未说明”，不要猜测或添加引用。"
                ),
            },
        ]
        messages.extend(history)
        messages.append({
            "role": "user",
            "content": (
                f"[1] 资料所属文档：{metadata['document_title']}\n"
                f"资料：\n{context}\n\n"
                f"问题：{question}"
            ),
        })

        try:
            response = provider.call(
                messages,
                options=ChatOptions(temperature=0.0, max_tokens=256),
            )
        except LLMToolkitError as exc:
            print("回答生成失败，本轮不加入历史：", exc)
            continue

        if not response.choices:
            print("模型没有返回候选回答，本轮不加入历史。")
            continue

        finish_reason = response.choices[0].finish_reason

        if finish_reason != "stop":
            print(
                f"回答未正常完成（{finish_reason}），"
                "本轮不加入历史。"
            )
            continue
        answer = extract_answer(response)

        if not answer.strip():
            print("模型返回空回答，本轮不加入历史。")
            continue

        print("回答：", answer)
        print(
            f"[1] 来源：{metadata['source']}，"
            f"片段 ID：{results['ids'][0][0]}"
        )

        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
finally:
    close_all()
