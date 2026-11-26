# Day 8：补回依据能否改善回答？

2026-10-13，使用相同实验代码、题集、标签和索引，实际生成 top3/top5 两个回答。教学题 comparison_015：“UploadPart 与 ListParts 所需的权限 Action 有何不同？”

该题根据上一轮检索报告有目的地选择：top3缺少UploadPart的必要依据，top5在第4位找到该依据。因此是展示机制的单题案例，不是随机样本或100题生成结论。

## top3

实际回答：资料仅说明 ListParts 对应的权限 Action 是 `oss:ListParts` [1]，未说明 UploadPart 所需的权限 Action，因此无法比较两者不同。

相关片段仅找到2个必要依据中的1个，Recall@3=0.5。它按实际上下文说明缺失信息，没有凭空补答案。助手按既有规则复核：正确性1、忠实度2、相关性1；不是完整回答，也不是不忠实的回答。

## top5

实际回答：UploadPart 对应的权限 Action 是 oss:PutObject [4]；ListParts 对应的权限 Action 是 oss:ListParts [1]。

第4位片段包含“UploadPart 对应的权限 Action 是 oss:PutObject。”，找齐2个必要依据，Recall@5=1。回答完整并引用匹配的资料。助手复核为2/2/2。

| 项目 | top3 | top5 |
|---|---:|---:|
| prompt_tokens | 308 | 422 |
| completion_tokens | 35 | 31 |
| total_tokens | 343 | 453 |
| 完整问答耗时（秒） | 3.201 | 1.952 |

top5本次输入增加114个token，且回答变得完整；单次生成耗时反而更短。两个样本不足以推断总体速度、费用或质量。缓存命中量不同，token总量也不能直接当实际账单；原始usage已保留。样本数1时汇总中的p50就是该题耗时，不能作为100题基线。

原始生成记录位于 data/eval_results/day8/rag_batch_1791861204939858200.json 和 rag_batch_1791861232231541700.json。单题评分是助手复核，保存于 generation_pair_review.json，未新增DeepSeek裁判调用，也不记为独立人工校准。

学习重点：先定位失败发生在检索还是生成。top3的问题是缺少依据，此时要求模型更自信不能解决检索缺失。增加候选在本题有效；整体最优top_k仍须批量质量、耗时和token对照。
