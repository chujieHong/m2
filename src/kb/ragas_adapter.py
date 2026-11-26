"""Day 7：把 M1 的模型调用适配为 RAGAS 结构化接口。"""

import asyncio
from typing import TypeVar

from llm_toolkit.providers.base import BaseProvider
from pydantic import BaseModel
from ragas.llms.base import InstructorBaseRagasLLM
import json

from llm_toolkit.providers import ChatOptions
from llm_toolkit.providers.base import extract_answer

ResultT = TypeVar("ResultT", bound=BaseModel)


class M1RagasLLM(InstructorBaseRagasLLM):
    def __init__(self, provider: BaseProvider) -> None:
        self.provider = provider
        self.trace: list[dict[str, object]] = []

    def generate(self, prompt: str, response_model: type[ResultT]) -> ResultT:
        schema = json.dumps(
            response_model.model_json_schema(),
            ensure_ascii=False,
        )

        response = self.provider.call(
            [
                {
                    "role": "system",
                    "content": (
                        "只输出符合以下 JSON Schema 的 JSON 对象：\n"
                        f"{schema}"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            options=ChatOptions(
                temperature=0.0,
                max_tokens=2048,
                response_format={"type": "json_object"},
            ),
        )

        if not response.choices:
            raise ValueError("RAGAS 裁判没有返回结果")

        if response.choices[0].finish_reason != "stop":
            raise ValueError("RAGAS 裁判生成未正常完成")

        result = response_model.model_validate_json(
            extract_answer(response),
            strict=True,
        )

        self.trace.append({
            "schema_name": response_model.__name__,
            "output": result.model_dump(),
        })

        return result

    async def agenerate(self, prompt: str, response_model: type[ResultT]) -> ResultT:
        # 将同步调用交给工作线程，避免阻塞 RAGAS 的异步事件循环。
        return await asyncio.to_thread(self.generate, prompt, response_model)
