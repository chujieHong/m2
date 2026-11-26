from pathlib import Path
from dotenv import load_dotenv
from llm_toolkit.providers import (
    ChatOptions,
    close_all,
    get_provider,
)
from llm_toolkit.providers.base import extract_answer, extract_usage

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

document = (ROOT / "examples" / "refund_policy.md").read_text(
    encoding="utf-8"
)

questions = [
    "云产品 A 购买后几天内可以申请退款？还有什么限制？",
    "云产品 A 支持七天无理由换货吗？",
]

provider = get_provider("deepseek")
options = ChatOptions(temperature = 0.0,max_tokens = 256)

try:
    for question in questions:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是文档问答助手，只依据提供的资料回答。"
                    "资料没有说明时，明确回答“资料未说明”，不要猜测。"
                ),
            },
            {
                "role": "user",
                "content": f"资料：\n{document}\n\n问题：{question}",
            },
        ]

        response = provider.call(messages, options=options)
        usage = extract_usage(response)

        print("\n问题：", question)
        print("回答：", extract_answer(response))
        print("输入 token：", usage.prompt_tokens)
        print("输出 token：", usage.completion_tokens)
finally:
    close_all()