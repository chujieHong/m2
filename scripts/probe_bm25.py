from collections import Counter
import math
import jieba


def tokenize(text: str) -> list[str]:
    tokens = jieba.lcut(text)

    return [
        token.lower()
        for token in tokens
        if any(character.isalnum() for character in token)
    ]


raw_documents = [
    "上传分片失败，错误码是 NoSuchUpload。",
    "上传分片需要上传权限。",
    "Bucket 的默认权限值是 private。",
]

question = "上传时出现 NoSuchUpload"

documents = [
    tokenize(text)
    for text in raw_documents
]
query_tokens = tokenize(question)

print("问题分词：", query_tokens)

for index, tokens in enumerate(documents):
    term_counts = Counter(tokens)

    print(f"\n文档 {index}：", tokens)
    for term in query_tokens:
        print(f"{term} 的出现次数：{term_counts[term]}")
        
document_frequencies = Counter()

for tokens in documents:
    unique_terms = set(tokens)
    document_frequencies.update(unique_terms)

print("\n文档频率 DF：")
for term in query_tokens:
    print(f"{term} 出现在 {document_frequencies[term]} 篇文档中")
    
document_count = len(documents)
idf_by_term = {}

for term in query_tokens:
    df = document_frequencies[term]

    idf = math.log(
        1 + (document_count - df + 0.5) / (df + 0.5)
    )

    idf_by_term[term] = idf
    print(f"{term} 的 IDF：{idf:.4f}")
    
k1 = 1.5
b = 0.75

average_length = (
    sum(len(tokens) for tokens in documents) / len(documents)
)

scores = []

for index, tokens in enumerate(documents):
    term_counts = Counter(tokens)
    document_length = len(tokens)

    length_factor = (
        1 - b + b * document_length / average_length
    )

    score = 0.0
    for term in query_tokens:
        tf = term_counts[term]
        tf_weight = (
            tf * (k1 + 1)
            / (tf + k1 * length_factor)
        )
        score += idf_by_term[term] * tf_weight

    scores.append((index, score))
    
ranked_scores = sorted(
    scores,
    key=lambda item: item[1],
    reverse=True,
)

print("\nBM25 检索排名：")
for index, score in ranked_scores:
    print(f"\n文档 {index}：{score:.4f}")
    print(raw_documents[index])
