import argparse
from pathlib import Path
from kb.ingestion import load_document
import chromadb
from fastembed import TextEmbedding
from kb.chunking import split_text

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser()
parser.add_argument(
    "--document", type=Path, default=ROOT / "examples" / "refund_policy.md"
)
parser.add_argument("--collection", default="refund_bge_small_zh_v1")
parser.add_argument("--id-prefix", default="refund")
args = parser.parse_args()

sections = load_document(args.document)

if not sections:
    raise ValueError("文档没有提取到可入库的正文")

chunks = []
metadatas = []

for section_index, section in enumerate(sections):
    heading = " > ".join(section.heading_path)

    bodies = split_text(
        section.text,
        chunk_size=400,
    )

    for body in bodies:
        chunk_index = len(chunks)

        chunk = f"{heading}\n{body}".strip()
        chunks.append(chunk)

        metadata = {
            "source": section.source,
            "document_title": (
                section.heading_path[0]
                if section.heading_path
                else section.source
            ),
            "heading_path": heading,
            "section_index": section_index,
            "chunk_index": chunk_index,
        }

        if section.page is not None:
            metadata["page"] = section.page

        metadatas.append(metadata)

model = TextEmbedding(
    model_name="BAAI/bge-small-zh-v1.5",
    cache_dir=str(ROOT / "data" / "models"),
    threads=2,
)

vectors = list(model.passage_embed(chunks))

client = chromadb.PersistentClient(
    path=str(ROOT / "data" / "chroma")
)

collection = client.get_or_create_collection(
    name=args.collection,
    embedding_function=None,
    configuration={"hnsw": {"space": "cosine"}},
)

collection.upsert(
    ids=[f"{args.id_prefix}-{index}" for index in range(len(chunks))],
    documents=chunks,
    embeddings=[vector.tolist() for vector in vectors],
    metadatas=metadatas,
)

print("文档：", args.document.resolve())
print("集合：", args.collection)
print("库中片段数：", collection.count())
