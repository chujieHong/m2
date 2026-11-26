rankings = [
    ["A", "B", "C"],
    ["B", "D", "A"],
]

rank_constant = 60
fused_scores = {}

for ranking in rankings:
    for rank, chunk_id in enumerate(ranking, 1):
        contribution = 1 / (rank_constant + rank)

        fused_scores[chunk_id] = (
            fused_scores.get(chunk_id, 0.0)
            + contribution
        )

fused_ranking = sorted(
    fused_scores.items(),
    key=lambda item: item[1],
    reverse=True,
)

for chunk_id, score in fused_ranking:
    print(f"{chunk_id}：{score:.6f}")