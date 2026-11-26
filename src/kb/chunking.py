# Day 5：文本切片。
def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    current: list[str] = []

    for character in text:
        current.append(character)

        if character in "。！？":
            sentences.append("".join(current))
            current.clear()

    if current:
        sentences.append("".join(current))

    return sentences
    
def merge_sentences(
    sentences: list[str],
    chunk_size: int,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")

    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for sentence in sentences:
        if current and (
            current_length + len(sentence) > chunk_size
        ):
            chunks.append("".join(current))
            current.clear()
            current_length = 0

        current.append(sentence)
        current_length += len(sentence)

    if current:
        chunks.append("".join(current))

    return chunks

def split_long_sentence(
    text: str,
    chunk_size: int,
    separators: tuple[str, ...] = ("；", "，"),
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")

    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    if not separators:
        return [
            text[start:start + chunk_size]
            for start in range(0, len(text), chunk_size)
        ]

    separator = separators[0]
    parts = text.split(separator)
    pieces: list[str] = []

    for index, part in enumerate(parts):
        if index < len(parts) - 1:
            part += separator

        pieces.extend(
            split_long_sentence(
                part,
                chunk_size,
                separators[1:],
            )
        )

    return pieces
    
def split_text(
    text: str,
    chunk_size: int = 400,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")

    paragraphs = text.split("\n\n")
    chunks: list[str] = []

    for index, paragraph in enumerate(paragraphs):
        if index < len(paragraphs) - 1:
            paragraph += "\n\n"

        sentences = split_sentences(paragraph)
        pieces: list[str] = []

        for sentence in sentences:
            pieces.extend(
                split_long_sentence(
                    sentence,
                    chunk_size,
                    separators=("\n", "；", "，"),
                )
            )

        chunks.extend(
            merge_sentences(pieces, chunk_size)
        )

    return chunks