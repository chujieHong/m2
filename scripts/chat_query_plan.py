from pathlib import Path

from dotenv import load_dotenv
from llm_toolkit.providers import ChatOptions, close_all, get_provider
from llm_toolkit.providers.base import extract_answer

from kb.bm25 import BM25
from kb.generation import build_answer_messages
from kb.ingestion import load_document
from plan_query import plan_query


ROOT = Path(__file__).resolve().parents[1]


def main():
    load_dotenv(ROOT / ".env")

    sections = load_document(ROOT / "examples" / "refund_policy.md")
    retriever = BM25([section.text for section in sections])
    history = []

    try:
        provider = get_provider("deepseek")

        while True:
            question = input("\n你：").strip()

            if question.lower() in {"exit", "quit"}:
                break

            if not question:
                continue

            plan = plan_query(
                provider,
                history=history,
                question=question,
            )

            if plan.action == "clarify":
                assert plan.clarification is not None
                answer = plan.clarification
            else:
                assert plan.query is not None
                print("检索问题：", plan.query)

                scores = retriever.score(plan.query)
                ranked = sorted(
                    enumerate(scores),
                    key=lambda item: item[1],
                    reverse=True,
                )

                documents = [
                    sections[index].text
                    for index, score in ranked
                    if score > 0
                ][:2]

                if not documents:
                    answer = "没有找到匹配的资料，请补充问题。"
                else:
                    response = provider.call(
                        build_answer_messages(plan.query, documents),
                        options=ChatOptions(
                            model="deepseek-flash",
                            temperature=0.0,
                            max_tokens=500,
                        ),
                    )

                    if not response.choices:
                        raise ValueError("回答没有返回结果")

                    if response.choices[0].finish_reason != "stop":
                        raise ValueError("回答未正常生成完毕")

                    answer = extract_answer(response).strip()
                    if not answer:
                        raise ValueError("回答为空")

                    print("\n本轮资料：")
                    for number, document in enumerate(documents, start=1):
                        print(f"[{number}] {document}")

            print("\n助手：", answer)

            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})

            # 教学演示只保留最近6轮，每轮包含两条消息。
            history = history[-12:]

    except (EOFError, KeyboardInterrupt):
        print("\n结束对话。")
    finally:
        close_all()


if __name__ == "__main__":
    main()