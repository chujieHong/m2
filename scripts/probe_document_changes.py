import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser()
parser.add_argument(
    "--document",
    type=Path,
    default=ROOT / "examples" / "refund_policy.md",
)
parser.add_argument("--save", action="store_true")
args = parser.parse_args()

document_path = args.document.resolve()
snapshot_path = ROOT / "data" / "day17" / "document_snapshots.json"

content = document_path.read_bytes()
current_hash = hashlib.sha256(content).hexdigest()

if snapshot_path.exists():
    snapshots = json.loads(
        snapshot_path.read_text(encoding="utf-8")
    )
else:
    snapshots = {}

document_key = str(document_path)
previous_hash = snapshots.get(document_key)

if previous_hash is None:
    status = "新文档"
elif previous_hash == current_hash:
    status = "内容未变"
else:
    status = "内容已变"

print("文件：", document_path)
print("状态：", status)
print("上次指纹：", previous_hash)
print("本次指纹：", current_hash)

if args.save:
    snapshots[document_key] = current_hash

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = snapshot_path.with_suffix(".tmp")

    temporary_path.write_text(
        json.dumps(snapshots, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(snapshot_path)

    print("已保存当前内容快照。")