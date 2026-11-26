# Day 7：检索指标。
from math import log2
def recall_at_k(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    k: int,
) -> float | None:
    if k <= 0:
        raise ValueError("k 必须大于 0")

    if not relevant_ids:
        return None

    retrieved = set(retrieved_ids[:k])
    hits = retrieved & relevant_ids

    return len(hits) / len(relevant_ids)
    
def reciprocal_rank_at_k(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    k: int,
) -> float | None:
    if k <= 0:
        raise ValueError("k 必须大于 0")

    if not relevant_ids:
        return None

    for rank, chunk_id in enumerate(
        retrieved_ids[:k],
        start=1,
    ):
        if chunk_id in relevant_ids:
            return 1 / rank

    return 0.0
    
def ndcg_at_k(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    k: int,
) -> float | None:
    if k <= 0:
        raise ValueError("k 必须大于 0")

    if not relevant_ids:
        return None

    dcg = 0.0
    seen: set[str] = set()

    for rank, chunk_id in enumerate(
        retrieved_ids[:k],
        start=1,
    ):
        if chunk_id in relevant_ids and chunk_id not in seen:
            dcg += 1 / log2(rank + 1)
            seen.add(chunk_id)

    ideal_count = min(k, len(relevant_ids))
    ideal_dcg = sum(
        1 / log2(rank + 1)
        for rank in range(1, ideal_count + 1)
    )

    return dcg / ideal_dcg