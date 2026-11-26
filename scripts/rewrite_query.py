import json

from llm_toolkit.providers import ChatOptions
from llm_toolkit.providers.base import BaseProvider, extract_answer


def rewrite_query(
    provider: BaseProvider,
    history: list[dict[str, str]],
    question: str,
) -> str:
    if not history:
        return question

    messages = [
        {
            "role": "system",
            "content": (
                "将用户最后一个问题改写成可独立理解的检索问题。"
                "只根据前面的对话补全指代，保留原意。"
                "不回答问题，不添加对话中没有的事实。"
                "指代不明确时保留原问题，不猜测。"
                '输出 JSON 对象，且只包含 query 字段。'
                '格式示例：{"query": "产品 B 的发票什么时候开具？"}'
            ),
        },
    ]

    messages.extend(history)
    messages.append({"role": "user", "content": question})

    response = provider.call(
        messages,
        options=ChatOptions(
            temperature=0.0,
            max_tokens=128,
            response_format={"type": "json_object"},
        ),
    )

    if not response.choices:
        raise ValueError("查询改写没有返回候选结果")

    finish_reason = response.choices[0].finish_reason
    if finish_reason != "stop":
        raise ValueError(f"查询改写未正常完成：{finish_reason}")

    data = json.loads(extract_answer(response))

    if not isinstance(data, dict) or set(data) != {"query"}:
        raise ValueError("输出必须且只能包含 query 字段")

    query = data["query"]

    if not isinstance(query, str) or not query.strip():
        raise ValueError("query 必须是非空字符串")

    return query.strip()
