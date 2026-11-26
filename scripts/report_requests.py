import argparse
import json
import math
from pathlib import Path

from kb.observability import estimate_token_cost, summarize_stages, summarize_usage


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log",
        type=Path,
        default=ROOT / "data" / "logs" / "requests.jsonl",
    )
    parser.add_argument("--cache-hit-price", type=float)
    parser.add_argument("--cache-miss-price", type=float)
    parser.add_argument("--output-price", type=float)
    parser.add_argument("--currency", default="CNY")
    args = parser.parse_args()

    prices = [args.cache_hit_price, args.cache_miss_price, args.output_price]
    if any(price is not None for price in prices):
        if any(price is None or not math.isfinite(price) or price < 0 for price in prices):
            parser.error("请同时提供三个非负、有限的每百万 Token 单价")

    if not args.log.is_file():
        parser.error(f"日志文件不存在：{args.log}")

    latest_cache_snapshot = None
    models = set()
    with args.log.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event") == "query_cache_snapshot":
                latest_cache_snapshot = event["stats"]
            if event.get("event") == "model_usage":
                models.add(event.get("response_model"))

    usage = summarize_usage(args.log)
    cost = None
    cost_note = "未提供单价，未估算成本"
    if all(price is not None for price in prices):
        if usage["missing_usage"] or usage["missing_cache_usage"]:
            cost_note = "用量缺失，未估算成本"
        elif len(models) != 1 or None in models:
            cost_note = "需提供只包含同一已知模型的日志"
        else:
            cost = estimate_token_cost(
                cache_hit_tokens=usage["cache_hit_tokens"],
                cache_miss_tokens=usage["cache_miss_tokens"],
                completion_tokens=usage["completion_tokens"],
                cache_hit_price=args.cache_hit_price,
                cache_miss_price=args.cache_miss_price,
                completion_price=args.output_price,
            )
            cost_note = "对整个日志应用所提供的单价；未自动识别历史价格或峰谷时段"

    report = {
        "usage": usage,
        "stages": summarize_stages(args.log),
        "latest_cache_snapshot": latest_cache_snapshot,
        "cost_estimate": {
            "amount": cost,
            "currency": args.currency,
            "prices_per_million": {
                "cache_hit": args.cache_hit_price,
                "cache_miss": args.cache_miss_price,
                "output": args.output_price,
            },
            "note": cost_note,
        },
    }

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
