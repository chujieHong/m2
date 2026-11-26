"""对照组 A：把 6 个参数【直接】写在 call / call_async 的签名上。

这个文件只用来数行数、跑类型检查，不真的调 API。
"""
from __future__ import annotations

from typing import Literal, overload

from openai import AsyncStream, Stream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionStreamOptionsParam,
    completion_create_params,
)

ResponseFormat = completion_create_params.ResponseFormat


class ProviderInline:
    model = "m"

    # ---- 下面 4 个签名，每个都要把 6 个参数完整抄一遍 ----
    @overload
    def call(
        self, messages: list[dict], stream: Literal[False] = False, *,
        model: str | None = None, temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: ResponseFormat | None = None,
        stream_options: ChatCompletionStreamOptionsParam | None = None,
        extra_body: dict[str, object] | None = None,
    ) -> ChatCompletion: ...
    @overload
    def call(
        self, messages: list[dict], stream: Literal[True], *,
        model: str | None = None, temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: ResponseFormat | None = None,
        stream_options: ChatCompletionStreamOptionsParam | None = None,
        extra_body: dict[str, object] | None = None,
    ) -> Stream[ChatCompletionChunk]: ...
    def call(
        self, messages: list[dict], stream: bool = False, **kw: object
    ) -> object:
        raise NotImplementedError

    @overload
    async def call_async(
        self, messages: list[dict], stream: Literal[False] = False, *,
        model: str | None = None, temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: ResponseFormat | None = None,
        stream_options: ChatCompletionStreamOptionsParam | None = None,
        extra_body: dict[str, object] | None = None,
    ) -> ChatCompletion: ...
    @overload
    async def call_async(
        self, messages: list[dict], stream: Literal[True], *,
        model: str | None = None, temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: ResponseFormat | None = None,
        stream_options: ChatCompletionStreamOptionsParam | None = None,
        extra_body: dict[str, object] | None = None,
    ) -> AsyncStream[ChatCompletionChunk]: ...
    async def call_async(
        self, messages: list[dict], stream: bool = False, **kw: object
    ) -> object:
        raise NotImplementedError


# ---- 上层包装：想把配置透传下去，6 个参数还得再抄一遍 ----
def summarize_inline(
    text: str,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    response_format: ResponseFormat | None = None,
    stream_options: ChatCompletionStreamOptionsParam | None = None,
    extra_body: dict[str, object] | None = None,
) -> str:
    return text
