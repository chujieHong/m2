import multiprocessing as mp
from pathlib import Path
from time import perf_counter
ROOT = Path(__file__).resolve().parents[1]


def rerank_worker(connection, question, documents):
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    try:
        reranker = TextCrossEncoder(
            model_name="BAAI/bge-reranker-v2-m3-int8",
            cache_dir=str(ROOT / "data" / "models"),
            threads=2,
            cuda=False,
            local_files_only=True,
        )

        scores = list(
            reranker.rerank(
                query=question,
                documents=documents,
                batch_size=1,
            )
        )

        connection.send({
            "ok": True,
            "scores": scores,
        })
    except Exception as error:
        connection.send({
            "ok": False,
            "error": f"{type(error).__name__}: {error}",
        })
    finally:
        connection.close()
        
def rerank_with_fallback(
    question,
    candidate_ids,
    documents,
    timeout_seconds=20.0,
):
    if timeout_seconds <= 0:
        raise ValueError("等待时间必须大于 0")
    if len(candidate_ids) != len(documents):
        raise ValueError("片段 ID 与正文数量不一致")

    context = mp.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)

    process = context.Process(
        target=rerank_worker,
        args=(sender, question, documents),
    )

    started = perf_counter()

    try:
        process.start()
        sender.close()

        remaining = max(
            0.0,
            timeout_seconds - (perf_counter() - started),
        )

        if not receiver.poll(remaining):
            return {
                "ids": list(candidate_ids),
                "reason": "timeout",
            }

        result = receiver.recv()

        if not result["ok"]:
            return {
                "ids": list(candidate_ids),
                "reason": f"worker_error: {result['error']}",
            }

        scores = result["scores"]
        if len(scores) != len(candidate_ids):
            return {
                "ids": list(candidate_ids),
                "reason": "score_count_mismatch",
            }

        ranked = sorted(
            zip(candidate_ids, scores),
            key=lambda item: item[1],
            reverse=True,
        )
        return {
            "ids": [chunk_id for chunk_id, score in ranked],
            "reason": "reranked",
        }
    except (EOFError, OSError) as error:
        return {
            "ids": list(candidate_ids),
            "reason": f"process_error: {error}",
        }
    finally:
        sender.close()
        receiver.close()

        if process.pid is not None:
            process.join(timeout=0.2)

            if process.is_alive():
                process.terminate()
                process.join(timeout=1.0)

            if process.is_alive():
                process.kill()
                process.join()

            process.close()

if __name__ == "__main__":
    question = "Bucket ACL 默认是什么权限值？"

    candidate_ids = ["upload", "bucket_acl", "object_acl"]
    documents = [
        "分片上传支持断点续传。",
        "Bucket ACL 的默认权限值是 private。",
        "Object ACL 的默认值是 default，表示继承 Bucket ACL。",
    ]

    experiments = [
        ("正常等待", 60.0),
        ("极短等待，触发回退", 0.01),
    ]

    for name, timeout_seconds in experiments:
        started = perf_counter()

        result = rerank_with_fallback(
            question,
            candidate_ids,
            documents,
            timeout_seconds=timeout_seconds,
        )

        elapsed = perf_counter() - started

        print(f"\n实验：{name}")
        print("结果来源：", result["reason"])
        print("返回顺序：", result["ids"])
        print(f"总耗时：{elapsed:.2f} 秒")

    print("\n仍在运行的子进程数量：", len(mp.active_children()))
    
    
    print("\n实验：故意传入错误正文类型")
    error_result = rerank_with_fallback(
        question,
        candidate_ids,
        [None, None, None],
        timeout_seconds=60.0,
    )
    print("结果来源：", error_result["reason"])
    print("返回顺序：", error_result["ids"])
    print("\n仍在运行的子进程数量：", len(mp.active_children()))