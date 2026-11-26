from kb.bm25 import BM25

parents = {
    "parent-delete": (
        "版本控制开启时，DELETE 未指定 versionId 会添加删除标记"
        "作为当前版本，原有数据版本不被该操作永久删除。\n"
        "当 Object 当前版本为删除标记时，"
        "读取当前版本的 GET 请求返回 404。"
    ),
    "parent-upload": (
        "分片上传支持断点续传。"
    ),
}

children = [
    {
        "id": "child-delete",
        "parent_id": "parent-delete",
        "text": "DELETE 未指定 versionId 会添加删除标记作为当前版本。",
    },
    {
        "id": "child-read",
        "parent_id": "parent-delete",
        "text": "当前版本为删除标记时，GET 请求返回 404。",
    },
    {
        "id": "child-upload",
        "parent_id": "parent-upload",
        "text": "分片上传支持断点续传。",
    },
]

question = "当前版本为删除标记时，GET 返回什么？"

retriever = BM25([
    child["text"]
    for child in children
])
scores = retriever.score(question)

ranked = sorted(
    enumerate(scores),
    key=lambda item: item[1],
    reverse=True,
)

index, score = ranked[0]
if score <= 0:
    raise ValueError("没有匹配的子块")

hit = children[index]
parent_text = parents[hit["parent_id"]]

print("问题：", question)
print("命中的子块 ID：", hit["id"])
print("子块得分：", score)
print("\n只返回子块：\n", hit["text"])
print("\n扩展为父块：\n", parent_text)

selected_parents = {}

for index, score in ranked[:2]:
    if score <= 0:
        continue

    child = children[index]
    parent_id = child["parent_id"]
    selected_parents[parent_id] = parents[parent_id]

print("\n前两个子块对应的父块：")
for parent_id, text in selected_parents.items():
    print(f"\n父块 ID：{parent_id}")
    print(text)