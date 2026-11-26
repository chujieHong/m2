"""数一数：A（直接写参数）和 B（打包 ChatOptions）各要改几处。

只数 5 个在这两个文件里不会重名的参数名，避免误伤。

输出写到 out_cmp.txt（UTF-8）。
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).parent
PARAMS = ["temperature", "max_tokens", "response_format", "stream_options", "extra_body"]

lines: list[str] = []


def say(s: str = "") -> None:
    lines.append(s)


say("=" * 58)
say("同一个功能，两种写法：参数名在文件里出现几次")
say("（出现几次 = 将来要改几处）")
say("=" * 58)

for fname, label in [
    ("_cmp_inline.py", "A  6个参数直接写在签名上"),
    ("_cmp_options.py", "B  打包成 ChatOptions"),
]:
    src = (HERE / fname).read_text(encoding="utf-8")
    total = 0
    detail: list[str] = []
    for p in PARAMS:
        n = src.count(p)
        total += n
        detail.append(f"{p}={n}")

    say()
    say(f"--- {label} ---")
    say(f"    文件总行数        : {len(src.splitlines())}")
    say(f"    参数名出现总次数  : {total}")
    say(f"    明细              : {', '.join(detail)}")

say()
say("=" * 58)
say("读懂这张表的关键：")
say("  '参数名出现几次' 就等于 '加第 7 个参数时要动几处'。")
say("  出现 1 次 = 改 1 个地方；出现 5 次 = 改 5 个地方，还得保证改全。")
say("=" * 58)

out = HERE / "out_cmp.txt"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"written: {out}")
