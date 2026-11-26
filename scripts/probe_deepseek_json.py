import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
    timeout=30,
    max_retries=0,
)

response = client.chat.completions.create(
    model="deepseek-flash",
    messages=[
        {
            "role": "system",
            "content": (
                "提取用户文字中的产品和问题，输出 JSON 对象。"
                '格式示例：{"product": "产品A", "query": "退款期限"}'
            ),
        },
        {
            "role": "user",
            "content": "我想知道云产品A的退款期限。",
        },
    ],
    response_format={"type": "json_object"},
    max_completion_tokens=200,
    extra_body={"thinking": {"type": "disabled"}},
)

choice = response.choices[0]
text = choice.message.content

print("实际模型：", response.model)
print("结束原因：", choice.finish_reason)
print("原始内容：", repr(text))

if not text:
    raise ValueError("模型没有返回内容")

try:
    data = json.loads(text)
except json.JSONDecodeError as exc:
    raise ValueError("模型输出不是合法 JSON") from exc
if not isinstance(data, dict):
    raise ValueError("输出必须是 JSON 对象")

if set(data) != {"product", "query"}:
    raise ValueError("输出必须且只能包含 product 和 query")

for field in ("product", "query"):
    value = data[field]

    if not isinstance(value, str):
        raise ValueError(f"{field} 必须是字符串")

    if not value.strip():
        raise ValueError(f"{field} 不能为空")

print("字段检查通过")
print("解析结果：", data)