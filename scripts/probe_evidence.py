import json
from pathlib import Path
from time import time_ns

from dotenv import load_dotenv
from llm_toolkit.providers import ChatOptions, close_all, get_provider
from llm_toolkit.providers.base import extract_answer

from kb.evidence import check_evidence
from kb.generation import build_answer_messages
from kb.grounding import check_answer_support


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

cases = [
    {
        "name": "资料足够",
        "question": "退款审核通过后多久到账？",
        "documents": [
            "退款审核通过后，在3个工作日内原路退回。",
        ],
        "expected": True,
    },
    {
        "name": "只覆盖部分问题",
        "question": "退款审核通过后多久到账，手续费是多少？",
        "documents": [
            "退款审核通过后，在3个工作日内原路退回。",
        ],
        "expected": False,
    },
    {
        "name": "资料无关",
        "question": "退款审核通过后多久到账？",
        "documents": [
            "电子发票在申请后的2个工作日内开具。",
        ],
        "expected": False,
    },
    {
        "name": "相同条件下的规则冲突",
        "question": "产品A的退款审核通过后多久到账？",
        "documents": [
            "产品A所有订单：退款一律在审核通过后的第3个工作日到账。",
            "产品A所有订单：退款一律在审核通过后的第5个工作日到账。",
        ],
        "expected": False,
    },
    {
        "name": "没有资料",
        "question": "退款审核通过后多久到账？",
        "documents": [],
        "expected": False,
    },
]

records = []

try:
    provider = get_provider("deepseek")

    for case in cases:
        decision = check_evidence(
            provider,
            question=case["question"],
            documents=case["documents"],
        )

        matched = decision.answerable == case["expected"]

        print(f"\n===== {case['name']} =====")
        print("预期可回答：", case["expected"])
        print("实际可回答：", decision.answerable)
        print("判断是否正确：", matched)
        print("依据编号：", decision.evidence_numbers)
        print("缺失或冲突：", decision.missing_information)

        review = None
        draft_answer = None

        if decision.answerable:
            response = provider.call(
                build_answer_messages(
                    case["question"],
                    case["documents"],
                ),
                options=ChatOptions(
                    model="deepseek-flash",
                    temperature=0.0,
                    max_tokens=500,
                ),
            )

            if not response.choices:
                raise ValueError("答案生成没有返回结果")

            if response.choices[0].finish_reason != "stop":
                raise ValueError("答案生成未正常完成")

            answer = extract_answer(response).strip()

            if not answer:
                raise ValueError("答案生成返回了空文本")

            draft_answer = answer

            review = check_answer_support(
                provider,
                question=case["question"],
                documents=case["documents"],
                answer=answer,
            )

            if not review.supported:
                answer = "生成的回答未通过资料依据审核，暂不提供该答案。"
        else:
            missing = "；".join(decision.missing_information)
            answer = f"现有资料不足以完整回答。缺失或冲突：{missing}"

        print("最终回复：", answer)

        records.append({
            **case,
            "decision": decision.model_dump(),
            "draft_answer": draft_answer,
            "review": review.model_dump() if review is not None else None,
            "answer": answer,
            "matched": matched,
        })
finally:
    close_all()

output_dir = ROOT / "data" / "day20"
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / f"evidence_check_{time_ns()}.json"

output_path.write_text(
    json.dumps(records, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

correct = sum(record["matched"] for record in records)
print(f"\n判断正确：{correct}/{len(records)}")
print("实验记录：", output_path)
