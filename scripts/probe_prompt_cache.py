import json
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from llm_toolkit.providers import close_all, get_provider
from openai.types.chat import ChatCompletion

from kb.evidence import check_evidence
from kb.observability import measure_stage, write_model_usage


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    load_dotenv(ROOT / ".env")
    document = (ROOT / "examples" / "refund_policy.md").read_text(
        encoding="utf-8"
    )
    log_path = ROOT / "data" / "day23" / f"prompt_cache_{uuid4().hex}.jsonl"
    provider = get_provider("deepseek")

    try:
        for number in range(1, 3):
            request_id = uuid4().hex

            def show_usage(response: ChatCompletion) -> None:
                write_model_usage(log_path, request_id, "evidence", response)
                usage = (
                    response.usage.model_dump(mode="json")
                    if response.usage is not None
                    else None
                )
                print(json.dumps(usage, ensure_ascii=False, indent=2))

            print(f"第 {number} 次调用")
            with measure_stage(log_path, request_id, "evidence"):
                decision = check_evidence(
                    provider,
                    question="退款多久到账？",
                    documents=[document],
                    on_response=show_usage,
                )
            print("资料是否充分：", decision.answerable)
    finally:
        close_all()
        print("本次验证日志：", log_path)


if __name__ == "__main__":
    main()
