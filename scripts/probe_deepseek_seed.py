"""追问：为什么 temperature=0.0 时，长回答还是会变？

在 what_is_temperature.py 里发现：
  A 短答案（1~2 个 token）：temp=0 时 6 次全一样
  B 长答案（一句话）：     temp=0 时 3 次全不一样   ← 意外

假设：长答案 = 更多次抽样 = 更容易在某一处"翻车"。

顺便测一件事：DeepSeek 支不支持 seed 参数？固定 seed 能不能锁住结果？
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import BadRequestError, OpenAI

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

OPEN_PROMPT = "用一句话形容秋天。只写这一句话，不要引号。"

lines: list[str] = []


def say(s: str = "") -> None:
    lines.append(s)


def run(label: str, n: int, **kw: object) -> None:
    say()
    say(f"--- {label} " + "-" * 20)
    outs: list[str] = []
    for i in range(n):
        try:
            r = client.chat.completions.create(
                model="deepseek-flash",
                messages=[{"role": "user", "content": OPEN_PROMPT}],
                max_completion_tokens=60,
                extra_body={"thinking": {"type": "disabled"}},
                **kw,  # type: ignore[arg-type]
            )
        except BadRequestError as exc:
            say(f"    [API 拒绝] {exc}")
            return
        outs.append((r.choices[0].message.content or "").strip())

    uniq = sorted(set(outs))
    for i, o in enumerate(outs, 1):
        say(f"    第 {i} 次  ->  {o}")
    say(f"    >>> 不同答案 {len(uniq)} 种 / 共 {n} 次")


say("=" * 62)
say(f'提示词: "{OPEN_PROMPT}"')
say("=" * 62)

# n 必须够大：n=3 时"2 种/3 次"和"3 种/3 次"的差别可能纯属巧合
N = 8
run("temperature=0.0，不传 seed", N, temperature=0.0)
run("temperature=0.0，seed=42", N, temperature=0.0, seed=42)
run("temperature=1.5，不传 seed", N, temperature=1.5)
run("temperature=1.5，seed=42", N, temperature=1.5, seed=42)

say()
say("=" * 62)

out = HERE / "out_seed.txt"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"written: {out}")
