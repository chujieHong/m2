def reciprocal_rank_fusion(
    rankings: list[list[str]],
    top_k: int = 5,
    rank_constant: int = 60,
) -> list[tuple[str, float]]:
    if top_k <= 0:
        raise ValueError("top_k 必须大于 0")
    if rank_constant < 0:
        raise ValueError("rank_constant 不能小于 0")

    fused_scores: dict[str, float] = {}

    for ranking in rankings:
        seen: set[str] = set()

        for rank, chunk_id in enumerate(ranking, 1):
            if chunk_id in seen:
                continue
            seen.add(chunk_id)

            fused_scores[chunk_id] = (
                fused_scores.get(chunk_id, 0.0)
                + 1 / (rank_constant + rank)
            )

    return sorted(
        fused_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:top_k]