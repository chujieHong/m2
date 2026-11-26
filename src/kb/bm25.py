from collections import Counter
import math

import jieba


def tokenize(
    text: str,
    search_mode: bool = False,
) -> list[str]:
    if search_mode:
        tokens = jieba.lcut_for_search(text)
    else:
        tokens = jieba.lcut(text)

    return [
        token.lower()
        for token in tokens
        if any(character.isalnum() for character in token)
    ]


class BM25:
    def __init__(
        self,
        documents: list[str],
        k1: float = 1.5,
        b: float = 0.75,
        search_mode: bool = False,
    ) -> None:
        if not documents:
            raise ValueError("文档列表不能为空")
        if not math.isfinite(k1) or k1 <= 0:
            raise ValueError("k1 必须是大于 0 的有限数")
        if not 0 <= b <= 1:
            raise ValueError("b 必须在 0 到 1 之间")

        self.k1 = k1
        self.b = b
        self.search_mode = search_mode
        
        tokenized_documents = [
            tokenize(document, search_mode=self.search_mode)
            for document in documents
        ]

        self.term_counts = [
            Counter(tokens)
            for tokens in tokenized_documents
        ]
        self.document_lengths = [
            len(tokens)
            for tokens in tokenized_documents
        ]
        self.document_count = len(documents)
        self.average_length = (
            sum(self.document_lengths) / self.document_count
        )

        if self.average_length == 0:
            raise ValueError("文档中没有可用于检索的词")

        self.document_frequencies = Counter()
        for tokens in tokenized_documents:
            self.document_frequencies.update(set(tokens))
            
    def score(
        self,
        question: str,
        query_stop_words: set[str] | None = None,
    ) -> list[float]:
        query_terms = set(
            tokenize(question, search_mode=self.search_mode)
        )

        if query_stop_words is not None:
            query_terms = query_terms - query_stop_words

        if not query_terms:
            raise ValueError("问题中没有可用于检索的词")

        idf_by_term = {}
        for term in query_terms:
            df = self.document_frequencies[term]
            idf_by_term[term] = math.log(
                1 + (self.document_count - df + 0.5) / (df + 0.5)
            )

        scores = []
        for counts, length in zip(
            self.term_counts,
            self.document_lengths,
        ):
            length_factor = (
                1 - self.b
                + self.b * length / self.average_length
            )

            score = 0.0
            for term in query_terms:
                tf = counts[term]
                tf_weight = (
                    tf * (self.k1 + 1)
                    / (tf + self.k1 * length_factor)
                )
                score += idf_by_term[term] * tf_weight

            scores.append(score)

        return scores