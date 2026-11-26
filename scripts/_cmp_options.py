"""实验组 B：把 6 个参数【打包】成 ChatOptions。

同样只用来数行数、跑类型检查。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, overload

from openai import AsyncStream, Stream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionStreamOptionsParam,
    completion_create_params,
)

ResponseFormat = completion_create_params.ResponseFormat


@dataclass(frozen=True)
class ChatOptions:
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    response_format: ResponseFormat | None = None
    stream_options: ChatCompletionStreamOptionsParam | None = None
    extra_body: dict[str, object] | None = None


class ProviderOptions:
    model = "m"

    @overload
    def call(
        self, messages: list[dict], stream: Literal[False] = False,
        options: ChatOptions | None = None,
    ) -> ChatCompletion: ...
    @overload
    def call(
        self, messages: list[dict], stream: Literal[True],
        options: ChatOptions | None = None,
    ) -> Stream[ChatCompletionChunk]: ...
    def call(
        self, messages: list[dict], stream: bool = False,
        options: ChatOptions | None = None,
    ) -> object:
        raise NotImplementedError

    @overload
    async def call_async(
        self, messages: list[dict], stream: Literal[False] = False,
        options: ChatOptions | None = None,
    ) -> ChatCompletion: ...
    @overload
    async def call_async(
        self, messages: list[dict], stream: Literal[True],
        options: ChatOptions | None = None,
    ) -> AsyncStream[ChatCompletionChunk]: ...
    async def call_async(
        self, messages: list[dict], stream: bool = False,
        options: ChatOptions | None = None,
    ) -> object:
        raise NotImplementedError


# ---- 上层包装：透传配置只需要 1 个参数 ----
def summarize_options(text: str, options: ChatOptions | None = None) -> str:
    return text
