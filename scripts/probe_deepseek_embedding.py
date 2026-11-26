"""Day 1 实证：DeepSeek 到底有没有 embedding 模型？

为什么不直接说"官方 issue 说过"：
    面试时你能说"我实测过"，而不是"我看过一篇文章"。
    M1 的教训 —— 验证方法必须和结论在同一层：
    要证明"某个 API 不存在"，就必须真的去调它。

实验设计上的一个关键点：
    光试探 deepseek-embedding 失败，不能说明问题 ——
    也可能是"我 URL 写错了"或"我没联网"。
    所以【加一个对照组】：用确实存在的 deepseek-chat 去调同一个端点。
    两个都失败 → 才能排除"是我自己搞错了"，指向"这个能力确实不存在"。
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def main() -> int:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("[X] 没找到 DEEPSEEK_API_KEY")
        print("    先复制 .env.example 成 .env，填上你的 DeepSeek key")
        return 1

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    # 对照组：deepseek-chat 是确实存在的【对话】模型。
    # 如果它在 embeddings 端点上也失败，说明失败原因不是"模型名写错了"，
    # 而是这个端点/这个模型类型确实不被支持。
    for model_name in ("deepseek-embedding", "deepseek-chat"):
        print("=" * 64)
        print(f"试探 model = {model_name!r}")
        print("=" * 64)
        try:
            resp = client.embeddings.create(model=model_name, input="测试文本")
            dim = len(resp.data[0].embedding)
            print(f"  [OK] 居然成功了！向量维度 = {dim}")
        except Exception as exc:
            print(f"  [FAIL] {type(exc).__name__}")
            print(f"  {str(exc)[:400]}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
