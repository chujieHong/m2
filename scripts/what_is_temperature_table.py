"""实验：把 temperature 作用的那张「概率表」真实打印出来。

思路：
  1. 给模型一个【没写完的句子】，让它必须续写下一个字
  2. 用 logprobs 拿到它心里排名前 8 的候选字 + 各自的真实概率
  3. 我自己用公式把这个概率表按不同 temperature 重新算一遍
     （这一步不需要再调 API，纯本地计算，完全可复现）

这样就能看到：temperature 不是"随机数开关"，
它是在【改造这张概率表】。

输出写到 out_logprobs.txt（UTF-8）。
"""
from __future__ import annotations

import math
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

PROMPT = "今天天气真"
TOP_N = 8
TEMPS = [0.0, 0.5, 1.0, 1.5, 2.0]

lines: list[str] = []


def say(s: str = "") -> None:
    lines.append(s)


r = client.chat.completions.create(
    model="deepseek-flash",
    messages=[{"role": "user", "content": PROMPT}],
    max_completion_tokens=1,
    temperature=1.0,          # 必须用 1.0，拿到的才是模型【原始】概率
    logprobs=True,
    top_logprobs=TOP_N,
    extra_body={"thinking": {"type": "disabled"}},
)

choice = r.choices[0]
lp = choice.logprobs
if lp is None or not lp.content:
    raise SystemExit("这次响应没有返回 logprobs")

cands = lp.content[0].top_logprobs
tokens = [c.token for c in cands]
logits = [c.logprob for c in cands]     # log 概率 = logit

say("=" * 66)
say(f'提示词: "{PROMPT}"  （故意不写完，模型必须续写下一个字）')
say(f"模型心里排名前 {TOP_N} 的候选字，以及原始概率：")
say("=" * 66)
say()
say(f"{'排名':<5}{'候选字':<10}{'原始概率':>10}   {'条状图'}")
for i, (tok, lg) in enumerate(zip(tokens, logits), 1):
    p = math.exp(lg)
    show = tok.replace("\n", "\\n").replace(" ", "␣")
    say(f"{i:<5}{show:<10}{p:>9.1%}   {'#' * round(p * 50)}")


def reshape(logits: list[float], t: float) -> list[float]:
    """把 logit 按温度 t 重新变成概率。"""
    if t <= 0.01:
        # 温度趋近 0 = 永远选概率最大的那个
        best = max(range(len(logits)), key=lambda i: logits[i])
        return [1.0 if i == best else 0.0 for i in range(len(logits))]
    scaled = [lg / t for lg in logits]
    m = max(scaled)
    exps = [math.exp(s - m) for s in scaled]
    total = sum(exps)
    return [e / total for e in exps]


say()
say("=" * 66)
say("同一张表，被不同 temperature 改造之后长什么样：")
say("=" * 66)

for t in TEMPS:
    ps = reshape(logits, t)
    label = "0.0（不加热）" if t == 0.0 else f"{t}"
    say()
    say(f"--- temperature = {label} " + "-" * 30)
    for tok, p in zip(tokens, ps):
        show = tok.replace("\n", "\\n").replace(" ", "␣")
        say(f"    {show:<10}{p:>8.1%}   {'#' * round(p * 50)}")

say()
say("=" * 66)
say("最后一步：抽签。")
say("模型每生成一个字，就是在这张表上抽一次签。")
say("下面用【同一组固定的随机数】去抽，看不同温度下抽到什么：")
say("=" * 66)

DRAWS = [0.05, 0.30, 0.55, 0.80, 0.95]

for t in TEMPS:
    ps = reshape(logits, t)
    picked: list[str] = []
    for u in DRAWS:
        acc = 0.0
        hit = tokens[-1]
        for tok, p in zip(tokens, ps):
            acc += p
            if u <= acc:
                hit = tok
                break
        picked.append(hit.replace("\n", "\\n").replace(" ", "␣"))

    label = "0.0" if t == 0.0 else f"{t}"
    say()
    say(f"temperature = {label}")
    for u, tok in zip(DRAWS, picked):
        say(f"    随机数 {u:.2f}  ->  抽到 「{tok}」")
    say(f"    >>> {len(set(picked))} 种不同结果")

say()

out = HERE / "out_logprobs.txt"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"written: {out}")
