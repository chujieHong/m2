"""Embedding 是什么？—— 用实验回答，而不是用嘴解释。

这是一个【教学用的临时脚本】，不属于正式代码，可以随时删。
它用 M2 真正会用的那个模型（bge-small-zh-v1.5）跑一遍，
让你亲眼看到三件事：
  1. 一句话真的变成了一串数字（512 个）
  2. 意思相近的句子，数字也算得近
  3. 字面完全不重合的句子，向量反而最像 —— 这就是为什么需要 embedding

⚠️ 本脚本的结论由【数据算出来】，不是写死的。
   第一版我把结论硬编码在 print 里，结果和真实输出对不上
   （我说「收费标准说明」最像，实际「价格与计费方式」最像）。
   教训：结论必须从数据推导，否则文档会撒谎。
"""
from __future__ import annotations

import numpy as np
from fastembed import TextEmbedding

QUESTION = "这个要花多少钱"

DOCUMENTS = [
    "收费标准说明",
    "价格与计费方式",
    "如何重置密码",
]


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """余弦相似度：两个向量的"夹角"。

    我们关心的不是向量有多长，而是【方向】像不像，
    所以先除以长度（归一化），再算点积。
    """
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def main() -> None:
    print("正在加载模型 BAAI/bge-small-zh-v1.5 ...")
    print("（第一次要下载约 100MB，之后就本地缓存了）\n")
    model = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")

    sentences = [QUESTION, *DOCUMENTS]
    vectors = [np.asarray(v) for v in model.embed(sentences)]
    question_vec = vectors[0]
    doc_vecs = vectors[1:]

    print("=" * 66)
    print(f"一句话被变成了 {len(question_vec)} 个数字（这就是 512 维向量）")
    print(f"前 8 个数字：{[round(float(x), 4) for x in question_vec[:8]]}")
    print("=" * 66)

    print(f"\n【用户的问题】{QUESTION}\n")

    # 两个指标都算出来，再一起看
    sims = [cosine(question_vec, v) for v in doc_vecs]
    shared = [len(set(QUESTION) & set(doc)) for doc in DOCUMENTS]

    print(f"{'相似度':>8}  {'共用字数':>8}   文档")
    print("-" * 66)
    for doc, s, n in zip(DOCUMENTS, sims, shared, strict=True):
        print(f"{s:>8.4f}  {n:>8}   {doc}")
    print("-" * 66)

    # ⭐ 结论由数据推导，不写死
    best = int(np.argmax(sims))
    worst = int(np.argmin(sims))

    print("\n看到了吗：")
    print(f"  最像的「{DOCUMENTS[best]}」和问题共用了 {shared[best]} 个字，"
          f"相似度 {sims[best]:.4f}")
    print(f"  最不像的「{DOCUMENTS[worst]}」和问题共用了 {shared[worst]} 个字，"
          f"相似度 {sims[worst]:.4f}")
    print(f"  → 两条字面重合度完全一样（都是 {shared[best]} 个字），"
          "但向量把它们分开了。")
    print("  → 字面匹配在这里【完全失效】，意思匹配才是我们要的。")
    print("     这就是 embedding 存在的理由，也是 RAG 的地基。")


if __name__ == "__main__":
    main()
