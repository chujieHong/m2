"""Day 23：将处理事件追加保存为 JSONL 日志。"""

import json
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any, Iterator

from openai.types.chat import ChatCompletion


LOG_LOCK = Lock()


def summarize_usage(log_path: Path) -> dict[str, int]:
    totals = {
        "model_responses": 0,
        "missing_usage": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cache_hit_tokens": 0,
        "cache_miss_tokens": 0,
        "missing_cache_usage": 0,
    }

    with log_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            event = json.loads(line)

            if event.get("event") != "model_usage":
                continue

            totals["model_responses"] += 1
            usage = event["usage"]

            if usage is None:
                totals["missing_usage"] += 1
                continue

            totals["prompt_tokens"] += usage["prompt_tokens"]
            totals["completion_tokens"] += usage["completion_tokens"]

            hit = usage.get("prompt_cache_hit_tokens")
            miss = usage.get("prompt_cache_miss_tokens")
            if hit is None or miss is None:
                totals["missing_cache_usage"] += 1
            else:
                if hit < 0 or miss < 0 or hit + miss != usage["prompt_tokens"]:
                    raise ValueError("缓存用量与输入 Token 总数不一致")
                totals["cache_hit_tokens"] += hit
                totals["cache_miss_tokens"] += miss

    return totals


def estimate_token_cost(
    *,
    cache_hit_tokens: int,
    cache_miss_tokens: int,
    completion_tokens: int,
    cache_hit_price: float,
    cache_miss_price: float,
    completion_price: float,
) -> float:
    return (
        cache_hit_tokens * cache_hit_price
        + cache_miss_tokens * cache_miss_price
        + completion_tokens * completion_price
    ) / 1_000_000


def summarize_stages(
    log_path: Path,
) -> dict[str, dict[str, Any]]:
    stages: dict[str, dict[str, Any]] = {}

    with log_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            event = json.loads(line)

            if "elapsed_seconds" not in event:
                continue

            stage = event["stage"]

            if stage not in stages:
                stages[stage] = {
                    "count": 0,
                    "errors": 0,
                    "total_seconds": 0.0,
                }

            stats = stages[stage]
            stats["count"] += 1
            stats["total_seconds"] += event["elapsed_seconds"]

            if event["status"] == "error":
                stats["errors"] += 1

    for stats in stages.values():
        stats["average_seconds"] = round(
            stats["total_seconds"] / stats["count"],
            6,
        )

    return stages


def write_model_usage(
    log_path: Path,
    request_id: str,
    stage: str,
    response: ChatCompletion,
) -> None:
    usage = (
        response.usage.model_dump(mode="json")
        if response.usage is not None
        else None
    )

    write_event(
        log_path,
        {
            "request_id": request_id,
            "stage": stage,
            "event": "model_usage",
            "response_model": response.model,
            "usage": usage,
        },
    )


def write_event(
    log_path: Path,
    event: dict[str, Any],
) -> None:
    line = json.dumps(
        event,
        ensure_ascii=False,
        allow_nan=False,
    )

    with LOG_LOCK:
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with log_path.open("a", encoding="utf-8") as file:
            file.write(line + "\n")


@contextmanager
def measure_stage(
    log_path: Path,
    request_id: str,
    stage: str,
) -> Iterator[None]:
    started = perf_counter()
    status = "ok"
    error_type = None

    try:
        yield
    except Exception as exc:
        status = "error"
        error_type = type(exc).__name__
        raise
    finally:
        write_event(
            log_path,
            {
                "request_id": request_id,
                "stage": stage,
                "status": status,
                "elapsed_seconds": round(perf_counter() - started, 6),
                "error_type": error_type,
            },
        )
