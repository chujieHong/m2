"""实验：如果 6 个参数直接写在签名上，把默认值【改漏一处】，谁会报警？

故意让 4 个签名里的默认值不一致：
  两个 overload 说 temperature 默认 0.0，实现却默认 1.0。

问题：mypy / pyright 会不会发现？
"""
from __future__ import annotations

from typing import Literal, overload

from openai import AsyncStream, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk


class ProviderInconsistent:
    model = "m"

    @overload
    def call(
        self, messages: list[dict], stream: Literal[False] = False, *,
        temperature: float = 0.0,          # 说好的默认 0.0
        max_tokens: int = 500,             # 说好的默认 500
    ) -> ChatCompletion: ...
    @overload
    def call(
        self, messages: list[dict], stream: Literal[True], *,
        temperature: float = 0.0,          # 说好的默认 0.0
        max_tokens: int = 500,             # 说好的默认 500
    ) -> Stream[ChatCompletionChunk]: ...
    def call(
        self, messages: list[dict], stream: bool = False, *,
        temperature: float = 1.0,          # 实际却是 1.0  ← 不一致
        max_tokens: int = 1024,            # 实际却是 1024 ← 不一致
    ) -> object:
        raise NotImplementedError

    @overload
    async def call_async(
        self, messages: list[dict], stream: Literal[False] = False, *,
        temperature: float = 0.0,
        max_tokens: int = 500,
    ) -> ChatCompletion: ...
    @overload
    async def call_async(
        self, messages: list[dict], stream: Literal[True], *,
        temperature: float = 0.0,
        max_tokens: int = 500,
    ) -> AsyncStream[ChatCompletionChunk]: ...
    async def call_async(
        self, messages: list[dict], stream: bool = False, *,
        temperature: float = 1.0,
        max_tokens: int = 1024,
    ) -> object:
        raise NotImplementedError


# 调用方（IDE 悬停会显示 overload 的默认值：0.0 / 500）
p = ProviderInconsistent()
p.call([{"role": "user", "content": "hi"}])   # 实际跑起来用的是 1.0 / 1024
