from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
document = (ROOT / "examples" / "refund_policy.md").read_text(
    encoding="utf-8"
)

chunk_size = 80
chunks = []

for start in range(0, len(document), chunk_size):
    chunk = document[start:start + chunk_size]
    chunks.append(chunk)

for index, chunk in enumerate(chunks, start=1):
    print(f"\n--- 第 {index} 块，共 {len(chunk)} 个字符 ---")
    print(chunk)

assert "".join(chunks) == document

print("\n=== 按二级标题切片 ===")

sections = document.split("\n## ")
heading_chunks = []

for index, section in enumerate(sections):
    if index == 0:
        chunk = section
    else:
        chunk = "\n## " + section

    heading_chunks.append(chunk)

for index, chunk in enumerate(heading_chunks, start=1):
    print(f"\n--- 第 {index} 块，共 {len(chunk)} 个字符 ---")
    print(chunk)

assert "".join(heading_chunks) == document