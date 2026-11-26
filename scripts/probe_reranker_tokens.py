from pathlib import Path
from tokenizers import Tokenizer
from fastembed.rerank.cross_encoder import TextCrossEncoder
import json
import chromadb
ROOT = Path(__file__).resolve().parents[1]

reranker = TextCrossEncoder(
    model_name="BAAI/bge-reranker-v2-m3-int8",
    cache_dir=str(ROOT / "data" / "models"),
    threads=2,
    cuda=False,
    local_files_only=True,
)

tokenizer = reranker.model.tokenizer

question = "当前版本为删除标记时，读取会怎样？"
document = "当 Object 当前版本为删除标记时，GET 请求返回 404。"

encoded = tokenizer.encode(question, document)

print("截断配置：", tokenizer.truncation)
print("正文字符数：", len(document))
print("问题与正文编码后的 token 数：", len(encoded.ids))

# 复制一个只用于统计完整长度的分词器
full_tokenizer = Tokenizer.from_str(tokenizer.to_str())
full_tokenizer.no_truncation()
full_tokenizer.no_padding()

long_document = document * 2000

full_encoded = full_tokenizer.encode(question, long_document)
limited_encoded = tokenizer.encode(question, long_document)

full_count = len(full_encoded.ids)
limited_count = len(limited_encoded.ids)

print("\n超长输入实验：")
print("完整 token 数：", full_count)
print("截断后 token 数：", limited_count)
print("是否发生截断：", full_count > limited_count)

report_path = ROOT / "data" / "eval_results" / "day13" / (
    "reranker_top5_1792239873697678300.json"
)
report = json.loads(report_path.read_text(encoding="utf-8"))

cases_path = ROOT / "examples" / "day6" / "oss_cases_100.json"
cases = json.loads(cases_path.read_text(encoding="utf-8"))
question_by_id = {
    case["id"]: case["question"]
    for case in cases
}

client = chromadb.PersistentClient(
    path=str(ROOT / "data" / "chroma")
)
collection = client.get_collection(
    report["collection"],
    embedding_function=None,
)
records = collection.get(include=["documents"])
document_by_id = dict(
    zip(records["ids"], records["documents"])
)

limit = tokenizer.truncation["max_length"]
pair_count = 0
over_limit_count = 0
max_tokens = 0

for case_result in report["cases"]:
    question = question_by_id[case_result["id"]]

    for chunk_id in case_result["candidate_ids"]:
        document = document_by_id[chunk_id]
        token_count = len(
            full_tokenizer.encode(question, document).ids
        )

        pair_count += 1
        max_tokens = max(max_tokens, token_count)

        if token_count > limit:
            over_limit_count += 1

print("\n实际重排序输入检查：")
print("问题与片段组合总数：", pair_count)
print("最长输入 token 数：", max_tokens)
print("超过截断上限的组合数：", over_limit_count)