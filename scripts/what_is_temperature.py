"""实验：temperature 到底控制什么？

做法：同一个提示词，在不同 temperature 下重复问多次，看答案变不变。

用两组提示词，因为它们的答案空间大小不同：
  A 答案空间小（1~100）：可以数"出现几种答案"
  B 答案空间大（随便形容）：可以肉眼看"措辞变不变"

输出写到 out_temperature.txt（UTF-8），避免控制台 GBK 乱码。
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

# (标题, 提示词, 每个温度问几次, 温度列表)
CASES = [
    (
        "A 答案空间小 —— 可以数出几种答案",
        "从 1 到 100 里随便挑一个数字。只回答数字本身，不要标点，不要解释。",
        6,
        [0.0, 1.5],
    ),
    (
        "B 答案空间大 —— 肉眼看措辞变不变",
        "用一句话形容秋天。只写这一句话，不要引号。",
        3,
        [0.0, 1.5],
    ),
]

lines: list[str] = []


def say(s: str = "") -> None:
    lines.append(s)


for title, prompt, n, temps in CASES:
    say("=" * 62)
    say(title)
    say(f'提示词: "{prompt}"')
    say(f"每个温度各问 {n} 次")
    say("=" * 62)

    for t in temps:
        outs: list[str] = []
        for _ in range(n):
            r = client.chat.completions.create(
                model="deepseek-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=t,
                max_completion_tokens=60,
                extra_body={"thinking": {"type": "disabled"}},
            )
            outs.append((r.choices[0].message.content or "").strip())

        uniq = sorted(set(outs))
        say()
        say(f"--- temperature = {t} " + "-" * 34)
        for i, o in enumerate(outs, 1):
            say(f"    第 {i} 次  ->  {o}")
        say(f"    >>> 不同答案 {len(uniq)} 种 / 共 {n} 次")

    say()

out = HERE / "out_temperature.txt"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"written: {out}")
