"""复核 2：M1 写死的 `deepseek-chat` 现在还管用吗？

背景：
    DeepSeek 官方 Models & Pricing 页（2026）里，当前只有两个模型：
        deepseek-flash      (DeepSeek-V4.1-Flash)
        deepseek-v4-pro     (DeepSeek-V4-Pro-0813)
    而 M1 的 DeepSeekProvider 里写的是：
        model = "deepseek-chat"          ← 不在官方列表里！

    如果这个旧名字已经失效，那 M1 就是【坏的】——
    这是个比"有没有 embedding"严重得多的问题，必须立刻查。

测什么：
    用同样的提示词，分别调 deepseek-chat 和 deepseek-flash，
    看旧名字还能不能用、能不能走到同一个模型。
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

CANDIDATES = [
    "deepseek-chat",        # M1 现在写死的名字
    "deepseek-flash",       # 官方当前的名字
]


def main() -> None:
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
    )

    for model_name in CANDIDATES:
        print("=" * 64)
        print(f"model = {model_name!r}")
        print("=" * 64)
        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "回答一个字：好"}],
                max_completion_tokens=16,
                temperature=0,
            )
            # 关键：服务端【实际】用了哪个模型？响应里会说
            print(f"  [OK] 真的通了")
            print(f"  响应里的 model 字段 : {resp.model}")
            print(f"  回复内容            : {resp.choices[0].message.content!r}")
            print(f"  finish_reason       : {resp.choices[0].finish_reason}")
            if resp.usage:
                print(f"  tokens              : in={resp.usage.prompt_tokens} out={resp.usage.completion_tokens}")
        except Exception as exc:
            print(f"  [FAIL] {type(exc).__name__}: {str(exc)[:300]}")
        print()


if __name__ == "__main__":
    main()
