"""复核 3：deepseek-flash 是不是默认开了 thinking 模式？

起因：
    同样一句 "回答一个字：好"，两个模型名的 token 消耗差异巨大：
        deepseek-chat  -> in=8   out=1
        deepseek-flash -> in=34  out=34     <-- 多出来的 33 个 token 去哪了？

    回复内容都是 '好'（1 个字符），所以那 33 个 token 不可能在 content 里。
    怀疑：默认 thinking 模式下，模型先"想"了一段，放在某个单独字段里。

为什么这事对 M2 很重要：
    如果默认就 thinking，那么
      - 成本会翻好几倍（M2 有大量调用：查询改写、判分、Contextual Retrieval）
      - 输出可能带推理内容，污染解析（M1 已经为 MiniMax 写过 strip_reasoning）
      - 延迟变高
    必须搞清楚默认行为，以及怎么关掉。
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def dump(label: str, **kwargs: object) -> None:
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
    )
    print("=" * 70)
    print(f"{label}     kwargs={kwargs}")
    print("=" * 70)
    try:
        resp = client.chat.completions.create(
            model="deepseek-flash",
            messages=[{"role": "user", "content": "回答一个字：好"}],
            max_completion_tokens=64,
            **kwargs,  # type: ignore[arg-type]
        )
        msg = resp.choices[0].message
        print(f"  resp.model       : {resp.model}")
        print(f"  content          : {msg.content!r}")
        # 关键：看看 message 上有没有额外的字段
        extra = {
            k: v
            for k, v in msg.model_dump().items()
            if k not in ("content", "role") and v is not None
        }
        print(f"  message 其它字段  : {extra}")
        if resp.usage:
            print(f"  usage            : {resp.usage.model_dump()}")
    except Exception as exc:
        print(f"  [FAIL] {type(exc).__name__}: {str(exc)[:300]}")
    print()


if __name__ == "__main__":
    dump("A. 什么都不传（看默认行为）")
    dump("B. 尝试关掉 thinking（extra_body）", extra_body={"thinking": {"type": "disabled"}})
