from pathlib import Path

from dotenv import load_dotenv
from llm_toolkit.providers import close_all, get_provider

from kb.bm25 import BM25
from kb.ingestion import load_document
from plan_query import plan_query


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

sections = load_document(ROOT / "examples" / "refund_policy.md")
retriever = BM25([section.text for section in sections])

cases = [
    {
        "name": "明确的历史追问",
        "history": [
            {"role": "user", "content": "退款有什么使用时长限制？"},
            {
                "role": "assistant",
                "content": "累计使用超过2小时的订单不支持退款。",
            },
        ],
        "question": "那超过了呢？",
        "expected_action": "search",
    },
    {
        "name": "独立完整问题",
        "history": [],
        "question": "退款审核通过后多久到账？",
        "expected_action": "search",
    },
    {
        "name": "存在多个可能的指代",
        "history": [
            {"role": "user", "content": "我想了解退款和发票。"},
            {"role": "assistant", "content": "你想了解哪一项？"},
        ],
        "question": "那个要多久？",
        "expected_action": "clarify",
    },
]

correct = 0

try:
    provider = get_provider("deepseek")

    for case in cases:
        plan = plan_query(
            provider,
            history=case["history"],
            question=case["question"],
        )

        matched = plan.action == case["expected_action"]
        correct += int(matched)

        print(f"\n===== {case['name']} =====")
        print("原问题：", case["question"])
        print("预期动作：", case["expected_action"])
        print("实际动作：", plan.action)
        print("动作是否正确：", matched)

        if plan.action == "clarify":
            print("向用户追问：", plan.clarification)
            print("本轮没有执行检索。")
            continue

        assert plan.query is not None
        print("检索问题：", plan.query)

        scores = retriever.score(plan.query)
        index, score = max(
            enumerate(scores),
            key=lambda item: item[1],
        )

        if score <= 0:
            print("没有匹配的资料。")
        else:
            print("命中的依据：\n", sections[index].text)

finally:
    close_all()

print(f"\n动作选择正确：{correct}/{len(cases)}")