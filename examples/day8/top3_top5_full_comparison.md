# Day 8：100题完整RAG配置对照 v1

2026-10-13。按用户授权自动完成重复执行与评分，先顺序运行top3、top5各100道公开OSS开发题，再用Day7相同裁判规则分别评分。两组均100次生成成功、100份格式合法评分、100份usage。这里的格式合法不表示评分内容正确。

配置仅改变实验名称和top_k。题集、标注、索引快照（包括向量）、主要执行代码的SHA256一致；裁判模型、选项、规则与评分代码SHA256一致。前三名检索结果保持一致。参考答案在生成结束后才加入裁判记录，已核对实际生成messages。

| 项目 | top3 | top5 |
|---|---:|---:|
| 平均Recall（分别@3、@5，90题） | 80.37% | 89.63% |
| 裁判正确性均分（0至2，100题） | 1.86 | 1.96 |
| 裁判忠实度均分（0至2，100题） | 1.90 | 1.97 |
| 裁判相关性均分（0至2，100题） | 2.00 | 2.00 |
| 完整RAG p50（秒，成功100题） | 0.825 | 0.728 |
| 输入token总量（100题） | 34936 | 48513 |
| 输出token总量（100题） | 3268 | 3251 |
| 输入缓存命中token | 14718 | 26240 |
| 输入缓存未命中token | 20218 | 22273 |

输入增加13577 token，即38.86%。平均每题输入从349.36增加到485.13 token。完整RAG计时包含问题向量化、查询、提示词拼接、生成和响应处理，不含模型/数据库初始化及评分。两套配置各顺序跑一次，后运行的top5缓存命中更多，网络和服务状态也可能变化；不能据一次p50下降认定top5更快。

按[DeepSeek官方价格页](https://api-docs.deepseek.com/quick_start/pricing/)2026-10-13核对的Flash单价，结合实际缓存用量：全低峰/全高峰假设下，top3这100次生成估算0.005038/0.010075美元，top5估算0.005370/0.010741美元。平均每次约0.00005038至0.00010075美元与0.00005370至0.00010741美元。只是成功答案生成估算，非实际账单，不含本轮200次裁判、其他探针、重试与机器成本。价表快照、计算公式和原始usage均保留。

## 配对比较

同一道题分别对应两个评分，再计算top5减top3：
- 正确性：6题提高、93题不变、1题下降，均分差+0.10。
- 忠实度：4题提高、96题不变、0题下降，均分差+0.07。
- 相关性：100题不变。

这些是裁判判定，不是独立人工复核后的进步或退步计数。比较题comparison_015中补回UploadPart依据后完整回答，是已经核对过的实际改善；comparison_012被裁判判为退步，但top3原评分本身有问题，不能据此断言更多片段导致退步。

## 定向检查发现的评分问题

已单独保存5条疑似问题的助手复核，原裁判记录与汇总不改写：
- comparison_007/top3：裁判用参考答案有答案为由，给实际资料不足的拒答忠实度0，违反既定分工。
- multi_hop_003/top5：资料仍缺少Object default继承规则，裁判却将关键结论判为完全支持。
- multi_hop_011/top5：回答包含具体404响应，但实际片段没有GET/404规则，裁判漏扣忠实度。
- comparison_012/top3：裁判将“未指定版本”的规则反向推断成“指定版本”的规则，并给不完整回答满分。
- comparison_004/top3：正确回答了两项中的一项，裁判将部分回答记正确性0且相关性2，助手认为应1/2/1。

详见 judge_spot_review.json。该复核只针对5个怀疑案例，不是200条独立审核，不推算“修正后的整体均分”。评分模型也负责生成，仍有自我偏好风险；固定开发题集不能当生产分布或独立测试集。

## 可复现入口与文件

执行生成：
```powershell
.\.venv\Scripts\python.exe scripts/run_batch_experiment.py --config examples/day8/top3.json --generate
.\.venv\Scripts\python.exe scripts/run_batch_experiment.py --config examples/day8/top5.json --generate
```

批量记录用 scripts/export_batch_answers.py 转换后，交给已有 scripts/judge_eval_answers.py；scripts/compare_batch_experiments.py 校验共同条件、计算配对差异、汇总用量和耗时。

原始记录：
- data/eval_results/day8/rag_batch_1791861421126117700.json
- data/eval_results/day8/rag_batch_1791861599370558900.json
- 同名追加_answers.json的转换记录
- data/eval_results/day8/top3_100_judgments_v1.json
- data/eval_results/day8/top5_100_judgments_v1.json
- data/eval_results/day8/top3_top5_comparison_v1.json

新增导出与对照脚本，加上配置、检索、提示词、共享流程、两个运行入口共8个文件mypy通过。两组100题计数、配对差异、均分计算关系及输入来源校验通过。

本次完成一个上下文数量对照与完整链路基线；尚未进行两种EmbeddingProvider/向量库的实现对照，不为满足接口数量添加空实现。课程下一步应理解配对比较与裁判误差，再进行真实检索策略实验。
