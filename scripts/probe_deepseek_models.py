"""复核：DeepSeek 到底提供哪些模型？

为什么需要这一步：
    上一次我用 404 推断"没有 /embeddings 端点"，但 404 也可能只是
    "这个模型不支持这个功能"。两者无法区分。

    最干净的办法：直接问服务端【你有哪些模型】。
    如果返回的列表里压根没有 embedding 类的模型，结论才算钉死。
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def main() -> None:
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
    )

    print("=" * 64)
    print("GET /models  ->  DeepSeek 到底提供了哪些模型")
    print("=" * 64)
    try:
        models = client.models.list()
        for m in models.data:
            print(f"  - {m.id}")
        print(f"\n共 {len(models.data)} 个模型")
    except Exception as exc:
        print(f"  [FAIL] {type(exc).__name__}: {exc}")

    print()
    print("=" * 64)
    print("再试一次 /embeddings，但这次把【完整错误体】打出来")
    print("=" * 64)
    for model_name in ("deepseek-embedding", "deepseek-chat"):
        try:
            client.embeddings.create(model=model_name, input="测试")
            print(f"  {model_name}: [OK]")
        except Exception as exc:
            print(f"\n  --- {model_name} ---")
            print(f"  类型: {type(exc).__name__}")
            # 把完整信息打出来，看服务端到底怎么说
            print(f"  str(exc)     : {exc}")
            body = getattr(exc, "body", None)
            print(f"  .body        : {body}")
            resp = getattr(exc, "response", None)
            if resp is not None:
                print(f"  .status_code : {resp.status_code}")
                print(f"  .url         : {resp.url}")
                print(f"  .text        : {resp.text[:500]}")


if __name__ == "__main__":
    main()
