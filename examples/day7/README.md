# Day 7：检索指标基线

100 题生成评测已运行，最新结果与失败分析见 `generation_baseline.md`。它使用自定义三维规则，不是 RAGAS 官方评测；独立人工校准仍未完成。

RAGAS 0.4.3 的最小接入现已运行：Faithfulness 一题及片段编号对照，AnswerRelevancy 一条真实回答加两个助手编写反例。方法、实际分数和限制见 `ragas_comparison.md`。没有将小样例结果冒充完整 100 题的 RAGAS 报告。

用户已将剩余 39 条审核委托助手完成。AI 复核与 DeepSeek 对照见 `ai_review_summary.md`，39 条均已审核，8 条存在至少一个评分分歧。人类初次评分仍仅 1 条；AI 评分另存，没有填进人工表或当作人工一致率。

人工标尺准备在 `human_calibration_40.json`：12 单跳、10 多跳、8 对比、5 表格、5 资料不足，选择典型及困难案例，不是随机生产样本。三个维度的人工分数当前均为 null，尚未完成一条，不填入助手建议冒充人工评分。表内不显示模型裁判分数，方便先独立判断。

本地运行 `scripts/compare_judge_labels.py` 比较真正填写完三个维度的记录，分别计算各维度精确一致率与整条三个分数全部一致的比例。未填完记录与评分失败单独计数；没有完成记录时一致率是 null，不是 0%。当前人工比较输出 `data/eval_results/day7_human_judge_agreement.json` 为 1 条已比较、39 条人工分数为空。使用 `--reviewer assistant --labels examples/day7/assistant_review_39.json --output data/eval_results/day7_ai_judge_agreement_39.json` 比较 AI 分数，输出及审核身份分开。

指标函数在 `src/kb/metrics.py`，批量评分入口为 `scripts/evaluate_metrics.py`。

本次使用固定 Day 6 的 100 题和 53 条索引记录。90 道可回答题参与指标均值，10 道资料不足题为未评分状态，后续单独评测拒答。

## 指标

- Recall@k：前 k 名找到多少标注相关片段。
- MRR@k：每题第一条相关片段的倒数排名，再对参与评分题求均值。
- nDCG@k：相关片段按位置折扣累加，除以理想排序得分。当前采用二元相关性，各标注相关片段同等重要。

这些是检索指标，不是生成准确率，也不是拒答成功率。

## 结果

| k | 平均 Recall@k | MRR@k | 平均 nDCG@k |
| --- | ---: | ---: | ---: |
| 3 | 80.37% | 0.7870 | 0.7507 |
| 5 | 89.63% | 0.8031 | 0.7944 |
| 10 | 95.37% | 0.8058 | 0.8172 |
| 20 | 98.33% | 0.8058 | 0.8267 |

结果汇总为 `retrieval_baseline.json`，逐题结果保存在 `data/eval_results/day6_oss_v1_bge_small_zh_oss_cases_100_top{k}_metrics{k}.json`。

标注来自必要事实 ID 与实际片段 ID 的对应，详见 `relevance_labels.json`。它不是所有语义相关候选的穷尽人工标注；指标只相对于这个标注集合计算。修改资料、切片或索引后必须重新检查标签，不能把旧 ID 直接用于新索引。

## 复现示例

在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py --cases examples/day6/oss_cases_100.json --collection day6_oss_v1_bge_small_zh --top-k 10
.\.venv\Scripts\python.exe scripts/evaluate_metrics.py --report data/eval_results/day6_oss_v1_bge_small_zh_oss_cases_100_top10.json --k 10
```

可以对保存了 10 个候选的报告计算 k<=10 的指标，但不能从只有 3 个候选的报告推算 Recall@20。批量指标程序会拒绝后一种情况。

## 本次验证与下一步

已验证三个核心函数的边界、重复 ID 和未评分处理，逐题结果范围以及四组指标的汇总一致性。新的检索运行仅使用本地 BGE 与 Chroma；指标程序只读取保存结果，不调用模型。

更多候选提高了本样例的覆盖，但未测生成质量、延迟和成本。多跳 Recall@5 为 62.50%，Recall@20 为 95.00%，后续可以验证更大候选集配合重排序等方案；不能据此直接认定应把 20 个片段全部交给 LLM。

下一步学习生成答案的忠实度、问题相关性以及资料不足时的拒答，生成指标需要新的数据和校准，不能把当前检索分数当作生成分数。

## 生成评分与裁判检查

`generation_rubric.md` 是自定义 0～2 分规则，`src/kb/answer_evaluation.py` 负责调用裁判并检查输出格式。`scripts/judge_eval_answers.py` 对已保存的三条真实回答评分，结果在 `data/eval_results/day7_judge_sample.json`，三题三个维度均为 2。生成与裁判均使用 DeepSeek Flash，这不是独立人工验证，也不是 100 题的生成准确率。

`judge_checks.json` 包含助手编写的六条虚构教学样例，预设标签待用户审核。`scripts/check_judge.py` 只将问题、前提、资料、待评回答、参考答案与规则传给裁判，不发送预设分数，并去掉规则中的带分数教学反例。

本次结果在 `data/eval_results/day7_judge_checks.json`：六次评分均返回合法结果，五条的三个分数与预设完全相同。唯一差异是“资料明确有答案却拒答”的相关性：预设 2，裁判给 1，理由是没有提供所询问信息。这暴露了相关性规则对拒答的边界仍需澄清。未修改预设分数迎合模型；该检查不构成独立人工校准，六条样例也不代表实际分布。

用户确认了 v2 拒答边界：仅针对当前问题的拒答，相关性记 2，合理性由正确性和忠实度分别判断。仅重评 `unnecessary_refusal`，新结果在 `data/eval_results/day7_judge_checks_v2_refusal.json`，得分为正确性 0、忠实度 0、相关性 2，与预设一致。旧结果保留；其余五条没有使用 v2 重评。针对同一已知分歧修订规则后重评，不等于独立样例校准或证明裁判整体可靠。

## 三条真实回答的汇总

运行 `scripts/summarize_generation.py` 只读取本地记录，不调用模型。输出 `data/eval_results/day7_generation_summary.json`：三条生成成功、三条评分成功，三个维度平均分均为 2。汇总复用原始三题的 v1 评分，不把它们标记为已经用 v2 重评；评分规则哈希保留在输出中。

拒答行为标注在 `response_behavior_labels.json`，由助手审核而非独立用户人工审核。三条中拒答 1 条（1/3）；题集资料不足题拒答 1/1；题集可回答题拒答 0/2。本次片段明确足以回答的题只有 1 条被确认，错误拒答为 0/1；`multi_hop_004` 的片段充分性留为待审核，不将覆盖率 50% 自动转为资料不足标签。分母为 0 返回 null；失败单独计数。

上述少量示例用于学习统计口径，不是完整 100 题的拒答效果，也不是人工验证的生成准确率。题集层面的可回答性与每次实际上下文的充分性必须分开：检索遗漏答案时拒答可能合理，同时系统仍存在检索失败。
